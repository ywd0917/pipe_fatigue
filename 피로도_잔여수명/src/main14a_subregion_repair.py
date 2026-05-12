"""
파이프 피로 손상 및 하위 지역 복구 작업 시각화 스크립트
- 0520 내부의 0470, 0480, 0490 하위 지역 지원
- CSV 파일의 피로 손상 데이터(*_D_final)를 기반으로 파이프를 색상으로 시각화
- results/*_520_위치추가.csv 파일의 복구 작업 위치를 점으로 표시
- 각 복구 작업 타입별로 개별 이미지 생성
"""

import argparse
import sys
import unicodedata
import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import Point
from sklearn.cluster import DBSCAN

from src.common.config import (
    DATA_DIR,
    FATIGUE_PIPE_LM_CSV,
    FATIGUE_SPLY_LS_CSV,
    RAW_DATA_DIR,
    REPAIR_COLORS,
    RESULTS_DIR,
    UNIFIED_REPAIR_CSV,
)
from src.common.shapefile_loader import (
    get_parent_region,
    get_smlz_shapefile_path,
    get_subregion_boundary,
    get_subregion_label,
    is_subregion,
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
from src.main14_common.visualization import plot_individual_repairs_with_clusters

# 비대화형 모드 체크
if "--no-interactive" in sys.argv:
    matplotlib.use("Agg")

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 시각화 상수
DPI_HIGH = 300  # 고해상도
FIGURE_WIDTH = 16  # 표준 크기
FIGURE_HEIGHT = 12  # 표준 크기


def get_repair_colors() -> dict[str, tuple[str, str]]:
    """복구 작업 유형별 색상 정의

    Returns:
        {작업유형: (색상코드, 표시명)} 형태의 딕셔너리
    """
    return REPAIR_COLORS


def load_520_repair_csv(csv_path: Path, verbose: bool = True) -> pd.DataFrame | None:
    """520 지역 복구 작업 CSV 파일 로드

    Args:
        csv_path: CSV 파일 경로
        verbose: 상세 정보 출력 여부

    Returns:
        DataFrame 또는 None (실패 시)
    """
    if not csv_path.exists():
        if verbose:
            print(f"파일을 찾을 수 없습니다: {csv_path}")
        return None

    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 필수 컬럼 확인
        if "위도" not in df.columns or "경도" not in df.columns:
            if verbose:
                print("오류: 위도/경도 컬럼이 없습니다.")
            return None

        # 유효한 좌표만 필터링
        valid_coords = df.dropna(subset=["위도", "경도"])
        valid_coords = valid_coords[
            (valid_coords["위도"] > 0) & (valid_coords["경도"] > 0)
        ]

        if verbose:
            print(f"{csv_path.stem} 데이터 로드: {len(valid_coords)}개 행")

        return valid_coords

    except Exception as e:
        if verbose:
            print(f"오류: CSV 데이터 로드 실패 - {e}")
        return None


def load_repair_data_for_region(
    results_dir: Path, region_code: str, verbose: bool = True
) -> dict[str, pd.DataFrame]:
    """특정 지역의 복구 작업 데이터 로드

    통합 CSV 파일이 있으면 우선 사용하고, 없으면 개별 파일 로드

    Args:
        results_dir: results 디렉토리 경로
        region_code: 지역 코드 (예: "0520", "0903")
        verbose: 상세 정보 출력 여부

    Returns:
        {파일타입: DataFrame} 형태의 딕셔너리
    """
    repair_data = {}

    # 통합 CSV 파일이 있으면 우선 사용
    if UNIFIED_REPAIR_CSV.exists() and region_code == "0520":
        if verbose:
            print(f"통합 재작업 파일 사용: {UNIFIED_REPAIR_CSV}")

        try:
            df = pd.read_csv(UNIFIED_REPAIR_CSV, encoding="utf-8-sig")

            # 파일타입별로 분리
            if "파일타입" in df.columns:
                for repair_type in df["파일타입"].unique():
                    repair_df = df[df["파일타입"] == repair_type].copy()
                    if len(repair_df) > 0:
                        repair_data[repair_type] = repair_df
                        if verbose:
                            print(f"{repair_type} 데이터 로드: {len(repair_df)}개 행")

            return repair_data

        except Exception as e:
            if verbose:
                print(f"통합 파일 로드 실패, 개별 파일로 전환: {e}")

    # 통합 파일이 없거나 로드 실패시 개별 파일 로드 (레거시 지원)
    colors = get_repair_colors()
    for repair_type in colors:
        csv_path = (
            results_dir / f"{repair_type}_{region_code[1:]}_위치추가.csv"
        )  # 0520 -> 520
        df = load_520_repair_csv(csv_path, verbose=verbose)
        if df is not None and len(df) > 0:
            repair_data[repair_type] = df

    return repair_data


def convert_wgs84_to_geodataframe(
    df: pd.DataFrame,
    lat_col: str = "위도",
    lon_col: str = "경도",
) -> gpd.GeoDataFrame:
    """WGS84 좌표를 GeoDataFrame으로 변환

    Args:
        df: 좌표가 포함된 DataFrame
        lat_col: 위도 컬럼명
        lon_col: 경도 컬럼명

    Returns:
        EPSG:5179 좌표계의 GeoDataFrame
    """
    # Point 객체 생성 (경도, 위도 순서 주의)
    geometry = [
        Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col], strict=False)
    ]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # EPSG:5179로 변환
    return gdf.to_crs("EPSG:5179")


def cluster_repair_points(
    gdf: gpd.GeoDataFrame, cluster_distance: float = 10.0
) -> pd.DataFrame:
    """재작업 위치를 클러스터링하여 재작업계수 계산

    Args:
        gdf: EPSG:5179 좌표계의 GeoDataFrame
        cluster_distance: 클러스터링 거리 (미터, 기본값: 10m)

    Returns:
        클러스터 정보를 담은 DataFrame (cluster_id, x, y, repair_count)
    """
    if len(gdf) == 0:
        return pd.DataFrame(columns=["cluster_id", "x", "y", "repair_count"])

    # 좌표 추출
    coords = np.array([[geom.x, geom.y] for geom in gdf.geometry])

    # DBSCAN 클러스터링 (10m 반경)
    clustering = DBSCAN(eps=cluster_distance, min_samples=1).fit(coords)
    gdf["cluster_id"] = clustering.labels_

    # 클러스터별 집계
    clusters = []
    for cluster_id in gdf["cluster_id"].unique():
        cluster_points = gdf[gdf["cluster_id"] == cluster_id]

        # 클러스터 중심점 계산
        center_x = cluster_points.geometry.x.mean()
        center_y = cluster_points.geometry.y.mean()
        repair_count = len(cluster_points)

        clusters.append(
            {
                "cluster_id": cluster_id,
                "x": center_x,
                "y": center_y,
                "repair_count": repair_count,
            }
        )

    return pd.DataFrame(clusters)


def plot_combined_repair_clusters(
    ax: Any,
    repair_df: pd.DataFrame,
) -> tuple[list[mpatches.Circle], int]:
    """통합된 복구 작업 점 그리기 (재작업계수 표시)

    Args:
        ax: matplotlib axes
        repair_df: 통합된 복구 작업 DataFrame

    Returns:
        (범례 요소 리스트, 클러스터 개수)
    """
    # WGS84 좌표를 GeoDataFrame으로 변환
    gdf = convert_wgs84_to_geodataframe(repair_df)

    if len(gdf) == 0:
        return [], 0

    # 클러스터링 수행
    clusters_df = cluster_repair_points(gdf, cluster_distance=10.0)

    # 재작업 횟수별 카운트
    count_ranges = {"1회": 0, "2-3회": 0, "4-5회": 0, "6회 이상": 0}

    # 클러스터별로 그리기
    for _, cluster in clusters_df.iterrows():
        repair_count = cluster["repair_count"]
        x_coord = cluster["x"]
        y_coord = cluster["y"]

        # 재작업 횟수에 따른 색상과 크기 설정
        if repair_count == 1:
            # 단일 재작업: 파란색
            point_color = "blue"
            point_size = 30
            show_text = False
            count_ranges["1회"] += 1
        elif repair_count <= 3:
            # 2-3회: 노란색
            point_color = "gold"
            point_size = 45
            show_text = True
            count_ranges["2-3회"] += 1
        elif repair_count <= 5:
            # 4-5회: 주황색
            point_color = "darkorange"
            point_size = 60
            show_text = True
            count_ranges["4-5회"] += 1
        else:
            # 6회 이상: 빨간색
            point_color = "red"
            point_size = 75
            show_text = True
            count_ranges["6회 이상"] += 1

        # 점 그리기
        ax.plot(
            x_coord,
            y_coord,
            "o",
            color=point_color,
            markersize=point_size / 5,
            markeredgecolor="black",
            markeredgewidth=0.5,
            alpha=0.7,
            zorder=5,
        )

        # 재작업 횟수 텍스트 표시
        if show_text and repair_count > 1:
            ax.text(
                x_coord,
                y_coord,
                str(int(repair_count)),  # 정수로 변환
                fontsize=8,
                fontweight="bold",
                ha="center",
                va="center",
                color="black",
                zorder=6,
            )

    # 범례 요소 생성
    legend_elements = []
    colors_and_labels = [
        ("blue", f'1회 ({count_ranges["1회"]}개)'),
        ("gold", f'2-3회 ({count_ranges["2-3회"]}개)'),
        ("darkorange", f'4-5회 ({count_ranges["4-5회"]}개)'),
        ("red", f'6회 이상 ({count_ranges["6회 이상"]}개)'),
    ]

    for color, label in colors_and_labels:
        count = int(label.split("(")[1].split("개")[0])
        if count > 0:  # 해당 범위에 데이터가 있을 때만 범례에 추가
            legend_elements.append(mpatches.Circle((0, 0), 1, color=color, label=label))

    return legend_elements, len(clusters_df)


def plot_repair_points_520(
    ax: Any,
    repair_df: pd.DataFrame,
    color: str,
    label: str,
    show_cluster_count: bool = True,
) -> tuple[list[mpatches.Circle], int]:
    """520 지역 복구 작업 점 그리기 (재작업계수 표시)

    Args:
        ax: matplotlib axes
        repair_df: 복구 작업 DataFrame
        color: 점 색상
        label: 범례 라벨
        show_cluster_count: 클러스터 재작업계수 표시 여부

    Returns:
        (범례 요소 리스트, 점 개수)
    """
    # WGS84 좌표를 GeoDataFrame으로 변환
    gdf = convert_wgs84_to_geodataframe(repair_df)

    if len(gdf) == 0:
        return [], 0

    # 클러스터링 수행
    clusters_df = cluster_repair_points(gdf, cluster_distance=10.0)

    # 클러스터별로 그리기
    for _, cluster in clusters_df.iterrows():
        repair_count = cluster["repair_count"]

        # 재작업 횟수에 따른 색상과 크기 설정
        if repair_count == 1:
            # 단일 재작업: 기본 표시
            point_color = color
            point_size = 30
            show_text = False
        elif repair_count <= 3:
            # 2-3회: 노란색
            point_color = "gold"
            point_size = 45
            show_text = True
        elif repair_count <= 5:
            # 4-5회: 주황색
            point_color = "darkorange"
            point_size = 60
            show_text = True
        else:
            # 6회 이상: 빨간색
            point_color = "red"
            point_size = 75
            show_text = True

        # 점 그리기
        ax.scatter(
            cluster["x"],
            cluster["y"],
            c=point_color,
            s=point_size,
            alpha=0.7,
            edgecolor="black",
            linewidth=1,
            zorder=5,
        )

        # 재작업계수 텍스트 표시 (2 이상일 때만)
        if show_text and show_cluster_count and repair_count >= 2:
            # 텍스트 색상 설정
            text_color = "black" if repair_count < 6 else "darkred"

            # 숫자 표시 (정수로 변환, 작은 크기)
            ax.text(
                cluster["x"],
                cluster["y"],
                str(int(repair_count)),  # 정수로 변환
                fontsize=7,  # 더 작게
                fontweight="bold",
                color=text_color,
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.1",  # 둥근 사각형, 최소 패딩
                    facecolor="white",
                    edgecolor="gray",
                    linewidth=0.5,  # 얇은 테두리
                    alpha=0.7,
                ),
                zorder=10,
            )

    # 범례 요소 생성
    legend_elements = []

    # 기본 범례
    legend_elements.append(
        mpatches.Circle(
            (0, 0),
            1,
            facecolor=color,
            edgecolor="white",
            label=f"{unicodedata.normalize('NFC', label)} ({len(gdf)}건)",
        )
    )

    # 클러스터 범례 추가
    multi_repair_clusters = clusters_df[clusters_df["repair_count"] >= 2]
    if len(multi_repair_clusters) > 0:
        legend_elements.append(
            mpatches.Circle(
                (0, 0),
                1,
                facecolor="orange",
                edgecolor="black",
                label=f"재작업 2회 이상 ({len(multi_repair_clusters)}개소)",
            )
        )

    return legend_elements, len(gdf)


def filter_pipes_by_region_safe(
    pipe_gdf: gpd.GeoDataFrame, region_boundary: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """안전한 파이프 필터링 (main14a 전용)

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        region_boundary: 지역 경계 GeoDataFrame

    Returns:
        필터링된 파이프 GeoDataFrame
    """
    try:
        # 원본 컬럼 저장
        original_columns = pipe_gdf.columns.tolist()

        # 공간 조인 - geometry만 사용
        filtered = gpd.sjoin(
            pipe_gdf,
            region_boundary[["geometry"]],  # geometry만 사용
            predicate="intersects",  # within 대신 intersects 사용
            how="inner",
        )

        # 중복 제거 및 원본 컬럼만 유지
        return filtered[original_columns].drop_duplicates()

    except Exception as e:
        print(f"필터링 실패, 전체 데이터 사용: {e}")
        return pipe_gdf


def plot_region_boundary(ax: Any, region_boundary: gpd.GeoDataFrame) -> None:
    """하위 지역 경계 표시

    Args:
        ax: matplotlib axes
        region_boundary: 지역 경계 GeoDataFrame
    """
    if region_boundary is not None and len(region_boundary) > 0:
        try:
            # 경계선 그리기 (회색으로, 파이프 뒤에 배치)
            region_boundary.boundary.plot(
                ax=ax,
                color="gray",
                linewidth=2,
                alpha=0.6,
                zorder=1,  # SMLZ(0) 위, 파이프(2,3) 아래
                label="지역 경계",
            )

            # 경계 안쪽을 약간 투명하게 채우기 (회색으로)
            region_boundary.plot(
                ax=ax,
                facecolor="gray",
                alpha=0.03,
                edgecolor="none",
                zorder=1,  # SMLZ(0) 위, 파이프(2,3) 아래
            )
        except Exception as e:
            print(f"경계 표시 실패: {e}")


def plot_pipe_fatigue_with_repair_520(
    pipe_gdf: gpd.GeoDataFrame,
    fatigue_dict: dict[str, float],
    repair_df: pd.DataFrame,
    repair_type: str,
    output_path: Path,
    title: str,
    show_plot: bool = False,
    smlz_file: Path | None = None,
) -> None:
    """파이프 피로 손상 및 520 지역 복구 작업 시각화"""
    setup_korean_font()

    # 피로 손상 데이터 준비
    pipe_gdf = prepare_fatigue_data(pipe_gdf, fatigue_dict)

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

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

    # 경계 설정 - 파이프와 복구 데이터 모두 포함
    all_bounds = pipe_gdf.total_bounds

    # 복구 데이터 경계도 포함
    if repair_df is not None and len(repair_df) > 0:
        repair_gdf = convert_wgs84_to_geodataframe(repair_df)
        if len(repair_gdf) > 0:
            repair_bounds = repair_gdf.total_bounds
            all_bounds = [
                min(all_bounds[0], repair_bounds[0]),
                min(all_bounds[1], repair_bounds[1]),
                max(all_bounds[2], repair_bounds[2]),
                max(all_bounds[3], repair_bounds[3]),
            ]

    x_margin = (all_bounds[2] - all_bounds[0]) * 0.05
    y_margin = (all_bounds[3] - all_bounds[1]) * 0.05
    ax.set_xlim(all_bounds[0] - x_margin, all_bounds[2] + x_margin)
    ax.set_ylim(all_bounds[1] - y_margin, all_bounds[3] + y_margin)

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

    if repair_df is not None and len(repair_df) > 0:
        colors = get_repair_colors()
        if repair_type in colors:
            try:
                color, label = colors[repair_type]
                legend_elements, points_count = plot_repair_points_520(
                    ax, repair_df, color, label
                )
                repair_legend_elements.extend(legend_elements)
                total_repair_points += points_count
            except Exception as e:
                print(f"복구 작업 점 표시 중 오류: {e}")

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
            loc="upper left",
            bbox_to_anchor=(0.02, 0.85),
            fontsize=9,
            title="복구 작업",
            title_fontsize=10,
        )
        ax.add_artist(repair_legend)

    # 저장 및 표시
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI_HIGH, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()

    plt.close()


def plot_pipe_fatigue_with_repair_520_v2(
    pipe_gdf: gpd.GeoDataFrame,
    fatigue_dict: dict[str, float],
    repair_df: pd.DataFrame,
    repair_type: str,
    output_path: Path,
    title: str,
    show_plot: bool = False,
    smlz_file: Path | None = None,
    region_boundary: gpd.GeoDataFrame | None = None,  # 새로 추가
) -> None:
    """파이프 피로 손상 및 520 지역 복구 작업 시각화 (v2 - 지역 경계 표시)"""
    setup_korean_font()

    # 피로 손상 데이터 준비
    pipe_gdf = prepare_fatigue_data(pipe_gdf, fatigue_dict)

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

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

    # 지역 경계 표시 (새로 추가)
    if region_boundary is not None:
        plot_region_boundary(ax, region_boundary)

    # 경계 설정 - 파이프와 복구 데이터 모두 포함
    all_bounds = pipe_gdf.total_bounds

    # 복구 데이터 경계도 포함
    if repair_df is not None and len(repair_df) > 0:
        repair_gdf = convert_wgs84_to_geodataframe(repair_df)
        if len(repair_gdf) > 0:
            repair_bounds = repair_gdf.total_bounds
            all_bounds = [
                min(all_bounds[0], repair_bounds[0]),
                min(all_bounds[1], repair_bounds[1]),
                max(all_bounds[2], repair_bounds[2]),
                max(all_bounds[3], repair_bounds[3]),
            ]

    x_margin = (all_bounds[2] - all_bounds[0]) * 0.05
    y_margin = (all_bounds[3] - all_bounds[1]) * 0.05
    ax.set_xlim(all_bounds[0] - x_margin, all_bounds[2] + x_margin)
    ax.set_ylim(all_bounds[1] - y_margin, all_bounds[3] + y_margin)

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

    if repair_df is not None and len(repair_df) > 0:
        colors = get_repair_colors()
        if repair_type in colors:
            try:
                color, label = colors[repair_type]
                legend_elements, points_count = plot_repair_points_520(
                    ax, repair_df, color, label
                )
                repair_legend_elements.extend(legend_elements)
                total_repair_points += points_count
            except Exception as e:
                print(f"복구 작업 점 표시 중 오류: {e}")

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
            loc="upper left",
            bbox_to_anchor=(0.02, 0.85),
            fontsize=9,
            title="복구 작업",
            title_fontsize=10,
        )
        ax.add_artist(repair_legend)

    # 지역 경계 범례 추가 (새로 추가)
    if region_boundary is not None:
        from matplotlib.lines import Line2D

        boundary_legend = Line2D(
            [0], [0], color="red", linewidth=3, alpha=0.8, label="지역 경계"
        )
        ax.legend(handles=[boundary_legend], loc="upper left", fontsize=9)

    # 저장 및 표시
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI_HIGH, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()

    plt.close()


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


def load_pipe_shapefiles(
    region_code: str, region_boundary: gpd.GeoDataFrame | None = None
) -> gpd.GeoDataFrame | None:
    """특정 지역의 파이프 shapefile 로드 및 병합

    Args:
        region_code: 지역 코드 (예: "0520", "0903", "0470")
        region_boundary: 하위 지역 경계 (선택사항)

    Returns:
        병합된 파이프 GeoDataFrame 또는 None
    """
    gdfs = []

    # 하위 지역인 경우 부모 지역 데이터 로드
    if is_subregion(region_code):
        parent_region = get_parent_region(region_code)
        pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, parent_region, "PIPE_LM")
    else:
        pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, region_code, "PIPE_LM")

    if pipe_lm_gdf is not None:
        gdfs.append(pipe_lm_gdf)

    # SPLY_LS 로드
    if is_subregion(region_code):
        parent_region = get_parent_region(region_code)
        sply_ls_gdf = load_pipe_shapefile(RAW_DATA_DIR, parent_region, "SPLY_LS")
    else:
        sply_ls_gdf = load_pipe_shapefile(RAW_DATA_DIR, region_code, "SPLY_LS")

    if sply_ls_gdf is not None:
        gdfs.append(sply_ls_gdf)

    if not gdfs:
        return None

    # 병합
    pipe_gdf = pd.concat(gdfs, ignore_index=True)
    pipe_gdf = gpd.GeoDataFrame(pipe_gdf, crs=gdfs[0].crs)

    # 하위 지역인 경우 경계로 필터링
    if region_boundary is not None:
        original_count = len(pipe_gdf)
        pipe_gdf = filter_pipes_by_region_safe(
            pipe_gdf, region_boundary
        )  # safe 함수 사용
        print(f"지역 필터링: {original_count}개 → {len(pipe_gdf)}개")

    print(f"파이프 데이터 로드 완료: {len(pipe_gdf)}개 객체")
    print(f"  - PIPE_LM: {len(pipe_gdf[pipe_gdf['PIPE_TYPE'] == 'PIPE_LM'])}개")
    print(f"  - SPLY_LS: {len(pipe_gdf[pipe_gdf['PIPE_TYPE'] == 'SPLY_LS'])}개")

    return pipe_gdf


def process_repair_type(
    repair_type: str,
    repair_df: pd.DataFrame,
    pipe_gdf: gpd.GeoDataFrame,
    fatigue_dict: dict[str, float],
    output_dir: Path,
    args: argparse.Namespace,
    smlz_file: Path | None,
    region_code: str,
    region_boundary: gpd.GeoDataFrame | None = None,  # 새로 추가
) -> None:
    """특정 복구 작업 타입 처리"""
    print(f"\n=== {repair_type} 처리 중 ===")

    try:
        # 출력 파일명 생성 (하위 지역은 전체 코드 사용)
        if is_subregion(region_code):
            output_path = output_dir / f"{repair_type}_{region_code}_pipe_fatigue.png"
        else:
            output_path = (
                output_dir / f"{repair_type}_{region_code[1:]}_pipe_fatigue.png"
            )
        title = f"파이프 피로 손상 및 {repair_type} - {region_code}"

        # 시각화 - v2 함수 사용
        plot_pipe_fatigue_with_repair_520_v2(
            pipe_gdf,
            fatigue_dict,
            repair_df,
            repair_type,
            output_path,
            title,
            show_plot=args.show,
            smlz_file=smlz_file,
            region_boundary=region_boundary,  # 경계 전달
        )
    except Exception as e:
        print(f"{repair_type} 처리 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="파이프 피로 손상 및 복구 작업 시각화")
    parser.add_argument(
        "--region",
        type=str,
        default="0520",
        help="지역 코드 (기본값: 0520)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="출력 디렉토리 (기본값: results/main14)",
    )
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="모든 복구 작업 타입을 하나의 이미지에 표시 (기본값)",
    )
    parser.add_argument(
        "--individual",
        action="store_true",
        help="각 복구 작업 타입별로 개별 이미지 생성",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="비대화형 모드로 실행",
    )
    return parser.parse_args()


def plot_all_repair_types(
    pipe_gdf: gpd.GeoDataFrame,
    fatigue_dict: dict[str, float],
    repair_data: dict[str, pd.DataFrame],
    output_dir: Path,
    region_code: str,
    show_plot: bool = False,
    smlz_file: Path | None = None,
    region_boundary: gpd.GeoDataFrame | None = None,  # 새로 추가
) -> None:
    """모든 복구 작업 타입을 하나의 이미지에 시각화"""
    setup_korean_font()

    # 피로 손상 데이터 준비
    pipe_gdf = prepare_fatigue_data(pipe_gdf, fatigue_dict)

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

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

    # 지역 경계 표시 (새로 추가)
    if region_boundary is not None:
        plot_region_boundary(ax, region_boundary)

    # 경계 설정 - 파이프와 모든 복구 데이터 포함
    all_bounds = pipe_gdf.total_bounds

    # 모든 복구 데이터 경계 계산
    for repair_type, repair_df in repair_data.items():
        if repair_df is not None and len(repair_df) > 0:
            repair_gdf = convert_wgs84_to_geodataframe(repair_df)
            if len(repair_gdf) > 0:
                repair_bounds = repair_gdf.total_bounds
                all_bounds = [
                    min(all_bounds[0], repair_bounds[0]),
                    min(all_bounds[1], repair_bounds[1]),
                    max(all_bounds[2], repair_bounds[2]),
                    max(all_bounds[3], repair_bounds[3]),
                ]

    x_margin = (all_bounds[2] - all_bounds[0]) * 0.05
    y_margin = (all_bounds[3] - all_bounds[1]) * 0.05
    ax.set_xlim(all_bounds[0] - x_margin, all_bounds[2] + x_margin)
    ax.set_ylim(all_bounds[1] - y_margin, all_bounds[3] + y_margin)

    # 제목 및 라벨 설정
    ax.set_title(
        f"파이프 피로 손상 및 복구 작업 전체 - {region_code}",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 통계 계산
    stats = calculate_fatigue_statistics(pipe_gdf)

    # 개별 재작업 점 표시 + 클러스터 숫자 오버레이
    repair_legend_elements, total_clusters = plot_individual_repairs_with_clusters(
        ax, repair_data, convert_wgs84_to_geodataframe, cluster_repair_points
    )

    # 통계 정보 표시
    stats_text = format_fatigue_stats_text(stats, total_clusters)
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
            loc="upper left",
            bbox_to_anchor=(0.02, 0.85),
            fontsize=9,
            title="복구 작업",
            title_fontsize=10,
        )
        ax.add_artist(repair_legend)

    # 저장 및 표시
    if is_subregion(region_code):
        output_path = output_dir / f"all_repair_{region_code}_pipe_fatigue.png"
    else:
        output_path = output_dir / f"all_repair_{region_code[1:]}_pipe_fatigue.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI_HIGH, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()

    plt.close()


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()
    region_code = args.region

    # 출력 디렉토리 설정
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR / "main14a"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"{region_code} 지역 파이프 피로 손상 및 복구 작업 시각화 시작...")
    print(f"데이터 디렉토리: {DATA_DIR}")
    print(f"결과 디렉토리: {output_dir}")

    # 피로 데이터 로드
    fatigue_df = load_pipe_fatigue_data()
    if fatigue_df is None:
        print("오류: 로드할 수 있는 피로 데이터가 없습니다.")
        return

    # 하위 지역 처리
    region_boundary = None
    if is_subregion(region_code):
        parent_region = get_parent_region(region_code)
        subregion_label = get_subregion_label(region_code)
        print(f"\n=== {region_code} 하위 지역 처리 ===")
        print(f"부모 지역: {parent_region}, 라벨: {subregion_label}")

        # WEA_SMLZ_AS에서 경계 추출
        smlz_path = (
            RAW_DATA_DIR / f"export_shp_20250704({parent_region})" / "WEA_SMLZ_AS.shp"
        )
        region_boundary = get_subregion_boundary(smlz_path, subregion_label)
        if region_boundary is None:
            print(f"오류: {region_code} 지역 경계를 찾을 수 없습니다.")
            return
        print(f"지역 경계 추출 완료: {len(region_boundary)}개 폴리곤")

    # 지역 파이프 shapefile 로드
    print(f"\n=== {region_code} 지역 파이프 데이터 로드 중 ===")
    pipe_gdf = load_pipe_shapefiles(region_code, region_boundary)
    if pipe_gdf is None:
        print(f"오류: {region_code} 지역의 파이프 shapefile을 찾을 수 없습니다.")
        return

    # FTR_IDN 확인
    if "FTR_IDN" not in pipe_gdf.columns:
        print("오류: FTR_IDN 컬럼이 없습니다.")
        return

    # 피로 손상 데이터 가져오기 (하위 지역은 해당 지역 코드 그대로 사용)
    fatigue_dict = get_fatigue_by_ftr_idn(
        fatigue_df, region_code
    )  # 0470, 0480, 0490 그대로 사용

    if not fatigue_dict:
        print(f"경고: {region_code} 지역의 피로 손상 데이터가 없습니다.")
        return

    print(f"피로 손상 데이터: {len(fatigue_dict)}개 파이프")

    # SMLZ 파일 찾기 (하위 지역은 부모 지역 파일 사용)
    if is_subregion(region_code):
        parent_region = get_parent_region(region_code)
        smlz_file = get_smlz_shapefile_path(RAW_DATA_DIR, parent_region)
    else:
        smlz_file = get_smlz_shapefile_path(RAW_DATA_DIR, region_code)

    # 복구 데이터 로드 (하위 지역은 부모 지역 데이터를 필터링)
    print(f"\n{region_code} 지역 복구 작업 데이터 로드 중...")
    if is_subregion(region_code):
        parent_region = get_parent_region(region_code)
        repair_data = load_repair_data_for_region(
            RESULTS_DIR, parent_region, verbose=True
        )

        # 지역 경계로 복구 데이터 필터링
        if repair_data and region_boundary is not None:
            filtered_repair_data = {}
            for repair_type, repair_df in repair_data.items():
                # WGS84 좌표를 EPSG:5179로 변환
                repair_gdf = convert_wgs84_to_geodataframe(repair_df)

                # 원본 데이터의 모든 컬럼을 GeoDataFrame에 추가
                for col in repair_df.columns:
                    if col not in repair_gdf.columns:
                        repair_gdf[col] = repair_df[col].values

                # 경계 내 데이터만 필터링
                filtered = gpd.sjoin(
                    repair_gdf, region_boundary, predicate="within", how="inner"
                )

                if len(filtered) > 0:
                    # 필요한 컬럼만 추출하여 DataFrame으로 변환
                    # sjoin으로 추가된 컬럼 제거
                    cols_to_keep = [
                        col for col in repair_df.columns if col in filtered.columns
                    ]
                    filtered_df = pd.DataFrame(filtered[cols_to_keep])
                    filtered_repair_data[repair_type] = filtered_df
                    print(
                        f"  - {repair_type}: {len(repair_df)}개 → {len(filtered_df)}개"
                    )
            repair_data = filtered_repair_data
    else:
        repair_data = load_repair_data_for_region(
            RESULTS_DIR, region_code, verbose=True
        )

    if not repair_data:
        print(f"경고: {region_code} 지역 복구 작업 데이터가 없습니다.")
        return

    # 옵션에 따른 처리
    if args.individual:
        # 개별 복구 작업 타입별 이미지 생성
        print("\n=== 개별 복구 작업 타입별 이미지 생성 ===")
        for repair_type, repair_df in repair_data.items():
            process_repair_type(
                repair_type,
                repair_df,
                pipe_gdf,
                fatigue_dict,
                output_dir,
                args,
                smlz_file,
                region_code,
                region_boundary,  # 경계 전달
            )
    else:
        # 기본값: 모든 복구 작업 타입을 하나의 이미지에 표시
        print("\n=== 모든 복구 작업 타입을 하나의 이미지에 표시 (기본값) ===")
        plot_all_repair_types(
            pipe_gdf,
            fatigue_dict,
            repair_data,
            output_dir,
            region_code,
            show_plot=args.show,
            smlz_file=smlz_file,
            region_boundary=region_boundary,  # 경계 전달
        )

    print("\n모든 시각화 완료!")


if __name__ == "__main__":
    main()
