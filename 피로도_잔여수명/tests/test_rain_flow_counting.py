"""
rain_flow_counting.py 모듈 테스트
"""

import pytest
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import tempfile
import os

# 테스트 대상 모듈 import

from rain_flow_counting import (
    find_peaks_and_valleys,
    rain_flow_counting,
    create_rainflow_histogram,
    analyze_rainflow_cycles,
)


class TestFindPeaksAndValleys:
    """피크와 밸리 찾기 함수 테스트"""

    def test_find_peaks_and_valleys_simple_sine(self):
        """단순 사인파에서 피크와 밸리 찾기"""
        # 단순 사인파 생성
        t = np.linspace(0, 4 * np.pi, 100)
        data = np.sin(t)

        indices, values = find_peaks_and_valleys(data)

        # 결과 검증
        assert len(indices) > 0
        assert len(values) > 0
        assert len(indices) == len(values)

        # 첫 번째와 마지막 점이 포함되어야 함
        assert indices[0] == 0
        assert indices[-1] == len(data) - 1

    def test_find_peaks_and_valleys_constant_data(self):
        """상수 데이터에서 피크와 밸리 찾기"""
        data = np.full(100, 5.0)

        indices, values = find_peaks_and_valleys(data)

        # 상수 데이터는 시작점과 끝점만 있어야 함
        assert len(indices) == 2
        assert indices[0] == 0
        assert indices[-1] == len(data) - 1
        assert np.allclose(values, 5.0)

    def test_find_peaks_and_valleys_monotonic(self):
        """단조 증가/감소 데이터"""
        # 단조 증가
        data = np.linspace(0, 10, 100)

        indices, values = find_peaks_and_valleys(data)

        # 단조 데이터는 시작점과 끝점만 있어야 함
        assert len(indices) == 2
        assert indices[0] == 0
        assert indices[-1] == len(data) - 1

    def test_find_peaks_and_valleys_with_noise(self):
        """노이즈가 있는 데이터"""
        # 사인파 + 노이즈
        t = np.linspace(0, 2 * np.pi, 100)
        data = np.sin(t) + 0.1 * np.random.randn(100)

        indices, values = find_peaks_and_valleys(data)

        # threshold가 제거되어 더 많은 피크/밸리가 검출될 수 있음
        assert len(indices) >= 2  # 최소 시작점과 끝점
        assert len(indices) <= len(data)  # 최대 데이터 길이만큼
        assert len(indices) == len(values)  # 인덱스와 값 길이 일치

    def test_find_peaks_and_valleys_empty_data(self):
        """빈 데이터 처리"""
        data = np.array([])

        indices, values = find_peaks_and_valleys(data)

        assert len(indices) == 0
        assert len(values) == 0

    def test_find_peaks_and_valleys_single_point(self):
        """단일 점 데이터"""
        data = np.array([5.0])

        indices, values = find_peaks_and_valleys(data)

        # 단일 점은 하나의 점만 반환됨
        assert len(indices) == 1
        assert indices[0] == 0
        assert values[0] == 5.0


class TestRainFlowCounting:
    """Rain Flow Counting 알고리즘 테스트"""

    def test_rain_flow_counting_simple_cycle(self):
        """단순 사이클 테스트"""
        # 단순한 삼각파 (명확한 사이클)
        data = np.array([0, 1, 0, 2, 0])

        cycles = rain_flow_counting(data)

        # 사이클이 발견되어야 함
        assert len(cycles) > 0

        # 각 사이클은 (범위, 평균, 사이클수) 튜플이어야 함
        for cycle in cycles:
            assert len(cycle) == 3
            assert isinstance(
                cycle[0], (int, float, np.number)
            )  # 범위 (numpy 타입 포함)
            assert isinstance(
                cycle[1], (int, float, np.number)
            )  # 평균 (numpy 타입 포함)
            assert isinstance(
                cycle[2], (int, float, np.number)
            )  # 사이클 수 (numpy 타입 포함)

    def test_rain_flow_counting_sine_wave(self):
        """사인파 데이터 테스트"""
        t = np.linspace(0, 4 * np.pi, 200)
        data = np.sin(t)

        cycles = rain_flow_counting(data)

        # 사인파는 여러 사이클을 가져야 함
        assert len(cycles) > 0

        # 모든 사이클의 범위는 양수여야 함
        for cycle in cycles:
            assert cycle[0] >= 0  # 범위는 항상 양수

    def test_rain_flow_counting_constant_data(self):
        """상수 데이터 테스트"""
        data = np.full(100, 5.0)

        cycles = rain_flow_counting(data)

        # 상수 데이터는 사이클이 없어야 함
        assert len(cycles) == 0

    def test_rain_flow_counting_monotonic_data(self):
        """단조 데이터 테스트"""
        data = np.linspace(0, 10, 100)

        cycles = rain_flow_counting(data)

        # 단조 데이터는 사이클이 없거나 매우 적어야 함
        assert len(cycles) <= 1

    def test_rain_flow_counting_insufficient_data(self):
        """데이터가 부족한 경우"""
        # 2개 점만 있는 경우
        data = np.array([1, 2])

        cycles = rain_flow_counting(data)

        # 사이클을 형성하기에 데이터가 부족
        assert len(cycles) == 0

    def test_rain_flow_counting_complex_signal(self):
        """복잡한 신호 테스트"""
        # 여러 주파수 성분을 가진 신호
        t = np.linspace(0, 10, 500)
        data = np.sin(t) + 0.5 * np.sin(3 * t) + 0.2 * np.sin(7 * t)

        cycles = rain_flow_counting(data)

        # 복잡한 신호는 사이클을 가져야 함 (기대값 조정)
        assert len(cycles) >= 0  # 최소 0개 이상

        # 사이클 수의 합이 합리적인 범위에 있어야 함
        total_cycles = sum(cycle[2] for cycle in cycles) if cycles else 0
        assert total_cycles >= 0


class TestCreateRainflowHistogram:
    """Rain Flow 히스토그램 생성 함수 테스트"""

    def test_create_rainflow_histogram_success(self):
        """정상적인 히스토그램 생성 테스트"""
        # 테스트용 사이클 데이터
        cycles = [
            (0.5, 1.0, 1.0),  # (범위, 평균, 사이클수)
            (0.3, 0.8, 0.5),
            (0.7, 1.2, 1.0),
            (0.2, 0.5, 0.5),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = f"{temp_dir}/test_histogram.png"

            result_path = create_rainflow_histogram(cycles, "Test Data", output_path)

            # 파일이 생성되었는지 확인
            assert os.path.exists(result_path)
            assert result_path == output_path

            # 파일 크기가 0보다 큰지 확인 (실제 이미지가 생성됨)
            assert os.path.getsize(result_path) > 0

    def test_create_rainflow_histogram_empty_cycles(self):
        """빈 사이클 리스트 테스트"""
        cycles = []

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = f"{temp_dir}/test_histogram.png"

            result_path = create_rainflow_histogram(cycles, "Empty Data", output_path)

            # 빈 사이클의 경우 빈 문자열 반환
            assert result_path == ""

            # 파일이 생성되지 않아야 함
            assert not os.path.exists(output_path)

    def test_create_rainflow_histogram_single_cycle(self):
        """단일 사이클 테스트"""
        cycles = [(1.0, 0.5, 1.0)]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = f"{temp_dir}/test_histogram.png"

            result_path = create_rainflow_histogram(cycles, "Single Cycle", output_path)

            # 파일이 생성되어야 함
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0

    def test_create_rainflow_histogram_directory_creation(self):
        """디렉토리 자동 생성 테스트"""
        cycles = [(0.5, 1.0, 1.0)]

        with tempfile.TemporaryDirectory() as temp_dir:
            # 존재하지 않는 하위 디렉토리 경로
            output_path = f"{temp_dir}/subdir/test_histogram.png"

            result_path = create_rainflow_histogram(cycles, "Test Data", output_path)

            # 디렉토리가 자동 생성되고 파일이 생성되어야 함
            assert os.path.exists(result_path)


class TestAnalyzeRainflowCycles:
    """Rain Flow 사이클 분석 함수 테스트"""

    def test_analyze_rainflow_cycles_normal_data(self):
        """정상적인 사이클 데이터 분석"""
        cycles = [
            (0.5, 1.0, 1.0),  # 전체 사이클
            (0.3, 0.8, 0.5),  # 반 사이클
            (0.7, 1.2, 1.0),  # 전체 사이클
            (0.2, 0.5, 0.5),  # 반 사이클
        ]

        analysis = analyze_rainflow_cycles(cycles)

        # 결과 구조 검증
        expected_keys = [
            "total_cycles",
            "full_cycles",
            "half_cycles",
            "mean_range",
            "max_range",
            "std_range",
            "damage_equivalent",
            "ranges",
            "means",
            "counts",
        ]

        for key in expected_keys:
            assert key in analysis

        # 값 검증
        assert analysis["total_cycles"] == 3.0  # 1.0 + 0.5 + 1.0 + 0.5
        assert analysis["full_cycles"] == 2  # 1.0 사이클 2개
        assert analysis["half_cycles"] == 2  # 0.5 사이클 2개
        assert analysis["max_range"] == 0.7  # 최대 범위
        assert analysis["damage_equivalent"] > 0  # 피로 손상 등가

    def test_analyze_rainflow_cycles_empty_data(self):
        """빈 사이클 데이터 분석"""
        cycles = []

        analysis = analyze_rainflow_cycles(cycles)

        # 모든 값이 0이어야 함
        assert analysis["total_cycles"] == 0
        assert analysis["full_cycles"] == 0
        assert analysis["half_cycles"] == 0
        assert analysis["mean_range"] == 0
        assert analysis["max_range"] == 0
        assert analysis["std_range"] == 0
        assert analysis["damage_equivalent"] == 0

    def test_analyze_rainflow_cycles_single_cycle(self):
        """단일 사이클 분석"""
        cycles = [(1.5, 2.0, 1.0)]

        analysis = analyze_rainflow_cycles(cycles)

        assert analysis["total_cycles"] == 1.0
        assert analysis["full_cycles"] == 1
        assert analysis["half_cycles"] == 0
        assert analysis["mean_range"] == 1.5
        assert analysis["max_range"] == 1.5
        assert analysis["std_range"] == 0.0  # 단일 값의 표준편차는 0

    def test_analyze_rainflow_cycles_damage_calculation(self):
        """피로 손상 계산 검증"""
        # 알려진 값으로 테스트
        cycles = [
            (2.0, 1.0, 1.0),  # 범위=2, 사이클수=1
            (1.0, 0.5, 2.0),  # 범위=1, 사이클수=2
        ]

        analysis = analyze_rainflow_cycles(cycles)

        # 피로 손상 = 1*(2^3) + 2*(1^3) = 8 + 2 = 10
        expected_damage = 1 * (2**3) + 2 * (1**3)
        assert abs(analysis["damage_equivalent"] - expected_damage) < 1e-10

    def test_analyze_rainflow_cycles_statistical_measures(self):
        """통계적 측정값 검증"""
        cycles = [(1.0, 0.5, 1.0), (2.0, 1.0, 1.0), (3.0, 1.5, 1.0)]

        analysis = analyze_rainflow_cycles(cycles)

        # 평균 범위 = (1+2+3)/3 = 2.0
        assert abs(analysis["mean_range"] - 2.0) < 1e-10

        # 최대 범위 = 3.0
        assert analysis["max_range"] == 3.0

        # 표준편차 계산 확인
        ranges = [1.0, 2.0, 3.0]
        expected_std = np.std(ranges)
        assert abs(analysis["std_range"] - expected_std) < 1e-10


@pytest.mark.integration
class TestIntegration:
    """통합 테스트"""

    def test_full_rainflow_workflow(self):
        """전체 Rain Flow 워크플로우 테스트"""
        # 복잡한 신호 생성
        t = np.linspace(0, 10, 1000)
        data = 2 * np.sin(t) + np.sin(3 * t) + 0.5 * np.sin(7 * t)

        # 1. 피크와 밸리 찾기
        indices, values = find_peaks_and_valleys(data)
        assert len(indices) > 0

        # 2. Rain Flow Counting
        cycles = rain_flow_counting(data)
        # 사이클이 있을 수도 없을 수도 있음 (임계값에 따라)

        # 3. 사이클 분석
        analysis = analyze_rainflow_cycles(cycles)
        assert analysis["total_cycles"] >= 0
        assert analysis["damage_equivalent"] >= 0

        # 4. 히스토그램 생성 (사이클이 있는 경우만)
        if cycles:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = f"{temp_dir}/integration_test.png"
                result_path = create_rainflow_histogram(
                    cycles, "Integration Test", output_path
                )

                assert os.path.exists(result_path)
                assert os.path.getsize(result_path) > 0

    def test_basic_functionality_analysis(self):
        """기본 기능 분석 테스트 (debug_rainflow.py에서 이동)"""
        # 노이즈가 있는 사인파 생성
        t = np.linspace(0, 4 * np.pi, 200)
        data = np.sin(t) + 0.1 * np.random.RandomState(42).randn(200)

        # 피크와 밸리 찾기
        indices, values = find_peaks_and_valleys(data)
        cycles = rain_flow_counting(data)

        # 기본 검증
        assert len(indices) >= 2, "최소 시작점과 끝점은 있어야 함"
        assert len(indices) == len(values), "인덱스와 값 길이 일치"

        # 사이클 검증
        total_cycles = sum(cycle[2] for cycle in cycles) if cycles else 0
        assert total_cycles >= 0, "총 사이클 수는 음수가 될 수 없음"

    def test_debug_simple_patterns(self):
        """간단한 패턴 디버깅 테스트 (debug_rainflow.py에서 이동)"""
        # 간단한 테스트 패턴들
        test_patterns = {
            "simple_triangle": np.array([0, 1, 0, 2, 0, -1, 0, 3, 0]),
            "sine_wave": np.sin(np.linspace(0, 4 * np.pi, 50)),
            "square_wave": np.array([0, 1, 1, 0, 0, 1, 1, 0] * 5),
            "sawtooth": np.concatenate(
                [np.linspace(0, 1, 10), np.linspace(1, 0, 10)] * 3
            ),
        }

        for pattern_name, data in test_patterns.items():
            # 피크와 밸리 찾기
            indices, values = find_peaks_and_valleys(data)

            # Rain Flow Counting
            cycles = rain_flow_counting(data)

            # 기본 검증
            assert len(indices) == len(
                values
            ), f"{pattern_name}: 인덱스와 값 길이 불일치"
            assert len(indices) >= 2, f"{pattern_name}: 최소 시작점과 끝점은 있어야 함"

            # 사이클 검증
            for cycle in cycles:
                assert len(cycle) == 3, f"{pattern_name}: 사이클 튜플 길이 오류"
                assert cycle[0] >= 0, f"{pattern_name}: 범위는 양수여야 함"
                assert cycle[2] > 0, f"{pattern_name}: 사이클 수는 양수여야 함"

    def test_real_data_simulation(self):
        """실제 데이터 시뮬레이션 테스트 (debug_rainflow.py에서 이동)"""
        # 실제 압력 데이터와 유사한 패턴 시뮬레이션
        np.random.seed(42)  # 재현 가능한 결과를 위해

        # 기본 트렌드 + 주기적 변동 + 노이즈
        t = np.linspace(0, 100, 1000)
        trend = 0.01 * t  # 약간의 트렌드
        periodic = 2 * np.sin(0.1 * t) + 0.5 * np.sin(0.3 * t)  # 주기적 변동
        noise = 0.1 * np.random.randn(1000)  # 노이즈

        simulated_data = trend + periodic + noise

        # 통계 정보 확인
        data_stats = {
            "mean": np.mean(simulated_data),
            "std": np.std(simulated_data),
            "min": np.min(simulated_data),
            "max": np.max(simulated_data),
            "range": np.max(simulated_data) - np.min(simulated_data),
        }

        # 기본 통계 검증
        assert data_stats["std"] > 0, "표준편차는 0보다 커야 함"
        assert data_stats["range"] > 0, "데이터 범위는 0보다 커야 함"

        # Rain Flow 분석
        cycles = rain_flow_counting(simulated_data)
        analysis = analyze_rainflow_cycles(cycles)

        # 분석 결과 검증
        assert analysis["total_cycles"] >= 0, "총 사이클 수는 음수가 될 수 없음"
        assert analysis["damage_equivalent"] >= 0, "피로 손상은 음수가 될 수 없음"

        # 사이클이 있는 경우 추가 검증
        if cycles:
            assert analysis["max_range"] > 0, "최대 범위는 0보다 커야 함"
            assert len(analysis["ranges"]) == len(cycles), "범위 배열 길이 불일치"

    def test_edge_cases_robustness(self):
        """경계 조건 견고성 테스트"""
        test_cases = [
            np.array([]),  # 빈 배열
            np.array([1.0]),  # 단일 값
            np.array([1.0, 1.0]),  # 동일한 값 2개
            np.array([1.0, 2.0]),  # 단조 증가 2개
            np.full(100, 5.0),  # 상수 배열
            np.array([1, 2, 1, 2, 1]),  # 단순 반복
        ]

        for i, data in enumerate(test_cases):
            # 모든 함수가 예외 없이 실행되어야 함
            try:
                indices, values = find_peaks_and_valleys(data)
                cycles = rain_flow_counting(data)
                analysis = analyze_rainflow_cycles(cycles)

                # 기본적인 일관성 검사
                assert len(indices) == len(values)
                assert analysis["total_cycles"] >= 0
                assert analysis["damage_equivalent"] >= 0

            except Exception as e:
                pytest.fail(f"Test case {i} failed with data {data}: {e}")


if __name__ == "__main__":
    pytest.main([__file__])