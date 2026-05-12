"""
재작업과 파이프 위험 요인 간 상관관계 분석 공통 함수
"""

from typing import Any
import pandas as pd
from scipy import stats

from .constants import FACTOR_NAMES, P_VALUE_THRESHOLD


def analyze_correlation(
    df_matched: pd.DataFrame,
    analysis_factors: list[str],
    min_repairs_for_frequent: int = 4,
) -> dict[str, Any]:
    """
    분석 요인들과 재작업 횟수 상관관계 분석

    Parameters:
    -----------
    df_matched : pd.DataFrame
        매칭된 클러스터-파이프 데이터
    analysis_factors : list[str]
        분석할 요인 리스트
    min_repairs_for_frequent : int
        빈번한 재작업 판단 기준 (기본값: 4)

    Returns:
    --------
    dict : 상관관계 분석 결과
    """
    print("\n=== 상관관계 분석 중 ===")

    results: dict[str, Any] = {}

    # 각 요인과 전략별 상관계수 계산
    strategies = ["max", "nearest", "avg"]

    print("\n상관계수 (Pearson):")
    print("-" * 60)

    for factor in analysis_factors:
        factor_name = FACTOR_NAMES.get(factor, factor)
        print(f"\n{factor_name} ({factor}):")
        for strategy in strategies:
            col_name = f"{strategy}_{factor}"
            if col_name in df_matched.columns and len(df_matched) >= 2:
                corr, p_value = stats.pearsonr(
                    df_matched[col_name], df_matched["repair_count"]
                )
                results[f"{col_name}_corr"] = corr
                results[f"{col_name}_p"] = p_value

                sig = "*" if p_value < P_VALUE_THRESHOLD else ""
                print(f"  {strategy:8s}: r={corr:7.4f}, p={p_value:.4f} {sig}")
            elif col_name in df_matched.columns:
                # 데이터가 2개 미만인 경우
                results[f"{col_name}_corr"] = 0.0
                results[f"{col_name}_p"] = 1.0
                print(f"  {strategy:8s}: 데이터 부족")

    # 빈번한 재작업 그룹 vs 일반 그룹 비교
    df_frequent = df_matched[df_matched["repair_count"] >= min_repairs_for_frequent]
    df_normal = df_matched[df_matched["repair_count"] < min_repairs_for_frequent]

    results["frequent_count"] = len(df_frequent)
    results["normal_count"] = len(df_normal)

    print(
        f"\n그룹 비교: 빈번한 재작업({len(df_frequent)}개) vs 일반({len(df_normal)}개)"
    )
    print("-" * 60)

    for factor in analysis_factors:
        factor_name = FACTOR_NAMES.get(factor, factor)
        print(f"\n{factor_name}:")
        for strategy in strategies:
            col_name = f"{strategy}_{factor}"
            if (
                col_name in df_matched.columns
                and len(df_frequent) > 0
                and len(df_normal) > 0
            ):
                # t-test
                t_stat, t_p = stats.ttest_ind(
                    df_frequent[col_name], df_normal[col_name]
                )

                results[f"{col_name}_t_stat"] = t_stat
                results[f"{col_name}_t_p"] = t_p
                results[f"{col_name}_frequent_mean"] = df_frequent[col_name].mean()
                results[f"{col_name}_normal_mean"] = df_normal[col_name].mean()

                diff = df_frequent[col_name].mean() - df_normal[col_name].mean()
                diff_pct = (
                    (diff / df_normal[col_name].mean() * 100)
                    if df_normal[col_name].mean() != 0
                    else 0
                )

                sig = "*" if t_p < P_VALUE_THRESHOLD else ""
                print(
                    f"  {strategy:8s}: 빈번={df_frequent[col_name].mean():.4f}, "
                    f"일반={df_normal[col_name].mean():.4f}, "
                    f"차이={diff_pct:+.1f}%, p={t_p:.4f} {sig}"
                )

    # 가장 강한 상관관계 찾기
    best_corr: float = 0.0
    best_factor = ""
    best_strategy = ""

    for factor in analysis_factors:
        for strategy in strategies:
            col_name = f"{strategy}_{factor}"
            corr_key = f"{col_name}_corr"
            if (
                corr_key in results
                and isinstance(results[corr_key], int | float)
                and abs(results[corr_key]) > abs(best_corr)
            ):
                best_corr = float(results[corr_key])
                best_factor = factor
                best_strategy = strategy

    results["best_factor"] = best_factor
    results["best_strategy"] = best_strategy
    results["best_corr"] = best_corr

    print(
        f"\n가장 강한 상관관계: {FACTOR_NAMES.get(best_factor, best_factor)} "
        f"({best_strategy}), r={best_corr:.4f}"
    )

    return results


def calculate_correlations_by_strategy(
    df_matched: pd.DataFrame, analysis_factors: list[str], strategies: list[str] = None
) -> dict[str, float]:
    """
    전략별 상관계수 계산

    Parameters:
    -----------
    df_matched : pd.DataFrame
        매칭된 데이터
    analysis_factors : list[str]
        분석 요인 리스트
    strategies : list[str], optional
        전략 리스트 (기본값: ["max", "nearest", "avg"])

    Returns:
    --------
    dict : 전략별 상관계수
    """
    if strategies is None:
        strategies = ["max", "nearest", "avg"]

    correlations = {}

    for factor in analysis_factors:
        for strategy in strategies:
            col_name = f"{strategy}_{factor}"
            if col_name in df_matched.columns and len(df_matched) >= 2:
                corr, p_value = stats.pearsonr(
                    df_matched[col_name], df_matched["repair_count"]
                )
                correlations[f"{col_name}_corr"] = corr
                correlations[f"{col_name}_p"] = p_value
            else:
                correlations[f"{col_name}_corr"] = 0.0
                correlations[f"{col_name}_p"] = 1.0

    return correlations


def perform_group_comparison(
    df_matched: pd.DataFrame,
    analysis_factors: list[str],
    min_repairs_for_frequent: int = 4,
    strategies: list[str] = None,
) -> dict[str, Any]:
    """
    빈번한 재작업 그룹과 일반 그룹 비교

    Parameters:
    -----------
    df_matched : pd.DataFrame
        매칭된 데이터
    analysis_factors : list[str]
        분석 요인 리스트
    min_repairs_for_frequent : int
        빈번한 재작업 기준
    strategies : list[str], optional
        전략 리스트

    Returns:
    --------
    dict : 그룹 비교 결과
    """
    if strategies is None:
        strategies = ["max", "nearest", "avg"]

    df_frequent = df_matched[df_matched["repair_count"] >= min_repairs_for_frequent]
    df_normal = df_matched[df_matched["repair_count"] < min_repairs_for_frequent]

    comparison = {"frequent_count": len(df_frequent), "normal_count": len(df_normal)}

    for factor in analysis_factors:
        for strategy in strategies:
            col_name = f"{strategy}_{factor}"
            if (
                col_name in df_matched.columns
                and len(df_frequent) > 0
                and len(df_normal) > 0
            ):
                # t-test
                t_stat, t_p = stats.ttest_ind(
                    df_frequent[col_name], df_normal[col_name]
                )

                comparison[f"{col_name}_t_stat"] = t_stat
                comparison[f"{col_name}_t_p"] = t_p
                comparison[f"{col_name}_frequent_mean"] = df_frequent[col_name].mean()
                comparison[f"{col_name}_normal_mean"] = df_normal[col_name].mean()

    return comparison


def find_best_correlation(
    results: dict[str, Any], analysis_factors: list[str], strategies: list[str] = None
) -> tuple[str, str, float]:
    """
    가장 강한 상관관계 찾기

    Parameters:
    -----------
    results : dict
        상관관계 분석 결과
    analysis_factors : list[str]
        분석 요인 리스트
    strategies : list[str], optional
        전략 리스트

    Returns:
    --------
    tuple : (best_factor, best_strategy, best_correlation)
    """
    if strategies is None:
        strategies = ["max", "nearest", "avg"]

    best_corr = 0.0
    best_factor = ""
    best_strategy = ""

    for factor in analysis_factors:
        for strategy in strategies:
            col_name = f"{strategy}_{factor}"
            corr_key = f"{col_name}_corr"
            if (
                corr_key in results
                and isinstance(results[corr_key], (int, float))
                and abs(results[corr_key]) > abs(best_corr)
            ):
                best_corr = float(results[corr_key])
                best_factor = factor
                best_strategy = strategy

    return best_factor, best_strategy, best_corr
