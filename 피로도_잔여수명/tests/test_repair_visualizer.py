"""
repair_visualizer.py 테스트
"""

from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from src.repair_visualizer import (
    calculate_repair_bounds,
    convert_coordinates_to_points,
    generate_random_points_in_polygon,
    generate_repair_points_from_smlz,
    get_repair_colors,
    get_repair_colors_for_pipe,
    plot_mdlz_background,
    plot_repair_points,
    plot_repair_points_on_pipe,
)


class TestGetRepairColors:
    """get_repair_colors 함수 테스트"""

    def test_get_repair_colors_structure(self):
        """색상 정보 구조 테스트"""
        result = get_repair_colors()

        assert isinstance(result, dict)
        assert "긴급복구" in result

        # 각 항목이 (색상코드, 표시명) 튜플인지 확인
        color_code, display_name = result["긴급복구"]
        assert isinstance(color_code, str)
        assert isinstance(display_name, str)
        assert color_code.startswith("#")
        assert display_name == "긴급복구"

    def test_get_repair_colors_for_pipe_structure(self):
        """파이프용 색상 정보 구조 테스트"""
        result = get_repair_colors_for_pipe()

        assert isinstance(result, dict)
        assert "긴급복구" in result

        # 파이프용 색상이 기본 색상과 다른지 확인
        basic_colors = get_repair_colors()
        pipe_colors = get_repair_colors_for_pipe()
        assert basic_colors["긴급복구"][0] != pipe_colors["긴급복구"][0]


class TestConvertCoordinatesToPoints:
    """convert_coordinates_to_points 함수 테스트"""

    @pytest.fixture
    def mock_repair_df(self):
        """테스트용 복구 작업 DataFrame"""
        return pd.DataFrame(
            {
                "epsg5179위도": [127.001, 127.002, 127.003],
                "epsg5179경도": [37.001, 37.002, 37.003],
                "구군": ["중구", "서구", "남구"],
            }
        )

    def test_convert_coordinates_to_points_success(self, mock_repair_df):
        """좌표를 Point 객체로 변환 테스트"""
        result = convert_coordinates_to_points(mock_repair_df)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 3
        assert "geometry" in result.columns
        assert all(isinstance(geom, Point) for geom in result.geometry)

        # 좌표값 확인
        first_point = result.geometry.iloc[0]
        assert first_point.x == 127.001
        assert first_point.y == 37.001

    def test_convert_coordinates_missing_columns(self):
        """epsg5179위도, epsg5179경도 컬럼이 없는 경우 테스트"""
        df = pd.DataFrame({"구군": ["중구", "서구"]})

        # 함수는 빈 GeoDataFrame을 반환함 (예외를 발생시키지 않음)
        result = convert_coordinates_to_points(df)
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 0

    def test_convert_coordinates_with_crs(self, mock_repair_df):
        """CRS 설정 테스트"""
        result = convert_coordinates_to_points(mock_repair_df, crs="EPSG:4326")

        assert result.crs.to_string() == "EPSG:4326"


class TestGenerateRandomPointsInPolygon:
    """generate_random_points_in_polygon 함수 테스트"""

    @pytest.fixture
    def test_polygon(self):
        """테스트용 다각형"""
        return Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])

    def test_generate_random_points_basic(self, test_polygon):
        """기본 랜덤 포인트 생성 테스트"""
        num_points = 5
        result = generate_random_points_in_polygon(test_polygon, num_points)

        assert len(result) == num_points
        assert all(isinstance(point, Point) for point in result)
        assert all(test_polygon.contains(point) for point in result)

    def test_generate_random_points_zero(self, test_polygon):
        """0개 포인트 생성 테스트"""
        result = generate_random_points_in_polygon(test_polygon, 0)
        assert len(result) == 0

    @patch("numpy.random.uniform")
    def test_generate_random_points_with_mock(self, mock_uniform, test_polygon):
        """랜덤 함수 모킹 테스트"""
        # 고정된 좌표 반환하도록 설정
        mock_uniform.side_effect = [0.5, 0.5, 0.3, 0.7]  # x1, y1, x2, y2

        result = generate_random_points_in_polygon(test_polygon, 2)

        assert len(result) == 2
        assert result[0].x == 0.5
        assert result[0].y == 0.5


class TestPlotMdlzBackground:
    """plot_mdlz_background 함수 테스트"""

    @pytest.fixture
    def mock_smlz_gdf(self):
        """테스트용 소구역 GeoDataFrame"""
        return gpd.GeoDataFrame(
            {
                "smlz": ["001", "002", "003"],
                "geometry": [
                    Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                    Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                    Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
                ],
            }
        )

    def test_plot_mdlz_background_success(self, mock_smlz_gdf):
        """소구역 배경 플롯 테스트"""
        fig, ax = plt.subplots()

        plot_mdlz_background(ax, mock_smlz_gdf)

        # 플롯이 생성되었는지 확인 (collection 수 확인)
        assert len(ax.collections) > 0
        plt.close(fig)

    def test_plot_mdlz_background_empty_gdf(self):
        """빈 GeoDataFrame 테스트"""
        fig, ax = plt.subplots()
        empty_gdf = gpd.GeoDataFrame()

        plot_mdlz_background(ax, empty_gdf)

        # 에러 없이 실행되는지 확인
        plt.close(fig)

    def test_plot_mdlz_background_with_labels(self, mock_smlz_gdf):
        """라벨 표시 옵션 테스트"""
        fig, ax = plt.subplots()

        plot_mdlz_background(ax, mock_smlz_gdf, show_labels=False)

        assert len(ax.collections) > 0
        plt.close(fig)


class TestPlotRepairPoints:
    """plot_repair_points 함수 테스트"""

    @pytest.fixture
    def mock_repair_data(self):
        """테스트용 복구 작업 데이터"""
        return {
            "긴급복구": pd.DataFrame(
                {
                    "구군": ["중구", "서구", "중구"],
                    "epsg5179위도": [127.001, 127.002, 127.003],
                    "epsg5179경도": [37.001, 37.002, 37.003],
                }
            )
        }

    def test_plot_repair_points_success(self, mock_repair_data):
        """복구 지점 플롯 테스트"""
        fig, ax = plt.subplots()

        legend_elements, total_points = plot_repair_points(ax, mock_repair_data)

        # 반환값 확인
        assert isinstance(legend_elements, list)
        assert isinstance(total_points, int)
        assert total_points == 3
        plt.close(fig)

    def test_plot_repair_points_with_pipe_colors(self, mock_repair_data):
        """파이프용 색상 사용 테스트"""
        fig, ax = plt.subplots()

        legend_elements, total_points = plot_repair_points(
            ax, mock_repair_data, use_pipe_colors=True
        )

        assert len(legend_elements) > 0
        plt.close(fig)

    def test_plot_repair_points_empty_data(self):
        """빈 데이터 테스트"""
        fig, ax = plt.subplots()

        legend_elements, total_points = plot_repair_points(ax, {})

        # 빈 데이터의 경우 0개 포인트
        assert total_points == 0
        assert len(legend_elements) == 0
        plt.close(fig)

    def test_plot_repair_points_custom_settings(self, mock_repair_data):
        """사용자 정의 설정 테스트"""
        fig, ax = plt.subplots()

        legend_elements, total_points = plot_repair_points(
            ax, mock_repair_data, point_size=100, point_alpha=0.5, zorder=5
        )

        assert total_points == 3
        plt.close(fig)


class TestPlotRepairPointsOnPipe:
    """plot_repair_points_on_pipe 함수 테스트"""

    @pytest.fixture
    def mock_repair_data(self):
        """테스트용 복구 작업 데이터"""
        return {
            "긴급복구": pd.DataFrame(
                {
                    "구군": ["중구", "서구"],
                    "소구역번호": ["001", "002"],
                    "epsg5179위도": [127.001, 127.002],
                    "epsg5179경도": [37.001, 37.002],
                }
            )
        }

    def test_plot_repair_points_on_pipe_basic(self, mock_repair_data):
        """파이프와 복구 지점 통합 플롯 기본 테스트"""
        fig, ax = plt.subplots()

        legend_elements, total_points = plot_repair_points_on_pipe(ax, mock_repair_data)

        # 반환값 확인
        assert isinstance(legend_elements, list)
        assert isinstance(total_points, int)
        assert total_points == 2
        plt.close(fig)

    def test_plot_repair_points_on_pipe_no_repair(self):
        """복구 데이터가 없는 경우 테스트"""
        fig, ax = plt.subplots()

        legend_elements, total_points = plot_repair_points_on_pipe(ax, {})

        # 복구 데이터가 없으면 0개 포인트
        assert total_points == 0
        assert len(legend_elements) == 0
        plt.close(fig)

    def test_plot_repair_points_on_pipe_with_smlz_file(
        self, mock_repair_data, tmp_path
    ):
        """SMLZ 파일 경로 제공 테스트"""
        # 임시 파일 생성
        smlz_file = tmp_path / "smlz.shp"
        smlz_file.touch()

        fig, ax = plt.subplots()

        legend_elements, total_points = plot_repair_points_on_pipe(
            ax, mock_repair_data, smlz_file=smlz_file
        )

        plt.close(fig)


class TestGenerateRepairPointsFromSmlz:
    """generate_repair_points_from_smlz 함수 테스트"""

    @pytest.fixture
    def mock_repair_df(self):
        """테스트용 복구 데이터"""
        return pd.DataFrame({"구군": ["중구", "서구"], "소구역번호": ["001", "002"]})

    def test_generate_repair_points_from_smlz_no_file(self, mock_repair_df, tmp_path):
        """SMLZ 파일이 없는 경우 테스트"""
        smlz_file = tmp_path / "nonexistent.shp"

        result = generate_repair_points_from_smlz(mock_repair_df, smlz_file, "긴급복구")

        # 파일이 없으면 빈 리스트 반환
        assert isinstance(result, list)
        assert len(result) == 0

    def test_generate_repair_points_from_smlz_invalid_file(
        self, mock_repair_df, tmp_path
    ):
        """잘못된 SMLZ 파일 테스트"""
        smlz_file = tmp_path / "invalid.shp"
        smlz_file.write_text("invalid content")

        result = generate_repair_points_from_smlz(mock_repair_df, smlz_file, "긴급복구")

        # 잘못된 파일이면 빈 리스트 반환
        assert isinstance(result, list)
        assert len(result) == 0


class TestCalculateRepairBounds:
    """calculate_repair_bounds 함수 테스트"""

    @pytest.fixture
    def mock_repair_data(self):
        """테스트용 복구 데이터"""
        return {
            "긴급복구": pd.DataFrame(
                {
                    "구군": ["중구", "서구", "남구"],
                    "epsg5179위도": [127.001, 127.003, 127.002],
                    "epsg5179경도": [37.001, 37.003, 37.002],
                }
            )
        }

    def test_calculate_repair_bounds_success(self, mock_repair_data):
        """복구 지점 경계 계산 테스트"""
        result = calculate_repair_bounds(mock_repair_data)

        assert result is not None
        assert isinstance(result, np.ndarray)
        assert len(result) == 4  # minx, miny, maxx, maxy

        minx, miny, maxx, maxy = result
        assert minx == 127.001
        assert miny == 37.001
        assert maxx == 127.003
        assert maxy == 37.003

    def test_calculate_repair_bounds_empty_data(self):
        """빈 복구 데이터 테스트"""
        empty_data = {}

        result = calculate_repair_bounds(empty_data)

        # 빈 데이터의 경우 None 반환
        assert result is None

    def test_calculate_repair_bounds_invalid_coordinates(self):
        """잘못된 좌표 데이터 테스트"""
        invalid_data = {
            "긴급복구": pd.DataFrame(
                {
                    "구군": ["중구", "서구"],
                    "wrong_col": [1, 2],  # 올바른 좌표 컬럼이 없음
                }
            )
        }

        result = calculate_repair_bounds(invalid_data)

        # 유효한 좌표가 없으면 None 반환
        assert result is None

    def test_calculate_repair_bounds_multiple_types(self):
        """여러 복구 유형 테스트"""
        multi_data = {
            "긴급복구": pd.DataFrame(
                {"epsg5179위도": [127.001, 127.002], "epsg5179경도": [37.001, 37.002]}
            ),
            "일반복구": pd.DataFrame(
                {"epsg5179위도": [127.003, 127.004], "epsg5179경도": [37.003, 37.004]}
            ),
        }

        result = calculate_repair_bounds(multi_data)

        assert result is not None
        minx, miny, maxx, maxy = result
        assert minx == 127.001
        assert miny == 37.001
        assert maxx == 127.004
        assert maxy == 37.004


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
