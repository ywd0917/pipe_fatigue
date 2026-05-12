"""파이프-도로 중첩 검증을 위한 샘플링 기반 시각화 스크립트."""

import argparse
import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from src.common import korean_font_utils
from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.shapefile_loader import load_pipe_shapefile
from src.overlap_verifier import (
    DPI,
    FIGURE_SIZE,
    LABEL_FONT_SIZE,
    SAMPLE_SIZE,
    TITLE_FONT_SIZE,
    calculate_verification_stats,
    create_legend_elements,
    select_sample_pipes,
    visualize_pipe_sample,
)
from src.road_loader import load_road_data

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def setup_plot_style() -> None:
    """플롯 스타일 설정"""
    plt.style.use("default")
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")


def load_traffic_results(region_code: str, pipe_type: str) -> pd.DataFrame | None:
    """교통 분석 결과 CSV 로드"""
    csv_path = RESULTS_DIR / "traffic" / f"{region_code}_{pipe_type}_traffic.csv"

    if not csv_path.exists():
        print(f"오류: CSV 파일을 찾을 수 없습니다: {csv_path}")
        return None

    return pd.read_csv(csv_path, dtype={"RN_CD": str, "FTR_IDN": int})


def find_available_regions() -> list[str] | None:
    """사용 가능한 지역 코드 찾기"""
    traffic_dir = RESULTS_DIR / "traffic"
    if not traffic_dir.exists():
        print("오류: traffic 디렉토리를 찾을 수 없습니다.")
        print("\n해결 방법:")
        print("먼저 main7_pipe_traffic.py를 실행하여 교통 분석 결과를 생성해야 합니다.")
        print("실행 예시: python src/main7_pipe_traffic.py")
        return None

    csv_files = list(traffic_dir.glob("*_traffic.csv"))
    if not csv_files:
        print("오류: traffic CSV 파일을 찾을 수 없습니다.")
        print("\n해결 방법:")
        print("main7_pipe_traffic.py를 실행하여 교통 분석 결과 CSV 파일을 생성하세요.")
        print("실행 예시: python src/main7_pipe_traffic.py")
        return None

    # 지역 코드 추출
    region_codes = set()
    for csv_file in csv_files:
        parts = csv_file.stem.split("_")
        if len(parts) >= 2:
            region_codes.add(parts[0])

    return sorted(list(region_codes))


def create_verification_plot(
    sample_ids: list[int],
    matching_info: dict[int, str | None],
    pipe_gdf: gpd.GeoDataFrame,
    road_gdf: gpd.GeoDataFrame,
    region_code: str,
    pipe_type: str,
) -> tuple[Any, dict[str, Any]]:
    """검증 플롯 생성"""
    n_samples = len(sample_ids)
    n_cols = 4
    n_rows = (n_samples + n_cols - 1) // n_cols

    # 그림 생성
    fig, axes = plt.subplots(n_rows, n_cols, figsize=FIGURE_SIZE)
    if n_rows == 1:
        axes = axes.reshape(1, -1)

    # 전체 제목
    fig.suptitle(
        f"파이프-도로 중첩 검증 샘플 (지역: {region_code}, {pipe_type.upper()})",
        fontsize=TITLE_FONT_SIZE + 2,
        fontweight="bold",
    )

    # 각 샘플 시각화
    for idx, (sample_id, ax) in enumerate(zip(sample_ids, axes.flat, strict=False)):
        matched_road = matching_info.get(sample_id)
        title = f"샘플 {idx + 1}"
        visualize_pipe_sample(pipe_gdf, road_gdf, sample_id, matched_road, ax, title)

    # 사용하지 않는 서브플롯 숨기기
    for idx in range(n_samples, n_rows * n_cols):
        axes.flat[idx].axis("off")

    # 범례 추가
    legend_elements = create_legend_elements()
    fig.legend(
        handles=legend_elements,
        loc="center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=5,
        fontsize=LABEL_FONT_SIZE,
    )

    # 통계 계산
    # traffic_df는 상위 함수에서 전달받아야 하므로 더미 통계 반환
    stats = {
        "matched_count": len([v for v in matching_info.values() if v is not None]),
        "unmatched_count": len([v for v in matching_info.values() if v is None]),
        "total_samples": len(sample_ids),
    }

    return fig, stats


def get_region_code(args: argparse.Namespace) -> str:
    """지역 코드 결정"""
    if args.region_code:
        return str(args.region_code)

    region_codes = find_available_regions()
    if not region_codes:
        raise ValueError("사용 가능한 지역 코드를 찾을 수 없습니다.")
    print(f"발견된 지역 코드: {', '.join(region_codes)}")
    print(f"첫 번째 지역 코드({region_codes[0]})로 진행합니다.")
    return region_codes[0]


def load_all_data(
    region_code: str, pipe_type: str
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame] | None:
    """모든 데이터 로드"""
    print("\n데이터 로딩 중...")
    road_gdf = load_road_data(RAW_DATA_DIR)
    if road_gdf is None:
        return None

    pipe_gdf = load_pipe_shapefile(
        RAW_DATA_DIR, region_code, "PIPE_LM" if pipe_type == "pipe" else "SPLY_LS"
    )
    if pipe_gdf is None:
        return None

    traffic_df = load_traffic_results(region_code, pipe_type)
    if traffic_df is None:
        return None

    return road_gdf, pipe_gdf, traffic_df


def save_and_show_plot(fig: Any, output_path: Path, show: bool) -> None:
    """플롯 저장 및 표시"""
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI, bbox_inches="tight")
    print(f"\n검증 이미지 저장: {output_path}")

    if show:
        plt.show()
    else:
        plt.close()


def print_statistics(stats: dict[str, Any]) -> None:
    """통계 정보 출력"""
    print("\n=== 검증 통계 ===")
    print(f"전체 파이프: {stats['total_pipes']}개")
    print(f"분석된 파이프: {stats['analyzed_pipes']}개")
    print(f"매칭된 파이프: {stats['matched_pipes']}개 ({stats['match_rate']:.1f}%)")
    print(f"검증 샘플: {stats['sample_count']}개")


def main() -> None:
    """메인 함수"""
    parser = argparse.ArgumentParser(description="파이프-도로 중첩 검증 (샘플링 기반)")
    parser.add_argument(
        "region_code",
        type=str,
        nargs="?",
        default=None,
        help="지역 코드 - 생략 시 첫 번째 발견된 지역 사용",
    )
    parser.add_argument(
        "--pipe-type", type=str, choices=["pipe", "sply"], default="pipe"
    )
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--output-dir", type=str, help="출력 디렉토리 경로")
    parser.add_argument("--show", action="store_true", help="화면에 표시")

    args = parser.parse_args()
    if not args.show:
        matplotlib.use("Agg")

    region_code = get_region_code(args)
    if not region_code:
        return

    print(f"파이프-도로 중첩 검증 시작 (지역: {region_code}, 유형: {args.pipe_type})")
    setup_plot_style()

    # 데이터 로드
    data = load_all_data(region_code, args.pipe_type)
    if data is None:
        return
    road_gdf, pipe_gdf, traffic_df = data

    # 샘플 선택 및 시각화
    sample_ids, matching_info = select_sample_pipes(
        pipe_gdf, traffic_df, args.sample_size
    )
    fig, stats = create_verification_plot(
        sample_ids, matching_info, pipe_gdf, road_gdf, region_code, args.pipe_type
    )

    # 출력 설정
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else RESULTS_DIR / "overlap_verification"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = (
        output_dir / f"verification_{region_code}_{args.pipe_type}_samples.png"
    )

    save_and_show_plot(fig, output_file, args.show)

    # 통계 출력
    print_statistics(calculate_verification_stats(pipe_gdf, traffic_df, sample_ids))


if __name__ == "__main__":
    main()
