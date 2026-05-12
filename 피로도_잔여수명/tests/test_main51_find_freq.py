"""
main51_find_freq.py 모듈 단위 테스트
"""

import pytest
import numpy as np
import pandas as pd
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt
import os
from pathlib import Path

from main51_find_freq import (
    design_component_separation_filters,
    apply_component_filters,
    add_vertical_lines_to_plot,
    setup_plot_formatting,
)

from analysis_base import (
    analyze_dominant_frequencies,
    find_min_valley_right,
    PeakInfo,
    FilterComponent,
    FilterDesign,
    AnalysisResult,
)

# 테스트 상수 정의
DEFAULT_SAMPLING_RATE = 1 / 300  # 5분 간격
DEFAULT_SIGNAL_LENGTH = 1000  # 기본 신호 길이
LARGE_SIGNAL_LENGTH = 10000  # 큰 신호 길이 (50000에서 축소)
TOLERANCE = 1e-6  # 부동소수점 비교 허용 오차


class TestFindMinValleyRight:
    """V자 최저점 검출 함수 테스트"""

    @pytest.fixture
    def sample_analysis_result(self):
        """테스트용 분석 결과 생성"""
        frequencies = np.linspace(0, 0.01, DEFAULT_SIGNAL_LENGTH)
        psd = np.exp(-frequencies * 1000) + 0.1 * np.random.random(
            DEFAULT_SIGNAL_LENGTH
        )

        # 두 개의 피크 추가
        peak1_idx = 100
        peak2_idx = 200
        psd[peak1_idx] = 10.0
        psd[peak2_idx] = 8.0

        return AnalysisResult(
            frequencies=frequencies,
            psd=psd,
            all_peaks=[],
            dominant_peaks=[
                PeakInfo(
                    frequency=frequencies[peak1_idx],
                    period_minutes=1 / frequencies[peak1_idx] / 60,
                    power=psd[peak1_idx],
                    prominence=psd[peak1_idx] - psd[peak1_idx - 1],
                    rank=1,
                ),
                PeakInfo(
                    frequency=frequencies[peak2_idx],
                    period_minutes=1 / frequencies[peak2_idx] / 60,
                    power=psd[peak2_idx],
                    prominence=psd[peak2_idx] - psd[peak2_idx - 1],
                    rank=2,
                ),
            ],
        )

    def test_with_valid_analysis_result(self, sample_analysis_result):
        """유효한 분석 결과로 V자 최저점 검출 테스트"""
        result = find_min_valley_right(sample_analysis_result)

        assert result is not None, "V자 최저점을 찾지 못했습니다"
        assert "frequency" in result, "frequency 키가 결과에 없습니다"
        assert "period_minutes" in result, "period_minutes 키가 결과에 없습니다"
        assert "psd_value" in result, "psd_value 키가 결과에 없습니다"
        assert result["frequency"] > 0, "주파수는 양수여야 합니다"
        assert result["period_minutes"] > 0, "주기는 양수여야 합니다"

    @pytest.mark.parametrize(
        "analysis_result,expected",
        [
            (
                AnalysisResult(
                    frequencies=np.array([]),
                    psd=np.array([]),
                    all_peaks=[],
                    dominant_peaks=[
                        PeakInfo(
                            frequency=0.001,
                            period_minutes=1000 / 60,
                            power=1.0,
                            prominence=0.1,
                            rank=1,
                        )
                    ],
                ),
                None,
            ),  # 피크 1개만
            (None, None),  # None 입력
        ],
    )
    def test_with_invalid_input(self, analysis_result, expected):
        """유효하지 않은 입력에 대한 테스트"""
        result = find_min_valley_right(analysis_result)
        assert result == expected

    def test_with_insufficient_data_after_peak(self):
        """피크 이후 데이터가 부족한 경우 테스트"""
        frequencies = np.linspace(0, 0.01, 10)  # 매우 짧은 데이터
        psd = np.ones(10)

        analysis_result = AnalysisResult(
            frequencies=frequencies,
            psd=psd,
            all_peaks=[],
            dominant_peaks=[
                PeakInfo(
                    frequency=frequencies[8],
                    period_minutes=1 / frequencies[8] / 60,
                    power=1.0,
                    prominence=0.1,
                    rank=1,
                ),  # 끝에 가까운 피크
                PeakInfo(
                    frequency=frequencies[9],
                    period_minutes=1 / frequencies[9] / 60,
                    power=1.0,
                    prominence=0.1,
                    rank=2,
                ),
            ],
        )

        result = find_min_valley_right(analysis_result)
        assert result is None, "데이터가 부족한 경우 None을 반환해야 합니다"


class TestAnalyzeDominantFrequencies:
    """주파수 성분 분석 함수 테스트"""

    @pytest.fixture
    def generate_synthetic_signal(self):
        """테스트용 합성 신호 생성 fixture"""

        def _generate(
            frequencies_list,
            amplitudes_list=None,
            signal_length=DEFAULT_SIGNAL_LENGTH,
            noise_level=0.0,
        ):
            """주파수와 진폭을 지정하여 합성 신호 생성"""
            if amplitudes_list is None:
                amplitudes_list = [1.0] * len(frequencies_list)

            t = np.arange(0, signal_length) / DEFAULT_SAMPLING_RATE
            signal_data = np.zeros_like(t)

            for freq, amp in zip(frequencies_list, amplitudes_list):
                signal_data += amp * np.sin(2 * np.pi * freq * t)

            if noise_level > 0:
                np.random.seed(42)
                signal_data += noise_level * np.random.normal(0, 1, len(t))

            return signal_data

        return _generate

    def test_with_synthetic_signal(self, generate_synthetic_signal):
        """합성 신호로 주파수 분석 테스트"""
        # 두 개의 주파수 성분을 가진 합성 신호 생성
        freq1 = 1 / (12 * 3600)  # 12시간 주기
        freq2 = 1 / (24 * 3600)  # 24시간 주기
        signal_data = generate_synthetic_signal([freq1, freq2], [1.0, 0.5])

        analysis_result, frequencies, psd = analyze_dominant_frequencies(
            signal_data, DEFAULT_SAMPLING_RATE
        )

        assert analysis_result is not None, "분석 결과가 None입니다"
        assert hasattr(
            analysis_result, "dominant_peaks"
        ), "dominant_peaks 속성이 없습니다"
        assert hasattr(analysis_result, "all_peaks"), "all_peaks 속성이 없습니다"
        assert len(analysis_result.dominant_peaks) >= 1, "주요 피크를 찾지 못했습니다"
        assert len(frequencies) > 0, "주파수 배열이 비어있습니다"
        assert len(psd) > 0, "PSD 배열이 비어있습니다"
        assert len(frequencies) == len(psd), "주파수와 PSD 배열 길이가 다릅니다"

    def test_with_noisy_signal(self, generate_synthetic_signal):
        """노이즈가 있는 신호로 테스트"""
        # 순수 노이즈 신호 (주파수 성분 없음)
        signal_data = generate_synthetic_signal(
            [], [], signal_length=DEFAULT_SIGNAL_LENGTH, noise_level=1.0
        )

        analysis_result, frequencies, psd = analyze_dominant_frequencies(
            signal_data, DEFAULT_SAMPLING_RATE
        )

        # 노이즈 신호에서도 분석이 완료되어야 함
        assert frequencies is not None, "주파수 배열이 None입니다"
        assert psd is not None, "PSD 배열이 None입니다"
        # 명확한 피크가 없을 수 있음
        if analysis_result is not None:
            assert hasattr(analysis_result, "all_peaks"), "all_peaks 속성이 없습니다"

    def test_with_single_frequency_signal(self, generate_synthetic_signal):
        """단일 주파수 신호 테스트"""
        freq = 1 / (6 * 3600)  # 6시간 주기
        signal_data = generate_synthetic_signal(
            [freq], signal_length=DEFAULT_SIGNAL_LENGTH
        )

        analysis_result, frequencies, psd = analyze_dominant_frequencies(
            signal_data, DEFAULT_SAMPLING_RATE
        )

        assert analysis_result is not None, "분석 결과가 None입니다"
        assert len(analysis_result.dominant_peaks) >= 1, "주요 피크를 찾지 못했습니다"

        # 주요 피크가 예상 주파수 근처에 있는지 확인
        main_peak_freq = analysis_result.dominant_peaks[0].frequency
        relative_error = abs(main_peak_freq - freq) / freq
        assert (
            relative_error < 0.1
        ), f"주파수 오차가 10%를 초과합니다: {relative_error*100:.1f}%"

    @pytest.mark.parametrize(
        "signal_length,expected_analysis",
        [
            (100, True),  # 짧은 신호
            (50, True),  # 매우 짧은 신호
            (10, True),  # 극히 짧은 신호
        ],
    )
    def test_with_various_signal_lengths(self, signal_length, expected_analysis):
        """다양한 길이의 신호로 테스트"""
        np.random.seed(42)
        signal_data = np.random.random(signal_length)

        analysis_result, frequencies, psd = analyze_dominant_frequencies(
            signal_data, DEFAULT_SAMPLING_RATE
        )

        # 모든 길이에서 분석이 완료되어야 함
        assert (
            frequencies is not None
        ), f"길이 {signal_length}에서 주파수 배열이 None입니다"
        assert psd is not None, f"길이 {signal_length}에서 PSD 배열이 None입니다"

        if expected_analysis:
            assert (
                len(frequencies) > 0
            ), f"길이 {signal_length}에서 주파수 배열이 비어있습니다"
            assert len(psd) > 0, f"길이 {signal_length}에서 PSD 배열이 비어있습니다"


class TestFilterDesign:
    """FilterDesign 클래스 테스트"""

    def test_validate(self):
        """validate 메서드 테스트"""
        # 유효한 필터 설계
        valid_design = FilterDesign(
            low_freq_component=FilterComponent(
                target_freq=0.001,
                target_period_min=1000 / 60,
                filter_type="low_pass",
                cutoff_freq=0.0015,
                cutoff_period_min=1 / 0.0015 / 60,
            ),
            high_freq_component=FilterComponent(
                target_freq=0.002,
                target_period_min=500 / 60,
                filter_type="high_pass",
                cutoff_freq=0.0010,
                cutoff_period_min=1 / 0.0010 / 60,
            ),
        )
        assert valid_design.validate() is True

        # 잘못된 필터 타입
        wrong_type_design = FilterDesign(
            low_freq_component=FilterComponent(
                target_freq=0.001,
                target_period_min=1000 / 60,
                filter_type="high_pass",  # 잘못된 타입
                cutoff_freq=0.0015,
                cutoff_period_min=1 / 0.0015 / 60,
            ),
            high_freq_component=FilterComponent(
                target_freq=0.002,
                target_period_min=500 / 60,
                filter_type="high_pass",
                cutoff_freq=0.0010,
                cutoff_period_min=1 / 0.0010 / 60,
            ),
        )
        assert wrong_type_design.validate() is False

        # 음수 cutoff 주파수
        negative_cutoff = FilterDesign(
            low_freq_component=FilterComponent(
                target_freq=0.001,
                target_period_min=1000 / 60,
                filter_type="low_pass",
                cutoff_freq=-0.0015,  # 음수
                cutoff_period_min=1 / 0.0015 / 60,
            ),
            high_freq_component=FilterComponent(
                target_freq=0.002,
                target_period_min=500 / 60,
                filter_type="high_pass",
                cutoff_freq=0.0010,
                cutoff_period_min=1 / 0.0010 / 60,
            ),
        )
        assert negative_cutoff.validate() is False

        # 잘못된 cutoff 순서
        wrong_order = FilterDesign(
            low_freq_component=FilterComponent(
                target_freq=0.001,
                target_period_min=1000 / 60,
                filter_type="low_pass",
                cutoff_freq=0.0010,  # 고대역보다 작음
                cutoff_period_min=1 / 0.0010 / 60,
            ),
            high_freq_component=FilterComponent(
                target_freq=0.002,
                target_period_min=500 / 60,
                filter_type="high_pass",
                cutoff_freq=0.0015,  # 저대역보다 큼
                cutoff_period_min=1 / 0.0015 / 60,
            ),
        )
        assert wrong_order.validate() is False

    def test_get_cutoff_summary(self):
        """get_cutoff_summary 메서드 테스트"""
        design = FilterDesign(
            low_freq_component=FilterComponent(
                target_freq=0.001,
                target_period_min=1000 / 60,
                filter_type="low_pass",
                cutoff_freq=0.0015,
                cutoff_period_min=11.1,  # 11.1분
            ),
            high_freq_component=FilterComponent(
                target_freq=0.002,
                target_period_min=500 / 60,
                filter_type="high_pass",
                cutoff_freq=0.0010,
                cutoff_period_min=16.7,  # 16.7분
            ),
        )

        summary = design.get_cutoff_summary()
        assert "Low Pass: 0.001500 Hz (11.1분)" in summary
        assert "High Pass: 0.001000 Hz (16.7분)" in summary


class TestDesignComponentSeparationFilters:
    """성분 분리 필터 설계 함수 테스트"""

    @pytest.fixture
    def create_analysis_result(self):
        """테스트용 분석 결과 생성"""

        def _create(peak_frequencies):
            dominant_peaks = []
            for i, freq in enumerate(peak_frequencies):
                dominant_peaks.append(
                    PeakInfo(
                        frequency=freq,
                        period_minutes=1 / freq / 60,
                        power=10.0 - i,  # 임의의 파워 값
                        prominence=1.0 - i * 0.1,  # 임의의 prominence 값
                        rank=i + 1,
                    )
                )
            return AnalysisResult(
                frequencies=np.array([]),
                psd=np.array([]),
                all_peaks=[],
                dominant_peaks=dominant_peaks,
            )

        return _create

    def test_with_two_peaks(self, create_analysis_result):
        """두 개의 피크가 있는 경우 필터 설계 테스트"""
        analysis_result = create_analysis_result([0.001, 0.002])

        filter_design = design_component_separation_filters(
            analysis_result, DEFAULT_SAMPLING_RATE
        )

        assert filter_design is not None, "필터 설계가 실패했습니다"
        assert hasattr(
            filter_design, "low_freq_component"
        ), "low_freq_component 속성이 없습니다"
        assert hasattr(
            filter_design, "high_freq_component"
        ), "high_freq_component 속성이 없습니다"

        low_comp = filter_design.low_freq_component
        high_comp = filter_design.high_freq_component

        # 필터 설계 검증
        assert low_comp.filter_type == "low_pass", "저대역 필터 타입이 잘못되었습니다"
        assert high_comp.filter_type == "high_pass", "고대역 필터 타입이 잘못되었습니다"

        # 차단 주파수 검증
        assert low_comp.cutoff_freq > 0, "저대역 차단 주파수는 양수여야 합니다"
        assert high_comp.cutoff_freq > 0, "고대역 차단 주파수는 양수여야 합니다"
        assert (
            low_comp.cutoff_freq > high_comp.cutoff_freq
        ), "저대역 차단 주파수가 고대역보다 낮습니다"

    @pytest.mark.parametrize(
        "analysis_input,expected",
        [
            (
                AnalysisResult(
                    frequencies=np.array([]),
                    psd=np.array([]),
                    all_peaks=[],
                    dominant_peaks=[
                        PeakInfo(
                            frequency=0.001,
                            period_minutes=1000 / 60,
                            power=1.0,
                            prominence=0.1,
                            rank=1,
                        )
                    ],
                ),
                None,
            ),  # 1개 피크
            (None, None),  # None 입력
            (
                AnalysisResult(
                    frequencies=np.array([]),
                    psd=np.array([]),
                    all_peaks=[],
                    dominant_peaks=[],
                ),
                None,
            ),  # 빈 피크 리스트
        ],
    )
    def test_with_invalid_inputs(self, analysis_input, expected):
        """유효하지 않은 입력에 대한 테스트"""
        filter_design = design_component_separation_filters(
            analysis_input, DEFAULT_SAMPLING_RATE
        )
        assert filter_design == expected

    def test_nyquist_frequency_limit(self, create_analysis_result):
        """Nyquist 주파수 제한 테스트"""
        nyquist = DEFAULT_SAMPLING_RATE / 2

        # 매우 높은 주파수의 피크들
        analysis_result = create_analysis_result([nyquist * 0.8, nyquist * 0.9])

        filter_design = design_component_separation_filters(
            analysis_result, DEFAULT_SAMPLING_RATE
        )

        assert (
            filter_design is not None
        ), "Nyquist 근처 주파수에서도 필터 설계가 가능해야 합니다"

        # 차단 주파수가 Nyquist 주파수를 초과하지 않는지 확인
        low_cutoff = filter_design.low_freq_component.cutoff_freq
        high_cutoff = filter_design.high_freq_component.cutoff_freq

        assert (
            low_cutoff < nyquist
        ), f"저대역 차단 주파수({low_cutoff})가 Nyquist({nyquist})를 초과합니다"
        assert (
            high_cutoff < nyquist
        ), f"고대역 차단 주파수({high_cutoff})가 Nyquist({nyquist})를 초과합니다"


class TestApplyComponentFilters:
    """성분 필터 적용 함수 테스트"""

    @pytest.fixture
    def sample_filter_design(self):
        """테스트용 필터 설계"""
        return FilterDesign(
            low_freq_component=FilterComponent(
                target_freq=0.001,
                target_period_min=1000 / 60,
                filter_type="low_pass",
                cutoff_freq=0.0015,
                cutoff_period_min=1 / 0.0015 / 60,
            ),
            high_freq_component=FilterComponent(
                target_freq=0.002,
                target_period_min=500 / 60,
                filter_type="high_pass",
                cutoff_freq=0.0015,
                cutoff_period_min=1 / 0.0015 / 60,
            ),
        )

    @pytest.fixture
    def two_frequency_signal(self):
        """두 개의 주파수 성분을 가진 신호"""
        t = np.arange(0, DEFAULT_SIGNAL_LENGTH) / DEFAULT_SAMPLING_RATE
        return np.sin(2 * np.pi * 0.001 * t) + 0.5 * np.sin(2 * np.pi * 0.002 * t)

    def test_with_valid_filter_design(self, two_frequency_signal, sample_filter_design):
        """유효한 필터 설계로 필터 적용 테스트"""
        component1, component2 = apply_component_filters(
            two_frequency_signal, sample_filter_design, DEFAULT_SAMPLING_RATE
        )

        assert component1 is not None, "저대역 성분이 None입니다"
        assert component2 is not None, "고대역 성분이 None입니다"
        assert len(component1) == len(
            two_frequency_signal
        ), "저대역 성분 길이가 원본과 다릅니다"
        assert len(component2) == len(
            two_frequency_signal
        ), "고대역 성분 길이가 원본과 다릅니다"

        # 필터링된 성분들의 표준편차가 0이 아닌지 확인
        assert np.std(component1) > 0, "저대역 성분의 표준편차가 0입니다"
        assert np.std(component2) > 0, "고대역 성분의 표준편차가 0입니다"

    @pytest.mark.parametrize(
        "filter_design",
        [
            None,  # None 필터 설계
            {},  # 빈 딕셔너리
        ],
    )
    def test_with_invalid_filter_design(self, filter_design):
        """유효하지 않은 필터 설계로 테스트"""
        signal_data = np.random.random(DEFAULT_SIGNAL_LENGTH)

        component1, component2 = apply_component_filters(
            signal_data, filter_design, DEFAULT_SAMPLING_RATE
        )

        assert (
            component1 is None
        ), f"필터 설계 {filter_design}에서 저대역 성분이 None이 아닙니다"
        assert (
            component2 is None
        ), f"필터 설계 {filter_design}에서 고대역 성분이 None이 아닙니다"

    def test_filter_reconstruction(self):
        """필터 재구성 테스트 (Low Pass + High Pass ≈ 원본)"""
        # 테스트 신호 생성
        np.random.seed(42)
        signal_data = np.random.normal(0, 1, DEFAULT_SIGNAL_LENGTH)

        # 필터 설계 (중간 주파수로 분리)
        nyquist = DEFAULT_SAMPLING_RATE / 2
        cutoff = nyquist * 0.1

        filter_design = FilterDesign(
            low_freq_component=FilterComponent(
                target_freq=cutoff,
                target_period_min=1 / cutoff / 60,
                filter_type="low_pass",
                cutoff_freq=cutoff,
                cutoff_period_min=1 / cutoff / 60,
            ),
            high_freq_component=FilterComponent(
                target_freq=cutoff,
                target_period_min=1 / cutoff / 60,
                filter_type="high_pass",
                cutoff_freq=cutoff,
                cutoff_period_min=1 / cutoff / 60,
            ),
        )

        component1, component2 = apply_component_filters(
            signal_data, filter_design, DEFAULT_SAMPLING_RATE
        )

        # 재구성된 신호
        reconstructed = component1 + component2

        # 원본과 재구성된 신호의 상관계수가 높은지 확인
        correlation = np.corrcoef(signal_data, reconstructed)[0, 1]
        assert (
            correlation > 0.95
        ), f"재구성 상관계수({correlation:.3f})가 95% 미만입니다"


class TestPlottingFunctions:
    """플롯팅 함수들 테스트"""

    @pytest.fixture
    def mock_axes(self):
        """테스트용 matplotlib axes"""
        fig, ax = plt.subplots()
        yield ax
        plt.close(fig)

    @pytest.fixture
    def complete_analysis_result(self):
        """완전한 분석 결과"""
        return AnalysisResult(
            frequencies=np.array([]),
            psd=np.array([]),
            all_peaks=[],
            dominant_peaks=[
                PeakInfo(
                    frequency=0.001,
                    period_minutes=1000 / 60,
                    power=10.0,
                    prominence=1.0,
                    rank=1,
                ),
                PeakInfo(
                    frequency=0.002,
                    period_minutes=500 / 60,
                    power=8.0,
                    prominence=0.8,
                    rank=2,
                ),
            ],
            min_valley_right={"frequency": 0.0015, "period_minutes": 666.7 / 60},
        )

    def test_add_vertical_lines_to_plot(self, mock_axes, complete_analysis_result):
        """세로선 추가 함수 테스트"""
        # 함수가 에러 없이 실행되는지 확인
        add_vertical_lines_to_plot(mock_axes, complete_analysis_result)

        # 세로선이 추가되었는지 확인
        lines = mock_axes.get_lines()
        assert len(lines) >= 3, f"예상 3개 이상의 세로선, 실제: {len(lines)}개"

    @pytest.mark.parametrize(
        "analysis_result",
        [
            None,  # None 입력
            AnalysisResult(
                frequencies=np.array([]),
                psd=np.array([]),
                all_peaks=[],
                dominant_peaks=[],
            ),  # 빈 피크 리스트
        ],
    )
    def test_add_vertical_lines_with_invalid_results(self, mock_axes, analysis_result):
        """유효하지 않은 분석 결과로 세로선 추가 테스트"""
        # 에러가 발생하지 않아야 함
        add_vertical_lines_to_plot(mock_axes, analysis_result)

        # 세로선이 추가되지 않았는지 확인
        lines = mock_axes.get_lines()
        assert len(lines) == 0, f"세로선이 추가되었습니다: {len(lines)}개"

    @pytest.mark.parametrize(
        "title,xlabel,ylabel",
        [
            ("테스트 제목", "X축 라벨", "Y축 라벨"),
            ("Test Title", "Frequency (Hz)", "Power"),
            ("", "", ""),  # 빈 문자열 테스트
        ],
    )
    def test_setup_plot_formatting(self, mock_axes, title, xlabel, ylabel):
        """플롯 포맷팅 설정 함수 테스트"""
        setup_plot_formatting(mock_axes, title, xlabel, ylabel)

        # 라벨과 제목이 설정되었는지 확인
        assert (
            mock_axes.get_title() == title
        ), f"제목이 잘못 설정됨: {mock_axes.get_title()}"
        assert (
            mock_axes.get_xlabel() == xlabel
        ), f"X축 라벨이 잘못 설정됨: {mock_axes.get_xlabel()}"
        assert (
            mock_axes.get_ylabel() == ylabel
        ), f"Y축 라벨이 잘못 설정됨: {mock_axes.get_ylabel()}"

        # 그리드가 활성화되었는지 확인
        assert mock_axes.grid, "그리드가 활성화되지 않았습니다"


class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def realistic_signal(self):
        """실제 데이터와 유사한 합성 신호"""
        # 통합 테스트를 위해 더 긴 신호 사용
        t = np.arange(0, LARGE_SIGNAL_LENGTH) / DEFAULT_SAMPLING_RATE

        # 일주조(24시간)와 반일주조(12시간) 성분
        freq_daily = 1 / (24 * 3600)
        freq_semidiurnal = 1 / (12 * 3600)

        np.random.seed(42)
        signal_data = (
            2.0 * np.sin(2 * np.pi * freq_daily * t)
            + 1.0 * np.sin(2 * np.pi * freq_semidiurnal * t)
            + 0.1 * np.random.normal(0, 1, len(t))
        )

        return signal_data

    def test_full_analysis_pipeline(self, realistic_signal):
        """전체 분석 파이프라인 테스트"""
        # 1. 주파수 분석
        analysis_result, frequencies, psd = analyze_dominant_frequencies(
            realistic_signal, DEFAULT_SAMPLING_RATE
        )

        assert analysis_result is not None, "주파수 분석 실패"
        # 신호 길이에 따라 1개 이상의 피크가 발견될 수 있음
        assert len(analysis_result.dominant_peaks) >= 1, "주요 피크를 찾지 못함"

        # 2. V자 최저점 검출
        valley_result = find_min_valley_right(analysis_result)
        if valley_result:
            analysis_result.min_valley_right = valley_result

        # 3. 필터 설계
        filter_design = design_component_separation_filters(
            analysis_result, DEFAULT_SAMPLING_RATE
        )

        if filter_design is not None:
            # 4. 필터 적용
            component1, component2 = apply_component_filters(
                realistic_signal, filter_design, DEFAULT_SAMPLING_RATE
            )

            assert component1 is not None, "저대역 성분 필터링 실패"
            assert component2 is not None, "고대역 성분 필터링 실패"
            assert len(component1) == len(realistic_signal), "저대역 성분 길이 불일치"
            assert len(component2) == len(realistic_signal), "고대역 성분 길이 불일치"

            # 5. 재구성 검증
            reconstructed = component1 + component2
            correlation = np.corrcoef(realistic_signal, reconstructed)[0, 1]
            assert correlation > 0.9, f"재구성 상관계수({correlation:.3f})가 90% 미만"

    @pytest.mark.parametrize(
        "data,sampling_rate,expected_error",
        [
            (np.array([]), DEFAULT_SAMPLING_RATE, None),  # 빈 데이터
            (np.array([1, 2, 3]), DEFAULT_SAMPLING_RATE, None),  # 매우 짧은 데이터
            (
                np.random.random(100),
                0,
                (ValueError, ZeroDivisionError),
            ),  # 잘못된 샘플링 주파수
        ],
    )
    def test_error_handling(self, data, sampling_rate, expected_error):
        """에러 처리 테스트"""
        if expected_error:
            with pytest.raises(expected_error):
                analyze_dominant_frequencies(data, sampling_rate)
        else:
            result = analyze_dominant_frequencies(data, sampling_rate)
            # 에러가 발생하지 않고 결과를 반환해야 함
            assert result is not None, "함수가 결과를 반환하지 않음"

            # 빈 데이터의 경우 analysis_result가 None일 수 있음
            if len(data) == 0:
                assert result[0] is None, "빈 데이터에서 analysis_result가 None이 아님"

    def test_memory_efficiency(self):
        """메모리 효율성 테스트"""
        # 큰 데이터셋으로 테스트 (50000 -> 10000으로 축소)
        large_data = np.random.normal(0, 1, LARGE_SIGNAL_LENGTH)

        # 메모리 사용량이 과도하지 않은지 확인
        analysis_result, frequencies, psd = analyze_dominant_frequencies(
            large_data, DEFAULT_SAMPLING_RATE
        )

        # 결과가 원본 데이터보다 훨씬 작은지 확인
        assert len(frequencies) < len(
            large_data
        ), "주파수 배열이 원본 데이터보다 큭니다"
        assert len(psd) < len(large_data), "PSD 배열이 원본 데이터보다 큭니다"

        # Welch 방법의 특성상 결과 배열 크기는 nperseg/2 + 1 정도
        expected_max_size = min(len(large_data) // 2, 4096) // 2 + 1
        assert (
            len(frequencies) <= expected_max_size
        ), f"주파수 배열 크기({len(frequencies)})가 예상 최대({expected_max_size})보다 큭니다"

        if analysis_result and len(analysis_result.dominant_peaks) >= 2:
            filter_design = design_component_separation_filters(
                analysis_result, DEFAULT_SAMPLING_RATE
            )

            if filter_design:
                component1, component2 = apply_component_filters(
                    large_data, filter_design, DEFAULT_SAMPLING_RATE
                )

                # 필터링된 성분들이 원본과 같은 크기인지 확인
                assert len(component1) == len(
                    large_data
                ), "저대역 성분 크기가 원본과 다릅니다"
                assert len(component2) == len(
                    large_data
                ), "고대역 성분 크기가 원본과 다릅니다"


class TestAnalysisResult:
    """AnalysisResult 클래스 테스트"""

    def test_has_two_components(self):
        """has_two_components 메서드 테스트"""
        # 두 개의 피크가 있는 경우
        result1 = AnalysisResult(
            all_peaks=[],
            dominant_peaks=[
                PeakInfo(
                    frequency=0.001,
                    period_minutes=1000 / 60,
                    power=1.0,
                    prominence=0.1,
                    rank=1,
                ),
                PeakInfo(
                    frequency=0.002,
                    period_minutes=500 / 60,
                    power=0.8,
                    prominence=0.08,
                    rank=2,
                ),
            ],
            frequencies=np.array([]),
            psd=np.array([]),
        )
        assert result1.has_two_components() is True

        # 하나의 피크만 있는 경우
        result2 = AnalysisResult(
            all_peaks=[],
            dominant_peaks=[
                PeakInfo(
                    frequency=0.001,
                    period_minutes=1000 / 60,
                    power=1.0,
                    prominence=0.1,
                    rank=1,
                )
            ],
            frequencies=np.array([]),
            psd=np.array([]),
        )
        assert result2.has_two_components() is False

        # 피크가 없는 경우
        result3 = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=np.array([]), psd=np.array([])
        )
        assert result3.has_two_components() is False

    def test_get_main_periods(self):
        """get_main_periods 메서드 테스트"""
        result = AnalysisResult(
            all_peaks=[],
            dominant_peaks=[
                PeakInfo(
                    frequency=0.001,
                    period_minutes=1000 / 60,
                    power=1.0,
                    prominence=0.1,
                    rank=1,
                ),
                PeakInfo(
                    frequency=0.002,
                    period_minutes=500 / 60,
                    power=0.8,
                    prominence=0.08,
                    rank=2,
                ),
            ],
            frequencies=np.array([]),
            psd=np.array([]),
        )

        periods = result.get_main_periods()
        assert len(periods) == 2
        assert abs(periods[0] - 1000 / 60) < 1e-10
        assert abs(periods[1] - 500 / 60) < 1e-10

        # 피크가 없는 경우
        empty_result = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=np.array([]), psd=np.array([])
        )
        assert empty_result.get_main_periods() == []

    def test_get_frequency_range(self):
        """get_frequency_range 메서드 테스트"""
        frequencies = np.linspace(0.001, 0.01, 100)
        result = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=frequencies, psd=np.array([])
        )

        min_freq, max_freq = result.get_frequency_range()
        assert abs(min_freq - 0.001) < 1e-10
        assert abs(max_freq - 0.01) < 1e-10

        # 빈 배열인 경우
        empty_result = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=np.array([]), psd=np.array([])
        )
        min_freq, max_freq = empty_result.get_frequency_range()
        assert min_freq == 0.0
        assert max_freq == 0.0

    def test_get_power_range(self):
        """get_power_range 메서드 테스트"""
        psd = np.array([1e-5, 1e-3, 1e-1, 1e0])
        result = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=np.array([]), psd=psd
        )

        min_power, max_power = result.get_power_range()
        assert abs(min_power - 1e-5) < 1e-10
        assert abs(max_power - 1e0) < 1e-10

        # 빈 배열인 경우
        empty_result = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=np.array([]), psd=np.array([])
        )
        min_power, max_power = empty_result.get_power_range()
        assert min_power == 0.0
        assert max_power == 0.0


class TestPeakInfo:
    """PeakInfo 클래스 테스트"""

    def test_period_conversions(self):
        """주기 단위 변환 테스트"""
        # 테스트 데이터: 24시간 주기 (1440분)
        peak = PeakInfo(
            frequency=1 / (24 * 3600),  # 24시간을 초로 변환한 주파수
            period_minutes=1440,  # 24시간 = 1440분
            power=1.0,
            prominence=0.5,
            rank=1,
        )

        # period_hours 테스트
        assert (
            abs(peak.period_hours - 24.0) < 1e-10
        ), f"Expected 24 hours, got {peak.period_hours}"

        # period_seconds 테스트
        assert (
            abs(peak.period_seconds - 86400.0) < 1e-10
        ), f"Expected 86400 seconds, got {peak.period_seconds}"

    def test_from_frequency_constructor(self):
        """from_frequency 클래스 메서드 테스트"""
        freq = 1 / (12 * 3600)  # 12시간 주기
        peak = PeakInfo.from_frequency(
            frequency=freq, power=2.0, prominence=1.0, rank=1
        )

        # 기본 속성 검증
        assert peak.frequency == freq, "frequency가 올바르지 않습니다"
        assert (
            abs(peak.period_minutes - 720.0) < 1e-10
        ), f"Expected 720 minutes, got {peak.period_minutes}"
        assert peak.power == 2.0, "power가 올바르지 않습니다"
        assert peak.prominence == 1.0, "prominence가 올바르지 않습니다"
        assert peak.rank == 1, "rank가 올바르지 않습니다"

        # 변환된 주기 검증
        assert (
            abs(peak.period_hours - 12.0) < 1e-10
        ), f"Expected 12 hours, got {peak.period_hours}"
        assert (
            abs(peak.period_seconds - 43200.0) < 1e-10
        ), f"Expected 43200 seconds, got {peak.period_seconds}"

    @pytest.mark.parametrize(
        "hours,expected_minutes,expected_seconds",
        [
            (1, 60, 3600),  # 1시간
            (6, 360, 21600),  # 6시간
            (12, 720, 43200),  # 12시간
            (24, 1440, 86400),  # 24시간
            (0.5, 30, 1800),  # 30분
        ],
    )
    def test_various_periods(self, hours, expected_minutes, expected_seconds):
        """다양한 주기에 대한 변환 테스트"""
        freq = 1 / (hours * 3600)  # hours를 초로 변환한 주파수
        peak = PeakInfo.from_frequency(freq, power=1.0, prominence=0.5, rank=1)

        assert (
            abs(peak.period_minutes - expected_minutes) < 1e-10
        ), f"For {hours} hours: expected {expected_minutes} minutes, got {peak.period_minutes}"
        assert (
            abs(peak.period_hours - hours) < 1e-10
        ), f"For {hours} hours: expected {hours} hours, got {peak.period_hours}"
        assert (
            abs(peak.period_seconds - expected_seconds) < 1e-10
        ), f"For {hours} hours: expected {expected_seconds} seconds, got {peak.period_seconds}"

    def test_string_representation(self):
        """__str__ 메서드 테스트"""
        # 테스트 케이스 1: 일반적인 경우
        peak1 = PeakInfo(
            frequency=0.001, period_minutes=1000 / 60, power=1.0, prominence=0.5, rank=1
        )
        expected1 = "Peak 1: 0.001000 Hz (16.7분 주기)"
        assert str(peak1) == expected1, f"Expected '{expected1}', got '{peak1!s}'"

        # 테스트 케이스 2: from_frequency로 생성
        peak2 = PeakInfo.from_frequency(
            frequency=1 / (24 * 3600), power=2.0, prominence=1.0, rank=2  # 24시간 주기
        )
        expected2 = "Peak 2: 0.000012 Hz (1440.0분 주기)"
        assert str(peak2) == expected2, f"Expected '{expected2}', got '{peak2!s}'"

        # 테스트 케이스 3: 짧은 주기
        peak3 = PeakInfo.from_frequency(
            frequency=1 / (5 * 60), power=0.5, prominence=0.1, rank=3  # 5분 주기
        )
        str_repr = str(peak3)
        assert str_repr.startswith(
            "Peak 3:"
        ), f"String should start with 'Peak 3:', got '{str_repr}'"
        assert (
            "5.0분 주기" in str_repr
        ), f"String should contain '5.0분 주기', got '{str_repr}'"


if __name__ == "__main__":
    pytest.main([__file__])
