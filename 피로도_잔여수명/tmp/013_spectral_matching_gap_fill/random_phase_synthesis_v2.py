#!/usr/bin/env python3
"""
Random Phase Synthesis v2 - Spectral Interpolation

Tiling Issue를 해결하기 위해 Spectral Interpolation 기반의
긴 Random Signal 합성 로직 구현
"""

import numpy as np
from scipy.fft import fft, ifft, fftfreq
from scipy.interpolate import interp1d
from typing import Tuple

def compute_magnitude_spectrum(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    데이터의 Magnitude Spectrum 계산 (Positive frequencies only)

    Args:
        data: 입력 시계열

    Returns:
        freqs: 정규화된 주파수 (0 ~ 0.5)
        magnitude: Magnitude 값
    """
    n = len(data)
    fft_val = fft(data)
    
    # Positive frequencies only
    n_half = n // 2 + 1
    magnitude = np.abs(fft_val[:n_half])
    freqs = np.linspace(0, 0.5, n_half)
    
    return freqs, magnitude

def spectral_interpolation_synthesis(reference: np.ndarray,
                                     gap_length: int,
                                     seed: int = None) -> np.ndarray:
    """
    Spectral Interpolation을 이용한 Random Phase Synthesis
    
    Reference의 PSD를 보간하여 Gap 길이에 맞는 스펙트럼을 생성하고
    Random Phase를 적용하여 반복되지 않는 긴 신호를 생성함

    Args:
        reference: 참조 시계열
        gap_length: 생성할 신호 길이
        seed: Random seed

    Returns:
        합성된 신호 (길이 gap_length)
    """
    if seed is not None:
        np.random.seed(seed)
        
    # 1. Reference Magnitude Spectrum 추출
    ref_freqs, ref_mag = compute_magnitude_spectrum(reference)
    
    # 2. Target Frequency Axis 생성
    # Gap 길이에 맞는 주파수 축 (0 ~ 0.5)
    n_target = gap_length
    n_half_target = n_target // 2 + 1
    target_freqs = np.linspace(0, 0.5, n_half_target)
    
    # 3. Spectral Interpolation
    # Reference Magnitude를 Target Frequency Axis에 맞게 보간
    interpolator = interp1d(ref_freqs, ref_mag, kind='linear', fill_value="extrapolate")
    target_mag = interpolator(target_freqs)
    
    # Energy Scaling
    # Parseval's theorem: Energy in time domain = Energy in freq domain / N
    # 보간으로 인해 총 에너지가 변할 수 있으므로 보정 필요
    # 그러나 여기서는 Magnitude 자체를 보간했으므로, IFFT 후 Std를 맞추는 것이 더 확실함.
    
    # 4. Random Phase 생성 (Hermitian symmetry 고려)
    random_phase = np.zeros(n_target)
    
    # Positive frequencies (excluding DC and Nyquist)
    random_phase_pos = np.random.uniform(0, 2*np.pi, n_half_target)
    random_phase_pos[0] = 0  # DC component phase = 0
    
    if n_target % 2 == 0:
        random_phase_pos[-1] = 0 # Nyquist phase = 0
        
    # Construct full spectrum
    # Positive part
    complex_spec_pos = target_mag * np.exp(1j * random_phase_pos)
    
    # Full spectrum construction
    full_spec = np.zeros(n_target, dtype=complex)
    full_spec[:n_half_target] = complex_spec_pos
    
    # Negative part (Hermitian symmetry)
    # X[N-k] = conj(X[k])
    for k in range(1, n_half_target):
        if n_target - k < n_target:
            full_spec[n_target - k] = np.conj(complex_spec_pos[k])
            
    # 5. IFFT
    synthesized_signal = np.real(ifft(full_spec))
    
    # 6. Amplitude Scaling (Mean/Std Matching)
    # Reference의 Mean/Std를 따르도록 조정
    # 고주파 성분 합성이므로 Mean은 보통 0에 가까워야 하나, Reference Mean을 따름
    
    ref_mean = np.mean(reference)
    ref_std = np.std(reference)
    
    syn_mean = np.mean(synthesized_signal)
    syn_std = np.std(synthesized_signal)
    
    if syn_std > 1e-10:
        synthesized_signal = (synthesized_signal - syn_mean) * (ref_std / syn_std) + ref_mean
    else:
        synthesized_signal = synthesized_signal - syn_mean + ref_mean
        
    return synthesized_signal

def test_v2():
    """Simple test"""
    # Reference: 100 points
    t = np.linspace(0, 10, 100)
    ref = np.sin(2*np.pi*1.0*t) + 0.5*np.sin(2*np.pi*2.5*t)
    
    # Target: 300 points (3x length)
    target_len = 300
    
    syn = spectral_interpolation_synthesis(ref, target_len, seed=42)
    
    print(f"Reference: len={len(ref)}, std={np.std(ref):.4f}")
    print(f"Synthesized: len={len(syn)}, std={np.std(syn):.4f}")
    
    # Check periodicity (autocorrelation)
    from scipy.signal import correlate
    acf = correlate(syn, syn, mode='full')
    acf = acf[len(acf)//2:]
    acf /= acf[0]
    
    # Peak check at lag 100 (reference length)
    print(f"ACF at lag 100: {acf[100]:.4f}") 
    # Tiling would have ACF ~ 1.0 at lag 100
    # Random should be low
    
if __name__ == "__main__":
    test_v2()
