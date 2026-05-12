"""
main13a_calculate_k_repair.py

파이프와 재작업 위치 간 거리를 분석하여 각 파이프의 재작업 횟수(K_repair) 계산

선형 거리 가중치 적용: 0m에서 가중치 1.0, 지정 거리에서 가중치 0.0으로 선형 감소
K_repair 정규화 시 최소 파이프 길이 10m 적용하여 짧은 파이프의 과도한 per-meter 값 방지

Usage:
    python src/main13a_calculate_k_repair.py [--distance 30] [--verbose]
"""

import argparse
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.strtree import STRtree

from src.common.config import get_config
from src.common.korean_font_utils import setup_korean_font

# 정규화 계산을 위한 최소 파이프 길이 (미터)
# 10m 미만 파이프는 정규화 시 10m로 처리하여 과도한 per-meter 값 방지
MIN_PIPE_LENGTH = 10.0


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="파이프별 재작업 횟수(K_repair) 계산")
    parser.add_argument(
        "--distance",
        type=float,
        default=30.0,
        help="매칭 거리 임계값 (미터, 기본값: 30)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/main13a_k_repair",
        help="출력 디렉토리 (기본값: results/main13a_k_repair/)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 출력",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="캐시 사용 안함",
    )
    return parser.parse_args()


def load_pipe_shapefile(
    pipe_type: str, data_dir: Path, verbose: bool = True
) -> gpd.GeoDataFrame | None:
    """파이프 shapefile 로드

    Args:
        pipe_type: "PIPE_LM" 또는 "SPLY_LS"
        data_dir: 데이터 디렉토리
        verbose: 상세 출력 여부

    Returns:
        파이프 GeoDataFrame 또는 None
    """
    # export 디렉토리 찾기
    export_dirs = list(data_dir.glob("export_shp_*0520*"))
    if not export_dirs:
        if verbose:
            print(f"오류: {data_dir}에서 export 디렉토리를 찾을 수 없습니다.")
        return None

    export_dir = export_dirs[0]

    # shapefile 경로
    shp_file = export_dir / f"V_WTL_{pipe_type}.shp"

    if not shp_file.exists():
        if verbose:
            print(f"오류: {shp_file}을 찾을 수 없습니다.")
        return None

    try:
        # shapefile 로드
        gdf = gpd.read_file(shp_file, encoding="euc-kr")

        # CRS 확인 및 변환
        if gdf.crs is None:
            gdf.set_crs("EPSG:5179", inplace=True)
        elif gdf.crs != "EPSG:5179":
            gdf = gdf.to_crs("EPSG:5179")

        # FTR_IDN 컬럼 확인
        if "FTR_IDN" not in gdf.columns:
            if verbose:
                print("경고: FTR_IDN 컬럼이 없습니다.")
            return None

        if verbose:
            print(f"{pipe_type} shapefile 로드 완료: {len(gdf):,}개 파이프")

        return gdf

    except Exception as e:
        if verbose:
            print(f"오류: shapefile 로드 실패 - {e}")
        return None


def load_unified_repair_csv(
    results_dir: Path, verbose: bool = True
) -> pd.DataFrame | None:
    """통합 재작업 CSV 파일 로드

    Args:
        results_dir: 결과 디렉토리
        verbose: 상세 출력 여부

    Returns:
        재작업 DataFrame 또는 None
    """
    # main13_crop_520 결과 디렉토리에서 통합 파일 로드
    csv_file = results_dir / "main13_crop_520" / "누수공사_통합_520_위치추가.csv"

    if not csv_file.exists():
        if verbose:
            print(f"경고: {csv_file}을 찾을 수 없습니다.")
        return None

    try:
        df = pd.read_csv(csv_file, encoding="utf-8-sig")

        # 파일타입 컬럼을 repair_type으로 변경
        if "파일타입" in df.columns:
            df["repair_type"] = df["파일타입"]
        else:
            if verbose:
                print("오류: 파일타입 컬럼이 없습니다.")
            return None

        # 필수 컬럼 확인
        if "위도" not in df.columns or "경도" not in df.columns:
            if verbose:
                print("오류: 위도/경도 컬럼이 없습니다.")
            return None

        # NaN 제거
        df = df.dropna(subset=["위도", "경도"])

        if verbose:
            print(f"통합 재작업 파일 로드 완료: {len(df):,}개 위치")
            # 재작업 유형별 개수 표시
            type_counts = df["repair_type"].value_counts()
            for repair_type, count in type_counts.items():
                print(f"  - {repair_type}: {count:,}개")

        return df

    except Exception as e:
        if verbose:
            print(f"오류: CSV 로드 실패 - {e}")
        return None


def convert_repairs_to_geodataframe(
    df: pd.DataFrame, verbose: bool = True
) -> gpd.GeoDataFrame:
    """재작업 DataFrame을 GeoDataFrame으로 변환 (WGS84 → EPSG:5179)

    Args:
        df: 재작업 DataFrame (위도/경도 포함)
        verbose: 상세 출력 여부

    Returns:
        GeoDataFrame (EPSG:5179)
    """
    # Point geometry 생성
    geometry = [
        Point(lon, lat) for lon, lat in zip(df["경도"], df["위도"], strict=False)
    ]

    # GeoDataFrame 생성 (WGS84)
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # EPSG:5179로 변환
    gdf = gdf.to_crs("EPSG:5179")

    if verbose:
        print("  좌표 변환 완료 (WGS84 → EPSG:5179)")

    return gdf


def calculate_k_repair_with_strtree(
    pipes_gdf: gpd.GeoDataFrame,
    repairs_gdf: gpd.GeoDataFrame,
    distance: float,
    verbose: bool = True,
) -> pd.DataFrame:
    """STRtree를 사용하여 K_repair 계산

    Args:
        pipes_gdf: 파이프 GeoDataFrame
        repairs_gdf: 재작업 GeoDataFrame
        distance: 매칭 거리 임계값 (미터)
        verbose: 상세 출력 여부

    Returns:
        FTR_IDN, pipe_length, K_repair(원본 및 1m당 정규화),
        K_repair_ground, K_repair_under, K_repair_emergency, K_repair_management가 포함된 DataFrame
    """
    if len(repairs_gdf) == 0:
        # 재작업이 없으면 모든 파이프의 K_repair = 0
        pipe_lengths = [geom.length for geom in pipes_gdf.geometry]
        return pd.DataFrame(
            {
                "FTR_IDN": pipes_gdf["FTR_IDN"],
                "pipe_length": pipe_lengths,
                "K_repair": 0.0,
                "K_repair_per_m": 0.0,
                "K_repair_ground": 0.0,
                "K_repair_ground_per_m": 0.0,
                "K_repair_under": 0.0,
                "K_repair_under_per_m": 0.0,
                "K_repair_emergency": 0.0,
                "K_repair_emergency_per_m": 0.0,
                "K_repair_management": 0.0,
                "K_repair_management_per_m": 0.0,
            }
        )

    # STRtree 구축
    if verbose:
        print("  공간 인덱스 구축 중...")
    repair_tree = STRtree(repairs_gdf.geometry.values)

    # 각 파이프에 대해 K_repair 계산
    k_repair_list = []

    if verbose:
        print(f"  {len(pipes_gdf):,}개 파이프 처리 중...")
        start_time = time.time()

    for idx, pipe in pipes_gdf.iterrows():
        # 파이프 주변 버퍼 생성
        buffer = pipe.geometry.buffer(distance)

        # 버퍼 내 재작업 찾기
        nearby_repair_indices = repair_tree.query(buffer)
        
        # 선형 거리 가중치 적용
        k_repair = 0.0
        k_repair_ground = 0.0
        k_repair_under = 0.0
        k_repair_emergency = 0.0
        k_repair_management = 0.0
        
        for repair_idx in nearby_repair_indices:
            repair_point = repairs_gdf.iloc[repair_idx].geometry
            
            # 파이프와 재작업 간 최단 거리 계산
            dist_to_pipe = pipe.geometry.distance(repair_point)
            
            # 선형 가중치 계산 (0m에서 1.0, distance에서 0.0)
            weight = max(0.0, 1.0 - (dist_to_pipe / distance))
            
            # 가중치 적용
            k_repair += weight
            
            # 재작업 유형별 가중치 적용
            if "repair_type" in repairs_gdf.columns:
                repair_type = repairs_gdf.iloc[repair_idx].get("repair_type", "")
                if repair_type == "지상누수":
                    k_repair_ground += weight
                elif repair_type == "지하누수":
                    k_repair_under += weight
                elif repair_type == "긴급공사":
                    k_repair_emergency += weight
                elif repair_type == "관리대장":
                    k_repair_management += weight

        # 파이프 길이 계산 (최소 10m 적용)
        actual_pipe_length = pipe.geometry.length
        pipe_length = max(actual_pipe_length, MIN_PIPE_LENGTH)

        # 1m당 정규화 값 계산
        if pipe_length > 0:
            k_repair_per_m = k_repair / pipe_length
            k_repair_ground_per_m = k_repair_ground / pipe_length
            k_repair_under_per_m = k_repair_under / pipe_length
            k_repair_emergency_per_m = k_repair_emergency / pipe_length
            k_repair_management_per_m = k_repair_management / pipe_length
        else:
            k_repair_per_m = 0
            k_repair_ground_per_m = 0
            k_repair_under_per_m = 0
            k_repair_emergency_per_m = 0
            k_repair_management_per_m = 0

        k_repair_list.append(
            {
                "FTR_IDN": pipe["FTR_IDN"],
                "pipe_length": round(actual_pipe_length, 2),  # 파이프 길이 (미터)
                "K_repair": round(k_repair, 2),  # 가중치 적용으로 실수값
                "K_repair_per_m": round(
                    k_repair_per_m, 4
                ),  # 1m당 정규화 (소수점 4자리)
                "K_repair_ground": round(k_repair_ground, 2),
                "K_repair_ground_per_m": round(k_repair_ground_per_m, 4),
                "K_repair_under": round(k_repair_under, 2),
                "K_repair_under_per_m": round(k_repair_under_per_m, 4),
                "K_repair_emergency": round(k_repair_emergency, 2),
                "K_repair_emergency_per_m": round(k_repair_emergency_per_m, 4),
                "K_repair_management": round(k_repair_management, 2),
                "K_repair_management_per_m": round(k_repair_management_per_m, 4),
            }
        )

        # 진행률 표시
        if verbose and (idx + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed
            remaining = (len(pipes_gdf) - idx - 1) / rate
            print(
                f"    {idx + 1:,}/{len(pipes_gdf):,} 처리 완료 "
                f"(예상 남은 시간: {remaining:.1f}초)"
            )

    if verbose:
        elapsed = time.time() - start_time
        print(f"  처리 완료 (소요 시간: {elapsed:.1f}초)")

    return pd.DataFrame(k_repair_list)


def print_k_repair_statistics(df: pd.DataFrame, pipe_type: str) -> None:
    """K_repair 통계 출력

    Args:
        df: K_repair DataFrame
        pipe_type: 파이프 타입
    """
    print(f"\n{pipe_type} K_repair 통계:")
    print(f"  - 전체 파이프: {len(df):,}개")

    # 파이프 길이 통계
    if "pipe_length" in df.columns:
        print("\n  - 파이프 길이 통계:")
        print(f"    최소: {df['pipe_length'].min():.1f}m")
        print(f"    평균: {df['pipe_length'].mean():.1f}m")
        print(f"    최대: {df['pipe_length'].max():.1f}m")

    # K_repair 분포 (원본)
    k_repair_counts = df["K_repair"].value_counts().sort_index()

    print("\n  - K_repair 분포 (원본):")
    # 상위 10개만 표시
    for i, (k, count) in enumerate(k_repair_counts.items()):
        if i >= 10:
            print(f"    ... ({len(k_repair_counts) - 10}개 더)")
            break
        percentage = count / len(df) * 100
        print(f"    K_repair = {k}: {count:,}개 ({percentage:.1f}%)")

    # 원본 요약 통계
    print("\n  - K_repair 요약 (원본):")
    print(f"    평균: {df['K_repair'].mean():.2f}")
    print(f"    최대: {df['K_repair'].max()}")
    print(
        f"    재작업 있는 파이프: {(df['K_repair'] > 0).sum():,}개 "
        f"({(df['K_repair'] > 0).sum() / len(df) * 100:.1f}%)"
    )

    # 1m당 정규화 통계
    if "K_repair_per_m" in df.columns:
        print("\n  - K_repair 요약 (1m당 정규화):")
        print(f"    평균: {df['K_repair_per_m'].mean():.4f}")
        print(f"    최대: {df['K_repair_per_m'].max():.4f}")
        print(f"    표준편차: {df['K_repair_per_m'].std():.4f}")

    # 재작업 유형별 통계
    if "K_repair_ground" in df.columns and "K_repair_under" in df.columns:
        total_ground = df["K_repair_ground"].sum()
        total_under = df["K_repair_under"].sum()
        total_emergency = df.get("K_repair_emergency", pd.Series([0])).sum()
        total_management = df.get("K_repair_management", pd.Series([0])).sum()
        total_repairs = df["K_repair"].sum()

        if total_repairs > 0:
            print("\n  - 재작업 유형별 분포:")
            print(
                f"    지상누수: {total_ground:,}개 ({total_ground/total_repairs*100:.1f}%)"
            )
            print(
                f"    지하누수: {total_under:,}개 ({total_under/total_repairs*100:.1f}%)"
            )
            if "K_repair_emergency" in df.columns:
                print(
                    f"    긴급공사: {total_emergency:,}개 ({total_emergency/total_repairs*100:.1f}%)"
                )
            if "K_repair_management" in df.columns and total_management > 0:
                print(
                    f"    관리대장: {total_management:,}개 ({total_management/total_repairs*100:.1f}%)"
                )

            if "K_repair_ground_per_m" in df.columns:
                print("\n  - 1m당 평균:")
                print(f"    지상누수: {df['K_repair_ground_per_m'].mean():.4f}")
                print(f"    지하누수: {df['K_repair_under_per_m'].mean():.4f}")
                if "K_repair_emergency_per_m" in df.columns:
                    print(f"    긴급공사: {df['K_repair_emergency_per_m'].mean():.4f}")
                if "K_repair_management_per_m" in df.columns and total_management > 0:
                    print(f"    관리대장: {df['K_repair_management_per_m'].mean():.4f}")


def main() -> None:
    """메인 실행 함수"""
    # 명령줄 인자 파싱
    args = parse_arguments()

    # 설정 로드
    config = get_config()

    # 디렉토리 설정
    data_dir = Path(config.get("DATA_DIR", "data/raw"))
    results_dir = Path(args.output_dir)

    # 출력 디렉토리 생성
    results_dir.mkdir(parents=True, exist_ok=True)

    # 한글 폰트 설정
    setup_korean_font()

    print("=" * 60)
    print("파이프별 재작업 횟수(K_repair) 계산")
    print("=" * 60)
    print(f"매칭 거리: {args.distance}m")
    print(f"데이터 디렉토리: {data_dir}")
    print(f"결과 디렉토리: {results_dir}")
    print()

    # 1. 파이프 데이터 로드
    print("1. 파이프 데이터 로드 중...")
    pipe_lm_gdf = load_pipe_shapefile("PIPE_LM", data_dir, args.verbose)
    sply_ls_gdf = load_pipe_shapefile("SPLY_LS", data_dir, args.verbose)

    if pipe_lm_gdf is None and sply_ls_gdf is None:
        print("오류: 파이프 데이터를 로드할 수 없습니다.")
        return

    # 2. 재작업 데이터 로드
    print("\n2. 재작업 데이터 로드 중...")
    # 통합 재작업 데이터는 results/ 디렉토리에서 로드
    repair_data_dir = Path(config.get("RESULTS_DIR", "results"))

    # 통합 재작업 데이터 로드
    repairs_df = load_unified_repair_csv(repair_data_dir, args.verbose)

    if repairs_df is None:
        print("\n오류: 재작업 데이터를 로드할 수 없습니다.")
        print(f"다음 파일을 찾을 수 없습니다:")
        print(
            f"  - {repair_data_dir / 'main13_crop_520' / '누수공사_통합_520_위치추가.csv'}"
        )
        print("\n먼저 재작업 데이터 파일을 생성해주세요.")
        print("예: python src/main13_crop_520.py")
        return

    print(f"전체 재작업: {len(repairs_df):,}개")

    # 3. 좌표 변환
    print("\n3. 좌표 변환 중...")
    repairs_gdf = convert_repairs_to_geodataframe(repairs_df, args.verbose)

    # 4. K_repair 계산
    print(f"\n4. K_repair 계산 중 (거리: {args.distance}m)...")

    # PIPE_LM 처리
    if pipe_lm_gdf is not None:
        print("\nPIPE_LM 처리 중...")
        pipe_lm_k_repair = calculate_k_repair_with_strtree(
            pipe_lm_gdf, repairs_gdf, args.distance, args.verbose
        )

        # 통계 출력
        print_k_repair_statistics(pipe_lm_k_repair, "PIPE_LM")

        # CSV 저장
        output_file = results_dir / "repair_pipe_lm.csv"
        pipe_lm_k_repair.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n결과 저장: {output_file}")

    # SPLY_LS 처리
    if sply_ls_gdf is not None:
        print("\nSPLY_LS 처리 중...")
        sply_ls_k_repair = calculate_k_repair_with_strtree(
            sply_ls_gdf, repairs_gdf, args.distance, args.verbose
        )

        # 통계 출력
        print_k_repair_statistics(sply_ls_k_repair, "SPLY_LS")

        # CSV 저장
        output_file = results_dir / "repair_sply_ls.csv"
        sply_ls_k_repair.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n결과 저장: {output_file}")

    print("\n" + "=" * 60)
    print("K_repair 계산 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
