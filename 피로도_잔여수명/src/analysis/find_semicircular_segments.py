"""
1m 이하 PIPE_LM 세그먼트 중 반원형(아크) 구조 찾기
- 연속된 짧은 세그먼트가 곡선을 이루는 패턴 탐지
- 각도 변화를 분석하여 반원형 구조 식별
"""

import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import LineString

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font
from src.common.semicircle_detection import (
    MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE,
    is_semicircular_pattern,
)
from src.common.shapefile_loader import get_smlz_shapefile_path, load_pipe_shapefile
from src.common.visualization_utils import setup_plot_style

MIN_CONNECTED_SEGMENTS = 3  # 연결된 세그먼트 그룹으로 인정하는 최소 개수


def find_connected_short_segments(
    pipe_gdf: gpd.GeoDataFrame, max_length: float = MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE
) -> list[list[LineString]]:
    """
    연결된 짧은 세그먼트 그룹 찾기

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        max_length: 최대 세그먼트 길이

    Returns:
        연결된 세그먼트 그룹 리스트
    """
    # 모든 짧은 세그먼트 추출
    short_segments = []
    segment_to_pipe = {}  # 세그먼트가 속한 원본 파이프 추적

    for idx, row in pipe_gdf.iterrows():
        if row.geometry is not None and row.geometry.geom_type == "LineString":
            coords = list(row.geometry.coords)
            for i in range(len(coords) - 1):
                segment = LineString([coords[i], coords[i + 1]])
                if segment.length <= max_length:
                    short_segments.append(segment)
                    segment_to_pipe[len(short_segments) - 1] = idx

    # 연결된 세그먼트 그룹 찾기
    connected_groups = []
    used_segments = set()

    for i, seg1 in enumerate(short_segments):
        if i in used_segments:
            continue

        # 같은 파이프에서 연속된 세그먼트 찾기
        group = [seg1]
        used_segments.add(i)
        pipe_idx = segment_to_pipe[i]

        # 앞뒤로 연결된 세그먼트 찾기
        for j, seg2 in enumerate(short_segments):
            if j in used_segments or segment_to_pipe[j] != pipe_idx:
                continue

            # 연결 여부 확인
            if (
                seg1.coords[-1] == seg2.coords[0]
                or seg2.coords[-1] == seg1.coords[0]
                or any(
                    g.coords[-1] == seg2.coords[0] or g.coords[0] == seg2.coords[-1]
                    for g in group
                )
            ):
                group.append(seg2)
                used_segments.add(j)

        if len(group) >= MIN_CONNECTED_SEGMENTS:  # 최소 연결 세그먼트 수 이상
            connected_groups.append(group)

    return connected_groups


def visualize_semicircular_segments() -> None:
    """반원형 세그먼트 시각화"""
    print("1m 이하 반원형 세그먼트 분석 시작...")

    # 한글 폰트 설정
    setup_korean_font()

    # PIPE_LM 데이터 로드
    print("\nPIPE_LM 데이터 로드 중...")
    pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "PIPE_LM")

    if pipe_lm_gdf is None:
        print("오류: PIPE_LM 데이터를 로드할 수 없습니다.")
        return

    print(f"전체 PIPE_LM 객체: {len(pipe_lm_gdf)}개")

    # 연결된 짧은 세그먼트 그룹 찾기
    print("\n연결된 짧은 세그먼트 그룹 찾기...")
    connected_groups = find_connected_short_segments(pipe_lm_gdf)
    print(f"연결된 세그먼트 그룹: {len(connected_groups)}개")

    # 반원형 패턴 찾기
    print("\n반원형 패턴 분석 중...")
    semicircular_groups = []

    for group in connected_groups:
        is_semi, total_angle = is_semicircular_pattern(group)
        if is_semi:
            semicircular_groups.append(
                {
                    "segments": group,
                    "total_angle": total_angle,
                    "angle_degrees": np.degrees(abs(total_angle)),
                }
            )

    print(f"발견된 반원형 구조: {len(semicircular_groups)}개")

    # 반원형 세그먼트를 GeoDataFrame으로 변환
    all_semicircular_segments = []
    for group_info in semicircular_groups:
        all_semicircular_segments.extend(group_info["segments"])

    if not all_semicircular_segments:
        print("반원형 세그먼트를 찾을 수 없습니다.")
        return

    semicircular_gdf = gpd.GeoDataFrame(
        geometry=all_semicircular_segments, crs=pipe_lm_gdf.crs
    )

    # SMLZ 파일 경로
    smlz_file = get_smlz_shapefile_path(RAW_DATA_DIR, "0520")

    # 전체 시각화
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

    # 반원형 세그먼트를 붉은색으로 강조
    semicircular_gdf.plot(
        ax=ax,
        color="red",
        linewidth=3.0,
        alpha=0.8,
        label=f"반원형 세그먼트 ({len(semicircular_groups)}개 그룹)",
    )

    # 경계 설정
    bounds = pipe_lm_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05
    ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)

    # 제목 및 라벨
    ax.set_title(
        "PIPE_LM 반원형 세그먼트 분포 - 0520", fontsize=16, fontweight="bold", pad=20
    )
    ax.set_xlabel("경도", fontsize=12)
    ax.set_ylabel("위도", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 범례
    ax.legend(loc="upper right", fontsize=10)

    # 통계 정보 추가
    stats_text = f"전체 PIPE_LM: {len(pipe_lm_gdf)}개\n"
    stats_text += f"반원형 구조: {len(semicircular_groups)}개\n"
    stats_text += f"반원형 세그먼트: {len(all_semicircular_segments)}개"

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
    output_path = output_dir / "pipe_lm_semicircular_segments.png"

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    plt.close()

    # 개별 반원형 구조 상세 시각화
    create_detailed_views(pipe_lm_gdf, semicircular_groups, output_dir)


def create_detailed_views(
    pipe_gdf: gpd.GeoDataFrame,
    semicircular_groups: list[dict[str, Any]],
    output_dir: Path,
    max_views: int = 10,
) -> None:
    """주요 반원형 구조의 상세 뷰 생성"""
    print("\n반원형 구조 상세 뷰 생성 중...")

    # 각도가 큰 순으로 정렬
    semicircular_groups.sort(key=lambda x: x["angle_degrees"], reverse=True)

    for i, group_info in enumerate(semicircular_groups[:max_views], 1):
        segments = group_info["segments"]
        angle_deg = group_info["angle_degrees"]

        # 세그먼트들의 경계 계산
        all_coords = []
        for seg in segments:
            all_coords.extend(list(seg.coords))

        xs = [c[0] for c in all_coords]
        ys = [c[1] for c in all_coords]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # 여유 공간 추가
        x_range = max_x - min_x
        y_range = max_y - min_y
        margin = max(x_range, y_range) * 0.5

        # 플롯 생성
        fig, ax = setup_plot_style(figsize=(10, 10))

        # 해당 지역의 파이프
        area_pipes = pipe_gdf.cx[
            min_x - margin : max_x + margin, min_y - margin : max_y + margin
        ]
        if len(area_pipes) > 0:
            area_pipes.plot(ax=ax, color="lightblue", linewidth=1.5, alpha=0.4)

        # 반원형 세그먼트 강조
        for seg in segments:
            x, y = seg.xy
            ax.plot(x, y, color="red", linewidth=4.0, alpha=0.9)

        # 경계 설정
        ax.set_xlim(min_x - margin, max_x + margin)
        ax.set_ylim(min_y - margin, max_y + margin)

        # 제목
        ax.set_title(
            f"반원형 구조 #{i} (회전각: {angle_deg:.1f}°, {len(segments)}개 세그먼트)",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xlabel("경도", fontsize=10)
        ax.set_ylabel("위도", fontsize=10)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_aspect("equal")

        # 저장
        output_path = output_dir / f"pipe_lm_semicircular_{i:02d}.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"  - 반원형 구조 #{i} 저장: {angle_deg:.1f}° ({len(segments)}개)")

        plt.close()


if __name__ == "__main__":
    visualize_semicircular_segments()
