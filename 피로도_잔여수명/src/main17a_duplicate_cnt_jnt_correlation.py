"""
main17a: 중복 재작업 위치와 파이프 연결점 복잡도(CNT_JNT) 상관관계 분석
- main15에서 생성한 Joint 데이터 사용
- main13에서 생성한 통합 복구 데이터 사용
- 매칭 거리를 매개변수로 설정 가능 (기본값: 30m)
- 범위 이내 모든 파이프 고려
- 최대 CNT_JNT, 평균 CNT_JNT, 가장 가까운 CNT_JNT 모두 분석
- KD-Tree 최적화 적용
"""

import json
import sys
import warnings
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 기본 상수 정의
DEFAULT_DISTANCE_THRESHOLD = 30.0  # 기본 파이프 검색 반경 (미터)
MIN_REPAIRS_FOR_FREQUENT = 4  # 빈번한 재작업 판단 기준


def calculate_euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """두 지점 간의 유클리드 거리 계산 (미터 단위, EPSG:5179 좌표계)"""
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def load_pipe_data() -> pd.DataFrame:
    """PIPE_LM_JOINT와 SPLY_LS_JOINT shapefile 로드 및 통합"""
    print("\n=== 파이프 데이터 로드 중 ===")

    import geopandas as gpd

    pipe_data = []

    # shapefile 디렉토리 (main15_extract_joint_data 출력)
    shp_dir = RESULTS_DIR / "main15_extract_joint_data" / "shapefiles"

    # PIPE_LM_JOINT.shp 로드
    pipe_lm_path = shp_dir / "PIPE_LM_JOINT.shp"
    if pipe_lm_path.exists():
        try:
            gdf_pipe_lm = gpd.read_file(pipe_lm_path)

            # EPSG:5179 유지 (좌표계 변환 없음)
            if gdf_pipe_lm.crs and gdf_pipe_lm.crs != "EPSG:5179":
                print(f"  좌표계 변환: {gdf_pipe_lm.crs} → EPSG:5179")
                gdf_pipe_lm = gdf_pipe_lm.to_crs("EPSG:5179")
            else:
                print("  좌표계: EPSG:5179 유지")

            # 좌표 추출
            df_pipe_lm = pd.DataFrame(
                {
                    "FTR_IDN": gdf_pipe_lm["FTR_IDN"],
                    "CNT_JNT": gdf_pipe_lm["CNT_JNT"],
                    "PIPE_TYPE": "PIPE_LM",
                }
            )

            # 각 세그먼트의 시작점과 끝점 좌표 추출
            start_coords = []
            end_coords = []
            center_coords = []

            for geom in gdf_pipe_lm.geometry:
                coords = list(geom.coords)
                start_coords.append(coords[0])
                end_coords.append(coords[-1])
                # 중심점 계산
                center_x = (coords[0][0] + coords[-1][0]) / 2
                center_y = (coords[0][1] + coords[-1][1]) / 2
                center_coords.append((center_x, center_y))

            df_pipe_lm["START_X"] = [c[0] for c in start_coords]
            df_pipe_lm["START_Y"] = [c[1] for c in start_coords]
            df_pipe_lm["END_X"] = [c[0] for c in end_coords]
            df_pipe_lm["END_Y"] = [c[1] for c in end_coords]
            df_pipe_lm["CENTER_X"] = [c[0] for c in center_coords]
            df_pipe_lm["CENTER_Y"] = [c[1] for c in center_coords]

            pipe_data.append(df_pipe_lm)
            print(f"  PIPE_LM_JOINT 로드: {len(df_pipe_lm):,}개 세그먼트")

            if "CNT_JNT" in df_pipe_lm.columns:
                cnt_stats = df_pipe_lm["CNT_JNT"].value_counts().sort_index()
                print("  CNT_JNT 분포:")
                for cnt, num in cnt_stats.items():
                    print(f"    - CNT_JNT = {cnt}: {num:,}개")
        except Exception as e:
            print(f"  오류: PIPE_LM_JOINT 로드 실패 - {e}")

    # SPLY_LS_JOINT.shp 로드
    sply_ls_path = shp_dir / "SPLY_LS_JOINT.shp"
    if sply_ls_path.exists():
        try:
            gdf_sply_ls = gpd.read_file(sply_ls_path)

            # EPSG:5179 유지 (좌표계 변환 없음)
            if gdf_sply_ls.crs and gdf_sply_ls.crs != "EPSG:5179":
                print(f"  좌표계 변환: {gdf_sply_ls.crs} → EPSG:5179")
                gdf_sply_ls = gdf_sply_ls.to_crs("EPSG:5179")
            else:
                print("  좌표계: EPSG:5179 유지")

            # 좌표 추출
            df_sply_ls = pd.DataFrame(
                {
                    "FTR_IDN": gdf_sply_ls["FTR_IDN"],
                    "CNT_JNT": gdf_sply_ls["CNT_JNT"],
                    "PIPE_TYPE": "SPLY_LS",
                }
            )

            # 각 세그먼트의 시작점과 끝점 좌표 추출
            start_coords = []
            end_coords = []
            center_coords = []

            for geom in gdf_sply_ls.geometry:
                coords = list(geom.coords)
                start_coords.append(coords[0])
                end_coords.append(coords[-1])
                # 중심점 계산
                center_x = (coords[0][0] + coords[-1][0]) / 2
                center_y = (coords[0][1] + coords[-1][1]) / 2
                center_coords.append((center_x, center_y))

            df_sply_ls["START_X"] = [c[0] for c in start_coords]
            df_sply_ls["START_Y"] = [c[1] for c in start_coords]
            df_sply_ls["END_X"] = [c[0] for c in end_coords]
            df_sply_ls["END_Y"] = [c[1] for c in end_coords]
            df_sply_ls["CENTER_X"] = [c[0] for c in center_coords]
            df_sply_ls["CENTER_Y"] = [c[1] for c in center_coords]

            pipe_data.append(df_sply_ls)
            print(f"  SPLY_LS_JOINT 로드: {len(df_sply_ls):,}개 세그먼트")

            if "CNT_JNT" in df_sply_ls.columns:
                cnt_stats = df_sply_ls["CNT_JNT"].value_counts().sort_index()
                print("  CNT_JNT 분포:")
                for cnt, num in cnt_stats.items():
                    print(f"    - CNT_JNT = {cnt}: {num:,}개")
        except Exception as e:
            print(f"  오류: SPLY_LS_JOINT 로드 실패 - {e}")

    if not pipe_data:
        raise FileNotFoundError("파이프 데이터 파일을 찾을 수 없습니다.")

    # 데이터 통합
    df_pipes = pd.concat(pipe_data, ignore_index=True)

    print(f"\n  총 파이프 세그먼트: {len(df_pipes):,}개")
    return df_pipes


def load_520_repair_operations() -> pd.DataFrame:
    """0520 지역 개별 복구 작업 데이터 로드 및 같은 위치 작업 횟수 계산"""
    print("\n=== 0520 지역 복구 작업 데이터 로드 중 ===")

    from pyproj import Transformer

    # 좌표 변환기 설정 (WGS84 → Korea TM)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)

    # 통합 CSV 파일 경로 (main13_crop_520 출력)
    unified_csv_path = (
        RESULTS_DIR / "main13_crop_520" / "누수공사_통합_520_위치추가.csv"
    )

    if not unified_csv_path.exists():
        raise FileNotFoundError(
            f"통합 복구 데이터 파일을 찾을 수 없습니다: {unified_csv_path}"
        )

    # 통합 CSV 파일 로드
    try:
        df_all = pd.read_csv(unified_csv_path, encoding="utf-8-sig")

        # 유효한 좌표만 필터링
        df_all = df_all.dropna(subset=["위도", "경도"]).copy()

        # 위경도를 EPSG:5179로 변환
        print("  좌표계 변환: EPSG:4326 (위경도) → EPSG:5179 (Korea TM)")
        x_coords, y_coords = transformer.transform(
            df_all["경도"].values, df_all["위도"].values
        )
        df_all["X"] = x_coords
        df_all["Y"] = y_coords

        # 파일타입을 작업타입으로 사용 (기타공사 제외)
        valid_types = ["지상누수", "지하누수", "긴급공사", "관리대장"]
        df_all = df_all[df_all["파일타입"].isin(valid_types)].copy()
        df_all["작업타입"] = df_all["파일타입"]

        # 각 타입별 통계 출력
        for repair_type in valid_types:
            count = len(df_all[df_all["작업타입"] == repair_type])
            if count > 0:
                print(f"  {repair_type}: {count:,}개 로드")

    except Exception as e:
        raise Exception(f"통합 CSV 파일 로드 실패: {e}")

    if len(df_all) == 0:
        raise ValueError("유효한 복구 데이터가 없습니다.")

    print(f"  전체 복구 작업: {len(df_all):,}개")

    # 각 작업에 대해 같은 위치(10m 이내) 작업 횟수 계산
    print("\n  같은 위치 작업 횟수 계산 중...")
    LOCATION_DISTANCE_THRESHOLD = 10.0  # 미터

    repair_counts = []
    for i in range(len(df_all)):
        x1 = df_all.iloc[i]["X"]
        y1 = df_all.iloc[i]["Y"]

        # 같은 위치(10m 이내) 작업 수 계산
        count = 0
        for j in range(len(df_all)):
            x2 = df_all.iloc[j]["X"]
            y2 = df_all.iloc[j]["Y"]

            dist = calculate_euclidean_distance(x1, y1, x2, y2)
            if dist <= LOCATION_DISTANCE_THRESHOLD:
                count += 1

        repair_counts.append(count)

    # 개별 작업 데이터프레임 생성
    df_operations = df_all.copy()
    df_operations["OPERATION_ID"] = range(len(df_operations))
    df_operations["REPAIR_COUNT_AT_LOCATION"] = repair_counts

    # 통계 출력
    print(f"\n  총 작업 수: {len(df_operations):,}개")

    # 작업 횟수별 분포
    count_dist = df_operations["REPAIR_COUNT_AT_LOCATION"].value_counts().sort_index()
    print("\n  같은 위치 작업 횟수 분포:")
    for count, num in count_dist.head(9).items():
        print(f"    {count}회: {num:,}개 작업")

    frequent_operations = len(
        df_operations[
            df_operations["REPAIR_COUNT_AT_LOCATION"] >= MIN_REPAIRS_FOR_FREQUENT
        ]
    )
    print(f"\n  4회 이상 재작업된 위치의 작업: {frequent_operations:,}개")

    return df_operations


def match_operations_to_pipes_v2(
    df_operations: pd.DataFrame,
    df_pipes: pd.DataFrame,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
) -> tuple[pd.DataFrame, int, int]:
    """각 개별 작업을 지정 거리 이내 모든 파이프와 매칭하여 다양한 CNT_JNT 전략 분석

    Args:
        df_operations: 개별 작업 데이터프레임
        df_pipes: 파이프 데이터프레임
        distance_threshold: 매칭 거리 임계값 (미터), 기본값 30m

    Returns:
        (매칭 결과 데이터프레임, 전체 작업 수, 매칭된 작업 수)
    """
    print(
        f"\n=== 개별 작업-파이프 매칭 중 ({distance_threshold}m 이내 모든 파이프 고려) ==="
    )

    all_operation_data = []
    total_operations = len(df_operations)
    matched_count = 0

    for idx, operation in df_operations.iterrows():
        if isinstance(idx, int) and idx % 100 == 0:
            print(
                f"  진행 중: {idx}/{total_operations} ({idx/total_operations*100:.1f}%)"
            )

        operation_x = operation["X"]
        operation_y = operation["Y"]

        # EPSG:5179에서는 직접 미터 단위로 범위 계산 가능
        # 범위 내 파이프를 먼저 필터링
        x_mask = (df_pipes["CENTER_X"] >= operation_x - distance_threshold) & (
            df_pipes["CENTER_X"] <= operation_x + distance_threshold
        )
        y_mask = (df_pipes["CENTER_Y"] >= operation_y - distance_threshold) & (
            df_pipes["CENTER_Y"] <= operation_y + distance_threshold
        )

        candidates = df_pipes[x_mask & y_mask]

        # 정확한 거리 계산
        nearby_pipes = []
        for _, pipe in candidates.iterrows():
            dist = calculate_euclidean_distance(
                operation_x, operation_y, pipe["CENTER_X"], pipe["CENTER_Y"]
            )

            if dist <= distance_threshold:
                nearby_pipes.append(
                    {
                        "CNT_JNT": pipe["CNT_JNT"],
                        "PIPE_TYPE": pipe["PIPE_TYPE"],
                        "DISTANCE_M": dist,
                        "FTR_IDN": pipe["FTR_IDN"],
                    }
                )

        if nearby_pipes:
            # 매칭된 경우
            matched_count += 1

            # 여러 전략으로 분석
            # 1. 최대 CNT_JNT를 가진 파이프
            max_cnt_pipe = max(nearby_pipes, key=lambda x: x["CNT_JNT"])

            # 2. 평균 CNT_JNT
            avg_cnt_jnt = np.mean([p["CNT_JNT"] for p in nearby_pipes])

            # 3. 가장 가까운 파이프
            nearest_pipe = min(nearby_pipes, key=lambda x: x["DISTANCE_M"])

            # 4. CNT_JNT >= 3인 파이프 개수
            high_cnt_pipes = [p for p in nearby_pipes if p["CNT_JNT"] >= 3]

            all_operation_data.append(
                {
                    "OPERATION_ID": operation["OPERATION_ID"],
                    "REPAIR_COUNT_AT_LOCATION": operation["REPAIR_COUNT_AT_LOCATION"],
                    "작업타입": operation["작업타입"],
                    "작업종료일": operation.get("작업종료일", None),
                    "IS_MATCHED": True,
                    "MATCH_REASON": "pipes_found",
                    # 최대 CNT_JNT 기준
                    "MAX_CNT_JNT": max_cnt_pipe["CNT_JNT"],
                    "MAX_CNT_PIPE_TYPE": max_cnt_pipe["PIPE_TYPE"],
                    "MAX_CNT_DISTANCE": max_cnt_pipe["DISTANCE_M"],
                    # 평균 CNT_JNT
                    "AVG_CNT_JNT": avg_cnt_jnt,
                    # 가장 가까운 파이프 CNT_JNT
                    "NEAREST_CNT_JNT": nearest_pipe["CNT_JNT"],
                    "NEAREST_DISTANCE": nearest_pipe["DISTANCE_M"],
                    # 통계
                    "NEARBY_PIPE_COUNT": len(nearby_pipes),
                    "HIGH_CNT_PIPE_COUNT": len(high_cnt_pipes),
                    "IS_FREQUENT": operation["REPAIR_COUNT_AT_LOCATION"]
                    >= MIN_REPAIRS_FOR_FREQUENT,
                }
            )
        else:
            # 매칭되지 않은 경우도 포함
            all_operation_data.append(
                {
                    "OPERATION_ID": operation["OPERATION_ID"],
                    "REPAIR_COUNT_AT_LOCATION": operation["REPAIR_COUNT_AT_LOCATION"],
                    "작업타입": operation["작업타입"],
                    "작업종료일": operation.get("작업종료일", None),
                    "IS_MATCHED": False,
                    "MATCH_REASON": f"no_pipes_within_{distance_threshold}m",
                    # CNT_JNT 관련 필드는 None
                    "MAX_CNT_JNT": None,
                    "MAX_CNT_PIPE_TYPE": None,
                    "MAX_CNT_DISTANCE": None,
                    "AVG_CNT_JNT": None,
                    "NEAREST_CNT_JNT": None,
                    "NEAREST_DISTANCE": None,
                    "NEARBY_PIPE_COUNT": 0,
                    "HIGH_CNT_PIPE_COUNT": 0,
                    "IS_FREQUENT": operation["REPAIR_COUNT_AT_LOCATION"]
                    >= MIN_REPAIRS_FOR_FREQUENT,
                }
            )

    df_all = pd.DataFrame(all_operation_data)

    print("\n  매칭 완료!")
    print(f"  매칭된 작업: {matched_count:,}개 / {total_operations:,}개")
    if total_operations > 0:
        print(f"  매칭률: {matched_count/total_operations*100:.1f}%")

    # 매칭 통계 (매칭된 것만)
    df_matched = df_all[df_all["IS_MATCHED"] == True]
    if len(df_matched) > 0:
        print("\n  매칭 통계:")
        print(
            f"    평균 근처 파이프 수: {df_matched['NEARBY_PIPE_COUNT'].mean():.1f}개"
        )
        print(
            f"    CNT_JNT≥3 파이프 있는 작업: {len(df_matched[df_matched['HIGH_CNT_PIPE_COUNT'] > 0]):,}개"
        )

    return df_all, total_operations, matched_count


def analyze_cnt_jnt_correlation_v2(df_all: pd.DataFrame) -> dict[str, Any]:
    """다양한 CNT_JNT 전략으로 재작업 빈도와의 상관관계 분석"""
    print("\n=== CNT_JNT 상관관계 분석 (V2) ===")

    results: dict[str, Any] = {}

    # 매칭된 작업만 분석
    df_matched = df_all[df_all["IS_MATCHED"] == True].copy()

    if len(df_matched) == 0:
        print("  경고: 매칭된 작업이 없습니다.")
        return results

    # 4회 이상 위치 vs 미만 위치 그룹 분리
    frequent_group = df_matched[df_matched["IS_FREQUENT"]]
    normal_group = df_matched[~df_matched["IS_FREQUENT"]]

    print(
        f"\n빈번한 재작업 위치의 작업 (≥{MIN_REPAIRS_FOR_FREQUENT}회): {len(frequent_group)}개"
    )
    print(f"일반 위치의 작업 (<{MIN_REPAIRS_FOR_FREQUENT}회): {len(normal_group)}개")

    # 1. 최대 CNT_JNT 기준 분석
    print("\n--- 최대 CNT_JNT 기준 ---")
    results["max_cnt_frequent"] = {
        "count": len(frequent_group),
        "cnt_jnt_mean": frequent_group["MAX_CNT_JNT"].mean(),
        "cnt_jnt_median": frequent_group["MAX_CNT_JNT"].median(),
        "cnt_jnt_std": frequent_group["MAX_CNT_JNT"].std(),
    }

    results["max_cnt_normal"] = {
        "count": len(normal_group),
        "cnt_jnt_mean": normal_group["MAX_CNT_JNT"].mean(),
        "cnt_jnt_median": normal_group["MAX_CNT_JNT"].median(),
        "cnt_jnt_std": normal_group["MAX_CNT_JNT"].std(),
    }

    print(
        f"빈번한 그룹 - 최대 CNT_JNT 평균: {results['max_cnt_frequent']['cnt_jnt_mean']:.2f}"
    )
    print(
        f"일반 그룹 - 최대 CNT_JNT 평균: {results['max_cnt_normal']['cnt_jnt_mean']:.2f}"
    )

    # 2. 평균 CNT_JNT 기준 분석
    print("\n--- 평균 CNT_JNT 기준 ---")
    results["avg_cnt_frequent"] = {
        "cnt_jnt_mean": frequent_group["AVG_CNT_JNT"].mean(),
        "cnt_jnt_median": frequent_group["AVG_CNT_JNT"].median(),
        "cnt_jnt_std": frequent_group["AVG_CNT_JNT"].std(),
    }

    results["avg_cnt_normal"] = {
        "cnt_jnt_mean": normal_group["AVG_CNT_JNT"].mean(),
        "cnt_jnt_median": normal_group["AVG_CNT_JNT"].median(),
        "cnt_jnt_std": normal_group["AVG_CNT_JNT"].std(),
    }

    print(
        f"빈번한 그룹 - 평균 CNT_JNT: {results['avg_cnt_frequent']['cnt_jnt_mean']:.2f}"
    )
    print(f"일반 그룹 - 평균 CNT_JNT: {results['avg_cnt_normal']['cnt_jnt_mean']:.2f}")

    # 3. 가장 가까운 파이프 CNT_JNT 기준
    print("\n--- 가장 가까운 파이프 CNT_JNT 기준 ---")
    results["nearest_cnt_frequent"] = {
        "cnt_jnt_mean": frequent_group["NEAREST_CNT_JNT"].mean(),
        "cnt_jnt_median": frequent_group["NEAREST_CNT_JNT"].median(),
    }

    results["nearest_cnt_normal"] = {
        "cnt_jnt_mean": normal_group["NEAREST_CNT_JNT"].mean(),
        "cnt_jnt_median": normal_group["NEAREST_CNT_JNT"].median(),
    }

    print(
        f"빈번한 그룹 - 가장 가까운 파이프 CNT_JNT 평균: {results['nearest_cnt_frequent']['cnt_jnt_mean']:.2f}"
    )
    print(
        f"일반 그룹 - 가장 가까운 파이프 CNT_JNT 평균: {results['nearest_cnt_normal']['cnt_jnt_mean']:.2f}"
    )

    # 통계적 검정 (최대 CNT_JNT 기준)
    if len(frequent_group) > 0 and len(normal_group) > 0:
        # t-test
        t_stat, t_pval = stats.ttest_ind(
            frequent_group["MAX_CNT_JNT"], normal_group["MAX_CNT_JNT"]
        )
        results["t_test_max"] = {"statistic": float(t_stat), "p_value": float(t_pval)}

        print("\n통계적 검정 (최대 CNT_JNT):")
        print(f"  t-test: t={t_stat:.3f}, p={t_pval:.4f}")

        if t_pval < 0.05:
            print(
                "  → 두 그룹 간 최대 CNT_JNT에 통계적으로 유의한 차이가 있습니다 (p<0.05)"
            )
        else:
            print(
                "  → 두 그룹 간 최대 CNT_JNT에 통계적으로 유의한 차이가 없습니다 (p≥0.05)"
            )

    # 상관계수, p-value, R² 계산
    if len(df_matched) > 1:
        # 최대 CNT_JNT
        correlation_max = df_matched["MAX_CNT_JNT"].corr(
            df_matched["REPAIR_COUNT_AT_LOCATION"]
        )
        r_max, p_max = stats.pearsonr(
            df_matched["MAX_CNT_JNT"], df_matched["REPAIR_COUNT_AT_LOCATION"]
        )
        r2_max = r_max**2

        # 평균 CNT_JNT
        correlation_avg = df_matched["AVG_CNT_JNT"].corr(
            df_matched["REPAIR_COUNT_AT_LOCATION"]
        )
        r_avg, p_avg = stats.pearsonr(
            df_matched["AVG_CNT_JNT"], df_matched["REPAIR_COUNT_AT_LOCATION"]
        )
        r2_avg = r_avg**2

        # 가장 가까운 CNT_JNT
        correlation_nearest = df_matched["NEAREST_CNT_JNT"].corr(
            df_matched["REPAIR_COUNT_AT_LOCATION"]
        )
        r_nearest, p_nearest = stats.pearsonr(
            df_matched["NEAREST_CNT_JNT"], df_matched["REPAIR_COUNT_AT_LOCATION"]
        )
        r2_nearest = r_nearest**2

        # 결과 저장
        results["correlation_max"] = float(correlation_max)
        results["correlation_avg"] = float(correlation_avg)
        results["correlation_nearest"] = float(correlation_nearest)

        results["r_max"] = float(r_max)
        results["p_max"] = float(p_max)
        results["r2_max"] = float(r2_max)

        results["r_avg"] = float(r_avg)
        results["p_avg"] = float(p_avg)
        results["r2_avg"] = float(r2_avg)

        results["r_nearest"] = float(r_nearest)
        results["p_nearest"] = float(p_nearest)
        results["r2_nearest"] = float(r2_nearest)

        print("\n상관계수:")
        print(
            f"  최대 CNT_JNT vs 재작업 횟수: r={correlation_max:.3f}, p={p_max:.4f}, R²={r2_max:.4f}"
        )
        print(
            f"  평균 CNT_JNT vs 재작업 횟수: r={correlation_avg:.3f}, p={p_avg:.4f}, R²={r2_avg:.4f}"
        )
        print(
            f"  가장 가까운 CNT_JNT vs 재작업 횟수: r={correlation_nearest:.3f}, p={p_nearest:.4f}, R²={r2_nearest:.4f}"
        )

    # 높은 CNT_JNT 파이프 근처 분석
    clusters_with_high_cnt = df_matched[df_matched["HIGH_CNT_PIPE_COUNT"] > 0]
    if len(clusters_with_high_cnt) > 0:
        high_cnt_frequent_ratio = len(
            clusters_with_high_cnt[clusters_with_high_cnt["IS_FREQUENT"]]
        ) / len(clusters_with_high_cnt)
        results["high_cnt_nearby_frequent_ratio"] = float(high_cnt_frequent_ratio)
        print(
            f"\nCNT_JNT≥3 파이프가 근처에 있는 위치에서 빈번한 재작업 비율: {high_cnt_frequent_ratio*100:.1f}%"
        )

    return results


def create_visualizations_v2(
    df_matched: pd.DataFrame, results: dict[str, Any], output_dir: Path | None = None
) -> None:
    """V2 분석 결과 시각화"""
    print("\n=== 시각화 생성 중 (V2) ===")

    # 출력 디렉토리 생성
    if output_dir is None:
        output_dir = RESULTS_DIR / "main17a_duplicate_cnt_jnt_correlation"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 한글 폰트 설정
    setup_korean_font()

    # 1. 3개 전략 비교 박스플롯
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 최대 CNT_JNT
    data_max = [
        df_matched[~df_matched["IS_FREQUENT"]]["MAX_CNT_JNT"].values,
        df_matched[df_matched["IS_FREQUENT"]]["MAX_CNT_JNT"].values,
    ]
    bp1 = axes[0].boxplot(
        data_max, tick_labels=["일반\n(<4회)", "빈번\n(≥4회)"], patch_artist=True
    )
    axes[0].set_ylabel("CNT_JNT", fontsize=12)
    axes[0].set_title("최대 CNT_JNT 전략", fontsize=12, fontweight="bold")
    axes[0].grid(True, alpha=0.3)

    # 평균 CNT_JNT
    data_avg = [
        df_matched[~df_matched["IS_FREQUENT"]]["AVG_CNT_JNT"].values,
        df_matched[df_matched["IS_FREQUENT"]]["AVG_CNT_JNT"].values,
    ]
    bp2 = axes[1].boxplot(
        data_avg, tick_labels=["일반\n(<4회)", "빈번\n(≥4회)"], patch_artist=True
    )
    axes[1].set_ylabel("CNT_JNT", fontsize=12)
    axes[1].set_title("평균 CNT_JNT 전략", fontsize=12, fontweight="bold")
    axes[1].grid(True, alpha=0.3)

    # 가장 가까운 CNT_JNT
    data_nearest = [
        df_matched[~df_matched["IS_FREQUENT"]]["NEAREST_CNT_JNT"].values,
        df_matched[df_matched["IS_FREQUENT"]]["NEAREST_CNT_JNT"].values,
    ]
    bp3 = axes[2].boxplot(
        data_nearest, tick_labels=["일반\n(<4회)", "빈번\n(≥4회)"], patch_artist=True
    )
    axes[2].set_ylabel("CNT_JNT", fontsize=12)
    axes[2].set_title("가장 가까운 파이프 전략", fontsize=12, fontweight="bold")
    axes[2].grid(True, alpha=0.3)

    # 박스 색상 설정
    for bp in [bp1, bp2, bp3]:
        bp["boxes"][0].set_facecolor("lightblue")
        bp["boxes"][1].set_facecolor("salmon")

    plt.suptitle("CNT_JNT 선택 전략별 비교", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(
        output_dir / "duplicate_cnt_jnt_strategy_comparison.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    # 2. 상관관계 산점도 (3개 전략)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 색상 설정
    colors = ["blue" if not x else "red" for x in df_matched["IS_FREQUENT"]]

    # 최대 CNT_JNT 산점도
    axes[0].scatter(
        df_matched["MAX_CNT_JNT"],
        df_matched["REPAIR_COUNT_AT_LOCATION"],
        alpha=0.6,
        c=colors,
        s=50,
    )
    axes[0].set_xlabel("최대 CNT_JNT", fontsize=12)
    axes[0].set_ylabel("재작업 횟수", fontsize=12)
    axes[0].set_title(
        f"최대 CNT_JNT (r={results.get('correlation_max', 0):.3f})",
        fontsize=12,
        fontweight="bold",
    )
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(y=MIN_REPAIRS_FOR_FREQUENT, color="red", linestyle="--", alpha=0.5)

    # 평균 CNT_JNT 산점도
    axes[1].scatter(
        df_matched["AVG_CNT_JNT"],
        df_matched["REPAIR_COUNT_AT_LOCATION"],
        alpha=0.6,
        c=colors,
        s=50,
    )
    axes[1].set_xlabel("평균 CNT_JNT", fontsize=12)
    axes[1].set_ylabel("재작업 횟수", fontsize=12)
    axes[1].set_title(
        f"평균 CNT_JNT (r={results.get('correlation_avg', 0):.3f})",
        fontsize=12,
        fontweight="bold",
    )
    axes[1].grid(True, alpha=0.3)
    axes[1].axhline(y=MIN_REPAIRS_FOR_FREQUENT, color="red", linestyle="--", alpha=0.5)

    # 가장 가까운 CNT_JNT 산점도
    axes[2].scatter(
        df_matched["NEAREST_CNT_JNT"],
        df_matched["REPAIR_COUNT_AT_LOCATION"],
        alpha=0.6,
        c=colors,
        s=50,
    )
    axes[2].set_xlabel("가장 가까운 CNT_JNT", fontsize=12)
    axes[2].set_ylabel("재작업 횟수", fontsize=12)
    axes[2].set_title(
        f"가장 가까운 CNT_JNT (r={results.get('correlation_nearest', 0):.3f})",
        fontsize=12,
        fontweight="bold",
    )
    axes[2].grid(True, alpha=0.3)
    axes[2].axhline(y=MIN_REPAIRS_FOR_FREQUENT, color="red", linestyle="--", alpha=0.5)

    # 범례 추가
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="blue", alpha=0.6, label="일반 (<4회)"),
        Patch(facecolor="red", alpha=0.6, label="빈번 (≥4회)"),
    ]
    fig.legend(
        handles=legend_elements, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.05)
    )

    plt.suptitle(
        "CNT_JNT와 재작업 횟수 상관관계", fontsize=14, fontweight="bold", y=1.02
    )
    plt.tight_layout()
    plt.savefig(
        output_dir / "duplicate_cnt_jnt_correlation_scatter_v2.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    # 3. 근처 파이프 수 분포
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    frequent = df_matched[df_matched["IS_FREQUENT"]]
    normal = df_matched[~df_matched["IS_FREQUENT"]]

    bins = range(max(df_matched["NEARBY_PIPE_COUNT"].max(), 10) + 2)
    ax.hist(
        [normal["NEARBY_PIPE_COUNT"], frequent["NEARBY_PIPE_COUNT"]],
        bins=bins,
        label=["일반 (<4회)", "빈번 (≥4회)"],
        color=["lightblue", "salmon"],
        alpha=0.7,
        edgecolor="black",
    )

    ax.set_xlabel(f"{DEFAULT_DISTANCE_THRESHOLD}m 이내 파이프 수", fontsize=12)
    ax.set_ylabel("클러스터 수", fontsize=12)
    ax.set_title("재작업 위치 근처 파이프 수 분포", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        output_dir / "duplicate_nearby_pipe_count_distribution.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    print("  시각화 파일 생성 완료")


def save_analysis_results_v2(
    df_all: pd.DataFrame,
    results: dict[str, Any],
    total_operations: int,
    matched_operations: int,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
    output_dir: Path | None = None,
) -> None:
    """V2 분석 결과 저장"""

    # 출력 디렉토리 생성
    if output_dir is None:
        output_dir = RESULTS_DIR / "main17a_duplicate_cnt_jnt_correlation"
    output_dir.mkdir(parents=True, exist_ok=True)
    print("\n=== 분석 결과 저장 중 ===")

    # 매칭된 작업만 필터링
    df_matched = df_all[df_all["IS_MATCHED"] == True].copy()

    # 1. 상세 분석 결과 텍스트 파일
    with (output_dir / "0520_duplicate_cnt_jnt_analysis_v2.txt").open(
        "w", encoding="utf-8"
    ) as f:
        f.write("=" * 70 + "\n")
        f.write("달서구 0520 지역 - CNT_JNT 상관관계 분석 (통합 버전)\n")
        f.write(f"({distance_threshold}m 이내 모든 파이프 고려)\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"분석 일시: {pd.Timestamp.now()}\n")
        f.write(f"분석 대상: {total_operations:,}개 개별 작업\n")
        f.write(
            f"매칭된 작업: {matched_operations:,}개 ({matched_operations/total_operations*100:.1f}%)\n"
        )
        f.write(f"빈번한 재작업 기준: {MIN_REPAIRS_FOR_FREQUENT}회 이상\n")
        f.write(f"파이프 검색 반경: {distance_threshold}m\n\n")

        f.write("-" * 70 + "\n")
        f.write(f"1. 최대 CNT_JNT 전략 ({distance_threshold}m 이내 파이프 중 최대값)\n")
        f.write("-" * 70 + "\n\n")

        f.write(
            f"빈번한 재작업 그룹 (≥{MIN_REPAIRS_FOR_FREQUENT}회): {results['max_cnt_frequent']['count']}개\n"
        )
        f.write(f"  - 평균: {results['max_cnt_frequent']['cnt_jnt_mean']:.2f}\n")
        f.write(f"  - 중앙값: {results['max_cnt_frequent']['cnt_jnt_median']:.1f}\n")
        f.write(f"  - 표준편차: {results['max_cnt_frequent']['cnt_jnt_std']:.2f}\n")

        f.write(
            f"\n일반 재작업 그룹 (<{MIN_REPAIRS_FOR_FREQUENT}회): {results['max_cnt_normal']['count']}개\n"
        )
        f.write(f"  - 평균: {results['max_cnt_normal']['cnt_jnt_mean']:.2f}\n")
        f.write(f"  - 중앙값: {results['max_cnt_normal']['cnt_jnt_median']:.1f}\n")
        f.write(f"  - 표준편차: {results['max_cnt_normal']['cnt_jnt_std']:.2f}\n")

        f.write("\n" + "-" * 70 + "\n")
        f.write(f"2. 평균 CNT_JNT 전략 ({distance_threshold}m 이내 모든 파이프 평균)\n")
        f.write("-" * 70 + "\n\n")

        f.write(
            f"빈번한 재작업 그룹: {results['avg_cnt_frequent']['cnt_jnt_mean']:.2f}\n"
        )
        f.write(f"일반 재작업 그룹: {results['avg_cnt_normal']['cnt_jnt_mean']:.2f}\n")

        f.write("\n" + "-" * 70 + "\n")
        f.write("3. 가장 가까운 파이프 전략\n")
        f.write("-" * 70 + "\n\n")

        f.write(
            f"빈번한 재작업 그룹: {results['nearest_cnt_frequent']['cnt_jnt_mean']:.2f}\n"
        )
        f.write(
            f"일반 재작업 그룹: {results['nearest_cnt_normal']['cnt_jnt_mean']:.2f}\n"
        )

        f.write("\n" + "-" * 70 + "\n")
        f.write("4. 상관계수 비교\n")
        f.write("-" * 70 + "\n\n")

        f.write(f"최대 CNT_JNT vs 재작업 횟수:\n")
        f.write(f"  - 상관계수(r): {results.get('r_max', 0):.3f}\n")
        f.write(f"  - p-value: {results.get('p_max', 0):.4f}\n")
        f.write(f"  - R²: {results.get('r2_max', 0):.4f}\n\n")

        f.write(f"평균 CNT_JNT vs 재작업 횟수:\n")
        f.write(f"  - 상관계수(r): {results.get('r_avg', 0):.3f}\n")
        f.write(f"  - p-value: {results.get('p_avg', 0):.4f}\n")
        f.write(f"  - R²: {results.get('r2_avg', 0):.4f}\n\n")

        f.write(f"가장 가까운 CNT_JNT vs 재작업 횟수:\n")
        f.write(f"  - 상관계수(r): {results.get('r_nearest', 0):.3f}\n")
        f.write(f"  - p-value: {results.get('p_nearest', 0):.4f}\n")
        f.write(f"  - R²: {results.get('r2_nearest', 0):.4f}\n")

        if "t_test_max" in results:
            f.write("\n" + "-" * 70 + "\n")
            f.write("5. 통계적 검정 (최대 CNT_JNT 기준)\n")
            f.write("-" * 70 + "\n\n")
            f.write(
                f"t-test: t={results['t_test_max']['statistic']:.3f}, p={results['t_test_max']['p_value']:.4f}\n"
            )

            if results["t_test_max"]["p_value"] < 0.05:
                f.write("→ 통계적으로 유의한 차이가 있습니다 (p<0.05)\n")
            else:
                f.write("→ 통계적으로 유의한 차이가 없습니다 (p≥0.05)\n")

        if "high_cnt_nearby_frequent_ratio" in results:
            f.write("\n" + "-" * 70 + "\n")
            f.write("6. 높은 CNT_JNT 파이프 근처 분석\n")
            f.write("-" * 70 + "\n\n")
            f.write(
                f"CNT_JNT≥3 파이프가 {distance_threshold}m 이내에 있는 위치에서 빈번한 재작업 비율: "
            )
            f.write(f"{results['high_cnt_nearby_frequent_ratio']*100:.1f}%\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("분석 완료\n")
        f.write("=" * 70 + "\n")

    # 2. 모든 작업 데이터 저장 (IS_MATCHED 컬럼 포함)
    df_all.to_csv(
        output_dir / "0520_duplicate_cnt_jnt_all_operations_v2.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # 3. 매칭된 작업만 별도 저장 (기존 호환성 유지)
    df_matched.to_csv(
        output_dir / "0520_duplicate_cnt_jnt_matched_operations_v2.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # 4. 메타데이터 JSON 저장
    metadata = {
        "analysis_date": datetime.now().isoformat(),
        "total_operations": total_operations,
        "matched_operations": matched_operations,
        "match_rate": (
            matched_operations / total_operations if total_operations > 0 else 0
        ),
        "distance_threshold": distance_threshold,
        "min_repairs_for_frequent": MIN_REPAIRS_FOR_FREQUENT,
        "results": results,
    }

    metadata_path = output_dir / "analysis_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"  메타데이터 JSON 저장: {metadata_path}")

    # 5. 통계 요약 테이블
    summary_df = pd.DataFrame(
        [
            {
                "전략": "최대 CNT_JNT",
                "빈번 그룹 평균": results["max_cnt_frequent"]["cnt_jnt_mean"],
                "일반 그룹 평균": results["max_cnt_normal"]["cnt_jnt_mean"],
                "차이": results["max_cnt_frequent"]["cnt_jnt_mean"]
                - results["max_cnt_normal"]["cnt_jnt_mean"],
                "상관계수(r)": results.get("r_max", 0),
                "p-value": results.get("p_max", 0),
                "R²": results.get("r2_max", 0),
            },
            {
                "전략": "평균 CNT_JNT",
                "빈번 그룹 평균": results["avg_cnt_frequent"]["cnt_jnt_mean"],
                "일반 그룹 평균": results["avg_cnt_normal"]["cnt_jnt_mean"],
                "차이": results["avg_cnt_frequent"]["cnt_jnt_mean"]
                - results["avg_cnt_normal"]["cnt_jnt_mean"],
                "상관계수(r)": results.get("r_avg", 0),
                "p-value": results.get("p_avg", 0),
                "R²": results.get("r2_avg", 0),
            },
            {
                "전략": "가장 가까운",
                "빈번 그룹 평균": results["nearest_cnt_frequent"]["cnt_jnt_mean"],
                "일반 그룹 평균": results["nearest_cnt_normal"]["cnt_jnt_mean"],
                "차이": results["nearest_cnt_frequent"]["cnt_jnt_mean"]
                - results["nearest_cnt_normal"]["cnt_jnt_mean"],
                "상관계수(r)": results.get("r_nearest", 0),
                "p-value": results.get("p_nearest", 0),
                "R²": results.get("r2_nearest", 0),
            },
        ]
    )

    summary_df.to_csv(
        output_dir / "0520_cnt_jnt_strategy_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("  분석 결과 파일 저장 완료")


def main(distance: float | None = None, output_dir: Path | str | None = None) -> None:
    """메인 실행 함수

    Args:
        distance: 매칭 거리 임계값 (미터). None이면 기본값 사용
        output_dir: 출력 디렉토리. None이면 기본 디렉토리 사용
    """
    try:
        # 거리 설정
        distance_threshold = (
            distance if distance is not None else DEFAULT_DISTANCE_THRESHOLD
        )
        print(f"\n매칭 거리 설정: {distance_threshold}m")

        # 파이프 데이터 로드
        df_pipes = load_pipe_data()

        # 0520 지역 개별 복구 작업 데이터 로드
        df_operations = load_520_repair_operations()

        # 지정된 거리 이내 모든 파이프 고려하여 매칭
        df_all, total_operations, matched_operations = match_operations_to_pipes_v2(
            df_operations, df_pipes, distance_threshold
        )

        if matched_operations == 0:
            print("\n경고: 매칭된 데이터가 없습니다.")
            return

        # CNT_JNT 상관관계 분석 (다양한 전략)
        results = analyze_cnt_jnt_correlation_v2(df_all)

        # 출력 디렉토리 설정
        if output_dir is not None:
            output_path = (
                Path(output_dir) if isinstance(output_dir, str) else output_dir
            )
        else:
            output_path = RESULTS_DIR / "main17a_duplicate_cnt_jnt_correlation"

        # 시각화 생성 (매칭된 작업만 사용)
        df_matched = df_all[df_all["IS_MATCHED"] == True].copy()
        create_visualizations_v2(df_matched, results, output_path)

        # 결과 저장
        save_analysis_results_v2(
            df_all,
            results,
            total_operations,
            matched_operations,
            distance_threshold,
            output_path,
        )

        print("\n=== 분석 완료 ===")
        print(f"결과 파일이 {output_path}에 저장되었습니다.")

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CNT_JNT 상관관계 분석 - 매칭 거리 옵션 지원"
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=DEFAULT_DISTANCE_THRESHOLD,
        help=f"파이프 매칭 거리 임계값 (미터), 기본값: {DEFAULT_DISTANCE_THRESHOLD}m",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="결과 저장 디렉토리 (기본값: results/main17a_duplicate_cnt_jnt_correlation)",
    )

    args = parser.parse_args()
    main(distance=args.distance, output_dir=args.output_dir)
