"""
1m 이하 PIPE_LM 세그먼트 시각화
- 전체 파이프를 흐리게 배경으로 표시
- 1m 이하 세그먼트를 붉은색으로 강조
"""

import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString, Point

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font
from src.common.shapefile_loader import get_smlz_shapefile_path, load_pipe_shapefile
from src.common.visualization_utils import setup_plot_style


def extract_short_segments(geometry: Any, max_length: float = 1.0) -> list[LineString]:
    """
    LineString에서 지정된 길이 이하의 세그먼트만 추출

    Args:
        geometry: LineString 또는 MultiLineString geometry
        max_length: 최대 길이 (기본값: 1.0m)

    Returns:
        짧은 LineString 세그먼트 리스트
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
                short_segments.append(segment)

    elif geometry.geom_type == "MultiLineString":
        for line in geometry.geoms:
            short_segments.extend(extract_short_segments(line, max_length))

    return short_segments


def visualize_short_pipe_segments() -> None:
    """1m 이하 PIPE_LM 세그먼트 시각화"""
    print("1m 이하 PIPE_LM 세그먼트 시각화 시작...")

    # 한글 폰트 설정
    setup_korean_font()

    # PIPE_LM 데이터 로드
    print("\nPIPE_LM 데이터 로드 중...")
    pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "PIPE_LM")

    if pipe_lm_gdf is None:
        print("오류: PIPE_LM 데이터를 로드할 수 없습니다.")
        return

    print(f"전체 PIPE_LM 객체: {len(pipe_lm_gdf)}개")

    # 1m 이하 세그먼트 추출
    print("\n1m 이하 세그먼트 추출 중...")
    all_short_segments = []

    for idx, row in pipe_lm_gdf.iterrows():
        if row.geometry is not None:
            short_segments = extract_short_segments(row.geometry, max_length=1.0)
            all_short_segments.extend(short_segments)

    print(f"추출된 1m 이하 세그먼트: {len(all_short_segments)}개")

    # GeoDataFrame 생성
    short_segments_gdf = gpd.GeoDataFrame(
        geometry=all_short_segments, crs=pipe_lm_gdf.crs
    )

    # SMLZ 파일 경로
    smlz_file = get_smlz_shapefile_path(RAW_DATA_DIR, "0520")

    # 플롯 생성
    fig, ax = setup_plot_style(figsize=(16, 12))

    # SMLZ 배경 (옵션)
    if smlz_file and smlz_file.exists():
        smlz_gdf = gpd.read_file(smlz_file)
        smlz_gdf.plot(
            ax=ax, facecolor="none", edgecolor="lightgray", linewidth=0.5, alpha=0.3
        )

    # 전체 파이프를 흐리게 표시
    pipe_lm_gdf.plot(
        ax=ax, color="lightblue", linewidth=0.8, alpha=0.3, label="전체 PIPE_LM"
    )

    # 1m 이하 세그먼트를 붉은색으로 강조
    short_segments_gdf.plot(
        ax=ax,
        color="red",
        linewidth=2.0,
        alpha=0.8,
        label=f"1m 이하 세그먼트 ({len(all_short_segments)}개)",
    )

    # 경계 설정
    bounds = pipe_lm_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05
    ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)

    # 제목 및 라벨
    ax.set_title(
        "PIPE_LM 1m 이하 세그먼트 분포 - 0520", fontsize=16, fontweight="bold", pad=20
    )
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 범례
    ax.legend(loc="upper right", fontsize=10)

    # 통계 정보 추가
    stats_text = f"전체 PIPE_LM: {len(pipe_lm_gdf)}개\n"
    stats_text += f"1m 이하 세그먼트: {len(all_short_segments)}개"

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
    output_dir = RESULTS_DIR / "pipe_segment_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pipe_lm_short_segments_1m.png"

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    plt.close()

    # 상세 분석을 위한 줌인 버전도 생성
    create_zoomed_views(pipe_lm_gdf, short_segments_gdf, output_dir)


def create_zoomed_views(
    pipe_gdf: gpd.GeoDataFrame,
    short_segments_gdf: gpd.GeoDataFrame,
    output_dir: Path,
    n_zones: int = 4,
) -> None:
    """주요 지역의 확대 뷰 생성"""
    print("\n확대 뷰 생성 중...")

    # 짧은 세그먼트가 집중된 지역 찾기
    bounds = short_segments_gdf.total_bounds
    x_range = bounds[2] - bounds[0]
    y_range = bounds[3] - bounds[1]

    # 그리드로 나누어 각 구역별로 시각화
    grid_size = int(np.sqrt(n_zones))

    for i in range(grid_size):
        for j in range(grid_size):
            zone_idx = i * grid_size + j + 1

            # 구역 경계 계산
            x_min = bounds[0] + (x_range / grid_size) * j
            x_max = bounds[0] + (x_range / grid_size) * (j + 1)
            y_min = bounds[1] + (y_range / grid_size) * i
            y_max = bounds[1] + (y_range / grid_size) * (i + 1)

            # 해당 구역의 세그먼트 필터링
            zone_segments = short_segments_gdf.cx[x_min:x_max, y_min:y_max]

            if len(zone_segments) < 10:  # 세그먼트가 너무 적으면 스킵
                continue

            # 플롯 생성
            fig, ax = setup_plot_style(figsize=(10, 10))

            # 해당 구역의 전체 파이프
            zone_pipes = pipe_gdf.cx[x_min:x_max, y_min:y_max]
            zone_pipes.plot(ax=ax, color="lightblue", linewidth=1.0, alpha=0.3)

            # 짧은 세그먼트 강조
            zone_segments.plot(ax=ax, color="red", linewidth=3.0, alpha=0.8)

            # 경계 설정
            margin = min(x_range, y_range) * 0.02
            ax.set_xlim(x_min - margin, x_max + margin)
            ax.set_ylim(y_min - margin, y_max + margin)

            # 제목
            ax.set_title(
                f"PIPE_LM 1m 이하 세그먼트 - 구역 {zone_idx} ({len(zone_segments)}개)",
                fontsize=14,
                fontweight="bold",
            )
            ax.set_xlabel("경도", fontsize=10)
            ax.set_ylabel("위도", fontsize=10)
            ax.grid(True, alpha=0.3, linestyle="--")
            ax.set_aspect("equal")

            # 저장
            output_path = output_dir / f"pipe_lm_short_segments_zone_{zone_idx}.png"
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            print(f"  - 구역 {zone_idx} 저장: {output_path}")

            plt.close()


if __name__ == "__main__":
    visualize_short_pipe_segments()
