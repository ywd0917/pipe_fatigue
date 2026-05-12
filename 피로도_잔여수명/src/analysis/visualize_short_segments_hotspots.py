"""
1m 이하 PIPE_LM 세그먼트 밀집 지역 확대 시각화
- 짧은 세그먼트가 가장 많이 몰려있는 10개 지역 찾기
- 각 지역을 개별적으로 확대하여 시각화
"""

import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString, Point, box

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font
from src.common.shapefile_loader import load_pipe_shapefile
from src.common.visualization_utils import setup_plot_style


def extract_short_segments(
    geometry: Any, max_length: float = 1.0
) -> list[tuple[LineString, Point]]:
    """
    LineString에서 지정된 길이 이하의 세그먼트와 중심점 추출

    Args:
        geometry: LineString 또는 MultiLineString geometry
        max_length: 최대 길이 (기본값: 1.0m)

    Returns:
        [(세그먼트, 중심점)] 리스트
    """
    short_segments = []

    if geometry.geom_type == "LineString":
        coords = list(geometry.coords)
        for i in range(len(coords) - 1):
            start = Point(coords[i])
            end = Point(coords[i + 1])
            segment_length = start.distance(end)

            if segment_length <= max_length:
                segment = LineString([coords[i], coords[i + 1]])
                # 세그먼트 중심점 계산
                center = Point(
                    (coords[i][0] + coords[i + 1][0]) / 2,
                    (coords[i][1] + coords[i + 1][1]) / 2,
                )
                short_segments.append((segment, center))

    elif geometry.geom_type == "MultiLineString":
        for line in geometry.geoms:
            short_segments.extend(extract_short_segments(line, max_length))

    return short_segments


def find_hotspot_areas_by_grid(
    centers: list[Point],
    total_bounds: tuple[float, float, float, float],
    n_hotspots: int = 10,
    grid_size: int = 100,
) -> list[dict[str, Any]]:
    """
    그리드 기반으로 세그먼트 밀집 지역 찾기

    Args:
        centers: 세그먼트 중심점 리스트
        total_bounds: 전체 영역 경계
        n_hotspots: 찾을 밀집 지역 수
        grid_size: 그리드 크기

    Returns:
        밀집 지역 정보 리스트
    """
    min_x, min_y, max_x, max_y = total_bounds
    x_step = (max_x - min_x) / grid_size
    y_step = (max_y - min_y) / grid_size

    # 각 그리드 셀의 세그먼트 수 계산
    grid_density: dict[tuple[int, int], list[Point]] = {}

    for center in centers:
        # 그리드 인덱스 계산
        i = int((center.x - min_x) / x_step)
        j = int((center.y - min_y) / y_step)

        # 경계 처리
        i = max(0, min(i, grid_size - 1))
        j = max(0, min(j, grid_size - 1))

        # 주변 셀도 포함하여 밀도 계산 (3x3 영역)
        for di in range(-1, 2):
            for dj in range(-1, 2):
                ni, nj = i + di, j + dj
                if 0 <= ni < grid_size and 0 <= nj < grid_size:
                    key = (ni, nj)
                    if key not in grid_density:
                        grid_density[key] = []
                    grid_density[key].append(center)

    # 밀집도가 높은 지역 찾기
    density_scores = []

    for (i, j), points in grid_density.items():
        if (
            len(set(points)) >= 5
        ):  # 최소 5개 이상의 unique 점 (더 작은 영역이므로 기준 완화)
            unique_points = list(set(points))

            # 실제 점들의 경계
            x_coords = [p.x for p in unique_points]
            y_coords = [p.y for p in unique_points]

            density_scores.append(
                {
                    "grid_pos": (i, j),
                    "center": Point(np.mean(x_coords), np.mean(y_coords)),
                    "bounds": (
                        min(x_coords),
                        min(y_coords),
                        max(x_coords),
                        max(y_coords),
                    ),
                    "count": len(unique_points),
                    "points": unique_points,
                    "density": len(unique_points)
                    / (x_step * y_step),  # 단위 면적당 밀도
                }
            )

    # 밀도가 높은 순으로 정렬
    density_scores.sort(key=lambda x: x["density"], reverse=True)

    # 겹치는 영역 제거
    hotspots: list[dict[str, Any]] = []
    selected_grids = set()

    for item in density_scores:
        i, j = item["grid_pos"]
        # 주변 영역이 이미 선택되었는지 확인 (더 작은 영역이므로 1x1만 체크)
        overlap = False
        for di in range(-1, 2):
            for dj in range(-1, 2):
                if (i + di, j + dj) in selected_grids:
                    overlap = True
                    break
            if overlap:
                break

        if not overlap and len(hotspots) < n_hotspots:
            hotspots.append(item)
            selected_grids.add((i, j))

    return hotspots


def visualize_hotspot(
    pipe_gdf: gpd.GeoDataFrame,
    short_segments_gdf: gpd.GeoDataFrame,
    hotspot: dict[str, Any],
    hotspot_idx: int,
    output_dir: Path,
) -> None:
    """
    특정 밀집 지역 확대 시각화

    Args:
        pipe_gdf: 전체 파이프 GeoDataFrame
        short_segments_gdf: 짧은 세그먼트 GeoDataFrame
        hotspot: 밀집 지역 정보
        hotspot_idx: 밀집 지역 인덱스
        output_dir: 출력 디렉토리
    """
    fig, ax = setup_plot_style(figsize=(12, 12))

    # 경계 설정 (여유 공간 추가)
    bounds = hotspot["bounds"]
    x_range = bounds[2] - bounds[0]
    y_range = bounds[3] - bounds[1]
    margin = max(x_range, y_range) * 0.5  # 더 많은 여유 공간

    x_min = bounds[0] - margin
    x_max = bounds[2] + margin
    y_min = bounds[1] - margin
    y_max = bounds[3] + margin

    # 해당 지역의 파이프 필터링
    area_pipes = pipe_gdf.cx[x_min:x_max, y_min:y_max]
    area_segments = short_segments_gdf.cx[x_min:x_max, y_min:y_max]

    # 배경 파이프 그리기
    if len(area_pipes) > 0:
        area_pipes.plot(
            ax=ax, color="lightblue", linewidth=1.5, alpha=0.4, label="전체 파이프"
        )

    # 짧은 세그먼트 강조
    if len(area_segments) > 0:
        area_segments.plot(
            ax=ax,
            color="red",
            linewidth=4.0,
            alpha=0.9,
            label=f"1m 이하 세그먼트 ({len(area_segments)}개)",
        )

    # 밀집 지역 경계 표시
    hotspot_box = box(bounds[0], bounds[1], bounds[2], bounds[3])
    gpd.GeoSeries([hotspot_box]).plot(
        ax=ax,
        facecolor="none",
        edgecolor="darkred",
        linewidth=2,
        linestyle="--",
        alpha=0.7,
    )

    # 경계 설정
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # 제목 및 라벨
    ax.set_title(
        f'PIPE_LM 1m 이하 세그먼트 밀집 지역 #{hotspot_idx} ({hotspot["count"]}개 세그먼트)',
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 범례
    ax.legend(loc="upper right", fontsize=10)

    # 통계 정보
    stats_text = f"밀집 지역 내: {hotspot['count']}개\n"
    stats_text += f"표시 영역 내: {len(area_segments)}개"

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # 저장
    output_path = output_dir / f"pipe_lm_hotspot_{hotspot_idx:02d}.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"  - 밀집 지역 #{hotspot_idx} 저장: {output_path} ({hotspot['count']}개)")

    plt.close()


def main() -> None:
    """메인 실행 함수"""
    print("1m 이하 PIPE_LM 세그먼트 밀집 지역 분석 시작...")

    # 한글 폰트 설정
    setup_korean_font()

    # PIPE_LM 데이터 로드
    print("\nPIPE_LM 데이터 로드 중...")
    pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "PIPE_LM")

    if pipe_lm_gdf is None:
        print("오류: PIPE_LM 데이터를 로드할 수 없습니다.")
        return

    print(f"전체 PIPE_LM 객체: {len(pipe_lm_gdf)}개")

    # 1m 이하 세그먼트와 중심점 추출
    print("\n1m 이하 세그먼트 추출 중...")
    all_segments_with_centers = []

    for idx, row in pipe_lm_gdf.iterrows():
        if row.geometry is not None:
            segments_with_centers = extract_short_segments(row.geometry, max_length=1.0)
            all_segments_with_centers.extend(segments_with_centers)

    print(f"추출된 1m 이하 세그먼트: {len(all_segments_with_centers)}개")

    # 세그먼트와 중심점 분리
    segments = [item[0] for item in all_segments_with_centers]
    centers = [item[1] for item in all_segments_with_centers]

    # GeoDataFrame 생성
    short_segments_gdf = gpd.GeoDataFrame(geometry=segments, crs=pipe_lm_gdf.crs)

    # 밀집 지역 찾기 (그리드 기반 분석)
    print("\n밀집 지역 분석 중...")
    hotspots = find_hotspot_areas_by_grid(
        centers, short_segments_gdf.total_bounds, n_hotspots=10
    )

    print(f"\n발견된 밀집 지역: {len(hotspots)}개")

    # 출력 디렉토리 생성
    output_dir = RESULTS_DIR / "pipe_segment_analysis" / "hotspots"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 각 밀집 지역 시각화
    print("\n밀집 지역 시각화 중...")
    for i, hotspot in enumerate(hotspots, 1):
        visualize_hotspot(pipe_lm_gdf, short_segments_gdf, hotspot, i, output_dir)

    # 전체 개요 맵 생성
    create_overview_map(pipe_lm_gdf, short_segments_gdf, hotspots, output_dir)

    print("\n분석 완료!")


def create_overview_map(
    pipe_gdf: gpd.GeoDataFrame,
    short_segments_gdf: gpd.GeoDataFrame,
    hotspots: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    """
    전체 개요 맵 생성 (모든 밀집 지역 표시)
    """
    fig, ax = setup_plot_style(figsize=(16, 12))

    # 전체 파이프 표시
    pipe_gdf.plot(
        ax=ax, color="lightblue", linewidth=0.8, alpha=0.3, label="전체 PIPE_LM"
    )

    # 짧은 세그먼트 표시
    short_segments_gdf.plot(
        ax=ax, color="red", linewidth=1.5, alpha=0.6, label="1m 이하 세그먼트"
    )

    # 밀집 지역 표시
    for i, hotspot in enumerate(hotspots, 1):
        bounds = hotspot["bounds"]
        hotspot_box = box(bounds[0], bounds[1], bounds[2], bounds[3])

        gpd.GeoSeries([hotspot_box]).plot(
            ax=ax, facecolor="yellow", edgecolor="darkred", linewidth=2, alpha=0.3
        )

        # 번호 표시
        ax.text(
            hotspot["center"].x,
            hotspot["center"].y,
            str(i),
            fontsize=12,
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(boxstyle="circle", facecolor="yellow", alpha=0.8),
        )

    # 경계 설정
    bounds = pipe_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05
    ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)

    # 제목 및 라벨
    ax.set_title(
        f"PIPE_LM 1m 이하 세그먼트 밀집 지역 개요 - 상위 {len(hotspots)}개 지역",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 범례
    ax.legend(loc="upper right", fontsize=10)

    # 저장
    output_path = output_dir / "pipe_lm_hotspots_overview.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n개요 맵 저장: {output_path}")

    plt.close()


if __name__ == "__main__":
    main()
