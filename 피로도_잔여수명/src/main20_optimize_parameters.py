"""
main20_optimize_parameters.py

공간 분석 스크립트들(main21-main25)을 위한 최적 파라미터를 찾는 스크립트.
520 지역 재작업 데이터를 사용하여 공간 및 시간 파라미터를 최적화합니다.
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.spatial_utils import (
    calculate_ann_distance,
    calculate_morans_i,
    create_spatial_weights_matrix,
)

warnings.filterwarnings("ignore")


class ParameterOptimizer:
    """공간-시간 파라미터 최적화 클래스"""

    def __init__(self, gdf: gpd.GeoDataFrame, memory_limit: float = 4.0):
        """
        Parameters
        ----------
        gdf : GeoDataFrame
            520 지역 재작업 데이터
        memory_limit : float
            메모리 제한 (GB)
        """
        self.gdf = gdf
        self.memory_limit = memory_limit
        self.optimal_params = {}
        self.optimization_metrics = {}

        # 데이터 기본 통계
        self.n_points = len(gdf)
        self.extent = gdf.total_bounds
        self.area = (self.extent[2] - self.extent[0]) * (
            self.extent[3] - self.extent[1]
        )
        self.data_density = self.n_points / (self.area / 1e6) if self.area > 0 else 0

        print(f"데이터 포인트 수: {self.n_points}")
        print(f"데이터 밀도: {self.data_density:.2f} points/km²")

    def optimize_spatial_parameters(self) -> dict[str, Any]:
        """공간 파라미터 최적화 (main21용)"""
        print("\n=== 공간 파라미터 최적화 시작 ===")

        # 1. Average Nearest Neighbor (ANN) 거리 계산
        ann_distance = calculate_ann_distance(self.gdf)
        print(f"평균 최근접 이웃 거리: {ann_distance:.2f}m")

        # 2. Incremental Spatial Autocorrelation
        distances = np.arange(20, min(200, ann_distance * 10), 10)
        morans_i_values = []
        z_scores = []

        for dist in distances:
            W = create_spatial_weights_matrix(
                self.gdf, method="distance", threshold=dist, binary=True
            )

            # CNT_JNT 컬럼이 있으면 사용, 없으면 포인트 카운트 사용
            if "CNT_JNT" in self.gdf.columns:
                values = self.gdf["CNT_JNT"].fillna(0).values
            else:
                # 포인트 밀도 계산
                values = np.ones(len(self.gdf))

            I, z_score, p_value = calculate_morans_i(values, W)
            morans_i_values.append(I)
            z_scores.append(z_score)

        # 3. 최적 거리 찾기 (z-score 피크)
        optimal_idx = np.argmax(z_scores)
        optimal_distance = distances[optimal_idx]
        max_morans_i = morans_i_values[optimal_idx]

        print(f"최대 Moran's I: {max_morans_i:.3f} at {optimal_distance:.0f}m")

        # 4. Ripley's K function (간소화 버전)
        k_distances = np.arange(10, min(100, ann_distance * 5), 5)
        k_values = []

        coords = np.array([[p.x, p.y] for p in self.gdf.geometry])

        for d in k_distances:
            # 거리 d 이내의 포인트 쌍 개수
            dist_matrix = cdist(coords, coords)
            k = np.sum(dist_matrix <= d) - self.n_points  # 자기 자신 제외
            k_normalized = k / (self.n_points * (self.n_points - 1))
            k_values.append(k_normalized)

        # K function의 변화율이 최대인 지점 찾기
        k_diff = np.diff(k_values)
        if len(k_diff) > 0:
            peak_idx = np.argmax(k_diff)
            ripley_peak = k_distances[peak_idx]
        else:
            ripley_peak = ann_distance * 2

        print(f"Ripley's K 피크 거리: {ripley_peak:.2f}m")

        # 5. 최적 그리드 크기 계산
        # ANN과 Ripley's K 피크의 조화평균
        grid_size = 2.0 / (1.0 / ann_distance + 1.0 / ripley_peak)

        # 메모리 제약 고려
        estimated_cells = self.area / (grid_size**2)
        if estimated_cells > 10000:  # 너무 많은 셀
            grid_size = np.sqrt(self.area / 10000)

        # 10m 단위로 반올림
        grid_size = round(grid_size / 10) * 10
        grid_size = max(10, min(100, grid_size))  # 10-100m 범위

        # 6. k-neighbors 계산
        k_neighbors = min(int(np.sqrt(self.n_points)), 20)
        k_neighbors = max(4, k_neighbors)

        spatial_params = {
            "grid_size": int(grid_size),
            "distance_threshold": int(optimal_distance),
            "k_neighbors": k_neighbors,
        }

        self.optimization_metrics["morans_i"] = max_morans_i
        self.optimization_metrics["ann_distance"] = ann_distance

        print("\n최적 공간 파라미터:")
        print(f"  - grid_size: {spatial_params['grid_size']}m")
        print(f"  - distance_threshold: {spatial_params['distance_threshold']}m")
        print(f"  - k_neighbors: {spatial_params['k_neighbors']}")

        return spatial_params

    def optimize_temporal_parameters(self, grid_size: int) -> dict[str, Any]:
        """시간 파라미터 최적화 (main22용)"""
        print("\n=== 시간 파라미터 최적화 시작 ===")

        temporal_params = {}

        # 시간 컬럼 확인
        time_column = None
        for col in ["작업종료일", "작업일자", "date", "Date"]:
            if col in self.gdf.columns:
                time_column = col
                break

        if time_column is None:
            print("시간 정보 없음 - 기본값 사용")
            return {
                "time_interval": "1M",
                "seasonal_period": 12,
                "trend_window": 6,
                "knox_distance": 50,
                "knox_time": 30,
            }

        # 시간 데이터 파싱
        self.gdf["datetime"] = pd.to_datetime(self.gdf[time_column], errors="coerce")
        valid_dates = self.gdf.dropna(subset=["datetime"])

        if len(valid_dates) < 10:
            print("유효한 시간 데이터 부족 - 기본값 사용")
            return {
                "time_interval": "1M",
                "seasonal_period": 12,
                "trend_window": 6,
                "knox_distance": 50,
                "knox_time": 30,
            }

        # 1. 시계열 빈도 분석
        date_range = (
            valid_dates["datetime"].max() - valid_dates["datetime"].min()
        ).days

        # 데이터 빈도에 따른 시간 간격 결정
        if date_range < 30:
            time_interval = "1D"
        elif date_range < 365:
            time_interval = "1W"
        elif date_range < 365 * 2:
            time_interval = "2W"
        else:
            time_interval = "1M"

        print(f"데이터 기간: {date_range}일")
        print(f"최적 시간 간격: {time_interval}")

        # 2. 시계열 집계
        valid_dates["year_month"] = valid_dates["datetime"].dt.to_period("M")
        monthly_counts = valid_dates.groupby("year_month").size()

        if len(monthly_counts) >= 12:
            # 3. ACF 분석으로 계절성 탐지
            try:
                acf_values = acf(
                    monthly_counts.values, nlags=min(24, len(monthly_counts) // 2)
                )

                # 첫 번째 유의미한 피크 찾기
                peaks = []
                for i in range(3, len(acf_values)):
                    if (
                        acf_values[i] > acf_values[i - 1]
                        and acf_values[i] > acf_values[i + 1]
                    ):
                        if acf_values[i] > 0.2:  # 유의미한 상관관계
                            peaks.append(i)

                seasonal_period = peaks[0] if peaks else 12

            except:
                seasonal_period = 12

            # 4. STL 분해 시도
            try:
                if len(monthly_counts) >= seasonal_period * 2:
                    stl = STL(
                        monthly_counts.values,
                        seasonal=(
                            seasonal_period + 1
                            if seasonal_period % 2 == 0
                            else seasonal_period
                        ),
                    )
                    result = stl.fit()

                    # 계절성 강도 계산
                    seasonal_strength = 1 - np.var(result.resid) / np.var(
                        result.seasonal + result.resid
                    )
                    print(f"계절성 강도: {seasonal_strength:.3f}")

                    if seasonal_strength < 0.3:
                        seasonal_period = 12  # 계절성이 약하면 기본값
            except:
                pass
        else:
            seasonal_period = 12

        print(f"최적 계절 주기: {seasonal_period}개월")

        # 5. Knox test 파라미터
        # 공간: grid_size의 1.5-2배
        knox_distance = int(grid_size * 1.5)

        # 시간: 평균 이벤트 간격 고려
        if len(valid_dates) > 1:
            time_diffs = valid_dates["datetime"].sort_values().diff().dropna()
            mean_interval = time_diffs.mean().days
            knox_time = min(max(7, mean_interval), 60)  # 7-60일 범위
        else:
            knox_time = 30

        temporal_params = {
            "time_interval": time_interval,
            "seasonal_period": int(seasonal_period),
            "trend_window": max(3, int(seasonal_period // 2)),
            "knox_distance": knox_distance,
            "knox_time": int(knox_time),
        }

        print("\n최적 시간 파라미터:")
        for key, value in temporal_params.items():
            print(f"  - {key}: {value}")

        return temporal_params

    def optimize_emerging_parameters(self, time_interval: str) -> dict[str, Any]:
        """Emerging hotspot 파라미터 최적화 (main23용)"""
        print("\n=== Emerging Hotspot 파라미터 최적화 시작 ===")

        # 데이터 기간 고려
        if "datetime" in self.gdf.columns:
            date_range = (self.gdf["datetime"].max() - self.gdf["datetime"].min()).days

            # lookback 기간 설정
            if date_range < 180:
                lookback_months = 3
            elif date_range < 365:
                lookback_months = 6
            elif date_range < 365 * 2:
                lookback_months = 12
            else:
                lookback_months = min(24, date_range // 60)

            # 최소 관측 수
            if time_interval == "1D":
                min_observations = 7
            elif time_interval == "1W":
                min_observations = 4
            else:
                min_observations = 3
        else:
            lookback_months = 6
            min_observations = 3

        emerging_params = {
            "lookback_months": int(lookback_months),
            "min_observations": min_observations,
            "trend_threshold": 0.1,
        }

        print("\n최적 Emerging 파라미터:")
        for key, value in emerging_params.items():
            print(f"  - {key}: {value}")

        return emerging_params

    def cross_validate_parameters(self, params: dict[str, Any]) -> float:
        """파라미터 교차 검증"""
        print("\n=== 파라미터 교차 검증 ===")

        # Leave-One-Out 또는 k-fold 교차검증
        n_folds = min(5, self.n_points // 10)

        if n_folds < 2:
            print("데이터 부족으로 교차 검증 생략")
            return 0.0

        scores = []

        for fold in range(n_folds):
            # 폴드 분할
            test_mask = np.zeros(self.n_points, dtype=bool)
            test_mask[fold::n_folds] = True

            train_gdf = self.gdf[~test_mask]
            test_gdf = self.gdf[test_mask]

            if len(train_gdf) < 10 or len(test_gdf) < 2:
                continue

            # 훈련 데이터로 Moran's I 계산
            W_train = create_spatial_weights_matrix(
                train_gdf,
                method="distance",
                threshold=params.get("distance_threshold", 100),
                binary=True,
            )

            if "CNT_JNT" in train_gdf.columns:
                values = train_gdf["CNT_JNT"].fillna(0).values
            else:
                values = np.ones(len(train_gdf))

            I, _, _ = calculate_morans_i(values, W_train)
            scores.append(I)

        if scores:
            cv_score = np.mean(scores)
            cv_std = np.std(scores)
            print(f"교차 검증 점수: {cv_score:.3f} ± {cv_std:.3f}")
            return cv_score

        return 0.0

    def optimize_integrated(self) -> dict[str, Any]:
        """통합 최적화"""
        print("\n" + "=" * 50)
        print("통합 파라미터 최적화 시작")
        print("=" * 50)

        # 1. 공간 파라미터 최적화
        spatial_params = self.optimize_spatial_parameters()

        # 2. 공통 grid_size 사용
        grid_size = spatial_params["grid_size"]

        # 3. 시간 파라미터 최적화
        temporal_params = self.optimize_temporal_parameters(grid_size)

        # 4. Emerging 파라미터 최적화
        emerging_params = self.optimize_emerging_parameters(
            temporal_params["time_interval"]
        )

        # 5. 교차 검증
        cv_score = self.cross_validate_parameters(spatial_params)

        # 6. 통합 결과
        return {
            "shared": {
                "grid_size": grid_size,
                "data_density": round(self.data_density, 2),
                "analysis_extent": self.extent.tolist(),
            },
            "main21": {
                "grid_size": grid_size,
                "distance_threshold": spatial_params["distance_threshold"],
                "k_neighbors": spatial_params["k_neighbors"],
            },
            "main22": {
                "grid_size": grid_size,
                "time_interval": temporal_params["time_interval"],
                "seasonal_period": temporal_params["seasonal_period"],
                "trend_window": temporal_params["trend_window"],
                "knox_distance": temporal_params["knox_distance"],
                "knox_time": temporal_params["knox_time"],
            },
            "main23": emerging_params,
            "optimization_metrics": {
                "morans_i": round(self.optimization_metrics.get("morans_i", 0), 3),
                "cross_validation_score": round(cv_score, 3),
                "n_points": self.n_points,
                "optimization_date": datetime.now().isoformat(),
            },
        }


def load_repair_data() -> gpd.GeoDataFrame:
    """520 지역 재작업 데이터 로드"""

    # 가능한 파일 경로들
    possible_files = [
        "data/520_area/repairs_with_location_520_v3.csv",
        "data/520_area/duplicate_repairs_520.csv",
        "data/520_area/repairs_520.csv",
        "results/repairs_with_location_520.csv",
    ]

    for file_path in possible_files:
        if os.path.exists(file_path):
            print(f"데이터 로드: {file_path}")
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            # 좌표 컬럼 확인
            if "x" in df.columns and "y" in df.columns:
                # GeoDataFrame 생성
                geometry = gpd.points_from_xy(df["x"], df["y"])
                gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:5186")

                # 유효한 좌표만 필터링
                gdf = gdf[(gdf["x"] > 0) & (gdf["y"] > 0)]

                print(f"로드된 데이터: {len(gdf)} 포인트")
                return gdf
            print(f"좌표 컬럼 없음: {file_path}")

    raise FileNotFoundError("520 지역 재작업 데이터 파일을 찾을 수 없습니다.")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="공간 분석 스크립트를 위한 최적 파라미터 탐색"
    )
    parser.add_argument(
        "--method",
        choices=["spatial", "temporal", "integrated", "all"],
        default="all",
        help="최적화 방법",
    )
    parser.add_argument(
        "--target",
        choices=["main21", "main22", "main23", "all"],
        default="all",
        help="대상 스크립트",
    )
    parser.add_argument(
        "--output",
        default="results/spatial_analysis/optimal_parameters.json",
        help="결과 저장 경로",
    )
    parser.add_argument(
        "--memory-limit", type=float, default=4.0, help="메모리 제한 (GB)"
    )

    args = parser.parse_args()

    # 로깅 설정
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    try:
        # 데이터 로드
        gdf = load_repair_data()

        # 최적화 실행
        optimizer = ParameterOptimizer(gdf, memory_limit=args.memory_limit)

        if args.method == "all" or args.method == "integrated":
            optimal_params = optimizer.optimize_integrated()
        elif args.method == "spatial":
            optimal_params = {"main21": optimizer.optimize_spatial_parameters()}
        elif args.method == "temporal":
            grid_size = 30  # 기본값
            optimal_params = {
                "main22": optimizer.optimize_temporal_parameters(grid_size)
            }
        else:
            optimal_params = {}

        # 결과 저장
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(optimal_params, f, ensure_ascii=False, indent=2)

        print(f"\n최적 파라미터가 저장되었습니다: {output_path}")

        # 결과 출력
        print("\n" + "=" * 50)
        print("최적화 결과 요약")
        print("=" * 50)
        print(json.dumps(optimal_params, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
