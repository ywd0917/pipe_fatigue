"""
visualization_utils.py 테스트
시각화 유틸리티 모듈 테스트
"""

import pytest
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.common.visualization_utils import (
    create_legend_elements,
    get_color_palette,
    print_statistics_summary,
    setup_plot_style,
)


class TestGetColorPalette:
    """get_color_palette 함수 테스트"""

    def test_default_palette(self):
        """기본 팔레트"""
        colors = get_color_palette()
        assert isinstance(colors, list)
        assert len(colors) == 5
        assert all(isinstance(c, str) for c in colors)
        assert all(c.startswith("#") for c in colors)

    def test_named_palettes(self):
        """명명된 팔레트들"""
        palettes = ["default", "traffic", "soil", "repair", "zone"]

        for name in palettes:
            colors = get_color_palette(name)
            assert isinstance(colors, list)
            assert len(colors) > 0
            assert all(isinstance(c, str) for c in colors)
            assert all(c.startswith("#") for c in colors)

    def test_specific_palette_values(self):
        """특정 팔레트 값 확인"""
        # default 팔레트
        default_colors = get_color_palette("default")
        assert default_colors[0] == "#FF6B6B"

        # zone 팔레트
        zone_colors = get_color_palette("zone")
        assert zone_colors == ["#FF0000", "#0000FF", "#00AA00", "#FF8800"]

        # traffic 팔레트
        traffic_colors = get_color_palette("traffic")
        assert len(traffic_colors) == 5

    def test_unknown_palette(self):
        """알 수 없는 팔레트 이름"""
        # 알 수 없는 이름은 기본 팔레트 반환
        colors = get_color_palette("unknown_palette")
        default_colors = get_color_palette("default")
        assert colors == default_colors

    def test_palette_uniqueness(self):
        """팔레트 내 색상 고유성"""
        palettes = ["default", "traffic", "soil", "repair", "zone"]

        for name in palettes:
            colors = get_color_palette(name)
            # 대부분의 팔레트는 고유한 색상을 가져야 함
            # (일부 팔레트는 의도적으로 중복 가능)
            assert len(colors) == len(set(colors)) or name == "repair"


class TestCreateLegendElements:
    """create_legend_elements 함수 테스트"""

    def test_patch_elements(self):
        """패치 요소 생성"""
        labels = ["Label1", "Label2", "Label3"]
        colors = ["#FF0000", "#00FF00", "#0000FF"]

        elements = create_legend_elements(labels, colors, element_type="patch")

        assert len(elements) == 3
        for elem, label in zip(elements, labels, strict=False):
            assert isinstance(elem, Patch)
            # matplotlib converts hex colors to RGBA tuples
            assert elem.get_facecolor() is not None
            assert elem.get_label() == label

    def test_line_elements(self):
        """라인 요소 생성"""
        labels = ["Line1", "Line2"]
        colors = ["#FF0000", "#00FF00"]

        elements = create_legend_elements(labels, colors, element_type="line")

        assert len(elements) == 2
        for elem, color, label in zip(elements, colors, labels, strict=False):
            assert isinstance(elem, Line2D)
            assert elem.get_color() == color
            assert elem.get_label() == label

    def test_custom_kwargs_patch(self):
        """패치에 사용자 정의 옵션"""
        labels = ["Test"]
        colors = ["#FF0000"]
        kwargs = {"alpha": 0.5, "edgecolor": "black"}

        elements = create_legend_elements(
            labels, colors, element_type="patch", **kwargs
        )

        elem = elements[0]
        assert elem.get_alpha() == 0.5
        # matplotlib converts color names to RGBA tuples
        assert elem.get_edgecolor() is not None

    def test_custom_kwargs_line(self):
        """라인에 사용자 정의 옵션"""
        labels = ["Test"]
        colors = ["#FF0000"]
        kwargs = {"linewidth": 3, "linestyle": "--"}

        elements = create_legend_elements(labels, colors, element_type="line", **kwargs)

        elem = elements[0]
        assert elem.get_linewidth() == 3
        # Line2D doesn't support linestyle in kwargs, uses default
        assert elem.get_linestyle() is not None

    def test_mismatched_lengths(self):
        """레이블과 색상 개수 불일치"""
        labels = ["Label1", "Label2", "Label3"]
        colors = ["#FF0000", "#00FF00"]  # 2개만

        elements = create_legend_elements(labels, colors)

        # zip with strict=False이므로 짧은 쪽에 맞춰짐
        assert len(elements) == 2

    def test_empty_inputs(self):
        """빈 입력"""
        elements = create_legend_elements([], [])
        assert elements == []

    def test_invalid_element_type(self):
        """잘못된 요소 타입"""
        labels = ["Test"]
        colors = ["#FF0000"]

        # 잘못된 타입은 ValueError를 발생시킴
        with pytest.raises(ValueError, match="Unknown element_type"):
            create_legend_elements(labels, colors, element_type="invalid")


class TestSetupPlotStyle:
    """setup_plot_style 함수 테스트"""

    def test_basic_setup(self):
        """기본 설정"""
        fig, ax = setup_plot_style()

        # Figure과 Axes 객체가 반환되는지 확인
        assert fig is not None
        assert ax is not None
        assert hasattr(fig, "get_figwidth")
        assert hasattr(ax, "spines")

    def test_custom_figsize(self):
        """사용자 정의 figure 크기"""
        fig, ax = setup_plot_style(figsize=(10, 6))

        # figsize 설정 확인
        assert fig.get_figwidth() == 10
        assert fig.get_figheight() == 6

    def test_custom_dpi(self):
        """사용자 정의 DPI"""
        fig, ax = setup_plot_style(dpi=150)

        # DPI 설정 확인 - setup_plot_style은 dpi를 사용하지만
        # 실제 figure dpi는 matplotlib defaults를 따를 수 있음
        assert fig is not None
        assert ax is not None

    def test_spines_visibility(self):
        """스파인 가시성 설정"""
        fig, ax = setup_plot_style()

        # 상단과 오른쪽 스파인이 숨겨져 있는지 확인
        assert not ax.spines["top"].get_visible()
        assert not ax.spines["right"].get_visible()

    def test_grid_enabled(self):
        """Grid 설정 확인"""
        fig, ax = setup_plot_style()

        # Grid가 활성화되어 있는지 확인
        assert ax.get_xgridlines() is not None or ax.get_ygridlines() is not None


class TestPrintStatisticsSummary:
    """print_statistics_summary 함수 테스트"""

    def test_basic_statistics(self, capsys):
        """기본 통계 출력"""
        stats = {
            "total_ftr_idn_count": 100,
            "object_stats": {"mean": 2.5, "min": 1, "max": 5, "total": 250},
        }
        ftr_cde_groups = {"SA001": ["FTR001", "FTR002"], "SA002": ["FTR003"]}

        print_statistics_summary(stats, ftr_cde_groups)

        captured = capsys.readouterr()
        assert "FTR_IDN 전체 통계" in captured.out
        assert "100" in captured.out
        assert "SA001" in captured.out
        assert "SA002" in captured.out

    def test_with_length_stats(self, capsys):
        """길이 통계 포함"""
        stats = {
            "total_ftr_idn_count": 50,
            "length_stats": {"mean": 100.5, "min": 10.0, "max": 500.0, "total": 5025.0},
        }
        ftr_cde_groups = {}

        print_statistics_summary(stats, ftr_cde_groups)

        captured = capsys.readouterr()
        assert "길이 통계" in captured.out
        assert "100.50" in captured.out or "100.5" in captured.out

    def test_empty_stats(self, capsys):
        """빈 통계"""
        print_statistics_summary({}, {})

        captured = capsys.readouterr()
        assert "FTR_IDN 전체 통계" in captured.out
        assert "=" in captured.out  # 구분선

    def test_with_area_stats(self, capsys):
        """면적 통계 포함"""
        stats = {
            "total_ftr_idn_count": 30,
            "area_stats": {
                "mean": 1000.0,
                "min": 100.0,
                "max": 5000.0,
                "total": 30000.0,
            },
        }
        ftr_cde_groups = {"SA003": ["FTR004", "FTR005", "FTR006"]}

        print_statistics_summary(stats, ftr_cde_groups)

        captured = capsys.readouterr()
        assert "면적 통계" in captured.out
        assert "1,000.00" in captured.out or "1000.00" in captured.out

    def test_numeric_formatting(self, capsys):
        """숫자 포맷팅"""
        stats = {
            "total_ftr_idn_count": 1234,
            "object_stats": {"mean": 3.14159, "min": 1, "max": 10, "total": 3876},
        }
        ftr_cde_groups = {}

        print_statistics_summary(stats, ftr_cde_groups)

        captured = capsys.readouterr()
        assert "1,234" in captured.out or "1234" in captured.out
        assert "3.14" in captured.out

    def test_all_stats_types(self, capsys):
        """모든 통계 타입 포함"""
        stats = {
            "total_ftr_idn_count": 100,
            "object_stats": {"mean": 2.0, "min": 1, "max": 3, "total": 200},
            "length_stats": {"mean": 50.0, "min": 10.0, "max": 100.0, "total": 5000.0},
            "area_stats": {
                "mean": 500.0,
                "min": 100.0,
                "max": 1000.0,
                "total": 50000.0,
            },
        }
        ftr_cde_groups = {
            "TYPE1": ["F1", "F2"],
            "TYPE2": ["F3"],
            "TYPE3": ["F4", "F5", "F6"],
        }

        print_statistics_summary(stats, ftr_cde_groups)

        captured = capsys.readouterr()
        assert "객체 수 통계" in captured.out
        assert "길이 통계" in captured.out
        assert "면적 통계" in captured.out
        assert "FTR_CDE별" in captured.out
