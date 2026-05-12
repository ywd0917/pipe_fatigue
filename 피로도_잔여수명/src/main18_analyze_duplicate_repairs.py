"""
복구 작업 중복 위치 분석 스크립트
- 통합 CSV 파일(누수공사_통합_위치추가.csv)의 위치 데이터 분석
- 같은 위치(거리 임계값 이내)에서 반복된 공사 탐지
- 중복 패턴 및 통계 분석
"""

import argparse
import time
import warnings
from collections import defaultdict
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    from scipy.spatial import cKDTree

    HAS_SPATIAL_LIBS = True
except ImportError:
    HAS_SPATIAL_LIBS = False
    print(
        "경고: geopandas 또는 scipy가 설치되지 않았습니다. 기본 알고리즘을 사용합니다."
    )

try:
    from sklearn.cluster import DBSCAN

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from src.common.config import RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# ========== 상수 정의 ==========
# 거리 임계값 설정 (미터 단위) - 쉽게 변경 가능
DISTANCE_THRESHOLD = 10.0  # 중복 판단 거리 (기본 10m)
MIN_TIME_INTERVAL_DAYS = 30  # 의미있는 재공사로 판단하는 최소 간격 (일)
MIN_CLUSTER_SIZE_FOR_ANALYSIS = 4  # 상세 분석 대상 최소 중복 횟수

# 데이터 파일명
UNIFIED_CSV_FILE = "main11e_merge_all_repairs/누수공사_통합_위치추가.csv"

# 작업 타입 목록
REPAIR_TYPES = ["지상누수", "지하누수", "긴급공사", "관리대장"]


def calculate_haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    두 지점 간의 거리를 Haversine 공식으로 계산 (미터 단위)

    Args:
        lat1, lon1: 첫 번째 지점의 위도, 경도
        lat2, lon2: 두 번째 지점의 위도, 경도

    Returns:
        거리 (미터)
    """
    # 지구 반지름 (미터)
    R = 6371000

    # 라디안으로 변환
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine 공식
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return R * c


def parse_numeric_date_column(df: pd.DataFrame, column_name: str) -> pd.Series:
    """
    숫자 형식의 날짜 컬럼을 datetime으로 파싱

    Args:
        df: DataFrame
        column_name: 파싱할 컬럼명

    Returns:
        파싱된 datetime Series (파싱 실패 시 NaT)
    """
    if column_name not in df.columns:
        return pd.Series(pd.NaT, index=df.index)

    # 숫자 형식 (예: 202206230912.0)을 문자열로 변환
    date_str = df[column_name].astype(str).str.replace(".0", "", regex=False)

    # YYYYMMDDHHMM 형식으로 파싱
    dates = pd.to_datetime(date_str, format="%Y%m%d%H%M", errors="coerce")

    # 비정상적인 날짜 필터링 (2000년 이전, 2030년 이후)
    dates.loc[dates.dt.year < 2000] = pd.NaT
    dates.loc[dates.dt.year > 2030] = pd.NaT

    return dates


def load_recovery_data(results_dir: Path) -> pd.DataFrame | None:
    """
    통합 복구 작업 CSV 파일을 로드

    Args:
        results_dir: 결과 디렉토리 경로

    Returns:
        통합된 DataFrame 또는 None
    """
    print("\n=== 데이터 로드 중 ===")

    # 통합 CSV 파일 경로
    file_path = results_dir / UNIFIED_CSV_FILE

    if not file_path.exists():
        print(f"  오류: {UNIFIED_CSV_FILE} 파일을 찾을 수 없습니다.")
        return None

    try:
        # 통합 CSV 파일 읽기
        df = pd.read_csv(file_path, encoding="utf-8-sig")
        print(f"  통합 파일 로드: {len(df):,}건")

        # 위도/경도가 있는 데이터만 필터링
        df_valid = df.dropna(subset=["위도", "경도"]).copy()
        print(f"  유효한 좌표 데이터: {len(df_valid):,}건")

        # 파일타입 컬럼을 작업타입으로 사용
        if "파일타입" in df_valid.columns:
            df_valid["작업타입"] = df_valid["파일타입"]
        else:
            print("  경고: 파일타입 컬럼이 없습니다. 작업타입을 '미분류'로 설정합니다.")
            df_valid["작업타입"] = "미분류"

        # 작업타입별 통계 출력
        print("\n  작업타입별 데이터:")
        for repair_type in REPAIR_TYPES:
            count = len(df_valid[df_valid["작업타입"] == repair_type])
            if count > 0:
                print(f"    - {repair_type}: {count:,}건")

        # 날짜 컬럼 파싱 - 우선순위: 기존 작업일시 > 접수일시 > 작업시작일시 > 작업종료일
        if "작업일시" in df_valid.columns:
            # 작업일시가 이미 있으면 datetime으로 변환
            df_valid["작업일시"] = pd.to_datetime(df_valid["작업일시"], errors="coerce")
        else:
            # 작업일시가 없으면 다른 컬럼들로부터 생성
            # 접수일시를 기본으로 사용
            if "접수일시" in df_valid.columns:
                df_valid["작업일시"] = parse_numeric_date_column(df_valid, "접수일시")
            else:
                df_valid["작업일시"] = pd.NaT

            # 누락된 값을 작업시작일시로 채우기
            mask = df_valid["작업일시"].isna()
            if mask.any() and "작업시작일시" in df_valid.columns:
                작업시작일시 = parse_numeric_date_column(df_valid, "작업시작일시")
                df_valid.loc[mask, "작업일시"] = 작업시작일시.loc[mask]

            # 여전히 누락된 값을 작업종료일로 채우기
            mask = df_valid["작업일시"].isna()
            if mask.any() and "작업종료일" in df_valid.columns:
                작업종료일 = parse_numeric_date_column(df_valid, "작업종료일")
                df_valid.loc[mask, "작업일시"] = 작업종료일.loc[mask]

        # 인덱스 추가 (고유 ID)
        df_valid["repair_id"] = range(len(df_valid))

        print(f"\n총 {len(df_valid):,}건의 데이터 로드 완료")

        return df_valid

    except Exception as e:
        print(f"  오류: {UNIFIED_CSV_FILE} 로드 실패 - {e}")
        return None


def find_duplicate_clusters_ckdtree(df: pd.DataFrame) -> dict[int, list[int]]:
    """
    cKDTree를 사용한 최적화된 중복 클러스터 찾기

    Args:
        df: 복구 작업 DataFrame

    Returns:
        클러스터 딕셔너리 {cluster_id: [repair_indices]}
    """
    n = len(df)
    print(f"  cKDTree 최적화 사용...")

    # 좌표 변환 (WGS84 → EPSG:5179)
    print("  좌표계 변환 중 (WGS84 → EPSG:5179)...")
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["경도"], df["위도"]), crs="EPSG:4326"
    ).to_crs("EPSG:5179")

    coords = np.array([[geom.x, geom.y] for geom in gdf.geometry])

    # cKDTree 구축
    print("  공간 인덱스 구축 중...")
    tree = cKDTree(coords)

    # 반경 내 이웃 찾기 (self-query)
    print("  반경 검색 수행 중...")
    neighbors = tree.query_ball_tree(tree, r=DISTANCE_THRESHOLD)

    # 클러스터 생성
    print("  클러스터 생성 중...")
    visited = set()
    clusters = {}
    cluster_id = 0

    for i in range(n):
        if i not in visited:
            # 이웃이 2개 이상인 경우만 (자기 자신 포함)
            if len(neighbors[i]) >= 2:
                # 아직 방문하지 않은 이웃들로 클러스터 생성
                cluster = [j for j in neighbors[i] if j not in visited]
                if len(cluster) >= 2:
                    clusters[cluster_id] = cluster
                    visited.update(cluster)
                    cluster_id += 1

        # 진행률 표시
        if (i + 1) % 10000 == 0:
            print(f"  진행 중: {i+1:,}/{n:,} ({(i+1)/n*100:.1f}%)")

    print(f"  중복 그룹 발견: {len(clusters):,}개")
    return clusters


def find_duplicate_clusters_dbscan(df: pd.DataFrame) -> dict[int, list[int]]:
    """
    DBSCAN 알고리즘을 사용한 중복 클러스터 찾기

    Args:
        df: 복구 작업 DataFrame

    Returns:
        클러스터 딕셔너리 {cluster_id: [repair_indices]}
    """
    n = len(df)
    print(f"  DBSCAN 최적화 사용...")

    # 좌표 변환 (WGS84 → EPSG:5179)
    print("  좌표계 변환 중 (WGS84 → EPSG:5179)...")
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["경도"], df["위도"]), crs="EPSG:4326"
    ).to_crs("EPSG:5179")

    coords = np.array([[geom.x, geom.y] for geom in gdf.geometry])

    # DBSCAN 클러스터링
    print("  DBSCAN 클러스터링 수행 중...")
    clustering = DBSCAN(
        eps=DISTANCE_THRESHOLD,
        min_samples=2,
        algorithm="kd_tree",
        n_jobs=-1,  # 모든 CPU 코어 사용
    ).fit(coords)

    # 클러스터 딕셔너리 생성
    clusters = defaultdict(list)
    for i, label in enumerate(clustering.labels_):
        if label != -1:  # -1은 노이즈 (클러스터에 속하지 않음)
            clusters[label].append(i)

    # defaultdict를 일반 dict로 변환하고 인덱스 재정렬
    clusters = {i: indices for i, indices in enumerate(clusters.values())}

    print(f"  중복 그룹 발견: {len(clusters):,}개")
    return clusters


def find_duplicate_clusters(df: pd.DataFrame) -> dict[int, list[int]]:
    """
    거리 임계값 이내의 중복 공사를 클러스터로 그룹화
    (최적화된 버전 - 공간 인덱싱 사용)

    Args:
        df: 복구 작업 DataFrame

    Returns:
        클러스터 딕셔너리 {cluster_id: [repair_ids]}
    """
    print(f"\n=== 중복 위치 탐색 중 (임계값: {DISTANCE_THRESHOLD}m) ===")

    n = len(df)
    print(f"  총 {n:,}개 데이터 분석 시작...")

    # 사용 가능한 라이브러리에 따라 최적 알고리즘 선택
    if HAS_SPATIAL_LIBS:
        start_time = time.time()

        # cKDTree 사용 (가장 빠름)
        result = find_duplicate_clusters_ckdtree(df)

        elapsed = time.time() - start_time
        print(f"  실행 시간: {elapsed:.2f}초")
        return result

    # 라이브러리가 없으면 기존 방식 사용
    print("  경고: 최적화 라이브러리가 없어 기본 알고리즘을 사용합니다.")

    # 작은 데이터셋은 기존 방식 사용
    if n < 5000:
        return _find_duplicate_clusters_simple(df)

    # 큰 데이터셋은 그리드 기반 최적화 사용
    return _find_duplicate_clusters_optimized(df)


def _find_duplicate_clusters_simple(df: pd.DataFrame) -> dict[int, list[int]]:
    """단순 버전 (작은 데이터셋용)"""
    n = len(df)
    visited = [False] * n
    clusters = {}
    cluster_id = 0

    # 각 점에 대해 클러스터링
    for i in range(n):
        if visited[i]:
            continue

        # 새 클러스터 시작
        cluster = [i]
        visited[i] = True

        lat1 = df.iloc[i]["위도"]
        lon1 = df.iloc[i]["경도"]

        # 임계값 이내의 모든 점 찾기
        for j in range(i + 1, n):
            if visited[j]:
                continue

            lat2 = df.iloc[j]["위도"]
            lon2 = df.iloc[j]["경도"]

            distance = calculate_haversine_distance(lat1, lon1, lat2, lon2)

            if distance <= DISTANCE_THRESHOLD:
                cluster.append(j)
                visited[j] = True

        # 2개 이상의 점이 있는 경우만 클러스터로 저장
        if len(cluster) >= 2:
            clusters[cluster_id] = cluster
            cluster_id += 1

        # 진행률 표시
        if (i + 1) % 1000 == 0:
            print(f"  진행 중: {i+1:,}/{n:,} ({(i+1)/n*100:.1f}%)")

    print(f"  중복 그룹 발견: {len(clusters):,}개")
    return clusters


def _find_duplicate_clusters_optimized(df: pd.DataFrame) -> dict[int, list[int]]:
    """최적화된 버전 (큰 데이터셋용 - 그리드 기반)"""
    n = len(df)

    # 그리드 셀 크기 (약 100m)
    grid_size = 0.001  # 약 100m in degrees

    print("  그리드 기반 최적화 사용 (셀 크기: ~100m)")

    # 그리드별로 점들을 그룹화
    grid_dict = defaultdict(list)
    for i in range(n):
        lat = df.iloc[i]["위도"]
        lon = df.iloc[i]["경도"]

        # 그리드 좌표 계산
        grid_x = int(lat / grid_size)
        grid_y = int(lon / grid_size)

        # 주변 9개 셀 모두에 추가 (인접 셀 검색을 위해)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                grid_dict[(grid_x + dx, grid_y + dy)].append(i)

    print(f"  그리드 생성 완료: {len(grid_dict):,}개 셀")

    visited = [False] * n
    clusters = {}
    cluster_id = 0

    # 각 점에 대해 클러스터링 (그리드 내에서만 검색)
    for i in range(n):
        if visited[i]:
            continue

        # 새 클러스터 시작
        cluster = [i]
        visited[i] = True

        lat1 = df.iloc[i]["위도"]
        lon1 = df.iloc[i]["경도"]

        # 그리드 좌표
        grid_x = int(lat1 / grid_size)
        grid_y = int(lon1 / grid_size)

        # 같은 그리드 셀의 점들만 검색
        candidates = grid_dict[(grid_x, grid_y)]

        for j in candidates:
            if j <= i or visited[j]:
                continue

            lat2 = df.iloc[j]["위도"]
            lon2 = df.iloc[j]["경도"]

            distance = calculate_haversine_distance(lat1, lon1, lat2, lon2)

            if distance <= DISTANCE_THRESHOLD:
                cluster.append(j)
                visited[j] = True

        # 2개 이상의 점이 있는 경우만 클러스터로 저장
        if len(cluster) >= 2:
            clusters[cluster_id] = cluster
            cluster_id += 1

        # 진행률 표시
        if (i + 1) % 10000 == 0:
            print(f"  진행 중: {i+1:,}/{n:,} ({(i+1)/n*100:.1f}%)")

    print(f"  중복 그룹 발견: {len(clusters):,}개")
    return clusters


def analyze_duplicate_patterns_filtered(
    df: pd.DataFrame, clusters: dict[int, list[int]], min_size: int = 2
) -> dict[str, Any]:
    """
    최소 크기 이상의 중복 패턴만 분석

    Args:
        df: 복구 작업 DataFrame
        clusters: 클러스터 딕셔너리
        min_size: 분석할 최소 클러스터 크기

    Returns:
        분석 결과 딕셔너리
    """
    # 크기 필터링
    filtered_clusters = {
        cid: indices for cid, indices in clusters.items() if len(indices) >= min_size
    }

    if min_size > 2:
        print(f"\n=== {min_size}회 이상 중복 패턴 분석 중 ===")
        print(
            f"  필터링 결과: {len(filtered_clusters):,}개 클러스터 (전체 {len(clusters):,}개 중)"
        )

    return analyze_duplicate_patterns(df, filtered_clusters)


def analyze_duplicate_patterns(
    df: pd.DataFrame, clusters: dict[int, list[int]]
) -> dict[str, Any]:
    """
    중복 패턴 분석

    Args:
        df: 복구 작업 DataFrame
        clusters: 클러스터 딕셔너리

    Returns:
        분석 결과 딕셔너리
    """
    print("\n=== 중복 패턴 분석 중 ===")

    # 전체 데이터의 날짜 범위 계산
    first_date = None
    last_date = None
    if "작업일시" in df.columns:
        valid_dates = df["작업일시"].dropna()
        if len(valid_dates) > 0:
            first_date = valid_dates.min()
            last_date = valid_dates.max()

    stats: dict[str, Any] = {
        "total_repairs": len(df),
        "duplicate_clusters": len(clusters),
        "duplicate_repairs": sum(len(cluster) for cluster in clusters.values()),
        "type_transitions": defaultdict(int),
        "time_intervals": [],
        "district_stats": defaultdict(lambda: {"total": 0, "duplicates": 0}),
        "cluster_details": [],
        "first_construction_date": first_date,
        "last_construction_date": last_date,
    }

    # 각 클러스터 분석
    for cluster_id, repair_indices in clusters.items():
        cluster_df = df.iloc[repair_indices].sort_values("작업일시")

        # 클러스터 상세 정보
        cluster_info = {
            "cluster_id": cluster_id,
            "size": len(repair_indices),
            "repairs": [],
            "types": cluster_df["작업타입"].tolist(),
            "districts": (
                cluster_df["구군"].unique().tolist()
                if "구군" in cluster_df.columns
                else []
            ),
            "date_range": None,
            "time_intervals": [],
            "avg_interval": None,  # 평균 재작업 간격
        }

        # 시간 간격 계산
        if "작업일시" in cluster_df.columns:
            dates = cluster_df["작업일시"].dropna()
            if len(dates) >= 2:
                date_min = dates.min()
                date_max = dates.max()
                cluster_info["date_range"] = (
                    f"{date_min:%Y-%m-%d} ~ {date_max:%Y-%m-%d}"
                )

                # 연속된 작업 간 시간 간격
                for i in range(1, len(dates)):
                    interval = (dates.iloc[i] - dates.iloc[i - 1]).days
                    if interval >= 0:
                        cast("list[int]", cluster_info["time_intervals"]).append(
                            interval
                        )
                        cast("list[int]", stats["time_intervals"]).append(interval)

                # 클러스터의 평균 재작업 간격 계산
                if cluster_info["time_intervals"]:
                    cluster_info["avg_interval"] = np.mean(
                        cluster_info["time_intervals"]
                    )

        # 작업 타입 전환 패턴
        types = cluster_df["작업타입"].tolist()
        for i in range(1, len(types)):
            transition = f"{types[i-1]} → {types[i]}"
            stats["type_transitions"][transition] += 1

        # 구군별 통계
        if "구군" in cluster_df.columns:
            for district in cluster_df["구군"].dropna().unique():
                stats["district_stats"][district]["duplicates"] += len(
                    cluster_df[cluster_df["구군"] == district]
                )

        # 클러스터 정보 저장
        for _, row in cluster_df.iterrows():
            cast("list[dict[str, Any]]", cluster_info["repairs"]).append(
                {
                    "repair_id": row["repair_id"],
                    "type": row["작업타입"],
                    "date": row.get("작업일시", ""),
                    "address": row.get("주소", ""),
                    "lat": row["위도"],
                    "lon": row["경도"],
                }
            )

        stats["cluster_details"].append(cluster_info)

    # 전체 구군별 통계 계산
    if "구군" in df.columns:
        for district in df["구군"].dropna().unique():
            stats["district_stats"][district]["total"] = len(df[df["구군"] == district])

    return stats


def generate_report(stats: dict[str, Any], title_suffix: str = "") -> str:
    """
    통계 보고서 생성

    Args:
        stats: 분석 결과 딕셔너리
        title_suffix: 제목에 추가할 접미사

    Returns:
        보고서 문자열
    """
    report = []
    report.append("=" * 60)
    report.append(f"복구 작업 중복 위치 분석 보고서{title_suffix}")
    report.append("=" * 60)
    report.append(f"\n분석 기준: 거리 임계값 {DISTANCE_THRESHOLD}m")
    report.append(f"생성 시간: {datetime.now():%Y-%m-%d %H:%M:%S}")

    # 기본 통계
    report.append("\n" + "=" * 40)
    report.append("1. 기본 통계")
    report.append("=" * 40)
    report.append(f"총 복구 작업 건수: {stats['total_repairs']:,}건")
    report.append(f"중복 위치 그룹 수: {stats['duplicate_clusters']:,}개")
    report.append(f"중복 복구 작업 건수: {stats['duplicate_repairs']:,}건")
    duplicate_rate = stats["duplicate_repairs"] / stats["total_repairs"] * 100
    report.append(f"중복 비율: {duplicate_rate:.2f}%")

    # 날짜 범위 추가
    if stats.get("first_construction_date") and stats.get("last_construction_date"):
        report.append(f"최초 시공일: {stats['first_construction_date']:%Y-%m-%d}")
        report.append(f"최후 시공일: {stats['last_construction_date']:%Y-%m-%d}")

    # 작업 타입별 전환 패턴
    report.append("\n" + "=" * 40)
    report.append("2. 작업 타입 전환 패턴")
    report.append("=" * 40)
    if stats["type_transitions"]:
        sorted_transitions = sorted(
            stats["type_transitions"].items(), key=lambda x: x[1], reverse=True
        )
        for transition, count in sorted_transitions[:10]:  # 상위 10개
            report.append(f"  {transition}: {count:,}건")
    else:
        report.append("  전환 패턴 없음")

    # 시간 간격 분석
    report.append("\n" + "=" * 40)
    report.append("3. 재작업 시간 간격")
    report.append("=" * 40)
    if stats["time_intervals"]:
        intervals = np.array(stats["time_intervals"])
        report.append(f"  평균 간격: {np.mean(intervals):.1f}일")
        report.append(f"  중앙값: {np.median(intervals):.1f}일")
        report.append(f"  최소 간격: {np.min(intervals)}일")
        report.append(f"  최대 간격: {np.max(intervals)}일")

        # 기간별 재작업 비율
        total_intervals = len(intervals)
        report.append(f"\n  [기간별 재작업 비율] - 전체 {total_intervals:,}건 기준")

        # 30일 이내
        repairs_30d = sum(1 for i in intervals if i <= 30)
        report.append(
            f"  30일 이내: {repairs_30d:,}건 / {total_intervals:,}건 "
            f"({repairs_30d/total_intervals*100:.1f}%)"
        )

        # 3개월(90일) 이내
        repairs_3m = sum(1 for i in intervals if i <= 90)
        report.append(
            f"  3개월 이내: {repairs_3m:,}건 / {total_intervals:,}건 "
            f"({repairs_3m/total_intervals*100:.1f}%)"
        )

        # 6개월(180일) 이내
        repairs_6m = sum(1 for i in intervals if i <= 180)
        report.append(
            f"  6개월 이내: {repairs_6m:,}건 / {total_intervals:,}건 "
            f"({repairs_6m/total_intervals*100:.1f}%)"
        )

        # 1년(365일) 이내
        repairs_1y = sum(1 for i in intervals if i <= 365)
        report.append(
            f"  1년 이내: {repairs_1y:,}건 / {total_intervals:,}건 "
            f"({repairs_1y/total_intervals*100:.1f}%)"
        )

        # 2년(730일) 이내
        repairs_2y = sum(1 for i in intervals if i <= 730)
        report.append(
            f"  2년 이내: {repairs_2y:,}건 / {total_intervals:,}건 "
            f"({repairs_2y/total_intervals*100:.1f}%)"
        )
    else:
        report.append("  시간 정보 없음")

    # 구군별 중복 발생률
    report.append("\n" + "=" * 40)
    report.append("4. 구군별 중복 발생률")
    report.append("=" * 40)
    if stats["district_stats"]:
        district_rates = []
        for district, data in stats["district_stats"].items():
            if data["total"] > 0:
                rate = data["duplicates"] / data["total"] * 100
                district_rates.append(
                    (district, data["total"], data["duplicates"], rate)
                )

        # 중복 발생률 순으로 정렬
        district_rates.sort(key=lambda x: x[3], reverse=True)

        for district, total, duplicates, rate in district_rates[:10]:  # 상위 10개
            report.append(f"  {district}: {rate:.1f}% ({duplicates:,}/{total:,})")
    else:
        report.append("  구군 정보 없음")

    # 클러스터 크기 분포
    report.append("\n" + "=" * 40)
    report.append("5. 중복 그룹 크기 분포")
    report.append("=" * 40)
    cluster_sizes = [len(c["repairs"]) for c in stats["cluster_details"]]
    if cluster_sizes:
        size_dist = pd.Series(cluster_sizes).value_counts().sort_index()
        for size, count in size_dist.items():
            report.append(f"  {size}개 중복: {count:,}개 그룹")

    return "\n".join(report)


def create_repair_count_pie_chart(stats: dict[str, Any], output_dir: Path) -> None:
    """
    재작업 횟수별 비중을 보여주는 파이 차트 생성

    Args:
        stats: 분석 결과 딕셔너리
        output_dir: 출력 디렉토리
    """
    # 클러스터 크기별 집계
    cluster_sizes = [len(c["repairs"]) for c in stats["cluster_details"]]

    if not cluster_sizes:
        print("  - 클러스터 데이터가 없어 파이 차트를 생성할 수 없습니다.")
        return

    # 한글 폰트 설정
    setup_korean_font()

    # 크기별 카운트
    size_counts = pd.Series(cluster_sizes).value_counts().sort_index()

    # 단독 공사와 중복 공사 분류
    single_repairs = stats["total_repairs"] - stats["duplicate_repairs"]

    # 카테고리별 집계
    categories: dict[str, int] = {}
    categories["단독 공사 (중복 없음)"] = single_repairs

    # 중복 횟수별 집계
    for size, count in size_counts.items():
        size_int = int(cast("Any", size))  # 명시적 타입 변환
        count_int = int(cast("Any", count))  # 명시적 타입 변환
        if size_int == 2:
            categories["2회 재작업"] = count_int * size_int
        elif size_int == 3:
            categories["3회 재작업"] = count_int * size_int
        elif size_int == 4:
            categories["4회 재작업"] = count_int * size_int
        elif size_int == 5:
            categories["5회 재작업"] = count_int * size_int
        elif size_int >= 6 and size_int <= 10:
            if "6~10회 재작업" not in categories:
                categories["6~10회 재작업"] = 0
            categories["6~10회 재작업"] += count_int * size_int
        elif size_int > 10:
            if "11회 이상 재작업" not in categories:
                categories["11회 이상 재작업"] = 0
            categories["11회 이상 재작업"] += count_int * size_int

    # 그림 생성
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # 파이 차트 1: 전체 비중
    labels1 = list(categories.keys())
    sizes1 = list(categories.values())
    colors1 = [
        "#66b3ff",
        "#ff9999",
        "#99ff99",
        "#ffcc99",
        "#ff99cc",
        "#99ccff",
        "#ffff99",
    ]

    # 퍼센트 계산
    total = sum(sizes1)
    percentages = [s / total * 100 for s in sizes1]

    # 라벨에 건수와 퍼센트 추가
    labels1_with_count = [
        f"{label}\n{size:,}건 ({pct:.1f}%)"
        for label, size, pct in zip(labels1, sizes1, percentages, strict=False)
    ]

    wedges1, texts1, autotexts1 = ax1.pie(
        sizes1,
        labels=labels1_with_count,
        colors=colors1[: len(sizes1)],
        autopct="",
        startangle=90,
    )

    ax1.set_title(
        f"전체 공사 중 재작업 횟수별 비중\n(총 {total:,}건)", fontsize=14, pad=20
    )

    # 파이 차트 2: 중복 공사만의 분포
    dup_categories = {
        k: v for k, v in categories.items() if k != "단독 공사 (중복 없음)"
    }
    labels2 = list(dup_categories.keys())
    sizes2 = list(dup_categories.values())
    colors2 = ["#ff9999", "#99ff99", "#ffcc99", "#ff99cc", "#99ccff", "#ffff99"]

    # 퍼센트 계산
    total_dup = sum(sizes2)
    percentages2 = [s / total_dup * 100 for s in sizes2]

    # 라벨에 건수와 퍼센트 추가
    labels2_with_count = [
        f"{label}\n{size:,}건 ({pct:.1f}%)"
        for label, size, pct in zip(labels2, sizes2, percentages2, strict=False)
    ]

    wedges2, texts2, autotexts2 = ax2.pie(
        sizes2,
        labels=labels2_with_count,
        colors=colors2[: len(sizes2)],
        autopct="",
        startangle=90,
    )

    ax2.set_title(
        f"중복 공사 내 재작업 횟수별 분포\n(총 {total_dup:,}건)", fontsize=14, pad=20
    )

    # 통계 요약 텍스트
    stats_text = (
        f"=== 재작업 통계 ===\n"
        f'총 공사: {stats["total_repairs"]:,}건\n'
        f'단독 공사: {single_repairs:,}건 ({single_repairs/stats["total_repairs"]*100:.1f}%)\n'
        f'중복 공사: {stats["duplicate_repairs"]:,}건 ({stats["duplicate_repairs"]/stats["total_repairs"]*100:.1f}%)\n'
        f'중복 위치: {stats["duplicate_clusters"]:,}개소\n'
        f"평균 중복 횟수: {np.mean(cluster_sizes):.1f}회"
    )

    fig.text(
        0.5,
        0.02,
        stats_text,
        ha="center",
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)

    # 파일로 저장
    pie_file = output_dir / "duplicate_repair_count_pie.png"
    plt.savefig(pie_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  - 재작업 횟수별 비중 파이 차트: {pie_file}")


def create_cluster_interval_histogram(
    cluster_avg_intervals: list[float], output_dir: Path
) -> None:
    """
    클러스터별 평균 재작업 간격 히스토그램 생성

    Args:
        cluster_avg_intervals: 클러스터별 평균 간격 리스트
        output_dir: 출력 디렉토리
    """
    if not cluster_avg_intervals:
        return

    # 한글 폰트 설정
    setup_korean_font()

    # 그림 생성
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    # 히스토그램 생성 (30일 단위)
    max_days = min(max(cluster_avg_intervals), 3650)  # 최대 10년까지만
    bins = list(range(0, int(max_days) + 31, 30))

    counts, edges, patches = ax.hist(
        cluster_avg_intervals,
        bins=bins,
        edgecolor="black",
        alpha=0.7,
        color="steelblue",
    )

    ax.set_xlabel("클러스터 평균 재작업 간격 (일)")
    ax.set_ylabel("클러스터 수")
    ax.set_title("중복 위치별 평균 재작업 간격 분포")
    ax.grid(True, alpha=0.3)

    # 주요 구간에 라벨 추가
    for i, count in enumerate(counts[:20]):  # 처음 20개 구간만
        if count > 0:
            ax.text(
                edges[i] + 15,
                count,
                f"{int(count)}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # 통계 정보 추가
    stats_text = (
        f"전체 클러스터: {len(cluster_avg_intervals):,}개\n"
        f"평균: {np.mean(cluster_avg_intervals):.1f}일\n"
        f"중앙값: {np.median(cluster_avg_intervals):.1f}일\n"
        f"━━━━━━━━━━━━━\n"
        f"30일 이내: {sum(1 for x in cluster_avg_intervals if x <= 30):,}개 ({sum(1 for x in cluster_avg_intervals if x <= 30)/len(cluster_avg_intervals)*100:.1f}%)\n"
        f"3개월 이내: {sum(1 for x in cluster_avg_intervals if x <= 90):,}개 ({sum(1 for x in cluster_avg_intervals if x <= 90)/len(cluster_avg_intervals)*100:.1f}%)\n"
        f"6개월 이내: {sum(1 for x in cluster_avg_intervals if x <= 180):,}개 ({sum(1 for x in cluster_avg_intervals if x <= 180)/len(cluster_avg_intervals)*100:.1f}%)\n"
        f"1년 이내: {sum(1 for x in cluster_avg_intervals if x <= 365):,}개 ({sum(1 for x in cluster_avg_intervals if x <= 365)/len(cluster_avg_intervals)*100:.1f}%)"
    )

    ax.text(
        0.98,
        0.97,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    # 파일로 저장
    histogram_file = output_dir / "duplicate_cluster_avg_histogram.png"
    plt.savefig(histogram_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  - 클러스터 평균 간격 히스토그램: {histogram_file}")


def create_interval_histogram(intervals: list[int], output_dir: Path) -> None:
    """
    재작업 시간 간격 히스토그램 생성

    Args:
        intervals: 시간 간격 리스트 (일 단위)
        output_dir: 출력 디렉토리
    """
    if not intervals:
        print("  - 시간 간격 데이터가 없어 히스토그램을 생성할 수 없습니다.")
        return

    # 한글 폰트 설정
    setup_korean_font()

    # 그림 생성
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # 전체 데이터 히스토그램 (30일 단위 빈)
    max_days = max(intervals)
    n_bins = int(max_days / 30) + 1
    bins = [i * 30 for i in range(n_bins + 1)]

    counts, edges, patches = ax1.hist(
        intervals, bins=bins, edgecolor="black", alpha=0.7
    )

    ax1.set_xlabel("재작업 간격 (일)")
    ax1.set_ylabel("건수")
    ax1.set_title("재작업 시간 간격 분포 (30일 단위)")
    ax1.grid(True, alpha=0.3)

    # 주요 구간에 라벨 추가
    for i, count in enumerate(counts[:20]):  # 처음 20개 구간만 표시
        if count > 0:
            ax1.text(
                edges[i] + 15,
                count,
                f"{int(count)}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # 1년 이내 데이터만 확대해서 보기
    intervals_1year = [i for i in intervals if i <= 365]
    if intervals_1year:
        bins_1year = list(range(0, 391, 30))  # 0일부터 390일까지 30일 단위

        counts_1year, edges_1year, patches_1year = ax2.hist(
            intervals_1year,
            bins=bins_1year,
            edgecolor="black",
            alpha=0.7,
            color="orange",
        )

        ax2.set_xlabel("재작업 간격 (일)")
        ax2.set_ylabel("건수")
        ax2.set_title("재작업 시간 간격 분포 (1년 이내, 30일 단위)")
        ax2.grid(True, alpha=0.3)

        # 구간별 라벨 추가
        for i, count in enumerate(counts_1year):
            if count > 0:
                ax2.text(
                    edges_1year[i] + 15,
                    count,
                    f"{int(count)}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

        # x축 라벨 설정
        ax2.set_xticks(bins_1year)
        ax2.set_xticklabels([f"{i}" for i in bins_1year], rotation=45)

    # 통계 정보 텍스트 추가
    intervals_array = np.array(intervals)
    stats_text = (
        f"전체: {len(intervals):,}건\n"
        f"평균: {np.mean(intervals_array):.1f}일\n"
        f"중앙값: {np.median(intervals_array):.1f}일\n"
        f"━━━━━━━━━━━━━\n"
        f"30일 이내: {sum(1 for i in intervals if i <= 30):,}건 ({sum(1 for i in intervals if i <= 30)/len(intervals)*100:.1f}%)\n"
        f"3개월 이내: {sum(1 for i in intervals if i <= 90):,}건 ({sum(1 for i in intervals if i <= 90)/len(intervals)*100:.1f}%)\n"
        f"6개월 이내: {sum(1 for i in intervals if i <= 180):,}건 ({sum(1 for i in intervals if i <= 180)/len(intervals)*100:.1f}%)\n"
        f"1년 이내: {len(intervals_1year):,}건 ({len(intervals_1year)/len(intervals)*100:.1f}%)"
    )

    fig.text(
        0.02,
        0.95,
        stats_text,
        transform=fig.transFigure,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    # 파일로 저장
    histogram_file = output_dir / "duplicate_interval_histogram.png"
    plt.savefig(histogram_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  - 시간 간격 히스토그램: {histogram_file}")


def save_results(df: pd.DataFrame, stats: dict[str, Any], output_dir: Path) -> None:
    """
    분석 결과를 파일로 저장

    Args:
        df: 원본 DataFrame
        stats: 분석 결과
        output_dir: 출력 디렉토리
    """
    print("\n=== 결과 저장 중 ===")

    # 1. 중복 그룹 상세 정보 CSV
    cluster_rows = []
    for cluster in stats["cluster_details"]:
        for repair in cluster["repairs"]:
            row = {
                "cluster_id": cluster["cluster_id"],
                "cluster_size": cluster["size"],
                "repair_id": repair["repair_id"],
                "작업타입": repair["type"],
                "작업일시": repair["date"],
                "주소": repair["address"],
                "위도": repair["lat"],
                "경도": repair["lon"],
            }
            cluster_rows.append(row)

    if cluster_rows:
        cluster_df = pd.DataFrame(cluster_rows)
        cluster_file = output_dir / "duplicate_repairs_analysis.csv"
        cluster_df.to_csv(cluster_file, index=False, encoding="utf-8-sig")
        print(f"  - 중복 그룹 상세: {cluster_file}")

    # 2. 통계 보고서 텍스트
    report = generate_report(stats)
    report_file = output_dir / "duplicate_statistics.txt"
    with report_file.open("w", encoding="utf-8") as f:
        f.write(report)
    print(f"  - 통계 보고서: {report_file}")

    # 3. 요약 통계 CSV
    summary_items = [
        "총 복구 작업",
        "중복 위치 그룹",
        "중복 복구 작업",
        "중복 비율(%)",
        "평균 재작업 간격(일)",
    ]
    summary_values = [
        stats["total_repairs"],
        stats["duplicate_clusters"],
        stats["duplicate_repairs"],
        f"{stats['duplicate_repairs']/stats['total_repairs']*100:.2f}",
        f"{np.mean(stats['time_intervals']):.1f}" if stats["time_intervals"] else "N/A",
    ]

    # 날짜 정보 추가
    if stats.get("first_construction_date"):
        summary_items.append("최초 시공일")
        summary_values.append(f"{stats['first_construction_date']:%Y-%m-%d}")
    if stats.get("last_construction_date"):
        summary_items.append("최후 시공일")
        summary_values.append(f"{stats['last_construction_date']:%Y-%m-%d}")

    summary = {
        "항목": summary_items,
        "값": summary_values,
    }
    summary_df = pd.DataFrame(summary)
    summary_file = output_dir / "duplicate_summary.csv"
    summary_df.to_csv(summary_file, index=False, encoding="utf-8-sig")
    print(f"  - 요약 통계: {summary_file}")

    # 4. 클러스터별 평균 재작업 간격 CSV
    cluster_avg_rows = []
    for cluster in stats["cluster_details"]:
        if cluster["avg_interval"] is not None:
            # 첫 번째 repair의 정보 가져오기
            first_repair = cluster["repairs"][0] if cluster["repairs"] else {}

            cluster_avg_rows.append(
                {
                    "cluster_id": cluster["cluster_id"],
                    "중복_건수": cluster["size"],
                    "평균_재작업_간격(일)": f"{cluster['avg_interval']:.1f}",
                    "최소_간격(일)": (
                        min(cluster["time_intervals"])
                        if cluster["time_intervals"]
                        else None
                    ),
                    "최대_간격(일)": (
                        max(cluster["time_intervals"])
                        if cluster["time_intervals"]
                        else None
                    ),
                    "기간": cluster["date_range"],
                    "작업타입_패턴": " → ".join(cluster["types"][:5]),  # 처음 5개만
                    "구군": cluster["districts"][0] if cluster["districts"] else "",
                    "대표_주소": first_repair.get("address", "")[:30],  # 30자까지만
                }
            )

    if cluster_avg_rows:
        # 평균 재작업 간격으로 정렬
        cluster_avg_df = pd.DataFrame(cluster_avg_rows)
        cluster_avg_df = cluster_avg_df.sort_values(
            "평균_재작업_간격(일)", ascending=True
        )

        cluster_avg_file = output_dir / "duplicate_cluster_intervals.csv"
        cluster_avg_df.to_csv(cluster_avg_file, index=False, encoding="utf-8-sig")
        print(f"  - 클러스터별 평균 간격: {cluster_avg_file}")

        # 통계 요약 출력
        avg_intervals = [
            c["avg_interval"]
            for c in stats["cluster_details"]
            if c["avg_interval"] is not None
        ]
        if avg_intervals:
            print("    * 클러스터 평균 간격 통계:")
            print(f"      - 분석 대상 클러스터: {len(avg_intervals):,}개")
            print(f"      - 전체 평균: {np.mean(avg_intervals):.1f}일")
            print(f"      - 중앙값: {np.median(avg_intervals):.1f}일")
            print(f"      - 최소: {np.min(avg_intervals):.1f}일")
            print(f"      - 최대: {np.max(avg_intervals):.1f}일")
            print(
                f"      - 30일 이내: {sum(1 for x in avg_intervals if x <= 30):,}개 ({sum(1 for x in avg_intervals if x <= 30)/len(avg_intervals)*100:.1f}%)"
            )
            print(
                f"      - 3개월 이내: {sum(1 for x in avg_intervals if x <= 90):,}개 ({sum(1 for x in avg_intervals if x <= 90)/len(avg_intervals)*100:.1f}%)"
            )
            print(
                f"      - 6개월 이내: {sum(1 for x in avg_intervals if x <= 180):,}개 ({sum(1 for x in avg_intervals if x <= 180)/len(avg_intervals)*100:.1f}%)"
            )
            print(
                f"      - 1년 이내: {sum(1 for x in avg_intervals if x <= 365):,}개 ({sum(1 for x in avg_intervals if x <= 365)/len(avg_intervals)*100:.1f}%)"
            )

            # 클러스터 평균 간격 히스토그램 생성
            create_cluster_interval_histogram(avg_intervals, output_dir)

    # 5. 재작업 횟수별 비중 파이 차트
    create_repair_count_pie_chart(stats, output_dir)

    # 6. 시간 간격 히스토그램
    if stats["time_intervals"]:
        create_interval_histogram(stats["time_intervals"], output_dir)

        # 7. 시간 간격 분포 테이블 CSV
        intervals_array = np.array(stats["time_intervals"])

        # 30일 단위 구간별 집계
        interval_bins = []
        interval_counts = []
        interval_percentages = []

        for i in range(0, 730, 30):  # 2년까지 30일 단위
            count = np.sum((intervals_array >= i) & (intervals_array < i + 30))
            if count > 0:
                interval_bins.append(f"{i}~{i+29}일")
                interval_counts.append(count)
                interval_percentages.append(f"{count/len(intervals_array)*100:.1f}%")

        # 2년 이상
        count_2years = np.sum(intervals_array >= 730)
        if count_2years > 0:
            interval_bins.append("730일 이상")
            interval_counts.append(count_2years)
            interval_percentages.append(f"{count_2years/len(intervals_array)*100:.1f}%")

        interval_dist_df = pd.DataFrame(
            {
                "재작업 간격": interval_bins,
                "건수": interval_counts,
                "비율": interval_percentages,
            }
        )

        interval_file = output_dir / "duplicate_interval_distribution.csv"
        interval_dist_df.to_csv(interval_file, index=False, encoding="utf-8-sig")
        print(f"  - 시간 간격 분포: {interval_file}")


def run_benchmark(df: pd.DataFrame) -> None:
    """
    여러 알고리즘의 성능을 벤치마크

    Args:
        df: 복구 작업 DataFrame
    """
    print("\n" + "=" * 60)
    print("성능 벤치마크 모드")
    print("=" * 60)

    results = {}
    n = len(df)

    # 1. 기본 그리드 알고리즘
    if n < 100000:  # 너무 큰 데이터는 제외
        print(f"\n[1] 그리드 기반 알고리즘 테스트...")
        start_time = time.time()
        clusters_grid = _find_duplicate_clusters_optimized(df)
        elapsed_grid = time.time() - start_time
        results["그리드"] = {
            "시간": elapsed_grid,
            "클러스터": len(clusters_grid),
        }
        print(f"  실행 시간: {elapsed_grid:.2f}초")
        print(f"  발견된 클러스터: {len(clusters_grid):,}개")

    # 2. cKDTree 알고리즘
    if HAS_SPATIAL_LIBS:
        print(f"\n[2] cKDTree 알고리즘 테스트...")
        start_time = time.time()
        clusters_kdtree = find_duplicate_clusters_ckdtree(df)
        elapsed_kdtree = time.time() - start_time
        results["cKDTree"] = {
            "시간": elapsed_kdtree,
            "클러스터": len(clusters_kdtree),
        }
        print(f"  실행 시간: {elapsed_kdtree:.2f}초")
        print(f"  발견된 클러스터: {len(clusters_kdtree):,}개")

    # 3. DBSCAN 알고리즘
    if HAS_SKLEARN and HAS_SPATIAL_LIBS:
        print(f"\n[3] DBSCAN 알고리즘 테스트...")
        start_time = time.time()
        clusters_dbscan = find_duplicate_clusters_dbscan(df)
        elapsed_dbscan = time.time() - start_time
        results["DBSCAN"] = {
            "시간": elapsed_dbscan,
            "클러스터": len(clusters_dbscan),
        }
        print(f"  실행 시간: {elapsed_dbscan:.2f}초")
        print(f"  발견된 클러스터: {len(clusters_dbscan):,}개")

    # 결과 요약
    print("\n" + "=" * 60)
    print("벤치마크 결과 요약")
    print("=" * 60)

    if results:
        # 가장 빠른 알고리즘 찾기
        fastest = min(results.items(), key=lambda x: x[1]["시간"])
        print(f"\n데이터 크기: {n:,}개")
        print(f"\n알고리즘별 성능:")
        for name, result in results.items():
            speedup = (
                results.get("그리드", {}).get("시간", 1) / result["시간"]
                if "그리드" in results
                else 1
            )
            print(
                f"  {name:10s}: {result['시간']:6.2f}초 (클러스터: {result['클러스터']:,}개) [속도향상: {speedup:.1f}x]"
            )

        print(f"\n최적 알고리즘: {fastest[0]} ({fastest[1]['시간']:.2f}초)")


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="복구 작업 중복 위치 분석")
    parser.add_argument(
        "--output-dir",
        type=str,
        help="출력 디렉토리 경로 (기본값: results/main18_duplicate_analysis/)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="성능 벤치마크 모드 (여러 알고리즘 비교)",
    )
    parser.add_argument(
        "--algorithm",
        choices=["auto", "ckdtree", "dbscan", "grid", "simple"],
        default="auto",
        help="사용할 알고리즘 선택 (기본값: auto - 자동 선택)",
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    print("\n" + "=" * 60)
    print("복구 작업 중복 위치 분석 시작")
    print("=" * 60)

    # 출력 디렉토리 설정
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else RESULTS_DIR / "main18_duplicate_analysis"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"출력 디렉토리: {output_dir}")

    # 데이터 로드
    df = load_recovery_data(RESULTS_DIR)
    if df is None:
        print("분석을 중단합니다.")
        return

    # 벤치마크 모드
    if args.benchmark:
        run_benchmark(df)
        return

    # 알고리즘 선택에 따른 중복 클러스터 찾기
    if args.algorithm == "ckdtree" and HAS_SPATIAL_LIBS:
        print("\ncKDTree 알고리즘 사용")
        clusters = find_duplicate_clusters_ckdtree(df)
    elif args.algorithm == "dbscan" and HAS_SKLEARN and HAS_SPATIAL_LIBS:
        print("\nDBSCAN 알고리즘 사용")
        clusters = find_duplicate_clusters_dbscan(df)
    elif args.algorithm == "grid":
        print("\n그리드 기반 알고리즘 사용")
        clusters = _find_duplicate_clusters_optimized(df)
    elif args.algorithm == "simple":
        print("\n단순 알고리즘 사용")
        clusters = _find_duplicate_clusters_simple(df)
    else:
        # auto 모드 - 자동 선택
        clusters = find_duplicate_clusters(df)

    if not clusters:
        print(f"\n거리 임계값 {DISTANCE_THRESHOLD}m 이내에 중복이 없습니다.")
        return

    # 전체 패턴 분석
    stats = analyze_duplicate_patterns(df, clusters)

    # 결과 출력
    print("\n" + generate_report(stats))

    # 결과 저장
    save_results(df, stats, output_dir)

    # 4회 이상 중복 분석
    print("\n" + "=" * 60)
    print("4회 이상 재작업 위치 상세 분석")
    print("=" * 60)

    stats_4plus = analyze_duplicate_patterns_filtered(
        df, clusters, min_size=MIN_CLUSTER_SIZE_FOR_ANALYSIS
    )

    if stats_4plus["duplicate_clusters"] > 0:
        # 4회 이상 통계 보고서 출력
        report_4plus = generate_report(stats_4plus, " (4회 이상)")
        print("\n" + report_4plus)

        # 4회 이상 통계 저장
        report_file_4plus = output_dir / "duplicate_4plus_statistics.txt"
        with report_file_4plus.open("w", encoding="utf-8") as f:
            f.write(report_4plus)
        print(f"\n4회 이상 통계 저장: {report_file_4plus}")

        # 4회 이상 클러스터 CSV 저장
        cluster_4plus_rows = []
        for cluster in stats_4plus["cluster_details"]:
            if len(cluster["repairs"]) >= MIN_CLUSTER_SIZE_FOR_ANALYSIS:
                first_repair = cluster["repairs"][0] if cluster["repairs"] else {}
                cluster_4plus_rows.append(
                    {
                        "cluster_id": cluster["cluster_id"],
                        "중복_건수": cluster["size"],
                        "평균_재작업_간격(일)": (
                            f"{cluster['avg_interval']:.1f}"
                            if cluster["avg_interval"]
                            else "N/A"
                        ),
                        "최소_간격(일)": (
                            min(cluster["time_intervals"])
                            if cluster["time_intervals"]
                            else None
                        ),
                        "최대_간격(일)": (
                            max(cluster["time_intervals"])
                            if cluster["time_intervals"]
                            else None
                        ),
                        "기간": cluster["date_range"],
                        "구군": cluster["districts"][0] if cluster["districts"] else "",
                        "대표_주소": first_repair.get("address", "")[:50],
                    }
                )

        if cluster_4plus_rows:
            cluster_4plus_df = pd.DataFrame(cluster_4plus_rows)
            cluster_4plus_df = cluster_4plus_df.sort_values(
                "중복_건수", ascending=False
            )
            cluster_4plus_file = output_dir / "duplicate_4plus_clusters.csv"
            cluster_4plus_df.to_csv(
                cluster_4plus_file, index=False, encoding="utf-8-sig"
            )
            print(f"4회 이상 클러스터 정보: {cluster_4plus_file}")
    else:
        print("\n4회 이상 중복 위치가 없습니다.")

    print("\n" + "=" * 60)
    print("분석 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
