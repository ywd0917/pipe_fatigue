"""
main22_spacetime_cube.py

시공간 큐브 분석을 통한 재작업 패턴의 시계열 분석.
계절성, 트렌드, Knox test 등을 수행합니다.
"""

import argparse
import json
import os
import pickle
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf, pacf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.config import FATIGUE_PIPE_LM_CSV
from src.common.korean_font_utils import setup_korean_font
from src.common.spatial_utils import create_spacetime_grid

warnings.filterwarnings("ignore")


class SpaceTimeCubeAnalyzer:
    """시공간 큐브 분석 클래스"""

    def __init__(self, gdf: gpd.GeoDataFrame, params: dict[str, Any]):
        """
        Parameters
        ----------
        gdf : GeoDataFrame
            520 지역 재작업 데이터 (시간 정보 포함)
        params : dict
            분석 파라미터
        """
        self.gdf = gdf
        self.params = params
        self.spacetime_cube = None
        self.time_series = None
        self.seasonal_decomposition = None
        self.trend_results = None
        self.knox_results = None
        self.cnt_jnt_timeseries = None  # CNT_JNT 시계열 분석 결과
        self.cnt_jnt_seasonal = None  # CNT_JNT 계절성 분석 결과

        # 한글 폰트 설정
        setup_korean_font()

        # 시간 컬럼 확인 및 파싱
        self._prepare_temporal_data()

    def _prepare_temporal_data(self):
        """시간 데이터 준비"""
        # 시간 컬럼 찾기
        time_column = None
        for col in ["작업종료일", "작업일자", "date", "Date"]:
            if col in self.gdf.columns:
                time_column = col
                break

        if time_column is None:
            raise ValueError("시간 정보를 포함한 컬럼을 찾을 수 없습니다.")

        # datetime으로 변환 (YYYYMMDDHHMM 형식 처리)
        if time_column == "작업종료일":
            # 숫자 형식의 날짜를 문자열로 변환 후 파싱
            self.gdf["datetime"] = pd.to_datetime(
                self.gdf[time_column].astype(str).str[:8],
                format="%Y%m%d",
                errors="coerce",
            )
        else:
            self.gdf["datetime"] = pd.to_datetime(
                self.gdf[time_column], errors="coerce"
            )

        # 유효한 날짜만 필터링
        valid_mask = ~self.gdf["datetime"].isna()
        self.gdf = self.gdf[valid_mask].copy()

        if len(self.gdf) == 0:
            raise ValueError("유효한 시간 데이터가 없습니다.")

        print(f"시간 데이터 준비 완료: {len(self.gdf)} 포인트")
        print(f"기간: {self.gdf['datetime'].min()} ~ {self.gdf['datetime'].max()}")

    def create_spacetime_cube(self) -> gpd.GeoDataFrame:
        """시공간 큐브 생성"""
        print("\n시공간 큐브 생성 중...")
        print(f"  - 공간: {self.params['grid_size']}m × {self.params['grid_size']}m")
        print(f"  - 시간: {self.params['time_interval']} 간격")

        # 시공간 그리드 생성
        self.spacetime_cube = create_spacetime_grid(
            self.gdf,
            grid_size=self.params["grid_size"],
            time_column="datetime",
            time_interval=self.params["time_interval"],
        )

        # 추가 통계 계산
        for idx, cell in self.spacetime_cube.iterrows():
            # 해당 시공간 셀의 포인트 찾기
            points_in_cell = self.gdf[self.gdf.geometry.within(cell.geometry)]

            if not points_in_cell.empty:
                # 시간 필터
                time_end = (
                    cell["time_bin"] + pd.DateOffset(months=1)
                    if self.params["time_interval"] == "1M"
                    else cell["time_bin"] + pd.Timedelta(self.params["time_interval"])
                )

                points_in_time = points_in_cell[
                    (points_in_cell["datetime"] >= cell["time_bin"])
                    & (points_in_cell["datetime"] < time_end)
                ]

                # CNT_JNT 통계
                if "CNT_JNT" in self.gdf.columns and len(points_in_time) > 0:
                    cnt_jnt = points_in_time["CNT_JNT"].dropna()
                    if len(cnt_jnt) > 0:
                        self.spacetime_cube.at[idx, "mean_cnt_jnt"] = cnt_jnt.mean()
                        self.spacetime_cube.at[idx, "sum_cnt_jnt"] = cnt_jnt.sum()
                        self.spacetime_cube.at[idx, "max_cnt_jnt"] = cnt_jnt.max()

                # K-factors 통계 (최대값/최소값 모두 처리)
                for k_factor in [
                    "K_total",
                    "K_age",
                    "K_soil",
                    "K_traffic",
                    "K_stress",
                    "D_final",
                    "0520_D_final",
                ]:
                    # 기본 컬럼
                    if k_factor in self.gdf.columns and len(points_in_time) > 0:
                        values = points_in_time[k_factor].dropna()
                        if len(values) > 0:
                            self.spacetime_cube.at[idx, f"mean_{k_factor}"] = (
                                values.mean()
                            )

                    # 최대값 컬럼
                    max_col = f"{k_factor}_max"
                    if max_col in self.gdf.columns and len(points_in_time) > 0:
                        max_values = points_in_time[max_col].dropna()
                        if len(max_values) > 0:
                            self.spacetime_cube.at[idx, f"max_{k_factor}"] = (
                                max_values.max()
                            )
                            self.spacetime_cube.at[idx, f"mean_max_{k_factor}"] = (
                                max_values.mean()
                            )

                    # 최소값 컬럼
                    min_col = f"{k_factor}_min"
                    if min_col in self.gdf.columns and len(points_in_time) > 0:
                        min_values = points_in_time[min_col].dropna()
                        if len(min_values) > 0:
                            self.spacetime_cube.at[idx, f"min_{k_factor}"] = (
                                min_values.min()
                            )
                            self.spacetime_cube.at[idx, f"mean_min_{k_factor}"] = (
                                min_values.mean()
                            )

        print(f"생성된 시공간 셀: {len(self.spacetime_cube)}개")

        # 시계열 집계
        self.time_series = (
            self.spacetime_cube.groupby("time_bin")
            .agg(
                {
                    "point_count": "sum",
                    "mean_cnt_jnt": (
                        "mean"
                        if "mean_cnt_jnt" in self.spacetime_cube.columns
                        else lambda x: 0
                    ),
                }
            )
            .sort_index()
        )

        print(f"시계열 길이: {len(self.time_series)} 시점")

        return self.spacetime_cube

    def perform_seasonal_decomposition(self) -> dict[str, Any]:
        """계절성 분해 (STL)"""
        print("\n계절성 분해 수행 중...")

        if len(self.time_series) < self.params["seasonal_period"] * 2:
            print("데이터 부족으로 계절성 분해 불가")
            return {}

        # STL 분해
        try:
            stl = STL(
                self.time_series["point_count"].values,
                seasonal=(
                    self.params["seasonal_period"] + 1
                    if self.params["seasonal_period"] % 2 == 0
                    else self.params["seasonal_period"]
                ),
            )
            result = stl.fit()

            self.seasonal_decomposition = {
                "observed": result.observed,
                "trend": result.trend,
                "seasonal": result.seasonal,
                "resid": result.resid,
            }

            # 계절성 강도 계산
            seasonal_strength = 1 - np.var(result.resid) / np.var(
                result.seasonal + result.resid
            )
            trend_strength = 1 - np.var(result.resid) / np.var(
                result.trend + result.resid
            )

            print(f"계절성 강도: {seasonal_strength:.3f}")
            print(f"트렌드 강도: {trend_strength:.3f}")

            return {
                "seasonal_strength": seasonal_strength,
                "trend_strength": trend_strength,
                "decomposition": self.seasonal_decomposition,
            }

        except Exception as e:
            print(f"STL 분해 실패: {e}")
            return {}

    def perform_trend_analysis(self) -> dict[str, Any]:
        """트렌드 분석 (Mann-Kendall test)"""
        print("\n트렌드 분석 수행 중...")

        # Mann-Kendall 트렌드 테스트
        def mann_kendall_test(x):
            n = len(x)
            s = 0

            for i in range(n - 1):
                for j in range(i + 1, n):
                    s += np.sign(x[j] - x[i])

            # 분산 계산
            var_s = n * (n - 1) * (2 * n + 5) / 18

            # Z-score
            if s > 0:
                z = (s - 1) / np.sqrt(var_s)
            elif s < 0:
                z = (s + 1) / np.sqrt(var_s)
            else:
                z = 0

            # p-value
            p_value = 2 * (1 - stats.norm.cdf(abs(z)))

            return s, z, p_value

        values = self.time_series["point_count"].values
        s, z, p_value = mann_kendall_test(values)

        # Sen's slope 추정
        n = len(values)
        slopes = []
        for i in range(n - 1):
            for j in range(i + 1, n):
                if j - i > 0:
                    slopes.append((values[j] - values[i]) / (j - i))

        sen_slope = np.median(slopes) if slopes else 0

        self.trend_results = {
            "mann_kendall_s": s,
            "mann_kendall_z": z,
            "mann_kendall_p": p_value,
            "sen_slope": sen_slope,
            "trend_direction": (
                "increasing" if z > 0 else ("decreasing" if z < 0 else "no trend")
            ),
            "significant": p_value < 0.05,
        }

        print(f"Mann-Kendall Z: {z:.3f} (p={p_value:.3f})")
        print(f"Sen's slope: {sen_slope:.3f}")
        print(f"트렌드: {self.trend_results['trend_direction']}")

        return self.trend_results

    def perform_knox_test(self) -> dict[str, Any]:
        """Knox test for space-time clustering"""
        print("\n시공간 군집 검정 (Knox test) 수행 중...")

        # 시공간 거리 계산
        coords = np.array([[p.x, p.y] for p in self.gdf.geometry])
        times = self.gdf["datetime"].values

        n = len(self.gdf)

        # 샘플링 (데이터가 너무 많으면)
        if n > 1000:
            sample_idx = np.random.choice(n, 1000, replace=False)
            coords = coords[sample_idx]
            times = times[sample_idx]
            n = 1000

        # Knox statistic 계산
        knox_count = 0
        total_pairs = 0

        for i in range(n - 1):
            for j in range(i + 1, n):
                # 공간 거리
                spatial_dist = np.sqrt(
                    (coords[i, 0] - coords[j, 0]) ** 2
                    + (coords[i, 1] - coords[j, 1]) ** 2
                )

                # 시간 거리 (일 단위)
                time_dist = abs((times[j] - times[i]) / np.timedelta64(1, "D"))

                # Knox criterion
                if (
                    spatial_dist <= self.params["knox_distance"]
                    and time_dist <= self.params["knox_time"]
                ):
                    knox_count += 1

                total_pairs += 1

        # 기댓값과 분산 (무작위 가정)
        p_space = np.sum(
            np.linalg.norm(coords[:, None] - coords, axis=2)
            <= self.params["knox_distance"]
        ) / (n * (n - 1))
        p_time = np.sum(
            np.abs(times[:, None] - times)
            <= np.timedelta64(self.params["knox_time"], "D")
        ) / (n * (n - 1))

        expected = total_pairs * p_space * p_time
        variance = expected * (1 - p_space * p_time)

        # Z-score
        if variance > 0:
            z_score = (knox_count - expected) / np.sqrt(variance)
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        else:
            z_score = 0
            p_value = 1

        self.knox_results = {
            "knox_statistic": knox_count,
            "expected": expected,
            "z_score": z_score,
            "p_value": p_value,
            "space_threshold": self.params["knox_distance"],
            "time_threshold": self.params["knox_time"],
            "significant_clustering": p_value < 0.05,
        }

        print(f"Knox statistic: {knox_count} (기댓값: {expected:.1f})")
        print(f"Z-score: {z_score:.3f} (p={p_value:.3f})")

        if p_value < 0.05:
            print("→ 유의미한 시공간 군집 발견")
        else:
            print("→ 시공간 군집 없음")

        return self.knox_results

    def analyze_cnt_jnt_temporal_patterns(self) -> dict[str, Any]:
        """CNT_JNT 시계열 패턴 분석 (Phase 3.2)"""
        if "mean_cnt_jnt" not in self.spacetime_cube.columns:
            print("\nCNT_JNT 데이터 없음 - 분석 건너뜀")
            return {}

        print("\n=== CNT_JNT 시계열 패턴 분석 (Phase 3.2) ===")

        # 1. 월별 CNT_JNT 평균값 추적
        print("\n1. 월별 CNT_JNT 평균값 추적...")
        monthly_cnt_jnt = self.spacetime_cube.groupby("time_bin")["mean_cnt_jnt"].mean()
        monthly_max = (
            self.spacetime_cube.groupby("time_bin")["max_cnt_jnt"].max()
            if "max_cnt_jnt" in self.spacetime_cube.columns
            else pd.Series()
        )
        monthly_sum = (
            self.spacetime_cube.groupby("time_bin")["sum_cnt_jnt"].sum()
            if "sum_cnt_jnt" in self.spacetime_cube.columns
            else pd.Series()
        )

        # 2. 높은 CNT_JNT 지역의 시간적 변화 분석
        print("\n2. 높은 CNT_JNT 지역(상위 25%)의 시간적 변화 분석...")
        high_cnt_threshold = self.spacetime_cube["mean_cnt_jnt"].quantile(0.75)
        high_cnt_areas = self.spacetime_cube[
            self.spacetime_cube["mean_cnt_jnt"] > high_cnt_threshold
        ]
        high_cnt_timeseries = high_cnt_areas.groupby("time_bin")["mean_cnt_jnt"].mean()

        # 3. 계절별 CNT_JNT 패턴 식별
        print("\n3. 계절별 CNT_JNT 패턴 식별...")
        self.spacetime_cube["month"] = pd.to_datetime(
            self.spacetime_cube["time_bin"]
        ).dt.month
        self.spacetime_cube["season"] = self.spacetime_cube["month"].apply(
            lambda x: (
                "Spring"
                if 3 <= x <= 5
                else "Summer" if 6 <= x <= 8 else "Fall" if 9 <= x <= 11 else "Winter"
            )
        )
        seasonal_patterns = self.spacetime_cube.groupby("season")["mean_cnt_jnt"].agg(
            ["mean", "std", "min", "max"]
        )

        # 4. 시계열 통계
        results = {
            "monthly_stats": {
                "mean": {str(k): v for k, v in monthly_cnt_jnt.to_dict().items()},
                "max": (
                    {str(k): v for k, v in monthly_max.to_dict().items()}
                    if len(monthly_max) > 0
                    else {}
                ),
                "sum": (
                    {str(k): v for k, v in monthly_sum.to_dict().items()}
                    if len(monthly_sum) > 0
                    else {}
                ),
                "overall_mean": float(monthly_cnt_jnt.mean()),
                "overall_std": float(monthly_cnt_jnt.std()),
                "trend": (
                    "increasing"
                    if monthly_cnt_jnt.iloc[-6:].mean()
                    > monthly_cnt_jnt.iloc[:6].mean()
                    else "decreasing"
                ),
            },
            "high_cnt_areas": {
                "threshold": float(high_cnt_threshold),
                "count": len(high_cnt_areas),
                "timeseries": (
                    {str(k): v for k, v in high_cnt_timeseries.to_dict().items()}
                    if len(high_cnt_timeseries) > 0
                    else {}
                ),
                "volatility": (
                    float(high_cnt_timeseries.std())
                    if len(high_cnt_timeseries) > 0
                    else 0
                ),
            },
            "seasonal_patterns": (
                seasonal_patterns.to_dict() if len(seasonal_patterns) > 0 else {}
            ),
            "temporal_correlation": {},
        }

        # 5. 자기상관 분석 (시계열 의존성)
        if len(monthly_cnt_jnt) > 10:
            print("\n4. 자기상관 분석 수행...")
            acf_values = acf(
                monthly_cnt_jnt.dropna().values,
                nlags=min(12, len(monthly_cnt_jnt) // 2),
            )
            pacf_values = pacf(
                monthly_cnt_jnt.dropna().values,
                nlags=min(12, len(monthly_cnt_jnt) // 2),
            )

            # Ljung-Box test
            lb_test = acorr_ljungbox(
                monthly_cnt_jnt.dropna().values, lags=10, return_df=True
            )

            results["temporal_correlation"] = {
                "acf": acf_values.tolist(),
                "pacf": pacf_values.tolist(),
                "ljung_box": {
                    "statistic": lb_test["lb_stat"].values.tolist(),
                    "p_value": lb_test["lb_pvalue"].values.tolist(),
                    "significant": bool((lb_test["lb_pvalue"] < 0.05).any()),
                },
            }

        # 결과 출력
        print(f"\n평균 CNT_JNT: {results['monthly_stats']['overall_mean']:.2f}")
        print(f"CNT_JNT 표준편차: {results['monthly_stats']['overall_std']:.2f}")
        print(f"트렌드: {results['monthly_stats']['trend']}")
        print(f"높은 CNT_JNT 지역 수: {results['high_cnt_areas']['count']}")

        if seasonal_patterns.shape[0] > 0:
            print("\n계절별 CNT_JNT 평균:")
            for season in seasonal_patterns.index:
                print(f"  {season}: {seasonal_patterns.loc[season, 'mean']:.2f}")

        self.cnt_jnt_timeseries = results
        return results

    def analyze_cnt_jnt_arima_forecast(self) -> dict[str, Any]:
        """CNT_JNT ARIMA 모델링 및 예측 (Phase 3.2.4)"""
        if (
            self.cnt_jnt_timeseries is None
            or "monthly_stats" not in self.cnt_jnt_timeseries
        ):
            print("\nCNT_JNT 시계열 데이터 없음 - ARIMA 분석 건너뜀")
            return {}

        print("\n5. ARIMA 모델링 및 예측...")

        # 월별 평균 데이터 준비
        monthly_data = pd.Series(self.cnt_jnt_timeseries["monthly_stats"]["mean"])

        if len(monthly_data) < 12:
            print("데이터가 너무 적음 (최소 12개월 필요)")
            return {}

        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.stattools import adfuller

            # 정상성 검정 (ADF test)
            adf_result = adfuller(monthly_data.dropna())

            # ARIMA 모델 파라미터 선택 (간단한 방법)
            # 실제로는 auto_arima 등을 사용하는 것이 좋음
            best_aic = np.inf
            best_order = (0, 0, 0)

            for p in range(3):
                for d in range(2):
                    for q in range(3):
                        try:
                            model = ARIMA(monthly_data.dropna(), order=(p, d, q))
                            fitted = model.fit()
                            if fitted.aic < best_aic:
                                best_aic = fitted.aic
                                best_order = (p, d, q)
                        except:
                            continue

            # 최적 모델로 예측
            model = ARIMA(monthly_data.dropna(), order=best_order)
            fitted = model.fit()

            # 6개월 예측
            forecast = fitted.forecast(steps=6)

            results = {
                "adf_test": {
                    "statistic": float(adf_result[0]),
                    "p_value": float(adf_result[1]),
                    "is_stationary": adf_result[1] < 0.05,
                },
                "best_order": best_order,
                "aic": float(best_aic),
                "forecast_6months": forecast.tolist(),
                "model_summary": str(fitted.summary()),
            }

            print(
                f"ADF 검정: p={adf_result[1]:.4f} ({'정상' if adf_result[1] < 0.05 else '비정상'})"
            )
            print(f"최적 ARIMA 모델: {best_order}")
            print(f"6개월 예측 평균: {np.mean(forecast):.2f}")

            return results

        except Exception as e:
            print(f"ARIMA 분석 실패: {e}")
            return {}

    def analyze_kfactors_dfinal_temporal_patterns(self) -> dict[str, Any]:
        """K-factors/D_final 시계열 패턴 분석 (Phase 3.3) - 최대값/최소값 분석 포함"""
        print("\n=== K-factors/D_final 시계열 패턴 분석 (Phase 3.3) ===")

        # K-factors 컬럼 확인
        kfactor_cols = [
            "K_total",
            "K_age",
            "K_soil",
            "K_traffic",
            "K_stress",
            "D_final",
            "0520_D_final",
        ]

        # 사용 가능한 컬럼 찾기 (mean, max, min)
        available_cols = []
        available_types = {}

        for col in kfactor_cols:
            types = []
            if f"mean_{col}" in self.spacetime_cube.columns:
                types.append("mean")
            if f"max_{col}" in self.spacetime_cube.columns:
                types.append("max")
            if f"min_{col}" in self.spacetime_cube.columns:
                types.append("min")

            if types:
                available_cols.append(col)
                available_types[col] = types

        if not available_cols:
            print("\nK-factors/D_final 데이터 없음 - 분석 건너뜀")
            return {}

        print(f"사용 가능한 K-factors: {available_cols}")
        for col in available_cols[:3]:  # 처음 3개만 출력
            print(f"  {col}: {', '.join(available_types[col])} 값 사용 가능")

        results = {
            "monthly_stats": {},
            "monthly_stats_max": {},
            "monthly_stats_min": {},
            "seasonal_patterns": {},
            "temporal_correlation": {},
            "composite_score": {},
            "composite_score_max": {},
            "composite_score_min": {},
            "risk_evolution": {},
        }

        # 1. 각 K-factor별 월별 통계 (mean, max, min)
        print("\n1. K-factors/D_final 월별 통계 계산...")
        for factor in available_cols:
            # Mean 값 통계
            mean_col = f"mean_{factor}"
            if mean_col in self.spacetime_cube.columns:
                monthly_mean = self.spacetime_cube.groupby("time_bin")[mean_col].mean()
                monthly_std = self.spacetime_cube.groupby("time_bin")[mean_col].std()

                results["monthly_stats"][factor] = {
                    "mean": {str(k): v for k, v in monthly_mean.to_dict().items()},
                    "std": {str(k): v for k, v in monthly_std.to_dict().items()},
                    "overall_mean": float(monthly_mean.mean()),
                    "overall_std": float(monthly_mean.std()),
                    "trend": (
                        "increasing"
                        if monthly_mean.iloc[-6:].mean() > monthly_mean.iloc[:6].mean()
                        else "decreasing"
                    ),
                }

                print(
                    f"  {factor} (평균): 평균={results['monthly_stats'][factor]['overall_mean']:.4f}, "
                    f"트렌드={results['monthly_stats'][factor]['trend']}"
                )

            # Max 값 통계
            max_col = f"max_{factor}"
            if max_col in self.spacetime_cube.columns:
                monthly_max = self.spacetime_cube.groupby("time_bin")[max_col].max()

                results["monthly_stats_max"][factor] = {
                    "max": {str(k): v for k, v in monthly_max.to_dict().items()},
                    "overall_max": float(monthly_max.max()),
                    "overall_mean": float(monthly_max.mean()),
                    "trend": (
                        "increasing"
                        if monthly_max.iloc[-6:].mean() > monthly_max.iloc[:6].mean()
                        else "decreasing"
                    ),
                }

                print(
                    f"  {factor} (최대): 최대={results['monthly_stats_max'][factor]['overall_max']:.4f}, "
                    f"트렌드={results['monthly_stats_max'][factor]['trend']}"
                )

            # Min 값 통계
            min_col = f"min_{factor}"
            if min_col in self.spacetime_cube.columns:
                monthly_min = self.spacetime_cube.groupby("time_bin")[min_col].min()

                results["monthly_stats_min"][factor] = {
                    "min": {str(k): v for k, v in monthly_min.to_dict().items()},
                    "overall_min": float(monthly_min.min()),
                    "overall_mean": float(monthly_min.mean()),
                    "trend": (
                        "increasing"
                        if monthly_min.iloc[-6:].mean() > monthly_min.iloc[:6].mean()
                        else "decreasing"
                    ),
                }

                print(
                    f"  {factor} (최소): 최소={results['monthly_stats_min'][factor]['overall_min']:.4f}, "
                    f"트렌드={results['monthly_stats_min'][factor]['trend']}"
                )

        # 2. K_total × D_final 통합 점수 계산 (최대값/최소값 포함)
        print("\n2. K-factors/D_final 통합 점수 (K_total × D_final) 계산...")

        # Mean 기반 통합 점수
        if "mean_K_total" in self.spacetime_cube.columns and any(
            col in ["mean_D_final", "mean_0520_D_final"]
            for col in self.spacetime_cube.columns
        ):
            d_final_col = (
                "mean_D_final"
                if "mean_D_final" in self.spacetime_cube.columns
                else "mean_0520_D_final"
            )

            # 통합 점수 계산
            self.spacetime_cube["kfactors_dfinal_score"] = (
                self.spacetime_cube["mean_K_total"] * self.spacetime_cube[d_final_col]
            )

            # 월별 통합 점수
            monthly_composite = self.spacetime_cube.groupby("time_bin")[
                "kfactors_dfinal_score"
            ].agg(["mean", "max", "std"])

            results["composite_score"] = {
                "monthly_mean": {
                    str(k): v for k, v in monthly_composite["mean"].to_dict().items()
                },
                "monthly_max": {
                    str(k): v for k, v in monthly_composite["max"].to_dict().items()
                },
                "monthly_std": {
                    str(k): v for k, v in monthly_composite["std"].to_dict().items()
                },
                "overall_mean": float(monthly_composite["mean"].mean()),
                "overall_max": float(monthly_composite["max"].max()),
                "trend": (
                    "increasing"
                    if monthly_composite["mean"].iloc[-6:].mean()
                    > monthly_composite["mean"].iloc[:6].mean()
                    else "decreasing"
                ),
            }

            print(
                f"  통합 점수 (평균): 평균={results['composite_score']['overall_mean']:.6f}, "
                f"최대={results['composite_score']['overall_max']:.6f}, "
                f"트렌드={results['composite_score']['trend']}"
            )

        # Max 기반 통합 점수
        if "max_K_total" in self.spacetime_cube.columns and any(
            col in ["max_D_final", "max_0520_D_final"]
            for col in self.spacetime_cube.columns
        ):
            d_final_max_col = (
                "max_D_final"
                if "max_D_final" in self.spacetime_cube.columns
                else "max_0520_D_final"
            )

            # 최대값 통합 점수 계산
            self.spacetime_cube["kfactors_dfinal_score_max"] = (
                self.spacetime_cube["max_K_total"]
                * self.spacetime_cube[d_final_max_col]
            )

            # 월별 최대값 통합 점수
            monthly_composite_max = self.spacetime_cube.groupby("time_bin")[
                "kfactors_dfinal_score_max"
            ].agg(["mean", "max"])

            results["composite_score_max"] = {
                "monthly_max": {
                    str(k): v for k, v in monthly_composite_max["max"].to_dict().items()
                },
                "overall_max": float(monthly_composite_max["max"].max()),
                "overall_mean": float(monthly_composite_max["mean"].mean()),
                "trend": (
                    "increasing"
                    if monthly_composite_max["mean"].iloc[-6:].mean()
                    > monthly_composite_max["mean"].iloc[:6].mean()
                    else "decreasing"
                ),
            }

            print(
                f"  통합 점수 (최대): 최대={results['composite_score_max']['overall_max']:.6f}, "
                f"평균={results['composite_score_max']['overall_mean']:.6f}, "
                f"트렌드={results['composite_score_max']['trend']}"
            )

        # Min 기반 통합 점수
        if "min_K_total" in self.spacetime_cube.columns and any(
            col in ["min_D_final", "min_0520_D_final"]
            for col in self.spacetime_cube.columns
        ):
            d_final_min_col = (
                "min_D_final"
                if "min_D_final" in self.spacetime_cube.columns
                else "min_0520_D_final"
            )

            # 최소값 통합 점수 계산
            self.spacetime_cube["kfactors_dfinal_score_min"] = (
                self.spacetime_cube["min_K_total"]
                * self.spacetime_cube[d_final_min_col]
            )

            # 월별 최소값 통합 점수
            monthly_composite_min = self.spacetime_cube.groupby("time_bin")[
                "kfactors_dfinal_score_min"
            ].agg(["mean", "min"])

            results["composite_score_min"] = {
                "monthly_min": {
                    str(k): v for k, v in monthly_composite_min["min"].to_dict().items()
                },
                "overall_min": float(monthly_composite_min["min"].min()),
                "overall_mean": float(monthly_composite_min["mean"].mean()),
                "trend": (
                    "increasing"
                    if monthly_composite_min["mean"].iloc[-6:].mean()
                    > monthly_composite_min["mean"].iloc[:6].mean()
                    else "decreasing"
                ),
            }

            print(
                f"  통합 점수 (최소): 최소={results['composite_score_min']['overall_min']:.6f}, "
                f"평균={results['composite_score_min']['overall_mean']:.6f}, "
                f"트렌드={results['composite_score_min']['trend']}"
            )

        # 3. 계절별 K-factors/D_final 패턴
        print("\n3. 계절별 K-factors/D_final 패턴 분석...")
        if "season" not in self.spacetime_cube.columns:
            self.spacetime_cube["month"] = pd.to_datetime(
                self.spacetime_cube["time_bin"]
            ).dt.month
            self.spacetime_cube["season"] = self.spacetime_cube["month"].apply(
                lambda x: (
                    "Spring"
                    if 3 <= x <= 5
                    else (
                        "Summer"
                        if 6 <= x <= 8
                        else "Fall" if 9 <= x <= 11 else "Winter"
                    )
                )
            )

        for factor in available_cols:
            mean_col = f"mean_{factor}"
            if mean_col in self.spacetime_cube.columns:
                seasonal = self.spacetime_cube.groupby("season")[mean_col].agg(
                    ["mean", "std", "min", "max"]
                )
                results["seasonal_patterns"][factor] = seasonal.to_dict()

                # 가장 높은 계절 찾기
                highest_season = seasonal["mean"].idxmax()
                print(
                    f"  {factor}: 최고 계절={highest_season} ({seasonal.loc[highest_season, 'mean']:.4f})"
                )

        # 4. 고위험 지역 진화 추적
        print("\n4. 고위험 지역 (상위 10%) 진화 추적...")
        if "kfactors_dfinal_score" in self.spacetime_cube.columns:
            # 고위험 임계값
            high_risk_threshold = self.spacetime_cube["kfactors_dfinal_score"].quantile(
                0.9
            )

            # 시간별 고위험 지역 수
            time_bins = self.spacetime_cube["time_bin"].unique()
            high_risk_evolution = []

            for time_bin in sorted(time_bins):
                time_data = self.spacetime_cube[
                    self.spacetime_cube["time_bin"] == time_bin
                ]
                high_risk_count = (
                    time_data["kfactors_dfinal_score"] > high_risk_threshold
                ).sum()
                high_risk_evolution.append(
                    {
                        "time": str(time_bin),
                        "count": int(high_risk_count),
                        "mean_score": (
                            float(
                                time_data[
                                    time_data["kfactors_dfinal_score"]
                                    > high_risk_threshold
                                ]["kfactors_dfinal_score"].mean()
                            )
                            if high_risk_count > 0
                            else 0
                        ),
                    }
                )

            results["risk_evolution"] = {
                "threshold": float(high_risk_threshold),
                "evolution": high_risk_evolution,
                "total_high_risk_cells": int(
                    sum(hr["count"] for hr in high_risk_evolution)
                ),
                "avg_high_risk_cells": float(
                    np.mean([hr["count"] for hr in high_risk_evolution])
                ),
            }

            print(f"  고위험 임계값: {high_risk_threshold:.6f}")
            print(
                f"  평균 고위험 셀 수: {results['risk_evolution']['avg_high_risk_cells']:.1f}"
            )

        # 5. K-factors 간 상관관계 분석
        print("\n5. K-factors 간 시간적 상관관계 분석...")
        correlation_matrix = {}
        for i, factor1 in enumerate(available_cols):
            correlation_matrix[factor1] = {}
            for factor2 in available_cols:
                mean_col1 = f"mean_{factor1}"
                mean_col2 = f"mean_{factor2}"
                if (
                    mean_col1 in self.spacetime_cube.columns
                    and mean_col2 in self.spacetime_cube.columns
                ):
                    monthly1 = self.spacetime_cube.groupby("time_bin")[mean_col1].mean()
                    monthly2 = self.spacetime_cube.groupby("time_bin")[mean_col2].mean()
                    if len(monthly1) > 2 and len(monthly2) > 2:
                        corr = monthly1.corr(monthly2)
                        correlation_matrix[factor1][factor2] = float(corr)

        results["temporal_correlation"]["matrix"] = correlation_matrix

        # 가장 강한 상관관계 찾기
        max_corr = 0
        max_pair = ("", "")
        for f1 in correlation_matrix:
            for f2 in correlation_matrix[f1]:
                if f1 != f2 and abs(correlation_matrix[f1][f2]) > abs(max_corr):
                    max_corr = correlation_matrix[f1][f2]
                    max_pair = (f1, f2)

        if max_pair[0]:
            print(f"  최강 상관관계: {max_pair[0]} ↔ {max_pair[1]} (r={max_corr:.3f})")

        self.kfactors_dfinal_timeseries = results
        return results

    def visualize_kfactors_dfinal_timeseries(self, output_dir: str):
        """K-factors/D_final 시계열 시각화 (Phase 3.3.5)"""
        if (
            not hasattr(self, "kfactors_dfinal_timeseries")
            or self.kfactors_dfinal_timeseries is None
        ):
            print("\nK-factors/D_final 시계열 데이터 없음 - 시각화 건너뜀")
            return

        print("\n=== K-factors/D_final 시계열 시각화 ===")

        # 1. 통합 점수 시계열 플롯
        if self.kfactors_dfinal_timeseries.get("composite_score"):
            fig, axes = plt.subplots(2, 2, figsize=(16, 10))

            # 통합 점수 시계열
            composite = self.kfactors_dfinal_timeseries["composite_score"]
            if "monthly_mean" in composite:
                ax = axes[0, 0]
                monthly_mean = pd.Series(composite["monthly_mean"])
                ax.plot(
                    range(len(monthly_mean)),
                    monthly_mean.values,
                    marker="o",
                    linewidth=2,
                    markersize=6,
                    color="darkred",
                    label="K_total × D_final",
                )

                # 트렌드 라인
                z = np.polyfit(range(len(monthly_mean)), monthly_mean.values, 1)
                p = np.poly1d(z)
                ax.plot(
                    range(len(monthly_mean)),
                    p(range(len(monthly_mean))),
                    "r--",
                    alpha=0.5,
                    label="트렌드",
                )

                ax.set_xlabel("월")
                ax.set_ylabel("통합 점수")
                ax.set_title(
                    "K-factors/D_final 통합 점수 시계열", fontsize=12, fontweight="bold"
                )
                ax.legend()
                ax.grid(True, alpha=0.3)

            # 고위험 지역 진화
            if "risk_evolution" in self.kfactors_dfinal_timeseries:
                ax = axes[0, 1]
                evolution = self.kfactors_dfinal_timeseries["risk_evolution"][
                    "evolution"
                ]
                if evolution:
                    counts = [e["count"] for e in evolution]
                    ax.bar(range(len(counts)), counts, color="coral", alpha=0.7)
                    ax.set_xlabel("시간 구간")
                    ax.set_ylabel("고위험 셀 수")
                    ax.set_title("고위험 지역 수 변화", fontsize=12, fontweight="bold")
                    ax.grid(True, alpha=0.3, axis="y")

            # 개별 K-factors 트렌드
            ax = axes[1, 0]
            colors = ["blue", "green", "orange", "purple", "brown", "red"]
            for i, (factor, stats) in enumerate(
                self.kfactors_dfinal_timeseries["monthly_stats"].items()
            ):
                if "mean" in stats and len(stats["mean"]) > 0:
                    monthly = pd.Series(stats["mean"])
                    # 정규화하여 비교 가능하게
                    normalized = (monthly - monthly.min()) / (
                        monthly.max() - monthly.min() + 1e-10
                    )
                    ax.plot(
                        range(len(normalized)),
                        normalized.values,
                        label=factor,
                        linewidth=1.5,
                        alpha=0.7,
                        color=colors[i % len(colors)],
                    )

            ax.set_xlabel("월")
            ax.set_ylabel("정규화된 값")
            ax.set_title(
                "K-factors 개별 트렌드 (정규화)", fontsize=12, fontweight="bold"
            )
            ax.legend(loc="upper left", fontsize=9)
            ax.grid(True, alpha=0.3)

            # 계절별 패턴
            ax = axes[1, 1]
            if "seasonal_patterns" in self.kfactors_dfinal_timeseries:
                # K_total의 계절별 패턴 표시
                if "K_total" in self.kfactors_dfinal_timeseries["seasonal_patterns"]:
                    seasonal = pd.DataFrame(
                        self.kfactors_dfinal_timeseries["seasonal_patterns"]["K_total"]
                    )
                    if "mean" in seasonal:
                        seasonal["mean"].plot(
                            kind="bar",
                            ax=ax,
                            color=["#90EE90", "#FFD700", "#FF6347", "#87CEEB"],
                        )
                        ax.set_xlabel("계절")
                        ax.set_ylabel("K_total 평균")
                        ax.set_title(
                            "계절별 K_total 패턴", fontsize=12, fontweight="bold"
                        )
                        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
                        ax.grid(True, alpha=0.3, axis="y")

            plt.suptitle(
                "K-factors/D_final 시계열 분석 (Phase 3.3)",
                fontsize=14,
                fontweight="bold",
                y=1.02,
            )
            plt.tight_layout()

            output_path = os.path.join(
                output_dir, "kfactors_dfinal_timeseries_analysis.png"
            )
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"K-factors/D_final 시계열 시각화 저장: {output_path}")

        # 2. 상관관계 히트맵
        if "temporal_correlation" in self.kfactors_dfinal_timeseries:
            if "matrix" in self.kfactors_dfinal_timeseries["temporal_correlation"]:
                corr_matrix = self.kfactors_dfinal_timeseries["temporal_correlation"][
                    "matrix"
                ]
                if corr_matrix:
                    # DataFrame으로 변환
                    factors = list(corr_matrix.keys())
                    matrix_data = []
                    for f1 in factors:
                        row = []
                        for f2 in factors:
                            row.append(corr_matrix[f1].get(f2, 0))
                        matrix_data.append(row)

                    fig, ax = plt.subplots(figsize=(10, 8))
                    im = ax.imshow(
                        matrix_data, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto"
                    )

                    # 레이블 설정
                    ax.set_xticks(range(len(factors)))
                    ax.set_yticks(range(len(factors)))
                    ax.set_xticklabels(factors, rotation=45, ha="right")
                    ax.set_yticklabels(factors)

                    # 값 표시
                    for i in range(len(factors)):
                        for j in range(len(factors)):
                            ax.text(
                                j,
                                i,
                                f"{matrix_data[i][j]:.2f}",
                                ha="center",
                                va="center",
                                color="black",
                                fontsize=10,
                            )

                    ax.set_title(
                        "K-factors 시간적 상관관계 매트릭스",
                        fontsize=14,
                        fontweight="bold",
                    )
                    plt.colorbar(im, ax=ax, label="상관계수")
                    plt.tight_layout()

                    output_path = os.path.join(
                        output_dir, "kfactors_correlation_matrix.png"
                    )
                    plt.savefig(output_path, dpi=300, bbox_inches="tight")
                    plt.close()

                    print(f"K-factors 상관관계 매트릭스 저장: {output_path}")

    def visualize_cnt_jnt_timeseries(self, output_dir: str):
        """CNT_JNT 시계열 시각화 (Phase 3.2.5)"""
        if self.cnt_jnt_timeseries is None:
            print("\nCNT_JNT 시계열 데이터 없음 - 시각화 건너뜀")
            return

        print("\n=== CNT_JNT 시계열 시각화 ===")

        fig, axes = plt.subplots(3, 1, figsize=(15, 12))

        # 1. 월별 CNT_JNT 평균값 시계열
        monthly_mean = pd.Series(self.cnt_jnt_timeseries["monthly_stats"]["mean"])
        if len(monthly_mean) > 0:
            ax = axes[0]
            ax.plot(
                range(len(monthly_mean)),
                monthly_mean.values,
                marker="o",
                linewidth=2,
                markersize=6,
                label="월별 평균",
            )

            # 트렌드 라인 추가
            z = np.polyfit(range(len(monthly_mean)), monthly_mean.values, 1)
            p = np.poly1d(z)
            ax.plot(
                range(len(monthly_mean)),
                p(range(len(monthly_mean))),
                "r--",
                alpha=0.5,
                label="트렌드",
            )

            ax.set_xlabel("월")
            ax.set_ylabel("평균 CNT_JNT")
            ax.set_title("CNT_JNT 월별 평균 시계열", fontsize=14)
            ax.legend()
            ax.grid(True, alpha=0.3)

        # 2. 계절별 패턴
        if self.cnt_jnt_timeseries.get("seasonal_patterns"):
            ax = axes[1]
            seasonal = pd.DataFrame(self.cnt_jnt_timeseries["seasonal_patterns"])
            if "mean" in seasonal:
                seasonal["mean"].plot(
                    kind="bar",
                    ax=ax,
                    color=["#90EE90", "#FFD700", "#FF6347", "#87CEEB"],
                )
                ax.set_xlabel("계절")
                ax.set_ylabel("평균 CNT_JNT")
                ax.set_title("계절별 CNT_JNT 패턴", fontsize=14)
                ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
                ax.grid(True, alpha=0.3)

        # 3. 높은 CNT_JNT 지역 vs 전체 비교
        if "high_cnt_areas" in self.cnt_jnt_timeseries:
            ax = axes[2]
            high_ts = pd.Series(self.cnt_jnt_timeseries["high_cnt_areas"]["timeseries"])
            if len(high_ts) > 0 and len(monthly_mean) > 0:
                ax.plot(
                    range(len(monthly_mean)),
                    monthly_mean.values,
                    label="전체 평균",
                    linewidth=2,
                    alpha=0.7,
                )
                ax.plot(
                    range(len(high_ts)),
                    high_ts.values,
                    label="높은 CNT_JNT 지역",
                    linewidth=2,
                    color="red",
                    alpha=0.7,
                )
                ax.set_xlabel("월")
                ax.set_ylabel("평균 CNT_JNT")
                ax.set_title("높은 CNT_JNT 지역 vs 전체 평균", fontsize=14)
                ax.legend()
                ax.grid(True, alpha=0.3)

        plt.tight_layout()

        output_path = os.path.join(output_dir, "cnt_jnt_timeseries_analysis.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"CNT_JNT 시계열 시각화 저장: {output_path}")

    def visualize_spacetime_cube(self, output_dir: str):
        """시공간 큐브 시각화"""
        print("\n시공간 큐브 시각화 중...")

        # 1. 시계열 플롯
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))

        # 재작업 횟수 시계열
        ax = axes[0]
        ax.plot(
            self.time_series.index,
            self.time_series["point_count"],
            marker="o",
            linewidth=2,
            markersize=6,
        )
        ax.set_xlabel("시간")
        ax.set_ylabel("재작업 횟수")
        ax.set_title("재작업 횟수 시계열", fontsize=14)
        ax.grid(True, alpha=0.3)

        # 계절성 분해 (있는 경우)
        if self.seasonal_decomposition:
            ax = axes[1]
            time_index = self.time_series.index
            ax.plot(
                time_index,
                self.seasonal_decomposition["trend"],
                label="트렌드",
                linewidth=2,
            )
            ax.plot(
                time_index,
                self.seasonal_decomposition["seasonal"],
                label="계절성",
                linewidth=1,
                alpha=0.7,
            )
            ax.set_xlabel("시간")
            ax.set_ylabel("값")
            ax.set_title("트렌드 및 계절성 요소", fontsize=14)
            ax.legend()
            ax.grid(True, alpha=0.3)

            # 잔차
            ax = axes[2]
            ax.plot(
                time_index,
                self.seasonal_decomposition["resid"],
                linewidth=1,
                alpha=0.7,
                color="gray",
            )
            ax.axhline(y=0, color="red", linestyle="--", alpha=0.5)
            ax.set_xlabel("시간")
            ax.set_ylabel("잔차")
            ax.set_title("잔차", fontsize=14)
            ax.grid(True, alpha=0.3)
        else:
            # ACF/PACF 플롯
            if len(self.time_series) > 10:
                from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

                plot_acf(
                    self.time_series["point_count"].values,
                    lags=min(20, len(self.time_series) // 2),
                    ax=axes[1],
                )
                axes[1].set_title("자기상관함수 (ACF)", fontsize=14)

                plot_pacf(
                    self.time_series["point_count"].values,
                    lags=min(20, len(self.time_series) // 2),
                    ax=axes[2],
                )
                axes[2].set_title("편자기상관함수 (PACF)", fontsize=14)

        plt.tight_layout()

        output_path = os.path.join(output_dir, "timeseries_analysis.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"시계열 시각화 저장: {output_path}")

        # 2. 3D 시공간 큐브 (Plotly)
        self.visualize_3d_spacetime_cube(output_dir)

    def visualize_3d_spacetime_cube(self, output_dir: str):
        """3D 시공간 큐브 시각화 (Plotly)"""
        print("3D 시공간 큐브 생성 중...")

        # 데이터 준비
        cube_data = self.spacetime_cube[self.spacetime_cube["point_count"] > 0].copy()

        if len(cube_data) > 1000:
            # 샘플링
            cube_data = cube_data.sample(n=1000)

        # 시간을 숫자로 변환 (일 단위)
        min_time = cube_data["time_bin"].min()
        cube_data["time_numeric"] = (cube_data["time_bin"] - min_time).dt.days

        # 3D scatter plot
        fig = go.Figure(
            data=[
                go.Scatter3d(
                    x=cube_data["grid_x"],
                    y=cube_data["grid_y"],
                    z=cube_data["time_numeric"],
                    mode="markers",
                    marker=dict(
                        size=5 + cube_data["point_count"] * 2,
                        color=cube_data["point_count"],
                        colorscale="Viridis",
                        showscale=True,
                        colorbar=dict(title="재작업 횟수"),
                        opacity=0.8,
                    ),
                    text=[
                        f"위치: ({x:.0f}, {y:.0f})<br>시간: {t}<br>횟수: {c}"
                        for x, y, t, c in zip(
                            cube_data["grid_x"],
                            cube_data["grid_y"],
                            cube_data["time_bin"].dt.strftime("%Y-%m"),
                            cube_data["point_count"],
                            strict=False,
                        )
                    ],
                    hovertemplate="%{text}<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="3D 시공간 큐브",
            scene=dict(
                xaxis_title="X 좌표 (m)",
                yaxis_title="Y 좌표 (m)",
                zaxis_title=f'시간 (일, {min_time.strftime("%Y-%m-%d")} 기준)',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
            ),
            width=1000,
            height=800,
        )

        output_path = os.path.join(output_dir, "spacetime_cube_3d.html")
        fig.write_html(output_path)

        print(f"3D 시공간 큐브 저장: {output_path}")

    def save_results(self, output_dir: str):
        """결과 저장"""

        # numpy 타입을 Python 기본 타입으로 변환
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.bool_ | bool):
                return bool(obj)
            if isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            if isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        # 시공간 큐브 저장 (pickle)
        cube_path = os.path.join(output_dir, "spacetime_cube.pkl")
        with open(cube_path, "wb") as f:
            pickle.dump(self.spacetime_cube, f)
        print(f"시공간 큐브 저장: {cube_path}")

        # 시계열 데이터 저장
        ts_path = os.path.join(output_dir, "timeseries.csv")
        self.time_series.to_csv(ts_path, encoding="utf-8-sig")
        print(f"시계열 데이터 저장: {ts_path}")

        # 분석 결과 저장
        results = {
            "analysis_date": datetime.now().isoformat(),
            "parameters": self.params,
            "n_points": len(self.gdf),
            "n_spacetime_cells": len(self.spacetime_cube),
            "time_range": {
                "start": str(self.gdf["datetime"].min()),
                "end": str(self.gdf["datetime"].max()),
            },
            "trend_analysis": convert_numpy(self.trend_results),
            "knox_test": convert_numpy(self.knox_results),
        }

        if self.seasonal_decomposition:
            results["seasonal_analysis"] = {
                "seasonal_strength": float(
                    1
                    - np.var(self.seasonal_decomposition["resid"])
                    / np.var(
                        self.seasonal_decomposition["seasonal"]
                        + self.seasonal_decomposition["resid"]
                    )
                ),
                "trend_strength": float(
                    1
                    - np.var(self.seasonal_decomposition["resid"])
                    / np.var(
                        self.seasonal_decomposition["trend"]
                        + self.seasonal_decomposition["resid"]
                    )
                ),
            }

        # CNT_JNT 시계열 분석 결과 추가
        if hasattr(self, "cnt_jnt_timeseries") and self.cnt_jnt_timeseries:
            results["cnt_jnt_analysis"] = convert_numpy(self.cnt_jnt_timeseries)

        # K-factors/D_final 시계열 분석 결과 추가 (Phase 3.3)
        if (
            hasattr(self, "kfactors_dfinal_timeseries")
            and self.kfactors_dfinal_timeseries
        ):
            results["kfactors_dfinal_analysis"] = convert_numpy(
                self.kfactors_dfinal_timeseries
            )

        results_path = os.path.join(output_dir, "spacetime_analysis_results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"분석 결과 저장: {results_path}")

    def generate_report(self, output_dir: str):
        """분석 보고서 생성"""
        report_lines = [
            "# 시공간 큐브 분석 보고서",
            f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. 데이터 개요",
            f"- 총 재작업 포인트: {len(self.gdf):,}개",
            f"- 시공간 큐브 셀: {len(self.spacetime_cube):,}개",
            f"- 분석 기간: {self.gdf['datetime'].min().strftime('%Y-%m-%d')} ~ {self.gdf['datetime'].max().strftime('%Y-%m-%d')}",
            f"- 공간 해상도: {self.params['grid_size']}m × {self.params['grid_size']}m",
            f"- 시간 해상도: {self.params['time_interval']}",
            "\n## 2. 트렌드 분석 결과",
        ]

        if self.trend_results:
            report_lines.extend(
                [
                    f"- Mann-Kendall Z: {self.trend_results['mann_kendall_z']:.3f}",
                    f"- P-value: {self.trend_results['mann_kendall_p']:.3f}",
                    f"- Sen's slope: {self.trend_results['sen_slope']:.3f}",
                    f"- 트렌드 방향: {self.trend_results['trend_direction']}",
                    f"- 통계적 유의성: {'있음' if self.trend_results['significant'] else '없음'}",
                ]
            )

        report_lines.append("\n## 3. 계절성 분석 결과")

        if self.seasonal_decomposition:
            seasonal_strength = 1 - np.var(
                self.seasonal_decomposition["resid"]
            ) / np.var(
                self.seasonal_decomposition["seasonal"]
                + self.seasonal_decomposition["resid"]
            )
            trend_strength = 1 - np.var(self.seasonal_decomposition["resid"]) / np.var(
                self.seasonal_decomposition["trend"]
                + self.seasonal_decomposition["resid"]
            )

            report_lines.extend(
                [
                    f"- 계절성 강도: {seasonal_strength:.3f}",
                    f"- 트렌드 강도: {trend_strength:.3f}",
                    f"- 계절 주기: {self.params['seasonal_period']}",
                ]
            )

            if seasonal_strength > 0.6:
                report_lines.append("- **해석**: 강한 계절성 패턴 존재")
            elif seasonal_strength > 0.3:
                report_lines.append("- **해석**: 중간 정도의 계절성 패턴")
            else:
                report_lines.append("- **해석**: 약한 계절성 패턴")
        else:
            report_lines.append("- 데이터 부족으로 계절성 분석 불가")

        report_lines.append("\n## 4. 시공간 군집 분석 (Knox Test)")

        if self.knox_results:
            report_lines.extend(
                [
                    f"- Knox statistic: {self.knox_results['knox_statistic']}",
                    f"- 기댓값: {self.knox_results['expected']:.1f}",
                    f"- Z-score: {self.knox_results['z_score']:.3f}",
                    f"- P-value: {self.knox_results['p_value']:.3f}",
                    f"- 공간 임계값: {self.knox_results['space_threshold']}m",
                    f"- 시간 임계값: {self.knox_results['time_threshold']}일",
                ]
            )

            if self.knox_results["significant_clustering"]:
                report_lines.append("- **해석**: 유의미한 시공간 군집 발견")
            else:
                report_lines.append("- **해석**: 시공간 군집 패턴 없음")

        # CNT_JNT 분석 결과 추가
        if hasattr(self, "cnt_jnt_timeseries") and self.cnt_jnt_timeseries:
            report_lines.append("\n## 5. CNT_JNT 시계열 분석 (Phase 3.2)")
            if "monthly_stats" in self.cnt_jnt_timeseries:
                stats = self.cnt_jnt_timeseries["monthly_stats"]
                report_lines.extend(
                    [
                        f"- 평균 CNT_JNT: {stats['overall_mean']:.2f}",
                        f"- 표준편차: {stats['overall_std']:.2f}",
                        f"- 트렌드: {stats['trend']}",
                    ]
                )
            if "high_cnt_areas" in self.cnt_jnt_timeseries:
                report_lines.append(
                    f"- 높은 CNT_JNT 지역 수: {self.cnt_jnt_timeseries['high_cnt_areas']['count']}"
                )

        # K-factors/D_final 분석 결과 추가 (Phase 3.3)
        if (
            hasattr(self, "kfactors_dfinal_timeseries")
            and self.kfactors_dfinal_timeseries
        ):
            report_lines.append("\n## 6. K-factors/D_final 시계열 분석 (Phase 3.3)")

            if "composite_score" in self.kfactors_dfinal_timeseries:
                composite = self.kfactors_dfinal_timeseries["composite_score"]
                report_lines.extend(
                    [
                        f"- 통합 점수 평균: {composite['overall_mean']:.6f}",
                        f"- 통합 점수 최대: {composite['overall_max']:.6f}",
                        f"- 트렌드: {composite['trend']}",
                    ]
                )

            if "risk_evolution" in self.kfactors_dfinal_timeseries:
                risk = self.kfactors_dfinal_timeseries["risk_evolution"]
                report_lines.extend(
                    [
                        f"- 고위험 임계값: {risk['threshold']:.6f}",
                        f"- 평균 고위험 셀 수: {risk['avg_high_risk_cells']:.1f}",
                    ]
                )

            if "monthly_stats" in self.kfactors_dfinal_timeseries:
                report_lines.append("\n### K-factors 개별 트렌드:")
                for factor, stats in self.kfactors_dfinal_timeseries[
                    "monthly_stats"
                ].items():
                    report_lines.append(
                        f"- {factor}: 평균={stats['overall_mean']:.4f}, 트렌드={stats['trend']}"
                    )

        report_lines.extend(
            [
                "\n## 7. 주요 발견사항",
                "- 시공간 큐브 분석을 통해 재작업의 시간적 변화 패턴 파악",
                "- 계절성과 트렌드 분리를 통한 장기 추세 이해",
                "- Knox test로 시공간 상호작용 검증",
                "- CNT_JNT와 K-factors/D_final의 시계열 패턴 분석",
                "\n## 8. 권장사항",
                "- 계절성이 강한 경우 계절별 유지보수 전략 수립",
                "- 증가 트렌드가 있는 경우 근본 원인 분석 필요",
                "- 시공간 군집이 발견된 경우 해당 지역-시기 집중 관리",
                "- 고위험 지역의 진화 패턴을 기반으로 예방적 유지보수 계획 수립",
            ]
        )

        report_path = os.path.join(output_dir, "spacetime_analysis_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"분석 보고서 저장: {report_path}")


def load_optimal_parameters(use_optimal: bool) -> dict[str, Any]:
    """최적 파라미터 로드"""
    if use_optimal:
        param_file = "results/spatial_analysis/optimal_parameters.json"
        if os.path.exists(param_file):
            print(f"최적 파라미터 로드: {param_file}")
            with open(param_file, encoding="utf-8") as f:
                params = json.load(f)
                if "main22" in params:
                    return params["main22"]
                if "shared" in params:
                    # shared + 기본값
                    return {
                        "grid_size": params["shared"]["grid_size"],
                        "time_interval": "1M",
                        "seasonal_period": 12,
                        "trend_window": 6,
                        "knox_distance": 50,
                        "knox_time": 30,
                    }

    # 기본값
    return {
        "grid_size": 30,
        "time_interval": "1M",
        "seasonal_period": 12,
        "trend_window": 6,
        "knox_distance": 50,
        "knox_time": 30,
    }


def load_repair_data() -> gpd.GeoDataFrame:
    """520 지역 재작업 데이터 로드 및 K-factors/D_final 데이터 병합"""

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

                # K-factors/D_final 데이터 로드 및 병합
                kfactors_shp = "data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp"
                kfactors_csv = str(FATIGUE_PIPE_LM_CSV)

                if os.path.exists(kfactors_shp) and os.path.exists(kfactors_csv):
                    print("K-factors/D_final 데이터 로드 중...")
                    print(f"  Shapefile: {kfactors_shp}")
                    print(f"  CSV: {kfactors_csv}")

                    # Shapefile 로드 (geometry용)
                    pipes_gdf = gpd.read_file(kfactors_shp)

                    # CRS 설정 (V_WTL 파일은 EPSG:5179 - 한국 TM)
                    if pipes_gdf.crs is None:
                        pipes_gdf = pipes_gdf.set_crs("EPSG:5179")

                    # CSV 로드 (K-factors/D_final용)
                    kfactors_df = pd.read_csv(kfactors_csv)

                    # FTR_IDN으로 병합
                    pipes_with_kfactors = pipes_gdf.merge(
                        kfactors_df, on="FTR_IDN", how="inner", suffixes=("", "_csv")
                    )

                    # K-factors 컬럼 목록
                    kfactor_columns = [
                        "K_age",
                        "K_soil",
                        "K_traffic",
                        "K_stress",
                        "K_total",
                        "STD_DIP",
                        "0520_D_final",
                    ]
                    available_cols = [
                        col
                        for col in kfactor_columns
                        if col in pipes_with_kfactors.columns
                    ]

                    if available_cols:
                        print(f"  사용 가능한 K-factors: {available_cols}")

                        # 공간 조인을 위해 좌표계 맞추기
                        if pipes_with_kfactors.crs != gdf.crs:
                            pipes_with_kfactors = pipes_with_kfactors.to_crs(gdf.crs)

                        # 최대값/최소값 컬럼 초기화
                        for col in available_cols:
                            gdf[f"{col}_max"] = np.nan
                            gdf[f"{col}_min"] = np.nan
                            gdf[f"{col}_mean"] = np.nan
                            gdf[f"{col}_count"] = 0

                        # 각 재작업 포인트에 대해 30m 반경 내 파이프 분석
                        for idx, point in gdf.iterrows():
                            # 30m 반경 내 파이프 찾기
                            buffer = point.geometry.buffer(30)
                            nearby_pipes = pipes_with_kfactors[
                                pipes_with_kfactors.intersects(buffer)
                            ]

                            if not nearby_pipes.empty:
                                # 30m 내 파이프 수
                                pipe_count = len(nearby_pipes)

                                for col in available_cols:
                                    # 유효한 값만 필터링
                                    valid_values = nearby_pipes[col].dropna()
                                    if not valid_values.empty:
                                        # 숫자 타입인지 확인
                                        try:
                                            # 숫자로 변환 시도
                                            numeric_values = pd.to_numeric(
                                                valid_values, errors="coerce"
                                            ).dropna()
                                            if not numeric_values.empty:
                                                gdf.at[idx, f"{col}_max"] = (
                                                    numeric_values.max()
                                                )
                                                gdf.at[idx, f"{col}_min"] = (
                                                    numeric_values.min()
                                                )
                                                gdf.at[idx, f"{col}_mean"] = (
                                                    numeric_values.mean()
                                                )
                                                gdf.at[idx, f"{col}_count"] = pipe_count
                                        except:
                                            # 숫자 변환 실패 시 건너뛰기
                                            pass

                        # D_final 컬럼명 통일 (최대값 사용)
                        if "0520_D_final_max" in gdf.columns:
                            gdf["D_final"] = gdf["0520_D_final_max"]
                            gdf["D_final_min"] = gdf["0520_D_final_min"]
                            gdf["D_final_mean"] = gdf["0520_D_final_mean"]

                        # 기본 K-factors 컬럼 생성 (최대값 기준)
                        for col in available_cols:
                            if f"{col}_max" in gdf.columns:
                                gdf[col] = gdf[f"{col}_max"]

                        # 통계 출력
                        matched_count = gdf[f"{available_cols[0]}_count"].notna().sum()
                        avg_pipes = gdf[f"{available_cols[0]}_count"].mean()
                        print("\n  매칭 결과:")
                        print(
                            f"    - 매칭된 재작업 포인트: {matched_count}/{len(gdf)}개"
                        )
                        print(f"    - 평균 파이프 수 (30m 내): {avg_pipes:.1f}개")

                        for col in available_cols[:3]:  # 주요 K-factors만 출력
                            if f"{col}_max" in gdf.columns:
                                max_avg = gdf[f"{col}_max"].mean()
                                min_avg = gdf[f"{col}_min"].mean()
                                print(
                                    f"    - {col}: 최대 평균={max_avg:.2f}, 최소 평균={min_avg:.2f}"
                                )

                        print("\nK-factors/D_final 데이터 병합 완료")
                    else:
                        print("K-factors/D_final 컬럼을 찾을 수 없음")
                else:
                    print("K-factors/D_final 파일 없음")
                    if not os.path.exists(kfactors_shp):
                        print(f"  - Shapefile 없음: {kfactors_shp}")
                    if not os.path.exists(kfactors_csv):
                        print(f"  - CSV 없음: {kfactors_csv}")

                print(f"로드된 데이터: {len(gdf)} 포인트")
                return gdf
            print(f"좌표 컬럼 없음: {file_path}")

    raise FileNotFoundError("520 지역 재작업 데이터 파일을 찾을 수 없습니다.")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="시공간 큐브 분석을 통한 재작업 패턴 분석"
    )
    parser.add_argument("--grid-size", type=int, help="공간 그리드 크기 (미터)")
    parser.add_argument(
        "--time-interval", default="1M", help="시간 간격 (D, W, M, Q, Y)"
    )
    parser.add_argument("--seasonal-period", type=int, help="계절 주기")
    parser.add_argument(
        "--use-optimal",
        action="store_true",
        default=True,
        help="main20에서 생성된 최적 파라미터 사용",
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/spacetime",
        help="결과 저장 디렉토리",
    )

    args = parser.parse_args()

    # 로깅 설정
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    try:
        # 데이터 로드
        gdf = load_repair_data()

        # 파라미터 설정
        params = load_optimal_parameters(args.use_optimal)

        # 명령줄 인자로 덮어쓰기
        if args.grid_size:
            params["grid_size"] = args.grid_size
        if args.time_interval:
            params["time_interval"] = args.time_interval
        if args.seasonal_period:
            params["seasonal_period"] = args.seasonal_period

        print("\n사용 파라미터:")
        for key, value in params.items():
            print(f"  {key}: {value}")

        # 분석 실행
        analyzer = SpaceTimeCubeAnalyzer(gdf, params)

        # 시공간 큐브 생성
        analyzer.create_spacetime_cube()

        # 계절성 분해
        analyzer.perform_seasonal_decomposition()

        # 트렌드 분석
        analyzer.perform_trend_analysis()

        # Knox test
        analyzer.perform_knox_test()

        # CNT_JNT 시계열 분석 (Phase 3.2)
        analyzer.analyze_cnt_jnt_temporal_patterns()

        # CNT_JNT ARIMA 예측 (Phase 3.2.4)
        analyzer.analyze_cnt_jnt_arima_forecast()

        # K-factors/D_final 시계열 분석 (Phase 3.3)
        analyzer.analyze_kfactors_dfinal_temporal_patterns()

        # 결과 저장
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        analyzer.save_results(str(output_dir))
        analyzer.visualize_spacetime_cube(str(output_dir))

        # CNT_JNT 시계열 시각화 (Phase 3.2.5)
        analyzer.visualize_cnt_jnt_timeseries(str(output_dir))

        # K-factors/D_final 시계열 시각화 (Phase 3.3.5)
        analyzer.visualize_kfactors_dfinal_timeseries(str(output_dir))

        analyzer.generate_report(str(output_dir))

        print(f"\n분석 완료! 결과: {output_dir}")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
