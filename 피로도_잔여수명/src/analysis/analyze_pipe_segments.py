"""
520 지역 파이프 shapefile의 LineString 세그먼트 분석
- LineString을 개별 선분으로 분리
- 1미터 단위 길이 통계 분석
- PIPE_LM과 SPLY_LS 별도 처리
"""

import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.semicircle_detection import find_semicircular_groups
from src.common.shapefile_loader import load_pipe_shapefile


def split_linestring_to_segments(geometry: Any) -> list[tuple[Point, Point, float]]:
    """
    LineString을 개별 선분으로 분리하고 각 선분의 길이 계산

    Args:
        geometry: LineString 또는 MultiLineString geometry

    Returns:
        [(시작점, 끝점, 길이)] 형태의 리스트
    """
    segments = []

    if geometry.geom_type == "LineString":
        coords = list(geometry.coords)
        for i in range(len(coords) - 1):
            start = Point(coords[i])
            end = Point(coords[i + 1])
            # 거리 계산 (미터 단위)
            segment_length = start.distance(end)
            segments.append((start, end, segment_length))

    elif geometry.geom_type == "MultiLineString":
        for line in geometry.geoms:
            segments.extend(split_linestring_to_segments(line))

    return segments


def analyze_pipe_segments(pipe_gdf: gpd.GeoDataFrame, pipe_type: str) -> pd.DataFrame:
    """
    파이프 GeoDataFrame의 모든 LineString을 세그먼트로 분리하고 분석

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)

    Returns:
        세그먼트 길이 통계 DataFrame
    """
    print(f"\n=== {pipe_type} 세그먼트 분석 시작 ===")
    print(f"전체 객체 수: {len(pipe_gdf)}")

    # 모든 세그먼트 수집 및 반원형 패턴 탐지
    all_segments = []
    semicircular_count = 0
    semicircular_segment_count = 0

    for idx, row in pipe_gdf.iterrows():
        if row.geometry is not None:
            segments = split_linestring_to_segments(row.geometry)
            all_segments.extend(segments)

            # 반원형 패턴 탐지
            coords = list(row.geometry.coords)
            semicircular_groups = find_semicircular_groups(coords)

            if len(semicircular_groups) > 0:
                semicircular_count += 1
                for group in semicircular_groups:
                    semicircular_segment_count += len(group)

    print(f"분리된 세그먼트 수: {len(all_segments)}")
    print(f"반원형 패턴이 있는 파이프: {semicircular_count}개")
    print(f"반원형 패턴에 속한 세그먼트: {semicircular_segment_count}개")

    # 세그먼트 길이 추출
    segment_lengths = [seg[2] for seg in all_segments]

    if not segment_lengths:
        print("경고: 세그먼트가 없습니다.")
        return pd.DataFrame()

    # 기본 통계
    lengths_array = np.array(segment_lengths)
    print("\n기본 통계:")
    print(f"  - 최소 길이: {lengths_array.min():.2f}m")
    print(f"  - 최대 길이: {lengths_array.max():.2f}m")
    print(f"  - 평균 길이: {lengths_array.mean():.2f}m")
    print(f"  - 중앙값: {np.median(lengths_array):.2f}m")
    print(f"  - 표준편차: {lengths_array.std():.2f}m")

    # 1m 미만 세그먼트 세분화 (10cm 단위)
    under_1m = lengths_array[lengths_array < 1]
    if len(under_1m) > 0:
        print(f"\n1m 미만 세그먼트 세부 분석 ({len(under_1m)}개):")

        # 10cm 단위 구간 생성
        cm_bins = np.arange(0, 1.1, 0.1)  # 0, 0.1, 0.2, ..., 1.0
        cm_hist, cm_edges = np.histogram(under_1m, bins=cm_bins)

        print("10cm 단위 분포:")
        for i in range(len(cm_hist)):
            if cm_hist[i] > 0:
                print(
                    f"  {int(cm_edges[i]*100)}-{int(cm_edges[i+1]*100)}cm: {cm_hist[i]}개 ({cm_hist[i]/len(under_1m)*100:.1f}%)"
                )

    # 1미터 단위 구간별 통계
    max_length = int(np.ceil(lengths_array.max()))
    bins = list(range(max_length + 2))  # 0-1, 1-2, ..., max-max+1

    # 히스토그램 생성
    hist, bin_edges = np.histogram(lengths_array, bins=bins)

    # 통계 DataFrame 생성 - 10cm 단위 추가
    stats_data = []
    total_segments = len(segment_lengths)
    cumulative_count = 0

    # 1m 미만은 10cm 단위로 세분화
    if len(under_1m) > 0:
        cm_bins = np.arange(0, 1.1, 0.1)
        cm_hist, cm_edges = np.histogram(under_1m, bins=cm_bins)

        for i in range(len(cm_hist)):
            if cm_hist[i] > 0:
                cumulative_count += cm_hist[i]
                stats_data.append(
                    {
                        "길이_구간": f"{cm_edges[i]:.1f}-{cm_edges[i+1]:.1f}m",
                        "시작(m)": cm_edges[i],
                        "끝(m)": cm_edges[i + 1],
                        "세그먼트_수": cm_hist[i],
                        "비율(%)": (cm_hist[i] / total_segments) * 100,
                        "누적_세그먼트_수": cumulative_count,
                        "누적_비율(%)": (cumulative_count / total_segments) * 100,
                    }
                )

    # 1m 이상은 1m 단위로
    for i in range(1, len(hist)):  # 1부터 시작 (0-1m는 이미 처리)
        bin_start = bin_edges[i]
        bin_end = bin_edges[i + 1]
        count = hist[i]
        cumulative_count += count

        if count > 0:  # 0개인 구간은 제외
            stats_data.append(
                {
                    "길이_구간": f"{int(bin_start)}-{int(bin_end)}m",
                    "시작(m)": bin_start,
                    "끝(m)": bin_end,
                    "세그먼트_수": count,
                    "비율(%)": (count / total_segments) * 100,
                    "누적_세그먼트_수": cumulative_count,
                    "누적_비율(%)": (cumulative_count / total_segments) * 100,
                }
            )

    stats_df = pd.DataFrame(stats_data)

    # 주요 구간 출력
    print("\n길이별 분포 (상위 30개 구간):")
    print(stats_df.head(30).to_string(index=False))

    # 요약 정보
    print("\n요약:")
    print(
        f"  - 1m 미만 세그먼트: {len([length for length in segment_lengths if length < 1])}개 ({len([length for length in segment_lengths if length < 1])/total_segments*100:.1f}%)"
    )
    print(
        f"  - 1-10m 세그먼트: {len([length for length in segment_lengths if 1 <= length < 10])}개 ({len([length for length in segment_lengths if 1 <= length < 10])/total_segments*100:.1f}%)"
    )
    print(
        f"  - 10m 이상 세그먼트: {len([length for length in segment_lengths if length >= 10])}개 ({len([length for length in segment_lengths if length >= 10])/total_segments*100:.1f}%)"
    )

    return stats_df


def main() -> None:
    """메인 실행 함수"""
    print("520 지역 파이프 세그먼트 분석 시작...")

    # 결과 저장 디렉토리 생성
    output_dir = RESULTS_DIR / "pipe_segment_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    # PIPE_LM 분석
    print("\n" + "=" * 60)
    print("PIPE_LM 데이터 로드 중...")
    pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "PIPE_LM")

    if pipe_lm_gdf is not None:
        pipe_lm_stats = analyze_pipe_segments(pipe_lm_gdf, "PIPE_LM")
        if not pipe_lm_stats.empty:
            output_path = output_dir / "pipe_lm_segment_statistics.csv"
            pipe_lm_stats.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"\nPIPE_LM 통계 저장: {output_path}")
    else:
        print("경고: PIPE_LM 데이터를 로드할 수 없습니다.")

    # SPLY_LS 분석
    print("\n" + "=" * 60)
    print("SPLY_LS 데이터 로드 중...")
    sply_ls_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "SPLY_LS")

    if sply_ls_gdf is not None:
        sply_ls_stats = analyze_pipe_segments(sply_ls_gdf, "SPLY_LS")
        if not sply_ls_stats.empty:
            output_path = output_dir / "sply_ls_segment_statistics.csv"
            sply_ls_stats.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"\nSPLY_LS 통계 저장: {output_path}")
    else:
        print("경고: SPLY_LS 데이터를 로드할 수 없습니다.")

    print("\n" + "=" * 60)
    print("분석 완료!")


if __name__ == "__main__":
    main()
