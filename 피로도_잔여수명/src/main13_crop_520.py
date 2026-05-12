"""
MDLZ 0520 영역의 복구 작업 데이터 중복 위치 분석 및 시각화 스크립트
- KDTree를 사용한 초고속 중복 위치 분석
- NumPy 벡터화 연산
- 10m 이내 중복 위치 클러스터링
- MDLZ 0520 영역 필터링 및 시각화
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
from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.visualization_utils import setup_plot_style

# 비대화형 모드 체크
if "--no-interactive" in sys.argv:
    matplotlib.use("Agg")

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 중복 판단 거리 임계값 (미터 단위)
DISTANCE_THRESHOLD = 10.0


def setup_korean_font() -> None:
    """한글 폰트 설정"""
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")
    else:
        print("경고: 한글 폰트를 찾을 수 없습니다.")


def get_repair2_colors() -> dict[str, tuple[str, str]]:
    """복구 작업 유형별 색상 정의"""
    return {
        "지상누수": ("#4ECDC4", "지상누수"),
        "지하누수": ("#45B7D1", "지하누수"),
        "긴급공사": ("#FF6B6B", "긴급공사"),
        "관리대장": ("#FFA500", "관리대장"),
    }


def load_mdlz_520_shapefile(
    data_dir: Path, verbose: bool = True
) -> gpd.GeoDataFrame | None:
    """MDLZ 0520 영역 shapefile 로드"""
    mdlz_path = data_dir / "export_shp_20250704(0520)" / "WEA_MDLZ_AS.shp"

    if not mdlz_path.exists():
        if verbose:
            print(f"오류: MDLZ shapefile을 찾을 수 없습니다: {mdlz_path}")
        return None

    try:
        mdlz_gdf = gpd.read_file(mdlz_path, encoding="euc-kr")

        if mdlz_gdf.crs is None:
            mdlz_gdf.set_crs("EPSG:5179", inplace=True)

        if verbose:
            print(f"MDLZ shapefile 로드 완료: {len(mdlz_gdf)}개 구역")

        # 0520 구역만 필터링
        mdlz_0520 = mdlz_gdf[mdlz_gdf["MDZ_NUM"] == "0520"]

        if verbose:
            print(f"MDZ_NUM 0520 구역만 필터링: {len(mdlz_0520)}개 구역")

        return mdlz_0520

    except Exception as e:
        if verbose:
            print(f"오류: MDLZ shapefile 로드 실패 - {e}")
        return None


def save_filtered_csv(
    repair_data: dict[str, pd.DataFrame], output_path: Path, verbose: bool = True
) -> None:
    """필터링된 520 지역 데이터를 통합 CSV로 저장"""
    if not repair_data:
        if verbose:
            print("저장할 데이터가 없습니다.")
        return

    # 모든 데이터프레임을 하나로 통합
    all_dfs = []
    for file_type, df in repair_data.items():
        if len(df) > 0:
            # 파일타입 컬럼이 없으면 추가
            if "파일타입" not in df.columns:
                df["파일타입"] = file_type
            all_dfs.append(df)

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        # 작업일시 기준으로 정렬
        if "작업일시" in combined_df.columns:
            combined_df = combined_df.sort_values("작업일시")

        combined_df.to_csv(output_path, index=False, encoding="utf-8-sig")

        if verbose:
            print(f"\n필터링된 데이터 저장 완료: {output_path}")
            print(f"  - 총 {len(combined_df)}개 행 저장")


def save_statistics_report(
    total_stats: dict, filtered_stats: dict, output_dir: Path, verbose: bool = True
) -> None:
    """처리 통계를 텍스트 파일로 저장"""
    report_path = output_dir / "처리통계.txt"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("MDLZ 0520 지역 복구 작업 데이터 처리 통계\n")
        f.write("=" * 60 + "\n\n")

        # 원본 데이터 통계
        f.write("[원본 데이터]\n")
        f.write(f"총 항목 수: {total_stats['total']:,}개\n")
        f.write("\n파일타입별 항목 수:\n")
        for file_type, count in total_stats["by_type"].items():
            f.write(f"  - {file_type}: {count:,}개\n")

        f.write(f"\n위치 정보가 있는 항목 수: {total_stats['with_location']:,}개\n")
        f.write("\n파일타입별 위치 정보 있는 항목 수:\n")
        for file_type, count in total_stats["with_location_by_type"].items():
            original_count = total_stats["by_type"].get(file_type, 0)
            diff = count - original_count
            f.write(f"  - {file_type}: {count:,}개 ({diff:+,}개)\n")

        # 520 지역 필터링 데이터 통계
        f.write("\n" + "=" * 60 + "\n")
        f.write("[MDLZ 0520 지역 필터링 후]\n")
        f.write(f"총 항목 수: {filtered_stats['total']:,}개\n")
        f.write("\n파일타입별 항목 수:\n")

        # 모든 파일타입 처리 (520 지역에 없는 것도 포함)
        all_types = set(total_stats["with_location_by_type"].keys())
        for file_type in all_types:
            count = filtered_stats["by_type"].get(file_type, 0)
            with_location_count = total_stats["with_location_by_type"].get(file_type, 0)
            if with_location_count > 0:
                percentage = (count / with_location_count) * 100
                f.write(
                    f"  - {file_type}: {count:,}개 (위치있는 것 대비 {percentage:.1f}%)\n"
                )
            else:
                f.write(f"  - {file_type}: {count:,}개 (위치있는 것 대비 0.0%)\n")

        # 필터링 비율
        if total_stats["with_location"] > 0:
            filter_rate = (filtered_stats["total"] / total_stats["with_location"]) * 100
            f.write(f"\n520 지역 필터링 비율: {filter_rate:.1f}%\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write(f"처리 일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    if verbose:
        print(f"\n처리 통계 저장 완료: {report_path}")


def load_repair2_csv_520(csv_path: Path, verbose: bool = True) -> pd.DataFrame | None:
    """520 지역 CSV 파일 로드"""
    if not csv_path.exists():
        if verbose:
            print(f"오류: CSV 파일을 찾을 수 없습니다: {csv_path}")
        return None

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if "위도" not in df.columns or "경도" not in df.columns:
            if verbose:
                print("오류: 위도/경도 컬럼이 없습니다.")
            return None

        valid_coords = df.dropna(subset=["위도", "경도"])
        valid_coords = valid_coords[
            (valid_coords["위도"] > 0) & (valid_coords["경도"] > 0)
        ]

        if verbose:
            print(f"{csv_path.stem} 데이터 로드 완료: {len(valid_coords)}개 행")

        return valid_coords

    except Exception as e:
        if verbose:
            print(f"오류: CSV 데이터 로드 실패 - {e}")
        return None


def load_unified_repair_data(
    input_path: Path, mdlz_gdf: gpd.GeoDataFrame | None = None, verbose: bool = True
) -> tuple[dict[str, pd.DataFrame], dict, dict]:
    """통합 CSV 파일 로드 및 520 지역 필터링

    Returns:
        tuple: (repair_data, total_stats, filtered_stats)
    """
    total_stats = {
        "total": 0,
        "by_type": {},
        "with_location": 0,
        "with_location_by_type": {},
    }

    filtered_stats = {"total": 0, "by_type": {}}

    if not input_path.exists():
        if verbose:
            print(f"오류: 통합 CSV 파일을 찾을 수 없습니다: {input_path}")
        return {}, total_stats, filtered_stats

    try:
        # 통합 CSV 파일 로드
        df_raw = pd.read_csv(input_path, encoding="utf-8-sig")

        # 원본 데이터 통계
        total_stats["total"] = len(df_raw)
        for file_type in df_raw["파일타입"].unique():
            total_stats["by_type"][file_type] = len(
                df_raw[df_raw["파일타입"] == file_type]
            )

        # 위도/경도가 있는 행만 필터링
        df = df_raw.dropna(subset=["위도", "경도"])
        df = df[(df["위도"] > 0) & (df["경도"] > 0)]

        # 위치 정보 있는 데이터 통계
        total_stats["with_location"] = len(df)
        for file_type in df["파일타입"].unique():
            total_stats["with_location_by_type"][file_type] = len(
                df[df["파일타입"] == file_type]
            )

        if verbose:
            removed_count = total_stats["total"] - total_stats["with_location"]
            if removed_count > 0:
                print(f"  - 위치 정보 없는 {removed_count:,}개 행 제거")

        # MDLZ 0520 영역으로 필터링 (mdlz_gdf가 있는 경우)
        if mdlz_gdf is not None and len(mdlz_gdf) > 0:
            # WGS84 좌표를 GeoDataFrame으로 변환
            from shapely.geometry import Point

            geometry = [
                Point(lon, lat)
                for lon, lat in zip(df["경도"], df["위도"], strict=False)
            ]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
            gdf = gdf.to_crs("EPSG:5179")

            # MDLZ 0520 영역 내의 점들만 선택
            within_520 = gpd.sjoin(gdf, mdlz_gdf, predicate="within", how="inner")
            df = df.loc[within_520.index]

            if verbose:
                print(f"  - MDLZ 0520 영역 내 {len(df):,}개 점 필터링 완료")

        # 520 필터링 후 통계
        filtered_stats["total"] = len(df)

        # 파일타입별로 데이터 분류
        all_data = {}
        file_types = df["파일타입"].unique()

        if verbose:
            print(f"\n통합 파일 로드 완료: 총 {len(df):,}개 행")
            print(f"파일 타입: {', '.join(file_types)}")

        for file_type in file_types:
            type_df = df[df["파일타입"] == file_type].copy()
            if len(type_df) > 0:
                all_data[file_type] = type_df
                filtered_stats["by_type"][file_type] = len(type_df)
                if verbose:
                    print(f"  - {file_type}: {len(type_df):,}개")

        return all_data, total_stats, filtered_stats

    except Exception as e:
        if verbose:
            print(f"오류: 통합 데이터 로드 실패 - {e}")
        return {}, total_stats, filtered_stats


def find_duplicate_clusters_ultra_fast(
    all_data: dict[str, pd.DataFrame],
) -> tuple[
    dict[int, list[tuple[float, float, str]]], dict[tuple[float, float, str], int]
]:
    """KDTree를 사용한 초고속 중복 위치 찾기"""
    all_points = []
    point_info = []

    for repair_type, df in all_data.items():
        valid_df = df.dropna(subset=["위도", "경도"])
        if len(valid_df) > 0:
            coords = valid_df[["위도", "경도"]].values
            all_points.append(coords)
            point_info.extend([(lat, lon, repair_type) for lat, lon in coords])

    if not all_points:
        return {}, {}

    all_coords = np.vstack(all_points)
    n = len(all_coords)

    print(f"  - 총 {n:,}개 점 분석 중...")
    print("  - KDTree 구축 중...")

    # KDTree 구축 (위도/경도를 미터 단위로 근사 변환)
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


def load_pipe_data_520(data_dir: Path, verbose: bool = True) -> gpd.GeoDataFrame | None:
    """MDLZ 0520 영역의 파이프 데이터 로드"""
    # V_WTL_PIPE_LM.shp 파일 사용 (Water Pipe Line)
    pipe_path = data_dir / "export_shp_20250704(0520)" / "V_WTL_PIPE_LM.shp"

    if not pipe_path.exists():
        if verbose:
            print(f"오류: 파이프 shapefile을 찾을 수 없습니다: {pipe_path}")
        return None

    try:
        pipe_gdf = gpd.read_file(pipe_path, encoding="euc-kr")

        if pipe_gdf.crs is None:
            pipe_gdf.set_crs("EPSG:5179", inplace=True)

        if verbose:
            print(f"파이프 shapefile 로드 완료: {len(pipe_gdf)}개 파이프")

        return pipe_gdf

    except Exception as e:
        if verbose:
            print(f"오류: 파이프 shapefile 로드 실패 - {e}")
        return None


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
    """NumPy 벡터화를 사용한 점 속성 사전 계산"""
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

        if len(attrs["x"]) > 0:
            # 한 번에 모든 점 그리기
            ax.scatter(
                attrs["x"],
                attrs["y"],
                s=attrs["sizes"],
                c=[attrs["color"]] * len(attrs["x"]),
                alpha=alpha,
                edgecolors=attrs["edge_colors"],
                linewidths=attrs["edge_widths"],
                zorder=3,  # zorder를 3으로 변경
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
    """벡터화된 클러스터 원 그리기"""
    if not clusters:
        return

    print("  - 클러스터 원 그리기 중...")

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

    if not centers:
        return

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
            zorder=2,  # zorder를 2로 변경
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


def plot_repair2_locations_520(
    repair_data: dict[str, pd.DataFrame],
    output_path: Path,
    title: str = "MDLZ 0520 복구 작업 위치 분포",
    show_plot: bool = False,
    mdlz_gdf: gpd.GeoDataFrame | None = None,
    pipe_gdf: gpd.GeoDataFrame | None = None,
    skip_duplicates: bool = False,
    min_duplicate_count: int = 0,
    scale: float = 1.0,
) -> None:
    """MDLZ 0520 영역 복구 작업 위치 시각화 (파이프 데이터 포함)"""
    setup_korean_font()

    # 플롯 생성 - 동적 크기 계산
    base_width, base_height = 16, 12
    figsize = (base_width * scale, base_height * scale)
    fig, ax = setup_plot_style(figsize=figsize)

    # MDLZ 배경 그리기
    if mdlz_gdf is not None and len(mdlz_gdf) > 0:
        mdlz_gdf.plot(
            ax=ax,
            facecolor="lightblue",  # 520 지역은 연한 파란색으로
            edgecolor="darkblue",
            linewidth=1.5,
            alpha=0.2,
            zorder=0,
        )

    # 파이프 네트워크 그리기
    if pipe_gdf is not None and len(pipe_gdf) > 0:
        pipe_gdf.plot(
            ax=ax,
            color="gray",
            linewidth=0.5,
            alpha=0.4,
            zorder=2,  # zorder를 2로 높여서 배경 위에 표시
        )

    legend_elements = []

    if not skip_duplicates:
        print("\n중복 위치 분석 중...")
        # 1. KDTree로 중복 클러스터 찾기
        clusters, point_to_cluster_size = find_duplicate_clusters_ultra_fast(
            repair_data
        )

        # 2. 벡터화된 점 속성 계산
        precomputed_attrs = precompute_point_attributes_vectorized(
            repair_data, point_to_cluster_size, min_duplicate_count=min_duplicate_count
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
                    mpatches.Circle(
                        (0, 0),
                        1,
                        facecolor="gray",
                        edgecolor="red",
                        linewidth=2,
                        label="중복 위치 (빨간 테두리)",
                    ),
                ]
            )

            # 통계 정보
            total_points = sum(len(df) for df in repair_data.values())
            displayed_points = sum(
                len(attrs["x"]) for attrs in precomputed_attrs.values()
            )
            filtered_clusters = sum(
                1
                for _, points in clusters.items()
                if len(points) >= min_duplicate_count
            )

            if min_duplicate_count > 0:
                stats_text = "MDLZ 0520 지역\n"
                stats_text += f"총 복구 작업: {total_points:,}건\n"
                stats_text += f"표시된 점: {displayed_points:,}건 ({min_duplicate_count}회 이상 중복)\n"
                stats_text += f"중복 클러스터: {filtered_clusters:,}개"
            else:
                stats_text = "MDLZ 0520 지역\n"
                stats_text += f"총 복구 작업: {total_points:,}건\n"
                stats_text += f"중복 클러스터: {len(clusters):,}개"

            # 파이프 정보 추가
            if pipe_gdf is not None and len(pipe_gdf) > 0:
                stats_text += f"\n파이프: {len(pipe_gdf):,}개"
        else:
            total_points = sum(len(df) for df in repair_data.values())
            stats_text = f"MDLZ 0520 지역\n총 복구 작업: {total_points:,}건"
            if pipe_gdf is not None and len(pipe_gdf) > 0:
                stats_text += f"\n파이프: {len(pipe_gdf):,}개"
    else:
        print("\n중복 위치 분석 건너뛰기...")
        # 단순 시각화
        colors = get_repair2_colors()
        total_points = 0

        for repair_type, df in repair_data.items():
            color, label = colors.get(repair_type, ("#808080", repair_type))
            gdf = convert_wgs84_to_geodataframe(df)

            if len(gdf) > 0:
                gdf.plot(
                    ax=ax,
                    color=color,
                    markersize=50,
                    alpha=0.8,
                    edgecolor="white",
                    linewidth=0.5,
                    zorder=3,  # zorder를 3으로 변경
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

        stats_text = f"MDLZ 0520 지역\n총 복구 작업: {total_points:,}건"

    # 경계 설정 (MDLZ 0520 영역에 맞춤)
    if mdlz_gdf is not None and len(mdlz_gdf) > 0:
        minx, miny, maxx, maxy = mdlz_gdf.total_bounds
        x_margin = (maxx - minx) * 0.05
        y_margin = (maxy - miny) * 0.05

        ax.set_xlim(minx - x_margin, maxx + x_margin)
        ax.set_ylim(miny - y_margin, maxy + y_margin)
        print("\nMDLZ 0520 영역 범위 사용")

    # 제목 및 라벨
    ax.set_title(title, fontsize=18, fontweight="bold", pad=20)
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

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
        description="MDLZ 0520 영역 복구 작업 중복 위치 분석 및 시각화"
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
        help="이미지 크기 배율 (기본값: 1, 기존 크기: 2)",
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    # 출력 디렉토리 설정: results/main13_crop_520/
    output_dir = (
        Path(args.output_dir) if args.output_dir else RESULTS_DIR / "main13_crop_520"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("MDLZ 0520 영역 복구 작업 중복 위치 분석")
    print("=" * 60)
    print(f"입력 디렉토리: {RESULTS_DIR / 'main11e_merge_all_repairs'}")
    print(f"출력 디렉토리: {output_dir}")

    # 통합 입력 파일 경로
    input_path = (
        RESULTS_DIR / "main11e_merge_all_repairs" / "누수공사_통합_위치추가.csv"
    )

    if not input_path.exists():
        print(f"\n오류: 통합 입력 파일을 찾을 수 없습니다: {input_path}")
        print("먼저 main11e 스크립트를 실행하여 통합 파일을 생성하세요.")
        return

    # MDLZ 0520 데이터 로드
    print("\nMDLZ 0520 영역 로드 중...")
    mdlz_gdf = load_mdlz_520_shapefile(RAW_DATA_DIR, verbose=True)

    # 통합 데이터 로드 및 520 지역 필터링
    print("\n통합 복구 작업 데이터 로드 및 520 지역 필터링 중...")
    repair_data, total_stats, filtered_stats = load_unified_repair_data(
        input_path, mdlz_gdf=mdlz_gdf, verbose=True
    )

    if not repair_data:
        print("\n520 지역에 해당하는 데이터가 없습니다.")
        return

    # 필터링된 데이터를 CSV로 저장
    csv_output_path = output_dir / "누수공사_통합_520_위치추가.csv"
    save_filtered_csv(repair_data, csv_output_path, verbose=True)

    # 처리 통계 저장
    save_statistics_report(total_stats, filtered_stats, output_dir, verbose=True)

    # 파이프 데이터 로드
    print("\n파이프 데이터 로드 중...")
    pipe_gdf = load_pipe_data_520(RAW_DATA_DIR, verbose=True)

    # 이미지 생성
    print("\nMDLZ 0520 영역 복구 작업 위치 시각화...")

    # 제목에 필터링 정보 추가
    title = "MDLZ 0520 영역 복구 작업 위치 분포"
    if args.min_duplicates > 0:
        title += f" - {args.min_duplicates}회 이상 중복만 표시"
        output_filename = f"누수공사_통합_520_위치추가_min{args.min_duplicates}.png"
    else:
        output_filename = "누수공사_통합_520_위치추가.png"

    png_output_path = output_dir / output_filename
    plot_repair2_locations_520(
        repair_data,
        png_output_path,
        title=title,
        show_plot=args.show,
        mdlz_gdf=mdlz_gdf,
        pipe_gdf=pipe_gdf,
        skip_duplicates=args.skip_duplicates,
        min_duplicate_count=args.min_duplicates,
        scale=args.scale,
    )

    print("\n시각화 완료!")
    print(f"CSV 저장: {csv_output_path}")
    print(f"이미지 저장: {png_output_path}")
    print(f"통계 저장: {output_dir / '처리통계.txt'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
