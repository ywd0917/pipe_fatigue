"""
main23_infrastructure_risk.py

핫스팟과 파이프 인프라(CNT_JNT, K-factors, D_final) 간의 상관관계 분석
Phase 2.5: Infrastructure Risk Correlation Analysis
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.korean_font_utils import setup_korean_font

warnings.filterwarnings("ignore")


class InfrastructureCorrelationAnalyzer:
    """핫스팟과 인프라 상관관계 분석 클래스"""

    def __init__(self, hotspot_dir: str, output_dir: str):
        """
        Parameters
        ----------
        hotspot_dir : str
            핫스팟 분석 결과 디렉토리
        output_dir : str
            출력 디렉토리
        """
        self.hotspot_dir = hotspot_dir
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self.hotspot_gdf = None
        self.joint_gdf = None
        self.fatigue_df = None
        self.analysis_results = {}

        # 한글 폰트 설정
        setup_korean_font()

    def load_hotspot_results(self) -> bool:
        """핫스팟 분석 결과 로드"""
        print("\n=== 핫스팟 분석 결과 로드 중 ===")

        # 핫스팟 결과 파일 경로
        hotspot_file = os.path.join(self.hotspot_dir, "hotspot_results.geojson")

        if not os.path.exists(hotspot_file):
            # 대체 경로 시도
            hotspot_file = os.path.join(self.hotspot_dir, "hotspot_grid.geojson")
            if not os.path.exists(hotspot_file):
                print(f"  ⚠️ 핫스팟 결과 파일을 찾을 수 없습니다: {self.hotspot_dir}")
                return False

        # GeoJSON 로드
        self.hotspot_gdf = gpd.read_file(hotspot_file)
        print(f"  ✓ 핫스팟 그리드 로드: {len(self.hotspot_gdf)} cells")

        # 핫스팟 분류 통계
        if "hotspot_confidence_90" in self.hotspot_gdf.columns:
            hotspots_90 = (self.hotspot_gdf["hotspot_confidence_90"] == 1).sum()
            coldspots_90 = (self.hotspot_gdf["hotspot_confidence_90"] == -1).sum()
            print(f"  90% 신뢰수준: 핫스팟 {hotspots_90}개, 콜드스팟 {coldspots_90}개")

        if "hotspot_confidence_95" in self.hotspot_gdf.columns:
            hotspots_95 = (self.hotspot_gdf["hotspot_confidence_95"] == 1).sum()
            coldspots_95 = (self.hotspot_gdf["hotspot_confidence_95"] == -1).sum()
            print(f"  95% 신뢰수준: 핫스팟 {hotspots_95}개, 콜드스팟 {coldspots_95}개")

        return True

    def load_pipe_joint_data(self) -> bool:
        """파이프 조인트 데이터 로드"""
        print("\n=== 파이프 조인트 데이터 로드 중 ===")

        # 가능한 경로들
        possible_paths = [
            (
                "results/shapefiles/PIPE_LM_JOINT.shp",
                "results/shapefiles/SPLY_LS_JOINT.shp",
            ),
            (
                "shp/GIS_F_NSIU_520_PIPE_LM/GIS_F_NSIU_520_PIPE_LM_JOINT.shp",
                "shp/GIS_F_NSIU_520_SPLY_LS/GIS_F_NSIU_520_SPLY_LS_JOINT.shp",
            ),
        ]

        pipe_lm_gdf = None
        sply_ls_gdf = None

        for pipe_lm_path, sply_ls_path in possible_paths:
            if os.path.exists(pipe_lm_path):
                print(f"  Loading {pipe_lm_path}")
                try:
                    pipe_lm_gdf = gpd.read_file(pipe_lm_path, encoding="cp949")
                    print(f"    PIPE_LM_JOINT: {len(pipe_lm_gdf)} records")
                except:
                    pipe_lm_gdf = gpd.read_file(pipe_lm_path, encoding="utf-8")
                break

        for pipe_lm_path, sply_ls_path in possible_paths:
            if os.path.exists(sply_ls_path):
                print(f"  Loading {sply_ls_path}")
                try:
                    sply_ls_gdf = gpd.read_file(sply_ls_path, encoding="cp949")
                    print(f"    SPLY_LS_JOINT: {len(sply_ls_gdf)} records")
                except:
                    sply_ls_gdf = gpd.read_file(sply_ls_path, encoding="utf-8")
                break

        # 데이터 병합
        gdfs_to_concat = []

        if pipe_lm_gdf is not None and "CNT_JNT" in pipe_lm_gdf.columns:
            gdfs_to_concat.append(pipe_lm_gdf[["CNT_JNT", "geometry"]])

        if sply_ls_gdf is not None and "CNT_JNT" in sply_ls_gdf.columns:
            gdfs_to_concat.append(sply_ls_gdf[["CNT_JNT", "geometry"]])

        if not gdfs_to_concat:
            print("  ⚠️ CNT_JNT 데이터를 찾을 수 없습니다.")
            return False

        self.joint_gdf = pd.concat(gdfs_to_concat, ignore_index=True)
        print(f"\n  총 조인트 데이터: {len(self.joint_gdf)} records")

        # CNT_JNT 통계
        print("\n  CNT_JNT 통계:")
        print(f"    평균: {self.joint_gdf['CNT_JNT'].mean():.2f}")
        print(f"    중앙값: {self.joint_gdf['CNT_JNT'].median():.2f}")
        print(f"    최소값: {self.joint_gdf['CNT_JNT'].min()}")
        print(f"    최대값: {self.joint_gdf['CNT_JNT'].max()}")

        return True

    def load_fatigue_data(self) -> bool:
        """피로 K-factors 데이터 로드"""
        print("\n=== K-factors 데이터 로드 중 ===")

        # 가능한 경로들
        possible_files = [
            "results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv",
            "results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv",
            "data/fatigue_pipe_lm_by_age.csv",
            "data/fatigue_sply_ls_by_age.csv",
        ]

        dfs = []
        for file_path in possible_files:
            if os.path.exists(file_path):
                print(f"  Loading {file_path}")
                df = pd.read_csv(file_path, encoding="utf-8-sig")
                dfs.append(df)
                print(f"    {len(df)} records loaded")

        if not dfs:
            print("  ⚠️ K-factors 데이터를 찾을 수 없습니다.")
            return False

        self.fatigue_df = pd.concat(dfs, ignore_index=True)

        # K-factors 컬럼 확인
        k_factors = [
            "K_age",
            "K_soil",
            "K_traffic",
            "hoop_stress",
            "K_stress",
            "K_total",
            "STD_DIP",
            "D_final",
        ]

        available_factors = [col for col in k_factors if col in self.fatigue_df.columns]
        print(f"\n  사용 가능한 K-factors: {', '.join(available_factors)}")

        # 통계 출력
        for factor in available_factors[:3]:  # 처음 3개만 표시
            print(
                f"    {factor}: mean={self.fatigue_df[factor].mean():.3f}, "
                f"std={self.fatigue_df[factor].std():.3f}"
            )

        return True

    def analyze_cnt_jnt_correlation(self) -> dict:
        """CNT_JNT와 핫스팟 상관관계 분석"""
        print("\n=== CNT_JNT 상관관계 분석 중 ===")

        if self.joint_gdf is None:
            print("  조인트 데이터 없음 - 분석 건너뜀")
            return {}

        # CRS 맞추기
        if self.hotspot_gdf.crs != self.joint_gdf.crs:
            print(f"  CRS 변환: {self.joint_gdf.crs} → {self.hotspot_gdf.crs}")
            self.joint_gdf = self.joint_gdf.to_crs(self.hotspot_gdf.crs)

        # 공간 조인
        print("  공간 조인 수행 중...")
        joined_gdf = gpd.sjoin(
            self.hotspot_gdf, self.joint_gdf, how="left", predicate="intersects"
        )

        # 그리드별 CNT_JNT 집계
        grid_stats = (
            joined_gdf.groupby("cell_id")
            .agg(
                {
                    "CNT_JNT": ["count", "sum", "mean", "max"],
                    "hotspot_confidence_90": "first",
                    "hotspot_confidence_95": "first",
                    "gi_star_z": "first",
                }
            )
            .reset_index()
        )

        grid_stats.columns = [
            "cell_id",
            "pipe_count",
            "total_cnt_jnt",
            "mean_cnt_jnt",
            "max_cnt_jnt",
            "hotspot_90",
            "hotspot_95",
            "gi_star_z",
        ]
        grid_stats = grid_stats.fillna(0)

        # 통계 분석
        results = {}

        # 핫스팟 유형별 비교
        for conf_level, col_name in [(90, "hotspot_90"), (95, "hotspot_95")]:
            hotspot_data = grid_stats[grid_stats[col_name] == 1]["total_cnt_jnt"]
            normal_data = grid_stats[grid_stats[col_name] == 0]["total_cnt_jnt"]

            if len(hotspot_data) > 0 and len(normal_data) > 0:
                # t-test
                t_stat, p_value = stats.ttest_ind(hotspot_data, normal_data)

                results[f"ttest_{conf_level}"] = {
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "hotspot_mean": float(hotspot_data.mean()),
                    "normal_mean": float(normal_data.mean()),
                }

                print(f"\n  {conf_level}% 신뢰수준:")
                print(f"    핫스팟 평균 CNT_JNT: {hotspot_data.mean():.2f}")
                print(f"    일반 평균 CNT_JNT: {normal_data.mean():.2f}")
                print(f"    t-test: t={t_stat:.3f}, p={p_value:.4f}")

        # 상관계수
        if len(grid_stats) > 3:
            pearson_r, pearson_p = stats.pearsonr(
                grid_stats["gi_star_z"], grid_stats["total_cnt_jnt"]
            )
            results["correlation"] = {
                "pearson_r": float(pearson_r),
                "pearson_p": float(pearson_p),
            }
            print(f"\n  Pearson 상관계수: r={pearson_r:.3f}, p={pearson_p:.4f}")

        self.analysis_results["cnt_jnt"] = results
        self.analysis_results["grid_stats"] = grid_stats

        return results

    def analyze_kfactors_correlation(self) -> dict:
        """K-factors와 핫스팟 상관관계 분석"""
        print("\n=== K-factors 상관관계 분석 중 ===")

        if self.fatigue_df is None:
            print("  K-factors 데이터 없음 - 분석 건너뜀")
            return {}

        # 좌표가 있는 경우 GeoDataFrame으로 변환
        if "x" in self.fatigue_df.columns and "y" in self.fatigue_df.columns:
            from shapely.geometry import Point

            geometry = [
                Point(xy)
                for xy in zip(self.fatigue_df.x, self.fatigue_df.y, strict=False)
            ]
            fatigue_gdf = gpd.GeoDataFrame(
                self.fatigue_df, geometry=geometry, crs=self.hotspot_gdf.crs
            )

            # 공간 조인
            print("  공간 조인 수행 중...")
            joined_gdf = gpd.sjoin(
                self.hotspot_gdf, fatigue_gdf, how="left", predicate="intersects"
            )

            # K-factors 분석
            k_factors = [
                "K_age",
                "K_soil",
                "K_traffic",
                "hoop_stress",
                "K_stress",
                "K_total",
                "D_final",
            ]
            available_factors = [col for col in k_factors if col in joined_gdf.columns]

            results = {}

            for factor in available_factors:
                # 그리드별 평균
                factor_stats = (
                    joined_gdf.groupby("cell_id")
                    .agg(
                        {
                            factor: "mean",
                            "hotspot_confidence_90": "first",
                            "gi_star_z": "first",
                        }
                    )
                    .reset_index()
                )

                # 핫스팟 vs 일반 비교
                hotspot_values = factor_stats[
                    factor_stats["hotspot_confidence_90"] == 1
                ][factor]
                normal_values = factor_stats[
                    factor_stats["hotspot_confidence_90"] == 0
                ][factor]

                if len(hotspot_values) > 0 and len(normal_values) > 0:
                    t_stat, p_value = stats.ttest_ind(
                        hotspot_values.dropna(), normal_values.dropna()
                    )

                    results[factor] = {
                        "t_statistic": float(t_stat),
                        "p_value": float(p_value),
                        "hotspot_mean": float(hotspot_values.mean()),
                        "normal_mean": float(normal_values.mean()),
                    }

                    print(f"\n  {factor}:")
                    print(f"    핫스팟 평균: {hotspot_values.mean():.3f}")
                    print(f"    일반 평균: {normal_values.mean():.3f}")
                    print(f"    t-test: t={t_stat:.3f}, p={p_value:.4f}")

            self.analysis_results["kfactors"] = results
            return results
        print("  좌표 정보 없음 - 공간 조인 불가")
        return {}

    def visualize_results(self):
        """결과 시각화"""
        print("\n=== 시각화 생성 중 ===")

        if "grid_stats" not in self.analysis_results:
            print("  분석 결과 없음 - 시각화 건너뜀")
            return

        grid_stats = self.analysis_results["grid_stats"]

        # 시각화
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # 1. 박스플롯: 핫스팟 유형별 CNT_JNT
        ax = axes[0, 0]
        data_to_plot = []
        labels = []

        for hotspot_val, label in [(1, "핫스팟"), (0, "일반"), (-1, "콜드스팟")]:
            mask = grid_stats["hotspot_90"] == hotspot_val
            if mask.any():
                data_to_plot.append(grid_stats[mask]["total_cnt_jnt"])
                labels.append(label)

        if data_to_plot:
            bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)
            colors = ["red", "gray", "blue"]
            for patch, color in zip(
                bp["boxes"], colors[: len(bp["boxes"])], strict=False
            ):
                patch.set_facecolor(color)
                patch.set_alpha(0.5)

        ax.set_title("핫스팟 유형별 CNT_JNT 분포")
        ax.set_ylabel("Total CNT_JNT")
        ax.grid(True, alpha=0.3)

        # 2. 산점도: Gi* z-score vs CNT_JNT
        ax = axes[0, 1]
        scatter = ax.scatter(
            grid_stats["gi_star_z"],
            grid_stats["total_cnt_jnt"],
            c=grid_stats["hotspot_90"],
            cmap="RdBu_r",
            alpha=0.6,
        )
        ax.set_xlabel("Gi* z-score")
        ax.set_ylabel("Total CNT_JNT")
        ax.set_title("Gi* z-score와 CNT_JNT 상관관계")
        ax.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax, label="핫스팟 유형")

        # 회귀선 추가
        valid_mask = (grid_stats["total_cnt_jnt"] > 0) | (grid_stats["gi_star_z"] != 0)
        if valid_mask.any():
            z = np.polyfit(
                grid_stats[valid_mask]["gi_star_z"],
                grid_stats[valid_mask]["total_cnt_jnt"],
                1,
            )
            p = np.poly1d(z)
            x_line = np.linspace(
                grid_stats["gi_star_z"].min(), grid_stats["gi_star_z"].max(), 100
            )
            ax.plot(
                x_line, p(x_line), "r-", alpha=0.5, label=f"y={z[0]:.2f}x+{z[1]:.2f}"
            )
            ax.legend()

        # 3. 히스토그램: CNT_JNT 분포
        ax = axes[1, 0]
        hotspot_mask = grid_stats["hotspot_90"] == 1
        normal_mask = grid_stats["hotspot_90"] == 0

        if hotspot_mask.any():
            ax.hist(
                grid_stats[hotspot_mask]["total_cnt_jnt"],
                bins=20,
                alpha=0.5,
                label="핫스팟",
                color="red",
                density=True,
            )
        if normal_mask.any():
            ax.hist(
                grid_stats[normal_mask]["total_cnt_jnt"],
                bins=20,
                alpha=0.5,
                label="일반",
                color="gray",
                density=True,
            )

        ax.set_xlabel("Total CNT_JNT")
        ax.set_ylabel("밀도")
        ax.set_title("CNT_JNT 분포 비교")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. 바이올린 플롯
        ax = axes[1, 1]
        data_df = []
        for hotspot_val, label in [(1, "핫스팟"), (0, "일반")]:
            mask = grid_stats["hotspot_90"] == hotspot_val
            if mask.any():
                temp_df = pd.DataFrame(
                    {"CNT_JNT": grid_stats[mask]["total_cnt_jnt"], "Type": label}
                )
                data_df.append(temp_df)

        if data_df:
            plot_df = pd.concat(data_df, ignore_index=True)
            sns.violinplot(data=plot_df, x="Type", y="CNT_JNT", ax=ax)
            ax.set_title("CNT_JNT 분포 (바이올린 플롯)")
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # 저장
        output_file = os.path.join(self.output_dir, "infrastructure_correlation.png")
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"  시각화 저장: {output_file}")
        plt.close()

        # K-factors 시각화 (있는 경우)
        if self.analysis_results.get("kfactors"):
            self.visualize_kfactors()

    def visualize_kfactors(self):
        """K-factors 시각화"""
        kfactors_results = self.analysis_results["kfactors"]

        # 결과 데이터프레임 생성
        factors_df = pd.DataFrame(kfactors_results).T
        factors_df = factors_df.reset_index()
        factors_df.columns = [
            "Factor",
            "t_statistic",
            "p_value",
            "hotspot_mean",
            "normal_mean",
        ]

        # 시각화
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        # 1. 평균값 비교 막대그래프
        ax = axes[0]
        x = np.arange(len(factors_df))
        width = 0.35

        ax.bar(
            x - width / 2,
            factors_df["hotspot_mean"],
            width,
            label="핫스팟",
            color="red",
            alpha=0.7,
        )
        ax.bar(
            x + width / 2,
            factors_df["normal_mean"],
            width,
            label="일반",
            color="gray",
            alpha=0.7,
        )

        ax.set_xlabel("K-factors")
        ax.set_ylabel("평균값")
        ax.set_title("핫스팟 vs 일반 지역 K-factors 비교")
        ax.set_xticks(x)
        ax.set_xticklabels(factors_df["Factor"], rotation=45)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. p-value 플롯
        ax = axes[1]
        colors = ["green" if p < 0.05 else "gray" for p in factors_df["p_value"]]
        ax.bar(x, factors_df["p_value"], color=colors, alpha=0.7)
        ax.axhline(y=0.05, color="r", linestyle="--", label="p=0.05")
        ax.set_xlabel("K-factors")
        ax.set_ylabel("p-value")
        ax.set_title("통계적 유의성 (t-test)")
        ax.set_xticks(x)
        ax.set_xticklabels(factors_df["Factor"], rotation=45)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # 저장
        output_file = os.path.join(self.output_dir, "kfactors_analysis.png")
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"  K-factors 시각화 저장: {output_file}")
        plt.close()

    def save_results(self):
        """결과 저장"""
        print("\n=== 결과 저장 중 ===")

        # 1. 분석 결과 JSON 저장
        json_file = os.path.join(self.output_dir, "infrastructure_analysis.json")

        # numpy 타입 변환
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict()
            if isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            if isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        results_clean = convert_numpy(self.analysis_results)

        # grid_stats는 별도로 저장
        if "grid_stats" in results_clean:
            grid_stats = results_clean.pop("grid_stats")
            # CSV로 저장
            csv_file = os.path.join(self.output_dir, "cnt_jnt_analysis.csv")
            pd.DataFrame(grid_stats).to_csv(csv_file, index=False, encoding="utf-8-sig")
            print(f"  CNT_JNT 분석 CSV 저장: {csv_file}")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results_clean, f, ensure_ascii=False, indent=2)
        print(f"  분석 결과 JSON 저장: {json_file}")

        # 2. 보고서 생성
        self.generate_report()

    def generate_report(self):
        """분석 보고서 생성"""
        report_file = os.path.join(self.output_dir, "infrastructure_report.md")

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 핫스팟-인프라 상관관계 분석 보고서\n\n")
            f.write(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 1. 데이터 개요\n")
            if self.hotspot_gdf is not None:
                f.write(f"- 핫스팟 그리드 수: {len(self.hotspot_gdf)}개\n")
                if "hotspot_confidence_90" in self.hotspot_gdf.columns:
                    f.write(
                        f"- 핫스팟 (90% 신뢰): "
                        f"{(self.hotspot_gdf['hotspot_confidence_90'] == 1).sum()}개\n"
                    )

            if self.joint_gdf is not None:
                f.write(f"- 파이프 조인트 수: {len(self.joint_gdf)}개\n")
                f.write(f"- 평균 CNT_JNT: {self.joint_gdf['CNT_JNT'].mean():.2f}\n")

            if self.fatigue_df is not None:
                f.write(f"- K-factors 데이터: {len(self.fatigue_df)}개\n")

            f.write("\n## 2. CNT_JNT 상관관계 분석\n")
            if "cnt_jnt" in self.analysis_results:
                cnt_results = self.analysis_results["cnt_jnt"]

                for conf_level in [90, 95]:
                    key = f"ttest_{conf_level}"
                    if key in cnt_results:
                        result = cnt_results[key]
                        f.write(f"\n### {conf_level}% 신뢰수준\n")
                        f.write(
                            f"- 핫스팟 평균 CNT_JNT: {result['hotspot_mean']:.2f}\n"
                        )
                        f.write(f"- 일반 평균 CNT_JNT: {result['normal_mean']:.2f}\n")
                        f.write(f"- t-statistic: {result['t_statistic']:.3f}\n")
                        f.write(f"- p-value: {result['p_value']:.4f}\n")

                        if result["p_value"] < 0.05:
                            f.write("- **결과: 통계적으로 유의미한 차이** (p < 0.05)\n")
                        else:
                            f.write("- 결과: 통계적으로 유의미한 차이 없음\n")

                if "correlation" in cnt_results:
                    f.write("\n### 상관관계\n")
                    f.write(
                        f"- Pearson r: {cnt_results['correlation']['pearson_r']:.3f} "
                    )
                    f.write(f"(p={cnt_results['correlation']['pearson_p']:.4f})\n")

            f.write("\n## 3. K-factors 상관관계 분석\n")
            if "kfactors" in self.analysis_results:
                kfactors_results = self.analysis_results["kfactors"]

                for factor, result in kfactors_results.items():
                    f.write(f"\n### {factor}\n")
                    f.write(f"- 핫스팟 평균: {result['hotspot_mean']:.3f}\n")
                    f.write(f"- 일반 평균: {result['normal_mean']:.3f}\n")
                    f.write(f"- t-statistic: {result['t_statistic']:.3f}\n")
                    f.write(f"- p-value: {result['p_value']:.4f}\n")

                    if result["p_value"] < 0.05:
                        f.write("- **통계적으로 유의미**\n")

            f.write("\n## 4. 결론 및 권장사항\n")
            f.write("- 핫스팟 지역과 파이프 인프라 특성 간의 상관관계 분석 완료\n")

            # 유의미한 요인 정리
            significant_factors = []
            if "cnt_jnt" in self.analysis_results:
                for key in ["ttest_90", "ttest_95"]:
                    if key in self.analysis_results["cnt_jnt"]:
                        if self.analysis_results["cnt_jnt"][key]["p_value"] < 0.05:
                            significant_factors.append("CNT_JNT")
                            break

            if "kfactors" in self.analysis_results:
                for factor, result in self.analysis_results["kfactors"].items():
                    if result["p_value"] < 0.05:
                        significant_factors.append(factor)

            if significant_factors:
                f.write(f"- 유의미한 요인: {', '.join(significant_factors)}\n")
                f.write("- 해당 요인들을 우선적으로 고려한 유지보수 계획 수립 권장\n")
            else:
                f.write("- 통계적으로 유의미한 요인이 발견되지 않음\n")
                f.write("- 추가 데이터 수집 및 분석 방법 개선 필요\n")

        print(f"  보고서 저장: {report_file}")

    def run_analysis(self):
        """전체 분석 실행"""
        print("\n" + "=" * 60)
        print("핫스팟-인프라 상관관계 분석 시작")
        print("=" * 60)

        # 1. 데이터 로드
        if not self.load_hotspot_results():
            print("\n⚠️ 핫스팟 데이터 로드 실패")
            print("   먼저 main21_spatial_hotspots.py를 실행하세요.")
            return False

        # 2. CNT_JNT 분석
        if self.load_pipe_joint_data():
            self.analyze_cnt_jnt_correlation()

        # 3. K-factors 분석
        if self.load_fatigue_data():
            self.analyze_kfactors_correlation()

        # 4. 시각화
        self.visualize_results()

        # 5. 결과 저장
        self.save_results()

        print("\n✅ 분석 완료!")
        print(f"   결과는 {self.output_dir}에 저장되었습니다.")

        return True


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="핫스팟과 파이프 인프라 상관관계 분석")
    parser.add_argument(
        "--hotspot-dir",
        default="results/spatial_analysis/hotspots",
        help="핫스팟 분석 결과 디렉토리",
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/infrastructure",
        help="출력 디렉토리",
    )

    args = parser.parse_args()

    # 분석 실행
    analyzer = InfrastructureCorrelationAnalyzer(
        hotspot_dir=args.hotspot_dir, output_dir=args.output_dir
    )

    analyzer.run_analysis()


if __name__ == "__main__":
    main()
