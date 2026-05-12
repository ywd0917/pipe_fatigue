"""
analyze13_short_pipes.py 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString

from src.analysis.analyze13_short_pipes import (
    PipeStats,
    analyze_short_pipes,
    create_length_distribution_bins,
    load_pipe_shapefile,
    LENGTH_THRESHOLD,
    BIN_SIZE,
    EXTREME_SHORT_THRESHOLD,
)


class TestAnalyze13ShortPipes:
    """analyze13_short_pipes.py 테스트 클래스"""

    @pytest.fixture
    def sample_pipe_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 파이프 GeoDataFrame 생성"""
        # 다양한 길이의 파이프 생성
        pipes_data = {
            "FTR_IDN": ["P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"],
            "geometry": [
                LineString([(0, 0), (0, 0.05)]),    # 0.05m - 극단적으로 짧음
                LineString([(0, 0), (0, 0.15)]),    # 0.15m 
                LineString([(0, 0), (0, 0.25)]),    # 0.25m
                LineString([(0, 0), (0, 0.45)]),    # 0.45m
                LineString([(0, 0), (0, 0.65)]),    # 0.65m
                LineString([(0, 0), (0, 0.85)]),    # 0.85m
                LineString([(0, 0), (0, 0.95)]),    # 0.95m
                LineString([(0, 0), (0, 1.5)]),     # 1.5m - 1m 초과
                LineString([(0, 0), (0, 2.0)]),     # 2.0m - 1m 초과
                LineString([(0, 0), (0, 0)]),       # 0m - 길이 0
            ]
        }
        gdf = gpd.GeoDataFrame(pipes_data, crs="EPSG:5179")
        gdf["pipe_length"] = gdf.geometry.length
        return gdf

    @pytest.fixture
    def empty_gdf(self) -> gpd.GeoDataFrame:
        """빈 GeoDataFrame"""
        gdf = gpd.GeoDataFrame({"FTR_IDN": [], "geometry": []}, crs="EPSG:5179")
        gdf["pipe_length"] = []  # 빈 pipe_length 컬럼 추가
        return gdf

    def test_analyze_short_pipes_basic(self, sample_pipe_gdf):
        """기본 짧은 파이프 분석 테스트"""
        # Given: 10개 파이프 (8개가 1m 미만)
        
        # When: 짧은 파이프 분석
        short_pipes, stats = analyze_short_pipes(sample_pipe_gdf, "TEST_PIPE")
        
        # Then: 8개 파이프가 1m 미만으로 식별됨
        assert stats.total_count == 10
        assert stats.short_count == 8
        assert stats.short_percentage == 80.0  # 8/10 * 100
        assert len(short_pipes) == 8
        
        # 길이 통계 검증
        assert stats.min_length == 0.0  # 0 길이 파이프 포함
        assert stats.max_length < 1.0   # 모든 짧은 파이프는 1m 미만
        assert stats.mean_length > 0    # 평균 길이는 0보다 커야 함

    def test_analyze_short_pipes_extreme_cases(self, sample_pipe_gdf):
        """극단적 케이스 분석 테스트"""
        # When: 분석 실행
        short_pipes, stats = analyze_short_pipes(sample_pipe_gdf, "TEST_PIPE")
        
        # Then: 특수 케이스 카운트 검증
        assert stats.zero_length_count == 1  # 0 길이 파이프 1개
        assert stats.extreme_short_count == 1  # 0.05m 미만 파이프 1개 (0m 파이프 포함)

    def test_analyze_short_pipes_empty_data(self, empty_gdf):
        """빈 데이터 분석 테스트"""
        # When: 빈 데이터로 분석
        short_pipes, stats = analyze_short_pipes(empty_gdf, "EMPTY_PIPE")
        
        # Then: 모든 값이 0이어야 함
        assert stats.total_count == 0
        assert stats.short_count == 0
        assert stats.short_percentage == 0
        assert len(short_pipes) == 0
        assert stats.zero_length_count == 0
        assert stats.extreme_short_count == 0

    def test_analyze_short_pipes_no_short_pipes(self):
        """짧은 파이프가 없는 경우 테스트"""
        # Given: 모든 파이프가 1m 이상
        long_pipes_data = {
            "FTR_IDN": ["L001", "L002", "L003"],
            "geometry": [
                LineString([(0, 0), (0, 1.5)]),
                LineString([(0, 0), (0, 2.0)]),
                LineString([(0, 0), (0, 3.0)]),
            ]
        }
        long_gdf = gpd.GeoDataFrame(long_pipes_data, crs="EPSG:5179")
        long_gdf["pipe_length"] = long_gdf.geometry.length
        
        # When: 분석 실행
        short_pipes, stats = analyze_short_pipes(long_gdf, "LONG_PIPE")
        
        # Then: 짧은 파이프 없음
        assert stats.total_count == 3
        assert stats.short_count == 0
        assert stats.short_percentage == 0
        assert len(short_pipes) == 0

    def test_create_length_distribution_bins(self, sample_pipe_gdf):
        """길이 분포 구간 생성 테스트"""
        # Given: 짧은 파이프들
        short_pipes = sample_pipe_gdf[sample_pipe_gdf.geometry.length < LENGTH_THRESHOLD]
        
        # When: 길이 분포 구간 생성
        distribution_df = create_length_distribution_bins(short_pipes)
        
        # Then: 구간별 분포 확인
        assert len(distribution_df) == int(LENGTH_THRESHOLD / BIN_SIZE)  # 10개 구간
        assert "bin_range" in distribution_df.columns
        assert "count" in distribution_df.columns
        assert "percentage" in distribution_df.columns
        
        # 첫 번째 구간 확인 (0.0-0.1)
        first_bin = distribution_df.iloc[0]
        assert first_bin["bin_range"] == "0.0-0.1"
        assert first_bin["count"] >= 1  # 적어도 0m, 0.05m 파이프 포함
        
        # 전체 비율 합계는 100%
        assert abs(distribution_df["percentage"].sum() - 100.0) < 1e-10

    def test_create_length_distribution_bins_empty(self, empty_gdf):
        """빈 데이터로 길이 분포 구간 생성 테스트"""
        # When: 빈 데이터로 분포 생성
        distribution_df = create_length_distribution_bins(empty_gdf)
        
        # Then: 빈 DataFrame 반환
        assert len(distribution_df) == 0
        assert list(distribution_df.columns) == ["bin_range", "count", "percentage"]

    def test_pipe_stats_dataclass(self):
        """PipeStats 데이터클래스 테스트"""
        # Given & When: PipeStats 인스턴스 생성
        stats = PipeStats(
            pipe_type="TEST",
            total_count=100,
            short_count=10,
            short_percentage=10.0,
            mean_length=0.5,
            median_length=0.4,
            min_length=0.1,
            max_length=0.9,
            std_length=0.2,
            zero_length_count=1,
            extreme_short_count=2
        )
        
        # Then: 모든 필드가 올바르게 설정됨
        assert stats.pipe_type == "TEST"
        assert stats.total_count == 100
        assert stats.short_count == 10
        assert stats.short_percentage == 10.0
        assert stats.zero_length_count == 1
        assert stats.extreme_short_count == 2

    @patch("src.analysis.analyze13_short_pipes.gpd.read_file")
    def test_load_pipe_shapefile_success(self, mock_read_file):
        """Shapefile 로드 성공 테스트"""
        # Given: 모킹된 GeoDataFrame
        mock_gdf = gpd.GeoDataFrame({
            "FTR_IDN": ["P001", "P002"],
            "geometry": [
                LineString([(0, 0), (0, 1)]),
                LineString([(0, 0), (0, 2)])
            ]
        }, crs="EPSG:5179")
        mock_read_file.return_value = mock_gdf
        
        # When: Shapefile 로드
        with patch("src.analysis.analyze13_short_pipes.get_config") as mock_config:
            mock_config.return_value.RAW_DATA_DIR = Path("/mock/data")
            with patch("pathlib.Path.glob", return_value=[Path("/mock/data/export_shp_0520")]):
                with patch("pathlib.Path.exists", return_value=True):
                    result = load_pipe_shapefile("PIPE_LM", verbose=False)
        
        # Then: 성공적으로 로드되고 길이 계산됨
        assert result is not None
        assert len(result) == 2
        assert "pipe_length" in result.columns
        assert "FTR_IDN" in result.columns

    def test_load_pipe_shapefile_no_export_dir(self):
        """Export 디렉토리가 없는 경우 테스트"""
        # When: Export 디렉토리가 없는 상황에서 로드 시도
        with patch("src.analysis.analyze13_short_pipes.get_config") as mock_config:
            mock_config.return_value.RAW_DATA_DIR = Path("/mock/data")
            with patch("pathlib.Path.glob", return_value=[]):  # 빈 리스트 반환
                result = load_pipe_shapefile("PIPE_LM", verbose=False)
        
        # Then: None 반환
        assert result is None

    def test_load_pipe_shapefile_no_ftr_idn(self):
        """FTR_IDN 컬럼이 없는 경우 테스트"""
        # Given: FTR_IDN이 없는 GeoDataFrame
        mock_gdf = gpd.GeoDataFrame({
            "OTHER_COLUMN": ["A", "B"],
            "geometry": [
                LineString([(0, 0), (0, 1)]),
                LineString([(0, 0), (0, 2)])
            ]
        }, crs="EPSG:5179")
        
        # When: FTR_IDN이 없는 shapefile 로드
        with patch("src.analysis.analyze13_short_pipes.gpd.read_file", return_value=mock_gdf):
            with patch("src.analysis.analyze13_short_pipes.get_config") as mock_config:
                mock_config.return_value.RAW_DATA_DIR = Path("/mock/data")
                with patch("pathlib.Path.glob", return_value=[Path("/mock/data/export_shp_0520")]):
                    with patch("pathlib.Path.exists", return_value=True):
                        result = load_pipe_shapefile("PIPE_LM", verbose=False)
        
        # Then: None 반환
        assert result is None

    def test_constants_values(self):
        """상수 값 테스트"""
        # Then: 상수들이 예상 값과 일치
        assert LENGTH_THRESHOLD == 1.0
        assert BIN_SIZE == 0.1
        assert EXTREME_SHORT_THRESHOLD == 0.05

    def test_binning_edge_cases(self):
        """구간 설정 경계값 테스트"""
        # Given: 경계값에 있는 파이프들
        edge_pipes_data = {
            "FTR_IDN": ["E001", "E002", "E003", "E004"],
            "geometry": [
                LineString([(0, 0), (0, 0.0)]),     # 정확히 0
                LineString([(0, 0), (0, 0.1)]),     # 정확히 0.1
                LineString([(0, 0), (0, 0.9)]),     # 정확히 0.9
                LineString([(0, 0), (0, 1.0)]),     # 정확히 1.0 (제외되어야 함)
            ]
        }
        edge_gdf = gpd.GeoDataFrame(edge_pipes_data, crs="EPSG:5179")
        edge_gdf["pipe_length"] = edge_gdf.geometry.length
        
        # When: 분석 실행
        short_pipes, stats = analyze_short_pipes(edge_gdf, "EDGE_PIPE")
        
        # Then: 1.0m는 제외, 나머지는 포함
        assert stats.short_count == 3  # 0, 0.1, 0.9만 포함
        assert len(short_pipes) == 3

    def test_statistics_accuracy(self, sample_pipe_gdf):
        """통계 계산 정확도 테스트"""
        # When: 분석 실행
        short_pipes, stats = analyze_short_pipes(sample_pipe_gdf, "ACCURACY_TEST")
        
        # Then: 수동 계산과 비교
        short_lengths = sample_pipe_gdf[sample_pipe_gdf["pipe_length"] < LENGTH_THRESHOLD]["pipe_length"]
        
        assert abs(stats.mean_length - short_lengths.mean()) < 1e-10
        assert abs(stats.median_length - short_lengths.median()) < 1e-10
        assert abs(stats.min_length - short_lengths.min()) < 1e-10
        assert abs(stats.max_length - short_lengths.max()) < 1e-10
        assert abs(stats.std_length - short_lengths.std()) < 1e-10