"""
하위 지역별 재작업 위치와 파이프 위험 요인 상관관계 분석

클러스터링 분석:
- 10m 반경으로 재작업 위치를 클러스터링하여 repair_count 생성
- 핵심 분석: repair_count(재작업 횟수)와 K-factors의 상관관계
- 지역별로 repair_count >= 4인 클러스터 비교

분석 대상:
- 0470, 0480, 0490 하위 지역별 개별 분석
- K-factors: K_age, K_soil, K_traffic, hoop_stress, K_stress, K_total, STD_DIP
- D_final: 피로 손상 지수 (지역별 컬럼 사용)
- 지역 간 비교 및 통합 보고서 생성
"""

import argparse
import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from shapely.geometry import Point

from src.common.config import (
    FATIGUE_PIPE_LM_CSV,
    FATIGUE_SPLY_LS_CSV,
    RAW_DATA_DIR,
    RESULTS_DIR,
)
from src.common.korean_font_utils import setup_korean_font
from src.common.shapefile_loader import (
    ShapefileLoader,
    get_smlz_shapefile_path,
    get_subregion_label,
)
from src.common.shapefile_loader import (
    get_subregion_boundary as get_subregion_boundary_from_loader,
)
from src.common.spatial_utils import convert_to_epsg5179
from src.main14_common.clustering import create_repair_clusters, match_clusters_to_pipes
from src.main14_common.constants import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    DEFAULT_DISTANCE,
    FACTOR_NAMES,
    OPTIONAL_K_FACTORS,
    P_VALUE_THRESHOLD,
    PARENT_REGION,
)
from src.main14_common.correlation_analysis import analyze_correlation
from src.main14_common.data_loader import (
    load_fatigue_csv,
    load_repair_csv_files,
)

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 상수 정의
DISTANCE_THRESHOLD_METERS = DEFAULT_DISTANCE  # 파이프 매칭 거리 임계값 (미터)
MIN_REPAIRS_FOR_FREQUENT = 4  # 빈번한 재작업 판단 기준
CLUSTER_DISTANCE_METERS = 10.0  # 클러스터링 거리 임계값 (미터)

# 분석 대상 하위 지역
VALID_SUBREGIONS = ["0243", "0461", "0470", "0480", "0490"]

# 분석 요인 리스트 - load_pipe_factors_for_subregion에서 설정됨
ANALYSIS_FACTORS = []  # 초기화, 실행 시 업데이트


def validate_region_code(region_code: str) -> None:
    """지역 코드 유효성 검증"""
    if region_code not in VALID_SUBREGIONS:
        raise ValueError(
            f"유효하지 않은 지역 코드: {region_code}. 유효한 코드: {', '.join(VALID_SUBREGIONS)}"
        )


def get_subregion_boundary(region_code: str) -> gpd.GeoDataFrame:
    """WEA_SMLZ_AS.shp에서 하위 지역 경계 추출"""
    validate_region_code(region_code)
    # SMLZ shapefile 경로 가져오기
    smlz_path = get_smlz_shapefile_path(RAW_DATA_DIR, PARENT_REGION)
    if not smlz_path:
        raise FileNotFoundError(
            f"{PARENT_REGION} 지역의 SMLZ shapefile을 찾을 수 없습니다."
        )

    # 하위 지역 라벨 가져오기
    label = get_subregion_label(region_code)

    # 경계 추출
    boundary = get_subregion_boundary_from_loader(smlz_path, label)
    if boundary is None:
        raise ValueError(f"{region_code} 지역의 경계를 찾을 수 없습니다.")

    return boundary


def load_repair_data_for_subregion(region_code: str) -> gpd.GeoDataFrame:
    """하위 지역 복구 데이터 로드 - 부모 지역 데이터에서 경계 내 필터링, EPSG:5179 유지"""
    validate_region_code(region_code)
    print(f"\n=== {region_code} 지역 복구 작업 데이터 로드 중 ===")

    # 공통 함수 사용하여 CSV 파일 로드
    required_columns = ["작업타입", "작업종료일", "주소", "위도", "경도"]
    df_repairs = load_repair_csv_files(required_columns)

    # 결측값 제거
    df_repairs = df_repairs.dropna(subset=["위도", "경도"])

    # WGS84 좌표를 GeoDataFrame으로 변환 후 EPSG:5179로 변환
    geometry = [
        Point(lon, lat)
        for lon, lat in zip(df_repairs["경도"], df_repairs["위도"], strict=False)
    ]
    gdf_repairs = gpd.GeoDataFrame(df_repairs, geometry=geometry, crs="EPSG:4326")
    gdf_repairs = convert_to_epsg5179(gdf_repairs)

    # 하위 지역 경계 가져오기
    boundary = get_subregion_boundary(region_code)

    # 경계 내 데이터만 필터링
    gdf_filtered = gdf_repairs[gdf_repairs.within(boundary.geometry.iloc[0])]

    print(
        f"{region_code} 지역 복구 작업: {len(gdf_filtered)}개 (전체 {len(gdf_repairs)}개 중)"
    )
    print("좌표계: EPSG:5179")

    return gdf_filtered


def load_pipe_factors_for_subregion(region_code: str) -> gpd.GeoDataFrame:
    """하위 지역 파이프 K-factors 및 D_final 데이터 로드 - LineString 유지"""
    validate_region_code(region_code)
    print(f"\n=== {region_code} 지역 파이프 위험 요인 데이터 로드 중 ===")

    # 공통 함수 사용하여 CSV 파일 로드
    df_pipe_lm, df_sply_ls, has_k_repair = load_fatigue_csv(
        FATIGUE_PIPE_LM_CSV, FATIGUE_SPLY_LS_CSV
    )

    # 기본 K-factors는 항상 존재
    k_factors = BASE_K_FACTORS.copy()
    if has_k_repair:
        k_factors.extend(OPTIONAL_K_FACTORS)

    # 필요한 컬럼 선택 (K-factors + 지역별 D_final)
    # D_final은 '0470_D_final', '0480_D_final', '0490_D_final' 컬럼명으로 저장
    d_final_col = f"{region_code}_D_final"
    cols_needed = ["FTR_IDN", *k_factors, d_final_col]

    # 컬럼 존재 확인
    if d_final_col not in df_pipe_lm.columns:
        raise ValueError(f"{d_final_col} 컬럼이 PIPE_LM CSV에 없습니다.")
    if d_final_col not in df_sply_ls.columns:
        raise ValueError(f"{d_final_col} 컬럼이 SPLY_LS CSV에 없습니다.")

    df_pipe_lm = df_pipe_lm[cols_needed].copy()
    df_sply_ls = df_sply_ls[cols_needed].copy()

    # D_final 컬럼명 변경
    df_pipe_lm.rename(columns={d_final_col: DAMAGE_FACTOR}, inplace=True)
    df_sply_ls.rename(columns={d_final_col: DAMAGE_FACTOR}, inplace=True)

    # 파이프 타입 추가
    df_pipe_lm["pipe_type"] = "PIPE_LM"
    df_sply_ls["pipe_type"] = "SPLY_LS"

    # 전역 ANALYSIS_FACTORS 업데이트
    global ANALYSIS_FACTORS
    # 기본 순서: BASE_K_FACTORS + D_final + OPTIONAL_K_FACTORS (있는 경우)
    ANALYSIS_FACTORS = [*BASE_K_FACTORS, DAMAGE_FACTOR]
    if has_k_repair:
        ANALYSIS_FACTORS.extend(OPTIONAL_K_FACTORS)

    # ShapefileLoader를 사용하여 geometry 정보 로드
    loader = ShapefileLoader(RAW_DATA_DIR, verbose=False)

    # PIPE_LM과 SPLY_LS shapefile 로드 (0520 지역)
    gdf_pipe_lm = loader.load_pipe_shapefile(PARENT_REGION, "PIPE_LM")
    gdf_sply_ls = loader.load_pipe_shapefile(PARENT_REGION, "SPLY_LS")

    if gdf_pipe_lm is None or gdf_sply_ls is None:
        raise FileNotFoundError(
            f"{region_code} 지역의 파이프 shapefile을 찾을 수 없습니다."
        )

    # 하위 지역 경계 가져오기
    boundary = get_subregion_boundary(region_code)

    # FTR_IDN을 기준으로 K-factors 데이터와 매칭 + 경계 내 필터링 (LineString 유지)
    pipe_lm_factors = []
    for ftr_idn in df_pipe_lm["FTR_IDN"].unique():
        segments = gdf_pipe_lm[gdf_pipe_lm["FTR_IDN"] == ftr_idn]
        if not segments.empty:
            # 경계 내 세그먼트만 선택
            segments_in_boundary = segments[segments.within(boundary.geometry.iloc[0])]
            if not segments_in_boundary.empty:
                # CSV 데이터에서 매칭되는 K-factors 찾기
                factors_match = df_pipe_lm[df_pipe_lm["FTR_IDN"] == ftr_idn]
                if not factors_match.empty:
                    factors = factors_match.iloc[0].to_dict()
                    # 모든 세그먼트의 geometry를 하나로 합치기 (MultiLineString 또는 LineString)
                    from shapely.ops import unary_union

                    combined_geom = unary_union(segments_in_boundary.geometry.tolist())
                    factors["geometry"] = (
                        combined_geom  # LineString/MultiLineString 유지
                    )
                    factors["segment_id"] = ftr_idn
                    pipe_lm_factors.append(factors)

    sply_ls_factors = []
    for ftr_idn in df_sply_ls["FTR_IDN"].unique():
        segments = gdf_sply_ls[gdf_sply_ls["FTR_IDN"] == ftr_idn]
        if not segments.empty:
            # 경계 내 세그먼트만 선택
            segments_in_boundary = segments[segments.within(boundary.geometry.iloc[0])]
            if not segments_in_boundary.empty:
                # CSV 데이터에서 매칭되는 K-factors 찾기
                factors_match = df_sply_ls[df_sply_ls["FTR_IDN"] == ftr_idn]
                if not factors_match.empty:
                    factors = factors_match.iloc[0].to_dict()
                    # 모든 세그먼트의 geometry를 하나로 합치기 (MultiLineString 또는 LineString)
                    from shapely.ops import unary_union

                    combined_geom = unary_union(segments_in_boundary.geometry.tolist())
                    factors["geometry"] = (
                        combined_geom  # LineString/MultiLineString 유지
                    )
                    factors["segment_id"] = ftr_idn
                    sply_ls_factors.append(factors)

    # GeoDataFrame 생성
    if pipe_lm_factors:
        gdf_pipe_lm_factors = gpd.GeoDataFrame(pipe_lm_factors, crs="EPSG:5179")
    else:
        gdf_pipe_lm_factors = gpd.GeoDataFrame(
            columns=["FTR_IDN", *ANALYSIS_FACTORS, "pipe_type", "geometry"],
            crs="EPSG:5179",
        )

    if sply_ls_factors:
        gdf_sply_ls_factors = gpd.GeoDataFrame(sply_ls_factors, crs="EPSG:5179")
    else:
        gdf_sply_ls_factors = gpd.GeoDataFrame(
            columns=["FTR_IDN", *ANALYSIS_FACTORS, "pipe_type", "geometry"],
            crs="EPSG:5179",
        )

    # 통합
    gdf_all_pipes = pd.concat(
        [gdf_pipe_lm_factors, gdf_sply_ls_factors], ignore_index=True
    )

    # 유효한 데이터만 필터링 (D_final이 0보다 큰 경우)
    if len(gdf_all_pipes) > 0:
        gdf_all_pipes = gdf_all_pipes[gdf_all_pipes["D_final"] > 0]

    print(f"{region_code} 지역 PIPE_LM: {len(gdf_pipe_lm_factors)}개 세그먼트")
    print(f"{region_code} 지역 SPLY_LS: {len(gdf_sply_ls_factors)}개 세그먼트")
    print(f"유효한 파이프 세그먼트: {len(gdf_all_pipes)}개")

    # 분석 요인 통계 출력
    print(f"\n=== {region_code} 지역 분석 요인 범위 ===")
    for factor in ANALYSIS_FACTORS:
        if factor in gdf_all_pipes.columns:
            factor_min = gdf_all_pipes[factor].min()
            factor_max = gdf_all_pipes[factor].max()
            factor_mean = gdf_all_pipes[factor].mean()

            if factor == "D_final":
                print(
                    f"{factor}: {factor_min:.6f} ~ {factor_max:.6f} (평균: {factor_mean:.6f})"
                )
            else:
                print(
                    f"{factor}: {factor_min:.4f} ~ {factor_max:.4f} (평균: {factor_mean:.4f})"
                )

    return gdf_all_pipes


def load_pipe_factors_data() -> pd.DataFrame:
    """PIPE_LM과 SPLY_LS의 K-factors 및 D_final 데이터 로드 및 통합"""
    print("\n=== 파이프 위험 요인 데이터 로드 중 ===")

    # CSV 파일 존재 확인
    pipe_lm_csv = FATIGUE_PIPE_LM_CSV
    sply_ls_csv = FATIGUE_SPLY_LS_CSV

    missing_files = []
    found_files = []

    if pipe_lm_csv.exists():
        found_files.append(pipe_lm_csv)
    else:
        missing_files.append(pipe_lm_csv)

    if sply_ls_csv.exists():
        found_files.append(sply_ls_csv)
    else:
        missing_files.append(sply_ls_csv)

    # 파일 상태 출력
    if found_files:
        print("\n발견된 파일:")
        for file_path in found_files:
            print(f"  ✓ {file_path}")

    if missing_files:
        print("\n" + "=" * 70)
        print("오류: K-factors 데이터 파일을 찾을 수 없습니다!")
        print("=" * 70)
        print("\n다음 파일들이 필요합니다:")
        for file_path in missing_files:
            print(f"  ✗ {file_path}")
        print("\n해결 방법:")
        print("1. 위 경로에 CSV 파일이 있는지 확인하세요.")
        print("2. 파일이 없다면 K-factors 계산 스크립트를 먼저 실행하세요.")
        print("   예: python src/main13a_calculate_k_repair.py")
        print("   또는: python src/calculate_fatigue_factors.py")
        print("3. 파일 이름이 정확한지 확인하세요:")
        print("   - results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv")
        print("   - results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv")
        print("=" * 70)
        sys.exit(1)

    # CSV 파일에서 데이터 로드
    try:
        df_pipe_lm = pd.read_csv(pipe_lm_csv)
        print(f"PIPE_LM 데이터 로드 성공: {len(df_pipe_lm)}개 레코드")
    except Exception as e:
        print("\n오류: PIPE_LM CSV 파일 읽기 실패")
        print(f"  파일: {pipe_lm_csv}")
        print(f"  에러: {e!s}")
        sys.exit(1)

    try:
        df_sply_ls = pd.read_csv(sply_ls_csv)
        print(f"SPLY_LS 데이터 로드 성공: {len(df_sply_ls)}개 레코드")
    except Exception as e:
        print("\n오류: SPLY_LS CSV 파일 읽기 실패")
        print(f"  파일: {sply_ls_csv}")
        print(f"  에러: {e!s}")
        sys.exit(1)

    # 기본 K-factors는 항상 존재
    k_factors = BASE_K_FACTORS.copy()

    # K_repair 컬럼 존재 여부 확인 (선택적)
    has_k_repair = "K_repair" in df_pipe_lm.columns and "K_repair" in df_sply_ls.columns
    if has_k_repair:
        k_factors.extend(OPTIONAL_K_FACTORS)
        print("K_repair 컬럼을 포함하여 분석합니다.")
    else:
        print("주의: K_repair 컬럼이 없어 분석에서 제외됩니다.")

    # 필요한 컬럼 선택
    # D_final은 '0520_D_final' 컬럼명으로 저장되어 있음
    cols_needed = ["FTR_IDN", *k_factors, "0520_D_final"]
    df_pipe_lm = df_pipe_lm[cols_needed].copy()
    df_sply_ls = df_sply_ls[cols_needed].copy()

    # D_final 컬럼명 변경
    df_pipe_lm.rename(columns={"0520_D_final": DAMAGE_FACTOR}, inplace=True)
    df_sply_ls.rename(columns={"0520_D_final": DAMAGE_FACTOR}, inplace=True)

    # 파이프 타입 추가
    df_pipe_lm["pipe_type"] = "PIPE_LM"
    df_sply_ls["pipe_type"] = "SPLY_LS"

    print(f"PIPE_LM: {len(df_pipe_lm)}개 레코드")
    print(f"SPLY_LS: {len(df_sply_ls)}개 레코드")

    # 전역 ANALYSIS_FACTORS 업데이트 (이 함수에서도 필요)
    global ANALYSIS_FACTORS
    # 기본 순서: BASE_K_FACTORS + D_final + OPTIONAL_K_FACTORS (있는 경우)
    ANALYSIS_FACTORS = [*BASE_K_FACTORS, DAMAGE_FACTOR]
    if has_k_repair:
        ANALYSIS_FACTORS.extend(OPTIONAL_K_FACTORS)

    # 분석 요인 통계 출력
    print("\n=== 분석 요인 범위 ===")
    for factor in ANALYSIS_FACTORS:
        if factor in df_pipe_lm.columns and factor in df_sply_ls.columns:
            pipe_min = df_pipe_lm[factor].min()
            pipe_max = df_pipe_lm[factor].max()
            sply_min = df_sply_ls[factor].min()
            sply_max = df_sply_ls[factor].max()

            # D_final은 다른 형식으로 출력
            if factor == "D_final":
                print(
                    f"{factor}: {min(pipe_min, sply_min):.6f} ~ {max(pipe_max, sply_max):.6f}"
                )
            else:
                print(
                    f"{factor}: {min(pipe_min, sply_min):.4f} ~ {max(pipe_max, sply_max):.4f}"
                )

    # ShapefileLoader를 사용하여 geometry 정보 로드
    loader = ShapefileLoader(RAW_DATA_DIR, verbose=False)

    # PIPE_LM과 SPLY_LS shapefile 로드 (0520 지역)
    print("\nShapefile 로드 중...")
    gdf_pipe_lm = loader.load_pipe_shapefile(PARENT_REGION, "PIPE_LM")
    gdf_sply_ls = loader.load_pipe_shapefile(PARENT_REGION, "SPLY_LS")

    missing_shapefiles = []
    if gdf_pipe_lm is None:
        missing_shapefiles.append(
            RAW_DATA_DIR / f"export_shp_({PARENT_REGION})" / "V_WTL_PIPE_LM.shp"
        )
    else:
        print(f"  ✓ PIPE_LM shapefile 로드 성공: {len(gdf_pipe_lm)}개 세그먼트")

    if gdf_sply_ls is None:
        missing_shapefiles.append(
            RAW_DATA_DIR / f"export_shp_({PARENT_REGION})" / "V_WTL_SPLY_LS.shp"
        )
    else:
        print(f"  ✓ SPLY_LS shapefile 로드 성공: {len(gdf_sply_ls)}개 세그먼트")

    if missing_shapefiles:
        print("\n" + "=" * 70)
        print("오류: 파이프 shapefile을 찾을 수 없습니다!")
        print("=" * 70)
        print("\n다음 파일들이 필요합니다:")
        for file_path in missing_shapefiles:
            print(f"  ✗ {file_path}")
        print("\n해결 방법:")
        print(f"1. {RAW_DATA_DIR} 디렉토리를 확인하세요.")
        print(f"2. export_shp_({PARENT_REGION}) 폴더가 있는지 확인하세요.")
        print("3. V_WTL_PIPE_LM.shp 및 V_WTL_SPLY_LS.shp 파일이 있는지 확인하세요.")
        print("4. shapefile 관련 파일들(.shx, .dbf, .prj)이 모두 있는지 확인하세요.")
        print("=" * 70)
        sys.exit(1)

    # FTR_IDN을 기준으로 K-factors 데이터와 매칭
    pipe_lm_geom = []
    for ftr_idn in df_pipe_lm["FTR_IDN"].unique():
        segments = gdf_pipe_lm[gdf_pipe_lm["FTR_IDN"] == ftr_idn]
        if not segments.empty:
            centroids = segments.geometry.centroid
            avg_x = centroids.x.mean()
            avg_y = centroids.y.mean()
            pipe_lm_geom.append({"FTR_IDN": ftr_idn, "geometry": Point(avg_x, avg_y)})

    sply_ls_geom = []
    for ftr_idn in df_sply_ls["FTR_IDN"].unique():
        segments = gdf_sply_ls[gdf_sply_ls["FTR_IDN"] == ftr_idn]
        if not segments.empty:
            centroids = segments.geometry.centroid
            avg_x = centroids.x.mean()
            avg_y = centroids.y.mean()
            sply_ls_geom.append({"FTR_IDN": ftr_idn, "geometry": Point(avg_x, avg_y)})

    # GeoDataFrame 생성
    gdf_pipe_lm_factors = gpd.GeoDataFrame(
        pd.merge(df_pipe_lm, pd.DataFrame(pipe_lm_geom), on="FTR_IDN"), crs="EPSG:5179"
    )

    gdf_sply_ls_factors = gpd.GeoDataFrame(
        pd.merge(df_sply_ls, pd.DataFrame(sply_ls_geom), on="FTR_IDN"), crs="EPSG:5179"
    )

    # WGS84로 변환
    gdf_pipe_lm_factors = gdf_pipe_lm_factors.to_crs("EPSG:4326")
    gdf_sply_ls_factors = gdf_sply_ls_factors.to_crs("EPSG:4326")

    # 위도/경도 추출
    gdf_pipe_lm_factors["경도"] = gdf_pipe_lm_factors.geometry.x
    gdf_pipe_lm_factors["위도"] = gdf_pipe_lm_factors.geometry.y

    gdf_sply_ls_factors["경도"] = gdf_sply_ls_factors.geometry.x
    gdf_sply_ls_factors["위도"] = gdf_sply_ls_factors.geometry.y

    # 통합
    cols_to_concat = ["FTR_IDN", *ANALYSIS_FACTORS, "pipe_type", "위도", "경도"]
    df_pipes = pd.concat(
        [
            gdf_pipe_lm_factors[cols_to_concat],
            gdf_sply_ls_factors[cols_to_concat],
        ],
        ignore_index=True,
    )

    # 유효한 데이터만 필터링 (D_final이 0보다 큰 경우)
    df_pipes = df_pipes[df_pipes["D_final"] > 0]

    print(f"\n유효한 파이프: {len(df_pipes)}개")

    return df_pipes  # type: ignore[no-any-return]


def create_visualizations(df_matched: pd.DataFrame, results: dict[str, Any]) -> None:
    """결과 시각화"""
    print("\n=== 시각화 생성 중 ===")

    setup_korean_font()

    # 1. 산점도 - 모든 분석 요인 (3x3 그리드, 9개 요인)
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    axes = axes.flatten()

    for idx, factor in enumerate(ANALYSIS_FACTORS):
        if idx >= len(axes):  # 9개 축, 9개 요인이므로 모두 들어감
            break
        ax = axes[idx]

        # 최대값 사용 (최악의 경우 고려)
        col_name = f"max_{factor}"
        if col_name in df_matched.columns:
            ax.scatter(
                df_matched[col_name],
                df_matched["repair_count"],
                c=df_matched["repair_count"],
                cmap="coolwarm",
                alpha=0.6,
                s=50,
            )

            # 회귀선 (데이터의 분산이 있을 때만)
            if df_matched[col_name].std() > 0:
                try:
                    z = np.polyfit(df_matched[col_name], df_matched["repair_count"], 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(
                        df_matched[col_name].min(), df_matched[col_name].max(), 100
                    )
                    ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
                except np.linalg.LinAlgError:
                    # 회귀선을 그릴 수 없는 경우 건너뛰기
                    pass

            # 상관계수 표시
            corr_key = f"{col_name}_corr"
            p_key = f"{col_name}_p"
            if corr_key in results:
                corr = results[corr_key]
                p_val = results[p_key]
                sig = "*" if p_val < 0.05 else ""
                ax.set_title(
                    f"{FACTOR_NAMES[factor]}\nr={corr:.4f}, p={p_val:.4f}{sig}"
                )
            else:
                ax.set_title(FACTOR_NAMES[factor])

            ax.set_xlabel(factor)
            ax.set_ylabel("재작업 횟수")
            ax.grid(True, alpha=0.3)

            # 4회 이상 재작업 위치 강조
            frequent = df_matched[
                df_matched["repair_count"] >= MIN_REPAIRS_FOR_FREQUENT
            ]
            if len(frequent) > 0:
                ax.scatter(
                    frequent[col_name],
                    frequent["repair_count"],
                    color="red",
                    s=100,
                    alpha=0.8,
                    edgecolors="black",
                    linewidths=2,
                    label="4회 이상",
                    zorder=5,
                )
                ax.legend()

    # 9개 요인이므로 모든 축을 사용함

    plt.suptitle(
        "파이프 위험 요인과 재작업 횟수 상관관계",
        fontsize=16,
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(
        RESULTS_DIR / "repair_k_factors_scatter.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    # 2. 박스플롯 - 그룹 비교 (3x3 그리드)
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    axes = axes.flatten()

    for idx, factor in enumerate(ANALYSIS_FACTORS):
        if idx >= len(axes):
            break
        ax = axes[idx]
        col_name = f"max_{factor}"

        if col_name in df_matched.columns:
            data_to_plot = []
            labels = []

            df_frequent = df_matched[
                df_matched["repair_count"] >= MIN_REPAIRS_FOR_FREQUENT
            ]
            df_normal = df_matched[
                df_matched["repair_count"] < MIN_REPAIRS_FOR_FREQUENT
            ]

            if len(df_normal) > 0:
                data_to_plot.append(df_normal[col_name])
                labels.append(f"일반\n(n={len(df_normal)})")

            if len(df_frequent) > 0:
                data_to_plot.append(df_frequent[col_name])
                labels.append(f"빈번\n(n={len(df_frequent)})")

            if data_to_plot:
                bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True)

                # 색상 설정
                colors = ["lightblue", "lightcoral"]
                for patch, color in zip(
                    bp["boxes"], colors[: len(bp["boxes"])], strict=False
                ):
                    patch.set_facecolor(color)

                ax.set_ylabel(factor)
                ax.set_title(FACTOR_NAMES[factor])
                ax.grid(True, alpha=0.3)

                # 통계 검정 결과 표시
                t_p_key = f"{col_name}_t_p"
                if t_p_key in results:
                    p_value = results[t_p_key]
                    sig = "*" if p_value < P_VALUE_THRESHOLD else ""
                    ax.text(
                        0.5,
                        0.95,
                        f"p={p_value:.4f}{sig}",
                        transform=ax.transAxes,
                        ha="center",
                        va="top",
                        bbox=dict(
                            boxstyle="round",
                            facecolor=(
                                "yellow" if p_value < P_VALUE_THRESHOLD else "white"
                            ),
                            alpha=0.5,
                        ),
                    )

    # 9개 요인이므로 모든 축을 사용함

    plt.suptitle("재작업 빈도별 위험 요인 분포 비교", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.savefig(
        RESULTS_DIR / "repair_k_factors_boxplot.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    # 3. 상관계수 히트맵
    # 상관계수 매트릭스 생성
    corr_data = []
    for factor in ANALYSIS_FACTORS:
        row = []
        for strategy in ["max", "nearest", "avg"]:
            col_name = f"{strategy}_{factor}"
            corr_key = f"{col_name}_corr"
            if corr_key in results:
                row.append(results[corr_key])
            else:
                row.append(0)
        corr_data.append(row)

    corr_matrix = pd.DataFrame(
        corr_data,
        index=[FACTOR_NAMES[f] for f in ANALYSIS_FACTORS],
        columns=["최대값", "가장 가까운", "평균값"],
    )

    # 히트맵 그리기
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=".4f",
        cmap="coolwarm",
        center=0,
        vmin=-0.3,
        vmax=0.3,
        square=True,
        linewidths=1,
        cbar_kws={"shrink": 0.8, "label": "상관계수"},
        ax=ax,
    )

    plt.title(
        "위험 요인과 재작업 횟수 상관계수 히트맵",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    plt.xlabel("매칭 전략", fontsize=12)
    plt.ylabel("위험 요인", fontsize=12)
    plt.tight_layout()
    plt.savefig(
        RESULTS_DIR / "repair_k_factors_heatmap.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    print("시각화 파일 생성 완료")


def analyze_subregion_correlation(
    region_code: str, distance_threshold: float = DISTANCE_THRESHOLD_METERS
) -> dict[str, Any]:
    """하위 지역별 상관관계 분석"""
    print(f"\n{'=' * 70}")
    print(f"{region_code} 지역 상관관계 분석")
    print("=" * 70)

    # 데이터 로드
    gdf_repairs = load_repair_data_for_subregion(region_code)  # 이제 GeoDataFrame 반환
    gdf_pipes = load_pipe_factors_for_subregion(region_code)

    if len(gdf_repairs) == 0:
        print(f"경고: {region_code} 지역에 복구 작업 데이터가 없습니다.")
        return {}

    if len(gdf_pipes) == 0:
        print(f"경고: {region_code} 지역에 파이프 데이터가 없습니다.")
        return {}

    # 클러스터링
    gdf_clusters = create_repair_clusters(
        gdf_repairs,
        cluster_distance=CLUSTER_DISTANCE_METERS,
        min_repairs_for_frequent=MIN_REPAIRS_FOR_FREQUENT,
    )

    # 매칭
    df_matched = match_clusters_to_pipes(
        gdf_clusters, gdf_pipes, distance_threshold, analysis_factors=ANALYSIS_FACTORS
    )

    if len(df_matched) == 0:
        print(f"경고: {region_code} 지역에 매칭된 데이터가 없습니다.")
        return {}

    # 상관관계 분석
    results = analyze_correlation(
        df_matched, ANALYSIS_FACTORS, MIN_REPAIRS_FOR_FREQUENT
    )
    results["region_code"] = region_code
    results["matched_count"] = len(df_matched)
    results["total_repairs"] = len(gdf_repairs)
    results["total_pipes"] = len(gdf_pipes)

    return {
        "region_code": region_code,
        "results": results,
        "df_matched": df_matched,
        "df_pipes": gdf_pipes,
        "df_repairs": gdf_repairs,
        "df_clusters": gdf_clusters,  # metadata.json 생성을 위해 추가
    }


def save_subregion_results(region_data: dict[str, Any], output_dir: Path) -> None:
    """하위 지역 결과 저장"""
    region_code = region_data["region_code"]
    df_matched = region_data["df_matched"]
    results = region_data["results"]
    gdf_pipes = region_data["df_pipes"]
    df_clusters = region_data.get("df_clusters")

    # 지역별 디렉토리 생성
    region_dir = output_dir / region_code
    region_dir.mkdir(parents=True, exist_ok=True)

    # CSV 저장
    csv_path = region_dir / "repair_k_factors_matched.csv"
    df_matched.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"{region_code} 매칭 결과 저장: {csv_path}")

    # 분석 결과 텍스트 저장
    txt_path = region_dir / "correlation_analysis.txt"
    save_analysis_report(
        txt_path, results, df_matched, gdf_pipes, region_code, df_clusters
    )
    print(f"{region_code} 분석 보고서 저장: {txt_path}")


def create_subregion_visualizations(
    region_data: dict[str, Any], output_dir: Path
) -> None:
    """하위 지역별 시각화"""
    region_code = region_data["region_code"]
    df_matched = region_data["df_matched"]
    results = region_data["results"]

    region_dir = output_dir / region_code
    region_dir.mkdir(parents=True, exist_ok=True)

    # 시각화 생성 (기존 create_visualizations 수정)
    create_visualizations_for_region(df_matched, results, region_dir, region_code)


def create_visualizations_for_region(
    df_matched: pd.DataFrame,
    results: dict[str, Any],
    output_dir: Path,
    region_code: str,
) -> None:
    """지역별 시각화 (기존 create_visualizations 함수 수정)"""
    print(f"\n=== {region_code} 지역 시각화 생성 중 ===")

    setup_korean_font()

    # 산점도
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    fig.suptitle(
        f"{region_code} 지역 재작업-위험요인 상관관계", fontsize=16, fontweight="bold"
    )
    axes = axes.flatten()

    for idx, factor in enumerate(ANALYSIS_FACTORS):
        if idx >= len(axes):
            break
        ax = axes[idx]

        col_name = f"nearest_{factor}"
        if col_name in df_matched.columns:
            ax.scatter(
                df_matched[col_name],
                df_matched["repair_count"],
                c=df_matched["repair_count"],
                cmap="coolwarm",
                alpha=0.6,
                s=50,
            )

            # 회귀선
            if df_matched[col_name].std() > 0:
                try:
                    z = np.polyfit(df_matched[col_name], df_matched["repair_count"], 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(
                        df_matched[col_name].min(), df_matched[col_name].max(), 100
                    )
                    ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
                except np.linalg.LinAlgError:
                    pass

            # 상관계수 표시
            corr_key = f"{col_name}_corr"
            p_key = f"{col_name}_p"
            if corr_key in results:
                corr = results[corr_key]
                p_val = results[p_key]
                sig = "*" if p_val < 0.05 else ""
                ax.set_title(
                    f"{FACTOR_NAMES[factor]}\nr={corr:.4f}, p={p_val:.4f}{sig}"
                )
            else:
                ax.set_title(FACTOR_NAMES[factor])

            ax.set_xlabel(factor)
            ax.set_ylabel("재작업 횟수")
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    scatter_path = output_dir / "scatter_plot.png"
    plt.savefig(scatter_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"산점도 저장: {scatter_path}")

    # 박스플롯
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    fig.suptitle(
        f"{region_code} 지역 빈번한 재작업 vs 일반", fontsize=16, fontweight="bold"
    )
    axes = axes.flatten()

    for idx, factor in enumerate(ANALYSIS_FACTORS):
        if idx >= len(axes):
            break
        ax = axes[idx]

        col_name = f"nearest_{factor}"
        if col_name in df_matched.columns:
            frequent = df_matched[
                df_matched["repair_count"] >= MIN_REPAIRS_FOR_FREQUENT
            ]
            normal = df_matched[df_matched["repair_count"] < MIN_REPAIRS_FOR_FREQUENT]

            data_to_plot = []
            labels = []

            if len(normal) > 0:
                data_to_plot.append(normal[col_name].values)
                labels.append(f"일반\n(n={len(normal)})")

            if len(frequent) > 0:
                data_to_plot.append(frequent[col_name].values)
                labels.append(f"빈번\n(n={len(frequent)})")

            if data_to_plot:
                bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True)
                colors = ["lightblue", "lightcoral"]
                for patch, color in zip(
                    bp["boxes"], colors[: len(bp["boxes"])], strict=False
                ):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)

            ax.set_title(FACTOR_NAMES[factor])
            ax.set_ylabel(factor)
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    boxplot_path = output_dir / "boxplot.png"
    plt.savefig(boxplot_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"박스플롯 저장: {boxplot_path}")


def save_analysis_report(
    filepath: Path,
    results: dict[str, Any],
    df_matched: pd.DataFrame,
    gdf_pipes: gpd.GeoDataFrame,
    region_code: str,
    df_clusters: gpd.GeoDataFrame | None = None,
) -> None:
    """분석 보고서 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 70}\n")
        f.write(f"{region_code} 지역 재작업-위험 요인 상관관계 분석 보고서\n")
        f.write(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'=' * 70}\n\n")

        f.write("1. 데이터 요약\n")
        f.write("-" * 70 + "\n")
        f.write(f"지역 코드: {region_code}\n")
        f.write(f"전체 복구 작업: {results.get('total_repairs', 0)}개\n")
        f.write(f"전체 파이프: {results.get('total_pipes', 0)}개\n")
        f.write(f"매칭된 클러스터: {results.get('matched_count', 0)}개\n\n")

        # 2. 상관관계 분석
        f.write("2. 상관관계 분석 결과\n")
        f.write("-" * 70 + "\n\n")

        strategies = ["nearest", "max", "weighted_avg"]
        strategy_names = {
            "nearest": "가장 가까운 파이프",
            "max": "최대값",
            "weighted_avg": "거리 가중 평균",
        }

        for strategy in strategies:
            f.write(f"전략: {strategy_names[strategy]}\n")
            for factor in ANALYSIS_FACTORS:
                col_name = f"{strategy}_{factor}"
                corr_key = f"{col_name}_corr"
                p_key = f"{col_name}_p"

                if corr_key in results:
                    corr = results[corr_key]
                    p_val = results[p_key]
                    sig = "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
                    f.write(
                        f"  {FACTOR_NAMES[factor]} ({factor}): r={corr:.4f}, p={p_val:.4f} {sig}\n"
                    )
            f.write("\n")

        # 최선의 상관관계
        if "best_factor" in results:
            factor_korean = FACTOR_NAMES.get(
                results["best_factor"], results["best_factor"]
            )
            f.write(f"가장 강한 상관관계: {factor_korean} ({results['best_factor']})\n")
            f.write(
                f"  전략: {strategy_names.get(results['best_strategy'], results['best_strategy'])}\n"
            )
            f.write(f"  상관계수: r={results['best_corr']:.4f}\n\n")

    # metadata.json 저장 (main14c2에서 사용)
    total_clusters = (
        len(df_clusters)
        if df_clusters is not None
        else results.get("total_clusters", len(df_matched))
    )
    matched_clusters = len(df_matched)
    matching_rate = (
        (matched_clusters / total_clusters * 100) if total_clusters > 0 else 0
    )

    metadata = {
        "region_code": region_code,
        "total_clusters": total_clusters,
        "matched_clusters": matched_clusters,
        "matching_rate": matching_rate,
        "avg_pipes_per_cluster": (
            df_matched["pipe_count"].mean() if "pipe_count" in df_matched.columns else 0
        ),
        "total_repairs": results.get("total_repairs", 0),
        "total_pipes": results.get("total_pipes", 0),
        "timestamp": datetime.now().isoformat(),
    }

    # Use the parent directory of the filepath
    region_dir = filepath.parent
    metadata_path = region_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"{region_code} 메타데이터 저장 완료: metadata.json")


def save_results(
    df_matched: pd.DataFrame, results: dict[str, Any], df_pipes: pd.DataFrame
) -> None:
    """분석 결과 저장 (기존 함수, 전체 분석용)"""
    print("\n=== 결과 저장 중 ===")

    # 매칭 데이터 저장
    df_matched.to_csv(RESULTS_DIR / "0520_repair_k_factors_matched.csv", index=False)

    # 분석 요약 저장
    with (RESULTS_DIR / "0520_repair_correlations_analysis.txt").open(
        "w", encoding="utf-8"
    ) as f:
        f.write("=" * 70 + "\n")
        f.write("0520 지역 - 재작업 위치와 파이프 위험 요인 상관관계 통합 분석\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"분석 일시: {datetime.now()}\n")
        f.write(f"분석 대상: {len(df_matched)}개 클러스터\n")
        f.write(f"빈번한 재작업 기준: {MIN_REPAIRS_FOR_FREQUENT}회 이상\n")
        f.write(f"파이프 검색 반경: {DISTANCE_THRESHOLD_METERS}m\n")
        # K-factors 개수 계산
        base_count = len(BASE_K_FACTORS)
        optional_count = len([f for f in OPTIONAL_K_FACTORS if f in ANALYSIS_FACTORS])

        f.write(f"분석 요인: 총 {len(ANALYSIS_FACTORS)}개\n")
        f.write(
            f"  - 기본 K-factors: {base_count}개 (STD_DIP, K_age, K_soil, K_traffic, hoop_stress, K_stress, K_total)\n"
        )
        f.write("  - 피로 손상 지수: 1개 (D_final)\n")
        if optional_count > 0:
            f.write(f"  - 선택적 K-factors: {optional_count}개 (K_repair)\n")
        f.write("\n")

        f.write("-" * 70 + "\n")
        f.write("1. 상관계수 분석 (가장 가까운 파이프 기준)\n")
        f.write("-" * 70 + "\n\n")

        for factor in ANALYSIS_FACTORS:
            col_name = f"nearest_{factor}"
            if f"{col_name}_corr" in results:
                f.write(f"{FACTOR_NAMES[factor]} ({factor}):\n")
                f.write(f"  상관계수: {results[f'{col_name}_corr']:.4f}\n")
                f.write(f"  p-value: {results[f'{col_name}_p']:.4f}\n")
                sig = "유의미" if results[f"{col_name}_p"] < 0.05 else "유의미하지 않음"
                f.write(f"  통계적 유의성: {sig}\n\n")

        f.write("-" * 70 + "\n")
        f.write("2. 전략별 상관계수 비교\n")
        f.write("-" * 70 + "\n\n")

        # 테이블 형식으로 출력
        f.write(
            f"{'K-factor':20s} {'가장 가까운':>12s} {'최대값':>12s} {'평균값':>12s}\n"
        )
        f.write("-" * 60 + "\n")

        for factor in ANALYSIS_FACTORS:
            row = f"{FACTOR_NAMES[factor]:20s}"
            for strategy in ["nearest", "max", "avg"]:
                col_name = f"{strategy}_{factor}"
                corr_key = f"{col_name}_corr"
                if corr_key in results:
                    row += f" {results[corr_key]:11.4f}"
                else:
                    row += f" {'N/A':>11s}"
            f.write(row + "\n")

        f.write("\n")
        f.write("-" * 70 + "\n")
        f.write("3. 그룹별 비교 (뺈번한 재작업 vs 일반)\n")
        f.write("-" * 70 + "\n\n")

        f.write(
            f"빈번한 재작업 그룹 (≥{MIN_REPAIRS_FOR_FREQUENT}회): {results.get('frequent_count', 0)}개\n"
        )
        f.write(
            f"일반 재작업 그룹 (<{MIN_REPAIRS_FOR_FREQUENT}회): {results.get('normal_count', 0)}개\n\n"
        )

        for factor in ANALYSIS_FACTORS:
            col_name = f"nearest_{factor}"
            if f"{col_name}_frequent_mean" in results:
                f.write(f"{FACTOR_NAMES[factor]} ({factor}):\n")
                freq_mean = results[f"{col_name}_frequent_mean"]
                norm_mean = results[f"{col_name}_normal_mean"]
                diff = freq_mean - norm_mean
                diff_pct = (diff / norm_mean * 100) if norm_mean != 0 else 0

                f.write(f"  빈번한 재작업 평균: {freq_mean:.4f}\n")
                f.write(f"  일반 재작업 평균: {norm_mean:.4f}\n")
                f.write(f"  차이: {diff:+.4f} ({diff_pct:+.1f}%)\n")
                f.write(
                    f"  t-test: t={results[f'{col_name}_t_stat']:.4f}, p={results[f'{col_name}_t_p']:.4f}\n"
                )
                sig = (
                    "유의미" if results[f"{col_name}_t_p"] < 0.05 else "유의미하지 않음"
                )
                f.write(f"  통계적 유의성: {sig}\n\n")

        f.write("-" * 70 + "\n")
        f.write("4. 위험 요인 분포 통계\n")
        f.write("-" * 70 + "\n\n")

        f.write(f"전체 파이프 수: {len(df_pipes)}개\n")
        f.write(f"  PIPE_LM: {len(df_pipes[df_pipes['pipe_type'] == 'PIPE_LM'])}개\n")
        f.write(f"  SPLY_LS: {len(df_pipes[df_pipes['pipe_type'] == 'SPLY_LS'])}개\n\n")

        for factor in ANALYSIS_FACTORS:
            f.write(f"{FACTOR_NAMES[factor]} ({factor}) 통계:\n")
            f.write(f"  최소값: {df_pipes[factor].min():.4f}\n")
            f.write(f"  25%: {df_pipes[factor].quantile(0.25):.4f}\n")
            f.write(f"  중앙값: {df_pipes[factor].median():.4f}\n")
            f.write(f"  75%: {df_pipes[factor].quantile(0.75):.4f}\n")
            f.write(f"  최대값: {df_pipes[factor].max():.4f}\n")
            f.write(f"  평균: {df_pipes[factor].mean():.4f}\n")
            f.write(f"  표준편차: {df_pipes[factor].std():.4f}\n\n")

        f.write("-" * 70 + "\n")
        f.write("5. 주요 발견사항\n")
        f.write("-" * 70 + "\n\n")

        # 가장 강한 상관관계
        if "best_factor" in results:
            f.write("가장 강한 상관관계:\n")
            f.write(
                f"  요인: {FACTOR_NAMES.get(results['best_factor'], results['best_factor'])}\n"
            )
            f.write(f"  전략: {results['best_strategy']}\n")
            f.write(f"  상관계수: {results['best_corr']:.4f}\n\n")

        # 유의미한 차이가 있는 요인들
        significant_factors = []
        for factor in ANALYSIS_FACTORS:
            col_name = f"nearest_{factor}"
            t_p_key = f"{col_name}_t_p"
            if t_p_key in results and results[t_p_key] < 0.05:
                significant_factors.append(FACTOR_NAMES[factor])

        if significant_factors:
            f.write("빈번한 재작업 그룹에서 유의미한 차이를 보이는 요인:\n")
            for sf in significant_factors:
                f.write(f"  - {sf}\n")
        else:
            f.write(
                "빈번한 재작업 그룹과 일반 그룹 간 유의미한 차이를 보이는 요인 없음\n"
            )

        f.write("\n" + "=" * 70 + "\n")
        f.write("분석 완료\n")
        f.write("=" * 70 + "\n")

    print("결과 파일 저장 완료")


def analyze_all_subregions(
    distance_threshold: float = DISTANCE_THRESHOLD_METERS,
    output_dir: Path = RESULTS_DIR / "main14c",
) -> list[dict[str, Any]]:
    """모든 하위 지역 순차 분석"""
    all_results = []

    for region_code in VALID_SUBREGIONS:
        region_data = analyze_subregion_correlation(region_code, distance_threshold)
        if region_data:
            all_results.append(region_data)
            # 결과 저장
            save_subregion_results(region_data, output_dir)
            # 시각화 생성
            create_subregion_visualizations(region_data, output_dir)

    return all_results


def compare_subregions(all_results: list[dict[str, Any]]) -> pd.DataFrame:
    """하위 지역 간 비교"""
    if not all_results:
        return pd.DataFrame()

    comparison_data = []

    for region_data in all_results:
        region_code = region_data["region_code"]
        results = region_data["results"]

        row = {
            "region_code": region_code,
            "total_repairs": results.get("total_repairs", 0),
            "total_pipes": results.get("total_pipes", 0),
            "matched_count": results.get("matched_count", 0),
        }

        # 각 요인별 최선의 상관계수 추가
        for factor in ANALYSIS_FACTORS:
            # nearest 전략의 상관계수 사용
            corr_key = f"nearest_{factor}_corr"
            if corr_key in results:
                row[f"{factor}_corr"] = results[corr_key]
                row[f"{factor}_p"] = results[f"nearest_{factor}_p"]

        # 최선의 요인
        if "best_factor" in results:
            row["best_factor"] = results["best_factor"]
            row["best_corr"] = results["best_corr"]
            row["best_strategy"] = results["best_strategy"]

        comparison_data.append(row)

    return pd.DataFrame(comparison_data)


def create_comparison_report(
    all_results: list[dict[str, Any]],
    output_dir: Path = RESULTS_DIR / "main14c",
    distance_threshold: float = 30.0,
) -> None:
    """통합 비교 보고서 생성"""
    if not all_results:
        print("비교할 결과가 없습니다.")
        return

    comparison_dir = output_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    # 비교 데이터프레임 생성
    df_comparison = compare_subregions(all_results)

    # CSV 저장
    csv_path = comparison_dir / "subregion_comparison.csv"
    df_comparison.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"비교 데이터 저장: {csv_path}")

    # 상관계수 매트릭스 생성
    corr_matrix = []
    for region_code in VALID_SUBREGIONS:
        row = {"region": region_code}
        region_row = df_comparison[df_comparison["region_code"] == region_code]
        if not region_row.empty:
            for factor in ANALYSIS_FACTORS:
                if f"{factor}_corr" in region_row.columns:
                    row[factor] = region_row[f"{factor}_corr"].values[0]
        corr_matrix.append(row)

    df_corr_matrix = pd.DataFrame(corr_matrix)
    matrix_path = comparison_dir / "correlation_matrix.csv"
    df_corr_matrix.to_csv(matrix_path, index=False, encoding="utf-8-sig")
    print(f"상관계수 매트릭스 저장: {matrix_path}")

    # 히트맵 생성
    setup_korean_font()
    fig, ax = plt.subplots(figsize=(12, 6))

    # 데이터 준비
    heatmap_data = df_corr_matrix.set_index("region")[ANALYSIS_FACTORS].T

    # 히트맵 그리기
    sns.heatmap(
        heatmap_data,
        annot=True,
        fmt=".3f",
        cmap="coolwarm",
        center=0,
        vmin=-0.5,
        vmax=0.5,
        square=True,
        ax=ax,
        cbar_kws={"label": "상관계수"},
    )

    ax.set_title(
        "하위 지역별 K-factors 상관계수 히트맵", fontsize=14, fontweight="bold"
    )
    ax.set_xlabel("지역 코드", fontsize=12)
    ax.set_ylabel("위험 요인", fontsize=12)

    # Y축 라벨을 한글명으로 변경
    y_labels = [FACTOR_NAMES[factor] for factor in ANALYSIS_FACTORS]
    ax.set_yticklabels(y_labels, rotation=0)

    plt.tight_layout()
    heatmap_path = comparison_dir / "correlation_heatmap.png"
    plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"히트맵 저장: {heatmap_path}")

    # 요인 중요도 그래프
    fig, ax = plt.subplots(figsize=(10, 6))

    # 각 요인별 평균 절대 상관계수 계산
    factor_importance = {}
    for factor in ANALYSIS_FACTORS:
        col_name = f"{factor}_corr"
        if col_name in df_comparison.columns:
            factor_importance[factor] = df_comparison[col_name].abs().mean()

    if factor_importance:
        factors = list(factor_importance.keys())
        importances = list(factor_importance.values())

        bars = ax.bar(range(len(factors)), importances, color="steelblue", alpha=0.8)
        ax.set_xticks(range(len(factors)))
        ax.set_xticklabels([FACTOR_NAMES[f] for f in factors], rotation=45, ha="right")
        ax.set_ylabel("평균 |상관계수|", fontsize=12)
        ax.set_title("하위 지역 평균 요인 중요도", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 값 표시
        for bar, val in zip(bars, importances, strict=False):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{val:.3f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

    plt.tight_layout()
    importance_path = comparison_dir / "factor_importance.png"
    plt.savefig(importance_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"요인 중요도 그래프 저장: {importance_path}")

    # 통합 보고서 작성
    report_path = comparison_dir / "integrated_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 하위 지역 K-factors 상관관계 분석 통합 보고서\n\n")
        f.write(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 1. 분석 개요\n\n")
        f.write(f"- 분석 지역: {', '.join(VALID_SUBREGIONS)}\n")
        f.write(f"- 분석 요인: {len(ANALYSIS_FACTORS)}개 (K-factors 7개 + D_final)\n")
        f.write(f"- 매칭 거리 임계값: {distance_threshold}m\n\n")

        f.write("## 2. 지역별 데이터 요약\n\n")
        f.write("| 지역 | 복구작업 | 파이프 | 매칭 클러스터 | 매칭률 |\n")
        f.write("|------|----------|--------|---------------|--------|\n")

        for _, row in df_comparison.iterrows():
            match_rate = (
                row["matched_count"] / row["total_repairs"] * 100
                if row["total_repairs"] > 0
                else 0
            )
            f.write(
                f"| {row['region_code']} | {row['total_repairs']} | {row['total_pipes']} | "
                f"{row['matched_count']} | {match_rate:.1f}% |\n"
            )

        f.write("\n## 3. 지역별 최강 상관관계\n\n")
        f.write("| 지역 | 최선 요인 | 상관계수 | 전략 |\n")
        f.write("|------|-----------|----------|------|\n")

        for _, row in df_comparison.iterrows():
            if "best_factor" in row and pd.notna(row["best_factor"]):
                f.write(
                    f"| {row['region_code']} | {FACTOR_NAMES.get(row['best_factor'], row['best_factor'])} | "
                    f"{row['best_corr']:.4f} | {row['best_strategy']} |\n"
                )

        f.write("\n## 4. 요인별 중요도 순위\n\n")

        if factor_importance:
            sorted_factors = sorted(
                factor_importance.items(), key=lambda x: x[1], reverse=True
            )
            f.write("| 순위 | 요인 | 평균 |상관계수| |\n")
            f.write("|------|------|----------------|\n")

            for i, (factor, importance) in enumerate(sorted_factors, 1):
                f.write(f"| {i} | {FACTOR_NAMES[factor]} | {importance:.4f} |\n")

        f.write("\n## 5. 주요 발견사항\n\n")

        # 가장 강한 상관관계 찾기
        best_overall = (
            df_comparison.loc[df_comparison["best_corr"].abs().idxmax()]
            if "best_corr" in df_comparison.columns
            else None
        )
        if best_overall is not None:
            f.write(
                f"- **가장 강한 상관관계**: {best_overall['region_code']} 지역의 "
                f"{FACTOR_NAMES.get(best_overall['best_factor'], best_overall['best_factor'])} "
                f"(r={best_overall['best_corr']:.4f})\n"
            )

        # 지역별 특성
        f.write("\n### 지역별 특성:\n\n")
        for region_code in VALID_SUBREGIONS:
            region_row = df_comparison[df_comparison["region_code"] == region_code]
            if not region_row.empty:
                row = region_row.iloc[0]
                f.write(f"- **{region_code}**: ")
                if "best_factor" in row and pd.notna(row["best_factor"]):
                    f.write(
                        f"{FACTOR_NAMES.get(row['best_factor'], row['best_factor'])}가 가장 영향력 있음 "
                    )
                    f.write(f"(r={row['best_corr']:.4f})\n")
                else:
                    f.write("유의미한 상관관계 없음\n")

        f.write("\n## 6. 결론 및 제언\n\n")
        f.write("- 지역별로 다른 위험 요인이 재작업과 연관됨\n")
        f.write("- 맞춤형 유지관리 전략 수립 필요\n")
        f.write("- 추가 데이터 수집 및 장기 모니터링 권장\n")

    print(f"통합 보고서 저장: {report_path}")


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="하위 지역별 재작업-위험요인 상관관계 분석"
    )
    parser.add_argument(
        "--region",
        type=str,
        choices=VALID_SUBREGIONS,
        help="분석할 하위 지역 코드 (0470, 0480, 0490)",
    )
    parser.add_argument(
        "--all-subregions", action="store_true", help="모든 하위 지역 분석 및 비교"
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=DISTANCE_THRESHOLD_METERS,
        help=f"파이프 매칭 거리 임계값 (기본값: {DISTANCE_THRESHOLD_METERS}m)",
    )
    parser.add_argument(
        "--output-dir", type=str, help="출력 디렉토리 (기본값: results/main14c)"
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    # 출력 디렉토리 설정
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR / "main14c"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("하위 지역별 재작업-위험요인 상관관계 분석")
    print("=" * 70)

    if args.all_subregions:
        # 모든 하위 지역 분석
        print("\n모든 하위 지역 분석 시작...")
        all_results = analyze_all_subregions(args.distance, output_dir)

        if all_results:
            # 비교 보고서 생성
            print("\n=== 지역 간 비교 분석 ===")
            create_comparison_report(all_results, output_dir, args.distance)

            print("\n모든 분석이 완료되었습니다.")
            print(f"결과 파일 위치: {output_dir}")
        else:
            print("\n분석 가능한 지역이 없습니다.")

    elif args.region:
        # 특정 지역만 분석
        print(f"\n{args.region} 지역 분석 시작...")
        region_data = analyze_subregion_correlation(args.region, args.distance)

        if region_data:
            save_subregion_results(region_data, output_dir)
            create_subregion_visualizations(region_data, output_dir)

            print(f"\n{args.region} 지역 분석 완료")
            print(f"결과 파일 위치: {output_dir / args.region}")
        else:
            print(f"\n{args.region} 지역 분석 실패")

    else:
        # 인자가 없으면 도움말 표시
        print("\n사용법:")
        print(
            "  개별 지역 분석: python src/main14c_subregion_correlations.py --region 0470"
        )
        print(
            "  모든 지역 분석: python src/main14c_subregion_correlations.py --all-subregions"
        )
        print("\n추가 옵션:")
        print(
            f"  --distance N: 매칭 거리 임계값 (기본값: {DISTANCE_THRESHOLD_METERS}m)"
        )
        print("  --output-dir PATH: 출력 디렉토리 지정")


if __name__ == "__main__":
    main()
