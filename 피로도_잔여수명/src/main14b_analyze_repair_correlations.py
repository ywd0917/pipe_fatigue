"""
재작업 위치와 파이프 위험 요인 상관관계 통합 분석

클러스터링 분석:
- 10m 반경으로 재작업 위치를 클러스터링하여 repair_count 생성
- 핵심 분석: repair_count(재작업 횟수)와 K-factors의 상관관계
- repair_count >= 4: 빈번한 재작업 그룹으로 분류

분석 요인:
- K-factors: K_age, K_soil, K_traffic, hoop_stress, K_stress, K_total, K_repair, STD_DIP
- D_final: 피로 손상 지수
- 0520 지역 재작업 위치와 각 요인의 관계 종합 분석
"""

import argparse
import json
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from shapely.geometry import Point

from src.common.config import (
    FATIGUE_PIPE_LM_CSV,
    FATIGUE_SPLY_LS_CSV,
    RAW_DATA_DIR,
    RESULTS_DIR,
)
from src.common.korean_font_utils import setup_korean_font
from src.common.spatial_utils import convert_to_epsg5179
from src.main14_common.constants import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    DEFAULT_DISTANCE,
    FACTOR_NAMES,
    OPTIONAL_K_FACTORS,
    P_VALUE_THRESHOLD,
)
from src.main14_common.data_loader import (
    load_repair_csv_files,
    load_fatigue_csv,
    load_pipe_shapefiles,
)
from src.main14_common.correlation_analysis import analyze_correlation
from src.main14_common.clustering import create_repair_clusters, match_clusters_to_pipes

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 스크립트별 상수 정의
MIN_REPAIRS_FOR_FREQUENT = 4  # 빈번한 재작업 판단 기준
CLUSTER_DISTANCE_METERS = 10.0  # 클러스터링 거리 임계값 (미터)

# 분석 요인 리스트 - load_pipe_factors_data에서 설정됨
ANALYSIS_FACTORS = []  # 초기화, 실행 시 업데이트


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="재작업 위치와 파이프 위험 요인 상관관계 분석"
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=DEFAULT_DISTANCE,
        help=f"파이프 매칭 거리 임계값 (미터, 기본값: {DEFAULT_DISTANCE})",
    )
    return parser.parse_args()


def load_repair_data() -> gpd.GeoDataFrame:
    """3개 복구 작업 CSV 파일 로드 및 통합, EPSG:5179로 변환"""
    print("\n=== 복구 작업 데이터 로드 중 ===")

    # 공통 함수 사용하여 CSV 파일 로드
    required_columns = ["작업타입", "작업종료일", "주소", "위도", "경도"]
    df_repairs = load_repair_csv_files(required_columns)

    # 결측값 제거
    df_repairs = df_repairs.dropna(subset=["위도", "경도"])

    # GeoDataFrame으로 변환
    repair_points = [
        Point(lon, lat)
        for lon, lat in zip(df_repairs["경도"], df_repairs["위도"], strict=False)
    ]
    gdf_repairs = gpd.GeoDataFrame(df_repairs, geometry=repair_points, crs="EPSG:4326")

    # EPSG:5179로 변환
    gdf_repairs = convert_to_epsg5179(gdf_repairs)

    print(f"전체 복구 작업: {len(gdf_repairs)}개")
    print("좌표계: EPSG:5179로 변환 완료")

    return gdf_repairs


def load_pipe_factors_data() -> gpd.GeoDataFrame:
    """PIPE_LM과 SPLY_LS의 K-factors 및 D_final 데이터 로드 및 통합"""
    print("\n=== 파이프 위험 요인 데이터 로드 중 ===")

    # 공통 함수 사용하여 CSV 파일 로드
    df_pipe_lm, df_sply_ls, has_k_repair = load_fatigue_csv(
        FATIGUE_PIPE_LM_CSV, FATIGUE_SPLY_LS_CSV
    )

    # 기본 K-factors는 항상 존재
    k_factors = BASE_K_FACTORS.copy()
    if has_k_repair:
        k_factors.extend(OPTIONAL_K_FACTORS)

    # 필요한 컬럼 선택
    # D_final은 '0520_D_final' 컬럼명으로 저장되어 있음
    cols_needed = ["FTR_IDN", *k_factors, "0520_D_final"]
    df_pipe_lm = df_pipe_lm[cols_needed].copy()
    df_sply_ls = df_sply_ls[cols_needed].copy()

    # D_final 컬럼명 변경
    df_pipe_lm.rename(columns={"0520_D_final": DAMAGE_FACTOR}, inplace=True)
    df_sply_ls.rename(columns={"0520_D_final": DAMAGE_FACTOR}, inplace=True)

    # 파이프 타입 추가
    df_pipe_lm["pipe_type"] = "PIPE_LM"
    df_sply_ls["pipe_type"] = "SPLY_LS"

    print(f"PIPE_LM: {len(df_pipe_lm)}개 레코드")
    print(f"SPLY_LS: {len(df_sply_ls)}개 레코드")

    # 전역 ANALYSIS_FACTORS 업데이트
    global ANALYSIS_FACTORS
    # 기본 순서: BASE_K_FACTORS + D_final + OPTIONAL_K_FACTORS (있는 경우)
    ANALYSIS_FACTORS = [*BASE_K_FACTORS, DAMAGE_FACTOR]
    if has_k_repair:
        ANALYSIS_FACTORS.extend(OPTIONAL_K_FACTORS)

    # 분석 요인 통계 출력
    print("\n=== 분석 요인 범위 ===")
    for factor in ANALYSIS_FACTORS:
        if factor in df_pipe_lm.columns and factor in df_sply_ls.columns:
            pipe_min = df_pipe_lm[factor].min()
            pipe_max = df_pipe_lm[factor].max()
            sply_min = df_sply_ls[factor].min()
            sply_max = df_sply_ls[factor].max()

            # D_final은 다른 형식으로 출력
            if factor == "D_final":
                print(
                    f"{factor}: {min(pipe_min, sply_min):.6f} ~ {max(pipe_max, sply_max):.6f}"
                )
            else:
                print(
                    f"{factor}: {min(pipe_min, sply_min):.4f} ~ {max(pipe_max, sply_max):.4f}"
                )

    # 공통 함수 사용하여 Shapefile 로드
    pipe_lm_shp = RAW_DATA_DIR / "export_shp_20250704(0520)" / "V_WTL_PIPE_LM.shp"
    sply_ls_shp = RAW_DATA_DIR / "export_shp_20250704(0520)" / "V_WTL_SPLY_LS.shp"

    gdf_pipe_lm, gdf_sply_ls = load_pipe_shapefiles(pipe_lm_shp, sply_ls_shp)

    # FTR_IDN을 기준으로 K-factors 데이터와 직접 매칭
    pipe_lm_factors = []
    for _, row in gdf_pipe_lm.iterrows():
        ftr_idn = row["FTR_IDN"]
        # CSV 데이터에서 매칭되는 K-factors 찾기
        factors_match = df_pipe_lm[df_pipe_lm["FTR_IDN"] == ftr_idn]
        if not factors_match.empty:
            factors = factors_match.iloc[0].to_dict()
            factors["geometry"] = row.geometry  # LineString 유지
            factors["segment_id"] = ftr_idn
            pipe_lm_factors.append(factors)

    sply_ls_factors = []
    for _, row in gdf_sply_ls.iterrows():
        ftr_idn = row["FTR_IDN"]
        # CSV 데이터에서 매칭되는 K-factors 찾기
        factors_match = df_sply_ls[df_sply_ls["FTR_IDN"] == ftr_idn]
        if not factors_match.empty:
            factors = factors_match.iloc[0].to_dict()
            factors["geometry"] = row.geometry  # LineString 유지
            factors["segment_id"] = ftr_idn
            sply_ls_factors.append(factors)

    # GeoDataFrame 생성
    if pipe_lm_factors:
        gdf_pipe_lm_factors = gpd.GeoDataFrame(pipe_lm_factors, crs="EPSG:5179")
    else:
        gdf_pipe_lm_factors = gpd.GeoDataFrame(
            columns=["FTR_IDN", *ANALYSIS_FACTORS, "pipe_type", "geometry"],
            crs="EPSG:5179",
        )

    if sply_ls_factors:
        gdf_sply_ls_factors = gpd.GeoDataFrame(sply_ls_factors, crs="EPSG:5179")
    else:
        gdf_sply_ls_factors = gpd.GeoDataFrame(
            columns=["FTR_IDN", *ANALYSIS_FACTORS, "pipe_type", "geometry"],
            crs="EPSG:5179",
        )

    # 통합
    gdf_pipes = pd.concat([gdf_pipe_lm_factors, gdf_sply_ls_factors], ignore_index=True)

    # 유효한 데이터만 필터링 (D_final이 0보다 큰 경우)
    if len(gdf_pipes) > 0:
        gdf_pipes = gdf_pipes[gdf_pipes["D_final"] > 0]

    print(f"\n유효한 파이프 세그먼트: {len(gdf_pipes)}개")

    return gdf_pipes


def create_visualizations(
    df_matched: pd.DataFrame, results: dict[str, Any], output_dir: Path
) -> None:
    """결과 시각화"""
    print("\n=== 시각화 생성 중 ===")

    setup_korean_font()

    # 1. 산점도 - 모든 분석 요인 (3x3 그리드, 9개 요인)
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    axes = axes.flatten()

    for idx, factor in enumerate(ANALYSIS_FACTORS):
        if idx >= len(axes):  # 9개 축, 9개 요인이므로 모두 들어감
            break
        ax = axes[idx]

        # 최대값 사용 (최악의 경우 고려)
        col_name = f"max_{factor}"
        if col_name in df_matched.columns:
            ax.scatter(
                df_matched[col_name],
                df_matched["repair_count"],
                c=df_matched["repair_count"],
                cmap="coolwarm",
                alpha=0.6,
                s=50,
            )

            # 회귀선 (데이터의 분산이 있을 때만)
            if df_matched[col_name].std() > 0:
                try:
                    z = np.polyfit(df_matched[col_name], df_matched["repair_count"], 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(
                        df_matched[col_name].min(), df_matched[col_name].max(), 100
                    )
                    ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2)
                except np.linalg.LinAlgError:
                    # 회귀선을 그릴 수 없는 경우 건너뛰기
                    pass

            # 상관계수 표시
            corr_key = f"{col_name}_corr"
            p_key = f"{col_name}_p"
            if corr_key in results:
                corr = results[corr_key]
                p_val = results[p_key]
                sig = "*" if p_val < P_VALUE_THRESHOLD else ""
                ax.set_title(
                    f"{FACTOR_NAMES[factor]}\nr={corr:.4f}, p={p_val:.4f}{sig}"
                )
            else:
                ax.set_title(FACTOR_NAMES[factor])

            ax.set_xlabel(factor)
            ax.set_ylabel("재작업 횟수")
            ax.grid(True, alpha=0.3)

            # 4회 이상 재작업 위치 강조
            frequent = df_matched[
                df_matched["repair_count"] >= MIN_REPAIRS_FOR_FREQUENT
            ]
            if len(frequent) > 0:
                ax.scatter(
                    frequent[col_name],
                    frequent["repair_count"],
                    color="red",
                    s=100,
                    alpha=0.8,
                    edgecolors="black",
                    linewidths=2,
                    label="4회 이상",
                    zorder=5,
                )
                ax.legend()

    # 9개 요인이므로 모든 축을 사용함

    # 사용하지 않는 subplot 숨기기
    for idx in range(len(ANALYSIS_FACTORS), 9):
        axes[idx].set_visible(False)

    plt.suptitle(
        "파이프 위험 요인과 재작업 횟수 상관관계",
        fontsize=16,
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(
        output_dir / "repair_k_factors_scatter.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    # 2. 박스플롯 - 그룹 비교 (3x3 그리드)
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    axes = axes.flatten()

    for idx, factor in enumerate(ANALYSIS_FACTORS):
        if idx >= len(axes):
            break
        ax = axes[idx]
        col_name = f"max_{factor}"

        if col_name in df_matched.columns:
            data_to_plot = []
            labels = []

            df_frequent = df_matched[
                df_matched["repair_count"] >= MIN_REPAIRS_FOR_FREQUENT
            ]
            df_normal = df_matched[
                df_matched["repair_count"] < MIN_REPAIRS_FOR_FREQUENT
            ]

            if len(df_normal) > 0:
                data_to_plot.append(df_normal[col_name])
                labels.append(f"일반\n(n={len(df_normal)})")

            if len(df_frequent) > 0:
                data_to_plot.append(df_frequent[col_name])
                labels.append(f"빈번\n(n={len(df_frequent)})")

            if data_to_plot:
                bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True)

                # 색상 설정
                colors = ["lightblue", "lightcoral"]
                for patch, color in zip(
                    bp["boxes"], colors[: len(bp["boxes"])], strict=False
                ):
                    patch.set_facecolor(color)

                ax.set_ylabel(factor)
                ax.set_title(FACTOR_NAMES[factor])
                ax.grid(True, alpha=0.3)

                # 통계 검정 결과 표시
                t_p_key = f"{col_name}_t_p"
                if t_p_key in results:
                    p_value = results[t_p_key]
                    sig = "*" if p_value < P_VALUE_THRESHOLD else ""
                    ax.text(
                        0.5,
                        0.95,
                        f"p={p_value:.4f}{sig}",
                        transform=ax.transAxes,
                        ha="center",
                        va="top",
                        bbox=dict(
                            boxstyle="round",
                            facecolor=(
                                "yellow" if p_value < P_VALUE_THRESHOLD else "white"
                            ),
                            alpha=0.5,
                        ),
                    )

    # 사용하지 않는 subplot 숨기기
    for idx in range(len(ANALYSIS_FACTORS), 9):
        axes[idx].set_visible(False)

    plt.suptitle("재작업 빈도별 위험 요인 분포 비교", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.savefig(
        output_dir / "repair_k_factors_boxplot.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    # 3. 상관계수 히트맵
    # 상관계수 매트릭스 생성
    corr_data = []
    for factor in ANALYSIS_FACTORS:
        row = []
        for strategy in ["max", "nearest", "avg"]:
            col_name = f"{strategy}_{factor}"
            corr_key = f"{col_name}_corr"
            if corr_key in results:
                row.append(results[corr_key])
            else:
                row.append(0)
        corr_data.append(row)

    corr_matrix = pd.DataFrame(
        corr_data,
        index=[FACTOR_NAMES[f] for f in ANALYSIS_FACTORS],
        columns=["최대값", "가장 가까운", "평균값"],
    )

    # 히트맵 그리기
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=".4f",
        cmap="coolwarm",
        center=0,
        vmin=-0.3,
        vmax=0.3,
        square=True,
        linewidths=1,
        cbar_kws={"shrink": 0.8, "label": "상관계수"},
        ax=ax,
    )

    plt.title(
        "위험 요인과 재작업 횟수 상관계수 히트맵",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    plt.xlabel("매칭 전략", fontsize=12)
    plt.ylabel("위험 요인", fontsize=12)
    plt.tight_layout()
    plt.savefig(
        output_dir / "repair_k_factors_heatmap.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    print("시각화 파일 생성 완료")


def save_results(
    df_matched: pd.DataFrame,
    results: dict[str, Any],
    df_pipes: pd.DataFrame,
    distance_threshold: float,
    output_dir: Path,
    gdf_clusters: gpd.GeoDataFrame = None,
) -> None:
    """분석 결과 저장"""
    print("\n=== 결과 저장 중 ===")

    # 매칭 데이터 저장
    df_matched.to_csv(output_dir / "0520_repair_k_factors_matched.csv", index=False)

    # 분석 요약 저장
    with (output_dir / "0520_repair_correlations_analysis.txt").open(
        "w", encoding="utf-8"
    ) as f:
        f.write("=" * 70 + "\n")
        f.write("0520 지역 - 재작업 위치와 파이프 위험 요인 상관관계 통합 분석\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"분석 일시: {datetime.now()}\n")
        f.write(f"분석 대상: {len(df_matched)}개 클러스터\n")
        f.write(f"빈번한 재작업 기준: {MIN_REPAIRS_FOR_FREQUENT}회 이상\n")
        f.write(f"파이프 검색 반경: {distance_threshold}m\n")
        # K-factors 개수 계산
        base_count = len(BASE_K_FACTORS)
        optional_count = len([f for f in OPTIONAL_K_FACTORS if f in ANALYSIS_FACTORS])

        f.write(f"분석 요인: 총 {len(ANALYSIS_FACTORS)}개\n")
        f.write(
            f"  - 기본 K-factors: {base_count}개 (STD_DIP, K_age, K_soil, K_traffic, hoop_stress, K_stress, K_total)\n"
        )
        f.write("  - 피로 손상 지수: 1개 (D_final)\n")
        if optional_count > 0:
            f.write(f"  - 선택적 K-factors: {optional_count}개 (K_repair)\n")
        f.write("\n")

        f.write("-" * 70 + "\n")
        f.write("1. 상관계수 분석 (범위 내 최대값 기준)\n")
        f.write("-" * 70 + "\n\n")

        for factor in ANALYSIS_FACTORS:
            col_name = f"max_{factor}"
            if f"{col_name}_corr" in results:
                f.write(f"{FACTOR_NAMES[factor]} ({factor}):\n")
                f.write(f"  상관계수: {results[f'{col_name}_corr']:.4f}\n")
                f.write(f"  p-value: {results[f'{col_name}_p']:.4f}\n")
                sig = (
                    "유의미"
                    if results[f"{col_name}_p"] < P_VALUE_THRESHOLD
                    else "유의미하지 않음"
                )
                f.write(f"  통계적 유의성: {sig}\n\n")

        f.write("-" * 70 + "\n")
        f.write("2. 전략별 상관계수 비교\n")
        f.write("-" * 70 + "\n\n")

        # 테이블 형식으로 출력
        f.write(
            f"{'K-factor':20s} {'최대값':>12s} {'가장 가까운':>12s} {'평균값':>12s}\n"
        )
        f.write("-" * 60 + "\n")

        for factor in ANALYSIS_FACTORS:
            row = f"{FACTOR_NAMES[factor]:20s}"
            for strategy in ["max", "nearest", "avg"]:
                col_name = f"{strategy}_{factor}"
                corr_key = f"{col_name}_corr"
                if corr_key in results:
                    row += f" {results[corr_key]:11.4f}"
                else:
                    row += f" {'N/A':>11s}"
            f.write(row + "\n")

        f.write("\n")
        f.write("-" * 70 + "\n")
        f.write("3. 그룹별 비교 (뺈번한 재작업 vs 일반)\n")
        f.write("-" * 70 + "\n\n")

        f.write(
            f"빈번한 재작업 그룹 (≥{MIN_REPAIRS_FOR_FREQUENT}회): {results.get('frequent_count', 0)}개\n"
        )
        f.write(
            f"일반 재작업 그룹 (<{MIN_REPAIRS_FOR_FREQUENT}회): {results.get('normal_count', 0)}개\n\n"
        )

        for factor in ANALYSIS_FACTORS:
            col_name = f"max_{factor}"
            if f"{col_name}_frequent_mean" in results:
                f.write(f"{FACTOR_NAMES[factor]} ({factor}):\n")
                freq_mean = results[f"{col_name}_frequent_mean"]
                norm_mean = results[f"{col_name}_normal_mean"]
                diff = freq_mean - norm_mean
                diff_pct = (diff / norm_mean * 100) if norm_mean != 0 else 0

                f.write(f"  빈번한 재작업 평균: {freq_mean:.4f}\n")
                f.write(f"  일반 재작업 평균: {norm_mean:.4f}\n")
                f.write(f"  차이: {diff:+.4f} ({diff_pct:+.1f}%)\n")
                f.write(
                    f"  t-test: t={results[f'{col_name}_t_stat']:.4f}, p={results[f'{col_name}_t_p']:.4f}\n"
                )
                sig = (
                    "유의미"
                    if results[f"{col_name}_t_p"] < P_VALUE_THRESHOLD
                    else "유의미하지 않음"
                )
                f.write(f"  통계적 유의성: {sig}\n\n")

        f.write("-" * 70 + "\n")
        f.write("4. 위험 요인 분포 통계\n")
        f.write("-" * 70 + "\n\n")

        f.write(f"전체 파이프 수: {len(df_pipes)}개\n")
        f.write(f"  PIPE_LM: {len(df_pipes[df_pipes['pipe_type'] == 'PIPE_LM'])}개\n")
        f.write(f"  SPLY_LS: {len(df_pipes[df_pipes['pipe_type'] == 'SPLY_LS'])}개\n\n")

        for factor in ANALYSIS_FACTORS:
            f.write(f"{FACTOR_NAMES[factor]} ({factor}) 통계:\n")
            f.write(f"  최소값: {df_pipes[factor].min():.4f}\n")
            f.write(f"  25%: {df_pipes[factor].quantile(0.25):.4f}\n")
            f.write(f"  중앙값: {df_pipes[factor].median():.4f}\n")
            f.write(f"  75%: {df_pipes[factor].quantile(0.75):.4f}\n")
            f.write(f"  최대값: {df_pipes[factor].max():.4f}\n")
            f.write(f"  평균: {df_pipes[factor].mean():.4f}\n")
            f.write(f"  표준편차: {df_pipes[factor].std():.4f}\n\n")

        f.write("-" * 70 + "\n")
        f.write("5. 주요 발견사항\n")
        f.write("-" * 70 + "\n\n")

        # 가장 강한 상관관계
        if "best_factor" in results:
            f.write("가장 강한 상관관계:\n")
            f.write(
                f"  요인: {FACTOR_NAMES.get(results['best_factor'], results['best_factor'])}\n"
            )
            f.write(f"  전략: {results['best_strategy']}\n")
            f.write(f"  상관계수: {results['best_corr']:.4f}\n\n")

        # 유의미한 차이가 있는 요인들
        significant_factors = []
        for factor in ANALYSIS_FACTORS:
            col_name = f"max_{factor}"
            t_p_key = f"{col_name}_t_p"
            if t_p_key in results and results[t_p_key] < P_VALUE_THRESHOLD:
                significant_factors.append(FACTOR_NAMES[factor])

        if significant_factors:
            f.write("빈번한 재작업 그룹에서 유의미한 차이를 보이는 요인:\n")
            for sf in significant_factors:
                f.write(f"  - {sf}\n")
        else:
            f.write(
                "빈번한 재작업 그룹과 일반 그룹 간 유의미한 차이를 보이는 요인 없음\n"
            )

        f.write("\n" + "=" * 70 + "\n")
        f.write("분석 완료\n")
        f.write("=" * 70 + "\n")

    print("결과 파일 저장 완료")

    # metadata.json 저장 (main14b2에서 사용)
    total_clusters = len(gdf_clusters) if gdf_clusters is not None else len(df_matched)
    matched_clusters = len(df_matched)
    matching_rate = (
        (matched_clusters / total_clusters * 100) if total_clusters > 0 else 0
    )

    metadata = {
        "total_clusters": total_clusters,
        "matched_clusters": matched_clusters,
        "matching_rate": matching_rate,
        "avg_pipes_per_cluster": (
            df_matched["pipe_count"].mean() if "pipe_count" in df_matched.columns else 0
        ),
        "distance_threshold": distance_threshold,
        "min_repairs_for_frequent": MIN_REPAIRS_FOR_FREQUENT,
        "analysis_factors": ANALYSIS_FACTORS,
        "timestamp": datetime.now().isoformat(),
    }

    with (output_dir / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("메타데이터 저장 완료 (metadata.json)")


def main() -> None:
    """메인 실행 함수"""
    # 명령줄 인자 파싱
    args = parse_arguments()
    distance_threshold = args.distance

    # 출력 디렉토리 설정
    output_dir = RESULTS_DIR / "main14b"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("재작업 위치와 파이프 위험 요인 상관관계 통합 분석")
    print("=" * 70)
    print(f"파이프 매칭 거리: {distance_threshold}m")
    print(f"결과 저장 디렉토리: {output_dir}")

    # 데이터 로드
    gdf_repairs = load_repair_data()  # 이제 GeoDataFrame 반환
    gdf_pipes = load_pipe_factors_data()

    # 클러스터링
    gdf_clusters = create_repair_clusters(
        gdf_repairs,
        cluster_distance=CLUSTER_DISTANCE_METERS,
        min_repairs_for_frequent=MIN_REPAIRS_FOR_FREQUENT,
    )  # 이제 GeoDataFrame 반환

    # 매칭
    df_matched = match_clusters_to_pipes(
        gdf_clusters, gdf_pipes, distance_threshold, ANALYSIS_FACTORS
    )

    if len(df_matched) == 0:
        print("\n경고: 매칭된 데이터가 없습니다.")
        print("거리 임계값을 조정하거나 데이터를 확인하세요.")
        return

    # 상관관계 분석
    results = analyze_correlation(
        df_matched, ANALYSIS_FACTORS, MIN_REPAIRS_FOR_FREQUENT
    )

    # 시각화
    create_visualizations(df_matched, results, output_dir)

    # 결과 저장
    save_results(
        df_matched, results, gdf_pipes, distance_threshold, output_dir, gdf_clusters
    )

    print("\n분석이 완료되었습니다.")
    print(f"결과 파일 위치: {output_dir}")


if __name__ == "__main__":
    main()
