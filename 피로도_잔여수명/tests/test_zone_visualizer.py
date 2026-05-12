"""zone_visualizer.py 모듈 테스트."""

from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import pytest

from src.zone_visualizer import (
    get_all_zone_files,
    load_zone_data,
)


class TestGetAllZoneFiles:
    """get_all_zone_files 함수 테스트"""

    def test_get_all_zone_files_success(self, tmp_path):
        """Zone 파일 경로 찾기 성공 테스트"""
        # Given: 테스트 디렉토리 구조 생성
        export_dir = tmp_path / "export_shp_20250704(0520)"
        export_dir.mkdir()

        # Zone shapefile 생성
        zone_types = ["LRGZ", "MDLZ", "SCDZ", "SMLZ"]
        for zone_type in zone_types:
            (export_dir / f"WEA_{zone_type}_AS.shp").touch()
            (export_dir / f"WEA_{zone_type}_AS.dbf").touch()
            (export_dir / f"WEA_{zone_type}_AS.shx").touch()

        # When: Zone 파일 찾기
        result = get_all_zone_files(tmp_path)

        # Then: 디렉토리별로 Zone 파일 경로 반환
        assert len(result) == 1  # 하나의 export 디렉토리
        assert "0520" in result
        zone_files = result["0520"]
        assert len(zone_files) == 4
        for zone_type in zone_types:
            assert zone_type.lower() in zone_files

    def test_get_all_zone_files_partial(self, tmp_path):
        """일부 Zone 파일만 있는 경우 테스트"""
        # Given: 일부 Zone 파일만 생성
        export_dir = tmp_path / "export_shp_20250704(0520)"
        export_dir.mkdir()

        (export_dir / "WEA_LRGZ_AS.shp").touch()
        (export_dir / "WEA_MDLZ_AS.shp").touch()

        # When: Zone 파일 찾기
        result = get_all_zone_files(tmp_path)

        # Then: 존재하는 파일만 반환
        assert len(result) == 1  # 하나의 export 디렉토리
        assert "0520" in result
        zone_files = result["0520"]
        assert len(zone_files) == 2
        assert "lrgz" in zone_files
        assert "mdlz" in zone_files
        assert "scdz" not in zone_files
        assert "smlz" not in zone_files


class TestLoadZoneData:
    """load_zone_data 함수 테스트"""

    @patch("geopandas.read_file")
    def test_load_zone_data_success(self, mock_read_file):
        """Zone 데이터 로드 성공 테스트"""
        # Given: Mock GeoDataFrame 생성
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.crs = "EPSG:5179"
        mock_gdf.__len__ = Mock(return_value=10)
        mock_read_file.return_value = mock_gdf

        zone_files = {
            "lrgz": Path("/path/to/LRGZ.shp"),
            "mdlz": Path("/path/to/MDLZ.shp"),
        }

        # When: Zone 데이터 로드
        result = load_zone_data(zone_files)

        # Then: 모든 Zone 데이터 반환
        assert len(result) == 2
        assert "lrgz" in result
        assert "mdlz" in result
        assert mock_read_file.call_count == 2

    @patch("geopandas.read_file")
    def test_load_zone_data_with_error(self, mock_read_file):
        """일부 Zone 데이터 로드 실패 테스트"""
        # Given: 첫 번째는 성공, 두 번째는 실패
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.crs = "EPSG:5179"
        mock_gdf.__len__ = Mock(return_value=5)
        mock_read_file.side_effect = [mock_gdf, Exception("Load error")]

        zone_files = {
            "lrgz": Path("/path/to/LRGZ.shp"),
            "mdlz": Path("/path/to/MDLZ.shp"),
        }

        # When: Zone 데이터 로드
        result = load_zone_data(zone_files)

        # Then: 성공한 데이터만 반환
        assert len(result) == 1
        assert "lrgz" in result
        assert "mdlz" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
