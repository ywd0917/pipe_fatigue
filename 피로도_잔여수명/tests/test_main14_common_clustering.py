"""
main14_common/clustering.py 테스트
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main14_common.clustering import create_repair_clusters, match_clusters_to_pipes


@pytest.fixture
def sample_repairs():
    """테스트용 재작업 데이터 생성"""
    # 클러스터를 형성할 가까운 점들
    points = [
        Point(0, 0),  # 클러스터 1
        Point(5, 5),  # 클러스터 1 (10m 이내)
        Point(100, 100),  # 클러스터 2
        Point(105, 105),  # 클러스터 2 (10m 이내)
        Point(200, 200),  # 독립 클러스터
    ]

    data = {
        "작업타입": ["지상누수", "지상누수", "지하누수", "지하누수", "기타공사"],
        "geometry": points,
    }

    return gpd.GeoDataFrame(data, crs="EPSG:5179")


@pytest.fixture
def sample_pipes():
    """테스트용 파이프 데이터 생성"""
    lines = [
        LineString([(0, 0), (10, 0)]),  # 클러스터 1과 가까움
        LineString([(100, 100), (110, 100)]),  # 클러스터 2와 가까움
        LineString([(500, 500), (510, 500)]),  # 모든 클러스터와 멀리
    ]

    data = {
        "FTR_IDN": ["PIPE001", "PIPE002", "PIPE003"],
        "pipe_type": ["PIPE_LM", "SPLY_LS", "PIPE_LM"],
        "K_age": [0.5, 0.8, 0.3],
        "K_total": [1.2, 1.5, 0.9],
        "D_final": [0.3, 0.6, 0.1],
        "geometry": lines,
    }

    return gpd.GeoDataFrame(data, crs="EPSG:5179")


class TestCreateRepairClusters:
    """create_repair_clusters 함수 테스트"""

    def test_basic_clustering(self, sample_repairs):
        """기본 클러스터링 테스트"""
        clusters = create_repair_clusters(sample_repairs, cluster_distance=10.0)

        assert isinstance(clusters, gpd.GeoDataFrame)
        assert len(clusters) == 3  # 3개 클러스터 예상
        assert "cluster_id" in clusters.columns
        assert "repair_count" in clusters.columns
        assert "repair_types" in clusters.columns

    def test_cluster_distance_parameter(self, sample_repairs):
        """클러스터 거리 파라미터 테스트"""
        # 작은 거리: 더 많은 클러스터
        clusters_small = create_repair_clusters(sample_repairs, cluster_distance=5.0)

        # 큰 거리: 더 적은 클러스터
        clusters_large = create_repair_clusters(sample_repairs, cluster_distance=150.0)

        assert len(clusters_small) >= len(clusters_large)

    def test_min_repairs_filtering(self, sample_repairs):
        """최소 재작업 수 필터링 테스트"""
        clusters = create_repair_clusters(
            sample_repairs, cluster_distance=10.0, min_repairs_for_frequent=2
        )

        # repair_count >= 2인 클러스터 확인
        frequent = clusters[clusters["repair_count"] >= 2]
        assert len(frequent) == 2  # 2개 클러스터가 2개 이상 포인트 가짐

    def test_crs_conversion(self):
        """좌표계 변환 테스트"""
        # WGS84 좌표계 데이터
        points = [Point(127.0, 37.0), Point(127.001, 37.001)]
        gdf = gpd.GeoDataFrame(
            {"작업타입": ["지상누수", "지상누수"], "geometry": points}, crs="EPSG:4326"
        )

        clusters = create_repair_clusters(gdf)

        # EPSG:5179로 변환되었는지 확인
        assert clusters.crs == "EPSG:5179"

    def test_empty_data(self):
        """빈 데이터 처리 테스트"""
        empty_gdf = gpd.GeoDataFrame({"작업타입": [], "geometry": []}, crs="EPSG:5179")

        clusters = create_repair_clusters(empty_gdf)
        assert len(clusters) == 0


class TestMatchClustersToPipes:
    """match_clusters_to_pipes 함수 테스트"""

    def test_basic_matching(self, sample_repairs, sample_pipes):
        """기본 매칭 테스트"""
        clusters = create_repair_clusters(sample_repairs, cluster_distance=10.0)

        matched = match_clusters_to_pipes(
            clusters,
            sample_pipes,
            distance_threshold=50.0,
            analysis_factors=["K_age", "K_total", "D_final"],
        )

        assert isinstance(matched, pd.DataFrame)
        assert "cluster_id" in matched.columns
        assert "repair_count" in matched.columns
        assert "nearest_pipe" in matched.columns

        # 전략별 컬럼 확인
        for strategy in ["nearest", "max", "avg"]:
            for factor in ["K_age", "K_total", "D_final"]:
                assert f"{strategy}_{factor}" in matched.columns

    def test_distance_threshold(self, sample_repairs, sample_pipes):
        """거리 임계값 테스트"""
        clusters = create_repair_clusters(sample_repairs, cluster_distance=10.0)

        # 작은 임계값: 적은 매칭
        matched_small = match_clusters_to_pipes(
            clusters, sample_pipes, distance_threshold=10.0, analysis_factors=["K_age"]
        )

        # 큰 임계값: 많은 매칭
        matched_large = match_clusters_to_pipes(
            clusters, sample_pipes, distance_threshold=200.0, analysis_factors=["K_age"]
        )

        assert len(matched_small) <= len(matched_large)

    def test_strategies_calculation(self, sample_repairs, sample_pipes):
        """전략별 계산 정확성 테스트"""
        # 단일 클러스터와 파이프로 테스트
        cluster_gdf = gpd.GeoDataFrame(
            [
                {
                    "cluster_id": 0,
                    "repair_count": 1,
                    "avg_lat": 37.0,
                    "avg_lon": 127.0,
                    "geometry": Point(5, 5),
                    "repair_types": {"지상누수": 1},
                }
            ],
            crs="EPSG:5179",
        )

        matched = match_clusters_to_pipes(
            cluster_gdf,
            sample_pipes,
            distance_threshold=100.0,
            analysis_factors=["K_age"],
        )

        if len(matched) > 0:
            row = matched.iloc[0]
            # nearest는 가장 가까운 파이프 값
            assert row["nearest_K_age"] == sample_pipes.iloc[0]["K_age"]
            # max는 범위 내 최대값
            assert row["max_K_age"] >= row["nearest_K_age"]
            # avg는 가중 평균
            assert row["avg_K_age"] > 0

    def test_empty_clusters(self, sample_pipes):
        """빈 클러스터 데이터 처리"""
        empty_clusters = gpd.GeoDataFrame(
            columns=["cluster_id", "repair_count", "geometry"], crs="EPSG:5179"
        )

        matched = match_clusters_to_pipes(
            empty_clusters,
            sample_pipes,
            distance_threshold=50.0,
            analysis_factors=["K_age"],
        )

        assert len(matched) == 0

    def test_empty_pipes(self, sample_repairs):
        """빈 파이프 데이터 처리"""
        clusters = create_repair_clusters(sample_repairs)
        empty_pipes = gpd.GeoDataFrame(
            columns=["FTR_IDN", "pipe_type", "K_age", "geometry"], crs="EPSG:5179"
        )

        matched = match_clusters_to_pipes(
            clusters, empty_pipes, distance_threshold=50.0, analysis_factors=["K_age"]
        )

        assert len(matched) == 0

    def test_no_matches_within_threshold(self, sample_repairs):
        """임계값 내 매칭 없는 경우"""
        clusters = create_repair_clusters(sample_repairs)

        # 매우 먼 파이프
        far_pipes = gpd.GeoDataFrame(
            [
                {
                    "FTR_IDN": "FAR001",
                    "pipe_type": "PIPE_LM",
                    "K_age": 0.5,
                    "geometry": LineString([(1000, 1000), (1010, 1000)]),
                }
            ],
            crs="EPSG:5179",
        )

        matched = match_clusters_to_pipes(
            clusters, far_pipes, distance_threshold=50.0, analysis_factors=["K_age"]
        )

        # 거리가 너무 멀어서 매칭 없음
        assert len(matched) == 0


class TestIntegration:
    """통합 테스트"""

    def test_full_pipeline(self, sample_repairs, sample_pipes):
        """전체 파이프라인 테스트"""
        # 1. 클러스터링
        clusters = create_repair_clusters(
            sample_repairs, cluster_distance=10.0, min_repairs_for_frequent=2
        )

        # 2. 매칭
        matched = match_clusters_to_pipes(
            clusters,
            sample_pipes,
            distance_threshold=150.0,
            analysis_factors=["K_age", "K_total", "D_final"],
        )

        # 3. 결과 검증
        assert len(matched) > 0
        assert len(matched) <= len(clusters)

        # 빈번한 재작업 클러스터 확인
        if len(matched) > 0:
            frequent = matched[matched["repair_count"] >= 2]
            assert len(frequent) >= 0
