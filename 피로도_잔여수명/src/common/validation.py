"""
데이터 검증 공통 유틸리티

이 모듈은 데이터 유효성 검사, 타입 체크, 범위 검증 등의 공통 기능을 제공합니다.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)


def validate_required_columns(
    df: pd.DataFrame, required_columns: list[str], raise_error: bool = True
) -> tuple[bool, list[str]]:
    """
    데이터프레임에 필수 컬럼이 있는지 확인

    Args:
        df: 검증할 데이터프레임
        required_columns: 필수 컬럼 목록
        raise_error: 컬럼이 없을 때 예외 발생 여부

    Returns:
        (검증 성공 여부, 누락된 컬럼 목록)

    Raises:
        ValueError: raise_error=True이고 필수 컬럼이 없을 때
    """
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        msg = f"Missing required columns: {missing_columns}"
        if raise_error:
            raise ValueError(msg)
        logger.warning(msg)
        return False, missing_columns

    return True, []


def validate_geometry_types(
    gdf: gpd.GeoDataFrame, allowed_types: list[str]
) -> tuple[bool, dict[str, int]]:
    """
    GeoDataFrame의 지오메트리 타입 검증

    Args:
        gdf: 검증할 GeoDataFrame
        allowed_types: 허용된 지오메트리 타입 목록

    Returns:
        (검증 성공 여부, 타입별 개수)
    """
    if gdf.empty:
        return True, {}

    # 지오메트리 타입별 개수 계산
    type_counts = gdf.geometry.geom_type.value_counts().to_dict()

    # 허용되지 않은 타입 확인
    invalid_types = [
        geom_type for geom_type in type_counts if geom_type not in allowed_types
    ]

    if invalid_types:
        logger.warning("Found invalid geometry types: %s", invalid_types)
        return False, type_counts

    return True, type_counts


def validate_crs(
    gdf: gpd.GeoDataFrame,
    expected_crs: str | None = None,
    convert_if_different: bool = False,
) -> gpd.GeoDataFrame:
    """
    좌표계(CRS) 검증 및 변환

    Args:
        gdf: 검증할 GeoDataFrame
        expected_crs: 기대하는 CRS (예: "EPSG:4326")
        convert_if_different: 다를 경우 변환 여부

    Returns:
        검증/변환된 GeoDataFrame
    """
    if gdf.crs is None:
        logger.warning("GeoDataFrame has no CRS")
        if expected_crs:
            logger.info("Setting CRS to %s", expected_crs)
            gdf = gdf.set_crs(expected_crs)
        return gdf

    current_crs = str(gdf.crs)
    logger.debug("Current CRS: %s", current_crs)

    if expected_crs and current_crs != expected_crs:
        if convert_if_different:
            logger.info("Converting CRS from %s to %s", current_crs, expected_crs)
            gdf = gdf.to_crs(expected_crs)
        else:
            logger.warning(
                "CRS mismatch: expected %s, got %s", expected_crs, current_crs
            )

    return gdf


def validate_numeric_range(
    series: pd.Series,
    min_value: float | None = None,
    max_value: float | None = None,
    column_name: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    숫자 값의 범위 검증

    Args:
        series: 검증할 시리즈
        min_value: 최소값
        max_value: 최대값
        column_name: 컬럼명 (로깅용)

    Returns:
        (검증 성공 여부, 통계 정보)
    """
    name = column_name or series.name or "series"
    stats = {
        "min": series.min(),
        "max": series.max(),
        "mean": series.mean(),
        "count": len(series),
        "null_count": series.isna().sum(),
    }

    valid = True

    if min_value is not None and stats["min"] < min_value:
        logger.warning(
            "%s: minimum value %s is below %s", name, stats["min"], min_value
        )
        valid = False

    if max_value is not None and stats["max"] > max_value:
        logger.warning(
            "%s: maximum value %s is above %s", name, stats["max"], max_value
        )
        valid = False

    if stats["null_count"] > 0:
        logger.info("%s: found %d null values", name, stats["null_count"])

    return valid, stats


def validate_date_format(
    series: pd.Series, date_format: str | None = None, convert: bool = True
) -> pd.Series:
    """
    날짜 형식 검증 및 변환

    Args:
        series: 검증할 시리즈
        date_format: 날짜 형식 (예: "%Y-%m-%d")
        convert: 변환 여부

    Returns:
        검증/변환된 시리즈
    """
    if not convert:
        return series

    try:
        if date_format:
            converted = pd.to_datetime(series, format=date_format, errors="coerce")
        else:
            converted = pd.to_datetime(series, errors="coerce")

        null_count = converted.isna().sum() - series.isna().sum()
        if null_count > 0:
            logger.warning("Failed to convert %d date values", null_count)

        return converted
    except Exception as e:
        logger.error("Date conversion failed: %s", e)
        return series


def remove_invalid_geometries(
    gdf: gpd.GeoDataFrame, remove_null: bool = True, remove_invalid: bool = True
) -> gpd.GeoDataFrame:
    """
    유효하지 않은 지오메트리 제거

    Args:
        gdf: 처리할 GeoDataFrame
        remove_null: NULL 지오메트리 제거 여부
        remove_invalid: 유효하지 않은 지오메트리 제거 여부

    Returns:
        정리된 GeoDataFrame
    """
    original_count = len(gdf)

    if remove_null:
        null_count = gdf.geometry.isna().sum()
        if null_count > 0:
            logger.info("Removing %d null geometries", null_count)
            gdf = gdf[gdf.geometry.notna()]

    if remove_invalid:
        invalid_mask = ~gdf.geometry.is_valid
        invalid_count = invalid_mask.sum()
        if invalid_count > 0:
            logger.info("Removing %d invalid geometries", invalid_count)
            gdf = gdf[gdf.geometry.is_valid]

    removed_count = original_count - len(gdf)
    if removed_count > 0:
        logger.info(
            "Removed %d geometries (%.1f%%)",
            removed_count,
            removed_count / original_count * 100,
        )

    return gdf


def validate_unique_values(
    series: pd.Series,
    expected_values: list[Any] | None = None,
    max_unique: int | None = None,
) -> tuple[bool, list[Any]]:
    """
    유니크 값 검증

    Args:
        series: 검증할 시리즈
        expected_values: 기대하는 값 목록
        max_unique: 최대 유니크 값 개수

    Returns:
        (검증 성공 여부, 유니크 값 목록)
    """
    unique_values = series.dropna().unique().tolist()
    valid = True

    if expected_values is not None:
        unexpected = [v for v in unique_values if v not in expected_values]
        if unexpected:
            logger.warning("Found unexpected values: %s...", unexpected[:10])
            valid = False

    if max_unique is not None and len(unique_values) > max_unique:
        logger.warning(
            "Too many unique values: %d > %d", len(unique_values), max_unique
        )
        valid = False

    return valid, unique_values
