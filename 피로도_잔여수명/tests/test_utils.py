"""
utils.py 모듈 단위 테스트
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

from utils import (
    interpolate_nan_values,
    calculate_sampling_rate,
    remove_outliers,
    smooth_data,
    normalize_data,
    denormalize_data,
)


class TestInterpolateNanValues:
    """NaN 값 보간 함수 테스트"""

    def test_no_nan_values(self):
        """NaN 값이 없는 경우 테스트"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        time_index = pd.date_range("2023-01-01", periods=5, freq="5min")

        result = interpolate_nan_values(data, time_index)

        np.testing.assert_array_equal(result, data)

    def test_linear_interpolation(self):
        """선형 보간 테스트"""
        data = np.array([1.0, np.nan, 3.0, np.nan, 5.0])
        time_index = pd.date_range("2023-01-01", periods=5, freq="5min")

        result = interpolate_nan_values(data, time_index, method="linear")
        expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        np.testing.assert_array_almost_equal(result, expected)

    def test_spline_interpolation(self):
        """스플라인 보간 테스트"""
        data = np.array([1.0, np.nan, 3.0, np.nan, 5.0, 6.0])
        time_index = pd.date_range("2023-01-01", periods=6, freq="5min")

        result = interpolate_nan_values(data, time_index, method="spline")

        # NaN 값이 보간되었는지 확인
        assert not np.any(np.isnan(result))
        # 원래 값들이 보존되었는지 확인 (부동소수점 오차 허용)
        assert abs(result[0] - 1.0) < 1e-10
        assert abs(result[2] - 3.0) < 1e-10
        assert abs(result[4] - 5.0) < 1e-10
        assert abs(result[5] - 6.0) < 1e-10

    def test_all_nan_values(self):
        """모든 값이 NaN인 경우 테스트"""
        data = np.array([np.nan, np.nan, np.nan])
        time_index = pd.date_range("2023-01-01", periods=3, freq="5min")

        result = interpolate_nan_values(data, time_index)

        # 모든 값이 동일한 값(평균)으로 채워져야 함
        assert len(np.unique(result[~np.isnan(result)])) <= 1

    def test_insufficient_valid_data(self):
        """유효한 데이터가 너무 적은 경우 테스트"""
        data = np.array([1.0, np.nan, np.nan, np.nan])
        time_index = pd.date_range("2023-01-01", periods=4, freq="5min")

        result = interpolate_nan_values(data, time_index)

        # 결과가 반환되어야 함
        assert len(result) == len(data)
        assert not np.any(np.isnan(result))


class TestCalculateSamplingRate:
    """샘플링 주파수 계산 함수 테스트"""

    def test_regular_5min_interval(self):
        """5분 간격 정규 데이터 테스트"""
        time_series = pd.date_range("2023-01-01", periods=100, freq="5min")

        sampling_rate = calculate_sampling_rate(time_series)
        expected_rate = 1 / 300  # 5분 = 300초

        assert abs(sampling_rate - expected_rate) < 1e-10

    def test_1hour_interval(self):
        """1시간 간격 데이터 테스트"""
        time_series = pd.date_range("2023-01-01", periods=24, freq="1h")

        sampling_rate = calculate_sampling_rate(time_series)
        expected_rate = 1 / 3600  # 1시간 = 3600초

        assert abs(sampling_rate - expected_rate) < 1e-10

    def test_insufficient_data(self):
        """데이터가 부족한 경우 테스트"""
        time_series = pd.date_range("2023-01-01", periods=1, freq="5min")

        with pytest.raises(ValueError, match="시계열 데이터가 너무 짧습니다"):
            calculate_sampling_rate(time_series)


class TestRemoveOutliers:
    """이상치 제거 함수 테스트"""

    def test_iqr_method(self):
        """IQR 방법 이상치 제거 테스트"""
        # 정상 데이터 + 이상치
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 100])  # 100이 이상치

        cleaned_data, outlier_mask = remove_outliers(data, method="iqr", factor=1.5)

        # 이상치가 NaN으로 변경되었는지 확인
        assert np.isnan(cleaned_data[-1])
        # 이상치 마스크가 올바른지 확인
        assert bool(outlier_mask[-1]) is True
        assert np.sum(outlier_mask) >= 1

    def test_zscore_method(self):
        """Z-score 방법 이상치 제거 테스트"""
        # 정상 분포 데이터 + 이상치
        np.random.seed(42)
        data = np.random.normal(0, 1, 100)
        data = np.append(data, [10, -10])  # 이상치 추가

        cleaned_data, outlier_mask = remove_outliers(data, method="zscore", factor=3.0)

        # 이상치가 검출되었는지 확인
        assert np.sum(outlier_mask) >= 1
        # 이상치가 NaN으로 변경되었는지 확인
        assert np.any(np.isnan(cleaned_data[outlier_mask]))

    def test_invalid_method(self):
        """잘못된 방법 지정 시 테스트"""
        data = np.array([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="지원하지 않는 방법입니다"):
            remove_outliers(data, method="invalid_method")


class TestSmoothData:
    """데이터 스무딩 함수 테스트"""

    def test_moving_average(self):
        """이동평균 스무딩 테스트"""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        window_size = 3

        smoothed = smooth_data(data, window_size=window_size, method="moving_average")

        # 결과 길이가 동일한지 확인
        assert len(smoothed) == len(data)
        # 스무딩 효과가 있는지 확인 (중간 값들이 평균에 가까워짐)
        assert abs(smoothed[4] - 5.0) < 0.1  # 중간 값 확인

    def test_savgol_filter(self):
        """Savitzky-Golay 필터 테스트"""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        window_size = 5

        smoothed = smooth_data(data, window_size=window_size, method="savgol")

        # 결과 길이가 동일한지 확인
        assert len(smoothed) == len(data)
        # 스무딩된 데이터가 원본과 유사하지만 더 부드러운지 확인
        assert np.corrcoef(data, smoothed)[0, 1] > 0.9

    def test_even_window_size_savgol(self):
        """짝수 윈도우 크기에 대한 Savitzky-Golay 필터 테스트"""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        window_size = 4  # 짝수

        smoothed = smooth_data(data, window_size=window_size, method="savgol")

        # 홀수로 변환되어 처리되어야 함
        assert len(smoothed) == len(data)

    def test_invalid_method(self):
        """잘못된 스무딩 방법 테스트"""
        data = np.array([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="지원하지 않는 방법입니다"):
            smooth_data(data, method="invalid_method")


class TestNormalizeData:
    """데이터 정규화 함수 테스트"""

    def test_minmax_normalization(self):
        """Min-Max 정규화 테스트"""
        data = np.array([1, 2, 3, 4, 5])

        normalized, scaler_params = normalize_data(data, method="minmax")

        # 0-1 범위로 정규화되었는지 확인
        assert np.min(normalized) == 0.0
        assert np.max(normalized) == 1.0
        # 스케일러 파라미터 확인
        assert scaler_params["min"] == 1
        assert scaler_params["max"] == 5

    def test_zscore_normalization(self):
        """Z-score 정규화 테스트"""
        data = np.array([1, 2, 3, 4, 5])

        normalized, scaler_params = normalize_data(data, method="zscore")

        # 평균 0, 표준편차 1에 가까운지 확인
        assert abs(np.mean(normalized)) < 1e-10
        assert abs(np.std(normalized) - 1.0) < 1e-10
        # 스케일러 파라미터 확인
        assert scaler_params["mean"] == 3.0
        assert scaler_params["std"] == np.std(data)

    def test_robust_normalization(self):
        """Robust 정규화 테스트"""
        data = np.array([1, 2, 3, 4, 5, 100])  # 이상치 포함

        normalized, scaler_params = normalize_data(data, method="robust")

        # 중앙값과 IQR 기반 정규화 확인
        assert "median" in scaler_params
        assert "iqr" in scaler_params
        assert scaler_params["median"] == np.median(data)

    def test_invalid_normalization_method(self):
        """잘못된 정규화 방법 테스트"""
        data = np.array([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="지원하지 않는 방법입니다"):
            normalize_data(data, method="invalid_method")


class TestDenormalizeData:
    """정규화 해제 함수 테스트"""

    def test_minmax_denormalization(self):
        """Min-Max 정규화 해제 테스트"""
        original_data = np.array([1, 2, 3, 4, 5])
        normalized, scaler_params = normalize_data(original_data, method="minmax")

        denormalized = denormalize_data(normalized, scaler_params, method="minmax")

        # 원본 데이터와 동일한지 확인
        np.testing.assert_array_almost_equal(denormalized, original_data)

    def test_zscore_denormalization(self):
        """Z-score 정규화 해제 테스트"""
        original_data = np.array([1, 2, 3, 4, 5])
        normalized, scaler_params = normalize_data(original_data, method="zscore")

        denormalized = denormalize_data(normalized, scaler_params, method="zscore")

        # 원본 데이터와 동일한지 확인
        np.testing.assert_array_almost_equal(denormalized, original_data)

    def test_robust_denormalization(self):
        """Robust 정규화 해제 테스트"""
        original_data = np.array([1, 2, 3, 4, 5, 100])
        normalized, scaler_params = normalize_data(original_data, method="robust")

        denormalized = denormalize_data(normalized, scaler_params, method="robust")

        # 원본 데이터와 동일한지 확인
        np.testing.assert_array_almost_equal(denormalized, original_data)

    def test_invalid_denormalization_method(self):
        """잘못된 정규화 해제 방법 테스트"""
        normalized_data = np.array([0, 0.25, 0.5, 0.75, 1.0])
        scaler_params = {"min": 1, "max": 5}

        with pytest.raises(ValueError, match="지원하지 않는 방법입니다"):
            denormalize_data(normalized_data, scaler_params, method="invalid_method")


# 통합 테스트
class TestIntegration:
    """통합 테스트"""

    def test_full_preprocessing_pipeline(self):
        """전체 전처리 파이프라인 테스트"""
        # 실제 데이터와 유사한 테스트 데이터 생성
        np.random.seed(42)
        time_series = pd.date_range("2023-01-01", periods=1000, freq="5min")
        data = np.random.normal(10, 2, 1000)

        # 일부 NaN 값과 이상치 추가
        data[100:105] = np.nan
        data[500] = 100  # 이상치

        # 1. NaN 값 보간
        interpolated = interpolate_nan_values(data, time_series)
        assert not np.any(np.isnan(interpolated))

        # 2. 이상치 제거
        cleaned, _ = remove_outliers(interpolated, method="iqr")

        # 3. 스무딩
        smoothed = smooth_data(cleaned, window_size=5)

        # 4. 정규화
        normalized, scaler_params = normalize_data(smoothed, method="minmax")

        # 5. 정규화 해제
        denormalized = denormalize_data(normalized, scaler_params, method="minmax")

        # 전체 파이프라인이 성공적으로 실행되었는지 확인
        assert len(denormalized) == len(data)
        assert not np.any(np.isnan(denormalized))

        # 샘플링 주파수 계산
        sampling_rate = calculate_sampling_rate(time_series)
        expected_rate = 1 / 300
        assert abs(sampling_rate - expected_rate) < 1e-10


if __name__ == "__main__":
    pytest.main([__file__])
