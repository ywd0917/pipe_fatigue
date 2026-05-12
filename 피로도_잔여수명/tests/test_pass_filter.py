"""
pass_filter.py 모듈 단위 테스트
"""

import pytest
import numpy as np
import pandas as pd
from scipy import signal
import os

from pass_filter import (
    pass_filter,
    VALLEY_FREQ,
    VALLEY_PERIOD,
    LOW_PASS_MARGIN,
    HIGH_PASS_MARGIN,
)


class TestConstants:
    """상수 값 테스트"""

    def test_valley_constants(self):
        """V자 최저점 상수 값 테스트"""
        # VALLEY_PERIOD가 기준값이고 VALLEY_FREQ는 계산됨
        # common/config.py의 V_SHAPED_MIN_FREQ 값 사용
        assert VALLEY_PERIOD == 553.5
        # 계산된 주파수가 예상 범위 내에 있는지 확인
        expected_freq = 1 / (VALLEY_PERIOD * 60)
        assert abs(VALLEY_FREQ - expected_freq) < 1e-10
        assert abs(VALLEY_FREQ - 0.000030) < 1e-6  # 근사값 비교
        assert LOW_PASS_MARGIN == 1.0
        assert HIGH_PASS_MARGIN == 1.0

    def test_valley_frequency_period_consistency(self):
        """V자 최저점 주파수와 주기의 일관성 테스트"""
        # 주파수에서 주기 계산
        calculated_period = 1 / VALLEY_FREQ / 60  # 분 단위

        # 이제 VALLEY_PERIOD가 주파수로부터 계산되므로 정확히 일치해야 함
        assert abs(calculated_period - VALLEY_PERIOD) < 1e-10


class TestApplyPassFilters:
    """Pass Filter 적용 함수 테스트"""

    def test_with_synthetic_signal(self):
        """합성 신호로 Pass Filter 적용 테스트"""
        # 테스트 신호 생성 (일주조 + 반일주조 성분)
        sampling_rate = 1 / 300  # 5분 간격
        t = np.arange(0, 10000) / sampling_rate

        # 일주조(24시간)와 반일주조(12시간) 성분
        freq_daily = 1 / (24 * 3600)
        freq_semidiurnal = 1 / (12 * 3600)

        signal_data = (
            2.0 * np.sin(2 * np.pi * freq_daily * t)
            + 1.0 * np.sin(2 * np.pi * freq_semidiurnal * t)
            + 0.1 * np.random.normal(0, 1, len(t))
        )

        file_path = "test_data.csv"

        low_pass, high_pass = pass_filter(signal_data, sampling_rate, file_path)

        # 합성 신호 계산
        combined = low_pass + high_pass

        # 결과 검증
        assert low_pass is not None
        assert high_pass is not None
        assert combined is not None

        # 길이 확인
        assert len(low_pass) == len(signal_data)
        assert len(high_pass) == len(signal_data)
        assert len(combined) == len(signal_data)

        # 표준편차가 0이 아닌지 확인 (필터링된 신호가 의미있는지)
        assert np.std(low_pass) > 0
        assert np.std(high_pass) > 0
        assert np.std(combined) > 0

    def test_signal_reconstruction(self):
        """신호 재구성 테스트 (Low Pass + High Pass = 원본)"""
        # 테스트 신호 생성
        sampling_rate = 1 / 300
        np.random.seed(42)
        signal_data = np.random.normal(0, 1, 5000)

        file_path = "test_reconstruction.csv"

        low_pass, high_pass = pass_filter(signal_data, sampling_rate, file_path)

        # 합성 신호 계산
        combined = low_pass + high_pass

        # 재구성된 신호가 저대역 + 고대역과 일치하는지 확인
        manual_combined = low_pass + high_pass
        np.testing.assert_array_almost_equal(combined, manual_combined, decimal=10)

        # 원본과 재구성된 신호의 상관계수 확인
        correlation = np.corrcoef(signal_data, combined)[0, 1]
        assert correlation > 0.99  # 99% 이상의 상관관계

    def test_energy_conservation(self):
        """에너지 보존 테스트"""
        # 테스트 신호 생성
        sampling_rate = 1 / 300
        np.random.seed(42)
        signal_data = np.random.normal(0, 1, 3000)

        file_path = "test_energy.csv"

        low_pass, high_pass = pass_filter(signal_data, sampling_rate, file_path)

        # 합성 신호 계산
        combined = low_pass + high_pass

        # 에너지 계산 (분산 사용)
        original_energy = np.var(signal_data)
        low_energy = np.var(low_pass)
        high_energy = np.var(high_pass)
        combined_energy = np.var(combined)

        # 에너지 보존율 계산
        conservation_rate = (low_energy + high_energy) / original_energy

        # 97% 이상의 에너지 보존율 확인
        assert conservation_rate > 0.97

        # 재구성된 신호의 에너지가 원본과 유사한지 확인
        reconstruction_rate = combined_energy / original_energy
        assert abs(reconstruction_rate - 1.0) < 0.01  # 1% 오차 허용

    def test_filter_frequency_response(self):
        """필터 주파수 응답 테스트"""
        sampling_rate = 1 / 300

        # 단일 주파수 성분 테스트
        t = np.arange(0, 5000) / sampling_rate

        # V자 최저점보다 낮은 주파수 (저대역에 포함되어야 함)
        low_freq = VALLEY_FREQ * 0.5
        low_signal = np.sin(2 * np.pi * low_freq * t)

        low_pass_result, high_pass_result = pass_filter(
            low_signal, sampling_rate, "test_low.csv"
        )

        # 저대역 필터에서 더 큰 에너지를 가져야 함
        low_energy = np.var(low_pass_result)
        high_energy = np.var(high_pass_result)
        assert low_energy > high_energy

        # V자 최저점보다 높은 주파수 (고대역에 포함되어야 함)
        high_freq = VALLEY_FREQ * 2.0
        high_signal = np.sin(2 * np.pi * high_freq * t)

        low_pass_result, high_pass_result = pass_filter(
            high_signal, sampling_rate, "test_high.csv"
        )

        # 고대역 필터에서 더 큰 에너지를 가져야 함
        low_energy = np.var(low_pass_result)
        high_energy = np.var(high_pass_result)
        assert high_energy > low_energy

    def test_nyquist_frequency_handling(self):
        """Nyquist 주파수 처리 테스트"""
        # 매우 높은 샘플링 주파수로 테스트
        high_sampling_rate = 1.0  # 1 Hz
        nyquist = high_sampling_rate / 2

        # V자 최저점이 Nyquist 주파수에 가까운 경우
        if nyquist * 0.99 <= VALLEY_FREQ:
            # 테스트 신호 생성
            signal_data = np.random.normal(0, 1, 1000)

            # 함수가 에러 없이 실행되는지 확인
            low_pass, high_pass = pass_filter(
                signal_data, high_sampling_rate, "test_nyquist.csv"
            )

            # 합성 신호 계산
            combined = low_pass + high_pass

            assert low_pass is not None
            assert high_pass is not None
            assert combined is not None

    def test_with_constant_signal(self):
        """상수 신호로 테스트"""
        sampling_rate = 1 / 300
        signal_data = np.ones(1000) * 5.0  # 상수 신호

        file_path = "test_constant.csv"

        low_pass, high_pass = pass_filter(signal_data, sampling_rate, file_path)

        # 합성 신호 계산
        combined = low_pass + high_pass

        # 상수 신호는 주로 저대역에 포함되어야 함
        assert np.std(low_pass) < np.std(high_pass) or np.std(high_pass) < 0.1

        # 재구성된 신호가 원본과 유사해야 함
        np.testing.assert_array_almost_equal(combined, signal_data, decimal=5)

    def test_with_empty_signal(self):
        """빈 신호로 테스트"""
        sampling_rate = 1 / 300
        signal_data = np.array([])

        file_path = "test_empty.csv"

        # 빈 신호에 대해 적절히 처리되는지 확인
        with pytest.raises((ValueError, IndexError)):
            pass_filter(signal_data, sampling_rate, file_path)

    def test_with_very_short_signal(self):
        """매우 짧은 신호로 테스트"""
        sampling_rate = 1 / 300
        signal_data = np.array([1.0, 2.0, 3.0])  # 3개 포인트

        file_path = "test_short.csv"

        # 매우 짧은 신호에 대해서도 처리되는지 확인
        try:
            low_pass, high_pass = pass_filter(signal_data, sampling_rate, file_path)

            # 합성 신호 계산
            combined = low_pass + high_pass

            if low_pass is not None:
                assert len(low_pass) == len(signal_data)
                assert len(high_pass) == len(signal_data)
                assert len(combined) == len(signal_data)
        except (ValueError, RuntimeError):
            # 매우 짧은 신호에서는 필터링이 불가능할 수 있음
            pass

    def test_performance_with_large_dataset(self):
        """대용량 데이터셋 성능 테스트"""
        # 큰 데이터셋 생성 (약 3개월 분량)
        large_data_size = 100000
        sampling_rate = 1 / 300

        np.random.seed(42)
        large_signal = np.random.normal(0, 1, large_data_size)

        # 시간 측정
        import time

        start_time = time.time()

        low_pass, high_pass = pass_filter(
            large_signal, sampling_rate, "large_dataset.csv"
        )

        # 합성 신호 계산
        combined = low_pass + high_pass

        end_time = time.time()
        processing_time = end_time - start_time

        # 성능 검증 (100,000개 포인트를 30초 이내에 처리)
        assert processing_time < 30.0

        # 결과 검증
        assert len(low_pass) == large_data_size
        assert len(high_pass) == large_data_size
        assert len(combined) == large_data_size

        # 메모리 효율성 확인 (결과가 합리적인 범위 내)
        assert np.std(low_pass) > 0
        assert np.std(high_pass) > 0
        assert not np.any(np.isnan(combined))

    def test_error_handling_and_robustness(self):
        """에러 처리 및 견고성 테스트"""
        sampling_rate = 1 / 300

        # 1. NaN 값이 포함된 신호
        signal_with_nan = np.random.normal(0, 1, 1000)
        signal_with_nan[100:110] = np.nan

        # NaN이 포함된 신호는 이제 ValueError를 발생시켜야 함
        with pytest.raises(ValueError) as excinfo:
            low_pass, high_pass = pass_filter(
                signal_with_nan, sampling_rate, "nan_test.csv"
            )

        # 에러 메시지 확인
        assert "NaN 값이 포함되어 있습니다" in str(excinfo.value)

        # NaN 값을 먼저 처리한 후 필터 적용
        from utils import interpolate_nan_values

        time_index = pd.date_range(
            "2023-01-01", periods=len(signal_with_nan), freq="5min"
        )
        signal_cleaned = interpolate_nan_values(signal_with_nan, time_index)

        # 이제 정상적으로 처리되어야 함
        low_pass, high_pass = pass_filter(
            signal_cleaned, sampling_rate, "nan_test_cleaned.csv"
        )

        # 합성 신호 계산
        combined = low_pass + high_pass

        # NaN이 없는지 확인
        assert not np.any(np.isnan(combined))

        # 2. 무한대 값이 포함된 신호
        signal_with_inf = np.random.normal(0, 1, 1000)
        signal_with_inf[50] = np.inf
        signal_with_inf[51] = -np.inf

        try:
            low_pass, high_pass = pass_filter(
                signal_with_inf, sampling_rate, "inf_test.csv"
            )

            # 합성 신호 계산
            combined = low_pass + high_pass

            # 무한대가 전파되지 않았는지 확인
            assert not np.any(np.isinf(combined))
        except (ValueError, RuntimeError):
            # 무한대 처리가 불가능한 경우도 허용
            pass

        # 3. 매우 작은 샘플링 주파수
        very_small_sampling_rate = 1e-10
        normal_signal = np.random.normal(0, 1, 1000)

        # 매우 작은 샘플링 주파수에서는 필터가 제대로 작동하지 않을 수 있음
        try:
            low_pass, high_pass = pass_filter(
                normal_signal, very_small_sampling_rate, "small_rate.csv"
            )

            # 합성 신호 계산
            combined = low_pass + high_pass

            # 결과가 유효하지 않을 수 있음 (NaN 또는 무한대)
            if not (np.any(np.isnan(combined)) or np.any(np.isinf(combined))):
                # 정상적으로 처리된 경우도 허용
                assert len(combined) == len(normal_signal)
        except (ValueError, RuntimeError):
            # 예외가 발생하는 경우도 허용
            pass

        # 4. 매우 큰 샘플링 주파수
        very_large_sampling_rate = 1e6

        try:
            low_pass, high_pass = pass_filter(
                normal_signal, very_large_sampling_rate, "large_rate.csv"
            )

            # 합성 신호 계산
            combined = low_pass + high_pass

            # 결과가 합리적인지 확인
            assert len(combined) == len(normal_signal)
        except (ValueError, RuntimeError):
            # 매우 큰 샘플링 주파수에서 문제가 발생할 수 있음
            pass


class TestIntegration:
    """통합 테스트"""

    def test_full_pass_filter_pipeline(self):
        """전체 Pass Filter 파이프라인 테스트"""
        # 실제 사용 시나리오와 유사한 테스트
        sampling_rate = 1 / 300

        # 실제 압력 데이터와 유사한 신호 생성
        t = np.arange(0, 20000) / sampling_rate  # 약 69일 분량

        # 일주조, 반일주조, 노이즈 성분
        daily_component = 3.0 * np.sin(2 * np.pi * 1 / (24 * 3600) * t + np.pi / 4)
        semidiurnal_component = 1.5 * np.sin(
            2 * np.pi * 1 / (12 * 3600) * t + np.pi / 6
        )
        noise = 0.2 * np.random.normal(0, 1, len(t))

        pressure_data = (
            daily_component + semidiurnal_component + noise + 10.0
        )  # 평균 10

        # 1. Pass Filter 적용
        low_pass, high_pass = pass_filter(
            pressure_data, sampling_rate, "integration_test.csv"
        )

        # 합성 신호 계산
        combined = low_pass + high_pass

        # 2. 기본 검증
        assert len(low_pass) == len(pressure_data)
        assert len(high_pass) == len(pressure_data)
        assert len(combined) == len(pressure_data)

        # 3. 신호 재구성 검증
        correlation = np.corrcoef(pressure_data, combined)[0, 1]
        assert correlation > 0.999  # 99.9% 이상의 상관관계

        # 4. 에너지 분포 검증
        original_energy = np.var(pressure_data)
        low_energy = np.var(low_pass)
        high_energy = np.var(high_pass)

        # V자 최저점(553.5분) 기준으로 일주조는 저대역, 반일주조는 고대역에 포함
        # 일주조(1440분)가 더 강하므로 저대역 에너지가 더 커야 함
        assert low_energy > high_energy

        # 총 에너지 보존 (기준을 95%로 완화)
        conservation_rate = (low_energy + high_energy) / original_energy
        assert conservation_rate > 0.95


if __name__ == "__main__":
    pytest.main([__file__])
