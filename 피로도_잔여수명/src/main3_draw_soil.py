"""
Soil (지질) 데이터 시각화 스크립트
Geology_250K 시리즈 shapefile들을 시각화
"""

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from src import soil_loader
from src.common import korean_font_utils
from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.visualization_utils import setup_plot_style
from src.soil_visualizer import (
    analyze_layer_data,
    get_soil_files,
    load_soil_layer,
    plot_frame_background,
    plot_integrated_layers,
    plot_layer_by_group,
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
        print("경고: 한글 폰트를 찾을 수 없습니다. 한글이 깨질 수 있습니다.")


def plot_individual_file(
    file_path: Path,
    output_path: Path,
    group_by: str | None = None,
    title: str | None = None,
    show_plot: bool = False,
    show_frame: bool = True,
) -> None:
    """개별 파일 시각화"""
    setup_korean_font()

    # 데이터 로드
    gdf = load_soil_layer(file_path)
    if gdf is None:
        return

    # 파일 타입 확인
    file_type = soil_loader.get_file_type_from_path(file_path)

    # 그룹화 필드 결정
    if group_by is None:
        group_by, _ = analyze_layer_data(gdf, file_type)
    elif group_by not in gdf.columns:
        print(f"경고: '{group_by}' 컬럼이 없습니다. 전체를 하나로 표시합니다.")
        group_by = None

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(14, 10))

    # Frame 배경 표시 (옵션)
    if show_frame and file_type != "frame":
        frame_path = file_path.parent / "Geology_250K_Frame.shp"
        if frame_path.exists():
            frame_gdf = load_soil_layer(frame_path)
            if frame_gdf is not None:
                plot_frame_background(ax, frame_gdf)

    # 데이터 시각화
    legend_elements = []
    if group_by:
        legend_elements = plot_layer_by_group(ax, gdf, group_by, file_type)
    else:
        # 전체를 하나의 색상으로
        geom_types = gdf.geometry.geom_type.unique()
        if any(t in ["Polygon", "MultiPolygon"] for t in geom_types):
            gdf.plot(
                ax=ax,
                facecolor="#4682B4",
                edgecolor="black",
                linewidth=0.5,
                alpha=0.7,
                zorder=1,
            )
        elif any(t in ["LineString", "MultiLineString"] for t in geom_types):
            gdf.plot(ax=ax, color="#4682B4", linewidth=1.5, alpha=0.8, zorder=2)

    # 제목 설정
    if title is None:
        if group_by:
            title = f"{file_path.stem} - {group_by}별 시각화"
        else:
            title = f"{file_path.stem} 시각화"

    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")

    # 범례 추가
    if legend_elements and len(legend_elements) <= 20:
        ax.legend(handles=legend_elements, loc="best", fontsize=8)

    ax.set_aspect("equal", adjustable="box")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()


def plot_all_layers(
    soil_files: dict[str, Path],
    output_path: Path,
    title: str = "지질도 통합 시각화",
    show_plot: bool = False,
    layers: list[str] | None = None,
) -> None:
    """모든 레이어 통합 시각화"""
    setup_korean_font()

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(16, 12))

    # 표시할 레이어 결정
    if layers is None:
        layers = ["frame", "litho", "boundary", "fault"]

    # 통합 레이어 시각화
    legend_elements = plot_integrated_layers(ax, soil_files, layers, RAW_DATA_DIR)

    # 제목 및 라벨 설정
    ax.set_title(title, fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.2, linestyle="--")

    # 범례 추가
    if legend_elements:
        if len(legend_elements) > 10:
            ax.legend(
                handles=legend_elements,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                fontsize=8,
            )
        else:
            ax.legend(handles=legend_elements, loc="best", fontsize=8)

    ax.set_aspect("equal", adjustable="box")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()


def process_individual_file(args: argparse.Namespace) -> None:
    """개별 파일 시각화 처리"""
    # 파일 찾기
    soil_files = get_soil_files(RAW_DATA_DIR)
    target_file = None

    for name, path in soil_files.items():
        if args.file in path.name:
            target_file = path
            break

    if target_file is None:
        print(f"오류: '{args.file}' 파일을 찾을 수 없습니다.")
        print("사용 가능한 파일:")
        for name, path in soil_files.items():
            print(f"  - {path.name}")
        return

    # 출력 경로 설정
    if args.output:
        output_path = Path(args.output)
    else:
        base_name = target_file.stem.replace("Geology_250K_", "")
        if args.group_by:
            output_path = RESULTS_DIR / f"soil_{base_name}_{args.group_by}.png"
        else:
            output_path = RESULTS_DIR / f"soil_{base_name}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 개별 파일 시각화
    plot_individual_file(
        target_file,
        output_path,
        group_by=args.group_by,
        title=args.title,
        show_plot=args.show,
        show_frame=not args.no_frame,
    )


def process_all_layers(args: argparse.Namespace) -> None:
    """전체 통합 시각화 처리"""
    soil_files = get_soil_files(RAW_DATA_DIR)

    # 출력 경로 설정
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = RESULTS_DIR / "soil_integrated.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 전체 레이어 시각화
    plot_all_layers(
        soil_files,
        output_path,
        title=args.title or "지질도 통합 시각화",
        show_plot=args.show,
        layers=args.layer,
    )


def parse_soil_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="Soil (지질) 데이터 시각화 스크립트")
    parser.add_argument(
        "--file", type=str, help="특정 shapefile 이름 (예: Geology_250K_Litho.shp)"
    )
    parser.add_argument(
        "--group-by", type=str, help="그룹화 필드 (예: age, TYPE, MAPNAME)"
    )
    parser.add_argument(
        "--layer",
        choices=["boundary", "fault", "frame", "litho"],
        nargs="+",
        help="표시할 레이어 선택 (기본값: 모든 레이어)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="출력 파일 경로 (기본값: results/soil_visualization.png)",
    )
    parser.add_argument("--title", type=str, help="그래프 제목")
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    parser.add_argument(
        "--no-frame", action="store_true", help="Frame 배경을 표시하지 않음"
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="비대화형 모드로 실행 (서버 환경에서 사용)",
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수"""
    args = parse_soil_arguments()

    print("Soil 데이터 시각화 시작...")
    print(f"데이터 디렉토리: {RAW_DATA_DIR}")

    try:
        # Soil 파일 찾기
        soil_files = get_soil_files(RAW_DATA_DIR)
        if not soil_files:
            print("오류: Soil shapefile을 찾을 수 없습니다.")
            return

        # 개별 파일 시각화 또는 전체 통합 시각화
        if args.file:
            process_individual_file(args)
        else:
            process_all_layers(args)

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
