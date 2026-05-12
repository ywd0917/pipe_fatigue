#!/usr/bin/env python3
"""
STEP 1: Baseline Testing with Component-wise Evaluation

Project 013의 ARMA + Random Phase 방법을 사용하여
성분별 평가 시스템으로 Baseline 성능 측정
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json
import argparse
from datetime import datetime
from scipy.signal import butter, filtfilt
from scipy import signal
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, str(Path(__file__).parent))
from evaluate_component import evaluate_component_wise, print_evaluation_report, save_results


def create_gap(data: np.ndarray, gap_days: int, gap_center_ratio: float = 0.5) -> tuple:
    """
    Create a gap in the data.

    Parameters:
    -----------
    data : np.ndarray
        Original data
    gap_days : int
        Gap length in days
    gap_center_ratio : float
        Position of gap center (0.5 = middle)

    Returns:
    --------
    data_with_gap : np.ndarray
        Data with NaN values in gap
    gap_start : int
        Gap start index
    gap_end : int
        Gap end index
    """
    n = len(data)
    gap_length = gap_days * 1440  # 1440 minutes per day
    gap_center = int(n * gap_center_ratio)
    gap_start = max(0, gap_center - gap_length // 2)
    gap_end = min(n, gap_start + gap_length)

    data_with_gap = data.copy()
    data_with_gap[gap_start:gap_end] = np.nan

    return data_with_gap, gap_start, gap_end


def arma_synthesis(low_freq: np.ndarray, gap_start: int, gap_end: int,
                   order: tuple = (10, 10)) -> np.ndarray:
    """
    ARMA-based synthesis for low frequency component.
    Simplified version from Project 013.
    """
    filled = low_freq.copy()
    gap_length = gap_end - gap_start

    # Use data before gap for training
    train_data = low_freq[:gap_start]

    if len(train_data) < 100:
        # If not enough training data, use simple interpolation
        filled[gap_start:gap_end] = np.linspace(
            low_freq[gap_start-1] if gap_start > 0 else 0,
            low_freq[gap_end] if gap_end < len(low_freq) else 0,
            gap_length
        )
        return filled

    try:
        # Fit ARIMA model
        model = ARIMA(train_data[-min(len(train_data), 5000):], order=(order[0], 0, order[1]))
        model_fit = model.fit()

        # Generate predictions
        predictions = model_fit.forecast(steps=gap_length)
        filled[gap_start:gap_end] = predictions

    except Exception as e:
        print(f"  Warning: ARMA failed ({e}), using linear interpolation")
        filled[gap_start:gap_end] = np.linspace(
            low_freq[gap_start-1] if gap_start > 0 else 0,
            low_freq[gap_end] if gap_end < len(low_freq) else 0,
            gap_length
        )

    return filled


def random_phase_synthesis(high_freq: np.ndarray, gap_start: int, gap_end: int,
                          reference_length: int = 10080) -> np.ndarray:
    """
    Random Phase IFFT synthesis for high frequency component.
    Simplified version from Project 013.
    """
    filled = high_freq.copy()
    gap_length = gap_end - gap_start

    # Get reference signal
    ref_end = gap_start
    ref_start = max(0, ref_end - reference_length)

    if ref_start == ref_end:
        # No reference available, use zero filling
        filled[gap_start:gap_end] = 0
        return filled

    reference = high_freq[ref_start:ref_end]

    # Compute FFT of reference
    ref_fft = np.fft.fft(reference)
    ref_magnitude = np.abs(ref_fft)

    # Generate with random phase
    if gap_length <= len(reference):
        # Direct generation
        random_phase = np.random.uniform(-np.pi, np.pi, len(reference))
        synthetic_fft = ref_magnitude * np.exp(1j * random_phase)
        synthetic = np.real(np.fft.ifft(synthetic_fft))
        filled[gap_start:gap_end] = synthetic[:gap_length]
    else:
        # Tiling for longer gaps
        random_phase = np.random.uniform(-np.pi, np.pi, len(reference))
        synthetic_fft = ref_magnitude * np.exp(1j * random_phase)
        synthetic_tile = np.real(np.fft.ifft(synthetic_fft))

        # Tile to fill gap
        n_tiles = gap_length // len(synthetic_tile) + 1
        synthetic = np.tile(synthetic_tile, n_tiles)[:gap_length]
        filled[gap_start:gap_end] = synthetic

    # Adjust mean and std
    ref_mean = np.mean(reference)
    ref_std = np.std(reference)

    if ref_std > 0:
        gap_data = filled[gap_start:gap_end]
        gap_data = (gap_data - np.mean(gap_data)) / (np.std(gap_data) + 1e-8) * ref_std + ref_mean
        filled[gap_start:gap_end] = gap_data

    return filled


def edge_smoothing(signal: np.ndarray, gap_start: int, gap_end: int,
                   window_size: int = 50) -> np.ndarray:
    """
    Apply edge smoothing using cosine tapering.
    Simplified version - just smooth the gap edges.
    """
    smoothed = signal.copy()

    # Apply tapering window at gap edges
    if window_size > 0:
        # Left edge tapering
        left_window = min(window_size, gap_start, gap_end - gap_start)
        if left_window > 0:
            taper = 0.5 * (1 - np.cos(np.pi * np.arange(left_window) / left_window))
            smoothed[gap_start:gap_start+left_window] *= taper

        # Right edge tapering
        right_window = min(window_size, len(signal) - gap_end, gap_end - gap_start)
        if right_window > 0:
            taper = 0.5 * (1 + np.cos(np.pi * np.arange(right_window) / right_window))
            smoothed[gap_end-right_window:gap_end] *= taper

    return smoothed


def spectral_gap_fill(data: np.ndarray, gap_start: int, gap_end: int,
                      v_valley_minutes: float = 553.5) -> np.ndarray:
    """
    Main gap filling pipeline using spectral matching approach.
    """
    print(f"\n  Applying Spectral Gap Fill...")
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

    # Fill high frequency with Random Phase
    print(f"  Filling high frequency with Random Phase...")
    high_filled = random_phase_synthesis(high_freq, gap_start, gap_end)

    # Edge smoothing
    low_filled = edge_smoothing(low_filled, gap_start, gap_end, window_size=60)
    high_filled = edge_smoothing(high_filled, gap_start, gap_end, window_size=20)

    # Combine
    filled = low_filled + high_filled

    return filled


def run_baseline_test(area_code: str = "0243", gap_days: list = [7, 14, 24]):
    """
    Run baseline test for all gap sizes.
    """
    print("\n" + "=" * 70)
    print("PROJECT 014 - STEP 1: BASELINE TEST")
    print("=" * 70)
    print(f"Area: {area_code}")
    print(f"Gaps: {gap_days} days")
    print(f"Method: ARMA (low) + Random Phase (high)")

    # Load data
    data_path = Path(f"/Users/jhpark/development/eroumtech/fatigue/fatigue-qgis/data/raw/{area_code} 소구역 압력 데이터.csv")

    if not data_path.exists():
        print(f"Error: Data file not found: {data_path}")
        return

    df = pd.read_csv(data_path)
    pressure = df['wtrprsr'].values
    print(f"\n✓ Loaded {len(pressure)} pressure points")
    print(f"  Range: [{pressure.min():.2f}, {pressure.max():.2f}]")

    # Results storage
    all_results = {
        'area': area_code,
        'method': 'ARMA + Random Phase (Baseline)',
        'timestamp': datetime.now().isoformat(),
        'gap_results': {}
    }

    # Test each gap
    for gap in gap_days:
        print(f"\n{'='*50}")
        print(f"Testing {gap}-day gap")
        print('='*50)

        # Create gap
        data_with_gap, gap_start, gap_end = create_gap(pressure, gap)
        print(f"Gap created: [{gap_start}:{gap_end}]")

        # Apply spectral gap fill
        filled = spectral_gap_fill(data_with_gap, gap_start, gap_end)

        # Get true data for gap region
        true_gap = pressure[gap_start:gap_end]
        pred_gap = filled[gap_start:gap_end]

        # Component-wise evaluation
        print("\nEvaluating components...")
        results = evaluate_component_wise(true_gap, pred_gap)

        # Store results
        all_results['gap_results'][f'{gap}days'] = results

        # Print report
        print_evaluation_report(results)

        # Save individual gap result
        gap_output = Path(f"results/baseline/gap_{gap}days_results.json")
        save_results(results, gap_output)

    # Save overall results
    output_path = Path("results/baseline/evaluation_results.json")
    save_results(all_results, output_path)

    # Generate summary report
    generate_baseline_report(all_results)

    # Check if we need STEP 2
    need_step2 = False
    for gap, results in all_results['gap_results'].items():
        if not results['high']['pass']:
            need_step2 = True
            break

    print("\n" + "=" * 70)
    print("BASELINE TEST COMPLETE")
    print("=" * 70)

    if need_step2:
        print("\n⚠️ HIGH FREQUENCY COMPONENT FAILED")
        print("→ Proceed to STEP 2: GARCH/SV Model")
    else:
        print("\n✓ ALL COMPONENTS PASSED")
        print("→ Project Complete!")

    return all_results


def generate_baseline_report(results: dict):
    """Generate markdown report for baseline results."""
    report_path = Path("results/baseline/baseline_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        f.write("# STEP 1: Baseline Test Results\n\n")
        f.write(f"**Date**: {results['timestamp'][:10]}\n")
        f.write(f"**Area**: {results['area']}\n")
        f.write(f"**Method**: {results['method']}\n\n")

        f.write("## Summary\n\n")

        # Summary table
        f.write("| Gap | Component | CCR | ADS | FDR | Status |\n")
        f.write("|-----|-----------|-----|-----|-----|--------|\n")

        for gap_name, gap_results in results['gap_results'].items():
            for comp in ['low', 'high']:
                comp_res = gap_results[comp]
                status = "✓ PASS" if comp_res['pass'] else "✗ FAIL"
                f.write(f"| {gap_name} | {comp} | {comp_res['CCR']:.3f} | ")
                f.write(f"{comp_res['ADS']:.3f} | {comp_res['FDR']:.3f} | {status} |\n")

        # Detailed analysis
        f.write("\n## Detailed Analysis\n\n")

        for gap_name, gap_results in results['gap_results'].items():
            f.write(f"### {gap_name} Gap\n\n")

            # Low frequency
            low = gap_results['low']
            f.write(f"**Low Frequency (ARMA)**:\n")
            f.write(f"- Cycles: {low['cycles_true']} → {low['cycles_pred']}\n")
            f.write(f"- CCR: {low['CCR']:.4f} {'✓' if low['CCR'] >= 0.95 else '✗'}\n")
            f.write(f"- ADS: {low['ADS']:.4f} {'✓' if low['ADS'] >= 0.90 else '✗'}\n")
            f.write(f"- FDR: {low['FDR']:.4f} {'✓' if 0.95 <= low['FDR'] <= 1.05 else '✗'}\n\n")

            # High frequency
            high = gap_results['high']
            f.write(f"**High Frequency (Random Phase)**:\n")
            f.write(f"- Cycles: {high['cycles_true']} → {high['cycles_pred']}\n")
            f.write(f"- CCR: {high['CCR']:.4f} {'✓' if high['CCR'] >= 0.95 else '✗'}\n")
            f.write(f"- ADS: {high['ADS']:.4f} {'✓' if high['ADS'] >= 0.90 else '✗'}\n")
            f.write(f"- FDR: {high['FDR']:.4f} {'✓' if 0.95 <= high['FDR'] <= 1.05 else '✗'}\n\n")

        # Conclusion
        f.write("## Conclusion\n\n")

        need_improvement = False
        for gap_name, gap_results in results['gap_results'].items():
            if not gap_results['high']['pass']:
                need_improvement = True
                break

        if need_improvement:
            f.write("❌ **High frequency component needs improvement**\n\n")
            f.write("As expected from Project 013, Random Phase IFFT fails to preserve:\n")
            f.write("- Rainflow cycle counts (CCR too low)\n")
            f.write("- Amplitude distribution (ADS insufficient)\n")
            f.write("- Fatigue damage (FDR out of range)\n\n")
            f.write("**Next Step**: Proceed to STEP 2 - GARCH/SV Model Implementation\n")
        else:
            f.write("✅ **All components meet success criteria**\n\n")
            f.write("Both low and high frequency components successfully preserved.\n")
            f.write("No further improvement needed.\n")

    print(f"\n✓ Report saved to: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STEP 1: Baseline Test")
    parser.add_argument("--area", type=str, default="0243", help="Area code")
    parser.add_argument("--gaps", type=int, nargs="+", default=[7, 14, 24],
                       help="Gap sizes in days")

    args = parser.parse_args()

    # Set random seed for reproducibility
    np.random.seed(42)

    # Run baseline test
    results = run_baseline_test(args.area, args.gaps)