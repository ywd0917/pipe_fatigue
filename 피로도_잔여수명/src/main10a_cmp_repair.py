"""
파이프 피로 손상 및 복구 작업 통합 시각화 스크립트
- CSV 파일의 피로 손상 데이터(*_D_final)를 기반으로 파이프를 색상으로 시각화
- 복구 작업 위치를 점으로 추가 표시
"""

import argparse
import sys
import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from src.common.config import (
    DATA_DIR,
    FATIGUE_PIPE_LM_CSV,
    FATIGUE_SPLY_LS_CSV,
    RAW_DATA_DIR,
    RESULTS_DIR,
)
from src.common.shapefile_loader import (
    get_smlz_shapefile_path,
    load_pipe_shapefile,
)
from src.common.visualization_utils import setup_korean_font, setup_plot_style
from src.fatigue_loader import (
    get_fatigue_by_ftr_idn,
    load_fatigue_data,
)
from src.fatigue_visualizer import (
    add_fatigue_colorbar,
    calculate_fatigue_statistics,
    create_fatigue_colormap,
    create_log_norm,
    format_fatigue_stats_text,
    plot_fatigue_pipes,
    plot_smlz_background,
    prepare_fatigue_data,
)
from src.repair_loader import load_all_repair_data
from src.repair_visualizer import plot_repair_points_on_pipe

# 비대화형 모드 체크
if "--no-interactive" in sys.argv:
    matplotlib.use("Agg")

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def plot_pipe_fatigue_with_repair(
    pipe_gdf: gpd.GeoDataFrame,
    fatigue_dict: dict[str, float],
    repair_data: dict[str, pd.DataFrame],
    output_path: Path,
    title: str = "파이프 피로 손상 및 복구 작업 시각화",
    show_plot: bool = False,
    smlz_file: Path | None = None,
    show_repair: bool = True,
) -> None:
    """파이프 피로 손상 및 복구 작업 통합 시각화"""
    setup_korean_font()

    # 피로 손상 데이터 준비
    pipe_gdf = prepare_fatigue_data(pipe_gdf, fatigue_dict)

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(16, 12))

    # SMLZ 배경 그리기
    if smlz_file is not None:
        plot_smlz_background(ax, smlz_file)

    # 컬러맵과 정규화 객체 생성
    cmap = create_fatigue_colormap()
    norm = create_log_norm()

    # 파이프 피로 손상 시각화
    plot_fatigue_pipes(ax, pipe_gdf, cmap, norm)

    # 컬러바 추가
    add_fatigue_colorbar(ax, cmap, norm)

    # 전체 경계 설정
    bounds = pipe_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05
    ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)

    # 제목 및 라벨 설정
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 통계 계산
    stats = calculate_fatigue_statistics(pipe_gdf)

    # 복구 작업 점 추가
    repair_legend_elements: list[Any] = []
    total_repair_points = 0

    if show_repair and repair_data:
        try:
            repair_legend_elements, total_repair_points = plot_repair_points_on_pipe(
                ax, repair_data, smlz_file
            )
        except Exception as e:
            print(f"복구 작업 표시 중 오류: {e}")
            import traceback

            traceback.print_exc()

    # 통계 정보 표시
    stats_text = format_fatigue_stats_text(stats, total_repair_points)
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # 복구 작업 범례 추가
    if repair_legend_elements:
        repair_legend = ax.legend(
            handles=repair_legend_elements,
            loc="upper right",
            bbox_to_anchor=(0.98, 0.85),
            fontsize=9,
            title="복구 작업",
            title_fontsize=10,
        )
        ax.add_artist(repair_legend)

    # 저장 및 표시
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()


def load_pipe_fatigue_data() -> pd.DataFrame | None:
    """파이프 피로 손상 데이터 로드"""
    fatigue_dfs = []

    # PIPE_LM 피로 데이터
    pipe_lm_csv = FATIGUE_PIPE_LM_CSV
    if pipe_lm_csv.exists():
        print(f"\nPIPE_LM 피로 데이터 로드: {pipe_lm_csv}")
        pipe_lm_fatigue = load_fatigue_data(pipe_lm_csv)
        if pipe_lm_fatigue is not None:
            fatigue_dfs.append(pipe_lm_fatigue)

    # SPLY_LS 피로 데이터
    sply_ls_csv = FATIGUE_SPLY_LS_CSV
    if sply_ls_csv.exists():
        print(f"\nSPLY_LS 피로 데이터 로드: {sply_ls_csv}")
        sply_ls_fatigue = load_fatigue_data(sply_ls_csv)
        if sply_ls_fatigue is not None:
            fatigue_dfs.append(sply_ls_fatigue)

    if not fatigue_dfs:
        return None

    # 데이터 병합
    fatigue_df = pd.concat(fatigue_dfs, ignore_index=True)
    print(f"\n병합된 피로 데이터: 총 {len(fatigue_df)}개 레코드")

    if "FTR_CDE" in fatigue_df.columns:
        for ftr_cde, count in fatigue_df["FTR_CDE"].value_counts().items():
            print(f"  - {ftr_cde}: {count}개")

    return fatigue_df


def load_pipe_shapefiles(region_code: str) -> gpd.GeoDataFrame | None:
    """파이프 shapefile 로드 및 병합"""
    import geopandas as gpd

    gdfs = []

    # PIPE_LM 로드
    pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, region_code, "PIPE_LM")
    if pipe_lm_gdf is not None:
        gdfs.append(pipe_lm_gdf)

    # SPLY_LS 로드
    sply_ls_gdf = load_pipe_shapefile(RAW_DATA_DIR, region_code, "SPLY_LS")
    if sply_ls_gdf is not None:
        gdfs.append(sply_ls_gdf)

    if not gdfs:
        return None

    # 병합
    pipe_gdf = pd.concat(gdfs, ignore_index=True)
    pipe_gdf = gpd.GeoDataFrame(pipe_gdf, crs=gdfs[0].crs)

    print(f"파이프 데이터 로드 완료: {len(pipe_gdf)}개 객체")
    print(f"  - PIPE_LM: {len(pipe_gdf[pipe_gdf['PIPE_TYPE'] == 'PIPE_LM'])}개")
    print(f"  - SPLY_LS: {len(pipe_gdf[pipe_gdf['PIPE_TYPE'] == 'SPLY_LS'])}개")

    return pipe_gdf


def process_region(
    region_code: str,
    fatigue_df: pd.DataFrame,
    repair_data: dict[str, pd.DataFrame],
    output_dir: Path,
    args: argparse.Namespace,
) -> None:
    """특정 지역의 피로 손상 및 복구 시각화 처리"""
    print(f"\n=== {region_code} 지역 처리 중 ===")

    # 파이프 shapefile 로드
    pipe_gdf = load_pipe_shapefiles(region_code)
    if pipe_gdf is None:
        print(f"경고: {region_code} 지역의 파이프 shapefile을 찾을 수 없습니다.")
        return

    try:
        # FTR_IDN 확인
        if "FTR_IDN" not in pipe_gdf.columns:
            print("오류: FTR_IDN 컬럼이 없습니다.")
            return

        # 피로 손상 데이터 가져오기
        fatigue_dict = get_fatigue_by_ftr_idn(fatigue_df, region_code)
        if not fatigue_dict:
            print(f"경고: {region_code} 지역의 피로 손상 데이터가 없습니다.")
            return

        print(f"피로 손상 데이터: {len(fatigue_dict)}개 파이프")

        # SMLZ 파일 찾기
        smlz_file = get_smlz_shapefile_path(RAW_DATA_DIR, region_code)

        # 출력 경로 및 제목 설정
        if repair_data and not args.no_repair:
            output_path = output_dir / f"main10_{region_code}_pipe_fatigue_repair.png"
            title = f"파이프 피로 손상 및 복구 작업 - {region_code}"
        else:
            output_path = output_dir / f"main10_{region_code}_pipe_fatigue_damage.png"
            title = f"파이프 피로 손상 시각화 - {region_code}"

        # 시각화
        plot_pipe_fatigue_with_repair(
            pipe_gdf,
            fatigue_dict,
            repair_data,
            output_path,
            title,
            show_plot=args.show,
            smlz_file=smlz_file,
            show_repair=(not args.no_repair),
        )

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="파이프 피로 손상 및 복구 작업 통합 시각화 스크립트"
    )
    parser.add_argument(
        "--regions",
        nargs="+",
        default=["0520", "0903"],
        help="시각화할 지역 코드 목록 (기본값: 0520 0903)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="출력 디렉토리 (기본값: results/)",
    )
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    parser.add_argument(
        "--no-repair",
        action="store_true",
        help="복구 작업 점 표시 안함",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="비대화형 모드로 실행",
    )
    return parser.parse_args()


def load_repair_data_if_needed(
    args: argparse.Namespace,
) -> dict[str, pd.DataFrame] | None:
    """필요한 경우 복구 데이터 로드"""
    if args.no_repair:
        return None

    print("\n복구 작업 데이터 로드 중...")
    repair_data = load_all_repair_data(DATA_DIR, verbose=True)
    if not repair_data:
        print("경고: 복구 작업 데이터를 로드할 수 없습니다. 피로 손상만 표시합니다.")
    return repair_data


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    # 출력 디렉토리 설정
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR / "main10a"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("파이프 피로 손상 및 복구 작업 통합 시각화 시작...")
    print(f"데이터 디렉토리: {DATA_DIR}")

    # 피로 데이터 로드
    fatigue_df = load_pipe_fatigue_data()
    if fatigue_df is None:
        print("오류: 로드할 수 있는 피로 데이터가 없습니다.")
        return

    # 복구 데이터 로드
    repair_data = load_repair_data_if_needed(args)

    # 각 지역별 처리
    for region_code in args.regions:
        process_region(region_code, fatigue_df, repair_data or {}, output_dir, args)

    print("\n모든 시각화 완료!")


if __name__ == "__main__":
    main()
