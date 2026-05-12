"""
복구 작업 위치 시각화 스크립트
- data/repair 폴더의 CSV 파일을 읽어서 위치를 지도에 표시
- EPSG:5179 (Korea 2000 / Central Belt 2010) 좌표계 사용
- 필터링 없이 모든 데이터를 표시
"""

import argparse
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from src.common import korean_font_utils
from src.common.config import DATA_DIR, RAW_DATA_DIR, RESULTS_DIR
from src.common.shapefile_loader import load_all_mdlz_shapefiles
from src.common.visualization_utils import setup_plot_style
from src.repair_loader import load_all_repair_data
from src.repair_visualizer import (
    calculate_repair_bounds,
    plot_mdlz_background,
    plot_repair_points,
)

# 비대화형 모드 체크
if "--no-interactive" in sys.argv:
    matplotlib.use("Agg")

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def setup_korean_font() -> None:
    """한글 폰트 설정"""
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")
    else:
        print("경고: 한글 폰트를 찾을 수 없습니다.")


def plot_repair_locations(
    repair_data: dict[str, pd.DataFrame],
    output_path: Path,
    title: str = "복구 작업 위치 분포",
    show_plot: bool = False,
    mdlz_gdf: gpd.GeoDataFrame | None = None,
) -> None:
    """복구 작업 위치를 지도에 표시"""
    setup_korean_font()

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(16, 12))

    # MDLZ 배경 그리기
    plot_mdlz_background(ax, mdlz_gdf)

    # 복구 작업 점 그리기
    legend_elements, total_points = plot_repair_points(ax, repair_data)

    # 경계 설정
    if mdlz_gdf is not None and len(mdlz_gdf) > 0:
        # MDLZ 경계 우선 사용
        bounds = mdlz_gdf.total_bounds
        x_margin = (bounds[2] - bounds[0]) * 0.05
        y_margin = (bounds[3] - bounds[1]) * 0.05
        ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
        ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)
    else:
        # 복구 데이터 경계 사용
        all_bounds = calculate_repair_bounds(repair_data)
        if all_bounds is not None:
            x_margin = (all_bounds[2] - all_bounds[0]) * 0.1
            y_margin = (all_bounds[3] - all_bounds[1]) * 0.1
            ax.set_xlim(all_bounds[0] - x_margin, all_bounds[2] + x_margin)
            ax.set_ylim(all_bounds[1] - y_margin, all_bounds[3] + y_margin)

    # 제목 및 라벨 (EPSG:5179 좌표계)
    ax.set_title(title, fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel("X (EPSG:5179)", fontsize=12)
    ax.set_ylabel("Y (EPSG:5179)", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 범례 추가
    if legend_elements:
        ax.legend(
            handles=legend_elements,
            loc="upper right",
            fontsize=11,
            title="복구 작업 유형",
            title_fontsize=12,
            framealpha=0.9,
        )

    # 통계 정보 표시
    stats_text = f"총 복구 작업: {total_points}건"
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=12,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # 저장 및 표시
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()

    plt.close()


def plot_repair_by_type(
    repair_data: dict[str, pd.DataFrame],
    output_dir: Path,
    show_plot: bool = False,
    mdlz_gdf: gpd.GeoDataFrame | None = None,
) -> None:
    """각 복구 작업 유형별로 개별 이미지 생성"""
    from src.repair_visualizer import get_repair_colors

    repair_colors = get_repair_colors()

    for repair_type, df in repair_data.items():
        if repair_type not in repair_colors:
            continue

        # 개별 데이터로 plot_repair_locations 호출
        single_data = {repair_type: df}
        output_path = output_dir / f"{repair_type}_locations.png"
        title = f"{repair_colors[repair_type][1]} 위치 분포"

        plot_repair_locations(
            single_data,
            output_path,
            title=title,
            show_plot=show_plot,
            mdlz_gdf=mdlz_gdf,
        )


def parse_repair_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="복구 작업 위치 시각화 스크립트")
    parser.add_argument(
        "--output-dir", type=str, help="출력 디렉토리 (기본값: results/)"
    )
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    parser.add_argument(
        "--separate", action="store_true", help="각 복구 작업 유형별로 개별 이미지 생성"
    )
    parser.add_argument(
        "--no-interactive", action="store_true", help="비대화형 모드로 실행"
    )
    parser.add_argument(
        "--use-sample", action="store_true", help="좌표가 포함된 샘플 데이터 사용"
    )
    return parser.parse_args()


def load_repair_data_with_option(args: argparse.Namespace) -> dict[str, pd.DataFrame]:
    """옵션에 따라 복구 데이터 로드"""
    print("\n복구 작업 데이터 로드 중...")

    if args.use_sample:
        print("좌표가 포함된 샘플 데이터를 사용합니다.")
        return load_all_repair_data(DATA_DIR, verbose=True, use_sample=True)

    return load_all_repair_data(DATA_DIR, verbose=True, use_sample=False)


def main() -> None:
    """메인 실행 함수"""
    args = parse_repair_arguments()

    # 출력 디렉토리 설정
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print("복구 작업 위치 시각화 시작...")
    print(f"데이터 디렉토리: {DATA_DIR}")
    print("좌표계: EPSG:5179 (Korea 2000 / Central Belt 2010)")

    # 복구 데이터 로드
    repair_data = load_repair_data_with_option(args)
    if not repair_data:
        print("오류: 복구 작업 데이터를 로드할 수 없습니다.")
        return

    # MDLZ (중구역) 데이터 로드 (EPSG:5179)
    print("\nMDLZ (중구역) 데이터 로드 중...")
    mdlz_gdf = load_all_mdlz_shapefiles(RAW_DATA_DIR, verbose=True)
    if mdlz_gdf is not None and len(mdlz_gdf) > 0:
        if mdlz_gdf.crs is None:
            mdlz_gdf = mdlz_gdf.set_crs("EPSG:5179")
            print("MDLZ 데이터에 EPSG:5179 좌표계 설정")
        elif mdlz_gdf.crs != "EPSG:5179":
            mdlz_gdf = mdlz_gdf.to_crs("EPSG:5179")
            print("MDLZ 데이터를 EPSG:5179로 변환")

    # 전체 통합 이미지 생성
    print("\n전체 복구 작업 위치 시각화...")
    output_path = output_dir / "all_repair_locations.png"
    plot_repair_locations(
        repair_data,
        output_path,
        title="전체 복구 작업 위치 분포 (EPSG:5179)",
        show_plot=args.show,
        mdlz_gdf=mdlz_gdf,
    )

    # 개별 이미지 생성 (옵션)
    if args.separate:
        print("\n개별 복구 작업 유형별 시각화...")
        plot_repair_by_type(
            repair_data, output_dir, show_plot=args.show, mdlz_gdf=mdlz_gdf
        )

    print("\n시각화 완료!")


if __name__ == "__main__":
    main()
