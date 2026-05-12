"""
main24_maintenance_priority.py

공간 분석 결과를 통합하여 유지보수 우선순위를 생성합니다.
핫스팟, 진화 패턴, K-factors를 결합한 종합 점수를 계산합니다.
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.korean_font_utils import setup_korean_font

warnings.filterwarnings("ignore")


class MaintenancePriorityAnalyzer:
    """유지보수 우선순위 분석 클래스"""

    def __init__(self, params: dict[str, Any]):
        """
        Parameters
        ----------
        params : dict
            가중치 및 분석 파라미터
        """
        self.params = params
        self.hotspot_data = None
        self.emerging_data = None
        self.kfactors_data = None
        self.priority_scores = None
        self.recommendations = None

        # 한글 폰트 설정
        setup_korean_font()

    def load_analysis_results(self, input_dirs: dict[str, str]):
        """분석 결과 로드"""
        print("\n분석 결과 로드 중...")

        # 1. 핫스팟 분석 결과
        hotspot_file = os.path.join(
            input_dirs.get("hotspots", ""), "hotspot_results.csv"
        )
        if os.path.exists(hotspot_file):
            self.hotspot_data = pd.read_csv(hotspot_file, encoding="utf-8-sig")
            print(f"핫스팟 데이터 로드: {len(self.hotspot_data)} 셀")
        else:
            print(f"핫스팟 파일 없음: {hotspot_file}")

        # 2. Emerging 패턴 결과
        emerging_file = os.path.join(
            input_dirs.get("emerging", ""), "pattern_classification.csv"
        )
        if os.path.exists(emerging_file):
            self.emerging_data = pd.read_csv(emerging_file, encoding="utf-8-sig")
            print(f"Emerging 패턴 로드: {len(self.emerging_data)} 셀")
        else:
            print(f"Emerging 파일 없음: {emerging_file}")

        # 3. K-factors 데이터 (있는 경우)
        kfactors_file = "data/520_area/fatigue_analysis_results.csv"
        if os.path.exists(kfactors_file):
            self.kfactors_data = pd.read_csv(kfactors_file, encoding="utf-8-sig")
            print(f"K-factors 데이터 로드: {len(self.kfactors_data)} 레코드")

    def calculate_priority_scores(self) -> pd.DataFrame:
        """우선순위 점수 계산"""
        print("\n우선순위 점수 계산 중...")

        priority_list = []

        # 데이터 병합 준비
        if self.hotspot_data is not None and self.emerging_data is not None:
            # cell_id로 병합
            merged_data = pd.merge(
                self.hotspot_data,
                self.emerging_data,
                on="cell_id",
                how="outer",
                suffixes=("_hot", "_emg"),
            )
        elif self.hotspot_data is not None:
            merged_data = self.hotspot_data
        elif self.emerging_data is not None:
            merged_data = self.emerging_data
        else:
            print("분석 데이터 없음")
            return pd.DataFrame()

        # 각 셀에 대한 점수 계산
        for _, row in merged_data.iterrows():
            score_components = {}

            # 1. 핫스팟 점수 (0-100)
            hotspot_score = 0
            if "gi_star_z" in row:
                z_score = row["gi_star_z"]
                if not pd.isna(z_score):
                    # z-score를 0-100 스케일로 변환
                    hotspot_score = min(100, max(0, (z_score + 3) * 100 / 6))

            score_components["hotspot_score"] = hotspot_score

            # 2. Emerging 패턴 점수 (0-100)
            pattern_scores = {
                "New": 90,  # 신규 핫스팟 - 높은 우선순위
                "Intensifying": 85,  # 강화되는 핫스팟
                "Persistent": 80,  # 지속적 핫스팟
                "Sporadic": 60,  # 간헐적 핫스팟
                "Oscillating": 50,  # 진동 패턴
                "Diminishing": 30,  # 감소하는 핫스팟
                "Historical": 20,  # 과거 핫스팟
                "Never": 10,  # 핫스팟 없음
                "Other": 40,
            }

            pattern = row.get("pattern", "Other")
            emerging_score = pattern_scores.get(pattern, 40)
            score_components["emerging_score"] = emerging_score

            # 3. K-factors 점수 (0-100)
            kfactor_score = 50  # 기본값

            if "mean_K_total" in row and not pd.isna(row["mean_K_total"]):
                # K_total 값을 0-100 스케일로 변환 (0.5-2.0 범위 가정)
                k_total = row["mean_K_total"]
                kfactor_score = min(100, max(0, (k_total - 0.5) * 100 / 1.5))
            elif "mean_D_final" in row and not pd.isna(row["mean_D_final"]):
                # D_final 값을 점수로 변환
                d_final = row["mean_D_final"]
                kfactor_score = min(100, d_final * 10)  # 스케일 조정 필요

            score_components["kfactor_score"] = kfactor_score

            # 4. 재작업 빈도 점수 (0-100)
            repair_score = 0
            if "repair_count" in row and not pd.isna(row["repair_count"]):
                # 재작업 횟수를 0-100 스케일로 변환
                count = row["repair_count"]
                repair_score = min(100, count * 10)  # 10회 = 100점
            elif "point_count" in row and not pd.isna(row["point_count"]):
                count = row["point_count"]
                repair_score = min(100, count * 10)

            score_components["repair_score"] = repair_score

            # 5. 종합 점수 계산 (가중 평균)
            weights = self.params
            total_score = (
                score_components["hotspot_score"] * weights["weight_hotspot"]
                + score_components["emerging_score"] * weights["weight_emerging"]
                + score_components["kfactor_score"] * weights["weight_kfactors"]
                + repair_score
                * (
                    1
                    - weights["weight_hotspot"]
                    - weights["weight_emerging"]
                    - weights["weight_kfactors"]
                )
            )

            # 결과 저장
            priority_item = {
                "cell_id": row.get("cell_id", ""),
                "total_score": total_score,
                "hotspot_score": score_components["hotspot_score"],
                "emerging_score": score_components["emerging_score"],
                "kfactor_score": score_components["kfactor_score"],
                "repair_score": repair_score,
                "pattern": row.get("pattern", ""),
                "gi_star_z": row.get("gi_star_z", 0),
                "repair_count": row.get("repair_count", row.get("point_count", 0)),
                "mean_cnt_jnt": row.get(
                    "mean_cnt_jnt_hot", row.get("mean_cnt_jnt_emg", 0)
                ),
            }

            # 위치 정보 추가 (있는 경우)
            if "grid_x" in row:
                priority_item["grid_x"] = row["grid_x"]
                priority_item["grid_y"] = row["grid_y"]

            priority_list.append(priority_item)

        # DataFrame 생성 및 정렬
        self.priority_scores = pd.DataFrame(priority_list)
        self.priority_scores = self.priority_scores.sort_values(
            "total_score", ascending=False
        )

        print(f"우선순위 계산 완료: {len(self.priority_scores)} 셀")

        return self.priority_scores

    def generate_recommendations(self, top_n: int = 10) -> pd.DataFrame:
        """상위 N개 지역에 대한 권장사항 생성"""
        print(f"\n상위 {top_n}개 지역 권장사항 생성 중...")

        recommendations = []

        for idx, row in self.priority_scores.head(top_n).iterrows():
            rec = {
                "rank": len(recommendations) + 1,
                "cell_id": row["cell_id"],
                "total_score": row["total_score"],
                "priority_level": self._get_priority_level(row["total_score"]),
                "pattern": row["pattern"],
                "repair_count": row["repair_count"],
            }

            # 권장 조치 결정
            actions = []

            # 패턴별 조치
            if row["pattern"] == "New":
                actions.append("즉시 원인 조사 및 응급 보수")
            elif row["pattern"] == "Intensifying":
                actions.append("조기 개입으로 확산 방지")
            elif row["pattern"] == "Persistent":
                actions.append("근본적 개선 공사 필요")
            elif row["pattern"] == "Sporadic":
                actions.append("주기적 모니터링 강화")

            # 점수별 조치
            if row["hotspot_score"] > 80:
                actions.append("핫스팟 지역 집중 관리")

            if row["kfactor_score"] > 70:
                actions.append("노후 인프라 교체 검토")

            if row["repair_score"] > 60:
                actions.append("빈발 구간 특별 점검")

            rec["recommended_actions"] = (
                "; ".join(actions) if actions else "정기 점검 유지"
            )

            # 예상 비용 등급 (간단한 추정)
            if row["total_score"] > 80:
                rec["cost_estimate"] = "높음"
            elif row["total_score"] > 60:
                rec["cost_estimate"] = "중간"
            else:
                rec["cost_estimate"] = "낮음"

            # 긴급도
            if row["pattern"] in ["New", "Intensifying"] and row["total_score"] > 70:
                rec["urgency"] = "긴급"
            elif row["total_score"] > 80:
                rec["urgency"] = "높음"
            elif row["total_score"] > 60:
                rec["urgency"] = "중간"
            else:
                rec["urgency"] = "낮음"

            recommendations.append(rec)

        self.recommendations = pd.DataFrame(recommendations)
        return self.recommendations

    def _get_priority_level(self, score: float) -> str:
        """점수를 우선순위 레벨로 변환"""
        if score >= 80:
            return "매우 높음"
        if score >= 60:
            return "높음"
        if score >= 40:
            return "중간"
        if score >= 20:
            return "낮음"
        return "매우 낮음"

    def perform_cost_benefit_analysis(self) -> pd.DataFrame:
        """비용-효익 분석"""
        print("\n비용-효익 분석 수행 중...")

        # 간단한 비용-효익 모델
        cba_results = []

        for idx, row in self.priority_scores.head(20).iterrows():
            # 예상 비용 (단순 모델)
            base_cost = 1000  # 기본 비용 (만원)

            if row["pattern"] == "Persistent":
                cost_multiplier = 3.0  # 지속적 문제는 비용 높음
            elif row["pattern"] in ["New", "Intensifying"]:
                cost_multiplier = 2.0
            else:
                cost_multiplier = 1.0

            estimated_cost = base_cost * cost_multiplier * (row["total_score"] / 50)

            # 예상 효익 (사고 예방, 재작업 감소)
            annual_repairs = row["repair_count"] * 12 / 24  # 2년 데이터 기준 연간 추정
            repair_cost_saved = annual_repairs * 500  # 재작업당 500만원

            # 위험 감소 효익
            risk_reduction_benefit = row["total_score"] * 10  # 점수당 10만원

            total_benefit = repair_cost_saved + risk_reduction_benefit

            # ROI 계산
            roi = (
                (total_benefit - estimated_cost) / estimated_cost * 100
                if estimated_cost > 0
                else 0
            )

            cba_results.append(
                {
                    "cell_id": row["cell_id"],
                    "estimated_cost": estimated_cost,
                    "annual_benefit": total_benefit,
                    "roi_percent": roi,
                    "payback_months": (
                        estimated_cost / (total_benefit / 12)
                        if total_benefit > 0
                        else 999
                    ),
                }
            )

        return pd.DataFrame(cba_results)

    def visualize_priorities(self, output_dir: str):
        """우선순위 시각화"""
        print("\n우선순위 시각화 중...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. 상위 20개 우선순위 막대 그래프
        ax = axes[0, 0]
        top_20 = self.priority_scores.head(20)
        ax.barh(range(len(top_20)), top_20["total_score"].values)
        ax.set_yticks(range(len(top_20)))
        ax.set_yticklabels([f"#{i+1}" for i in range(len(top_20))])
        ax.set_xlabel("우선순위 점수")
        ax.set_title("상위 20개 우선순위 지역", fontsize=14)
        ax.invert_yaxis()

        # 2. 점수 구성 요소 스택 차트
        ax = axes[0, 1]
        components = [
            "hotspot_score",
            "emerging_score",
            "kfactor_score",
            "repair_score",
        ]
        bottom = np.zeros(10)

        for component in components:
            values = self.priority_scores.head(10)[component].values
            ax.bar(
                range(10), values, bottom=bottom, label=component.replace("_score", "")
            )
            bottom += values

        ax.set_xlabel("순위")
        ax.set_ylabel("점수")
        ax.set_title("상위 10개 지역 점수 구성", fontsize=14)
        ax.legend()
        ax.set_xticks(range(10))
        ax.set_xticklabels([f"#{i+1}" for i in range(10)])

        # 3. 패턴별 우선순위 분포
        ax = axes[1, 0]
        pattern_scores = self.priority_scores.groupby("pattern")["total_score"].agg(
            ["mean", "count"]
        )
        pattern_scores = pattern_scores.sort_values("mean", ascending=False)

        ax.bar(range(len(pattern_scores)), pattern_scores["mean"].values)
        ax.set_xticks(range(len(pattern_scores)))
        ax.set_xticklabels(pattern_scores.index, rotation=45, ha="right")
        ax.set_ylabel("평균 우선순위 점수")
        ax.set_title("패턴별 평균 우선순위", fontsize=14)

        # 개수 표시
        for i, (mean, count) in enumerate(pattern_scores.values):
            ax.text(i, mean + 1, f"n={int(count)}", ha="center")

        # 4. 우선순위 점수 분포
        ax = axes[1, 1]
        ax.hist(
            self.priority_scores["total_score"], bins=30, edgecolor="black", alpha=0.7
        )
        ax.axvline(x=80, color="red", linestyle="--", label="높은 우선순위 (>80)")
        ax.axvline(x=60, color="orange", linestyle="--", label="중간 우선순위 (>60)")
        ax.set_xlabel("우선순위 점수")
        ax.set_ylabel("빈도")
        ax.set_title("우선순위 점수 분포", fontsize=14)
        ax.legend()

        plt.tight_layout()

        output_path = os.path.join(output_dir, "priority_analysis.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"우선순위 시각화 저장: {output_path}")

        # 공간 분포 시각화 (좌표 정보가 있는 경우)
        if "grid_x" in self.priority_scores.columns:
            self.visualize_spatial_priorities(output_dir)

    def visualize_spatial_priorities(self, output_dir: str):
        """공간적 우선순위 분포 시각화"""
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))

        # 우선순위 점수를 색상으로 표현
        scatter = ax.scatter(
            self.priority_scores["grid_x"],
            self.priority_scores["grid_y"],
            c=self.priority_scores["total_score"],
            cmap="RdYlGn_r",
            s=50,
            alpha=0.6,
            edgecolors="black",
            linewidth=0.5,
        )

        # 상위 10개 지역 강조
        top_10 = self.priority_scores.head(10)
        ax.scatter(
            top_10["grid_x"],
            top_10["grid_y"],
            s=200,
            facecolors="none",
            edgecolors="red",
            linewidth=2,
            label="Top 10",
        )

        # 라벨 추가
        for idx, row in top_10.iterrows():
            ax.annotate(
                f"#{list(self.priority_scores.index).index(idx)+1}",
                (row["grid_x"], row["grid_y"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
                fontweight="bold",
            )

        plt.colorbar(scatter, ax=ax, label="우선순위 점수")
        ax.set_xlabel("X 좌표 (m)")
        ax.set_ylabel("Y 좌표 (m)")
        ax.set_title("유지보수 우선순위 공간 분포", fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)

        output_path = os.path.join(output_dir, "priority_spatial_distribution.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"공간 우선순위 분포 저장: {output_path}")

    def save_results(self, output_dir: str):
        """결과 저장"""
        # 우선순위 점수 저장
        priority_path = os.path.join(output_dir, "priority_rankings.csv")
        self.priority_scores.to_csv(priority_path, index=False, encoding="utf-8-sig")
        print(f"우선순위 순위 저장: {priority_path}")

        # 권장사항 저장
        if self.recommendations is not None:
            rec_path = os.path.join(output_dir, "maintenance_recommendations.csv")
            self.recommendations.to_csv(rec_path, index=False, encoding="utf-8-sig")
            print(f"유지보수 권장사항 저장: {rec_path}")

        # 상위 50개 우선순위 별도 저장
        top50_path = os.path.join(output_dir, "top50_priorities.csv")
        self.priority_scores.head(50).to_csv(
            top50_path, index=False, encoding="utf-8-sig"
        )
        print(f"상위 50개 우선순위 저장: {top50_path}")

        # 메타데이터 저장
        metadata = {
            "analysis_date": datetime.now().isoformat(),
            "parameters": self.params,
            "n_cells": len(self.priority_scores),
            "priority_summary": {
                "very_high": int((self.priority_scores["total_score"] >= 80).sum()),
                "high": int(
                    (
                        (self.priority_scores["total_score"] >= 60)
                        & (self.priority_scores["total_score"] < 80)
                    ).sum()
                ),
                "medium": int(
                    (
                        (self.priority_scores["total_score"] >= 40)
                        & (self.priority_scores["total_score"] < 60)
                    ).sum()
                ),
                "low": int((self.priority_scores["total_score"] < 40).sum()),
            },
            "top_10_avg_score": float(
                self.priority_scores.head(10)["total_score"].mean()
            ),
        }

        metadata_path = os.path.join(output_dir, "priority_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"메타데이터 저장: {metadata_path}")

    def generate_report(self, output_dir: str):
        """분석 보고서 생성"""
        report_lines = [
            "# 유지보수 우선순위 분석 보고서",
            f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. 분석 개요",
            f"- 분석 셀 수: {len(self.priority_scores):,}개",
            f"- 가중치: 핫스팟 {self.params['weight_hotspot']:.0%}, ",
            f"  Emerging {self.params['weight_emerging']:.0%}, ",
            f"  K-factors {self.params['weight_kfactors']:.0%}",
            "\n## 2. 우선순위 분포",
            "\n| 우선순위 | 개수 | 비율(%) |",
            "|---------|------|---------|",
        ]

        priority_dist = {
            "매우 높음 (≥80)": (self.priority_scores["total_score"] >= 80).sum(),
            "높음 (60-79)": (
                (self.priority_scores["total_score"] >= 60)
                & (self.priority_scores["total_score"] < 80)
            ).sum(),
            "중간 (40-59)": (
                (self.priority_scores["total_score"] >= 40)
                & (self.priority_scores["total_score"] < 60)
            ).sum(),
            "낮음 (<40)": (self.priority_scores["total_score"] < 40).sum(),
        }

        total = len(self.priority_scores)
        for level, count in priority_dist.items():
            report_lines.append(f"| {level} | {count} | {count/total*100:.1f} |")

        # 상위 10개 지역
        report_lines.extend(
            [
                "\n## 3. 상위 10개 우선순위 지역",
                "\n| 순위 | Cell ID | 총점 | 패턴 | 재작업 횟수 |",
                "|------|---------|------|------|------------|",
            ]
        )

        for idx, row in self.priority_scores.head(10).iterrows():
            rank = list(self.priority_scores.index).index(idx) + 1
            report_lines.append(
                f"| {rank} | {row['cell_id']} | {row['total_score']:.1f} | "
                f"{row['pattern']} | {int(row['repair_count'])} |"
            )

        # 권장사항
        if self.recommendations is not None:
            report_lines.extend(["\n## 4. 주요 권장사항", ""])

            for _, rec in self.recommendations.head(5).iterrows():
                report_lines.extend(
                    [
                        f"### #{rec['rank']} - {rec['cell_id']}",
                        f"- 우선순위: {rec['priority_level']}",
                        f"- 긴급도: {rec['urgency']}",
                        f"- 권장 조치: {rec['recommended_actions']}",
                        f"- 예상 비용: {rec['cost_estimate']}",
                        "",
                    ]
                )

        report_lines.extend(
            [
                "\n## 5. 주요 발견사항",
                f"- 매우 높은 우선순위 지역: {priority_dist['매우 높음 (≥80)']}개",
                f"- 상위 10개 평균 점수: {self.priority_scores.head(10)['total_score'].mean():.1f}",
                "- New/Intensifying 패턴 지역 즉시 조치 필요",
                "\n## 6. 실행 계획",
                "1. **단기 (1개월 이내)**: 상위 10개 지역 집중 점검",
                "2. **중기 (3개월 이내)**: 높은 우선순위 전체 개선",
                "3. **장기 (6개월 이내)**: 중간 우선순위 예방 정비",
            ]
        )

        report_path = os.path.join(output_dir, "priority_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"분석 보고서 저장: {report_path}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="유지보수 우선순위 분석 및 권장사항 생성"
    )
    parser.add_argument(
        "--weight-hotspot", type=float, default=0.3, help="핫스팟 가중치"
    )
    parser.add_argument(
        "--weight-emerging", type=float, default=0.3, help="신흥 패턴 가중치"
    )
    parser.add_argument(
        "--weight-kfactors", type=float, default=0.4, help="K-factors 가중치"
    )
    parser.add_argument("--top-n", type=int, default=10, help="상위 N개 우선순위 출력")
    parser.add_argument(
        "--budget-constraint", type=float, help="예산 제약 (선택사항, 만원)"
    )
    parser.add_argument(
        "--input-dirs",
        nargs="+",
        default=[
            "results/spatial_analysis/hotspots",
            "results/spatial_analysis/emerging",
        ],
        help="입력 디렉토리 목록",
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/priority",
        help="결과 저장 디렉토리",
    )

    args = parser.parse_args()

    # 로깅 설정
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    try:
        # 파라미터 설정
        params = {
            "weight_hotspot": args.weight_hotspot,
            "weight_emerging": args.weight_emerging,
            "weight_kfactors": args.weight_kfactors,
        }

        # 가중치 합이 1이 되도록 정규화
        weight_sum = sum(params.values())
        if weight_sum > 0:
            for key in params:
                params[key] /= weight_sum

        print("\n사용 파라미터:")
        for key, value in params.items():
            print(f"  {key}: {value:.2f}")

        # 입력 디렉토리 매핑
        input_dirs = {
            "hotspots": args.input_dirs[0] if len(args.input_dirs) > 0 else "",
            "emerging": args.input_dirs[1] if len(args.input_dirs) > 1 else "",
        }

        # 분석 실행
        analyzer = MaintenancePriorityAnalyzer(params)

        # 데이터 로드
        analyzer.load_analysis_results(input_dirs)

        # 우선순위 계산
        analyzer.calculate_priority_scores()

        # 권장사항 생성
        analyzer.generate_recommendations(top_n=args.top_n)

        # 비용-효익 분석
        cba_results = analyzer.perform_cost_benefit_analysis()

        # 결과 저장
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        analyzer.save_results(str(output_dir))
        analyzer.visualize_priorities(str(output_dir))
        analyzer.generate_report(str(output_dir))

        # 비용-효익 결과 저장
        if not cba_results.empty:
            cba_path = os.path.join(output_dir, "cost_benefit_analysis.csv")
            cba_results.to_csv(cba_path, index=False, encoding="utf-8-sig")
            print(f"비용-효익 분석 저장: {cba_path}")

        print(f"\n분석 완료! 결과: {output_dir}")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
