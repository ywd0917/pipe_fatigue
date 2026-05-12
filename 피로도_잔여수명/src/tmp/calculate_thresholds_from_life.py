#!/usr/bin/env python3
"""
잔여 수명 기준으로 D_final_org 임계값 역산
잔여 수명 = 1 / D_final_org (근사식)
"""

import pandas as pd
import numpy as np
from pathlib import Path

def analyze_life_to_dfinal_relationship():
    """잔여 수명과 D_final의 관계 분석 및 임계값 역산"""

    print("=" * 70)
    print("잔여 수명 기준 D_final_org 임계값 역산")
    print("=" * 70)
    print()

    # 잔여 수명 기준 (년)
    life_thresholds = {
        '즉시교체': 0,     # 0년 이하
        '매우위험': 5,     # 0-5년
        '위험': 10,        # 5-10년
        '주의': 30,        # 10-30년
        '안전': float('inf')  # 30년 이상
    }

    print("잔여 수명 기준:")
    print("-" * 50)
    print("0년 이하: 즉시교체 (빨강 #FF0000)")
    print("0-5년: 매우위험 (빨강→주황 그라데이션)")
    print("5-10년: 위험 (주황→노랑 그라데이션)")
    print("10-30년: 주의 (노랑→연두 그라데이션)")
    print("30년 이상: 안전 (연두→초록)")
    print()

    # 실제 데이터에서 관계 분석
    files = [
        ("PIPE_LM", Path("results/main56_calc_fatigure/fatigue_pipe_lm.csv")),
        ("SPLY_LS", Path("results/main56_calc_fatigure/fatigue_sply_ls.csv"))
    ]

    regions = ['0470', '0480', '0490', '0520']

    # 데이터 수집
    all_data = []

    for file_type, file_path in files:
        if not file_path.exists():
            continue

        df = pd.read_csv(file_path)

        for region in regions:
            d_col = f'{region}_D_final'
            d_org_col = f'{region}_D_final_org'
            life_col = f'{region}_remaining_life_years'

            if d_col in df.columns and life_col in df.columns and d_org_col in df.columns:
                valid_data = df[[d_col, d_org_col, life_col]].dropna()

                for _, row in valid_data.iterrows():
                    if row[life_col] > 0 and row[d_org_col] > 0:  # 양수 값만
                        all_data.append({
                            'D_final': row[d_col],
                            'D_final_org': row[d_org_col],
                            'remaining_life': row[life_col],
                            'type': file_type,
                            'region': region
                        })

    if not all_data:
        print("❌ 분석할 데이터가 없습니다.")
        return

    df_analysis = pd.DataFrame(all_data)

    print(f"분석 데이터: {len(df_analysis):,}개 레코드")
    print()

    # 잔여 수명별 D_final_org 분석
    print("잔여 수명별 D_final_org 통계:")
    print("-" * 70)

    life_ranges = [
        (0, 5, '0-5년 (매우위험)'),
        (5, 10, '5-10년 (위험)'),
        (10, 30, '10-30년 (주의)'),
        (30, 50, '30-50년 (안전)'),
        (50, 100, '50-100년 (매우안전)'),
        (100, float('inf'), '100년+ (우수)')
    ]

    for min_life, max_life, label in life_ranges:
        mask = (df_analysis['remaining_life'] > min_life) & (df_analysis['remaining_life'] <= max_life)
        subset = df_analysis[mask]

        if len(subset) > 0:
            print(f"\n{label}:")
            print(f"  샘플 수: {len(subset):,}")
            print(f"  D_final_org 평균: {subset['D_final_org'].mean():.6f}")
            print(f"  D_final_org 중앙값: {subset['D_final_org'].median():.6f}")
            print(f"  D_final_org 최소: {subset['D_final_org'].min():.6f}")
            print(f"  D_final_org 최대: {subset['D_final_org'].max():.6f}")

            # 해당 범위의 95% 신뢰구간
            p5 = subset['D_final_org'].quantile(0.05)
            p95 = subset['D_final_org'].quantile(0.95)
            print(f"  D_final_org 90% 범위: [{p5:.6f}, {p95:.6f}]")

    # 역산 공식 적용 (간단한 역비례 가정)
    print("\n" + "=" * 70)
    print("역산된 D_final_org 임계값 (잔여수명 기준)")
    print("=" * 70)

    # 실제 데이터에서 잔여수명 경계값에 해당하는 D_final_org 찾기
    thresholds = {}

    for life_threshold in [5, 10, 30, 50]:
        # 해당 잔여수명 근처의 데이터 찾기 (±2년 범위)
        mask = (df_analysis['remaining_life'] >= life_threshold - 2) & \
               (df_analysis['remaining_life'] <= life_threshold + 2)
        subset = df_analysis[mask]

        if len(subset) > 0:
            # 해당 잔여수명에서의 D_final_org 중앙값
            d_threshold = subset['D_final_org'].median()
            thresholds[life_threshold] = d_threshold
            print(f"잔여수명 {life_threshold}년 → D_final_org ≈ {d_threshold:.6f}")

    # 보간법으로 추가 임계값 계산
    print("\n보간법 기반 추천 임계값:")
    print("-" * 50)

    # 로그 관계 가정: remaining_life ≈ k / D_final_org
    # 데이터에서 k 추정
    df_positive = df_analysis[(df_analysis['remaining_life'] > 0) & (df_analysis['D_final_org'] > 0)]
    if len(df_positive) > 0:
        # k = remaining_life * D_final_org의 중앙값
        k_values = df_positive['remaining_life'] * df_positive['D_final_org']
        k_median = k_values.median()

        print(f"추정된 관계식: remaining_life ≈ {k_median:.3f} / D_final_org")
        print()

        # 잔여수명 기준으로 D_final_org 역산
        life_targets = [5, 10, 30, 50, 100]
        d_thresholds = []

        for life in life_targets:
            d_calc = k_median / life
            d_thresholds.append(d_calc)
            print(f"잔여수명 {life:3d}년 → D_final_org = {d_calc:.6f}")

        print("\n" + "=" * 70)
        print("최종 추천 5단계 임계값")
        print("=" * 70)

        # 실제 데이터 percentile과 비교
        percentiles = [99, 95, 75, 50, 25]
        p_values = [df_analysis['D_final_org'].quantile(p/100) for p in percentiles]

        print("\n데이터 기반 percentile:")
        for p, val in zip(percentiles, p_values):
            print(f"  {p:2d}th percentile: {val:.6f}")

        print("\n잔여수명 역산 기준:")
        print(f"  즉시교체 (0-5년):    D_final_org > {k_median/5:.6f}")
        print(f"  매우위험 (5-10년):   D_final_org > {k_median/10:.6f}")
        print(f"  위험 (10-30년):      D_final_org > {k_median/30:.6f}")
        print(f"  주의 (30-50년):      D_final_org > {k_median/50:.6f}")
        print(f"  안전 (50년+):        D_final_org ≤ {k_median/50:.6f}")

        # 색상 매핑 제안
        print("\n색상 매핑:")
        print("-" * 50)
        print(f"D_final_org > {k_median/5:.6f}: 빨강 (#FF0000)")
        print(f"D_final_org {k_median/10:.6f} - {k_median/5:.6f}: 빨강→주황 그라데이션")
        print(f"D_final_org {k_median/30:.6f} - {k_median/10:.6f}: 주황→노랑 그라데이션")
        print(f"D_final_org {k_median/50:.6f} - {k_median/30:.6f}: 노랑→연두 그라데이션")
        print(f"D_final_org ≤ {k_median/50:.6f}: 연두→초록")

if __name__ == "__main__":
    analyze_life_to_dfinal_relationship()