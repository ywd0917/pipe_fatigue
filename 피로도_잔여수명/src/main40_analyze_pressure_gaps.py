"""
main40_analyze_pressure_gaps.py
압력 데이터 결측치 및 시간 간격 품질 검사 스크립트

주요 기능:
- 결측치 분석 (빈 값, NaN, 연속 결측 구간 탐지)
- 시간 간격 검증 (5분 간격 불일치, 중복 타임스탬프, 시간 순서 검증)
- 임계값 기반 자동 경고 (모든 지역 동일 기준 적용)
- 시각화 및 Markdown 보고서 생성
"""

import argparse
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# src/common 유틸리티 import
from src.common.config import get_config
from src.common.file_utils import ensure_directory_exists, validate_file_exists
from src.common.logging_utils import (
    ProgressLogger,
    log_execution_time,
    setup_logging,
)
from src.common.validation import validate_date_format, validate_required_columns
from src.common.visualization_utils import (
    get_color_palette,
    setup_korean_font,
    setup_plot_style,
)

# =============================================================================
# 상수 및 설정
# =============================================================================

DEFAULT_THRESHOLDS = {
    "missing_ratio_warning": 1.0,  # 1% 이상 → WARNING
    "missing_ratio_critical": 3.0,  # 3% 이상 → CRITICAL
    "consecutive_hours_warning": 24,  # 24시간 이상 → WARNING
    "consecutive_days_critical": 7,  # 7일 이상 → CRITICAL
}

EXPECTED_INTERVAL_SEC = 300  # 5분 간격


# =============================================================================
# 데이터 로딩 함수
# =============================================================================


def extract_area_name(file_path: Path) -> str:
    """
    파일명에서 지역 번호 추출

    Args:
        file_path: 압력 데이터 파일 경로

    Returns:
        지역 번호 (예: "0470", "0520")
    """
    # 정규식으로 4자리 숫자 추출
    match = re.search(r"(\d{4})", file_path.name)
    if match:
        return match.group(1)
    return "Unknown"


@log_execution_time
def load_pressure_data(file_path: Path, encoding: str = "euc-kr") -> pd.DataFrame:
    """
    압력 데이터 CSV 로드

    Args:
        file_path: CSV 파일 경로
        encoding: 파일 인코딩

    Returns:
        압력 데이터 DataFrame
    """
    # macOS Unicode 정규화 (NFC)
    file_path = Path(unicodedata.normalize("NFC", str(file_path)))

    if not validate_file_exists(file_path, raise_error=False):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    # CSV 로드
    df = pd.read_csv(file_path, encoding=encoding)

    # 필수 컬럼 검증
    validate_required_columns(df, ["manage_id", "msrmt_dt", "wtrprsr"])

    # 날짜 변환
    df["msrmt_dt"] = validate_date_format(df["msrmt_dt"])

    # 시간순 정렬
    df = df.sort_values("msrmt_dt").reset_index(drop=True)

    return df


# =============================================================================
# 결측치 분석 함수
# =============================================================================


def detect_time_gap_missing(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    5분 간격 기준으로 빠진 시간대를 탐지하여 결측으로 표시

    Args:
        df: 압력 데이터 DataFrame (msrmt_dt, wtrprsr 포함)

    Returns:
        Tuple[pd.DataFrame, Dict]:
            - 완전한 5분 간격 시계열 DataFrame (빠진 시간대 NaN 추가)
            - 결측 통계 딕셔너리
    """
    # 원본 NaN 개수 (CSV에 행은 있지만 압력값이 NaN)
    original_nan_count = df['wtrprsr'].isna().sum()

    # 완전한 5분 간격 시계열 생성
    start_time = df['msrmt_dt'].min()
    end_time = df['msrmt_dt'].max()

    full_range = pd.date_range(
        start=start_time,
        end=end_time,
        freq='5min'
    )

    # 완전한 시계열 DataFrame 생성
    df_full = pd.DataFrame({'msrmt_dt': full_range})

    # 원본 데이터에 결측 유형 마커 추가
    df_with_marker = df.copy()
    df_with_marker['in_original'] = True

    # 원본 데이터와 병합 (빠진 시간대는 NaN)
    df_full = df_full.merge(df_with_marker, on='msrmt_dt', how='left')

    # 결측 유형 구분
    # 'nan': 원본에 있었지만 압력값이 NaN
    # 'time_gap': 원본에 없던 시간대 (Time Gap)
    # None: 정상 데이터
    df_full['missing_type'] = None
    df_full.loc[df_full['in_original'].isna(), 'missing_type'] = 'time_gap'
    df_full.loc[(df_full['in_original'] == True) & (df_full['wtrprsr'].isna()), 'missing_type'] = 'nan'

    # in_original 컬럼 제거
    df_full = df_full.drop(columns=['in_original'])

    # Time Gap 결측 개수 (5분 간격이 빠진 시간대)
    time_gap_missing_count = df_full['wtrprsr'].isna().sum() - original_nan_count

    # 통계 정보
    stats = {
        'original_records': len(df),
        'expected_records': len(df_full),
        'original_nan': original_nan_count,
        'time_gap_missing': time_gap_missing_count,
        'total_missing': df_full['wtrprsr'].isna().sum(),
    }

    return df_full, stats


def find_consecutive_gaps(df: pd.DataFrame) -> List[Dict]:
    """
    연속된 결측 구간 찾기

    Args:
        df: 압력 데이터 DataFrame

    Returns:
        연속 결측 구간 리스트
        [
            {
                "start_time": pd.Timestamp,
                "end_time": pd.Timestamp,
                "duration_hours": float,
                "missing_count": int,
            },
            ...
        ]
    """
    # 결측 마스크 생성
    missing_mask = df["wtrprsr"].isna()

    # 연속 구간 그룹화
    groups = missing_mask.ne(missing_mask.shift()).cumsum()

    gaps = []
    for group_id, group in df[missing_mask].groupby(groups[missing_mask]):
        if len(group) >= 3:  # 최소 3개 이상 (15분 이상)
            start_time = group["msrmt_dt"].iloc[0]
            end_time = group["msrmt_dt"].iloc[-1]
            duration_hours = (end_time - start_time).total_seconds() / 3600

            gaps.append(
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_hours": duration_hours,
                    "missing_count": len(group),
                }
            )

    return gaps


def detect_missing_values(df: pd.DataFrame, area_name: str) -> Dict:
    """
    결측치 패턴 분석 (NaN + Time Gap 결측 모두 탐지)

    Args:
        df: 압력 데이터 DataFrame
        area_name: 지역명

    Returns:
        결측치 분석 결과
    """
    # 원본 레코드 수
    original_records = len(df)

    # Time Gap 결측 탐지 (5분 간격 기준)
    df_full, gap_stats = detect_time_gap_missing(df)

    # 빈 문자열 개수
    empty_string_count = (df["wtrprsr"] == "").sum()

    # NaN 개수 (원본 데이터)
    nan_count = df["wtrprsr"].isna().sum()

    # Time Gap 결측 개수
    time_gap_missing = gap_stats['time_gap_missing']

    # 전체 결측 개수 (NaN + Time Gap)
    total_missing_count = gap_stats['total_missing']

    # 전체 예상 레코드 수 (5분 간격 기준)
    expected_records = gap_stats['expected_records']

    # 결측 비율 (전체 예상 레코드 대비)
    missing_ratio = (total_missing_count / expected_records * 100) if expected_records > 0 else 0

    # 연속 결측 구간 탐지 (완전한 시계열 기준)
    consecutive_gaps = find_consecutive_gaps(df_full)

    # 최대 연속 결측 기간
    max_gap_duration = max([gap["duration_hours"] for gap in consecutive_gaps], default=0)

    return {
        "area": area_name,
        "original_records": original_records,
        "expected_records": expected_records,
        "empty_string_count": empty_string_count,
        "nan_count": nan_count,
        "time_gap_missing": time_gap_missing,
        "total_missing": total_missing_count,
        "missing_ratio": missing_ratio,
        "consecutive_gaps": consecutive_gaps,
        "max_gap_duration": max_gap_duration,
        "df_full": df_full,  # 완전한 시계열 DataFrame (시각화용)
    }


# =============================================================================
# 시간 간격 검증 함수
# =============================================================================


def validate_time_intervals(
    df: pd.DataFrame, expected_interval_sec: int = EXPECTED_INTERVAL_SEC
) -> Dict:
    """
    시간 간격 검증

    Args:
        df: 압력 데이터 DataFrame
        expected_interval_sec: 예상 간격 (초)

    Returns:
        시간 간격 검증 결과
    """
    # 중복 타임스탬프 탐지
    duplicate_timestamps = df["msrmt_dt"].duplicated().sum()

    # 시간 순서 검증
    out_of_order = not df["msrmt_dt"].is_monotonic_increasing

    # 시간 간격 계산
    time_diff = df["msrmt_dt"].diff()
    intervals = time_diff.dt.total_seconds().dropna()

    # 불규칙 간격 (300초가 아닌 경우)
    irregular_mask = intervals != expected_interval_sec
    irregular_intervals = intervals[irregular_mask]

    # 간격 분포
    interval_distribution = intervals.value_counts().to_dict()

    return {
        "duplicate_timestamps": int(duplicate_timestamps),
        "out_of_order": out_of_order,
        "irregular_count": len(irregular_intervals),
        "interval_distribution": interval_distribution,
        "irregular_intervals": irregular_intervals.head(100).to_dict(),  # 상위 100개만
    }


# =============================================================================
# 경고 생성 함수
# =============================================================================


def generate_warnings(results: Dict, thresholds: Dict = None) -> List[str]:
    """
    모든 지역에 동일한 임계값 적용하여 자동 경고 생성

    Args:
        results: 각 지역별 분석 결과
        thresholds: 경고 임계값 (None이면 DEFAULT_THRESHOLDS 사용)

    Returns:
        임계값 초과한 모든 지역의 경고 메시지 리스트
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    warnings = []

    for area, result in results.items():
        missing_ratio = result["missing"]["missing_ratio"]
        max_gap_hours = result["missing"]["max_gap_duration"]
        max_gap_days = max_gap_hours / 24
        total_missing = result["missing"]["total_missing"]
        nan_count = result["missing"]["nan_count"]
        time_gap_missing = result["missing"]["time_gap_missing"]

        # 결측 비율 검사
        if missing_ratio >= thresholds["missing_ratio_critical"]:
            warnings.append(
                f"🔴 CRITICAL: {area} 지역 결측 비율 {missing_ratio:.2f}% "
                f"(총 {total_missing:,}개: NaN {nan_count:,}개 + Time Gap {time_gap_missing:,}개, "
                f"임계값: {thresholds['missing_ratio_critical']:.1f}%)"
            )
        elif missing_ratio >= thresholds["missing_ratio_warning"]:
            warnings.append(
                f"⚠️ WARNING: {area} 지역 결측 비율 {missing_ratio:.2f}% "
                f"(총 {total_missing:,}개: NaN {nan_count:,}개 + Time Gap {time_gap_missing:,}개, "
                f"임계값: {thresholds['missing_ratio_warning']:.1f}%)"
            )

        # 연속 결측 검사
        if max_gap_days >= thresholds["consecutive_days_critical"]:
            gaps = result["missing"]["consecutive_gaps"]
            longest_gap = max(gaps, key=lambda x: x["duration_hours"]) if gaps else None
            if longest_gap:
                warnings.append(
                    f"🔴 CRITICAL: {area} 지역 최대 연속 결측 {max_gap_days:.1f}일 "
                    f"({longest_gap['start_time'].strftime('%Y-%m-%d')} ~ "
                    f"{longest_gap['end_time'].strftime('%Y-%m-%d')})"
                )
        elif max_gap_hours >= thresholds["consecutive_hours_warning"]:
            warnings.append(
                f"⚠️ WARNING: {area} 지역 최대 연속 결측 {max_gap_hours:.1f}시간 "
                f"(임계값: {thresholds['consecutive_hours_warning']}시간)"
            )

    return warnings


def generate_recommendations(area_result: Dict, thresholds: Dict) -> List[str]:
    """
    각 지역별 결측 비율에 따른 권장 조치사항

    Args:
        area_result: 특정 지역의 분석 결과
        thresholds: 임계값

    Returns:
        권장 조치사항 리스트
    """
    missing_ratio = area_result["missing"]["missing_ratio"]
    recommendations = []

    if missing_ratio < thresholds["missing_ratio_warning"]:
        recommendations.append("✅ 데이터 품질 양호. 그대로 사용 가능.")
    elif missing_ratio < thresholds["missing_ratio_critical"]:
        recommendations.append(
            "⚠️ linear 보간 권장. main51 실행 전 `interpolate_nan_values(method='linear')` 사용."
        )
    else:
        recommendations.append("🔴 time 또는 spline 보간 검토 필요.")
        recommendations.append("   - 연속 결측 구간이 긴 경우, 해당 기간을 분석에서 제외하는 것을 권장")
        recommendations.append("   - main20-30 공간 분석 시 해당 지역 가중치 낮춤 고려")

    return recommendations


# =============================================================================
# 시각화 함수
# =============================================================================


def plot_missing_comparison(
    results: Dict, output_dir: Path, thresholds: Dict
) -> None:
    """
    모든 지역 결측 비율 비교 막대 그래프

    Args:
        results: 전체 결과
        output_dir: 출력 디렉토리
        thresholds: 임계값
    """
    # 데이터 준비
    areas = []
    missing_ratios = []

    for area, result in sorted(results.items()):
        areas.append(area)
        missing_ratios.append(result["missing"]["missing_ratio"])

    # Figure 생성
    fig, ax = setup_plot_style(figsize=(12, 6), dpi=100)

    # 막대 색상 결정 (임계값 기반)
    colors = []
    for ratio in missing_ratios:
        if ratio >= thresholds["missing_ratio_critical"]:
            colors.append("#e74c3c")  # 빨간색 (CRITICAL)
        elif ratio >= thresholds["missing_ratio_warning"]:
            colors.append("#f39c12")  # 노란색 (WARNING)
        else:
            colors.append("#95a5a6")  # 회색 (정상)

    # 막대 그래프
    bars = ax.bar(areas, missing_ratios, color=colors, alpha=0.8, edgecolor="black")

    # 임계값 기준선
    ax.axhline(
        thresholds["missing_ratio_warning"],
        color="#f39c12",
        linestyle="--",
        linewidth=2,
        label=f"WARNING ({thresholds['missing_ratio_warning']:.1f}%)",
    )
    ax.axhline(
        thresholds["missing_ratio_critical"],
        color="#e74c3c",
        linestyle="--",
        linewidth=2,
        label=f"CRITICAL ({thresholds['missing_ratio_critical']:.1f}%)",
    )

    # 레이블 및 제목
    ax.set_xlabel("지역", fontsize=12, fontweight="bold")
    ax.set_ylabel("결측 비율 (%)", fontsize=12, fontweight="bold")
    ax.set_title("압력 데이터 결측 비율 비교 (전체 지역)", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    # 값 표시
    for bar, ratio in zip(bars, missing_ratios):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{ratio:.2f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(output_dir / "missing_ratio_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()


def plot_missing_timeline(
    df: pd.DataFrame, area_name: str, output_dir: Path, gaps: List[Dict]
) -> None:
    """
    결측 시점을 타임라인으로 시각화 (결측 유형별 색상 구분)

    Args:
        df: 압력 데이터 DataFrame (missing_type 컬럼 포함)
        area_name: 지역명
        output_dir: 출력 디렉토리
        gaps: 연속 결측 구간 리스트
    """
    fig, ax = setup_plot_style(figsize=(14, 6), dpi=100)

    # 압력값 시계열 플롯
    ax.plot(
        df["msrmt_dt"],
        df["wtrprsr"],
        color="#3498db",
        linewidth=0.5,
        label="압력 데이터",
    )

    # 결측 유형별 구간 구분
    # NaN 결측과 Time Gap 결측 구간을 각각 그룹화
    missing_mask = df['wtrprsr'].isna()
    groups = missing_mask.ne(missing_mask.shift()).cumsum()

    nan_gaps_drawn = False
    time_gap_drawn = False

    for group_id, group in df[missing_mask].groupby(groups[missing_mask]):
        if len(group) >= 3:  # 최소 3개 이상
            start_time = group['msrmt_dt'].iloc[0]
            end_time = group['msrmt_dt'].iloc[-1]

            # 결측 유형 확인 (그룹 내 첫 번째 값 기준)
            missing_type = group['missing_type'].iloc[0]

            if missing_type == 'nan':
                # NaN 결측: 빨간색
                ax.axvspan(
                    start_time,
                    end_time,
                    color="#e74c3c",
                    alpha=0.4,
                    label="NaN 결측 (날짜는 있음)" if not nan_gaps_drawn else "",
                )
                nan_gaps_drawn = True
            elif missing_type == 'time_gap':
                # Time Gap 결측: 주황색
                ax.axvspan(
                    start_time,
                    end_time,
                    color="#ff8c00",
                    alpha=0.4,
                    label="Time Gap 결측 (날짜 없음)" if not time_gap_drawn else "",
                )
                time_gap_drawn = True

    # 레이블 및 제목
    ax.set_xlabel("날짜", fontsize=12, fontweight="bold")
    ax.set_ylabel("압력 (MPa)", fontsize=12, fontweight="bold")
    ax.set_title(f"{area_name} 지역 압력 데이터 결측 타임라인", fontsize=14, fontweight="bold")

    # 범례 (중복 제거)
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=10)

    # Y축 범위 고정 (0-5)
    ax.set_ylim(0, 5.0)

    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / f"missing_timeline_{area_name}.png", dpi=300, bbox_inches="tight")
    plt.close()


def plot_interval_distribution(results: Dict, output_dir: Path) -> None:
    """
    시간 간격 분포 히스토그램

    Args:
        results: 전체 결과
        output_dir: 출력 디렉토리
    """
    # 모든 지역의 간격 분포 통합
    all_intervals = {}
    for area, result in results.items():
        dist = result["intervals"]["interval_distribution"]
        for interval, count in dist.items():
            all_intervals[interval] = all_intervals.get(interval, 0) + count

    # 상위 20개 간격만 표시
    sorted_intervals = sorted(all_intervals.items(), key=lambda x: x[1], reverse=True)[:20]
    intervals, counts = zip(*sorted_intervals) if sorted_intervals else ([], [])

    # Figure 생성
    fig, ax = setup_plot_style(figsize=(12, 6), dpi=100)

    # 색상 결정 (300초만 초록색)
    colors = ["#27ae60" if int(i) == 300 else "#95a5a6" for i in intervals]

    # 막대 그래프
    ax.bar(range(len(intervals)), counts, color=colors, alpha=0.8, edgecolor="black")
    ax.set_xticks(range(len(intervals)))
    ax.set_xticklabels([f"{int(i)}s" for i in intervals], rotation=45, ha="right")

    # 로그 스케일
    ax.set_yscale("log")

    # 레이블 및 제목
    ax.set_xlabel("시간 간격 (초)", fontsize=12, fontweight="bold")
    ax.set_ylabel("빈도수 (로그 스케일)", fontsize=12, fontweight="bold")
    ax.set_title("압력 데이터 시간 간격 분포", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "time_interval_distribution.png", dpi=300, bbox_inches="tight")
    plt.close()


# =============================================================================
# Markdown 보고서 생성 함수
# =============================================================================


def generate_markdown_report(
    results: Dict,
    warnings: List[str],
    thresholds: Dict,
    output_dir: Path,
) -> None:
    """
    Markdown 통합 보고서 생성

    Args:
        results: 전체 결과
        warnings: 경고 메시지 리스트
        thresholds: 임계값
        output_dir: 출력 디렉토리
    """
    report_path = output_dir / "data_quality_report.md"

    with report_path.open("w", encoding="utf-8") as f:
        # 헤더
        f.write("# 압력 데이터 품질 검사 보고서\n\n")
        f.write(f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # 1. Executive Summary
        f.write("## 1. Executive Summary\n\n")
        f.write("### 분석 개요\n")
        f.write(f"- **분석 지역 수**: {len(results)}개\n")
        f.write(f"- **임계값 설정**:\n")
        f.write(f"  - 결측 비율 WARNING: {thresholds['missing_ratio_warning']:.1f}%\n")
        f.write(f"  - 결측 비율 CRITICAL: {thresholds['missing_ratio_critical']:.1f}%\n")
        f.write(f"  - 연속 결측 WARNING: {thresholds['consecutive_hours_warning']}시간\n")
        f.write(f"  - 연속 결측 CRITICAL: {thresholds['consecutive_days_critical']}일\n\n")

        f.write("### 주요 발견사항\n")
        if warnings:
            for warning in warnings:
                f.write(f"- {warning}\n")
        else:
            f.write("- ✅ 모든 지역 데이터 품질 양호 (임계값 미달)\n")
        f.write("\n---\n\n")

        # 2. 결측치 분석 결과
        f.write("## 2. 결측치 분석 결과\n\n")
        f.write("### 결측 데이터 정의\n")
        f.write("- **NaN 결측**: 원본 CSV에 행은 있지만 압력값(wtrprsr)이 NaN인 경우\n")
        f.write("- **Time Gap 결측**: 5분 간격이 빠진 시간대 (행 자체가 없음)\n")
        f.write("- **총 결측**: NaN 결측 + Time Gap 결측\n\n")

        f.write("### 지역별 결측 통계\n\n")
        f.write("| 지역 | 원본 레코드 | 예상 레코드 | NaN 결측 | Time Gap 결측 | 총 결측 | 결측 비율 | 최대 연속 결측 |\n")
        f.write("|------|-------------|-------------|----------|---------------|---------|-----------|----------------|\n")

        for area, result in sorted(results.items()):
            missing = result["missing"]
            max_gap = missing["max_gap_duration"]
            max_gap_str = f"{max_gap:.1f}시간" if max_gap > 0 else "-"

            f.write(
                f"| {area} | {missing['original_records']:,} | {missing['expected_records']:,} | "
                f"{missing['nan_count']:,} | {missing['time_gap_missing']:,} | "
                f"{missing['total_missing']:,} | {missing['missing_ratio']:.3f}% | {max_gap_str} |\n"
            )

        f.write("\n### 연속 결측 구간 상세\n\n")
        for area, result in sorted(results.items()):
            gaps = result["missing"]["consecutive_gaps"]
            if gaps:
                f.write(f"**{area} 지역** ({len(gaps)}개 구간):\n")
                for i, gap in enumerate(gaps[:5], 1):  # 상위 5개만
                    f.write(
                        f"{i}. {gap['start_time'].strftime('%Y-%m-%d %H:%M')} ~ "
                        f"{gap['end_time'].strftime('%Y-%m-%d %H:%M')} "
                        f"({gap['duration_hours']:.1f}시간, {gap['missing_count']}개)\n"
                    )
                if len(gaps) > 5:
                    f.write(f"   ... 외 {len(gaps) - 5}개 구간\n")
                f.write("\n")

        f.write("---\n\n")

        # 3. 시간 간격 검증 결과
        f.write("## 3. 시간 간격 검증 결과\n\n")
        f.write("| 지역 | 중복 타임스탬프 | 시간 순서 역전 | 불규칙 간격 |\n")
        f.write("|------|-----------------|----------------|-------------|\n")

        for area, result in sorted(results.items()):
            intervals = result["intervals"]
            out_of_order_str = "❌ Yes" if intervals["out_of_order"] else "✅ No"

            f.write(
                f"| {area} | {intervals['duplicate_timestamps']} | {out_of_order_str} | "
                f"{intervals['irregular_count']:,} |\n"
            )

        f.write("\n---\n\n")

        # 4. 경고 및 권장사항
        f.write("## 4. 경고 및 권장사항\n\n")
        f.write("### 경고 메시지\n")
        if warnings:
            for warning in warnings:
                f.write(f"- {warning}\n")
        else:
            f.write("- ✅ 경고 없음\n")

        f.write("\n### 지역별 권장 조치사항\n\n")
        for area, result in sorted(results.items()):
            recommendations = generate_recommendations(result, thresholds)
            f.write(f"**{area} 지역**:\n")
            for rec in recommendations:
                f.write(f"- {rec}\n")
            f.write("\n")

        f.write("---\n\n")

        # 5. 첨부 차트
        f.write("## 5. 첨부 차트\n\n")
        f.write("### 결측 비율 비교\n")
        f.write("![결측 비율 비교](figures/missing_ratio_comparison.png)\n\n")

        # 전체 지역 타임라인
        f.write("### 결측 타임라인 (전체 지역)\n\n")
        for area, result in sorted(results.items()):
            f.write(f"**{area} 지역**:\n")
            f.write(f"![{area} 타임라인](figures/missing_timeline_{area}.png)\n\n")

        f.write("### 시간 간격 분포\n")
        f.write("![시간 간격 분포](figures/time_interval_distribution.png)\n\n")

        f.write("---\n\n")
        f.write("**보고서 종료**\n")


# =============================================================================
# Main 함수
# =============================================================================


@log_execution_time
def main(
    output_dir: Optional[Path] = None,
    thresholds: Optional[Dict] = None,
) -> None:
    """
    main40 압력 데이터 품질 검사 메인 함수

    Args:
        output_dir: 출력 디렉토리 (None이면 기본값 사용)
        thresholds: 임계값 (None이면 DEFAULT_THRESHOLDS 사용)
    """
    # 1. 설정 초기화
    config = get_config()

    if output_dir is None:
        output_dir = config.RESULTS_DIR / "main40_data_quality"

    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    ensure_directory_exists(output_dir)
    figures_dir = ensure_directory_exists(output_dir / "figures")

    # 2. 로깅 설정
    logger = setup_logging(
        log_level="INFO",
        log_file=output_dir / "main40.log",
        add_timestamp=True,
    )
    logger.info("=== main40_analyze_pressure_gaps 시작 ===")
    logger.info(f"출력 디렉토리: {output_dir}")
    logger.info(f"임계값: {thresholds}")

    # 3. 한글 폰트 설정
    font_name = setup_korean_font()
    if font_name:
        logger.info(f"✓ 한글 폰트 설정 완료: {font_name}")
    else:
        logger.warning("! 한글 폰트를 찾을 수 없습니다. 영문 레이블을 사용합니다.")

    # 4. 압력 데이터 파일 검증
    pressure_files = config.PRESSURE_DATA_FILES
    valid_files = [f for f in pressure_files if validate_file_exists(f, raise_error=False)]
    logger.info(f"유효한 압력 데이터 파일: {len(valid_files)}/{len(pressure_files)}")

    if len(valid_files) == 0:
        logger.error("❌ 유효한 압력 데이터 파일이 없습니다.")
        return

    # 5. 데이터 로드 및 분석
    results = {}
    progress = ProgressLogger(total=len(valid_files), desc="압력 데이터 분석")

    for file_path in valid_files:
        area_name = extract_area_name(file_path)
        logger.info(f"처리 중: {area_name} ({file_path.name})")

        try:
            # 데이터 로드
            df = load_pressure_data(file_path, encoding=config.encoding)

            # 결측치 분석
            missing_result = detect_missing_values(df, area_name)

            # 시간 간격 검증
            interval_result = validate_time_intervals(df)

            # 결과 저장
            results[area_name] = {
                "missing": missing_result,
                "intervals": interval_result,
                "df": df,  # 타임라인 생성용
            }

            logger.info(
                f"  - 원본 레코드: {missing_result['original_records']:,}, "
                f"예상 레코드: {missing_result['expected_records']:,}"
            )
            logger.info(
                f"  - NaN 결측: {missing_result['nan_count']:,}, "
                f"Time Gap 결측: {missing_result['time_gap_missing']:,}, "
                f"총 결측: {missing_result['total_missing']:,} ({missing_result['missing_ratio']:.3f}%)"
            )
            logger.info(
                f"  - 불규칙 간격: {interval_result['irregular_count']:,}개"
            )

        except Exception as e:
            logger.error(f"❌ {area_name} 처리 중 오류: {e}")

        progress.update(1)

    progress.finish()

    # 6. 경고 생성
    logger.info("경고 메시지 생성 중...")
    warnings = generate_warnings(results, thresholds)

    for warning in warnings:
        logger.warning(warning)

    if not warnings:
        logger.info("✅ 모든 지역 데이터 품질 양호 (임계값 미달)")

    # 7. 시각화 생성
    logger.info("시각화 생성 중...")

    # 7.1 결측 비율 비교 그래프
    plot_missing_comparison(results, figures_dir, thresholds)
    logger.info("  ✓ 결측 비율 비교 그래프 생성 완료")

    # 7.2 전체 지역 타임라인 (결측 여부 무관)
    for area, result in results.items():
        # 완전한 시계열 데이터 사용 (Time Gap 결측 포함)
        df_full = result["missing"]["df_full"]
        plot_missing_timeline(
            df_full, area, figures_dir, result["missing"]["consecutive_gaps"]
        )
        logger.info(f"  ✓ {area} 타임라인 생성 완료")

    # 7.3 시간 간격 분포
    plot_interval_distribution(results, figures_dir)
    logger.info("  ✓ 시간 간격 분포 생성 완료")

    # 8. Markdown 보고서 생성
    logger.info("Markdown 보고서 생성 중...")
    generate_markdown_report(results, warnings, thresholds, output_dir)
    logger.info(f"  ✓ 보고서 생성 완료: {output_dir / 'data_quality_report.md'}")

    # 9. 완료
    logger.info("=== main40 완료 ===")
    logger.info(f"결과 디렉토리: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="압력 데이터 품질 검사 스크립트")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="결과 저장 디렉토리 (기본값: results/main40_data_quality/)",
    )
    parser.add_argument(
        "--missing-warning",
        type=float,
        default=DEFAULT_THRESHOLDS["missing_ratio_warning"],
        help=f"결측 비율 WARNING 임계값 (기본값: {DEFAULT_THRESHOLDS['missing_ratio_warning']}%%)",
    )
    parser.add_argument(
        "--missing-critical",
        type=float,
        default=DEFAULT_THRESHOLDS["missing_ratio_critical"],
        help=f"결측 비율 CRITICAL 임계값 (기본값: {DEFAULT_THRESHOLDS['missing_ratio_critical']}%%)",
    )
    parser.add_argument(
        "--gap-hours-warning",
        type=float,
        default=DEFAULT_THRESHOLDS["consecutive_hours_warning"],
        help=f"연속 결측 WARNING 임계값 (시간, 기본값: {DEFAULT_THRESHOLDS['consecutive_hours_warning']})",
    )
    parser.add_argument(
        "--gap-days-critical",
        type=float,
        default=DEFAULT_THRESHOLDS["consecutive_days_critical"],
        help=f"연속 결측 CRITICAL 임계값 (일, 기본값: {DEFAULT_THRESHOLDS['consecutive_days_critical']})",
    )

    args = parser.parse_args()

    # 임계값 설정
    custom_thresholds = {
        "missing_ratio_warning": args.missing_warning,
        "missing_ratio_critical": args.missing_critical,
        "consecutive_hours_warning": args.gap_hours_warning,
        "consecutive_days_critical": args.gap_days_critical,
    }

    main(output_dir=args.output_dir, thresholds=custom_thresholds)
