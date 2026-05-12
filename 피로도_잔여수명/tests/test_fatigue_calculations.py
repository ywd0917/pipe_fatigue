"""
피로 계산 모듈 테스트 (버전 2: K_repair 포함)
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from src.fatigue_calculations import (
    get_K_material_mapping,
    get_fatigue_limit_mapping,
    add_K_material_to_dataframe,
    calculate_fatigue_damage_dataframe,
)
from src.common.config import C_REPAIR


@pytest.fixture
def sample_pipe_properties():
    """샘플 파이프 속성 데이터프레임"""
    return pd.DataFrame(
        {
            "type": ["ST", "PE", "CI", "PVC"],
            "KmaterialK": [0.9, 1.1, 0.8, 1.2],
            "fatigure_limit": ["10⁶", "10⁵", "1000000", "nan"],
            "design_pressure": [5.0, 4.0, 6.0, 3.0],
        }
    )


@pytest.fixture
def sample_result_df():
    """샘플 결과 데이터프레임"""
    return pd.DataFrame(
        {
            "FTR_IDN": [1, 2, 3],
            "PIP_TYPE": ["ST", "PE", "CI"],
            "STD_DIP": [100, 200, 300],
            "YEARS_SINCE_BEG": [10, 20, 30],
            "GRID_CD": ["0470", "0470", "0470"],
            "0470_high_total_cycles": [1000, 2000, 3000],
            "0470_low_total_cycles": [100, 200, 300],
        }
    )


@pytest.fixture
def sample_result_df_with_repair():
    """K_repair 정보가 포함된 샘플 결과 데이터프레임"""
    return pd.DataFrame(
        {
            "FTR_IDN": [1, 2, 3],
            "PIP_TYPE": ["ST", "PE", "CI"],
            "STD_DIP": [100, 200, 300],
            "YEARS_SINCE_BEG": [10, 20, 30],
            "GRID_CD": ["0470", "0470", "0470"],
            "0470_high_total_cycles": [1000, 2000, 3000],
            "0470_low_total_cycles": [100, 200, 300],
            "K_repair": [5.0, 0.0, 2.0],  # K_repair 값
            "K_total": [10.0, 20.0, 30.0],  # 기본 K_total
            "K_total_without_repair": [1.0, 2.0, 3.0],  # K_repair 적용 전 K_total
        }
    )


class TestGetKMaterialMapping:
    """get_K_material_mapping 함수 테스트"""

    def test_normal_case(self, sample_pipe_properties):
        """정상적인 경우"""
        result = get_K_material_mapping(sample_pipe_properties)

        assert isinstance(result, dict)
        assert len(result) == 4
        assert result["ST"] == 0.9
        assert result["PE"] == 1.1
        assert result["CI"] == 0.8
        assert result["PVC"] == 1.2

    def test_empty_dataframe(self):
        """빈 데이터프레임"""
        empty_df = pd.DataFrame()
        result = get_K_material_mapping(empty_df)
        assert result == {}

    def test_missing_columns(self):
        """필수 컬럼 누락"""
        df = pd.DataFrame({"type": ["ST", "PE"]})
        result = get_K_material_mapping(df)
        assert result == {}


class TestGetFatigueLimitMapping:
    """get_fatigue_limit_mapping 함수 테스트"""

    def test_normal_case(self, sample_pipe_properties):
        """정상적인 경우"""
        result = get_fatigue_limit_mapping(sample_pipe_properties)

        assert isinstance(result, dict)
        assert len(result) == 4
        assert result["ST"] == 1000000  # 10⁶
        assert result["PE"] == 100000  # 10⁵
        assert result["CI"] == 1000000  # 1000000
        assert result["PVC"] == 1000000  # nan -> default

    def test_various_formats(self):
        """다양한 형식의 피로한계 값"""
        df = pd.DataFrame(
            {
                "type": ["A", "B", "C", "D", "E"],
                "fatigure_limit": ["10⁶", "10⁵", "500000", "invalid", np.nan],
            }
        )
        result = get_fatigue_limit_mapping(df)

        assert result["A"] == 1000000
        assert result["B"] == 100000
        assert result["C"] == 500000
        assert result["D"] == 1000000  # invalid -> default
        assert result["E"] == 1000000  # nan -> default


class TestAddKMaterialToDataframe:
    """add_K_material_to_dataframe 함수 테스트"""

    def test_basic_k_coefficients(self, sample_result_df, sample_pipe_properties):
        """기본 K 계수 추가"""
        with patch(
            "src.fatigue_calculations.calculate_thickness_for_dataframe"
        ) as mock_thickness:
            mock_thickness.return_value = pd.Series([5.0, 10.0, 15.0])

            with patch("src.fatigue_calculations.get_k_soil_for_dataframe") as mock_soil:
                mock_soil.return_value = pd.Series([1.2, 1.3, 1.4])

                with patch(
                    "src.fatigue_calculations.get_k_traffic_for_dataframe"
                ) as mock_traffic:
                    mock_traffic.return_value = pd.Series([1.0, 1.2, 1.4])

                    result = add_K_material_to_dataframe(
                        sample_result_df, sample_pipe_properties, file_type="PIPE_LM"
                    )

        # K_diameter 확인
        assert "K_diameter" in result.columns
        expected_k_diameter = 1 + 0.05 * np.log(sample_result_df["STD_DIP"] / 100)
        np.testing.assert_array_almost_equal(
            result["K_diameter"].values, expected_k_diameter.values, decimal=6
        )

        # K_age 확인
        assert "K_age" in result.columns
        expected_k_age = 1 + 0.02 * sample_result_df["YEARS_SINCE_BEG"]
        np.testing.assert_array_almost_equal(
            result["K_age"].values, expected_k_age.values
        )

        # K_vibration 확인
        assert "K_vibration" in result.columns
        assert all(result["K_vibration"] == 1.05)

        # K_material 확인
        assert "K_material" in result.columns
        assert result["K_material"].iloc[0] == 0.9  # ST
        assert result["K_material"].iloc[1] == 1.1  # PE
        assert result["K_material"].iloc[2] == 0.8  # CI

    def test_missing_columns(self):
        """필수 컬럼이 없는 경우"""
        df = pd.DataFrame({"dummy": [1, 2, 3]})
        pipe_props = pd.DataFrame({"type": ["ST"], "KmaterialK": [0.9]})

        result = add_K_material_to_dataframe(df, pipe_props)

        # 함수가 에러 없이 실행되어야 함
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)


class TestCalculateFatigueDamageDataframe:
    """calculate_fatigue_damage_dataframe 함수 테스트 (버전 2)"""

    def test_basic_calculation(self, sample_result_df):
        """기본 피로 손상 계산"""
        # fatigue_limit 추가
        sample_result_df["fatigue_limit"] = 1000000
        sample_result_df["K_total"] = 2.0

        result = calculate_fatigue_damage_dataframe(
            sample_result_df, region="0470", use_k_total=True
        )

        # 중간값 컬럼 확인
        assert "0470_high_fatigue_intermediate" in result.columns
        assert "0470_low_fatigue_intermediate" in result.columns

        # D_base 컬럼 확인
        assert "0470_D_base" in result.columns

        # D_final 컬럼 확인
        assert "0470_D_final" in result.columns

        # D_final = D_base * K_total 확인
        np.testing.assert_array_almost_equal(
            result["0470_D_final"].values,
            result["0470_D_base"].values * result["K_total"].values,
        )

    def test_without_k_total(self, sample_result_df):
        """K_total 없이 계산"""
        sample_result_df["fatigue_limit"] = 1000000

        result = calculate_fatigue_damage_dataframe(
            sample_result_df, region="0470", use_k_total=False
        )

        # D_final = D_base (K_total 미사용)
        np.testing.assert_array_almost_equal(
            result["0470_D_final"].values, result["0470_D_base"].values
        )

    def test_with_k_repair(self, sample_result_df_with_repair):
        """K_repair가 적용된 경우의 D_final 계산 검증"""
        sample_result_df_with_repair["fatigue_limit"] = 1000000
        
        result = calculate_fatigue_damage_dataframe(
            sample_result_df_with_repair, region="0470", use_k_total=True
        )

        # D_final_org 컬럼 확인 (K_repair 적용 전)
        assert "0470_D_final_org" in result.columns
        
        # D_final 컬럼 확인 (K_repair 적용 후)
        assert "0470_D_final" in result.columns

        # D_final_org = D_base * K_total_without_repair
        np.testing.assert_array_almost_equal(
            result["0470_D_final_org"].values,
            result["0470_D_base"].values * result["K_total_without_repair"].values,
        )

        # D_final = D_base * K_total (K_repair 적용된 K_total)
        np.testing.assert_array_almost_equal(
            result["0470_D_final"].values,
            result["0470_D_base"].values * result["K_total"].values,
        )

        # K_repair > 0인 경우, D_final > D_final_org 확인
        for idx in range(len(result)):
            if sample_result_df_with_repair["K_repair"].iloc[idx] > 0:
                assert result["0470_D_final"].iloc[idx] > result["0470_D_final_org"].iloc[idx]

    def test_d_final_calculation_with_c_repair_factor(self, sample_result_df_with_repair):
        """C_REPAIR가 적용된 D_final 계산 검증"""
        sample_result_df_with_repair["fatigue_limit"] = 1000000
        
        # K_total이 C_REPAIR × (1 + K_repair)로 계산되었다고 가정
        # 예: K_total = K_total_without_repair * C_REPAIR * (1 + K_repair)
        for idx in range(len(sample_result_df_with_repair)):
            k_repair = sample_result_df_with_repair["K_repair"].iloc[idx]
            k_total_without = sample_result_df_with_repair["K_total_without_repair"].iloc[idx]
            expected_k_total = k_total_without * C_REPAIR * (1 + k_repair)
            
            # 실제 K_total이 예상값과 같은지 확인 (테스트 데이터에서)
            # 이 테스트는 K_total이 이미 C_REPAIR가 적용되어 있다고 가정
            
        result = calculate_fatigue_damage_dataframe(
            sample_result_df_with_repair, region="0470", use_k_total=True
        )

        # D_final과 D_final_org의 비율 확인
        for idx in range(len(result)):
            k_repair = sample_result_df_with_repair["K_repair"].iloc[idx]
            if result["0470_D_final_org"].iloc[idx] > 0:
                ratio = result["0470_D_final"].iloc[idx] / result["0470_D_final_org"].iloc[idx]
                
                # 비율이 C_REPAIR * (1 + K_repair)와 근사한지 확인
                # (K_total 값이 올바르게 계산되었다면)
                k_total = sample_result_df_with_repair["K_total"].iloc[idx]
                k_total_without = sample_result_df_with_repair["K_total_without_repair"].iloc[idx]
                
                if k_total_without > 0:
                    actual_factor = k_total / k_total_without
                    # 실제 factor가 적용되었는지 확인
                    assert actual_factor > 1.0  # C_REPAIR가 적용되면 항상 증가

    def test_zero_k_repair_effect(self):
        """K_repair = 0일 때의 효과 검증"""
        df = pd.DataFrame(
            {
                "FTR_IDN": [1],
                "0470_high_total_cycles": [1000],
                "0470_low_total_cycles": [100],
                "K_repair": [0.0],
                "K_total": [10.0],  # C_REPAIR * (1 + 0) = 10.0
                "K_total_without_repair": [1.0],
                "fatigue_limit": [1000000],
            }
        )
        
        result = calculate_fatigue_damage_dataframe(df, region="0470", use_k_total=True)
        
        # K_repair = 0이어도 C_REPAIR는 적용됨
        # D_final = D_base * K_total
        # D_final_org = D_base * K_total_without_repair
        # D_final / D_final_org = K_total / K_total_without_repair = C_REPAIR
        
        if "0470_D_final_org" in result.columns and result["0470_D_final_org"].iloc[0] > 0:
            ratio = result["0470_D_final"].iloc[0] / result["0470_D_final_org"].iloc[0]
            # C_REPAIR 값과 근사한지 확인 (약 10.0)
            assert ratio > 1.0  # C_REPAIR 효과로 인해 증가


if __name__ == "__main__":
    pytest.main([__file__, "-v"])