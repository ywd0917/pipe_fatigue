"""
main53_rainflow.py 모듈 테스트
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from main53_rainflow import (
    load_and_process_data,
    perform_rainflow_analysis,
    analyze_file_fatigue,
    compare_fatigue_results,
)

# 테스트 상수 정의
DEFAULT_SAMPLING_RATE = 1 / 300  # 5분 간격
DEFAULT_SIGNAL_LENGTH = 100  # 기본 신호 길이
LARGE_SIGNAL_LENGTH = 500  # 큰 신호 길이


@pytest.fixture
def create_csv_file():
    """테스트용 CSV 파일 생성 fixture"""

    def _create_csv(
        num_rows=DEFAULT_SIGNAL_LENGTH, include_nan=False, nan_position=None
    ):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # 헤더 작성
            f.write("msrmt_dt,wtrprsr,other_col\n")

            # 샘플 데이터 작성
            base_time = pd.Timestamp("2023-01-01 00:00:00")
            np.random.seed(42)

            for i in range(num_rows):
                time_str = (base_time + pd.Timedelta(minutes=5 * i)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                if include_nan and i == (nan_position or num_rows // 2):
                    f.write(f"{time_str},,dummy\n")
                else:
                    pressure = 3.0 + 0.5 * np.sin(i * 0.1) + 0.1 * np.random.randn()
                    f.write(f"{time_str},{pressure:.4f},dummy\n")

            temp_file = f.name

        return temp_file

    created_files = []

    def cleanup():
        for file_path in created_files:
            if os.path.exists(file_path):
                os.unlink(file_path)

    def create_and_track(*args, **kwargs):
        file_path = _create_csv(*args, **kwargs)
        created_files.append(file_path)
        return file_path

    yield create_and_track
    cleanup()


class TestLoadAndProcessData:
    """데이터 로드 및 전처리 함수 테스트"""

    def test_load_and_process_data_success(self, create_csv_file):
        """정상적인 데이터 로드 및 전처리 테스트"""
        csv_file = create_csv_file()
        original, low_pass, high_pass = load_and_process_data(csv_file)

        # 반환값 검증
        assert isinstance(original, np.ndarray)
        assert isinstance(low_pass, np.ndarray)
        assert isinstance(high_pass, np.ndarray)

        # 길이 검증
        assert len(original) == DEFAULT_SIGNAL_LENGTH, "원본 데이터 길이 불일치"
        assert len(low_pass) == DEFAULT_SIGNAL_LENGTH, "저대역 성분 길이 불일치"
        assert len(high_pass) == DEFAULT_SIGNAL_LENGTH, "고대역 성분 길이 불일치"

        # 데이터 타입 검증
        assert original.dtype == np.float64
        assert low_pass.dtype == np.float64
        assert high_pass.dtype == np.float64

    def test_load_and_process_data_with_nan(self, create_csv_file):
        """NaN 값이 포함된 데이터 처리 테스트"""
        csv_file = create_csv_file(num_rows=50, include_nan=True, nan_position=25)

        original, low_pass, high_pass = load_and_process_data(csv_file)

        # NaN이 보간되었는지 확인
        assert not np.any(np.isnan(original)), "NaN이 보간되지 않았습니다"
        assert not np.any(np.isnan(low_pass)), "저대역 성분에 NaN이 있습니다"
        assert not np.any(np.isnan(high_pass)), "고대역 성분에 NaN이 있습니다"

        # 데이터 길이 확인
        assert len(original) == 50, "원본 데이터 길이가 50이 아닙니다"
        assert len(low_pass) == 50, "저대역 성분 길이가 50이 아닙니다"
        assert len(high_pass) == 50, "고대역 성분 길이가 50이 아닙니다"

    def test_load_and_process_data_file_not_found(self):
        """존재하지 않는 파일 처리 테스트"""
        with pytest.raises(FileNotFoundError):
            load_and_process_data("nonexistent_file.csv")


class TestPerformRainflowAnalysis:
    """Rain Flow 분석 함수 테스트"""

    @pytest.fixture
    def generate_test_signal(self):
        """테스트용 신호 생성 fixture"""

        def _generate(signal_type="cyclic", length=DEFAULT_SIGNAL_LENGTH):
            if signal_type == "cyclic":
                # 사인파 데이터 (사이클이 있는 데이터)
                t = np.linspace(0, 4 * np.pi, length)
                return np.sin(t) + 0.5 * np.sin(3 * t)
            elif signal_type == "monotonic":
                # 단조 증가 데이터
                return np.linspace(0, 10, length)
            elif signal_type == "constant":
                # 상수 데이터
                return np.full(length, 5.0)
            else:
                raise ValueError(f"Unknown signal type: {signal_type}")

        return _generate

    @pytest.mark.parametrize(
        "signal_type,expected_cycles",
        [
            ("cyclic", True),  # 사이클이 있는 데이터
            ("monotonic", False),  # 단조 증가 데이터
            ("constant", False),  # 상수 데이터
        ],
    )
    def test_perform_rainflow_analysis_various_signals(
        self, generate_test_signal, signal_type, expected_cycles, tmp_path
    ):
        """다양한 신호 타입에 대한 Rain Flow 분석 테스트"""
        data = generate_test_signal(signal_type)

        result = perform_rainflow_analysis(
            data, f"{signal_type}_data", "test_file.csv", str(tmp_path)
        )

        # 결과 구조 검증
        assert "cycles" in result, "cycles 키가 결과에 없습니다"
        assert "analysis" in result, "analysis 키가 결과에 없습니다"
        assert "histogram_path" in result, "histogram_path 키가 결과에 없습니다"

        # 사이클 존재 여부 확인
        if expected_cycles:
            assert len(result["cycles"]) > 0, f"{signal_type} 신호에 사이클이 없습니다"
            assert result["analysis"]["total_cycles"] > 0, "총 사이클 수가 0입니다"
        else:
            assert (
                len(result["cycles"]) == 0
            ), f"{signal_type} 신호에 예상치 않은 사이클이 있습니다"
            if signal_type != "cyclic":
                assert (
                    result["histogram_path"] == ""
                ), "히스토그램 경로가 비어있지 않습니다"


class TestAnalyzeFileFatigue:
    """파일별 피로 분석 함수 테스트"""

    def test_analyze_file_fatigue_success(self, create_csv_file, tmp_path):
        """정상적인 파일 분석 테스트"""
        # 사인파 형태의 데이터 생성을 위해 더 긴 데이터 사용
        csv_file = create_csv_file(num_rows=200)
        result = analyze_file_fatigue(csv_file, str(tmp_path))

        # 결과 구조 검증
        assert "file_path" in result
        assert "file_name" in result
        assert "results" in result
        assert "success" in result

        # 성공 여부 확인
        assert result["success"] is True, "파일 분석이 실패했습니다"

        # 각 데이터 타입별 결과 확인
        assert "original" in result["results"]
        assert "low_pass" in result["results"]
        assert "high_pass" in result["results"]

    def test_analyze_file_fatigue_file_not_found(self, tmp_path):
        """존재하지 않는 파일 분석 테스트"""
        result = analyze_file_fatigue("nonexistent.csv", str(tmp_path))

        # 실패 결과 확인
        assert (
            result["success"] is False
        ), "존재하지 않는 파일에 대해 성공이 반환되었습니다"
        assert "error" in result, "error 키가 결과에 없습니다"


class TestCompareFatigueResults:
    """피로 결과 비교 함수 테스트"""

    @pytest.fixture
    def mock_fatigue_results(self):
        """테스트용 모의 피로 결과 생성"""

        def _create_results(success=True, include_cycles=True):
            if not success:
                return [{"success": False, "error": "Test error"}]

            base_result = {
                "success": True,
                "file_name": "test1.csv",
                "results": {
                    "original": {
                        "cycles": (
                            [(0.1, 0.5, 1.0), (0.2, 0.6, 0.5)] if include_cycles else []
                        ),
                        "analysis": {
                            "total_cycles": 1.5 if include_cycles else 0,
                            "full_cycles": 1 if include_cycles else 0,
                            "half_cycles": 1 if include_cycles else 0,
                            "mean_range": 0.15 if include_cycles else 0,
                            "max_range": 0.2 if include_cycles else 0,
                            "std_range": 0.05 if include_cycles else 0,
                            "damage_equivalent": 10.0 if include_cycles else 0,
                        },
                    },
                    "low_pass": {"cycles": []},
                    "high_pass": {
                        "cycles": [(0.05, 0.3, 1.0)] if include_cycles else [],
                        "analysis": {
                            "total_cycles": 1.0 if include_cycles else 0,
                            "full_cycles": 1 if include_cycles else 0,
                            "half_cycles": 0,
                            "mean_range": 0.05 if include_cycles else 0,
                            "max_range": 0.05 if include_cycles else 0,
                            "std_range": 0.0,
                            "damage_equivalent": 5.0 if include_cycles else 0,
                        },
                    },
                },
            }
            return [base_result]

        return _create_results

    def test_compare_fatigue_results_success(self, mock_fatigue_results, tmp_path):
        """정상적인 결과 비교 테스트"""
        mock_results = mock_fatigue_results(success=True, include_cycles=True)

        # 함수 실행 (예외 발생하지 않아야 함)
        compare_fatigue_results(mock_results, str(tmp_path))

        # CSV 파일 생성 확인
        csv_path = tmp_path / "fatigue_comparison.csv"
        assert csv_path.exists(), "CSV 파일이 생성되지 않았습니다"

        # CSV 내용 확인
        df = pd.read_csv(csv_path)
        assert (
            len(df) == 2
        ), "CSV에 예상된 2개의 행이 없습니다"  # original과 high_pass 데이터
        assert "File" in df.columns, "File 콜럼이 없습니다"
        assert "Data_Type" in df.columns, "Data_Type 콜럼이 없습니다"
        assert "Total_Cycles" in df.columns, "Total_Cycles 콜럼이 없습니다"

    @pytest.mark.parametrize(
        "test_case,expected_csv",
        [
            ("no_success", False),  # 성공한 결과가 없는 경우
            ("empty_list", False),  # 빈 결과 리스트
        ],
    )
    def test_compare_fatigue_results_edge_cases(
        self, mock_fatigue_results, tmp_path, test_case, expected_csv
    ):
        """비정상적인 경우의 결과 비교 테스트"""
        if test_case == "no_success":
            mock_results = mock_fatigue_results(success=False)
        elif test_case == "empty_list":
            mock_results = []

        # 함수 실행 (예외 발생하지 않아야 함)
        compare_fatigue_results(mock_results, str(tmp_path))

        # CSV 파일 생성 여부 확인
        csv_path = tmp_path / "fatigue_comparison.csv"
        if expected_csv:
            assert csv_path.exists(), f"{test_case}: CSV 파일이 생성되지 않았습니다"
        else:
            assert not csv_path.exists(), f"{test_case}: CSV 파일이 잘못 생성되었습니다"


@pytest.mark.integration
class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def complex_signal_csv(self, create_csv_file):
        """복잡한 신호를 가진 CSV 파일 생성"""
        # 여러 주파수 성분을 포함한 신호 생성
        num_rows = 500
        base_time = pd.Timestamp("2023-01-01 00:00:00")

        # 임시 파일에 복잡한 신호 작성
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("msrmt_dt,wtrprsr,other_col\n")

            np.random.seed(42)
            for i in range(num_rows):
                time_str = (base_time + pd.Timedelta(minutes=5 * i)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                # 저주파 + 고주파 성분
                pressure = (
                    3.0
                    + 0.8 * np.sin(i * 0.02)  # 저주파
                    + 0.3 * np.sin(i * 0.2)  # 고주파
                    + 0.1 * np.random.randn()
                )  # 노이즈
                f.write(f"{time_str},{pressure:.4f},dummy\n")

            return f.name

    def test_full_workflow_integration(self, complex_signal_csv, tmp_path):
        """전체 워크플로우 통합 테스트"""
        try:
            # 전체 분석 실행
            result = analyze_file_fatigue(complex_signal_csv, str(tmp_path))

            # 성공 확인
            assert result["success"] is True, "파일 분석이 실패했습니다"

            # 각 성분별 분석 결과 확인
            results = result["results"]

            # 원본 데이터는 사이클이 있어야 함
            assert (
                len(results["original"]["cycles"]) > 0
            ), "원본 데이터에 사이클이 없습니다"

            # 고주파 성분도 사이클이 있어야 함
            assert (
                len(results["high_pass"]["cycles"]) > 0
            ), "고주파 성분에 사이클이 없습니다"

            # 비교 분석 실행
            compare_fatigue_results([result], str(tmp_path))

            # 결과 파일 확인
            csv_path = tmp_path / "fatigue_comparison.csv"
            assert csv_path.exists(), "비교 결과 CSV 파일이 생성되지 않았습니다"

            # CSV 내용 검증
            df = pd.read_csv(csv_path)
            assert len(df) > 0, "CSV 파일이 비어있습니다"
            assert "File" in df.columns, "File 컬럼이 없습니다"
            assert "Data_Type" in df.columns, "Data_Type 컬럼이 없습니다"

        finally:
            if os.path.exists(complex_signal_csv):
                os.unlink(complex_signal_csv)


class TestErrorHandling:
    """에러 처리 테스트"""

    def test_load_and_process_data_with_corrupted_csv(self, tmp_path):
        """손상된 CSV 파일 처리 테스트"""
        # 잘못된 형식의 CSV 파일 생성
        corrupted_file = tmp_path / "corrupted.csv"
        corrupted_file.write_text("invalid,csv,content\nno,proper,datetime\n")

        with pytest.raises((KeyError, ValueError)):
            load_and_process_data(str(corrupted_file))

    def test_perform_rainflow_with_empty_data(self, tmp_path):
        """빈 데이터로 Rain Flow 분석 테스트"""
        empty_data = np.array([])

        result = perform_rainflow_analysis(
            empty_data, "empty_data", "test.csv", str(tmp_path)
        )

        # 빈 데이터에서도 결과 구조는 반환되어야 함
        assert "cycles" in result
        assert "analysis" in result
        assert len(result["cycles"]) == 0
        # 빈 데이터의 경우 analysis가 비어있을 수 있음
        if result["analysis"]:
            assert result["analysis"].get("total_cycles", 0) == 0

    @pytest.mark.parametrize(
        "invalid_data",
        [
            np.array([np.nan, np.nan, np.nan]),  # 모두 NaN
            np.array([1.0]),  # 데이터 포인트 1개
            np.array([1.0, 1.0, 1.0]),  # 모두 같은 값
        ],
    )
    def test_perform_rainflow_with_invalid_data(self, invalid_data, tmp_path):
        """유효하지 않은 데이터로 Rain Flow 분석 테스트"""
        result = perform_rainflow_analysis(
            invalid_data, "invalid_data", "test.csv", str(tmp_path)
        )

        # 유효하지 않은 데이터에서도 결과는 반환되어야 함
        assert "cycles" in result
        assert "analysis" in result
        # 사이클이 없거나 매우 적어야 함
        if result["analysis"]:
            total_cycles = result["analysis"].get("total_cycles", 0)
            assert total_cycles == 0 or total_cycles < 1
        else:
            # analysis가 비어있으면 사이클이 없는 것
            assert len(result["cycles"]) == 0


if __name__ == "__main__":
    pytest.main([__file__])