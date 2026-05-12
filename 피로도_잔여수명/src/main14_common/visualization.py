"""
재작업 시각화 관련 공통 함수 모듈

main14 시리즈 스크립트에서 사용하는 시각화 함수들을 제공합니다.
"""

from typing import Any, Dict, List, Tuple, Callable
import pandas as pd
import matplotlib.patches as mpatches
from src.common.config import REPAIR_COLORS


def plot_individual_repairs_with_clusters(
    ax: Any,
    repair_data: Dict[str, pd.DataFrame],
    convert_wgs84_to_geodataframe: Callable,
    cluster_repair_points: Callable,
) -> Tuple[List[Any], int]:
    """개별 재작업 점 표시 + 클러스터 숫자 오버레이

    Args:
        ax: matplotlib axes
        repair_data: 재작업 타입별 DataFrame 딕셔너리
        convert_wgs84_to_geodataframe: WGS84 좌표 변환 함수
        cluster_repair_points: 클러스터링 함수

    Returns:
        (범례 요소 리스트, 전체 클러스터 개수)
    """
    legend_elements = []
    all_repairs = []

    # 1. 개별 재작업 점 표시 (타입별로)
    for repair_type, repair_df in repair_data.items():
        if (
            repair_df is not None
            and len(repair_df) > 0
            and repair_type in REPAIR_COLORS
        ):
            # WGS84 좌표를 GeoDataFrame으로 변환
            gdf = convert_wgs84_to_geodataframe(repair_df)
            if len(gdf) == 0:
                continue

            color, label = REPAIR_COLORS[repair_type]

            # 개별 점 표시
            ax.scatter(
                gdf.geometry.x,
                gdf.geometry.y,
                c=color,
                s=20,  # 작은 크기
                alpha=0.6,
                edgecolor="black",
                linewidth=0.5,
                zorder=5,
                label=f"{label} ({len(gdf)}개)",
            )

            # 범례 요소 추가
            legend_elements.append(
                mpatches.Circle((0, 0), 1, color=color, label=f"{label} ({len(gdf)}개)")
            )

            all_repairs.append(repair_df)

    # 2. 전체 데이터로 클러스터링 및 숫자 표시
    if all_repairs:
        # 모든 복구 데이터 합치기
        combined_repairs = pd.concat(all_repairs, ignore_index=True)
        combined_gdf = convert_wgs84_to_geodataframe(combined_repairs)

        # 클러스터링 수행
        clusters_df = cluster_repair_points(combined_gdf, cluster_distance=10.0)

        # 2개 이상 클러스터에 숫자 표시
        multi_clusters = 0
        for _, cluster in clusters_df.iterrows():
            repair_count = cluster["repair_count"]

            if repair_count >= 2:
                multi_clusters += 1

                # 배경 색상 결정
                if repair_count <= 3:
                    bg_color = "yellow"
                    text_color = "black"
                elif repair_count <= 5:
                    bg_color = "orange"
                    text_color = "black"
                else:
                    bg_color = "red"
                    text_color = "white"

                # 숫자 표시
                ax.text(
                    cluster["x"],
                    cluster["y"],
                    str(int(repair_count)),
                    fontsize=8,
                    fontweight="bold",
                    color=text_color,
                    ha="center",
                    va="center",
                    bbox=dict(
                        boxstyle="round,pad=0.1",  # 둥근 사각형, 최소 패딩
                        facecolor=bg_color,
                        edgecolor="black",
                        linewidth=1,
                        alpha=0.8,
                    ),
                    zorder=10,
                )

        # 클러스터 정보를 범례에 추가
        legend_elements.append(
            mpatches.Patch(color="none", label=f"2개 이상 클러스터: {multi_clusters}개")
        )

        print(f"\n전체 재작업: {len(combined_repairs)}개")
        print(f"클러스터링 결과: {len(clusters_df)}개 클러스터")
        print(f"2개 이상 클러스터: {multi_clusters}개")

        return legend_elements, len(clusters_df)

    return legend_elements, 0
