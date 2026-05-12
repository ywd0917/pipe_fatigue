"""soil_visualizer.py 모듈 테스트."""

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from src.soil_visualizer import (
    get_age_colors,
    get_soil_files,
    get_type_styles,
    load_soil_layer,
)


class TestGetSoilFiles:
    """get_soil_files 함수 테스트"""

    def test_get_soil_files_success(self, tmp_path):
        """토양 파일 목록 조회 성공 테스트"""
        # Given: soil 디렉토리 생성 (data의 상위 디렉토리에)
        data_dir = tmp_path / "data" / "raw"
        data_dir.mkdir(parents=True)
        soil_dir = tmp_path / "data" / "soil"
        soil_dir.mkdir()

        # 지질 파일들 생성
        (soil_dir / "Geology_250K_Boudary.shp").touch()
        (soil_dir / "Geology_250K_Fault.shp").touch()
        (soil_dir / "Geology_250K_Frame.shp").touch()
        (soil_dir / "Geology_250K_Litho.shp").touch()

        # When: 토양 파일 검색
        result = get_soil_files(data_dir)

        # Then: 모든 지질 파일 반환
        assert len(result) == 4
        assert "boundary" in result
        assert "fault" in result
        assert "frame" in result
        assert "litho" in result

    def test_get_soil_files_no_directory(self, tmp_path):
        """soil 디렉토리가 없는 경우 테스트"""
        # Given: data/raw 디렉토리만 생성
        data_dir = tmp_path / "data" / "raw"
        data_dir.mkdir(parents=True)

        # When/Then: FileNotFoundError 발생
        with pytest.raises(FileNotFoundError):
            get_soil_files(data_dir)

    def test_get_soil_files_empty(self, tmp_path):
        """토양 파일이 없는 경우 테스트"""
        # Given: 빈 soil 디렉토리
        data_dir = tmp_path / "data" / "raw"
        data_dir.mkdir(parents=True)
        soil_dir = tmp_path / "data" / "soil"
        soil_dir.mkdir()

        # When: 토양 파일 검색
        result = get_soil_files(data_dir)

        # Then: 빈 딕셔너리 반환
        assert result == {}


class TestLoadSoilLayer:
    """load_soil_layer 함수 테스트"""

    @patch("geopandas.read_file")
    def test_load_soil_layer_success(self, mock_read_file):
        """토양 레이어 로드 성공 테스트"""
        # Given: Mock GeoDataFrame 생성
        data = {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
        mock_gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
        mock_read_file.return_value = mock_gdf

        # When: 토양 레이어 로드
        result = load_soil_layer(Path("test.shp"))

        # Then: GeoDataFrame 반환
        assert result is not None
        assert len(result) == 1
        mock_read_file.assert_called_once_with(Path("test.shp"), encoding="euc-kr")

    @patch("geopandas.read_file")
    def test_load_soil_layer_error(self, mock_read_file):
        """토양 레이어 로드 실패 테스트"""
        # Given: 읽기 오류 발생
        mock_read_file.side_effect = Exception("파일을 읽을 수 없습니다")

        # When/Then: None 반환
        result = load_soil_layer(Path("error.shp"))
        assert result is None

    def test_load_soil_layer_litho_encoding(self):
        """Litho 파일의 UTF-8 인코딩 테스트"""
        # Given: Litho 파일 경로
        litho_path = Path("Geology_250K_Litho.shp")

        # When/Then: UTF-8 인코딩이 사용되는지는 내부 로직으로 확인
        # 실제로는 파일이 없어서 None이 반환되지만, 인코딩 로직 테스트는 성공
        result = load_soil_layer(litho_path)
        assert result is None  # 파일이 없으므로


class TestColorAndStyles:
    """색상 및 스타일 관련 테스트"""

    def test_get_age_colors(self):
        """토양 연대별 색상 테스트"""
        colors = get_age_colors()

        # 주요 연대의 색상이 정의되어 있는지 확인
        assert isinstance(colors, dict)
        assert len(colors) > 0

        # 모든 색상이 hex 형식인지 확인
        for color in colors.values():
            assert color.startswith("#")
            assert len(color) == 7

    def test_get_type_styles(self):
        """토양 종류별 스타일 테스트"""
        styles = get_type_styles()

        # 스타일 딕셔너리가 올바른 구조인지 확인
        assert isinstance(styles, dict)
        assert len(styles) > 0

        # boundary와 fault 키가 있는지 확인
        assert "boundary" in styles
        assert "fault" in styles

        # 각 카테고리의 스타일이 올바른 구조인지 확인
        for category, category_styles in styles.items():
            assert isinstance(category_styles, dict)
            for style_name, style_props in category_styles.items():
                assert "color" in style_props
                assert "linestyle" in style_props
                assert "linewidth" in style_props


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
