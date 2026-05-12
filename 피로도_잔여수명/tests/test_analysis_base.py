"""
analysis_base.py 모듈 단위 테스트
"""

import pytest
import numpy as np
from numpy.typing import NDArray
import os

from analysis_base import (
    PeakInfo,
    FilterComponent,
    FilterDesign,
    AnalysisResult,
    find_min_valley_right,
    analyze_dominant_frequencies,
)


class TestPeakInfo:
    """PeakInfo 데이터 클래스 테스트"""

    def test_peak_info_creation(self):
        """PeakInfo 객체 생성 테스트"""
        peak = PeakInfo(
            frequency=0.001, period_minutes=16.667, power=100.0, prominence=50.0, rank=1
        )

        assert peak.frequency == 0.001
        assert peak.period_minutes == 16.667
        assert peak.power == 100.0
        assert peak.prominence == 50.0
        assert peak.rank == 1

    def test_peak_info_properties(self):
        """PeakInfo 속성 테스트"""
        peak = PeakInfo(
            frequency=0.001, period_minutes=60.0, power=100.0, prominence=50.0, rank=1
        )

        assert peak.period_hours == 1.0
        assert peak.period_seconds == 3600.0

    def test_from_frequency_constructor(self):
        """from_frequency 클래스 메서드 테스트"""
        frequency = 0.001  # Hz
        power = 100.0
        prominence = 50.0
        rank = 1

        peak = PeakInfo.from_frequency(frequency, power, prominence, rank)

        assert peak.frequency == frequency
        assert pytest.approx(peak.period_minutes, rel=1e-6) == 1 / frequency / 60
        assert peak.power == power
        assert peak.prominence == prominence
        assert peak.rank == rank

    def test_string_representation(self):
        """__str__ 메서드 테스트"""
        peak = PeakInfo(
            frequency=0.001, period_minutes=16.667, power=100.0, prominence=50.0, rank=1
        )

        str_repr = str(peak)
        assert "Peak 1" in str_repr
        assert "0.001000 Hz" in str_repr
        assert "16.7분 주기" in str_repr


class TestFilterComponent:
    """FilterComponent 데이터 클래스 테스트"""

    def test_filter_component_creation(self):
        """FilterComponent 객체 생성 테스트"""
        component = FilterComponent(
            target_freq=0.001,
            target_period_min=16.667,
            filter_type="low_pass",
            cutoff_freq=0.0015,
            cutoff_period_min=11.111,
        )

        assert component.target_freq == 0.001
        assert component.target_period_min == 16.667
        assert component.filter_type == "low_pass"
        assert component.cutoff_freq == 0.0015
        assert component.cutoff_period_min == 11.111


class TestFilterDesign:
    """FilterDesign 데이터 클래스 테스트"""

    def test_filter_design_creation(self):
        """FilterDesign 객체 생성 테스트"""
        low_component = FilterComponent(
            target_freq=0.001,
            target_period_min=16.667,
            filter_type="low_pass",
            cutoff_freq=0.0015,
            cutoff_period_min=11.111,
        )

        high_component = FilterComponent(
            target_freq=0.002,
            target_period_min=8.333,
            filter_type="high_pass",
            cutoff_freq=0.0005,
            cutoff_period_min=33.333,
        )

        design = FilterDesign(
            low_freq_component=low_component, high_freq_component=high_component
        )

        assert design.low_freq_component == low_component
        assert design.high_freq_component == high_component

    def test_validate_valid_design(self):
        """validate 메서드 - 유효한 설계 테스트"""
        low_component = FilterComponent(
            target_freq=0.001,
            target_period_min=16.667,
            filter_type="low_pass",
            cutoff_freq=0.0015,
            cutoff_period_min=11.111,
        )

        high_component = FilterComponent(
            target_freq=0.002,
            target_period_min=8.333,
            filter_type="high_pass",
            cutoff_freq=0.0005,
            cutoff_period_min=33.333,
        )

        design = FilterDesign(
            low_freq_component=low_component, high_freq_component=high_component
        )

        assert design.validate() is True

    def test_validate_invalid_filter_types(self):
        """validate 메서드 - 잘못된 필터 타입 테스트"""
        # 저대역이 high_pass인 경우
        low_component = FilterComponent(
            target_freq=0.001,
            target_period_min=16.667,
            filter_type="high_pass",  # 잘못된 타입
            cutoff_freq=0.0015,
            cutoff_period_min=11.111,
        )

        high_component = FilterComponent(
            target_freq=0.002,
            target_period_min=8.333,
            filter_type="high_pass",
            cutoff_freq=0.0005,
            cutoff_period_min=33.333,
        )

        design = FilterDesign(
            low_freq_component=low_component, high_freq_component=high_component
        )

        assert design.validate() is False

    def test_validate_invalid_cutoff_frequencies(self):
        """validate 메서드 - 잘못된 차단 주파수 테스트"""
        # 저대역 cutoff이 고대역 cutoff보다 작은 경우
        low_component = FilterComponent(
            target_freq=0.001,
            target_period_min=16.667,
            filter_type="low_pass",
            cutoff_freq=0.0005,  # 고대역보다 작음
            cutoff_period_min=33.333,
        )

        high_component = FilterComponent(
            target_freq=0.002,
            target_period_min=8.333,
            filter_type="high_pass",
            cutoff_freq=0.0015,  # 저대역보다 큼
            cutoff_period_min=11.111,
        )

        design = FilterDesign(
            low_freq_component=low_component, high_freq_component=high_component
        )

        assert design.validate() is False

    def test_get_cutoff_summary(self):
        """get_cutoff_summary 메서드 테스트"""
        low_component = FilterComponent(
            target_freq=0.001,
            target_period_min=16.667,
            filter_type="low_pass",
            cutoff_freq=0.0015,
            cutoff_period_min=11.111,
        )

        high_component = FilterComponent(
            target_freq=0.002,
            target_period_min=8.333,
            filter_type="high_pass",
            cutoff_freq=0.0005,
            cutoff_period_min=33.333,
        )

        design = FilterDesign(
            low_freq_component=low_component, high_freq_component=high_component
        )

        summary = design.get_cutoff_summary()
        assert "Low Pass: 0.001500 Hz" in summary
        assert "11.1분" in summary
        assert "High Pass: 0.000500 Hz" in summary
        assert "33.3분" in summary


class TestAnalysisResult:
    """AnalysisResult 데이터 클래스 테스트"""

    def test_analysis_result_creation(self):
        """AnalysisResult 객체 생성 테스트"""
        peak1 = PeakInfo.from_frequency(0.001, 100.0, 50.0, 1)
        peak2 = PeakInfo.from_frequency(0.002, 80.0, 40.0, 2)

        frequencies = np.array([0.0, 0.001, 0.002, 0.003])
        psd = np.array([0.0, 100.0, 80.0, 10.0])

        result = AnalysisResult(
            all_peaks=[peak1, peak2],
            dominant_peaks=[peak1, peak2],
            frequencies=frequencies,
            psd=psd,
            min_valley_right={
                "frequency": 0.0025,
                "period_minutes": 6.667,
                "psd_value": 5.0,
            },
        )

        assert len(result.all_peaks) == 2
        assert len(result.dominant_peaks) == 2
        assert np.array_equal(result.frequencies, frequencies)
        assert np.array_equal(result.psd, psd)
        assert result.min_valley_right is not None

    def test_has_two_components(self):
        """has_two_components 메서드 테스트"""
        peak1 = PeakInfo.from_frequency(0.001, 100.0, 50.0, 1)
        peak2 = PeakInfo.from_frequency(0.002, 80.0, 40.0, 2)

        # 두 개의 주요 성분이 있는 경우
        result = AnalysisResult(
            all_peaks=[peak1, peak2],
            dominant_peaks=[peak1, peak2],
            frequencies=np.array([]),
            psd=np.array([]),
        )
        assert result.has_two_components() is True

        # 한 개의 주요 성분만 있는 경우
        result_single = AnalysisResult(
            all_peaks=[peak1],
            dominant_peaks=[peak1],
            frequencies=np.array([]),
            psd=np.array([]),
        )
        assert result_single.has_two_components() is False

    def test_get_main_periods(self):
        """get_main_periods 메서드 테스트"""
        peak1 = PeakInfo(
            frequency=0.001, period_minutes=16.667, power=100.0, prominence=50.0, rank=1
        )
        peak2 = PeakInfo(
            frequency=0.002, period_minutes=8.333, power=80.0, prominence=40.0, rank=2
        )

        result = AnalysisResult(
            all_peaks=[peak1, peak2],
            dominant_peaks=[peak1, peak2],
            frequencies=np.array([]),
            psd=np.array([]),
        )

        periods = result.get_main_periods()
        assert periods == [16.667, 8.333]

    def test_get_frequency_range(self):
        """get_frequency_range 메서드 테스트"""
        frequencies = np.array([0.001, 0.002, 0.003, 0.004, 0.005])

        result = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=frequencies, psd=np.array([])
        )

        freq_min, freq_max = result.get_frequency_range()
        assert freq_min == 0.001
        assert freq_max == 0.005

        # 빈 배열의 경우
        result_empty = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=np.array([]), psd=np.array([])
        )

        freq_min, freq_max = result_empty.get_frequency_range()
        assert freq_min == 0.0
        assert freq_max == 0.0

    def test_get_power_range(self):
        """get_power_range 메서드 테스트"""
        psd = np.array([10.0, 100.0, 50.0, 20.0, 5.0])

        result = AnalysisResult(
            all_peaks=[], dominant_peaks=[], frequencies=np.array([]), psd=psd
        )

        power_min, power_max = result.get_power_range()
        assert power_min == 5.0
        assert power_max == 100.0


class TestFindMinValleyRight:
    """find_min_valley_right 함수 테스트"""

    def test_with_valid_data(self):
        """정상적인 데이터로 테스트"""
        # 두 개의 피크와 그 사이의 valley를 가진 데이터 생성
        frequencies = np.linspace(0.0001, 0.01, 100)
        psd = np.zeros(100)

        # 첫 번째 피크 (인덱스 20)
        psd[20] = 100.0
        # 두 번째 피크 (인덱스 60)
        psd[60] = 80.0
        # Valley (인덱스 65에서 다시 올라감)
        psd[61:65] = [70, 60, 50, 45]
        psd[65] = 55

        peak1 = PeakInfo.from_frequency(frequencies[20], psd[20], 50.0, 1)
        peak2 = PeakInfo.from_frequency(frequencies[60], psd[60], 40.0, 2)

        result = AnalysisResult(
            all_peaks=[peak1, peak2],
            dominant_peaks=[peak1, peak2],
            frequencies=frequencies,
            psd=psd,
        )

        valley = find_min_valley_right(result)

        assert valley is not None
        assert "frequency" in valley
        assert "period_minutes" in valley
        assert "psd_value" in valley
        assert valley["psd_value"] == 45.0  # Valley 지점의 값

    def test_with_insufficient_peaks(self):
        """피크가 부족한 경우 테스트"""
        frequencies = np.linspace(0.0001, 0.01, 100)
        psd = np.ones(100) * 10.0

        peak1 = PeakInfo.from_frequency(frequencies[20], psd[20], 50.0, 1)

        result = AnalysisResult(
            all_peaks=[peak1], dominant_peaks=[peak1], frequencies=frequencies, psd=psd
        )

        valley = find_min_valley_right(result)
        assert valley is None

    def test_with_none_input(self):
        """None 입력 테스트"""
        valley = find_min_valley_right(None)
        assert valley is None


class TestAnalyzeDominantFrequencies:
    """analyze_dominant_frequencies 함수 테스트"""

    def test_with_synthetic_signal(self):
        """합성 신호로 테스트"""
        # 두 개의 주파수 성분을 가진 신호 생성
        sampling_rate = 1.0  # Hz
        t = np.arange(0, 1000, 1 / sampling_rate)

        # 0.01 Hz와 0.02 Hz 성분
        signal = np.sin(2 * np.pi * 0.01 * t) + 0.5 * np.sin(2 * np.pi * 0.02 * t)

        result, frequencies, psd = analyze_dominant_frequencies(signal, sampling_rate)

        assert result is not None
        assert len(frequencies) > 0
        assert len(psd) > 0
        assert len(result.dominant_peaks) >= 1

    def test_with_constant_signal(self):
        """상수 신호로 테스트"""
        signal = np.ones(1000)
        sampling_rate = 1.0

        result, frequencies, psd = analyze_dominant_frequencies(signal, sampling_rate)

        # 상수 신호는 DC 성분만 가지므로 피크가 없을 수 있음
        assert frequencies is not None
        assert psd is not None

    def test_with_empty_signal(self):
        """빈 신호로 테스트"""
        signal = np.array([])
        sampling_rate = 1.0

        result, frequencies, psd = analyze_dominant_frequencies(signal, sampling_rate)

        assert result is None or len(result.all_peaks) == 0
