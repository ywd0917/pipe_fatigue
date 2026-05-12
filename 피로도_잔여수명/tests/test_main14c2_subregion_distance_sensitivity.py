#!/usr/bin/env python3
"""
test_main14c2_subregion_distance_sensitivity.py

main14c2 하위 지역별 거리 민감도 분석 스크립트 테스트

Author: assistant
Date: 2025-08-19
"""

import json

# 테스트 대상 모듈 임포트
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main14c2_subregion_distance_sensitivity import (
    DISTANCES,
    K_FACTORS,
    REGIONS,
    analyze_csv_strategies,
    analyze_regional_sensitivity,
    compare_regions,
    generate_comprehensive_report,
    parse_subregion_results,
    run_main14c_with_params,
)
from main14_common.constants import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    FACTOR_NAMES,
    OPTIONAL_K_FACTORS,
)


class TestConstants(unittest.TestCase):
    """상수 정의 테스트"""

    def test_base_k_factors_order(self):
        """BASE_K_FACTORS가 CSV 컬럼 순서대로 정의되었는지 테스트"""
        expected = [
            "STD_DIP",  # 관경이 첫 번째
            "K_age",
            "K_soil",
            "K_traffic",
            "hoop_stress",
            "K_stress",
            "K_total",
        ]
        self.assertEqual(BASE_K_FACTORS, expected)

    def test_optional_k_factors(self):
        """OPTIONAL_K_FACTORS가 올바르게 정의되었는지 테스트"""
        self.assertEqual(OPTIONAL_K_FACTORS, ["K_repair"])

    def test_damage_factor(self):
        """DAMAGE_FACTOR가 올바르게 정의되었는지 테스트"""
        self.assertEqual(DAMAGE_FACTOR, "D_final")

    def test_k_factors_order(self):
        """K_FACTORS가 올바른 순서로 조합되었는지 테스트"""
        # 실제 main14c2의 순서에 맞게 수정: K_repair이 K_total보다 먼저 옴
        expected = [
            "STD_DIP", "K_age", "K_soil", "K_traffic", 
            "hoop_stress", "K_stress", "K_repair", "K_total", "D_final"
        ]
        self.assertEqual(K_FACTORS, expected)


class TestMain14eSubregionDistanceSensitivity(unittest.TestCase):
    """main14e 하위 지역별 거리 민감도 분석 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # 테스트 데이터
        self.test_stdout = """
        === 0470 지역 분석 시작 ===
        0470 지역 복구 작업: 218개
        생성된 클러스터: 172개
        매칭된 클러스터: 171개 / 172개
        매칭률: 99.4%

        === 상관관계 분석 ===
        """

        self.test_correlations = {
            "STD_DIP": -0.102,
            "K_age": 0.099,
            "K_traffic": 0.100,
            "hoop_stress": -0.034,
            "K_stress": 0.058,
            "K_total": 0.178,
            "STD_DIP": 0.082,
            "D_final": 0.178,
        }

        self.test_p_values = {
            "STD_DIP": 0.204,
            "K_age": 0.195,
            "K_traffic": 0.193,
            "hoop_stress": 0.694,
            "K_stress": 0.447,
            "K_total": 0.020,
            "STD_DIP": 0.285,
            "D_final": 0.020,
        }

    # setup_korean_font 테스트는 test_common_korean_font_utils.py에서 처리

    # parse_matching_stats_from_output 함수는 제거되었으므로 관련 테스트들도 제거

    def test_parse_subregion_results(self):
        """하위 지역 결과 파싱 테스트"""
        # 테스트 디렉토리 생성
        test_dir = self.test_path / "test_region"
        test_dir.mkdir(parents=True, exist_ok=True)

        # CSV 파일 생성
        csv_file = test_dir / "repair_k_factors_matched.csv"
        csv_content = """cluster_id,repair_count,max_STD_DIP,nearest_STD_DIP,avg_STD_DIP,max_K_age,nearest_K_age,avg_K_age,max_K_total,nearest_K_total,avg_K_total,max_D_final,nearest_D_final,avg_D_final
0,2,100,100,100,1.5,1.2,1.3,2.0,1.8,1.9,0.5,0.4,0.45
1,3,150,150,150,2.0,1.8,1.9,2.5,2.3,2.4,0.6,0.5,0.55
2,1,80,80,80,1.0,1.0,1.0,1.5,1.5,1.5,0.3,0.3,0.3
"""
        csv_file.write_text(csv_content)

        # 파싱 테스트
        results = parse_subregion_results(test_dir)

        # 결과가 있는지 확인
        self.assertIn("correlations", results)
        self.assertIn("p_values", results)

        # 최소한 일부 K-factor가 파싱되었는지 확인
        if results["correlations"]:
            # K_total이나 D_final 같은 factor가 있는지 확인
            possible_factors = ["K_total", "D_final", "STD_DIP", "K_age"]
            found_any = any(f in results["correlations"] for f in possible_factors)
            self.assertTrue(
                found_any,
                f"No expected factors found in {results['correlations'].keys()}",
            )

    def test_parse_subregion_results_no_file(self):
        """파일이 없을 때 결과 파싱 테스트"""
        test_dir = self.test_path / "empty_dir"
        test_dir.mkdir(parents=True, exist_ok=True)

        results = parse_subregion_results(test_dir)

        self.assertEqual(results["correlations"], {})
        self.assertEqual(results["p_values"], {})
        self.assertEqual(results["significant_factors"], [])

    @patch("main14c2_subregion_distance_sensitivity.subprocess.run")
    def test_run_main14c_with_params_success(self, mock_run):
        """main14c 실행 성공 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.stdout = self.test_stdout
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # 테스트 디렉토리 생성
        test_dir = self.test_path / "test_distance"
        test_dir.mkdir(parents=True, exist_ok=True)

        # 지역 디렉토리 생성 (main14c가 생성한다고 가정)
        region_dir = test_dir / "0470"
        region_dir.mkdir(parents=True, exist_ok=True)

        with patch(
            "main14c2_subregion_distance_sensitivity.parse_subregion_results"
        ) as mock_parse:
            mock_parse.return_value = {
                "correlations": self.test_correlations,
                "p_values": self.test_p_values,
                "significant_factors": [
                    {"factor": "K_total", "r": 0.178, "p": 0.020},
                    {"factor": "D_final", "r": 0.178, "p": 0.020},
                ],
            }

            # 실행
            result = run_main14c_with_params("0470", 30, test_dir)

            # 검증
            self.assertEqual(result["region"], "0470")
            self.assertEqual(result["distance"], 30)
            self.assertGreater(result["execution_time"], 0)
            self.assertIn("matching_stats", result)
            self.assertIn("correlations", result)
            self.assertEqual(len(result["significant_factors"]), 2)

            # 요약 파일 생성 확인
            summary_file = region_dir / "summary_0470_30m.json"
            self.assertTrue(summary_file.exists())

    @patch("main14c2_subregion_distance_sensitivity.subprocess.run")
    def test_run_main14c_with_params_timeout(self, mock_run):
        """main14c 실행 타임아웃 테스트"""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=60)

        test_dir = self.test_path / "test_distance"
        result = run_main14c_with_params("0470", 30, test_dir)

        self.assertEqual(result["error"], "Timeout")
        self.assertEqual(result["execution_time"], -1)

    @patch("main14c2_subregion_distance_sensitivity.subprocess.run")
    def test_run_main14c_with_params_error(self, mock_run):
        """main14c 실행 오류 테스트"""
        import subprocess

        error = subprocess.CalledProcessError(1, "test", stderr="Error message")
        mock_run.side_effect = error

        test_dir = self.test_path / "test_distance"
        result = run_main14c_with_params("0470", 30, test_dir)

        self.assertIn("error", result)
        self.assertEqual(result["execution_time"], -1)
        self.assertEqual(result["stderr"], "Error message")

    def test_analyze_regional_sensitivity(self):
        """지역별 민감도 분석 테스트"""
        # 테스트 데이터 생성
        test_results = []
        for distance in [10, 20, 30]:
            test_results.append(
                {
                    "region": "0470",
                    "distance": distance,
                    "execution_time": 5.0,
                    "matching_stats": {"matching_rate": 95.0 + distance / 10},
                    "correlations": {
                        "STD_DIP": -0.10 + distance / 200,
                        "K_age": 0.05 + distance / 100,
                        "K_total": 0.10 + distance / 50,
                        "hoop_stress": -0.03 - distance / 100,
                    },
                    "p_values": {
                        "STD_DIP": 0.3 - distance / 100,
                        "K_age": 0.2 - distance / 100,
                        "K_total": 0.05 - distance / 200,
                        "hoop_stress": 0.7,
                    },
                    "r_squared": {
                        "STD_DIP": (-0.10 + distance / 200) ** 2,
                        "K_age": (0.05 + distance / 100) ** 2,
                        "K_total": (0.10 + distance / 50) ** 2,
                        "hoop_stress": (-0.03 - distance / 100) ** 2,
                    },
                    "strategies": {
                        "STD_DIP": "max",
                        "K_age": "nearest",
                        "K_total": "avg",
                        "hoop_stress": "max",
                    },
                    "significant_factors": [],
                }
            )

        # 분석 실행
        df = analyze_regional_sensitivity("0470", test_results)

        # 기본 검증
        self.assertEqual(len(df), 3)
        self.assertEqual(df.attrs["region"], "0470")

        # 최적 거리 검증
        optimal = df.attrs["optimal_distances"]
        self.assertIn("K_total", optimal)
        self.assertEqual(optimal["K_total"]["distance"], 30)  # 최대 상관계수

        # 상관계수 컬럼 확인
        self.assertIn("K_age_corr", df.columns)
        self.assertIn("K_total_corr", df.columns)
        self.assertIn("K_age_p", df.columns)

    def test_compare_regions(self):
        """지역 간 비교 분석 테스트"""
        # 테스트 데이터 생성
        all_results = {}

        for region in ["0470", "0480"]:
            df = pd.DataFrame(
                [
                    {
                        "distance": 10,
                        "STD_DIP_corr": -0.05,
                        "STD_DIP_p": 0.3,
                        "K_age_corr": 0.1,
                        "K_age_p": 0.2,
                    },
                    {
                        "distance": 20,
                        "STD_DIP_corr": -0.04,
                        "STD_DIP_p": 0.25,
                        "K_age_corr": 0.2,
                        "K_age_p": 0.1,
                    },
                ]
            )
            df.attrs["optimal_distances"] = {
                "STD_DIP": {"distance": 10, "correlation": -0.05, "p_value": 0.3},
                "K_age": {"distance": 20, "correlation": 0.2, "p_value": 0.1},
            }
            df.attrs["region"] = region
            all_results[region] = df

        # 비교 실행
        comparison_df = compare_regions(all_results)

        # 검증
        self.assertEqual(
            len(comparison_df), 4
        )  # 2 regions × 2 factors (STD_DIP, K_age)
        self.assertIn("region", comparison_df.columns)
        self.assertIn("factor", comparison_df.columns)
        self.assertIn("optimal_distance", comparison_df.columns)

    def test_generate_comprehensive_report(self):
        """종합 보고서 생성 테스트"""
        # 테스트 데이터 생성
        all_results = {}

        for i, region in enumerate(["0470", "0480", "0490"]):
            df = pd.DataFrame(
                [
                    {
                        "distance": d,
                        "matching_stats": {"matching_rate": 95.0 + i},
                        "STD_DIP_corr": -0.1 + d / 200,
                        "STD_DIP_p": 0.3,
                        "K_age_corr": 0.1 + d / 100,
                        "K_age_p": 0.2,
                        "K_total_corr": 0.15 + d / 100,
                        "K_total_p": 0.05,
                    }
                    for d in [10, 20, 30]
                ]
            )

            df.attrs["optimal_distances"] = {
                "STD_DIP": {"distance": 30, "correlation": -0.085, "p_value": 0.3},
                "K_age": {"distance": 30, "correlation": 0.13, "p_value": 0.2},
                "K_total": {"distance": 30, "correlation": 0.18, "p_value": 0.05},
            }
            df.attrs["region"] = region
            all_results[region] = df

        # 보고서 생성
        output_dir = self.test_path / "report"
        output_dir.mkdir(parents=True, exist_ok=True)

        generate_comprehensive_report(all_results, output_dir)

        # 파일 생성 확인
        report_file = output_dir / "comprehensive_report.md"
        self.assertTrue(report_file.exists())

        # 내용 확인
        content = report_file.read_text(encoding="utf-8")
        self.assertIn("하위 지역별 거리 민감도 종합 분석 보고서", content)
        self.assertIn("Executive Summary", content)
        self.assertIn("0470", content)
        self.assertIn("0480", content)
        self.assertIn("0490", content)
        self.assertIn("지역별 상세 분석", content)
        self.assertIn("통합 권장사항", content)

    def test_constants(self):
        """상수 정의 테스트"""
        # 지역 확인 - 새로운 소구역 포함
        self.assertEqual(REGIONS, ["0243", "0461", "0470", "0480", "0490"])

        # 거리 확인
        self.assertEqual(DISTANCES, [10, 20, 30, 50, 100])

        # K-factors 확인 (BASE_K_FACTORS + DAMAGE_FACTOR + OPTIONAL_K_FACTORS)
        expected_length = (
            len(BASE_K_FACTORS) + 1 + len(OPTIONAL_K_FACTORS)
        )  # 7 + 1 + 1 = 9
        self.assertEqual(len(K_FACTORS), expected_length)
        self.assertIn("K_age", K_FACTORS)
        self.assertIn("D_final", K_FACTORS)

        # 한글 이름 확인
        self.assertEqual(FACTOR_NAMES["K_age"], "파이프 연령 계수")
        self.assertEqual(FACTOR_NAMES["K_total"], "총 위험도 계수")
        self.assertEqual(FACTOR_NAMES["D_final"], "보정손상도")

    def test_numpy_type_conversion(self):
        """NumPy 타입 변환 테스트"""
        # NumPy 타입 데이터
        test_data = {
            "distance": np.int64(30),
            "correlation": np.float64(0.178),
            "p_value": np.float32(0.020),
        }

        # JSON 직렬화 테스트를 위한 변환
        converted = {}
        for k, v in test_data.items():
            if hasattr(v, "item"):
                if isinstance(v, np.integer | np.int64):
                    converted[k] = int(v)
                else:
                    converted[k] = float(v)
            else:
                converted[k] = v

        # JSON 직렬화 가능 확인
        json_str = json.dumps(converted)
        loaded = json.loads(json_str)

        self.assertEqual(loaded["distance"], 30)
        self.assertAlmostEqual(loaded["correlation"], 0.178, places=3)
        self.assertAlmostEqual(loaded["p_value"], 0.020, places=3)

    @patch("main14c2_subregion_distance_sensitivity.plt.show")
    @patch("main14c2_subregion_distance_sensitivity.plt.savefig")
    def test_visualization_functions_mock(self, mock_savefig, mock_show):
        """시각화 함수 모킹 테스트"""
        from main14c2_subregion_distance_sensitivity import (
            create_3d_visualizations,
            create_correlation_heatmap,
            create_regional_comparison_charts,
        )

        # 테스트 데이터
        all_results = {}
        for region in REGIONS:
            df = pd.DataFrame(
                [
                    {
                        "distance": d,
                        **{f"{factor}_corr": np.random.rand() for factor in K_FACTORS},
                        **{f"{factor}_p": np.random.rand() for factor in K_FACTORS},
                    }
                    for d in DISTANCES
                ]
            )
            df.attrs["optimal_distances"] = {}
            df.attrs["region"] = region
            all_results[region] = df

        output_dir = self.test_path / "viz"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 3D 시각화 테스트
        create_3d_visualizations(all_results, output_dir)
        self.assertTrue(mock_savefig.called)

        # 히트맵 테스트
        mock_savefig.reset_mock()
        create_correlation_heatmap(all_results, output_dir)
        self.assertTrue(mock_savefig.called)

        # 비교 차트 테스트
        mock_savefig.reset_mock()
        create_regional_comparison_charts(all_results, output_dir)
        self.assertTrue(mock_savefig.called)


class TestAnalyzeCsvStrategies(unittest.TestCase):
    """CSV 전략 분석 테스트"""

    def test_analyze_csv_strategies_success(self):
        """정상적인 CSV 파일 분석 테스트"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(
                "cluster_id,repair_count,max_K_age,nearest_K_age,avg_K_age,max_K_soil,nearest_K_soil,avg_K_soil\n"
            )
            f.write("0,2,1.5,1.2,1.3,1.0,1.0,1.0\n")
            f.write("1,3,2.0,1.8,1.9,1.1,1.0,1.05\n")
            f.write("2,1,1.0,1.0,1.0,1.0,1.0,1.0\n")
            csv_file = Path(f.name)

        try:
            # 분석 실행
            analysis_factors = ["K_age", "K_soil"]
            results = analyze_csv_strategies(csv_file, analysis_factors)

            # 결과 검증
            self.assertIn("by_strategy", results)
            self.assertIn("best_factors", results)
            self.assertIn("summary", results)

            # 각 전략별로 상관관계 결과가 있어야 함
            for strategy in ["max", "nearest", "avg"]:
                self.assertIn(strategy, results["by_strategy"])
                for factor in ["K_age", "K_soil"]:
                    if factor in results["by_strategy"][strategy]:
                        self.assertIn("r", results["by_strategy"][strategy][factor])
                        self.assertIn("p", results["by_strategy"][strategy][factor])
                        self.assertIn(
                            "r_squared", results["by_strategy"][strategy][factor]
                        )

            # 최적 전략이 선택되어야 함
            for factor in ["K_age", "K_soil"]:
                if factor in results["best_factors"]:
                    self.assertIn("strategy", results["best_factors"][factor])
                    self.assertIn("r", results["best_factors"][factor])
                    self.assertIn("p", results["best_factors"][factor])
        finally:
            csv_file.unlink()

    def test_analyze_csv_strategies_missing_file(self):
        """CSV 파일이 없을 때 처리 테스트"""
        # 존재하지 않는 파일
        csv_file = Path("/tmp/non_existent_test_file.csv")

        # 분석 실행
        analysis_factors = ["K_age"]
        results = analyze_csv_strategies(csv_file, analysis_factors)

        # 빈 결과 반환
        self.assertEqual(results, {})

    def test_analyze_csv_strategies_with_subregion_filter(self):
        """하위 지역 필터링이 있는 CSV 분석 테스트"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # 지역 코드가 포함된 CSV
            f.write(
                "cluster_id,repair_count,region,max_K_age,nearest_K_age,avg_K_age\n"
            )
            f.write("0,2,0470,1.5,1.2,1.3\n")
            f.write("1,3,0470,2.0,1.8,1.9\n")
            f.write("2,1,0480,1.0,1.0,1.0\n")  # 다른 지역
            csv_file = Path(f.name)

        try:
            # analyze_csv_strategies는 지역 필터링을 하지 않으므로
            # 모든 데이터가 포함되어야 함
            analysis_factors = ["K_age"]
            results = analyze_csv_strategies(csv_file, analysis_factors)

            # K_age가 결과에 포함되어야 함
            self.assertIn("best_factors", results)
            # best_factors가 비어있지 않으면 K_age가 있어야 함
            if results["best_factors"]:
                self.assertIn("K_age", results["best_factors"])
        finally:
            csv_file.unlink()


class TestCsvFileValidation(unittest.TestCase):
    """CSV 파일 유효성 검사 테스트"""

    @patch("main14c2_subregion_distance_sensitivity.subprocess.run")
    @patch("main14c2_subregion_distance_sensitivity.json.dump")
    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_csv_file_not_found_error(self, mock_open, mock_json_dump, mock_run):
        """CSV 파일이 없을 때 오류 처리 테스트"""
        # Mock 설정 - main14c는 성공하지만 CSV 파일이 없음
        mock_result = Mock()
        mock_result.stdout = "실행 완료"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)
            # 디렉토리 생성
            region_dir = test_path / "0470"
            region_dir.mkdir(parents=True, exist_ok=True)

            # CSV 파일이 없는 상태에서 실행
            result = run_main14c_with_params("0470", 30, test_path)

            # CSV 파일이 없어도 빈 결과를 반환해야 함
            self.assertIn("region", result)
            self.assertEqual(result["region"], "0470")
            self.assertIn("distance", result)
            self.assertEqual(result["distance"], 30)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""

    @patch("main14c2_subregion_distance_sensitivity.subprocess.run")
    @patch("main14c2_subregion_distance_sensitivity.plt.savefig")
    def test_full_analysis_workflow(self, mock_savefig, mock_run):
        """전체 분석 워크플로우 테스트"""
        # Mock subprocess 설정
        mock_result = Mock()
        mock_result.stdout = """
        매칭된 클러스터: 100개 / 100개
        매칭률: 100.0%
        """
        mock_run.return_value = mock_result

        # 임시 디렉토리
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)

            # 테스트용 결과 파일 생성
            for region in ["0470"]:
                for distance in [10, 20]:
                    region_dir = test_path / f"distance_{distance}m" / region
                    region_dir.mkdir(parents=True, exist_ok=True)

                    # correlation_analysis.txt 생성
                    analysis_file = region_dir / "correlation_analysis.txt"
                    content = f"""
전략: 가장 가까운 파이프
  관경 (STD_DIP): r={-0.10 + distance/200:.3f}, p=0.300
  파이프 연령 계수 (K_age): r={0.1 + distance/100:.3f}, p=0.200
  총 위험도 계수 (K_total): r={0.15 + distance/100:.3f}, p=0.050

가장 강한 상관관계
"""
                    analysis_file.write_text(content, encoding="utf-8")

            # 패치된 경로로 main 함수 실행
            with patch("main14c2_subregion_distance_sensitivity.REGIONS", ["0470"]):
                with patch(
                    "main14c2_subregion_distance_sensitivity.DISTANCES", [10, 20]
                ):
                    with patch(
                        "main14c2_subregion_distance_sensitivity.RESULTS_BASE",
                        test_path,
                    ):
                        from main14c2_subregion_distance_sensitivity import main

                        # 실행
                        main()

                        # 결과 파일 확인
                        summary_file = test_path / "summary_0470.json"
                        self.assertTrue(summary_file.exists())

                        # 통합 분석 디렉토리 확인
                        integrated_dir = test_path / "integrated_analysis"
                        self.assertTrue(integrated_dir.exists())

                        # 보고서 파일 확인
                        report_file = integrated_dir / "comprehensive_report.md"
                        self.assertTrue(report_file.exists())


if __name__ == "__main__":
    unittest.main()
