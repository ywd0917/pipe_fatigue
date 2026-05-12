"""
현재 발견된 모든 반원형 패턴 종합 시각화
- main15에서 처리된 반원형 패턴 (IS_SEMICIRCULAR=True)
- 일반 반원형 패턴 (6개 이상 세그먼트)
- 작은 반원형 패턴 (3-5개 세그먼트)
- 모든 반원형을 붉은색으로 강조 표시
"""

import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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
MIN_SEGMENTS_FOR_SMALL_SEMICIRCLE = 3
MAX_SEGMENTS_FOR_SMALL_SEMICIRCLE = 5
MAX_ANGLE_VARIATION_SMALL = 0.4
MIN_TOTAL_ANGLE_SMALL = np.pi / 4
MAX_TOTAL_ANGLE_SMALL = np.pi * 1.2
MIN_CONNECTED_SEGMENTS = 3


def is_small_semicircular_pattern(segments: list[LineString]) -> tuple[bool, float]:
    """작은 반원형 패턴 검사"""
    if (
        len(segments) < MIN_SEGMENTS_FOR_SMALL_SEMICIRCLE
        or len(segments) > MAX_SEGMENTS_FOR_SMALL_SEMICIRCLE
    ):
        return False, 0.0

    return is_semicircular_pattern(
        segments,
        min_segments=MIN_SEGMENTS_FOR_SMALL_SEMICIRCLE,
        max_angle_variation=MAX_ANGLE_VARIATION_SMALL,
        min_total_angle=MIN_TOTAL_ANGLE_SMALL,
        max_total_angle=MAX_TOTAL_ANGLE_SMALL,
    )


def extract_short_segments(
    geometry: Any, max_length: float = MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE
) -> list[LineString]:
    """짧은 세그먼트 추출"""
    short_segments = []

    if geometry.geom_type == "LineString":
        coords = list(geometry.coords)
        for i in range(len(coords) - 1):
            segment = LineString([coords[i], coords[i + 1]])
            if segment.length <= max_length:
                short_segments.append(segment)
    elif geometry.geom_type == "MultiLineString":
        for line in geometry.geoms:
            short_segments.extend(extract_short_segments(line, max_length))

    return short_segments


def find_connected_short_segments(
    pipe_gdf: gpd.GeoDataFrame, max_length: float = MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE
) -> list[list[LineString]]:
    """연결된 짧은 세그먼트 그룹 찾기"""
    short_segments = []
    segment_to_pipe = {}

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

        group = [seg1]
        used_segments.add(i)
        pipe_idx = segment_to_pipe[i]

        for j, seg2 in enumerate(short_segments):
            if j in used_segments or segment_to_pipe[j] != pipe_idx:
                continue

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

        if len(group) >= MIN_CONNECTED_SEGMENTS:
            connected_groups.append(group)

    return connected_groups


def load_merged_semicircles_from_joint_data() -> tuple[list[LineString], int]:
    """Joint 데이터에서 병합된 반원형 세그먼트 로드"""
    joint_csv = RESULTS_DIR / "PIPE_LM_JOINT.csv"
    joint_shp = RESULTS_DIR / "shapefiles" / "PIPE_LM_JOINT.shp"

    merged_segments = []
    merged_count = 0

    # CSV 우선 확인 (IS_SEMICIRCULAR 컬럼이 있음)
    if joint_csv.exists():
        print("Joint CSV에서 병합된 반원형 정보 확인 중...")
        joint_df = pd.read_csv(joint_csv, encoding="utf-8-sig")

        if "IS_SEMICIRCULAR" in joint_df.columns:
            merged_df = joint_df[joint_df["IS_SEMICIRCULAR"]]
            merged_count = (
                merged_df["ORIG_FTR_IDN"].nunique()
                if "ORIG_FTR_IDN" in merged_df.columns
                else len(merged_df)
            )
            print(
                f"병합된 반원형 파이프: {merged_count}개 (세그먼트 {len(merged_df)}개)"
            )

            # Shapefile에서 geometry 로드
            if joint_shp.exists():
                print("Joint shapefile에서 병합된 세그먼트 geometry 로드 중...")
                joint_gdf = gpd.read_file(joint_shp)

                # CSV의 IS_SEMICIRCULAR=True인 FTR_IDN과 매칭
                merged_ftr_idns = set(merged_df["FTR_IDN"].astype(str))
                merged_gdf = joint_gdf[joint_gdf["FTR_IDN"].isin(merged_ftr_idns)]
                merged_segments = list(merged_gdf.geometry)

                print(f"병합된 반원형 세그먼트 geometry: {len(merged_segments)}개")

    elif joint_shp.exists():
        print("Joint shapefile에서 세그먼트 정보 확인 중...")
        joint_gdf = gpd.read_file(joint_shp)
        print(
            "경고: Shapefile에 IS_SEMICIRCULAR 컬럼이 없어 병합된 반원형을 식별할 수 없습니다."
        )

    return merged_segments, merged_count


def analyze_all_semicircular_patterns(pipe_gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """모든 반원형 패턴 분석"""
    print("=== 모든 반원형 패턴 분석 시작 ===")

    results = {
        "merged_segments": [],
        "merged_count": 0,
        "regular_segments": [],
        "regular_count": 0,
        "small_segments": [],
        "small_count": 0,
        "total_segments": [],
        "total_pipes": 0,
    }

    # 1. Joint 데이터에서 병합된 반원형 로드
    merged_segments, merged_count = load_merged_semicircles_from_joint_data()
    results["merged_segments"] = merged_segments
    results["merged_count"] = merged_count

    # 2. 연결된 짧은 세그먼트 그룹 찾기
    print("\n연결된 짧은 세그먼트 그룹 찾기...")
    connected_groups = find_connected_short_segments(pipe_gdf)
    print(f"연결된 세그먼트 그룹: {len(connected_groups)}개")

    # 3. 일반 반원형 패턴 (6개 이상)
    print("\n일반 반원형 패턴 분석 중...")
    regular_semicircular_segments = []
    regular_count = 0

    for group in connected_groups:
        if len(group) >= 6:  # 6개 이상만 일반 반원형으로 검사
            is_semi, _ = is_semicircular_pattern(group)
            if is_semi:
                regular_semicircular_segments.extend(group)
                regular_count += 1

    results["regular_segments"] = regular_semicircular_segments
    results["regular_count"] = regular_count
    print(
        f"발견된 일반 반원형 구조: {regular_count}개 (세그먼트 {len(regular_semicircular_segments)}개)"
    )

    # 4. 작은 반원형 패턴 (3-5개)
    print("\n작은 반원형 패턴 분석 중...")
    small_semicircular_segments = []
    small_count = 0

    for group in connected_groups:
        if 3 <= len(group) <= 5:  # 3-5개만 작은 반원형으로 검사
            is_semi, _ = is_small_semicircular_pattern(group)
            if is_semi:
                small_semicircular_segments.extend(group)
                small_count += 1

    results["small_segments"] = small_semicircular_segments
    results["small_count"] = small_count
    print(
        f"발견된 작은 반원형 구조: {small_count}개 (세그먼트 {len(small_semicircular_segments)}개)"
    )

    # 5. 전체 통합
    all_segments = (
        merged_segments + regular_semicircular_segments + small_semicircular_segments
    )
    total_pipes = merged_count + regular_count + small_count

    results["total_segments"] = all_segments
    results["total_pipes"] = total_pipes

    print("\n=== 전체 반원형 패턴 요약 ===")
    print(
        f"- 병합된 반원형: {merged_count}개 파이프 ({len(merged_segments)}개 세그먼트)"
    )
    print(
        f"- 일반 반원형: {regular_count}개 구조 ({len(regular_semicircular_segments)}개 세그먼트)"
    )
    print(
        f"- 작은 반원형: {small_count}개 구조 ({len(small_semicircular_segments)}개 세그먼트)"
    )
    print(f"- 총 반원형: {total_pipes}개 구조 ({len(all_segments)}개 세그먼트)")

    return results


def create_comprehensive_visualization(
    pipe_gdf: gpd.GeoDataFrame, analysis_results: dict[str, Any], output_dir: Path
) -> None:
    """종합적인 반원형 패턴 시각화"""
    print("\n종합 시각화 생성 중...")

    # 한글 폰트 설정
    setup_korean_font()

    # SMLZ 파일 경로
    smlz_file = get_smlz_shapefile_path(RAW_DATA_DIR, "0520")

    # 전체 시각화
    fig, ax = setup_plot_style(figsize=(20, 16))

    # SMLZ 배경 (옵션)
    if smlz_file and smlz_file.exists():
        smlz_gdf = gpd.read_file(smlz_file)
        smlz_gdf.plot(
            ax=ax, facecolor="none", edgecolor="lightgray", linewidth=0.5, alpha=0.3
        )

    # 전체 파이프를 흐리게 표시
    pipe_gdf.plot(
        ax=ax, color="lightblue", linewidth=0.8, alpha=0.3, label="전체 PIPE_LM"
    )

    # 모든 반원형 세그먼트를 붉은색으로 강조
    if analysis_results["total_segments"]:
        all_semicircles_gdf = gpd.GeoDataFrame(
            geometry=analysis_results["total_segments"], crs=pipe_gdf.crs
        )

        all_semicircles_gdf.plot(
            ax=ax,
            color="red",
            linewidth=3.0,
            alpha=0.8,
            label=f'모든 반원형 패턴 ({analysis_results["total_pipes"]}개 구조)',
        )

    # 경계 설정
    bounds = pipe_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05
    ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)

    # 제목 및 라벨
    ax.set_title(
        "PIPE_LM 모든 반원형 패턴 종합 시각화 - 0520",
        fontsize=18,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("경도", fontsize=14)
    ax.set_ylabel("위도", fontsize=14)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 범례
    ax.legend(loc="upper right", fontsize=12)

    # 상세 통계 정보
    stats_text = f"전체 PIPE_LM: {len(pipe_gdf)}개\n"
    stats_text += f"총 반원형 구조: {analysis_results['total_pipes']}개\n"
    stats_text += f"총 반원형 세그먼트: {len(analysis_results['total_segments'])}개\n\n"
    stats_text += f"병합된 반원형: {analysis_results['merged_count']}개\n"
    stats_text += f"일반 반원형: {analysis_results['regular_count']}개\n"
    stats_text += f"작은 반원형: {analysis_results['small_count']}개"

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    # 저장
    output_path = output_dir / "all_semicircular_patterns_comprehensive.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"종합 시각화 저장: {output_path}")
    plt.close()


def create_detailed_breakdown_visualization(
    pipe_gdf: gpd.GeoDataFrame, analysis_results: dict[str, Any], output_dir: Path
) -> None:
    """유형별 상세 분해 시각화"""
    print("\n유형별 상세 시각화 생성 중...")

    # 3개 서브플롯 생성
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))

    # 공통 경계 설정
    bounds = pipe_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05

    # 1. 병합된 반원형
    ax1 = axes[0]
    pipe_gdf.plot(ax=ax1, color="lightblue", linewidth=0.5, alpha=0.3)

    if analysis_results["merged_segments"]:
        merged_gdf = gpd.GeoDataFrame(
            geometry=analysis_results["merged_segments"], crs=pipe_gdf.crs
        )
        merged_gdf.plot(ax=ax1, color="red", linewidth=2.5, alpha=0.8)

    ax1.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax1.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)
    ax1.set_title(
        f'병합된 반원형\n({analysis_results["merged_count"]}개 파이프)',
        fontsize=12,
        fontweight="bold",
    )
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)

    # 2. 일반 반원형 (6개 이상)
    ax2 = axes[1]
    pipe_gdf.plot(ax=ax2, color="lightblue", linewidth=0.5, alpha=0.3)

    if analysis_results["regular_segments"]:
        regular_gdf = gpd.GeoDataFrame(
            geometry=analysis_results["regular_segments"], crs=pipe_gdf.crs
        )
        regular_gdf.plot(ax=ax2, color="red", linewidth=2.5, alpha=0.8)

    ax2.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax2.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)
    ax2.set_title(
        f'일반 반원형 (6개 이상)\n({analysis_results["regular_count"]}개 구조)',
        fontsize=12,
        fontweight="bold",
    )
    ax2.set_aspect("equal")
    ax2.grid(True, alpha=0.3)

    # 3. 작은 반원형 (3-5개)
    ax3 = axes[2]
    pipe_gdf.plot(ax=ax3, color="lightblue", linewidth=0.5, alpha=0.3)

    if analysis_results["small_segments"]:
        small_gdf = gpd.GeoDataFrame(
            geometry=analysis_results["small_segments"], crs=pipe_gdf.crs
        )
        small_gdf.plot(ax=ax3, color="red", linewidth=2.5, alpha=0.8)

    ax3.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax3.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)
    ax3.set_title(
        f'작은 반원형 (3-5개)\n({analysis_results["small_count"]}개 구조)',
        fontsize=12,
        fontweight="bold",
    )
    ax3.set_aspect("equal")
    ax3.grid(True, alpha=0.3)

    # 전체 제목
    fig.suptitle(
        "PIPE_LM 반원형 패턴 유형별 분석 - 0520", fontsize=16, fontweight="bold"
    )

    # 저장
    output_path = output_dir / "semicircular_patterns_breakdown.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"유형별 시각화 저장: {output_path}")
    plt.close()


def main() -> None:
    """메인 실행 함수"""
    print("=== 모든 반원형 패턴 종합 시각화 시작 ===")

    # 출력 디렉토리 생성
    output_dir = RESULTS_DIR / "semicircular_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    # PIPE_LM 데이터 로드
    print("\nPIPE_LM 데이터 로드 중...")
    pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "PIPE_LM")

    if pipe_lm_gdf is None:
        print("오류: PIPE_LM 데이터를 로드할 수 없습니다.")
        return

    print(f"전체 PIPE_LM 객체: {len(pipe_lm_gdf)}개")

    # 모든 반원형 패턴 분석
    analysis_results = analyze_all_semicircular_patterns(pipe_lm_gdf)

    if len(analysis_results["total_segments"]) == 0:
        print("경고: 발견된 반원형 패턴이 없습니다.")
        return

    # 종합 시각화 생성
    create_comprehensive_visualization(pipe_lm_gdf, analysis_results, output_dir)

    # 유형별 상세 시각화 생성
    create_detailed_breakdown_visualization(pipe_lm_gdf, analysis_results, output_dir)

    # 결과 요약 저장
    summary_data = {
        "유형": ["병합된 반원형", "일반 반원형 (6개+)", "작은 반원형 (3-5개)", "전체"],
        "구조_수": [
            analysis_results["merged_count"],
            analysis_results["regular_count"],
            analysis_results["small_count"],
            analysis_results["total_pipes"],
        ],
        "세그먼트_수": [
            len(analysis_results["merged_segments"]),
            len(analysis_results["regular_segments"]),
            len(analysis_results["small_segments"]),
            len(analysis_results["total_segments"]),
        ],
    }

    summary_df = pd.DataFrame(summary_data)
    summary_path = output_dir / "semicircular_patterns_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"요약 데이터 저장: {summary_path}")

    print("\n=== 시각화 완료 ===")
    print(f"결과 저장 위치: {output_dir}")
    print(f"발견된 총 반원형 구조: {analysis_results['total_pipes']}개")
    print(f"발견된 총 반원형 세그먼트: {len(analysis_results['total_segments'])}개")


if __name__ == "__main__":
    main()
