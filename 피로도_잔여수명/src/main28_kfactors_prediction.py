#!/usr/bin/env python3
"""
Phase 10: K-factors/D_final Prediction
K-factors/D_final 트렌드 기반 예측 유지보수
"""

import argparse
import json

# 프로젝트 모듈
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression

sys.path.append(str(Path(__file__).parent.parent))

from src.common.config import RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font

warnings.filterwarnings("ignore")


class KFactorsPredictionAnalyzer:
    """K-factors/D_final 예측 분석기"""

    def __init__(
        self,
        emerging_path: str,
        evolution_path: str,
        prediction_horizon: int = 6,
        risk_threshold: float = 0.7,
        confidence_level: float = 0.95,
        output_dir: str | None = None,
    ):
        """
        초기화

        Args:
            emerging_path: Emerging hotspot 결과 디렉토리
            evolution_path: K-factors evolution 결과 디렉토리
            prediction_horizon: 예측 기간 (개월)
            risk_threshold: 위험 임계값
            confidence_level: 신뢰구간
            output_dir: 출력 디렉토리
        """
        self.emerging_path = Path(emerging_path)
        self.evolution_path = Path(evolution_path)
        self.prediction_horizon = prediction_horizon
        self.risk_threshold = risk_threshold
        self.confidence_level = confidence_level
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else RESULTS_DIR / "spatial_analysis" / "predictions"
        )

        # 한글 폰트 설정
        setup_korean_font()

        # 데이터 저장소
        self.emerging_patterns = None
        self.evolution_data = None
        self.predictions = {}
        self.early_warnings = []

    def load_data(self) -> bool:
        """데이터 로드"""
        print("\n=== 예측 분석 데이터 로드 중 ===")

        # Emerging patterns 로드
        emerging_file = self.emerging_path / "kfactors_dfinal_evolution.json"
        if emerging_file.exists():
            with open(emerging_file, encoding="utf-8") as f:
                self.emerging_patterns = json.load(f)
            print(
                f"✓ Emerging patterns 로드: {len(self.emerging_patterns.get('patterns', {}))} 패턴"
            )
        else:
            print(f"✗ Emerging patterns 파일 없음: {emerging_file}")
            return False

        # Evolution data 로드
        evolution_file = self.evolution_path / "kfactors_evolution_results.json"
        if evolution_file.exists():
            with open(evolution_file, encoding="utf-8") as f:
                self.evolution_data = json.load(f)
            print(
                f"✓ Evolution data 로드: {len(self.evolution_data.get('evolution_metrics', {}))} 메트릭"
            )
        else:
            print(f"✗ Evolution data 파일 없음: {evolution_file}")
            return False

        return True

    def predict_kfactors_trends(self) -> dict[str, Any]:
        """K-factors/D_final 트렌드 예측"""
        print("\n=== K-factors/D_final 트렌드 예측 ===")

        predictions = {
            "metric_predictions": {},
            "confidence_intervals": {},
            "trend_forecasts": {},
        }

        # 각 메트릭별 예측
        for metric_name, metric_data in self.evolution_data.get(
            "evolution_metrics", {}
        ).items():
            if "timeline" in metric_data and len(metric_data["timeline"]) >= 3:
                timeline = metric_data["timeline"]

                # 시계열 데이터 추출
                times = np.arange(len(timeline))
                values = np.array([t["mean"] for t in timeline])

                # 선형 회귀 모델
                model = LinearRegression()
                model.fit(times.reshape(-1, 1), values)

                # 미래 예측
                future_times = np.arange(
                    len(timeline), len(timeline) + self.prediction_horizon
                )
                future_predictions = model.predict(future_times.reshape(-1, 1))

                # 신뢰구간 계산
                residuals = values - model.predict(times.reshape(-1, 1))
                std_error = np.std(residuals)
                z_score = stats.norm.ppf((1 + self.confidence_level) / 2)

                confidence_lower = future_predictions - z_score * std_error
                confidence_upper = future_predictions + z_score * std_error

                predictions["metric_predictions"][metric_name] = {
                    "forecast": future_predictions.tolist(),
                    "last_value": float(values[-1]),
                    "trend_slope": float(model.coef_[0]),
                    "expected_change": float(future_predictions[-1] - values[-1]),
                    "change_rate": (
                        float((future_predictions[-1] - values[-1]) / values[-1])
                        if values[-1] != 0
                        else 0
                    ),
                }

                predictions["confidence_intervals"][metric_name] = {
                    "lower": confidence_lower.tolist(),
                    "upper": confidence_upper.tolist(),
                    "confidence_level": self.confidence_level,
                }

                print(
                    f"  {metric_name}: 예측 변화율={predictions['metric_predictions'][metric_name]['change_rate']:.2%}"
                )

        return predictions

    def analyze_risk_patterns(self) -> dict[str, Any]:
        """위험 패턴 분석"""
        print("\n=== 위험 패턴 분석 ===")

        risk_analysis = {"high_risk_cells": [], "risk_scores": {}, "pattern_risks": {}}

        # 패턴별 위험도 가중치
        pattern_weights = {
            "New Hot Spot": 1.5,
            "Intensifying": 2.0,
            "Persistent": 1.8,
            "Diminishing": 0.5,
            "Oscillating": 1.2,
            "Sporadic": 0.8,
            "Other": 1.0,
        }

        # 각 셀별 위험도 계산
        for cell_id, pattern_info in self.emerging_patterns.get("patterns", {}).items():
            pattern_type = pattern_info.get("pattern", "Other")
            kfactors_score = pattern_info.get("kfactors_dfinal_score", 0)

            # 위험 점수 = 패턴 가중치 × K-factors/D_final 점수
            pattern_weight = pattern_weights.get(pattern_type, 1.0)
            risk_score = pattern_weight * kfactors_score

            risk_analysis["risk_scores"][cell_id] = {
                "pattern": pattern_type,
                "pattern_weight": pattern_weight,
                "kfactors_score": kfactors_score,
                "risk_score": risk_score,
                "risk_level": (
                    "High"
                    if risk_score > self.risk_threshold
                    else "Medium" if risk_score > self.risk_threshold * 0.5 else "Low"
                ),
            }

            # 고위험 셀 식별
            if risk_score > self.risk_threshold:
                risk_analysis["high_risk_cells"].append(
                    {
                        "cell_id": cell_id,
                        "risk_score": risk_score,
                        "pattern": pattern_type,
                        "coordinates": pattern_info.get("coordinates", {}),
                    }
                )

        # 패턴별 평균 위험도
        for pattern_type in pattern_weights:
            pattern_cells = [
                score["risk_score"]
                for score in risk_analysis["risk_scores"].values()
                if score["pattern"] == pattern_type
            ]

            if pattern_cells:
                risk_analysis["pattern_risks"][pattern_type] = {
                    "avg_risk": float(np.mean(pattern_cells)),
                    "max_risk": float(np.max(pattern_cells)),
                    "cell_count": len(pattern_cells),
                }

        # 고위험 셀 정렬
        risk_analysis["high_risk_cells"] = sorted(
            risk_analysis["high_risk_cells"],
            key=lambda x: x["risk_score"],
            reverse=True,
        )[
            :20
        ]  # 상위 20개

        print(f"  고위험 셀: {len(risk_analysis['high_risk_cells'])}개")
        print(
            f"  평균 위험 점수: {np.mean([s['risk_score'] for s in risk_analysis['risk_scores'].values()]):.3f}"
        )

        return risk_analysis

    def generate_early_warnings(
        self, predictions: dict, risk_analysis: dict
    ) -> list[dict]:
        """조기 경보 생성"""
        print("\n=== 조기 경보 생성 ===")

        warnings = []

        # 1. 급격한 증가 예측 메트릭
        for metric_name, pred in predictions["metric_predictions"].items():
            if pred["change_rate"] > 0.2:  # 20% 이상 증가 예측
                warnings.append(
                    {
                        "type": "Rapid Increase",
                        "metric": metric_name,
                        "severity": "High" if pred["change_rate"] > 0.5 else "Medium",
                        "expected_change": pred["change_rate"],
                        "message": f"{metric_name}이(가) {self.prediction_horizon}개월 내 {pred['change_rate']:.1%} 증가 예상",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # 2. 고위험 셀 경보
        for cell in risk_analysis["high_risk_cells"][:5]:  # 상위 5개
            warnings.append(
                {
                    "type": "High Risk Cell",
                    "cell_id": cell["cell_id"],
                    "severity": "High",
                    "risk_score": cell["risk_score"],
                    "pattern": cell["pattern"],
                    "message": f"셀 {cell['cell_id']}: {cell['pattern']} 패턴, 위험 점수 {cell['risk_score']:.2f}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 3. 가속 구역 경보
        if self.evolution_data.get("acceleration_zones"):
            for zone in self.evolution_data["acceleration_zones"][:3]:  # 상위 3개
                if zone["acceleration"] > 0.01:  # 임계값
                    warnings.append(
                        {
                            "type": "Acceleration Zone",
                            "location": f"({zone['grid_x']:.1f}, {zone['grid_y']:.1f})",
                            "severity": (
                                "High" if zone["acceleration"] > 0.05 else "Medium"
                            ),
                            "acceleration": zone["acceleration"],
                            "message": f"가속 구역: 가속도 {zone['acceleration']:.4f}, 성장률 {zone['growth_rate']:.1%}",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

        print(f"  생성된 경보: {len(warnings)}개")

        # 심각도별 집계
        severity_counts = {}
        for warning in warnings:
            severity = warning.get("severity", "Unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for severity, count in severity_counts.items():
            print(f"    - {severity}: {count}개")

        return warnings

    def create_maintenance_schedule(self, risk_analysis: dict) -> dict[str, list]:
        """예측 유지보수 일정 생성"""
        print("\n=== 예측 유지보수 일정 생성 ===")

        schedule = {
            "immediate": [],  # 즉시 (1개월 이내)
            "short_term": [],  # 단기 (1-3개월)
            "medium_term": [],  # 중기 (3-6개월)
            "long_term": [],  # 장기 (6개월 이후)
        }

        # 위험도에 따른 일정 배정
        for cell_id, risk_info in risk_analysis["risk_scores"].items():
            risk_score = risk_info["risk_score"]
            pattern = risk_info["pattern"]

            maintenance_item = {
                "cell_id": cell_id,
                "risk_score": risk_score,
                "pattern": pattern,
                "priority": None,
                "estimated_date": None,
            }

            # 위험도와 패턴에 따른 우선순위 결정
            if risk_score > self.risk_threshold * 1.5 or pattern == "Intensifying":
                maintenance_item["priority"] = "Critical"
                maintenance_item["estimated_date"] = (
                    datetime.now() + timedelta(days=30)
                ).strftime("%Y-%m")
                schedule["immediate"].append(maintenance_item)

            elif risk_score > self.risk_threshold or pattern in [
                "New Hot Spot",
                "Persistent",
            ]:
                maintenance_item["priority"] = "High"
                maintenance_item["estimated_date"] = (
                    datetime.now() + timedelta(days=60)
                ).strftime("%Y-%m")
                schedule["short_term"].append(maintenance_item)

            elif risk_score > self.risk_threshold * 0.5:
                maintenance_item["priority"] = "Medium"
                maintenance_item["estimated_date"] = (
                    datetime.now() + timedelta(days=120)
                ).strftime("%Y-%m")
                schedule["medium_term"].append(maintenance_item)

            else:
                maintenance_item["priority"] = "Low"
                maintenance_item["estimated_date"] = (
                    datetime.now() + timedelta(days=180)
                ).strftime("%Y-%m")
                schedule["long_term"].append(maintenance_item)

        # 각 기간별 정렬
        for period in schedule:
            schedule[period] = sorted(
                schedule[period], key=lambda x: x["risk_score"], reverse=True
            )[:10]

        # 일정 요약
        print(f"  즉시 조치: {len(schedule['immediate'])}개")
        print(f"  단기 (1-3개월): {len(schedule['short_term'])}개")
        print(f"  중기 (3-6개월): {len(schedule['medium_term'])}개")
        print(f"  장기 (6개월+): {len(schedule['long_term'])}개")

        return schedule

    def visualize_predictions(self):
        """예측 결과 시각화"""
        print("\n=== 예측 결과 시각화 ===")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. K-factors 예측 트렌드
        ax = axes[0, 0]

        for i, (metric_name, pred) in enumerate(
            list(self.predictions["metric_predictions"].items())[:5]
        ):
            if "forecast" in pred:
                # 과거 데이터
                timeline = self.evolution_data["evolution_metrics"][metric_name][
                    "timeline"
                ]
                past_values = [t["mean"] for t in timeline]
                past_times = list(range(len(past_values)))

                # 미래 예측
                future_values = pred["forecast"]
                future_times = list(
                    range(len(past_values), len(past_values) + len(future_values))
                )

                # 플롯
                ax.plot(
                    past_times,
                    past_values,
                    "o-",
                    label=f"{metric_name} (과거)",
                    alpha=0.7,
                )
                ax.plot(
                    future_times,
                    future_values,
                    "s--",
                    label=f"{metric_name} (예측)",
                    alpha=0.7,
                )

                # 신뢰구간
                if metric_name in self.predictions["confidence_intervals"]:
                    ci = self.predictions["confidence_intervals"][metric_name]
                    ax.fill_between(future_times, ci["lower"], ci["upper"], alpha=0.2)

        ax.set_xlabel("시간 (월)")
        ax.set_ylabel("값")
        ax.set_title("K-factors/D_final 예측 트렌드", fontsize=12, fontweight="bold")
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.axvline(x=len(past_times) - 1, color="red", linestyle=":", alpha=0.5)
        ax.text(len(past_times) - 1, ax.get_ylim()[1] * 0.9, "현재", ha="center")

        # 2. 위험도 분포
        ax = axes[0, 1]

        [
            info["risk_score"]
            for info in self.predictions["risk_analysis"]["risk_scores"].values()
        ]
        risk_levels = [
            info["risk_level"]
            for info in self.predictions["risk_analysis"]["risk_scores"].values()
        ]

        level_counts = pd.Series(risk_levels).value_counts()
        colors = {"High": "red", "Medium": "orange", "Low": "green"}

        bars = ax.bar(
            level_counts.index,
            level_counts.values,
            color=[colors.get(l, "gray") for l in level_counts.index],
        )
        ax.set_ylabel("셀 수")
        ax.set_title("위험도 레벨 분포", fontsize=12, fontweight="bold")

        # 값 표시
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height)}",
                ha="center",
                va="bottom",
            )

        # 3. 패턴별 위험도
        ax = axes[1, 0]

        if self.predictions["risk_analysis"]["pattern_risks"]:
            patterns = list(self.predictions["risk_analysis"]["pattern_risks"].keys())
            avg_risks = [
                self.predictions["risk_analysis"]["pattern_risks"][p]["avg_risk"]
                for p in patterns
            ]

            bars = ax.barh(patterns, avg_risks, color="steelblue", alpha=0.7)
            ax.set_xlabel("평균 위험 점수")
            ax.set_title("패턴별 평균 위험도", fontsize=12, fontweight="bold")
            ax.axvline(
                x=self.risk_threshold,
                color="red",
                linestyle="--",
                alpha=0.5,
                label="위험 임계값",
            )
            ax.legend()

            # 값 표시
            for bar, val in zip(bars, avg_risks, strict=False):
                width = bar.get_width()
                ax.text(
                    width,
                    bar.get_y() + bar.get_height() / 2.0,
                    f"{val:.2f}",
                    ha="left",
                    va="center",
                )

        # 4. 유지보수 일정
        ax = axes[1, 1]

        schedule_counts = {
            "즉시": len(self.predictions["maintenance_schedule"]["immediate"]),
            "단기\n(1-3개월)": len(
                self.predictions["maintenance_schedule"]["short_term"]
            ),
            "중기\n(3-6개월)": len(
                self.predictions["maintenance_schedule"]["medium_term"]
            ),
            "장기\n(6개월+)": len(
                self.predictions["maintenance_schedule"]["long_term"]
            ),
        }

        colors_schedule = ["red", "orange", "yellow", "green"]
        bars = ax.bar(
            schedule_counts.keys(),
            schedule_counts.values(),
            color=colors_schedule,
            alpha=0.7,
            edgecolor="black",
        )
        ax.set_ylabel("작업 수")
        ax.set_title("예측 유지보수 일정", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 값 표시
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height)}",
                ha="center",
                va="bottom",
            )

        plt.suptitle(
            "K-factors/D_final Prediction Analysis",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()

        # 저장
        output_path = self.output_dir / "kfactors_prediction_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"예측 분석 시각화 저장: {output_path}")

    def generate_report(self):
        """예측 보고서 생성"""
        print("\n=== 예측 보고서 생성 중 ===")

        report_lines = [
            "# K-factors/D_final Prediction Report",
            f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. 예측 설정",
            f"- 예측 기간: {self.prediction_horizon}개월",
            f"- 위험 임계값: {self.risk_threshold}",
            f"- 신뢰수준: {self.confidence_level*100}%",
            "\n## 2. 주요 예측 결과",
        ]

        # 주요 메트릭 예측
        report_lines.append("\n### 2.1 K-factors/D_final 예측")
        for metric, pred in list(self.predictions["metric_predictions"].items())[:5]:
            change_pct = pred["change_rate"] * 100
            trend = "증가" if pred["trend_slope"] > 0 else "감소"
            report_lines.append(f"- **{metric}**: {change_pct:+.1f}% {trend} 예상")

        # 고위험 셀
        report_lines.append("\n### 2.2 고위험 셀 (Top 5)")
        high_risk = self.predictions["risk_analysis"]["high_risk_cells"][:5]

        if high_risk:
            report_lines.append("\n| 순위 | Cell ID | 위험점수 | 패턴 |")
            report_lines.append("|------|---------|----------|------|")

            for i, cell in enumerate(high_risk, 1):
                report_lines.append(
                    f"| {i} | {cell['cell_id']} | {cell['risk_score']:.2f} | {cell['pattern']} |"
                )

        # 조기 경보
        report_lines.append("\n### 2.3 조기 경보")
        high_severity_warnings = [
            w for w in self.predictions["early_warnings"] if w["severity"] == "High"
        ]

        for warning in high_severity_warnings[:5]:
            report_lines.append(f"- ⚠️ {warning['message']}")

        # 유지보수 일정 요약
        report_lines.append("\n## 3. 유지보수 일정")
        schedule = self.predictions["maintenance_schedule"]

        report_lines.append(
            f"- **즉시 조치 필요**: {len(schedule['immediate'])}개 지역"
        )
        report_lines.append(
            f"- **단기 (1-3개월)**: {len(schedule['short_term'])}개 지역"
        )
        report_lines.append(
            f"- **중기 (3-6개월)**: {len(schedule['medium_term'])}개 지역"
        )
        report_lines.append(f"- **장기 (6개월+)**: {len(schedule['long_term'])}개 지역")

        # 권장사항
        report_lines.extend(
            [
                "\n## 4. 권장사항",
                "- 고위험 셀에 대한 즉각적인 점검 실시",
                "- Intensifying 패턴 지역 집중 모니터링",
                "- 급격한 증가 예측 메트릭 주시",
                "- 예측 기반 예방 정비 일정 수립",
            ]
        )

        # 파일 저장
        report_path = self.output_dir / "kfactors_prediction_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"보고서 저장: {report_path}")

    def save_results(self):
        """결과 저장"""
        print("\n=== 결과 저장 중 ===")

        # 전체 예측 결과
        self.predictions = {
            "metric_predictions": self.predictions,
            "risk_analysis": self.predictions.get("risk_analysis", {}),
            "early_warnings": self.predictions.get("early_warnings", []),
            "maintenance_schedule": self.predictions.get("maintenance_schedule", {}),
            "metadata": {
                "prediction_horizon": self.prediction_horizon,
                "risk_threshold": self.risk_threshold,
                "confidence_level": self.confidence_level,
                "generated_at": datetime.now().isoformat(),
            },
        }

        # JSON 저장
        json_path = self.output_dir / "kfactors_prediction_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.predictions, f, ensure_ascii=False, indent=2, default=str)
        print(f"예측 결과 저장: {json_path}")

        # 조기 경보 CSV
        if self.predictions["early_warnings"]:
            warnings_df = pd.DataFrame(self.predictions["early_warnings"])
            warnings_path = self.output_dir / "early_warnings.csv"
            warnings_df.to_csv(warnings_path, index=False, encoding="utf-8-sig")
            print(f"조기 경보 저장: {warnings_path}")

        # 유지보수 일정 CSV
        all_maintenance = []
        for period, items in self.predictions["maintenance_schedule"].items():
            for item in items:
                item["period"] = period
                all_maintenance.append(item)

        if all_maintenance:
            maintenance_df = pd.DataFrame(all_maintenance)
            maintenance_path = self.output_dir / "maintenance_schedule.csv"
            maintenance_df.to_csv(maintenance_path, index=False, encoding="utf-8-sig")
            print(f"유지보수 일정 저장: {maintenance_path}")

    def run(self):
        """전체 분석 실행"""
        print("\n" + "=" * 60)
        print("K-factors/D_final Prediction Analysis (Phase 10)")
        print("=" * 60)

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 데이터 로드
        if not self.load_data():
            print("데이터 로드 실패")
            return False

        # 예측 분석
        trend_predictions = self.predict_kfactors_trends()
        risk_analysis = self.analyze_risk_patterns()
        early_warnings = self.generate_early_warnings(trend_predictions, risk_analysis)
        maintenance_schedule = self.create_maintenance_schedule(risk_analysis)

        # 결과 통합
        self.predictions = {
            "metric_predictions": trend_predictions["metric_predictions"],
            "confidence_intervals": trend_predictions["confidence_intervals"],
            "risk_analysis": risk_analysis,
            "early_warnings": early_warnings,
            "maintenance_schedule": maintenance_schedule,
        }

        # 시각화
        self.visualize_predictions()

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
        description="K-factors/D_final Prediction Analysis (Phase 10)"
    )
    parser.add_argument(
        "--emerging-path",
        default="results/spatial_analysis/emerging",
        help="Emerging hotspot 결과 디렉토리",
    )
    parser.add_argument(
        "--evolution-path",
        default="results/spatial_analysis/kfactors_evolution",
        help="K-factors evolution 결과 디렉토리",
    )
    parser.add_argument(
        "--prediction-horizon", type=int, default=6, help="예측 기간 (개월)"
    )
    parser.add_argument("--risk-threshold", type=float, default=0.7, help="위험 임계값")
    parser.add_argument(
        "--confidence-level", type=float, default=0.95, help="신뢰수준 (0-1)"
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/predictions",
        help="결과 저장 디렉토리",
    )

    args = parser.parse_args()

    # 분석기 생성 및 실행
    analyzer = KFactorsPredictionAnalyzer(
        emerging_path=args.emerging_path,
        evolution_path=args.evolution_path,
        prediction_horizon=args.prediction_horizon,
        risk_threshold=args.risk_threshold,
        confidence_level=args.confidence_level,
        output_dir=args.output_dir,
    )

    success = analyzer.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
