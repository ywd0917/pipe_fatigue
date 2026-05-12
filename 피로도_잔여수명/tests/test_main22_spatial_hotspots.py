"""
test_main21_spatial_hotspots.py

main21_spatial_hotspots.py 스크립트에 대한 테스트
"""

import os
import tempfile
import unittest
import warnings
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

from src.main22_spatial_hotspots import (
    SpatialHotspotAnalyzer,
    load_optimal_parameters,
    load_repair_data,
)

warnings.filterwarnings("ignore")


class TestSpatialHotspotAnalyzer(unittest.TestCase):
    """공간 핫스팟 분석 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        # 더미 GeoDataFrame 생성
        np.random.seed(42)
        n_points = 100

        # 랜덤 좌표 생성
        x = np.random.uniform(344000, 346000, n_points)
        y = np.random.uniform(366500, 368000, n_points)

        # GeoDataFrame 생성
        self.gdf = gpd.GeoDataFrame(
            {
                "x": x,
                "y": y,
                "CNT_JNT": np.random.randint(1, 20, n_points),
                "K_total": np.random.uniform(0.5, 2.0, n_points),
                "D_final": np.random.uniform(0.01, 0.1, n_points),
            },
            geometry=[Point(xi, yi) for xi, yi in zip(x, y, strict=False)],
            crs="EPSG:5186",
        )

        # 파라미터 설정
        self.params = {"grid_size": 60, "distance_threshold": 140, "k_neighbors": 13}

        # 분석기 생성
        self.analyzer = SpatialHotspotAnalyzer(self.gdf, self.params)

    def test_create_grid_aggregation(self):
        """그리드 집계 생성 테스트"""
        grid = self.analyzer.create_grid_aggregation()

        # GeoDataFrame인지 확인
        self.assertIsInstance(grid, gpd.GeoDataFrame)

        # 그리드 셀이 생성되었는지 확인
        self.assertGreater(len(grid), 0)

        # 필수 컬럼 확인
        self.assertIn("repair_count", grid.columns)
        self.assertIn("geometry", grid.columns)

        # geometry가 Polygon인지 확인
        self.assertTrue(all(isinstance(geom, Polygon) for geom in grid.geometry))

    def test_calculate_getis_ord_gi(self):
        """Getis-Ord Gi* 통계 계산 테스트"""
        # 먼저 grid를 생성
        self.analyzer.grid_gdf = self.analyzer.create_grid_aggregation()
        # Getis-Ord Gi* 계산
        grid_with_gi = self.analyzer.calculate_getis_ord_gi()

        # Gi* 관련 컬럼 확인
        self.assertIn("gi_star_z", grid_with_gi.columns)
        # hotspot 컬럼 확인 (실제 구현에서는 hotspot_confidence_90 형식)
        self.assertIn("hotspot_confidence_90", grid_with_gi.columns)
        self.assertIn("hotspot_confidence_95", grid_with_gi.columns)
        self.assertIn("hotspot_confidence_99", grid_with_gi.columns)

        # Z-score 범위 확인 (일반적으로 -10 ~ 10)
        self.assertTrue(
            all(abs(z) < 20 for z in grid_with_gi["gi_star_z"] if not pd.isna(z))
        )

        # 분류 값 확인 (0: Not Significant, 1: Hot Spot, -1: Cold Spot)
        valid_values = [0, 1, -1]  # 실제 구현은 숫자값 사용
        for col in [
            "hotspot_confidence_90",
            "hotspot_confidence_95",
            "hotspot_confidence_99",
        ]:
            self.assertTrue(all(val in valid_values for val in grid_with_gi[col]))

    def test_calculate_global_morans_i(self):
        """Global Moran's I 계산 테스트"""
        # 먼저 grid를 생성
        self.analyzer.grid_gdf = self.analyzer.create_grid_aggregation()
        morans_result = self.analyzer.calculate_global_morans_i()

        # Tuple 반환 확인 (I, z_score, p_value)
        self.assertIsInstance(morans_result, tuple)
        self.assertEqual(len(morans_result), 3)

        I, z_score, p_value = morans_result

        # Moran's I 범위 확인 (-1 ~ 1)
        self.assertGreaterEqual(I, -1)
        self.assertLessEqual(I, 1)

        # P-value 범위 확인
        self.assertGreaterEqual(p_value, 0)
        self.assertLessEqual(p_value, 1)

    def test_analyze_cnt_jnt_correlation(self):
        """CNT_JNT 상관관계 분석 테스트"""
        # 먼저 grid를 생성하고 Getis-Ord Gi* 계산
        self.analyzer.grid_gdf = self.analyzer.create_grid_aggregation()
        self.analyzer.grid_gdf = self.analyzer.calculate_getis_ord_gi()
        correlation = self.analyzer.analyze_cnt_jnt_correlation()

        # 결과 딕셔너리 확인
        self.assertIsInstance(correlation, dict)

        # 통계 정보 확인 - 중첩된 dictionary 구조
        for key in correlation:
            if isinstance(correlation[key], dict):
                # 중첩된 dictionary인 경우
                for subkey in correlation[key]:
                    if isinstance(correlation[key][subkey], dict):
                        self.assertIn("mean", correlation[key][subkey])
                        self.assertIn("median", correlation[key][subkey])
                        self.assertIn("count", correlation[key][subkey])

    def test_save_results(self):
        """결과 저장 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # grid를 먼저 생성하고 분석
            self.analyzer.grid_gdf = self.analyzer.create_grid_aggregation()
            self.analyzer.grid_gdf = self.analyzer.calculate_getis_ord_gi()

            # save_results 메서드 호출
            self.analyzer.save_results(tmpdir)

            # 파일 생성 확인 - 실제 파일명
            expected_files = [
                "hotspot_results.geojson",  # 실제 파일명
                "hotspot_results.csv",
                "hotspot_metadata.json",
            ]

            for file in expected_files:
                file_path = os.path.join(tmpdir, file)
                self.assertTrue(os.path.exists(file_path), f"{file} not created")

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.savefig")
    def test_visualize_hotspots(self, mock_savefig, mock_show):
        """핫스팟 시각화 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # grid를 먼저 생성하고 분석
            self.analyzer.grid_gdf = self.analyzer.create_grid_aggregation()
            self.analyzer.grid_gdf = self.analyzer.calculate_getis_ord_gi()

            # visualize_hotspots 메서드 호출
            self.analyzer.visualize_hotspots(tmpdir)

            # savefig가 호출되었는지 확인
            self.assertTrue(mock_savefig.called)

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.savefig")
    def test_visualize_cnt_jnt_correlation(self, mock_savefig, mock_show):
        """CNT_JNT 상관관계 시각화 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # grid를 먼저 생성하고 분석
            self.analyzer.grid_gdf = self.analyzer.create_grid_aggregation()
            self.analyzer.grid_gdf = self.analyzer.calculate_getis_ord_gi()

            # visualize_cnt_jnt_correlation 메서드 호출
            self.analyzer.visualize_cnt_jnt_correlation(tmpdir)

            # savefig가 호출되었는지 확인
            self.assertTrue(mock_savefig.called)

    def test_generate_report(self):
        """보고서 생성 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # grid를 먼저 생성하고 분석
            self.analyzer.grid_gdf = self.analyzer.create_grid_aggregation()
            self.analyzer.grid_gdf = self.analyzer.calculate_getis_ord_gi()
            # morans_results 설정 (필수)
            self.analyzer.morans_results = {"I": 0.1, "z_score": 1.0, "p_value": 0.3}

            # generate_report 메서드 호출
            self.analyzer.generate_report(tmpdir)

            # 보고서 파일 생성 확인
            report_path = os.path.join(tmpdir, "hotspot_analysis_report.md")
            self.assertTrue(os.path.exists(report_path))

            # 보고서 내용 확인
            with open(report_path, encoding="utf-8") as f:
                content = f.read()
                self.assertIn("# 공간 핫스팟 분석 보고서", content)
                self.assertIn("데이터 개요", content)
                self.assertIn("Global Moran's I", content)


class TestDataLoading(unittest.TestCase):
    """데이터 로딩 테스트"""

    def test_load_repair_data(self):
        """데이터 로딩 테스트"""
        # 실제 파일이 있는 경우만 테스트
        data_file = "data/520_area/repairs_with_location_520_v3.csv"

        if os.path.exists(data_file):
            gdf = load_repair_data()

            # GeoDataFrame인지 확인
            self.assertIsInstance(gdf, gpd.GeoDataFrame)

            # 필수 컬럼 확인
            self.assertIn("x", gdf.columns)
            self.assertIn("y", gdf.columns)
            self.assertIn("geometry", gdf.columns)

    def test_load_optimal_parameters_with_file(self):
        """파일이 있을 때 파라미터 로딩 테스트"""
        # 실제 파일이 있는 경우
        param_file = "results/spatial_analysis/optimal_parameters.json"
        if os.path.exists(param_file):
            params = load_optimal_parameters(use_optimal=True)

            # 파라미터 확인
            self.assertIn("grid_size", params)
            self.assertIn("distance_threshold", params)
            self.assertIn("k_neighbors", params)

    def test_load_optimal_parameters_default(self):
        """기본 파라미터 로딩 테스트"""
        # use_optimal=False일 때 기본값 반환
        params = load_optimal_parameters(use_optimal=False)

        # 파라미터 확인
        self.assertIn("grid_size", params)
        self.assertIn("distance_threshold", params)
        self.assertIn("k_neighbors", params)

        # 기본값 확인
        self.assertEqual(params["grid_size"], 30)
        self.assertEqual(params["distance_threshold"], 100)
        self.assertEqual(params["k_neighbors"], 8)


if __name__ == "__main__":
    unittest.main()
