"""
GIS 파일 읽기 스크립트
data/raw 폴더 내의 모든 shapefile을 읽고 객체 정보를 출력
"""

from pathlib import Path

import geopandas as gpd

from src.common.config import RAW_DATA_DIR
from src.common.visualization_utils import print_statistics_summary
from src.gis_analyzer import (
    analyze_ftr_groups,
    calculate_summary_statistics,
    format_attributes,
    get_geometry_info,
    group_by_ftr_cde,
    load_shapefile,
)


def find_shapefiles(directory: Path) -> list[Path]:
    """
    지정된 디렉토리와 하위 디렉토리에서 모든 shapefile을 찾기

    Args:
        directory: 검색할 디렉토리 경로

    Returns:
        shapefile 경로 리스트
    """
    return list(directory.rglob("*.shp"))


def read_shapefile_info(shapefile_path: Path) -> tuple[str, int, str, str]:
    """
    shapefile을 읽고 기본 정보 추출

    Args:
        shapefile_path: shapefile 경로

    Returns:
        (파일명, 레코드수, geometry타입, CRS)
    """
    try:
        gdf = load_shapefile(shapefile_path)

        # 기본 정보 추출
        filename = shapefile_path.name
        record_count = len(gdf)

        # Geometry 타입
        if not gdf.empty and gdf.geometry.notna().any():
            geom_types = gdf.geometry.geom_type.unique()
            geom_type = ", ".join(geom_types)
        else:
            geom_type = "No geometry"

        # CRS 정보
        crs = str(gdf.crs) if gdf.crs else "No CRS (Set to EPSG:5179)"

        return filename, record_count, geom_type, crs

    except Exception as e:
        return shapefile_path.name, 0, "Error", str(e)


def print_records_without_ftr_idn(gdf: gpd.GeoDataFrame) -> None:
    """FTR_IDN이 없는 경우 일반 출력"""
    print("  FTR_IDN 컬럼이 없습니다. 일반 출력 모드로 전환합니다.")

    for idx, row in gdf.iterrows():
        geom_info = get_geometry_info(row.geometry)
        attrs_str = format_attributes(row, ["geometry"], max_attrs=5)
        print(f"  [{idx}] {geom_info.info_string} | {attrs_str}")


def print_ftr_group(ftr_idn: str, group: gpd.GeoDataFrame, attrs_str: str) -> None:
    """FTR_IDN 그룹 정보 출력"""
    print(f"\n  FTR_IDN: {ftr_idn} ({len(group)}개 객체){attrs_str}")

    for idx, row in group.iterrows():
        geom_info = get_geometry_info(row.geometry)
        attrs_str = format_attributes(row, ["geometry", "FTR_IDN"], max_attrs=5)
        print(f"    [{idx}] {geom_info.info_string} | {attrs_str}")


def print_all_records(shapefile_path: Path) -> None:
    """
    shapefile의 모든 레코드를 FTR_IDN별로 그룹화하여 출력

    Args:
        shapefile_path: shapefile 경로
    """
    try:
        gdf = load_shapefile(shapefile_path)

        # FTR_IDN이 없는 경우
        if "FTR_IDN" not in gdf.columns:
            print_records_without_ftr_idn(gdf)
            return

        # FTR_IDN별 통계 분석
        ftr_stats = analyze_ftr_groups(gdf)

        # 각 FTR_IDN 그룹 출력
        grouped = gdf.groupby("FTR_IDN")
        for ftr_idn, group in grouped:
            # 속성 문자열 생성
            attrs_list = ftr_stats[str(ftr_idn)].attrs
            attrs_str = " | " + ", ".join(attrs_list) if attrs_list else ""

            # 그룹 정보 출력
            print_ftr_group(str(ftr_idn), group, attrs_str)

        # 전체 통계 출력
        summary_stats = calculate_summary_statistics(ftr_stats)
        ftr_cde_groups = group_by_ftr_cde(ftr_stats)
        print_statistics_summary(summary_stats, ftr_cde_groups)

    except Exception as e:
        print(f"  오류: {e}")


def main() -> None:
    """메인 실행 함수"""
    print(f"GIS 파일 검색 시작: {RAW_DATA_DIR}")
    print("-" * 100)

    # 모든 shapefile 찾기
    shapefiles = find_shapefiles(RAW_DATA_DIR)

    if not shapefiles:
        print("shapefile을 찾을 수 없습니다.")
        return

    print(f"총 {len(shapefiles)}개의 shapefile 발견\n")

    # 각 shapefile의 모든 레코드 출력
    for shapefile in sorted(shapefiles):
        # 상대 경로 표시
        relative_path = shapefile.relative_to(RAW_DATA_DIR)

        # 파일 정보 출력
        filename, count, geom_type, crs = read_shapefile_info(shapefile)
        print(f"\n{relative_path}: {count}개 레코드, {geom_type}, CRS={crs}")

        # 모든 레코드 출력
        print_all_records(shapefile)


if __name__ == "__main__":
    main()
