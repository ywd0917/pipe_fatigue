"""도로 데이터를 시각화하는 스크립트."""

import argparse
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt

from src.common import korean_font_utils
from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.visualization_utils import setup_plot_style
from src.road_loader import load_road_data as load_road_from_file
from src.road_visualizer import (
    DPI,
    FIGURE_SIZE_CENTER,
    FIGURE_SIZE_FULL,
    analyze_road_attributes,
    create_road_legend_elements,
    extract_center_area,
    plot_roads_by_class_and_width,
    print_road_analysis,
)

# 비대화형 모드 체크
if "--show" not in sys.argv:
    matplotlib.use("Agg")

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def setup_korean_font() -> None:
    """한글 폰트 설정"""
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")
    else:
        print("한글 폰트를 찾지 못했습니다. 영문 레이블을 사용합니다.")


def plot_road_network(
    gdf: gpd.GeoDataFrame,
    figsize: tuple[int, int] = FIGURE_SIZE_FULL,
    output_file: str | Path | None = None,
    show_plot: bool = False,
) -> None:
    """도로 네트워크를 시각화합니다.

    Args:
        gdf: 도로 데이터 GeoDataFrame
        figsize: 그림 크기
        output_file: 저장할 파일 경로 (None이면 저장하지 않음)
        show_plot: 플롯을 화면에 표시할지 여부
    """
    # 한글 폰트 설정
    setup_korean_font()

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=figsize, dpi=100)

    # ROA_CLS_SE와 ROAD_BT 필드 확인
    has_roa_cls = "ROA_CLS_SE" in gdf.columns
    has_road_bt = "ROAD_BT" in gdf.columns

    if not has_roa_cls:
        print("경고: ROA_CLS_SE 필드가 없습니다. 기본 색상을 사용합니다.")
    if not has_road_bt:
        print("경고: ROAD_BT 필드가 없습니다. 기본 선 두께를 사용합니다.")

    # 도로 시각화
    plot_roads_by_class_and_width(ax, gdf, has_roa_cls, has_road_bt)

    # 축 설정
    ax.set_xlabel("경도 (Easting)", fontsize=12)
    ax.set_ylabel("위도 (Northing)", fontsize=12)
    ax.set_title("대구광역시 도로 네트워크", fontsize=16, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    # 범례 추가
    if has_roa_cls or has_road_bt:
        legend_elements = create_road_legend_elements(gdf, has_roa_cls, has_road_bt)
        ax.legend(
            handles=legend_elements,
            loc="upper right",
            fontsize=10,
            framealpha=0.9,
            title="도로 구분",
        )

    # 레이아웃 조정 및 저장
    plt.tight_layout()
    if output_file:
        plt.savefig(output_file, dpi=DPI, bbox_inches="tight")
        print(f"도로 네트워크 이미지 저장: {output_file}")

    if show_plot:
        plt.show()
    else:
        plt.close()


def plot_center_area_if_needed(
    gdf: gpd.GeoDataFrame, args: argparse.Namespace, output_file: Path
) -> None:
    """필요한 경우 중심부 영역 시각화"""
    if args.no_center or len(gdf) == 0:
        return

    center_gdf = extract_center_area(gdf)
    if len(center_gdf) == 0:
        return

    print(f"\n중심부 영역 도로 구간 수: {len(center_gdf)}")

    # 중심부 출력 파일 경로
    if args.output:
        center_output = (
            output_file.parent / f"{output_file.stem}_center{output_file.suffix}"
        )
    else:
        center_filename = (
            f"{args.prefix}road_network_center.png"
            if args.prefix
            else "road_network_center.png"
        )
        center_output = RESULTS_DIR / center_filename

    plot_road_network(
        center_gdf,
        output_file=center_output,
        figsize=FIGURE_SIZE_CENTER,
        show_plot=args.show,
    )


def get_output_file_path(args: argparse.Namespace) -> Path:
    """출력 파일 경로 결정"""
    if args.output:
        return Path(args.output)

    filename = f"{args.prefix}road_network.png" if args.prefix else "road_network.png"
    return RESULTS_DIR / filename


def main() -> None:
    """메인 함수"""
    parser = argparse.ArgumentParser(description="도로 데이터 시각화")
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    parser.add_argument(
        "--prefix", type=str, default="", help="출력 파일 이름에 추가할 접두사"
    )
    parser.add_argument(
        "--no-center", action="store_true", help="중심부 영역 시각화를 생략"
    )
    parser.add_argument("--output", type=str, help="출력 파일 경로")

    args = parser.parse_args()

    # RESULTS 디렉토리 생성
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 도로 데이터 로드
    print("도로 데이터 로딩 중...")
    gdf = load_road_from_file(RAW_DATA_DIR)
    if gdf is None:
        return

    # 도로 속성 분석
    analysis = analyze_road_attributes(gdf)
    print_road_analysis(analysis)

    # 출력 파일 경로 설정
    output_file = get_output_file_path(args)

    # 전체 도로 네트워크 시각화
    plot_road_network(gdf, output_file=output_file, show_plot=args.show)

    # 중심부 영역 시각화
    plot_center_area_if_needed(gdf, args, output_file)


if __name__ == "__main__":
    main()
