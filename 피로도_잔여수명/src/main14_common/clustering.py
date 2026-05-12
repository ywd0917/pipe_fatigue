"""
재작업 위치 클러스터링 및 파이프 매칭 공통 함수
"""

import time
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.strtree import STRtree

from .constants import FACTOR_NAMES


def create_repair_clusters(
    gdf_repairs: gpd.GeoDataFrame,
    cluster_distance: float = 10.0,
    min_repairs_for_frequent: int = 4,
) -> gpd.GeoDataFrame:
    """
    재작업 위치 클러스터링 (EPSG:5179 기준)

    Parameters:
    -----------
    gdf_repairs : gpd.GeoDataFrame
        재작업 위치 데이터 (EPSG:5179 좌표계)
    cluster_distance : float
        클러스터링 거리 임계값 (미터 단위, 기본값: 10m)
    min_repairs_for_frequent : int
        빈번한 재작업 판단 기준 (기본값: 4)

    Returns:
    --------
    gpd.GeoDataFrame : 클러스터 정보
    """
    print("\n=== 재작업 위치 클러스터링 중 ===")

    # 인덱스를 리셋하여 정수 인덱스 보장
    gdf_repairs = gdf_repairs.reset_index(drop=True)

    # EPSG:5179 확인
    if gdf_repairs.crs != "EPSG:5179":
        gdf_repairs = gdf_repairs.to_crs("EPSG:5179")

    clusters = []
    visited = set()

    for i, row1 in gdf_repairs.iterrows():
        if i in visited:
            continue

        cluster = [i]
        visited.add(i)

        for j, row2 in gdf_repairs.iterrows():
            if j <= i or j in visited:
                continue

            # EPSG:5179에서 직접 유클리드 거리 계산 (미터 단위)
            dist = row1.geometry.distance(row2.geometry)

            if dist <= cluster_distance:
                cluster.append(j)
                visited.add(j)

        clusters.append(cluster)

    # 클러스터 정보 생성
    cluster_data = []
    for cluster_id, indices in enumerate(clusters):
        cluster_df = gdf_repairs.iloc[indices]

        # 클러스터 중심점 계산 (EPSG:5179)
        cluster_center = cluster_df.geometry.union_all().centroid

        # WGS84로 변환해서 위도/경도 저장 (표시용)
        center_wgs84 = gpd.GeoSeries([cluster_center], crs="EPSG:5179").to_crs(
            "EPSG:4326"
        )[0]

        cluster_data.append(
            {
                "cluster_id": cluster_id,
                "repair_count": len(indices),
                "avg_lat": center_wgs84.y,
                "avg_lon": center_wgs84.x,
                "geometry": cluster_center,  # EPSG:5179 좌표 유지
                "repair_types": (
                    cluster_df["작업타입"].value_counts().to_dict()
                    if "작업타입" in cluster_df.columns
                    else {}
                ),
            }
        )

    # 빈 데이터 처리
    if not cluster_data:
        return gpd.GeoDataFrame(
            columns=[
                "cluster_id",
                "repair_count",
                "avg_lat",
                "avg_lon",
                "geometry",
                "repair_types",
            ],
            crs="EPSG:5179",
        )

    gdf_clusters = gpd.GeoDataFrame(cluster_data, crs="EPSG:5179")

    print(f"생성된 클러스터: {len(gdf_clusters)}개")
    if len(gdf_clusters) > 0:
        frequent_clusters = len(
            gdf_clusters[gdf_clusters["repair_count"] >= min_repairs_for_frequent]
        )
        print(
            f"{min_repairs_for_frequent}회 이상 재작업 클러스터: {frequent_clusters}개"
        )

    return gdf_clusters


def match_clusters_to_pipes(
    gdf_clusters: gpd.GeoDataFrame,
    gdf_pipes: gpd.GeoDataFrame,
    distance_threshold: float,
    analysis_factors: list[str],
) -> pd.DataFrame:
    """
    클러스터와 파이프 매칭 - 파이프 LineString에 대한 최단거리 계산

    Parameters:
    -----------
    gdf_clusters : gpd.GeoDataFrame
        클러스터 데이터
    gdf_pipes : gpd.GeoDataFrame
        파이프 세그먼트 데이터
    distance_threshold : float
        매칭 거리 임계값 (미터 단위)
    analysis_factors : list[str]
        분석할 위험 요인 리스트

    Returns:
    --------
    pd.DataFrame : 매칭된 클러스터-파이프 데이터
    """
    print("\n=== 클러스터-파이프 매칭 중 (최단거리 방식) ===")
    print(f"클러스터 수: {len(gdf_clusters)}, 파이프 세그먼트 수: {len(gdf_pipes)}")
    print(f"매칭 거리 임계값: {distance_threshold}m")

    # 빈 데이터 처리
    if len(gdf_clusters) == 0 or len(gdf_pipes) == 0:
        return pd.DataFrame()

    start_time = time.time()

    # 파이프도 EPSG:5179로 통일 (이미 5179일 수 있음)
    if gdf_pipes.crs != "EPSG:5179":
        gdf_pipes = gdf_pipes.to_crs("EPSG:5179")

    # 클러스터도 EPSG:5179 확인
    if gdf_clusters.crs != "EPSG:5179":
        gdf_clusters = gdf_clusters.to_crs("EPSG:5179")

    matched_data = []
    total_clusters = len(gdf_clusters)

    # STRtree를 사용한 공간 인덱싱으로 사전 필터링 (성능 최적화)
    pipe_tree = STRtree(gdf_pipes.geometry.tolist())

    for cluster_idx, cluster in gdf_clusters.iterrows():
        if cluster_idx % 50 == 0:
            print(
                f"  처리 중: {cluster_idx}/{total_clusters} ({cluster_idx/total_clusters*100:.1f}%)"
            )

        cluster_point = cluster.geometry

        # 거리 임계값보다 넓은 버퍼로 후보 파이프 먼저 필터링
        buffer = cluster_point.buffer(distance_threshold * 1.5)
        candidate_indices = pipe_tree.query(buffer)

        # 실제 거리 계산
        pipes_within_range = []
        for pipe_idx in candidate_indices:
            pipe = gdf_pipes.iloc[pipe_idx]
            # Shapely의 distance 메서드 - LineString의 최단거리 자동 계산
            distance = pipe.geometry.distance(cluster_point)

            if distance <= distance_threshold:
                pipe_data = {
                    "pipe_idx": pipe_idx,
                    "distance": distance,
                    "FTR_IDN": pipe.get("FTR_IDN", ""),
                    "pipe_type": pipe.get("pipe_type", ""),
                }

                # 분석 요인 추가
                for factor in analysis_factors:
                    if factor in pipe:
                        pipe_data[factor] = pipe[factor]
                    else:
                        pipe_data[factor] = 0.0  # 기본값

                pipes_within_range.append(pipe_data)

        if pipes_within_range:
            # 거리순 정렬
            pipes_within_range.sort(key=lambda x: x["distance"])

            # 가장 가까운 파이프
            nearest_pipe = pipes_within_range[0]

            result = {
                "cluster_id": cluster["cluster_id"],
                "repair_count": cluster["repair_count"],
                "avg_lat": cluster.get("avg_lat", 0),
                "avg_lon": cluster.get("avg_lon", 0),
                "nearest_pipe": nearest_pipe["FTR_IDN"],
                "nearest_type": nearest_pipe["pipe_type"],
                "nearest_dist": nearest_pipe["distance"],
                "pipe_count": len(pipes_within_range),
            }

            # 각 분석 요인에 대해 nearest, max, avg 계산
            for factor in analysis_factors:
                # 가장 가까운 파이프의 값
                result[f"nearest_{factor}"] = nearest_pipe.get(factor, 0)

                # 최대값
                result[f"max_{factor}"] = max(
                    p.get(factor, 0) for p in pipes_within_range
                )

                # 거리 가중 평균
                total_weight = 0
                weighted_sum = 0
                for p in pipes_within_range:
                    weight = 1 / (p["distance"] + 1)  # 거리가 0일 때를 위해 1 추가
                    weighted_sum += weight * p.get(factor, 0)
                    total_weight += weight
                result[f"avg_{factor}"] = (
                    weighted_sum / total_weight if total_weight > 0 else 0
                )

            matched_data.append(result)

    df_matched = pd.DataFrame(matched_data)

    elapsed = time.time() - start_time
    print(f"\n매칭 완료: {elapsed:.2f}초")
    print(f"매칭된 클러스터: {len(df_matched)}개 / {len(gdf_clusters)}개")

    if len(df_matched) > 0:
        print(f"매칭률: {len(df_matched) / len(gdf_clusters) * 100:.1f}%")

    return df_matched


def calculate_matching_statistics(
    df_matched: pd.DataFrame, gdf_clusters: gpd.GeoDataFrame
) -> dict[str, Any]:
    """
    매칭 통계 계산

    Parameters:
    -----------
    df_matched : pd.DataFrame
        매칭된 데이터
    gdf_clusters : gpd.GeoDataFrame
        전체 클러스터 데이터

    Returns:
    --------
    dict : 매칭 통계
    """
    total_clusters = len(gdf_clusters)
    matched_clusters = len(df_matched)

    stats = {
        "total_clusters": total_clusters,
        "matched_clusters": matched_clusters,
        "unmatched_clusters": total_clusters - matched_clusters,
        "matching_rate": (
            (matched_clusters / total_clusters * 100) if total_clusters > 0 else 0
        ),
    }

    if len(df_matched) > 0:
        stats.update(
            {
                "avg_nearest_distance": df_matched["nearest_dist"].mean(),
                "max_nearest_distance": df_matched["nearest_dist"].max(),
                "min_nearest_distance": df_matched["nearest_dist"].min(),
                "avg_pipe_count": df_matched["pipe_count"].mean(),
            }
        )

    return stats
