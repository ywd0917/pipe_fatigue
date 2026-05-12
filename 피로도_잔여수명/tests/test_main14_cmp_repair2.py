"""
main14_cmp_repair2.py 테스트
"""

import argparse
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from src.main14_cmp_repair2 import (
    convert_wgs84_to_geodataframe,
    get_repair_colors,
    load_520_repair_csv,
    load_pipe_shapefiles,
    load_repair_data_for_region,
    parse_arguments,
    plot_repair_points_520,
    process_repair_type,
)


class TestGetRepairColors:
    """get_repair_colors 함수 테스트"""

    def test_repair_colors(self):
        """복구 작업 색상 정의 테스트"""
        colors = get_repair_colors()

        # 필수 작업 유형 확인
        assert "지상누수" in colors
        assert "지하누수" in colors

        # 각 항목이 (색상, 라벨) 튜플인지 확인
        for repair_type, (color, label) in colors.items():
            assert isinstance(color, str)
            assert color.startswith("#")
            assert isinstance(label, str)
            assert label == repair_type


class TestLoad520RepairCsv:
    """load_520_repair_csv 함수 테스트"""

    def test_load_valid_csv(self, tmp_path):
        """유효한 CSV 파일 로드 테스트"""
        # 테스트 CSV 생성
        csv_path = tmp_path / "test_repair.csv"
        test_data = pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7],
                "경도": [127.0, 127.1, 127.2],
                "주소": ["서울시 A", "서울시 B", "서울시 C"],
            }
        )
        test_data.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # 함수 실행
        result = load_520_repair_csv(csv_path, verbose=False)

        assert result is not None
        assert len(result) == 3
        assert "위도" in result.columns
        assert "경도" in result.columns

    def test_load_missing_file(self, tmp_path):
        """존재하지 않는 파일 처리 테스트"""
        csv_path = tmp_path / "nonexistent.csv"

        result = load_520_repair_csv(csv_path, verbose=False)

        assert result is None

    def test_filter_invalid_coords(self, tmp_path):
        """유효하지 않은 좌표 필터링 테스트"""
        csv_path = tmp_path / "test_repair.csv"
        test_data = pd.DataFrame(
            {
                "위도": [37.5, None, -10, 37.7],
                "경도": [127.0, 127.1, 127.2, None],
                "주소": ["A", "B", "C", "D"],
            }
        )
        test_data.to_csv(csv_path, index=False, encoding="utf-8-sig")

        result = load_520_repair_csv(csv_path, verbose=False)

        assert result is not None
        assert len(result) == 1  # 첫 번째 행만 유효
        assert result.iloc[0]["위도"] == 37.5
        assert result.iloc[0]["경도"] == 127.0


class TestLoadRepairDataForRegion:
    """load_repair_data_for_region 함수 테스트"""

    @patch("src.main14_cmp_repair2.UNIFIED_REPAIR_CSV")
    def test_load_repair_data_with_unified_csv(self, mock_csv, tmp_path):
        """통합 CSV 파일 우선 사용 테스트"""
        # 통합 CSV 파일 생성
        unified_csv = tmp_path / "unified.csv"
        test_data = pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7, 37.8],
                "경도": [127.0, 127.1, 127.2, 127.3],
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
            }
        )
        test_data.to_csv(unified_csv, index=False, encoding="utf-8-sig")

        # 모킹 설정
        mock_csv.exists.return_value = True

        # pd.read_csv 패치
        with patch("src.main14_cmp_repair2.pd.read_csv", return_value=test_data):
            result = load_repair_data_for_region(tmp_path, "0520", verbose=False)

        assert len(result) == 4
        assert "지상누수" in result
        assert "지하누수" in result
        assert "긴급공사" in result
        assert "관리대장" in result

    @patch("src.main14_cmp_repair2.UNIFIED_REPAIR_CSV")
    def test_load_repair_data_no_unified_file(self, mock_csv, tmp_path):
        """통합 CSV 없을 때 빈 dict 반환 테스트"""
        mock_csv.exists.return_value = False

        # 함수 실행 - 통합 파일이 없으면 빈 dict 반환
        result = load_repair_data_for_region(tmp_path, "0520", verbose=False)

        # 통합 파일이 없으므로 빈 dict 반환
        assert len(result) == 0
        assert isinstance(result, dict)

    def test_load_repair_data_unsupported_region(self, tmp_path):
        """520 이외 지역 요청시 빈 dict 반환 테스트"""
        result = load_repair_data_for_region(tmp_path, "0903", verbose=False)

        # 현재 520 지역만 지원하므로 빈 dict 반환
        assert len(result) == 0
        assert isinstance(result, dict)


class TestConvertWgs84ToGeodataframe:
    """convert_wgs84_to_geodataframe 함수 테스트"""

    def test_convert_coordinates(self):
        """WGS84 좌표 변환 테스트"""
        df = pd.DataFrame(
            {
                "위도": [37.5665, 37.5512],
                "경도": [126.9780, 126.9882],
                "주소": ["서울시청", "남산타워"],
            }
        )

        result = convert_wgs84_to_geodataframe(df)

        assert isinstance(result, gpd.GeoDataFrame)
        assert result.crs.to_string() == "EPSG:5179"
        assert len(result) == 2
        assert all(result.geometry.type == "Point")


class TestPlotRepairPoints520:
    """plot_repair_points_520 함수 테스트"""

    @patch("matplotlib.pyplot.gca")
    def test_plot_repair_points(self, mock_gca):
        """복구 작업 점 그리기 테스트"""
        # Mock axes 설정
        mock_ax = MagicMock()
        mock_gca.return_value = mock_ax

        # 테스트 데이터
        repair_df = pd.DataFrame(
            {
                "위도": [37.5665, 37.5512],
                "경도": [126.9780, 126.9882],
                "주소": ["위치1", "위치2"],
            }
        )

        # 함수 실행
        legend_elements, count = plot_repair_points_520(
            mock_ax, repair_df, show_cluster_count=True
        )

        assert count == 2
        assert len(legend_elements) == 1
        # 클러스터링으로 인해 scatter가 클러스터 수만큼 호출됨
        assert mock_ax.scatter.call_count == 2  # 2개의 별도 클러스터

    def test_empty_dataframe(self):
        """빈 DataFrame 처리 테스트"""
        mock_ax = MagicMock()
        repair_df = pd.DataFrame(columns=["위도", "경도"])

        legend_elements, count = plot_repair_points_520(
            mock_ax, repair_df, show_cluster_count=False
        )

        assert count == 0
        assert len(legend_elements) == 0


class TestLoadPipeShapefiles:
    """load_pipe_shapefiles 함수 테스트"""

    @patch("src.main14_cmp_repair2.load_pipe_shapefile")
    def test_load_pipe_shapefiles_both_types(self, mock_load):
        """PIPE_LM과 SPLY_LS 모두 로드 테스트"""
        # Mock GeoDataFrame 생성
        pipe_lm_gdf = gpd.GeoDataFrame(
            {
                "PIPE_TYPE": ["PIPE_LM"] * 3,
                "FTR_IDN": [1, 2, 3],
                "geometry": [LineString([(0, 0), (1, 1)])] * 3,
            },
            crs="EPSG:5179",
        )

        sply_ls_gdf = gpd.GeoDataFrame(
            {
                "PIPE_TYPE": ["SPLY_LS"] * 2,
                "FTR_IDN": [4, 5],
                "geometry": [LineString([(2, 2), (3, 3)])] * 2,
            },
            crs="EPSG:5179",
        )

        mock_load.side_effect = [pipe_lm_gdf, sply_ls_gdf]

        # 함수 실행
        result = load_pipe_shapefiles("0520")

        assert result is not None
        assert len(result) == 5
        assert len(result[result["PIPE_TYPE"] == "PIPE_LM"]) == 3
        assert len(result[result["PIPE_TYPE"] == "SPLY_LS"]) == 2

    @patch("src.main14_cmp_repair2.load_pipe_shapefile")
    def test_load_pipe_shapefiles_none_found(self, mock_load):
        """shapefile이 없는 경우 테스트"""
        mock_load.side_effect = [None, None]

        result = load_pipe_shapefiles("0520")

        assert result is None


class TestProcessRepairType:
    """process_repair_type 함수 테스트"""

    @patch("src.main14_cmp_repair2.plot_pipe_fatigue_with_repair_520")
    def test_process_repair_type_success(self, mock_plot, tmp_path):
        """정상 처리 테스트"""
        # 테스트 데이터 준비
        repair_df = pd.DataFrame({"위도": [37.5], "경도": [127.0]})
        pipe_gdf = gpd.GeoDataFrame()
        fatigue_dict = {"1": 0.01}
        args = argparse.Namespace(show=False)

        # 함수 실행
        process_repair_type(
            "지상누수", repair_df, pipe_gdf, fatigue_dict, tmp_path, args, None, "0520"
        )

        # plot 함수가 호출되었는지 확인
        mock_plot.assert_called_once()

        # 출력 파일 경로 확인
        call_args = mock_plot.call_args[0]
        output_path = call_args[4]
        assert output_path.name == "지상누수_520_pipe_fatigue.png"

    @patch("src.main14_cmp_repair2.plot_pipe_fatigue_with_repair_520")
    def test_process_repair_type_error_handling(self, mock_plot, tmp_path, capsys):
        """에러 처리 테스트"""
        # plot 함수에서 예외 발생하도록 설정
        mock_plot.side_effect = Exception("Test error")

        repair_df = pd.DataFrame({"위도": [37.5], "경도": [127.0]})
        pipe_gdf = gpd.GeoDataFrame()
        fatigue_dict = {"1": 0.01}
        args = argparse.Namespace(show=False)

        # 함수 실행 (예외가 발생해도 프로그램이 중단되지 않아야 함)
        process_repair_type(
            "지상누수", repair_df, pipe_gdf, fatigue_dict, tmp_path, args, None, "0520"
        )

        # 에러 메시지 출력 확인
        captured = capsys.readouterr()
        assert "지상누수 처리 중 오류 발생" in captured.out


class TestParseArguments:
    """parse_arguments 함수 테스트"""

    def test_default_arguments(self):
        """기본 인자 테스트"""
        with patch("sys.argv", ["test_script.py"]):
            args = parse_arguments()

            assert args.region == "0520"
            assert args.output_dir is None
            assert args.show is False
            assert args.all is True  # --all이 기본값
            assert args.individual is False
            assert args.no_interactive is False

    def test_custom_region(self):
        """지역 코드 지정 테스트"""
        with patch("sys.argv", ["test_script.py", "--region", "0903"]):
            args = parse_arguments()

            assert args.region == "0903"
            assert args.all is True  # --all이 기본값

    def test_individual_option(self):
        """개별 이미지 생성 옵션 테스트"""
        with patch("sys.argv", ["test_script.py", "--individual"]):
            args = parse_arguments()

            assert args.individual is True
            assert args.all is True  # --all은 여전히 기본값

    def test_all_options(self):
        """모든 옵션 테스트"""
        with patch(
            "sys.argv",
            [
                "test_script.py",
                "--region",
                "0903",
                "--output-dir",
                "/tmp/output",
                "--show",
                "--no-interactive",
                "--individual",
            ],
        ):
            args = parse_arguments()

            assert args.region == "0903"
            assert args.output_dir == "/tmp/output"
            assert args.show is True
            assert args.all is True  # 기본값
            assert args.individual is True
            assert args.no_interactive is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
