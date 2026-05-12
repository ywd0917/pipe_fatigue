#!/usr/bin/env python3
"""
주파수 성분별 Rainflow Count 분석 시각화
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json

# 한글 폰트 설정을 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.common.korean_font_utils import setup_korean_font


def plot_component_comparison(all_results, output_dir):
    """
    성분별 비교 시각화

    Args:
        all_results: 전체 gap 분석 결과
        output_dir: 출력 디렉토리
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    gap_days_list = [r["gap_days"] for r in all_results]

    # 1. Cycle 수 비교 (Stacked Bar)
    ax1 = axes[0, 0]

    # True cycles
    low_true = [r["low_true"]["cycles_count"] for r in all_results]
    high_true = [r["high_true"]["cycles_count"] for r in all_results]

    # Pred cycles
    low_pred = [r["low_pred"]["cycles_count"] for r in all_results]
    high_pred = [r["high_pred"]["cycles_count"] for r in all_results]

    x = np.arange(len(gap_days_list))
    width = 0.35

    # True stacked bar
    ax1.bar(x - width/2, low_true, width, label='Low True', color='lightblue', alpha=0.7)
    ax1.bar(x - width/2, high_true, width, bottom=low_true, label='High True', color='darkblue', alpha=0.7)

    # Pred stacked bar
    ax1.bar(x + width/2, low_pred, width, label='Low Pred', color='lightcoral', alpha=0.7)
    ax1.bar(x + width/2, high_pred, width, bottom=low_pred, label='High Pred', color='darkred', alpha=0.7)

    ax1.set_xlabel('Gap (days)')
    ax1.set_ylabel('Cycle Count')
    ax1.set_title('Cycle Count by Component (Stacked)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(gap_days_list)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # 2. 비율 비교 (Line Plot)
    ax2 = axes[0, 1]

    low_ratios = [r["analysis"]["ratios"]["low_ratio"] for r in all_results]
    high_ratios = [r["analysis"]["ratios"]["high_ratio"] for r in all_results]
    total_ratios = [r["analysis"]["ratios"]["total_ratio"] for r in all_results]

    ax2.plot(gap_days_list, low_ratios, 'o-', linewidth=2, markersize=8, label='Low Ratio', color='blue')
    ax2.plot(gap_days_list, high_ratios, 's-', linewidth=2, markersize=8, label='High Ratio', color='red')
    ax2.plot(gap_days_list, total_ratios, '^-', linewidth=2, markersize=8, label='Total Ratio', color='black')
    ax2.axhline(1.0, color='gray', linestyle='--', alpha=0.5, label='Perfect Match')

    ax2.set_xlabel('Gap (days)')
    ax2.set_ylabel('Ratio (Pred / True)')
    ax2.set_title('Cycle Count Ratios')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 기여도 분석 (Pie Charts)
    ax3 = axes[1, 0]

    # 평균 기여도
    avg_low_contrib = np.mean([r["analysis"]["contributions"]["low_pct"] for r in all_results])
    avg_high_contrib = np.mean([r["analysis"]["contributions"]["high_pct"] for r in all_results])
    avg_interaction_contrib = np.mean([r["analysis"]["contributions"]["interaction_pct"] for r in all_results])

    # Interaction이 negative인 경우 처리
    if avg_interaction_contrib < 0:
        # Negative interaction은 별도 표시
        contributions = [avg_low_contrib, avg_high_contrib]
        labels = [f'저주파\n{avg_low_contrib:.1f}%', f'고주파\n{avg_high_contrib:.1f}%']
        colors = ['lightblue', 'lightcoral']

        wedges, texts, autotexts = ax3.pie(contributions, labels=labels, colors=colors,
                                            autopct='%1.1f%%', startangle=90)

        # Negative interaction 텍스트 추가
        ax3.text(0, -1.3, f'상호작용 (재조합 시 감소): {avg_interaction_contrib:.1f}%',
                ha='center', fontsize=10, style='italic')
    else:
        contributions = [avg_low_contrib, avg_high_contrib, avg_interaction_contrib]
        labels = [f'저주파\n{avg_low_contrib:.1f}%',
                 f'고주파\n{avg_high_contrib:.1f}%',
                 f'상호작용\n{avg_interaction_contrib:.1f}%']
        colors = ['lightblue', 'lightcoral', 'lightgreen']

        ax3.pie(contributions, labels=labels, colors=colors,
               autopct='%1.1f%%', startangle=90)

    ax3.set_title('Average Excess Contribution')

    # 4. Gap별 기여도 변화 (Stacked Bar)
    ax4 = axes[1, 1]

    low_contribs = [r["analysis"]["contributions"]["low_pct"] for r in all_results]
    high_contribs = [r["analysis"]["contributions"]["high_pct"] for r in all_results]
    interaction_contribs = [r["analysis"]["contributions"]["interaction_pct"] for r in all_results]

    # 기여도 stacked bar
    ax4.bar(x, low_contribs, width, label='Low', color='lightblue', alpha=0.7)
    ax4.bar(x, high_contribs, width, bottom=low_contribs, label='High', color='lightcoral', alpha=0.7)

    # Interaction은 별도 (negative 가능)
    ax4.bar(x, interaction_contribs, width,
           bottom=np.array(low_contribs) + np.array(high_contribs),
           label='Interaction', color='lightgreen', alpha=0.7)

    ax4.set_xlabel('Gap (days)')
    ax4.set_ylabel('Contribution (%)')
    ax4.set_title('Excess Contribution by Gap')
    ax4.set_xticks(x)
    ax4.set_xticklabels(gap_days_list)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.axhline(0, color='black', linewidth=0.5)

    plt.tight_layout()
    output_file = output_dir / "component_analysis_summary.png"
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"✓ Saved: {output_file}")


def plot_amplitude_comparison(all_results, output_dir):
    """
    Amplitude 비교 시각화

    Args:
        all_results: 전체 gap 분석 결과
        output_dir: 출력 디렉토리
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    gap_days_list = [r["gap_days"] for r in all_results]

    # 각 gap별로 subplot
    for idx, (result, gap_days) in enumerate(zip(all_results, gap_days_list)):
        ax = axes[idx // 2, idx % 2]

        components = ['low_true', 'low_pred', 'high_true', 'high_pred', 'total_true', 'total_pred']
        names = [result[c]["name"] for c in components]
        amp_means = [result[c]["amplitude_mean"] for c in components]
        amp_stds = [result[c]["amplitude_std"] for c in components]

        x = np.arange(len(names))
        colors = ['lightblue', 'blue', 'lightcoral', 'red', 'lightgray', 'black']

        bars = ax.bar(x, amp_means, color=colors, alpha=0.7)

        # Error bars
        ax.errorbar(x, amp_means, yerr=amp_stds, fmt='none', ecolor='black', capsize=5, alpha=0.5)

        ax.set_ylabel('Amplitude Mean')
        ax.set_title(f'Gap {gap_days} days - Amplitude Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')

        # Add values on bars
        for bar, val in zip(bars, amp_means):
            height = bar.get_height()
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{val:.4f}',
                       ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    output_file = output_dir / "component_amplitude_comparison.png"
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"✓ Saved: {output_file}")


def plot_cycle_decomposition(all_results, output_dir):
    """
    Cycle 수 분해 시각화

    Args:
        all_results: 전체 gap 분석 결과
        output_dir: 출력 디렉토리
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    for idx, result in enumerate(all_results):
        ax = axes[idx // 2, idx % 2]
        gap_days = result["gap_days"]
        decomp = result["analysis"]["cycle_decomposition"]

        # Data
        categories = ['저주파\nTrue', '저주파\nPred', '고주파\nTrue', '고주파\nPred', '전체\nTrue', '전체\nPred']
        values = [
            decomp["low_true"],
            decomp["low_pred"],
            decomp["high_true"],
            decomp["high_pred"],
            decomp["total_true"],
            decomp["total_pred"]
        ]

        colors = ['lightblue', 'blue', 'lightcoral', 'red', 'lightgray', 'black']

        bars = ax.bar(range(len(categories)), values, color=colors, alpha=0.7)

        ax.set_ylabel('Cycle Count')
        ax.set_title(f'Gap {gap_days} days - Cycle Decomposition')
        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories, rotation=0)
        ax.grid(True, alpha=0.3, axis='y')

        # Add values on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:,}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Add excess annotations
        # Low excess
        ax.annotate(f'+{decomp["low_excess"]}',
                   xy=(1, decomp["low_pred"]), xytext=(1, decomp["low_pred"] + 5),
                   ha='center', fontsize=8, color='blue', weight='bold')

        # High excess
        ax.annotate(f'+{decomp["high_excess"]}',
                   xy=(3, decomp["high_pred"]), xytext=(3, decomp["high_pred"] * 1.05),
                   ha='center', fontsize=8, color='red', weight='bold')

        # Total excess
        ax.annotate(f'+{decomp["total_excess"]}',
                   xy=(5, decomp["total_pred"]), xytext=(5, decomp["total_pred"] * 1.05),
                   ha='center', fontsize=8, color='black', weight='bold')

    plt.tight_layout()
    output_file = output_dir / "component_cycle_decomposition.png"
    plt.savefig(output_file, dpi=150)
    plt.close()

    print(f"✓ Saved: {output_file}")


def main():
    """Main function"""
    # 한글 폰트 설정
    setup_korean_font()

    results_dir = Path(__file__).parent / "results"

    # Load results
    json_file = results_dir / "component_analysis_results.json"
    with open(json_file, 'r', encoding='utf-8') as f:
        all_results = json.load(f)

    print("="*70)
    print("주파수 성분별 분석 시각화")
    print("="*70)

    # Generate plots
    plot_component_comparison(all_results, results_dir)
    plot_amplitude_comparison(all_results, results_dir)
    plot_cycle_decomposition(all_results, results_dir)

    print("\n" + "="*70)
    print("✓ 시각화 완료")
    print("="*70)


if __name__ == "__main__":
    main()
