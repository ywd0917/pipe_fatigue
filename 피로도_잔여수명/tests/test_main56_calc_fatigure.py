"""
main56_calc_fatigure.py 통합 테스트

main56 스크립트의 전체 워크플로우를 테스트합니다.
실제 계산 검증은 서브 모듈 테스트에서 수행됩니다:
- test_fatigue_calculations.py: D_final, D_base 계산 검증
- test_repair_loader_k.py: K_repair 적용 및 K_total 계산 검증
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import tempfile
import os
from datetime import datetime, timedelta

# 테스트 대상 모듈 import
from src.main56_calc_fatigure import (
    get_rainflow_summary,
    main,
    process_all_pipe_data_with_rainflow_and_repair,
)

from src.common.config import PROJECT_ROOT

# 테스트 상수 정의
DEFAULT_SIGNAL_LENGTH = 100
TEST_OUTPUT_DIR = "test_results"
DEFAULT_YEAR = 2023
DEFAULT_DATE_RANGE = ("2023-01-01", "2023-12-31")


@pytest.fixture
def create_test_csv():
    """테스트용 CSV 파일 생성 fixture"""

    def _create(
        num_rows=DEFAULT_SIGNAL_LENGTH,
        include_nan=False,
        nan_position=None,
        start_date=datetime(2023, 1, 1),
        interval_minutes=5,
    ):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # 헤더 작성
            f.write("msrmt_dt,wtrprsr,other_col\n")

            # 샘플 데이터 작성
            base_time = start_date
            np.random.seed(42)

            for i in range(num_rows):
                time_str = (
                    base_time + timedelta(minutes=interval_minutes * i)
                ).strftime("%Y-%m-%d %H:%M:%S")

                if include_nan and i == (nan_position or num_rows // 2):
                    f.write(f"{time_str},,dummy\n")
                else:
                    pressure = 3.0 + 0.5 * np.sin(i * 0.01) + 0.1 * np.random.randn()
                    f.write(f"{time_str},{pressure:.4f},dummy\n")

            temp_file = f.name

        return temp_file

    created_files = []

    def cleanup():
        for file_path in created_files:
            if os.path.exists(file_path):
                os.unlink(file_path)

    def create_and_track(*args, **kwargs):
        file_path = _create(*args, **kwargs)
        created_files.append(file_path)
        return file_path

    yield create_and_track
    cleanup()


class TestGetRainflowSummary:
    """Rain Flow Counting 요약 함수 테스트"""

    def test_get_rainflow_summary_success(self):
        """정상적인 Rain Flow Counting 요약 테스트"""
        mock_analysis_result = {
            "success": True,
            "results": {
                "low_pass": {
                    "has_cycles": True,
                    "analysis": {
                        "total_cycles": 30.0,
                        "full_cycles": 25,
                        "half_cycles": 10,
                        "mean_range": 0.5,
                        "max_range": 1.0,
                    },
                },
                "high_pass": {
                    "has_cycles": True,
                    "analysis": {
                        "total_cycles": 20.0,
                        "full_cycles": 15,
                        "half_cycles": 10,
                        "mean_range": 0.3,
                        "max_range": 0.8,
                    },
                },
            },
        }

        summary = get_rainflow_summary(mock_analysis_result)

        # 결과 구조 검증
        expected_keys = [
            "high_total_cycles",
            "low_total_cycles",
            "high_full_cycles",
            "low_full_cycles",
            "high_half_cycles",
            "low_half_cycles",
            "high_mean_range",
            "low_mean_range",
            "high_max_range",
            "low_max_range",
        ]

        for key in expected_keys:
            assert key in summary

        # 값 검증
        assert summary["low_total_cycles"] == 30.0
        assert summary["high_total_cycles"] == 20.0

    def test_get_rainflow_summary_failed_analysis(self):
        """실패한 분석 결과 요약 테스트"""
        mock_analysis_result = {"success": False, "error": "Test error"}

        summary = get_rainflow_summary(mock_analysis_result)

        # 모든 값이 0이어야 함
        expected_keys = [
            "high_total_cycles",
            "low_total_cycles",
        ]

        for key in expected_keys:
            assert summary[key] == 0.0


class TestCSVOutputStructure:
    """CSV 출력 파일 구조 검증"""

    def test_output_directory(self):
        """출력 디렉토리 확인"""
        output_dir = PROJECT_ROOT / "results" / "main56_calc_fatigure"
        assert output_dir.exists(), "main56_calc_fatigure 출력 디렉토리가 존재해야 합니다"

    def test_output_files_exist(self):
        """출력 파일 존재 확인"""
        output_dir = PROJECT_ROOT / "results" / "main56_calc_fatigure"
        
        if output_dir.exists():
            csv_files = list(output_dir.glob("*.csv"))
            assert len(csv_files) > 0, "CSV 출력 파일이 존재해야 합니다"
            
            # 파일명 확인 (_by_age가 없어야 함)
            for csv_file in csv_files:
                assert "_by_age" not in csv_file.name, f"파일명에 _by_age가 없어야 합니다: {csv_file.name}"

    def test_csv_has_required_columns(self):
        """CSV 파일에 필수 컬럼 존재 확인"""
        csv_path = PROJECT_ROOT / "results" / "main56_calc_fatigure" / "fatigue_pipe_lm.csv"
        
        if csv_path.exists():
            df = pd.read_csv(csv_path, nrows=0)
            columns = df.columns.tolist()
            
            # 필수 컬럼 확인
            assert "FTR_IDN" in columns, "FTR_IDN 컬럼이 필요합니다"
            assert "K_repair" in columns, "K_repair 컬럼이 필요합니다"
            assert "K_total" in columns, "K_total 컬럼이 필요합니다"
            
            # D_final_org 컬럼 확인 (최소 하나의 지역)
            d_final_org_cols = [col for col in columns if col.endswith("_D_final_org")]
            assert len(d_final_org_cols) > 0, "D_final_org 컬럼이 최소 하나 있어야 합니다"


@pytest.mark.integration
class TestMainFunction:
    """메인 함수 통합 테스트"""

    @patch("src.main56_calc_fatigure.load_k_repair_mapping")
    @patch("src.main56_calc_fatigure.read_pipe_properties")
    @patch("src.main56_calc_fatigure.process_all_pipe_data_with_rainflow_and_repair")
    @patch("src.main56_calc_fatigure.analyze_date_range_rainflow")
    @patch("pathlib.Path.exists")
    def test_main_workflow(
        self, mock_exists, mock_analyze, mock_process, mock_read_pipe, mock_load_repair
    ):
        """main56 전체 워크플로우 테스트"""
        # Mock 설정
        mock_exists.return_value = True

        # K_repair 데이터 Mock
        mock_load_repair.return_value = {
            "PIPE_LM": pd.DataFrame({"K_repair_per_m": [10.0]}).set_index(
                pd.Index([71585], name="FTR_IDN")
            ),
            "SPLY_LS": pd.DataFrame({"K_repair_per_m": [5.0]}).set_index(
                pd.Index([313693], name="FTR_IDN")
            ),
        }

        # 파이프 속성 데이터 Mock
        mock_read_pipe.return_value = pd.DataFrame(
            {
                "type": ["STS", "ST"],
                "KmaterialK": [0.7, 0.9],
                "fatigure_limit": ["10⁶ 이상", "10⁶ 이상"],
            }
        )

        mock_analyze.return_value = {
            "success": True,
            "file_name": "test.csv",
            "data_period": {
                "start": datetime(2023, 1, 1),
                "end": datetime(2023, 12, 31),
                "total_points": 1000,
            },
            "results": {
                "low_pass": {"has_cycles": True, "analysis": {"total_cycles": 100.0}},
                "high_pass": {"has_cycles": True, "analysis": {"total_cycles": 200.0}},
            },
        }

        # 함수 실행
        main()

        # 워크플로우 검증
        mock_load_repair.assert_called_once()  # K_repair 로드
        mock_read_pipe.assert_called_once()    # 파이프 속성 로드
        mock_process.assert_called_once()      # 파이프 데이터 처리

    @patch("src.main56_calc_fatigure.load_k_repair_mapping")
    @patch("src.main56_calc_fatigure.process_all_pipe_data_with_rainflow_and_repair")
    def test_main_pipes_only(self, mock_process_all, mock_load_repair):
        """파이프 데이터만 처리하는 경우"""
        # Mock 설정
        mock_load_repair.return_value = {
            "PIPE_LM": pd.DataFrame(),
            "SPLY_LS": pd.DataFrame(),
        }

        # 함수 실행 (Rain Flow Counting 비활성화)
        main(process_rainflow=False)

        # 필수 함수 호출 확인
        mock_load_repair.assert_called_once()
        mock_process_all.assert_called_once()

    @patch("src.main56_calc_fatigure.load_k_repair_mapping")
    def test_k_repair_data_loading(self, mock_load_repair):
        """K_repair 데이터 로드 검증"""
        # FileNotFoundError 시뮬레이션
        mock_load_repair.side_effect = FileNotFoundError("K_repair 파일 없음")

        with pytest.raises(SystemExit):
            main(process_pipes=True, process_rainflow=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])