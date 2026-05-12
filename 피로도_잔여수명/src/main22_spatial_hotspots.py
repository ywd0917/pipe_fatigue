"""
main21_spatial_hotspots.py

520 지역의 공간 핫스팟 분석 스크립트.
Getis-Ord Gi*와 Moran's I를 사용하여 재작업 핫스팟을 식별합니다.
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
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.korean_font_utils import setup_korean_font
from src.common.spatial_utils import (
    calculate_getis_ord_gi,
    calculate_morans_i,
    create_spacetime_grid,
    create_spatial_weights_matrix,
    identify_hotspots,
)

warnings.filterwarnings("ignore")


class SpatialHotspotAnalyzer:
    """공간 핫스팟 분석 클래스"""

    def __init__(self, gdf: gpd.GeoDataFrame, params: dict[str, Any]):
        """
        Parameters
        ----------
        gdf : GeoDataFrame
            520 지역 재작업 데이터
        params : dict
            분석 파라미터
        """
        self.gdf = gdf
        self.params = params
        self.grid_gdf = None
        self.hotspot_results = None
        self.morans_results = None

        # 한글 폰트 설정
        setup_korean_font()

    def create_grid_aggregation(self) -> gpd.GeoDataFrame:
        """그리드 생성 및 데이터 집계"""
        print(
            f"\n{self.params['grid_size']}m × {self.params['grid_size']}m 그리드 생성 중..."
        )

        # 그리드 생성
        self.grid_gdf = create_spacetime_grid(
            self.gdf,
            grid_size=self.params["grid_size"],
            time_column=None,  # 공간 분석만
        )

        # 각 그리드 셀에 대한 통계 계산
        for idx, cell in self.grid_gdf.iterrows():
            points_in_cell = self.gdf[self.gdf.geometry.within(cell.geometry)]

            # 재작업 횟수
            self.grid_gdf.at[idx, "repair_count"] = len(points_in_cell)

            # CNT_JNT 통계 (있는 경우)
            if "CNT_JNT" in self.gdf.columns and len(points_in_cell) > 0:
                cnt_jnt_values = points_in_cell["CNT_JNT"].dropna()
                if len(cnt_jnt_values) > 0:
                    self.grid_gdf.at[idx, "mean_cnt_jnt"] = cnt_jnt_values.mean()
                    self.grid_gdf.at[idx, "max_cnt_jnt"] = cnt_jnt_values.max()
                    self.grid_gdf.at[idx, "sum_cnt_jnt"] = cnt_jnt_values.sum()
                else:
                    self.grid_gdf.at[idx, "mean_cnt_jnt"] = 0
                    self.grid_gdf.at[idx, "max_cnt_jnt"] = 0
                    self.grid_gdf.at[idx, "sum_cnt_jnt"] = 0

            # K-factors 통계 (있는 경우)
            for k_factor in [
                "K_total",
                "K_age",
                "K_soil",
                "K_traffic",
                "hoop_stress",
                "D_final",
            ]:
                if k_factor in self.gdf.columns and len(points_in_cell) > 0:
                    values = points_in_cell[k_factor].dropna()
                    if len(values) > 0:
                        self.grid_gdf.at[idx, f"mean_{k_factor}"] = values.mean()
                        self.grid_gdf.at[idx, f"max_{k_factor}"] = values.max()

        # 빈 셀 제거 (옵션)
        self.grid_gdf = self.grid_gdf[self.grid_gdf["repair_count"] > 0].copy()

        print(f"생성된 그리드 셀: {len(self.grid_gdf)}개")
        print(f"평균 재작업 횟수: {self.grid_gdf['repair_count'].mean():.2f}")

        return self.grid_gdf

    def calculate_global_morans_i(self) -> tuple[float, float, float]:
        """Global Moran's I 계산"""
        print("\nGlobal Moran's I 계산 중...")

        # 공간 가중치 행렬 생성
        W = create_spatial_weights_matrix(
            self.grid_gdf,
            method="distance",
            threshold=self.params["distance_threshold"],
            binary=True,
        )

        # 재작업 횟수로 Moran's I 계산
        values = self.grid_gdf["repair_count"].values
        I, z_score, p_value = calculate_morans_i(values, W)

        print(f"Moran's I: {I:.4f}")
        print(f"Z-score: {z_score:.4f}")
        print(f"P-value: {p_value:.4f}")

        if p_value < 0.05:
            if I > 0:
                print("→ 유의미한 공간 군집 패턴 발견 (핫스팟 존재)")
            else:
                print("→ 유의미한 공간 분산 패턴 발견")
        else:
            print("→ 무작위 공간 패턴")

        self.morans_results = {"I": I, "z_score": z_score, "p_value": p_value}

        return I, z_score, p_value

    def calculate_getis_ord_gi(self) -> gpd.GeoDataFrame:
        """Getis-Ord Gi* 통계 계산"""
        print("\nGetis-Ord Gi* 계산 중...")

        # 공간 가중치 행렬 생성
        W = create_spatial_weights_matrix(
            self.grid_gdf,
            method="distance",
            threshold=self.params["distance_threshold"],
            binary=True,
        )

        # Gi* z-scores 계산
        values = self.grid_gdf["repair_count"].values
        z_scores = calculate_getis_ord_gi(values, W, star=True)

        # 결과 저장
        self.grid_gdf["gi_star_z"] = z_scores

        # 핫스팟/콜드스팟 분류
        hotspot_classes = identify_hotspots(
            z_scores, confidence_levels=[0.90, 0.95, 0.99]
        )

        for conf_level, classification in hotspot_classes.items():
            self.grid_gdf[f"hotspot_{conf_level}"] = classification

        # 통계 출력
        for conf_level in ["confidence_90", "confidence_95", "confidence_99"]:
            hot = np.sum(self.grid_gdf[f"hotspot_{conf_level}"] == 1)
            cold = np.sum(self.grid_gdf[f"hotspot_{conf_level}"] == -1)
            print(f"{conf_level}: 핫스팟 {hot}개, 콜드스팟 {cold}개")

        return self.grid_gdf

    def analyze_cnt_jnt_correlation(self) -> dict[str, Any]:
        """CNT_JNT와 핫스팟 상관관계 분석"""
        if "mean_cnt_jnt" not in self.grid_gdf.columns:
            print("\nCNT_JNT 데이터 없음 - 분석 건너뜀")
            return {}

        print("\nCNT_JNT와 핫스팟 상관관계 분석 중...")

        results = {}

        # 핫스팟 유형별 CNT_JNT 비교
        hotspot_99 = self.grid_gdf["hotspot_confidence_99"]

        hot_cells = self.grid_gdf[hotspot_99 == 1]
        cold_cells = self.grid_gdf[hotspot_99 == -1]
        normal_cells = self.grid_gdf[hotspot_99 == 0]

        results["cnt_jnt_by_type"] = {
            "hotspot": {
                "mean": hot_cells["mean_cnt_jnt"].mean() if len(hot_cells) > 0 else 0,
                "median": (
                    hot_cells["mean_cnt_jnt"].median() if len(hot_cells) > 0 else 0
                ),
                "count": len(hot_cells),
            },
            "coldspot": {
                "mean": cold_cells["mean_cnt_jnt"].mean() if len(cold_cells) > 0 else 0,
                "median": (
                    cold_cells["mean_cnt_jnt"].median() if len(cold_cells) > 0 else 0
                ),
                "count": len(cold_cells),
            },
            "normal": {
                "mean": (
                    normal_cells["mean_cnt_jnt"].mean() if len(normal_cells) > 0 else 0
                ),
                "median": (
                    normal_cells["mean_cnt_jnt"].median()
                    if len(normal_cells) > 0
                    else 0
                ),
                "count": len(normal_cells),
            },
        }

        # 상관계수 계산
        from scipy.stats import pearsonr, spearmanr

        if len(self.grid_gdf) > 3:
            pearson_r, pearson_p = pearsonr(
                self.grid_gdf["gi_star_z"], self.grid_gdf["mean_cnt_jnt"]
            )
            spearman_r, spearman_p = spearmanr(
                self.grid_gdf["gi_star_z"], self.grid_gdf["mean_cnt_jnt"]
            )

            results["correlation"] = {
                "pearson_r": pearson_r,
                "pearson_p": pearson_p,
                "spearman_r": spearman_r,
                "spearman_p": spearman_p,
            }

            print(f"Pearson 상관계수: {pearson_r:.3f} (p={pearson_p:.3f})")
            print(f"Spearman 상관계수: {spearman_r:.3f} (p={spearman_p:.3f})")

        # ANOVA 또는 Kruskal-Wallis 검정
        from scipy.stats import f_oneway, kruskal

        groups = []
        if len(hot_cells) > 0:
            groups.append(hot_cells["mean_cnt_jnt"].values)
        if len(normal_cells) > 0:
            groups.append(normal_cells["mean_cnt_jnt"].values)
        if len(cold_cells) > 0:
            groups.append(cold_cells["mean_cnt_jnt"].values)

        if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
            f_stat, anova_p = f_oneway(*groups)
            h_stat, kw_p = kruskal(*groups)

            results["statistical_tests"] = {
                "anova_f": f_stat,
                "anova_p": anova_p,
                "kruskal_h": h_stat,
                "kruskal_p": kw_p,
            }

            print(f"ANOVA F-statistic: {f_stat:.3f} (p={anova_p:.3f})")
            print(f"Kruskal-Wallis H: {h_stat:.3f} (p={kw_p:.3f})")

        return results

    def visualize_hotspots(self, output_dir: str):
        """핫스팟 시각화"""
        print("\n핫스팟 시각화 중...")

        fig, axes = plt.subplots(2, 2, figsize=(20, 20))

        # 1. 원시 재작업 포인트
        ax = axes[0, 0]
        self.gdf.plot(ax=ax, color="red", markersize=1, alpha=0.5)
        ax.set_title("원시 재작업 위치", fontsize=14)
        ax.set_xlabel("X 좌표 (m)")
        ax.set_ylabel("Y 좌표 (m)")

        # 2. 그리드 집계
        ax = axes[0, 1]
        self.grid_gdf.plot(
            column="repair_count",
            ax=ax,
            legend=True,
            cmap="YlOrRd",
            legend_kwds={"label": "재작업 횟수"},
        )
        ax.set_title(f'그리드 집계 ({self.params["grid_size"]}m)', fontsize=14)
        ax.set_xlabel("X 좌표 (m)")
        ax.set_ylabel("Y 좌표 (m)")

        # 3. Gi* Z-scores
        ax = axes[1, 0]
        vmin, vmax = -3, 3
        self.grid_gdf.plot(
            column="gi_star_z",
            ax=ax,
            legend=True,
            cmap="RdBu_r",
            vmin=vmin,
            vmax=vmax,
            legend_kwds={"label": "Gi* Z-score"},
        )
        ax.set_title("Getis-Ord Gi* Z-scores", fontsize=14)
        ax.set_xlabel("X 좌표 (m)")
        ax.set_ylabel("Y 좌표 (m)")

        # 4. 핫스팟/콜드스팟 분류 (99% 신뢰수준)
        ax = axes[1, 1]
        colors = {-1: "blue", 0: "gray", 1: "red"}
        labels = {-1: "콜드스팟", 0: "일반", 1: "핫스팟"}

        for value, color in colors.items():
            mask = self.grid_gdf["hotspot_confidence_99"] == value
            if mask.any():
                self.grid_gdf[mask].plot(
                    ax=ax, color=color, label=labels[value], alpha=0.7
                )

        ax.set_title("핫스팟/콜드스팟 (99% 신뢰수준)", fontsize=14)
        ax.set_xlabel("X 좌표 (m)")
        ax.set_ylabel("Y 좌표 (m)")
        ax.legend()

        plt.tight_layout()

        output_path = os.path.join(output_dir, "hotspot_analysis.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"시각화 저장: {output_path}")

        # CNT_JNT 상관관계 시각화 (있는 경우)
        if "mean_cnt_jnt" in self.grid_gdf.columns:
            self.visualize_cnt_jnt_correlation(output_dir)

    def visualize_cnt_jnt_correlation(self, output_dir: str):
        """CNT_JNT 상관관계 시각화"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        # 1. CNT_JNT 공간 분포
        ax = axes[0]
        self.grid_gdf.plot(
            column="mean_cnt_jnt",
            ax=ax,
            legend=True,
            cmap="viridis",
            legend_kwds={"label": "평균 CNT_JNT"},
        )
        ax.set_title("CNT_JNT 공간 분포", fontsize=14)
        ax.set_xlabel("X 좌표 (m)")
        ax.set_ylabel("Y 좌표 (m)")

        # 2. 산점도
        ax = axes[1]
        ax.scatter(self.grid_gdf["mean_cnt_jnt"], self.grid_gdf["gi_star_z"], alpha=0.5)
        ax.set_xlabel("평균 CNT_JNT")
        ax.set_ylabel("Gi* Z-score")
        ax.set_title("CNT_JNT vs 핫스팟 강도")
        ax.grid(True, alpha=0.3)

        # 3. 박스플롯
        ax = axes[2]
        data_for_plot = []
        labels_for_plot = []

        for value, label in [(-1, "콜드스팟"), (0, "일반"), (1, "핫스팟")]:
            mask = self.grid_gdf["hotspot_confidence_99"] == value
            if mask.any():
                data_for_plot.append(self.grid_gdf[mask]["mean_cnt_jnt"].values)
                labels_for_plot.append(label)

        if data_for_plot:
            ax.boxplot(data_for_plot, labels=labels_for_plot)
            ax.set_ylabel("평균 CNT_JNT")
            ax.set_title("핫스팟 유형별 CNT_JNT 분포")
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        output_path = os.path.join(output_dir, "cnt_jnt_correlation.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"CNT_JNT 상관관계 시각화 저장: {output_path}")

    def save_results(self, output_dir: str):
        """결과 저장"""
        # GeoDataFrame 저장
        output_path = os.path.join(output_dir, "hotspot_results.geojson")
        self.grid_gdf.to_file(output_path, driver="GeoJSON")
        print(f"공간 데이터 저장: {output_path}")

        # CSV로도 저장
        csv_path = os.path.join(output_dir, "hotspot_results.csv")
        df = self.grid_gdf.drop("geometry", axis=1)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"테이블 데이터 저장: {csv_path}")

        # 메타데이터 저장
        metadata = {
            "analysis_date": datetime.now().isoformat(),
            "parameters": self.params,
            "n_points": len(self.gdf),
            "n_grid_cells": len(self.grid_gdf),
            "morans_i_results": self.morans_results,
            "hotspot_counts": {
                "confidence_90": {
                    "hot": int(np.sum(self.grid_gdf["hotspot_confidence_90"] == 1)),
                    "cold": int(np.sum(self.grid_gdf["hotspot_confidence_90"] == -1)),
                },
                "confidence_95": {
                    "hot": int(np.sum(self.grid_gdf["hotspot_confidence_95"] == 1)),
                    "cold": int(np.sum(self.grid_gdf["hotspot_confidence_95"] == -1)),
                },
                "confidence_99": {
                    "hot": int(np.sum(self.grid_gdf["hotspot_confidence_99"] == 1)),
                    "cold": int(np.sum(self.grid_gdf["hotspot_confidence_99"] == -1)),
                },
            },
        }

        metadata_path = os.path.join(output_dir, "hotspot_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"메타데이터 저장: {metadata_path}")

    def generate_report(self, output_dir: str):
        """분석 보고서 생성"""
        report_lines = [
            "# 공간 핫스팟 분석 보고서",
            f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. 데이터 개요",
            f"- 총 재작업 포인트: {len(self.gdf):,}개",
            f"- 생성된 그리드 셀: {len(self.grid_gdf):,}개",
            f"- 그리드 크기: {self.params['grid_size']}m × {self.params['grid_size']}m",
            f"- 공간 가중치 거리: {self.params['distance_threshold']}m",
            "\n## 2. Global Moran's I 결과",
            f"- Moran's I: {self.morans_results['I']:.4f}",
            f"- Z-score: {self.morans_results['z_score']:.4f}",
            f"- P-value: {self.morans_results['p_value']:.4f}",
        ]

        if self.morans_results["p_value"] < 0.05:
            if self.morans_results["I"] > 0:
                report_lines.append("- **해석**: 유의미한 공간 군집 패턴 (핫스팟 존재)")
            else:
                report_lines.append("- **해석**: 유의미한 공간 분산 패턴")
        else:
            report_lines.append("- **해석**: 무작위 공간 패턴")

        report_lines.extend(
            [
                "\n## 3. 핫스팟 분석 결과",
                "\n### 신뢰수준별 핫스팟/콜드스팟 개수",
                "| 신뢰수준 | 핫스팟 | 콜드스팟 | 일반 |",
                "|---------|--------|----------|------|",
            ]
        )

        for conf_level in [90, 95, 99]:
            col_name = f"hotspot_confidence_{conf_level}"
            hot = np.sum(self.grid_gdf[col_name] == 1)
            cold = np.sum(self.grid_gdf[col_name] == -1)
            normal = np.sum(self.grid_gdf[col_name] == 0)
            report_lines.append(f"| {conf_level}% | {hot} | {cold} | {normal} |")

        # CNT_JNT 분석 결과 (있는 경우)
        if "mean_cnt_jnt" in self.grid_gdf.columns:
            report_lines.extend(
                [
                    "\n## 4. CNT_JNT 상관관계 분석",
                    "\n### 핫스팟 유형별 평균 CNT_JNT",
                    "| 구분 | 평균 CNT_JNT | 중앙값 | 개수 |",
                    "|------|-------------|--------|------|",
                ]
            )

            hotspot_99 = self.grid_gdf["hotspot_confidence_99"]
            for value, label in [(1, "핫스팟"), (0, "일반"), (-1, "콜드스팟")]:
                mask = hotspot_99 == value
                if mask.any():
                    mean_val = self.grid_gdf[mask]["mean_cnt_jnt"].mean()
                    median_val = self.grid_gdf[mask]["mean_cnt_jnt"].median()
                    count = mask.sum()
                    report_lines.append(
                        f"| {label} | {mean_val:.2f} | {median_val:.2f} | {count} |"
                    )

        report_lines.extend(
            [
                "\n## 5. 주요 발견사항",
                "- 핫스팟 지역은 재작업이 집중적으로 발생하는 구역",
                "- 콜드스팟 지역은 상대적으로 재작업이 적은 구역",
                "- 공간 자기상관이 높을수록 유사한 특성의 지역이 군집",
                "\n## 6. 권장사항",
                "- 핫스팟 지역에 대한 집중적인 유지보수 필요",
                "- 핫스팟 원인 분석을 위한 추가 조사 권장",
                "- 시계열 분석을 통한 핫스팟 진화 패턴 파악 필요",
            ]
        )

        report_path = os.path.join(output_dir, "hotspot_analysis_report.md")
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
                if "main21" in params:
                    return params["main21"]
                if "shared" in params:
                    # shared 파라미터 사용
                    return {
                        "grid_size": params["shared"]["grid_size"],
                        "distance_threshold": params["shared"].get("grid_size", 30) * 3,
                        "k_neighbors": 8,
                    }

    # 기본값
    return {"grid_size": 30, "distance_threshold": 100, "k_neighbors": 8}


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
    parser = argparse.ArgumentParser(description="520 지역 공간 핫스팟 분석")
    parser.add_argument("--grid-size", type=int, help="그리드 크기 (미터)")
    parser.add_argument("--distance", type=int, help="공간 가중치 거리 임계값 (미터)")
    parser.add_argument("--k-neighbors", type=int, help="k-최근접 이웃 수")
    parser.add_argument(
        "--use-optimal",
        action="store_true",
        default=True,
        help="main20에서 생성된 최적 파라미터 사용",
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/hotspots",
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
        if args.distance:
            params["distance_threshold"] = args.distance
        if args.k_neighbors:
            params["k_neighbors"] = args.k_neighbors

        print("\n사용 파라미터:")
        for key, value in params.items():
            print(f"  {key}: {value}")

        # 분석 실행
        analyzer = SpatialHotspotAnalyzer(gdf, params)

        # 그리드 생성 및 집계
        analyzer.create_grid_aggregation()

        # Global Moran's I
        analyzer.calculate_global_morans_i()

        # Getis-Ord Gi*
        analyzer.calculate_getis_ord_gi()

        # CNT_JNT 상관관계 분석
        analyzer.analyze_cnt_jnt_correlation()

        # 결과 저장
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        analyzer.save_results(str(output_dir))
        analyzer.visualize_hotspots(str(output_dir))
        analyzer.generate_report(str(output_dir))

        print(f"\n분석 완료! 결과: {output_dir}")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
