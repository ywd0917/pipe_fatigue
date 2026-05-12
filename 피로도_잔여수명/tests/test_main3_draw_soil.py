"""
main3_draw_soil.py 테스트
"""

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from src.main3_draw_soil import (
    main,
    plot_all_layers,
    plot_individual_file,
)
from src.soil_visualizer import (
    get_age_colors,
    get_soil_files,
    get_type_styles,
    load_soil_layer,
)


@pytest.fixture
def mock_data_dir(tmp_path):
    """테스트용 데이터 디렉토리 생성"""
    # data/raw 디렉토리 생성
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    # soil 디렉토리는 data 바로 아래에 생성
    soil_dir = tmp_path / "data" / "soil"
    soil_dir.mkdir(parents=True)
    return raw_dir


@pytest.fixture
def mock_soil_files(mock_data_dir):
    """테스트용 soil 파일 경로"""
    # soil 디렉토리는 data 바로 아래에 있음
    soil_dir = mock_data_dir.parent / "soil"

    # 빈 파일 생성
    files = {
        "boundary": soil_dir / "Geology_250K_Boudary.shp",
        "fault": soil_dir / "Geology_250K_Fault.shp",
        "frame": soil_dir / "Geology_250K_Frame.shp",
        "litho": soil_dir / "Geology_250K_Litho.shp",
    }

    for file_path in files.values():
        file_path.touch()
        # .shx, .dbf, .prj 파일도 생성
        file_path.with_suffix(".shx").touch()
        file_path.with_suffix(".dbf").touch()
        file_path.with_suffix(".prj").touch()

    return files


def create_mock_gdf(geom_type="polygon", num_features=5):
    """모의 GeoDataFrame 생성"""
    if geom_type == "polygon":
        geometries = [
            Polygon([(i, i), (i + 1, i), (i + 1, i + 1), (i, i + 1)])
            for i in range(num_features)
        ]
    elif geom_type == "line":
        geometries = [LineString([(i, i), (i + 1, i + 1)]) for i in range(num_features)]
    elif geom_type == "point":
        geometries = [Point(i, i) for i in range(num_features)]

    data = {
        "geometry": geometries,
        "TYPE": [
            "지질경계",
            "추정지질경계",
            "점이지질경계",
            "지질경계",
            "추정지질경계",
        ][:num_features],
        "MAPNAME": [f"지역{i}" for i in range(num_features)],
        "age": [
            "중생대 백악기",
            "캄브리아기",
            "제4기",
            "중생대 쥐라기",
            "고생대 석탄기",
        ][:num_features],
    }

    return gpd.GeoDataFrame(data, crs="EPSG:4326")


class TestGetSoilFiles:
    """get_soil_files 함수 테스트"""

    def test_get_soil_files_success(self, mock_soil_files, mock_data_dir):
        """정상적인 파일 찾기"""
        result = get_soil_files(mock_data_dir)
        assert len(result) == 4
        assert all(key in result for key in ["boundary", "fault", "frame", "litho"])

    def test_get_soil_files_missing_dir(self, tmp_path):
        """soil 디렉토리가 없는 경우"""
        with pytest.raises(FileNotFoundError, match="soil 디렉토리를 찾을 수 없습니다"):
            get_soil_files(tmp_path)

    def test_get_soil_files_partial(self, mock_data_dir):
        """일부 파일만 있는 경우"""
        # soil 디렉토리는 data 바로 아래에 있음
        soil_dir = mock_data_dir.parent / "soil"
        # 일부 파일만 생성
        (soil_dir / "Geology_250K_Litho.shp").touch()

        with patch("builtins.print") as mock_print:
            result = get_soil_files(mock_data_dir)
            assert len(result) == 1
            assert "litho" in result
            # 경고 메시지 출력 확인
            mock_print.assert_any_call("경고: 일부 파일을 찾을 수 없습니다:")


class TestLoadSoilLayer:
    """load_soil_layer 함수 테스트"""

    @patch("geopandas.read_file")
    def test_load_soil_layer_success(self, mock_read_file):
        """정상적인 데이터 로드"""
        mock_gdf = create_mock_gdf()
        mock_read_file.return_value = mock_gdf

        result = load_soil_layer(Path("test.shp"))
        assert result is not None
        assert len(result) == 5
        mock_read_file.assert_called_once_with(Path("test.shp"), encoding="euc-kr")

    @patch("geopandas.read_file")
    def test_load_soil_layer_with_null_geometry(self, mock_read_file):
        """NULL geometry가 있는 경우"""
        mock_gdf = create_mock_gdf()
        # NULL geometry 추가
        mock_gdf.loc[len(mock_gdf)] = {
            "geometry": None,
            "TYPE": "test",
            "MAPNAME": "test",
            "age": "test",
        }
        mock_read_file.return_value = mock_gdf

        with patch("builtins.print") as mock_print:
            result = load_soil_layer(Path("test.shp"))
            assert len(result) == 5  # NULL geometry 제거됨
            mock_print.assert_any_call("경고: NULL geometry 1개 제거")

    @patch("geopandas.read_file")
    def test_load_soil_layer_error(self, mock_read_file):
        """로드 실패"""
        mock_read_file.side_effect = Exception("Test error")

        with patch("builtins.print") as mock_print:
            result = load_soil_layer(Path("test.shp"))
            assert result is None
            mock_print.assert_called_with("오류: test 로드 실패 - Test error")


class TestColorAndStyles:
    """색상 및 스타일 함수 테스트"""

    def test_get_age_colors(self):
        """지질 시대별 색상 확인"""
        colors = get_age_colors()
        assert isinstance(colors, dict)
        assert "중생대 백악기" in colors
        assert "고생대 캄브리아기" in colors
        assert all(color.startswith("#") for color in colors.values())

    def test_get_type_styles(self):
        """타입별 스타일 확인"""
        styles = get_type_styles()
        assert "boundary" in styles
        assert "fault" in styles

        # boundary 스타일 확인
        assert "지질경계" in styles["boundary"]
        assert "color" in styles["boundary"]["지질경계"]
        assert "linestyle" in styles["boundary"]["지질경계"]


class TestPlotIndividualFile:
    """plot_individual_file 함수 테스트"""

    @patch("src.soil_visualizer.load_soil_layer")
    @patch("src.main3_draw_soil.analyze_layer_data")
    @patch("src.main3_draw_soil.plot_layer_by_group")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.close")
    def test_plot_individual_file_litho(
        self,
        mock_close,
        mock_show,
        mock_savefig,
        mock_plot_layer,
        mock_analyze,
        mock_load,
    ):
        """Litho 파일 시각화"""
        mock_gdf = create_mock_gdf()
        mock_load.return_value = mock_gdf
        mock_analyze.return_value = ("age", None)
        mock_plot_layer.return_value = []

        output_path = Path("test_output.png")
        plot_individual_file(
            Path("data/soil/Geology_250K_Litho.shp"),
            output_path,
            group_by="age",
            show_plot=False,
        )

        mock_savefig.assert_called_once()
        mock_close.assert_called_once()
        mock_show.assert_not_called()

    @patch("src.soil_visualizer.load_soil_layer")
    @patch("src.main3_draw_soil.analyze_layer_data")
    @patch("src.main3_draw_soil.plot_layer_by_group")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    def test_plot_individual_file_boundary(
        self, mock_close, mock_savefig, mock_plot_layer, mock_analyze, mock_load
    ):
        """Boundary 파일 시각화"""
        mock_gdf = create_mock_gdf(geom_type="line")
        mock_load.return_value = mock_gdf
        mock_analyze.return_value = ("TYPE", "TYPE")
        mock_plot_layer.return_value = []

        output_path = Path("test_output.png")
        plot_individual_file(
            Path("data/soil/Geology_250K_Boudary.shp"), output_path, show_plot=False
        )

        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    @patch("src.soil_visualizer.load_soil_layer")
    def test_plot_individual_file_no_data(self, mock_load):
        """데이터 로드 실패시"""
        mock_load.return_value = None

        # 함수가 에러 없이 종료되어야 함
        plot_individual_file(Path("test.shp"), Path("output.png"), show_plot=False)


class TestPlotAllLayers:
    """plot_all_layers 함수 테스트"""

    @patch("src.soil_loader.load_soil_data")
    @patch("src.soil_visualizer.load_soil_layer")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    def test_plot_all_layers_default(
        self, mock_close, mock_savefig, mock_load_layer, mock_soil_loader
    ):
        """기본 전체 레이어 시각화"""
        # soil_loader는 사용되지 않음 (deprecated)
        mock_soil_loader.return_value = create_mock_gdf()

        # 모든 레이어는 load_soil_layer로 로드
        mock_load_layer.side_effect = [
            create_mock_gdf(),  # frame
            create_mock_gdf(),  # litho
            create_mock_gdf(geom_type="line"),  # boundary
            create_mock_gdf(geom_type="line"),  # fault
        ]

        soil_files = {
            "frame": Path("frame.shp"),
            "litho": Path("litho.shp"),
            "boundary": Path("boundary.shp"),
            "fault": Path("fault.shp"),
        }

        plot_all_layers(soil_files, Path("output.png"), show_plot=False)

        assert mock_load_layer.call_count == 4
        assert mock_soil_loader.call_count == 0  # No longer used
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    @patch("src.soil_loader.load_soil_data")
    @patch("src.soil_visualizer.load_soil_layer")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    def test_plot_all_layers_selected(
        self, mock_close, mock_savefig, mock_load_layer, mock_soil_loader
    ):
        """선택된 레이어만 시각화"""
        mock_load_layer.return_value = create_mock_gdf()

        soil_files = {
            "frame": Path("frame.shp"),
            "litho": Path("litho.shp"),
        }

        plot_all_layers(
            soil_files, Path("output.png"), layers=["litho"], show_plot=False
        )

        mock_load_layer.assert_called_once()  # litho만 로드
        mock_soil_loader.assert_not_called()  # 다른 로더는 사용하지 않음
        mock_savefig.assert_called_once()


class TestMainFunction:
    """main 함수 통합 테스트"""

    @patch("src.soil_visualizer.get_soil_files")
    @patch("src.main3_draw_soil.plot_individual_file")
    @patch("sys.argv", ["main3_draw_soil.py", "--file", "Litho", "--no-interactive"])
    def test_main_individual_file(self, mock_plot, mock_get_files):
        """개별 파일 시각화 모드"""
        mock_files = {"litho": Path("data/soil/Geology_250K_Litho.shp")}
        mock_get_files.return_value = mock_files

        main()

        mock_plot.assert_called_once()
        args = mock_plot.call_args[0]
        assert "Litho" in str(args[0])  # 파일 경로

    @patch("src.soil_visualizer.get_soil_files")
    @patch("src.main3_draw_soil.plot_all_layers")
    @patch("sys.argv", ["main3_draw_soil.py", "--no-interactive"])
    def test_main_all_layers(self, mock_plot, mock_get_files):
        """전체 레이어 시각화 모드"""
        mock_files = {
            "litho": Path("litho.shp"),
            "boundary": Path("boundary.shp"),
        }
        mock_get_files.return_value = mock_files

        main()

        mock_plot.assert_called_once()

    @patch("src.main3_draw_soil.process_all_layers")
    @patch("src.main3_draw_soil.process_individual_file")
    @patch("src.main3_draw_soil.get_soil_files")
    @patch("sys.argv", ["main3_draw_soil.py"])
    def test_main_no_files(
        self, mock_get_files, mock_process_individual, mock_process_all
    ):
        """파일이 없는 경우"""
        # Mock should return empty dict
        mock_get_files.return_value = {}

        with patch("builtins.print") as mock_print:
            main()

            # Verify the error message was printed
            mock_print.assert_any_call("오류: Soil shapefile을 찾을 수 없습니다.")

        # Verify no processing functions were called
        mock_process_individual.assert_not_called()
        mock_process_all.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
