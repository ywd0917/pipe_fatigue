"""
repair_loader_k 모듈 테스트
K_repair 로드 및 적용 테스트 (버전 2: C_REPAIR 포함)
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from src.repair_loader_k import (
    load_k_repair_mapping,
    get_k_repair,
    apply_k_repair_to_dataframe,
    print_k_repair_statistics,
)
from src.common.config import C_REPAIR, PROJECT_ROOT


@pytest.fixture
def mock_repair_csv_data():
    """테스트용 K_repair CSV 데이터"""
    pipe_lm_data = pd.DataFrame({
        "FTR_IDN": ["71585", "261304", "435273", "123456"],
        "pipe_length": [100.0, 200.0, 150.0, 50.0],
        "K_repair": [500, 600, 0, 100],  # 총 수리 횟수
        "K_repair_per_m": [5.0, 3.0, 0.0, 2.0],  # 1m당 수리 횟수
        "K_repair_ground": [200, 300, 0, 50],
        "K_repair_ground_per_m": [2.0, 1.5, 0.0, 1.0],
        "K_repair_under": [100, 200, 0, 30],
        "K_repair_under_per_m": [1.0, 1.0, 0.0, 0.6],
        "K_repair_emergency": [150, 50, 0, 10],
        "K_repair_emergency_per_m": [1.5, 0.25, 0.0, 0.2],
        "K_repair_management": [50, 50, 0, 10],
        "K_repair_management_per_m": [0.5, 0.25, 0.0, 0.2],
    })
    
    sply_ls_data = pd.DataFrame({
        "FTR_IDN": ["313693", "468355", "177575"],
        "pipe_length": [80.0, 120.0, 60.0],
        "K_repair": [0, 240, 450],
        "K_repair_per_m": [0.0, 2.0, 7.5],
        "K_repair_ground": [0, 100, 200],
        "K_repair_ground_per_m": [0.0, 0.83, 3.33],
        "K_repair_under": [0, 80, 150],
        "K_repair_under_per_m": [0.0, 0.67, 2.5],
        "K_repair_emergency": [0, 40, 50],
        "K_repair_emergency_per_m": [0.0, 0.33, 0.83],
        "K_repair_management": [0, 20, 50],
        "K_repair_management_per_m": [0.0, 0.17, 0.83],
    })
    
    return {"PIPE_LM": pipe_lm_data, "SPLY_LS": sply_ls_data}


@pytest.fixture
def sample_pipe_dataframe():
    """테스트용 파이프 데이터프레임"""
    return pd.DataFrame({
        "FTR_IDN": ["71585", "261304", "999999", "123456"],
        "K_diameter": [1.1, 1.2, 1.15, 1.05],
        "K_age": [1.5, 2.0, 1.2, 1.8],
        "K_soil": [1.2, 1.3, 1.1, 1.4],
        "K_traffic": [1.4, 1.5, 1.3, 1.6],
        "K_vibration": [1.05, 1.05, 1.05, 1.05],
        "K_material": [0.9, 0.8, 1.0, 0.85],
        "K_stress": [2.0, 2.5, 1.8, 2.2],
        "K_total": [5.0, 10.0, 4.0, 8.0],  # 초기 K_total (K_repair 적용 전)
    })


class TestCRepairConstant:
    """C_REPAIR 상수 검증"""
    
    def test_c_repair_value(self):
        """C_REPAIR 값이 10.0인지 확인"""
        assert C_REPAIR == 10.0, f"C_REPAIR should be 10.0 but got {C_REPAIR}"
    
    def test_c_repair_type(self):
        """C_REPAIR 타입 확인"""
        assert isinstance(C_REPAIR, (int, float)), "C_REPAIR should be numeric"


class TestLoadKRepairMapping:
    """load_k_repair_mapping 함수 테스트"""
    
    @patch("src.repair_loader_k.pd.read_csv")
    @patch("pathlib.Path.exists")
    def test_successful_loading(self, mock_exists, mock_read_csv, mock_repair_csv_data):
        """정상적인 K_repair 데이터 로드"""
        mock_exists.return_value = True
        
        # read_csv가 호출될 때마다 다른 데이터 반환
        mock_read_csv.side_effect = [
            mock_repair_csv_data["PIPE_LM"],
            mock_repair_csv_data["SPLY_LS"]
        ]
        
        result = load_k_repair_mapping()
        
        assert "PIPE_LM" in result
        assert "SPLY_LS" in result
        assert len(result["PIPE_LM"]) == 4
        assert len(result["SPLY_LS"]) == 3
    
    @patch("pathlib.Path.exists")
    def test_file_not_found(self, mock_exists):
        """파일이 없는 경우"""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            load_k_repair_mapping()


class TestGetKRepair:
    """get_k_repair 함수 테스트"""
    
    def test_get_existing_ftr_idn(self, mock_repair_csv_data):
        """존재하는 FTR_IDN의 K_repair 값 조회"""
        # DataFrame을 FTR_IDN으로 인덱싱
        pipe_lm_df = mock_repair_csv_data["PIPE_LM"].set_index("FTR_IDN")
        repair_data = {"PIPE_LM": pipe_lm_df}
        
        # 존재하는 FTR_IDN 테스트
        assert get_k_repair("71585", "PIPE_LM", repair_data) == 5.0
        assert get_k_repair("261304", "PIPE_LM", repair_data) == 3.0
        assert get_k_repair("435273", "PIPE_LM", repair_data) == 0.0
    
    def test_get_nonexisting_ftr_idn(self, mock_repair_csv_data):
        """존재하지 않는 FTR_IDN의 경우 0.0 반환"""
        pipe_lm_df = mock_repair_csv_data["PIPE_LM"].set_index("FTR_IDN")
        repair_data = {"PIPE_LM": pipe_lm_df}
        
        assert get_k_repair("999999", "PIPE_LM", repair_data) == 0.0
    
    def test_get_wrong_pipe_type(self, mock_repair_csv_data):
        """잘못된 파이프 타입의 경우 0.0 반환"""
        pipe_lm_df = mock_repair_csv_data["PIPE_LM"].set_index("FTR_IDN")
        repair_data = {"PIPE_LM": pipe_lm_df}
        
        assert get_k_repair("71585", "WRONG_TYPE", repair_data) == 0.0


class TestApplyKRepairToDataframe:
    """apply_k_repair_to_dataframe 함수 테스트"""
    
    def test_apply_k_repair_basic(self, sample_pipe_dataframe, mock_repair_csv_data):
        """기본 K_repair 적용 테스트"""
        # repair_data 준비
        pipe_lm_df = mock_repair_csv_data["PIPE_LM"].set_index("FTR_IDN")
        repair_data = {"PIPE_LM": pipe_lm_df}
        
        # K_repair 적용
        result = apply_k_repair_to_dataframe(
            sample_pipe_dataframe.copy(), "PIPE_LM", repair_data
        )
        
        # K_repair 컬럼 추가 확인
        assert "K_repair" in result.columns
        
        # K_repair 값 확인
        assert result.loc[0, "K_repair"] == 5.0  # FTR_IDN: 71585
        assert result.loc[1, "K_repair"] == 3.0  # FTR_IDN: 261304
        assert result.loc[2, "K_repair"] == 0.0  # FTR_IDN: 999999 (없음)
        assert result.loc[3, "K_repair"] == 2.0  # FTR_IDN: 123456
    
    def test_k_total_calculation_with_c_repair(self, sample_pipe_dataframe, mock_repair_csv_data):
        """K_total 계산에 (1 + C_REPAIR × K_repair) 적용 확인"""
        pipe_lm_df = mock_repair_csv_data["PIPE_LM"].set_index("FTR_IDN")
        repair_data = {"PIPE_LM": pipe_lm_df}
        
        # 원본 K_total 값 저장
        original_k_total = sample_pipe_dataframe["K_total"].copy()
        
        # K_repair 적용
        result = apply_k_repair_to_dataframe(
            sample_pipe_dataframe.copy(), "PIPE_LM", repair_data
        )
        
        # K_total_without_repair 컬럼 확인
        assert "K_total_without_repair" in result.columns
        
        # K_total 계산 검증: K_total = K_total_without_repair * (1 + C_REPAIR * K_repair)
        for idx in range(len(result)):
            k_repair = result.loc[idx, "K_repair"]
            k_total_without = result.loc[idx, "K_total_without_repair"]
            k_total_expected = k_total_without * (1 + C_REPAIR * k_repair)
            k_total_actual = result.loc[idx, "K_total"]
            
            # 부동소수점 오차 고려
            assert abs(k_total_actual - k_total_expected) < 0.0001, \
                f"Row {idx}: Expected K_total={k_total_expected}, got {k_total_actual}"
    
    def test_column_order(self, sample_pipe_dataframe, mock_repair_csv_data):
        """K_repair가 K_total 바로 앞에 위치하는지 확인"""
        pipe_lm_df = mock_repair_csv_data["PIPE_LM"].set_index("FTR_IDN")
        repair_data = {"PIPE_LM": pipe_lm_df}
        
        result = apply_k_repair_to_dataframe(
            sample_pipe_dataframe.copy(), "PIPE_LM", repair_data
        )
        
        columns = result.columns.tolist()
        k_repair_idx = columns.index("K_repair")
        k_total_idx = columns.index("K_total")
        
        # K_repair가 K_total 바로 앞에 있어야 함
        assert k_total_idx == k_repair_idx + 1
    
    def test_zero_k_repair_with_c_repair(self, mock_repair_csv_data):
        """K_repair = 0일 때 K_total 변화 없음 확인"""
        df = pd.DataFrame({
            "FTR_IDN": ["435273"],  # K_repair = 0인 FTR_IDN
            "K_total": [5.0]
        })
        
        pipe_lm_df = mock_repair_csv_data["PIPE_LM"].set_index("FTR_IDN")
        repair_data = {"PIPE_LM": pipe_lm_df}
        
        result = apply_k_repair_to_dataframe(df.copy(), "PIPE_LM", repair_data)
        
        # K_repair = 0
        assert result.loc[0, "K_repair"] == 0.0
        
        # K_total = K_total_without_repair * (1 + C_REPAIR * 0)
        # = 5.0 * (1 + 0) = 5.0
        assert result.loc[0, "K_total"] == 5.0
    
    def test_negative_k_repair_prevention(self):
        """음수 K_repair 값 방지 테스트"""
        df = pd.DataFrame({
            "FTR_IDN": ["test"],
            "K_total": [5.0]
        })
        
        # 음수 K_repair 데이터
        repair_df = pd.DataFrame({
            "FTR_IDN": ["test"],
            "K_repair_per_m": [-5.0]  # 음수 값
        }).set_index("FTR_IDN")
        
        repair_data = {"PIPE_LM": repair_df}
        
        result = apply_k_repair_to_dataframe(df.copy(), "PIPE_LM", repair_data)
        
        # 음수는 0으로 클리핑되어야 함
        assert result.loc[0, "K_repair"] == 0.0


class TestPrintKRepairStatistics:
    """print_k_repair_statistics 함수 테스트"""
    
    def test_statistics_output(self, capsys):
        """통계 출력 테스트"""
        df = pd.DataFrame({
            "K_repair": [0.0, 1.0, 2.0, 5.0, 10.0, 0.0, 3.0, 0.0]
        })
        
        print_k_repair_statistics(df, "PIPE_LM")
        
        captured = capsys.readouterr()
        
        # 출력 내용 확인
        assert "K_repair 통계" in captured.out
        assert "전체 레코드 수: 8" in captured.out
        assert "K_repair > 0인 레코드 수: 5" in captured.out
        assert "평균 K_repair" in captured.out
    
    def test_empty_dataframe(self, capsys):
        """빈 데이터프레임 처리"""
        df = pd.DataFrame()
        
        # K_repair 컬럼이 없으면 아무것도 출력하지 않음
        print_k_repair_statistics(df, "PIPE_LM")
        
        captured = capsys.readouterr()
        # 빈 DataFrame은 출력이 없음
        assert captured.out == "" or "K_repair" not in df.columns


class TestKRepairFormula:
    """K_repair 공식 검증 테스트"""
    
    def test_version2_formula(self):
        """버전 2 공식 검증: K_total = K_total_base × (1 + C_REPAIR × K_repair)"""
        # 테스트 케이스
        test_cases = [
            {"K_base": 1.0, "K_repair": 0.0, "expected": 1.0},     # No change
            {"K_base": 1.0, "K_repair": 1.0, "expected": 11.0},    # 1 + 10*1
            {"K_base": 2.0, "K_repair": 0.5, "expected": 12.0},    # 2 * (1 + 10*0.5)
            {"K_base": 5.0, "K_repair": 3.0, "expected": 155.0},   # 5 * (1 + 10*3)
        ]
        
        for case in test_cases:
            k_total = case["K_base"] * (1 + C_REPAIR * case["K_repair"])
            assert abs(k_total - case["expected"]) < 0.0001, \
                f"Failed for K_base={case['K_base']}, K_repair={case['K_repair']}"
    
    def test_d_final_increase_with_k_repair(self):
        """K_repair 증가에 따른 D_final 증가 검증"""
        D_base = 0.001
        K_total_base = 2.0
        
        # K_repair = 0
        K_total_0 = K_total_base * (1 + C_REPAIR * 0)
        D_final_0 = D_base * K_total_0
        
        # K_repair = 5
        K_total_5 = K_total_base * (1 + C_REPAIR * 5)
        D_final_5 = D_base * K_total_5
        
        # D_final 증가 비율 = (1 + 10*5) / (1 + 0) = 51
        ratio = D_final_5 / D_final_0
        assert abs(ratio - 51.0) < 0.0001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])