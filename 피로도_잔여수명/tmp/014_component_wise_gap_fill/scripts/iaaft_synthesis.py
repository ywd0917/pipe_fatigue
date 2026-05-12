#!/usr/bin/env python3
"""
IAAFT (Iterated Amplitude Adjusted Fourier Transform) Synthesis

Preserves both:
1. Power spectral density (magnitude spectrum)
2. Amplitude distribution (sorted values)

This dual constraint helps maintain peak-valley patterns crucial for Rainflow counting.
"""

import numpy as np
from scipy import signal
from typing import Tuple, Optional


def iaaft_synthesis(data: np.ndarray,
                   gap_start: int,
                   gap_end: int,
                   reference_length: int = 10080,
                   max_iterations: int = 50,
                   convergence_tol: float = 1e-6,
                   random_seed: Optional[int] = None) -> np.ndarray:
    """
    IAAFT-based synthesis for gap filling.

    Parameters:
    -----------
    data : np.ndarray
        Full signal with gap (gap region ignored)
    gap_start : int
        Start index of gap
    gap_end : int
        End index of gap
    reference_length : int
        Length of reference window (default: 10080 = 7 days)
    max_iterations : int
        Maximum iterations for IAAFT
    convergence_tol : float
        Convergence tolerance
    random_seed : int, optional
        Random seed for reproducibility

    Returns:
    --------
    filled : np.ndarray
        Complete signal with gap filled
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    filled = data.copy()
    gap_length = gap_end - gap_start

    # Get reference data before gap
    ref_end = gap_start
    ref_start = max(0, ref_end - reference_length)

    if ref_start == ref_end:
        # No reference available, use zero filling
        filled[gap_start:gap_end] = 0
        return filled

    reference = data[ref_start:ref_end]

    # Generate synthetic data using IAAFT
    synthetic = iaaft_core(reference, gap_length, max_iterations, convergence_tol)

    # Fill the gap
    filled[gap_start:gap_end] = synthetic

    return filled


def iaaft_core(reference: np.ndarray,
               target_length: int,
               max_iterations: int = 50,
               convergence_tol: float = 1e-6) -> np.ndarray:
    """
    Core IAAFT algorithm.

    Iteratively adjusts a random signal to match both:
    - Amplitude distribution of reference
    - Power spectrum of reference
    """
    # If target is longer than reference, tile reference
    if target_length > len(reference):
        n_tiles = target_length // len(reference) + 1
        extended_ref = np.tile(reference, n_tiles)[:target_length]
        return iaaft_single(extended_ref, max_iterations, convergence_tol)
    else:
        # Use a segment of reference length
        ref_segment = reference[-target_length:] if target_length < len(reference) else reference
        return iaaft_single(ref_segment, max_iterations, convergence_tol)[:target_length]


def iaaft_single(reference: np.ndarray,
                max_iterations: int = 50,
                convergence_tol: float = 1e-6) -> np.ndarray:
    """
    IAAFT for single segment.

    Algorithm:
    1. Start with random Gaussian noise
    2. Iteratively:
       a. Match amplitude distribution (rank ordering)
       b. Match power spectrum (FFT magnitude)
    3. Continue until convergence or max iterations
    """
    n = len(reference)

    # Step 1: Sort reference amplitudes
    sorted_reference = np.sort(reference)

    # Step 2: Compute reference power spectrum
    ref_fft = np.fft.rfft(reference)
    ref_magnitude = np.abs(ref_fft)

    # Step 3: Initialize with random Gaussian noise
    synthetic = np.random.randn(n)
    synthetic = (synthetic - np.mean(synthetic)) / np.std(synthetic)
    synthetic = synthetic * np.std(reference) + np.mean(reference)

    # Step 4: Iterative adjustment
    prev_error = float('inf')

    for iteration in range(max_iterations):
        # Step 4a: Amplitude adjustment (rank ordering)
        # Sort synthetic and get ranking
        sorted_indices = np.argsort(synthetic)
        rank_ordered = np.zeros_like(synthetic)
        rank_ordered[sorted_indices] = sorted_reference

        # Step 4b: Spectral adjustment
        # FFT of rank-ordered signal
        rank_fft = np.fft.rfft(rank_ordered)
        rank_phase = np.angle(rank_fft)

        # Impose reference magnitude with current phase
        adjusted_fft = ref_magnitude * np.exp(1j * rank_phase)
        synthetic = np.fft.irfft(adjusted_fft, n=n)

        # Check convergence (spectral error)
        synth_fft = np.fft.rfft(synthetic)
        spectral_error = np.mean(np.abs(np.abs(synth_fft) - ref_magnitude))

        if spectral_error < convergence_tol:
            print(f"  IAAFT converged at iteration {iteration + 1}")
            break

        if abs(spectral_error - prev_error) < convergence_tol * 0.1:
            print(f"  IAAFT plateau at iteration {iteration + 1}")
            break

        prev_error = spectral_error

    # Final amplitude adjustment
    sorted_indices = np.argsort(synthetic)
    final = np.zeros_like(synthetic)
    final[sorted_indices] = sorted_reference

    # One more spectral adjustment for better spectrum match
    final_fft = np.fft.rfft(final)
    final_phase = np.angle(final_fft)
    adjusted_fft = ref_magnitude * np.exp(1j * final_phase)
    synthetic = np.fft.irfft(adjusted_fft, n=n)

    # Ensure mean and std match
    synthetic = (synthetic - np.mean(synthetic)) / (np.std(synthetic) + 1e-8)
    synthetic = synthetic * np.std(reference) + np.mean(reference)

    return synthetic


def validate_iaaft(reference: np.ndarray, synthetic: np.ndarray) -> dict:
    """
    Validate IAAFT results by checking preservation of:
    1. Amplitude distribution
    2. Power spectrum

    Returns:
    --------
    metrics : dict
        Validation metrics
    """
    from scipy.stats import ks_2samp, wasserstein_distance

    # 1. Amplitude distribution similarity
    ks_stat, ks_pval = ks_2samp(reference, synthetic)
    w_dist = wasserstein_distance(reference, synthetic)

    # 2. Power spectrum similarity
    ref_psd = np.abs(np.fft.rfft(reference))**2
    syn_psd = np.abs(np.fft.rfft(synthetic))**2

    # Normalize PSDs
    ref_psd_norm = ref_psd / np.sum(ref_psd)
    syn_psd_norm = syn_psd / np.sum(syn_psd)

    psd_correlation = np.corrcoef(ref_psd_norm, syn_psd_norm)[0, 1]
    psd_rmse = np.sqrt(np.mean((ref_psd_norm - syn_psd_norm)**2))

    # 3. Basic statistics
    mean_diff = abs(np.mean(synthetic) - np.mean(reference))
    std_ratio = np.std(synthetic) / (np.std(reference) + 1e-8)

    metrics = {
        'amplitude_ks_statistic': ks_stat,
        'amplitude_ks_pvalue': ks_pval,
        'amplitude_wasserstein': w_dist,
        'psd_correlation': psd_correlation,
        'psd_rmse': psd_rmse,
        'mean_difference': mean_diff,
        'std_ratio': std_ratio,
        'validation_pass': (ks_pval > 0.05 and psd_correlation > 0.95)
    }

    return metrics


def iaaft_with_constraints(reference: np.ndarray,
                          target_length: int,
                          preserve_extrema: bool = True,
                          max_iterations: int = 100) -> np.ndarray:
    """
    Enhanced IAAFT with additional constraints for better Rainflow preservation.

    Parameters:
    -----------
    preserve_extrema : bool
        If True, tries to preserve peak-valley patterns better
    """
    # Basic IAAFT
    synthetic = iaaft_core(reference, target_length, max_iterations)

    if not preserve_extrema:
        return synthetic

    # Additional extrema preservation
    # Find peaks and valleys in reference
    ref_peaks, _ = signal.find_peaks(reference)
    ref_valleys, _ = signal.find_peaks(-reference)

    if len(ref_peaks) > 0 and len(ref_valleys) > 0:
        # Calculate average peak/valley spacing
        avg_peak_spacing = np.mean(np.diff(ref_peaks)) if len(ref_peaks) > 1 else len(reference) // 4
        avg_valley_spacing = np.mean(np.diff(ref_valleys)) if len(ref_valleys) > 1 else len(reference) // 4

        # Impose similar spacing in synthetic
        syn_peaks, _ = signal.find_peaks(synthetic, distance=int(avg_peak_spacing * 0.7))
        syn_valleys, _ = signal.find_peaks(-synthetic, distance=int(avg_valley_spacing * 0.7))

        # Adjust amplitudes at extrema to better match reference distribution
        if len(syn_peaks) > 0:
            ref_peak_values = np.sort(reference[ref_peaks])
            syn_peak_indices = np.argsort(synthetic[syn_peaks])
            for i, idx in enumerate(syn_peak_indices[:min(len(ref_peak_values), len(syn_peaks))]):
                synthetic[syn_peaks[idx]] = ref_peak_values[min(i, len(ref_peak_values)-1)]

        if len(syn_valleys) > 0:
            ref_valley_values = np.sort(reference[ref_valleys])
            syn_valley_indices = np.argsort(synthetic[syn_valleys])
            for i, idx in enumerate(syn_valley_indices[:min(len(ref_valley_values), len(syn_valleys))]):
                synthetic[syn_valleys[idx]] = ref_valley_values[min(i, len(ref_valley_values)-1)]

    return synthetic


if __name__ == "__main__":
    """Test IAAFT implementation"""
    print("IAAFT Synthesis Module")
    print("=" * 50)

    # Create test signal
    t = np.linspace(0, 100, 1000)
    test_signal = (np.sin(2 * np.pi * 0.1 * t) +
                   0.5 * np.sin(2 * np.pi * 0.3 * t) +
                   0.2 * np.random.randn(1000))

    # Create gap
    gap_start, gap_end = 400, 600
    gapped = test_signal.copy()
    gapped[gap_start:gap_end] = np.nan

    # Test IAAFT
    print("\nTesting IAAFT synthesis...")
    filled = iaaft_synthesis(gapped, gap_start, gap_end, random_seed=42)

    # Validate
    reference = test_signal[:gap_start]
    synthetic = filled[gap_start:gap_end]
    metrics = validate_iaaft(reference[-200:], synthetic)

    print("\nValidation Results:")
    print(f"  Amplitude KS p-value: {metrics['amplitude_ks_pvalue']:.4f}")
    print(f"  PSD correlation: {metrics['psd_correlation']:.4f}")
    print(f"  Validation: {'PASS' if metrics['validation_pass'] else 'FAIL'}")
    print("\nIAAFT module ready for integration.")