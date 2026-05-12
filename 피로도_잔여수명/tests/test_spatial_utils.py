"""
spatial_utils 모듈 테스트
"""

import unittest

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from src.common.spatial_utils import (
    calculate_ann_distance,
    calculate_getis_ord_gi,
    calculate_morans_i,
    calculate_spatial_lag,
    convert_to_epsg5179,
    create_distance_band_weights,
    create_spacetime_grid,
    create_spatial_weights_matrix,
    identify_hotspots,
)


class TestSpatialUtils(unittest.TestCase):
    """공간 유틸리티 함수 테스트"""

    def setUp(self):
        """테스트용 데이터 생성"""
        # 테스트용 포인트 데이터 생성 (3x3 그리드)
        self.coords = np.array(
            [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [1, 2], [2, 2]]
        )

        # GeoDataFrame 생성
        points = [Point(x, y) for x, y in self.coords]
        self.gdf = gpd.GeoDataFrame(
            {
                "id": range(9),
                "value": [1, 2, 3, 2, 5, 2, 3, 2, 1],
                "작업종료일": pd.date_range("2024-01-01", periods=9, freq="W"),
            },
            geometry=points,
            crs="EPSG:5186",
        )

    def test_create_spatial_weights_matrix_distance(self):
        """거리 기반 공간 가중치 행렬 생성 테스트"""
        W = create_spatial_weights_matrix(
            self.gdf, method="distance", threshold=1.5, binary=True
        )

        # 행렬 크기 확인
        self.assertEqual(W.shape, (9, 9))

        # 대각선 요소가 0인지 확인
        self.assertTrue(np.allclose(np.diag(W), 0))

        # 행 합이 1 또는 0인지 확인 (행 표준화)
        row_sums = W.sum(axis=1)
        self.assertTrue(np.all((row_sums == 0) | (np.abs(row_sums - 1) < 1e-10)))

    def test_create_spatial_weights_matrix_knn(self):
        """KNN 기반 공간 가중치 행렬 생성 테스트"""
        W = create_spatial_weights_matrix(self.gdf, method="knn", k=4, binary=True)

        # 행렬 크기 확인
        self.assertEqual(W.shape, (9, 9))

        # 각 행에 정확히 4개의 이웃이 있는지 확인
        for i in range(9):
            self.assertEqual(np.sum(W[i] > 0), 4)

    def test_create_spacetime_grid(self):
        """시공간 그리드 생성 테스트"""
        grid = create_spacetime_grid(
            self.gdf, grid_size=1.0, time_column="작업종료일", time_interval="1M"
        )

        # 그리드가 생성되었는지 확인
        self.assertIsInstance(grid, gpd.GeoDataFrame)
        self.assertIn("geometry", grid.columns)
        self.assertIn("cell_id", grid.columns)
        self.assertIn("time_bin", grid.columns)
        self.assertIn("point_count", grid.columns)

    def test_calculate_spatial_lag(self):
        """공간 지연 계산 테스트"""
        W = create_spatial_weights_matrix(
            self.gdf, method="distance", threshold=1.5, binary=True
        )

        values = self.gdf["value"].values
        lag = calculate_spatial_lag(values, W)

        # 결과 크기 확인
        self.assertEqual(len(lag), len(values))

        # 모든 값이 유한한지 확인
        self.assertTrue(np.all(np.isfinite(lag)))

    def test_calculate_morans_i(self):
        """Moran's I 계산 테스트"""
        W = create_spatial_weights_matrix(
            self.gdf, method="distance", threshold=1.5, binary=True
        )

        values = self.gdf["value"].values
        I, z_score, p_value = calculate_morans_i(values, W)

        # 결과가 유효한 범위인지 확인
        self.assertTrue(-1 <= I <= 1)
        self.assertTrue(np.isfinite(z_score))
        self.assertTrue(0 <= p_value <= 1)

    def test_calculate_getis_ord_gi(self):
        """Getis-Ord Gi* 계산 테스트"""
        W = create_spatial_weights_matrix(
            self.gdf, method="distance", threshold=1.5, binary=True
        )

        values = self.gdf["value"].values
        z_scores = calculate_getis_ord_gi(values, W, star=True)

        # 결과 크기 확인
        self.assertEqual(len(z_scores), len(values))

        # 모든 값이 유한한지 확인
        self.assertTrue(np.all(np.isfinite(z_scores)))

    def test_identify_hotspots(self):
        """핫스팟 식별 테스트"""
        # 테스트용 z-scores
        z_scores = np.array([-3, -2, -1, 0, 1, 2, 3, 2.5, -2.5])

        hotspots = identify_hotspots(z_scores)

        # 결과 키 확인
        self.assertIn("confidence_90", hotspots)
        self.assertIn("confidence_95", hotspots)
        self.assertIn("confidence_99", hotspots)

        # 99% 신뢰수준에서 극단값만 핫스팟/콜드스팟으로 분류되는지 확인
        confidence_99 = hotspots["confidence_99"]
        self.assertEqual(confidence_99[0], -1)  # -3: 콜드스팟
        self.assertEqual(confidence_99[6], 1)  # 3: 핫스팟

    def test_create_distance_band_weights(self):
        """거리 밴드 가중치 행렬 생성 테스트"""
        W = create_distance_band_weights(
            self.gdf, min_distance=1.0, max_distance=2.0, binary=True
        )

        # 행렬 크기 확인
        self.assertEqual(W.shape, (9, 9))

        # 대각선 요소가 0인지 확인
        self.assertTrue(np.allclose(np.diag(W), 0))

    def test_calculate_ann_distance(self):
        """평균 최근접 이웃 거리 계산 테스트"""
        ann = calculate_ann_distance(self.gdf)

        # 결과가 양수인지 확인
        self.assertGreater(ann, 0)

        # 예상값과 비교 (3x3 그리드에서 이웃 거리는 1)
        self.assertAlmostEqual(ann, 1.0, places=1)

    def test_numpy_array_input(self):
        """numpy array 입력 처리 테스트"""
        # numpy array로 직접 입력
        W = create_spatial_weights_matrix(
            self.coords, method="distance", threshold=1.5, binary=True
        )

        # 결과 확인
        self.assertEqual(W.shape, (9, 9))

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        # 단일 포인트
        single_point = gpd.GeoDataFrame(
            {"value": [1]}, geometry=[Point(0, 0)], crs="EPSG:5186"
        )

        W = create_spatial_weights_matrix(
            single_point, method="distance", threshold=1.0
        )

        self.assertEqual(W.shape, (1, 1))
        self.assertEqual(W[0, 0], 0)

        # 빈 값
        empty_values = np.array([])
        empty_weights = np.array([]).reshape(0, 0)
        lag = calculate_spatial_lag(empty_values, empty_weights)
        self.assertEqual(len(lag), 0)

    def test_convert_to_epsg5179(self):
        """EPSG:5179 좌표계 변환 테스트"""
        # WGS84 좌표계로 GeoDataFrame 생성
        gdf_wgs84 = gpd.GeoDataFrame(
            {"id": [1, 2, 3]},
            geometry=[Point(127.0, 37.5), Point(127.1, 37.6), Point(127.2, 37.7)],
            crs="EPSG:4326",
        )

        # EPSG:5179로 변환
        gdf_5179 = convert_to_epsg5179(gdf_wgs84)

        # 검증
        self.assertEqual(gdf_5179.crs.to_string(), "EPSG:5179")
        self.assertEqual(len(gdf_5179), 3)

        # 이미 EPSG:5179인 경우 그대로 반환
        gdf_5179_2 = convert_to_epsg5179(gdf_5179)
        self.assertEqual(gdf_5179_2.crs.to_string(), "EPSG:5179")
        self.assertTrue(gdf_5179.equals(gdf_5179_2))

        # CRS가 없는 경우 에러 발생
        gdf_no_crs = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(127.0, 37.5)])
        with self.assertRaises(ValueError) as context:
            convert_to_epsg5179(gdf_no_crs)
        self.assertIn("좌표계(CRS)가 정의되어 있지 않습니다", str(context.exception))


if __name__ == "__main__":
    unittest.main()
