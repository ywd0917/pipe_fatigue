#!/usr/bin/env python3
"""
main13c: 구역별 피로 손상 데이터 병합 스크립트

피로 손상 데이터(fatigue_pipe_lm.csv, fatigue_sply_ls.csv)와 파이프 shapefile을 결합하여,
각 파이프가 어느 구역(0470, 0480, 0490, 0520)에 속하는지 파악하고,
해당 구역별 데이터만 포함하는 통합 테이블을 생성합니다.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

# 프로젝트 루트 경로 설정
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.common.config import DATA_DIR, RAW_DATA_DIR, RESULTS_DIR

# 상수 정의
DEFAULT_EXPORT_DIR = RAW_DATA_DIR / "export_shp_20250704(0520)"
FATIGUE_DATA_DIR = RESULTS_DIR / "main56_calc_fatigure"  # 피로 데이터 디렉토리
OUTPUT_DIR = RESULTS_DIR / "main13c_zone_fatigue_merge"
OUTPUT_FILE = OUTPUT_DIR / "zone_fatigue_merged.csv"

# 구역 코드
SUBREGIONS = ["0243", "0461", "0470", "0480", "0490"]  # 소구역
MAIN_REGION = "0520"  # 중구역
ALL_REGIONS = [*SUBREGIONS, MAIN_REGION]


def load_fatigue_csv(file_path: Path, pipe_type: str) -> pd.DataFrame:
    """피로 손상 CSV 파일 로드

    Args:
        file_path: CSV 파일 경로
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)

    Returns:
        피로 손상 데이터 DataFrame
    """
    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
        print(f"✓ {pipe_type} 피로 손상 데이터 로드: {len(df)}개 파이프")
        return df
    except Exception as e:
        print(f"✗ {pipe_type} 피로 손상 데이터 로드 실패: {e}")
        raise


def load_pipe_shapefile(shp_path: Path, pipe_type: str) -> gpd.GeoDataFrame:
    """파이프 Shapefile 로드

    Args:
        shp_path: Shapefile 경로
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)

    Returns:
        파이프 GeoDataFrame
    """
    try:
        gdf = gpd.read_file(shp_path, encoding="cp949")

        # CRS 설정
        if gdf.crs is None:
            gdf.set_crs("EPSG:5179", inplace=True)
        elif gdf.crs != "EPSG:5179":
            gdf = gdf.to_crs("EPSG:5179")

        print(f"✓ {pipe_type} Shapefile 로드: {len(gdf)}개 파이프")
        return gdf
    except Exception as e:
        print(f"✗ {pipe_type} Shapefile 로드 실패: {e}")
        raise


def load_zone_boundaries(export_dir: Path) -> dict[str, gpd.GeoDataFrame]:
    """구역 경계 Shapefile 로드

    Args:
        export_dir: export 디렉토리 경로

    Returns:
        {구역코드: 경계 GeoDataFrame} 딕셔너리
    """
    boundaries = {}

    # 소구역 경계 로드 (WEA_SMLZ_AS.shp)
    smlz_path = export_dir / "WEA_SMLZ_AS.shp"
    if smlz_path.exists():
        try:
            smlz_gdf = gpd.read_file(smlz_path, encoding="cp949")
            if smlz_gdf.crs is None:
                smlz_gdf.set_crs("EPSG:5179", inplace=True)

            # 각 소구역 추출
            for region in SUBREGIONS:
                # SMZ_NUM 필드에서 매칭 ("0470", "0480", "0490")
                region_gdf = smlz_gdf[smlz_gdf["SMZ_NUM"] == region].copy()
                if not region_gdf.empty:
                    boundaries[region] = region_gdf
                    print(f"✓ 소구역 {region} 경계 로드")
        except Exception as e:
            print(f"⚠ 소구역 경계 로드 실패: {e}")

    # 중구역 경계 로드 (WEA_MDLZ_AS.shp)
    mdlz_path = export_dir / "WEA_MDLZ_AS.shp"
    if mdlz_path.exists():
        try:
            mdlz_gdf = gpd.read_file(mdlz_path, encoding="cp949")
            if mdlz_gdf.crs is None:
                mdlz_gdf.set_crs("EPSG:5179", inplace=True)

            # 0520 중구역 전체를 하나의 경계로 사용
            if not mdlz_gdf.empty:
                boundaries[MAIN_REGION] = mdlz_gdf
                print(f"✓ 중구역 {MAIN_REGION} 경계 로드")
        except Exception as e:
            print(f"⚠ 중구역 경계 로드 실패: {e}")

    return boundaries


def determine_zone(pipe_geometry: Any, boundaries: dict[str, gpd.GeoDataFrame]) -> str:
    """파이프가 속한 구역 판별

    Args:
        pipe_geometry: 파이프 geometry (LineString)
        boundaries: 구역 경계 딕셔너리

    Returns:
        구역 코드 (0470, 0480, 0490, 0520, UNKNOWN)
    """
    # 파이프의 대표점 계산
    if hasattr(pipe_geometry, "representative_point"):
        point = pipe_geometry.representative_point()
    elif hasattr(pipe_geometry, "centroid"):
        point = pipe_geometry.centroid
    else:
        return "UNKNOWN"

    # 소구역 확인 (우선순위)
    for region in SUBREGIONS:
        if region in boundaries:
            for _, boundary in boundaries[region].iterrows():
                if boundary.geometry.contains(point):
                    return region

    # 중구역 확인
    if MAIN_REGION in boundaries:
        for _, boundary in boundaries[MAIN_REGION].iterrows():
            if boundary.geometry.contains(point):
                return MAIN_REGION

    return "UNKNOWN"


def merge_fatigue_and_shapefile(
    fatigue_df: pd.DataFrame,
    pipe_gdf: gpd.GeoDataFrame,
    boundaries: dict[str, gpd.GeoDataFrame],
    pipe_type: str,
) -> pd.DataFrame:
    """피로 손상 데이터와 Shapefile 병합 및 구역 판별

    Args:
        fatigue_df: 피로 손상 DataFrame
        pipe_gdf: 파이프 GeoDataFrame
        boundaries: 구역 경계 딕셔너리
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)

    Returns:
        구역이 판별된 병합 DataFrame
    """
    # FTR_IDN 기준으로 병합
    merged = pipe_gdf[["FTR_IDN", "geometry"]].merge(
        fatigue_df, on="FTR_IDN", how="inner"
    )

    print(f"  - {pipe_type}: {len(merged)}개 파이프 매칭 (전체 {len(fatigue_df)}개 중)")

    # 각 파이프의 구역 판별
    zones = []
    zone_counts = dict.fromkeys([*ALL_REGIONS, "UNKNOWN"], 0)

    for idx, row in merged.iterrows():
        zone = determine_zone(row.geometry, boundaries)
        zones.append(zone)
        zone_counts[zone] += 1

    merged["zone"] = zones
    merged["DATA_SRC"] = pipe_type

    # 통계 출력
    print("  - 구역별 분포:")
    for zone, count in zone_counts.items():
        if count > 0:
            print(f"    • {zone}: {count}개")

    # geometry 컬럼 제거 (CSV 저장용)
    return merged.drop(columns=["geometry"])


def filter_zone_columns(df: pd.DataFrame) -> pd.DataFrame:
    """구역별 컬럼 필터링 및 이름 변경

    각 행의 zone에 해당하는 컬럼만 유지하고 prefix 제거
    원본 CSV의 컬럼 순서를 최대한 유지

    Args:
        df: 병합된 DataFrame

    Returns:
        필터링된 DataFrame
    """
    # 원본 컬럼 순서를 기준으로 한 기본 컬럼 정의
    # 이 순서는 fatigue_sply_ls.csv의 원본 순서를 기반으로 함
    expected_basic_order = [
        "DATA_SRC", "zone", "FTR_IDN", "FTR_CDE", "HJD_CDE", "SHT_NUM", "MNG_CDE",
        "MOP_CDE", "STD_DIP", "BYC_LEN", "JHT_CDE", "LOW_DEP", "HGH_DEP", "CNT_NUM",
        "SYS_CHK", "PIP_LBL", "IQT_CDE", "GIS_IDN", "FTC_CDE", "CLS_YMD", "MET_IDN",
        "GU_CDE", "SMZ_NUM", "MDZ_NUM", "LGZ_NUM", "AVG_DEP", "WTP_CDE", "PIP_TYPE",
        "IST_YMD", "FNS_YMD", "BEG_YMD", "DAYS_SINCE_BEG", "YEARS_SINCE_BEG",
        "design_pressure", "thickness", "K_material", "fatigue_limit", "K_diameter",
        "K_age", "K_soil", "K_traffic", "K_vibration", "hoop_stress", "K_stress",
        "K_repair", "K_total"
    ]
    
    # 실제 존재하는 기본 컬럼들과 zone 컬럼들 분류
    basic_columns: list[str] = []
    zone_column_groups: dict[str, list[str]] = {zone: [] for zone in ALL_REGIONS}

    for col in df.columns:
        # zone prefix 확인
        has_zone_prefix = False
        for zone in ALL_REGIONS:
            if col.startswith(f"{zone}_"):
                zone_column_groups[zone].append(col)
                has_zone_prefix = True
                break

        # zone prefix가 없으면 기본 컬럼
        if not has_zone_prefix:
            basic_columns.append(col)

    # 기본 컬럼들을 예상 순서에 맞춰 정렬
    ordered_basic_columns = []
    for col in expected_basic_order:
        if col in basic_columns:
            ordered_basic_columns.append(col)
    
    # 예상 순서에 없는 추가 컬럼들을 끝에 추가
    for col in basic_columns:
        if col not in ordered_basic_columns:
            ordered_basic_columns.append(col)

    # 각 zone별로 처리
    result_dfs = []

    for zone in df["zone"].unique():
        if zone == "UNKNOWN":
            # UNKNOWN은 기본 컬럼만 유지
            zone_df = df[df["zone"] == zone][ordered_basic_columns].copy()
        else:
            # 해당 zone의 컬럼 선택
            zone_cols = zone_column_groups.get(zone, [])
            
            # zone 컬럼들은 원본 DataFrame 순서를 유지 (sorting 제거)
            selected_cols = ordered_basic_columns + zone_cols
            zone_df = df[df["zone"] == zone][selected_cols].copy()

            # prefix 제거
            rename_dict = {col: col.replace(f"{zone}_", "") for col in zone_cols}
            zone_df = zone_df.rename(columns=rename_dict)

        result_dfs.append(zone_df)

    # 모든 zone 데이터 결합
    result = pd.concat(result_dfs, ignore_index=True)

    return result


def main() -> None:
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="구역별 피로 손상 데이터 병합")
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Export shapefile 디렉토리 경로",
    )
    parser.add_argument(
        "--output", type=Path, default=OUTPUT_FILE, help="출력 CSV 파일 경로"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("main13c: 구역별 피로 손상 데이터 병합")
    print("=" * 60)

    # 출력 디렉토리 생성
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # 1. 피로 손상 데이터 로드
    print("\n1. 피로 손상 데이터 로드")
    fatigue_pipe_lm = load_fatigue_csv(
        FATIGUE_DATA_DIR / "fatigue_pipe_lm.csv", "PIPE_LM"
    )
    fatigue_sply_ls = load_fatigue_csv(
        FATIGUE_DATA_DIR / "fatigue_sply_ls.csv", "SPLY_LS"
    )

    # 2. 파이프 Shapefile 로드
    print("\n2. 파이프 Shapefile 로드")
    pipe_lm_gdf = load_pipe_shapefile(args.export_dir / "V_WTL_PIPE_LM.shp", "PIPE_LM")
    sply_ls_gdf = load_pipe_shapefile(args.export_dir / "V_WTL_SPLY_LS.shp", "SPLY_LS")

    # 3. 구역 경계 로드
    print("\n3. 구역 경계 로드")
    boundaries = load_zone_boundaries(args.export_dir)

    if not boundaries:
        print("✗ 구역 경계를 로드할 수 없습니다.")
        sys.exit(1)

    # 4. 데이터 병합 및 구역 판별
    print("\n4. 데이터 병합 및 구역 판별")
    merged_pipe_lm = merge_fatigue_and_shapefile(
        fatigue_pipe_lm, pipe_lm_gdf, boundaries, "PIPE_LM"
    )
    merged_sply_ls = merge_fatigue_and_shapefile(
        fatigue_sply_ls, sply_ls_gdf, boundaries, "SPLY_LS"
    )

    # 5. 두 테이블 병합
    print("\n5. PIPE_LM과 SPLY_LS 데이터 통합")
    combined = pd.concat([merged_pipe_lm, merged_sply_ls], ignore_index=True)
    print(f"✓ 전체 {len(combined)}개 파이프 통합")

    # 6. 구역별 컬럼 필터링
    print("\n6. 구역별 컬럼 필터링 및 정리")
    final_df = filter_zone_columns(combined)

    # 7. 결과 저장
    print("\n7. 결과 저장")
    # FTR_IDN을 int로 변환 (CSV에 소수점 없이 저장)
    final_df["FTR_IDN"] = final_df["FTR_IDN"].astype(float).astype(int)
    final_df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"✓ 결과 저장: {args.output}")

    # 최종 통계
    print("\n" + "=" * 60)
    print("최종 통계:")
    print(f"- 전체 파이프 수: {len(final_df)}")
    print("- DATA_SRC별:")
    for src, count in final_df["DATA_SRC"].value_counts().items():
        print(f"  • {src}: {count}개")
    print("- zone별:")
    for zone, count in final_df["zone"].value_counts().items():
        print(f"  • {zone}: {count}개")
    print("=" * 60)
    print("✓ 구역별 피로 손상 데이터 병합 완료")


if __name__ == "__main__":
    main()
