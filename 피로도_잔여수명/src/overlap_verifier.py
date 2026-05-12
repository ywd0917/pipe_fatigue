"""
중첩 검증을 위한 특화 모듈
파이프-도로 중첩 샘플링 및 시각화 비즈니스 로직
"""

import random
import warnings

import geopandas as gpd
import matplotlib
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 시각화 설정
FIGURE_SIZE = (16, 12)  # 이미지 크기
DPI = 300  # 해상도
SAMPLE_SIZE = 20  # 지역별 샘플 수
BUFFER_RADIUS = 100  # 표시할 주변 영역 반경 (미터)

# 색상 설정
COLOR_MATCHED_PIPE = "#FF0000"  # 매칭된 파이프 (빨간색)
COLOR_UNMATCHED_PIPE = "#0000FF"  # 매칭 안된 파이프 (파란색)
COLOR_MATCHED_ROAD = "#FF7F00"  # 매칭된 도로 (주황색)
COLOR_OTHER_ROAD = "#808080"  # 기타 도로 (회색)
COLOR_BUFFER = "#FFE4B5"  # 버퍼 영역 (연한 주황색)

# 선 두께
PIPE_WIDTH = 2.0
ROAD_WIDTH_MATCHED = 1.5
ROAD_WIDTH_OTHER = 0.5

# 투명도
ALPHA_BUFFER = 0.3
ALPHA_ROAD = 0.8
ALPHA_PIPE = 1.0

# 폰트 크기
TITLE_FONT_SIZE = 14
LABEL_FONT_SIZE = 10
TEXT_FONT_SIZE = 8


def select_sample_pipes(
    pipe_gdf: gpd.GeoDataFrame, traffic_df: pd.DataFrame, sample_size: int = SAMPLE_SIZE
) -> tuple[list[int], dict[int, str | None]]:
    """검증할 파이프 샘플을 선택

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        traffic_df: 교통 분석 결과 DataFrame
        sample_size: 샘플 크기

    Returns:
        (샘플 FTR_IDN 리스트, FTR_IDN별 매칭 도로 코드 딕셔너리)
    """
    # 매칭된 파이프와 안된 파이프 구분
    matched_pipes = traffic_df[traffic_df["RN_CD"].notna()]["FTR_IDN"].tolist()
    unmatched_pipes = traffic_df[traffic_df["RN_CD"].isna()]["FTR_IDN"].tolist()

    # 각각에서 절반씩 샘플링하되, 한쪽이 부족하면 다른 쪽에서 더 선택
    n_matched = min(len(matched_pipes), sample_size // 2)
    n_unmatched = min(len(unmatched_pipes), sample_size - n_matched)

    # 전체 샘플 수가 부족하면 가능한 쪽에서 더 선택
    if n_matched + n_unmatched < sample_size:
        if len(matched_pipes) > n_matched:
            n_matched = min(len(matched_pipes), sample_size - n_unmatched)
        elif len(unmatched_pipes) > n_unmatched:
            n_unmatched = min(len(unmatched_pipes), sample_size - n_matched)

    sampled_matched = random.sample(matched_pipes, n_matched) if matched_pipes else []
    sampled_unmatched = (
        random.sample(unmatched_pipes, n_unmatched) if unmatched_pipes else []
    )

    # 전체 샘플 리스트
    sample_ids = sampled_matched + sampled_unmatched

    # 매칭 정보 딕셔너리 생성
    matching_info = {}
    for _, row in traffic_df.iterrows():
        ftr_idn = row["FTR_IDN"]
        if ftr_idn in sample_ids:
            rn_cd = row["RN_CD"]
            matching_info[ftr_idn] = rn_cd if pd.notna(rn_cd) else None

    print(
        f"샘플 선택: 매칭 {len(sampled_matched)}개, 미매칭 {len(sampled_unmatched)}개"
    )

    return sample_ids, matching_info


def visualize_pipe_sample(
    pipe_gdf: gpd.GeoDataFrame,
    road_gdf: gpd.GeoDataFrame,
    sample_id: int,
    matched_road_code: str | None,
    ax: matplotlib.axes.Axes,
    title: str,
) -> None:
    """하나의 파이프 샘플과 주변 도로를 시각화

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        road_gdf: 도로 GeoDataFrame
        sample_id: 파이프 FTR_IDN
        matched_road_code: 매칭된 도로 코드 (없으면 None)
        ax: matplotlib axes
        title: 서브플롯 제목
    """
    # 해당 파이프 찾기
    pipe = pipe_gdf[pipe_gdf["FTR_IDN"] == sample_id]
    if pipe.empty:
        ax.text(
            0.5,
            0.5,
            f"파이프 {sample_id} 없음",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title(title)
        return

    # 파이프 중심점과 경계 구하기
    pipe_geom = pipe.geometry.iloc[0]
    pipe_bounds = pipe_geom.bounds
    center_x = (pipe_bounds[0] + pipe_bounds[2]) / 2
    center_y = (pipe_bounds[1] + pipe_bounds[3]) / 2

    # 표시 영역 설정
    xlim = (center_x - BUFFER_RADIUS, center_x + BUFFER_RADIUS)
    ylim = (center_y - BUFFER_RADIUS, center_y + BUFFER_RADIUS)

    # 주변 도로 찾기
    nearby_roads = road_gdf.cx[xlim[0] : xlim[1], ylim[0] : ylim[1]]

    # 도로 그리기
    if not nearby_roads.empty:
        # 매칭된 도로와 기타 도로 구분
        if matched_road_code:
            matched_roads = nearby_roads[nearby_roads["RN_CD"] == matched_road_code]
            other_roads = nearby_roads[nearby_roads["RN_CD"] != matched_road_code]

            # 기타 도로 먼저 그리기
            if not other_roads.empty:
                other_roads.plot(
                    ax=ax,
                    color=COLOR_OTHER_ROAD,
                    linewidth=ROAD_WIDTH_OTHER,
                    alpha=ALPHA_ROAD,
                )

            # 매칭된 도로 강조
            if not matched_roads.empty:
                matched_roads.plot(
                    ax=ax,
                    color=COLOR_MATCHED_ROAD,
                    linewidth=ROAD_WIDTH_MATCHED,
                    alpha=ALPHA_ROAD,
                )

                # 버퍼 영역 표시
                road_bt = matched_roads.iloc[0]["ROAD_BT"]
                buffer_dist = road_bt * 0.5  # main7에서 사용한 비율
                buffer_dist = max(3.0, min(20.0, buffer_dist))  # 3-20m 제한

                buffered = matched_roads.geometry.iloc[0].buffer(buffer_dist)
                gpd.GeoSeries([buffered]).plot(
                    ax=ax, color=COLOR_BUFFER, alpha=ALPHA_BUFFER
                )
        else:
            # 매칭 안된 경우 모든 도로를 기본 색상으로
            nearby_roads.plot(
                ax=ax,
                color=COLOR_OTHER_ROAD,
                linewidth=ROAD_WIDTH_OTHER,
                alpha=ALPHA_ROAD,
            )

    # 파이프 그리기
    color = COLOR_MATCHED_PIPE if matched_road_code else COLOR_UNMATCHED_PIPE
    pipe.plot(ax=ax, color=color, linewidth=PIPE_WIDTH, alpha=ALPHA_PIPE)

    # 축 설정
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect("equal")

    # 제목과 정보 표시
    ax.set_title(title, fontsize=TITLE_FONT_SIZE)

    # 매칭 정보 텍스트
    info_text = f"FTR_IDN: {sample_id}"
    if matched_road_code:
        matched_road = road_gdf[road_gdf["RN_CD"] == matched_road_code]
        if not matched_road.empty:
            road_name = matched_road.iloc[0]["RN"]
            road_width = matched_road.iloc[0]["ROAD_BT"]
            info_text += f"\n도로: {road_name}\n폭: {road_width}m"
    else:
        info_text += "\n매칭 없음"

    ax.text(
        0.02,
        0.98,
        info_text,
        transform=ax.transAxes,
        fontsize=TEXT_FONT_SIZE,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
    )

    # 격자 추가
    ax.grid(True, alpha=0.3)


def create_legend_elements() -> list[Line2D | Rectangle]:
    """범례 요소 생성

    Returns:
        범례 요소 리스트
    """
    return [
        Line2D([0], [0], color=COLOR_MATCHED_PIPE, linewidth=2, label="매칭된 파이프"),
        Line2D(
            [0], [0], color=COLOR_UNMATCHED_PIPE, linewidth=2, label="매칭 안된 파이프"
        ),
        Line2D([0], [0], color=COLOR_MATCHED_ROAD, linewidth=2, label="매칭된 도로"),
        Line2D([0], [0], color=COLOR_OTHER_ROAD, linewidth=1, label="기타 도로"),
        Rectangle(
            (0, 0), 1, 1, facecolor=COLOR_BUFFER, alpha=ALPHA_BUFFER, label="도로 버퍼"
        ),
    ]


def calculate_verification_stats(
    pipe_gdf: gpd.GeoDataFrame, traffic_df: pd.DataFrame, sample_ids: list[int]
) -> dict[str, float]:
    """검증 통계 계산

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        traffic_df: 교통 분석 결과 DataFrame
        sample_ids: 샘플 ID 리스트

    Returns:
        통계 정보 딕셔너리
    """
    matched_count = traffic_df["RN_CD"].notna().sum()
    total_analyzed = len(traffic_df)

    return {
        "total_pipes": len(pipe_gdf),
        "analyzed_pipes": total_analyzed,
        "matched_pipes": matched_count,
        "match_rate": matched_count / total_analyzed * 100 if total_analyzed > 0 else 0,
        "sample_count": len(sample_ids),
    }
