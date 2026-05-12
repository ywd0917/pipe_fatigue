"""
test_main20_optimize_parameters.py

main20_optimize_parameters.py 스크립트에 대한 테스트
"""

import json
import os
import tempfile
import unittest

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from src.main20_optimize_parameters import ParameterOptimizer, load_repair_data


class TestParameterOptimizer(unittest.TestCase):
    """파라미터 최적화 테스트"""

    def setUp(self):
        """테스트 데이터 생성"""
        # 더미 GeoDataFrame 생성
        np.random.seed(42)
        n_points = 100

        # 랜덤 좌표 생성
        x = np.random.uniform(344000, 346000, n_points)
        y = np.random.uniform(366000, 368000, n_points)

        # 시간 데이터 생성
        dates = pd.date_range("2022-01-01", periods=n_points, freq="D")

        # GeoDataFrame 생성
        self.gdf = gpd.GeoDataFrame(
            {
                "x": x,
                "y": y,
                "작업종료일": dates.strftime("%Y%m%d%H%M"),
                "CNT_JNT": np.random.randint(1, 20, n_points),
                "K_total": np.random.uniform(0.5, 2.0, n_points),
                "D_final": np.random.uniform(0.01, 0.1, n_points),
            },
            geometry=[Point(xi, yi) for xi, yi in zip(x, y, strict=False)],
            crs="EPSG:5186",
        )

        # 최적화 객체 생성
        self.optimizer = ParameterOptimizer(self.gdf, memory_limit=1.0)

    def test_calculate_average_nearest_neighbor(self):
        """평균 최근접 이웃 거리 계산 테스트"""
        from src.common.spatial_utils import calculate_ann_distance

        ann_distance = calculate_ann_distance(self.gdf)

        # 결과가 양수인지 확인
        self.assertGreater(ann_distance, 0)

        # 합리적인 범위인지 확인 (1m ~ 1000m)
        self.assertLess(ann_distance, 1000)
        self.assertGreater(ann_distance, 1)

    def test_calculate_morans_i(self):
        """Moran's I 계산 테스트"""
        from src.common.spatial_utils import calculate_morans_i

        # 테스트용 간단한 값 배열
        values = np.array([1, 2, 1, 2, 1])
        W = np.array(
            [
                [0, 1, 0, 0, 0],
                [1, 0, 1, 0, 0],
                [0, 1, 0, 1, 0],
                [0, 0, 1, 0, 1],
                [0, 0, 0, 1, 0],
            ]
        )

        I, z_score, p_value = calculate_morans_i(values, W)

        # Moran's I는 -1과 1 사이
        self.assertGreaterEqual(I, -1)
        self.assertLessEqual(I, 1)

        # p-value는 0과 1 사이
        self.assertGreaterEqual(p_value, 0)
        self.assertLessEqual(p_value, 1)

    def test_optimize_spatial_parameters(self):
        """공간 파라미터 최적화 테스트"""
        params = self.optimizer.optimize_spatial_parameters()

        # 필수 키 확인
        self.assertIn("grid_size", params)
        self.assertIn("distance_threshold", params)
        self.assertIn("k_neighbors", params)

        # 값 범위 확인
        self.assertGreater(params["grid_size"], 0)
        self.assertGreater(params["distance_threshold"], 0)
        self.assertGreater(params["k_neighbors"], 0)

        # grid_size는 10-100 사이
        self.assertGreaterEqual(params["grid_size"], 10)
        self.assertLessEqual(params["grid_size"], 100)

    def test_optimize_temporal_parameters(self):
        """시간 파라미터 최적화 테스트"""
        # grid_size 파라미터 추가
        params = self.optimizer.optimize_temporal_parameters(grid_size=30)

        # 필수 키 확인
        self.assertIn("time_interval", params)
        self.assertIn("seasonal_period", params)
        self.assertIn("trend_window", params)
        self.assertIn("knox_distance", params)
        self.assertIn("knox_time", params)

        # 값 유효성 확인
        self.assertIn(
            params["time_interval"], ["1D", "1W", "2W", "1M", "3M", "6M", "1Y"]
        )
        self.assertGreater(params["seasonal_period"], 0)
        self.assertGreater(params["trend_window"], 0)

    def test_optimize_emerging_parameters(self):
        """Emerging 파라미터 최적화 테스트"""
        # time_interval 파라미터 추가
        params = self.optimizer.optimize_emerging_parameters(time_interval="1M")

        # 필수 키 확인
        self.assertIn("lookback_months", params)
        self.assertIn("min_observations", params)
        self.assertIn("trend_threshold", params)

        # 값 범위 확인
        self.assertGreaterEqual(params["lookback_months"], 3)
        self.assertLessEqual(params["lookback_months"], 24)
        self.assertGreater(params["min_observations"], 0)
        self.assertGreater(params["trend_threshold"], 0)

    def test_optimize_integrated(self):
        """통합 최적화 테스트"""
        params = self.optimizer.optimize_integrated()

        # 필수 섹션 확인
        self.assertIn("shared", params)
        self.assertIn("main21", params)
        self.assertIn("main22", params)
        self.assertIn("main23", params)
        self.assertIn("optimization_metrics", params)

        # shared grid_size가 main21과 main22에서 동일한지 확인
        self.assertEqual(params["shared"]["grid_size"], params["main21"]["grid_size"])
        self.assertEqual(params["shared"]["grid_size"], params["main22"]["grid_size"])

    def test_cross_validate_parameters(self):
        """교차 검증 테스트"""
        params = {"grid_size": 30, "distance_threshold": 100}

        # 단일 값 반환으로 수정
        result = self.optimizer.cross_validate_parameters(params)

        # 점수가 유효한 범위인지 확인
        self.assertIsNotNone(result)
        # 결과가 숫자인지 확인
        self.assertIsInstance(result, (int, float))

    def test_save_load_parameters(self):
        """파라미터 저장 및 로드 테스트"""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            # 최적화 실행
            params = self.optimizer.optimize_integrated()

            # 파일로 저장
            with open(temp_file, "w") as f:
                json.dump(params, f, indent=2)

            # 파일에서 로드
            with open(temp_file) as f:
                loaded_params = json.load(f)

            # 동일한지 확인
            self.assertEqual(
                params["shared"]["grid_size"], loaded_params["shared"]["grid_size"]
            )

        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_memory_constraint(self):
        """메모리 제약 테스트"""
        # 작은 메모리 제한으로 최적화
        small_optimizer = ParameterOptimizer(self.gdf, memory_limit=0.1)
        params = small_optimizer.optimize_spatial_parameters()

        # grid_size가 증가했는지 확인 (메모리 절약을 위해)
        self.assertGreaterEqual(params["grid_size"], 30)


class TestDataLoading(unittest.TestCase):
    """데이터 로딩 테스트"""

    def test_load_repair_data(self):
        """실제 데이터 로딩 테스트"""
        # 데이터 파일이 존재하는 경우만 테스트
        data_file = "data/520_area/repairs_with_location_520_v3.csv"

        if os.path.exists(data_file):
            gdf = load_repair_data()

            # GeoDataFrame인지 확인
            self.assertIsInstance(gdf, gpd.GeoDataFrame)

            # 필수 컬럼 확인
            self.assertIn("x", gdf.columns)
            self.assertIn("y", gdf.columns)
            self.assertIn("geometry", gdf.columns)

            # 좌표가 유효한지 확인
            self.assertTrue((gdf["x"] > 0).all())
            self.assertTrue((gdf["y"] > 0).all())


if __name__ == "__main__":
    unittest.main()
