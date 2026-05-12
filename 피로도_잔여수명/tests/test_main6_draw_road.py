"""main6_draw_road.py 테스트 코드."""

from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from src.main6_draw_road import (
    main,
    plot_road_network,
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


@pytest.fixture
def mock_road_file(tmp_path):
    """임시 도로 shapefile 경로 생성."""
    road_dir = tmp_path / "road"
    road_dir.mkdir()
    return road_dir / "TL_SPRD_MANAGE.shp"


class TestPlotRoadNetwork:
    """plot_road_network 함수 테스트."""

    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("matplotlib.pyplot.subplots")
    @patch("src.common.visualization_utils.setup_plot_style")
    def test_plot_road_network_no_show(
        self,
        mock_setup_style,
        mock_subplots,
        mock_tight_layout,
        mock_savefig,
        mock_close,
        sample_road_gdf,
        tmp_path,
    ):
        """도로 네트워크 플롯 (show_plot=False) 테스트."""
        # Mock 설정
        fig_mock = MagicMock()
        ax_mock = MagicMock()
        mock_subplots.return_value = (fig_mock, ax_mock)

        output_file = tmp_path / "test_road.png"

        # 함수 실행 (기본값 show_plot=False)
        plot_road_network(sample_road_gdf, output_file=output_file)

        # 검증
        mock_tight_layout.assert_called_once()
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("matplotlib.pyplot.subplots")
    @patch("src.common.visualization_utils.setup_plot_style")
    def test_plot_road_network_with_show(
        self,
        mock_setup_style,
        mock_subplots,
        mock_tight_layout,
        mock_savefig,
        mock_show,
        sample_road_gdf,
        tmp_path,
    ):
        """도로 네트워크 플롯 (show_plot=True) 테스트."""
        # Mock 설정
        fig_mock = MagicMock()
        ax_mock = MagicMock()
        mock_subplots.return_value = (fig_mock, ax_mock)

        output_file = tmp_path / "test_road.png"

        # 함수 실행
        plot_road_network(sample_road_gdf, output_file=output_file, show_plot=True)

        # 검증
        mock_show.assert_called_once()


class TestMain:
    """main 함수 테스트."""

    @patch("src.main6_draw_road.plot_road_network")
    @patch("src.main6_draw_road.print_road_analysis")
    @patch("src.main6_draw_road.analyze_road_attributes")
    @patch("src.main6_draw_road.load_road_from_file")
    @patch("pathlib.Path.mkdir")
    def test_main_success(
        self,
        mock_mkdir,
        mock_load_data,
        mock_analyze,
        mock_print_analysis,
        mock_plot,
        sample_road_gdf,
        tmp_path,
    ):
        """main 함수 정상 실행 테스트."""
        # Mock 설정
        mock_load_data.return_value = sample_road_gdf

        # Mock analyze_road_attributes 반환값
        mock_analyze.return_value = {
            "total_segments": 4,
            "has_roa_cls": True,
            "has_road_bt": True,
        }

        # 함수 실행 (argparse를 사용하기 때문에 sys.argv를 mock)
        with patch("sys.argv", ["main6_draw_road.py", "--prefix", "test_"]):
            main()

        # 검증
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_load_data.assert_called_once()
        mock_analyze.assert_called_once_with(sample_road_gdf)
        mock_print_analysis.assert_called_once_with(mock_analyze.return_value)
        assert mock_plot.call_count == 2  # 전체 + 중심부

    @patch("src.main6_draw_road.load_road_from_file")
    @patch("pathlib.Path.mkdir")
    def test_main_file_not_found(self, mock_mkdir, mock_load_data, capsys):
        """도로 파일이 없을 때 테스트."""
        mock_load_data.return_value = None

        with patch("sys.argv", ["main6_draw_road.py"]):
            main()

    @patch("src.main6_draw_road.plot_road_network")
    @patch("src.main6_draw_road.print_road_analysis")
    @patch("src.main6_draw_road.analyze_road_attributes")
    @patch("src.main6_draw_road.load_road_from_file")
    @patch("pathlib.Path.mkdir")
    def test_main_empty_gdf(
        self,
        mock_mkdir,
        mock_load_data,
        mock_analyze,
        mock_print_analysis,
        mock_plot,
    ):
        """빈 GeoDataFrame 처리 테스트."""
        # Mock 설정
        mock_load_data.return_value = gpd.GeoDataFrame()
        mock_analyze.return_value = {
            "total_segments": 0,
            "has_roa_cls": False,
            "has_road_bt": False,
        }

        # 함수 실행
        with patch("sys.argv", ["main6_draw_road.py"]):
            main()

        # 검증
        mock_analyze.assert_called_once()
        mock_plot.assert_called_once()  # 빈 데이터는 중심부 플롯 생략


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
