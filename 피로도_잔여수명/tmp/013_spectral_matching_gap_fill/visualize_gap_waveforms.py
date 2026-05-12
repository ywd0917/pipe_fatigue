#!/usr/bin/env python3
"""
결측 구간 파형 분해 시각화 스크립트

목적: "Interaction 58.6%" 결과의 의미를 시각적으로 검증
- 재조합 정확도 확인 (low + high = original)
- True와 Pred의 위상 관계 차이 분석
- Peak 생성 메커니즘 비교
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
from scipy.signal import find_peaks
from pathlib import Path
import json
from typing import Dict, Tuple, List
import sys

# 한글 폰트 설정
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.common.korean_font_utils import setup_korean_font

def load_gap_data(gap_days: int) -> Dict[str, np.ndarray]:
    """Gap 데이터 및 주파수 성분 로드"""
    gap_dir = Path(__file__).parent / "results" / f"gap_{gap_days}days"

    data = {
        'gap_true': np.load(gap_dir / "gap_true.npy"),
        'gap_pred': np.load(gap_dir / "gap_pred.npy"),
        'low_true': np.load(gap_dir / "low_freq_true.npy"),
        'high_true': np.load(gap_dir / "high_freq_true.npy"),
        'low_pred': np.load(gap_dir / "low_freq_pred.npy"),
        'high_pred': np.load(gap_dir / "high_freq_pred.npy")
    }

    print(f"\n=== Gap {gap_days} days 데이터 로드 완료 ===")
    print(f"신호 길이: {len(data['gap_true'])} points")

    return data

def verify_reconstruction(original: np.ndarray, low: np.ndarray, high: np.ndarray) -> float:
    """재조합 정확도 검증

    Returns:
        max_error: 최대 재조합 오차
    """
    reconstructed = low + high
    error = np.abs(original - reconstructed)
    max_error = np.max(error)
    mean_error = np.mean(error)

    print(f"재조합 오차 - 최대: {max_error:.2e}, 평균: {mean_error:.2e}")

    # Assert 대신 경고
    if max_error > 1e-10:
        print(f"⚠️ 경고: 재조합 오차가 예상보다 큼 ({max_error:.2e} > 1e-10)")
    else:
        print("✅ 재조합 정확도 검증 통과 (오차 < 1e-10)")

    return max_error

def analyze_correlation(low: np.ndarray, high: np.ndarray) -> Dict[str, float]:
    """저주파-고주파 상관관계 분석

    Returns:
        dict: Pearson r, p-value, coherent percentage
    """
    # Pearson correlation
    r, p_value = pearsonr(low, high)

    # 같은 방향 움직임 비율
    low_diff = np.diff(low)
    high_diff = np.diff(high)
    same_direction = np.sum((low_diff * high_diff) > 0)
    coherent_pct = same_direction / len(low_diff) * 100

    return {
        'pearson_r': r,
        'p_value': p_value,
        'coherent_pct': coherent_pct
    }

def compare_peaks(original: np.ndarray, low: np.ndarray, high: np.ndarray,
                  prominence: float = 0.01) -> Dict[str, int]:
    """Peak 개수 비교

    Returns:
        dict: 각 신호의 peak 개수
    """
    peaks_original, _ = find_peaks(original, prominence=prominence)
    peaks_low, _ = find_peaks(low, prominence=prominence)
    peaks_high, _ = find_peaks(high, prominence=prominence)
    peaks_combined, _ = find_peaks(low + high, prominence=prominence)

    return {
        'original': len(peaks_original),
        'low': len(peaks_low),
        'high': len(peaks_high),
        'combined': len(peaks_combined)
    }

def analyze_peak_directions(low: np.ndarray, high: np.ndarray) -> Dict[str, float]:
    """Peak 방향 분석 - 저주파와 고주파의 극값 방향 비교

    Returns:
        dict: 같은/반대 방향 비율, 상쇄 비율
    """
    # Find peaks and troughs
    low_peaks, _ = find_peaks(low)
    low_troughs, _ = find_peaks(-low)
    high_peaks, _ = find_peaks(high)
    high_troughs, _ = find_peaks(-high)

    # All extrema
    low_extrema = np.sort(np.concatenate([low_peaks, low_troughs]))
    high_extrema = np.sort(np.concatenate([high_peaks, high_troughs]))

    # Direction at each time point (simplified)
    low_grad = np.gradient(low)
    high_grad = np.gradient(high)

    # Same direction: both up or both down
    same_dir = np.sum((low_grad * high_grad) > 0) / len(low_grad) * 100

    # Cancellation: one large, one small in opposite directions
    cancellation = 0
    for i in range(len(low_grad)):
        if abs(low_grad[i]) > 0.01 and abs(high_grad[i]) > 0.01:
            if low_grad[i] * high_grad[i] < 0:  # Opposite directions
                cancellation += 1
    cancellation_ratio = cancellation / len(low_grad) * 100

    return {
        'same_direction_pct': same_dir,
        'opposite_direction_pct': 100 - same_dir,
        'cancellation_ratio': cancellation_ratio
    }

def plot_waveform_decomposition(gap_days: int, data_type: str, data: Dict[str, np.ndarray],
                                save_dir: Path) -> None:
    """단일 gap의 파형 분해 시각화"""

    # Select data
    if data_type == 'true':
        original = data['gap_true']
        low = data['low_true']
        high = data['high_true']
        title_suffix = "True (실제 신호)"
    else:
        original = data['gap_pred']
        low = data['low_pred']
        high = data['high_pred']
        title_suffix = "Pred (예측 신호)"

    # Verify reconstruction
    max_error = verify_reconstruction(original, low, high)

    # Create figure
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # 1. 전체 구간 파형 Overlay
    ax1 = axes[0]
    ax1.plot(original, 'k-', linewidth=2, alpha=0.8, label='원본')
    ax1.plot(high, 'r-', alpha=0.6, label='고주파')
    ax1.plot(low + high, 'g--', alpha=0.6, label='재조합')
    ax1.plot(low, 'lime', alpha=1.0, label='저주파')  # 마지막에 그려서 가려지지 않게
    ax1.set_title(f'Gap {gap_days} days - {title_suffix} - 파형 분해')
    ax1.set_xlabel('Time (minutes)')
    ax1.set_ylabel('Pressure')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 확대 구간 (처음 500 points)
    ax2 = axes[1]
    zoom_end = min(500, len(original))
    ax2.plot(original[:zoom_end], 'k-', linewidth=2, alpha=0.8, label='원본')
    ax2.plot(high[:zoom_end], 'r-', alpha=0.6, label='고주파')
    ax2.plot((low + high)[:zoom_end], 'g--', alpha=0.6, label='재조합')
    ax2.plot(low[:zoom_end], 'lime', alpha=1.0, label='저주파')  # 마지막에 그려서 가려지지 않게
    ax2.set_title(f'확대 구간 (처음 {zoom_end} points)')
    ax2.set_xlabel('Time (minutes)')
    ax2.set_ylabel('Pressure')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 재조합 오차
    ax3 = axes[2]
    error = np.abs(original - (low + high))
    ax3.plot(error, 'r-', alpha=0.7)
    ax3.set_title(f'재조합 오차 (최대: {max_error:.2e})')
    ax3.set_xlabel('Time (minutes)')
    ax3.set_ylabel('|원본 - (저주파 + 고주파)|')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = save_dir / f'waveform_decomposition_{data_type}.png'
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"저장: {output_file}")

def plot_correlation_comparison(gap_days: int, data: Dict[str, np.ndarray], save_dir: Path) -> Dict:
    """True와 Pred의 상관관계 비교 시각화"""

    # Analyze correlations
    corr_true = analyze_correlation(data['low_true'], data['high_true'])
    corr_pred = analyze_correlation(data['low_pred'], data['high_pred'])

    # Peak analysis
    peaks_true = compare_peaks(data['gap_true'], data['low_true'], data['high_true'])
    peaks_pred = compare_peaks(data['gap_pred'], data['low_pred'], data['high_pred'])

    # Direction analysis
    dir_true = analyze_peak_directions(data['low_true'], data['high_true'])
    dir_pred = analyze_peak_directions(data['low_pred'], data['high_pred'])

    # Create comparison plot
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # 1. Correlation coefficients
    ax1 = axes[0, 0]
    labels = ['True', 'Pred']
    pearson_values = [corr_true['pearson_r'], corr_pred['pearson_r']]
    colors = ['blue', 'orange']
    bars = ax1.bar(labels, pearson_values, color=colors, alpha=0.7)
    ax1.set_title('저주파-고주파 Pearson 상관계수')
    ax1.set_ylabel('Correlation coefficient')
    ax1.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax1.set_ylim(-1, 1)
    for bar, val in zip(bars, pearson_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}', ha='center', va='bottom' if val > 0 else 'top')

    # 2. Coherent movement percentage
    ax2 = axes[0, 1]
    coherent_values = [corr_true['coherent_pct'], corr_pred['coherent_pct']]
    bars = ax2.bar(labels, coherent_values, color=colors, alpha=0.7)
    ax2.set_title('같은 방향 움직임 비율')
    ax2.set_ylabel('Percentage (%)')
    ax2.axhline(y=50, color='k', linestyle='--', alpha=0.3, label='Random (50%)')
    ax2.set_ylim(0, 100)
    for bar, val in zip(bars, coherent_values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%', ha='center', va='bottom')
    ax2.legend()

    # 3. Peak count comparison
    ax3 = axes[1, 0]
    peak_categories = ['원본', '저주파', '고주파', '재조합']
    true_counts = [peaks_true['original'], peaks_true['low'],
                   peaks_true['high'], peaks_true['combined']]
    pred_counts = [peaks_pred['original'], peaks_pred['low'],
                   peaks_pred['high'], peaks_pred['combined']]

    x = np.arange(len(peak_categories))
    width = 0.35
    ax3.bar(x - width/2, true_counts, width, label='True', color='blue', alpha=0.7)
    ax3.bar(x + width/2, pred_counts, width, label='Pred', color='orange', alpha=0.7)
    ax3.set_xlabel('신호 유형')
    ax3.set_ylabel('Peak 개수')
    ax3.set_title('Peak 개수 비교')
    ax3.set_xticks(x)
    ax3.set_xticklabels(peak_categories)
    ax3.legend()

    # 4. Peak ratio (Pred/True)
    ax4 = axes[1, 1]
    ratios = [pred_counts[i]/true_counts[i] if true_counts[i] > 0 else 0
              for i in range(len(true_counts))]
    bars = ax4.bar(peak_categories, ratios, color='red', alpha=0.7)
    ax4.set_title('Peak 개수 비율 (Pred/True)')
    ax4.set_ylabel('비율')
    ax4.axhline(y=1.0, color='k', linestyle='--', alpha=0.3, label='1.0 (동일)')
    ax4.axhline(y=2.0, color='r', linestyle='--', alpha=0.3, label='2.0 (2배)')
    for bar, val in zip(bars, ratios):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}', ha='center', va='bottom')
    ax4.legend()

    plt.suptitle(f'Gap {gap_days} days - 상관관계 및 Peak 분석', fontsize=14)
    plt.tight_layout()

    output_file = save_dir / f'correlation_analysis.png'
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"저장: {output_file}")

    # Return analysis results
    return {
        'correlation_true': corr_true,
        'correlation_pred': corr_pred,
        'peaks_true': peaks_true,
        'peaks_pred': peaks_pred,
        'direction_true': dir_true,
        'direction_pred': dir_pred
    }

def save_analysis_summary(gap_days: int, analysis: Dict, save_dir: Path) -> None:
    """분석 결과를 JSON으로 저장"""
    summary = {
        'gap_days': gap_days,
        'correlation_analysis': {
            'true': analysis['correlation_true'],
            'pred': analysis['correlation_pred']
        },
        'peak_analysis': {
            'true': analysis['peaks_true'],
            'pred': analysis['peaks_pred'],
            'ratio_pred_over_true': {
                'original': analysis['peaks_pred']['original'] / max(analysis['peaks_true']['original'], 1),
                'combined': analysis['peaks_pred']['combined'] / max(analysis['peaks_true']['combined'], 1)
            }
        },
        'direction_analysis': {
            'true': analysis['direction_true'],
            'pred': analysis['direction_pred']
        }
    }

    output_file = save_dir / 'waveform_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"분석 결과 저장: {output_file}")

def main():
    """메인 실행 함수"""
    print("="*70)
    print("결측 구간 파형 분해 시각화")
    print("목적: Interaction 58.6% 기여도의 시각적 검증")
    print("="*70)

    # Setup Korean font
    setup_korean_font()

    # Gap days to analyze
    gap_days_list = [3, 7, 14, 24]

    all_results = {}

    for gap_days in gap_days_list:
        print(f"\n{'='*50}")
        print(f"Processing Gap {gap_days} days")
        print(f"{'='*50}")

        # Create output directory
        save_dir = Path(__file__).parent / "results" / f"gap_{gap_days}days" / "waveforms"
        save_dir.mkdir(parents=True, exist_ok=True)

        # Load data
        data = load_gap_data(gap_days)

        # Visualize waveform decomposition
        print("\n--- True 신호 분석 ---")
        plot_waveform_decomposition(gap_days, 'true', data, save_dir)

        print("\n--- Pred 신호 분석 ---")
        plot_waveform_decomposition(gap_days, 'pred', data, save_dir)

        # Correlation and peak analysis
        print("\n--- 상관관계 및 Peak 분석 ---")
        analysis = plot_correlation_comparison(gap_days, data, save_dir)

        # Save summary
        save_analysis_summary(gap_days, analysis, save_dir)

        # Store results
        all_results[f'gap_{gap_days}days'] = analysis

        # Print key findings
        print("\n=== 주요 발견사항 ===")
        print(f"1. 저주파-고주파 상관계수:")
        print(f"   - True: {analysis['correlation_true']['pearson_r']:.3f}")
        print(f"   - Pred: {analysis['correlation_pred']['pearson_r']:.3f}")
        print(f"2. Peak 개수 (재조합):")
        print(f"   - True: {analysis['peaks_true']['combined']}")
        print(f"   - Pred: {analysis['peaks_pred']['combined']}")
        print(f"   - 비율: {analysis['peaks_pred']['combined']/max(analysis['peaks_true']['combined'], 1):.2f}x")
        print(f"3. 상쇄 비율:")
        print(f"   - True: {analysis['direction_true']['cancellation_ratio']:.1f}%")
        print(f"   - Pred: {analysis['direction_pred']['cancellation_ratio']:.1f}%")

    print("\n" + "="*70)
    print("모든 Gap 분석 완료!")
    print("="*70)

    # Save overall summary
    overall_dir = Path(__file__).parent / "results"
    overall_file = overall_dir / "waveform_analysis_all_gaps.json"
    with open(overall_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n전체 결과 저장: {overall_file}")

if __name__ == "__main__":
    main()