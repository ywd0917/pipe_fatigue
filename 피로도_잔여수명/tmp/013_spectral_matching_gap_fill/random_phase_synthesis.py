#!/usr/bin/env python3
"""
Random Phase 기반 고주파 스펙트럴 합성

고주파 성분 (ACF 0.0746)은 예측 불가능하므로
동일한 PSD(Power Spectral Density)를 가진 랜덤 신호 생성
"""

import numpy as np
from scipy.fft import fft, ifft, fftfreq
from scipy.signal import welch
from typing import Tuple


def compute_psd(data: np.ndarray, fs: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Welch method로 Power Spectral Density 계산

    Args:
        data: 시계열 데이터
        fs: 샘플링 주파수 (기본값: 1.0 = 1분)

    Returns:
        freqs: 주파수
        psd: Power Spectral Density
    """
    freqs, psd = welch(data, fs=fs, nperseg=min(256, len(data)//4))
    return freqs, psd


def random_phase_synthesis(reference: np.ndarray,
                           gap_length: int,
                           preserve_psd: bool = True,
                           seed: int = None) -> np.ndarray:
    """
    Random Phase IFFT 기반 고주파 합성

    동일한 Magnitude Spectrum을 유지하면서
    Phase를 랜덤화하여 통계적으로 유사한 신호 생성

    Args:
        reference: 참조 시계열 (Gap 전후 데이터)
        gap_length: Gap 길이
        preserve_psd: PSD 보존 여부
        seed: Random seed (재현성 필요 시)

    Returns:
        합성된 고주파 신호 (길이 gap_length)
    """
    print(f"\n=== Random Phase Synthesis ===")
    print(f"Reference length: {len(reference)}")
    print(f"Gap length: {gap_length}")

    if seed is not None:
        np.random.seed(seed)

    # 1. Reference FFT
    ref_fft = fft(reference)
    magnitude = np.abs(ref_fft)  # Magnitude spectrum
    freqs = fftfreq(len(reference))

    print(f"\nMagnitude spectrum:")
    print(f"  Mean: {np.mean(magnitude):.4f}")
    print(f"  Std: {np.std(magnitude):.4f}")
    print(f"  Max: {np.max(magnitude):.4f}")

    # 2. Random Phase 생성
    # Hermitian symmetry 유지 (실수 신호 생성 위해)
    n = len(reference)
    n_half = n // 2 + 1

    # Positive frequencies: Random phase
    random_phase_pos = np.random.uniform(0, 2*np.pi, n_half)

    # DC component는 phase 0
    random_phase_pos[0] = 0

    # Nyquist frequency도 phase 0 (짝수 길이인 경우)
    if n % 2 == 0:
        random_phase_pos[-1] = 0

    # Negative frequencies: Hermitian symmetry
    random_phase_neg = -random_phase_pos[1:-1][::-1] if n % 2 == 0 else -random_phase_pos[1:][::-1]

    # 전체 phase
    random_phase = np.concatenate([
        random_phase_pos,
        random_phase_neg
    ])

    print(f"\nRandom phase:")
    print(f"  Positive freqs: {len(random_phase_pos)}")
    print(f"  Negative freqs: {len(random_phase_neg)}")
    print(f"  Total: {len(random_phase)}")

    # 3. Magnitude 보존 + Random Phase
    synthesized_fft = magnitude * np.exp(1j * random_phase)

    # 4. IFFT로 시간 영역 신호 생성
    synthesized_signal = np.real(ifft(synthesized_fft))

    print(f"\nSynthesized signal:")
    print(f"  Length: {len(synthesized_signal)}")
    print(f"  Mean: {np.mean(synthesized_signal):.4f}")
    print(f"  Std: {np.std(synthesized_signal):.4f}")
    print(f"  Min/Max: [{np.min(synthesized_signal):.4f}, {np.max(synthesized_signal):.4f}]")

    # 5. Gap 길이만큼 추출
    if len(synthesized_signal) >= gap_length:
        # 중간 부분 추출 (edge effect 회피)
        start_idx = (len(synthesized_signal) - gap_length) // 2
        gap = synthesized_signal[start_idx:start_idx + gap_length]
    else:
        # 부족한 경우 반복
        repeats = gap_length // len(synthesized_signal) + 1
        extended = np.tile(synthesized_signal, repeats)
        gap = extended[:gap_length]

    print(f"\nExtracted gap:")
    print(f"  Length: {len(gap)}")
    print(f"  Mean: {np.mean(gap):.4f}")
    print(f"  Std: {np.std(gap):.4f}")

    # 6. PSD 검증
    if preserve_psd:
        ref_freqs, ref_psd = compute_psd(reference)
        gap_freqs, gap_psd = compute_psd(gap)

        # PSD similarity (상관계수)
        if len(ref_psd) == len(gap_psd):
            psd_corr = np.corrcoef(ref_psd, gap_psd)[0, 1]
            print(f"\n✓ PSD correlation: {psd_corr:.4f}")
        else:
            print(f"\n⚠ PSD length mismatch: {len(ref_psd)} vs {len(gap_psd)}")

    print(f"\n✓ Random phase synthesis complete")

    return gap


def improved_random_phase_synthesis(reference: np.ndarray,
                                    gap_length: int,
                                    seed: int = None) -> np.ndarray:
    """
    개선된 Random Phase 합성

    원본 길이와 gap 길이가 다른 경우를 더 잘 처리
    """
    if seed is not None:
        np.random.seed(seed)

    # Gap 길이에 맞춰 reference 리샘플링
    if len(reference) != gap_length:
        from scipy.interpolate import interp1d
        x_old = np.linspace(0, 1, len(reference))
        x_new = np.linspace(0, 1, gap_length)
        interpolator = interp1d(x_old, reference, kind='cubic')
        reference_resampled = interpolator(x_new)
    else:
        reference_resampled = reference.copy()

    # FFT
    ref_fft = fft(reference_resampled)
    magnitude = np.abs(ref_fft)

    # Random phase (Hermitian symmetry)
    n = len(reference_resampled)
    random_phase = np.zeros(n)

    # Positive frequencies
    n_half = n // 2 + 1
    random_phase[:n_half] = np.random.uniform(0, 2*np.pi, n_half)
    random_phase[0] = 0  # DC component
    if n % 2 == 0:
        random_phase[n//2] = 0  # Nyquist

    # Negative frequencies (Hermitian)
    for i in range(n_half, n):
        random_phase[i] = -random_phase[n - i]

    # Synthesis
    synthesized_fft = magnitude * np.exp(1j * random_phase)
    synthesized_signal = np.real(ifft(synthesized_fft))

    return synthesized_signal


def test_random_phase_synthesis():
    """
    Random Phase 합성 테스트
    """
    print("="*70)
    print("Testing Random Phase Synthesis")
    print("="*70)

    # 테스트 데이터 생성 (고주파 노이즈)
    np.random.seed(42)
    n = 1000
    t = np.arange(n)

    # 고주파 신호: 여러 주파수 성분의 합
    signal = (
        np.sin(2*np.pi*0.1*t) +
        0.5*np.sin(2*np.pi*0.15*t) +
        0.3*np.sin(2*np.pi*0.25*t) +
        0.2*np.random.randn(n)  # 노이즈
    )

    # Gap 생성
    gap_start = 400
    gap_end = 600
    gap_length = gap_end - gap_start

    # Gap 전후 reference
    reference = np.concatenate([
        signal[gap_start-150:gap_start],
        signal[gap_end:gap_end+150]
    ])

    gap_true = signal[gap_start:gap_end]

    # Random Phase 합성
    gap_pred = random_phase_synthesis(
        reference,
        gap_length,
        preserve_psd=True,
        seed=42
    )

    # 통계 비교
    print("\n" + "="*70)
    print("Results")
    print("="*70)
    print(f"Gap true - Mean: {np.mean(gap_true):.4f}, Std: {np.std(gap_true):.4f}")
    print(f"Gap pred - Mean: {np.mean(gap_pred):.4f}, Std: {np.std(gap_pred):.4f}")

    mean_diff = abs(np.mean(gap_true) - np.mean(gap_pred))
    std_ratio = np.std(gap_pred) / np.std(gap_true)

    print(f"\nMean difference: {mean_diff:.4f}")
    print(f"Std ratio: {std_ratio:.4f}")

    # PSD 비교
    ref_freqs, ref_psd = compute_psd(gap_true)
    gap_freqs, gap_psd = compute_psd(gap_pred)

    # 시각화
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(3, 1, figsize=(12, 10))

        # 전체 시계열
        ax1 = axes[0]
        ax1.plot(signal, 'k-', alpha=0.3, label='Original')
        ax1.axvline(gap_start, color='red', linestyle='--', alpha=0.5)
        ax1.axvline(gap_end, color='red', linestyle='--', alpha=0.5)
        ax1.plot(range(gap_start, gap_end), gap_pred, 'b-', linewidth=2, label='Random Phase Synthesis')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Value')
        ax1.set_title('Random Phase Synthesis Test')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Gap 확대
        ax2 = axes[1]
        ax2.plot(gap_true, 'k-', alpha=0.7, label='True (removed)', linewidth=1.5)
        ax2.plot(gap_pred, 'b-', linewidth=2, label='Random Phase Synthesis', alpha=0.7)
        ax2.set_xlabel('Gap Index')
        ax2.set_ylabel('Value')
        ax2.set_title('Gap Region Comparison')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # PSD 비교
        ax3 = axes[2]
        ax3.semilogy(ref_freqs, ref_psd, 'k-', alpha=0.7, label='True PSD', linewidth=2)
        ax3.semilogy(gap_freqs, gap_psd, 'b--', label='Synthesized PSD', linewidth=2)
        ax3.set_xlabel('Frequency')
        ax3.set_ylabel('PSD')
        ax3.set_title('Power Spectral Density Comparison')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('results/random_phase_synthesis_test.png', dpi=150)
        print("\n✓ Saved: results/random_phase_synthesis_test.png")
        plt.close()

    except Exception as e:
        print(f"\n⚠ Visualization skipped: {e}")

    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)


if __name__ == "__main__":
    test_random_phase_synthesis()
