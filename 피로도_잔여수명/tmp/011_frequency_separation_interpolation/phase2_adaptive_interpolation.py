#!/usr/bin/env python3
"""
Phase 2: 적응적 주파수 분리 기반 Gap 보간

Phase 1 분석 결과에 기반하여:
- 저주파: 예측 가능성에 따라 Spline/Linear/Mean
- 고주파: 예측 가능성에 따라 Periodic/SARIMA/Mean/Zero
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import timedelta

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

# 009 utils 추가
utils_dir = Path(__file__).parent.parent / "009_prophet_poc" / "utils"
sys.path.insert(0, str(utils_dir))

# Imports
from pass_filter import pass_filter, VALLEY_FREQ, VALLEY_PERIOD
import data_loader
import evaluation
import visualization


def cubic_spline_interpolation(before_value: float, after_value: float, n_points: int) -> np.ndarray:
    """
    Cubic spline 보간

    Args:
        before_value: Gap 직전 값
        after_value: Gap 직후 값
        n_points: Gap 길이

    Returns:
        보간된 값들
    """
    x = [0, n_points - 1]
    y = [before_value, after_value]

    cs = CubicSpline(x, y, bc_type='natural')
    x_new = np.arange(n_points)

    return cs(x_new)


def linear_interpolation(before_value: float, after_value: float, n_points: int) -> np.ndarray:
    """
    선형 보간
    """
    return np.linspace(before_value, after_value, n_points)


def mean_interpolation(before_value: float, after_value: float, n_points: int) -> np.ndarray:
    """
    평균값 보간
    """
    mean_value = (before_value + after_value) / 2
    return np.full(n_points, mean_value)


def zero_fill(n_points: int) -> np.ndarray:
    """
    Zero-fill (고주파 성분 제거)
    """
    return np.zeros(n_points)


def mean_high_freq(high_before: np.ndarray, high_after: np.ndarray, n_points: int) -> np.ndarray:
    """
    고주파 평균값 보간
    """
    # 전후 각 1일(288 records) 평균
    window_size = min(288, len(high_before), len(high_after))
    mean_value = (np.mean(high_before[-window_size:]) + np.mean(high_after[:window_size])) / 2
    return np.full(n_points, mean_value)


def select_interpolation_methods(low_score: float, high_score: float) -> dict:
    """
    예측 가능성 점수에 따라 보간 방법 선택

    Args:
        low_score: 저주파 예측 가능성 점수
        high_score: 고주파 예측 가능성 점수

    Returns:
        {'low': method_name, 'high': method_name}
    """
    methods = {}

    # 저주파 방법
    if low_score > 30:
        methods['low'] = 'spline'
    elif low_score > 15:
        methods['low'] = 'linear'
    else:
        methods['low'] = 'mean'

    # 고주파 방법
    if high_score > 30:
        methods['high'] = 'mean'  # SARIMA/Periodic는 복잡하므로 일단 mean
    elif high_score > 15:
        methods['high'] = 'mean'
    else:
        methods['high'] = 'zero'

    return methods


def adaptive_freq_separation_interpolation(df: pd.DataFrame,
                                           gap_start: str,
                                           gap_end: str,
                                           predictability_scores: dict,
                                           area: str = '0243') -> dict:
    """
    주파수 분리 기반 적응적 보간

    Args:
        df: 전체 압력 데이터
        gap_start: Gap 시작 시간
        gap_end: Gap 종료 시간
        predictability_scores: Phase 1 분석 결과
        area: 지역 코드

    Returns:
        dict with interpolated data and metrics
    """
    print(f"\n=== Adaptive Frequency Separation Interpolation ===")
    print(f"Gap: {gap_start} ~ {gap_end}")

    # 1. 보간 방법 선택
    low_score = predictability_scores['low_pass']['score']
    high_score = predictability_scores['high_pass']['score']

    methods = select_interpolation_methods(low_score, high_score)

    print(f"\nSelected methods (based on Phase 1 scores):")
    print(f"  Low Pass (score={low_score:.1f}): {methods['low']}")
    print(f"  High Pass (score={high_score:.1f}): {methods['high']}")

    # 2. Gap 생성
    df_train, df_gap_true, gap_mask = data_loader.create_artificial_gap(
        df, gap_start, gap_end
    )

    gap_indices = np.where(gap_mask)[0]
    n_gap_points = len(gap_indices)

    print(f"\nGap info:")
    print(f"  Gap length: {n_gap_points} points")
    print(f"  Gap duration: {(pd.to_datetime(gap_end) - pd.to_datetime(gap_start)).days} days")

    # 3. Gap 전후 데이터 추출 (필터 적용 위해 충분한 길이 필요)
    gap_start_idx = gap_indices[0]
    gap_end_idx = gap_indices[-1]

    # 전후 각 4096 points (FFT window 크기)
    before_start_idx = max(0, gap_start_idx - 4096)
    before_data = df['wtrprsr'].iloc[before_start_idx:gap_start_idx].values

    after_end_idx = min(len(df), gap_end_idx + 4096)
    after_data = df['wtrprsr'].iloc[gap_end_idx + 1:after_end_idx].values

    print(f"\nBefore gap data: {len(before_data)} points")
    print(f"After gap data: {len(after_data)} points")

    # 4. 컴포넌트 분리 (전후 데이터)
    print(f"\nSeparating components (V-valley={VALLEY_PERIOD:.1f} min)...")
    sampling_rate = 1 / 300  # 5분 간격

    low_before, high_before = pass_filter(before_data, sampling_rate, "temp_before")
    low_after, high_after = pass_filter(after_data, sampling_rate, "temp_after")

    # 5. 저주파 보간
    print(f"\nInterpolating Low Pass with '{methods['low']}'...")
    low_methods_dict = {
        'spline': lambda: cubic_spline_interpolation(low_before[-1], low_after[0], n_gap_points),
        'linear': lambda: linear_interpolation(low_before[-1], low_after[0], n_gap_points),
        'mean': lambda: mean_interpolation(low_before[-1], low_after[0], n_gap_points)
    }
    low_interpolated = low_methods_dict[methods['low']]()

    # 6. 고주파 보간
    print(f"Interpolating High Pass with '{methods['high']}'...")
    high_methods_dict = {
        'mean': lambda: mean_high_freq(high_before, high_after, n_gap_points),
        'zero': lambda: zero_fill(n_gap_points)
    }
    high_interpolated = high_methods_dict[methods['high']]()

    # 7. 재조합
    gap_interpolated = low_interpolated + high_interpolated

    print(f"\nInterpolation completed:")
    print(f"  Low Pass std: {np.std(low_interpolated):.4f}")
    print(f"  High Pass std: {np.std(high_interpolated):.4f}")
    print(f"  Combined std: {np.std(gap_interpolated):.4f}")

    # 8. 에너지 보존 검증
    original_gap_values = df_gap_true['wtrprsr'].values
    orig_var = np.var(original_gap_values)
    low_var = np.var(low_interpolated)
    high_var = np.var(high_interpolated)
    combined_var = np.var(gap_interpolated)

    # 에너지 보존율 (재조합된 신호 분산 / 원본 분산)
    conservation_rate = (combined_var / orig_var * 100) if orig_var > 0 else 0

    print(f"\nEnergy conservation:")
    print(f"  Original variance: {orig_var:.6f}")
    print(f"  Combined variance: {combined_var:.6f}")
    print(f"  Conservation rate: {conservation_rate:.1f}%")

    if not (50 <= conservation_rate <= 150):
        print(f"  ⚠️ Warning: Conservation rate outside 50-150% range!")

    # 9. 평가
    print(f"\nEvaluating performance...")
    y_true = original_gap_values
    y_pred = gap_interpolated

    metrics = evaluation.calculate_metrics(y_true, y_pred)
    grade = evaluation.grade_performance(metrics)

    print(f"\n{'='*60}")
    print(f"Performance Metrics:")
    print(f"{'='*60}")
    print(f"  R²:    {metrics['r2']:.4f}")
    print(f"  MAE:   {metrics['mae']:.4f}")
    print(f"  RMSE:  {metrics['rmse']:.4f}")
    print(f"  MAPE:  {metrics['mape']:.2f}%")
    print(f"  Grade: {grade}")
    print(f"{'='*60}")

    return {
        'gap_start': gap_start,
        'gap_end': gap_end,
        'gap_days': (pd.to_datetime(gap_end) - pd.to_datetime(gap_start)).days,
        'n_points': n_gap_points,
        'methods': methods,
        'predictability_scores': {
            'low': low_score,
            'high': high_score
        },
        'interpolated': {
            'low': low_interpolated,
            'high': high_interpolated,
            'combined': gap_interpolated
        },
        'true_values': y_true,
        'timestamps': df_gap_true['msrmt_dt'].values,
        'metrics': metrics,
        'grade': grade,
        'conservation_rate': conservation_rate
    }


def generate_comparison_plots(results: dict, output_dir: Path):
    """
    비교 시각화 생성
    """
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    timestamps = pd.to_datetime(results['timestamps'])
    y_true = results['true_values']
    y_pred = results['interpolated']['combined']
    low_comp = results['interpolated']['low']
    high_comp = results['interpolated']['high']

    # 1. 예측 vs 실제
    axes[0].plot(timestamps, y_true, 'k-', linewidth=1, alpha=0.7, label='True')
    axes[0].plot(timestamps, y_pred, 'r--', linewidth=1.5, label='Predicted')
    axes[0].set_ylabel('Pressure (MPa)')
    axes[0].set_title(f'Forecast vs True (R²={results["metrics"]["r2"]:.4f})')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # 2. 저주파 컴포넌트
    # 저주파의 true 값 구하기 (원본 gap 데이터를 필터링)
    sampling_rate = 1 / 300
    true_low, _ = pass_filter(y_true, sampling_rate, "temp_true")

    axes[1].plot(timestamps, true_low, 'k-', linewidth=1, alpha=0.7, label='True Low')
    axes[1].plot(timestamps, low_comp, 'b--', linewidth=1.5, label=f'Predicted Low ({results["methods"]["low"]})')
    axes[1].set_ylabel('Pressure (MPa)')
    axes[1].set_title(f'Low Pass Component (≥{VALLEY_PERIOD:.0f} min)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # 3. 고주파 컴포넌트
    _, true_high = pass_filter(y_true, sampling_rate, "temp_true")

    axes[2].plot(timestamps, true_high, 'k-', linewidth=0.5, alpha=0.7, label='True High')
    axes[2].plot(timestamps, high_comp, 'r--', linewidth=1, label=f'Predicted High ({results["methods"]["high"]})')
    axes[2].set_ylabel('Pressure (MPa)')
    axes[2].set_title(f'High Pass Component (<{VALLEY_PERIOD:.0f} min)')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    # 4. 잔차
    residuals = y_true - y_pred
    axes[3].plot(timestamps, residuals, 'g-', linewidth=0.5)
    axes[3].axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    axes[3].fill_between(timestamps, 0, residuals, alpha=0.3)
    axes[3].set_ylabel('Residual (MPa)')
    axes[3].set_xlabel('Time')
    axes[3].set_title(f'Residuals (MAE={results["metrics"]["mae"]:.4f})')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()

    plot_path = output_dir / 'forecast_comparison.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to {plot_path}")
    plt.close()


def generate_report(results: dict, output_dir: Path):
    """
    보간 결과 보고서 생성
    """
    report_path = output_dir / 'interpolation_report.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 주파수 분리 기반 Gap 보간 결과\n\n")
        f.write(f"**Gap 기간**: {results['gap_start']} ~ {results['gap_end']}\n")
        f.write(f"**Gap 길이**: {results['gap_days']}일 ({results['n_points']} records)\n")
        f.write(f"**V-valley 기준**: {VALLEY_PERIOD:.1f}분\n")
        f.write(f"**분석 일시**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("---\n\n")
        f.write("## 📊 보간 전략\n\n")
        f.write("### Phase 1 예측 가능성 점수\n\n")
        f.write(f"- **Low Pass**: {results['predictability_scores']['low']:.2f}/100\n")
        f.write(f"- **High Pass**: {results['predictability_scores']['high']:.2f}/100\n\n")

        f.write("### 선택된 보간 방법\n\n")
        f.write(f"- **Low Pass**: {results['methods']['low']}\n")
        f.write(f"- **High Pass**: {results['methods']['high']}\n\n")

        f.write("---\n\n")
        f.write("## 📈 성능 결과\n\n")

        metrics = results['metrics']
        f.write("| 지표 | 값 | 평가 |\n")
        f.write("|------|-----|------|\n")
        f.write(f"| **R²** | **{metrics['r2']:.4f}** | ")
        if metrics['r2'] > 0.3:
            f.write("✅ 우수\n")
        elif metrics['r2'] > 0:
            f.write("⚠️ 양호\n")
        else:
            f.write("❌ 실패\n")

        f.write(f"| MAE | {metrics['mae']:.4f} | ")
        f.write("✅ 우수\n" if metrics['mae'] < 0.10 else "⚠️ 보통\n")

        f.write(f"| RMSE | {metrics['rmse']:.4f} | ")
        f.write("✅ 우수\n" if metrics['rmse'] < 0.15 else "⚠️ 보통\n")

        f.write(f"| MAPE | {metrics['mape']:.2f}% | ")
        f.write("✅ 우수\n" if metrics['mape'] < 7 else "⚠️ 보통\n")

        f.write(f"| **종합 등급** | **{results['grade']}** | |\n\n")

        f.write("---\n\n")
        f.write("## 🔍 컴포넌트 분석\n\n")

        low_std = np.std(results['interpolated']['low'])
        high_std = np.std(results['interpolated']['high'])
        combined_std = np.std(results['interpolated']['combined'])

        f.write("### 표준편차\n\n")
        f.write(f"- Low Pass: {low_std:.4f}\n")
        f.write(f"- High Pass: {high_std:.4f}\n")
        f.write(f"- Combined: {combined_std:.4f}\n\n")

        f.write("### 에너지 보존\n\n")
        f.write(f"- Conservation rate: {results['conservation_rate']:.1f}%\n")
        if 95 <= results['conservation_rate'] <= 105:
            f.write("- 판정: ✅ 정상 (95-105%)\n\n")
        elif 50 <= results['conservation_rate'] <= 150:
            f.write("- 판정: ⚠️ 주의 (50-150%)\n\n")
        else:
            f.write("- 판정: ❌ 비정상\n\n")

        f.write("---\n\n")
        f.write("## 💡 결론\n\n")

        if metrics['r2'] > 0.3:
            f.write("✅ **성공**: 주파수 분리 기반 보간이 효과적\n\n")
            f.write("- R² > 0.3 달성\n")
            f.write("- 기존 방법(XGBoost, Prophet, Linear) 대비 대폭 개선\n")
            f.write("- 저주파 트렌드 보존 및 고주파 노이즈 제거 성공\n")
        elif metrics['r2'] > 0:
            f.write("⚠️ **부분 성공**: 개선 효과 있으나 제한적\n\n")
            f.write("- R² > 0 달성 (기존 방법 대비 개선)\n")
            f.write("- 실용적 수준에는 미달\n")
            f.write("- 추가 최적화 필요\n")
        else:
            f.write("❌ **실패**: 주파수 분리로도 보간 불가\n\n")
            f.write("- R² < 0\n")
            f.write("- Gap 길이가 너무 길거나 데이터 특성의 근본적 한계\n")
            f.write("- 대안: Gap 허용 또는 Linear interpolation (경고 포함)\n")

    print(f"Report saved to {report_path}")


def run_gap_interpolation_test(area: str,
                               gap_days: int,
                               predictability_path: Path,
                               output_dir: Path):
    """
    Gap 보간 테스트 실행
    """
    print(f"\n{'='*70}")
    print(f"Gap Interpolation Test: {area}, {gap_days} days")
    print(f"{'='*70}")

    # 1. Phase 1 결과 로드
    with open(predictability_path, 'r', encoding='utf-8') as f:
        predictability_scores = json.load(f)

    print(f"\nLoaded Phase 1 results:")
    print(f"  Low Pass score: {predictability_scores['low_pass']['score']:.2f}/100")
    print(f"  High Pass score: {predictability_scores['high_pass']['score']:.2f}/100")

    # 2. 데이터 로드
    df = data_loader.load_pressure_data(area)

    # 3. Gap 설정
    gap_configs = {
        3: {"start": "2025-05-19 13:40", "end": "2025-05-22 13:40"},
        7: {"start": "2025-05-19 13:40", "end": "2025-05-26 13:40"},
        14: {"start": "2025-05-19 13:40", "end": "2025-06-02 13:40"},
        24: {"start": "2025-05-19 13:40", "end": "2025-06-12 14:40"}
    }

    if gap_days not in gap_configs:
        raise ValueError(f"Invalid gap_days: {gap_days}. Must be one of {list(gap_configs.keys())}")

    gap_config = gap_configs[gap_days]

    # 4. 보간 실행
    results = adaptive_freq_separation_interpolation(
        df=df,
        gap_start=gap_config['start'],
        gap_end=gap_config['end'],
        predictability_scores=predictability_scores,
        area=area
    )

    # 5. 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 6. 시각화 생성
    generate_comparison_plots(results, output_dir)

    # 7. 보고서 생성
    generate_report(results, output_dir)

    # 8. 결과 저장 (JSON)
    results_json = {
        'gap_start': results['gap_start'],
        'gap_end': results['gap_end'],
        'gap_days': results['gap_days'],
        'n_points': results['n_points'],
        'methods': results['methods'],
        'predictability_scores': results['predictability_scores'],
        'metrics': results['metrics'],
        'grade': results['grade'],
        'conservation_rate': results['conservation_rate']
    }

    json_path = output_dir / 'results.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False)

    print(f"\nResults JSON saved to {json_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Phase 2: Adaptive Gap Interpolation')
    parser.add_argument('--area', type=str, default='0243',
                       help='Area code (default: 0243)')
    parser.add_argument('--gap-days', type=int, required=True,
                       choices=[3, 7, 14, 24],
                       help='Gap length in days (3, 7, 14, or 24)')
    parser.add_argument('--predictability', type=str,
                       default='results/component_analysis/predictability_scores.json',
                       help='Path to Phase 1 predictability scores JSON')
    parser.add_argument('--output', type=str,
                       help='Output directory (default: results/interpolation/gap_Xdays/)')

    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    predictability_path = script_dir / args.predictability

    if not predictability_path.exists():
        raise FileNotFoundError(f"Predictability scores not found: {predictability_path}")

    if args.output:
        output_dir = script_dir / args.output
    else:
        output_dir = script_dir / f"results/interpolation/gap_{args.gap_days}days"

    # Run test
    results = run_gap_interpolation_test(
        area=args.area,
        gap_days=args.gap_days,
        predictability_path=predictability_path,
        output_dir=output_dir
    )

    print("\n" + "="*70)
    print(f"Phase 2 ({args.gap_days}일 gap) 완료!")
    print("="*70)
    print(f"\nFinal Result:")
    print(f"  R²: {results['metrics']['r2']:.4f}")
    print(f"  Grade: {results['grade']}")


if __name__ == '__main__':
    main()
