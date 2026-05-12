"""road_loader.py 테스트 코드."""

import sys
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString

# src 디렉토리를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.road_loader import (  # noqa: E402
    get_road_info,
    get_road_path,
    load_road_data,
    validate_road_data,
)


@pytest.fixture
def sample_road_gdf():
    """테스트용 도로 GeoDataFrame 생성."""
    data = {
        "BSI_INT_SN": [1, 2, 3],
        "RDS_MAN_NO": [1001, 1002, 1003],
        "SIG_CD": ["27110", "27110", "27230"],
        "geometry": [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 0)]),
            LineString([(0, 1), (2, 1)]),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


class TestGetRoadPath:
    """get_road_path 함수 테스트."""

    def test_get_road_path_from_raw(self):
        """raw 디렉토리에서 경로 가져오기."""
        base_dir = Path("/data/raw")
        expected = Path("/data/road/TL_SPRD_MANAGE.shp")
        assert get_road_path(base_dir) == expected

    def test_get_road_path_from_data(self):
        """data 디렉토리에서 경로 가져오기."""
        base_dir = Path("/data")
        expected = Path("/data/road/TL_SPRD_MANAGE.shp")
        assert get_road_path(base_dir) == expected


class TestValidateRoadData:
    """validate_road_data 함수 테스트."""

    def test_validate_road_data_normal(self, sample_road_gdf):
        """정상 데이터 검증."""
        result = validate_road_data(sample_road_gdf)
        assert len(result) == 3
        assert result.crs == "EPSG:5179"

    def test_validate_road_data_null_geometry(self, sample_road_gdf):
        """NULL geometry 제거 테스트."""
        # NULL geometry 추가
        sample_road_gdf.loc[3] = {
            "BSI_INT_SN": 4,
            "RDS_MAN_NO": 1004,
            "SIG_CD": "27230",
            "geometry": None,
        }
        result = validate_road_data(sample_road_gdf)
        assert len(result) == 3  # NULL geometry가 제거됨

    def test_validate_road_data_no_crs(self):
        """CRS가 없는 데이터 처리."""
        data = {"geometry": [LineString([(0, 0), (1, 1)])]}
        gdf = gpd.GeoDataFrame(data, crs=None)
        result = validate_road_data(gdf)
        assert result.crs == "EPSG:5179"


class TestLoadRoadData:
    """load_road_data 함수 테스트."""

    @patch("pathlib.Path.exists")
    @patch("geopandas.read_file")
    def test_load_road_data_success(self, mock_read_file, mock_exists, sample_road_gdf):
        """정상 로드 테스트."""
        mock_exists.return_value = True
        mock_read_file.return_value = sample_road_gdf

        result = load_road_data(Path("/data/raw"))
        assert result is not None
        assert len(result) == 3

    @patch("pathlib.Path.exists")
    def test_load_road_data_file_not_found(self, mock_exists):
        """파일이 없을 때 테스트."""
        mock_exists.return_value = False
        result = load_road_data(Path("/data/raw"))
        assert result is None

    @patch("pathlib.Path.exists")
    @patch("geopandas.read_file")
    def test_load_road_data_encoding_fallback(
        self, mock_read_file, mock_exists, sample_road_gdf
    ):
        """인코딩 폴백 테스트."""
        mock_exists.return_value = True
        # 첫 번째 호출은 UnicodeDecodeError, 두 번째는 성공
        mock_read_file.side_effect = [
            UnicodeDecodeError("euc-kr", b"", 0, 1, ""),
            sample_road_gdf,
        ]

        result = load_road_data(Path("/data/raw"))
        assert result is not None
        assert mock_read_file.call_count == 2

    @patch("pathlib.Path.exists")
    @patch("geopandas.read_file")
    def test_load_road_data_encoding_fallback_fail(
        self, mock_read_file, mock_exists, capsys
    ):
        """인코딩 폴백도 실패하는 경우 테스트."""
        mock_exists.return_value = True
        # 첫 번째는 UnicodeDecodeError, 두 번째도 실패
        mock_read_file.side_effect = [
            UnicodeDecodeError("euc-kr", b"", 0, 1, ""),
            Exception("UTF-8 읽기도 실패"),
        ]

        result = load_road_data(Path("/data/raw"), verbose=True)
        captured = capsys.readouterr()

        assert result is None
        assert mock_read_file.call_count == 2
        assert "euc-kr 인코딩 실패, utf-8로 재시도" in captured.out
        assert "오류: 도로 데이터 로드 실패 - UTF-8 읽기도 실패" in captured.out

    @patch("pathlib.Path.exists")
    @patch("geopandas.read_file")
    def test_load_road_data_general_error(self, mock_read_file, mock_exists, capsys):
        """일반적인 읽기 오류 테스트."""
        mock_exists.return_value = True
        # 일반적인 예외 발생
        mock_read_file.side_effect = Exception("파일 손상")

        result = load_road_data(Path("/data/raw"), verbose=True)
        captured = capsys.readouterr()

        assert result is None
        assert "오류: 도로 데이터 로드 실패 - 파일 손상" in captured.out


class TestGetRoadInfo:
    """get_road_info 함수 테스트."""

    def test_get_road_info(self, sample_road_gdf):
        """도로 정보 반환 테스트."""
        info = get_road_info(sample_road_gdf)
        assert info["total_features"] == 3
        assert info["crs"] == "EPSG:5179"
        assert "BSI_INT_SN" in info["columns"]
        assert info["unique_bsi_int_sn"] == 3
        assert info["unique_rds_man_no"] == 3
        assert info["unique_sig_cd"] == 2
        assert info["sig_cd_values"] == ["27110", "27230"]

    def test_get_road_info_empty(self):
        """빈 GeoDataFrame 정보 테스트."""
        gdf = gpd.GeoDataFrame()
        info = get_road_info(gdf)
        assert info["total_features"] == 0
        assert info["bounds"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
