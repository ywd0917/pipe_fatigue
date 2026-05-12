"""
데이터 처리 유틸리티 함수들
- NaN 값 보간
- 기타 공통 데이터 처리 함수들
"""

import pandas as pd
import numpy as np
from scipy import interpolate
from typing import Union, Tuple, Dict


def interpolate_nan_values(
    data: np.ndarray,
    time_index: Union[pd.DatetimeIndex, np.ndarray],
    method: str = "linear",
) -> np.ndarray:
    """
    NaN 값 보간

    Args:
        data (array): 보간할 데이터 배열
        time_index (array): 시간 인덱스 (pandas datetime 또는 숫자)
        method (str): 보간 방법 ('linear', 'spline', 'time')

    Returns:
        array: 보간된 데이터 배열
    """
    print(f"NaN 값 보간 중... (방법: {method})")

    nan_mask = np.isnan(data)
    nan_count = np.sum(nan_mask)

    if nan_count == 0:
        print("NaN 값이 없습니다.")
        return data

    print(f"NaN 값 개수: {nan_count} ({nan_count/len(data)*100:.2f}%)")

    valid_mask = ~nan_mask
    valid_indices = np.where(valid_mask)[0]
    valid_data = data[valid_mask]

    if len(valid_data) < 2:
        print("경고: 유효한 데이터가 너무 적습니다.")
        return np.full_like(data, np.nanmean(data))

    if method == "linear":
        f = interpolate.interp1d(
            valid_indices, valid_data, kind="linear", fill_value="extrapolate"
        )
        interpolated_data = f(np.arange(len(data)))
    elif method == "spline":
        if len(valid_data) >= 4:
            f = interpolate.interp1d(
                valid_indices, valid_data, kind="cubic", fill_value="extrapolate"
            )
        else:
            f = interpolate.interp1d(
                valid_indices, valid_data, kind="linear", fill_value="extrapolate"
            )
        interpolated_data = f(np.arange(len(data)))
    else:
        # pandas 시간 기반 보간
        df_temp = pd.DataFrame({"time": time_index, "value": data})
        df_temp.set_index("time", inplace=True)
        df_interpolated = df_temp.interpolate(method="time")
        interpolated_data = df_interpolated["value"].values

    print(
        f"보간 완료. 보간 전 평균: {np.nanmean(data):.4f}, 보간 후 평균: {np.mean(interpolated_data):.4f}"
    )
    return interpolated_data


def calculate_sampling_rate(
    time_series: Union[pd.DatetimeIndex, np.ndarray], unit: str = "seconds"
) -> float:
    """
    시계열 데이터의 샘플링 주파수 계산

    Args:
        time_series (array): 시간 배열 (pandas datetime)
        unit (str): 반환 단위 ('seconds', 'minutes', 'hours')

    Returns:
        float: 샘플링 주파수 (Hz)
    """
    if len(time_series) < 2:
        raise ValueError("시계열 데이터가 너무 짧습니다.")

    # 시간 간격 계산 (초 단위)
    datetime_series = pd.to_datetime(time_series)
    time_diff = pd.Series(datetime_series).diff().dropna()
    avg_interval_seconds = time_diff.dt.total_seconds().mean()

    # 샘플링 주파수 (Hz)
    sampling_rate = 1 / avg_interval_seconds

    return sampling_rate


def remove_outliers(
    data: np.ndarray, method: str = "iqr", factor: float = 1.5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    이상치 제거

    Args:
        data (array): 데이터 배열
        method (str): 이상치 검출 방법 ('iqr', 'zscore')
        factor (float): 이상치 판정 기준 (IQR의 경우 1.5, Z-score의 경우 3.0 권장)

    Returns:
        tuple: (cleaned_data, outlier_mask)
    """
    data = np.array(data, dtype=float)  # float로 변환하여 NaN 할당 가능하게 함

    if method == "iqr":
        Q1 = np.percentile(data, 25)
        Q3 = np.percentile(data, 75)
        IQR = Q3 - Q1

        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR

        outlier_mask = (data < lower_bound) | (data > upper_bound)

    elif method == "zscore":
        z_scores = np.abs((data - np.mean(data)) / np.std(data))
        outlier_mask = z_scores > factor

    else:
        raise ValueError("지원하지 않는 방법입니다. 'iqr' 또는 'zscore'를 사용하세요.")

    cleaned_data = data.copy()
    cleaned_data[outlier_mask] = np.nan

    print(
        f"이상치 검출 ({method}): {np.sum(outlier_mask)}개 ({np.sum(outlier_mask)/len(data)*100:.2f}%)"
    )

    return cleaned_data, outlier_mask


def smooth_data(
    data: np.ndarray, window_size: int = 5, method: str = "moving_average"
) -> np.ndarray:
    """
    데이터 스무딩

    Args:
        data (array): 스무딩할 데이터
        window_size (int): 윈도우 크기
        method (str): 스무딩 방법 ('moving_average', 'savgol')

    Returns:
        array: 스무딩된 데이터
    """
    data = np.array(data)

    # NaN 값이 있는 경우 처리
    if np.any(np.isnan(data)):
        # NaN 값을 선형 보간으로 임시 처리
        valid_mask = ~np.isnan(data)
        if np.sum(valid_mask) < 2:
            return data  # 유효한 데이터가 너무 적으면 원본 반환

        valid_indices = np.where(valid_mask)[0]
        valid_data = data[valid_mask]

        f = interpolate.interp1d(
            valid_indices, valid_data, kind="linear", fill_value="extrapolate"
        )
        data_interpolated = f(np.arange(len(data)))
    else:
        data_interpolated = data

    if method == "moving_average":
        # 이동평균
        smoothed = np.convolve(
            data_interpolated, np.ones(window_size) / window_size, mode="same"
        )

    elif method == "savgol":
        # Savitzky-Golay 필터
        from scipy.signal import savgol_filter

        if window_size % 2 == 0:
            window_size += 1  # 홀수로 만들기
        smoothed = savgol_filter(data_interpolated, window_size, 3)

    else:
        raise ValueError(
            "지원하지 않는 방법입니다. 'moving_average' 또는 'savgol'을 사용하세요."
        )

    return smoothed


def normalize_data(
    data: np.ndarray, method: str = "minmax"
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    데이터 정규화

    Args:
        data (array): 정규화할 데이터
        method (str): 정규화 방법 ('minmax', 'zscore', 'robust')

    Returns:
        tuple: (normalized_data, scaler_params)
    """
    data = np.array(data)

    if method == "minmax":
        # Min-Max 정규화 (0-1 범위)
        data_min = np.min(data)
        data_max = np.max(data)
        normalized = (data - data_min) / (data_max - data_min)
        scaler_params = {"min": data_min, "max": data_max}

    elif method == "zscore":
        # Z-score 정규화 (평균 0, 표준편차 1)
        data_mean = np.mean(data)
        data_std = np.std(data)
        normalized = (data - data_mean) / data_std
        scaler_params = {"mean": data_mean, "std": data_std}

    elif method == "robust":
        # Robust 정규화 (중앙값과 IQR 사용)
        data_median = np.median(data)
        data_iqr = np.percentile(data, 75) - np.percentile(data, 25)
        normalized = (data - data_median) / data_iqr
        scaler_params = {"median": data_median, "iqr": data_iqr}

    else:
        raise ValueError(
            "지원하지 않는 방법입니다. 'minmax', 'zscore', 'robust'를 사용하세요."
        )

    return normalized, scaler_params


def denormalize_data(
    normalized_data: np.ndarray, scaler_params: Dict[str, float], method: str = "minmax"
) -> np.ndarray:
    """
    정규화된 데이터를 원래 스케일로 복원

    Args:
        normalized_data (array): 정규화된 데이터
        scaler_params (dict): normalize_data에서 반환된 스케일러 파라미터
        method (str): 정규화 방법 ('minmax', 'zscore', 'robust')

    Returns:
        array: 원래 스케일로 복원된 데이터
    """
    normalized_data = np.array(normalized_data)

    if method == "minmax":
        data_min = scaler_params["min"]
        data_max = scaler_params["max"]
        denormalized = normalized_data * (data_max - data_min) + data_min

    elif method == "zscore":
        data_mean = scaler_params["mean"]
        data_std = scaler_params["std"]
        denormalized = normalized_data * data_std + data_mean

    elif method == "robust":
        data_median = scaler_params["median"]
        data_iqr = scaler_params["iqr"]
        denormalized = normalized_data * data_iqr + data_median

    else:
        raise ValueError(
            "지원하지 않는 방법입니다. 'minmax', 'zscore', 'robust'를 사용하세요."
        )

    return denormalized
