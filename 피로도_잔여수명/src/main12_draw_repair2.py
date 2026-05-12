"""
results 디렉토리의 *_위치추가.csv 파일들을 읽어서 지도에 표시하는 스크립트 (초고속 버전)
- KDTree를 사용한 공간 인덱싱
- NumPy 벡터화 연산
- 메모리 효율적 처리
- 10m 이내 중복 위치 클러스터링 및 표시
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
from matplotlib.patches import Circle
from scipy.spatial import cKDTree
from shapely.geometry import Point

from src.common import korean_font_utils
from src.common.config import RAW_DATA_DIR, REPAIR_COLORS, RESULTS_DIR
from src.common.shapefile_loader import load_all_mdlz_shapefiles
from src.common.visualization_utils import setup_plot_style

# 비대화형 모드 체크
if "--no-interactive" in sys.argv:
    matplotlib.use("Agg")

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 중복 판단 거리 임계값 (미터 단위)
DISTANCE_THRESHOLD = 10.0

# 영어-한글 복구 유형 매핑
BOUNDS_TYPE_MAP = {
    "ground": "지상누수",
    "underground": "지하누수",
    "emergency": "긴급공사",
    "registry": "관리대장",
}


def haversine_vectorized(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """벡터화된 Haversine 거리 계산 (미터 단위)"""
    R = 6371000  # 지구 반경 (미터)

    # 라디안 변환
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    result: np.ndarray = R * c
    return result


def setup_korean_font() -> None:
    """한글 폰트 설정"""
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")
    else:
        print("경고: 한글 폰트를 찾을 수 없습니다.")


def get_repair2_colors() -> dict[str, tuple[str, str]]:
    """복구 작업 유형별 색상 정의"""
    # config에서 중앙 관리되는 색상 사용
    return REPAIR_COLORS


# 더 이상 사용되지 않음 - 통합 CSV 파일에서 필터링하여 사용
# def load_repair2_csv(csv_path: Path, verbose: bool = True) -> pd.DataFrame | None:
#     """CSV 파일 로드"""
#     if not csv_path.exists():
#         if verbose:
#             print(f"오류: CSV 파일을 찾을 수 없습니다: {csv_path}")
#         return None
#
#     try:
#         df = pd.read_csv(csv_path, encoding="utf-8-sig")
#         if "위도" not in df.columns or "경도" not in df.columns:
#             if verbose:
#                 print("오류: 위도/경도 컬럼이 없습니다.")
#             return None
#
#         valid_coords = df.dropna(subset=["위도", "경도"])
#         valid_coords = valid_coords[
#             (valid_coords["위도"] > 0) & (valid_coords["경도"] > 0)
#         ]
#
#         if verbose:
#             print(f"{csv_path.stem} 데이터 로드 완료: {len(valid_coords)}개 행")
#
#         return valid_coords
#
#     except Exception as e:
#         if verbose:
#             print(f"오류: CSV 데이터 로드 실패 - {e}")
#         return None


def load_all_repair2_data(
    results_dir: Path, verbose: bool = True
) -> dict[str, pd.DataFrame]:
    """통합 CSV 파일 로드 및 파일타입별로 분류"""
    all_data = {}

    # 통합 CSV 파일 경로
    csv_path = results_dir / "main11e_merge_all_repairs" / "누수공사_통합_위치추가.csv"

    if not csv_path.exists():
        if verbose:
            print(f"\n오류: 통합 CSV 파일을 찾을 수 없습니다: {csv_path}")
            print("먼저 main11e 스크립트를 실행하여 통합 파일을 생성하세요.")
        return all_data

    if verbose:
        print("\n통합 CSV 파일 로드 중...")

    try:
        # 통합 CSV 파일 로드
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        if "위도" not in df.columns or "경도" not in df.columns:
            if verbose:
                print("오류: 위도/경도 컬럼이 없습니다.")
            return all_data

        if "파일타입" not in df.columns:
            if verbose:
                print("오류: 파일타입 컬럼이 없습니다.")
            return all_data

        # 위치 정보가 유효한 행만 필터링
        valid_coords = df.dropna(subset=["위도", "경도"])
        valid_coords = valid_coords[
            (valid_coords["위도"] > 0) & (valid_coords["경도"] > 0)
        ]

        if verbose:
            print(f"통합 데이터 로드 완료: 총 {len(valid_coords)}개 행")

        # 파일타입별로 데이터 분류
        file_types = valid_coords["파일타입"].unique()
        for file_type in file_types:
            type_df = valid_coords[valid_coords["파일타입"] == file_type].copy()
            if len(type_df) > 0:
                all_data[file_type] = type_df
                if verbose:
                    print(f"  - {file_type}: {len(type_df)}개")

    except Exception as e:
        if verbose:
            print(f"오류: 통합 CSV 데이터 로드 실패 - {e}")

    return all_data


def find_duplicate_clusters_ultra_fast(
    all_data: dict[str, pd.DataFrame],
) -> tuple[
    dict[int, list[tuple[float, float, str]]], dict[tuple[float, float, str], int]
]:
    """
    KDTree를 사용한 초고속 중복 위치 찾기

    Returns:
        - clusters: {cluster_id: [(lat, lon, type), ...]}
        - point_to_cluster_size: {(lat, lon, type): cluster_size}
    """
    # 모든 데이터를 NumPy 배열로 변환
    all_points = []
    point_info = []  # (lat, lon, type) 정보 저장

    for repair_type, df in all_data.items():
        valid_df = df.dropna(subset=["위도", "경도"])
        if len(valid_df) > 0:
            coords = valid_df[["위도", "경도"]].values
            all_points.append(coords)
            point_info.extend([(lat, lon, repair_type) for lat, lon in coords])

    if not all_points:
        return {}, {}

    # NumPy 배열로 변환
    all_coords = np.vstack(all_points)
    n = len(all_coords)

    print(f"  - 총 {n:,}개 점 분석 중...")
    print("  - KDTree 구축 중...")

    # KDTree 구축 (위도/경도를 미터 단위로 근사 변환)
    # 대한민국 위도에서 1도 ≈ 111km, 경도 1도 ≈ 88km
    coords_scaled = all_coords.copy()
    coords_scaled[:, 0] *= 111000  # 위도를 미터로
    coords_scaled[:, 1] *= 88000  # 경도를 미터로

    tree = cKDTree(coords_scaled)

    print("  - 근접 점 검색 중...")

    # 10m 이내의 모든 점 쌍 찾기
    pairs = tree.query_pairs(r=DISTANCE_THRESHOLD, output_type="ndarray")

    if len(pairs) == 0:
        print("  - 중복 위치 없음")
        return {}, {}

    print(f"  - {len(pairs):,}개 근접 쌍 발견")

    # Union-Find로 클러스터 구성
    print("  - 클러스터 구성 중...")
    parent = list(range(n))

    def find(x: int) -> int:
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # 모든 근접 쌍을 연결
    for i, j in pairs:
        union(i, j)

    # 클러스터 구성
    cluster_members: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        if root not in cluster_members:
            cluster_members[root] = []
        cluster_members[root].append(i)

    # 2개 이상의 점을 가진 클러스터만 저장
    clusters = {}
    cluster_id = 0

    for members in cluster_members.values():
        if len(members) >= 2:
            clusters[cluster_id] = [point_info[i] for i in members]
            cluster_id += 1

    print(f"  - {len(clusters):,}개 클러스터 발견")

    # 각 점이 속한 클러스터 크기 매핑
    print("  - 클러스터 크기 매핑 테이블 생성 중...")
    point_to_cluster_size = {}

    for cid, cluster_points in clusters.items():
        cluster_size = len(cluster_points)
        for lat, lon, repair_type in cluster_points:
            key = (round(lat, 6), round(lon, 6), repair_type)
            point_to_cluster_size[key] = cluster_size

    print(f"  - 매핑 완료: {len(point_to_cluster_size):,}개 점")

    return clusters, point_to_cluster_size


def convert_wgs84_to_geodataframe(
    df: pd.DataFrame,
    lat_col: str = "위도",
    lon_col: str = "경도",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """WGS84 좌표를 GeoDataFrame으로 변환"""
    geometry = [
        Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col], strict=False)
    ]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
    return gdf.to_crs("EPSG:5179")


def precompute_point_attributes_vectorized(
    repair_data: dict[str, pd.DataFrame],
    point_to_cluster_size: dict[tuple[float, float, str], int],
    base_size: int = 50,
    min_duplicate_count: int = 0,
) -> dict[str, dict[str, Any]]:
    """
    NumPy 벡터화를 사용한 점 속성 사전 계산

    Args:
        repair_data: 복구 작업 데이터
        point_to_cluster_size: 점별 클러스터 크기 매핑
        base_size: 기본 점 크기
        min_duplicate_count: 표시할 최소 중복 횟수
    """
    print("\n점 속성 사전 계산 중...")

    colors = get_repair2_colors()
    result = {}

    for repair_type, df in repair_data.items():
        print(f"  - {repair_type}: {len(df)}개 점 처리 중...")

        # GeoDataFrame 변환
        gdf = convert_wgs84_to_geodataframe(df)
        if len(gdf) == 0:
            continue

        # 좌표 추출
        x_coords = gdf.geometry.x.values
        y_coords = gdf.geometry.y.values

        # 벡터화된 클러스터 크기 조회
        n_points = len(df)
        cluster_sizes = np.ones(n_points, dtype=int)
        mask = np.ones(n_points, dtype=bool)  # 표시할 점들의 마스크

        for i, (_, row) in enumerate(df.iterrows()):
            if pd.notna(row["위도"]) and pd.notna(row["경도"]):
                key = (round(row["위도"], 6), round(row["경도"], 6), repair_type)
                cluster_sizes[i] = point_to_cluster_size.get(key, 1)

                # 최소 중복 횟수 필터링
                if min_duplicate_count > 0 and cluster_sizes[i] < min_duplicate_count:
                    mask[i] = False

        # 모든 점을 동일한 크기로 설정
        sizes = np.full(n_points, base_size)

        # 모든 점을 동일한 엣지 색상과 너비로 설정
        edge_colors = ["white"] * n_points
        edge_widths = np.full(n_points, 0.5)

        color, _ = colors.get(repair_type, ("#808080", repair_type))

        # 필터링된 데이터만 반환
        result[repair_type] = {
            "x": x_coords[mask],
            "y": y_coords[mask],
            "sizes": sizes[mask],
            "color": color,
            "edge_colors": [ec for i, ec in enumerate(edge_colors) if mask[i]],
            "edge_widths": edge_widths[mask],
        }

    return result


def plot_optimized_scatter_batch(
    ax: Any, precomputed_attrs: dict[str, dict[str, Any]], alpha: float = 0.8
) -> list[Any]:
    """배치 처리로 최적화된 scatter plot"""
    print("\n최적화된 시각화 시작...")

    legend_elements = []
    colors = get_repair2_colors()

    for repair_type, attrs in precomputed_attrs.items():
        _, label = colors.get(repair_type, ("#808080", repair_type))

        # 한 번에 모든 점 그리기
        ax.scatter(
            attrs["x"],
            attrs["y"],
            s=attrs["sizes"],
            c=[attrs["color"]] * len(attrs["x"]),
            alpha=alpha,
            edgecolors=attrs["edge_colors"],
            linewidths=attrs["edge_widths"],
            zorder=3,
        )

        print(f"    {repair_type}: {len(attrs['x'])}개 완료")

        # 범례 추가
        legend_elements.append(
            mpatches.Circle(
                (0, 0),
                1,
                facecolor=attrs["color"],
                edgecolor="white",
                label=f"{unicodedata.normalize('NFC', label)} ({len(attrs['x'])}건)",
            )
        )

    return legend_elements


def plot_cluster_circles_vectorized(
    ax: Any,
    clusters: dict[int, list[tuple[float, float, str]]],
    min_duplicate_count: int = 0,
) -> None:
    """벡터화된 클러스터 원 그리기

    Args:
        ax: matplotlib axis
        clusters: 클러스터 데이터
        min_duplicate_count: 표시할 최소 중복 횟수
    """
    if not clusters:
        return

    print("  - 클러스터 원 그리기 중...")

    # 모든 클러스터 정보를 NumPy 배열로 변환
    centers = []
    counts = []

    for cluster_id, cluster_points in clusters.items():
        cluster_size = len(cluster_points)
        # 최소 중복 횟수 필터링
        if min_duplicate_count > 0 and cluster_size < min_duplicate_count:
            continue

        lats = np.array([p[0] for p in cluster_points])
        lons = np.array([p[1] for p in cluster_points])
        centers.append((lats.mean(), lons.mean()))
        counts.append(cluster_size)

    # 좌표 변환 (벡터화)
    centers_array = np.array(centers)
    centers_df = pd.DataFrame(centers_array, columns=["위도", "경도"])
    centers_gdf = convert_wgs84_to_geodataframe(centers_df)

    x_coords = centers_gdf.geometry.x.values
    y_coords = centers_gdf.geometry.y.values

    # 모든 원과 텍스트 한 번에 추가
    for i, (x, y, count) in enumerate(zip(x_coords, y_coords, counts, strict=False)):
        # 10m 반경 원
        circle = Circle(
            (x, y),
            10.0,
            facecolor="yellow",
            alpha=0.2,
            edgecolor="orange",
            linewidth=1,
            linestyle="--",
            zorder=2,
        )
        ax.add_patch(circle)

        # 중복 횟수 텍스트 (라운드 박스와 함께)
        if count >= 2:
            ax.text(
                x,
                y,
                str(count),
                fontsize=10,
                fontweight="bold",
                color="black",
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.05",
                    facecolor="white",
                    edgecolor="darkred",
                    linewidth=0.5,
                    alpha=0.9,
                ),
                zorder=5,
            )


def plot_repair2_locations_ultra_fast(
    repair_data: dict[str, pd.DataFrame],
    output_path: Path,
    title: str = "복구 작업 위치 분포",
    show_plot: bool = False,
    mdlz_gdf: gpd.GeoDataFrame | None = None,
    skip_duplicates: bool = False,
    min_duplicate_count: int = 0,
    scale: float = 1.0,
    bounds_type: str = "all",
    repair_type: str = "all",
) -> None:
    """초고속 복구 작업 위치 시각화

    Args:
        repair_data: 복구 작업 데이터
        output_path: 출력 경로
        title: 그래프 제목
        show_plot: 화면 표시 여부
        mdlz_gdf: MDLZ 배경 데이터
        skip_duplicates: 중복 분석 건너뛰기
        min_duplicate_count: 표시할 최소 중복 횟수 (0: 모두 표시, 2: 중복만, 4: 4회 이상만)
        scale: 이미지 크기 배율 (기본값: 1)
        bounds_type: 표시 영역 설정 (ground,underground,emergency,registry,all)
        repair_type: 표시할 복구 작업 유형 (ground,underground,emergency,registry,all)
    """
    setup_korean_font()

    # repair_type에 따라 표시할 데이터 필터링
    display_data = {}
    if repair_type == "all":
        # 모든 데이터 표시
        display_data = repair_data
        print(f"\n표시할 복구 작업 유형: 전체")
    else:
        # 특정 유형만 표시
        repair_types = [r.strip() for r in repair_type.split(",")]

        for rtype in repair_types:
            if rtype in BOUNDS_TYPE_MAP:
                korean_type = BOUNDS_TYPE_MAP[rtype]
                if korean_type in repair_data:
                    display_data[korean_type] = repair_data[korean_type]
                    print(f"  - 표시할 유형: {rtype} ({korean_type})")
                else:
                    print(f"  - 경고: {rtype} ({korean_type}) 데이터가 없습니다.")
            else:
                print(f"  - 경고: 알 수 없는 repair 유형: {rtype}")

        if not display_data:
            print("  - 경고: 표시할 유효한 데이터가 없습니다.")
            return

    # 플롯 생성 - 동적 크기 계산
    base_width, base_height = 16, 12
    figsize = (base_width * scale, base_height * scale)
    fig, ax = setup_plot_style(figsize=figsize)

    # MDLZ 배경 그리기
    if mdlz_gdf is not None and len(mdlz_gdf) > 0:
        mdlz_gdf.plot(
            ax=ax,
            facecolor="lightgray",
            edgecolor="darkgray",
            linewidth=0.5,
            alpha=0.3,
            zorder=0,
        )

    legend_elements = []

    if not skip_duplicates:
        print("\n중복 위치 분석 중...")
        # 1. KDTree로 중복 클러스터 찾기 (display_data 사용)
        clusters, point_to_cluster_size = find_duplicate_clusters_ultra_fast(
            display_data
        )

        # 2. 벡터화된 점 속성 계산 (display_data 사용)
        precomputed_attrs = precompute_point_attributes_vectorized(
            display_data, point_to_cluster_size, min_duplicate_count=min_duplicate_count
        )

        # 3. 벡터화된 클러스터 원 그리기
        if clusters:
            plot_cluster_circles_vectorized(ax, clusters, min_duplicate_count)

        # 4. 배치 scatter plot
        legend_elements = plot_optimized_scatter_batch(ax, precomputed_attrs)

        # 중복 표시 범례 추가
        if clusters:
            legend_elements.extend(
                [
                    mpatches.Rectangle(
                        (0, 0),
                        1,
                        1,
                        facecolor="none",
                        edgecolor="none",
                        label="─────────────",
                    ),
                    mpatches.Circle(
                        (0, 0),
                        1,
                        facecolor="yellow",
                        alpha=0.3,
                        edgecolor="orange",
                        label="10m 반경 클러스터",
                    ),
                ]
            )

            # 통계 정보 (display_data 사용)
            total_points = sum(len(df) for df in display_data.values())
            displayed_points = sum(
                len(attrs["x"]) for attrs in precomputed_attrs.values()
            )
            filtered_clusters = sum(
                1
                for _, points in clusters.items()
                if len(points) >= min_duplicate_count
            )

            if min_duplicate_count > 0:
                stats_text = f"총 복구 작업: {total_points:,}건\n"
                stats_text += f"표시된 점: {displayed_points:,}건 ({min_duplicate_count}회 이상 중복)\n"
                stats_text += f"중복 클러스터: {filtered_clusters:,}개"
            else:
                stats_text = f"총 복구 작업: {total_points:,}건\n중복 클러스터: {len(clusters):,}개"
        else:
            total_points = sum(len(df) for df in display_data.values())
            stats_text = f"총 복구 작업: {total_points:,}건"
    else:
        print("\n중복 위치 분석 건너뛰기...")
        # 단순 시각화 (display_data 사용)
        colors = get_repair2_colors()
        total_points = 0

        for repair_type_key, df in display_data.items():
            color, label = colors.get(repair_type_key, ("#808080", repair_type_key))
            gdf = convert_wgs84_to_geodataframe(df)

            if len(gdf) > 0:
                gdf.plot(
                    ax=ax,
                    color=color,
                    markersize=50,
                    alpha=0.8,
                    edgecolor="white",
                    linewidth=0.5,
                    zorder=3,
                )
                total_points += len(gdf)

                legend_elements.append(
                    mpatches.Circle(
                        (0, 0),
                        1,
                        facecolor=color,
                        edgecolor="white",
                        label=f"{unicodedata.normalize('NFC', label)} ({len(gdf)}건)",
                    )
                )

        stats_text = f"총 복구 작업: {total_points:,}건"

    # 경계 설정 - bounds_type에 따른 경계 계산
    print("\n데이터 기반 자동 경계 계산")

    # bounds_type 파싱 및 검증
    if bounds_type == "all":
        # 모든 데이터 사용
        selected_types = list(repair_data.keys())
        print(f"  - 표시 영역: 전체 데이터")
    else:
        # 특정 유형만 사용
        bounds_list = [b.strip() for b in bounds_type.split(",")]
        selected_types = []

        for bound in bounds_list:
            if bound in BOUNDS_TYPE_MAP:
                korean_type = BOUNDS_TYPE_MAP[bound]
                if korean_type in repair_data:
                    selected_types.append(korean_type)
                    print(f"  - 표시 영역 포함: {bound} ({korean_type})")
                else:
                    print(f"  - 경고: {bound} ({korean_type}) 데이터가 없습니다.")
            else:
                print(f"  - 경고: 알 수 없는 bounds 유형: {bound}")

        if not selected_types:
            print("  - 경고: 유효한 bounds 유형이 없어 전체 데이터를 사용합니다.")
            selected_types = list(repair_data.keys())

    # 선택된 유형의 데이터로만 경계 계산
    bounds_x = []
    bounds_y = []

    for repair_type in selected_types:
        if repair_type in repair_data:
            df = repair_data[repair_type]
            gdf = convert_wgs84_to_geodataframe(df)
            if len(gdf) > 0:
                bounds_x.extend(gdf.geometry.x.values)
                bounds_y.extend(gdf.geometry.y.values)

    if bounds_x and bounds_y:
        x_min, x_max = min(bounds_x), max(bounds_x)
        y_min, y_max = min(bounds_y), max(bounds_y)
        x_margin = (x_max - x_min) * 0.05
        y_margin = (y_max - y_min) * 0.05

        # 먼저 limits 설정
        ax.set_xlim(x_min - x_margin, x_max + x_margin)
        ax.set_ylim(y_min - y_margin, y_max + y_margin)

        print(f"  - X 범위: {x_min:.2f} ~ {x_max:.2f}")
        print(f"  - Y 범위: {y_min:.2f} ~ {y_max:.2f}")
    else:
        # 데이터가 없는 경우 경고 메시지 출력
        print("  - 경고: 시각화할 데이터가 없습니다.")
        # MDLZ 경계 사용 시도
        if mdlz_gdf is not None and len(mdlz_gdf) > 0:
            bounds = mdlz_gdf.total_bounds  # [minx, miny, maxx, maxy]
            ax.set_xlim(bounds[0], bounds[2])
            ax.set_ylim(bounds[1], bounds[3])
            print("  - MDLZ 경계를 사용합니다.")
        else:
            # 기본 서울시 범위 (대략적인 값)
            ax.set_xlim(1070000, 1120000)
            ax.set_ylim(1730000, 1780000)
            print("  - 기본 서울시 범위를 사용합니다.")

    # limits 설정 후 aspect ratio 설정 (adjustable='box'로 설정하여 axes box 조정)
    ax.set_aspect("equal", adjustable="box")

    # 제목 및 라벨
    ax.set_title(title, fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")

    # 범례
    if legend_elements:
        ax.legend(
            handles=legend_elements,
            loc="upper right",
            fontsize=10,
            title="복구 작업 유형",
            title_fontsize=11,
            framealpha=0.9,
        )

    # 통계 정보
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=12,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # 저장 (tight_layout 대신 subplots_adjust 사용하여 중앙 정렬)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    plt.savefig(output_path, dpi=300)
    print(f"\n이미지 저장 완료: {output_path}")

    if show_plot:
        plt.show()

    plt.close()


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="초고속 복구 작업 위치 시각화 스크립트"
    )
    parser.add_argument("--output-dir", type=str, help="출력 디렉토리")
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    parser.add_argument("--no-interactive", action="store_true", help="비대화형 모드")
    parser.add_argument(
        "--skip-duplicates", action="store_true", help="중복 분석 건너뛰기"
    )
    parser.add_argument(
        "--min-duplicates",
        type=int,
        default=0,
        help="표시할 최소 중복 횟수 (0: 모두, 2: 중복만, 4: 4회 이상)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="이미지 크기 배율 (기본값: 1, 기존 크기: 8)",
    )
    parser.add_argument(
        "--bounds-type",
        type=str,
        default=None,
        help="표시 영역 설정 (기본값: --repair-type과 동일) - ground,underground,emergency,registry,all - 여러 개는 쉼표로 구분",
    )
    parser.add_argument(
        "--repair-type",
        type=str,
        default="all",
        help="표시할 복구 작업 유형 (ground,underground,emergency,registry,all) - 여러 개는 쉼표로 구분",
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else RESULTS_DIR / "main12_draw_repair2"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("초고속 복구 작업 위치 시각화 (KDTree + NumPy 최적화)")
    print("=" * 60)
    print(f"데이터 디렉토리: {RESULTS_DIR}")

    # 데이터 로드
    print("\n복구 작업 데이터 로드 중...")
    repair_data = load_all_repair2_data(RESULTS_DIR, verbose=True)
    if not repair_data:
        print("오류: 복구 작업 데이터를 로드할 수 없습니다.")
        return

    # MDLZ 데이터 로드
    print("\nMDLZ (중구역) 데이터 로드 중...")
    mdlz_gdf = load_all_mdlz_shapefiles(RAW_DATA_DIR, verbose=True)

    # bounds_type이 None이면 repair_type과 동일하게 설정
    if args.bounds_type is None:
        bounds_type = args.repair_type
    else:
        bounds_type = args.bounds_type

    # 전체 통합 이미지 생성
    print("\n전체 복구 작업 위치 시각화...")

    # 제목에 필터링 정보 추가
    title = "전체 복구 작업 위치 분포 (초고속 버전)"
    if args.min_duplicates > 0:
        title += f" - {args.min_duplicates}회 이상 중복만 표시"
        output_filename = f"all_repair2_ultra_fast_min{args.min_duplicates}.png"
    else:
        output_filename = "all_repair2_ultra_fast.png"

    output_path = output_dir / output_filename
    plot_repair2_locations_ultra_fast(
        repair_data,
        output_path,
        title=title,
        show_plot=args.show,
        mdlz_gdf=mdlz_gdf,
        skip_duplicates=args.skip_duplicates,
        min_duplicate_count=args.min_duplicates,
        scale=args.scale,
        bounds_type=bounds_type,
        repair_type=args.repair_type,
    )

    print("\n시각화 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
