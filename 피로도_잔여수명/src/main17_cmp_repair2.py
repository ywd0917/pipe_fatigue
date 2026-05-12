"""
PIPE_LM + SPLY_LS 파이프 데이터와 repair2 복구 작업 데이터 통합 시각화
- main15에서 생성한 PIPE_LM_JOINT.shp, SPLY_LS_JOINT.shp 로드
- CNT_JNT 값에 따른 색상으로 파이프 표시
- main13에서 생성한 *_520_위치추가.csv 파일들을 점으로 표시
- 기본: 3개의 개별 이미지 생성, --all 옵션: 통합 이미지
"""

import argparse
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from shapely.geometry import Point

from src.common import korean_font_utils
from src.common.config import RESULTS_DIR, UNIFIED_REPAIR_CSV
from src.common.visualization_utils import setup_plot_style

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 시각화 상수
DPI_HIGH = 300  # 고해상도 (main14와 동일)
FIGURE_WIDTH = 32  # 2배 크기 (해상도 4배)
FIGURE_HEIGHT = 24  # 2배 크기 (해상도 4배)
RECOVERY_POINT_SIZE = 30  # 복구 작업 점 크기
RECOVERY_POINT_ALPHA = 0.6  # 복구 작업 점 투명도
RECOVERY_EDGE_WIDTH = 0.5  # 복구 작업 점 테두리 두께
PIPE_LM_WIDTH = 1.5  # PIPE_LM 선 두께
SPLY_LS_WIDTH = 0.5  # SPLY_LS 선 두께 (PIPE_LM의 1/3)
PIPE_ALPHA = 0.7  # 파이프 선 투명도

# CNT_JNT 색상 정의
CNT_JNT_COLORS = {
    0: "#0066CC",  # 파란색
    1: "#00AA00",  # 초록색
    2: "#FFD700",  # 노란색
    3: "#FF8C00",  # 주황색
    4: "#FF0000",  # 빨간색
    5: "#800080",  # 보라색
    6: "#000000",  # 검은색 (6 이상)
}

# 복구 작업 색상 정의
RECOVERY_COLORS = {
    "지상누수": "#FF1493",  # 진한 핑크
    "지하누수": "#0000FF",  # 파란색
    "긴급공사": "#FF8C00",  # 다크 오렌지
    "관리대장": "#008000",  # 녹색
}


def setup_korean_font() -> None:
    """한글 폰트 설정"""
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")
    else:
        print("경고: 한글 폰트를 찾을 수 없습니다.")


def load_pipe_joint_shapefiles(
    results_dir: Path, verbose: bool = True
) -> gpd.GeoDataFrame | None:
    """PIPE_LM_JOINT.shp와 SPLY_LS_JOINT.shp 로드 및 통합

    Args:
        results_dir: 결과 디렉토리
        verbose: 상세 정보 출력 여부

    Returns:
        통합된 파이프 GeoDataFrame 또는 None
    """
    # main15_extract_joint_data의 출력 디렉토리에서 읽기
    shp_dir = results_dir / "main15_extract_joint_data" / "shapefiles"

    pipe_gdfs = []

    # PIPE_LM_JOINT.shp 로드
    pipe_lm_path = shp_dir / "PIPE_LM_JOINT.shp"
    if pipe_lm_path.exists():
        try:
            pipe_lm_gdf = gpd.read_file(pipe_lm_path)
            pipe_lm_gdf["PIPE_TYPE"] = "PIPE_LM"
            pipe_gdfs.append(pipe_lm_gdf)
            if verbose:
                print(f"PIPE_LM_JOINT 로드: {len(pipe_lm_gdf)}개 세그먼트")
                # CNT_JNT 통계
                if "CNT_JNT" in pipe_lm_gdf.columns:
                    cnt_stats = pipe_lm_gdf["CNT_JNT"].value_counts().sort_index()
                    print("  CNT_JNT 분포:")
                    for cnt, num in cnt_stats.items():
                        print(f"    - CNT_JNT = {cnt}: {num}개")
        except Exception as e:
            if verbose:
                print(f"오류: PIPE_LM_JOINT 로드 실패 - {e}")
    else:
        if verbose:
            print(f"PIPE_LM_JOINT.shp 파일을 찾을 수 없습니다: {pipe_lm_path}")

    # SPLY_LS_JOINT.shp 로드
    sply_ls_path = shp_dir / "SPLY_LS_JOINT.shp"
    if sply_ls_path.exists():
        try:
            sply_ls_gdf = gpd.read_file(sply_ls_path)
            sply_ls_gdf["PIPE_TYPE"] = "SPLY_LS"
            pipe_gdfs.append(sply_ls_gdf)
            if verbose:
                print(f"SPLY_LS_JOINT 로드: {len(sply_ls_gdf)}개 세그먼트")
                # CNT_JNT 통계
                if "CNT_JNT" in sply_ls_gdf.columns:
                    cnt_stats = sply_ls_gdf["CNT_JNT"].value_counts().sort_index()
                    print("  CNT_JNT 분포:")
                    for cnt, num in cnt_stats.items():
                        print(f"    - CNT_JNT = {cnt}: {num}개")
        except Exception as e:
            if verbose:
                print(f"오류: SPLY_LS_JOINT 로드 실패 - {e}")
    else:
        if verbose:
            print(f"SPLY_LS_JOINT.shp 파일을 찾을 수 없습니다: {sply_ls_path}")

    # 통합
    if pipe_gdfs:
        combined_gdf = pd.concat(pipe_gdfs, ignore_index=True)
        if verbose:
            print(f"\n통합 파이프 데이터: 총 {len(combined_gdf)}개 세그먼트")
        return combined_gdf
    if verbose:
        print("로드된 파이프 데이터가 없습니다.")
    return None


def get_cnt_jnt_color(cnt_jnt: int) -> str:
    """CNT_JNT 값에 따른 색상 반환

    Args:
        cnt_jnt: Joint 연결 수

    Returns:
        색상 문자열
    """
    if cnt_jnt >= 6:
        return CNT_JNT_COLORS[6]  # 6 이상은 검은색
    return CNT_JNT_COLORS.get(cnt_jnt, CNT_JNT_COLORS[6])  # 기본값도 검은색


def load_repair_csv_files(
    results_dir: Path, repair_type: str | None = None, verbose: bool = True
) -> pd.DataFrame | None:
    """복구 작업 CSV 파일들 로드

    Args:
        results_dir: 결과 디렉토리
        repair_type: 특정 복구 타입 (지상누수, 지하누수, 긴급공사, 관리대장) 또는 None (전체)
        verbose: 상세 정보 출력 여부

    Returns:
        복구 작업 DataFrame 또는 None
    """
    # 통합 CSV 파일 사용
    if not UNIFIED_REPAIR_CSV.exists():
        if verbose:
            print(f"오류: 통합 재작업 파일을 찾을 수 없습니다: {UNIFIED_REPAIR_CSV}")
            print("먼저 main13_crop_520.py를 실행하여 통합 파일을 생성하세요.")
        return None

    try:
        # 통합 CSV 파일 읽기
        df = pd.read_csv(UNIFIED_REPAIR_CSV, encoding="utf-8-sig")

        # 파일타입 커럼 확인
        if "파일타입" not in df.columns:
            if verbose:
                print("오류: 파일타입 커럼이 없습니다.")
            return None

        # 유효한 좌표만 필터링
        df = df.dropna(subset=["위도", "경도"])
        df = df[(df["위도"] > 0) & (df["경도"] > 0)]

        # 복구타입 커럼 추가 (파일타입과 동일)
        df["복구타입"] = df["파일타입"]

        if repair_type:
            # 특정 타입만 필터링
            df = df[df["파일타입"] == repair_type]
            if verbose:
                print(f"{repair_type} 데이터 로드: {len(df)}개 지점")
        else:
            # 모든 타입 (기타공사 제외)
            valid_types = ["지상누수", "지하누수", "긴급공사", "관리대장"]
            df = df[df["파일타입"].isin(valid_types)]

            if verbose:
                for rtype in valid_types:
                    count = len(df[df["파일타입"] == rtype])
                    if count > 0:
                        print(f"{rtype} 데이터 로드: {count}개 지점")
                print(f"\n로드된 복구 작업 데이터: 총 {len(df)}개 지점")

        return df if len(df) > 0 else None

    except Exception as e:
        if verbose:
            print(f"오류: 통합 파일 로드 실패 - {e}")
        return None


def visualize_pipes_and_repair(
    pipe_gdf: gpd.GeoDataFrame,
    repair_df: pd.DataFrame | None,
    title: str,
    output_path: Path,
    verbose: bool = True,
) -> None:
    """파이프와 복구 작업 데이터 시각화

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        repair_df: 복구 작업 DataFrame
        title: 그래프 제목
        output_path: 출력 파일 경로
        verbose: 상세 정보 출력 여부
    """
    # 플롯 설정 (고해상도)
    fig, ax = setup_plot_style(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # 1. 파이프 그리기 (CNT_JNT 값에 따른 색상)
    if verbose:
        print("\n파이프 세그먼트 그리기...")

    # CNT_JNT 값별로 그룹화하여 그리기 (성능 최적화)
    from matplotlib.collections import LineCollection

    for cnt_value in sorted(pipe_gdf["CNT_JNT"].unique()):
        subset = pipe_gdf[pipe_gdf["CNT_JNT"] == cnt_value]
        color = get_cnt_jnt_color(cnt_value)

        # 파이프 타입별로 분리하여 LineCollection 생성
        for pipe_type in ["PIPE_LM", "SPLY_LS"]:
            type_subset = subset[subset.get("PIPE_TYPE") == pipe_type]
            if len(type_subset) == 0:
                continue

            # LineCollection용 선분 리스트 생성
            lines = []
            for _, row in type_subset.iterrows():
                if row.geometry and row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    if len(coords) >= 2:
                        lines.append(coords)

            if lines:
                # LineCollection으로 한 번에 그리기 (두께로 구분)
                linewidth = PIPE_LM_WIDTH if pipe_type == "PIPE_LM" else SPLY_LS_WIDTH
                lc = LineCollection(
                    lines,
                    colors=color,
                    linewidths=linewidth,
                    linestyles="-",
                    alpha=PIPE_ALPHA,
                )
                ax.add_collection(lc)

    # 2. 복구 작업 데이터 그리기 (반투명 점으로 통일)
    repair_type_counts = {}
    if repair_df is not None and len(repair_df) > 0:
        if verbose:
            print(f"복구 작업 지점 그리기: {len(repair_df)}개")

        # WGS84 좌표를 Point 객체로 변환
        geometry = [
            Point(lon, lat)
            for lon, lat in zip(repair_df["경도"], repair_df["위도"], strict=False)
        ]
        repair_gdf = gpd.GeoDataFrame(repair_df, geometry=geometry, crs="EPSG:4326")

        # EPSG:5179로 변환 (파이프와 동일한 좌표계)
        repair_gdf = repair_gdf.to_crs(pipe_gdf.crs)

        # 복구 타입별 색상 사용

        # 복구 타입별로 반투명 점 그리기
        for repair_type, color in RECOVERY_COLORS.items():
            subset = repair_gdf[repair_gdf["복구타입"] == repair_type]
            if len(subset) > 0:
                repair_type_counts[repair_type] = len(subset)
                x = [geom.x for geom in subset.geometry]
                y = [geom.y for geom in subset.geometry]
                ax.scatter(
                    x,
                    y,
                    c=color,
                    s=RECOVERY_POINT_SIZE,  # 상수 사용
                    alpha=RECOVERY_POINT_ALPHA,  # 투명도 상수
                    edgecolor="white",
                    linewidth=RECOVERY_EDGE_WIDTH,  # 테두리 두께 상수
                    zorder=5,
                )

    # 3. 범례 생성
    legend_elements: list[mpatches.Patch | Line2D] = []

    # CNT_JNT 색상 범례
    legend_elements.append(mpatches.Patch(color="white", label="[Joint 연결 수]"))
    legend_elements.append(mpatches.Patch(color=CNT_JNT_COLORS[0], label="CNT_JNT = 0"))
    legend_elements.append(mpatches.Patch(color=CNT_JNT_COLORS[1], label="CNT_JNT = 1"))
    legend_elements.append(mpatches.Patch(color=CNT_JNT_COLORS[2], label="CNT_JNT = 2"))
    legend_elements.append(mpatches.Patch(color=CNT_JNT_COLORS[3], label="CNT_JNT = 3"))
    legend_elements.append(mpatches.Patch(color=CNT_JNT_COLORS[4], label="CNT_JNT = 4"))
    legend_elements.append(mpatches.Patch(color=CNT_JNT_COLORS[5], label="CNT_JNT = 5"))
    legend_elements.append(mpatches.Patch(color=CNT_JNT_COLORS[6], label="CNT_JNT ≥ 6"))

    # 파이프 타입 범례
    legend_elements.append(mpatches.Patch(color="white", label=""))
    legend_elements.append(mpatches.Patch(color="white", label="[파이프 타입]"))
    legend_elements.append(
        Line2D(
            [0],
            [0],
            color="gray",
            linewidth=3,
            linestyle="-",
            label="PIPE_LM (굵은 선)",
        )
    )
    legend_elements.append(
        Line2D(
            [0],
            [0],
            color="gray",
            linewidth=1,
            linestyle="-",
            label="SPLY_LS (얇은 선)",
        )
    )

    # 복구 작업 범례 (main14와 동일한 스타일)
    if repair_type_counts:
        legend_elements.append(mpatches.Patch(color="white", label=""))
        legend_elements.append(mpatches.Patch(color="white", label="[복구 작업]"))

        for repair_type, count in repair_type_counts.items():
            color = RECOVERY_COLORS.get(repair_type, "#808080")
            legend_elements.append(
                mpatches.Circle(
                    (0, 0),
                    1,
                    facecolor=color,
                    edgecolor="white",
                    label=f"{repair_type} ({count}건)",
                )
            )

    ax.legend(handles=legend_elements, loc="upper right", fontsize=10, framealpha=0.9)

    # 제목 및 라벨
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.set_xlabel("X 좌표 (EPSG:5179)", fontsize=10)
    ax.set_ylabel("Y 좌표 (EPSG:5179)", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    # 저장 (고해상도)
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI_HIGH, bbox_inches="tight")
    plt.close()

    if verbose:
        print(f"이미지 저장 완료: {output_path}")


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="파이프 (CNT_JNT 색상) + 복구 작업 통합 시각화"
    )
    parser.add_argument(
        "--output-dir", type=str, help="출력 디렉토리 (기본값: results/)"
    )
    parser.add_argument(
        "--input-dir", type=str, help="입력 디렉토리 (기본값: results/)"
    )
    parser.add_argument(
        "--all", action="store_true", help="모든 복구 타입을 하나의 이미지로 출력"
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    # 한글 폰트 설정
    setup_korean_font()

    # 디렉토리 설정
    input_dir = Path(args.input_dir) if args.input_dir else RESULTS_DIR
    output_dir = (
        Path(args.output_dir) if args.output_dir else RESULTS_DIR / "main17_cmp_repair2"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print("파이프 + 복구 작업 통합 시각화 시작...")
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")

    # 1. 파이프 데이터 로드
    print("\n파이프 Joint 데이터 로드 중...")
    pipe_gdf = load_pipe_joint_shapefiles(input_dir, verbose=True)

    if pipe_gdf is None:
        print("오류: 파이프 데이터를 로드할 수 없습니다.")
        return

    # 2. 시각화 생성
    if args.all:
        # 모든 복구 타입을 하나의 이미지로
        print("\n모든 복구 타입 통합 시각화...")
        repair_df = load_repair_csv_files(input_dir, repair_type=None, verbose=True)

        output_path = output_dir / "pipe_repair_all.png"
        visualize_pipes_and_repair(
            pipe_gdf,
            repair_df,
            "파이프 네트워크 (CNT_JNT 기반) + 복구 작업 위치 (전체)",
            output_path,
            verbose=True,
        )
    else:
        # 각 복구 타입별로 개별 이미지 생성
        repair_types = ["지상누수", "지하누수", "긴급공사", "관리대장"]

        for repair_type in repair_types:
            print(f"\n{repair_type} 시각화...")
            repair_df = load_repair_csv_files(
                input_dir, repair_type=repair_type, verbose=True
            )

            output_path = output_dir / f"pipe_repair_{repair_type}.png"
            visualize_pipes_and_repair(
                pipe_gdf,
                repair_df,
                f"파이프 네트워크 (CNT_JNT 기반) + {repair_type} 위치",
                output_path,
                verbose=True,
            )

    print("\n시각화 완료!")
    print(f"결과 파일 위치: {output_dir}")


if __name__ == "__main__":
    main()
