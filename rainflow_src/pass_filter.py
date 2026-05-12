"""
Apply Pass Filters 모듈
- V자 최저점을 기준으로 저대역/고대역 성분 분리하는 함수
"""

import numpy as np
from scipy import signal
from typing import Tuple
import warnings

warnings.filterwarnings("ignore")

# common.config에서 통합된 V자 최저점 값 사용
from common.config import V_SHAPED_MIN_FREQ

# ============================================================================
# V자 최저점 기준 필터 설정 (find_freq.py 분석 결과)
# ============================================================================

# 0520 중구역 V자 최저점을 기준으로 통합
VALLEY_PERIOD = V_SHAPED_MIN_FREQ  # 분 (config에서 가져옴)
VALLEY_FREQ = 1 / (VALLEY_PERIOD * 60)  # Hz (주기로부터 계산)

# 필터 설계 파라미터 (연속적인 필터로 신호 손실 방지)
LOW_PASS_MARGIN = 1.0  # V자 최저점의 100%를 Low Pass 차단 주파수로 사용
HIGH_PASS_MARGIN = 1.0  # V자 최저점의 100%를 High Pass 차단 주파수로 사용


def pass_filter(
    data: np.ndarray, sampling_rate: float, file_path: str
) -> Tuple[np.ndarray, np.ndarray]:
    """
    V자 최저점을 기준으로 저대역/고대역 성분 분리

    분석 결과:
    - 저대역 성분: V자 최저점 이하 주파수 (Low Pass Filter)
    - 고대역 성분: V자 최저점 이상 주파수 (High Pass Filter)

    Returns:
        Tuple[np.ndarray, np.ndarray]: (low_pass_filtered, high_pass_filtered)
    """
    print("V자 최저점 기준 Pass Filter 적용 중...")

    # NaN 값 검증만 수행 (실제 보간은 호출하는 쪽에서 처리)
    nan_count = np.sum(np.isnan(data))
    if nan_count > 0:
        print(f"경고: 입력 데이터에 {nan_count}개의 NaN 값이 있습니다.")
        print("NaN 값은 사전에 처리되어야 합니다.")
        raise ValueError(
            f"입력 데이터에 {nan_count}개의 NaN 값이 포함되어 있습니다. 필터 적용 전에 NaN 값을 처리해주세요."
        )

    nyquist = sampling_rate / 2

    # 통합된 V자 최저점 주파수 사용
    print(f"V자 최저점: {VALLEY_FREQ:.6f} Hz ({VALLEY_PERIOD}분 주기)")

    # V자 최저점 기준 차단 주파수 계산
    low_pass_cutoff = VALLEY_FREQ * LOW_PASS_MARGIN  # V자 최저점의 100%
    high_pass_cutoff = VALLEY_FREQ * HIGH_PASS_MARGIN  # V자 최저점의 100%

    print("필터 차단 주파수:")
    print(
        f"  저대역 (Low Pass): {low_pass_cutoff:.6f} Hz ({1/low_pass_cutoff/60:.1f}분)"
    )
    print(
        f"  고대역 (High Pass): {high_pass_cutoff:.6f} Hz ({1/high_pass_cutoff/60:.1f}분)"
    )

    # Nyquist 주파수 제한 확인
    if low_pass_cutoff / nyquist >= 0.99:
        low_pass_cutoff = nyquist * 0.95
        print(f"  저대역 차단 주파수 조정: {low_pass_cutoff:.6f} Hz (Nyquist 제한)")

    if high_pass_cutoff / nyquist >= 0.99:
        high_pass_cutoff = nyquist * 0.95
        print(f"  고대역 차단 주파수 조정: {high_pass_cutoff:.6f} Hz (Nyquist 제한)")

    # 저대역 성분 추출 (Low Pass Filter)
    # V자 최저점 이하의 모든 주파수 성분 통과
    b_low, a_low = signal.butter(4, low_pass_cutoff / nyquist, btype="low")
    low_pass_filtered = signal.filtfilt(b_low, a_low, data)

    # 고대역 성분 추출 (High Pass Filter)
    # V자 최저점 이상의 모든 주파수 성분 통과
    b_high, a_high = signal.butter(4, high_pass_cutoff / nyquist, btype="high")
    high_pass_filtered = signal.filtfilt(b_high, a_high, data)

    print("필터 적용 완료:")
    print(f"  원본 신호 표준편차: {np.std(data):.4f}")
    print(f"  저대역 성분 표준편차: {np.std(low_pass_filtered):.4f}")
    print(f"  고대역 성분 표준편차: {np.std(high_pass_filtered):.4f}")

    return low_pass_filtered, high_pass_filtered
