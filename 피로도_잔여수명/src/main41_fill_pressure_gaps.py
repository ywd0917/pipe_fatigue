#!/usr/bin/env python
"""
main41_fill_pressure_gaps.py

압력 데이터의 결측 구간(gap)을 채우는 메인 스크립트.
- 1시간 이내 gap: XGBoost 기계학습 보간
- 1시간 초과 gap: Component-wise Spectral 방법 (ARMA + Random Phase)

모든 6개 지역 처리: 0243, 0461, 0470, 0480, 0490, 0520
"""

import sys
import warnings
import argparse
import json
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# Common modules
sys.path.append(str(Path(__file__).parent))
from common.config import get_config
from common.file_utils import ensure_directory_exists, validate_file_exists
from common.logging_utils import setup_logging, log_execution_time
from common.validation import validate_date_format, validate_required_columns
from common.visualization_utils import setup_korean_font, setup_plot_style
from common.gap_fill_utils import (
    detect_gaps, fill_pressure_gaps,
    validate_filled_data, xgboost_interpolation,
    spectral_gap_fill, butterworth_frequency_separation
)

# Suppress warnings
warnings.filterwarnings('ignore')

# Logger
logger = None

# ============================================================================
# Configuration
# ============================================================================

# 지역 코드 리스트
AREA_CODES = ['0243', '0461', '0470', '0480', '0490', '0520']

# Gap filling 파라미터
GAP_THRESHOLD_HOURS = 1.0  # XGBoost vs Spectral 선택 기준
V_VALLEY_MINUTES = 553.5   # main51과 동일
SAMPLING_MINUTES = 5.0      # 5분 간격

# ============================================================================
# Data Loading
# ============================================================================

def load_pressure_data(area_code: str, config: Dict) -> Tuple[pd.DataFrame, Path]:
    """
    압력 데이터 로드.

    Parameters
    ----------
    area_code : str
        지역 코드
    config : Dict
        설정 정보

    Returns
    -------
    Tuple[pd.DataFrame, Path]
        (데이터프레임, 파일 경로)
    """
    # 파일 경로 구성
    raw_dir = Path(config.RAW_DATA_DIR)

    # 모든 CSV 파일 중에서 패턴 매칭 (더 안정적인 방법)
    all_csv_files = list(raw_dir.glob('*.csv'))
    matching_files = []

    # 디버깅: 0520인 경우 파일 목록 출력
    if area_code == '0520':
        logger.info(f"Looking in directory: {raw_dir}")
        logger.info(f"Found {len(all_csv_files)} CSV files")
        for f in all_csv_files:
            if '0520' in f.name:
                logger.info(f"  - {f.name}")

    # 지역 코드로 시작하고 "압력 데이터.csv"로 끝나는 파일 찾기
    # (소구역, 중구역, 대구역 모두 포함)
    # macOS 파일 시스템의 NFD 한글 인코딩 대응
    for file in all_csv_files:
        normalized_name = unicodedata.normalize('NFC', file.name)
        if (normalized_name.startswith(area_code) and
            '구역' in normalized_name and
            normalized_name.endswith('압력 데이터.csv')):
            matching_files.append(file)
            logger.info(f"Matched: {file.name}")

    if not matching_files:
        logger.warning(f"No pressure data file found for area {area_code}")
        return None, None

    # 첫 번째 매칭 파일 사용
    file_path = matching_files[0]

    if len(matching_files) > 1:
        logger.warning(f"Multiple files found for {area_code}, using: {file_path.name}")
    else:
        logger.info(f"Found file: {file_path.name}")

    try:
        # CSV 파일 읽기 (euc-kr 인코딩)
        df = pd.read_csv(file_path, encoding='euc-kr')

        # 컬럼 검증
        required_columns = ['manage_id', 'msrmt_dt', 'wtrprsr']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Missing required columns in {area_code}")
            return None, file_path

        # 날짜 파싱
        df['msrmt_dt'] = pd.to_datetime(df['msrmt_dt'])
        df = df.sort_values('msrmt_dt').reset_index(drop=True)

        # 압력 데이터를 float으로 변환
        df['wtrprsr'] = pd.to_numeric(df['wtrprsr'], errors='coerce')

        logger.info(f"Loaded {area_code}: {len(df)} records, "
                   f"{df['wtrprsr'].isna().sum()} missing values")

        return df, file_path

    except Exception as e:
        logger.error(f"Failed to load {area_code}: {e}")
        return None, file_path

# ============================================================================
# Gap Filling
# ============================================================================

def process_area_gaps(df: pd.DataFrame, area_code: str) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    한 지역의 모든 gap을 처리.

    Parameters
    ----------
    df : pd.DataFrame
        압력 데이터
    area_code : str
        지역 코드

    Returns
    -------
    Tuple[pd.DataFrame, List[Dict]]
        (채워진 데이터프레임, gap 정보)
    """
    if df is None:
        return None, []

    # 압력 데이터 추출
    pressure_data = df['wtrprsr'].values.copy()
    timestamps = df['msrmt_dt']

    # Gap 탐지
    gaps = detect_gaps(pressure_data, timestamps)

    if not gaps:
        logger.info(f"{area_code}: No gaps detected")
        return df, []

    logger.info(f"{area_code}: Found {len(gaps)} gaps")

    # Gap별로 처리
    filled_data = pressure_data.copy()
    gap_info_list = []

    for i, gap in enumerate(gaps):
        start_idx = gap['start_idx']
        end_idx = gap['end_idx']
        length = gap['length']
        length_hours = gap.get('length_hours', length * SAMPLING_MINUTES / 60)

        # 방법 선택
        if length_hours <= GAP_THRESHOLD_HOURS:
            method = 'xgboost'
            logger.info(f"  Gap {i+1}: {length} points ({length_hours:.2f}h) - Using XGBoost")
            filled_data = xgboost_interpolation(filled_data, start_idx, end_idx)
        else:
            method = 'spectral'
            logger.info(f"  Gap {i+1}: {length} points ({length_hours:.2f}h) - Using Spectral")
            filled_data = spectral_gap_fill(filled_data, start_idx, end_idx, V_VALLEY_MINUTES)

        # Gap 정보 저장
        gap_info = {
            'gap_id': i + 1,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'length': length,
            'length_hours': length_hours,
            'method': method
        }

        if 'start_time' in gap:
            gap_info['start_time'] = str(gap['start_time'])
        if 'end_time' in gap:
            gap_info['end_time'] = str(gap['end_time'])

        gap_info_list.append(gap_info)

    # 채워진 데이터로 DataFrame 업데이트
    df_filled = df.copy()
    df_filled['wtrprsr_original'] = df['wtrprsr']
    df_filled['wtrprsr'] = filled_data
    df_filled['gap_filled'] = pd.Series(pressure_data).isna() & ~pd.Series(filled_data).isna()

    # 검증
    validation = validate_filled_data(pressure_data, filled_data,
                                     [(g['start_idx'], g['end_idx']) for g in gap_info_list])

    logger.info(f"{area_code}: Validation - {validation}")

    return df_filled, gap_info_list

# ============================================================================
# Visualization
# ============================================================================

def visualize_gap_filling(df_original: pd.DataFrame, df_filled: pd.DataFrame,
                         area_code: str, gap_info: List[Dict],
                         output_dir: Path) -> Path:
    """
    Gap filling 결과 시각화.

    Parameters
    ----------
    df_original : pd.DataFrame
        원본 데이터
    df_filled : pd.DataFrame
        채워진 데이터
    area_code : str
        지역 코드
    gap_info : List[Dict]
        Gap 정보
    output_dir : Path
        출력 디렉토리

    Returns
    -------
    Path
        저장된 이미지 경로
    """
    if df_filled is None or not gap_info:
        return None

    # 한글 폰트 설정
    setup_korean_font()

    # Figure 생성
    fig, axes = plt.subplots(3, 1, figsize=(15, 10))

    timestamps = df_filled['msrmt_dt']
    original = df_filled['wtrprsr_original'].values
    filled = df_filled['wtrprsr'].values

    # 1. 전체 시계열
    ax = axes[0]
    ax.plot(timestamps, original, 'b-', alpha=0.5, label='원본 데이터', linewidth=0.5)
    ax.plot(timestamps, filled, 'r-', alpha=0.7, label='채워진 데이터', linewidth=0.5)

    # Gap 영역 표시
    for gap in gap_info:
        start_idx = gap['start_idx']
        end_idx = gap['end_idx']
        if start_idx < len(timestamps) and end_idx <= len(timestamps):
            ax.axvspan(timestamps.iloc[start_idx], timestamps.iloc[end_idx-1],
                      alpha=0.2, color='yellow',
                      label=f"Gap (방법: {gap['method']})" if gap == gap_info[0] else "")

    ax.set_title(f'{area_code} 지역 - 전체 압력 데이터')
    ax.set_xlabel('시간')
    ax.set_ylabel('압력 (MPa)')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    # 2. Gap 주변 확대 (첫 번째 gap)
    if gap_info:
        ax = axes[1]
        first_gap = gap_info[0]
        start_idx = max(0, first_gap['start_idx'] - 200)
        end_idx = min(len(timestamps), first_gap['end_idx'] + 200)

        ax.plot(timestamps.iloc[start_idx:end_idx],
               original[start_idx:end_idx], 'b-', alpha=0.7, label='원본', linewidth=1)
        ax.plot(timestamps.iloc[start_idx:end_idx],
               filled[start_idx:end_idx], 'r-', alpha=0.9, label='채워짐', linewidth=1)

        # Gap 영역 표시
        gap_start = timestamps.iloc[first_gap['start_idx']]
        gap_end = timestamps.iloc[min(first_gap['end_idx']-1, len(timestamps)-1)]
        ax.axvspan(gap_start, gap_end, alpha=0.3, color='yellow')

        ax.set_title(f'Gap 주변 확대 ({first_gap["length_hours"]:.1f}시간 gap, '
                    f'{first_gap["method"]} 방법)')
        ax.set_xlabel('시간')
        ax.set_ylabel('압력 (MPa)')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

    # 3. 통계 정보
    ax = axes[2]
    ax.axis('off')

    # 통계 텍스트
    stats_text = f"""
    지역 코드: {area_code}
    전체 데이터 포인트: {len(df_filled):,}
    총 Gap 수: {len(gap_info)}
    채워진 포인트: {df_filled['gap_filled'].sum():,}

    Gap 상세:
    """

    for i, gap in enumerate(gap_info):
        stats_text += f"\n    Gap {i+1}: {gap['length']} 포인트 ({gap['length_hours']:.1f}시간) - {gap['method'].upper()} 방법"
        if 'start_time' in gap and 'end_time' in gap:
            stats_text += f"\n        {gap['start_time']} ~ {gap['end_time']}"

    ax.text(0.1, 0.9, stats_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top')

    plt.tight_layout()

    # 저장
    output_path = output_dir / f'{area_code}_gap_comparison.png'
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()

    logger.info(f"Saved visualization: {output_path}")
    return output_path

# ============================================================================
# Report Generation
# ============================================================================

def generate_report(all_results: Dict[str, Any], output_dir: Path) -> Path:
    """
    전체 처리 결과 보고서 생성.

    Parameters
    ----------
    all_results : Dict
        모든 지역 처리 결과
    output_dir : Path
        출력 디렉토리

    Returns
    -------
    Path
        보고서 경로
    """
    report_path = output_dir / 'gap_filling_report.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# 압력 데이터 Gap Filling 보고서\n\n')
        f.write(f'**생성 일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'**처리 스크립트**: main41_fill_pressure_gaps.py\n\n')

        f.write('---\n\n')
        f.write('## 1. 요약\n\n')

        # 처리된 지역 수 계산
        processed = sum(1 for r in all_results.values() if r['processed'])
        gaps_found = sum(len(r['gaps']) for r in all_results.values())
        xgboost_count = sum(1 for r in all_results.values()
                          for g in r['gaps'] if g.get('method') == 'xgboost')
        spectral_count = sum(1 for r in all_results.values()
                           for g in r['gaps'] if g.get('method') == 'spectral')

        f.write(f'- **전체 지역**: {len(all_results)}개\n')
        f.write(f'- **처리된 지역**: {processed}개\n')
        f.write(f'- **발견된 Gap**: {gaps_found}개\n')
        f.write(f'- **XGBoost 방법**: {xgboost_count}개 gap\n')
        f.write(f'- **Spectral 방법**: {spectral_count}개 gap\n\n')

        f.write('---\n\n')
        f.write('## 2. 지역별 상세\n\n')

        for area_code in AREA_CODES:
            result = all_results.get(area_code, {})

            f.write(f'### {area_code} 지역\n\n')

            if not result.get('processed'):
                f.write('- **상태**: ❌ 파일 없음 또는 오류\n\n')
                continue

            gaps = result.get('gaps', [])

            if not gaps:
                f.write('- **상태**: ✅ Gap 없음 (데이터 완전)\n')
            else:
                f.write(f'- **상태**: ✅ {len(gaps)}개 gap 처리 완료\n')
                f.write('- **Gap 상세**:\n\n')

                f.write('| Gap # | 포인트 수 | 시간 (h) | 방법 | 시작 시간 | 종료 시간 |\n')
                f.write('|-------|----------|---------|------|-----------|----------|\n')

                for gap in gaps:
                    start_time = gap.get('start_time', '-')
                    end_time = gap.get('end_time', '-')
                    f.write(f'| {gap["gap_id"]} | {gap["length"]} | '
                           f'{gap["length_hours"]:.1f} | {gap["method"].upper()} | '
                           f'{start_time} | {end_time} |\n')

            # 시각화 링크
            if result.get('visualization'):
                viz_path = Path(result['visualization']).name
                f.write(f'\n![{area_code} Gap 비교](visualizations/{viz_path})\n')

            f.write('\n')

        f.write('---\n\n')
        f.write('## 3. 처리 방법 설명\n\n')
        f.write('### XGBoost (≤ 1시간 gap)\n')
        f.write('- 기계학습 기반 시계열 예측\n')
        f.write('- 주변 데이터의 패턴을 학습하여 정확한 예측\n')
        f.write('- 짧은 gap에 효과적\n\n')

        f.write('### Spectral (> 1시간 gap)\n')
        f.write('- Component-wise 주파수 도메인 접근\n')
        f.write('- Butterworth 필터로 저/고주파 분리\n')
        f.write('- 저주파: ARMA 모델, 고주파: Random Phase IFFT\n')
        f.write('- 긴 gap에서도 시계열 특성 유지\n\n')

        f.write('---\n\n')
        f.write('## 4. 다음 단계\n\n')
        f.write('1. **main51_find_freq.py** 실행하여 주파수 분석\n')
        f.write('2. **main52-57** 피로 분석 파이프라인 실행\n')
        f.write('3. Gap이 채워진 기간의 피로 분석 결과 신뢰도 검토\n\n')

        f.write('---\n\n')
        f.write('**보고서 종료**\n')

    logger.info(f"Report saved: {report_path}")
    return report_path

# ============================================================================
# Main Function
# ============================================================================

@log_execution_time
def main(areas: List[str] = None, skip_no_gap: bool = False,
         output_dir: Path = None, visualize: bool = True) -> Dict[str, Any]:
    """
    메인 처리 함수.

    Parameters
    ----------
    areas : List[str]
        처리할 지역 코드 리스트 (None이면 전체)
    skip_no_gap : bool
        Gap이 없는 지역 건너뛰기
    output_dir : Path
        출력 디렉토리
    visualize : bool
        시각화 생성 여부

    Returns
    -------
    Dict[str, Any]
        처리 결과
    """
    global logger

    # Configuration
    config = get_config()

    # Output directory
    if output_dir is None:
        output_dir = Path(config.RESULTS_DIR) / 'main41_gap_filling'

    ensure_directory_exists(output_dir)
    ensure_directory_exists(output_dir / 'filled_data')
    ensure_directory_exists(output_dir / 'quality_metrics')
    ensure_directory_exists(output_dir / 'visualizations')

    # Setup logging
    log_file = output_dir / 'main41.log'
    logger = setup_logging('INFO', log_file)

    logger.info('=' * 70)
    logger.info('Starting main41_fill_pressure_gaps.py')
    logger.info('=' * 70)

    # 처리할 지역 결정
    if areas is None:
        areas = AREA_CODES

    logger.info(f"Processing areas: {areas}")

    # 전체 결과 저장
    all_results = {}

    # 각 지역 처리
    for area_code in areas:
        logger.info(f"\nProcessing area: {area_code}")
        logger.info('-' * 50)

        result = {
            'area': area_code,
            'processed': False,
            'gaps': [],
            'file_path': None,
            'output_file': None,
            'visualization': None,
            'metrics': {}
        }

        # 데이터 로드
        df, file_path = load_pressure_data(area_code, config)
        result['file_path'] = str(file_path) if file_path else None

        if df is None:
            logger.warning(f"Skipping {area_code}: Failed to load data")
            all_results[area_code] = result
            continue

        # Gap 처리
        df_filled, gap_info = process_area_gaps(df, area_code)

        if df_filled is None:
            logger.warning(f"Skipping {area_code}: Processing failed")
            all_results[area_code] = result
            continue

        result['processed'] = True
        result['gaps'] = gap_info

        # Gap이 없으면 건너뛰기 옵션
        if skip_no_gap and not gap_info:
            logger.info(f"Skipping {area_code}: No gaps to fill")
            all_results[area_code] = result
            continue

        # 결과 저장
        if gap_info:  # Gap이 있는 경우만 저장
            output_file = output_dir / 'filled_data' / f'{area_code}_filled.csv'

            # 메타데이터 추가
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('# Gap Filling Metadata\n')
                f.write(f'# Original file: {file_path.name}\n')
                f.write(f'# Gaps filled: {len(gap_info)}\n')
                for gap in gap_info:
                    f.write(f'# Gap {gap["gap_id"]}: {gap.get("start_time", "N/A")} ~ '
                           f'{gap.get("end_time", "N/A")} ({gap["length"]} points, '
                           f'{gap["method"]} method)\n')
                f.write(f'# Processed by: main41_fill_pressure_gaps.py\n')
                f.write(f'# Date: {datetime.now()}\n')
                f.write('#\n')

            # CSV 저장 (원본 컬럼만)
            df_save = df_filled[['manage_id', 'msrmt_dt', 'wtrprsr']].copy()
            df_save.to_csv(output_file, mode='a', index=False, encoding='utf-8')

            result['output_file'] = str(output_file)
            logger.info(f"Saved filled data: {output_file}")

            # 메트릭 저장 (numpy 타입을 Python 타입으로 변환)
            metrics = {
                'area': area_code,
                'total_records': int(len(df_filled)),
                'total_gaps_filled': int(len(gap_info)),
                'gaps': gap_info,
                'timestamp': datetime.now().isoformat()
            }

            # gap_info 내의 numpy 타입도 변환
            for gap in metrics['gaps']:
                for key, value in gap.items():
                    if isinstance(value, (np.integer, np.int64)):
                        gap[key] = int(value)
                    elif isinstance(value, (np.floating, np.float64)):
                        gap[key] = float(value)

            metrics_file = output_dir / 'quality_metrics' / f'{area_code}_metrics.json'
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

            result['metrics'] = metrics
            logger.info(f"Saved metrics: {metrics_file}")

        # 시각화
        if visualize and gap_info:
            viz_path = visualize_gap_filling(
                df, df_filled, area_code, gap_info,
                output_dir / 'visualizations'
            )
            result['visualization'] = str(viz_path) if viz_path else None

        all_results[area_code] = result

    # 전체 보고서 생성
    report_path = generate_report(all_results, output_dir)

    logger.info('\n' + '=' * 70)
    logger.info('Processing completed')
    logger.info(f'Report: {report_path}')
    logger.info('=' * 70)

    return all_results

# ============================================================================
# CLI Interface
# ============================================================================

def parse_arguments():
    """커맨드 라인 인자 파싱."""
    parser = argparse.ArgumentParser(
        description='압력 데이터 Gap Filling (XGBoost + Spectral)'
    )

    parser.add_argument(
        '--areas',
        nargs='+',
        default=None,
        help='처리할 지역 코드 (기본값: 전체)'
    )

    parser.add_argument(
        '--skip-no-gap',
        action='store_true',
        help='Gap이 없는 지역 건너뛰기'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='출력 디렉토리'
    )

    parser.add_argument(
        '--no-visualize',
        action='store_true',
        help='시각화 생성 안함'
    )

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    # XGBoost 설치 확인
    try:
        import xgboost as xgb
        print(f"XGBoost version: {xgb.__version__}")
    except ImportError:
        print("Warning: XGBoost not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost>=1.7.0"])
        print("XGBoost installed successfully. Please run the script again.")
        sys.exit(0)

    # 실행
    results = main(
        areas=args.areas,
        skip_no_gap=args.skip_no_gap,
        output_dir=args.output_dir,
        visualize=not args.no_visualize
    )

    # 결과 출력
    print("\nProcessing Summary:")
    print("-" * 50)
    for area_code, result in results.items():
        if result['processed']:
            gaps = len(result['gaps'])
            status = f"{gaps} gaps filled" if gaps > 0 else "No gaps"
            print(f"{area_code}: ✅ {status}")
        else:
            print(f"{area_code}: ❌ Failed or not found")