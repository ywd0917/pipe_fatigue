#!/usr/bin/env python3
"""
Visualize Spectral Gap Fill Results

결과 시각화:
- Gap filling 비교
- PSD 비교
- Rainflow cycle 분포 비교
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import argparse
from scipy.signal import welch
from validation import simple_rainflow_count


def plot_gap_fill_comparison(gap_true, gap_pred, gap_days, output_dir):
    """
    Gap filling 비교 시각화

    Args:
        gap_true: 원본 gap
        gap_pred: 예측 gap
        gap_days: Gap 일수
        output_dir: 출력 디렉토리
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # 전체 비교
    ax1 = axes[0]
    ax1.plot(gap_true, 'k-', alpha=0.5, linewidth=1, label='True (removed)')
    ax1.plot(gap_pred, 'b-', linewidth=1.5, label='Spectral Synthesis', alpha=0.8)
    ax1.set_xlabel('Time (minutes)')
    ax1.set_ylabel('Pressure (kPa)')
    ax1.set_title(f'Gap Fill Comparison - {gap_days} days ({len(gap_true):,} points)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 확대 (첫 1000 points)
    ax2 = axes[1]
    zoom_points = min(1000, len(gap_true))
    ax2.plot(gap_true[:zoom_points], 'k-', alpha=0.5, linewidth=1, label='True')
    ax2.plot(gap_pred[:zoom_points], 'b-', linewidth=1.5, label='Predicted', alpha=0.8)
    ax2.set_xlabel('Time (minutes)')
    ax2.set_ylabel('Pressure (kPa)')
    ax2.set_title(f'Zoom-in: First {zoom_points} points')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = output_dir / f"gap_{gap_days}days_comparison.png"
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"✓ Saved: {output_file}")


def plot_psd_comparison(gap_true, gap_pred, gap_days, output_dir):
    """
    PSD 비교 시각화

    Args:
        gap_true: 원본 gap
        gap_pred: 예측 gap
        gap_days: Gap 일수
        output_dir: 출력 디렉토리
    """
    # PSD 계산
    nperseg = min(256, min(len(gap_true), len(gap_pred)) // 4)
    freqs_true, psd_true = welch(gap_true, fs=1.0, nperseg=nperseg)
    freqs_pred, psd_pred = welch(gap_pred, fs=1.0, nperseg=nperseg)

    # 시각화
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # PSD (log scale)
    ax1 = axes[0]
    ax1.semilogy(freqs_true, psd_true, 'k-', linewidth=2, label='True', alpha=0.7)
    ax1.semilogy(freqs_pred, psd_pred, 'b--', linewidth=2, label='Predicted', alpha=0.7)
    ax1.set_xlabel('Frequency (cycles/min)')
    ax1.set_ylabel('PSD')
    ax1.set_title(f'Power Spectral Density - {gap_days} days')
    ax1.legend()
    ax1.grid(True, alpha=0.3, which='both')

    # PSD ratio
    ax2 = axes[1]
    min_len = min(len(psd_true), len(psd_pred))
    psd_ratio = psd_pred[:min_len] / (psd_true[:min_len] + 1e-10)
    ax2.plot(freqs_true[:min_len], psd_ratio, 'g-', linewidth=1.5)
    ax2.axhline(1.0, color='red', linestyle='--', alpha=0.5, label='Perfect match')
    ax2.set_xlabel('Frequency (cycles/min)')
    ax2.set_ylabel('PSD Ratio (Predicted / True)')
    ax2.set_title('PSD Preservation')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 3])

    plt.tight_layout()
    output_file = output_dir / f"gap_{gap_days}days_psd.png"
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"✓ Saved: {output_file}")


def plot_rainflow_comparison(gap_true, gap_pred, gap_days, output_dir):
    """
    Rainflow cycle 분포 비교

    Args:
        gap_true: 원본 gap
        gap_pred: 예측 gap
        gap_days: Gap 일수
        output_dir: 출력 디렉토리
    """
    # Rainflow counting
    cycles_true = simple_rainflow_count(gap_true)
    cycles_pred = simple_rainflow_count(gap_pred)

    if len(cycles_true) == 0 or len(cycles_pred) == 0:
        print(f"⚠ No cycles detected for {gap_days} days")
        return

    amplitudes_true = cycles_true[:, 0]
    amplitudes_pred = cycles_pred[:, 0]

    # 시각화
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Histogram (amplitude)
    ax1 = axes[0, 0]
    bins = np.linspace(
        min(amplitudes_true.min(), amplitudes_pred.min()),
        max(amplitudes_true.max(), amplitudes_pred.max()),
        30
    )
    ax1.hist(amplitudes_true, bins=bins, alpha=0.5, label='True', color='black', density=True)
    ax1.hist(amplitudes_pred, bins=bins, alpha=0.5, label='Predicted', color='blue', density=True)
    ax1.set_xlabel('Cycle Amplitude')
    ax1.set_ylabel('Density')
    ax1.set_title(f'Rainflow Amplitude Distribution - {gap_days} days')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # CDF (Cumulative Distribution)
    ax2 = axes[0, 1]
    ax2.hist(amplitudes_true, bins=50, cumulative=True, density=True,
             alpha=0.5, label='True', color='black', histtype='step', linewidth=2)
    ax2.hist(amplitudes_pred, bins=50, cumulative=True, density=True,
             alpha=0.5, label='Predicted', color='blue', histtype='step', linewidth=2)
    ax2.set_xlabel('Cycle Amplitude')
    ax2.set_ylabel('Cumulative Probability')
    ax2.set_title('Cumulative Distribution Function (CDF)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Scatter (amplitude vs mean)
    ax3 = axes[1, 0]
    ax3.scatter(cycles_true[:, 1], cycles_true[:, 0],
               alpha=0.3, s=10, label='True', color='black')
    ax3.scatter(cycles_pred[:, 1], cycles_pred[:, 0],
               alpha=0.3, s=10, label='Predicted', color='blue')
    ax3.set_xlabel('Cycle Mean')
    ax3.set_ylabel('Cycle Amplitude')
    ax3.set_title('Rainflow Cycles (Amplitude vs Mean)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Statistics comparison
    ax4 = axes[1, 1]
    stats_data = {
        'Count': [len(cycles_true), len(cycles_pred)],
        'Mean Amp': [amplitudes_true.mean(), amplitudes_pred.mean()],
        'Std Amp': [amplitudes_true.std(), amplitudes_pred.std()],
        'Max Amp': [amplitudes_true.max(), amplitudes_pred.max()]
    }

    x = np.arange(len(stats_data))
    width = 0.35

    stats_names = list(stats_data.keys())
    true_vals = [stats_data[k][0] for k in stats_names]
    pred_vals = [stats_data[k][1] for k in stats_names]

    # Normalize for visualization
    true_vals_norm = [v / max(true_vals[i], pred_vals[i]) if max(true_vals[i], pred_vals[i]) > 0 else 0
                     for i, v in enumerate(true_vals)]
    pred_vals_norm = [v / max(true_vals[i], pred_vals[i]) if max(true_vals[i], pred_vals[i]) > 0 else 0
                     for i, v in enumerate(pred_vals)]

    ax4.bar(x - width/2, true_vals_norm, width, label='True', color='black', alpha=0.7)
    ax4.bar(x + width/2, pred_vals_norm, width, label='Predicted', color='blue', alpha=0.7)
    ax4.set_ylabel('Normalized Value')
    ax4.set_title('Rainflow Statistics Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(stats_names, rotation=45)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')

    # Add actual values as text
    for i, (name, vals) in enumerate(stats_data.items()):
        ax4.text(i, 1.05, f"T:{vals[0]:.2f}\nP:{vals[1]:.2f}",
                ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    output_file = output_dir / f"gap_{gap_days}days_rainflow.png"
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"✓ Saved: {output_file}")


def plot_all_gaps_summary(output_dir):
    """
    모든 gap 결과 요약 시각화

    Args:
        output_dir: 출력 디렉토리 (results/)
    """
    # Load comparison table
    csv_file = output_dir / "gap_test_comparison.csv"

    if not csv_file.exists():
        print(f"⚠ Comparison file not found: {csv_file}")
        return

    import pandas as pd
    df = pd.read_csv(csv_file)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Rainflow Match vs Gap Days
    ax1 = axes[0, 0]
    ax1.plot(df['gap_days'], df['rainflow_match'], 'bo-', linewidth=2, markersize=10)
    ax1.axhline(0.95, color='green', linestyle='--', alpha=0.5, label='Excellent (> 0.95)')
    ax1.axhline(0.90, color='orange', linestyle='--', alpha=0.5, label='Good (> 0.90)')
    ax1.set_xlabel('Gap Length (days)')
    ax1.set_ylabel('Rainflow Match Score')
    ax1.set_title('Rainflow Match vs Gap Length')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 1])

    # Multiple metrics comparison
    ax2 = axes[0, 1]
    metrics = ['psd_similarity', 'acf_correlation', 'rainflow_match']
    for metric in metrics:
        ax2.plot(df['gap_days'], df[metric], 'o-', linewidth=2, markersize=8, label=metric.replace('_', ' ').title())
    ax2.axhline(0.95, color='gray', linestyle='--', alpha=0.3)
    ax2.set_xlabel('Gap Length (days)')
    ax2.set_ylabel('Score')
    ax2.set_title('All Metrics vs Gap Length')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 1])

    # Energy preservation
    ax3 = axes[1, 0]
    ax3.plot(df['gap_days'], df['energy_preservation_pct'], 'ro-', linewidth=2, markersize=10)
    ax3.axhline(100, color='green', linestyle='--', alpha=0.5, label='Perfect (100%)')
    ax3.axhspan(95, 105, color='green', alpha=0.1, label='Target (95-105%)')
    ax3.set_xlabel('Gap Length (days)')
    ax3.set_ylabel('Energy Preservation (%)')
    ax3.set_title('Energy Preservation vs Gap Length')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Overall judgment
    ax4 = axes[1, 1]
    judgments = df['judgment'].value_counts()
    colors = {'EXCELLENT': 'green', 'GOOD': 'lightgreen', 'MARGINAL': 'orange', 'FAIL': 'red'}
    judgment_colors = [colors.get(j, 'gray') for j in judgments.index]

    ax4.bar(range(len(judgments)), judgments.values, color=judgment_colors)
    ax4.set_xticks(range(len(judgments)))
    ax4.set_xticklabels(judgments.index, rotation=45)
    ax4.set_ylabel('Count')
    ax4.set_title('Overall Judgment Distribution')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    output_file = output_dir / "all_gaps_summary.png"
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"✓ Saved: {output_file}")


def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description="Visualize Spectral Gap Fill Results")
    parser.add_argument("--gap-days", type=int, default=None, help="특정 gap만 시각화 (None이면 전체)")
    parser.add_argument("--summary", action="store_true", help="전체 요약만 생성")

    args = parser.parse_args()

    results_dir = Path(__file__).parent / "results"

    if args.summary:
        # Summary만 생성
        print("Generating summary visualization...")
        plot_all_gaps_summary(results_dir)
        return

    # 특정 gap 또는 모든 gap 시각화
    gap_dirs = []

    if args.gap_days is not None:
        gap_dirs = [results_dir / f"gap_{args.gap_days}days"]
    else:
        # 모든 gap 찾기
        gap_dirs = sorted(results_dir.glob("gap_*days"))

    for gap_dir in gap_dirs:
        if not gap_dir.exists():
            print(f"⚠ Directory not found: {gap_dir}")
            continue

        # Gap days 추출
        gap_days = int(gap_dir.name.replace("gap_", "").replace("days", ""))

        print(f"\n{'='*70}")
        print(f"Visualizing Gap: {gap_days} days")
        print(f"{'='*70}")

        # 데이터 로드
        gap_true = np.load(gap_dir / "gap_true.npy")
        gap_pred = np.load(gap_dir / "gap_pred.npy")

        # 시각화
        plot_gap_fill_comparison(gap_true, gap_pred, gap_days, gap_dir)
        plot_psd_comparison(gap_true, gap_pred, gap_days, gap_dir)
        plot_rainflow_comparison(gap_true, gap_pred, gap_days, gap_dir)

    # Summary 생성
    print(f"\n{'='*70}")
    print("Generating summary visualization...")
    print(f"{'='*70}")
    plot_all_gaps_summary(results_dir)

    print(f"\n✓ All visualizations complete")


if __name__ == "__main__":
    main()
