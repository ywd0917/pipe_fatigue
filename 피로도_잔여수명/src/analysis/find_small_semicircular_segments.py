"""
1m 이하 PIPE_LM 세그먼트 중 작은 반원형(아크) 구조 찾기
- 5개 이하의 세그먼트로 이루어진 반원형 패턴 탐지
- 짧지만 명확한 곡선을 이루는 구조 식별
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

# 작은 반원형 패턴 탐지 상수들
MIN_SEGMENTS_FOR_SMALL_SEMICIRCLE = 3  # 작은 반원형으로 인정하는 최소 세그먼트 수
MAX_SEGMENTS_FOR_SMALL_SEMICIRCLE = 5  # 작은 반원형으로 인정하는 최대 세그먼트 수
MAX_ANGLE_VARIATION_SMALL = 0.4  # 작은 구조에서는 각도 변화 허용범위를 조금 더 넓게
MIN_TOTAL_ANGLE_SMALL = np.pi / 4  # 전체 회전 각도의 최소값 (45도)
MAX_TOTAL_ANGLE_SMALL = np.pi * 1.2  # 전체 회전 각도의 최대값 (216도)
MIN_CONNECTED_SEGMENTS = 3  # 연결된 세그먼트 그룹으로 인정하는 최소 개수


def is_small_semicircular_pattern(
    segments: list[LineString],
    min_segments: int = MIN_SEGMENTS_FOR_SMALL_SEMICIRCLE,
    max_segments: int = MAX_SEGMENTS_FOR_SMALL_SEMICIRCLE,
    max_angle_variation: float = MAX_ANGLE_VARIATION_SMALL,
    min_total_angle: float = MIN_TOTAL_ANGLE_SMALL,
    max_total_angle: float = MAX_TOTAL_ANGLE_SMALL,
) -> tuple[bool, float]:
    """
    연속된 세그먼트가 작은 반원형 패턴을 이루는지 확인

    Args:
        segments: 연속된 LineString 세그먼트 리스트
        min_segments: 최소 세그먼트 수 (기본값: 3개)
        max_segments: 최대 세그먼트 수 (기본값: 5개)
        max_angle_variation: 각 세그먼트 간 각도 변화의 최대 변동
        min_total_angle: 전체 회전 각도의 최소값 (45도)
        max_total_angle: 전체 회전 각도의 최대값 (216도)

    Returns:
        (반원형 여부, 전체 회전 각도)
    """
    # 세그먼트 수 제한 확인
    if len(segments) < min_segments or len(segments) > max_segments:
        return False, 0.0

    # 공통 모듈의 반원형 패턴 검사 사용
    return is_semicircular_pattern(
        segments,
        min_segments=min_segments,
        max_angle_variation=max_angle_variation,
        min_total_angle=min_total_angle,
        max_total_angle=max_total_angle,
    )


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


def visualize_small_semicircular_segments() -> None:
    """작은 반원형 세그먼트 시각화"""
    print("1m 이하 작은 반원형 세그먼트 분석 시작...")

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

    # 작은 반원형 패턴 찾기
    print("\n작은 반원형 패턴 분석 중...")
    small_semicircular_groups: list[dict[str, Any]] = []

    for group in connected_groups:
        is_semi, total_angle = is_small_semicircular_pattern(group)
        if is_semi:
            small_semicircular_groups.append(
                {
                    "segments": group,
                    "total_angle": total_angle,
                    "angle_degrees": np.degrees(abs(total_angle)),
                    "segment_count": len(group),
                }
            )

    print(f"발견된 작은 반원형 구조: {len(small_semicircular_groups)}개")

    # 세그먼트 수별 통계
    segment_counts: dict[int, int] = {}
    for group in small_semicircular_groups:  # type: ignore[assignment]
        count = group["segment_count"]  # type: ignore[call-overload]
        if count not in segment_counts:
            segment_counts[count] = 0
        segment_counts[count] += 1

    print("세그먼트 수별 분포:")
    for count in sorted(segment_counts.keys()):
        print(f"  - {count}개 세그먼트: {segment_counts[count]}개 구조")

    # 작은 반원형 세그먼트를 GeoDataFrame으로 변환
    all_small_semicircular_segments = []
    for group_info in small_semicircular_groups:
        all_small_semicircular_segments.extend(group_info["segments"])

    if not all_small_semicircular_segments:
        print("작은 반원형 세그먼트를 찾을 수 없습니다.")
        return

    small_semicircular_gdf = gpd.GeoDataFrame(
        geometry=all_small_semicircular_segments, crs=pipe_lm_gdf.crs
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

    # 작은 반원형 세그먼트를 붉은색으로 강조
    small_semicircular_gdf.plot(
        ax=ax,
        color="red",
        linewidth=3.0,
        alpha=0.8,
        label=f"작은 반원형 세그먼트 ({len(small_semicircular_groups)}개 그룹)",
    )

    # 경계 설정
    bounds = pipe_lm_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05
    ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)

    # 제목 및 라벨
    ax.set_title(
        "PIPE_LM 작은 반원형 세그먼트 분포 (3-5개) - 0520",
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

    # 통계 정보 추가
    stats_text = f"전체 PIPE_LM: {len(pipe_lm_gdf)}개\n"
    stats_text += f"작은 반원형 구조: {len(small_semicircular_groups)}개\n"
    stats_text += f"작은 반원형 세그먼트: {len(all_small_semicircular_segments)}개\n"
    for count in sorted(segment_counts.keys()):
        stats_text += f"{count}개 세그먼트: {segment_counts[count]}개\n"

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
    output_path = output_dir / "pipe_lm_small_semicircular_segments.png"

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")

    plt.close()

    # 개별 작은 반원형 구조 상세 시각화
    create_detailed_views(pipe_lm_gdf, small_semicircular_groups, output_dir)


def create_detailed_views(
    pipe_gdf: gpd.GeoDataFrame,
    small_semicircular_groups: list[dict[str, Any]],
    output_dir: Path,
    max_views: int = 15,
) -> None:
    """주요 작은 반원형 구조의 상세 뷰 생성"""
    print("\n작은 반원형 구조 상세 뷰 생성 중...")

    # 각도가 큰 순으로 정렬
    small_semicircular_groups.sort(key=lambda x: x["angle_degrees"], reverse=True)

    for i, group_info in enumerate(small_semicircular_groups[:max_views], 1):
        segments = group_info["segments"]
        angle_deg = group_info["angle_degrees"]
        segment_count = group_info["segment_count"]

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
        margin = max(x_range, y_range) * 0.8  # 작은 구조이므로 더 많은 여유 공간

        # 플롯 생성
        fig, ax = setup_plot_style(figsize=(8, 8))

        # 해당 지역의 파이프
        area_pipes = pipe_gdf.cx[
            min_x - margin : max_x + margin, min_y - margin : max_y + margin
        ]
        if len(area_pipes) > 0:
            area_pipes.plot(ax=ax, color="lightblue", linewidth=2.0, alpha=0.4)

        # 작은 반원형 세그먼트 강조
        for seg in segments:
            x, y = seg.xy
            ax.plot(x, y, color="red", linewidth=5.0, alpha=0.9)

        # 경계 설정
        ax.set_xlim(min_x - margin, max_x + margin)
        ax.set_ylim(min_y - margin, max_y + margin)

        # 제목
        ax.set_title(
            f"작은 반원형 구조 #{i} (회전각: {angle_deg:.1f}°, {segment_count}개 세그먼트)",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("경도", fontsize=10)
        ax.set_ylabel("위도", fontsize=10)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_aspect("equal")

        # 저장
        output_path = output_dir / f"pipe_lm_small_semicircular_{i:02d}.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"  - 작은 반원형 구조 #{i} 저장: {angle_deg:.1f}° ({segment_count}개)")

        plt.close()


if __name__ == "__main__":
    visualize_small_semicircular_segments()
