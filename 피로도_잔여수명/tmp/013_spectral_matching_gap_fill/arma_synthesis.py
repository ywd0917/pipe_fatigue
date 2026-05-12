#!/usr/bin/env python3
"""
ARMA 기반 저주파 스펙트럴 합성

저주파 성분 (ACF 0.9997)은 예측 가능하므로
ARMA 모델을 사용하여 gap 전후를 부드럽게 연결
"""

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import acf, pacf
from typing import Tuple


def auto_arima_order(data: np.ndarray, max_p: int = 10, max_q: int = 10) -> Tuple[int, int]:
    """
    PACF/ACF 분석으로 ARMA 차수 자동 결정

    Args:
        data: 시계열 데이터
        max_p: 최대 AR 차수
        max_q: 최대 MA 차수

    Returns:
        (p, q): 최적 ARMA 차수
    """
    # PACF로 AR 차수 추정
    pacf_vals = pacf(data, nlags=max_p, method='ywm')
    threshold = 1.96 / np.sqrt(len(data))

    # 첫 번째 유의하지 않은 lag 찾기
    p = 1
    for i in range(1, len(pacf_vals)):
        if abs(pacf_vals[i]) < threshold:
            p = max(1, i - 1)
            break
    p = min(p, max_p)

    # ACF로 MA 차수 추정
    acf_vals = acf(data, nlags=max_q, fft=True)
    q = 1
    for i in range(1, len(acf_vals)):
        if abs(acf_vals[i]) < threshold:
            q = max(1, i - 1)
            break
    q = min(q, max_q)

    return p, q


def fit_arma_model(data: np.ndarray, order: Tuple[int, int] = None):
    """
    ARMA 모델 학습

    Args:
        data: 시계열 데이터
        order: (p, q) ARMA 차수. None이면 자동 결정

    Returns:
        Fitted ARIMA model
    """
    if order is None:
        p, q = auto_arima_order(data)
    else:
        p, q = order

    print(f"  ARMA order: ({p}, {q})")

    # ARIMA(p, 0, q) = ARMA(p, q)
    model = ARIMA(data, order=(p, 0, q))
    fitted = model.fit()

    return fitted


def arma_forward_synthesis(before: np.ndarray,
                           gap_length: int,
                           order: Tuple[int, int] = None) -> np.ndarray:
    """
    Forward ARMA: gap 이전 데이터로 gap 초반 예측

    Args:
        before: Gap 이전 데이터
        gap_length: Gap 길이
        order: ARMA 차수

    Returns:
        Forward prediction
    """
    # ARMA 모델 학습
    model = fit_arma_model(before, order)

    # Gap 전반부 예측
    forecast_length = gap_length // 2 + gap_length % 2  # 절반 + 나머지
    forecast = model.forecast(steps=forecast_length)

    return np.array(forecast)


def arma_backward_synthesis(after: np.ndarray,
                            gap_length: int,
                            order: Tuple[int, int] = None) -> np.ndarray:
    """
    Backward ARMA: gap 이후 데이터를 역방향으로 학습하여 gap 후반 예측

    Args:
        after: Gap 이후 데이터
        gap_length: Gap 길이
        order: ARMA 차수

    Returns:
        Backward prediction (시간 순서대로)
    """
    # 데이터 역방향 정렬
    after_reversed = after[::-1]

    # ARMA 모델 학습 (역방향)
    model = fit_arma_model(after_reversed, order)

    # Gap 후반부 예측 (역방향)
    forecast_length = gap_length // 2
    forecast_reversed = model.forecast(steps=forecast_length)

    # 다시 정방향으로 정렬
    forecast = forecast_reversed[::-1]

    return np.array(forecast)


def weighted_blend(forward: np.ndarray, backward: np.ndarray) -> np.ndarray:
    """
    Forward/Backward 예측을 가중 평균으로 부드럽게 연결

    가중치는 gap 중간에서 0.5, 양 끝으로 갈수록 0 또는 1

    Args:
        forward: Forward prediction (gap 전반부)
        backward: Backward prediction (gap 후반부)

    Returns:
        Blended gap filling
    """
    len_forward = len(forward)
    len_backward = len(backward)
    total_length = len_forward + len_backward

    # 가중치 생성 (linear blending)
    # Forward weight: 1.0 → 0.0
    # Backward weight: 0.0 → 1.0
    weights_forward = np.linspace(1.0, 0.0, len_forward)
    weights_backward = np.linspace(0.0, 1.0, len_backward)

    # Forward part (100% → blend)
    forward_blended = forward * weights_forward

    # Backward part (blend → 100%)
    backward_blended = backward * weights_backward

    # Overlap 처리
    if len_forward > 0 and len_backward > 0:
        # 중간 부분이 겹치는 경우 평균
        overlap_length = min(len_forward, len_backward)
        overlap_forward = forward_blended[-overlap_length:]
        overlap_backward = backward_blended[:overlap_length]

        # Blending
        blended_overlap = overlap_forward + overlap_backward

        # 결합
        if len_forward > overlap_length:
            result = np.concatenate([
                forward_blended[:-overlap_length],
                blended_overlap,
                backward_blended[overlap_length:]
            ])
        else:
            result = np.concatenate([
                blended_overlap,
                backward_blended[overlap_length:]
            ])
    else:
        # Overlap 없는 경우 단순 연결
        result = np.concatenate([forward_blended, backward_blended])

    return result


def arma_spectral_synthesis(before: np.ndarray,
                            after: np.ndarray,
                            gap_length: int,
                            order: Tuple[int, int] = None) -> np.ndarray:
    """
    ARMA 기반 저주파 스펙트럴 합성

    Gap 전후 데이터로 ARMA 모델을 학습하여
    양방향에서 예측한 후 부드럽게 연결

    Args:
        before: Gap 이전 데이터 (최소 300개 권장)
        after: Gap 이후 데이터 (최소 300개 권장)
        gap_length: Gap 길이
        order: ARMA 차수 (None이면 자동 결정)

    Returns:
        Gap filling 결과 (길이 gap_length)
    """
    print(f"\n=== ARMA Spectral Synthesis ===")
    print(f"Before length: {len(before)}")
    print(f"After length: {len(after)}")
    print(f"Gap length: {gap_length}")

    # 1. Forward ARMA (gap 전반부)
    print("\n1. Forward ARMA prediction...")
    forward = arma_forward_synthesis(before, gap_length, order)
    print(f"  Forward length: {len(forward)}")

    # 2. Backward ARMA (gap 후반부)
    print("\n2. Backward ARMA prediction...")
    backward = arma_backward_synthesis(after, gap_length, order)
    print(f"  Backward length: {len(backward)}")

    # 3. Weighted blending
    print("\n3. Weighted blending...")
    gap_filled = weighted_blend(forward, backward)
    print(f"  Blended length: {len(gap_filled)}")

    # 길이 검증
    if len(gap_filled) != gap_length:
        # 길이 조정 (interpolation)
        from scipy.interpolate import interp1d
        x_old = np.linspace(0, 1, len(gap_filled))
        x_new = np.linspace(0, 1, gap_length)
        interpolator = interp1d(x_old, gap_filled, kind='cubic')
        gap_filled = interpolator(x_new)
        print(f"  Adjusted to gap_length: {len(gap_filled)}")

    print(f"\n✓ ARMA synthesis complete")
    print(f"  Mean: {np.mean(gap_filled):.4f}")
    print(f"  Std: {np.std(gap_filled):.4f}")
    print(f"  Min/Max: [{np.min(gap_filled):.4f}, {np.max(gap_filled):.4f}]")

    return gap_filled


def test_arma_synthesis():
    """
    ARMA 합성 테스트
    """
    print("="*70)
    print("Testing ARMA Spectral Synthesis")
    print("="*70)

    # 테스트 데이터 생성 (AR(2) 프로세스)
    np.random.seed(42)
    n = 1000
    ar_params = np.array([0.75, -0.25])
    ma_params = np.array([0.65, 0.35])

    # ARMA(2,2) 생성
    from statsmodels.tsa.arima_process import ArmaProcess
    ar = np.r_[1, -ar_params]
    ma = np.r_[1, ma_params]
    arma_process = ArmaProcess(ar, ma)
    data = arma_process.generate_sample(n)

    # Gap 생성
    gap_start = 400
    gap_end = 600
    gap_length = gap_end - gap_start

    before = data[:gap_start]
    after = data[gap_end:]
    gap_true = data[gap_start:gap_end]

    # ARMA 합성
    gap_pred = arma_spectral_synthesis(
        before[-300:],  # 마지막 300개
        after[:300],     # 처음 300개
        gap_length
    )

    # 결과 비교
    print("\n" + "="*70)
    print("Results")
    print("="*70)
    print(f"Gap true - Mean: {np.mean(gap_true):.4f}, Std: {np.std(gap_true):.4f}")
    print(f"Gap pred - Mean: {np.mean(gap_pred):.4f}, Std: {np.std(gap_pred):.4f}")

    # 통계 비교
    mean_diff = abs(np.mean(gap_true) - np.mean(gap_pred))
    std_ratio = np.std(gap_pred) / np.std(gap_true)

    print(f"\nMean difference: {mean_diff:.4f}")
    print(f"Std ratio: {std_ratio:.4f}")

    # 시각화
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        # 전체 시계열
        ax1 = axes[0]
        ax1.plot(data, 'k-', alpha=0.3, label='Original')
        ax1.axvline(gap_start, color='red', linestyle='--', alpha=0.5)
        ax1.axvline(gap_end, color='red', linestyle='--', alpha=0.5)
        ax1.plot(range(gap_start, gap_end), gap_pred, 'b-', linewidth=2, label='ARMA Synthesis')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Value')
        ax1.set_title('ARMA Spectral Synthesis Test')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Gap 확대
        ax2 = axes[1]
        ax2.plot(gap_true, 'k-', alpha=0.7, label='True (removed)')
        ax2.plot(gap_pred, 'b-', linewidth=2, label='ARMA Synthesis')
        ax2.set_xlabel('Gap Index')
        ax2.set_ylabel('Value')
        ax2.set_title('Gap Region Comparison')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('results/arma_synthesis_test.png', dpi=150)
        print("\n✓ Saved: results/arma_synthesis_test.png")
        plt.close()

    except Exception as e:
        print(f"\n⚠ Visualization skipped: {e}")

    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)


if __name__ == "__main__":
    test_arma_synthesis()
