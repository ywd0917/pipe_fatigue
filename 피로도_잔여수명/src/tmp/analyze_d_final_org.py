#!/usr/bin/env python3
"""
임시 스크립트: D_final_org 값 범위 분석
main56 출력 파일에서 D_final_org 값의 분포와 범위를 분석
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import sys

def analyze_d_final_org() -> None:
    """main56 출력 파일의 D_final_org 값 범위 분석"""

    print("=" * 70)
    print("D_final_org Value Range Analysis from main56 Output Files")
    print("=" * 70)
    print()

    # 분석할 파일들
    files = [
        ("PIPE_LM", Path("results/main56_calc_fatigure/fatigue_pipe_lm.csv")),
        ("SPLY_LS", Path("results/main56_calc_fatigure/fatigue_sply_ls.csv"))
    ]

    all_regions = ['0243', '0461', '0470', '0480', '0490', '0520']
    combined_data = []

    for file_type, file_path in files:
        print(f"\n{file_type} Data Analysis")
        print("-" * 50)

        if not file_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
            continue

        df = pd.read_csv(file_path)
        print(f"Total records: {len(df):,}")

        for region in all_regions:
            col_name = f'{region}_D_final_org'
            if col_name in df.columns:
                values = df[col_name].dropna()
                if len(values) > 0:
                    print(f"\n{col_name}:")
                    print(f"  Count: {len(values):,} ({len(values)/len(df)*100:.1f}% of records)")
                    print(f"  Range: [{values.min():.6f}, {values.max():.6f}]")
                    print(f"  Mean: {values.mean():.6f} (±{values.std():.6f})")
                    print(f"  Median: {values.median():.6f}")
                    print(f"  95th percentile: {values.quantile(0.95):.6f}")
                    print(f"  99th percentile: {values.quantile(0.99):.6f}")

                    # 극값 체크
                    extreme_high = values[values > 1.0]
                    if len(extreme_high) > 0:
                        print(f"  ⚠️ Values > 1.0: {len(extreme_high)} records")

                    extreme_low = values[values < 0.001]
                    if len(extreme_low) > 0:
                        print(f"  ⚠️ Values < 0.001: {len(extreme_low)} records")

                    # 전체 통계용 데이터 수집
                    combined_data.extend(values.tolist())

    # 전체 통계
    print("\n" + "=" * 70)
    print("Summary of D_final_org Ranges Across All Regions")
    print("=" * 70)

    if combined_data:
        combined = np.array(combined_data)
        print(f"\nOverall D_final_org Statistics (all regions, both files):")
        print(f"  Total values: {len(combined):,}")
        print(f"  Global range: [{combined.min():.6f}, {combined.max():.6f}]")
        print(f"  Global mean: {combined.mean():.6f}")
        print(f"  Global median: {np.median(combined):.6f}")
        print(f"  Standard deviation: {combined.std():.6f}")
        print()
        print("  Distribution:")
        print(f"    < 0.01: {(combined < 0.01).sum():,} ({(combined < 0.01).sum()/len(combined)*100:.1f}%)")
        print(f"    0.01-0.1: {((combined >= 0.01) & (combined < 0.1)).sum():,} ({((combined >= 0.01) & (combined < 0.1)).sum()/len(combined)*100:.1f}%)")
        print(f"    0.1-1.0: {((combined >= 0.1) & (combined < 1.0)).sum():,} ({((combined >= 0.1) & (combined < 1.0)).sum()/len(combined)*100:.1f}%)")
        print(f"    >= 1.0: {(combined >= 1.0).sum():,} ({(combined >= 1.0).sum()/len(combined)*100:.1f}%)")

        # 리스크 임계값 제안
        print("\n" + "-" * 50)
        print("Suggested Risk Thresholds for main58:")
        print("-" * 50)
        print(f"  Critical (>95th percentile): > {np.percentile(combined, 95):.6f}")
        print(f"  Warning (75th-95th percentile): {np.percentile(combined, 75):.6f} - {np.percentile(combined, 95):.6f}")
        print(f"  Safe (<75th percentile): < {np.percentile(combined, 75):.6f}")
        print(f"  Very Low (<25th percentile): < {np.percentile(combined, 25):.6f}")
    else:
        print("❌ 분석할 데이터가 없습니다.")

if __name__ == "__main__":
    analyze_d_final_org()