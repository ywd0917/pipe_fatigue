#!/usr/bin/env python3
"""
Test Tiling Fix: Comparison of Tiling vs Spectral Interpolation

Random Phase Synthesis의 두 가지 방식 비교:
1. Method A (Existing): Reference 신호를 반복(Tiling)
2. Method B (Improved): Spectral Interpolation으로 긴 신호 생성
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate, welch
from pathlib import Path
import sys

# Import modules
# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from random_phase_synthesis import random_phase_synthesis
from random_phase_synthesis_v2 import spectral_interpolation_synthesis

def compute_acf(x):
    """Compute Autocorrelation Function (normalized)"""
    n = len(x)
    # Subtract mean
    x_centered = x - np.mean(x)
    acf = correlate(x_centered, x_centered, mode='full')
    acf = acf[n-1:]
    acf /= acf[0]
    return acf

def main():
    print("="*70)
    print("TEST: Tiling Fix Comparison")
    print("="*70)
    
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    # 1. Create Reference Data (20 hours = 1200 minutes)
    # Mix of sine waves + noise
    n_ref = 1200
    t_ref = np.linspace(0, n_ref, n_ref)
    
    # Frequencies: 1/10 min, 1/50 min, 1/200 min
    reference = (
        1.0 * np.sin(2*np.pi * t_ref / 10) +
        0.5 * np.sin(2*np.pi * t_ref / 50) +
        0.3 * np.sin(2*np.pi * t_ref / 200) +
        0.2 * np.random.randn(n_ref)  # Noise
    )
    
    print(f"Reference length: {n_ref}")
    
    # 2. Target Gap Length (3 days = 4320 minutes)
    n_gap = 4320
    print(f"Target Gap length: {n_gap} (~3.6x Reference)")
    
    # 3. Method A: Tiling (Existing)
    print("\n[Method A] Tiling Synthesis...")
    gap_tiled = random_phase_synthesis(reference, n_gap, seed=42)
    
    # 4. Method B: Spectral Interpolation (Improved)
    print("\n[Method B] Spectral Interpolation Synthesis...")
    gap_interp = spectral_interpolation_synthesis(reference, n_gap, seed=42)
    
    # 5. Analysis
    
    # 5.1 Autocorrelation
    acf_tiled = compute_acf(gap_tiled)
    acf_interp = compute_acf(gap_interp)
    
    # Check peak at lag 1200 (Reference length)
    peak_lag = n_ref
    print(f"\nACF at lag {peak_lag}:")
    print(f"  Method A (Tiled): {acf_tiled[peak_lag]:.4f}")
    print(f"  Method B (Interp): {acf_interp[peak_lag]:.4f}")
    
    # 5.2 Visualization
    fig, axes = plt.subplots(3, 1, figsize=(12, 12))
    
    # Time Series
    ax1 = axes[0]
    ax1.plot(gap_tiled, 'r-', alpha=0.7, label='Method A (Tiled)')
    ax1.plot(gap_interp, 'b-', alpha=0.7, label='Method B (Interpolated)')
    ax1.set_title('Time Series Comparison')
    ax1.set_xlim(0, n_gap)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Time Series Zoom
    ax2 = axes[1]
    ax2.plot(gap_tiled, 'r-', alpha=0.7, label='Method A (Tiled)')
    ax2.plot(gap_interp, 'b-', alpha=0.7, label='Method B (Interpolated)')
    ax2.set_title('Time Series Zoom (1000-2400)')
    ax2.set_xlim(1000, 2400)
    ax2.axvline(1200, color='k', linestyle='--', label='Tile Boundary')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # ACF
    ax3 = axes[2]
    lags = np.arange(len(acf_tiled))
    ax3.plot(lags, acf_tiled, 'r-', label='Method A (Tiled)')
    ax3.plot(lags, acf_interp, 'b-', label='Method B (Interpolated)')
    ax3.set_title('Autocorrelation Function')
    ax3.set_xlabel('Lag')
    ax3.set_xlim(0, 2000)
    ax3.axvline(n_ref, color='k', linestyle='--', label='Reference Length')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_file = output_dir / 'tiling_fix_comparison.png'
    plt.savefig(output_file)
    print(f"\nSaved visualization: {output_file}")
    
    # 6. Conclusion
    if acf_tiled[peak_lag] > 0.5 and acf_interp[peak_lag] < 0.2:
        print("\n✅ SUCCESS: Tiling artifacts removed!")
    else:
        print("\n❌ FAILURE: Periodicity still present or Tiling not detected.")

if __name__ == "__main__":
    main()
