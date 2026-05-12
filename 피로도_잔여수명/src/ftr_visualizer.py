"""
FTR_IDN별 시각화를 위한 특화 모듈
Shapefile의 FTR_IDN별 색상 할당 및 시각화 관련 비즈니스 로직
"""

from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.colors as mcolors
import pandas as pd


def load_shapefile_with_validation(shapefile_path: Path) -> gpd.GeoDataFrame:
    """Shapefile 로드 및 검증

    Args:
        shapefile_path: Shapefile 경로

    Returns:
        검증된 GeoDataFrame
    """
    gdf = gpd.read_file(shapefile_path, encoding="euc-kr")

    # CRS 설정
    if gdf.crs is None:
        gdf.set_crs("EPSG:5179", inplace=True)

    print(f"Shapefile 로드 완료: {len(gdf)}개 객체")

    # NULL geometry 제거
    null_geom = gdf[gdf.geometry.isnull()].shape[0]
    if null_geom > 0:
        print(f"경고: NULL geometry를 가진 객체 {null_geom}개 발견")
        gdf = gdf[~gdf.geometry.isnull()]

    # 빈 geometry 제거
    empty_geom = gdf[gdf.geometry.is_empty].shape[0]
    if empty_geom > 0:
        print(f"경고: 빈 geometry를 가진 객체 {empty_geom}개 발견")
        gdf = gdf[~gdf.geometry.is_empty]

    return gdf


def analyze_ftr_idn(gdf: gpd.GeoDataFrame) -> tuple[list[str], pd.Series]:
    """FTR_IDN 분석

    Args:
        gdf: GeoDataFrame

    Returns:
        (고유 FTR_IDN 리스트, FTR_IDN별 카운트)
    """
    if "FTR_IDN" not in gdf.columns:
        print("경고: FTR_IDN 컬럼이 없습니다. 전체를 하나의 그룹으로 처리합니다.")
        gdf["_group_id"] = "전체"
        return ["전체"], pd.Series({"전체": len(gdf)})

    # FTR_IDN별 그룹화
    unique_ids = gdf["FTR_IDN"].unique().tolist()
    gdf["_group_id"] = gdf["FTR_IDN"]
    print(f"총 {len(unique_ids)}개의 고유 FTR_IDN 발견")

    # FTR_IDN별 객체 수 확인
    ftr_idn_counts = gdf["FTR_IDN"].value_counts()
    multi_object_ids = ftr_idn_counts[ftr_idn_counts > 1]

    if len(multi_object_ids) > 0:
        print(f"복수 객체를 가진 FTR_IDN: {len(multi_object_ids)}개")
        print(f"최대 객체 수를 가진 FTR_IDN: {ftr_idn_counts.max()}개 객체")

    return unique_ids, ftr_idn_counts


def generate_distinct_colors(n: int, max_colors: int = 64) -> list[str]:
    """구별 가능한 n개의 색상 생성

    Args:
        n: 생성할 색상 개수
        max_colors: 색상 풀의 최대 크기

    Returns:
        색상 코드 리스트
    """
    # 기본 색상 팔레트 (구별하기 쉬운 색상들)
    base_colors = [
        "#FF0000",
        "#00FF00",
        "#0000FF",
        "#FFFF00",
        "#FF00FF",
        "#00FFFF",
        "#800000",
        "#008000",
        "#000080",
        "#808000",
        "#800080",
        "#008080",
        "#FFA500",
        "#A52A2A",
        "#DEB887",
        "#5F9EA0",
        "#7FFF00",
        "#D2691E",
        "#FF7F50",
        "#6495ED",
        "#DC143C",
        "#00FA9A",
        "#FFD700",
        "#ADFF2F",
        "#F0E68C",
        "#E6E6FA",
        "#DDA0DD",
        "#B0E0E6",
        "#98FB98",
        "#F5DEB3",
    ]

    color_pool = base_colors.copy()

    # 부족한 색상 생성 (HSV 색공간 활용)
    while len(color_pool) < max_colors:
        hue = (len(color_pool) - len(base_colors)) / (max_colors - len(base_colors))
        saturation = 0.8
        value = 0.8
        rgb = mcolors.hsv_to_rgb((hue, saturation, value))
        hex_color = mcolors.to_hex(tuple(rgb))
        color_pool.append(hex_color)

    # 실제 사용할 색상 선택
    actual_colors = min(n, max_colors)
    colors = color_pool[:actual_colors]

    # n이 max_colors보다 큰 경우 순환
    if n > max_colors:
        result = []
        for i in range(n):
            result.append(colors[i % max_colors])
        return result

    return colors


def plot_geometry_by_type(
    ax: Any, gdf: gpd.GeoDataFrame, color: str, zorder_base: int = 1
) -> int:
    """Geometry 타입별로 시각화

    Args:
        ax: matplotlib axes
        gdf: GeoDataFrame
        color: 색상
        zorder_base: 기본 z-order

    Returns:
        그려진 객체 수
    """
    objects_drawn = 0
    geom_types = gdf.geometry.geom_type.unique()

    for geom_type in geom_types:
        type_group = gdf[gdf.geometry.geom_type == geom_type]
        objects_drawn += len(type_group)

        try:
            if geom_type == "Point":
                # Point는 scatter로 표시
                x = type_group.geometry.x
                y = type_group.geometry.y
                ax.scatter(
                    x,
                    y,
                    color=color,
                    s=50,
                    alpha=0.8,
                    edgecolors="black",
                    linewidth=0.5,
                    zorder=zorder_base + 2,
                )

            elif geom_type in ["LineString", "MultiLineString"]:
                # Line은 선으로만 표시
                type_group.plot(
                    ax=ax, color=color, linewidth=2.0, alpha=0.8, zorder=zorder_base + 1
                )

            elif geom_type in ["Polygon", "MultiPolygon"]:
                # Polygon은 면과 경계선 표시
                type_group.plot(
                    ax=ax,
                    facecolor=color,
                    edgecolor="black",
                    linewidth=0.5,
                    alpha=0.7,
                    zorder=zorder_base,
                )

            else:
                # 기타 geometry 타입
                type_group.plot(
                    ax=ax, color=color, linewidth=1.5, alpha=0.8, zorder=zorder_base
                )

        except Exception as e:
            print(f"경고: {geom_type} 타입 그리기 실패 - {e}")

    return objects_drawn


def load_background_smlz(smlz_path: Path, ax: Any) -> gpd.GeoDataFrame | None:
    """SMLZ 배경 로드 및 그리기

    Args:
        smlz_path: SMLZ 파일 경로
        ax: matplotlib axes

    Returns:
        SMLZ GeoDataFrame (실패시 None)
    """
    if not smlz_path or not smlz_path.exists():
        return None

    try:
        smlz_gdf = gpd.read_file(smlz_path, encoding="euc-kr")

        # CRS 설정
        if smlz_gdf.crs is None:
            smlz_gdf.set_crs("EPSG:5179", inplace=True)

        # 배경으로 그리기
        smlz_gdf.plot(
            ax=ax,
            facecolor="lightgray",
            edgecolor="darkgray",
            linewidth=0.5,
            alpha=0.3,
            zorder=0,
        )

        print(f"SMLZ 배경 추가: {len(smlz_gdf)}개 영역")
        return smlz_gdf

    except Exception as e:
        print(f"SMLZ 로드 실패: {e}")
        return None


def calculate_plot_bounds(
    primary_gdf: gpd.GeoDataFrame,
    background_gdf: gpd.GeoDataFrame | None = None,
    margin_ratio: float = 0.05,
) -> tuple[float, float, float, float]:
    """플롯 경계 계산

    Args:
        primary_gdf: 주요 GeoDataFrame
        background_gdf: 배경 GeoDataFrame (선택적)
        margin_ratio: 여백 비율

    Returns:
        (minx, miny, maxx, maxy) with margin
    """
    # 배경 데이터가 있으면 그것을 기준으로
    if background_gdf is not None and len(background_gdf) > 0:
        bounds = background_gdf.total_bounds
    else:
        bounds = primary_gdf.total_bounds

    x_margin = (bounds[2] - bounds[0]) * margin_ratio
    y_margin = (bounds[3] - bounds[1]) * margin_ratio

    return (
        bounds[0] - x_margin,
        bounds[1] - y_margin,
        bounds[2] + x_margin,
        bounds[3] + y_margin,
    )
