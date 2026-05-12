#!/usr/bin/env python3
"""
Edge Smoothing for Gap Filling

Gap 경계에서 불연속성 제거 및 부드러운 전환 생성
Kaiser-Bessel window 사용
"""

import numpy as np
from scipy.signal.windows import kaiser, get_window
from typing import Optional


def edge_smoothing(gap: np.ndarray,
                   before: np.ndarray,
                   after: np.ndarray,
                   window_size: int = 60,
                   window_type: str = 'kaiser',
                   beta: float = 8.6) -> np.ndarray:
    """
    Gap 경계를 부드럽게 연결하여 불연속 제거

    Args:
        gap: Gap 구간 데이터
        before: Gap 이전 데이터 (최소 window_size 이상)
        after: Gap 이후 데이터 (최소 window_size 이상)
        window_size: Smoothing window 크기 (기본값: 60분)
        window_type: Window 종류 ('kaiser', 'hann', 'hamming', 'blackman')
        beta: Kaiser window beta 파라미터 (기본값: 8.6, 약 60dB attenuation)

    Returns:
        Edge smoothing이 적용된 gap 데이터
    """
    print(f"\n=== Edge Smoothing ===")
    print(f"Gap length: {len(gap)}")
    print(f"Before length: {len(before)}")
    print(f"After length: {len(after)}")
    print(f"Window size: {window_size}")
    print(f"Window type: {window_type}")

    # Input validation
    if len(before) < window_size:
        raise ValueError(f"Before data length ({len(before)}) < window_size ({window_size})")
    if len(after) < window_size:
        raise ValueError(f"After data length ({len(after)}) < window_size ({window_size})")
    if len(gap) < 2 * window_size:
        # Gap이 window 2개보다 작으면 window_size 조정
        window_size = max(1, len(gap) // 4)
        print(f"⚠ Gap too short, adjusted window_size to {window_size}")

    # Copy gap to avoid modifying original
    gap_smoothed = gap.copy()

    # 1. Left edge smoothing (gap 시작 부분)
    left_edge = smooth_left_edge(
        gap_smoothed[:window_size],
        before[-window_size:],
        window_size,
        window_type,
        beta
    )
    gap_smoothed[:window_size] = left_edge

    # 2. Right edge smoothing (gap 끝 부분)
    right_edge = smooth_right_edge(
        gap_smoothed[-window_size:],
        after[:window_size],
        window_size,
        window_type,
        beta
    )
    gap_smoothed[-window_size:] = right_edge

    print(f"\n✓ Edge smoothing complete")
    print(f"  Left edge adjusted: {window_size} points")
    print(f"  Right edge adjusted: {window_size} points")

    return gap_smoothed


def smooth_left_edge(gap_left: np.ndarray,
                     before_right: np.ndarray,
                     window_size: int,
                     window_type: str = 'kaiser',
                     beta: float = 8.6) -> np.ndarray:
    """
    Gap 왼쪽 경계 smoothing

    Before 데이터의 마지막 부분과 gap 초반 부분을 부드럽게 연결

    Args:
        gap_left: Gap의 왼쪽 window_size 개 데이터
        before_right: Before의 마지막 window_size 개 데이터
        window_size: Window 크기
        window_type: Window 종류
        beta: Kaiser window beta

    Returns:
        Smoothed left edge
    """
    # Window 생성 (0 → 1로 증가)
    if window_type == 'kaiser':
        window = kaiser(window_size, beta)
    else:
        window = get_window(window_type, window_size)

    # Normalize window to [0, 1]
    window = (window - window.min()) / (window.max() - window.min())

    # Weighted blending
    # before_weight: 1.0 → 0.0
    # gap_weight: 0.0 → 1.0
    before_weight = 1.0 - window
    gap_weight = window

    smoothed = before_right * before_weight + gap_left * gap_weight

    return smoothed


def smooth_right_edge(gap_right: np.ndarray,
                      after_left: np.ndarray,
                      window_size: int,
                      window_type: str = 'kaiser',
                      beta: float = 8.6) -> np.ndarray:
    """
    Gap 오른쪽 경계 smoothing

    Gap 끝 부분과 after 데이터의 초반 부분을 부드럽게 연결

    Args:
        gap_right: Gap의 오른쪽 window_size 개 데이터
        after_left: After의 처음 window_size 개 데이터
        window_size: Window 크기
        window_type: Window 종류
        beta: Kaiser window beta

    Returns:
        Smoothed right edge
    """
    # Window 생성 (1 → 0로 감소)
    if window_type == 'kaiser':
        window = kaiser(window_size, beta)
    else:
        window = get_window(window_type, window_size)

    # Normalize and reverse
    window = (window - window.min()) / (window.max() - window.min())
    window = window[::-1]  # Reverse for right edge

    # Weighted blending
    # gap_weight: 1.0 → 0.0
    # after_weight: 0.0 → 1.0
    gap_weight = 1.0 - window
    after_weight = window

    smoothed = gap_right * gap_weight + after_left * after_weight

    return smoothed


def adaptive_edge_smoothing(gap: np.ndarray,
                            before: np.ndarray,
                            after: np.ndarray,
                            max_window_size: int = 120) -> np.ndarray:
    """
    적응형 Edge Smoothing

    Gap 길이에 따라 window_size 자동 조정

    Args:
        gap: Gap 구간 데이터
        before: Gap 이전 데이터
        after: Gap 이후 데이터
        max_window_size: 최대 window 크기

    Returns:
        Edge smoothing이 적용된 gap 데이터
    """
    # Gap 길이에 비례한 window_size
    # Gap의 10% 또는 max_window_size 중 작은 값
    window_size = min(max_window_size, max(10, len(gap) // 10))

    # Before/after 길이 제약
    window_size = min(window_size, len(before), len(after))

    print(f"\n=== Adaptive Edge Smoothing ===")
    print(f"Gap length: {len(gap)}")
    print(f"Adaptive window_size: {window_size}")

    return edge_smoothing(gap, before, after, window_size)


def test_edge_smoothing():
    """
    Edge Smoothing 테스트
    """
    print("="*70)
    print("Testing Edge Smoothing")
    print("="*70)

    # 테스트 데이터 생성
    np.random.seed(42)
    n = 1000

    # Before: Smooth trend + noise
    t_before = np.linspace(0, 10, 400)
    before = 5 + 2*np.sin(t_before) + 0.2*np.random.randn(400)

    # After: Smooth trend + noise (연속)
    t_after = np.linspace(10, 20, 400)
    after = 5 + 2*np.sin(t_after) + 0.2*np.random.randn(400)

    # Gap: 불연속적인 합성 데이터
    gap_length = 200
    t_gap = np.linspace(10, 12, gap_length)
    gap_raw = 6 + 1.5*np.sin(t_gap*2) + 0.5*np.random.randn(gap_length)

    # Gap 시작/끝 점프 추가 (의도적 불연속)
    gap_raw = gap_raw + 1.5  # 위로 shift

    print(f"\nRaw gap discontinuity:")
    print(f"  Before end: {before[-1]:.4f}")
    print(f"  Gap start: {gap_raw[0]:.4f}")
    print(f"  Jump: {abs(gap_raw[0] - before[-1]):.4f}")
    print(f"  Gap end: {gap_raw[-1]:.4f}")
    print(f"  After start: {after[0]:.4f}")
    print(f"  Jump: {abs(after[0] - gap_raw[-1]):.4f}")

    # Edge Smoothing 적용
    gap_smoothed = edge_smoothing(
        gap_raw,
        before,
        after,
        window_size=60,
        window_type='kaiser',
        beta=8.6
    )

    print(f"\nSmoothed gap:")
    print(f"  Before end: {before[-1]:.4f}")
    print(f"  Gap start: {gap_smoothed[0]:.4f}")
    print(f"  Jump: {abs(gap_smoothed[0] - before[-1]):.4f}")
    print(f"  Gap end: {gap_smoothed[-1]:.4f}")
    print(f"  After start: {after[0]:.4f}")
    print(f"  Jump: {abs(after[0] - gap_smoothed[-1]):.4f}")

    # Adaptive smoothing 테스트
    gap_adaptive = adaptive_edge_smoothing(gap_raw, before, after)

    # 시각화
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(3, 1, figsize=(14, 10))

        # 전체 시계열 (Raw gap)
        ax1 = axes[0]
        full_data_raw = np.concatenate([before, gap_raw, after])
        ax1.plot(full_data_raw, 'k-', alpha=0.3, linewidth=0.5, label='Before/After')
        ax1.plot(range(len(before), len(before) + len(gap_raw)),
                 gap_raw, 'r-', linewidth=2, label='Gap (Raw)', alpha=0.7)
        ax1.axvline(len(before), color='red', linestyle='--', alpha=0.5, label='Gap boundary')
        ax1.axvline(len(before) + len(gap_raw), color='red', linestyle='--', alpha=0.5)
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Value')
        ax1.set_title('Before Edge Smoothing (Discontinuous)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 전체 시계열 (Smoothed gap)
        ax2 = axes[1]
        full_data_smoothed = np.concatenate([before, gap_smoothed, after])
        ax2.plot(full_data_smoothed, 'k-', alpha=0.3, linewidth=0.5, label='Before/After')
        ax2.plot(range(len(before), len(before) + len(gap_smoothed)),
                 gap_smoothed, 'b-', linewidth=2, label='Gap (Smoothed)', alpha=0.7)
        ax2.axvline(len(before), color='blue', linestyle='--', alpha=0.5, label='Gap boundary')
        ax2.axvline(len(before) + len(gap_smoothed), color='blue', linestyle='--', alpha=0.5)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Value')
        ax2.set_title('After Edge Smoothing (Continuous)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 경계 부분 확대
        ax3 = axes[2]
        window_view = 100
        left_start = len(before) - window_view
        left_end = len(before) + window_view

        # Raw
        ax3.plot(range(left_start, left_end),
                 full_data_raw[left_start:left_end],
                 'r-', linewidth=2, label='Raw', alpha=0.7)
        # Smoothed
        ax3.plot(range(left_start, left_end),
                 full_data_smoothed[left_start:left_end],
                 'b-', linewidth=2, label='Smoothed', alpha=0.7)
        ax3.axvline(len(before), color='gray', linestyle='--', alpha=0.5)
        ax3.axvline(len(before) + len(gap_smoothed), color='gray', linestyle='--', alpha=0.5)
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Value')
        ax3.set_title('Left Edge Zoom-in (Before/Gap boundary)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('results/edge_smoothing_test.png', dpi=150)
        print("\n✓ Saved: results/edge_smoothing_test.png")
        plt.close()

    except Exception as e:
        print(f"\n⚠ Visualization skipped: {e}")

    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)


if __name__ == "__main__":
    test_edge_smoothing()
