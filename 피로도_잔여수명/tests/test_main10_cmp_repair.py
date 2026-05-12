"""
main10_cmp_repair.py 테스트
"""

from unittest.mock import Mock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from src.main10_cmp_repair import (
    load_pipe_fatigue_data,
    load_pipe_shapefiles,
    main,
    plot_pipe_fatigue_with_repair,
)


@pytest.fixture
def mock_pipe_gdf():
    """테스트용 파이프 GeoDataFrame"""
    data = {
        "FTR_IDN": [1001, 1002, 1003, 1004],
        "PIPE_TYPE": ["PIPE_LM", "PIPE_LM", "SPLY_LS", "SPLY_LS"],
        "geometry": [
            Point(200000, 400000).buffer(100),
            Point(210000, 410000).buffer(100),
            Point(220000, 420000).buffer(50),
            Point(230000, 430000).buffer(50),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


@pytest.fixture
def mock_fatigue_dict():
    """테스트용 피로 손상 딕셔너리"""
    return {
        "1001": 0.005,
        "1002": 0.02,
        "1003": 0.1,
        "1004": 0.5,
    }


@pytest.fixture
def mock_repair_data():
    """테스트용 복구 작업 데이터"""
    data = {
        "epsg5179위도": [205000.0, 215000.0, 225000.0],
        "epsg5179경도": [405000.0, 415000.0, 425000.0],
        "공사명": ["복구1", "복구2", "복구3"],
    }
    return {"긴급복구": pd.DataFrame(data)}


@pytest.fixture
def mock_polygon():
    """테스트용 폴리곤"""
    return Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])


class TestLoadPipeFatigueData:
    """load_pipe_fatigue_data 함수 테스트"""

    @patch("src.main10_cmp_repair.load_fatigue_data")
    @patch("pathlib.Path.exists")
    def test_load_pipe_fatigue_data_success(self, mock_exists, mock_load_fatigue):
        """피로 데이터 로드 성공 테스트"""
        # Given: CSV 파일들이 존재하고 데이터 로드 성공
        mock_exists.return_value = True
        mock_pipe_lm_df = pd.DataFrame(
            {"FTR_IDN": [1001, 1002], "0520_D_final": [0.01, 0.02]}
        )
        mock_sply_ls_df = pd.DataFrame(
            {"FTR_IDN": [2001, 2002], "0520_D_final": [0.03, 0.04]}
        )
        mock_load_fatigue.side_effect = [mock_pipe_lm_df, mock_sply_ls_df]

        # When: 피로 데이터 로드
        result = load_pipe_fatigue_data()

        # Then: 병합된 데이터 반환
        assert result is not None
        assert len(result) == 4  # 두 데이터프레임 병합
        assert "FTR_IDN" in result.columns
        assert "0520_D_final" in result.columns

    @patch("pathlib.Path.exists")
    def test_load_pipe_fatigue_data_no_files(self, mock_exists):
        """피로 데이터 파일이 없는 경우 테스트"""
        # Given: CSV 파일들이 존재하지 않음
        mock_exists.return_value = False

        # When: 피로 데이터 로드
        result = load_pipe_fatigue_data()

        # Then: None 반환
        assert result is None


class TestLoadPipeShapefiles:
    """load_pipe_shapefiles 함수 테스트"""

    @patch("src.main10_cmp_repair.load_pipe_shapefile")
    def test_load_pipe_shapefiles_success(self, mock_load_pipe, mock_pipe_gdf):
        """파이프 shapefile 로드 성공 테스트"""
        # Given: 두 타입의 파이프 데이터 로드 성공
        pipe_lm_gdf = mock_pipe_gdf.copy()
        sply_ls_gdf = mock_pipe_gdf.copy()
        mock_load_pipe.side_effect = [pipe_lm_gdf, sply_ls_gdf]

        # When: 파이프 shapefile 로드
        result = load_pipe_shapefiles("0520")

        # Then: 병합된 GeoDataFrame 반환
        assert result is not None
        assert len(result) == 8  # 두 GeoDataFrame 병합 (각각 4개 행)

        # load_pipe_shapefile이 두 번 호출되었는지 확인
        assert mock_load_pipe.call_count == 2

    @patch("src.main10_cmp_repair.load_pipe_shapefile")
    def test_load_pipe_shapefiles_no_data(self, mock_load_pipe):
        """파이프 shapefile이 없는 경우 테스트"""
        # Given: 파이프 데이터 로드 실패
        mock_load_pipe.return_value = None

        # When: 파이프 shapefile 로드
        result = load_pipe_shapefiles("9999")

        # Then: None 반환
        assert result is None


class TestPlotPipeFatigueWithRepair:
    """plot_pipe_fatigue_with_repair 함수 테스트"""

    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("src.main10_cmp_repair.setup_korean_font")
    @patch("src.main10_cmp_repair.setup_plot_style")
    @patch("src.main10_cmp_repair.prepare_fatigue_data")
    @patch("src.main10_cmp_repair.plot_smlz_background")
    @patch("src.main10_cmp_repair.create_fatigue_colormap")
    @patch("src.main10_cmp_repair.create_log_norm")
    @patch("src.main10_cmp_repair.plot_fatigue_pipes")
    @patch("src.main10_cmp_repair.add_fatigue_colorbar")
    @patch("src.main10_cmp_repair.calculate_fatigue_statistics")
    @patch("src.main10_cmp_repair.format_fatigue_stats_text")
    def test_plot_pipe_fatigue_basic(
        self,
        mock_format_stats,
        mock_calc_stats,
        mock_add_colorbar,
        mock_plot_pipes,
        mock_create_norm,
        mock_create_cmap,
        mock_plot_smlz,
        mock_prepare_data,
        mock_setup_style,
        mock_setup_font,
        mock_tight_layout,
        mock_savefig,
        mock_close,
        mock_pipe_gdf,
        mock_fatigue_dict,
        tmp_path,
    ):
        """기본 파이프 피로 손상 시각화 테스트"""
        # Mock 설정
        mock_fig = Mock()
        mock_ax = Mock()
        mock_setup_style.return_value = (mock_fig, mock_ax)
        mock_prepare_data.return_value = mock_pipe_gdf
        mock_cmap = Mock()
        mock_norm = Mock()
        mock_create_cmap.return_value = mock_cmap
        mock_create_norm.return_value = mock_norm
        mock_calc_stats.return_value = {"mean": 0.1, "max": 0.5}
        mock_format_stats.return_value = "통계 정보"

        output_path = tmp_path / "test_output.png"

        # When: 기본 시각화 실행
        plot_pipe_fatigue_with_repair(
            mock_pipe_gdf,
            mock_fatigue_dict,
            None,  # No repair data
            output_path,
            show_plot=False,
        )

        # Then: 모든 함수 호출 확인
        mock_setup_font.assert_called_once()
        mock_setup_style.assert_called_once()
        mock_prepare_data.assert_called_once_with(mock_pipe_gdf, mock_fatigue_dict)
        # SMLZ background is not called when smlz_file is None
        mock_plot_smlz.assert_not_called()
        mock_plot_pipes.assert_called_once_with(
            mock_ax, mock_pipe_gdf, mock_cmap, mock_norm
        )
        mock_add_colorbar.assert_called_once_with(mock_ax, mock_cmap, mock_norm)
        mock_tight_layout.assert_called_once()
        mock_savefig.assert_called_once_with(output_path, dpi=300, bbox_inches="tight")

    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("src.main10_cmp_repair.setup_korean_font")
    @patch("src.main10_cmp_repair.setup_plot_style")
    @patch("src.main10_cmp_repair.prepare_fatigue_data")
    @patch("src.main10_cmp_repair.plot_smlz_background")
    @patch("src.main10_cmp_repair.create_fatigue_colormap")
    @patch("src.main10_cmp_repair.create_log_norm")
    @patch("src.main10_cmp_repair.plot_fatigue_pipes")
    @patch("src.main10_cmp_repair.add_fatigue_colorbar")
    @patch("src.main10_cmp_repair.calculate_fatigue_statistics")
    @patch("src.main10_cmp_repair.format_fatigue_stats_text")
    @patch("src.main10_cmp_repair.plot_repair_points_on_pipe")
    def test_plot_pipe_fatigue_with_repair_data(
        self,
        mock_plot_repair,
        mock_format_stats,
        mock_calc_stats,
        mock_add_colorbar,
        mock_plot_pipes,
        mock_create_norm,
        mock_create_cmap,
        mock_plot_smlz,
        mock_prepare_data,
        mock_setup_style,
        mock_setup_font,
        mock_tight_layout,
        mock_savefig,
        mock_close,
        mock_pipe_gdf,
        mock_fatigue_dict,
        mock_repair_data,
        tmp_path,
    ):
        """복구 작업 데이터 포함 시각화 테스트"""
        # Mock 설정
        mock_fig = Mock()
        mock_ax = Mock()
        mock_ax.legend = Mock()
        mock_ax.add_artist = Mock()
        mock_setup_style.return_value = (mock_fig, mock_ax)
        mock_prepare_data.return_value = mock_pipe_gdf
        mock_cmap = Mock()
        mock_norm = Mock()
        mock_create_cmap.return_value = mock_cmap
        mock_create_norm.return_value = mock_norm
        mock_calc_stats.return_value = {"mean": 0.1, "max": 0.5}
        mock_format_stats.return_value = "통계 정보"
        mock_plot_repair.return_value = ([], 5)  # legend_elements, total_points

        output_path = tmp_path / "test_output.png"

        # When: 복구 데이터 포함 시각화 실행
        plot_pipe_fatigue_with_repair(
            mock_pipe_gdf,
            mock_fatigue_dict,
            mock_repair_data,
            output_path,
            show_plot=False,
            show_repair=True,
        )

        # Then: 복구 점 플롯 함수 호출 확인
        mock_plot_repair.assert_called_once_with(mock_ax, mock_repair_data, None)

    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("src.main10_cmp_repair.setup_korean_font")
    @patch("src.main10_cmp_repair.setup_plot_style")
    @patch("src.main10_cmp_repair.prepare_fatigue_data")
    @patch("src.main10_cmp_repair.plot_smlz_background")
    @patch("src.main10_cmp_repair.create_fatigue_colormap")
    @patch("src.main10_cmp_repair.create_log_norm")
    @patch("src.main10_cmp_repair.plot_fatigue_pipes")
    @patch("src.main10_cmp_repair.add_fatigue_colorbar")
    @patch("src.main10_cmp_repair.calculate_fatigue_statistics")
    @patch("src.main10_cmp_repair.format_fatigue_stats_text")
    def test_plot_pipe_fatigue_with_smlz_background(
        self,
        mock_format_stats,
        mock_calc_stats,
        mock_add_colorbar,
        mock_plot_pipes,
        mock_create_norm,
        mock_create_cmap,
        mock_plot_smlz,
        mock_prepare_data,
        mock_setup_style,
        mock_setup_font,
        mock_tight_layout,
        mock_savefig,
        mock_close,
        mock_pipe_gdf,
        mock_fatigue_dict,
        tmp_path,
    ):
        """SMLZ 배경과 함께 시각화 테스트"""
        # Mock 설정
        mock_fig = Mock()
        mock_ax = Mock()
        mock_setup_style.return_value = (mock_fig, mock_ax)
        mock_prepare_data.return_value = mock_pipe_gdf
        mock_cmap = Mock()
        mock_norm = Mock()
        mock_create_cmap.return_value = mock_cmap
        mock_create_norm.return_value = mock_norm
        mock_calc_stats.return_value = {"mean": 0.1, "max": 0.5}
        mock_format_stats.return_value = "통계 정보"

        output_path = tmp_path / "test_output.png"
        smlz_file = tmp_path / "test_smlz.shp"
        smlz_file.touch()  # 파일 존재 시뮬레이션

        # When: SMLZ 배경과 함께 시각화 실행
        plot_pipe_fatigue_with_repair(
            mock_pipe_gdf,
            mock_fatigue_dict,
            None,
            output_path,
            show_plot=False,
            smlz_file=smlz_file,
        )

        # Then: SMLZ 배경 플롯 함수 호출 확인
        mock_plot_smlz.assert_called_once_with(mock_ax, smlz_file)


class TestMain:
    """main 함수 테스트"""

    @patch("src.main10_cmp_repair.load_pipe_fatigue_data")
    @patch("src.main10_cmp_repair.load_all_repair_data")
    @patch("src.main10_cmp_repair.load_pipe_shapefiles")
    @patch("src.main10_cmp_repair.get_fatigue_by_ftr_idn")
    @patch("src.main10_cmp_repair.plot_pipe_fatigue_with_repair")
    @patch("src.main10_cmp_repair.get_smlz_shapefile_path")
    @patch("pathlib.Path.mkdir")
    def test_main_basic(
        self,
        mock_mkdir,
        mock_get_smlz,
        mock_plot,
        mock_get_fatigue,
        mock_load_pipe,
        mock_load_repair,
        mock_load_fatigue,
        mock_pipe_gdf,
        mock_fatigue_dict,
        mock_repair_data,
    ):
        """기본 main 함수 실행 테스트"""
        # Mock 설정
        mock_fatigue_df = pd.DataFrame(
            {"FTR_IDN": [1001, 1002], "0520_D_final": [0.01, 0.02]}
        )
        mock_load_fatigue.return_value = mock_fatigue_df
        mock_load_repair.return_value = mock_repair_data
        mock_load_pipe.return_value = mock_pipe_gdf
        mock_get_fatigue.return_value = mock_fatigue_dict
        mock_get_smlz.return_value = None

        with patch("sys.argv", ["main10_cmp_repair.py"]):
            main()

        mock_load_fatigue.assert_called_once()
        mock_load_repair.assert_called_once()
        mock_load_pipe.assert_called()  # 각 지역별로 호출되므로 정확한 횟수는 확인하지 않음
        mock_plot.assert_called()

    @patch("src.main10_cmp_repair.load_pipe_fatigue_data")
    def test_main_no_fatigue_data(self, mock_load_fatigue, capsys):
        """피로 데이터가 없는 경우 테스트"""
        # Given: 피로 데이터 로드 실패
        mock_load_fatigue.return_value = None

        # When: main 함수 실행
        with patch("sys.argv", ["main10_cmp_repair.py"]):
            main()

        # Then: 오류 메시지 출력 확인
        captured = capsys.readouterr()
        assert "오류: 로드할 수 있는 피로 데이터가 없습니다." in captured.out

    @patch("src.main10_cmp_repair.load_pipe_fatigue_data")
    @patch("src.main10_cmp_repair.load_all_repair_data")
    @patch("src.main10_cmp_repair.load_pipe_shapefiles")
    @patch("pathlib.Path.mkdir")
    def test_main_no_pipe_data(
        self, mock_mkdir, mock_load_pipe, mock_load_repair, mock_load_fatigue, capsys
    ):
        """파이프 데이터가 없는 경우 테스트"""
        # Given: 피로 데이터는 있지만 파이프 shapefile이 없음
        mock_fatigue_df = pd.DataFrame({"FTR_IDN": [1001], "0520_D_final": [0.01]})
        mock_load_fatigue.return_value = mock_fatigue_df
        mock_load_repair.return_value = {}
        mock_load_pipe.return_value = None

        # When: main 함수 실행
        with patch("sys.argv", ["main10_cmp_repair.py"]):
            main()

        # Then: 경고 메시지 출력 확인
        captured = capsys.readouterr()
        assert "지역의 파이프 shapefile을 찾을 수 없습니다." in captured.out

    @patch("src.main10_cmp_repair.load_pipe_fatigue_data")
    @patch("src.main10_cmp_repair.load_all_repair_data")
    @patch("pathlib.Path.mkdir")
    def test_main_with_no_repair_option(
        self, mock_mkdir, mock_load_repair, mock_load_fatigue
    ):
        """--no-repair 옵션 테스트"""
        # Given: 피로 데이터만 있음
        mock_fatigue_df = pd.DataFrame({"FTR_IDN": [1001], "0520_D_final": [0.01]})
        mock_load_fatigue.return_value = mock_fatigue_df

        # When: --no-repair 옵션으로 실행
        with patch("sys.argv", ["main10_cmp_repair.py", "--no-repair"]):
            main()

        # Then: 복구 데이터 로드 함수가 호출되지 않음
        mock_load_repair.assert_not_called()
