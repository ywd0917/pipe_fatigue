"""
Shapefile 로더 테스트
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd

from src.common.shapefile_loader import (
    ShapefileConfig,
    ShapefileLoader,
    get_mdlz_shapefile_path,
    get_smlz_shapefile_path,
    load_all_mdlz_shapefiles,
    load_pipe_shapefile,
)


class TestShapefileConfig:
    """ShapefileConfig 클래스 테스트"""

    def test_pipe_types(self):
        """파이프 타입 설정 확인"""
        assert "PIPE_LM" in ShapefileConfig.PIPE_TYPES
        assert ShapefileConfig.PIPE_TYPES["PIPE_LM"]["filename"] == "V_WTL_PIPE_LM.shp"
        assert ShapefileConfig.PIPE_TYPES["PIPE_LM"]["ftr_cde"] == "SA001"

        assert "SPLY_LS" in ShapefileConfig.PIPE_TYPES
        assert ShapefileConfig.PIPE_TYPES["SPLY_LS"]["filename"] == "V_WTL_SPLY_LS.shp"
        assert ShapefileConfig.PIPE_TYPES["SPLY_LS"]["ftr_cde"] == "SA002"

    def test_zone_files(self):
        """구역 파일명 확인"""
        assert ShapefileConfig.ZONE_FILES["SMLZ"] == "WEA_SMLZ_AS.shp"
        assert ShapefileConfig.ZONE_FILES["MDLZ"] == "WEA_MDLZ_AS.shp"
        assert ShapefileConfig.ZONE_FILES["LRGZ"] == "WEA_LRGZ_AS.shp"

    def test_default_settings(self):
        """기본 설정 확인"""
        assert ShapefileConfig.DEFAULT_CRS == "EPSG:5179"
        assert ShapefileConfig.DEFAULT_ENCODING == "euc-kr"


class TestShapefileLoader:
    """ShapefileLoader 클래스 테스트"""

    def test_init(self):
        """초기화 테스트"""
        loader = ShapefileLoader("/test/path", verbose=False)
        assert loader.data_dir == Path("/test/path")
        assert loader.verbose is False

    @patch("pathlib.Path.iterdir")
    def test_find_export_directory(self, mock_iterdir):
        """export 디렉토리 찾기"""
        # Mock 디렉토리 구조
        mock_dir1 = Mock(spec=Path)
        mock_dir1.is_dir.return_value = True
        mock_dir1.name = "export_shp_20240101(0520)"

        mock_dir2 = Mock(spec=Path)
        mock_dir2.is_dir.return_value = True
        mock_dir2.name = "export_shp_20240102(0903)"

        mock_file = Mock(spec=Path)
        mock_file.is_dir.return_value = False
        mock_file.name = "not_a_directory.txt"

        mock_iterdir.return_value = [mock_dir1, mock_dir2, mock_file]

        loader = ShapefileLoader(Path("/test"), verbose=False)

        # 0520 지역 찾기
        result = loader.find_export_directory("0520")
        assert result == mock_dir1

        # 0903 지역 찾기
        result = loader.find_export_directory("0903")
        assert result == mock_dir2

        # 없는 지역
        result = loader.find_export_directory("9999")
        assert result is None

    @patch("geopandas.read_file")
    def test_load_shapefile_success(self, mock_read_file):
        """shapefile 로딩 성공"""
        # Mock GeoDataFrame
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_gdf.__len__.return_value = 100
        mock_gdf.crs = None
        mock_read_file.return_value = mock_gdf

        # Mock 파일 경로
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.name = "test.shp"

        loader = ShapefileLoader(Path("/test"), verbose=True)

        # 추가 필드와 함께 로드
        result = loader.load_shapefile(
            mock_path,
            crs="EPSG:5179",
            additional_fields={"FIELD1": "value1", "FIELD2": 123},
        )

        assert result is mock_gdf
        mock_read_file.assert_called_with(mock_path, encoding="euc-kr")
        mock_gdf.set_crs.assert_called_with("EPSG:5179", inplace=True)
        # 필드 설정 확인
        mock_gdf.__setitem__.assert_any_call("FIELD1", "value1")
        mock_gdf.__setitem__.assert_any_call("FIELD2", 123)

    @patch("geopandas.read_file")
    def test_load_shapefile_file_not_exists(self, mock_read_file):
        """존재하지 않는 파일"""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False

        loader = ShapefileLoader(Path("/test"), verbose=True)
        result = loader.load_shapefile(mock_path)

        assert result is None
        mock_read_file.assert_not_called()

    @patch("geopandas.read_file")
    def test_load_shapefile_exception(self, mock_read_file):
        """shapefile 로딩 중 예외"""
        mock_read_file.side_effect = Exception("Read error")

        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True

        loader = ShapefileLoader(Path("/test"), verbose=True)
        result = loader.load_shapefile(mock_path)

        assert result is None

    def test_load_pipe_shapefile_invalid_type(self):
        """잘못된 파이프 타입"""
        loader = ShapefileLoader(Path("/test"), verbose=True)
        result = loader.load_pipe_shapefile("0520", "INVALID_TYPE")

        assert result is None

    @patch.object(ShapefileLoader, "find_export_directory")
    def test_load_pipe_shapefile_no_export_dir(self, mock_find_export):
        """export 디렉토리 없음"""
        mock_find_export.return_value = None

        loader = ShapefileLoader(Path("/test"), verbose=True)
        result = loader.load_pipe_shapefile("0520", "PIPE_LM")

        assert result is None

    @patch.object(ShapefileLoader, "load_shapefile")
    @patch.object(ShapefileLoader, "find_export_directory")
    def test_load_pipe_shapefile_success(self, mock_find_export, mock_load_shapefile):
        """파이프 shapefile 로딩 성공"""
        # Mock export 디렉토리
        mock_export_dir = MagicMock(spec=Path)
        mock_shp_path = MagicMock(spec=Path)
        mock_export_dir.__truediv__.return_value = mock_shp_path
        mock_find_export.return_value = mock_export_dir

        # Mock GeoDataFrame
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_load_shapefile.return_value = mock_gdf

        loader = ShapefileLoader(Path("/test"), verbose=True)
        result = loader.load_pipe_shapefile("0520", "PIPE_LM")

        assert result is mock_gdf

        # load_shapefile 호출 확인
        mock_export_dir.__truediv__.assert_called_with("V_WTL_PIPE_LM.shp")
        mock_load_shapefile.assert_called_with(
            mock_shp_path,
            crs="EPSG:5179",
            additional_fields={"FTR_CDE": "SA001", "PIPE_TYPE": "PIPE_LM"},
        )

    def test_get_zone_shapefile_path_invalid_type(self):
        """잘못된 구역 타입"""
        loader = ShapefileLoader(Path("/test"), verbose=True)
        result = loader.get_zone_shapefile_path("0520", "INVALID_ZONE")

        assert result is None

    @patch.object(ShapefileLoader, "find_export_directory")
    def test_get_zone_shapefile_path_success(self, mock_find_export):
        """구역 shapefile 경로 찾기 성공"""
        # Mock export 디렉토리와 파일
        mock_export_dir = MagicMock(spec=Path)
        mock_zone_path = MagicMock(spec=Path)
        mock_zone_path.exists.return_value = True
        mock_export_dir.__truediv__.return_value = mock_zone_path
        mock_find_export.return_value = mock_export_dir

        loader = ShapefileLoader(Path("/test"), verbose=False)
        result = loader.get_zone_shapefile_path("0520", "MDLZ")

        assert result is mock_zone_path

    @patch("pathlib.Path.iterdir")
    @patch.object(ShapefileLoader, "load_shapefile")
    def test_load_all_zone_shapefiles(self, mock_load_shapefile, mock_iterdir):
        """모든 구역 shapefile 로드 및 병합"""
        # Mock 디렉토리 구조
        mock_export1 = MagicMock(spec=Path)
        mock_export1.is_dir.return_value = True
        mock_export1.name = "export_shp_20240101(0520)"

        mock_export2 = MagicMock(spec=Path)
        mock_export2.is_dir.return_value = True
        mock_export2.name = "export_shp_20240102(0903)"

        # Mock zone 파일
        mock_zone_path1 = MagicMock(spec=Path)
        mock_zone_path1.exists.return_value = True
        mock_zone_path2 = MagicMock(spec=Path)
        mock_zone_path2.exists.return_value = True

        mock_export1.__truediv__.return_value = mock_zone_path1
        mock_export2.__truediv__.return_value = mock_zone_path2

        mock_iterdir.return_value = [mock_export1, mock_export2]

        # Mock GeoDataFrames
        mock_gdf1 = MagicMock(spec=gpd.GeoDataFrame)
        mock_gdf1.crs = "EPSG:5179"
        mock_gdf2 = MagicMock(spec=gpd.GeoDataFrame)
        mock_gdf2.crs = "EPSG:5179"

        mock_load_shapefile.side_effect = [mock_gdf1, mock_gdf2]

        # pd.concat mock
        with patch("pandas.concat") as mock_concat:
            mock_combined = MagicMock(spec=gpd.GeoDataFrame)
            mock_combined.__len__.return_value = 200
            mock_combined.columns = ["REGION_CODE"]

            # value_counts mock
            value_counts_mock = Mock()
            value_counts_mock.items.return_value = [("0520", 100), ("0903", 100)]
            mock_combined.__getitem__.return_value.value_counts.return_value = (
                value_counts_mock
            )

            mock_concat.return_value = mock_combined

            with patch("geopandas.GeoDataFrame", return_value=mock_combined):
                loader = ShapefileLoader(Path("/test"), verbose=True)
                result = loader.load_all_zone_shapefiles("MDLZ")

        assert result == mock_combined
        assert mock_load_shapefile.call_count == 2


class TestCompatibilityFunctions:
    """호환성 래퍼 함수 테스트"""

    @patch("src.common.shapefile_loader.ShapefileLoader")
    def test_load_pipe_shapefile_wrapper(self, mock_loader_class):
        """load_pipe_shapefile 래퍼"""
        mock_loader = Mock()
        mock_gdf = Mock()
        mock_loader.load_pipe_shapefile.return_value = mock_gdf
        mock_loader_class.return_value = mock_loader

        result = load_pipe_shapefile(Path("/test"), "0520", "PIPE_LM", verbose=True)

        assert result is mock_gdf
        mock_loader_class.assert_called_with(Path("/test"), True)
        mock_loader.load_pipe_shapefile.assert_called_with("0520", "PIPE_LM")

    @patch("src.common.shapefile_loader.ShapefileLoader")
    def test_get_smlz_shapefile_path_wrapper(self, mock_loader_class):
        """get_smlz_shapefile_path 래퍼"""
        mock_loader = Mock()
        mock_path = Mock()
        mock_loader.get_zone_shapefile_path.return_value = mock_path
        mock_loader_class.return_value = mock_loader

        result = get_smlz_shapefile_path(Path("/test"), "0520")

        assert result is mock_path
        mock_loader_class.assert_called_with(Path("/test"), verbose=False)
        mock_loader.get_zone_shapefile_path.assert_called_with("0520", "SMLZ")

    @patch("src.common.shapefile_loader.ShapefileLoader")
    def test_get_mdlz_shapefile_path_wrapper(self, mock_loader_class):
        """get_mdlz_shapefile_path 래퍼"""
        mock_loader = Mock()
        mock_path = Mock()
        mock_loader.get_zone_shapefile_path.return_value = mock_path
        mock_loader_class.return_value = mock_loader

        result = get_mdlz_shapefile_path(Path("/test"), "0520")

        assert result is mock_path
        mock_loader.get_zone_shapefile_path.assert_called_with("0520", "MDLZ")

    @patch("src.common.shapefile_loader.ShapefileLoader")
    def test_load_all_mdlz_shapefiles_wrapper(self, mock_loader_class):
        """load_all_mdlz_shapefiles 래퍼"""
        mock_loader = Mock()
        mock_gdf = Mock()
        mock_loader.load_all_zone_shapefiles.return_value = mock_gdf
        mock_loader_class.return_value = mock_loader

        result = load_all_mdlz_shapefiles(Path("/test"), verbose=True)

        assert result is mock_gdf
        mock_loader.load_all_zone_shapefiles.assert_called_with("MDLZ")
