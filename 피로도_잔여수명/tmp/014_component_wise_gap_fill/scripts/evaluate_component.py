#!/usr/bin/env python3
"""
Component-wise evaluation system for fatigue analysis Gap filling
Project 014: STEP 1 - Baseline measurement and evaluation system

평가 지표:
1. CCR (Cycle Count Ratio): 사이클 수 비율
2. ADS (Amplitude Distribution Similarity): 진폭 분포 유사도
3. FDR (Fatigue Damage Ratio): 피로 손상 비율
"""

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
from scipy.stats import wasserstein_distance
from typing import Tuple, Dict
import json
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import rainflow counting from common utilities
try:
    from src.common.rainflow_utils import rainflow_count_amplitude_only
except ImportError:
    print("Warning: Could not import rainflow_count_amplitude_only")
    # Fallback implementation
    def rainflow_count_amplitude_only(signal):
        """Simplified rainflow counting - returns cycle count and amplitudes"""
        # Find peaks and valleys
        diff = np.diff(signal)
        peaks_idx = np.where((diff[:-1] > 0) & (diff[1:] <= 0))[0] + 1
        valleys_idx = np.where((diff[:-1] < 0) & (diff[1:] >= 0))[0] + 1

        # Calculate amplitudes
        amplitudes = []
        for i in range(min(len(peaks_idx), len(valleys_idx))):
            amp = abs(signal[peaks_idx[i]] - signal[valleys_idx[i]]) / 2
            amplitudes.append(amp)

        return len(amplitudes), np.array(amplitudes)


def butterworth_filter(signal: np.ndarray, v_valley_minutes: float = 553.5,
                       fs: float = 1/1.44) -> Tuple[np.ndarray, np.ndarray]:
    """
    Separate signal into low and high frequency components using Butterworth filter.

    Parameters:
    -----------
    signal : np.ndarray
        Input signal
    v_valley_minutes : float
        V-valley period in minutes (default: 553.5 from Project 013)
    fs : float
        Sampling frequency (1 sample per 1.44 minutes for 1000개/day)

    Returns:
    --------
    low_freq : np.ndarray
        Low frequency component
    high_freq : np.ndarray
        High frequency component
    """
    # Convert V-valley period to frequency
    cutoff_freq = 1 / v_valley_minutes
    nyquist_freq = fs / 2
    normalized_cutoff = cutoff_freq / nyquist_freq

    # Design 4th order Butterworth filter
    b, a = butter(4, normalized_cutoff, btype='low')

    # Apply filter
    low_freq = filtfilt(b, a, signal)
    high_freq = signal - low_freq

    return low_freq, high_freq


def calculate_ccr(cycles_true: int, cycles_pred: int) -> float:
    """
    Calculate Cycle Count Ratio (CCR).

    CCR = min(cycles_pred/cycles_true, cycles_true/cycles_pred)
    Range: [0, 1], where 1 is perfect match
    """
    if cycles_true == 0 or cycles_pred == 0:
        return 0.0

    ratio = cycles_pred / cycles_true
    return min(ratio, 1/ratio)


def calculate_ads(amps_true: np.ndarray, amps_pred: np.ndarray) -> float:
    """
    Calculate Amplitude Distribution Similarity (ADS).

    Uses Wasserstein distance to compare amplitude distributions.
    ADS = 1 - normalized_wasserstein_distance
    Range: [0, 1], where 1 is perfect match
    """
    if len(amps_true) == 0 or len(amps_pred) == 0:
        return 0.0

    # Normalize amplitudes to create distributions
    max_amp = max(amps_true.max(), amps_pred.max())
    if max_amp == 0:
        return 1.0

    amps_true_norm = amps_true / max_amp
    amps_pred_norm = amps_pred / max_amp

    # Calculate Wasserstein distance
    distance = wasserstein_distance(amps_true_norm, amps_pred_norm)

    # Convert to similarity (1 - normalized distance)
    # Wasserstein distance is bounded by the maximum distance between bins
    ads = 1 - min(distance, 1.0)

    return ads


def calculate_fatigue_damage(amplitudes: np.ndarray, k: float = 3.0) -> float:
    """
    Calculate fatigue damage using Palmgren-Miner rule.

    Parameters:
    -----------
    amplitudes : np.ndarray
        Stress amplitudes from rainflow counting
    k : float
        Fatigue exponent (default: 3.0 for steel)

    Returns:
    --------
    damage : float
        Cumulative fatigue damage
    """
    if len(amplitudes) == 0:
        return 0.0

    # Damage = sum(amplitude^k)
    damage = np.sum(amplitudes ** k)
    return damage


def calculate_fdr(damage_true: float, damage_pred: float) -> float:
    """
    Calculate Fatigue Damage Ratio (FDR).

    FDR = damage_pred / damage_true
    Target range: [0.95, 1.05]
    """
    if damage_true == 0:
        return 1.0 if damage_pred == 0 else float('inf')

    return damage_pred / damage_true


def evaluate_component(true_signal: np.ndarray, pred_signal: np.ndarray,
                      component_name: str) -> Dict:
    """
    Evaluate a single component (low or high frequency).

    Parameters:
    -----------
    true_signal : np.ndarray
        True (original) signal component
    pred_signal : np.ndarray
        Predicted (gap-filled) signal component
    component_name : str
        Name of component ('low' or 'high')

    Returns:
    --------
    results : dict
        Evaluation metrics and pass/fail status
    """
    # Rainflow counting
    cycles_true, amps_true = rainflow_count_amplitude_only(true_signal)
    cycles_pred, amps_pred = rainflow_count_amplitude_only(pred_signal)

    # Calculate metrics
    ccr = calculate_ccr(cycles_true, cycles_pred)
    ads = calculate_ads(amps_true, amps_pred)

    damage_true = calculate_fatigue_damage(amps_true)
    damage_pred = calculate_fatigue_damage(amps_pred)
    fdr = calculate_fdr(damage_true, damage_pred)

    # Check if all criteria are met
    pass_criteria = (ccr >= 0.95 and
                    ads >= 0.90 and
                    0.95 <= fdr <= 1.05)

    results = {
        'component': component_name,
        'cycles_true': int(cycles_true),
        'cycles_pred': int(cycles_pred),
        'CCR': round(ccr, 4),
        'ADS': round(ads, 4),
        'FDR': round(fdr, 4),
        'damage_true': damage_true,
        'damage_pred': damage_pred,
        'pass': pass_criteria,
        'amplitude_stats': {
            'true_mean': float(np.mean(amps_true)) if len(amps_true) > 0 else 0,
            'true_std': float(np.std(amps_true)) if len(amps_true) > 0 else 0,
            'true_max': float(np.max(amps_true)) if len(amps_true) > 0 else 0,
            'pred_mean': float(np.mean(amps_pred)) if len(amps_pred) > 0 else 0,
            'pred_std': float(np.std(amps_pred)) if len(amps_pred) > 0 else 0,
            'pred_max': float(np.max(amps_pred)) if len(amps_pred) > 0 else 0,
        }
    }

    return results


def evaluate_component_wise(true_signal: np.ndarray, pred_signal: np.ndarray,
                           v_valley_minutes: float = 553.5) -> Dict:
    """
    Perform component-wise evaluation of gap filling quality.

    Parameters:
    -----------
    true_signal : np.ndarray
        Original complete signal
    pred_signal : np.ndarray
        Gap-filled signal
    v_valley_minutes : float
        V-valley period for frequency separation

    Returns:
    --------
    results : dict
        Evaluation results for both components
    """
    # 1. Separate signals into components
    low_true, high_true = butterworth_filter(true_signal, v_valley_minutes)
    low_pred, high_pred = butterworth_filter(pred_signal, v_valley_minutes)

    # 2. Evaluate each component
    low_results = evaluate_component(low_true, low_pred, 'low')
    high_results = evaluate_component(high_true, high_pred, 'high')

    # 3. Overall assessment
    overall_pass = low_results['pass'] and high_results['pass']

    results = {
        'low': low_results,
        'high': high_results,
        'overall_pass': overall_pass,
        'v_valley_minutes': v_valley_minutes,
        'signal_length': len(true_signal),
        'evaluation_summary': {
            'low_pass': low_results['pass'],
            'high_pass': high_results['pass'],
            'critical_component': 'high' if not high_results['pass'] else
                                  ('low' if not low_results['pass'] else 'none'),
        }
    }

    return results


def print_evaluation_report(results: Dict):
    """Print formatted evaluation report."""
    print("\n" + "=" * 70)
    print("COMPONENT-WISE EVALUATION REPORT")
    print("=" * 70)

    for comp in ['low', 'high']:
        comp_results = results[comp]
        print(f"\n### {comp.upper()} FREQUENCY COMPONENT ###")
        print(f"  Cycles - True: {comp_results['cycles_true']}, Pred: {comp_results['cycles_pred']}")
        print(f"  CCR: {comp_results['CCR']:.4f} {'✓' if comp_results['CCR'] >= 0.95 else '✗'} (target ≥ 0.95)")
        print(f"  ADS: {comp_results['ADS']:.4f} {'✓' if comp_results['ADS'] >= 0.90 else '✗'} (target ≥ 0.90)")
        print(f"  FDR: {comp_results['FDR']:.4f} {'✓' if 0.95 <= comp_results['FDR'] <= 1.05 else '✗'} (target 0.95-1.05)")
        print(f"  Status: {'PASS ✓' if comp_results['pass'] else 'FAIL ✗'}")

    print(f"\n### OVERALL RESULT ###")
    print(f"  Overall Status: {'PASS ✓✓✓' if results['overall_pass'] else 'FAIL'}")

    if not results['overall_pass']:
        critical = results['evaluation_summary']['critical_component']
        if critical != 'none':
            print(f"  Critical Component: {critical.upper()} frequency needs improvement")

    print("=" * 70)


def save_results(results: Dict, output_path: Path):
    """Save evaluation results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to: {output_path}")


if __name__ == "__main__":
    # Example usage - will be updated when running actual baseline test
    print("Component-wise Evaluation System for Project 014")
    print("This script will be used to evaluate gap filling methods")
    print("\nUsage:")
    print("  from evaluate_component import evaluate_component_wise")
    print("  results = evaluate_component_wise(true_signal, pred_signal)")
    print("\nReady for STEP 1: Baseline testing")