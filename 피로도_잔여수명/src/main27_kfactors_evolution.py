#!/usr/bin/env python3
"""
Phase 9: K-factors/D_final Evolution Analysis
K-factors와 D_final의 시간적 변화 추적 및 4D 시각화
"""

import argparse
import json
import pickle

# 프로젝트 모듈
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats

sys.path.append(str(Path(__file__).parent.parent))

from src.common.config import RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font

warnings.filterwarnings("ignore")


class KFactorsEvolutionAnalyzer:
    """K-factors/D_final 진화 분석기"""

    def __init__(
        self,
        spacetime_cube_path: str,
        kfactors_grid_path: str,
        time_window: int = 12,
        output_dir: str | None = None,
    ):
        """
        초기화

        Args:
            spacetime_cube_path: Space-time cube pickle 파일 경로
            kfactors_grid_path: K-factors/D_final grid CSV 경로
            time_window: 분석 시간 윈도우 (개월)
            output_dir: 출력 디렉토리
        """
        self.spacetime_cube_path = Path(spacetime_cube_path)
        self.kfactors_grid_path = Path(kfactors_grid_path)
        self.time_window = time_window
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else RESULTS_DIR / "spatial_analysis" / "kfactors_evolution"
        )

        # 한글 폰트 설정
        setup_korean_font()

        # 데이터 저장소
        self.spacetime_cube = None
        self.kfactors_grid = None
        self.evolution_data = {}
        self.acceleration_zones = []

    def load_data(self) -> bool:
        """데이터 로드"""
        print("\n=== K-factors/D_final Evolution 데이터 로드 중 ===")

        # Space-time cube 로드
        if self.spacetime_cube_path.exists():
            with open(self.spacetime_cube_path, "rb") as f:
                self.spacetime_cube = pickle.load(f)
            print(f"✓ Space-time cube 로드: {len(self.spacetime_cube)} 셀")
        else:
            print(f"✗ Space-time cube 파일 없음: {self.spacetime_cube_path}")
            return False

        # K-factors grid 로드
        if self.kfactors_grid_path.exists():
            self.kfactors_grid = pd.read_csv(self.kfactors_grid_path)
            print(f"✓ K-factors grid 로드: {len(self.kfactors_grid)} 그리드")
        else:
            print(f"✗ K-factors grid 파일 없음: {self.kfactors_grid_path}")
            return False

        return True

    def analyze_temporal_evolution(self) -> dict[str, Any]:
        """K-factors/D_final 시간적 진화 분석"""
        print("\n=== K-factors/D_final 시간적 진화 분석 ===")

        results = {
            "evolution_metrics": {},
            "acceleration_zones": [],
            "seasonal_patterns": {},
            "trend_analysis": {},
        }

        # K-factors 컬럼 찾기
        kfactor_cols = []
        for col in ["K_total", "K_age", "K_soil", "K_traffic", "K_stress"]:
            # 최대값, 최소값, 평균값 모두 확인
            if f"mean_{col}" in self.spacetime_cube.columns:
                kfactor_cols.append(("mean", col))
            if f"max_{col}" in self.spacetime_cube.columns:
                kfactor_cols.append(("max", col))
            if f"min_{col}" in self.spacetime_cube.columns:
                kfactor_cols.append(("min", col))

        # D_final 컬럼 찾기
        dfinal_cols = []
        for col in ["D_final", "0520_D_final"]:
            if f"mean_{col}" in self.spacetime_cube.columns:
                dfinal_cols.append(("mean", col))
            if f"max_{col}" in self.spacetime_cube.columns:
                dfinal_cols.append(("max", col))
            if f"min_{col}" in self.spacetime_cube.columns:
                dfinal_cols.append(("min", col))

        print(f"분석 가능한 K-factors: {len(kfactor_cols)}개")
        print(f"분석 가능한 D_final: {len(dfinal_cols)}개")

        # 1. 시간별 진화 메트릭 계산
        print("\n1. 시간별 진화 메트릭 계산...")
        time_bins = sorted(self.spacetime_cube["time_bin"].unique())

        for stat_type, factor in kfactor_cols[:5]:  # 처음 5개만
            col_name = f"{stat_type}_{factor}"
            if col_name in self.spacetime_cube.columns:
                evolution = []
                for time_bin in time_bins:
                    time_data = self.spacetime_cube[
                        self.spacetime_cube["time_bin"] == time_bin
                    ]
                    valid_data = time_data[col_name].dropna()

                    if not valid_data.empty:
                        evolution.append(
                            {
                                "time": str(time_bin),
                                "mean": float(valid_data.mean()),
                                "std": float(valid_data.std()),
                                "max": float(valid_data.max()),
                                "min": float(valid_data.min()),
                                "count": len(valid_data),
                            }
                        )

                if evolution:
                    # 변화율 계산
                    changes = []
                    for i in range(1, len(evolution)):
                        if evolution[i - 1]["mean"] > 0:
                            change_rate = (
                                evolution[i]["mean"] - evolution[i - 1]["mean"]
                            ) / evolution[i - 1]["mean"]
                            changes.append(change_rate)

                    results["evolution_metrics"][col_name] = {
                        "timeline": evolution,
                        "avg_change_rate": float(np.mean(changes)) if changes else 0,
                        "max_change_rate": (
                            float(np.max(np.abs(changes))) if changes else 0
                        ),
                        "trend": (
                            "increasing"
                            if evolution[-1]["mean"] > evolution[0]["mean"]
                            else "decreasing"
                        ),
                    }

                    print(
                        f"  {col_name}: 평균 변화율={results['evolution_metrics'][col_name]['avg_change_rate']:.4f}"
                    )

        # 2. 가속 구역 식별 (K-factors/D_final이 급격히 증가하는 지역)
        print("\n2. 가속 구역 식별...")

        # K_total × D_final 복합 점수 계산

        if (
            "mean_K_total" in self.spacetime_cube.columns
            and "mean_D_final" in self.spacetime_cube.columns
        ):
            self.spacetime_cube["composite_score"] = (
                self.spacetime_cube["mean_K_total"]
                * self.spacetime_cube["mean_D_final"]
            )

            # 공간 그룹별로 가속도 계산
            spatial_groups = self.spacetime_cube.groupby(["grid_x", "grid_y"])

            for (x, y), group in spatial_groups:
                if len(group) >= 3:  # 최소 3개 시점 필요
                    group_sorted = group.sort_values("time_bin")
                    scores = group_sorted["composite_score"].dropna().values

                    if len(scores) >= 3:
                        # 가속도 계산 (2차 미분)
                        acceleration = (
                            np.diff(scores, n=2).mean() if len(scores) > 2 else 0
                        )

                        if acceleration > 0:  # 양의 가속도
                            results["acceleration_zones"].append(
                                {
                                    "grid_x": float(x),
                                    "grid_y": float(y),
                                    "acceleration": float(acceleration),
                                    "final_score": float(scores[-1]),
                                    "initial_score": float(scores[0]),
                                    "growth_rate": (
                                        float((scores[-1] - scores[0]) / scores[0])
                                        if scores[0] > 0
                                        else 0
                                    ),
                                }
                            )

            # 상위 10개 가속 구역
            results["acceleration_zones"] = sorted(
                results["acceleration_zones"],
                key=lambda x: x["acceleration"],
                reverse=True,
            )[:10]

            print(f"  식별된 가속 구역: {len(results['acceleration_zones'])}개")

            if results["acceleration_zones"]:
                top_zone = results["acceleration_zones"][0]
                print(
                    f"  최고 가속 구역: ({top_zone['grid_x']}, {top_zone['grid_y']}), "
                    f"가속도={top_zone['acceleration']:.6f}"
                )

        # 3. 계절별 패턴 분석
        print("\n3. 계절별 K-factors/D_final 패턴...")

        if "time_bin" in self.spacetime_cube.columns:
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

            for stat_type, factor in kfactor_cols[:3]:  # 주요 K-factors만
                col_name = f"{stat_type}_{factor}"
                if col_name in self.spacetime_cube.columns:
                    seasonal = self.spacetime_cube.groupby("season")[col_name].agg(
                        ["mean", "std"]
                    )
                    results["seasonal_patterns"][col_name] = seasonal.to_dict()

                    # 계절 변동성
                    seasonal_var = (
                        seasonal["mean"].std() / seasonal["mean"].mean()
                        if seasonal["mean"].mean() > 0
                        else 0
                    )
                    results["seasonal_patterns"][col_name]["variability"] = float(
                        seasonal_var
                    )

                    print(f"  {col_name}: 계절 변동성={seasonal_var:.3f}")

        # 4. 트렌드 분석
        print("\n4. 장기 트렌드 분석...")

        for stat_type, factor in kfactor_cols[:3]:
            col_name = f"{stat_type}_{factor}"
            if col_name in self.spacetime_cube.columns:
                monthly_avg = self.spacetime_cube.groupby("time_bin")[col_name].mean()

                if len(monthly_avg) >= 6:
                    # 선형 회귀
                    x = np.arange(len(monthly_avg))
                    y = monthly_avg.values
                    valid_mask = ~np.isnan(y)

                    if valid_mask.sum() >= 6:
                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            x[valid_mask], y[valid_mask]
                        )

                        results["trend_analysis"][col_name] = {
                            "slope": float(slope),
                            "r_squared": float(r_value**2),
                            "p_value": float(p_value),
                            "trend_strength": (
                                "strong"
                                if abs(r_value) > 0.7
                                else "moderate" if abs(r_value) > 0.4 else "weak"
                            ),
                        }

                        print(
                            f"  {col_name}: slope={slope:.6f}, R²={r_value**2:.3f}, p={p_value:.4f}"
                        )

        self.evolution_data = results
        return results

    def create_4d_visualization(self):
        """4D 시각화 생성 (3D 공간 + 시간)"""
        print("\n=== 4D 시각화 생성 중 ===")

        # 시간 순서대로 정렬
        time_bins = sorted(self.spacetime_cube["time_bin"].unique())

        # 복합 점수가 있는 경우만
        if "composite_score" not in self.spacetime_cube.columns:
            if (
                "mean_K_total" in self.spacetime_cube.columns
                and "mean_D_final" in self.spacetime_cube.columns
            ):
                self.spacetime_cube["composite_score"] = (
                    self.spacetime_cube["mean_K_total"]
                    * self.spacetime_cube["mean_D_final"]
                )
            else:
                print("복합 점수 계산 불가 - 시각화 건너뜀")
                return

        # 애니메이션 프레임 생성
        frames = []

        for i, time_bin in enumerate(time_bins[:24]):  # 최대 24개월
            time_data = self.spacetime_cube[self.spacetime_cube["time_bin"] == time_bin]

            if not time_data.empty:
                # 유효한 데이터만 필터링
                valid_data = time_data.dropna(
                    subset=["grid_x", "grid_y", "composite_score"]
                )

                if not valid_data.empty:
                    frame = go.Scatter3d(
                        x=valid_data["grid_x"],
                        y=valid_data["grid_y"],
                        z=valid_data["composite_score"],
                        mode="markers",
                        marker=dict(
                            size=8,
                            color=valid_data["composite_score"],
                            colorscale="RdYlBu_r",
                            showscale=True,
                            colorbar=dict(title="K×D Score"),
                        ),
                        text=[f"Score: {s:.2f}" for s in valid_data["composite_score"]],
                        hovertemplate="X: %{x}<br>Y: %{y}<br>%{text}<extra></extra>",
                        name=str(time_bin),
                    )
                    frames.append(go.Frame(data=[frame], name=str(i)))

        if frames:
            # 초기 프레임
            fig = go.Figure(data=frames[0].data)

            # 레이아웃 설정
            fig.update_layout(
                title="K-factors/D_final Evolution in 4D Space",
                scene=dict(
                    xaxis_title="X Grid",
                    yaxis_title="Y Grid",
                    zaxis_title="K×D Score",
                    camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
                ),
                updatemenus=[
                    {
                        "type": "buttons",
                        "showactive": False,
                        "buttons": [
                            {
                                "label": "Play",
                                "method": "animate",
                                "args": [
                                    None,
                                    {
                                        "frame": {"duration": 500, "redraw": True},
                                        "fromcurrent": True,
                                    },
                                ],
                            },
                            {
                                "label": "Pause",
                                "method": "animate",
                                "args": [
                                    [None],
                                    {
                                        "frame": {"duration": 0, "redraw": False},
                                        "mode": "immediate",
                                    },
                                ],
                            },
                        ],
                    }
                ],
                sliders=[
                    {
                        "steps": [
                            {
                                "args": [
                                    [f.name],
                                    {
                                        "frame": {"duration": 300, "redraw": True},
                                        "mode": "immediate",
                                    },
                                ],
                                "label": str(time_bins[int(f.name)])[:7],
                                "method": "animate",
                            }
                            for f in frames
                        ],
                        "active": 0,
                        "y": 0,
                        "len": 0.9,
                        "x": 0.1,
                        "xanchor": "left",
                        "yanchor": "top",
                    }
                ],
                height=700,
                width=900,
            )

            # 프레임 추가
            fig.frames = frames

            # 저장
            output_path = self.output_dir / "kfactors_evolution_4d.html"
            fig.write_html(str(output_path))
            print(f"4D 시각화 저장: {output_path}")

    def visualize_evolution(self):
        """진화 패턴 시각화"""
        print("\n=== 진화 패턴 시각화 ===")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. K-factors 시간별 진화
        ax = axes[0, 0]

        for i, (metric_name, metric_data) in enumerate(
            list(self.evolution_data["evolution_metrics"].items())[:5]
        ):
            if "timeline" in metric_data:
                timeline = metric_data["timeline"]
                [t["time"][:7] for t in timeline]  # YYYY-MM 형식
                means = [t["mean"] for t in timeline]

                ax.plot(
                    range(len(means)),
                    means,
                    marker="o",
                    label=metric_name.replace("_", " "),
                    linewidth=2,
                )

        ax.set_xlabel("시간")
        ax.set_ylabel("평균값")
        ax.set_title("K-factors/D_final 시간별 진화", fontsize=12, fontweight="bold")
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)

        # 2. 가속 구역 히트맵
        ax = axes[0, 1]

        if self.evolution_data["acceleration_zones"]:
            # 가속 구역 데이터를 히트맵으로 변환
            accel_zones = self.evolution_data["acceleration_zones"]

            # 그리드 생성
            x_coords = [z["grid_x"] for z in accel_zones]
            y_coords = [z["grid_y"] for z in accel_zones]
            accel_values = [z["acceleration"] for z in accel_zones]

            # 산점도로 표시
            scatter = ax.scatter(
                x_coords,
                y_coords,
                c=accel_values,
                s=200,
                cmap="Reds",
                alpha=0.7,
                edgecolors="black",
                linewidth=1,
            )
            plt.colorbar(scatter, ax=ax, label="가속도")

            ax.set_xlabel("X Grid Index")
            ax.set_ylabel("Y Grid Index")
            ax.set_title(
                "K-factors/D_final 가속 구역 (Top 10)", fontsize=12, fontweight="bold"
            )
            ax.grid(True, alpha=0.3)

        # 3. 계절별 패턴
        ax = axes[1, 0]

        if self.evolution_data["seasonal_patterns"]:
            seasons = ["Spring", "Summer", "Fall", "Winter"]

            # 첫 번째 metric의 계절별 평균값
            first_metric = next(iter(self.evolution_data["seasonal_patterns"].keys()))
            seasonal_data = self.evolution_data["seasonal_patterns"][first_metric]

            if "mean" in seasonal_data:
                means = [seasonal_data["mean"].get(s, 0) for s in seasons]
                colors = ["green", "yellow", "orange", "blue"]

                bars = ax.bar(
                    seasons, means, color=colors, alpha=0.7, edgecolor="black"
                )
                ax.set_ylabel("평균값")
                ax.set_title(
                    f"계절별 {first_metric} 패턴", fontsize=12, fontweight="bold"
                )
                ax.grid(True, alpha=0.3, axis="y")

                # 값 표시
                for bar, val in zip(bars, means, strict=False):
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{val:.2f}",
                        ha="center",
                        va="bottom",
                    )

        # 4. 트렌드 강도
        ax = axes[1, 1]

        if self.evolution_data["trend_analysis"]:
            metrics = []
            r_squared = []
            colors = []

            for metric, trend in self.evolution_data["trend_analysis"].items():
                metrics.append(metric.replace("_", " "))
                r_squared.append(trend["r_squared"])

                # 색상 결정
                if trend["slope"] > 0:
                    colors.append(
                        "red" if trend["trend_strength"] == "strong" else "orange"
                    )
                else:
                    colors.append(
                        "blue" if trend["trend_strength"] == "strong" else "lightblue"
                    )

            bars = ax.barh(
                metrics, r_squared, color=colors, alpha=0.7, edgecolor="black"
            )
            ax.set_xlabel("R² (트렌드 강도)")
            ax.set_title(
                "K-factors/D_final 트렌드 분석", fontsize=12, fontweight="bold"
            )
            ax.set_xlim([0, 1])
            ax.grid(True, alpha=0.3, axis="x")

            # 값 표시
            for bar, val in zip(bars, r_squared, strict=False):
                width = bar.get_width()
                ax.text(
                    width,
                    bar.get_y() + bar.get_height() / 2.0,
                    f"{val:.3f}",
                    ha="left",
                    va="center",
                )

        plt.suptitle(
            "K-factors/D_final Evolution Analysis",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()

        # 저장
        output_path = self.output_dir / "kfactors_evolution_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"진화 분석 시각화 저장: {output_path}")

    def generate_report(self):
        """분석 보고서 생성"""
        print("\n=== 분석 보고서 생성 중 ===")

        report_lines = [
            "# K-factors/D_final Evolution Analysis Report",
            f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. 분석 개요",
            f"- 분석 기간: {self.time_window}개월",
            f"- Space-time cube 셀 수: {len(self.spacetime_cube):,}개",
            f"- 분석된 메트릭 수: {len(self.evolution_data.get('evolution_metrics', {}))}개",
            "\n## 2. 주요 발견사항",
            "\n### 2.1 진화 메트릭",
        ]

        # 진화 메트릭 요약
        for metric, data in list(
            self.evolution_data.get("evolution_metrics", {}).items()
        )[:5]:
            if "avg_change_rate" in data:
                report_lines.append(
                    f"- **{metric}**: "
                    f"평균 변화율={data['avg_change_rate']:.4f}, "
                    f"트렌드={data['trend']}"
                )

        # 가속 구역
        report_lines.append("\n### 2.2 가속 구역 (Top 5)")
        accel_zones = self.evolution_data.get("acceleration_zones", [])[:5]

        if accel_zones:
            report_lines.append("\n| 순위 | X Index | Y Index | 가속도 | 성장률(%) |")
            report_lines.append("|------|---------|---------|--------|-----------|")

            for i, zone in enumerate(accel_zones, 1):
                growth_pct = zone["growth_rate"] * 100
                report_lines.append(
                    f"| {i} | {zone['grid_x']:.1f} | {zone['grid_y']:.1f} | "
                    f"{zone['acceleration']:.6f} | {growth_pct:.1f} |"
                )

        # 계절별 패턴
        report_lines.append("\n### 2.3 계절별 변동성")
        for metric, pattern in list(
            self.evolution_data.get("seasonal_patterns", {}).items()
        )[:3]:
            if "variability" in pattern:
                report_lines.append(
                    f"- **{metric}**: 변동성={pattern['variability']:.3f}"
                )

        # 트렌드 분석
        report_lines.append("\n### 2.4 장기 트렌드")
        for metric, trend in list(
            self.evolution_data.get("trend_analysis", {}).items()
        )[:5]:
            if "slope" in trend:
                report_lines.append(
                    f"- **{metric}**: "
                    f"기울기={trend['slope']:.6f}, "
                    f"R²={trend['r_squared']:.3f}, "
                    f"강도={trend['trend_strength']}"
                )

        # 권장사항
        report_lines.extend(
            [
                "\n## 3. 권장사항",
                "- 가속 구역에 대한 집중 모니터링 필요",
                "- 계절별 변동성이 높은 지역 예방 정비",
                "- 강한 증가 트렌드를 보이는 K-factors 관리",
                "- 복합 점수가 급증하는 지역 우선 점검",
            ]
        )

        # 파일 저장
        report_path = self.output_dir / "kfactors_evolution_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"보고서 저장: {report_path}")

    def save_results(self):
        """결과 저장"""
        print("\n=== 결과 저장 중 ===")

        # JSON 결과 저장
        json_path = self.output_dir / "kfactors_evolution_results.json"

        # numpy/pandas 타입 변환
        def convert_types(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.int64 | np.int32):
                return int(obj)
            if isinstance(obj, np.float64 | np.float32):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_types(item) for item in obj]
            return obj

        results_to_save = convert_types(self.evolution_data)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results_to_save, f, ensure_ascii=False, indent=2)

        print(f"JSON 결과 저장: {json_path}")

        # 가속 구역 CSV 저장
        if self.evolution_data.get("acceleration_zones"):
            accel_df = pd.DataFrame(self.evolution_data["acceleration_zones"])
            accel_path = self.output_dir / "acceleration_zones.csv"
            accel_df.to_csv(accel_path, index=False, encoding="utf-8-sig")
            print(f"가속 구역 저장: {accel_path}")

    def run(self):
        """전체 분석 실행"""
        print("\n" + "=" * 60)
        print("K-factors/D_final Evolution Analysis (Phase 9)")
        print("=" * 60)

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 데이터 로드
        if not self.load_data():
            print("데이터 로드 실패")
            return False

        # 진화 분석
        self.analyze_temporal_evolution()

        # 시각화
        self.create_4d_visualization()
        self.visualize_evolution()

        # 보고서 생성
        self.generate_report()

        # 결과 저장
        self.save_results()

        print("\n" + "=" * 60)
        print(f"분석 완료! 결과: {self.output_dir}")
        print("=" * 60)

        return True


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="K-factors/D_final Evolution Analysis (Phase 9)"
    )
    parser.add_argument(
        "--input-cube",
        default="results/spatial_analysis/spacetime/spacetime_cube.pkl",
        help="Space-time cube pickle 파일 경로",
    )
    parser.add_argument(
        "--kfactors-grid",
        default="results/spatial_analysis/0520_kfactors_dfinal_grid.csv",
        help="K-factors/D_final grid CSV 경로",
    )
    parser.add_argument(
        "--time-window", type=int, default=12, help="분석 시간 윈도우 (개월)"
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/kfactors_evolution",
        help="결과 저장 디렉토리",
    )

    args = parser.parse_args()

    # 분석기 생성 및 실행
    analyzer = KFactorsEvolutionAnalyzer(
        spacetime_cube_path=args.input_cube,
        kfactors_grid_path=args.kfactors_grid,
        time_window=args.time_window,
        output_dir=args.output_dir,
    )

    success = analyzer.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
