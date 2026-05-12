"""
파이프라인과 공급관로의 토양 매칭 스크립트
V_WTL_PIPE_LM과 V_WTL_SPLY_LS를 토양 데이터(Geology_250K_Litho)와 공간 조인하여
FTR_IDN별 lithoidx 값을 CSV로 저장
"""

import argparse
import re
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src import soil_loader
from src.common.config import DATA_DIR, RAW_DATA_DIR, REGION_CODE_PATTERN, RESULTS_DIR
from src.common.shapefile_loader import load_pipe_shapefile

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def get_export_directories(data_dir: Path) -> list[tuple[Path, str]]:
    """export_shp_* 디렉토리들을 찾고 버전 정보 추출"""
    export_dirs = []
    for d in sorted(data_dir.iterdir()):
        if d.is_dir() and d.name.startswith("export_shp_"):
            match = re.search(REGION_CODE_PATTERN, d.name)
            version = match.group(1) if match else "unknown"
            export_dirs.append((d, version))
    return export_dirs


def process_pipe_type(
    region_code: str,
    pipe_type: str,
    soil_gdf: gpd.GeoDataFrame,
    k_soil_df: pd.DataFrame,
) -> None:
    """특정 파이프 타입 처리 및 저장"""
    # 파이프 데이터 로드
    pipe_gdf = load_pipe_shapefile(RAW_DATA_DIR, region_code, pipe_type)
    if pipe_gdf is None or len(pipe_gdf) == 0:
        return

    # 공간 조인 수행
    print(f"\n{pipe_type} 공간 조인 수행 중...")
    result = soil_loader.spatial_join_with_soil(pipe_gdf, soil_gdf, k_soil_df)

    # 결과 저장
    output_file = (
        f"{region_code}_{'pipe' if pipe_type == 'PIPE_LM' else 'supply'}_soil.csv"
    )
    output_path = RESULTS_DIR / output_file
    soil_loader.save_soil_matching_result(result, output_path)


def process_regions(
    args: argparse.Namespace, soil_gdf: gpd.GeoDataFrame, k_soil_df: pd.DataFrame
) -> None:
    """지역별 처리"""
    export_dirs = get_export_directories(RAW_DATA_DIR)
    if not export_dirs:
        print("오류: export_shp_ 디렉토리를 찾을 수 없습니다.")
        return

    print(f"\n총 {len(export_dirs)}개의 export 디렉토리 발견")

    for export_dir, version in export_dirs:
        if args.version and version != args.version:
            continue

        print(f"\n=== {version} 지역 처리 중 ===")

        if args.type in ["pipe", "both"]:
            process_pipe_type(version, "PIPE_LM", soil_gdf, k_soil_df)

        if args.type in ["supply", "both"]:
            process_pipe_type(version, "SPLY_LS", soil_gdf, k_soil_df)


def main() -> None:
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="파이프라인/공급관로와 토양 데이터 매칭"
    )
    parser.add_argument("--version", type=str, help="특정 버전만 처리 (예: 0520)")
    parser.add_argument(
        "--type",
        choices=["pipe", "supply", "both"],
        default="both",
        help="처리할 데이터 타입",
    )

    args = parser.parse_args()

    print("파이프라인-토양 매칭 시작...")
    print(f"데이터 디렉토리: {RAW_DATA_DIR}")
    RESULTS_DIR.mkdir(exist_ok=True)

    # 토양 데이터 로드
    print("\n토양 데이터 로드 중...")
    soil_gdf = soil_loader.load_soil_data(DATA_DIR)
    if soil_gdf is None:
        print("오류: 토양 데이터를 로드할 수 없습니다.")
        return

    # K_SOIL 데이터 로드
    print("\nK_SOIL 데이터 로드 중...")
    k_soil_df = soil_loader.load_k_soil_data(RESULTS_DIR)

    if k_soil_df is None:
        print("오류: K_SOIL 데이터를 로드할 수 없습니다.")
        return

    # 지역별 처리
    process_regions(args, soil_gdf, k_soil_df)
    print("\n모든 처리 완료!")


if __name__ == "__main__":
    main()
