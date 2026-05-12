"""파이프-도로 중첩 분석을 통한 교통 정보 CSV 생성 스크립트."""

import argparse
import re
import warnings
from pathlib import Path

import geopandas as gpd

from src.common.config import RAW_DATA_DIR, REGION_CODE_PATTERN, RESULTS_DIR
from src.common.shapefile_loader import load_pipe_shapefile
from src.road_loader import load_road_data
from src.traffic_analyzer import (
    analyze_pipe_traffic,
    create_road_buffers,
    save_traffic_csv,
)

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def get_export_directories(base_dir: Path) -> list[Path]:
    """export_shp_* 디렉토리들을 찾고 정렬"""
    export_dirs = list(base_dir.glob("export_shp_*"))
    export_dirs.sort()
    return export_dirs


def extract_region_code(dirname: str) -> str:
    """디렉토리명에서 지역 코드 추출"""
    match = re.search(REGION_CODE_PATTERN, dirname)
    return match.group(1) if match else "unknown"


def process_region(
    region_code: str,
    road_buffered_gdf: gpd.GeoDataFrame,
    output_dir: Path,
    verbose: bool = True,
) -> dict[str, dict[str, float]]:
    """특정 지역의 파이프 데이터 처리"""
    print(f"\n=== {region_code} 지역 처리 중 ===")

    stats = {}

    # PIPE_LM 처리
    pipe_gdf = load_pipe_shapefile(RAW_DATA_DIR, region_code, "PIPE_LM", verbose)
    if pipe_gdf is not None:
        result, pipe_stats = analyze_pipe_traffic(pipe_gdf, road_buffered_gdf, verbose)
        output_path = output_dir / f"{region_code}_pipe_traffic.csv"
        save_traffic_csv(result, output_path, verbose)
        stats["pipe"] = pipe_stats

    # SPLY_LS 처리
    sply_gdf = load_pipe_shapefile(RAW_DATA_DIR, region_code, "SPLY_LS", verbose)
    if sply_gdf is not None:
        result, sply_stats = analyze_pipe_traffic(sply_gdf, road_buffered_gdf, verbose)
        output_path = output_dir / f"{region_code}_sply_traffic.csv"
        save_traffic_csv(result, output_path, verbose)
        stats["sply"] = sply_stats

    return stats


def print_final_statistics(all_stats: dict[str, dict[str, dict[str, float]]]) -> None:
    """최종 통계 출력"""
    print("\n=== 전체 처리 완료 ===")
    for region_code, export_stats in all_stats.items():
        print(f"\n지역 {region_code}:")
        for pipe_type, stats in export_stats.items():
            print(f"  {pipe_type.upper()}:")
            print(f"    - 전체: {stats['total']}개")
            print(f"    - 매칭: {stats['matched']}개 ({stats['match_rate']:.1f}%)")


def load_and_buffer_roads(verbose: bool) -> gpd.GeoDataFrame | None:
    """도로 데이터 로드 및 버퍼 생성"""
    print("\n도로 데이터 로딩 중...")
    road_gdf = load_road_data(RAW_DATA_DIR, verbose=verbose)
    if road_gdf is None:
        return None
    return create_road_buffers(road_gdf, verbose)


def main() -> None:
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="파이프-도로 중첩 분석을 통한 교통 정보 CSV 생성"
    )
    parser.add_argument("--output-dir", type=str, help="출력 디렉토리 경로")
    parser.add_argument(
        "--verbose", action="store_true", default=True, help="상세 정보 출력"
    )
    parser.add_argument("--quiet", action="store_true", help="최소 정보만 출력")

    args = parser.parse_args()
    verbose = not args.quiet

    print("파이프-도로 중첩 분석 시작...")

    # 출력 디렉토리 설정
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR / "traffic"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"출력 디렉토리: {output_dir}")

    # 도로 데이터 로드 및 버퍼 생성
    road_buffered_gdf = load_and_buffer_roads(verbose)
    if road_buffered_gdf is None:
        return

    # export 디렉토리 찾기
    export_dirs = get_export_directories(RAW_DATA_DIR)
    if not export_dirs:
        print("오류: export 디렉토리를 찾을 수 없습니다.")
        return
    print(f"발견된 export 디렉토리: {len(export_dirs)}개")

    # 각 지역별 처리
    all_stats = {}
    for export_dir in export_dirs:
        region_code = extract_region_code(export_dir.name)
        stats = process_region(region_code, road_buffered_gdf, output_dir, verbose)
        if stats:
            all_stats[region_code] = stats

    # 최종 통계 출력
    print_final_statistics(all_stats)
    print(f"\n결과 파일 위치: {output_dir}")


if __name__ == "__main__":
    main()
