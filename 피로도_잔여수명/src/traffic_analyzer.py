"""
교통량 분석을 위한 특화 모듈
파이프-도로 중첩 분석 및 교통 정보 생성 비즈니스 로직
"""

import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 버퍼 설정
ROAD_BUFFER_RATIO = 0.5  # 도로 폭의 절반을 버퍼로 사용
MIN_BUFFER_DISTANCE = 3.0  # 최소 버퍼 거리 (미터) - GPS 오차 고려
MAX_BUFFER_DISTANCE = 20.0  # 최대 버퍼 거리 (미터) - 95% 도로 커버

# 공간 조인 설정
SPATIAL_PREDICATE = "intersects"  # 공간 조인 방법
BUFFER_CAP_STYLE = "round"  # 버퍼 끝부분 스타일

# 출력 설정
OUTPUT_ENCODING = "utf-8-sig"  # CSV 출력 인코딩 (한글 지원)


def calculate_buffer_distance(road_width: float) -> float:
    """도로 폭을 기반으로 버퍼 거리를 계산

    Args:
        road_width: 도로 폭 (미터)

    Returns:
        버퍼 거리 (미터)
    """
    buffer_dist = road_width * ROAD_BUFFER_RATIO
    buffer_dist = max(MIN_BUFFER_DISTANCE, buffer_dist)
    return min(MAX_BUFFER_DISTANCE, buffer_dist)


def create_road_buffers(
    road_gdf: gpd.GeoDataFrame, verbose: bool = True
) -> gpd.GeoDataFrame:
    """도로에 버퍼를 생성

    Args:
        road_gdf: 도로 GeoDataFrame
        verbose: 상세 정보 출력 여부

    Returns:
        버퍼가 추가된 도로 GeoDataFrame
    """
    # 빈 GeoDataFrame 또는 필수 컬럼이 없는 경우 처리
    if len(road_gdf) == 0 or "ROAD_BT" not in road_gdf.columns:
        return road_gdf

    if verbose:
        print("\n도로 버퍼 생성 중...")

    # 버퍼 거리 계산
    road_gdf = road_gdf.copy()
    road_gdf["buffer_dist"] = road_gdf["ROAD_BT"].apply(calculate_buffer_distance)

    # 버퍼 생성
    road_gdf["buffered_geometry"] = road_gdf.apply(
        lambda row: row.geometry.buffer(row["buffer_dist"], cap_style=BUFFER_CAP_STYLE),
        axis=1,
    )

    # 버퍼된 geometry를 사용하는 새 GeoDataFrame 생성
    buffered_gdf = road_gdf.copy()
    buffered_gdf.set_geometry("buffered_geometry", inplace=True)

    if verbose:
        print("버퍼 생성 완료")
        print(f"  - 평균 버퍼 거리: {road_gdf['buffer_dist'].mean():.1f}m")
        print(f"  - 최소 버퍼 거리: {road_gdf['buffer_dist'].min():.1f}m")
        print(f"  - 최대 버퍼 거리: {road_gdf['buffer_dist'].max():.1f}m")

    return buffered_gdf


def perform_spatial_join(
    pipe_gdf: gpd.GeoDataFrame,
    road_buffered_gdf: gpd.GeoDataFrame,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """파이프와 버퍼된 도로 간 공간 조인을 수행

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        road_buffered_gdf: 버퍼된 도로 GeoDataFrame
        verbose: 상세 정보 출력 여부

    Returns:
        조인 결과 GeoDataFrame
    """
    if verbose:
        print("\n공간 조인 수행 중...")

    # 필요한 컬럼만 선택
    road_cols = ["RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE", "SIG_CD", "buffered_geometry"]
    road_subset = road_buffered_gdf[road_cols].copy()

    # 공간 조인 (left join으로 모든 파이프 포함)
    overlaps = gpd.sjoin(
        pipe_gdf[["FTR_IDN", "geometry"]],
        road_subset,
        how="left",
        predicate=SPATIAL_PREDICATE,
    )

    if verbose:
        print(f"공간 조인 완료: {len(overlaps)}개의 매칭")
        unique_pipes = overlaps["FTR_IDN"].nunique()
        print(f"  - 매칭된 파이프 수: {unique_pipes}")
        print(f"  - 원본 파이프 수: {len(pipe_gdf)}")
        print(f"  - 매칭 비율: {unique_pipes/len(pipe_gdf)*100:.1f}%")

    return overlaps


def select_primary_road(
    overlaps_df: pd.DataFrame, verbose: bool = True
) -> pd.DataFrame:
    """도로 폭 우선순위로 각 파이프의 주요 도로를 선택

    Args:
        overlaps_df: 공간 조인 결과 DataFrame
        verbose: 상세 정보 출력 여부

    Returns:
        각 파이프당 하나의 도로만 포함하는 DataFrame
    """
    if verbose:
        print("\n도로 폭 우선순위 적용 중...")

    # 중복 파이프 확인
    duplicate_pipes = overlaps_df.groupby("FTR_IDN").size()
    multi_road_pipes = (duplicate_pipes > 1).sum()

    if verbose and multi_road_pipes > 0:
        print(f"  - 여러 도로와 중첩된 파이프: {multi_road_pipes}개")
        max_roads = duplicate_pipes.max()
        print(f"  - 최대 중첩 도로 수: {max_roads}개")

    # 우선순위 정렬: 1) 도로폭(내림차순), 2) 도로등급(오름차순), 3) 도로코드(오름차순)
    sorted_df = overlaps_df.sort_values(
        by=["FTR_IDN", "ROAD_BT", "ROA_CLS_SE", "RN_CD"],
        ascending=[True, False, True, True],
    )

    # 각 파이프당 첫 번째 도로만 선택
    result = sorted_df.drop_duplicates(subset=["FTR_IDN"], keep="first")

    if verbose:
        print(f"우선순위 적용 완료: {len(result)}개의 파이프-도로 매칭")

    return result


def analyze_pipe_traffic(
    pipe_gdf: gpd.GeoDataFrame,
    road_buffered_gdf: gpd.GeoDataFrame,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """파이프와 도로의 교통 정보를 분석

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        road_buffered_gdf: 버퍼된 도로 GeoDataFrame
        verbose: 상세 정보 출력 여부

    Returns:
        (분석 결과 DataFrame, 통계 딕셔너리)
    """
    # 공간 조인
    overlaps = perform_spatial_join(pipe_gdf, road_buffered_gdf, verbose)

    # 우선순위 적용
    result = select_primary_road(overlaps, verbose)

    # 매칭된 도로 수 계산
    matched_count = result["RN_CD"].notna().sum()

    stats = {
        "total": len(pipe_gdf),
        "matched": matched_count,
        "match_rate": matched_count / len(pipe_gdf) * 100 if len(pipe_gdf) > 0 else 0,
    }

    return result, stats


def save_traffic_csv(
    df: pd.DataFrame,
    output_path: Path,
    verbose: bool = True,
) -> None:
    """교통 정보 CSV를 저장

    Args:
        df: 저장할 DataFrame
        output_path: 출력 파일 경로
        verbose: 상세 정보 출력 여부
    """
    # 필요한 컬럼만 선택
    output_cols = ["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]
    output_df = df[output_cols].copy()

    # FTR_IDN을 정수로 변환 (소수점 제거)
    output_df["FTR_IDN"] = output_df["FTR_IDN"].astype(float).astype(int)

    # CSV 저장
    output_df.to_csv(output_path, index=False, encoding=OUTPUT_ENCODING)

    if verbose:
        print(f"  - {output_path.name}: {len(output_df)}개 레코드")
