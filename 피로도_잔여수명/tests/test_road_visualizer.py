"""road_visualizer.py 테스트 코드."""

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from src.road_visualizer import (
    analyze_road_attributes,
    get_road_color,
    get_road_width,
)


@pytest.fixture
def sample_road_gdf():
    """테스트용 도로 GeoDataFrame 생성."""
    # 샘플 도로 데이터 생성
    data = {
        "BSI_INT_SN": [1, 2, 3, 4],
        "EVE_BSI_MN": [100, 200, 300, 400],
        "EVE_BSI_SL": [10, 20, 30, 40],
        "ODD_BSI_MN": [101, 201, 301, 401],
        "ODD_BSI_SL": [11, 21, 31, 41],
        "OPERT_DE": ["20230101", "20230102", None, "20230104"],
        "RDS_MAN_NO": [1001, 1002, 1003, 1004],
        "SIG_CD": ["27110", "27110", "27230", "27230"],
        "ROA_CLS_SE": ["1", "2", "3", "4"],
        "ROAD_BT": [35.0, 20.0, 10.0, 5.0],
        "geometry": [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 0)]),
            LineString([(0, 1), (2, 1)]),
            LineString([(2, 0), (3, 1)]),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


class TestAnalyzeRoadAttributes:
    """analyze_road_attributes 함수 테스트."""

    def test_analyze_road_attributes(self, sample_road_gdf):
        """도로 속성 분석 테스트."""
        result = analyze_road_attributes(sample_road_gdf)

        assert result["total_segments"] == 4
        assert result["has_roa_cls"] is True
        assert result["has_road_bt"] is True
        assert "road_class_distribution" in result
        assert "road_width_distribution" in result


class TestGetRoadColor:
    """get_road_color 함수 테스트."""

    def test_get_road_color_valid_int(self):
        """유효한 정수 등급 테스트."""
        assert get_road_color(1) == "#FF0000"  # 빨간색
        assert get_road_color(2) == "#FF7F00"  # 주황색
        assert get_road_color(3) == "#0000FF"  # 파란색
        assert get_road_color(4) == "#00AA00"  # 녹색

    def test_get_road_color_valid_str(self):
        """유효한 문자열 등급 테스트."""
        assert get_road_color("1") == "#FF0000"
        assert get_road_color("2") == "#FF7F00"
        assert get_road_color("3") == "#0000FF"
        assert get_road_color("4") == "#00AA00"

    def test_get_road_color_invalid(self):
        """유효하지 않은 입력 테스트."""
        assert get_road_color(5) == "#808080"  # 기본값
        assert get_road_color("invalid") == "#808080"
        assert get_road_color(None) == "#808080"


class TestGetRoadWidth:
    """get_road_width 함수 테스트."""

    def test_get_road_width_categories(self):
        """도로 폭 카테고리별 테스트."""
        assert get_road_width(35.0) == 0.125  # 30m 이상
        assert get_road_width(20.0) == 0.09  # 15-30m
        assert get_road_width(10.0) == 0.06  # 8-15m
        assert get_road_width(5.0) == 0.04  # 8m 미만

    def test_get_road_width_boundaries(self):
        """경계값 테스트."""
        assert get_road_width(30.0) == 0.125
        assert get_road_width(15.0) == 0.09
        assert get_road_width(8.0) == 0.06
        assert get_road_width(7.9) == 0.04
