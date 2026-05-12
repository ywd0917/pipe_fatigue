#!/usr/bin/env python3
"""
Test All Gaps - 3, 7, 14, 24 days

전체 gap 테스트 및 결과 비교
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json
import argparse
from datetime import datetime
import subprocess
import sys


def run_gap_test(area: str, gap_days: int, seed: int = 42) -> dict:
    """
    특정 gap length에 대한 테스트 실행

    Args:
        area: 소구역
        gap_days: Gap 일수
        seed: Random seed

    Returns:
        테스트 결과
    """
    print("\n" + "="*70)
    print(f"TESTING GAP: {gap_days} days")
    print("="*70)

    # spectral_gap_fill.py 실행
    cmd = [
        sys.executable,
        "spectral_gap_fill.py",
        "--area", area,
        "--gap-days", str(gap_days),
        "--seed", str(seed)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"✗ Gap {gap_days} days FAILED")
        print(result.stderr)
        return None

    print(f"✓ Gap {gap_days} days COMPLETED")

    # 결과 로드
    result_dir = Path(__file__).parent / "results" / f"gap_{gap_days}days"
    results_file = result_dir / "spectral_gap_fill_results.json"

    if not results_file.exists():
        print(f"✗ Results file not found: {results_file}")
        return None

    with open(results_file, 'r') as f:
        results = json.load(f)

    # Validation 실행
    print(f"\nRunning validation for gap {gap_days} days...")

    gap_true = np.load(result_dir / "gap_true.npy")
    gap_pred = np.load(result_dir / "gap_pred.npy")

    # Import validation module
    from validation import validate_spectral_gap_fill

    validation_results = validate_spectral_gap_fill(gap_true, gap_pred, result_dir)

    # 결과 통합
    results["validation"] = validation_results

    # 업데이트된 결과 저장
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def compare_all_results(results_list: list) -> pd.DataFrame:
    """
    모든 gap 테스트 결과 비교

    Args:
        results_list: 결과 리스트

    Returns:
        비교 DataFrame
    """
    comparison = []

    for results in results_list:
        if results is None:
            continue

        gap_days = results["gap_days"]
        stats = results["statistics"]["comparison"]
        val = results.get("validation", {})

        row = {
            "gap_days": gap_days,
            "gap_points": results["gap_length"],
            "mean_diff": stats["mean_diff"],
            "std_ratio": stats["std_ratio"],
            "variance_ratio": stats["variance_ratio"],
            "psd_similarity": val.get("psd", {}).get("psd_similarity", 0),
            "psd_correlation": val.get("psd", {}).get("psd_correlation", 0),
            "energy_preservation_pct": val.get("psd", {}).get("energy_preservation_pct", 0),
            "acf_correlation": val.get("acf", {}).get("acf_correlation", 0),
            "rainflow_match": val.get("rainflow", {}).get("rainflow_match", 0),
            "rainflow_cycles_true": val.get("rainflow", {}).get("cycles_true", 0),
            "rainflow_cycles_pred": val.get("rainflow", {}).get("cycles_pred", 0),
            "overall_score": val.get("overall_judgment", {}).get("overall_score", 0),
            "judgment": val.get("overall_judgment", {}).get("judgment", "UNKNOWN")
        }

        comparison.append(row)

    df = pd.DataFrame(comparison)
    return df


def generate_final_report(df: pd.DataFrame, output_dir: Path):
    """
    최종 보고서 생성

    Args:
        df: 비교 DataFrame
        output_dir: 출력 디렉토리
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV 저장
    csv_file = output_dir / "gap_test_comparison.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ Comparison table saved: {csv_file}")

    # Markdown 보고서
    md_file = output_dir / "FINAL_REPORT.md"

    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# 013: Spectral Matching Gap Fill - Final Report\n\n")
        f.write(f"**실행일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        f.write("## 📊 전체 결과 요약\n\n")

        f.write("### Gap 테스트 결과\n\n")
        f.write("| Gap (일) | Points | Mean Diff | Std Ratio | PSD Sim | ACF Corr | Rainflow | Overall | 판정 |\n")
        f.write("|----------|--------|-----------|-----------|---------|----------|----------|---------|------|\n")

        for _, row in df.iterrows():
            f.write(f"| {row['gap_days']} | {row['gap_points']:,} | "
                   f"{row['mean_diff']:.4f} | {row['std_ratio']:.4f} | "
                   f"{row['psd_similarity']:.4f} | {row['acf_correlation']:.4f} | "
                   f"{row['rainflow_match']:.4f} | {row['overall_score']:.4f} | "
                   f"{row['judgment']} |\n")

        f.write("\n### 성공 기준 체크\n\n")

        f.write("| 메트릭 | 최소 목표 | 우수 목표 | 3일 | 7일 | 14일 | 24일 |\n")
        f.write("|--------|-----------|-----------|-----|-----|------|------|\n")

        metrics = [
            ("PSD Similarity", 0.90, 0.95, "psd_similarity"),
            ("Variance Ratio", 0.80, 0.90, "variance_ratio"),
            ("ACF Correlation", 0.80, 0.90, "acf_correlation"),
            ("Rainflow Match", 0.90, 0.95, "rainflow_match")
        ]

        for metric_name, min_target, excellent_target, col_name in metrics:
            row_str = f"| {metric_name} | {min_target:.2f} | {excellent_target:.2f} |"

            for _, row in df.iterrows():
                val = row[col_name]
                if val >= excellent_target:
                    status = f" ✅ {val:.3f}"
                elif val >= min_target:
                    status = f" ⚠️ {val:.3f}"
                else:
                    status = f" ❌ {val:.3f}"
                row_str += status + " |"

            f.write(row_str + "\n")

        f.write("\n### 최종 판정\n\n")

        # 각 gap에 대한 판정
        for _, row in df.iterrows():
            gap_days = row['gap_days']
            judgment = row['judgment']
            rainflow = row['rainflow_match']

            if judgment == "EXCELLENT":
                icon = "✅✅✅"
            elif judgment == "GOOD":
                icon = "✅✅"
            elif judgment == "MARGINAL":
                icon = "⚠️"
            else:
                icon = "❌"

            f.write(f"**{gap_days}일 Gap**: {icon} {judgment} (Rainflow: {rainflow:.3f})\n\n")

        f.write("\n---\n\n")

        f.write("## 🔍 분석\n\n")

        # Rainflow match 분석
        f.write("### Rainflow Matching 분석\n\n")

        excellent_count = (df['rainflow_match'] > 0.95).sum()
        good_count = ((df['rainflow_match'] > 0.90) & (df['rainflow_match'] <= 0.95)).sum()
        fail_count = (df['rainflow_match'] <= 0.90).sum()

        f.write(f"- **우수 (> 0.95)**: {excellent_count}개 Gap\n")
        f.write(f"- **양호 (> 0.90)**: {good_count}개 Gap\n")
        f.write(f"- **실패 (< 0.90)**: {fail_count}개 Gap\n\n")

        if excellent_count > 0:
            f.write("✅ **성공**: 일부 gap에서 Fatigue 계산 사용 가능\n\n")
        elif good_count > 0:
            f.write("⚠️ **부분 성공**: 통계 분석 용도로 제한적 사용 가능\n\n")
        else:
            f.write("❌ **실패**: Spectral matching 방법으로는 Rainflow 목표 미달성\n\n")

        # Gap 길이 영향
        f.write("### Gap 길이 영향 분석\n\n")

        f.write("**Rainflow Match vs Gap Length**:\n")
        for _, row in df.iterrows():
            f.write(f"- {row['gap_days']:2d}일 ({row['gap_points']:6,} points): {row['rainflow_match']:.4f}\n")

        f.write("\n")

        # 상관관계
        if len(df) >= 3:
            corr_gap_rainflow = df['gap_days'].corr(df['rainflow_match'])
            f.write(f"**Gap 길이와 Rainflow 상관계수**: {corr_gap_rainflow:.4f}\n\n")

        f.write("---\n\n")

        f.write("## 📈 권장사항\n\n")

        # 평균 Rainflow score
        avg_rainflow = df['rainflow_match'].mean()

        if avg_rainflow > 0.95:
            f.write("### ✅ 방법 채택 권장\n\n")
            f.write("- Spectral matching 방법이 성공적\n")
            f.write("- Fatigue 계산에 사용 가능\n")
            f.write("- main41 구현 진행 권장\n\n")

        elif avg_rainflow > 0.85:
            f.write("### ⚠️ 조건부 채택\n\n")
            f.write("- 일부 개선 필요:\n")
            f.write("  - High-frequency synthesis 알고리즘 조정\n")
            f.write("  - Edge smoothing 파라미터 최적화\n")
            f.write("  - Rainflow cycle 분포 추가 분석\n\n")

        else:
            f.write("### ❌ 대안 방법 모색\n\n")
            f.write("- Spectral matching 방법 한계 확인\n")
            f.write("- **대안**:\n")
            f.write("  1. Gap 허용 정책 수립\n")
            f.write("  2. 물리 모델 기반 접근\n")
            f.write("  3. 센서 데이터 품질 개선\n\n")

        f.write("---\n\n")
        f.write(f"**보고서 생성**: {datetime.now().isoformat()}\n")

    print(f"✓ Final report saved: {md_file}")


def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description="Test All Gap Lengths")
    parser.add_argument("--area", type=str, default="0243", help="소구역")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--gaps", type=int, nargs="+", default=[3, 7, 14, 24],
                       help="Gap 일수 리스트")

    args = parser.parse_args()

    print("="*70)
    print("TEST ALL GAPS - Spectral Matching Gap Fill")
    print("="*70)
    print(f"Area: {args.area}")
    print(f"Gaps: {args.gaps} days")
    print(f"Seed: {args.seed}")
    print("="*70)

    # 각 gap 테스트
    results_list = []

    for gap_days in args.gaps:
        result = run_gap_test(args.area, gap_days, args.seed)
        results_list.append(result)

    # 결과 비교
    print("\n" + "="*70)
    print("COMPARING ALL RESULTS")
    print("="*70)

    df = compare_all_results(results_list)

    print("\n" + df.to_string(index=False))

    # 최종 보고서
    output_dir = Path(__file__).parent / "results"
    generate_final_report(df, output_dir)

    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
