#!/usr/bin/env python3
"""
Phase 1: 주파수 컴포넌트별 예측 가능성 분석

저주파(≥553.5분)/고주파(<553.5분) 각각의:
- ACF (시간 의존성)
- Periodicity (주기성)
- Variation consistency (변동 일관성)
측정 후 예측 가능성 점수 산출
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import timedelta

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
from statsmodels.tsa.stattools import acf

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

# 009 utils 추가
utils_dir = Path(__file__).parent.parent / "009_prophet_poc" / "utils"
sys.path.insert(0, str(utils_dir))

# Imports
from pass_filter import pass_filter, VALLEY_FREQ, VALLEY_PERIOD
import data_loader


def calculate_acf_lag1(data: np.ndarray) -> float:
    """
    ACF (Autocorrelation Function) lag=1 계산

    Args:
        data: 시계열 데이터

    Returns:
        acf_lag1: lag=1에서의 ACF 값 (0-1)
    """
    acf_values = acf(data, nlags=1, fft=True)
    return float(acf_values[1])  # lag=1


def calculate_periodicity(data: np.ndarray, fs: float = 1/300) -> float:
    """
    Periodicity (주기성 강도) 계산

    Args:
        data: 시계열 데이터
        fs: 샘플링 주파수 (Hz, 기본값: 1/300 = 5분 간격)

    Returns:
        periodicity: 주기성 강도 (0-1)
    """
    # Welch PSD
    frequencies, psd = signal.welch(
        data,
        fs=fs,
        nperseg=min(4096, len(data) // 2),
        noverlap=None
    )

    # DC 제거
    psd_no_dc = psd[1:]

    if len(psd_no_dc) == 0:
        return 0.0

    # 피크 탐지
    peaks, properties = signal.find_peaks(
        psd_no_dc,
        prominence=np.max(psd_no_dc) * 0.005,  # 0.5% prominence
        distance=len(psd_no_dc) // 200
    )

    if len(peaks) == 0:
        return 0.0

    # 가장 높은 피크의 prominence / 전체 파워
    max_prominence = np.max(properties['prominences'])
    total_power = np.sum(psd_no_dc)

    periodicity = max_prominence / total_power if total_power > 0 else 0.0

    return float(min(periodicity, 1.0))


def calculate_variation_consistency(data: np.ndarray, window_size: int = 288) -> float:
    """
    Variation Consistency (변동 일관성) 계산

    Args:
        data: 시계열 데이터
        window_size: 윈도우 크기 (기본값: 288 = 1일)

    Returns:
        consistency: 변동 일관성 (0-1)
    """
    if len(data) < window_size * 2:
        return 0.0

    # 슬라이딩 윈도우로 변동 계산
    variations = []
    for i in range(0, len(data) - window_size, window_size // 2):
        window = data[i:i + window_size]
        variation = np.std(window)
        variations.append(variation)

    if len(variations) < 2:
        return 0.0

    variations = np.array(variations)

    # 변동의 일관성: 1 - (변동의 표준편차 / 변동의 평균)
    mean_variation = np.mean(variations)
    std_variation = np.std(variations)

    if mean_variation == 0:
        return 0.0

    consistency = 1 - (std_variation / mean_variation)
    consistency = max(0, min(consistency, 1.0))  # 0-1 범위로 제한

    return float(consistency)


def calculate_predictability_score(acf_val: float,
                                   periodicity: float,
                                   consistency: float) -> dict:
    """
    예측 가능성 점수 계산 (0-100)

    Args:
        acf_val: ACF lag=1 값
        periodicity: 주기성 강도
        consistency: 변동 일관성

    Returns:
        dict with score and breakdown
    """
    # ACF 기여 (0-40점)
    acf_score = min(acf_val * 100, 40)

    # Periodicity 기여 (0-30점)
    period_score = min(periodicity * 100, 30)

    # Consistency 기여 (0-30점)
    consistency_score = consistency * 30

    total_score = acf_score + period_score + consistency_score

    return {
        'score': round(total_score, 2),
        'acf': round(acf_val, 4),
        'acf_contribution': round(acf_score, 2),
        'periodicity': round(periodicity, 4),
        'periodicity_contribution': round(period_score, 2),
        'consistency': round(consistency, 4),
        'consistency_contribution': round(consistency_score, 2)
    }


def analyze_component_predictability(area: str = '0243',
                                     window_days: int = 30,
                                     output_dir: Path = None) -> dict:
    """
    주파수 컴포넌트별 예측 가능성 분석

    Args:
        area: 지역 코드 (예: '0243')
        window_days: 분석 윈도우 (일)
        output_dir: 결과 저장 디렉토리

    Returns:
        분석 결과 dict
    """
    print(f"=== Phase 1: Component Predictability Analysis for {area} ===\n")

    # 1. 데이터 로드
    print("Loading data...")
    df = data_loader.load_pressure_data(area)
    print(f"Loaded {len(df)} records ({df['msrmt_dt'].iloc[0]} ~ {df['msrmt_dt'].iloc[-1]})")

    # 분석 윈도우 추출 (최근 window_days)
    if len(df) > window_days * 288:
        df_window = df.iloc[-window_days * 288:].copy()
    else:
        df_window = df.copy()

    data = df_window['wtrprsr'].values
    print(f"Analysis window: {len(data)} records ({window_days} days)\n")

    # 2. pass_filter로 컴포넌트 분리
    print(f"Separating components (V-valley={VALLEY_PERIOD:.1f} min)...")
    sampling_rate = 1 / 300  # 5분 간격 = 300초
    low_pass, high_pass = pass_filter(data, sampling_rate, "temp")
    print(f"  Low Pass: ≥{VALLEY_PERIOD:.1f} min period")
    print(f"  High Pass: <{VALLEY_PERIOD:.1f} min period\n")

    # 3. 저주파 분석
    print("Analyzing Low Pass component...")
    low_acf = calculate_acf_lag1(low_pass)
    low_periodicity = calculate_periodicity(low_pass)
    low_consistency = calculate_variation_consistency(low_pass)
    low_results = calculate_predictability_score(low_acf, low_periodicity, low_consistency)
    print(f"  ACF (lag=1): {low_acf:.4f}")
    print(f"  Periodicity: {low_periodicity:.4f}")
    print(f"  Consistency: {low_consistency:.4f}")
    print(f"  → Predictability Score: {low_results['score']:.2f}/100\n")

    # 4. 고주파 분석
    print("Analyzing High Pass component...")
    high_acf = calculate_acf_lag1(high_pass)
    high_periodicity = calculate_periodicity(high_pass)
    high_consistency = calculate_variation_consistency(high_pass)
    high_results = calculate_predictability_score(high_acf, high_periodicity, high_consistency)
    print(f"  ACF (lag=1): {high_acf:.4f}")
    print(f"  Periodicity: {high_periodicity:.4f}")
    print(f"  Consistency: {high_consistency:.4f}")
    print(f"  → Predictability Score: {high_results['score']:.2f}/100\n")

    # 5. 비교 및 판정
    score_diff = abs(low_results['score'] - high_results['score'])
    print(f"Score difference: {score_diff:.2f}")

    if score_diff < 5:
        print("  → 분리 효과 미미 (차이 < 5)")
    elif score_diff < 10:
        print("  → 약한 분리 효과 (차이 5-10)")
    else:
        print("  → 명확한 분리 효과 (차이 > 10)")

    # 6. 전략 추천
    print("\n=== Recommended Strategy ===")
    better_component = "Low Pass" if low_results['score'] > high_results['score'] else "High Pass"
    print(f"Better component: {better_component}")

    recommendation = recommend_strategy(low_results['score'], high_results['score'])
    print(f"Low Pass: {recommendation['low']}")
    print(f"High Pass: {recommendation['high']}")

    if low_results['score'] < 15 and high_results['score'] < 15:
        print("\n⚠️ WARNING: 둘 다 점수 < 15 → Phase 2 중단 권장")
        proceed_phase2 = False
    else:
        print("\n✓ Phase 2 진행 가능")
        proceed_phase2 = True

    # 7. 결과 저장
    results = {
        'area': area,
        'analysis_window_days': window_days,
        'n_records': len(data),
        'valley_period_min': VALLEY_PERIOD,
        'low_pass': low_results,
        'high_pass': high_results,
        'score_difference': round(score_diff, 2),
        'better_component': better_component,
        'recommendation': recommendation,
        'proceed_phase2': proceed_phase2
    }

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON 저장
        json_path = output_dir / 'predictability_scores.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {json_path}")

        # 시각화
        plot_component_comparison(
            df_window['msrmt_dt'],
            data,
            low_pass,
            high_pass,
            low_results,
            high_results,
            output_dir
        )

        # 보고서 생성
        generate_report(results, output_dir)

    return results


def recommend_strategy(low_score: float, high_score: float) -> dict:
    """
    예측 가능성 점수에 따른 보간 전략 추천

    Args:
        low_score: 저주파 점수
        high_score: 고주파 점수

    Returns:
        dict with 'low' and 'high' strategies
    """
    strategy = {}

    # 저주파 전략
    if low_score > 30:
        strategy['low'] = 'spline (정밀 보간)'
    elif low_score > 15:
        strategy['low'] = 'linear (단순 보간)'
    else:
        strategy['low'] = 'mean (평균값)'

    # 고주파 전략
    if high_score > 30:
        strategy['high'] = 'periodic/sarima (정밀 보간)'
    elif high_score > 15:
        strategy['high'] = 'mean (평균값)'
    else:
        strategy['high'] = 'zero (제거)'

    return strategy


def plot_component_comparison(timestamps, original, low_pass, high_pass,
                              low_results, high_results, output_dir):
    """
    컴포넌트 비교 시각화
    """
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # 1. 원본 데이터
    axes[0].plot(timestamps, original, 'k-', linewidth=0.5, alpha=0.7)
    axes[0].set_ylabel('Pressure (MPa)')
    axes[0].set_title('Original Data')
    axes[0].grid(True, alpha=0.3)

    # 2. 저주파 컴포넌트
    axes[1].plot(timestamps, low_pass, 'b-', linewidth=0.8)
    axes[1].set_ylabel('Pressure (MPa)')
    axes[1].set_title(f'Low Pass (≥{VALLEY_PERIOD:.0f} min) - Score: {low_results["score"]:.1f}/100')
    axes[1].grid(True, alpha=0.3)
    axes[1].text(0.02, 0.95,
                f"ACF: {low_results['acf']:.3f}\nPeriodicity: {low_results['periodicity']:.3f}\nConsistency: {low_results['consistency']:.3f}",
                transform=axes[1].transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 3. 고주파 컴포넌트
    axes[2].plot(timestamps, high_pass, 'r-', linewidth=0.5, alpha=0.7)
    axes[2].set_ylabel('Pressure (MPa)')
    axes[2].set_title(f'High Pass (<{VALLEY_PERIOD:.0f} min) - Score: {high_results["score"]:.1f}/100')
    axes[2].grid(True, alpha=0.3)
    axes[2].text(0.02, 0.95,
                f"ACF: {high_results['acf']:.3f}\nPeriodicity: {high_results['periodicity']:.3f}\nConsistency: {high_results['consistency']:.3f}",
                transform=axes[2].transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # 4. 재조합 검증
    reconstructed = low_pass + high_pass
    axes[3].plot(timestamps, original, 'k-', linewidth=0.5, alpha=0.7, label='Original')
    axes[3].plot(timestamps, reconstructed, 'g--', linewidth=0.8, label='Reconstructed')
    axes[3].set_ylabel('Pressure (MPa)')
    axes[3].set_xlabel('Time')
    axes[3].set_title('Reconstruction Validation')
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()

    plot_path = output_dir / 'component_comparison.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to {plot_path}")
    plt.close()

    # ACF 비교 플롯
    fig, axes = plt.subplots(3, 1, figsize=(10, 9))

    # Original ACF
    acf_orig = acf(original, nlags=100, fft=True)
    axes[0].stem(acf_orig, linefmt='k-', markerfmt='ko', basefmt='k-')
    axes[0].axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
    axes[0].set_ylabel('ACF')
    axes[0].set_title(f'Original ACF (lag=1: {acf_orig[1]:.3f})')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim([-0.5, 1.0])

    # Low Pass ACF
    acf_low = acf(low_pass, nlags=100, fft=True)
    axes[1].stem(acf_low, linefmt='b-', markerfmt='bo', basefmt='b-')
    axes[1].axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
    axes[1].set_ylabel('ACF')
    axes[1].set_title(f'Low Pass ACF (lag=1: {acf_low[1]:.3f}) - Score: {low_results["score"]:.1f}/100')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim([-0.5, 1.0])

    # High Pass ACF
    acf_high = acf(high_pass, nlags=100, fft=True)
    axes[2].stem(acf_high, linefmt='r-', markerfmt='ro', basefmt='r-')
    axes[2].axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
    axes[2].set_ylabel('ACF')
    axes[2].set_xlabel('Lag')
    axes[2].set_title(f'High Pass ACF (lag=1: {acf_high[1]:.3f}) - Score: {high_results["score"]:.1f}/100')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_ylim([-0.5, 1.0])

    plt.tight_layout()

    acf_plot_path = output_dir / 'component_acf.png'
    plt.savefig(acf_plot_path, dpi=150, bbox_inches='tight')
    print(f"ACF plot saved to {acf_plot_path}")
    plt.close()


def generate_report(results: dict, output_dir: Path):
    """
    Phase 1 분석 보고서 생성
    """
    report_path = output_dir / 'predictability_report.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Phase 1: 컴포넌트 예측 가능성 분석 보고서\n\n")
        f.write(f"**지역**: {results['area']}\n")
        f.write(f"**분석 윈도우**: {results['analysis_window_days']}일 ({results['n_records']} records)\n")
        f.write(f"**V-valley 기준**: {results['valley_period_min']:.1f}분\n")
        f.write(f"**분석 일시**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("---\n\n")
        f.write("## 📊 분석 결과\n\n")

        # 저주파
        f.write("### Low Pass Component (≥{:.0f}분 주기)\n\n".format(results['valley_period_min']))
        low = results['low_pass']
        f.write(f"| 지표 | 값 | 기여도 |\n")
        f.write(f"|------|-----|-------|\n")
        f.write(f"| ACF (lag=1) | {low['acf']:.4f} | {low['acf_contribution']:.1f}/40 |\n")
        f.write(f"| Periodicity | {low['periodicity']:.4f} | {low['periodicity_contribution']:.1f}/30 |\n")
        f.write(f"| Consistency | {low['consistency']:.4f} | {low['consistency_contribution']:.1f}/30 |\n")
        f.write(f"| **예측 가능성 점수** | **{low['score']:.2f}/100** | |\n\n")

        # 고주파
        f.write("### High Pass Component (<{:.0f}분 주기)\n\n".format(results['valley_period_min']))
        high = results['high_pass']
        f.write(f"| 지표 | 값 | 기여도 |\n")
        f.write(f"|------|-----|-------|\n")
        f.write(f"| ACF (lag=1) | {high['acf']:.4f} | {high['acf_contribution']:.1f}/40 |\n")
        f.write(f"| Periodicity | {high['periodicity']:.4f} | {high['periodicity_contribution']:.1f}/30 |\n")
        f.write(f"| Consistency | {high['consistency']:.4f} | {high['consistency_contribution']:.1f}/30 |\n")
        f.write(f"| **예측 가능성 점수** | **{high['score']:.2f}/100** | |\n\n")

        # 비교
        f.write("---\n\n")
        f.write("## 🔍 비교 분석\n\n")
        f.write(f"**점수 차이**: {results['score_difference']:.2f}\n")
        f.write(f"**우세 컴포넌트**: {results['better_component']}\n\n")

        if results['score_difference'] < 5:
            f.write("**판정**: ⚠️ 분리 효과 미미 (차이 < 5)\n\n")
        elif results['score_difference'] < 10:
            f.write("**판정**: ⚠️ 약한 분리 효과 (차이 5-10)\n\n")
        else:
            f.write("**판정**: ✅ 명확한 분리 효과 (차이 > 10)\n\n")

        # 추천 전략
        f.write("---\n\n")
        f.write("## 💡 추천 보간 전략\n\n")
        rec = results['recommendation']
        f.write(f"- **Low Pass**: {rec['low']}\n")
        f.write(f"- **High Pass**: {rec['high']}\n\n")

        # Phase 2 진행 여부
        f.write("---\n\n")
        f.write("## ✅ Phase 2 진행 여부\n\n")
        if results['proceed_phase2']:
            f.write("**판정**: ✓ Phase 2 진행 가능\n\n")
            f.write("최소 하나의 컴포넌트가 점수 ≥ 15\n")
        else:
            f.write("**판정**: ❌ Phase 2 중단 권장\n\n")
            f.write("⚠️ 둘 다 점수 < 15 → 주파수 분리 무의미\n\n")
            f.write("**대안**:\n")
            f.write("- Linear interpolation 사용 (가장 안전)\n")
            f.write("- Gap 허용 (분석 제외)\n")

    print(f"Report saved to {report_path}")


def main():
    parser = argparse.ArgumentParser(description='Phase 1: Component Predictability Analysis')
    parser.add_argument('--area', type=str, default='0243',
                       help='Area code (default: 0243)')
    parser.add_argument('--window-days', type=int, default=30,
                       help='Analysis window in days (default: 30)')
    parser.add_argument('--output', type=str, default='results/component_analysis',
                       help='Output directory (default: results/component_analysis)')

    args = parser.parse_args()

    # Output directory
    script_dir = Path(__file__).parent
    output_dir = script_dir / args.output

    # Run analysis
    results = analyze_component_predictability(
        area=args.area,
        window_days=args.window_days,
        output_dir=output_dir
    )

    print("\n" + "=" * 70)
    print("Phase 1 분석 완료!")
    print("=" * 70)


if __name__ == '__main__':
    main()
