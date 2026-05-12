"""
gis_analyzer.py 모듈 테스트
GIS 데이터 분석 및 통계 처리 함수들의 단위 테스트
"""

from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, Polygon

from src.gis_analyzer import (
    FtrStatistics,
    GeometryInfo,
    analyze_ftr_groups,
    calculate_summary_statistics,
    extract_ftr_attributes,
    format_attributes,
    get_geometry_info,
    group_by_ftr_cde,
    load_shapefile,
)


class TestDataClasses:
    """데이터 클래스 테스트"""

    def test_ftr_statistics_creation(self):
        """FtrStatistics 클래스 생성 테스트"""
        stats = FtrStatistics(
            count=10,
            total_length=100.5,
            total_area=0.0,
            geom_types={"LineString", "Point"},
            attrs=["FTR_CDE=SA001", "재질=PVC"],
        )
        assert stats.count == 10
        assert stats.total_length == 100.5
        assert stats.total_area == 0.0
        assert stats.geom_types == {"LineString", "Point"}
        assert stats.attrs == ["FTR_CDE=SA001", "재질=PVC"]

    def test_geometry_info_creation(self):
        """GeometryInfo 클래스 생성 테스트"""
        info = GeometryInfo(
            geom_type="LineString",
            info_string="LineString(길이: 50.25)",
            length=50.25,
            area=None,
        )
        assert info.geom_type == "LineString"
        assert info.info_string == "LineString(길이: 50.25)"
        assert info.length == 50.25
        assert info.area is None


class TestLoadShapefile:
    """load_shapefile 함수 테스트"""

    @patch("geopandas.read_file")
    def test_load_shapefile_with_crs(self, mock_read_file):
        """CRS가 있는 shapefile 로드 테스트"""
        # Given: CRS가 있는 GeoDataFrame
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.crs = "EPSG:4326"
        mock_read_file.return_value = mock_gdf

        # When: shapefile 로드
        result = load_shapefile(Path("test.shp"))

        # Then: CRS 변경 없이 반환
        assert result == mock_gdf
        mock_read_file.assert_called_once_with(Path("test.shp"), encoding="euc-kr")

    @patch("geopandas.read_file")
    def test_load_shapefile_without_crs(self, mock_read_file):
        """CRS가 없는 shapefile 로드 테스트"""
        # Given: CRS가 없는 GeoDataFrame
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.crs = None
        mock_read_file.return_value = mock_gdf

        # When: shapefile 로드
        _ = load_shapefile(Path("test.shp"), encoding="utf-8")

        # Then: EPSG:5179로 CRS 설정
        mock_gdf.set_crs.assert_called_once_with("EPSG:5179", inplace=True)
        mock_read_file.assert_called_once_with(Path("test.shp"), encoding="utf-8")


class TestGetGeometryInfo:
    """get_geometry_info 함수 테스트"""

    def test_get_geometry_info_none(self):
        """None geometry 처리 테스트"""
        info = get_geometry_info(None)
        assert info.geom_type == "No geometry"
        assert info.info_string == "No geometry"
        assert info.length is None
        assert info.area is None

    def test_get_geometry_info_point(self):
        """Point geometry 처리 테스트"""
        point = Point(10.5, 20.3)
        info = get_geometry_info(point)
        assert info.geom_type == "Point"
        assert info.info_string == "Point(10.50, 20.30)"
        assert info.length is None
        assert info.area is None

    def test_get_geometry_info_linestring(self):
        """LineString geometry 처리 테스트"""
        line = LineString([(0, 0), (10, 0)])
        info = get_geometry_info(line)
        assert info.geom_type == "LineString"
        assert "길이: 10.00" in info.info_string
        assert info.length == 10.0
        assert info.area is None

    def test_get_geometry_info_polygon(self):
        """Polygon geometry 처리 테스트"""
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        info = get_geometry_info(polygon)
        assert info.geom_type == "Polygon"
        assert "면적: 100.00" in info.info_string
        assert info.length is None
        assert info.area == 100.0


class TestExtractFtrAttributes:
    """extract_ftr_attributes 함수 테스트"""

    def test_extract_all_attributes(self):
        """모든 속성이 있는 경우 테스트"""
        row = pd.Series(
            {
                "FTR_CDE": "SA001",
                "FTC_CDE": "FTC001",
                "SAA_CDE": "SAA001",
                "MOP_CDE": "PVC",
                "STD_DIP": 300,
            }
        )
        columns = pd.Index(["FTR_CDE", "FTC_CDE", "SAA_CDE", "MOP_CDE", "STD_DIP"])

        attrs = extract_ftr_attributes(row, columns)
        assert "FTR_CDE=SA001" in attrs
        assert "FTC_CDE=FTC001" in attrs
        assert "SAA_CDE=SAA001" in attrs
        assert "재질=PVC" in attrs
        assert "관경=300" in attrs

    def test_extract_partial_attributes(self):
        """일부 속성만 있는 경우 테스트"""
        row = pd.Series(
            {
                "FTR_CDE": "SA001",
                "MOP_CDE": "PE",
                "OTHER_FIELD": "value",
            }
        )
        columns = pd.Index(["FTR_CDE", "MOP_CDE", "OTHER_FIELD"])

        attrs = extract_ftr_attributes(row, columns)
        assert "FTR_CDE=SA001" in attrs
        assert "재질=PE" in attrs
        assert len(attrs) == 2

    def test_extract_attributes_with_null(self):
        """null 값이 포함된 경우 테스트"""
        row = pd.Series(
            {
                "FTR_CDE": "SA001",
                "MOP_CDE": None,
                "STD_DIP": pd.NA,
            }
        )
        columns = pd.Index(["FTR_CDE", "MOP_CDE", "STD_DIP"])

        attrs = extract_ftr_attributes(row, columns)
        assert "FTR_CDE=SA001" in attrs
        assert len(attrs) == 1  # null 값은 제외


class TestFormatAttributes:
    """format_attributes 함수 테스트"""

    def test_format_attributes_basic(self):
        """기본 속성 포맷팅 테스트"""
        row = pd.Series(
            {
                "field1": "value1",
                "field2": "value2",
                "field3": "value3",
                "geometry": "POINT(0 0)",
            }
        )

        result = format_attributes(row, ["geometry"], max_attrs=3)
        assert "field1=value1" in result
        assert "field2=value2" in result
        assert "field3=value3" in result
        assert "geometry" not in result

    def test_format_attributes_max_limit(self):
        """최대 속성 개수 제한 테스트"""
        row = pd.Series({f"field{i}": f"value{i}" for i in range(10)})

        result = format_attributes(row, [], max_attrs=3)
        assert result.count("=") == 3
        assert "..." in result

    def test_format_attributes_with_null(self):
        """null 값 처리 테스트"""
        row = pd.Series(
            {
                "field1": "value1",
                "field2": None,
                "field3": pd.NA,
                "field4": "value4",
            }
        )

        result = format_attributes(row, [], max_attrs=5)
        assert "field1=value1" in result
        assert "field4=value4" in result
        assert "field2" not in result
        assert "field3" not in result


class TestAnalyzeFtrGroups:
    """analyze_ftr_groups 함수 테스트"""

    def test_analyze_ftr_groups_basic(self):
        """기본 FTR_IDN 그룹 분석 테스트"""
        # Given: FTR_IDN으로 그룹화할 수 있는 데이터
        data = {
            "FTR_IDN": ["12345", "12345", "67890"],
            "FTR_CDE": ["SA001", "SA001", "SA002"],
            "MOP_CDE": ["PVC", "PVC", "PE"],
            "geometry": [
                LineString([(0, 0), (10, 0)]),
                LineString([(10, 0), (20, 0)]),
                Point(5, 5),
            ],
        }
        gdf = gpd.GeoDataFrame(data)

        # When: FTR 그룹 분석
        stats = analyze_ftr_groups(gdf)

        # Then: 올바른 통계 생성
        assert len(stats) == 2
        assert "12345" in stats
        assert "67890" in stats

        # 12345 그룹 검증
        stats_12345 = stats["12345"]
        assert stats_12345.count == 2
        assert stats_12345.total_length == 20.0  # 10 + 10
        assert stats_12345.total_area == 0.0
        assert stats_12345.geom_types == {"LineString"}

        # 67890 그룹 검증
        stats_67890 = stats["67890"]
        assert stats_67890.count == 1
        assert stats_67890.total_length == 0.0
        assert stats_67890.total_area == 0.0
        assert stats_67890.geom_types == {"Point"}

    def test_analyze_ftr_groups_without_ftr_idn(self):
        """FTR_IDN 컬럼이 없는 경우 테스트"""
        data = {
            "FTR_CDE": ["SA001"],
            "geometry": [Point(0, 0)],
        }
        gdf = gpd.GeoDataFrame(data)

        stats = analyze_ftr_groups(gdf)
        assert stats == {}

    def test_analyze_ftr_groups_with_mixed_geometries(self):
        """다양한 geometry 타입 처리 테스트"""
        data = {
            "FTR_IDN": ["12345", "12345", "12345"],
            "FTR_CDE": ["SA001", "SA001", "SA001"],
            "geometry": [
                Point(0, 0),
                LineString([(0, 0), (10, 0)]),
                Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]),
            ],
        }
        gdf = gpd.GeoDataFrame(data)

        stats = analyze_ftr_groups(gdf)
        stats_12345 = stats["12345"]

        assert stats_12345.count == 3
        assert stats_12345.total_length == 10.0
        assert stats_12345.total_area == 100.0
        assert stats_12345.geom_types == {"Point", "LineString", "Polygon"}


class TestCalculateSummaryStatistics:
    """calculate_summary_statistics 함수 테스트"""

    def test_calculate_summary_statistics_basic(self):
        """기본 통계 계산 테스트"""
        ftr_stats = {
            "12345": FtrStatistics(
                count=5,
                total_length=50.0,
                total_area=0.0,
                geom_types={"LineString"},
                attrs=[],
            ),
            "67890": FtrStatistics(
                count=3,
                total_length=30.0,
                total_area=0.0,
                geom_types={"LineString"},
                attrs=[],
            ),
            "11111": FtrStatistics(
                count=2,
                total_length=0.0,
                total_area=100.0,
                geom_types={"Polygon"},
                attrs=[],
            ),
        }

        summary = calculate_summary_statistics(ftr_stats)

        assert summary["total_ftr_idn_count"] == 3
        assert summary["object_stats"]["total"] == 10  # 5 + 3 + 2
        assert summary["object_stats"]["mean"] == 10 / 3
        assert summary["object_stats"]["min"] == 2
        assert summary["object_stats"]["max"] == 5

        assert summary["length_stats"]["total"] == 80.0  # 50 + 30
        assert summary["length_stats"]["mean"] == 40.0  # 80 / 2
        assert summary["length_stats"]["min"] == 30.0
        assert summary["length_stats"]["max"] == 50.0

        assert summary["area_stats"]["total"] == 100.0
        assert summary["area_stats"]["mean"] == 100.0
        assert summary["area_stats"]["min"] == 100.0
        assert summary["area_stats"]["max"] == 100.0

    def test_calculate_summary_statistics_empty(self):
        """빈 통계 계산 테스트"""
        summary = calculate_summary_statistics({})
        assert summary == {}

    def test_calculate_summary_statistics_no_length_area(self):
        """길이/면적이 없는 경우 테스트"""
        ftr_stats = {
            "12345": FtrStatistics(
                count=5,
                total_length=0.0,
                total_area=0.0,
                geom_types={"Point"},
                attrs=[],
            ),
        }

        summary = calculate_summary_statistics(ftr_stats)
        assert "length_stats" not in summary
        assert "area_stats" not in summary


class TestGroupByFtrCde:
    """group_by_ftr_cde 함수 테스트"""

    def test_group_by_ftr_cde_basic(self):
        """FTR_CDE별 그룹화 테스트"""
        ftr_stats = {
            "12345": FtrStatistics(
                count=1,
                total_length=0,
                total_area=0,
                geom_types=set(),
                attrs=["FTR_CDE=SA001", "재질=PVC"],
            ),
            "67890": FtrStatistics(
                count=1,
                total_length=0,
                total_area=0,
                geom_types=set(),
                attrs=["FTR_CDE=SA001", "재질=PE"],
            ),
            "11111": FtrStatistics(
                count=1,
                total_length=0,
                total_area=0,
                geom_types=set(),
                attrs=["FTR_CDE=SA002", "재질=PVC"],
            ),
        }

        groups = group_by_ftr_cde(ftr_stats)

        assert len(groups) == 2
        assert "SA001" in groups
        assert "SA002" in groups
        assert groups["SA001"] == ["12345", "67890"]
        assert groups["SA002"] == ["11111"]

    def test_group_by_ftr_cde_no_ftr_cde(self):
        """FTR_CDE 속성이 없는 경우 테스트"""
        ftr_stats = {
            "12345": FtrStatistics(
                count=1,
                total_length=0,
                total_area=0,
                geom_types=set(),
                attrs=["재질=PVC", "관경=300"],
            ),
        }

        groups = group_by_ftr_cde(ftr_stats)
        assert groups == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
