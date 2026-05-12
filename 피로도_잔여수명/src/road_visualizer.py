"""
도로 데이터 시각화를 위한 특화 모듈
도로 네트워크 시각화 관련 비즈니스 로직
"""

from enum import IntEnum
from typing import Any, Optional

import geopandas as gpd
from matplotlib.lines import Line2D


class RoadClass(IntEnum):
    """도로 등급 정의"""

    HIGHWAY = 1  # 고속도로
    BOULEVARD = 2  # 대로
    ROAD = 3  # 로
    STREET = 4  # 길

    @property
    def korean_name(self) -> str:
        """한글 이름 반환"""
        names = {
            RoadClass.HIGHWAY: "고속도로",
            RoadClass.BOULEVARD: "대로",
            RoadClass.ROAD: "로",
            RoadClass.STREET: "길",
        }
        return names[self]

    @property
    def color(self) -> str:
        """도로 등급별 색상 반환"""
        colors = {
            RoadClass.HIGHWAY: "#FF0000",  # 빨간색
            RoadClass.BOULEVARD: "#FF7F00",  # 주황색
            RoadClass.ROAD: "#0000FF",  # 파란색
            RoadClass.STREET: "#00AA00",  # 녹색
        }
        return colors[self]

    @classmethod
    def from_value(cls, value: str) -> Optional["RoadClass"]:
        """값으로부터 RoadClass 인스턴스 생성"""
        try:
            return cls(int(value))
        except (ValueError, TypeError):
            return None


# 시각화 설정 상수
FIGURE_SIZE_FULL = (24, 20)  # 전체 도로 네트워크 이미지 크기
FIGURE_SIZE_CENTER = (20, 20)  # 중심부 도로 네트워크 이미지 크기
DPI = 1200  # 이미지 해상도

# 도로 폭 기준값 (미터)
ROAD_WIDTH_THRESHOLD_30M = 30  # 대로 기준
ROAD_WIDTH_THRESHOLD_15M = 15  # 중로 기준
ROAD_WIDTH_THRESHOLD_8M = 8  # 소로 기준

# 도로 폭별 선 두께 설정
ROAD_WIDTH_30M_PLUS = 0.125  # 30m 이상 도로
ROAD_WIDTH_15_30M = 0.09  # 15-30m 도로
ROAD_WIDTH_8_15M = 0.06  # 8-15m 도로
ROAD_WIDTH_UNDER_8M = 0.04  # 8m 미만 도로
ROAD_WIDTH_DEFAULT = 0.05  # 기본 선 두께 (ROAD_BT 없을 때)
ROAD_WIDTH_NO_CLASS = 0.025  # 도로 등급 정보 없을 때

# 색상 설정
DEFAULT_COLOR = "#808080"  # 기본 색상 (회색)
NO_CLASS_COLOR = "blue"  # 도로 등급 정보 없을 때 색상

# 투명도 설정
ALPHA_WITH_CLASS = 0.8  # 도로 등급 정보 있을 때
ALPHA_NO_CLASS = 0.7  # 도로 등급 정보 없을 때


def get_road_color(roa_cls_se: str) -> str:
    """ROA_CLS_SE 값에 따른 색상 반환.

    Args:
        roa_cls_se: 도로 등급 (1-4, 문자열 또는 숫자)

    Returns:
        색상 코드
    """
    road_class = RoadClass.from_value(roa_cls_se)
    if road_class is None:
        return DEFAULT_COLOR
    return road_class.color


def get_road_width(road_bt: float) -> float:
    """ROAD_BT 값에 따른 선 두께 반환.

    Args:
        road_bt: 도로 폭 (미터)

    Returns:
        선 두께
    """
    if road_bt >= ROAD_WIDTH_THRESHOLD_30M:
        return ROAD_WIDTH_30M_PLUS
    if road_bt >= ROAD_WIDTH_THRESHOLD_15M:
        return ROAD_WIDTH_15_30M
    if road_bt >= ROAD_WIDTH_THRESHOLD_8M:
        return ROAD_WIDTH_8_15M
    return ROAD_WIDTH_UNDER_8M


def categorize_road_width(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """도로 폭 카테고리 컬럼 추가

    Args:
        gdf: 도로 GeoDataFrame

    Returns:
        카테고리가 추가된 GeoDataFrame
    """
    if "ROAD_BT" in gdf.columns:
        gdf["width_category"] = gdf["ROAD_BT"].apply(
            lambda x: (
                3
                if x >= ROAD_WIDTH_THRESHOLD_30M
                else (
                    2
                    if x >= ROAD_WIDTH_THRESHOLD_15M
                    else (1 if x >= ROAD_WIDTH_THRESHOLD_8M else 0)
                )
            )
        )
    return gdf


def plot_roads_by_class_and_width(
    ax: Any, gdf: gpd.GeoDataFrame, has_roa_cls: bool, has_road_bt: bool
) -> None:
    """도로 등급과 폭에 따라 시각화

    Args:
        ax: matplotlib axes
        gdf: 도로 GeoDataFrame
        has_roa_cls: ROA_CLS_SE 필드 존재 여부
        has_road_bt: ROAD_BT 필드 존재 여부
    """
    if has_roa_cls and has_road_bt:
        # 도로 폭 카테고리 추가
        gdf = categorize_road_width(gdf)

        # ROA_CLS_SE와 width_category로 그룹화하여 효율적으로 그리기
        for roa_cls in sorted(gdf["ROA_CLS_SE"].unique()):
            color = get_road_color(roa_cls)
            cls_gdf = gdf[gdf["ROA_CLS_SE"] == roa_cls]

            # 도로 폭 카테고리별로 그리기
            for width_cat in sorted(cls_gdf["width_category"].unique()):
                cat_gdf = cls_gdf[cls_gdf["width_category"] == width_cat]
                if len(cat_gdf) > 0:
                    # 대표 도로 폭으로 선 두께 결정
                    sample_bt = (
                        35
                        if width_cat == 3
                        else (20 if width_cat == 2 else (10 if width_cat == 1 else 5))
                    )
                    width = get_road_width(sample_bt)
                    cat_gdf.plot(
                        ax=ax, color=color, linewidth=width, alpha=ALPHA_WITH_CLASS
                    )
    elif has_roa_cls:
        # ROA_CLS_SE만 있는 경우
        for roa_cls in sorted(gdf["ROA_CLS_SE"].unique()):
            cls_gdf = gdf[gdf["ROA_CLS_SE"] == roa_cls]
            color = get_road_color(roa_cls)
            cls_gdf.plot(
                ax=ax, color=color, linewidth=ROAD_WIDTH_DEFAULT, alpha=ALPHA_WITH_CLASS
            )
    else:
        # 기본 시각화
        gdf.plot(
            ax=ax,
            color=NO_CLASS_COLOR,
            linewidth=ROAD_WIDTH_NO_CLASS,
            alpha=ALPHA_NO_CLASS,
        )


def create_road_legend_elements(
    gdf: gpd.GeoDataFrame, has_roa_cls: bool, has_road_bt: bool
) -> list[Line2D]:
    """도로 범례 요소 생성

    Args:
        gdf: 도로 GeoDataFrame
        has_roa_cls: ROA_CLS_SE 필드 존재 여부
        has_road_bt: ROAD_BT 필드 존재 여부

    Returns:
        범례 요소 리스트
    """
    legend_elements = []

    # 도로 등급 범례
    if has_roa_cls:
        for roa_cls in sorted(gdf["ROA_CLS_SE"].unique()):
            road_class = RoadClass.from_value(roa_cls)
            if road_class is not None:
                legend_elements.append(
                    Line2D(
                        [0],
                        [0],
                        color=road_class.color,
                        linewidth=0.1,  # 범례용 얇은 선
                        label=f"{road_class.korean_name} (등급 {road_class.value})",
                    )
                )

    # 도로 폭 범례
    if has_road_bt:
        # 구분선 추가
        if legend_elements:
            legend_elements.append(
                Line2D([0], [0], color="white", linewidth=0, label=" ")
            )

        legend_elements.extend(
            [
                Line2D(
                    [0],
                    [0],
                    color="black",
                    linewidth=ROAD_WIDTH_30M_PLUS,
                    label="도로 폭 30m 이상",
                ),
                Line2D(
                    [0],
                    [0],
                    color="black",
                    linewidth=ROAD_WIDTH_15_30M,
                    label="도로 폭 15-30m",
                ),
                Line2D(
                    [0],
                    [0],
                    color="black",
                    linewidth=ROAD_WIDTH_8_15M,
                    label="도로 폭 8-15m",
                ),
                Line2D(
                    [0],
                    [0],
                    color="black",
                    linewidth=ROAD_WIDTH_UNDER_8M,
                    label="도로 폭 8m 미만",
                ),
            ]
        )

    return legend_elements


def analyze_road_attributes(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """도로 속성 정보를 분석

    Args:
        gdf: 도로 데이터 GeoDataFrame

    Returns:
        분석 결과 딕셔너리
    """
    analysis: dict[str, Any] = {
        "total_segments": len(gdf),
        "has_roa_cls": "ROA_CLS_SE" in gdf.columns,
        "has_road_bt": "ROAD_BT" in gdf.columns,
    }

    # ROA_CLS_SE 분석
    if analysis["has_roa_cls"]:
        roa_cls_dist = {}
        for cls_val, count in gdf["ROA_CLS_SE"].value_counts().sort_index().items():
            percentage = (count / len(gdf)) * 100
            road_class = RoadClass.from_value(cls_val)
            cls_name = road_class.korean_name if road_class else f"기타({cls_val})"
            roa_cls_dist[cls_val] = {
                "name": cls_name,
                "count": count,
                "percentage": percentage,
            }
        analysis["road_class_distribution"] = roa_cls_dist

    # ROAD_BT 분석
    if analysis["has_road_bt"]:
        road_bt_stats = {
            "min": gdf["ROAD_BT"].min(),
            "max": gdf["ROAD_BT"].max(),
            "mean": gdf["ROAD_BT"].mean(),
            "median": gdf["ROAD_BT"].median(),
        }

        # 구간별 분포
        width_dist = {
            "30m_plus": (gdf["ROAD_BT"] >= ROAD_WIDTH_THRESHOLD_30M).sum(),
            "15_30m": (
                (gdf["ROAD_BT"] >= ROAD_WIDTH_THRESHOLD_15M)
                & (gdf["ROAD_BT"] < ROAD_WIDTH_THRESHOLD_30M)
            ).sum(),
            "8_15m": (
                (gdf["ROAD_BT"] >= ROAD_WIDTH_THRESHOLD_8M)
                & (gdf["ROAD_BT"] < ROAD_WIDTH_THRESHOLD_15M)
            ).sum(),
            "under_8m": (gdf["ROAD_BT"] < ROAD_WIDTH_THRESHOLD_8M).sum(),
        }

        analysis["road_width_stats"] = road_bt_stats
        analysis["road_width_distribution"] = width_dist

    return analysis


def extract_center_area(
    gdf: gpd.GeoDataFrame, buffer_km: float = 5.0
) -> gpd.GeoDataFrame:
    """중심부 영역 추출

    Args:
        gdf: 전체 도로 GeoDataFrame
        buffer_km: 중심점으로부터의 거리 (km)

    Returns:
        중심부 GeoDataFrame
    """
    if len(gdf) == 0:
        return gdf

    # 전체 경계 구하기
    bounds = gdf.total_bounds
    center_x = (bounds[0] + bounds[2]) / 2
    center_y = (bounds[1] + bounds[3]) / 2

    # 중심부 영역만 추출
    buffer_m = buffer_km * 1000  # km to meters
    return gdf.cx[
        center_x - buffer_m : center_x + buffer_m,
        center_y - buffer_m : center_y + buffer_m,
    ]


def print_road_analysis(analysis: dict[str, Any]) -> None:
    """도로 분석 결과 출력

    Args:
        analysis: 분석 결과 딕셔너리
    """
    print("\n=== 도로 속성 분석 ===")
    print(f"전체 도로 구간 수: {analysis['total_segments']}")

    # ROA_CLS_SE 분포
    if "road_class_distribution" in analysis:
        print("\n=== ROA_CLS_SE (도로 등급) 분포 ===")
        for cls_val, info in analysis["road_class_distribution"].items():
            print(
                f"  - {cls_val} ({info['name']}): "
                f"{info['count']}개 ({info['percentage']:.1f}%)"
            )

    # ROAD_BT 분포
    if "road_width_stats" in analysis:
        stats = analysis["road_width_stats"]
        print("\n=== ROAD_BT (도로 폭) 분포 ===")
        print(f"  - 최소값: {stats['min']:.1f}m")
        print(f"  - 최대값: {stats['max']:.1f}m")
        print(f"  - 평균: {stats['mean']:.1f}m")
        print(f"  - 중앙값: {stats['median']:.1f}m")

        dist = analysis["road_width_distribution"]
        total = analysis["total_segments"]
        print("\n  구간별 분포:")
        print(
            f"    - 30m 이상: {dist['30m_plus']}개 ({dist['30m_plus']/total*100:.1f}%)"
        )
        print(f"    - 15-30m: {dist['15_30m']}개 ({dist['15_30m']/total*100:.1f}%)")
        print(f"    - 8-15m: {dist['8_15m']}개 ({dist['8_15m']/total*100:.1f}%)")
        print(
            f"    - 8m 미만: {dist['under_8m']}개 ({dist['under_8m']/total*100:.1f}%)"
        )
