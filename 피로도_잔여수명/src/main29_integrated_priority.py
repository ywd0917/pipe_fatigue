#!/usr/bin/env python3
"""
Phase 11: Enhanced Priority System with K-factors/D_final Integration
통합 우선순위 시스템 - 모든 분석 결과를 종합한 최종 우선순위 결정
"""

import argparse
import json

# 프로젝트 모듈
import sys
import warnings
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sys.path.append(str(Path(__file__).parent.parent))

from src.common.config import RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font

warnings.filterwarnings("ignore")


class IntegratedPriorityAnalyzer:
    """통합 우선순위 분석기"""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        budget: float | None = None,
        risk_categories: dict[str, float] | None = None,
        output_dir: str | None = None,
    ):
        """
        초기화

        Args:
            weights: 우선순위 구성요소별 가중치
            budget: 예산 제약 (선택사항)
            risk_categories: 위험 카테고리 임계값
            output_dir: 출력 디렉토리
        """
        # 기본 가중치
        self.weights = weights or {
            "hotspot": 0.25,  # 핫스팟 점수
            "kfactors": 0.40,  # K-factors/D_final (가장 중요)
            "cnt_jnt": 0.15,  # CNT_JNT
            "pattern": 0.20,  # Emerging pattern
        }

        # 가중치 정규화
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}

        self.budget = budget

        # 위험 카테고리 임계값
        self.risk_categories = risk_categories or {
            "critical": 80,  # 80점 이상
            "high": 60,  # 60-79점
            "medium": 40,  # 40-59점
            "low": 0,  # 40점 미만
        }

        self.output_dir = (
            Path(output_dir)
            if output_dir
            else RESULTS_DIR / "spatial_analysis" / "integrated_priority"
        )

        # 한글 폰트 설정
        setup_korean_font()

        # 데이터 저장소
        self.all_results = {}
        self.priority_scores = []
        self.decision_matrix = None

    def load_all_results(self) -> bool:
        """모든 분석 결과 로드"""
        print("\n=== 통합 분석 데이터 로드 중 ===")

        results_loaded = []

        # 1. K-factors/D_final grid (main21)
        kfactors_file = (
            RESULTS_DIR / "spatial_analysis" / "0520_kfactors_dfinal_grid.csv"
        )
        if kfactors_file.exists():
            self.all_results["kfactors"] = pd.read_csv(kfactors_file)
            results_loaded.append(
                f"K-factors grid: {len(self.all_results['kfactors'])} cells"
            )

        # 2. Hotspot results (main22)
        hotspot_file = (
            RESULTS_DIR / "spatial_analysis" / "hotspots" / "hotspot_results.geojson"
        )
        if hotspot_file.exists():
            self.all_results["hotspots"] = gpd.read_file(hotspot_file)
            results_loaded.append(
                f"Hotspots: {len(self.all_results['hotspots'])} cells"
            )

        # 3. Infrastructure analysis (main23)
        infra_file = (
            RESULTS_DIR
            / "spatial_analysis"
            / "infrastructure"
            / "infrastructure_correlation_results.json"
        )
        if infra_file.exists():
            with open(infra_file, encoding="utf-8") as f:
                self.all_results["infrastructure"] = json.load(f)
            results_loaded.append("Infrastructure analysis loaded")

        # 4. Emerging patterns (main25)
        emerging_file = (
            RESULTS_DIR
            / "spatial_analysis"
            / "emerging"
            / "kfactors_dfinal_evolution.json"
        )
        if emerging_file.exists():
            with open(emerging_file, encoding="utf-8") as f:
                self.all_results["emerging"] = json.load(f)
            results_loaded.append("Emerging patterns loaded")

        # 5. Priority rankings (main26)
        priority_file = (
            RESULTS_DIR / "spatial_analysis" / "priority" / "priority_rankings.csv"
        )
        if priority_file.exists():
            self.all_results["existing_priority"] = pd.read_csv(priority_file)
            results_loaded.append(
                f"Existing priority: {len(self.all_results['existing_priority'])} cells"
            )

        # 6. K-factors evolution (main27)
        evolution_file = (
            RESULTS_DIR
            / "spatial_analysis"
            / "kfactors_evolution"
            / "kfactors_evolution_results.json"
        )
        if evolution_file.exists():
            with open(evolution_file, encoding="utf-8") as f:
                self.all_results["evolution"] = json.load(f)
            results_loaded.append("K-factors evolution loaded")

        # 7. Predictions (main28)
        prediction_file = (
            RESULTS_DIR
            / "spatial_analysis"
            / "predictions"
            / "kfactors_prediction_results.json"
        )
        if prediction_file.exists():
            with open(prediction_file, encoding="utf-8") as f:
                self.all_results["predictions"] = json.load(f)
            results_loaded.append("Predictions loaded")

        print(f"✓ 로드된 데이터셋: {len(results_loaded)}개")
        for item in results_loaded:
            print(f"  - {item}")

        return len(results_loaded) > 0

    def calculate_integrated_scores(self) -> pd.DataFrame:
        """통합 우선순위 점수 계산"""
        print("\n=== 통합 우선순위 점수 계산 ===")

        # 기본 데이터프레임 생성
        if "kfactors" in self.all_results:
            base_df = self.all_results["kfactors"].copy()
        elif "hotspots" in self.all_results:
            base_df = self.all_results["hotspots"].copy()
        else:
            print("기본 데이터 없음")
            return pd.DataFrame()

        # cell_id가 없으면 생성
        if "cell_id" not in base_df.columns:
            if "grid_x" in base_df.columns and "grid_y" in base_df.columns:
                base_df["cell_id"] = (
                    base_df["grid_x"].astype(str) + "_" + base_df["grid_y"].astype(str)
                )
            else:
                base_df["cell_id"] = base_df.index.astype(str)

        # 1. K-factors/D_final 점수 (0-100 정규화)
        kfactors_score = pd.Series(0, index=base_df.index)
        if "composite_score" in base_df.columns:
            kfactors_score = base_df["composite_score"]
        elif "K_total" in base_df.columns and "D_final" in base_df.columns:
            kfactors_score = base_df["K_total"] * base_df["D_final"]

        # 정규화
        if kfactors_score.max() > 0:
            kfactors_score = (
                (kfactors_score - kfactors_score.min())
                / (kfactors_score.max() - kfactors_score.min())
                * 100
            )

        base_df["kfactors_score"] = kfactors_score

        # 2. Hotspot 점수
        hotspot_score = pd.Series(0, index=base_df.index)
        if (
            "hotspots" in self.all_results
            and "z_score" in self.all_results["hotspots"].columns
        ):
            # cell_id로 매칭
            hotspot_dict = (
                self.all_results["hotspots"].set_index("cell_id")["z_score"].to_dict()
            )
            hotspot_score = base_df["cell_id"].map(hotspot_dict).fillna(0)

            # z-score를 0-100으로 변환
            hotspot_score = hotspot_score.clip(lower=-3, upper=3)  # -3 ~ 3 범위로 제한
            hotspot_score = (hotspot_score + 3) / 6 * 100  # 0-100으로 변환

        base_df["hotspot_score"] = hotspot_score

        # 3. CNT_JNT 점수
        cnt_jnt_score = pd.Series(0, index=base_df.index)
        if "CNT_JNT" in base_df.columns:
            cnt_jnt_score = base_df["CNT_JNT"].fillna(0)
            # 정규화
            if cnt_jnt_score.max() > 0:
                cnt_jnt_score = (
                    (cnt_jnt_score - cnt_jnt_score.min())
                    / (cnt_jnt_score.max() - cnt_jnt_score.min())
                    * 100
                )

        base_df["cnt_jnt_score"] = cnt_jnt_score

        # 4. Pattern 점수
        pattern_score = pd.Series(50, index=base_df.index)  # 기본값 50
        pattern_weights = {
            "New Hot Spot": 90,
            "Intensifying": 100,
            "Persistent": 80,
            "Diminishing": 30,
            "Oscillating": 60,
            "Sporadic": 40,
            "Other": 50,
        }

        if (
            "emerging" in self.all_results
            and "patterns" in self.all_results["emerging"]
        ):
            for cell_id, pattern_info in self.all_results["emerging"][
                "patterns"
            ].items():
                if cell_id in base_df["cell_id"].values:
                    idx = base_df[base_df["cell_id"] == cell_id].index[0]
                    pattern_type = pattern_info.get("pattern", "Other")
                    pattern_score.loc[idx] = pattern_weights.get(pattern_type, 50)

        base_df["pattern_score"] = pattern_score

        # 5. 통합 점수 계산
        base_df["integrated_score"] = (
            self.weights["kfactors"] * base_df["kfactors_score"]
            + self.weights["hotspot"] * base_df["hotspot_score"]
            + self.weights["cnt_jnt"] * base_df["cnt_jnt_score"]
            + self.weights["pattern"] * base_df["pattern_score"]
        )

        # 6. 위험 카테고리 분류
        def categorize_risk(score):
            if score >= self.risk_categories["critical"]:
                return "Critical"
            if score >= self.risk_categories["high"]:
                return "High"
            if score >= self.risk_categories["medium"]:
                return "Medium"
            return "Low"

        base_df["risk_category"] = base_df["integrated_score"].apply(categorize_risk)

        # 7. 우선순위 순위
        base_df["priority_rank"] = (
            base_df["integrated_score"].rank(ascending=False, method="min").astype(int)
        )

        # 정렬
        base_df = base_df.sort_values("integrated_score", ascending=False)

        print(f"  통합 점수 계산 완료: {len(base_df)} cells")
        print(f"  평균 점수: {base_df['integrated_score'].mean():.2f}")
        print(f"  최고 점수: {base_df['integrated_score'].max():.2f}")

        # 위험 카테고리별 집계
        risk_counts = base_df["risk_category"].value_counts()
        print("\n  위험 카테고리 분포:")
        for category in ["Critical", "High", "Medium", "Low"]:
            count = risk_counts.get(category, 0)
            print(f"    - {category}: {count}개")

        return base_df

    def perform_cost_benefit_analysis(self, priority_df: pd.DataFrame) -> pd.DataFrame:
        """비용-편익 분석"""
        print("\n=== 비용-편익 분석 ===")

        # 예상 비용 (위험도에 따라 증가)
        cost_factors = {"Critical": 2.0, "High": 1.5, "Medium": 1.0, "Low": 0.5}

        base_cost = 1000  # 기본 비용 (만원)

        priority_df["estimated_cost"] = priority_df.apply(
            lambda row: base_cost
            * cost_factors.get(row["risk_category"], 1.0)
            * (1 + row["kfactors_score"] / 100),  # K-factors에 따른 조정
            axis=1,
        )

        # 예상 편익 (위험 감소)
        priority_df["risk_reduction"] = priority_df.apply(
            lambda row: row["integrated_score"] * 0.7, axis=1  # 70% 위험 감소 가정
        )

        # 편익 (연간 예상 손실 방지액)
        annual_loss_per_score = 10  # 점수당 연간 손실액 (만원)
        priority_df["annual_benefit"] = (
            priority_df["risk_reduction"] * annual_loss_per_score
        )

        # ROI 계산
        priority_df["roi"] = (
            (priority_df["annual_benefit"] - priority_df["estimated_cost"])
            / priority_df["estimated_cost"]
            * 100
        )

        # 투자회수기간 (개월)
        priority_df["payback_months"] = priority_df["estimated_cost"] / (
            priority_df["annual_benefit"] / 12
        )
        priority_df["payback_months"] = priority_df["payback_months"].clip(
            upper=120
        )  # 최대 10년

        print(f"  총 예상 비용: {priority_df['estimated_cost'].sum():,.0f}만원")
        print(f"  총 연간 편익: {priority_df['annual_benefit'].sum():,.0f}만원")
        print(f"  평균 ROI: {priority_df['roi'].mean():.1f}%")

        # 예산 제약 적용
        if self.budget:
            print(f"\n  예산 제약: {self.budget:,.0f}만원")

            # 누적 비용 계산
            priority_df["cumulative_cost"] = priority_df["estimated_cost"].cumsum()

            # 예산 내 작업
            within_budget = priority_df[priority_df["cumulative_cost"] <= self.budget]
            print(f"  예산 내 처리 가능: {len(within_budget)}개 지역")
            print(
                f"  예산 내 총 비용: {within_budget['estimated_cost'].sum():,.0f}만원"
            )
            print(
                f"  예산 내 연간 편익: {within_budget['annual_benefit'].sum():,.0f}만원"
            )

        return priority_df

    def create_decision_matrix(self, priority_df: pd.DataFrame) -> pd.DataFrame:
        """의사결정 매트릭스 생성"""
        print("\n=== 의사결정 매트릭스 생성 ===")

        # 주요 컬럼만 선택
        decision_cols = [
            "cell_id",
            "priority_rank",
            "integrated_score",
            "risk_category",
            "kfactors_score",
            "hotspot_score",
            "cnt_jnt_score",
            "pattern_score",
            "estimated_cost",
            "annual_benefit",
            "roi",
            "payback_months",
        ]

        # 필요한 컬럼만 있는지 확인
        available_cols = [col for col in decision_cols if col in priority_df.columns]
        decision_matrix = priority_df[available_cols].copy()

        # 액션 플랜 추가
        def generate_action_plan(row):
            if row["risk_category"] == "Critical":
                return "즉시 교체 및 모니터링 강화"
            if row["risk_category"] == "High":
                return "3개월 내 정밀 점검 및 부분 교체"
            if row["risk_category"] == "Medium":
                return "6개월 내 정기 점검 및 예방 정비"
            return "연간 정기 점검"

        decision_matrix["action_plan"] = decision_matrix.apply(
            generate_action_plan, axis=1
        )

        # 우선순위 레이블
        def priority_label(rank):
            if rank <= 10:
                return "최우선"
            if rank <= 50:
                return "우선"
            if rank <= 100:
                return "일반"
            return "관찰"

        decision_matrix["priority_label"] = decision_matrix["priority_rank"].apply(
            priority_label
        )

        print(f"  의사결정 매트릭스 생성 완료: {len(decision_matrix)} rows")

        # 상위 10개 출력
        print("\n  상위 10개 우선순위:")
        top10 = decision_matrix.head(10)
        for idx, row in top10.iterrows():
            print(
                f"    #{row['priority_rank']}: {row['cell_id']} "
                f"(점수: {row['integrated_score']:.1f}, "
                f"카테고리: {row['risk_category']}, "
                f"액션: {row['action_plan']})"
            )

        return decision_matrix

    def visualize_integrated_priority(self):
        """통합 우선순위 시각화"""
        print("\n=== 통합 우선순위 시각화 ===")

        fig, axes = plt.subplots(2, 3, figsize=(18, 12))

        # 1. 구성요소별 기여도
        ax = axes[0, 0]

        # 가중치 파이 차트
        weights_df = pd.DataFrame.from_dict(
            self.weights, orient="index", columns=["Weight"]
        )
        weights_df["Percentage"] = weights_df["Weight"] * 100

        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
        wedges, texts, autotexts = ax.pie(
            weights_df["Percentage"],
            labels=weights_df.index,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
        )
        ax.set_title("우선순위 구성요소 가중치", fontsize=12, fontweight="bold")

        # 2. 위험 카테고리 분포
        ax = axes[0, 1]

        if not self.priority_scores.empty:
            risk_counts = self.priority_scores["risk_category"].value_counts()
            risk_colors = {
                "Critical": "red",
                "High": "orange",
                "Medium": "yellow",
                "Low": "green",
            }

            bars = ax.bar(
                risk_counts.index,
                risk_counts.values,
                color=[risk_colors.get(x, "gray") for x in risk_counts.index],
            )
            ax.set_ylabel("지역 수")
            ax.set_title("위험 카테고리 분포", fontsize=12, fontweight="bold")

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

        # 3. 통합 점수 분포
        ax = axes[0, 2]

        if not self.priority_scores.empty:
            ax.hist(
                self.priority_scores["integrated_score"],
                bins=30,
                color="steelblue",
                alpha=0.7,
                edgecolor="black",
            )
            ax.axvline(
                self.priority_scores["integrated_score"].mean(),
                color="red",
                linestyle="--",
                label="평균",
            )
            ax.set_xlabel("통합 점수")
            ax.set_ylabel("빈도")
            ax.set_title("통합 점수 분포", fontsize=12, fontweight="bold")
            ax.legend()

        # 4. 구성요소별 점수 상관관계
        ax = axes[1, 0]

        if not self.priority_scores.empty:
            score_cols = [
                "kfactors_score",
                "hotspot_score",
                "cnt_jnt_score",
                "pattern_score",
            ]
            available_score_cols = [
                col for col in score_cols if col in self.priority_scores.columns
            ]

            if len(available_score_cols) > 1:
                corr_matrix = self.priority_scores[available_score_cols].corr()
                sns.heatmap(
                    corr_matrix,
                    annot=True,
                    fmt=".2f",
                    cmap="coolwarm",
                    center=0,
                    ax=ax,
                    cbar_kws={"label": "상관계수"},
                )
                ax.set_title("구성요소 간 상관관계", fontsize=12, fontweight="bold")

        # 5. ROI 분석
        ax = axes[1, 1]

        if not self.priority_scores.empty and "roi" in self.priority_scores.columns:
            # ROI별 지역 수
            roi_bins = [-100, 0, 50, 100, 200, 1000]
            roi_labels = ["< 0%", "0-50%", "50-100%", "100-200%", "> 200%"]
            self.priority_scores["roi_category"] = pd.cut(
                self.priority_scores["roi"], bins=roi_bins, labels=roi_labels
            )

            roi_counts = self.priority_scores["roi_category"].value_counts()
            bars = ax.bar(
                roi_counts.index,
                roi_counts.values,
                color=["red", "orange", "yellow", "lightgreen", "green"],
            )
            ax.set_xlabel("ROI 범위")
            ax.set_ylabel("지역 수")
            ax.set_title("투자수익률(ROI) 분포", fontsize=12, fontweight="bold")

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

        # 6. 우선순위 상위 지역 특성
        ax = axes[1, 2]

        if not self.priority_scores.empty:
            top20 = self.priority_scores.head(20)

            # 각 구성요소의 평균 기여도
            components = [
                "kfactors_score",
                "hotspot_score",
                "cnt_jnt_score",
                "pattern_score",
            ]
            available_components = [c for c in components if c in top20.columns]

            if available_components:
                means = [top20[c].mean() for c in available_components]
                labels = [c.replace("_score", "") for c in available_components]

                bars = ax.bar(
                    labels, means, color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
                )
                ax.set_ylabel("평균 점수")
                ax.set_title(
                    "상위 20개 지역 구성요소 평균", fontsize=12, fontweight="bold"
                )
                ax.set_ylim([0, 100])

                # 값 표시
                for bar, val in zip(bars, means, strict=False):
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{val:.1f}",
                        ha="center",
                        va="bottom",
                    )

        plt.suptitle(
            "Integrated Priority Analysis", fontsize=14, fontweight="bold", y=1.02
        )
        plt.tight_layout()

        # 저장
        output_path = self.output_dir / "integrated_priority_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"통합 우선순위 시각화 저장: {output_path}")

    def generate_report(self):
        """통합 보고서 생성"""
        print("\n=== 통합 보고서 생성 중 ===")

        report_lines = [
            "# Integrated Priority Analysis Report",
            f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. 분석 설정",
            "### 가중치",
            f"- K-factors/D_final: {self.weights['kfactors']*100:.1f}%",
            f"- Hotspot: {self.weights['hotspot']*100:.1f}%",
            f"- CNT_JNT: {self.weights['cnt_jnt']*100:.1f}%",
            f"- Pattern: {self.weights['pattern']*100:.1f}%",
            "\n### 위험 카테고리 임계값",
            f"- Critical: ≥ {self.risk_categories['critical']}점",
            f"- High: {self.risk_categories['high']}-{self.risk_categories['critical']-1}점",
            f"- Medium: {self.risk_categories['medium']}-{self.risk_categories['high']-1}점",
            f"- Low: < {self.risk_categories['medium']}점",
        ]

        if self.budget:
            report_lines.append(f"\n### 예산 제약: {self.budget:,.0f}만원")

        # 통계 요약
        if not self.priority_scores.empty:
            report_lines.extend(
                [
                    "\n## 2. 통계 요약",
                    f"- 총 분석 지역: {len(self.priority_scores)}개",
                    f"- 평균 통합 점수: {self.priority_scores['integrated_score'].mean():.2f}",
                    f"- 최고 점수: {self.priority_scores['integrated_score'].max():.2f}",
                    f"- 표준편차: {self.priority_scores['integrated_score'].std():.2f}",
                ]
            )

            # 위험 카테고리 분포
            risk_counts = self.priority_scores["risk_category"].value_counts()
            report_lines.append("\n### 위험 카테고리 분포")
            for category in ["Critical", "High", "Medium", "Low"]:
                count = risk_counts.get(category, 0)
                pct = count / len(self.priority_scores) * 100
                report_lines.append(f"- {category}: {count}개 ({pct:.1f}%)")

        # 상위 20개 우선순위
        if not self.priority_scores.empty:
            report_lines.append("\n## 3. 상위 20개 우선순위 지역")
            report_lines.append(
                "\n| 순위 | Cell ID | 통합점수 | 카테고리 | K-factors | 액션플랜 |"
            )
            report_lines.append(
                "|------|---------|----------|----------|-----------|----------|"
            )

            top20 = self.priority_scores.head(20)
            for idx, row in top20.iterrows():
                action = (
                    self.decision_matrix.loc[idx, "action_plan"]
                    if self.decision_matrix is not None
                    else "N/A"
                )
                report_lines.append(
                    f"| {row['priority_rank']} | {row['cell_id']} | "
                    f"{row['integrated_score']:.1f} | {row['risk_category']} | "
                    f"{row.get('kfactors_score', 0):.1f} | {action} |"
                )

        # 비용-편익 분석 요약
        if "estimated_cost" in self.priority_scores.columns:
            report_lines.extend(
                [
                    "\n## 4. 비용-편익 분석",
                    f"- 총 예상 비용: {self.priority_scores['estimated_cost'].sum():,.0f}만원",
                    f"- 총 연간 편익: {self.priority_scores['annual_benefit'].sum():,.0f}만원",
                    f"- 평균 ROI: {self.priority_scores['roi'].mean():.1f}%",
                    f"- 평균 투자회수기간: {self.priority_scores['payback_months'].mean():.1f}개월",
                ]
            )

            # 예산 내 처리 가능
            if self.budget and "cumulative_cost" in self.priority_scores.columns:
                within_budget = self.priority_scores[
                    self.priority_scores["cumulative_cost"] <= self.budget
                ]
                report_lines.extend(
                    [
                        "\n### 예산 제약 분석",
                        f"- 예산 내 처리 가능: {len(within_budget)}개 지역",
                        f"- 예산 내 총 비용: {within_budget['estimated_cost'].sum():,.0f}만원",
                        f"- 예산 내 연간 편익: {within_budget['annual_benefit'].sum():,.0f}만원",
                        f"- 예산 내 평균 ROI: {within_budget['roi'].mean():.1f}%",
                    ]
                )

        # 권장사항
        report_lines.extend(
            [
                "\n## 5. 권장사항",
                "- Critical 등급 지역 즉시 조치 필요",
                "- K-factors/D_final 점수가 높은 지역 우선 처리",
                "- ROI가 높은 지역부터 순차적 진행",
                "- 예산 제약 시 Critical/High 등급 우선",
                "- 정기적인 우선순위 재평가 필요",
            ]
        )

        # 파일 저장
        report_path = self.output_dir / "integrated_priority_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"보고서 저장: {report_path}")

    def save_results(self):
        """결과 저장"""
        print("\n=== 결과 저장 중 ===")

        # 우선순위 CSV 저장
        if not self.priority_scores.empty:
            priority_path = self.output_dir / "integrated_priority_rankings.csv"
            self.priority_scores.to_csv(
                priority_path, index=False, encoding="utf-8-sig"
            )
            print(f"우선순위 순위 저장: {priority_path}")

        # 의사결정 매트릭스 저장
        if self.decision_matrix is not None:
            matrix_path = self.output_dir / "decision_matrix.csv"
            self.decision_matrix.to_csv(matrix_path, index=False, encoding="utf-8-sig")
            print(f"의사결정 매트릭스 저장: {matrix_path}")

        # 메타데이터 저장
        metadata = {
            "weights": self.weights,
            "risk_categories": self.risk_categories,
            "budget": self.budget,
            "generated_at": datetime.now().isoformat(),
            "total_cells": (
                len(self.priority_scores) if not self.priority_scores.empty else 0
            ),
            "statistics": {
                "mean_score": (
                    float(self.priority_scores["integrated_score"].mean())
                    if not self.priority_scores.empty
                    else 0
                ),
                "max_score": (
                    float(self.priority_scores["integrated_score"].max())
                    if not self.priority_scores.empty
                    else 0
                ),
                "std_score": (
                    float(self.priority_scores["integrated_score"].std())
                    if not self.priority_scores.empty
                    else 0
                ),
            },
        }

        metadata_path = self.output_dir / "integrated_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"메타데이터 저장: {metadata_path}")

    def run(self):
        """전체 분석 실행"""
        print("\n" + "=" * 60)
        print("Integrated Priority Analysis (Phase 11)")
        print("=" * 60)

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 데이터 로드
        if not self.load_all_results():
            print("데이터 로드 실패")
            return False

        # 통합 점수 계산
        self.priority_scores = self.calculate_integrated_scores()

        if self.priority_scores.empty:
            print("통합 점수 계산 실패")
            return False

        # 비용-편익 분석
        self.priority_scores = self.perform_cost_benefit_analysis(self.priority_scores)

        # 의사결정 매트릭스 생성
        self.decision_matrix = self.create_decision_matrix(self.priority_scores)

        # 시각화
        self.visualize_integrated_priority()

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
        description="Integrated Priority Analysis (Phase 11)"
    )

    # 가중치 설정
    parser.add_argument(
        "--weight-hotspot", type=float, default=0.25, help="핫스팟 가중치"
    )
    parser.add_argument(
        "--weight-kfactors", type=float, default=0.40, help="K-factors/D_final 가중치"
    )
    parser.add_argument(
        "--weight-cnt-jnt", type=float, default=0.15, help="CNT_JNT 가중치"
    )
    parser.add_argument(
        "--weight-pattern", type=float, default=0.20, help="Emerging pattern 가중치"
    )

    # 예산 제약
    parser.add_argument("--budget", type=float, help="예산 제약 (만원)")

    # 위험 카테고리
    parser.add_argument(
        "--critical-threshold", type=float, default=80, help="Critical 카테고리 임계값"
    )
    parser.add_argument(
        "--high-threshold", type=float, default=60, help="High 카테고리 임계값"
    )
    parser.add_argument(
        "--medium-threshold", type=float, default=40, help="Medium 카테고리 임계값"
    )

    # 출력 디렉토리
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/integrated_priority",
        help="결과 저장 디렉토리",
    )

    args = parser.parse_args()

    # 가중치 딕셔너리 생성
    weights = {
        "hotspot": args.weight_hotspot,
        "kfactors": args.weight_kfactors,
        "cnt_jnt": args.weight_cnt_jnt,
        "pattern": args.weight_pattern,
    }

    # 위험 카테고리 딕셔너리
    risk_categories = {
        "critical": args.critical_threshold,
        "high": args.high_threshold,
        "medium": args.medium_threshold,
        "low": 0,
    }

    # 분석기 생성 및 실행
    analyzer = IntegratedPriorityAnalyzer(
        weights=weights,
        budget=args.budget,
        risk_categories=risk_categories,
        output_dir=args.output_dir,
    )

    success = analyzer.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
