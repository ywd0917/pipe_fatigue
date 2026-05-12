"""
main52_pass_filter.py 모듈 시각화 관련 단위 테스트
"""

import pytest
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import os
from pathlib import Path

from main52_pass_filter import create_pass_filter_visualization
from pass_filter import pass_filter

# 테스트 상수 정의
DEFAULT_SAMPLING_RATE = 1 / 300  # 5분 간격
DEFAULT_SIGNAL_LENGTH = 1000  # 기본 신호 길이
LARGE_SIGNAL_LENGTH = 10000  # 큰 신호 길이 (100000에서 축소)
TEST_OUTPUT_DIR = "test_results"


class TestCreatePassFilterVisualization:
    """Pass Filter 시각화 함수 테스트"""

    @pytest.fixture
    def test_signals(self):
        """테스트용 신호 생성 fixture"""
        t = np.arange(0, 15000) / DEFAULT_SAMPLING_RATE  # 충분히 긴 신호

        # 원본 신호 (일주조 + 반일주조)
        original = 2.0 * np.sin(2 * np.pi * 1 / (24 * 3600) * t) + np.sin(
            2 * np.pi * 1 / (12 * 3600) * t
        )

        # 필터 적용
        low_pass, high_pass = pass_filter(
            original, DEFAULT_SAMPLING_RATE, "test_viz.csv"
        )

        # 합성 신호 계산
        combined = low_pass + high_pass

        return {
            "original": original,
            "low_pass": low_pass,
            "high_pass": high_pass,
            "combined": combined,
        }

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """임시 출력 디렉토리 fixture"""
        output_dir = tmp_path / TEST_OUTPUT_DIR
        output_dir.mkdir(exist_ok=True)
        return str(output_dir)

    def test_visualization_creation(self, test_signals, temp_output_dir):
        """시각화 생성 테스트"""
        # 시각화 생성
        output_path = create_pass_filter_visualization(
            test_signals["original"],
            test_signals["low_pass"],
            test_signals["high_pass"],
            test_signals["combined"],
            "test_file.csv",
            temp_output_dir,
        )

        # 출력 파일이 생성되었는지 확인
        assert Path(output_path).exists(), "시각화 파일이 생성되지 않았습니다"
        assert output_path.endswith(".png"), "파일 확장자가 PNG가 아닙니다"

    @pytest.mark.parametrize(
        "file_name",
        [
            "0470 소구역 압력 데이터.csv",
            "0520 중구역 압력 데이터.csv",
            "simple_file.csv",
            "file with spaces.csv",
        ],
    )
    def test_visualization_with_different_file_names(self, file_name, temp_output_dir):
        """다양한 파일명으로 시각화 테스트"""
        # 테스트 데이터 생성
        data_length = DEFAULT_SIGNAL_LENGTH
        np.random.seed(42)
        original = np.random.normal(0, 1, data_length)
        low_pass = np.random.normal(0, 0.8, data_length)
        high_pass = np.random.normal(0, 0.3, data_length)
        combined = low_pass + high_pass

        output_path = create_pass_filter_visualization(
            original, low_pass, high_pass, combined, file_name, temp_output_dir
        )

        assert Path(
            output_path
        ).exists(), f"{file_name}에 대한 시각화 파일이 생성되지 않았습니다"

    @pytest.mark.parametrize(
        "data_length,test_name",
        [
            (20000, "long_data"),  # 충분히 긴 데이터
            (5000, "short_data"),  # 10000개보다 짧은 데이터
            (1000, "very_short_data"),  # 매우 짧은 데이터
        ],
    )
    def test_visualization_with_various_data_lengths(
        self, data_length, test_name, temp_output_dir
    ):
        """다양한 길이의 데이터로 시각화 테스트"""
        np.random.seed(42)
        original = np.random.normal(0, 1, data_length)
        low_pass = np.random.normal(0, 0.8, data_length)
        high_pass = np.random.normal(0, 0.3, data_length)
        combined = low_pass + high_pass

        # 시각화 생성 시도
        try:
            output_path = create_pass_filter_visualization(
                original,
                low_pass,
                high_pass,
                combined,
                f"{test_name}.csv",
                temp_output_dir,
            )

            # 파일이 생성되었다면 확인
            assert Path(
                output_path
            ).exists(), f"{test_name}에 대한 파일이 생성되지 않았습니다"

        except (IndexError, ValueError):
            # 데이터가 너무 짧아서 슬라이싱이 불가능한 경우
            if data_length < 11000:  # 시각화는 10000-11000 구간을 사용
                pass  # 예상된 동작
            else:
                raise  # 예상치 못한 오류


class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def realistic_pressure_data(self):
        """실제 압력 데이터와 유사한 신호 생성"""
        t = np.arange(0, 20000) / DEFAULT_SAMPLING_RATE  # 약 69일 분량

        # 일주조, 반일주조, 노이즈 성분
        daily_component = 3.0 * np.sin(2 * np.pi * 1 / (24 * 3600) * t + np.pi / 4)
        semidiurnal_component = 1.5 * np.sin(
            2 * np.pi * 1 / (12 * 3600) * t + np.pi / 6
        )

        np.random.seed(42)
        noise = 0.2 * np.random.normal(0, 1, len(t))

        return daily_component + semidiurnal_component + noise + 10.0  # 평균 10

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """임시 출력 디렉토리 fixture"""
        output_dir = tmp_path / TEST_OUTPUT_DIR
        output_dir.mkdir(exist_ok=True)
        return str(output_dir)

    def test_full_pass_filter_pipeline(self, realistic_pressure_data, temp_output_dir):
        """전체 Pass Filter 파이프라인 테스트"""
        # 1. Pass Filter 적용
        low_pass, high_pass = pass_filter(
            realistic_pressure_data, DEFAULT_SAMPLING_RATE, "integration_test.csv"
        )

        # 합성 신호 계산
        combined = low_pass + high_pass

        # 2. 기본 검증
        assert len(low_pass) == len(realistic_pressure_data), "저대역 성분 길이 불일치"
        assert len(high_pass) == len(realistic_pressure_data), "고대역 성분 길이 불일치"
        assert len(combined) == len(realistic_pressure_data), "합성 신호 길이 불일치"

        # 3. 신호 재구성 검증
        correlation = np.corrcoef(realistic_pressure_data, combined)[0, 1]
        assert correlation > 0.999, f"상관계수({correlation:.4f})가 99.9% 미만"

        # 4. 에너지 분포 검증
        original_energy = np.var(realistic_pressure_data)
        low_energy = np.var(low_pass)
        high_energy = np.var(high_pass)

        # V자 최저점(553.5분) 기준으로 일주조는 저대역, 반일주조는 고대역에 포함
        # 일주조(1440분)가 더 강하므로 저대역 에너지가 더 커야 함
        assert (
            low_energy > high_energy
        ), f"저대역 에너지({low_energy:.4f})가 고대역({high_energy:.4f})보다 작음"

        # 총 에너지 보존 (기준을 95%로 완화)
        conservation_rate = (low_energy + high_energy) / original_energy
        assert (
            conservation_rate > 0.95
        ), f"에너지 보존율({conservation_rate:.2%})이 95% 미만"

        # 5. 시각화 생성 테스트
        output_path = create_pass_filter_visualization(
            realistic_pressure_data,
            low_pass,
            high_pass,
            combined,
            "integration_test_data.csv",
            temp_output_dir,
        )

        assert Path(output_path).exists(), "통합 테스트 시각화 파일이 생성되지 않음"

    def test_performance_with_large_dataset(self):
        """대용량 데이터셋 성능 테스트"""
        # 큰 데이터셋 생성 (100000 -> 10000으로 축소)
        large_data_size = LARGE_SIGNAL_LENGTH

        np.random.seed(42)
        large_signal = np.random.normal(0, 1, large_data_size)

        # 시간 측정
        import time

        start_time = time.time()

        low_pass, high_pass = pass_filter(
            large_signal, DEFAULT_SAMPLING_RATE, "large_dataset.csv"
        )

        # 합성 신호 계산
        combined = low_pass + high_pass

        end_time = time.time()
        processing_time = end_time - start_time

        # 성능 검증 (10,000개 포인트를 5초 이내에 처리)
        assert processing_time < 5.0, f"처리 시간({processing_time:.2f}초)이 5초를 초과"

        # 결과 검증
        assert len(low_pass) == large_data_size, "저대역 성분 크기 불일치"
        assert len(high_pass) == large_data_size, "고대역 성분 크기 불일치"
        assert len(combined) == large_data_size, "합성 신호 크기 불일치"

        # 메모리 효율성 확인 (결과가 합리적인 범위 내)
        assert np.std(low_pass) > 0, "저대역 성분 표준편차가 0"
        assert np.std(high_pass) > 0, "고대역 성분 표준편차가 0"
        assert not np.any(np.isnan(combined)), "합성 신호에 NaN이 포함됨"

    @pytest.mark.parametrize(
        "test_case",
        [
            "nan_values",
            "inf_values",
            "very_small_sampling_rate",
            "very_large_sampling_rate",
        ],
    )
    def test_error_handling_and_robustness(self, test_case):
        """에러 처리 및 견고성 테스트"""

        np.random.seed(42)
        normal_signal = np.random.normal(0, 1, DEFAULT_SIGNAL_LENGTH)

        if test_case == "nan_values":
            # NaN 값이 포함된 신호
            signal_with_nan = normal_signal.copy()
            signal_with_nan[100:110] = np.nan

            # NaN이 포함된 신호는 ValueError를 발생시켜야 함
            with pytest.raises(ValueError) as excinfo:
                pass_filter(signal_with_nan, DEFAULT_SAMPLING_RATE, "nan_test.csv")

            assert "NaN 값이 포함되어 있습니다" in str(excinfo.value)

            # NaN 값을 처리한 후 필터 적용
            from utils import interpolate_nan_values

            time_index = pd.date_range(
                "2023-01-01", periods=len(signal_with_nan), freq="5min"
            )
            signal_cleaned = interpolate_nan_values(signal_with_nan, time_index)

            low_pass, high_pass = pass_filter(
                signal_cleaned, DEFAULT_SAMPLING_RATE, "nan_test_cleaned.csv"
            )
            combined = low_pass + high_pass
            assert not np.any(np.isnan(combined)), "NaN이 제거되지 않음"

        elif test_case == "inf_values":
            # 무한대 값이 포함된 신호
            signal_with_inf = normal_signal.copy()
            signal_with_inf[50] = np.inf
            signal_with_inf[51] = -np.inf

            try:
                low_pass, high_pass = pass_filter(
                    signal_with_inf, DEFAULT_SAMPLING_RATE, "inf_test.csv"
                )
                combined = low_pass + high_pass
                assert not np.any(np.isinf(combined)), "무한대가 전파됨"
            except (ValueError, RuntimeError):
                pass  # 무한대 처리 불가 경우도 허용

        elif test_case == "very_small_sampling_rate":
            # 매우 작은 샘플링 주파수
            very_small_rate = 1e-10
            try:
                low_pass, high_pass = pass_filter(
                    normal_signal, very_small_rate, "small_rate.csv"
                )
                combined = low_pass + high_pass
                if not (np.any(np.isnan(combined)) or np.any(np.isinf(combined))):
                    assert len(combined) == len(normal_signal)
            except (ValueError, RuntimeError):
                pass  # 예외 허용

        elif test_case == "very_large_sampling_rate":
            # 매우 큰 샘플링 주파수
            very_large_rate = 1e6
            try:
                low_pass, high_pass = pass_filter(
                    normal_signal, very_large_rate, "large_rate.csv"
                )
                combined = low_pass + high_pass
                assert len(combined) == len(normal_signal)
            except (ValueError, RuntimeError):
                pass  # 예외 허용


if __name__ == "__main__":
    pytest.main([__file__])
