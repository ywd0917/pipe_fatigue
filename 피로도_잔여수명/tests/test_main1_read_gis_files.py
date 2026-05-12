"""
main1_read_gis_files.py 테스트
"""

from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from src.gis_analyzer import FtrStatistics, GeometryInfo
from src.main1_read_gis_files import (
    find_shapefiles,
    print_all_records,
    print_ftr_group,
    print_records_without_ftr_idn,
    read_shapefile_info,
)


class TestFindShapefiles:
    """find_shapefiles 함수 테스트"""

    def test_find_shapefiles_with_files(self, tmp_path):
        """shapefile이 있는 경우 테스트"""
        # Given: 테스트용 디렉토리 구조 생성
        subdir1 = tmp_path / "subdir1"
        subdir2 = tmp_path / "subdir2"
        subdir1.mkdir()
        subdir2.mkdir()

        # shapefile 생성
        (subdir1 / "test1.shp").touch()
        (subdir1 / "test1.shx").touch()
        (subdir1 / "test1.dbf").touch()
        (subdir2 / "test2.shp").touch()
        (tmp_path / "test3.shp").touch()

        # 다른 파일도 생성
        (subdir1 / "other.txt").touch()

        # When: shapefile 검색
        result = find_shapefiles(tmp_path)

        # Then: 3개의 shapefile을 찾아야 함
        assert len(result) == 3
        shp_names = [f.name for f in result]
        assert "test1.shp" in shp_names
        assert "test2.shp" in shp_names
        assert "test3.shp" in shp_names

    def test_find_shapefiles_empty_directory(self, tmp_path):
        """shapefile이 없는 경우 테스트"""
        # Given: 빈 디렉토리
        # When: shapefile 검색
        result = find_shapefiles(tmp_path)

        # Then: 빈 리스트 반환
        assert result == []


class TestReadShapefileInfo:
    """read_shapefile_info 함수 테스트"""

    @patch("src.main1_read_gis_files.load_shapefile")
    def test_read_shapefile_info_success(self, mock_load_shapefile):
        """정상적인 shapefile 읽기 테스트"""
        # Given: Mock GeoDataFrame 생성
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.__len__ = Mock(return_value=10)
        mock_gdf.empty = False
        mock_gdf.crs = "EPSG:5186"

        # geometry 설정
        mock_geometry = Mock()
        mock_geometry.notna.return_value.any.return_value = True
        mock_geometry.geom_type = Mock()
        mock_geometry.geom_type.unique.return_value = ["LineString"]
        mock_gdf.geometry = mock_geometry

        mock_load_shapefile.return_value = mock_gdf

        # When: shapefile 정보 읽기
        test_path = Path("/test/file.shp")
        filename, count, geom_type, crs = read_shapefile_info(test_path)

        # Then: 올바른 정보 반환
        assert filename == "file.shp"
        assert count == 10
        assert geom_type == "LineString"
        assert crs == "EPSG:5186"

    @patch("src.main1_read_gis_files.load_shapefile")
    def test_read_shapefile_info_empty_gdf(self, mock_load_shapefile):
        """빈 GeoDataFrame 처리 테스트"""
        # Given: 빈 GeoDataFrame
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.__len__ = Mock(return_value=0)
        mock_gdf.empty = True
        mock_gdf.crs = None

        mock_load_shapefile.return_value = mock_gdf

        # When: shapefile 정보 읽기
        test_path = Path("/test/empty.shp")
        filename, count, geom_type, crs = read_shapefile_info(test_path)

        # Then: 적절한 메시지 반환
        assert filename == "empty.shp"
        assert count == 0
        assert geom_type == "No geometry"
        assert crs == "No CRS (Set to EPSG:5179)"

    @patch("src.main1_read_gis_files.load_shapefile")
    def test_read_shapefile_info_error(self, mock_load_shapefile):
        """파일 읽기 오류 처리 테스트"""
        # Given: 읽기 오류 발생
        mock_load_shapefile.side_effect = Exception("File not found")

        # When: shapefile 정보 읽기
        test_path = Path("/test/error.shp")
        filename, count, geom_type, crs = read_shapefile_info(test_path)

        # Then: 오류 정보 반환
        assert filename == "error.shp"
        assert count == 0
        assert geom_type == "Error"
        assert "File not found" in crs

    @patch("src.main1_read_gis_files.load_shapefile")
    def test_read_shapefile_info_with_many_attributes(self, mock_load_shapefile):
        """많은 속성을 가진 shapefile 테스트"""
        # Given: 많은 속성을 가진 GeoDataFrame
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.__len__ = Mock(return_value=1)
        mock_gdf.empty = False
        mock_gdf.crs = "EPSG:4326"

        # geometry 설정
        mock_geometry = Mock()
        mock_geometry.notna.return_value.any.return_value = True
        mock_geometry.geom_type = Mock()
        mock_geometry.geom_type.unique.return_value = ["Point"]
        mock_gdf.geometry = mock_geometry

        mock_load_shapefile.return_value = mock_gdf

        # When: shapefile 정보 읽기
        test_path = Path("/test/many_attrs.shp")
        filename, count, geom_type, crs = read_shapefile_info(test_path)

        # Then: 올바른 정보 반환
        assert filename == "many_attrs.shp"
        assert count == 1


class TestPrintHelpers:
    """출력 헬퍼 함수들 테스트"""

    @patch("src.main1_read_gis_files.get_geometry_info")
    @patch("src.main1_read_gis_files.format_attributes")
    def test_print_records_without_ftr_idn(
        self, mock_format_attrs, mock_get_geom_info, capsys
    ):
        """FTR_IDN이 없는 경우 출력 테스트"""
        # Given: Mock 설정
        mock_get_geom_info.return_value = GeometryInfo("Point", "Point(10.00, 20.00)")
        mock_format_attrs.return_value = "field1=value1"

        data = {"geometry": [Point(10, 20)], "field1": ["value1"]}
        gdf = gpd.GeoDataFrame(data)

        # When: 출력
        print_records_without_ftr_idn(gdf)

        # Then: 검증
        captured = capsys.readouterr()
        assert "FTR_IDN 컬럼이 없습니다" in captured.out
        assert "[0] Point(10.00, 20.00)" in captured.out
        assert "field1=value1" in captured.out

    def test_print_ftr_group(self, capsys):
        """FTR_IDN 그룹 출력 테스트"""
        # Given: 테스트 데이터
        data = {"geometry": [LineString([(0, 0), (10, 0)])], "FTR_IDN": ["12345"]}
        group = gpd.GeoDataFrame(data)

        # When: 출력
        print_ftr_group("12345", group, " | FTR_CDE=SA001")

        # Then: 검증
        captured = capsys.readouterr()
        assert "FTR_IDN: 12345 (1개 객체) | FTR_CDE=SA001" in captured.out


class TestPrintAllRecords:
    """print_all_records 함수 테스트"""

    @patch("src.main1_read_gis_files.load_shapefile")
    @patch("src.main1_read_gis_files.analyze_ftr_groups")
    @patch("src.main1_read_gis_files.calculate_summary_statistics")
    @patch("src.main1_read_gis_files.group_by_ftr_cde")
    @patch("src.main1_read_gis_files.print_statistics_summary")
    def test_print_all_records_with_grouping(
        self,
        mock_print_stats,
        mock_group_by_cde,
        mock_calc_stats,
        mock_analyze_ftr,
        mock_load_shapefile,
        capsys,
    ):
        """FTR_IDN으로 그룹화된 shapefile 레코드 출력 테스트"""
        # Given: Mock GeoDataFrame with multiple records
        data = {
            "geometry": [
                LineString([(0, 0), (1, 1)]),
                Point(10, 20),
                LineString([(0, 0), (5, 5), (10, 10)]),
            ],
            "FTR_CDE": ["SA001", "SA002", "SA001"],
            "FTR_IDN": ["12345", "67890", "12345"],
            "MOP_CDE": ["PVC", "PE", "PVC"],
        }
        gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
        mock_load_shapefile.return_value = gdf

        # Mock 분석 결과
        mock_analyze_ftr.return_value = {
            "12345": FtrStatistics(
                count=2,
                total_length=20.0,
                total_area=0.0,
                geom_types={"LineString"},
                attrs=["FTR_CDE=SA001", "재질=PVC"],
            ),
            "67890": FtrStatistics(
                count=1,
                total_length=0.0,
                total_area=0.0,
                geom_types={"Point"},
                attrs=["FTR_CDE=SA002", "재질=PE"],
            ),
        }
        mock_calc_stats.return_value = {"total_ftr_idn_count": 2}
        mock_group_by_cde.return_value = {"SA001": ["12345"], "SA002": ["67890"]}

        # When: print records
        test_path = Path("/test/file.shp")
        print_all_records(test_path)

        # Then: check output for grouping
        captured = capsys.readouterr()
        assert "FTR_IDN: 12345 (2개 객체)" in captured.out
        assert "FTR_IDN: 67890 (1개 객체)" in captured.out
        assert "FTR_CDE=SA001" in captured.out
        assert "재질=PVC" in captured.out

    @patch("src.main1_read_gis_files.load_shapefile")
    def test_print_all_records_empty_gdf(self, mock_load_shapefile, capsys):
        """빈 GeoDataFrame 처리 테스트"""
        # Given: empty GeoDataFrame with geometry column
        mock_gdf = gpd.GeoDataFrame({"geometry": []}, crs="EPSG:5179")
        mock_load_shapefile.return_value = mock_gdf

        # When: print records
        test_path = Path("/test/empty.shp")
        print_all_records(test_path)

        # Then: FTR_IDN 컬럼이 없다는 메시지 출력
        captured = capsys.readouterr()
        assert "FTR_IDN 컬럼이 없습니다" in captured.out

    @patch("src.main1_read_gis_files.load_shapefile")
    def test_print_all_records_error(self, mock_load_shapefile, capsys):
        """파일 읽기 오류 처리 테스트"""
        # Given: read error
        mock_load_shapefile.side_effect = Exception("File not found")

        # When: print records
        test_path = Path("/test/error.shp")
        print_all_records(test_path)

        # Then: error message printed
        captured = capsys.readouterr()
        assert "오류: File not found" in captured.out

    @patch("src.main1_read_gis_files.load_shapefile")
    @patch("src.main1_read_gis_files.print_records_without_ftr_idn")
    def test_print_all_records_without_ftr_idn(
        self, mock_print_without_ftr, mock_load_shapefile, capsys
    ):
        """FTR_IDN 컬럼이 없는 경우 테스트"""
        # Given: GeoDataFrame without FTR_IDN
        data = {
            "geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])],
            "FTR_CDE": ["SA001"],
            "FIELD1": ["test_value"],
        }
        mock_gdf = gpd.GeoDataFrame(data)
        mock_load_shapefile.return_value = mock_gdf

        # When: print records
        test_path = Path("/test/polygon.shp")
        print_all_records(test_path)

        # Then: print_records_without_ftr_idn 호출 확인
        mock_print_without_ftr.assert_called_once_with(mock_gdf)


class TestMain:
    """main 함수 테스트"""

    @patch("src.main1_read_gis_files.find_shapefiles")
    @patch("src.main1_read_gis_files.read_shapefile_info")
    @patch("src.main1_read_gis_files.print_all_records")
    @patch("src.main1_read_gis_files.RAW_DATA_DIR")
    def test_main_with_shapefiles(
        self,
        mock_data_dir,
        mock_print_all,
        mock_read_info,
        mock_find_shapefiles,
        capsys,
    ):
        """shapefile이 있는 경우 main 함수 테스트"""
        # Given: RAW_DATA_DIR 설정
        mock_data_dir_path = Path("/data/raw")
        mock_data_dir.__str__.return_value = str(mock_data_dir_path)
        mock_data_dir.__fspath__.return_value = str(mock_data_dir_path)

        # shapefile 목록
        mock_shapefiles = [
            mock_data_dir_path / "test1.shp",
            mock_data_dir_path / "subdir" / "test2.shp",
        ]
        mock_find_shapefiles.return_value = mock_shapefiles
        mock_read_info.side_effect = [
            ("test1.shp", 100, "Point", "EPSG:5179"),
            ("test2.shp", 50, "LineString", "EPSG:5179"),
        ]

        # When: main 함수 실행
        from src.main1_read_gis_files import main

        main()

        # Then: 올바른 순서로 호출 확인
        captured = capsys.readouterr()
        assert "GIS 파일 검색 시작:" in captured.out
        assert "총 2개의 shapefile 발견" in captured.out
        # 어느 파일이든 출력되었는지만 확인
        assert "100개 레코드" in captured.out
        assert "50개 레코드" in captured.out

        # 함수 호출 확인
        assert mock_print_all.call_count == 2

    @patch("src.main1_read_gis_files.find_shapefiles")
    def test_main_no_shapefiles(self, mock_find_shapefiles, capsys):
        """shapefile이 없는 경우 main 함수 테스트"""
        # Given: 빈 shapefile 목록
        mock_find_shapefiles.return_value = []

        # When: main 함수 실행
        from src.main1_read_gis_files import main

        main()

        # Then: 적절한 메시지 출력
        captured = capsys.readouterr()
        assert "shapefile을 찾을 수 없습니다." in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
