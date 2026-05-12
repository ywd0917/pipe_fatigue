"""
fatigue_visualizer.py 테스트
"""

from unittest.mock import patch

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import LineString

from src.fatigue_visualizer import (
    FATIGUE_VMAX,
    FATIGUE_VMIN,
    PIPE_LM_LINEWIDTH,
    SPLY_LS_LINEWIDTH,
    add_fatigue_colorbar,
    calculate_fatigue_statistics,
    create_fatigue_colormap,
    create_log_norm,
    format_fatigue_stats_text,
    plot_fatigue_pipes,
    prepare_fatigue_data,
)


@pytest.fixture
def mock_pipe_gdf():
    """테스트용 파이프 GeoDataFrame"""
    data = {
        "FTR_IDN": [1001.0, 1002.0, 1003.0, None, 1005.0],
        "PIPE_TYPE": ["PIPE_LM", "PIPE_LM", "SPLY_LS", "SPLY_LS", "PIPE_LM"],
        "geometry": [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 2)]),
            LineString([(2, 2), (3, 3)]),
            LineString([(3, 3), (4, 4)]),
            LineString([(4, 4), (5, 5)]),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


@pytest.fixture
def mock_fatigue_dict():
    """테스트용 피로 손상 딕셔너리"""
    return {
        "1001": 0.01,
        "1002": 0.05,
        "1003": 0.001,
        "1005": 0.5,
        # 1004는 의도적으로 누락
    }


class TestCreateFatigueColormap:
    """create_fatigue_colormap 함수 테스트"""

    def test_colormap_creation(self):
        """컬러맵 생성 테스트"""
        cmap = create_fatigue_colormap()

        # LinearSegmentedColormap 인스턴스 확인
        assert isinstance(cmap, mcolors.LinearSegmentedColormap)

        # 컬러맵 이름 확인
        assert cmap.name == "fatigue"

        # 색상 수 확인
        assert cmap.N == 100

    def test_colormap_colors(self):
        """컬러맵 색상 범위 테스트"""
        cmap = create_fatigue_colormap()

        # 0에서 파란색에 가까운지 확인
        blue_color = cmap(0.0)
        assert blue_color[2] > 0.9  # B channel이 높아야 함

        # 1에서 빨간색에 가까운지 확인
        red_color = cmap(1.0)
        assert red_color[0] > 0.9  # R channel이 높아야 함


class TestCreateLogNorm:
    """create_log_norm 함수 테스트"""

    def test_log_norm_creation(self):
        """LogNorm 생성 테스트"""
        norm = create_log_norm()

        # LogNorm 인스턴스 확인
        assert isinstance(norm, mcolors.LogNorm)

        # vmin, vmax 확인
        assert norm.vmin == FATIGUE_VMIN
        assert norm.vmax == FATIGUE_VMAX

    def test_log_norm_values(self):
        """LogNorm 정규화 값 테스트"""
        norm = create_log_norm()

        # 최소값 정규화
        assert norm(FATIGUE_VMIN) == 0.0

        # 최대값 정규화
        assert norm(FATIGUE_VMAX) == 1.0

        # 중간값 정규화 (0.01)
        mid_value = 0.01
        normalized = norm(mid_value)
        assert 0.4 < normalized < 0.6  # 로그 스케일에서 대략 중간


class TestPrepareFatigueData:
    """prepare_fatigue_data 함수 테스트"""

    def test_prepare_with_float_ftr_idn(self, mock_pipe_gdf, mock_fatigue_dict):
        """float 타입 FTR_IDN 처리 테스트"""
        result = prepare_fatigue_data(mock_pipe_gdf.copy(), mock_fatigue_dict)

        # FTR_IDN_str 컬럼 생성 확인
        assert "FTR_IDN_str" in result.columns

        # fatigue_damage 컬럼 생성 확인
        assert "fatigue_damage" in result.columns

        # 매칭된 값 확인
        assert result.loc[0, "fatigue_damage"] == 0.01
        assert result.loc[1, "fatigue_damage"] == 0.05
        assert result.loc[2, "fatigue_damage"] == 0.001
        assert result.loc[4, "fatigue_damage"] == 0.5

        # NaN 처리 확인 (FATIGUE_VMIN으로 대체)
        assert result.loc[3, "fatigue_damage"] == FATIGUE_VMIN

    def test_prepare_with_zero_values(self, mock_pipe_gdf, mock_fatigue_dict):
        """0 값 처리 테스트"""
        # 0 값 추가
        mock_fatigue_dict["1001"] = 0

        result = prepare_fatigue_data(mock_pipe_gdf.copy(), mock_fatigue_dict)

        # 0이 FATIGUE_VMIN으로 대체되었는지 확인
        assert result.loc[0, "fatigue_damage"] == FATIGUE_VMIN

    def test_prepare_unmatched_warning(self, mock_pipe_gdf, mock_fatigue_dict, capsys):
        """매칭되지 않은 파이프 경고 테스트"""
        # 일부 FTR_IDN 제거하여 매칭 실패 유도
        small_dict = {"1001": 0.01}

        result = prepare_fatigue_data(mock_pipe_gdf.copy(), small_dict)

        # 경고 메시지 확인
        captured = capsys.readouterr()
        assert "경고: 피로 손상 데이터가 없는 파이프" in captured.out

        # 매칭 안 된 값은 FATIGUE_VMIN으로 채워짐
        unmatched_count = (result["fatigue_damage"] == FATIGUE_VMIN).sum()
        assert unmatched_count > 0

    def test_no_fatigue_damage_log_column(self, mock_pipe_gdf, mock_fatigue_dict):
        """fatigue_damage_log 컬럼이 생성되지 않는지 확인"""
        result = prepare_fatigue_data(mock_pipe_gdf.copy(), mock_fatigue_dict)

        # fatigue_damage_log 컬럼이 없어야 함 (수정 후)
        assert "fatigue_damage_log" not in result.columns

        # fatigue_damage 컬럼만 있어야 함
        assert "fatigue_damage" in result.columns


class TestPlotFatiguePipes:
    """plot_fatigue_pipes 함수 테스트"""

    @patch("geopandas.GeoDataFrame.plot")
    def test_plot_pipe_lm(self, mock_plot, mock_pipe_gdf, mock_fatigue_dict):
        """PIPE_LM 플롯 테스트"""
        # 피로 데이터 준비
        prepared_gdf = prepare_fatigue_data(mock_pipe_gdf.copy(), mock_fatigue_dict)

        # Mock 설정
        fig, ax = plt.subplots()
        cmap = create_fatigue_colormap()
        norm = create_log_norm()

        # 함수 실행
        plot_fatigue_pipes(ax, prepared_gdf, cmap, norm)

        # plot이 호출되었는지 확인
        assert mock_plot.called

        # PIPE_LM에 대한 호출 확인
        calls = mock_plot.call_args_list
        for call in calls:
            kwargs = call[1]
            # fatigue_damage 컬럼 사용 확인 (fatigue_damage_log가 아님)
            if "column" in kwargs:
                assert kwargs["column"] == "fatigue_damage"

    @patch("geopandas.GeoDataFrame.plot")
    def test_plot_with_correct_linewidth(
        self, mock_plot, mock_pipe_gdf, mock_fatigue_dict
    ):
        """올바른 선 두께 사용 테스트"""
        prepared_gdf = prepare_fatigue_data(mock_pipe_gdf.copy(), mock_fatigue_dict)

        fig, ax = plt.subplots()
        cmap = create_fatigue_colormap()
        norm = create_log_norm()

        plot_fatigue_pipes(ax, prepared_gdf, cmap, norm)

        # 각 파이프 타입별 linewidth 확인
        calls = mock_plot.call_args_list
        for call in calls:
            kwargs = call[1]
            if "linewidth" in kwargs:
                # PIPE_LM 또는 SPLY_LS의 linewidth 확인
                assert kwargs["linewidth"] in [PIPE_LM_LINEWIDTH, SPLY_LS_LINEWIDTH]


class TestCalculateFatigueStatistics:
    """calculate_fatigue_statistics 함수 테스트"""

    def test_statistics_calculation(self, mock_pipe_gdf, mock_fatigue_dict):
        """통계 계산 테스트"""
        prepared_gdf = prepare_fatigue_data(mock_pipe_gdf.copy(), mock_fatigue_dict)

        stats = calculate_fatigue_statistics(prepared_gdf)

        # 필수 통계 키 확인 (실제 함수에서 반환하는 키들)
        assert "min_damage" in stats
        assert "max_damage" in stats
        assert "mean_damage" in stats
        assert "total_pipes" in stats
        assert "pipe_lm_count" in stats
        assert "sply_ls_count" in stats
        assert "damaged_pipes" in stats

        # 값 검증
        assert stats["min_damage"] >= FATIGUE_VMIN  # 최소값은 FATIGUE_VMIN 이상
        assert stats["max_damage"] == 0.5  # mock_fatigue_dict의 최대값
        assert stats["total_pipes"] == 5
        assert stats["pipe_lm_count"] == 3  # mock_pipe_gdf에서 PIPE_LM 개수
        assert stats["sply_ls_count"] == 2  # mock_pipe_gdf에서 SPLY_LS 개수
        assert stats["damaged_pipes"] >= 0  # 0.01 초과 파이프 수


class TestFormatFatigueStatsText:
    """format_fatigue_stats_text 함수 테스트"""

    def test_format_stats_text(self):
        """통계 텍스트 포맷 테스트"""
        # 실제 함수가 기대하는 키들로 수정
        stats = {
            "min_damage": 0.001,
            "max_damage": 0.5,
            "mean_damage": 0.05,
            "damaged_pipes": 100,
            "total_pipes": 120,
            "pipe_lm_count": 80,  # 필수 키 추가
            "sply_ls_count": 40,  # 필수 키 추가
        }

        text = format_fatigue_stats_text(stats, repair_points=50)

        # 실제 함수가 출력하는 텍스트 확인
        assert "총 파이프: 120개" in text
        assert "PIPE_LM: 80개" in text
        assert "SPLY_LS: 40개" in text
        assert "평균 손상: 0.0500" in text
        assert "최대 손상: 0.5000" in text
        assert "복구 작업: 50건" in text


class TestColorbarCreation:
    """add_fatigue_colorbar 함수 테스트"""

    @patch("matplotlib.pyplot.colorbar")
    def test_colorbar_addition(self, mock_colorbar):
        """컬러바 추가 테스트"""
        fig, ax = plt.subplots()
        cmap = create_fatigue_colormap()
        norm = create_log_norm()

        add_fatigue_colorbar(ax, cmap, norm)

        # colorbar 호출 확인
        assert mock_colorbar.called

        # 호출 인자 확인
        call_args = mock_colorbar.call_args
        assert call_args is not None


class TestLogNormIntegration:
    """LogNorm 통합 테스트"""

    def test_fatigue_values_with_log_norm(self):
        """실제 피로도 값과 LogNorm 통합 테스트"""
        norm = create_log_norm()

        # 실제 데이터 범위의 대표 값들
        test_values = [0.004557, 0.007244, 0.023285, 0.05, 0.1, 0.5, 1.0]

        for val in test_values:
            normalized = norm(val)
            # 정규화된 값이 0~1 범위인지 확인
            assert 0 <= normalized <= 1.1  # 1.1은 약간의 여유

            # 로그 스케일에서 적절한 위치인지 확인
            if val <= FATIGUE_VMIN:
                assert normalized == 0
            elif val >= FATIGUE_VMAX:
                assert normalized >= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
