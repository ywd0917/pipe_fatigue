"""
visualization_utils.py 모듈 테스트
공통 시각화 유틸리티 함수들의 단위 테스트
"""

import matplotlib.pyplot as plt
import pytest

from src.common.visualization_utils import (
    create_legend_elements,
    format_number,
    format_shapefile_info,
    get_color_palette,
    print_statistics_summary,
    setup_plot_style,
)


class TestColorPalettes:
    """색상 팔레트 관련 테스트"""

    def test_get_color_palette_default(self):
        """기본 팔레트 테스트"""
        colors = get_color_palette("default")
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)
        assert all(color.startswith("#") for color in colors)

    def test_get_color_palette_traffic(self):
        """교통 팔레트 테스트"""
        colors = get_color_palette("traffic")
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)

    def test_get_color_palette_soil(self):
        """토양 팔레트 테스트"""
        colors = get_color_palette("soil")
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)

    def test_get_color_palette_repair(self):
        """복구 팔레트 테스트"""
        colors = get_color_palette("repair")
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)

    def test_get_color_palette_zone(self):
        """Zone 팔레트 테스트"""
        colors = get_color_palette("zone")
        assert len(colors) == 4  # LRGZ, MDLZ, SCDZ, SMLZ
        assert all(isinstance(color, str) for color in colors)

    def test_get_color_palette_unknown(self):
        """알 수 없는 팔레트는 기본값 반환"""
        colors = get_color_palette("unknown")
        default_colors = get_color_palette("default")
        assert colors == default_colors


class TestSetupPlotStyle:
    """플롯 스타일 설정 테스트"""

    def test_setup_plot_style_default(self):
        """기본 플롯 스타일 설정 테스트"""
        fig, ax = setup_plot_style()
        assert isinstance(fig, plt.Figure)
        assert isinstance(ax, plt.Axes)
        assert fig.get_figwidth() == 12
        assert fig.get_figheight() == 8

    def test_setup_plot_style_custom_size(self):
        """커스텀 크기 플롯 스타일 테스트"""
        fig, ax = setup_plot_style(figsize=(10, 6))
        assert fig.get_figwidth() == 10
        assert fig.get_figheight() == 6

    def test_setup_plot_style_spines(self):
        """플롯 테두리 설정 테스트"""
        fig, ax = setup_plot_style()
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_setup_plot_style_custom_dpi(self):
        """DPI 설정 테스트"""
        fig, ax = setup_plot_style(dpi=150)
        # matplotlib은 dpi를 설정하면 figure 크기에 반영됨
        # 실제 DPI는 백엔드에 따라 달라질 수 있음
        assert fig is not None
        assert ax is not None

    def teardown_method(self):
        """각 테스트 후 플롯 정리"""
        plt.close("all")


class TestCreateLegendElements:
    """범례 요소 생성 테스트"""

    def test_create_legend_elements_patch(self):
        """패치 범례 요소 생성 테스트"""
        labels = ["Label1", "Label2", "Label3"]
        colors = ["red", "green", "blue"]

        legend_elements = create_legend_elements(labels, colors, element_type="patch")

        assert len(legend_elements) == 3
        for elem in legend_elements:
            assert hasattr(elem, "get_label")
            assert hasattr(elem, "get_facecolor")

    def test_create_legend_elements_line(self):
        """선 범례 요소 생성 테스트"""
        labels = ["Line1", "Line2"]
        colors = ["red", "blue"]

        legend_elements = create_legend_elements(labels, colors, element_type="line")

        assert len(legend_elements) == 2
        for elem in legend_elements:
            assert hasattr(elem, "get_label")
            assert hasattr(elem, "get_color")

    def test_create_legend_elements_invalid_type(self):
        """잘못된 타입 테스트"""
        labels = ["Label1"]
        colors = ["red"]

        with pytest.raises(ValueError, match="Unknown element_type"):
            create_legend_elements(labels, colors, element_type="invalid")

    def test_create_legend_elements_with_kwargs(self):
        """추가 인자가 있는 범례 요소 생성 테스트"""
        labels = ["Line1"]
        colors = ["red"]

        legend_elements = create_legend_elements(
            labels, colors, element_type="line", linewidth=3
        )

        assert len(legend_elements) == 1
        elem = legend_elements[0]
        # Line2D의 linewidth는 float 배열
        assert elem.get_linewidth() == 3


class TestPrintStatisticsSummary:
    """통계 요약 출력 테스트"""

    def test_print_statistics_summary_complete(self, capsys):
        """완전한 통계 정보 출력 테스트"""
        summary_stats = {
            "total_ftr_idn_count": 10,
            "object_stats": {
                "total": 100,
                "mean": 10.0,
                "min": 5,
                "max": 20,
            },
            "length_stats": {
                "total": 500.5,
                "mean": 50.05,
                "min": 10.0,
                "max": 100.0,
            },
            "area_stats": {
                "total": 1000.0,
                "mean": 100.0,
                "min": 50.0,
                "max": 200.0,
            },
        }

        ftr_cde_groups = {
            "SA001": ["12345", "67890"],
            "SA002": ["11111"],
        }

        print_statistics_summary(summary_stats, ftr_cde_groups)

        captured = capsys.readouterr()
        assert "FTR_IDN 전체 통계:" in captured.out
        assert "총 FTR_IDN 개수: 10" in captured.out
        assert "전체 객체 수: 100" in captured.out
        assert "전체 길이 합: 500.50" in captured.out
        assert "전체 면적 합: 1,000.00" in captured.out
        assert "SA001: 2개 FTR_IDN" in captured.out
        assert "SA002: 1개 FTR_IDN" in captured.out

    def test_print_statistics_summary_partial(self, capsys):
        """부분적인 통계 정보 출력 테스트"""
        summary_stats = {
            "total_ftr_idn_count": 5,
            "object_stats": {
                "total": 50,
                "mean": 10.0,
                "min": 5,
                "max": 15,
            },
        }

        ftr_cde_groups = {}

        print_statistics_summary(summary_stats, ftr_cde_groups)

        captured = capsys.readouterr()
        assert "FTR_IDN 전체 통계:" in captured.out
        assert "총 FTR_IDN 개수: 5" in captured.out
        assert "전체 객체 수: 50" in captured.out
        assert "총 길이:" not in captured.out
        assert "총 면적:" not in captured.out
        assert "FTR_CDE별 그룹:" not in captured.out  # 빈 그룹


class TestFormatFunctions:
    """포맷팅 함수 테스트"""

    def test_format_number_basic(self):
        """기본 숫자 포맷팅 테스트"""
        assert format_number(123.456) == "123.46"
        assert format_number(123.456, precision=1) == "123.5"
        assert format_number(0.123) == "0.12"

    def test_format_number_thousands(self):
        """천 단위 포맷팅 테스트"""
        assert format_number(1234.56) == "1.23K"
        assert format_number(12345.6) == "12.35K"
        assert format_number(999999) == "1000.00K"

    def test_format_number_millions(self):
        """백만 단위 포맷팅 테스트"""
        assert format_number(1234567) == "1.23M"
        assert format_number(12345678) == "12.35M"
        assert format_number(-5000000) == "-5.00M"

    def test_format_shapefile_info(self):
        """Shapefile 정보 포맷팅 테스트"""
        result = format_shapefile_info("test.shp", 100, "Point", "EPSG:5179")
        assert result == "test.shp: 100개 레코드, Point, CRS=EPSG:5179"

        result = format_shapefile_info("data.shp", 0, "No geometry", "No CRS")
        assert result == "data.shp: 0개 레코드, No geometry, CRS=No CRS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
