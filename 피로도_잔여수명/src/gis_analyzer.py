"""
GIS 데이터 분석 및 통계 처리를 위한 특화 모듈
shapefile의 FTR_IDN별 그룹화, 통계 계산, 도메인별 속성 처리
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


@dataclass
class FtrStatistics:
    """FTR_IDN별 통계 정보를 담는 데이터 클래스"""

    count: int
    total_length: float
    total_area: float
    geom_types: set[str]
    attrs: list[str]


@dataclass
class GeometryInfo:
    """Geometry 정보를 담는 데이터 클래스"""

    geom_type: str
    info_string: str
    length: float | None = None
    area: float | None = None


def load_shapefile(shapefile_path: Path, encoding: str = "euc-kr") -> gpd.GeoDataFrame:
    """
    shapefile을 로드하고 CRS 설정

    Args:
        shapefile_path: shapefile 경로
        encoding: 파일 인코딩

    Returns:
        GeoDataFrame
    """
    gdf = gpd.read_file(shapefile_path, encoding=encoding)

    # CRS 설정 (EPSG:5179 - Korea 2000 / Unified CS)
    if gdf.crs is None:
        gdf.set_crs("EPSG:5179", inplace=True)

    return gdf


def get_geometry_info(geometry: Any) -> GeometryInfo:
    """
    Geometry 객체의 정보를 추출

    Args:
        geometry: Shapely geometry 객체

    Returns:
        GeometryInfo 객체
    """
    if geometry is None:
        return GeometryInfo("No geometry", "No geometry")

    geom_type = geometry.geom_type
    info_string = f"{geom_type}"
    length = None
    area = None

    if geom_type == "Point":
        info_string += f"({geometry.x:.2f}, {geometry.y:.2f})"
    elif geom_type in ["LineString", "MultiLineString"]:
        length = geometry.length
        info_string += f"(길이: {length:.2f})"
    elif geom_type in ["Polygon", "MultiPolygon"]:
        area = geometry.area
        info_string += f"(면적: {area:.2f})"

    return GeometryInfo(geom_type, info_string, length, area)


def extract_ftr_attributes(row: pd.Series, columns: pd.Index) -> list[str]:
    """
    FTR_IDN의 주요 속성 추출

    Args:
        row: DataFrame의 행
        columns: DataFrame의 컬럼 목록

    Returns:
        속성 문자열 리스트
    """
    attrs = []

    # 도메인별 주요 속성 매핑
    attribute_mapping = {
        "FTR_CDE": "FTR_CDE",
        "FTC_CDE": "FTC_CDE",
        "SAA_CDE": "SAA_CDE",
        "MOP_CDE": "재질",
        "STD_DIP": "관경",
    }

    for col, label in attribute_mapping.items():
        if col in columns and pd.notna(row.get(col)):
            if col == label:
                attrs.append(f"{label}={row[col]}")
            else:
                attrs.append(f"{label}={row[col]}")

    return attrs


def format_attributes(
    row: pd.Series, exclude_cols: list[str], max_attrs: int = 5
) -> str:
    """
    행의 속성을 포맷팅

    Args:
        row: DataFrame의 행
        exclude_cols: 제외할 컬럼 리스트
        max_attrs: 표시할 최대 속성 개수

    Returns:
        포맷팅된 속성 문자열
    """
    attrs = {k: v for k, v in row.items() if k not in exclude_cols and pd.notna(v)}

    attrs_str = ", ".join([f"{k}={v}" for k, v in list(attrs.items())[:max_attrs]])

    if len(attrs) > max_attrs:
        attrs_str += "..."

    return attrs_str


def analyze_ftr_groups(gdf: gpd.GeoDataFrame) -> dict[str, FtrStatistics]:
    """
    FTR_IDN으로 그룹화하여 통계 정보 수집

    Args:
        gdf: GeoDataFrame

    Returns:
        FTR_IDN별 통계 정보 딕셔너리
    """
    if "FTR_IDN" not in gdf.columns:
        return {}

    grouped = gdf.groupby("FTR_IDN")
    ftr_stats = {}

    for ftr_idn, group in grouped:
        # 첫 번째 행에서 대표 속성 추출
        first_row = group.iloc[0]
        ftr_attrs = extract_ftr_attributes(first_row, group.columns)

        # 통계 정보 수집
        total_length = 0.0
        total_area = 0.0
        geom_types = []

        for _, row in group.iterrows():
            geom_info = get_geometry_info(row.geometry)
            geom_types.append(geom_info.geom_type)

            if geom_info.length:
                total_length += geom_info.length
            if geom_info.area:
                total_area += geom_info.area

        ftr_stats[str(ftr_idn)] = FtrStatistics(
            count=len(group),
            total_length=total_length,
            total_area=total_area,
            geom_types=set(geom_types),
            attrs=ftr_attrs,
        )

    return ftr_stats


def calculate_summary_statistics(ftr_stats: dict[str, FtrStatistics]) -> dict[str, Any]:
    """
    전체 통계 계산

    Args:
        ftr_stats: FTR_IDN별 통계 정보

    Returns:
        요약 통계 딕셔너리
    """
    if not ftr_stats:
        return {}

    all_counts = [stats.count for stats in ftr_stats.values()]
    all_lengths = [
        stats.total_length for stats in ftr_stats.values() if stats.total_length > 0
    ]
    all_areas = [
        stats.total_area for stats in ftr_stats.values() if stats.total_area > 0
    ]

    summary = {
        "total_ftr_idn_count": len(ftr_stats),
        "object_stats": {
            "mean": sum(all_counts) / len(all_counts) if all_counts else 0,
            "min": min(all_counts) if all_counts else 0,
            "max": max(all_counts) if all_counts else 0,
            "total": sum(all_counts) if all_counts else 0,
        },
    }

    if all_lengths:
        total_length = sum(all_lengths)
        summary["length_stats"] = {
            "mean": total_length / len(all_lengths),
            "min": min(all_lengths),
            "max": max(all_lengths),
            "total": total_length,
        }

    if all_areas:
        total_area = sum(all_areas)
        summary["area_stats"] = {
            "mean": total_area / len(all_areas),
            "min": min(all_areas),
            "max": max(all_areas),
            "total": total_area,
        }

    return summary


def group_by_ftr_cde(ftr_stats: dict[str, FtrStatistics]) -> dict[str, list[str]]:
    """
    FTR_CDE별로 FTR_IDN 그룹화

    Args:
        ftr_stats: FTR_IDN별 통계 정보

    Returns:
        FTR_CDE별 FTR_IDN 리스트
    """
    ftr_cde_groups: dict[str, list[str]] = {}

    for ftr_idn, stats in ftr_stats.items():
        for attr in stats.attrs:
            if attr.startswith("FTR_CDE="):
                ftr_cde = attr.split("=")[1]
                if ftr_cde not in ftr_cde_groups:
                    ftr_cde_groups[ftr_cde] = []
                ftr_cde_groups[ftr_cde].append(ftr_idn)
                break

    return ftr_cde_groups
