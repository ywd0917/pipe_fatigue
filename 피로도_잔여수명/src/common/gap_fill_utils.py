"""
Gap filling utility functions for pressure data.

이 모듈은 압력 데이터의 결측 구간(gap)을 채우기 위한 다양한 방법을 제공합니다.
- XGBoost: 1시간 이내의 짧은 gap용
- Spectral (ARMA + Random Phase): 1시간 초과의 긴 gap용

Project 014에서 검증된 방법론을 기반으로 구현되었습니다.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, List, Optional, Any
from scipy import signal
from scipy.interpolate import interp1d
from statsmodels.tsa.arima.model import ARIMA
import warnings
import logging

logger = logging.getLogger(__name__)

# XGBoost import - optional dependency
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("XGBoost not installed. XGBoost interpolation will not be available.")

# ==============================================================================
# Gap Detection
# ==============================================================================

def detect_gaps(data: np.ndarray, timestamps: pd.DatetimeIndex = None,
                min_gap_size: int = 1) -> List[Dict[str, Any]]:
    """
    결측 구간 탐지.

    Parameters
    ----------
    data : np.ndarray
        압력 데이터
    timestamps : pd.DatetimeIndex, optional
        타임스탬프
    min_gap_size : int
        최소 gap 크기 (포인트 수)

    Returns
    -------
    List[Dict]
        gap 정보 리스트. 각 dict는:
        - start_idx: gap 시작 인덱스
        - end_idx: gap 종료 인덱스 (exclusive)
        - length: gap 길이 (포인트 수)
        - length_hours: gap 길이 (시간 단위, timestamps가 있을 경우)
    """
    gaps = []

    # NaN 위치 찾기
    nan_mask = np.isnan(data)

    if not nan_mask.any():
        return gaps

    # 연속된 NaN 그룹 찾기
    diff = np.diff(np.concatenate(([False], nan_mask, [False])).astype(int))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    for start, end in zip(starts, ends):
        length = end - start
        if length >= min_gap_size:
            gap_info = {
                'start_idx': start,
                'end_idx': end,
                'length': length
            }

            # 시간 정보가 있으면 시간 단위 길이 계산
            if timestamps is not None:
                # 5분 간격 가정 (실제 간격 계산 가능)
                gap_info['length_hours'] = length * 5 / 60  # 5분 * length / 60분
                gap_info['start_time'] = timestamps[start] if start < len(timestamps) else None
                gap_info['end_time'] = timestamps[end-1] if end-1 < len(timestamps) else None

            gaps.append(gap_info)

    return gaps

# ==============================================================================
# Frequency Separation (Butterworth Filter)
# ==============================================================================

def butterworth_frequency_separation(data: np.ndarray,
                                    v_valley_minutes: float = 553.5,
                                    sampling_minutes: float = 5.0,
                                    filter_order: int = 4) -> Tuple[np.ndarray, np.ndarray]:
    """
    Butterworth 필터로 저주파/고주파 성분 분리.

    Parameters
    ----------
    data : np.ndarray
        원본 신호
    v_valley_minutes : float
        V-valley 주기 (분 단위), main51과 동일한 553.5분 사용
    sampling_minutes : float
        샘플링 간격 (분 단위), 기본 5분
    filter_order : int
        Butterworth 필터 차수

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (저주파 성분, 고주파 성분)
    """
    # Nyquist 주파수 계산
    nyquist_freq = 1 / (2 * sampling_minutes)
    cutoff_freq = 1 / v_valley_minutes
    normalized_cutoff = cutoff_freq / nyquist_freq

    # 필터 설계
    b, a = signal.butter(filter_order, normalized_cutoff, btype='low')

    # NaN 처리를 위한 마스킹
    valid_mask = ~np.isnan(data)
    valid_data = data[valid_mask]

    if len(valid_data) < filter_order * 3:
        # 데이터가 너무 짧으면 단순 평균으로 대체
        low_freq = np.full_like(data, np.nanmean(data))
        high_freq = data - low_freq
        return low_freq, high_freq

    # 저주파 성분 추출
    low_freq = np.full_like(data, np.nan)
    low_freq[valid_mask] = signal.filtfilt(b, a, valid_data)

    # 고주파 성분 = 원본 - 저주파
    high_freq = data - low_freq

    return low_freq, high_freq

# ==============================================================================
# XGBoost Interpolation (for gaps ≤ 1 hour)
# ==============================================================================

def xgboost_interpolation(data: np.ndarray, gap_start: int, gap_end: int,
                         lookback: int = 24, lookahead: int = 24,
                         n_estimators: int = 100, max_depth: int = 3,
                         learning_rate: float = 0.1) -> np.ndarray:
    """
    XGBoost를 사용한 단기 gap 보간 (1시간 이내).

    Parameters
    ----------
    data : np.ndarray
        gap이 있는 데이터 (NaN 포함)
    gap_start : int
        gap 시작 인덱스
    gap_end : int
        gap 종료 인덱스 (exclusive)
    lookback : int
        학습에 사용할 이전 데이터 포인트 수
    lookahead : int
        학습에 사용할 이후 데이터 포인트 수
    n_estimators : int
        XGBoost 트리 개수
    max_depth : int
        트리 최대 깊이
    learning_rate : float
        학습률

    Returns
    -------
    np.ndarray
        gap이 채워진 데이터
    """
    if not HAS_XGBOOST:
        logger.warning("XGBoost not available. Using linear interpolation instead.")
        return linear_interpolation(data, gap_start, gap_end)

    filled_data = data.copy()
    gap_length = gap_end - gap_start

    # 학습 데이터 준비
    # gap 주변의 유효한 데이터를 사용
    train_start = max(0, gap_start - lookback - gap_length)
    train_end = min(len(data), gap_end + lookahead + gap_length)

    # Feature 생성: 시계열 lag features
    features = []
    targets = []

    # 유효한 데이터에서 feature 생성
    for i in range(train_start + lookback, train_end):
        if i >= gap_start and i < gap_end:
            continue  # gap 내부는 학습 데이터에서 제외

        if not np.isnan(data[i]):
            # Lag features
            feature_vec = []
            for lag in range(1, min(lookback + 1, i - train_start + 1)):
                if i - lag >= 0:
                    val = data[i - lag]
                    if np.isnan(val):
                        # gap 근처의 NaN은 선형 보간으로 임시 채움
                        val = np.nanmean(data[max(0, i-lag-3):min(len(data), i-lag+4)])
                    feature_vec.append(val if not np.isnan(val) else 0)

            # 시간 특징 추가 (상대 위치)
            feature_vec.append(i / len(data))

            if len(feature_vec) > 0:
                features.append(feature_vec)
                targets.append(data[i])

    if len(features) < 5:
        # 학습 데이터가 부족하면 선형 보간 사용
        logger.warning(f"Insufficient training data for XGBoost. Using linear interpolation.")
        return linear_interpolation(data, gap_start, gap_end)

    # Feature 길이 맞추기
    max_len = max(len(f) for f in features)
    features = [f + [0]*(max_len - len(f)) for f in features]

    X_train = np.array(features)
    y_train = np.array(targets)

    # XGBoost 모델 학습
    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        random_state=42,
        verbosity=0
    )

    model.fit(X_train, y_train)

    # Gap 채우기
    for i in range(gap_start, gap_end):
        # Feature 생성
        feature_vec = []
        for lag in range(1, min(lookback + 1, i + 1)):
            if i - lag >= 0:
                val = filled_data[i - lag]
                feature_vec.append(val if not np.isnan(val) else 0)

        # 시간 특징
        feature_vec.append(i / len(data))

        # 길이 맞추기
        feature_vec = feature_vec + [0]*(max_len - len(feature_vec))

        # 예측
        pred = model.predict(np.array([feature_vec[:max_len]]))[0]
        filled_data[i] = pred

    return filled_data

# ==============================================================================
# Linear Interpolation (Fallback)
# ==============================================================================

def linear_interpolation(data: np.ndarray, gap_start: int, gap_end: int) -> np.ndarray:
    """
    선형 보간 (fallback 방법).

    Parameters
    ----------
    data : np.ndarray
        gap이 있는 데이터
    gap_start : int
        gap 시작 인덱스
    gap_end : int
        gap 종료 인덱스

    Returns
    -------
    np.ndarray
        선형 보간된 데이터
    """
    filled_data = data.copy()

    # gap 전후 유효한 값 찾기
    before_val = np.nan
    after_val = np.nan

    if gap_start > 0:
        before_val = data[gap_start - 1]
    if gap_end < len(data):
        after_val = data[gap_end]

    # 선형 보간
    if not np.isnan(before_val) and not np.isnan(after_val):
        filled_data[gap_start:gap_end] = np.linspace(
            before_val, after_val, gap_end - gap_start + 2
        )[1:-1]
    elif not np.isnan(before_val):
        filled_data[gap_start:gap_end] = before_val
    elif not np.isnan(after_val):
        filled_data[gap_start:gap_end] = after_val
    else:
        filled_data[gap_start:gap_end] = np.nanmean(data)

    return filled_data

# ==============================================================================
# ARMA Synthesis (for low frequency component)
# ==============================================================================

def arma_synthesis(data: np.ndarray, gap_start: int, gap_end: int,
                  arma_order: Tuple[int, int] = (10, 10),
                  max_training_length: int = 10080) -> np.ndarray:
    """
    ARMA 모델을 사용한 저주파 성분 합성.

    Parameters
    ----------
    data : np.ndarray
        저주파 성분 데이터
    gap_start : int
        gap 시작 인덱스
    gap_end : int
        gap 종료 인덱스
    arma_order : Tuple[int, int]
        ARMA(p, q) 차수
    max_training_length : int
        최대 학습 데이터 길이

    Returns
    -------
    np.ndarray
        ARMA로 채워진 데이터
    """
    filled_data = data.copy()
    gap_length = gap_end - gap_start

    # 학습 데이터 준비 (gap 이전 데이터)
    train_end = gap_start
    train_start = max(0, gap_start - max_training_length)
    train_data = data[train_start:train_end]

    # 유효한 데이터만 사용
    valid_mask = ~np.isnan(train_data)
    if valid_mask.sum() < 50:  # 학습 데이터 부족
        logger.warning("Insufficient training data for ARMA. Using linear interpolation.")
        return linear_interpolation(data, gap_start, gap_end)

    train_data = train_data[valid_mask]

    try:
        # ARIMA 모델 학습 (ARMA는 ARIMA(p,0,q))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ARIMA(train_data, order=(arma_order[0], 0, arma_order[1]))
            fitted_model = model.fit()

        # 예측
        forecast = fitted_model.forecast(steps=gap_length)
        filled_data[gap_start:gap_end] = forecast

    except Exception as e:
        logger.warning(f"ARMA fitting failed: {e}. Using linear interpolation.")
        filled_data = linear_interpolation(data, gap_start, gap_end)

    return filled_data

# ==============================================================================
# Random Phase Synthesis (for high frequency component)
# ==============================================================================

def random_phase_synthesis(data: np.ndarray, gap_start: int, gap_end: int,
                          reference_length: int = 10080,
                          random_seed: Optional[int] = None) -> np.ndarray:
    """
    Random Phase IFFT를 사용한 고주파 성분 합성.

    Parameters
    ----------
    data : np.ndarray
        고주파 성분 데이터
    gap_start : int
        gap 시작 인덱스
    gap_end : int
        gap 종료 인덱스
    reference_length : int
        참조 신호 길이 (7일 = 10080 포인트)
    random_seed : int, optional
        재현성을 위한 랜덤 시드

    Returns
    -------
    np.ndarray
        Random Phase로 채워진 데이터
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    filled_data = data.copy()
    gap_length = gap_end - gap_start

    # 참조 데이터 선택 (gap 이전/이후 데이터)
    ref_end = gap_start
    ref_start = max(0, gap_start - reference_length)

    if ref_end - ref_start < 100:  # 참조 데이터 부족
        # gap 이후 데이터도 사용
        ref_start = gap_end
        ref_end = min(len(data), gap_end + reference_length)

    if ref_end - ref_start < 100:  # 여전히 부족
        # 전체 데이터에서 유효한 부분 사용
        valid_data = data[~np.isnan(data)]
        if len(valid_data) < 100:
            # 데이터 부족, 노이즈로 채움
            filled_data[gap_start:gap_end] = np.random.randn(gap_length) * np.nanstd(data)
            return filled_data
        ref_data = valid_data[-min(reference_length, len(valid_data)):]
    else:
        ref_data = data[ref_start:ref_end]
        ref_data = ref_data[~np.isnan(ref_data)]

    # FFT로 스펙트럼 추출
    ref_fft = np.fft.rfft(ref_data)
    ref_magnitude = np.abs(ref_fft)

    # Gap 길이에 맞게 스펙트럼 조정
    if gap_length <= len(ref_magnitude):
        # 스펙트럼 자르기
        gap_magnitude = ref_magnitude[:gap_length // 2 + 1]
    else:
        # 스펙트럼 보간
        old_freqs = np.linspace(0, 1, len(ref_magnitude))
        new_freqs = np.linspace(0, 1, gap_length // 2 + 1)
        interp_func = interp1d(old_freqs, ref_magnitude, kind='linear',
                              fill_value='extrapolate')
        gap_magnitude = interp_func(new_freqs)

    # Random phase 생성
    random_phase = np.random.uniform(-np.pi, np.pi, len(gap_magnitude))
    random_phase[0] = 0  # DC 성분은 실수
    if gap_length % 2 == 0:
        random_phase[-1] = 0  # Nyquist 주파수도 실수

    # 복소 스펙트럼 생성
    gap_fft = gap_magnitude * np.exp(1j * random_phase)

    # IFFT로 시간 도메인 신호 생성
    synthesized = np.fft.irfft(gap_fft, n=gap_length)

    # 평균과 표준편차 맞추기
    ref_mean = np.nanmean(ref_data)
    ref_std = np.nanstd(ref_data)
    synthesized = (synthesized - synthesized.mean()) * ref_std / synthesized.std() + ref_mean

    filled_data[gap_start:gap_end] = synthesized

    return filled_data

# ==============================================================================
# Edge Smoothing
# ==============================================================================

def edge_smoothing(data: np.ndarray, gap_start: int, gap_end: int,
                  window_size: int = 20) -> np.ndarray:
    """
    Gap 경계에서 cosine tapering으로 edge smoothing.

    Parameters
    ----------
    data : np.ndarray
        gap이 채워진 데이터
    gap_start : int
        gap 시작 인덱스
    gap_end : int
        gap 종료 인덱스
    window_size : int
        smoothing window 크기

    Returns
    -------
    np.ndarray
        edge가 smoothing된 데이터
    """
    smoothed_data = data.copy()

    # Left edge smoothing
    if gap_start > 0 and gap_start - window_size >= 0:
        # Cosine taper 생성
        taper = 0.5 * (1 - np.cos(np.pi * np.arange(window_size) / window_size))

        # 원본과 채워진 값 블렌딩
        original_section = data[gap_start - window_size:gap_start]
        filled_section = data[gap_start:gap_start + window_size]

        if not np.any(np.isnan(original_section)) and not np.any(np.isnan(filled_section)):
            # 경계 값 차이
            gap_diff = data[gap_start] - data[gap_start - 1]

            # Smoothing 적용
            for i in range(window_size):
                if gap_start - window_size + i < len(smoothed_data):
                    smoothed_data[gap_start - window_size + i] += gap_diff * taper[i]

    # Right edge smoothing
    if gap_end < len(data) and gap_end + window_size <= len(data):
        # Cosine taper 생성 (역방향)
        taper = 0.5 * (1 - np.cos(np.pi * (window_size - np.arange(window_size)) / window_size))

        # 채워진 값과 원본 블렌딩
        filled_section = data[gap_end - window_size:gap_end]
        original_section = data[gap_end:gap_end + window_size]

        if not np.any(np.isnan(filled_section)) and not np.any(np.isnan(original_section)):
            # 경계 값 차이
            gap_diff = data[gap_end] - data[gap_end - 1]

            # Smoothing 적용
            for i in range(window_size):
                if gap_end - window_size + i < len(smoothed_data):
                    smoothed_data[gap_end - window_size + i] += gap_diff * taper[i]

    return smoothed_data

# ==============================================================================
# Main Spectral Gap Filling
# ==============================================================================

def spectral_gap_fill(data: np.ndarray, gap_start: int, gap_end: int,
                     v_valley_minutes: float = 553.5,
                     sampling_minutes: float = 5.0,
                     arma_order: Tuple[int, int] = (10, 10),
                     low_freq_window: int = 60,
                     high_freq_window: int = 20) -> np.ndarray:
    """
    Component-wise spectral gap filling (1시간 초과 gap용).

    Parameters
    ----------
    data : np.ndarray
        원본 압력 데이터
    gap_start : int
        gap 시작 인덱스
    gap_end : int
        gap 종료 인덱스
    v_valley_minutes : float
        V-valley 주기 (분)
    sampling_minutes : float
        샘플링 간격 (분)
    arma_order : Tuple[int, int]
        ARMA 차수
    low_freq_window : int
        저주파 edge smoothing window
    high_freq_window : int
        고주파 edge smoothing window

    Returns
    -------
    np.ndarray
        gap이 채워진 데이터
    """
    # 1. 주파수 분리
    low_freq, high_freq = butterworth_frequency_separation(
        data, v_valley_minutes, sampling_minutes
    )

    # 2. 저주파 성분 채우기 (ARMA)
    filled_low = arma_synthesis(low_freq, gap_start, gap_end, arma_order)
    filled_low = edge_smoothing(filled_low, gap_start, gap_end, low_freq_window)

    # 3. 고주파 성분 채우기 (Random Phase)
    filled_high = random_phase_synthesis(high_freq, gap_start, gap_end)
    filled_high = edge_smoothing(filled_high, gap_start, gap_end, high_freq_window)

    # 4. 성분 합치기
    filled_data = filled_low + filled_high

    return filled_data

# ==============================================================================
# Validation
# ==============================================================================

def validate_filled_data(original: np.ndarray, filled: np.ndarray,
                        gap_indices: List[Tuple[int, int]]) -> Dict[str, Any]:
    """
    채워진 데이터 검증.

    Parameters
    ----------
    original : np.ndarray
        원본 데이터 (NaN 포함)
    filled : np.ndarray
        채워진 데이터
    gap_indices : List[Tuple[int, int]]
        gap 위치 리스트

    Returns
    -------
    Dict
        검증 결과
    """
    results = {
        'no_new_nans': True,
        'all_gaps_filled': True,
        'continuity_preserved': True,
        'variance_ratio': 1.0,
        'mean_shift': 0.0
    }

    # 새로운 NaN 확인
    original_nan_mask = np.isnan(original)
    filled_nan_mask = np.isnan(filled)
    new_nans = filled_nan_mask & ~original_nan_mask
    results['no_new_nans'] = not new_nans.any()

    # 모든 gap이 채워졌는지 확인
    for start, end in gap_indices:
        if np.any(np.isnan(filled[start:end])):
            results['all_gaps_filled'] = False
            break

    # 연속성 확인 (gap 경계에서 급격한 점프 없는지)
    for start, end in gap_indices:
        if start > 0:
            left_diff = abs(filled[start] - filled[start-1])
            if left_diff > 3 * np.nanstd(original):
                results['continuity_preserved'] = False
        if end < len(filled):
            right_diff = abs(filled[end] - filled[end-1])
            if right_diff > 3 * np.nanstd(original):
                results['continuity_preserved'] = False

    # 통계적 특성 비교
    original_valid = original[~original_nan_mask]
    filled_valid = filled[~filled_nan_mask]

    if len(original_valid) > 0 and len(filled_valid) > 0:
        results['variance_ratio'] = np.var(filled_valid) / np.var(original_valid)
        results['mean_shift'] = np.mean(filled_valid) - np.mean(original_valid)

    return results

# ==============================================================================
# Main Gap Filling Function
# ==============================================================================

def fill_pressure_gaps(data: np.ndarray, timestamps: pd.DatetimeIndex = None,
                      method_threshold_hours: float = 1.0,
                      v_valley_minutes: float = 553.5) -> Tuple[np.ndarray, List[Dict]]:
    """
    압력 데이터의 모든 gap을 자동으로 채움.

    Parameters
    ----------
    data : np.ndarray
        원본 압력 데이터
    timestamps : pd.DatetimeIndex
        타임스탬프
    method_threshold_hours : float
        XGBoost vs Spectral 방법 선택 기준 (시간)
    v_valley_minutes : float
        V-valley 주기

    Returns
    -------
    Tuple[np.ndarray, List[Dict]]
        (채워진 데이터, gap 정보 및 사용된 방법)
    """
    # Gap 탐지
    gaps = detect_gaps(data, timestamps)

    if not gaps:
        logger.info("No gaps detected in data.")
        return data.copy(), []

    filled_data = data.copy()
    gap_info = []

    for gap in gaps:
        start = gap['start_idx']
        end = gap['end_idx']
        length_hours = gap.get('length_hours', gap['length'] * 5 / 60)

        # 방법 선택
        if length_hours <= method_threshold_hours:
            # 짧은 gap: XGBoost
            method = 'xgboost'
            logger.info(f"Filling gap {start}-{end} ({length_hours:.1f}h) with XGBoost")
            filled_data = xgboost_interpolation(filled_data, start, end)
        else:
            # 긴 gap: Spectral
            method = 'spectral'
            logger.info(f"Filling gap {start}-{end} ({length_hours:.1f}h) with Spectral method")
            filled_data = spectral_gap_fill(filled_data, start, end, v_valley_minutes)

        # Gap 정보 저장
        gap['method'] = method
        gap_info.append(gap)

    # 검증
    validation = validate_filled_data(data, filled_data,
                                     [(g['start_idx'], g['end_idx']) for g in gaps])

    logger.info(f"Validation results: {validation}")

    return filled_data, gap_info