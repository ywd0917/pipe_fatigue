"""
main14_common/correlation_analysis.py 테스트 모듈
재작업과 파이프 위험 요인 간 상관관계 분석 공통 함수 테스트
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.main14_common.correlation_analysis import (
    analyze_correlation,
    calculate_correlations_by_strategy,
    find_best_correlation,
    perform_group_comparison,
)


class TestCorrelationAnalysis(unittest.TestCase):
    """상관관계 분석 함수 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        # 테스트용 데이터프레임 생성
        self.test_data = pd.DataFrame(
            {
                "cluster_id": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "repair_count": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "max_K_age": [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8],
                "nearest_K_age": [0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7],
                "avg_K_age": [
                    0.95,
                    1.15,
                    1.35,
                    1.55,
                    1.75,
                    1.95,
                    2.15,
                    2.35,
                    2.55,
                    2.75,
                ],
                "max_K_soil": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4],
                "nearest_K_soil": [
                    0.45,
                    0.55,
                    0.65,
                    0.75,
                    0.85,
                    0.95,
                    1.05,
                    1.15,
                    1.25,
                    1.35,
                ],
                "avg_K_soil": [
                    0.475,
                    0.575,
                    0.675,
                    0.775,
                    0.875,
                    0.975,
                    1.075,
                    1.175,
                    1.275,
                    1.375,
                ],
                "max_D_final": [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55],
                "nearest_D_final": [
                    0.09,
                    0.14,
                    0.19,
                    0.24,
                    0.29,
                    0.34,
                    0.39,
                    0.44,
                    0.49,
                    0.54,
                ],
                "avg_D_final": [
                    0.095,
                    0.145,
                    0.195,
                    0.245,
                    0.295,
                    0.345,
                    0.395,
                    0.445,
                    0.495,
                    0.545,
                ],
            }
        )

        self.analysis_factors = ["K_age", "K_soil", "D_final"]

    def test_analyze_correlation_basic(self):
        """analyze_correlation 기본 기능 테스트"""
        results = analyze_correlation(
            self.test_data, self.analysis_factors, min_repairs_for_frequent=5
        )

        # 결과 키 확인
        self.assertIn("best_factor", results)
        self.assertIn("best_strategy", results)
        self.assertIn("best_corr", results)
        self.assertIn("frequent_count", results)
        self.assertIn("normal_count", results)

        # 상관계수 키 존재 확인
        for factor in self.analysis_factors:
            for strategy in ["max", "nearest", "avg"]:
                self.assertIn(f"{strategy}_{factor}_corr", results)
                self.assertIn(f"{strategy}_{factor}_p", results)

        # 그룹 카운트 확인
        self.assertEqual(results["frequent_count"], 6)  # repair_count >= 5
        self.assertEqual(results["normal_count"], 4)  # repair_count < 5

    def test_analyze_correlation_perfect_correlation(self):
        """완벽한 상관관계 테스트"""
        # 완벽한 양의 상관관계 데이터
        perfect_data = pd.DataFrame(
            {
                "repair_count": [1, 2, 3, 4, 5],
                "max_perfect": [1, 2, 3, 4, 5],
                "nearest_perfect": [1, 2, 3, 4, 5],
                "avg_perfect": [1, 2, 3, 4, 5],
            }
        )

        results = analyze_correlation(
            perfect_data, ["perfect"], min_repairs_for_frequent=3
        )

        # 상관계수가 1에 가까운지 확인
        self.assertAlmostEqual(results["max_perfect_corr"], 1.0, places=5)
        self.assertAlmostEqual(results["nearest_perfect_corr"], 1.0, places=5)
        self.assertAlmostEqual(results["avg_perfect_corr"], 1.0, places=5)

    def test_analyze_correlation_negative_correlation(self):
        """음의 상관관계 테스트"""
        # 완벽한 음의 상관관계 데이터
        negative_data = pd.DataFrame(
            {
                "repair_count": [1, 2, 3, 4, 5],
                "max_negative": [5, 4, 3, 2, 1],
                "nearest_negative": [5, 4, 3, 2, 1],
                "avg_negative": [5, 4, 3, 2, 1],
            }
        )

        results = analyze_correlation(
            negative_data, ["negative"], min_repairs_for_frequent=3
        )

        # 상관계수가 -1에 가까운지 확인
        self.assertAlmostEqual(results["max_negative_corr"], -1.0, places=5)
        self.assertAlmostEqual(results["nearest_negative_corr"], -1.0, places=5)
        self.assertAlmostEqual(results["avg_negative_corr"], -1.0, places=5)

    def test_analyze_correlation_insufficient_data(self):
        """데이터 부족 상황 테스트"""
        # 데이터가 1개만 있는 경우
        insufficient_data = pd.DataFrame(
            {
                "repair_count": [1],
                "max_test": [1.0],
                "nearest_test": [1.0],
                "avg_test": [1.0],
            }
        )

        results = analyze_correlation(
            insufficient_data, ["test"], min_repairs_for_frequent=2
        )

        # 상관계수가 0이고 p-value가 1인지 확인
        self.assertEqual(results["max_test_corr"], 0.0)
        self.assertEqual(results["max_test_p"], 1.0)

    def test_calculate_correlations_by_strategy(self):
        """전략별 상관계수 계산 테스트"""
        correlations = calculate_correlations_by_strategy(
            self.test_data, self.analysis_factors
        )

        # 모든 전략과 요인에 대한 상관계수 존재 확인
        for factor in self.analysis_factors:
            for strategy in ["max", "nearest", "avg"]:
                self.assertIn(f"{strategy}_{factor}_corr", correlations)
                self.assertIn(f"{strategy}_{factor}_p", correlations)

                # 상관계수가 -1과 1 사이인지 확인
                corr = correlations[f"{strategy}_{factor}_corr"]
                self.assertGreaterEqual(corr, -1.0)
                self.assertLessEqual(corr, 1.0)

                # p-value가 0과 1 사이인지 확인
                p_val = correlations[f"{strategy}_{factor}_p"]
                self.assertGreaterEqual(p_val, 0.0)
                self.assertLessEqual(p_val, 1.0)

    def test_calculate_correlations_custom_strategies(self):
        """커스텀 전략 리스트 테스트"""
        custom_strategies = ["max", "nearest"]
        correlations = calculate_correlations_by_strategy(
            self.test_data, self.analysis_factors, strategies=custom_strategies
        )

        # 지정된 전략만 결과에 포함되는지 확인
        for factor in self.analysis_factors:
            self.assertIn(f"max_{factor}_corr", correlations)
            self.assertIn(f"nearest_{factor}_corr", correlations)
            self.assertNotIn(f"avg_{factor}_corr", correlations)

    def test_perform_group_comparison(self):
        """그룹 비교 함수 테스트"""
        comparison = perform_group_comparison(
            self.test_data, self.analysis_factors, min_repairs_for_frequent=5
        )

        # 그룹 카운트 확인
        self.assertEqual(comparison["frequent_count"], 6)
        self.assertEqual(comparison["normal_count"], 4)

        # t-test 결과 확인
        for factor in self.analysis_factors:
            for strategy in ["max", "nearest", "avg"]:
                col_name = f"{strategy}_{factor}"
                self.assertIn(f"{col_name}_t_stat", comparison)
                self.assertIn(f"{col_name}_t_p", comparison)
                self.assertIn(f"{col_name}_frequent_mean", comparison)
                self.assertIn(f"{col_name}_normal_mean", comparison)

                # 빈번한 그룹의 평균이 더 높은지 확인 (이 테스트 데이터의 경우)
                self.assertGreater(
                    comparison[f"{col_name}_frequent_mean"],
                    comparison[f"{col_name}_normal_mean"],
                )

    def test_perform_group_comparison_empty_group(self):
        """빈 그룹이 있는 경우 테스트"""
        # 모든 데이터가 normal 그룹인 경우
        low_repair_data = self.test_data.copy()
        low_repair_data["repair_count"] = [1, 1, 2, 2, 2, 2, 2, 2, 2, 2]

        comparison = perform_group_comparison(
            low_repair_data,
            self.analysis_factors,
            min_repairs_for_frequent=10,  # 높은 임계값
        )

        self.assertEqual(comparison["frequent_count"], 0)
        self.assertEqual(comparison["normal_count"], 10)

        # t-test 관련 키가 없어야 함 (빈번한 그룹이 비어있으므로)
        for factor in self.analysis_factors:
            for strategy in ["max", "nearest", "avg"]:
                col_name = f"{strategy}_{factor}"
                self.assertNotIn(f"{col_name}_t_stat", comparison)

    def test_find_best_correlation(self):
        """최적 상관관계 찾기 테스트"""
        # 테스트용 결과 딕셔너리
        test_results = {
            "max_K_age_corr": 0.8,
            "nearest_K_age_corr": 0.7,
            "avg_K_age_corr": 0.6,
            "max_K_soil_corr": -0.9,  # 가장 강한 상관관계 (절대값)
            "nearest_K_soil_corr": -0.5,
            "avg_K_soil_corr": -0.4,
            "max_D_final_corr": 0.3,
            "nearest_D_final_corr": 0.2,
            "avg_D_final_corr": 0.1,
        }

        best_factor, best_strategy, best_corr = find_best_correlation(
            test_results, self.analysis_factors
        )

        self.assertEqual(best_factor, "K_soil")
        self.assertEqual(best_strategy, "max")
        self.assertEqual(best_corr, -0.9)

    def test_find_best_correlation_custom_strategies(self):
        """커스텀 전략으로 최적 상관관계 찾기 테스트"""
        test_results = {
            "max_K_age_corr": 0.8,
            "nearest_K_age_corr": 0.9,  # nearest 전략 중 최고
            "avg_K_age_corr": 0.6,  # 제외됨
            "max_K_soil_corr": 0.7,
            "nearest_K_soil_corr": 0.5,
            "avg_K_soil_corr": 0.4,  # 제외됨
        }

        best_factor, best_strategy, best_corr = find_best_correlation(
            test_results, ["K_age", "K_soil"], strategies=["max", "nearest"]
        )

        self.assertEqual(best_factor, "K_age")
        self.assertEqual(best_strategy, "nearest")
        self.assertEqual(best_corr, 0.9)

    def test_find_best_correlation_no_results(self):
        """결과가 없는 경우 테스트"""
        empty_results = {}

        best_factor, best_strategy, best_corr = find_best_correlation(
            empty_results, self.analysis_factors
        )

        self.assertEqual(best_factor, "")
        self.assertEqual(best_strategy, "")
        self.assertEqual(best_corr, 0.0)

    def test_missing_columns(self):
        """필수 컬럼이 없는 경우 테스트"""
        # repair_count 컬럼이 없는 데이터
        incomplete_data = pd.DataFrame(
            {
                "max_K_age": [1.0, 1.2, 1.4],
                "nearest_K_age": [0.9, 1.1, 1.3],
                "avg_K_age": [0.95, 1.15, 1.35],
            }
        )

        with self.assertRaises(KeyError):
            analyze_correlation(incomplete_data, ["K_age"], min_repairs_for_frequent=2)

    @patch("builtins.print")
    def test_print_output(self, mock_print):
        """출력 메시지 테스트"""
        analyze_correlation(
            self.test_data, self.analysis_factors, min_repairs_for_frequent=5
        )

        # 주요 출력 메시지 확인
        print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]

        # 상관관계 분석 시작 메시지
        self.assertTrue(any("상관관계 분석 중" in str(msg) for msg in print_calls))

        # Pearson 상관계수 헤더
        self.assertTrue(any("상관계수 (Pearson)" in str(msg) for msg in print_calls))

        # 그룹 비교 메시지
        self.assertTrue(any("그룹 비교" in str(msg) for msg in print_calls))

        # 가장 강한 상관관계 메시지
        self.assertTrue(any("가장 강한 상관관계" in str(msg) for msg in print_calls))


class TestEdgeCases(unittest.TestCase):
    """엣지 케이스 테스트"""

    def test_nan_values(self):
        """NaN 값이 포함된 데이터 테스트"""
        nan_data = pd.DataFrame(
            {
                "repair_count": [1, 2, 3, np.nan, 5],
                "max_test": [1.0, 2.0, np.nan, 4.0, 5.0],
                "nearest_test": [1.0, 2.0, 3.0, 4.0, np.nan],
                "avg_test": [1.0, np.nan, 3.0, 4.0, 5.0],
            }
        )

        # NaN이 있으면 결과에 NaN이 포함됨
        results = analyze_correlation(nan_data, ["test"], min_repairs_for_frequent=3)

        # 상관계수가 NaN인지 확인
        self.assertTrue(np.isnan(results["max_test_corr"]))

    def test_identical_values(self):
        """모든 값이 동일한 경우 테스트"""
        identical_data = pd.DataFrame(
            {
                "repair_count": [3, 3, 3, 3, 3],
                "max_same": [1.0, 1.0, 1.0, 1.0, 1.0],
                "nearest_same": [1.0, 1.0, 1.0, 1.0, 1.0],
                "avg_same": [1.0, 1.0, 1.0, 1.0, 1.0],
            }
        )

        results = analyze_correlation(
            identical_data, ["same"], min_repairs_for_frequent=3
        )

        # 분산이 0이므로 상관계수를 계산할 수 없음
        # scipy는 이 경우 NaN을 반환
        self.assertTrue(np.isnan(results["max_same_corr"]))

    def test_extreme_values(self):
        """극단적인 값 테스트"""
        extreme_data = pd.DataFrame(
            {
                "repair_count": [1, 1000000, 2, 3, 4],
                "max_extreme": [0.0000001, 1000000.0, 2.0, 3.0, 4.0],
                "nearest_extreme": [1.0, 2.0, 3.0, 4.0, 5.0],
                "avg_extreme": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )

        results = analyze_correlation(
            extreme_data, ["extreme"], min_repairs_for_frequent=10
        )

        # 결과가 정상적으로 반환되는지 확인
        self.assertIn("max_extreme_corr", results)
        self.assertIn("best_factor", results)
        self.assertIn("best_strategy", results)


if __name__ == "__main__":
    unittest.main()
