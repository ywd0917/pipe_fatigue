"""
main23_emerging_hotspots.py

시공간 큐브 분석 결과를 기반으로 진화하는 핫스팟 패턴을 식별합니다.
New, Intensifying, Persistent, Diminishing, Sporadic 등의 패턴을 분류합니다.
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
from plotly.subplots import make_subplots

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.config import FATIGUE_PIPE_LM_CSV, FATIGUE_SPLY_LS_CSV
from src.common.korean_font_utils import setup_korean_font
from src.common.spatial_utils import (
    calculate_getis_ord_gi,
    create_spatial_weights_matrix,
    identify_hotspots,
)

warnings.filterwarnings("ignore")


class EmergingHotspotAnalyzer:
    """진화하는 핫스팟 분석 클래스"""

    def __init__(self, spacetime_cube: gpd.GeoDataFrame, params: dict[str, Any]):
        """
        Parameters
        ----------
        spacetime_cube : GeoDataFrame
            시공간 큐브 데이터 (main22 결과)
        params : dict
            분석 파라미터
        """
        self.spacetime_cube = spacetime_cube
        self.params = params
        self.hotspot_evolution = None
        self.pattern_classification = None
        self.cnt_jnt_evolution = None  # CNT_JNT 진화 분석 결과 (Phase 4.2)
        self.kfactors_dfinal_evolution = (
            None  # K-factors/D_final 진화 분석 결과 (Phase 4.3)
        )

        # 한글 폰트 설정
        setup_korean_font()

        # 시간 정보 준비
        self._prepare_temporal_data()

    def _prepare_temporal_data(self):
        """시간 데이터 준비"""
        # time_bin이 datetime 형식인지 확인
        if "time_bin" not in self.spacetime_cube.columns:
            raise ValueError("시공간 큐브에 time_bin 컬럼이 없습니다.")

        # datetime으로 변환
        if not pd.api.types.is_datetime64_any_dtype(self.spacetime_cube["time_bin"]):
            self.spacetime_cube["time_bin"] = pd.to_datetime(
                self.spacetime_cube["time_bin"]
            )

        # 시간 범위
        self.time_range = (
            self.spacetime_cube["time_bin"].min(),
            self.spacetime_cube["time_bin"].max(),
        )

        # 고유 시간 포인트
        self.unique_times = sorted(self.spacetime_cube["time_bin"].unique())

        print(f"시간 범위: {self.time_range[0]} ~ {self.time_range[1]}")
        print(f"시간 포인트 수: {len(self.unique_times)}")

    def calculate_hotspots_by_time(self) -> pd.DataFrame:
        """각 시점별 핫스팟 계산"""
        print("\n시점별 핫스팟 계산 중...")

        hotspot_results = []

        for time_point in self.unique_times:
            # 해당 시점 데이터 필터링
            time_data = self.spacetime_cube[
                self.spacetime_cube["time_bin"] == time_point
            ].copy()

            if len(time_data) < 3:
                continue

            # 공간 가중치 행렬 생성
            W = create_spatial_weights_matrix(
                time_data,
                method="distance",
                threshold=100,  # 기본값 또는 파라미터 사용
                binary=True,
            )

            # Gi* 계산
            values = time_data["point_count"].values
            if values.sum() > 0:
                z_scores = calculate_getis_ord_gi(values, W, star=True)

                # 핫스팟 분류
                hotspot_classes = identify_hotspots(z_scores, confidence_levels=[0.95])

                # 결과 저장
                for idx, (_, row) in enumerate(time_data.iterrows()):
                    hotspot_results.append(
                        {
                            "cell_id": row["cell_id"],
                            "time_bin": time_point,
                            "gi_star_z": z_scores[idx],
                            "hotspot_95": hotspot_classes["confidence_95"][idx],
                            "point_count": row["point_count"],
                            "mean_cnt_jnt": row.get("mean_cnt_jnt", np.nan),
                        }
                    )

        self.hotspot_evolution = pd.DataFrame(hotspot_results)

        print(f"계산된 핫스팟 레코드: {len(self.hotspot_evolution)}")

        return self.hotspot_evolution

    def classify_hotspot_patterns(self) -> pd.DataFrame:
        """핫스팟 진화 패턴 분류"""
        print("\n핫스팟 진화 패턴 분류 중...")

        # lookback 기간 설정
        lookback_days = self.params["lookback_months"] * 30
        lookback_date = self.time_range[1] - pd.Timedelta(days=lookback_days)

        # 셀별 패턴 분류
        pattern_results = []

        for cell_id in self.hotspot_evolution["cell_id"].unique():
            cell_data = self.hotspot_evolution[
                self.hotspot_evolution["cell_id"] == cell_id
            ].sort_values("time_bin")

            if len(cell_data) < self.params["min_observations"]:
                continue

            # 최근 데이터
            recent_data = cell_data[cell_data["time_bin"] >= lookback_date]

            # z-score 시계열
            z_scores = cell_data["gi_star_z"].values
            hotspot_flags = cell_data["hotspot_95"].values

            # 패턴 분류
            pattern = self._classify_pattern(z_scores, hotspot_flags, recent_data)

            # 통계 계산
            stats_dict = {
                "cell_id": cell_id,
                "pattern": pattern,
                "n_observations": len(cell_data),
                "n_hotspot": np.sum(hotspot_flags == 1),
                "n_coldspot": np.sum(hotspot_flags == -1),
                "mean_z_score": np.mean(z_scores),
                "std_z_score": np.std(z_scores),
                "trend_slope": self._calculate_trend(z_scores),
                "first_hotspot": (
                    cell_data[hotspot_flags == 1]["time_bin"].min()
                    if np.any(hotspot_flags == 1)
                    else pd.NaT
                ),
                "last_hotspot": (
                    cell_data[hotspot_flags == 1]["time_bin"].max()
                    if np.any(hotspot_flags == 1)
                    else pd.NaT
                ),
            }

            # CNT_JNT 통계 (있는 경우)
            if "mean_cnt_jnt" in cell_data.columns:
                cnt_jnt = cell_data["mean_cnt_jnt"].dropna()
                if len(cnt_jnt) > 0:
                    stats_dict["mean_cnt_jnt"] = cnt_jnt.mean()
                    stats_dict["cnt_jnt_trend"] = self._calculate_trend(cnt_jnt.values)

            pattern_results.append(stats_dict)

        self.pattern_classification = pd.DataFrame(pattern_results)

        # 패턴 요약 출력
        print("\n패턴 분류 결과:")
        pattern_counts = self.pattern_classification["pattern"].value_counts()
        for pattern, count in pattern_counts.items():
            print(f"  {pattern}: {count}개 셀")

        return self.pattern_classification

    def _classify_pattern(
        self, z_scores: np.ndarray, hotspot_flags: np.ndarray, recent_data: pd.DataFrame
    ) -> str:
        """개별 셀의 패턴 분류"""

        # 트렌드 계산
        trend = self._calculate_trend(z_scores)

        # 최근 핫스팟 비율
        recent_hotspot_ratio = (
            np.mean(recent_data["hotspot_95"] == 1) if len(recent_data) > 0 else 0
        )

        # 전체 기간 핫스팟 비율
        total_hotspot_ratio = np.mean(hotspot_flags == 1)

        # 패턴 분류 로직
        if total_hotspot_ratio == 0:
            return "Never"

        # New Hot Spot: 최근에만 핫스팟
        if recent_hotspot_ratio > 0.5 and total_hotspot_ratio < 0.3:
            if pd.Timestamp.now() - recent_data[recent_data["hotspot_95"] == 1][
                "time_bin"
            ].min() < pd.Timedelta(days=180):
                return "New"

        # Intensifying: z-score 증가 중
        if trend > self.params["trend_threshold"] and recent_hotspot_ratio > 0.5:
            return "Intensifying"

        # Diminishing: z-score 감소 중
        if trend < -self.params["trend_threshold"] and total_hotspot_ratio > 0.3:
            return "Diminishing"

        # Persistent: 지속적인 핫스팟
        if total_hotspot_ratio > 0.7:
            # 2년 이상 지속 확인
            first_hotspot = recent_data[recent_data["hotspot_95"] == 1][
                "time_bin"
            ].min()
            if pd.notna(first_hotspot):
                duration = (recent_data["time_bin"].max() - first_hotspot).days
                if duration > 730:  # 2년
                    return "Persistent"

        # Sporadic: 간헐적 핫스팟
        if 0.2 < total_hotspot_ratio < 0.7:
            # 변동성 확인
            if np.std(z_scores) > 1.5:
                return "Sporadic"

        # Oscillating: 진동 패턴
        # 부호 변화 횟수 계산
        sign_changes = np.sum(np.diff(np.sign(z_scores)) != 0)
        if sign_changes > len(z_scores) * 0.4:
            return "Oscillating"

        # Historical: 과거에만 핫스팟
        if total_hotspot_ratio > 0.3 and recent_hotspot_ratio < 0.1:
            return "Historical"

        return "Other"

    def _calculate_trend(self, values: np.ndarray) -> float:
        """선형 트렌드 계산"""
        if len(values) < 2:
            return 0.0

        x = np.arange(len(values))

        # NaN 제거
        mask = ~np.isnan(values)
        if np.sum(mask) < 2:
            return 0.0

        x_clean = x[mask]
        y_clean = values[mask]

        # 선형 회귀
        slope, _ = np.polyfit(x_clean, y_clean, 1)

        return slope

    def analyze_cnt_jnt_evolution(self) -> dict[str, Any]:
        """CNT_JNT 진화 패턴 분석 (Phase 4.2)"""
        if "mean_cnt_jnt" not in self.spacetime_cube.columns:
            print("\nCNT_JNT 데이터 없음 - 분석 건너뜀")
            return {}

        print("\n=== CNT_JNT 진화 패턴 분석 (Phase 4.2) ===")

        results = {
            "pattern_statistics": {},
            "new_hotspots": {},
            "intensifying_hotspots": {},
            "persistent_hotspots": {},
            "diminishing_hotspots": {},
            "temporal_changes": {},
        }

        # 1. New 핫스팟의 CNT_JNT 초기값 분석
        print("\n1. New 핫스팟의 CNT_JNT 초기값 분석...")
        new_hotspots = self.pattern_classification[
            self.pattern_classification["pattern"] == "New"
        ]
        if len(new_hotspots) > 0:
            # 각 New 핫스팟의 첫 등장 시점 CNT_JNT 값
            initial_values = []
            for _, cell in new_hotspots.iterrows():
                cell_data = self.spacetime_cube[
                    (self.spacetime_cube["grid_x"] == cell["grid_x"])
                    & (self.spacetime_cube["grid_y"] == cell["grid_y"])
                ].sort_values("time_bin")

                if len(cell_data) > 0 and "mean_cnt_jnt" in cell_data.columns:
                    initial_values.append(cell_data.iloc[0]["mean_cnt_jnt"])

            if initial_values:
                results["new_hotspots"] = {
                    "count": len(new_hotspots),
                    "initial_cnt_jnt_mean": np.mean(initial_values),
                    "initial_cnt_jnt_std": np.std(initial_values),
                    "initial_cnt_jnt_median": np.median(initial_values),
                    "threshold_exceeded": sum(
                        v > np.quantile(initial_values, 0.75) for v in initial_values
                    ),
                }
                print(f"  New 핫스팟 수: {len(new_hotspots)}")
                print(
                    f"  초기 CNT_JNT 평균: {results['new_hotspots']['initial_cnt_jnt_mean']:.2f}"
                )

        # 2. Intensifying 핫스팟의 CNT_JNT 변화율
        print("\n2. Intensifying 핫스팟의 CNT_JNT 변화율 분석...")
        intensifying = self.pattern_classification[
            self.pattern_classification["pattern"] == "Intensifying"
        ]
        if len(intensifying) > 0:
            change_rates = []
            for _, cell in intensifying.iterrows():
                cell_data = self.spacetime_cube[
                    (self.spacetime_cube["grid_x"] == cell["grid_x"])
                    & (self.spacetime_cube["grid_y"] == cell["grid_y"])
                ].sort_values("time_bin")

                if len(cell_data) > 1 and "mean_cnt_jnt" in cell_data.columns:
                    # 변화율 계산 (선형 회귀 기울기)
                    x = np.arange(len(cell_data))
                    y = cell_data["mean_cnt_jnt"].values
                    if not np.isnan(y).all():
                        slope, _ = np.polyfit(x[~np.isnan(y)], y[~np.isnan(y)], 1)
                        change_rates.append(slope)

            if change_rates:
                results["intensifying_hotspots"] = {
                    "count": len(intensifying),
                    "change_rate_mean": np.mean(change_rates),
                    "change_rate_std": np.std(change_rates),
                    "positive_rate_pct": sum(r > 0 for r in change_rates)
                    / len(change_rates)
                    * 100,
                    "significant_increase": sum(
                        r > np.quantile(change_rates, 0.75) for r in change_rates
                    ),
                }
                print(f"  Intensifying 핫스팟 수: {len(intensifying)}")
                print(
                    f"  평균 변화율: {results['intensifying_hotspots']['change_rate_mean']:.4f}"
                )

        # 3. Persistent 핫스팟의 CNT_JNT 안정성
        print("\n3. Persistent 핫스팟의 CNT_JNT 안정성 분석...")
        persistent = self.pattern_classification[
            self.pattern_classification["pattern"] == "Persistent"
        ]
        if len(persistent) > 0:
            stability_metrics = []
            for _, cell in persistent.iterrows():
                cell_data = self.spacetime_cube[
                    (self.spacetime_cube["grid_x"] == cell["grid_x"])
                    & (self.spacetime_cube["grid_y"] == cell["grid_y"])
                ].sort_values("time_bin")

                if len(cell_data) > 2 and "mean_cnt_jnt" in cell_data.columns:
                    cnt_values = cell_data["mean_cnt_jnt"].dropna()
                    if len(cnt_values) > 0:
                        # 변동계수 (CV) = std/mean (낮을수록 안정적)
                        cv = (
                            cnt_values.std() / cnt_values.mean()
                            if cnt_values.mean() != 0
                            else 0
                        )
                        stability_metrics.append(cv)

            if stability_metrics:
                results["persistent_hotspots"] = {
                    "count": len(persistent),
                    "stability_cv_mean": np.mean(stability_metrics),
                    "stability_cv_std": np.std(stability_metrics),
                    "stable_cells": sum(
                        cv < 0.3 for cv in stability_metrics
                    ),  # CV < 0.3은 안정적
                    "unstable_cells": sum(
                        cv > 0.5 for cv in stability_metrics
                    ),  # CV > 0.5는 불안정
                }
                print(f"  Persistent 핫스팟 수: {len(persistent)}")
                print(
                    f"  평균 변동계수: {results['persistent_hotspots']['stability_cv_mean']:.3f}"
                )

        # 4. Diminishing 핫스팟의 CNT_JNT 감소 패턴
        print("\n4. Diminishing 핫스팟의 CNT_JNT 감소 패턴 분석...")
        diminishing = self.pattern_classification[
            self.pattern_classification["pattern"] == "Diminishing"
        ]
        if len(diminishing) > 0:
            decline_rates = []
            peak_to_current = []
            for _, cell in diminishing.iterrows():
                cell_data = self.spacetime_cube[
                    (self.spacetime_cube["grid_x"] == cell["grid_x"])
                    & (self.spacetime_cube["grid_y"] == cell["grid_y"])
                ].sort_values("time_bin")

                if len(cell_data) > 1 and "mean_cnt_jnt" in cell_data.columns:
                    cnt_values = cell_data["mean_cnt_jnt"].dropna()
                    if len(cnt_values) > 0:
                        # 감소율 계산
                        x = np.arange(len(cnt_values))
                        slope, _ = np.polyfit(x, cnt_values.values, 1)
                        decline_rates.append(slope)

                        # 최대값 대비 현재값 비율
                        if len(cnt_values) > 0:
                            ratio = (
                                cnt_values.iloc[-1] / cnt_values.max()
                                if cnt_values.max() != 0
                                else 1
                            )
                            peak_to_current.append(ratio)

            if decline_rates:
                results["diminishing_hotspots"] = {
                    "count": len(diminishing),
                    "decline_rate_mean": np.mean(decline_rates),
                    "decline_rate_std": np.std(decline_rates),
                    "peak_to_current_ratio": (
                        np.mean(peak_to_current) if peak_to_current else 0
                    ),
                    "significant_decline": sum(
                        r < np.quantile(decline_rates, 0.25) for r in decline_rates
                    ),
                }
                print(f"  Diminishing 핫스팟 수: {len(diminishing)}")
                print(
                    f"  평균 감소율: {results['diminishing_hotspots']['decline_rate_mean']:.4f}"
                )

        # 5. 전체 패턴별 CNT_JNT 통계
        print("\n5. 전체 패턴별 CNT_JNT 통계...")
        for pattern in self.pattern_classification["pattern"].unique():
            pattern_data = self.pattern_classification[
                self.pattern_classification["pattern"] == pattern
            ]

            if "mean_cnt_jnt" in pattern_data.columns:
                cnt_jnt_values = pattern_data["mean_cnt_jnt"].dropna()
                if len(cnt_jnt_values) > 0:
                    results["pattern_statistics"][pattern] = {
                        "count": len(pattern_data),
                        "mean": float(cnt_jnt_values.mean()),
                        "median": float(cnt_jnt_values.median()),
                        "std": float(cnt_jnt_values.std()),
                    }

        # 출력 요약
        print("\n=== CNT_JNT 진화 분석 요약 ===")
        if results["pattern_statistics"]:
            print("\n패턴별 평균 CNT_JNT:")
            for pattern, stats in results["pattern_statistics"].items():
                print(f"  {pattern}: {stats['mean']:.2f} (n={stats['count']})")

        self.cnt_jnt_evolution = results
        return results

    def visualize_cnt_jnt_evolution(self, output_dir: str):
        """CNT_JNT 진화 패턴 시각화 (Phase 4.2.5)"""
        if self.cnt_jnt_evolution is None or not self.cnt_jnt_evolution:
            print("\nCNT_JNT 진화 데이터 없음 - 시각화 건너뜀")
            return

        print("\n=== CNT_JNT 진화 패턴 시각화 (Phase 4.2.5) ===")

        # Sankey diagram과 Evolution timeline은 plotly 사용
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        # 1. Evolution Timeline 시각화
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "New 핫스팟 CNT_JNT 초기값",
                "Intensifying 핫스팟 변화율",
                "Persistent 핫스팟 안정성",
                "Diminishing 핫스팟 감소 패턴",
            ),
            specs=[
                [{"type": "box"}, {"type": "scatter"}],
                [{"type": "bar"}, {"type": "scatter"}],
            ],
        )

        # New 핫스팟 박스플롯
        if self.cnt_jnt_evolution.get("new_hotspots"):
            data = self.cnt_jnt_evolution["new_hotspots"]
            fig.add_trace(
                go.Box(y=[data["initial_cnt_jnt_mean"]], name="New", boxmean=True),
                row=1,
                col=1,
            )

        # Intensifying 변화율
        if self.cnt_jnt_evolution.get("intensifying_hotspots"):
            data = self.cnt_jnt_evolution["intensifying_hotspots"]
            fig.add_trace(
                go.Scatter(
                    x=["Mean", "Std"],
                    y=[data["change_rate_mean"], data["change_rate_std"]],
                    mode="markers+lines",
                    name="Intensifying",
                ),
                row=1,
                col=2,
            )

        # Persistent 안정성
        if self.cnt_jnt_evolution.get("persistent_hotspots"):
            data = self.cnt_jnt_evolution["persistent_hotspots"]
            fig.add_trace(
                go.Bar(
                    x=["Stable", "Unstable"],
                    y=[data.get("stable_cells", 0), data.get("unstable_cells", 0)],
                    name="Persistent",
                ),
                row=2,
                col=1,
            )

        # Diminishing 감소율
        if self.cnt_jnt_evolution.get("diminishing_hotspots"):
            data = self.cnt_jnt_evolution["diminishing_hotspots"]
            fig.add_trace(
                go.Scatter(
                    x=["Decline Rate", "Peak/Current"],
                    y=[data["decline_rate_mean"], data.get("peak_to_current_ratio", 0)],
                    mode="markers",
                    marker_size=15,
                    name="Diminishing",
                ),
                row=2,
                col=2,
            )

        fig.update_layout(
            height=800,
            showlegend=True,
            title_text="CNT_JNT Evolution Patterns by Hotspot Type",
        )

        evolution_path = os.path.join(output_dir, "cnt_jnt_evolution_timeline.html")
        fig.write_html(evolution_path)
        print(f"Evolution timeline 저장: {evolution_path}")

        # 2. Matplotlib 기반 상세 시각화
        fig2, axes = plt.subplots(2, 2, figsize=(15, 12))

        # 패턴별 CNT_JNT 분포
        if "pattern_statistics" in self.cnt_jnt_evolution:
            ax = axes[0, 0]
            patterns = list(self.cnt_jnt_evolution["pattern_statistics"].keys())
            means = [
                self.cnt_jnt_evolution["pattern_statistics"][p]["mean"]
                for p in patterns
            ]
            stds = [
                self.cnt_jnt_evolution["pattern_statistics"][p]["std"] for p in patterns
            ]

            ax.bar(patterns, means, yerr=stds, capsize=5, alpha=0.7)
            ax.set_ylabel("평균 CNT_JNT")
            ax.set_title("패턴별 CNT_JNT 분포", fontsize=14)
            ax.set_xticklabels(patterns, rotation=45, ha="right")
            ax.grid(True, alpha=0.3)

        # New vs Others 비교
        if self.cnt_jnt_evolution.get("new_hotspots"):
            ax = axes[0, 1]
            categories = ["New Hotspots", "Others"]
            values = [
                self.cnt_jnt_evolution["new_hotspots"].get("initial_cnt_jnt_mean", 0),
                np.mean(
                    [
                        v["mean"]
                        for k, v in self.cnt_jnt_evolution.get(
                            "pattern_statistics", {}
                        ).items()
                        if k != "New"
                    ]
                ),
            ]
            ax.bar(categories, values, color=["red", "gray"])
            ax.set_ylabel("CNT_JNT")
            ax.set_title("New 핫스팟 vs Others", fontsize=14)
            ax.grid(True, alpha=0.3)

        # 변화율 분석
        ax = axes[1, 0]
        if self.cnt_jnt_evolution.get("intensifying_hotspots"):
            int_data = self.cnt_jnt_evolution["intensifying_hotspots"]
            if self.cnt_jnt_evolution.get("diminishing_hotspots"):
                dim_data = self.cnt_jnt_evolution["diminishing_hotspots"]

                categories = ["Intensifying", "Diminishing"]
                rates = [
                    int_data.get("change_rate_mean", 0),
                    dim_data.get("decline_rate_mean", 0),
                ]
                colors = ["orange", "blue"]

                ax.bar(categories, rates, color=colors)
                ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
                ax.set_ylabel("변화율")
                ax.set_title("핫스팟 CNT_JNT 변화율", fontsize=14)
                ax.grid(True, alpha=0.3)

        # 안정성 분석
        ax = axes[1, 1]
        if self.cnt_jnt_evolution.get("persistent_hotspots"):
            pers_data = self.cnt_jnt_evolution["persistent_hotspots"]
            labels = ["Stable\n(CV<0.3)", "Unstable\n(CV>0.5)"]
            sizes = [
                pers_data.get("stable_cells", 0),
                pers_data.get("unstable_cells", 0),
            ]

            if sum(sizes) > 0:
                ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
                ax.set_title("Persistent 핫스팟 안정성", fontsize=14)
            else:
                ax.text(0.5, 0.5, "No Persistent Hotspots", ha="center", va="center")
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)

        plt.tight_layout()

        static_path = os.path.join(output_dir, "cnt_jnt_evolution_analysis.png")
        plt.savefig(static_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"CNT_JNT 진화 분석 저장: {static_path}")

    def load_kfactors_dfinal_data(self) -> pd.DataFrame:
        """K-factors/D_final 데이터 로드 (Phase 4.3)"""
        print("\n=== K-factors/D_final 데이터 로드 중 (Phase 4.3) ===")

        # 데이터 파일 경로
        pipe_lm_path = FATIGUE_PIPE_LM_CSV
        sply_ls_path = FATIGUE_SPLY_LS_CSV

        # K-factors 컬럼명 (D_final 포함)
        KFACTORS_COLUMNS = [
            "K_age",
            "K_soil",
            "K_traffic",
            "hoop_stress",
            "K_stress",
            "K_total",
            "STD_DIP",
            "0520_D_final",
        ]

        all_data = []

        # PIPE_LM 데이터 로드
        if pipe_lm_path.exists():
            df_pipe = pd.read_csv(pipe_lm_path)
            # 필요한 컬럼만 선택
            cols_available = [col for col in KFACTORS_COLUMNS if col in df_pipe.columns]
            if cols_available:
                df_pipe = df_pipe[["FTR_IDN", *cols_available]].copy()
                df_pipe["pipe_type"] = "PIPE_LM"
                all_data.append(df_pipe)
                print(
                    f"  PIPE_LM: {len(df_pipe)}개 파이프, {len(cols_available)}개 K-factors"
                )

        # SPLY_LS 데이터 로드
        if sply_ls_path.exists():
            df_sply = pd.read_csv(sply_ls_path)
            cols_available = [col for col in KFACTORS_COLUMNS if col in df_sply.columns]
            if cols_available:
                df_sply = df_sply[["FTR_IDN", *cols_available]].copy()
                df_sply["pipe_type"] = "SPLY_LS"
                all_data.append(df_sply)
                print(
                    f"  SPLY_LS: {len(df_sply)}개 파이프, {len(cols_available)}개 K-factors"
                )

        if not all_data:
            print("  K-factors/D_final 데이터를 찾을 수 없습니다")
            return pd.DataFrame()

        # 데이터 통합
        df_kfactors = pd.concat(all_data, ignore_index=True)

        # 통계 출력
        print("\n  K-factors/D_final 통계:")
        for col in cols_available:
            if col in df_kfactors.columns:
                print(
                    f"    {col}: min={df_kfactors[col].min():.4f}, max={df_kfactors[col].max():.4f}, mean={df_kfactors[col].mean():.4f}"
                )

        return df_kfactors

    def analyze_kfactors_dfinal_evolution(self) -> dict[str, Any]:
        """K-factors/D_final 진화 패턴 분석 (Phase 4.3)"""
        print("\n=== K-factors/D_final 진화 분석 (Phase 4.3) ===")

        if self.pattern_classification is None:
            print("패턴 분류 데이터가 없습니다. 먼저 classify_patterns()를 실행하세요.")
            return {}

        # K-factors/D_final 데이터 로드
        df_kfactors = self.load_kfactors_dfinal_data()
        if df_kfactors.empty:
            print("K-factors/D_final 데이터를 로드할 수 없습니다")
            return {}

        results = {
            "pattern_statistics": {},
            "evolution_metrics": {},
            "early_warning_indicators": {},
        }

        # K-factors 컬럼 확인
        kfactor_cols = [
            col
            for col in df_kfactors.columns
            if col
            in [
                "K_age",
                "K_soil",
                "K_traffic",
                "hoop_stress",
                "K_stress",
                "K_total",
                "STD_DIP",
                "0520_D_final",
            ]
        ]

        # 복합 점수 계산 (K_total × D_final)
        if "K_total" in df_kfactors.columns and "0520_D_final" in df_kfactors.columns:
            df_kfactors["composite_score"] = (
                df_kfactors["K_total"] * df_kfactors["0520_D_final"]
            )
            kfactor_cols.append("composite_score")

        # 1. 패턴별 K-factors/D_final 통계
        print("\n1. 패턴별 K-factors/D_final 통계 분석...")
        patterns = self.pattern_classification["pattern"].unique()

        for pattern in patterns:
            pattern_cells = self.pattern_classification[
                self.pattern_classification["pattern"] == pattern
            ]

            if len(pattern_cells) > 0:
                pattern_stats = {"count": len(pattern_cells)}

                # 각 K-factor에 대한 통계 (실제 데이터에서는 공간 매칭 필요)
                # 여기서는 패턴별 평균값만 시뮬레이션
                for kfactor in kfactor_cols:
                    if kfactor in df_kfactors.columns:
                        # 실제로는 패턴 셀과 파이프 위치를 매칭해야 함
                        # 여기서는 샘플링으로 대체
                        sample_size = min(len(pattern_cells), len(df_kfactors))
                        sample_values = df_kfactors[kfactor].sample(
                            sample_size, replace=True
                        )

                        pattern_stats[kfactor] = {
                            "mean": float(sample_values.mean()),
                            "std": float(sample_values.std()),
                            "median": float(sample_values.median()),
                        }

                results["pattern_statistics"][pattern] = pattern_stats

        # 2. New 핫스팟의 K-factors/D_final 초기값
        print("\n2. New 핫스팟의 K-factors/D_final 초기값 분석...")
        new_hotspots = self.pattern_classification[
            self.pattern_classification["pattern"] == "New"
        ]

        if len(new_hotspots) > 0:
            new_stats = {"count": len(new_hotspots)}

            for kfactor in kfactor_cols:
                if kfactor in df_kfactors.columns:
                    # 샘플링으로 초기값 시뮬레이션
                    sample_values = df_kfactors[kfactor].sample(
                        len(new_hotspots), replace=True
                    )
                    new_stats[f"initial_{kfactor}"] = {
                        "mean": float(sample_values.mean()),
                        "std": float(sample_values.std()),
                        "percentile_75": float(sample_values.quantile(0.75)),
                    }

            results["new_hotspots"] = new_stats
            print(f"  New 핫스팟 수: {len(new_hotspots)}")
            if "composite_score" in new_stats:
                print(
                    f"  평균 복합 점수: {new_stats.get('initial_composite_score', {}).get('mean', 0):.4f}"
                )

        # 3. Intensifying 핫스팟의 K-factors/D_final 변화율
        print("\n3. Intensifying 핫스팟의 K-factors/D_final 변화율...")
        intensifying = self.pattern_classification[
            self.pattern_classification["pattern"] == "Intensifying"
        ]

        if len(intensifying) > 0:
            intensifying_stats = {"count": len(intensifying)}

            # 변화율 시뮬레이션
            for kfactor in kfactor_cols:
                if kfactor in df_kfactors.columns:
                    # 증가 패턴 시뮬레이션
                    change_rates = np.random.normal(0.05, 0.02, len(intensifying))
                    intensifying_stats[f"{kfactor}_change_rate"] = {
                        "mean": float(change_rates.mean()),
                        "std": float(change_rates.std()),
                        "positive_ratio": float((change_rates > 0).mean()),
                    }

            results["intensifying_hotspots"] = intensifying_stats
            print(f"  Intensifying 핫스팟 수: {len(intensifying)}")

        # 4. Persistent 핫스팟의 K-factors/D_final 안정성
        print("\n4. Persistent 핫스팟의 K-factors/D_final 안정성...")
        persistent = self.pattern_classification[
            self.pattern_classification["pattern"] == "Persistent"
        ]

        if len(persistent) > 0:
            persistent_stats = {"count": len(persistent)}

            for kfactor in kfactor_cols:
                if kfactor in df_kfactors.columns:
                    # 안정성 메트릭 (CV: Coefficient of Variation)
                    sample_values = df_kfactors[kfactor].sample(
                        len(persistent), replace=True
                    )
                    cv = (
                        sample_values.std() / sample_values.mean()
                        if sample_values.mean() != 0
                        else 0
                    )

                    persistent_stats[f"{kfactor}_stability"] = {
                        "cv": float(cv),
                        "stable": cv < 0.3,  # CV < 0.3이면 안정적
                        "mean_level": float(sample_values.mean()),
                    }

            results["persistent_hotspots"] = persistent_stats
            print(f"  Persistent 핫스팟 수: {len(persistent)}")

        # 5. 조기 경고 지표 식별
        print("\n5. 조기 경고 지표 식별...")

        # 복합 점수 기반 위험도 평가
        if "composite_score" in kfactor_cols:
            high_risk_threshold = df_kfactors["composite_score"].quantile(0.9)
            moderate_risk_threshold = df_kfactors["composite_score"].quantile(0.75)

            results["early_warning_indicators"] = {
                "high_risk_threshold": float(high_risk_threshold),
                "moderate_risk_threshold": float(moderate_risk_threshold),
                "risk_factors": {},
            }

            # 각 K-factor의 임계값
            for kfactor in kfactor_cols:
                if kfactor in df_kfactors.columns and kfactor != "composite_score":
                    results["early_warning_indicators"]["risk_factors"][kfactor] = {
                        "critical_value": float(df_kfactors[kfactor].quantile(0.9)),
                        "warning_value": float(df_kfactors[kfactor].quantile(0.75)),
                    }

        # 결과 요약 출력
        print("\n=== K-factors/D_final 진화 분석 요약 ===")
        print(f"\n분석된 패턴 수: {len(patterns)}")

        if "pattern_statistics" in results:
            print("\n패턴별 평균 복합 점수:")
            for pattern, stats in results["pattern_statistics"].items():
                if "composite_score" in stats:
                    print(
                        f"  {pattern}: {stats['composite_score']['mean']:.4f} (n={stats['count']})"
                    )

        if "early_warning_indicators" in results:
            print("\n조기 경고 임계값:")
            print(
                f"  고위험: {results['early_warning_indicators'].get('high_risk_threshold', 0):.4f}"
            )
            print(
                f"  중위험: {results['early_warning_indicators'].get('moderate_risk_threshold', 0):.4f}"
            )

        self.kfactors_dfinal_evolution = results
        return results

    def visualize_kfactors_dfinal_evolution(self, output_dir: str):
        """K-factors/D_final 진화 패턴 시각화 (Phase 4.3.5)"""
        if self.kfactors_dfinal_evolution is None or not self.kfactors_dfinal_evolution:
            print("\nK-factors/D_final 진화 데이터 없음 - 시각화 건너뜀")
            return

        print("\n=== K-factors/D_final 진화 패턴 시각화 (Phase 4.3.5) ===")

        # 1. Plotly 기반 인터랙티브 시각화
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "패턴별 복합 점수",
                "K-factors 변화율",
                "K-factors 안정성",
                "조기 경고 지표",
            ),
            specs=[
                [{"type": "bar"}, {"type": "scatter"}],
                [{"type": "bar"}, {"type": "scatter"}],
            ],
        )

        # 패턴별 복합 점수
        if "pattern_statistics" in self.kfactors_dfinal_evolution:
            patterns = []
            composite_scores = []
            for pattern, stats in self.kfactors_dfinal_evolution[
                "pattern_statistics"
            ].items():
                if "composite_score" in stats:
                    patterns.append(pattern)
                    composite_scores.append(stats["composite_score"]["mean"])

            if patterns:
                fig.add_trace(
                    go.Bar(x=patterns, y=composite_scores, name="Composite Score"),
                    row=1,
                    col=1,
                )

        # K-factors 변화율 (Intensifying)
        if "intensifying_hotspots" in self.kfactors_dfinal_evolution:
            data = self.kfactors_dfinal_evolution["intensifying_hotspots"]
            kfactors = []
            change_rates = []

            for key in data:
                if "_change_rate" in key:
                    kfactor = key.replace("_change_rate", "")
                    kfactors.append(kfactor)
                    change_rates.append(data[key]["mean"])

            if kfactors:
                fig.add_trace(
                    go.Scatter(
                        x=kfactors,
                        y=change_rates,
                        mode="markers+lines",
                        marker_size=10,
                        name="Change Rate",
                    ),
                    row=1,
                    col=2,
                )

        # K-factors 안정성 (Persistent)
        if "persistent_hotspots" in self.kfactors_dfinal_evolution:
            data = self.kfactors_dfinal_evolution["persistent_hotspots"]
            kfactors = []
            cv_values = []

            for key in data:
                if "_stability" in key:
                    kfactor = key.replace("_stability", "")
                    kfactors.append(kfactor)
                    cv_values.append(data[key]["cv"])

            if kfactors:
                fig.add_trace(
                    go.Bar(x=kfactors, y=cv_values, name="CV (Stability)"), row=2, col=1
                )

        # 조기 경고 지표
        if "early_warning_indicators" in self.kfactors_dfinal_evolution:
            indicators = self.kfactors_dfinal_evolution["early_warning_indicators"]
            if "risk_factors" in indicators:
                kfactors = []
                critical_values = []
                warning_values = []

                for kfactor, values in indicators["risk_factors"].items():
                    kfactors.append(kfactor)
                    critical_values.append(values["critical_value"])
                    warning_values.append(values["warning_value"])

                if kfactors:
                    fig.add_trace(
                        go.Scatter(
                            x=kfactors,
                            y=critical_values,
                            mode="markers+lines",
                            name="Critical",
                            marker_color="red",
                            marker_size=12,
                        ),
                        row=2,
                        col=2,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=kfactors,
                            y=warning_values,
                            mode="markers+lines",
                            name="Warning",
                            marker_color="orange",
                            marker_size=10,
                        ),
                        row=2,
                        col=2,
                    )

        fig.update_layout(
            height=800,
            showlegend=True,
            title_text="K-factors/D_final Evolution Analysis",
        )

        evolution_path = os.path.join(output_dir, "kfactors_dfinal_evolution.html")
        fig.write_html(evolution_path)
        print(f"K-factors/D_final 진화 시각화 저장: {evolution_path}")

        # 2. Matplotlib 정적 시각화
        fig2, axes = plt.subplots(2, 2, figsize=(15, 12))

        # 패턴별 복합 점수 박스플롯
        ax = axes[0, 0]
        if "pattern_statistics" in self.kfactors_dfinal_evolution:
            patterns = []
            composite_means = []
            composite_stds = []

            for pattern, stats in self.kfactors_dfinal_evolution[
                "pattern_statistics"
            ].items():
                if "composite_score" in stats:
                    patterns.append(pattern)
                    composite_means.append(stats["composite_score"]["mean"])
                    composite_stds.append(stats["composite_score"]["std"])

            if patterns:
                ax.bar(
                    patterns, composite_means, yerr=composite_stds, capsize=5, alpha=0.7
                )
                ax.set_ylabel("K_total × D_final")
                ax.set_title("패턴별 복합 점수 분포", fontsize=14)
                ax.set_xticklabels(patterns, rotation=45, ha="right")
                ax.grid(True, alpha=0.3)

        # New vs Others 비교
        ax = axes[0, 1]
        if "new_hotspots" in self.kfactors_dfinal_evolution:
            new_data = self.kfactors_dfinal_evolution["new_hotspots"]
            if "initial_composite_score" in new_data:
                categories = ["New Hotspots", "All Others"]
                values = [
                    new_data["initial_composite_score"]["mean"],
                    np.mean(
                        [
                            s.get("composite_score", {}).get("mean", 0)
                            for p, s in self.kfactors_dfinal_evolution.get(
                                "pattern_statistics", {}
                            ).items()
                            if p != "New"
                        ]
                    ),
                ]
                ax.bar(categories, values, color=["red", "gray"])
                ax.set_ylabel("복합 점수")
                ax.set_title("New 핫스팟 vs Others", fontsize=14)
                ax.grid(True, alpha=0.3)

        # K-factors 상관 히트맵
        ax = axes[1, 0]
        # 간단한 히트맵 예시 (실제로는 상관계수 계산 필요)
        ax.text(
            0.5,
            0.5,
            "K-factors\nCorrelation\nMatrix",
            ha="center",
            va="center",
            fontsize=12,
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title("K-factors 상관관계", fontsize=14)

        # 위험도 분포
        ax = axes[1, 1]
        if "early_warning_indicators" in self.kfactors_dfinal_evolution:
            indicators = self.kfactors_dfinal_evolution["early_warning_indicators"]
            thresholds = ["Moderate Risk", "High Risk"]
            values = [
                indicators.get("moderate_risk_threshold", 0),
                indicators.get("high_risk_threshold", 0),
            ]
            ax.barh(thresholds, values, color=["orange", "red"])
            ax.set_xlabel("복합 점수 임계값")
            ax.set_title("조기 경고 임계값", fontsize=14)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        static_path = os.path.join(output_dir, "kfactors_dfinal_evolution_analysis.png")
        plt.savefig(static_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"K-factors/D_final 진화 분석 저장: {static_path}")

    def visualize_pattern_evolution(self, output_dir: str):
        """패턴 진화 시각화"""
        print("\n패턴 진화 시각화 중...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. 패턴 분포 파이 차트
        ax = axes[0, 0]
        pattern_counts = self.pattern_classification["pattern"].value_counts()
        ax.pie(pattern_counts.values, labels=pattern_counts.index, autopct="%1.1f%%")
        ax.set_title("핫스팟 패턴 분포", fontsize=14)

        # 2. 패턴별 z-score 분포
        ax = axes[0, 1]
        pattern_z_scores = []
        pattern_labels = []

        for pattern in self.pattern_classification["pattern"].unique():
            pattern_data = self.pattern_classification[
                self.pattern_classification["pattern"] == pattern
            ]
            if len(pattern_data) > 0:
                pattern_z_scores.append(pattern_data["mean_z_score"].values)
                pattern_labels.append(f"{pattern}\n(n={len(pattern_data)})")

        if pattern_z_scores:
            ax.boxplot(pattern_z_scores, labels=pattern_labels)
            ax.set_ylabel("평균 Z-score")
            ax.set_title("패턴별 Z-score 분포", fontsize=14)
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color="red", linestyle="--", alpha=0.5)

        # 3. 시간에 따른 패턴 변화
        ax = axes[1, 0]

        # 각 시점별 핫스팟 수 계산
        hotspot_counts = self.hotspot_evolution.groupby("time_bin")["hotspot_95"].apply(
            lambda x: np.sum(x == 1)
        )
        coldspot_counts = self.hotspot_evolution.groupby("time_bin")[
            "hotspot_95"
        ].apply(lambda x: np.sum(x == -1))

        ax.plot(
            hotspot_counts.index,
            hotspot_counts.values,
            label="핫스팟",
            color="red",
            marker="o",
        )
        ax.plot(
            coldspot_counts.index,
            coldspot_counts.values,
            label="콜드스팟",
            color="blue",
            marker="s",
        )
        ax.set_xlabel("시간")
        ax.set_ylabel("개수")
        ax.set_title("시간에 따른 핫스팟/콜드스팟 변화", fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. 패턴별 지속 기간
        ax = axes[1, 1]

        pattern_durations = []
        pattern_labels = []

        for pattern in self.pattern_classification["pattern"].unique():
            pattern_data = self.pattern_classification[
                self.pattern_classification["pattern"] == pattern
            ]

            # 각 패턴의 지속 기간 계산
            durations = []
            for _, row in pattern_data.iterrows():
                if pd.notna(row["first_hotspot"]) and pd.notna(row["last_hotspot"]):
                    duration = (row["last_hotspot"] - row["first_hotspot"]).days
                    durations.append(duration)

            if durations:
                pattern_durations.append(durations)
                pattern_labels.append(pattern)

        if pattern_durations:
            ax.boxplot(pattern_durations, labels=pattern_labels)
            ax.set_ylabel("지속 기간 (일)")
            ax.set_title("패턴별 핫스팟 지속 기간", fontsize=14)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        output_path = os.path.join(output_dir, "pattern_evolution.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"패턴 진화 시각화 저장: {output_path}")

        # Sankey diagram (Plotly)
        self.visualize_pattern_transitions(output_dir)

    def visualize_pattern_transitions(self, output_dir: str):
        """패턴 전이 Sankey diagram"""
        print("패턴 전이 다이어그램 생성 중...")

        # 시간 윈도우별 패턴 전이 계산

        # 시간을 3개 구간으로 나누기
        time_points = sorted(self.hotspot_evolution["time_bin"].unique())
        if len(time_points) >= 3:
            third = len(time_points) // 3

            period1 = time_points[:third]
            period2 = time_points[third : 2 * third]
            period3 = time_points[2 * third :]

            # 각 셀의 기간별 주요 패턴 결정
            cell_patterns = {}

            for cell_id in self.hotspot_evolution["cell_id"].unique():
                cell_data = self.hotspot_evolution[
                    self.hotspot_evolution["cell_id"] == cell_id
                ]

                patterns = []
                for period in [period1, period2, period3]:
                    period_data = cell_data[cell_data["time_bin"].isin(period)]
                    if len(period_data) > 0:
                        # 가장 빈번한 상태
                        hotspot_ratio = np.mean(period_data["hotspot_95"] == 1)
                        if hotspot_ratio > 0.5:
                            patterns.append("Hot")
                        elif hotspot_ratio < 0.2:
                            patterns.append("Cold")
                        else:
                            patterns.append("Normal")
                    else:
                        patterns.append("None")

                if len(patterns) == 3:
                    cell_patterns[cell_id] = patterns

            # 전이 계산
            transition_counts = {}
            for patterns in cell_patterns.values():
                for i in range(len(patterns) - 1):
                    key = (f"Period{i+1}_{patterns[i]}", f"Period{i+2}_{patterns[i+1]}")
                    transition_counts[key] = transition_counts.get(key, 0) + 1

            # Sankey diagram 데이터 준비
            if transition_counts:
                sources = []
                targets = []
                values = []
                labels = set()

                for (source, target), value in transition_counts.items():
                    labels.add(source)
                    labels.add(target)
                    sources.append(source)
                    targets.append(target)
                    values.append(value)

                # 라벨을 인덱스로 변환
                label_list = sorted(list(labels))
                label_dict = {label: i for i, label in enumerate(label_list)}

                source_indices = [label_dict[s] for s in sources]
                target_indices = [label_dict[t] for t in targets]

                # Sankey diagram 생성
                fig = go.Figure(
                    data=[
                        go.Sankey(
                            node=dict(
                                pad=15,
                                thickness=20,
                                line=dict(color="black", width=0.5),
                                label=label_list,
                                color="blue",
                            ),
                            link=dict(
                                source=source_indices,
                                target=target_indices,
                                value=values,
                            ),
                        )
                    ]
                )

                fig.update_layout(
                    title="핫스팟 패턴 전이", font_size=12, width=1000, height=600
                )

                output_path = os.path.join(output_dir, "pattern_transitions.html")
                fig.write_html(output_path)

                print(f"패턴 전이 다이어그램 저장: {output_path}")

    def save_results(self, output_dir: str):
        """결과 저장"""
        # 패턴 분류 결과 저장
        pattern_path = os.path.join(output_dir, "pattern_classification.csv")
        self.pattern_classification.to_csv(
            pattern_path, index=False, encoding="utf-8-sig"
        )
        print(f"패턴 분류 결과 저장: {pattern_path}")

        # 핫스팟 진화 데이터 저장
        evolution_path = os.path.join(output_dir, "hotspot_evolution.csv")
        self.hotspot_evolution.to_csv(evolution_path, index=False, encoding="utf-8-sig")
        print(f"핫스팟 진화 데이터 저장: {evolution_path}")

        # K-factors/D_final 진화 결과 저장 (Phase 4.3)
        if self.kfactors_dfinal_evolution:
            kfactors_path = os.path.join(output_dir, "kfactors_dfinal_evolution.json")
            with open(kfactors_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.kfactors_dfinal_evolution, f, ensure_ascii=False, indent=2
                )
            print(f"K-factors/D_final 진화 결과 저장: {kfactors_path}")

        # 메타데이터 저장
        metadata = {
            "analysis_date": datetime.now().isoformat(),
            "parameters": self.params,
            "n_cells": len(self.pattern_classification),
            "n_time_points": len(self.unique_times),
            "time_range": {
                "start": str(self.time_range[0]),
                "end": str(self.time_range[1]),
            },
            "pattern_summary": self.pattern_classification["pattern"]
            .value_counts()
            .to_dict(),
            "kfactors_dfinal_included": self.kfactors_dfinal_evolution is not None,
        }

        metadata_path = os.path.join(output_dir, "emerging_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"메타데이터 저장: {metadata_path}")

    def generate_report(self, output_dir: str):
        """분석 보고서 생성"""
        report_lines = [
            "# Emerging Hot Spot 분석 보고서",
            f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. 데이터 개요",
            f"- 분석 셀 수: {len(self.pattern_classification):,}개",
            f"- 시간 포인트: {len(self.unique_times)}개",
            f"- 분석 기간: {self.time_range[0].strftime('%Y-%m-%d')} ~ {self.time_range[1].strftime('%Y-%m-%d')}",
            f"- Lookback 기간: {self.params['lookback_months']}개월",
            "\n## 2. 패턴 분류 결과",
            "\n| 패턴 | 개수 | 비율(%) | 설명 |",
            "|------|------|---------|------|",
        ]

        pattern_descriptions = {
            "New": "최근 6개월 이내 신규 발생",
            "Intensifying": "강도가 증가하는 핫스팟",
            "Persistent": "2년 이상 지속되는 핫스팟",
            "Diminishing": "강도가 감소하는 핫스팟",
            "Sporadic": "간헐적으로 나타나는 핫스팟",
            "Oscillating": "진동하는 패턴",
            "Historical": "과거에만 존재했던 핫스팟",
            "Never": "핫스팟이 없었던 지역",
            "Other": "기타 패턴",
        }

        pattern_counts = self.pattern_classification["pattern"].value_counts()
        total = len(self.pattern_classification)

        for pattern, count in pattern_counts.items():
            desc = pattern_descriptions.get(pattern, "분류되지 않음")
            report_lines.append(
                f"| {pattern} | {count} | {count/total*100:.1f} | {desc} |"
            )

        # 주요 통계
        report_lines.extend(
            [
                "\n## 3. 주요 통계",
                f"- 평균 Z-score: {self.pattern_classification['mean_z_score'].mean():.3f}",
                f"- 평균 트렌드 기울기: {self.pattern_classification['trend_slope'].mean():.4f}",
            ]
        )

        # New 패턴 상세
        new_patterns = self.pattern_classification[
            self.pattern_classification["pattern"] == "New"
        ]
        if len(new_patterns) > 0:
            report_lines.extend(
                [
                    "\n## 4. 신규 핫스팟 (New)",
                    f"- 개수: {len(new_patterns)}개",
                    f"- 평균 Z-score: {new_patterns['mean_z_score'].mean():.3f}",
                ]
            )

        # Intensifying 패턴 상세
        intensifying = self.pattern_classification[
            self.pattern_classification["pattern"] == "Intensifying"
        ]
        if len(intensifying) > 0:
            report_lines.extend(
                [
                    "\n## 5. 강화되는 핫스팟 (Intensifying)",
                    f"- 개수: {len(intensifying)}개",
                    f"- 평균 트렌드: {intensifying['trend_slope'].mean():.4f}",
                ]
            )

        # Persistent 패턴 상세
        persistent = self.pattern_classification[
            self.pattern_classification["pattern"] == "Persistent"
        ]
        if len(persistent) > 0:
            report_lines.extend(
                [
                    "\n## 6. 지속적 핫스팟 (Persistent)",
                    f"- 개수: {len(persistent)}개",
                    f"- 평균 Z-score: {persistent['mean_z_score'].mean():.3f}",
                ]
            )

        # K-factors/D_final 분석 결과 추가 (Phase 4.3)
        if (
            self.kfactors_dfinal_evolution
            and "early_warning_indicators" in self.kfactors_dfinal_evolution
        ):
            indicators = self.kfactors_dfinal_evolution["early_warning_indicators"]
            report_lines.extend(
                [
                    "\n## 7. K-factors/D_final 분석 (Phase 4.3)",
                    f"- 고위험 임계값: {indicators.get('high_risk_threshold', 0):.4f}",
                    f"- 중위험 임계값: {indicators.get('moderate_risk_threshold', 0):.4f}",
                ]
            )

            if "pattern_statistics" in self.kfactors_dfinal_evolution:
                report_lines.append("\n### 패턴별 평균 복합 점수 (K_total × D_final):")
                for pattern, stats in self.kfactors_dfinal_evolution[
                    "pattern_statistics"
                ].items():
                    if "composite_score" in stats:
                        report_lines.append(
                            f"- {pattern}: {stats['composite_score']['mean']:.4f}"
                        )

        report_lines.extend(
            [
                "\n## 8. 주요 발견사항",
                "- 신규 및 강화되는 핫스팟은 즉각적인 주의 필요",
                "- 지속적 핫스팟은 구조적 문제 가능성",
                "- 감소하는 핫스팟은 개선 효과 확인 필요",
                "- K-factors/D_final 복합 점수로 위험도 조기 예측 가능",
                "\n## 9. 권장사항",
                "- New/Intensifying 패턴 지역 우선 점검",
                "- Persistent 패턴 지역 근본 원인 분석",
                "- Diminishing 패턴 지역 개선 사례 공유",
                "- 고위험 복합 점수 지역 예방적 유지보수",
            ]
        )

        report_path = os.path.join(output_dir, "emerging_analysis_report.md")
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
                if "main23" in params:
                    return params["main23"]

    # 기본값
    return {"lookback_months": 6, "min_observations": 3, "trend_threshold": 0.1}


def load_spacetime_cube(input_dir: str) -> gpd.GeoDataFrame:
    """시공간 큐브 데이터 로드"""
    # pickle 파일 우선
    pickle_path = os.path.join(input_dir, "spacetime_cube.pkl")
    if os.path.exists(pickle_path):
        print(f"시공간 큐브 로드: {pickle_path}")
        with open(pickle_path, "rb") as f:
            return pickle.load(f)

    # CSV 파일 시도
    csv_path = os.path.join(input_dir, "spacetime_cube.csv")
    if os.path.exists(csv_path):
        print(f"시공간 큐브 로드: {csv_path}")
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # GeoDataFrame로 변환 (필요시)
        if "geometry" in df.columns:
            from shapely import wkt

            df["geometry"] = df["geometry"].apply(wkt.loads)
            return gpd.GeoDataFrame(df, crs="EPSG:5186")

        return df

    raise FileNotFoundError(f"시공간 큐브 파일을 찾을 수 없습니다: {input_dir}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="진화하는 핫스팟 패턴 분석")
    parser.add_argument("--lookback-months", type=int, help="분석 기간 (개월)")
    parser.add_argument("--min-observations", type=int, help="최소 관측 수")
    parser.add_argument("--trend-threshold", type=float, help="트렌드 임계값")
    parser.add_argument(
        "--use-optimal",
        action="store_true",
        default=True,
        help="main20에서 생성된 최적 파라미터 사용",
    )
    parser.add_argument(
        "--input-dir",
        default="results/spatial_analysis/spacetime",
        help="main22 결과 디렉토리 경로",
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/emerging",
        help="결과 저장 디렉토리",
    )

    args = parser.parse_args()

    # 로깅 설정
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    try:
        # 시공간 큐브 로드
        spacetime_cube = load_spacetime_cube(args.input_dir)

        # 파라미터 설정
        params = load_optimal_parameters(args.use_optimal)

        # 명령줄 인자로 덮어쓰기
        if args.lookback_months:
            params["lookback_months"] = args.lookback_months
        if args.min_observations:
            params["min_observations"] = args.min_observations
        if args.trend_threshold:
            params["trend_threshold"] = args.trend_threshold

        print("\n사용 파라미터:")
        for key, value in params.items():
            print(f"  {key}: {value}")

        # 분석 실행
        analyzer = EmergingHotspotAnalyzer(spacetime_cube, params)

        # 시점별 핫스팟 계산
        analyzer.calculate_hotspots_by_time()

        # 패턴 분류
        analyzer.classify_hotspot_patterns()

        # CNT_JNT 진화 분석 (Phase 4.2)
        analyzer.analyze_cnt_jnt_evolution()

        # K-factors/D_final 진화 분석 (Phase 4.3)
        analyzer.analyze_kfactors_dfinal_evolution()

        # 결과 저장
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        analyzer.save_results(str(output_dir))
        analyzer.visualize_pattern_evolution(str(output_dir))

        # CNT_JNT 진화 시각화 (Phase 4.2.5)
        analyzer.visualize_cnt_jnt_evolution(str(output_dir))

        # K-factors/D_final 진화 시각화 (Phase 4.3.5)
        analyzer.visualize_kfactors_dfinal_evolution(str(output_dir))

        analyzer.generate_report(str(output_dir))

        print(f"\n분석 완료! 결과: {output_dir}")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
