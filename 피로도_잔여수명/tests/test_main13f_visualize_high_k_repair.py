"""
main13f_visualize_high_k_repair.py 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from src.main13f_visualize_high_k_repair import (
    detect_clusters,
    find_nearby_repairs,
    find_top_k_repair_pipes,
    load_k_repair_data,
    load_pipe_shapefile,
    load_repair_locations,
)


class TestMain13fVisualizeHighKRepair:
    """main13f_visualize_high_k_repair.py 테스트 클래스"""

    @pytest.fixture
    def sample_k_repair_data(self) -> pd.DataFrame:
        """테스트용 K_repair 데이터 생성"""
        return pd.DataFrame({
            "FTR_IDN": ["P001", "P002", "P003", "P004", "P005"],
            "pipe_length": [100.0, 50.0, 200.0, 75.0, 120.0],
            "K_repair": [10, 15, 8, 25, 12],
            "K_repair_per_m": [0.1000, 0.3000, 0.0400, 0.3333, 0.1000],
            "K_repair_ground": [5, 8, 3, 12, 6],
            "K_repair_under": [3, 4, 2, 8, 4],
            "K_repair_emergency": [2, 3, 3, 5, 2],
        })

    @pytest.fixture
    def sample_pipe_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 파이프 GeoDataFrame 생성"""
        pipes = {
            "FTR_IDN": ["P001", "P002", "P003", "P004", "P005"],
            "geometry": [
                LineString([(0, 0), (100, 0)]),
                LineString([(200, 0), (250, 0)]),
                LineString([(0, 100), (200, 100)]),
                LineString([(300, 0), (375, 0)]),
                LineString([(0, 200), (120, 200)]),
            ],
        }
        return gpd.GeoDataFrame(pipes, crs="EPSG:5179")

    @pytest.fixture
    def sample_repair_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 누수 위치 GeoDataFrame 생성"""
        repairs = {
            "repair_type": ["지상누수", "지하누수", "긴급공사", "지상누수", "지상누수"],
            "geometry": [
                Point(50, 10),   # P001 근처
                Point(225, 15),  # P002 근처
                Point(100, 110), # P003 근처
                Point(350, 25),  # P004 근처
                Point(60, 210),  # P005 근처
            ],
        }
        return gpd.GeoDataFrame(repairs, crs="EPSG:5179")

    def test_find_top_k_repair_pipes(self, sample_k_repair_data):
        """상위 K_repair_per_m 파이프 선택 테스트"""
        # Given: 5개 파이프 중 상위 3개 선택
        top_n = 3

        # When: 상위 파이프 선택
        result = find_top_k_repair_pipes(sample_k_repair_data, top_n)

        # Then: K_repair_per_m 내림차순으로 3개 선택됨
        assert len(result) == 3
        assert list(result["FTR_IDN"]) == ["P004", "P002", "P001"]  # 0.3333, 0.3000, 0.1000
        assert list(result["K_repair_per_m"]) == [0.3333, 0.3000, 0.1000]

    def test_find_top_k_repair_pipes_empty(self):
        """빈 데이터에서 상위 파이프 선택 테스트"""
        # Given: 빈 DataFrame
        empty_df = pd.DataFrame({
            "FTR_IDN": [],
            "pipe_length": [],
            "K_repair": [],
            "K_repair_per_m": [],
        })

        # When: 상위 파이프 선택
        result = find_top_k_repair_pipes(empty_df, 5)

        # Then: 빈 결과 반환
        assert len(result) == 0

    def test_find_nearby_repairs(self, sample_pipe_gdf, sample_repair_gdf):
        """파이프 주변 누수 지점 찾기 테스트"""
        # Given: P001 파이프와 30m 거리
        pipe_geometry = sample_pipe_gdf[sample_pipe_gdf["FTR_IDN"] == "P001"].iloc[0].geometry
        distance = 30.0

        # When: 주변 누수 찾기
        result = find_nearby_repairs(pipe_geometry, sample_repair_gdf, distance)

        # Then: P001 근처 누수만 선택됨
        assert len(result) == 1
        assert result.iloc[0]["repair_type"] == "지상누수"

    def test_find_nearby_repairs_no_results(self, sample_pipe_gdf, sample_repair_gdf):
        """파이프 주변에 누수가 없는 경우 테스트"""
        # Given: P001 파이프와 매우 작은 거리 (5m)
        pipe_geometry = sample_pipe_gdf[sample_pipe_gdf["FTR_IDN"] == "P001"].iloc[0].geometry
        distance = 5.0

        # When: 주변 누수 찾기
        result = find_nearby_repairs(pipe_geometry, sample_repair_gdf, distance)

        # Then: 결과 없음
        assert len(result) == 0

    def test_detect_clusters_basic(self):
        """기본 클러스터 탐지 테스트"""
        # Given: 클러스터를 형성하는 누수 지점들
        repairs = gpd.GeoDataFrame({
            "repair_type": ["지상누수", "지상누수", "지하누수", "긴급공사"],
            "geometry": [
                Point(100, 100),  # 클러스터 1
                Point(105, 105),  # 클러스터 1 (거리 ~7m)
                Point(200, 200),  # 독립
                Point(300, 300),  # 독립
            ]
        }, crs="EPSG:5179")

        cluster_radius = 10.0

        # When: 클러스터 탐지
        result = detect_clusters(repairs, cluster_radius)

        # Then: 1개 클러스터 탐지
        assert len(result) == 1
        cluster_center, cluster_count = result[0]
        assert cluster_count == 2
        assert abs(cluster_center.x - 102.5) < 1.0  # 중심점 확인
        assert abs(cluster_center.y - 102.5) < 1.0

    def test_detect_clusters_empty(self):
        """빈 데이터에서 클러스터 탐지 테스트"""
        # Given: 빈 GeoDataFrame
        empty_gdf = gpd.GeoDataFrame({"repair_type": [], "geometry": []}, crs="EPSG:5179")

        # When: 클러스터 탐지
        result = detect_clusters(empty_gdf, 10.0)

        # Then: 클러스터 없음
        assert len(result) == 0

    def test_detect_clusters_no_clusters(self):
        """클러스터가 형성되지 않는 경우 테스트"""
        # Given: 서로 멀리 떨어진 누수 지점들
        repairs = gpd.GeoDataFrame({
            "repair_type": ["지상누수", "지하누수", "긴급공사"],
            "geometry": [
                Point(0, 0),
                Point(100, 0),
                Point(0, 100),
            ]
        }, crs="EPSG:5179")

        cluster_radius = 10.0

        # When: 클러스터 탐지
        result = detect_clusters(repairs, cluster_radius)

        # Then: 클러스터 없음
        assert len(result) == 0

    @patch("src.main13f_visualize_high_k_repair.pd.read_csv")
    def test_load_k_repair_data_success(self, mock_read_csv):
        """K_repair 데이터 로드 성공 테스트"""
        # Given: 모킹된 CSV 데이터
        mock_df = pd.DataFrame({
            "FTR_IDN": ["P001", "P002"],
            "K_repair_per_m": [0.1, 0.2],
        })
        mock_read_csv.return_value = mock_df

        # When: 데이터 로드
        with patch("src.main13f_visualize_high_k_repair.get_config") as mock_config:
            mock_config.return_value.RESULTS_DIR = Path("/mock/results")
            with patch("pathlib.Path.exists", return_value=True):
                result = load_k_repair_data("PIPE_LM")

        # Then: 데이터 로드 성공
        assert result is not None
        assert len(result) == 2

    @patch("src.main13f_visualize_high_k_repair.pd.read_csv")
    def test_load_k_repair_data_file_not_found(self, mock_read_csv):
        """K_repair 데이터 파일이 없는 경우 테스트"""
        # Given: 파일이 존재하지 않음
        with patch("pathlib.Path.exists", return_value=False):
            # When: 데이터 로드 시도
            result = load_k_repair_data("PIPE_LM")

        # Then: None 반환
        assert result is None

    @patch("src.main13f_visualize_high_k_repair.gpd.read_file")
    def test_load_pipe_shapefile_success(self, mock_read_file):
        """파이프 shapefile 로드 성공 테스트"""
        # Given: 모킹된 shapefile 데이터
        mock_gdf = gpd.GeoDataFrame({
            "FTR_IDN": ["P001", "P002"],
            "geometry": [LineString([(0, 0), (100, 0)]), LineString([(0, 100), (100, 100)])],
        }, crs="EPSG:5179")
        mock_read_file.return_value = mock_gdf

        # When: shapefile 로드
        with patch("src.main13f_visualize_high_k_repair.get_config") as mock_config:
            mock_config.return_value.RAW_DATA_DIR = Path("/mock/data")
            with patch("pathlib.Path.glob", return_value=[Path("/mock/data/export_shp_0520")]):
                with patch("pathlib.Path.exists", return_value=True):
                    result = load_pipe_shapefile("PIPE_LM")

        # Then: 데이터 로드 성공
        assert result is not None
        assert len(result) == 2

    @patch("src.main13f_visualize_high_k_repair.pd.read_csv")
    def test_load_repair_locations_success(self, mock_read_csv):
        """누수 위치 데이터 로드 성공 테스트"""
        # Given: 모킹된 CSV 데이터
        mock_df = pd.DataFrame({
            "파일타입": ["지상누수", "지하누수"],
            "위도": [37.5, 37.6],
            "경도": [126.9, 127.0],
        })
        mock_read_csv.return_value = mock_df

        # When: 데이터 로드
        with patch("src.main13f_visualize_high_k_repair.get_config") as mock_config:
            mock_config.return_value.UNIFIED_REPAIR_CSV = Path("/mock/repair.csv")
            with patch("pathlib.Path.exists", return_value=True):
                result = load_repair_locations()

        # Then: GeoDataFrame 생성 및 좌표계 변환 확인
        assert result is not None
        assert len(result) == 2
        assert result.crs.to_string() == "EPSG:5179"
        assert "repair_type" in result.columns

    def test_integration_workflow(self, sample_k_repair_data, sample_pipe_gdf, sample_repair_gdf):
        """통합 워크플로우 테스트"""
        # Given: 샘플 데이터
        top_n = 2
        distance = 30.0

        # When: 전체 워크플로우 실행
        # 1. 상위 파이프 선택
        top_pipes = find_top_k_repair_pipes(sample_k_repair_data, top_n)

        # 2. 첫 번째 파이프의 주변 누수 찾기
        first_pipe_row = top_pipes.iloc[0]
        pipe_geometry = sample_pipe_gdf[
            sample_pipe_gdf["FTR_IDN"] == first_pipe_row["FTR_IDN"]
        ].iloc[0].geometry
        nearby_repairs = find_nearby_repairs(pipe_geometry, sample_repair_gdf, distance)

        # 3. 클러스터 탐지
        clusters = detect_clusters(nearby_repairs, 10.0)

        # Then: 각 단계 결과 확인
        assert len(top_pipes) == 2
        assert top_pipes.iloc[0]["FTR_IDN"] == "P004"  # 최고 K_repair_per_m
        assert len(nearby_repairs) >= 0  # 주변 누수 결과
        assert len(clusters) >= 0  # 클러스터 결과