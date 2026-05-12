#!/usr/bin/env python3
"""
main14b2_distance_sensitivity.py

거리 민감도 분석 스크립트
main14b를 다양한 거리 임계값으로 실행하여 최적 거리를 찾는 분석

Author: assistant
Date: 2025-08-19
Refactored: 2025-01-21 - 공통 모듈 사용으로 리팩토링
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 공통 모듈 import
from common.korean_font_utils import setup_korean_font
from main14_common.constants import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    FACTOR_NAMES,
    OPTIONAL_K_FACTORS,
)

# ResultParser는 더 이상 사용하지 않음 (JSON 파일로 대체)

# 결과 디렉토리 설정
RESULTS_BASE = Path("results/main14b2_distance_sensitivity")
RESULTS_BASE.mkdir(parents=True, exist_ok=True)

# setup_korean_font는 이제 main14_common.utils에서 import하여 사용


def run_main14b_with_distance(distance: int, output_dir: Path) -> dict[str, Any]:
    """
    지정된 거리로 main14b를 실행하고 결과를 수집

    Parameters:
    -----------
    distance : int
        거리 임계값 (미터)
    output_dir : Path
        결과 저장 디렉토리

    Returns:
    --------
    Dict[str, Any]
        실행 결과 정보
    """
    print(f"\n{'='*60}")
    print(f"main14b 실행 중... (거리: {distance}m)")
    print(f"{'='*60}")

    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 실행 시작 시간
    start_time = datetime.now()

    try:
        # main14b 실행
        result = subprocess.run(
            [
                sys.executable,
                "src/main14b_analyze_repair_correlations.py",
                "--distance",
                str(distance),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # 실행 시간 계산
        execution_time = (datetime.now() - start_time).total_seconds()

        # 결과 파일 복사
        source_dir = Path("results") / "main14b"

        # CSV 파일 복사
        csv_file = source_dir / "0520_repair_k_factors_matched.csv"
        if csv_file.exists():
            shutil.copy(csv_file, output_dir / csv_file.name)
            print(f"✓ CSV 파일 복사: {csv_file.name}")
        else:
            print(f"❌ 오류: CSV 파일이 없습니다: {csv_file}")
            print(f"  main14b가 정상적으로 실행되었는지 확인하세요")
            return {
                "distance": distance,
                "execution_time": -1,
                "error": "CSV file not found",
                "timestamp": datetime.now().isoformat(),
            }

        # metadata.json 파일 읽기 (콘솔 파싱 대신)
        metadata_file = source_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            matching_stats = {
                "total_clusters": metadata.get("total_clusters", 0),
                "matched_clusters": metadata.get("matched_clusters", 0),
                "matching_rate": metadata.get("matching_rate", 0),
                "avg_pipes_per_cluster": metadata.get("avg_pipes_per_cluster", 0),
            }
            print(f"✓ 메타데이터 로드: metadata.json")
        else:
            print(f"❌ 오류: metadata.json 파일이 없습니다")
            print(f"  main14b가 최신 버전인지 확인하세요")
            return {
                "distance": distance,
                "execution_time": -1,
                "error": "metadata.json not found",
                "timestamp": datetime.now().isoformat(),
            }

        # 결과 파싱 - CSV 파일에서 직접 처리되므로 빈 딕셔너리로 초기화
        analysis_results = {
            "correlations": {},
            "p_values": {},
            "significant_factors": [],
            "best_strategies": {},
        }

        # 요약 정보 생성
        summary = {
            "distance": distance,
            "execution_time": execution_time,
            "matching_stats": matching_stats,
            "correlations": analysis_results.get("correlations", {}),
            "p_values": analysis_results.get("p_values", {}),
            "significant_factors": analysis_results.get("significant_factors", []),
            "best_strategies": analysis_results.get(
                "best_strategies", {}
            ),  # 전략 정보 추가
            "timestamp": datetime.now().isoformat(),
        }

        # 요약 정보 저장
        with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"✓ 실행 완료 (실행 시간: {execution_time:.2f}초)")
        print(f"  - 매칭률: {matching_stats.get('matching_rate', 0):.1f}%")
        print(
            f"  - 유의미한 요인: {len(analysis_results.get('significant_factors', []))}개"
        )

        return summary

    except subprocess.CalledProcessError as e:
        print(f"✗ 실행 실패: {e}")
        print(f"  - stderr: {e.stderr}")
        return {
            "distance": distance,
            "execution_time": -1,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# parse_matching_stats 함수는 더 이상 사용하지 않음 (JSON 파일로 대체)


def analyze_csv_strategies(
    csv_path: Path, analysis_factors: list[str]
) -> dict[str, Any]:
    """
    CSV 파일에서 전략별 상관계수 직접 계산

    Parameters:
    -----------
    csv_path : Path
        CSV 파일 경로
    analysis_factors : list[str]
        분석 요인 리스트

    Returns:
    --------
    dict : 전략별 상관계수 및 최적 전략
    """
    if not csv_path.exists():
        return {}

    df = pd.read_csv(csv_path)

    results = {
        "correlations": {},
        "p_values": {},
        "best_strategies": {},
        "significant_factors": [],
    }

    strategies = ["max", "nearest", "avg"]

    for factor in analysis_factors:
        best_r = 0
        best_strategy = ""
        best_p = 1.0

        for strategy in strategies:
            col_name = f"{strategy}_{factor}"
            if col_name in df.columns and "repair_count" in df.columns:
                try:
                    from scipy import stats

                    corr, p_value = stats.pearsonr(df[col_name], df["repair_count"])

                    results["correlations"][f"{strategy}_{factor}"] = corr
                    results["p_values"][f"{strategy}_{factor}"] = p_value

                    # 최적 전략 추적
                    if abs(corr) > abs(best_r):
                        best_r = corr
                        best_strategy = strategy
                        best_p = p_value
                except:
                    pass

        if best_strategy:
            results["best_strategies"][factor] = {
                "strategy": best_strategy,
                "r": best_r,
                "p": best_p,
            }

            # p < 0.05 기준으로 유의미한 요인 추가
            if best_p < 0.05:
                results["significant_factors"].append(
                    {
                        "factor": factor,
                        "strategy": best_strategy,
                        "r": best_r,
                        "p": best_p,
                    }
                )

    return results


def analyze_distance_sensitivity(distances: list[int]) -> pd.DataFrame:
    """
    거리별 민감도 분석 실행

    Parameters:
    -----------
    distances : List[int]
        분석할 거리 리스트

    Returns:
    --------
    pd.DataFrame
        통합 분석 결과
    """
    results = []

    for distance in distances:
        output_dir = RESULTS_BASE / f"distance_{distance}m"

        # main14b 실행
        summary = run_main14b_with_distance(distance, output_dir)

        # CSV 파일에서 전략별 분석 추가
        csv_file = output_dir / "0520_repair_k_factors_matched.csv"
        if csv_file.exists() and summary.get("execution_time", -1) > 0:
            # K-factors 리스트 - K_repair을 K_total 전에 배치
            k_factors = [
                "STD_DIP", "K_age", "K_soil", "K_traffic", "hoop_stress", "K_stress",
                "K_repair", "K_total", "D_final"
            ]

            # CSV에서 전략별 상관계수 계산
            csv_analysis = analyze_csv_strategies(csv_file, k_factors)

            # 결과 병합
            if csv_analysis.get("best_strategies"):
                summary["best_strategies"] = csv_analysis["best_strategies"]
                summary["correlations"].update(csv_analysis.get("correlations", {}))
                summary["p_values"].update(csv_analysis.get("p_values", {}))
                summary["significant_factors"] = csv_analysis.get(
                    "significant_factors", []
                )

        # 결과 추가
        if summary.get("execution_time", -1) > 0:
            results.append(summary)

    # DataFrame 생성
    df_results = pd.DataFrame(results)

    # 통합 결과 저장
    integrated_dir = RESULTS_BASE / "integrated_analysis"
    integrated_dir.mkdir(parents=True, exist_ok=True)

    # 상관계수 테이블 생성
    create_correlation_table(df_results, integrated_dir)

    # 매칭 통계 테이블 생성
    create_matching_stats_table(df_results, integrated_dir)

    # 시각화 생성
    create_visualizations(df_results, integrated_dir)

    # 보고서 생성
    create_sensitivity_report(df_results, integrated_dir)

    return df_results


def create_correlation_table(df_results: pd.DataFrame, output_dir: Path):
    """
    거리별 상관계수 테이블 생성

    Parameters:
    -----------
    df_results : pd.DataFrame
        분석 결과
    output_dir : Path
        출력 디렉토리
    """
    # K-factors 리스트 - K_repair을 K_total 전에 배치
    k_factors = [
        "STD_DIP", "K_age", "K_soil", "K_traffic", "hoop_stress", "K_stress",
        "K_repair", "K_total", "D_final"
    ]

    # 상관계수 테이블 생성
    correlation_data = []

    for _, row in df_results.iterrows():
        distance = row["distance"]
        correlations = row.get("correlations", {})

        row_data = {"distance": distance}
        for factor in k_factors:
            row_data[factor] = correlations.get(factor, np.nan)

        correlation_data.append(row_data)

    df_corr = pd.DataFrame(correlation_data)
    df_corr.set_index("distance", inplace=True)

    # CSV 저장
    df_corr.to_csv(output_dir / "correlation_by_distance.csv")

    print("\n상관계수 테이블:")
    print(df_corr.round(4))


def create_matching_stats_table(df_results: pd.DataFrame, output_dir: Path):
    """
    거리별 매칭 통계 테이블 생성

    Parameters:
    -----------
    df_results : pd.DataFrame
        분석 결과
    output_dir : Path
        출력 디렉토리
    """
    matching_data = []

    for _, row in df_results.iterrows():
        distance = row["distance"]
        stats = row.get("matching_stats", {})

        matching_data.append(
            {
                "distance": distance,
                "execution_time": row.get("execution_time", 0),
                "total_clusters": stats.get("total_clusters", 0),
                "matched_clusters": stats.get("matched_clusters", 0),
                "matching_rate": stats.get("matching_rate", 0),
                "avg_pipes_per_cluster": stats.get("avg_pipes_per_cluster", 0),
            }
        )

    df_matching = pd.DataFrame(matching_data)

    # CSV 저장
    df_matching.to_csv(output_dir / "matching_statistics.csv", index=False)

    print("\n매칭 통계 테이블:")
    print(df_matching)


def create_visualizations(df_results: pd.DataFrame, output_dir: Path):
    """
    시각화 생성

    Parameters:
    -----------
    df_results : pd.DataFrame
        분석 결과
    output_dir : Path
        출력 디렉토리
    """
    # 한글 폰트 설정
    setup_korean_font()

    # Visualization removed (unused)

    # 1. 매칭률 라인 차트
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # 매칭률
    distances = df_results["distance"].values
    matching_rates = [
        row.get("matching_stats", {}).get("matching_rate", 0)
        for _, row in df_results.iterrows()
    ]

    axes[0, 0].plot(distances, matching_rates, "o-", linewidth=2, markersize=8)
    axes[0, 0].set_xlabel("거리 (m)")
    axes[0, 0].set_ylabel("매칭률 (%)")
    axes[0, 0].set_title("거리별 매칭률")
    axes[0, 0].grid(True, alpha=0.3)

    # 2. K-factors 상관계수 변화
    k_factors = [
        "STD_DIP", "K_age", "K_soil", "K_traffic", "hoop_stress", "K_stress",
        "K_repair", "K_total", "D_final"
    ]

    for factor in k_factors:
        correlations = []
        for _, row in df_results.iterrows():
            corr_dict = row.get("correlations", {})
            correlations.append(corr_dict.get(factor, 0))

        axes[0, 1].plot(distances, correlations, "o-", label=factor, alpha=0.7)

    axes[0, 1].set_xlabel("거리 (m)")
    axes[0, 1].set_ylabel("상관계수 (r)")
    axes[0, 1].set_title("K-factors 상관계수 변화")
    axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].axhline(y=0, color="k", linestyle="-", alpha=0.3)

    # 3. 히트맵: 거리 × K-factor 상관계수
    corr_matrix = []
    for _, row in df_results.iterrows():
        correlations = row.get("correlations", {})
        corr_row = [correlations.get(factor, 0) for factor in k_factors]
        corr_matrix.append(corr_row)

    corr_matrix = np.array(corr_matrix)

    im = axes[1, 0].imshow(
        corr_matrix.T, aspect="auto", cmap="RdBu_r", vmin=-0.2, vmax=0.2
    )
    axes[1, 0].set_xticks(range(len(distances)))
    axes[1, 0].set_xticklabels([f"{d}m" for d in distances])
    axes[1, 0].set_yticks(range(len(k_factors)))
    axes[1, 0].set_yticklabels(k_factors)
    axes[1, 0].set_xlabel("거리")
    axes[1, 0].set_title("거리 × K-factor 상관계수 히트맵")

    # 값 표시
    for i in range(len(distances)):
        for j in range(len(k_factors)):
            axes[1, 0].text(
                i,
                j,
                f"{corr_matrix[i, j]:.3f}",
                ha="center",
                va="center",
                color="black",
                fontsize=8,
            )

    plt.colorbar(im, ax=axes[1, 0])

    # 4. 실행 시간
    exec_times = [row.get("execution_time", 0) for _, row in df_results.iterrows()]

    axes[1, 1].bar(distances, exec_times, width=5, alpha=0.7, color="skyblue")
    axes[1, 1].set_xlabel("거리 (m)")
    axes[1, 1].set_ylabel("실행 시간 (초)")
    axes[1, 1].set_title("거리별 실행 시간")
    axes[1, 1].grid(True, alpha=0.3, axis="y")

    # 값 표시
    for i, (d, t) in enumerate(zip(distances, exec_times, strict=False)):
        axes[1, 1].text(d, t + 0.01, f"{t:.2f}s", ha="center", va="bottom")

    plt.tight_layout()
    plt.savefig(
        output_dir / "distance_sensitivity_analysis.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    print(f"✓ 시각화 저장: {output_dir / 'distance_sensitivity_analysis.png'}")

    # 5. 개별 K-factor 차트
    fig, axes = plt.subplots(3, 3, figsize=(20, 15))
    axes = axes.flatten()

    for idx, factor in enumerate(k_factors):
        correlations = []
        p_values = []

        for _, row in df_results.iterrows():
            corr_dict = row.get("correlations", {})
            p_dict = row.get("p_values", {})
            correlations.append(corr_dict.get(factor, 0))
            p_values.append(p_dict.get(factor, 1))

        # 상관계수 플롯
        ax = axes[idx]
        ax.plot(distances, correlations, "o-", linewidth=2, markersize=8, color="blue")
        ax.set_xlabel("거리 (m)")
        ax.set_ylabel("상관계수 (r)", color="blue")
        ax.set_title(f"{factor}")
        ax.tick_params(axis="y", labelcolor="blue")
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color="k", linestyle="-", alpha=0.3)

        # p-value를 오른쪽 y축에
        ax2 = ax.twinx()
        ax2.plot(
            distances,
            p_values,
            "s--",
            linewidth=1,
            markersize=6,
            color="red",
            alpha=0.6,
        )
        ax2.set_ylabel("p-value", color="red")
        ax2.tick_params(axis="y", labelcolor="red")
        ax2.axhline(y=0.05, color="red", linestyle=":", alpha=0.5, label="p=0.05")
        ax2.axhline(y=0.1, color="orange", linestyle=":", alpha=0.5, label="p=0.1")

        # 최적 거리 표시 (가장 높은 절대 상관계수)
        best_idx = np.argmax(np.abs(correlations))
        ax.scatter(
            distances[best_idx],
            correlations[best_idx],
            s=200,
            color="green",
            marker="*",
            zorder=5,
        )
        ax.text(
            distances[best_idx],
            correlations[best_idx],
            f"\n최적: {distances[best_idx]}m\nr={correlations[best_idx]:.3f}",
            ha="center",
            va="top",
            fontsize=8,
        )

    # 사용하지 않는 subplot 숨기기
    for idx in range(len(k_factors), 9):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.savefig(
        output_dir / "individual_factor_analysis.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    print(f"✓ 개별 요인 분석 저장: {output_dir / 'individual_factor_analysis.png'}")


def create_sensitivity_report(df_results: pd.DataFrame, output_dir: Path):
    """
    민감도 분석 보고서 생성

    Parameters:
    -----------
    df_results : pd.DataFrame
        분석 결과
    output_dir : Path
        출력 디렉토리
    """
    report_lines = []

    report_lines.append("# 거리 민감도 분석 보고서")
    report_lines.append(f"\n생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("\n" + "=" * 60)

    # 1. 요약
    report_lines.append("\n## 1. 요약")

    # 최적 거리 찾기
    k_factors = [
        "STD_DIP", "K_age", "K_soil", "K_traffic", "hoop_stress", "K_stress",
        "K_repair", "K_total", "D_final"
    ]

    optimal_distances = {}
    for factor in k_factors:
        max_corr = 0
        optimal_dist = 0
        optimal_strategy = "max"  # 기본값
        optimal_p = 1.0

        for _, row in df_results.iterrows():
            distance = row["distance"]

            # 전략별 상관계수 확인
            best_strat = row.get("best_strategies", {}).get(factor, {})
            if best_strat:
                corr = abs(best_strat.get("r", 0))
                if corr > max_corr:
                    max_corr = corr
                    optimal_dist = distance
                    optimal_strategy = best_strat.get("strategy", "max")
                    optimal_p = best_strat.get("p", 1.0)
            else:
                # 하위 호환성
                corr = abs(row.get("correlations", {}).get(factor, 0))
                p_val = row.get("p_values", {}).get(factor, 1.0)
                if corr > max_corr:
                    max_corr = corr
                    optimal_dist = distance
                    optimal_p = p_val

        optimal_distances[factor] = (
            optimal_dist,
            max_corr,
            optimal_strategy,
            optimal_p,
        )

    # 전체 최적 거리 (평균)
    avg_optimal = np.mean([d[0] for d in optimal_distances.values()])
    report_lines.append(f"\n- **전체 최적 거리**: {avg_optimal:.0f}m (평균)")

    # 주요 발견사항
    report_lines.append("\n### 주요 발견사항:")

    # 가장 높은 상관계수를 보이는 요인
    best_factor = max(optimal_distances.items(), key=lambda x: x[1][1])
    strategy_str = f"({best_factor[1][2]})" if len(best_factor[1]) > 2 else ""
    report_lines.append(
        f"- 가장 높은 상관: {best_factor[0]}{strategy_str} (r={best_factor[1][1]:.3f} at {best_factor[1][0]}m)"
    )

    # 유의미한 요인 수
    significant_counts = {}
    for _, row in df_results.iterrows():
        distance = row["distance"]
        significant_counts[distance] = len(row.get("significant_factors", []))

    best_distance_for_significance = max(significant_counts.items(), key=lambda x: x[1])
    if best_distance_for_significance[1] > 0:
        report_lines.append(
            f"- 최다 유의미 요인: {best_distance_for_significance[0]}m에서 {best_distance_for_significance[1]}개"
        )

    # 2. 매칭 성능
    report_lines.append("\n## 2. 매칭 성능")
    report_lines.append("\n| 거리 | 매칭률 | 매칭 클러스터 | 실행시간 |")
    report_lines.append("|------|--------|--------------|----------|")

    for _, row in df_results.iterrows():
        distance = row["distance"]
        stats = row.get("matching_stats", {})
        exec_time = row.get("execution_time", 0)

        report_lines.append(
            f"| {distance}m | {stats.get('matching_rate', 0):.1f}% | "
            f"{stats.get('matched_clusters', 0)}/{stats.get('total_clusters', 0)} | "
            f"{exec_time:.2f}s |"
        )

    # 3. 상관관계 분석
    report_lines.append("\n## 3. 상관관계 분석")

    # 3.1 K-factor별 최적 거리 및 전략 (상세 테이블)
    report_lines.append("\n### K-factor별 최적 거리 및 전략:")
    report_lines.append("\n| K-factor | 전략 | 거리 | r | p | R² |")
    report_lines.append("|----------|------|------|-----|-----|-----|")

    for factor in k_factors:
        if factor in optimal_distances:
            opt_data = optimal_distances[factor]
            dist = opt_data[0]
            corr = opt_data[1]
            strategy = opt_data[2] if len(opt_data) > 2 else "max"
            p_value = opt_data[3] if len(opt_data) > 3 else 1.0
            r_squared = corr**2

            # 실제 상관계수 값 (절대값이 아닌 원본)
            actual_corr = 0
            for _, row in df_results.iterrows():
                if row["distance"] == dist:
                    best_strat = row.get("best_strategies", {}).get(factor, {})
                    if best_strat:
                        actual_corr = best_strat.get("r", 0)
                    else:
                        actual_corr = row.get("correlations", {}).get(factor, 0)
                    break

            report_lines.append(
                f"| {FACTOR_NAMES.get(factor, factor)} | {strategy} | {dist}m | "
                f"{actual_corr:.3f} | {p_value:.3f} | {r_squared*100:.2f}% |"
            )

    # 3.2 거리별 상세 분석
    report_lines.append("\n### 거리별 상세 분석:")

    for _, row in df_results.iterrows():
        distance = row["distance"]
        report_lines.append(f"\n#### {distance}m 거리")
        report_lines.append("\n| K-factor | 전략 | r | p | R² |")
        report_lines.append("|----------|------|-----|-----|-----|")

        for factor in k_factors:
            best_strat = row.get("best_strategies", {}).get(factor, {})
            if best_strat:
                strategy = best_strat.get("strategy", "max")
                r = best_strat.get("r", 0)
                p = best_strat.get("p", 1.0)
                r_squared = r**2
            else:
                # 하위 호환성
                strategy = "max"
                r = row.get("correlations", {}).get(factor, 0)
                p = row.get("p_values", {}).get(factor, 1.0)
                r_squared = r**2

            report_lines.append(
                f"| {FACTOR_NAMES.get(factor, factor)} | {strategy} | "
                f"{r:.3f} | {p:.3f} | {r_squared*100:.2f}% |"
            )

    # 4. 통계적 유의성
    report_lines.append("\n## 4. 통계적 유의성")
    report_lines.append("\n### 거리별 유의미한 요인 (p < 0.05):")

    # 유의성 테이블
    report_lines.append("\n| 거리 | 유의미한 요인 | r | p | R² |")
    report_lines.append("|------|--------------|-----|-----|-----|")

    for _, row in df_results.iterrows():
        distance = row["distance"]
        significant = row.get("significant_factors", [])

        if significant:
            for s in significant:
                factor = s["factor"]
                strategy = s.get("strategy", "max")
                r = s.get("r", 0)
                p = s.get("p", 1.0)
                r_squared = r**2
                report_lines.append(
                    f"| {distance}m | {FACTOR_NAMES.get(factor, factor)}({strategy}) | "
                    f"{r:.3f} | {p:.3f} | {r_squared*100:.2f}% |"
                )
        else:
            report_lines.append(f"| {distance}m | 없음 | - | - | - |")

    # 5. 결론 및 제언
    report_lines.append("\n## 5. 결론 및 제언")

    # 권장 거리 결정
    if 20 <= avg_optimal <= 30:
        recommended = 30
        reason = "균형잡힌 매칭률과 상관관계"
    elif avg_optimal < 20:
        recommended = 20
        reason = "국지적 영향 포착"
    else:
        recommended = 50
        reason = "지역적 패턴 분석"

    report_lines.append(f"\n### 권장 거리: **{recommended}m**")
    report_lines.append(f"- 이유: {reason}")
    report_lines.append(f"- 평균 최적 거리: {avg_optimal:.0f}m")

    # 추가 권고사항
    report_lines.append("\n### 추가 권고사항:")
    report_lines.append("- K_soil과 같은 지역적 특성은 30-50m 범위가 적합")
    report_lines.append("- K_traffic과 같은 국지적 영향은 10-20m 범위가 적합")
    report_lines.append("- 종합 분석을 위해서는 20-30m 권장")

    # 보고서 저장
    report_path = output_dir / "sensitivity_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n✓ 보고서 저장: {report_path}")

    # 콘솔 출력
    print("\n" + "=" * 60)
    print("분석 완료 요약")
    print("=" * 60)
    print(f"전체 최적 거리: {avg_optimal:.0f}m")
    print(f"권장 거리: {recommended}m ({reason})")
    strategy_info = f"({best_factor[1][2]})" if len(best_factor[1]) > 2 else ""
    print(
        f"최고 상관: {best_factor[0]}{strategy_info} at {best_factor[1][0]}m (r={best_factor[1][1]:.3f})"
    )


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("거리 민감도 분석 시작")
    print("=" * 60)

    # 분석할 거리 리스트
    distances = [10, 20, 30, 50, 100]

    print(f"\n분석 거리: {distances}")
    print(f"결과 디렉토리: {RESULTS_BASE}")

    # 민감도 분석 실행
    analyze_distance_sensitivity(distances)

    print("\n" + "=" * 60)
    print("모든 분석 완료!")
    print("=" * 60)
    print(f"\n결과 위치: {RESULTS_BASE}")
    print(f"- 거리별 결과: {RESULTS_BASE}/distance_*m/")
    print(f"- 통합 분석: {RESULTS_BASE}/integrated_analysis/")
    print(f"- 보고서: {RESULTS_BASE}/integrated_analysis/sensitivity_report.md")


if __name__ == "__main__":
    main()
