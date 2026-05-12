#!/usr/bin/env python3
"""
test_main13d_visualize_zone_fatigue.py

main13d_visualize_zone_fatigue.py 스크립트에 대한 테스트
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Polygon

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main13d_visualize_zone_fatigue import (
    create_visualization,
    load_pipe_data,
    load_zone_boundaries,
    parse_arguments,
)


class TestParseArguments:
    """명령줄 인자 파싱 테스트"""

    @patch("sys.argv", ["main13d_visualize_zone_fatigue.py"])
    def test_default_arguments(self):
        """기본 인자 테스트"""
        args = parse_arguments()
        assert args.scale == 1.0
        assert not args.debug
        assert "main13c_zone_fatigue_merge" in str(args.input_dir)
        assert "main13d_visualize_zone_fatigue" in str(args.output_dir)

    @patch("sys.argv", ["main13d_visualize_zone_fatigue.py", "--scale", "2.0", "--debug"])
    def test_custom_arguments(self):
        """사용자 정의 인자 테스트"""
        args = parse_arguments()
        assert args.scale == 2.0
        assert args.debug


class TestLoadZoneBoundaries:
    """구역 경계 로드 테스트"""

    @patch("main13d_visualize_zone_fatigue.get_config")
    @patch("geopandas.read_file")
    def test_load_zone_boundaries_success(self, mock_read_file, mock_get_config):
        """구역 경계 로드 성공 테스트"""
        # Mock 설정
        mock_config = MagicMock()
        mock_config.RAW_DATA_DIR = Path("/test/data/raw")
        mock_get_config.return_value = mock_config

        # Mock export 디렉토리
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [Path("/test/data/raw/export_shp_20250704(0520)")]

            # Mock shapefiles
            mdlz_gdf = gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
                crs="EPSG:5179",
            )
            
            smlz_gdf = gpd.GeoDataFrame(
                {
                    "SMZ_NUM": ["0470", "0480", "0490"],
                    "geometry": [
                        Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]),
                        Polygon([(3, 0), (6, 0), (6, 3), (3, 3)]),
                        Polygon([(6, 0), (9, 0), (9, 3), (6, 3)]),
                    ],
                },
                crs="EPSG:5179",
            )

            mock_read_file.side_effect = [mdlz_gdf, smlz_gdf]

            with patch("pathlib.Path.exists", return_value=True):
                mdlz_0520, smlz_subregions = load_zone_boundaries()

                assert len(mdlz_0520) == 1
                assert len(smlz_subregions) == 3
                assert set(smlz_subregions["SMZ_NUM"]) == {"0470", "0480", "0490"}

    @patch("main13d_visualize_zone_fatigue.get_config")
    def test_load_zone_boundaries_no_export_dir(self, mock_get_config):
        """Export 디렉토리가 없을 때 테스트"""
        mock_config = MagicMock()
        mock_config.RAW_DATA_DIR = Path("/test/data/raw")
        mock_get_config.return_value = mock_config

        with patch("pathlib.Path.glob", return_value=[]):
            with pytest.raises(FileNotFoundError, match="Export 디렉토리를 찾을 수 없습니다"):
                load_zone_boundaries()


class TestLoadPipeData:
    """파이프 데이터 로드 테스트"""

    @patch("main13d_visualize_zone_fatigue.get_config")
    @patch("geopandas.read_file")
    @patch("pandas.read_csv")
    def test_load_pipe_data_with_geometry(self, mock_read_csv, mock_read_file, mock_get_config):
        """geometry가 있는 파이프 데이터 로드 테스트"""
        # Mock 설정
        mock_config = MagicMock()
        mock_config.RAW_DATA_DIR = Path("/test/data/raw")
        mock_get_config.return_value = mock_config

        # Mock CSV 데이터
        csv_data = pd.DataFrame({
            "DATA_SRC": ["PIPE_LM", "PIPE_LM", "SPLY_LS", "SPLY_LS"],
            "zone": ["0470", "0480", "0490", "0470"],
            "FTR_IDN": [1.0, 2.0, 3.0, 4.0],
        })
        mock_read_csv.return_value = csv_data

        # Mock Shapefiles
        pipe_lm_shp = gpd.GeoDataFrame({
            "FTR_IDN": [1.0, 2.0],
            "geometry": [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
            ],
        }, crs="EPSG:5179")
        
        sply_ls_shp = gpd.GeoDataFrame({
            "FTR_IDN": [3.0, 4.0],
            "geometry": [
                LineString([(2, 2), (3, 3)]),
                LineString([(3, 3), (4, 4)]),
            ],
        }, crs="EPSG:5179")

        mock_read_file.side_effect = [pipe_lm_shp, sply_ls_shp]

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [Path("/test/data/raw/export_shp_20250704(0520)")]
            
            with patch("pathlib.Path.exists", return_value=True):
                input_dir = Path("/test/results/main13c")
                pipe_lm_gdf, sply_ls_gdf = load_pipe_data(input_dir)

                assert pipe_lm_gdf is not None
                assert len(pipe_lm_gdf) == 2
                assert sply_ls_gdf is not None
                assert len(sply_ls_gdf) == 2

    def test_load_pipe_data_no_csv(self):
        """CSV 파일이 없을 때 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir)
            pipe_lm_gdf, sply_ls_gdf = load_pipe_data(input_dir)
            
            assert pipe_lm_gdf is None
            assert sply_ls_gdf is None


class TestCreateVisualization:
    """시각화 생성 테스트"""

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    @patch("main13d_visualize_zone_fatigue.setup_korean_font")
    def test_create_visualization_zones_only(
        self, mock_font, mock_close, mock_adjust, mock_tight, mock_savefig
    ):
        """구역만 있는 시각화 테스트"""
        # 구역 데이터 생성
        mdlz_0520 = gpd.GeoDataFrame(
            {"geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
            crs="EPSG:5179",
        )
        
        smlz_subregions = gpd.GeoDataFrame(
            {
                "SMZ_NUM": ["0470", "0480", "0490"],
                "geometry": [
                    Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]),
                    Polygon([(3, 0), (6, 0), (6, 3), (3, 3)]),
                    Polygon([(6, 0), (9, 0), (9, 3), (6, 3)]),
                ],
            },
            crs="EPSG:5179",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_map.png"
            
            create_visualization(
                mdlz_0520,
                smlz_subregions,
                None,  # No pipes
                None,  # No pipes
                output_path,
                scale=1.0
            )
            
            mock_savefig.assert_called_once()
            mock_close.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    @patch("main13d_visualize_zone_fatigue.setup_korean_font")
    def test_create_visualization_with_pipes(
        self, mock_font, mock_close, mock_adjust, mock_tight, mock_savefig
    ):
        """파이프가 포함된 시각화 테스트"""
        # 구역 데이터
        mdlz_0520 = gpd.GeoDataFrame(
            {"geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
            crs="EPSG:5179",
        )
        
        smlz_subregions = gpd.GeoDataFrame(
            {
                "SMZ_NUM": ["0470", "0480", "0490"],
                "geometry": [
                    Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]),
                    Polygon([(3, 0), (6, 0), (6, 3), (3, 3)]),
                    Polygon([(6, 0), (9, 0), (9, 3), (6, 3)]),
                ],
            },
            crs="EPSG:5179",
        )

        # 파이프 데이터
        pipe_lm_gdf = gpd.GeoDataFrame(
            {
                "zone": ["0470", "0480"],
                "geometry": [
                    LineString([(0, 0), (1, 1)]),
                    LineString([(3, 3), (4, 4)]),
                ],
            },
            crs="EPSG:5179",
        )
        
        sply_ls_gdf = gpd.GeoDataFrame(
            {
                "zone": ["0490", "0470"],
                "geometry": [
                    LineString([(6, 6), (7, 7)]),
                    LineString([(1, 1), (2, 2)]),
                ],
            },
            crs="EPSG:5179",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_map.png"
            
            create_visualization(
                mdlz_0520,
                smlz_subregions,
                pipe_lm_gdf,
                sply_ls_gdf,
                output_path,
                scale=2.0  # Test scale option
            )
            
            mock_savefig.assert_called_once()
            mock_close.assert_called_once()


@patch("sys.argv", ["main13d_visualize_zone_fatigue.py"])
@patch("main13d_visualize_zone_fatigue.create_visualization")
@patch("main13d_visualize_zone_fatigue.load_pipe_data")
@patch("main13d_visualize_zone_fatigue.load_zone_boundaries")
def test_main_function(mock_load_zones, mock_load_pipes, mock_create_viz):
    """메인 함수 통합 테스트"""
    from main13d_visualize_zone_fatigue import main
    
    # Mock 설정
    mock_mdlz = MagicMock()
    mock_smlz = MagicMock()
    mock_load_zones.return_value = (mock_mdlz, mock_smlz)
    
    mock_pipe_lm = MagicMock()
    mock_sply_ls = MagicMock()
    mock_load_pipes.return_value = (mock_pipe_lm, mock_sply_ls)
    
    # 메인 함수 실행
    main()
    
    # 검증
    mock_load_zones.assert_called_once()
    mock_load_pipes.assert_called_once()
    mock_create_viz.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])