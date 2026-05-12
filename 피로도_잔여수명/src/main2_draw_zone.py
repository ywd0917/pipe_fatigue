"""
Zone 영역 시각화 스크립트
WEA_LRGZ_AS, WEA_MDLZ_AS, WEA_SCDZ_AS, WEA_SMLZ_AS 영역을 시각화
"""

import argparse
import re
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt

from src.common import korean_font_utils
from src.common.config import RAW_DATA_DIR, REGION_CODE_PATTERN, RESULTS_DIR
from src.common.visualization_utils import setup_plot_style
from src.ftr_visualizer import (
    analyze_ftr_idn,
    calculate_plot_bounds,
    generate_distinct_colors,
    load_background_smlz,
    load_shapefile_with_validation,
    plot_geometry_by_type,
)
from src.zone_visualizer import (
    calculate_bounds_with_margin,
    create_zone_legend_elements,
    get_all_zone_files,
    get_zone_metadata,
    load_zone_data,
    plot_zone_labels,
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


def plot_zones(
    zone_data: dict[str, gpd.GeoDataFrame],
    output_path: Path,
    title: str = "Zone 영역 시각화",
    show_plot: bool = False,
    single_zone: bool = False,
) -> None:
    """Zone 영역 시각화"""
    # 한글 폰트 설정
    setup_korean_font()

    # 플롯 스타일 설정
    fig, ax = setup_plot_style()

    zone_metadata = get_zone_metadata()
    zone_order = ["lrgz", "mdlz", "scdz", "smlz"]

    # 각 Zone 그리기
    for zone_type in zone_order:
        if zone_type in zone_data:
            gdf = zone_data[zone_type]
            color, _, _ = zone_metadata[zone_type]

            if single_zone:
                # 단일 Zone 표시 (내부 색칠)
                gdf.plot(
                    ax=ax,
                    facecolor=color,
                    edgecolor=color,
                    linewidth=1.5,
                    alpha=0.2,
                )
                # 경계선을 더 진하게
                gdf.plot(
                    ax=ax,
                    facecolor="none",
                    edgecolor=color,
                    linewidth=1.5,
                    alpha=0.8,
                )
                # 라벨 표시
                plot_zone_labels(ax, gdf, zone_type, color)
            else:
                # 전체 Zone 표시 (경계선만)
                gdf.plot(
                    ax=ax,
                    facecolor="none",
                    edgecolor=color,
                    linewidth=1.5,
                    alpha=0.8,
                )

    # 전체 경계 설정
    all_gdfs = list(zone_data.values())
    if all_gdfs:
        minx, miny, maxx, maxy = calculate_bounds_with_margin(all_gdfs)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)

    # 제목 및 라벨 설정
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")

    # 범례 추가
    legend_elements = create_zone_legend_elements(zone_data, zone_metadata)
    ax.legend(handles=legend_elements, loc="upper right", fontsize=10)

    # 축 비율 유지
    ax.set_aspect("equal")

    # 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()
    plt.close()


def plot_shapefile_by_ftr_idn(
    shapefile_path: Path,
    output_path: Path,
    title: str = "FTR_IDN별 시각화",
    show_plot: bool = False,
    smlz_file: Path | None = None,
) -> None:
    """특정 shapefile을 FTR_IDN별로 랜덤 색상으로 시각화"""
    # 한글 폰트 설정
    setup_korean_font()

    try:
        # Shapefile 로드 및 검증
        gdf = load_shapefile_with_validation(shapefile_path)

        # FTR_IDN 분석
        unique_ids, _ = analyze_ftr_idn(gdf)

        # 색상 생성 및 매핑
        colors = generate_distinct_colors(len(unique_ids))
        color_map = dict(zip(unique_ids, colors, strict=False))

        # 플롯 생성
        fig, ax = setup_plot_style(figsize=(14, 10))

        # SMLZ 배경 그리기
        smlz_gdf = None
        if smlz_file:
            smlz_gdf = load_background_smlz(smlz_file, ax)

        # FTR_IDN별로 그리기
        total_objects_drawn = 0
        for ftr_id, group in gdf.groupby("_group_id"):
            color = color_map[ftr_id]
            objects_drawn = plot_geometry_by_type(ax, group, color)
            total_objects_drawn += objects_drawn

        # 경계 설정
        minx, miny, maxx, maxy = calculate_plot_bounds(gdf, smlz_gdf)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)

        # 제목 및 라벨 설정
        ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
        ax.set_xlabel("경도", fontsize=12)
        ax.set_ylabel("위도", fontsize=12)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_aspect("equal")

        # 저장
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"\n이미지 저장 완료: {output_path}")
        print(f"그려진 총 객체 수: {total_objects_drawn} (원본: {len(gdf)})")

        if show_plot:
            plt.show()
        plt.close()

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


def process_zone_visualization(args: argparse.Namespace) -> None:
    """Zone 시각화 처리"""
    print("Zone 영역 시각화 시작...")
    print(f"데이터 디렉토리: {RAW_DATA_DIR}")

    try:
        # Zone 파일 찾기
        all_zone_files = get_all_zone_files(RAW_DATA_DIR)

        if not all_zone_files:
            print("오류: Zone shapefile을 찾을 수 없습니다.")
            return

        # 각 디렉토리별로 처리
        for dir_version, zone_files in all_zone_files.items():
            print(f"\n=== {dir_version} 버전 처리 중 ===")

            # Zone 데이터 로드
            zone_data = load_zone_data(zone_files, args.zone)

            if not zone_data:
                print("경고: Zone 데이터가 없습니다.")
                continue

            # 제목 설정
            if args.title:
                title = args.title
            elif args.zone:
                zone_names = {
                    "lrgz": "대블록 (LRGZ)",
                    "mdlz": "중블록 (MDLZ)",
                    "scdz": "2차구역 (SCDZ)",
                    "smlz": "소블록 (SMLZ)",
                }
                title = f"{zone_names[args.zone]} 영역"
            else:
                title = "Zone 영역 시각화"

            # 출력 경로 설정
            if args.output:
                user_output = Path(args.output)
                if user_output.parent == Path():
                    output_path = RESULTS_DIR / f"{dir_version}_{user_output.name}"
                else:
                    output_path = (
                        user_output.parent / f"{dir_version}_{user_output.name}"
                    )
            else:
                if args.zone:
                    base_name = f"{dir_version}_zone_{args.zone}.png"
                else:
                    base_name = f"{dir_version}_zone_all.png"
                output_path = RESULTS_DIR / base_name

            # 출력 디렉토리 생성
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Zone 시각화
            plot_zones(
                zone_data,
                output_path,
                title,
                show_plot=args.show,
                single_zone=(args.zone is not None),
            )

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


def process_ftr_visualization(args: argparse.Namespace) -> None:
    """FTR_IDN별 시각화 처리"""
    input_path = Path(args.file)

    # 파일 경로 처리
    if input_path.is_absolute() and input_path.exists():
        shapefile_paths = [input_path]
    else:
        # 파일명만 주어진 경우 모든 export 디렉토리에서 찾기
        filename = input_path.name
        shapefile_paths = []

        export_dirs = sorted(
            [
                d
                for d in RAW_DATA_DIR.iterdir()
                if d.is_dir() and d.name.startswith("export_shp_")
            ]
        )

        for export_dir in export_dirs:
            shapefile_path = export_dir / filename
            if shapefile_path.exists():
                shapefile_paths.append(shapefile_path)

        if not shapefile_paths:
            print(f"오류: 파일을 찾을 수 없습니다 - {filename}")
            return

    # 각 shapefile 처리
    for shapefile_path in shapefile_paths:
        # 버전 정보 추출
        dir_version = None
        for parent in shapefile_path.parents:
            if parent.name.startswith("export_shp_"):
                match = re.search(REGION_CODE_PATTERN, parent.name)
                dir_version = match.group(1) if match else "unknown"
                break

        # 출력 경로 설정
        if args.output:
            user_output = Path(args.output)
            if user_output.parent == Path():
                if dir_version:
                    output_path = RESULTS_DIR / f"{dir_version}_{user_output.name}"
                else:
                    output_path = RESULTS_DIR / user_output.name
            else:
                output_path = user_output
        else:
            clean_name = shapefile_path.stem.replace("V_WTL_", "").replace("WTL_", "")
            if dir_version:
                output_path = RESULTS_DIR / f"{dir_version}_{clean_name}.png"
            else:
                output_path = RESULTS_DIR / f"{clean_name}.png"

        # 출력 디렉토리 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 제목 설정
        if args.title:
            title = args.title
        else:
            filename = shapefile_path.stem
            if dir_version:
                title = f"{filename} - FTR_IDN별 시각화 ({dir_version})"
            else:
                title = f"{filename} - FTR_IDN별 시각화"

        # SMLZ 파일 찾기
        smlz_file = None
        smlz_path = shapefile_path.parent / "WEA_SMLZ_AS.shp"
        if smlz_path.exists():
            smlz_file = smlz_path

        print(f"\nShapefile 시각화 시작: {shapefile_path}")

        # FTR_IDN별 시각화
        plot_shapefile_by_ftr_idn(
            shapefile_path,
            output_path,
            title,
            show_plot=args.show,
            smlz_file=smlz_file,
        )


def main() -> None:
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Zone 영역 시각화 스크립트")
    parser.add_argument(
        "--zone",
        choices=["lrgz", "mdlz", "scdz", "smlz"],
        help="표시할 특정 Zone 선택",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="특정 shapefile 경로 (FTR_IDN별 시각화)",
    )
    parser.add_argument("--output", type=str, help="출력 파일 경로")
    parser.add_argument("--title", type=str, help="그래프 제목")
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="비대화형 모드로 실행",
    )

    args = parser.parse_args()

    # --file과 --zone 옵션 동시 사용 체크
    if args.file and args.zone:
        print("오류: --file과 --zone 옵션은 동시에 사용할 수 없습니다.")
        return

    # FTR_IDN별 시각화
    if args.file:
        process_ftr_visualization(args)
    # Zone 시각화
    else:
        process_zone_visualization(args)


if __name__ == "__main__":
    main()
