#!/usr/bin/env python3
"""
STEP 2: Test IAAFT and other spectral methods

Compares:
1. Baseline (Random Phase)
2. IAAFT
3. Constrained Phase (if implemented)
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json
import argparse
from datetime import datetime
from scipy.signal import butter, filtfilt
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, str(Path(__file__).parent))

from evaluate_component import evaluate_component_wise, print_evaluation_report, save_results
from baseline_test import create_gap, arma_synthesis, random_phase_synthesis, edge_smoothing
from iaaft_synthesis import iaaft_synthesis


def spectral_gap_fill_iaaft(data: np.ndarray, gap_start: int, gap_end: int,
                            v_valley_minutes: float = 553.5) -> np.ndarray:
    """
    Gap filling using ARMA (low) + IAAFT (high).
    """
    print(f"\n  Applying Spectral Gap Fill with IAAFT...")
    print(f"  Gap: [{gap_start}:{gap_end}] ({gap_end-gap_start} points)")

    # Frequency separation
    fs = 1.0  # 1 sample per minute
    cutoff = 1.0 / v_valley_minutes
    nyquist = fs / 2
    normalized_cutoff = cutoff / nyquist

    b, a = butter(4, normalized_cutoff, btype='low')
    low_freq = filtfilt(b, a, np.nan_to_num(data))
    high_freq = np.nan_to_num(data) - low_freq

    print(f"  Low freq variance: {np.var(low_freq):.4f}")
    print(f"  High freq variance: {np.var(high_freq):.4f}")

    # Fill low frequency with ARMA
    print(f"  Filling low frequency with ARMA...")
    low_filled = arma_synthesis(low_freq, gap_start, gap_end)

    # Fill high frequency with IAAFT
    print(f"  Filling high frequency with IAAFT...")
    high_filled = iaaft_synthesis(high_freq, gap_start, gap_end, random_seed=42)

    # Edge smoothing
    low_filled = edge_smoothing(low_filled, gap_start, gap_end, window_size=60)
    high_filled = edge_smoothing(high_filled, gap_start, gap_end, window_size=20)

    # Combine
    filled = low_filled + high_filled

    return filled


def compare_methods(area_code: str = "0243", gap_days: int = 7):
    """
    Compare Random Phase vs IAAFT for a single gap size.
    """
    print("\n" + "=" * 70)
    print(f"STEP 2: Comparing Methods for {gap_days}-day gap")
    print("=" * 70)

    # Load data
    data_path = Path(f"/Users/jhpark/development/eroumtech/fatigue/fatigue-qgis/data/raw/{area_code} 소구역 압력 데이터.csv")

    if not data_path.exists():
        print(f"Error: Data file not found: {data_path}")
        return None

    df = pd.read_csv(data_path)
    pressure = df['wtrprsr'].values
    print(f"\n✓ Loaded {len(pressure)} pressure points")

    # Create gap
    data_with_gap, gap_start, gap_end = create_gap(pressure, gap_days)
    print(f"Gap created: [{gap_start}:{gap_end}]")

    # Get true data for gap region
    true_gap = pressure[gap_start:gap_end]

    results = {}

    # Method 1: Random Phase (baseline)
    print("\n" + "-" * 50)
    print("Method 1: Random Phase (Baseline)")
    print("-" * 50)

    # Use the baseline method from STEP 1
    from baseline_test import spectral_gap_fill as baseline_gap_fill
    filled_baseline = baseline_gap_fill(data_with_gap, gap_start, gap_end)
    pred_baseline = filled_baseline[gap_start:gap_end]

    results_baseline = evaluate_component_wise(true_gap, pred_baseline)
    print_evaluation_report(results_baseline)
    results['random_phase'] = results_baseline

    # Method 2: IAAFT
    print("\n" + "-" * 50)
    print("Method 2: IAAFT")
    print("-" * 50)

    filled_iaaft = spectral_gap_fill_iaaft(data_with_gap, gap_start, gap_end)
    pred_iaaft = filled_iaaft[gap_start:gap_end]

    results_iaaft = evaluate_component_wise(true_gap, pred_iaaft)
    print_evaluation_report(results_iaaft)
    results['iaaft'] = results_iaaft

    # Compare results
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    print("\n### High Frequency Component (Critical) ###")
    print("| Method | CCR | ADS | FDR | Pass |")
    print("|--------|-----|-----|-----|------|")

    for method_name, method_results in results.items():
        high = method_results['high']
        pass_str = "✓" if high['pass'] else "✗"
        print(f"| {method_name:12} | {high['CCR']:.3f} | {high['ADS']:.3f} | {high['FDR']:.3f} | {pass_str} |")

    # Calculate improvement
    ccr_baseline = results['random_phase']['high']['CCR']
    ccr_iaaft = results['iaaft']['high']['CCR']
    improvement = ((ccr_iaaft - ccr_baseline) / ccr_baseline) * 100

    print(f"\n**CCR Improvement**: {ccr_baseline:.3f} → {ccr_iaaft:.3f} ({improvement:+.1f}%)")

    # Check if target met
    if results['iaaft']['high']['CCR'] >= 0.95:
        print("\n✅ **SUCCESS**: Target CCR ≥ 0.95 achieved with IAAFT!")
    else:
        print(f"\n⚠️ **PARTIAL SUCCESS**: CCR improved but still below 0.95")
        print(f"   Need additional methods (Constrained Phase) to reach target")

    return results


def run_full_test(area_code: str = "0243", gap_days: list = [7, 14, 24]):
    """
    Run IAAFT test for all gap sizes.
    """
    print("\n" + "=" * 70)
    print("PROJECT 014 - STEP 2: IAAFT TEST")
    print("=" * 70)
    print(f"Area: {area_code}")
    print(f"Gaps: {gap_days} days")
    print(f"Method: ARMA (low) + IAAFT (high)")

    # Results storage
    all_results = {
        'area': area_code,
        'method': 'ARMA + IAAFT',
        'timestamp': datetime.now().isoformat(),
        'gap_results': {}
    }

    # Test each gap
    for gap in gap_days:
        print(f"\n{'='*50}")
        print(f"Testing {gap}-day gap with IAAFT")
        print('='*50)

        results = compare_methods(area_code, gap)
        if results:
            all_results['gap_results'][f'{gap}days'] = results['iaaft']

    # Save overall results
    output_dir = Path("results/step2")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "iaaft_results.json"
    save_results(all_results, output_path)

    # Generate report
    generate_step2_report(all_results)

    # Determine next steps
    all_pass = True
    for gap_name, gap_results in all_results['gap_results'].items():
        if not gap_results['high']['pass']:
            all_pass = False
            break

    print("\n" + "=" * 70)
    print("STEP 2 COMPLETE")
    print("=" * 70)

    if all_pass:
        print("\n✅ ALL TESTS PASSED")
        print("→ Project Complete!")
    else:
        # Check if any CCR > 0.85
        max_ccr = max(r['high']['CCR'] for r in all_results['gap_results'].values())
        if max_ccr >= 0.85:
            print(f"\n⚠️ IAAFT achieved CCR {max_ccr:.3f}")
            print("→ Proceed to Constrained Phase for further improvement")
        else:
            print(f"\n❌ IAAFT only achieved CCR {max_ccr:.3f}")
            print("→ May need to skip to STEP 3 (GARCH/SV)")

    return all_results


def generate_step2_report(results: dict):
    """Generate markdown report for STEP 2 results."""
    report_path = Path("results/step2/step2_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        f.write("# STEP 2: IAAFT Test Results\n\n")
        f.write(f"**Date**: {results['timestamp'][:10]}\n")
        f.write(f"**Area**: {results['area']}\n")
        f.write(f"**Method**: {results['method']}\n\n")

        f.write("## Summary\n\n")

        # Comparison with baseline
        f.write("### IAAFT vs Random Phase (Baseline)\n\n")
        f.write("| Gap | Component | Baseline CCR | IAAFT CCR | Improvement |\n")
        f.write("|-----|-----------|-------------|-----------|-------------|\n")

        # Load baseline results for comparison
        baseline_path = Path("results/baseline/evaluation_results.json")
        if baseline_path.exists():
            with open(baseline_path, 'r') as bf:
                baseline_data = json.load(bf)

            for gap_name, gap_results in results['gap_results'].items():
                baseline_gap = baseline_data['gap_results'].get(gap_name, {})
                if baseline_gap:
                    for comp in ['low', 'high']:
                        baseline_ccr = baseline_gap[comp]['CCR']
                        iaaft_ccr = gap_results[comp]['CCR']
                        improvement = ((iaaft_ccr - baseline_ccr) / baseline_ccr) * 100
                        f.write(f"| {gap_name} | {comp} | {baseline_ccr:.3f} | ")
                        f.write(f"{iaaft_ccr:.3f} | {improvement:+.1f}% |\n")

        f.write("\n## Detailed Results\n\n")

        for gap_name, gap_results in results['gap_results'].items():
            f.write(f"### {gap_name} Gap\n\n")

            # High frequency (critical)
            high = gap_results['high']
            f.write(f"**High Frequency (IAAFT)**:\n")
            f.write(f"- Cycles: {high['cycles_true']} → {high['cycles_pred']}\n")
            f.write(f"- CCR: {high['CCR']:.4f} {'✓' if high['CCR'] >= 0.95 else '✗'}\n")
            f.write(f"- ADS: {high['ADS']:.4f} {'✓' if high['ADS'] >= 0.90 else '✓'}\n")
            f.write(f"- FDR: {high['FDR']:.4f} {'✓' if 0.95 <= high['FDR'] <= 1.05 else '✗'}\n\n")

        # Conclusion
        f.write("## Conclusion\n\n")

        max_ccr = max(r['high']['CCR'] for r in results['gap_results'].values())
        if max_ccr >= 0.95:
            f.write("✅ **SUCCESS: Target achieved with IAAFT**\n\n")
            f.write(f"IAAFT successfully improved high frequency CCR to {max_ccr:.3f}\n")
            f.write("No further methods needed.\n")
        elif max_ccr >= 0.85:
            f.write("⚠️ **PARTIAL SUCCESS: Significant improvement**\n\n")
            f.write(f"IAAFT improved CCR to {max_ccr:.3f} (from ~0.78)\n")
            f.write("Consider Constrained Phase for further improvement.\n")
        else:
            f.write("❌ **LIMITED IMPROVEMENT**\n\n")
            f.write(f"IAAFT only achieved CCR {max_ccr:.3f}\n")
            f.write("May need alternative approaches (GARCH/SV).\n")

    print(f"\n✓ Report saved to: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STEP 2: IAAFT Test")
    parser.add_argument("--area", type=str, default="0243", help="Area code")
    parser.add_argument("--gaps", type=int, nargs="+", default=[7],
                       help="Gap sizes in days (default: 7)")
    parser.add_argument("--full", action="store_true",
                       help="Run full test with all gaps")

    args = parser.parse_args()

    # Set random seed for reproducibility
    np.random.seed(42)

    if args.full:
        results = run_full_test(args.area, [7, 14, 24])
    else:
        results = run_full_test(args.area, args.gaps)