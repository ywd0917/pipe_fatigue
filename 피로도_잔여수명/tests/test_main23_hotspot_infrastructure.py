"""
test_main23_hotspot_infrastructure.py

main23_infrastructure_risk.py 테스트
"""

import os
import shutil
import tempfile
import unittest
import warnings
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

from src.main23_infrastructure_risk import InfrastructureCorrelationAnalyzer

warnings.filterwarnings("ignore")


class TestInfrastructureCorrelationAnalyzer(unittest.TestCase):
    """인프라 상관관계 분석 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = InfrastructureCorrelationAnalyzer(
            hotspot_dir=self.temp_dir, output_dir=self.temp_dir
        )

        # 테스트용 핫스팟 데이터 생성
        np.random.seed(42)
        n_cells = 50

        # 그리드 셀 생성
        grid_cells = []
        for i in range(n_cells):
            x_min = 344000 + i * 100
            y_min = 366500 + i * 100
            grid_cells.append(
                Polygon(
                    [
                        (x_min, y_min),
                        (x_min + 100, y_min),
                        (x_min + 100, y_min + 100),
                        (x_min, y_min + 100),
                    ]
                )
            )

        self.analyzer.hotspot_gdf = gpd.GeoDataFrame(
            {
                "cell_id": range(n_cells),
                "gi_star_z": np.random.randn(n_cells),
                "hotspot_confidence_90": np.random.choice(
                    [0, 1, -1], n_cells, p=[0.8, 0.15, 0.05]
                ),
                "hotspot_confidence_95": np.random.choice(
                    [0, 1, -1], n_cells, p=[0.9, 0.08, 0.02]
                ),
                "hotspot_confidence_99": np.random.choice(
                    [0, 1, -1], n_cells, p=[0.95, 0.04, 0.01]
                ),
            },
            geometry=grid_cells,
            crs="EPSG:5186",
        )

        # 테스트용 조인트 데이터 생성
        n_joints = 100
        x = np.random.uniform(344000, 346000, n_joints)
        y = np.random.uniform(366500, 368000, n_joints)

        self.analyzer.joint_gdf = gpd.GeoDataFrame(
            {"CNT_JNT": np.random.randint(1, 20, n_joints)},
            geometry=[Point(xi, yi) for xi, yi in zip(x, y, strict=False)],
            crs="EPSG:5186",
        )

        # 테스트용 피로 데이터 생성
        self.analyzer.fatigue_df = pd.DataFrame(
            {
                "x": x[:50],
                "y": y[:50],
                "K_age": np.random.uniform(0.5, 1.5, 50),
                "K_soil": np.random.uniform(0.8, 1.2, 50),
                "K_traffic": np.random.uniform(0.9, 1.1, 50),
                "K_total": np.random.uniform(0.5, 2.0, 50),
                "D_final": np.random.uniform(0.01, 0.1, 50),
            }
        )

    def test_load_hotspot_results(self):
        """핫스팟 결과 로드 테스트"""
        # 테스트용 GeoJSON 파일 생성
        hotspot_file = os.path.join(self.temp_dir, "hotspot_results.geojson")
        self.analyzer.hotspot_gdf.to_file(hotspot_file, driver="GeoJSON")

        # 로드 테스트
        result = self.analyzer.load_hotspot_results()
        self.assertTrue(result)
        self.assertIsNotNone(self.analyzer.hotspot_gdf)
        self.assertGreater(len(self.analyzer.hotspot_gdf), 0)

    def test_analyze_cnt_jnt_correlation(self):
        """CNT_JNT 상관관계 분석 테스트"""
        results = self.analyzer.analyze_cnt_jnt_correlation()

        self.assertIsInstance(results, dict)

        # t-test 결과 확인
        if "ttest_90" in results:
            self.assertIn("t_statistic", results["ttest_90"])
            self.assertIn("p_value", results["ttest_90"])
            self.assertIn("hotspot_mean", results["ttest_90"])
            self.assertIn("normal_mean", results["ttest_90"])

        # 상관계수 확인
        if "correlation" in results:
            self.assertIn("pearson_r", results["correlation"])
            self.assertIn("pearson_p", results["correlation"])

    def test_analyze_kfactors_correlation(self):
        """K-factors 상관관계 분석 테스트"""
        results = self.analyzer.analyze_kfactors_correlation()

        self.assertIsInstance(results, dict)

        # K-factors 분석 결과 확인
        for factor in ["K_age", "K_soil", "K_traffic", "K_total", "D_final"]:
            if factor in results:
                self.assertIn("t_statistic", results[factor])
                self.assertIn("p_value", results[factor])
                self.assertIn("hotspot_mean", results[factor])
                self.assertIn("normal_mean", results[factor])

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.show")
    def test_visualize_results(self, mock_show, mock_savefig):
        """결과 시각화 테스트"""
        # 분석 결과 설정
        self.analyzer.analysis_results = {
            "grid_stats": pd.DataFrame(
                {
                    "cell_id": range(10),
                    "total_cnt_jnt": np.random.randint(0, 100, 10),
                    "gi_star_z": np.random.randn(10),
                    "hotspot_90": np.random.choice([0, 1, -1], 10),
                }
            )
        }

        # 시각화 실행
        self.analyzer.visualize_results()

        # savefig 호출 확인
        self.assertTrue(mock_savefig.called)

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.show")
    def test_visualize_kfactors(self, mock_show, mock_savefig):
        """K-factors 시각화 테스트"""
        # K-factors 결과 설정
        self.analyzer.analysis_results = {
            "kfactors": {
                "K_age": {
                    "t_statistic": 2.5,
                    "p_value": 0.02,
                    "hotspot_mean": 1.2,
                    "normal_mean": 0.9,
                },
                "K_total": {
                    "t_statistic": 1.8,
                    "p_value": 0.08,
                    "hotspot_mean": 1.5,
                    "normal_mean": 1.2,
                },
            }
        }

        # 시각화 실행
        self.analyzer.visualize_kfactors()

        # savefig 호출 확인
        self.assertTrue(mock_savefig.called)

    def test_save_results(self):
        """결과 저장 테스트"""
        # 분석 결과 설정
        self.analyzer.analysis_results = {
            "cnt_jnt": {
                "ttest_90": {
                    "t_statistic": 2.0,
                    "p_value": 0.05,
                    "hotspot_mean": 50.0,
                    "normal_mean": 100.0,
                }
            },
            "grid_stats": pd.DataFrame(
                {"cell_id": [1, 2, 3], "total_cnt_jnt": [10, 20, 30]}
            ),
        }

        # 결과 저장
        self.analyzer.save_results()

        # JSON 파일 확인
        json_file = os.path.join(self.temp_dir, "infrastructure_analysis.json")
        self.assertTrue(os.path.exists(json_file))

        # CSV 파일 확인
        csv_file = os.path.join(self.temp_dir, "cnt_jnt_analysis.csv")
        self.assertTrue(os.path.exists(csv_file))

        # 보고서 파일 확인
        report_file = os.path.join(self.temp_dir, "infrastructure_report.md")
        self.assertTrue(os.path.exists(report_file))

    def test_generate_report(self):
        """보고서 생성 테스트"""
        # 필요한 데이터 설정
        self.analyzer.analysis_results = {
            "cnt_jnt": {
                "ttest_90": {
                    "t_statistic": 2.0,
                    "p_value": 0.03,
                    "hotspot_mean": 50.0,
                    "normal_mean": 100.0,
                }
            }
        }

        # 보고서 생성
        self.analyzer.generate_report()

        # 보고서 파일 확인
        report_file = os.path.join(self.temp_dir, "infrastructure_report.md")
        self.assertTrue(os.path.exists(report_file))

        # 보고서 내용 확인
        with open(report_file, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("핫스팟-인프라 상관관계 분석", content)
            self.assertIn("CNT_JNT", content)

    def test_run_analysis_without_data(self):
        """데이터 없이 분석 실행 테스트"""
        analyzer = InfrastructureCorrelationAnalyzer(
            hotspot_dir="/non/existent/path", output_dir=self.temp_dir
        )

        result = analyzer.run_analysis()
        self.assertFalse(result)

    def tearDown(self):
        """테스트 정리"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    unittest.main()
