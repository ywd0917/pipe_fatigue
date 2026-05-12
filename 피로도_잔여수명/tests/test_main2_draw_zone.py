"""
main2_draw_zone.py 테스트
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import pytest

from src.common.visualization_utils import get_color_palette
from src.ftr_visualizer import generate_distinct_colors
from src.main2_draw_zone import (
    main,
    plot_shapefile_by_ftr_idn,
    plot_zones,
    process_ftr_visualization,
    process_zone_visualization,
    setup_korean_font,
)
from src.zone_visualizer import get_all_zone_files, load_zone_data


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

        # Then: 모든 Zone 파일 경로 반환
        assert len(result) == 1
        assert "0520" in result
        zone_files = result["0520"]
        assert len(zone_files) == 4
        assert all(zone.lower() in zone_files for zone in zone_types)

    def test_get_all_zone_files_no_export_dir(self, tmp_path):
        """export_shp_ 디렉토리가 없는 경우 테스트"""
        # Given: 빈 디렉토리
        # When/Then: FileNotFoundError 발생
        with pytest.raises(
            FileNotFoundError, match="export_shp_ 디렉토리를 찾을 수 없습니다"
        ):
            get_all_zone_files(tmp_path)


class TestGetColorPalette:
    """get_color_palette 함수의 zone 팔레트 테스트"""

    def test_get_zone_color_palette(self):
        """Zone 색상 팔레트 테스트"""
        # When: Zone 색상 팔레트 가져오기
        colors = get_color_palette("zone")

        # Then: 4개의 Zone 색상 확인
        assert len(colors) == 4
        assert all(isinstance(color, str) for color in colors)
        assert all(color.startswith("#") for color in colors)
        assert all(len(color) == 7 for color in colors)  # #RRGGBB 형식


class TestLoadZoneData:
    """load_zone_data 함수 테스트"""

    @patch("geopandas.read_file")
    def test_load_zone_data_all_zones(self, mock_read_file):
        """모든 Zone 데이터 로드 테스트"""
        # Given: Mock GeoDataFrame
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_gdf.__len__ = Mock(return_value=10)
        mock_read_file.return_value = mock_gdf

        zone_files = {
            "lrgz": Path("/test/WEA_LRGZ_AS.shp"),
            "mdlz": Path("/test/WEA_MDLZ_AS.shp"),
            "scdz": Path("/test/WEA_SCDZ_AS.shp"),
            "smlz": Path("/test/WEA_SMLZ_AS.shp"),
        }

        # When: 모든 Zone 데이터 로드
        result = load_zone_data(zone_files)

        # Then: 모든 Zone 데이터 반환
        assert len(result) == 4
        assert all(zone in result for zone in zone_files)
        assert mock_read_file.call_count == 4


class TestPlotZones:
    """plot_zones 함수 테스트"""

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("src.main2_draw_zone.setup_plot_style")
    def test_plot_zones_basic(
        self, mock_setup_style, mock_tight_layout, mock_savefig, tmp_path
    ):
        """기본 Zone 표시 테스트"""
        # Given: Mock 설정
        fig, ax = Mock(), Mock()
        mock_setup_style.return_value = (fig, ax)

        # Mock GeoDataFrame
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_gdf.total_bounds = [0, 0, 10, 10]

        zone_data = {
            "lrgz": mock_gdf,
            "mdlz": mock_gdf,
        }

        output_path = tmp_path / "test_output.png"

        # When: Zone 표시
        plot_zones(zone_data, output_path, single_zone=False)

        # Then: 저장 호출
        mock_savefig.assert_called_once()


class TestGenerateDistinctColors:
    """generate_distinct_colors 함수 테스트"""

    def test_generate_small_number_of_colors(self):
        """적은 수의 색상 생성 테스트"""
        # Given: 5개의 색상 요청
        n = 5

        # When: 색상 생성
        colors = generate_distinct_colors(n)

        # Then: 올바른 개수와 형식
        assert len(colors) == n
        assert all(isinstance(color, str) for color in colors)
        assert all(color.startswith("#") and len(color) == 7 for color in colors)


class TestPlotShapefileByFtrIdn:
    """plot_shapefile_by_ftr_idn 함수 테스트"""

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("src.main2_draw_zone.setup_plot_style")
    @patch("src.main2_draw_zone.analyze_ftr_idn")
    @patch("src.main2_draw_zone.load_shapefile_with_validation")
    @patch("src.main2_draw_zone.plot_geometry_by_type")
    def test_plot_basic(
        self,
        mock_plot_geometry,
        mock_load_shapefile,
        mock_analyze_ftr,
        mock_setup_style,
        mock_tight_layout,
        mock_savefig,
        tmp_path,
    ):
        """기본 시각화 테스트"""
        # Given: Mock 설정
        fig, ax = Mock(), Mock()
        mock_setup_style.return_value = (fig, ax)

        # Mock GeoDataFrame
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_gdf.__len__ = Mock(return_value=3)
        mock_gdf.columns = ["FTR_IDN", "geometry", "_group_id"]
        mock_gdf.total_bounds = [0, 0, 10, 10]

        # FTR_IDN 설정
        mock_gdf["FTR_IDN"] = Mock()
        mock_gdf["FTR_IDN"].unique = Mock(return_value=["IDN001", "IDN002"])

        # _group_id 설정 (리팩토링 후 사용)
        mock_gdf["_group_id"] = Mock()

        # groupby 설정 (리팩토링 후 _group_id로 groupby)
        mock_group = Mock()
        mock_gdf.groupby = Mock(
            return_value=[("IDN001", mock_group), ("IDN002", mock_group)]
        )

        mock_load_shapefile.return_value = mock_gdf

        # analyze_ftr_idn mock 설정
        mock_analyze_ftr.return_value = (["IDN001", "IDN002"], None)

        # plot_geometry_by_type mock 설정
        mock_plot_geometry.return_value = 1  # 그려진 객체 수

        output_path = tmp_path / "test.png"

        # When: 시각화
        plot_shapefile_by_ftr_idn(Path("/test/shapefile.shp"), output_path)

        # Then: 저장 호출
        mock_savefig.assert_called_once()


class TestSetupKoreanFont:
    """setup_korean_font 함수 테스트"""

    @patch("src.main2_draw_zone.korean_font_utils.setup_korean_font")
    def test_setup_korean_font_success(self, mock_font_setup):
        """한글 폰트 설정 성공 테스트"""
        # Given: 한글 폰트 설정 성공
        mock_font_setup.return_value = "Apple SD Gothic Neo"

        # When: 한글 폰트 설정
        setup_korean_font()

        # Then: 폰트 설정 함수 호출
        mock_font_setup.assert_called_once()


class TestProcessFunctions:
    """process_zone_visualization와 process_ftr_visualization 함수 테스트"""

    @patch("src.main2_draw_zone.get_all_zone_files")
    @patch("src.main2_draw_zone.load_zone_data")
    @patch("src.main2_draw_zone.plot_zones")
    def test_process_zone_visualization(
        self, mock_plot_zones, mock_load_data, mock_get_files
    ):
        """Zone 시각화 처리 테스트"""
        # Given: Mock 설정
        args = Mock()
        args.zone = None
        args.output = None
        args.title = None
        args.show = False

        mock_get_files.return_value = {"0520": {"lrgz": Path("/test/LRGZ.shp")}}
        mock_load_data.return_value = {"lrgz": Mock()}

        # When: Zone 시각화 처리
        process_zone_visualization(args)

        # Then: 함수 호출 확인
        mock_get_files.assert_called_once()
        mock_load_data.assert_called_once()
        mock_plot_zones.assert_called_once()

    @patch("src.main2_draw_zone.plot_shapefile_by_ftr_idn")
    @patch("pathlib.Path.exists")
    def test_process_ftr_visualization(self, mock_exists, mock_plot):
        """FTR_IDN 시각화 처리 테스트"""
        # Given: Mock 설정
        args = Mock()
        args.file = "test.shp"
        args.output = None
        args.title = None
        args.show = False

        mock_exists.return_value = True

        # When: FTR_IDN 시각화 처리
        process_ftr_visualization(args)

        # Then: 함수 호출 확인 (두 개의 export 디렉토리에서 파일을 찾으므로 2번 호출)
        assert mock_plot.call_count == 2


class TestMain:
    """main 함수 테스트"""

    @patch("sys.argv", ["main2_draw_zone.py", "--zone", "lrgz", "--no-interactive"])
    @patch("src.main2_draw_zone.process_zone_visualization")
    def test_main_zone_mode(self, mock_process_zone):
        """Zone 모드 main 함수 테스트"""
        # When: main 함수 실행
        main()

        # Then: Zone 처리 함수 호출
        mock_process_zone.assert_called_once()

    @patch("sys.argv", ["main2_draw_zone.py", "--file", "test.shp", "--no-interactive"])
    @patch("src.main2_draw_zone.process_ftr_visualization")
    def test_main_file_mode(self, mock_process_ftr):
        """파일 모드 main 함수 테스트"""
        # When: main 함수 실행
        main()

        # Then: FTR 처리 함수 호출
        mock_process_ftr.assert_called_once()

    @patch("sys.argv", ["main2_draw_zone.py", "--file", "test.shp", "--zone", "lrgz"])
    @patch("builtins.print")
    def test_main_conflict_options(self, mock_print):
        """충돌하는 옵션 테스트"""
        # When: main 함수 실행
        main()

        # Then: 오류 메시지 출력
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any(
            "--file과 --zone 옵션은 동시에 사용할 수 없습니다" in str(call)
            for call in print_calls
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
