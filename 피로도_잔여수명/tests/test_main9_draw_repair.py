"""
main9_draw_repair.py 테스트
"""

from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from src.main9_draw_repair import (
    main,
    plot_repair_by_type,
    plot_repair_locations,
    setup_korean_font,
)


@pytest.fixture
def mock_repair_data():
    """테스트용 복구 작업 데이터"""
    return {
        "긴급복구": pd.DataFrame(
            {
                "epsg5179위도": [200000.0, 210000.0, 220000.0],
                "epsg5179경도": [400000.0, 410000.0, 420000.0],
                "공사명": ["복구작업1", "복구작업2", "복구작업3"],
                "주소": ["주소1", "주소2", "주소3"],
                "구군": ["구1", "구2", "구3"],
            }
        )
    }


@pytest.fixture
def mock_mdlz_gdf():
    """테스트용 MDLZ GeoDataFrame"""
    data = {
        "MDZ_NUM": ["M001", "M002"],
        "geometry": [
            Point(205000, 405000).buffer(5000),
            Point(215000, 415000).buffer(5000),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


@pytest.fixture
def mock_data_dir(tmp_path):
    """테스트용 데이터 디렉토리 생성"""
    data_dir = tmp_path / "data"
    repair_dir = data_dir / "repair"
    repair_dir.mkdir(parents=True)

    # 테스트용 CSV 파일 생성
    csv_file = repair_dir / "긴급복구.csv"
    mock_data = {
        "epsg5179위도": [200000.0, 210000.0],
        "epsg5179경도": [400000.0, 410000.0],
        "공사명": ["테스트복구1", "테스트복구2"],
    }
    pd.DataFrame(mock_data).to_csv(csv_file, index=False, encoding="utf-8-sig")

    return data_dir


class TestSetupKoreanFont:
    """setup_korean_font 함수 테스트"""

    @patch("src.common.korean_font_utils.setup_korean_font")
    def test_setup_korean_font_success(self, mock_setup_font, capsys):
        """한글 폰트 설정 성공 테스트"""
        # Given: 폰트 설정 성공
        mock_setup_font.return_value = "맑은 고딕"

        # When: 폰트 설정
        setup_korean_font()

        # Then: 성공 메시지 출력
        captured = capsys.readouterr()
        assert "한글 폰트 설정: 맑은 고딕" in captured.out

    @patch("src.common.korean_font_utils.setup_korean_font")
    def test_setup_korean_font_failure(self, mock_setup_font, capsys):
        """한글 폰트 설정 실패 테스트"""
        # Given: 폰트 설정 실패
        mock_setup_font.return_value = None

        # When: 폰트 설정
        setup_korean_font()

        # Then: 경고 메시지 출력
        captured = capsys.readouterr()
        assert "경고: 한글 폰트를 찾을 수 없습니다." in captured.out


class TestPlotRepairLocations:
    """plot_repair_locations 함수 테스트"""

    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("src.main9_draw_repair.plot_repair_points")
    @patch("src.main9_draw_repair.plot_mdlz_background")
    @patch("src.main9_draw_repair.calculate_repair_bounds")
    @patch("src.main9_draw_repair.setup_plot_style")
    @patch("src.main9_draw_repair.setup_korean_font")
    def test_plot_repair_locations_basic(
        self,
        mock_setup_font,
        mock_setup_style,
        mock_calc_bounds,
        mock_plot_mdlz,
        mock_plot_repair,
        mock_tight_layout,
        mock_savefig,
        mock_close,
        mock_repair_data,
        mock_mdlz_gdf,
        tmp_path,
    ):
        """복구 위치 플롯 기본 테스트"""
        # Given: Mock 설정
        fig_mock = MagicMock()
        ax_mock = MagicMock()
        mock_setup_style.return_value = (fig_mock, ax_mock)
        mock_calc_bounds.return_value = (100, 200, 300, 400)  # minx, miny, maxx, maxy
        mock_plot_repair.return_value = ([], 0)  # legend_elements, total_points

        output_path = tmp_path / "repair_test.png"

        # When: 복구 위치 플롯
        plot_repair_locations(
            repair_data=mock_repair_data,
            output_path=output_path,
            title="테스트 복구 위치",
            show_plot=False,
            mdlz_gdf=mock_mdlz_gdf,
        )

        # Then: 모든 함수 호출 확인
        mock_setup_font.assert_called_once()
        mock_setup_style.assert_called_once()
        # mdlz_gdf가 제공되면 calculate_repair_bounds가 호출되지 않음
        mock_calc_bounds.assert_not_called()
        mock_plot_mdlz.assert_called_once_with(ax_mock, mock_mdlz_gdf)
        mock_plot_repair.assert_called_once_with(ax_mock, mock_repair_data)
        mock_tight_layout.assert_called_once()
        mock_savefig.assert_called_once_with(output_path, dpi=300, bbox_inches="tight")
        mock_close.assert_called_once()

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("src.main9_draw_repair.plot_repair_points")
    @patch("src.main9_draw_repair.plot_mdlz_background")
    @patch("src.main9_draw_repair.calculate_repair_bounds")
    @patch("src.main9_draw_repair.setup_plot_style")
    @patch("src.main9_draw_repair.setup_korean_font")
    def test_plot_repair_locations_with_show(
        self,
        mock_setup_font,
        mock_setup_style,
        mock_calc_bounds,
        mock_plot_mdlz,
        mock_plot_repair,
        mock_tight_layout,
        mock_savefig,
        mock_show,
        mock_repair_data,
        tmp_path,
    ):
        """복구 위치 플롯 (show_plot=True) 테스트"""
        # Given: Mock 설정
        fig_mock = MagicMock()
        ax_mock = MagicMock()
        mock_setup_style.return_value = (fig_mock, ax_mock)
        mock_calc_bounds.return_value = (100, 200, 300, 400)
        mock_plot_repair.return_value = ([], 0)  # legend_elements, total_points

        output_path = tmp_path / "repair_test.png"

        # When: 복구 위치 플롯 (show_plot=True)
        plot_repair_locations(
            repair_data=mock_repair_data,
            output_path=output_path,
            show_plot=True,
        )

        # Then: show 함수 호출 확인
        mock_show.assert_called_once()


class TestPlotRepairByType:
    """plot_repair_by_type 함수 테스트"""

    @patch("src.main9_draw_repair.plot_repair_locations")
    def test_plot_repair_by_type(
        self,
        mock_plot_locations,
        mock_repair_data,
        tmp_path,
    ):
        """복구 작업 유형별 개별 시각화 테스트"""
        # Given: 테스트 데이터
        output_dir = tmp_path

        # When: 유형별 플롯 실행
        plot_repair_by_type(
            repair_data=mock_repair_data,
            output_dir=output_dir,
            show_plot=False,
            mdlz_gdf=None,
        )

        # Then: 각 유형별로 plot_repair_locations 호출 확인
        assert mock_plot_locations.call_count == len(mock_repair_data)

        # 호출 인자 검증
        for call_args in mock_plot_locations.call_args_list:
            assert call_args[1]["show_plot"] is False
            assert call_args[1]["mdlz_gdf"] is None


class TestMain:
    """main 함수 테스트"""

    @patch("src.main9_draw_repair.plot_repair_locations")
    @patch("src.main9_draw_repair.load_all_mdlz_shapefiles")
    @patch("src.main9_draw_repair.load_all_repair_data")
    @patch("pathlib.Path.mkdir")
    def test_main_success(
        self,
        mock_mkdir,
        mock_load_repair,
        mock_load_mdlz,
        mock_plot_locations,
        mock_repair_data,
        mock_mdlz_gdf,
    ):
        """main 함수 정상 실행 테스트"""
        # Given: Mock 설정
        mock_load_repair.return_value = mock_repair_data
        mock_load_mdlz.return_value = mock_mdlz_gdf

        # When: main 함수 실행 (argparse를 사용하므로 sys.argv mock)
        with patch("sys.argv", ["main9_draw_repair.py", "--output-dir", "test_"]):
            main()

        # Then: 모든 함수 호출 확인
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_load_repair.assert_called_once()
        mock_load_mdlz.assert_called_once()
        mock_plot_locations.assert_called_once()

    @patch("src.main9_draw_repair.load_all_repair_data")
    @patch("pathlib.Path.mkdir")
    def test_main_no_repair_data(self, mock_mkdir, mock_load_repair, capsys):
        """복구 데이터가 없는 경우 테스트"""
        # Given: 복구 데이터 없음
        mock_load_repair.return_value = {}

        # When: main 함수 실행
        with patch("sys.argv", ["main9_draw_repair.py"]):
            main()

        # Then: 오류 메시지 출력
        captured = capsys.readouterr()
        assert "오류: 복구 작업 데이터를 로드할 수 없습니다." in captured.out

    @patch("src.main9_draw_repair.plot_repair_by_type")
    @patch("src.main9_draw_repair.plot_repair_locations")
    @patch("src.main9_draw_repair.load_all_mdlz_shapefiles")
    @patch("src.main9_draw_repair.load_all_repair_data")
    @patch("pathlib.Path.mkdir")
    def test_main_with_separate_option(
        self,
        mock_mkdir,
        mock_load_repair,
        mock_load_mdlz,
        mock_plot_locations,
        mock_plot_by_type,
        mock_repair_data,
        mock_mdlz_gdf,
    ):
        """--separate 옵션으로 main 함수 실행 테스트"""
        # Given: Mock 설정
        mock_load_repair.return_value = mock_repair_data
        mock_load_mdlz.return_value = mock_mdlz_gdf

        # When: main 함수 실행 (--separate 옵션)
        with patch(
            "sys.argv",
            ["main9_draw_repair.py", "--separate", "--output-dir", "custom_"],
        ):
            main()

        # Then: 함수 호출 확인
        mock_plot_locations.assert_called_once()
        mock_plot_by_type.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
