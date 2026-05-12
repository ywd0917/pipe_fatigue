"""
복구 공사 데이터와 주변 시설물(인프라)의 상관관계를 분석
하위 지역별 반경 민감도 분석 (통계적 유의미성 조사)
0470, 0480, 0490 각 지역에서 10m, 20m, 30m, 50m, 100m 반경별 상관관계 분석
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

from src.common.config import DATA_DIR, RAW_DATA_DIR, RESULTS_DIR
from src.common.shapefile_loader import (
    get_parent_region,
    get_subregion_boundary,
    get_subregion_label,
    is_subregion,
)
from src.main19_visualize_520_repairs import (
    load_520_csv_files,
    load_background_data,
)

# main19a_fast_radius_analysis와 main14a에서 필요한 함수 임포트
from src.main19a_fast_radius_analysis import (
    analyze_infrastructure_correlation_fast,
    setup_korean_font,
)

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 분석 상수
SUBREGIONS = ["0470", "0480", "0490"]
RADII = [10, 20, 30, 50, 100]
INFRA_TYPES = ["sply_ls", "valve", "fire", "total_infra"]

# 출력 디렉토리
OUTPUT_BASE_DIR = RESULTS_DIR / "main19b_subregion_analysis"


def load_subregion_data(region_code: str, verbose: bool = True) -> pd.DataFrame | None:
    """하위 지역 복구 데이터 로드 및 필터링

    Args:
        region_code: 지역 코드 (0470, 0480, 0490)
        verbose: 상세 출력 여부

    Returns:
        필터링된 복구 데이터 DataFrame
    """
    if not is_subregion(region_code):
        print(f"경고: {region_code}는 하위 지역이 아닙니다.")
        return None

    # 부모 지역(0520) 데이터 로드
    parent_region = get_parent_region(region_code)
    df = load_520_csv_files(RESULTS_DIR, verbose=verbose)

    if df is None or len(df) == 0:
        return None

    # 지역 경계 추출
    smlz_path = (
        RAW_DATA_DIR / f"export_shp_20250704({parent_region})" / "WEA_SMLZ_AS.shp"
    )
    region_boundary = get_subregion_boundary(
        smlz_path, get_subregion_label(region_code)
    )

    if region_boundary is None:
        print(f"오류: {region_code} 지역 경계를 찾을 수 없습니다.")
        return None

    # WGS84 좌표를 GeoDataFrame으로 변환
    from shapely.geometry import Point

    geometry = [
        Point(lon, lat) for lon, lat in zip(df["경도"], df["위도"], strict=False)
    ]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf = gdf.to_crs("EPSG:5179")

    # 지역 경계 내 데이터만 필터링
    filtered = gpd.sjoin(gdf, region_boundary, predicate="within", how="inner")

    # DataFrame으로 변환 (원본 컬럼 유지)
    result_df = pd.DataFrame(filtered.drop(columns=["geometry", "index_right"]))

    if verbose:
        print(f"{region_code} 지역 복구 데이터: {len(df)}개 → {len(result_df)}개")

    return result_df


def load_subregion_infrastructure(
    region_code: str, verbose: bool = True
) -> dict[str, gpd.GeoDataFrame]:
    """하위 지역 인프라 데이터 로드 및 필터링

    Args:
        region_code: 지역 코드 (0470, 0480, 0490)
        verbose: 상세 출력 여부

    Returns:
        필터링된 인프라 데이터 딕셔너리
    """
    # 부모 지역 인프라 데이터 로드
    parent_region = get_parent_region(region_code)
    background_data = load_background_data(DATA_DIR, verbose=verbose)

    if not is_subregion(region_code):
        return background_data

    # 지역 경계 추출
    smlz_path = (
        RAW_DATA_DIR / f"export_shp_20250704({parent_region})" / "WEA_SMLZ_AS.shp"
    )
    region_boundary = get_subregion_boundary(
        smlz_path, get_subregion_label(region_code)
    )

    if region_boundary is None:
        print(f"오류: {region_code} 지역 경계를 찾을 수 없습니다.")
        return background_data

    # 각 인프라 타입별로 필터링
    filtered_data = {}
    for key in ["sply_ls", "valves", "fires"]:
        if background_data.get(key) is not None and len(background_data[key]) > 0:
            try:
                # 공간 조인으로 경계 내 데이터만 필터링
                filtered = gpd.sjoin(
                    background_data[key],
                    region_boundary,
                    predicate="intersects",
                    how="inner",
                )
                # 중복 제거
                original_columns = background_data[key].columns.tolist()
                filtered = filtered[original_columns].drop_duplicates()
                filtered_data[key] = filtered

                if verbose:
                    print(f"  {key}: {len(background_data[key])}개 → {len(filtered)}개")
            except Exception as e:
                print(f"  {key} 필터링 실패: {e}")
                filtered_data[key] = background_data[key]
        else:
            filtered_data[key] = background_data[key]

    return filtered_data


def analyze_single_combination(
    region_code: str,
    radius: float,
    repair_df: pd.DataFrame,
    background_data: dict[str, Any],
    output_dir: Path,
    verbose: bool = False,
) -> dict[str, Any]:
    """단일 지역-반경 조합 분석

    Args:
        region_code: 지역 코드
        radius: 분석 반경 (미터)
        repair_df: 복구 데이터
        background_data: 인프라 데이터
        output_dir: 출력 디렉토리
        verbose: 상세 출력 여부

    Returns:
        통계 분석 결과 딕셔너리
    """
    if verbose:
        print(f"    {region_code} - {radius}m 분석 중...")

    # 고속 인프라 상관관계 분석
    results = analyze_infrastructure_correlation_fast(
        repair_df, background_data, output_dir, radius=radius, verbose=False
    )

    if results is None:
        return {}

    # 통계 결과 추출
    stats_results = {}

    # 각 인프라 타입별로 결과 추출
    for infra_type in ["sply_ls", "valve", "fire", "total_infra"]:
        corr_key = f"corr_{infra_type}_avg"
        p_key = f"p_{infra_type}_avg"

        if corr_key in results and p_key in results:
            stats_results[infra_type] = {
                "correlation": (
                    float(results[corr_key]) if not np.isnan(results[corr_key]) else 0.0
                ),
                "p_value": (
                    float(results[p_key]) if not np.isnan(results[p_key]) else 1.0
                ),
                "significant": (
                    float(results[p_key]) < 0.05
                    if not np.isnan(results[p_key])
                    else False
                ),
            }
        else:
            stats_results[infra_type] = {
                "correlation": 0.0,
                "p_value": 1.0,
                "significant": False,
            }

    # 추가 통계 정보
    stats_results["summary"] = {
        "total_repairs": results.get("total_repairs", 0),
        "total_clusters": results.get("total_clusters", 0),
        "frequent_clusters": results.get("frequent_clusters", 0),
        "avg_sply_ls": results.get("avg_sply_ls", 0),
        "avg_valve": results.get("avg_valve", 0),
        "avg_fire": results.get("avg_fire", 0),
    }

    return stats_results


def analyze_subregion_radius_sensitivity() -> dict[str, dict[str, dict]]:
    """모든 하위 지역의 반경별 민감도 분석

    Returns:
        {지역: {반경: {통계결과}}} 형태의 중첩 딕셔너리
    """
    print("\n=== 하위 지역별 반경 민감도 분석 시작 ===")
    print(f"분석 지역: {', '.join(SUBREGIONS)}")
    print(f"분석 반경: {', '.join([f'{r}m' for r in RADII])}")

    all_results = {}

    for region in SUBREGIONS:
        print(f"\n[{region} 지역 분석]")
        region_start = time.time()

        # 지역별 출력 디렉토리 생성
        region_dir = OUTPUT_BASE_DIR / region
        region_dir.mkdir(parents=True, exist_ok=True)

        # 하위 지역 데이터 로드
        print("  데이터 로드 중...")
        repair_df = load_subregion_data(region, verbose=False)
        background_data = load_subregion_infrastructure(region, verbose=False)

        if repair_df is None or len(repair_df) == 0:
            print(f"  경고: {region} 지역 복구 데이터가 없습니다.")
            continue

        region_results = {}

        # 각 반경별 분석
        for radius in RADII:
            radius_dir = region_dir / f"radius_{radius}m"
            radius_dir.mkdir(parents=True, exist_ok=True)

            stats = analyze_single_combination(
                region, radius, repair_df, background_data, radius_dir, verbose=False
            )

            region_results[f"{radius}m"] = stats

            # 유의미한 상관관계 출력
            sig_count = sum(
                1
                for infra in INFRA_TYPES
                if stats.get(infra, {}).get("significant", False)
            )
            print(f"    반경 {radius:3d}m: {sig_count}개 유의미한 상관관계")

        all_results[region] = region_results

        # 지역 분석 시간
        region_elapsed = time.time() - region_start
        print(f"  {region} 분석 완료: {region_elapsed:.1f}초")

    return all_results


def create_significance_matrix(results: dict) -> pd.DataFrame:
    """통계적 유의미성 매트릭스 생성

    Args:
        results: 분석 결과 딕셔너리

    Returns:
        유의미성 매트릭스 DataFrame
    """
    rows = []

    for region in results:
        for radius_str in results[region]:
            radius = int(radius_str.replace("m", ""))
            for infra_type in INFRA_TYPES:
                if infra_type in results[region][radius_str]:
                    data = results[region][radius_str][infra_type]
                    rows.append(
                        {
                            "Region": region,
                            "Radius": radius,
                            "Infrastructure": infra_type,
                            "Correlation": data.get("correlation", 0),
                            "P_value": data.get("p_value", 1),
                            "Significant": data.get("significant", False),
                        }
                    )

    matrix = pd.DataFrame(rows)

    # 인프라 타입 한글 변환
    infra_labels = {
        "sply_ls": "SPLY_LS",
        "valve": "밸브",
        "fire": "소화전",
        "total_infra": "총인프라",
    }
    matrix["Infrastructure"] = matrix["Infrastructure"].map(infra_labels)

    return matrix


def find_optimal_radius(results: dict) -> dict[str, dict]:
    """각 지역별 최적 반경 도출

    Args:
        results: 분석 결과 딕셔너리

    Returns:
        {지역: {radius, score}} 형태의 최적 반경 딕셔너리
    """
    optimal = {}

    for region in results:
        best_score = -1
        best_radius = None

        for radius_str in results[region]:
            # 유의미한 상관관계 개수
            sig_count = 0
            total_corr = 0

            for infra_type in INFRA_TYPES:
                if infra_type in results[region][radius_str]:
                    data = results[region][radius_str][infra_type]
                    if data.get("significant", False):
                        sig_count += 1
                    total_corr += abs(data.get("correlation", 0))

            # 종합 점수: 유의미한 개수 × 평균 상관계수
            avg_corr = total_corr / len(INFRA_TYPES) if len(INFRA_TYPES) > 0 else 0
            score = sig_count * avg_corr

            if score > best_score:
                best_score = score
                best_radius = radius_str

        optimal[region] = {"radius": best_radius, "score": best_score}

    return optimal


def create_correlation_heatmap(
    results: dict, output_path: Path, show_plot: bool = False
):
    """상관계수 히트맵 생성

    Args:
        results: 분석 결과 딕셔너리
        output_path: 저장 경로
        show_plot: 그래프를 화면에 표시할지 여부
    """
    setup_korean_font()

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for idx, region in enumerate(SUBREGIONS):
        if region not in results:
            continue

        # 데이터 매트릭스 생성
        data = []
        for radius in RADII:
            radius_str = f"{radius}m"
            if radius_str not in results[region]:
                data.append([0, 0, 0, 0])
                continue

            row = []
            for infra_type in INFRA_TYPES:
                if infra_type in results[region][radius_str]:
                    corr = results[region][radius_str][infra_type].get("correlation", 0)
                else:
                    corr = 0
                row.append(corr)
            data.append(row)

        # 히트맵 그리기
        sns.heatmap(
            data,
            ax=axes[idx],
            xticklabels=["SPLY_LS", "밸브", "소화전", "총인프라"],
            yticklabels=[f"{r}m" for r in RADII],
            cmap="coolwarm",
            center=0,
            vmin=-1,
            vmax=1,
            annot=True,
            fmt=".3f",
            cbar_kws={"label": "상관계수"},
        )
        axes[idx].set_title(f"{region} 지역", fontsize=14, fontweight="bold")
        axes[idx].set_xlabel("인프라 타입", fontsize=11)
        if idx == 0:
            axes[idx].set_ylabel("반경", fontsize=11)

    plt.suptitle(
        "하위 지역별 반경-인프라 상관계수 히트맵",
        fontsize=16,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")

    if show_plot:
        plt.show()
    else:
        plt.close()

    print(f"히트맵 저장: {output_path}")


def create_pvalue_matrix_plot(
    results: dict, output_path: Path, show_plot: bool = False
):
    """P-value 매트릭스 플롯 생성

    Args:
        results: 분석 결과 딕셔너리
        output_path: 저장 경로
        show_plot: 그래프를 화면에 표시할지 여부
    """
    setup_korean_font()

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for idx, region in enumerate(SUBREGIONS):
        if region not in results:
            continue

        # P-value 매트릭스 생성
        data = []
        annotations = []

        for radius in RADII:
            radius_str = f"{radius}m"
            row_data = []
            row_annot = []

            if radius_str not in results[region]:
                row_data = [1.0] * 4
                row_annot = [""] * 4
            else:
                for infra_type in INFRA_TYPES:
                    if infra_type in results[region][radius_str]:
                        p_val = results[region][radius_str][infra_type].get(
                            "p_value", 1
                        )
                        row_data.append(p_val)

                        # 유의미성 표시
                        if p_val < 0.001:
                            row_annot.append("***")
                        elif p_val < 0.01:
                            row_annot.append("**")
                        elif p_val < 0.05:
                            row_annot.append("*")
                        else:
                            row_annot.append("")
                    else:
                        row_data.append(1.0)
                        row_annot.append("")

            data.append(row_data)
            annotations.append(row_annot)

        # 히트맵 그리기 (P-value는 낮을수록 좋으므로 색상 반전)
        im = axes[idx].imshow(data, cmap="RdYlGn_r", vmin=0, vmax=0.1, aspect="auto")

        # 격자 및 라벨 설정
        axes[idx].set_xticks(np.arange(4))
        axes[idx].set_yticks(np.arange(len(RADII)))
        axes[idx].set_xticklabels(["SPLY_LS", "밸브", "소화전", "총인프라"])
        axes[idx].set_yticklabels([f"{r}m" for r in RADII])

        # 유의미성 표시 추가
        for i in range(len(RADII)):
            for j in range(4):
                axes[idx].text(
                    j,
                    i,
                    annotations[i][j],
                    ha="center",
                    va="center",
                    color="black",
                    fontsize=12,
                )

        axes[idx].set_title(f"{region} 지역", fontsize=14, fontweight="bold")
        axes[idx].set_xlabel("인프라 타입", fontsize=11)
        if idx == 0:
            axes[idx].set_ylabel("반경", fontsize=11)

        # 컬러바 추가
        if idx == 2:
            cbar = plt.colorbar(im, ax=axes[idx])
            cbar.set_label("P-value", rotation=270, labelpad=15)

    plt.suptitle(
        "통계적 유의미성 (p < 0.05: *, p < 0.01: **, p < 0.001: ***)",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")

    if show_plot:
        plt.show()
    else:
        plt.close()

    print(f"P-value 매트릭스 저장: {output_path}")


def generate_comparative_report(
    results: dict, optimal_radii: dict, matrix_df: pd.DataFrame, output_path: Path
):
    """비교 분석 보고서 생성

    Args:
        results: 분석 결과
        optimal_radii: 최적 반경
        matrix_df: 유의미성 매트릭스
        output_path: 저장 경로
    """
    report = []
    report.append("# 하위 지역별 반경 민감도 분석 보고서\n")
    report.append(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"분석 지역: {', '.join(SUBREGIONS)}\n")
    report.append(f"분석 반경: {', '.join([f'{r}m' for r in RADII])}\n\n")

    # 1. 최적 반경 요약
    report.append("## 1. 지역별 최적 반경\n\n")
    report.append("| 지역 | 최적 반경 | 점수 |\n")
    report.append("|------|-----------|------|\n")
    for region, data in optimal_radii.items():
        report.append(f"| {region} | {data['radius']} | {data['score']:.3f} |\n")
    report.append("\n")

    # 2. 통계적 유의미성 요약
    report.append("## 2. 통계적 유의미성 분석\n\n")
    report.append("### 2.1 지역별 유의미한 상관관계 개수\n\n")
    report.append("| 지역 | 10m | 20m | 30m | 50m | 100m | 합계 |\n")
    report.append("|------|-----|-----|-----|-----|------|------|\n")

    for region in SUBREGIONS:
        if region not in results:
            continue
        counts = []
        total = 0
        for radius in RADII:
            radius_str = f"{radius}m"
            if radius_str in results[region]:
                count = sum(
                    1
                    for infra in INFRA_TYPES
                    if results[region][radius_str]
                    .get(infra, {})
                    .get("significant", False)
                )
                counts.append(str(count))
                total += count
            else:
                counts.append("0")
        report.append(f"| {region} | {' | '.join(counts)} | {total} |\n")
    report.append("\n")

    # 3. 인프라별 상세 분석 (r, p-value, R² 포함)
    report.append("## 3. 지역별 상세 상관관계 분석\n\n")

    for region in SUBREGIONS:
        if region not in results:
            continue

        report.append(f"### {region} 지역\n\n")

        for radius in RADII:
            radius_str = f"{radius}m"
            if radius_str not in results[region]:
                continue

            report.append(f"#### 반경 {radius}m 분석 결과\n\n")
            report.append(
                "| 인프라 타입 | r (상관계수) | p-value | R² (결정계수) | 유의성 |\n"
            )
            report.append(
                "|------------|-------------|---------|--------------|--------|\n"
            )

            for infra_type, infra_label in [
                ("sply_ls", "SPLY_LS"),
                ("valve", "밸브"),
                ("fire", "소화전"),
                ("total_infra", "총인프라"),
            ]:
                if infra_type in results[region][radius_str]:
                    data = results[region][radius_str][infra_type]
                    corr = data.get("correlation", 0)
                    p_val = data.get("p_value", 1)
                    r_squared = corr**2
                    sig = "*" if p_val < 0.05 else ""

                    report.append(
                        f"| {infra_label} | {corr:.4f} | {p_val:.4f} | {r_squared:.4f} | {sig} |\n"
                    )
            report.append("\n")

        report.append("\n")

    # 4. 인프라 타입별 최고 상관계수 요약
    report.append("## 4. 인프라 타입별 최고 상관계수\n\n")
    for infra_type, infra_label in [
        ("sply_ls", "SPLY_LS"),
        ("valve", "밸브"),
        ("fire", "소화전"),
        ("total_infra", "총인프라"),
    ]:
        report.append(f"### {infra_label}\n\n")
        report.append("| 지역 | 반경 | r | p-value | R² | 유의성 |\n")
        report.append("|------|------|---|---------|-----|--------|\n")

        for region in results:
            best_corr = 0
            best_radius = None
            best_data = None

            for radius_str in results[region]:
                if infra_type in results[region][radius_str]:
                    corr = abs(
                        results[region][radius_str][infra_type].get("correlation", 0)
                    )
                    if corr > best_corr:
                        best_corr = corr
                        best_radius = radius_str
                        best_data = results[region][radius_str][infra_type]

            if best_data:
                corr = best_data.get("correlation", 0)
                p_val = best_data.get("p_value", 1)
                r_squared = corr**2
                sig = "*" if p_val < 0.05 else ""
                report.append(
                    f"| {region} | {best_radius} | {corr:.4f} | {p_val:.4f} | {r_squared:.4f} | {sig} |\n"
                )
        report.append("\n")

    # 5. 권장사항
    report.append("## 5. 권장사항\n\n")
    for region, data in optimal_radii.items():
        if data["score"] > 0:
            report.append(f"### {region} 지역\n")
            report.append(f"- 권장 분석 반경: **{data['radius']}**\n")

            # 해당 반경의 유의미한 인프라 나열
            radius_str = data["radius"]
            if region in results and radius_str in results[region]:
                sig_infras = []
                for infra_type in INFRA_TYPES:
                    if (
                        results[region][radius_str]
                        .get(infra_type, {})
                        .get("significant", False)
                    ):
                        infra_label = {
                            "sply_ls": "SPLY_LS",
                            "valve": "밸브",
                            "fire": "소화전",
                            "total_infra": "총인프라",
                        }.get(infra_type, infra_type)
                        sig_infras.append(infra_label)

                if sig_infras:
                    report.append(f"- 유의미한 상관관계: {', '.join(sig_infras)}\n")
            report.append("\n")

    # 6. 데이터 요약
    report.append("## 6. 데이터 요약\n\n")
    for region in SUBREGIONS:
        if region in results:
            # 첫 번째 반경의 summary 정보 사용
            first_radius = f"{RADII[0]}m"
            if (
                first_radius in results[region]
                and "summary" in results[region][first_radius]
            ):
                summary = results[region][first_radius]["summary"]
                report.append(f"### {region} 지역\n")
                report.append(f"- 총 복구 작업: {summary.get('total_repairs', 0)}건\n")
                report.append(f"- 클러스터 수: {summary.get('total_clusters', 0)}개\n")
                report.append(
                    f"- 빈번한 클러스터: {summary.get('frequent_clusters', 0)}개\n\n"
                )

    # 통계 표시 설명 추가
    report.append("---\n")
    report.append("**참고**: * 표시는 p < 0.05 (통계적으로 유의미)\n\n")
    report.append(f"*보고서 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    # 파일 저장
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(report)

    print(f"비교 분석 보고서 저장: {output_path}")


def save_results(results: dict, output_dir: Path):
    """분석 결과를 JSON 파일로 저장

    Args:
        results: 분석 결과
        output_dir: 저장 디렉토리
    """
    # 전체 결과 저장
    output_path = output_dir / "all_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "analysis_date": datetime.now().isoformat(),
                "regions": SUBREGIONS,
                "radii": RADII,
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"전체 결과 저장: {output_path}")

    # 각 지역별 결과도 개별 저장
    for region in results:
        region_dir = output_dir / region
        region_dir.mkdir(parents=True, exist_ok=True)

        region_path = region_dir / f"statistical_summary_{region}.json"
        with open(region_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "region": region,
                    "analysis_date": datetime.now().isoformat(),
                    "radii": RADII,
                    "results": results[region],
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"{region} 결과 저장: {region_path}")


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="하위 지역별 반경 민감도 분석")
    parser.add_argument(
        "--regions",
        nargs="+",
        type=str,
        help=f"분석할 지역 목록 (기본값: {SUBREGIONS})",
    )
    parser.add_argument(
        "--radii", nargs="+", type=float, help=f"분석할 반경 목록 (기본값: {RADII})"
    )
    parser.add_argument("--verbose", action="store_true", help="상세 출력")
    parser.add_argument("--show", action="store_true", help="그래프를 화면에 표시")
    return parser.parse_args()


def main():
    """메인 실행 함수"""
    args = parse_arguments()

    # 한글 폰트 설정
    setup_korean_font()

    # 분석할 지역과 반경 설정
    global SUBREGIONS, RADII
    if args.regions:
        SUBREGIONS = args.regions
    if args.radii:
        RADII = [int(r) for r in args.radii]

    # 출력 디렉토리 생성
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    comparative_dir = OUTPUT_BASE_DIR / "comparative_analysis"
    comparative_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("하위 지역별 반경 민감도 분석")
    print("=" * 70)
    print(f"출력 디렉토리: {OUTPUT_BASE_DIR}")

    # 전체 시작 시간
    total_start = time.time()

    # 1. 모든 조합 분석
    results = analyze_subregion_radius_sensitivity()

    if not results:
        print("\n오류: 분석 결과가 없습니다.")
        return

    # 2. 유의미성 매트릭스 생성
    print("\n=== 통계 분석 중 ===")
    matrix_df = create_significance_matrix(results)
    matrix_path = comparative_dir / "significance_matrix.csv"
    matrix_df.to_csv(matrix_path, index=False, encoding="utf-8-sig")
    print(f"유의미성 매트릭스 저장: {matrix_path}")

    # 3. 최적 반경 도출
    optimal_radii = find_optimal_radius(results)
    print("\n최적 반경:")
    for region, data in optimal_radii.items():
        print(f"  {region}: {data['radius']} (점수: {data['score']:.3f})")

    # 4. 시각화 생성
    print("\n=== 시각화 생성 중 ===")

    # 상관계수 히트맵
    heatmap_path = comparative_dir / "correlation_heatmap.png"
    create_correlation_heatmap(results, heatmap_path, show_plot=args.show)

    # P-value 매트릭스
    pvalue_path = comparative_dir / "pvalue_matrix.png"
    create_pvalue_matrix_plot(results, pvalue_path, show_plot=args.show)

    # 5. 비교 분석 보고서 생성
    print("\n=== 보고서 생성 중 ===")
    report_path = comparative_dir / "optimal_radius_report.md"
    generate_comparative_report(results, optimal_radii, matrix_df, report_path)

    # 6. 결과 저장
    save_results(results, OUTPUT_BASE_DIR)

    # 전체 처리 시간
    total_elapsed = time.time() - total_start

    print("\n" + "=" * 70)
    print("분석 완료!")
    print("=" * 70)
    print("생성된 파일:")
    print(f"  - 유의미성 매트릭스: {matrix_path}")
    print(f"  - 상관계수 히트맵: {heatmap_path}")
    print(f"  - P-value 매트릭스: {pvalue_path}")
    print(f"  - 비교 분석 보고서: {report_path}")
    print(f"  - JSON 결과: {OUTPUT_BASE_DIR}/all_results.json")
    print(f"\n전체 처리 시간: {total_elapsed:.1f}초")
    print(f"지역당 평균: {total_elapsed/len(SUBREGIONS):.1f}초")

    return 0


if __name__ == "__main__":
    main()
