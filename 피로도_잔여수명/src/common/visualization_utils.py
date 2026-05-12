"""
시각화 관련 공통 유틸리티 모듈
matplotlib 설정, 색상 팔레트, 범례 생성 등 시각화에 필요한 공통 기능 제공
"""

from typing import Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.common import korean_font_utils


def setup_korean_font() -> None:
    """한글 폰트 설정"""
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")
    else:
        print("경고: 한글 폰트를 찾을 수 없습니다.")


def get_color_palette(name: str = "default") -> list[str]:
    """
    사전 정의된 색상 팔레트 반환

    Args:
        name: 팔레트 이름 ("default", "traffic", "soil", "repair", "zone")

    Returns:
        색상 코드 리스트
    """
    palettes = {
        "default": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57"],
        "traffic": ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#6A994E"],
        "soil": ["#8B4513", "#D2691E", "#F4A460", "#DEB887", "#FFE4B5"],
        "repair": ["#FF0000", "#FFA500", "#FFFF00", "#00FF00", "#0000FF"],
        "zone": ["#FF0000", "#0000FF", "#00AA00", "#FF8800"],  # LRGZ, MDLZ, SCDZ, SMLZ
    }
    return palettes.get(name, palettes["default"])


def create_legend_elements(
    labels: list[str], colors: list[str], element_type: str = "patch", **kwargs: Any
) -> list[Any]:
    """
    범례 요소 생성

    Args:
        labels: 범례 레이블
        colors: 색상 리스트
        element_type: "patch" (사각형) 또는 "line" (선)
        **kwargs: 추가 스타일 옵션

    Returns:
        범례 요소 리스트
    """
    elements = []

    for label, color in zip(labels, colors, strict=False):
        element: Any
        if element_type == "patch":
            element = Patch(facecolor=color, label=label, **kwargs)
        elif element_type == "line":
            element = Line2D(
                [0], [0], color=color, label=label, linewidth=kwargs.get("linewidth", 2)
            )
        else:
            raise ValueError(f"Unknown element_type: {element_type}")

        elements.append(element)

    return elements


def setup_plot_style(
    figsize: tuple[float, float] = (12, 8), dpi: int = 100
) -> tuple[Any, Any]:
    """
    기본 플롯 스타일 설정

    Args:
        figsize: 그림 크기
        dpi: 해상도

    Returns:
        Figure와 Axes 객체
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    # 기본 스타일 설정
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.3, linestyle="--")

    return fig, ax


def add_scalebar(
    ax: Any, length: float = 1000, location: str = "lower right", **kwargs: Any
) -> None:
    """
    지도에 축척 막대 추가

    Args:
        ax: matplotlib axes
        length: 축척 막대 길이 (미터)
        location: 위치
        **kwargs: 추가 스타일 옵션
    """
    # 축척 막대 구현 (간단한 버전)
    # 실제 구현은 좌표계와 투영법에 따라 달라짐


def format_number(value: float, precision: int = 2) -> str:
    """
    숫자를 보기 좋게 포맷팅

    Args:
        value: 포맷팅할 값
        precision: 소수점 자리수

    Returns:
        포맷팅된 문자열
    """
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.{precision}f}M"
    if abs(value) >= 1_000:
        return f"{value/1_000:.{precision}f}K"
    return f"{value:.{precision}f}"


def print_statistics_summary(
    summary_stats: dict[str, Any], ftr_cde_groups: dict[str, list[str]]
) -> None:
    """
    통계 요약 정보를 포맷팅하여 출력

    Args:
        summary_stats: 요약 통계 딕셔너리
        ftr_cde_groups: FTR_CDE별 그룹 정보
    """
    print("\n" + "=" * 80)
    print("  FTR_IDN 전체 통계:")
    print("=" * 80)

    print(f"\n  총 FTR_IDN 개수: {summary_stats.get('total_ftr_idn_count', 0):,}개")

    # 객체 수 통계
    if "object_stats" in summary_stats:
        obj_stats = summary_stats["object_stats"]
        print("\n  객체 수 통계:")
        print(f"    - 평균 객체 수: {obj_stats['mean']:.2f}개")
        print(f"    - 최소 객체 수: {obj_stats['min']}개")
        print(f"    - 최대 객체 수: {obj_stats['max']}개")
        print(f"    - 전체 객체 수: {obj_stats['total']:,}개")

    # 길이 통계
    if "length_stats" in summary_stats:
        len_stats = summary_stats["length_stats"]
        print("\n  길이 통계 (LineString/MultiLineString):")
        print(f"    - 평균 총 길이: {len_stats['mean']:,.2f}")
        print(f"    - 최소 총 길이: {len_stats['min']:,.2f}")
        print(f"    - 최대 총 길이: {len_stats['max']:,.2f}")
        print(f"    - 전체 길이 합: {len_stats['total']:,.2f}")

    # 면적 통계
    if "area_stats" in summary_stats:
        area_stats = summary_stats["area_stats"]
        print("\n  면적 통계 (Polygon/MultiPolygon):")
        print(f"    - 평균 총 면적: {area_stats['mean']:,.2f}")
        print(f"    - 최소 총 면적: {area_stats['min']:,.2f}")
        print(f"    - 최대 총 면적: {area_stats['max']:,.2f}")
        print(f"    - 전체 면적 합: {area_stats['total']:,.2f}")

    # FTR_CDE별 요약
    if ftr_cde_groups:
        print("\n  FTR_CDE별 FTR_IDN 분포:")
        for ftr_cde, ftr_idns in sorted(ftr_cde_groups.items()):
            print(f"    - {ftr_cde}: {len(ftr_idns)}개 FTR_IDN")

    print("\n" + "=" * 80)


def format_shapefile_info(
    filename: str, record_count: int, geom_type: str, crs: str
) -> str:
    """
    Shapefile 정보를 포맷팅

    Args:
        filename: 파일명
        record_count: 레코드 수
        geom_type: Geometry 타입
        crs: 좌표계 정보

    Returns:
        포맷팅된 문자열
    """
    return f"{filename}: {record_count}개 레코드, {geom_type}, CRS={crs}"
