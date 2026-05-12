"""
데이터 로딩 공통 함수 모듈

main14b와 main14c에서 사용하는 파일 로딩 함수들을 제공합니다.
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.common.config import UNIFIED_REPAIR_CSV


def load_unified_repair_csv(
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    통합 재작업 데이터 CSV 파일을 로드합니다.

    Parameters
    ----------
    required_columns : list[str], optional
        선택할 컬럼 리스트. None이면 모든 컬럼 유지

    Returns
    -------
    pd.DataFrame
        통합된 재작업 데이터

    Raises
    ------
    SystemExit
        파일을 찾을 수 없는 경우
    """
    # 통합 CSV 파일 경로
    csv_path = UNIFIED_REPAIR_CSV

    if not csv_path.exists():
        print("\n" + "=" * 70)
        print("오류: 통합 재작업 데이터 파일을 찾을 수 없습니다!")
        print("=" * 70)
        print(f"\n필요한 파일: {csv_path}")
        print("\n해결 방법:")
        print("1. main13_crop_520.py 스크립트를 먼저 실행하세요.")
        print("   예: python src/main13_crop_520.py")
        sys.exit(1)

    try:
        # CSV 파일 로드
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 파일타입을 작업타입으로 매핑
        if "파일타입" in df.columns:
            df["작업타입"] = df["파일타입"]
        else:
            print("경고: 파일타입 컬럼이 없습니다.")

        print(f"✓ 통합 재작업 데이터: {len(df)}개 레코드")

        # 작업타입별 개수 출력
        if "작업타입" in df.columns:
            type_counts = df["작업타입"].value_counts()
            for repair_type, count in type_counts.items():
                print(f"  - {repair_type}: {count}개")

        # 필요한 컬럼만 선택
        if required_columns:
            # 존재하는 컬럼만 선택
            available_columns = [col for col in required_columns if col in df.columns]
            if "작업타입" not in available_columns and "작업타입" in df.columns:
                available_columns = ["작업타입", *available_columns]
            df = df[available_columns].copy()

        return df

    except Exception as e:
        print("\n오류: CSV 파일을 읽는 중 문제가 발생했습니다.")
        print(f"상세 오류: {e}")
        sys.exit(1)


def load_repair_csv_files(
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    재작업 데이터 CSV 파일들을 로드하고 통합합니다.
    통합 CSV 파일만 사용합니다.

    Parameters
    ----------
    required_columns : list[str], optional
        선택할 컬럼 리스트. None이면 모든 컬럼 유지

    Returns
    -------
    pd.DataFrame
        통합된 재작업 데이터

    Raises
    ------
    SystemExit
        파일을 찾을 수 없는 경우
    """
    # 통합 CSV 파일만 사용
    return load_unified_repair_csv(required_columns)


def load_fatigue_csv(
    pipe_lm_csv_path: Path, sply_ls_csv_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """
    피로 손상 K-factors CSV 파일을 로드하고 검증합니다.

    Parameters
    ----------
    pipe_lm_csv_path : Path
        PIPE_LM CSV 파일 경로
    sply_ls_csv_path : Path
        SPLY_LS CSV 파일 경로

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, bool]
        (df_pipe_lm, df_sply_ls, has_k_repair)
        - df_pipe_lm: PIPE_LM 데이터
        - df_sply_ls: SPLY_LS 데이터
        - has_k_repair: K_repair 컬럼 존재 여부

    Raises
    ------
    SystemExit
        파일을 찾을 수 없거나 읽을 수 없는 경우
    """
    # 파일 존재 확인
    missing_files = []
    if not pipe_lm_csv_path.exists():
        missing_files.append(str(pipe_lm_csv_path))
    if not sply_ls_csv_path.exists():
        missing_files.append(str(sply_ls_csv_path))

    if missing_files:
        print("\n" + "=" * 70)
        print("오류: K-factors/D_final 데이터 파일을 찾을 수 없습니다!")
        print("=" * 70)
        print("\n다음 파일들이 필요합니다:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("\n해결 방법:")
        print("1. data/pipe_fatigue/ 디렉토리에 위 파일들이 있는지 확인하세요.")
        print("2. 파일이 없다면 피로 손상 계산 스크립트를 먼저 실행하세요.")
        print("   예: python src/main8_calculate_fatigue.py")
        sys.exit(1)

    # CSV 파일 로드
    try:
        df_pipe_lm = pd.read_csv(pipe_lm_csv_path)
        df_sply_ls = pd.read_csv(sply_ls_csv_path)
        print(f"✓ PIPE_LM 데이터: {len(df_pipe_lm)}개 레코드")
        print(f"✓ SPLY_LS 데이터: {len(df_sply_ls)}개 레코드")
    except Exception as e:
        print("\n오류: CSV 파일을 읽는 중 문제가 발생했습니다.")
        print(f"상세 오류: {e}")
        sys.exit(1)

    # K_repair 컬럼 존재 여부 확인
    has_k_repair = "K_repair" in df_pipe_lm.columns and "K_repair" in df_sply_ls.columns
    if has_k_repair:
        print("K_repair 컬럼을 포함하여 분석합니다.")
    else:
        print("주의: K_repair 컬럼이 없어 분석에서 제외됩니다.")

    return df_pipe_lm, df_sply_ls, has_k_repair


def load_pipe_shapefiles(
    pipe_lm_shp_path: Path, sply_ls_shp_path: Path
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    파이프 Shapefile을 로드합니다.

    Parameters
    ----------
    pipe_lm_shp_path : Path
        PIPE_LM shapefile 경로
    sply_ls_shp_path : Path
        SPLY_LS shapefile 경로

    Returns
    -------
    Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]
        (gdf_pipe_lm, gdf_sply_ls)
        - gdf_pipe_lm: PIPE_LM GeoDataFrame
        - gdf_sply_ls: SPLY_LS GeoDataFrame

    Raises
    ------
    SystemExit
        파일을 찾을 수 없거나 읽을 수 없는 경우
    """
    # 파일 존재 확인
    missing_shapefiles = []
    if not pipe_lm_shp_path.exists():
        missing_shapefiles.append(str(pipe_lm_shp_path))
    if not sply_ls_shp_path.exists():
        missing_shapefiles.append(str(sply_ls_shp_path))

    if missing_shapefiles:
        print("\n" + "=" * 70)
        print("오류: 파이프 Shapefile을 찾을 수 없습니다!")
        print("=" * 70)
        print("\n다음 파일들이 필요합니다:")
        for file_path in missing_shapefiles:
            print(f"  - {file_path}")
        print("\n해결 방법:")
        print("1. data/raw/export_shp_*/ 디렉토리를 확인하세요.")
        print("2. V_WTL_PIPE_LM.shp 와 V_WTL_SPLY_LS.shp 파일이 있는지 확인하세요.")
        print("3. 파일이 없다면 GIS 데이터를 먼저 준비하세요.")
        sys.exit(1)

    # Shapefile 로드
    try:
        gdf_pipe_lm = gpd.read_file(pipe_lm_shp_path)
        gdf_sply_ls = gpd.read_file(sply_ls_shp_path)
        print(f"✓ PIPE_LM Shapefile: {len(gdf_pipe_lm)}개 피처")
        print(f"✓ SPLY_LS Shapefile: {len(gdf_sply_ls)}개 피처")
    except Exception as e:
        print("\n오류: Shapefile을 읽는 중 문제가 발생했습니다.")
        print(f"상세 오류: {e}")
        sys.exit(1)

    return gdf_pipe_lm, gdf_sply_ls
