#!/usr/bin/env python3
"""
압력 데이터 특성 분석 및 SAITS 적합성 검토

목적:
1. 센서간 상관관계 분석
2. 시간적 자기상관 분석
3. 주기성/계절성 탐지
4. SAITS 적합성 점수 산출
5. 최적 방법론 추천
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.signal import find_peaks
from statsmodels.tsa.stattools import acf, ccf
from statsmodels.graphics.tsaplots import plot_acf
import warnings
warnings.filterwarnings('ignore')

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from common import config

# Set plot style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_pressure_data(area: str) -> pd.DataFrame:
    """Load pressure data for specific area"""
    cfg = config.ProjectConfig()

    pressure_paths = {
        '0243': cfg.SMALL_AREA_0243_PRESSURE_DATA_PATH,
        '0461': cfg.SMALL_AREA_0461_PRESSURE_DATA_PATH,
        '0470': cfg.SMALL_AREA_0470_PRESSURE_DATA_PATH,
        '0480': cfg.SMALL_AREA_0480_PRESSURE_DATA_PATH,
        '0490': cfg.SMALL_AREA_0490_PRESSURE_DATA_PATH,
    }

    if area not in pressure_paths:
        raise ValueError(f"Unknown area: {area}")

    file_path = pressure_paths[area]
    df = pd.read_csv(file_path)
    df['msrmt_dt'] = pd.to_datetime(df['msrmt_dt'])
    df = df.sort_values('msrmt_dt').reset_index(drop=True)

    return df


def analyze_cross_correlation(df_aligned: pd.DataFrame, sensors: list) -> dict:
    """
    센서간 상관관계 분석

    Returns:
        dict with correlation_matrix, mean_correlation, max_lag_correlation
    """
    print("\n[1] 센서간 상관관계 분석...")

    # Pearson correlation matrix
    pressure_cols = [f'pressure_{s}' for s in sensors]
    corr_matrix = df_aligned[pressure_cols].corr()

    # Mean correlation (excluding diagonal)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    mean_corr = corr_matrix.where(mask).stack().mean()

    print(f"  - 평균 상관계수: {mean_corr:.3f}")
    print(f"  - 최소 상관계수: {corr_matrix.where(mask).stack().min():.3f}")
    print(f"  - 최대 상관계수: {corr_matrix.where(mask).stack().max():.3f}")

    # Cross-correlation with lag
    print("\n  센서간 시차 상관관계 (Cross-correlation with lag):")
    max_lag = 100  # 최대 lag: ~8시간 (100 * 5분)

    ccf_results = {}
    for i, s1 in enumerate(sensors[:-1]):
        for s2 in sensors[i+1:]:
            col1 = f'pressure_{s1}'
            col2 = f'pressure_{s2}'

            # Calculate cross-correlation
            series1 = df_aligned[col1].dropna()
            series2 = df_aligned[col2].dropna()

            # Align by index
            common_idx = series1.index.intersection(series2.index)
            if len(common_idx) < 100:
                continue

            series1_aligned = series1.loc[common_idx]
            series2_aligned = series2.loc[common_idx]

            # Use scipy.signal.correlate for faster computation
            from scipy.signal import correlate
            correlation = correlate(series1_aligned, series2_aligned, mode='same')
            correlation = correlation / (len(series1_aligned) * series1_aligned.std() * series2_aligned.std())

            center = len(correlation) // 2
            lags = np.arange(-max_lag, max_lag+1)
            ccf_values = correlation[center-max_lag:center+max_lag+1]

            max_ccf_idx = np.argmax(np.abs(ccf_values))
            max_ccf_lag = lags[max_ccf_idx]
            max_ccf_value = ccf_values[max_ccf_idx]

            ccf_results[f'{s1}-{s2}'] = {
                'max_lag': max_ccf_lag,
                'max_ccf': max_ccf_value,
                'zero_lag': ccf_values[max_lag]
            }

            print(f"    {s1} vs {s2}:")
            print(f"      - Lag 0 상관계수: {ccf_values[max_lag]:.3f}")
            print(f"      - 최대 상관 lag: {max_ccf_lag} (약 {max_ccf_lag*5/60:.1f}시간)")
            print(f"      - 최대 상관계수: {max_ccf_value:.3f}")

    return {
        'correlation_matrix': corr_matrix,
        'mean_correlation': mean_corr,
        'ccf_results': ccf_results
    }


def analyze_autocorrelation(df_aligned: pd.DataFrame, target_sensor: str, max_lag: int = 500) -> dict:
    """
    시간적 자기상관 분석

    Args:
        max_lag: 최대 lag (500 = ~42시간)
    """
    print(f"\n[2] 시간적 자기상관 분석 (Target: {target_sensor})...")

    col = f'pressure_{target_sensor}'
    series = df_aligned[col].dropna()

    # Autocorrelation function
    acf_values = acf(series, nlags=max_lag, fft=True)

    # Find significant lags (above 95% confidence)
    conf_interval = 1.96 / np.sqrt(len(series))
    significant_lags = np.where(np.abs(acf_values) > conf_interval)[0]

    print(f"  - ACF[1] (5분 전): {acf_values[1]:.3f}")
    print(f"  - ACF[12] (1시간 전): {acf_values[12]:.3f}")
    print(f"  - ACF[288] (24시간 전): {acf_values[288]:.3f}" if max_lag >= 288 else "")
    print(f"  - 유의미한 lag 개수: {len(significant_lags)}")

    # Find peaks in ACF (주기성)
    peaks, properties = find_peaks(acf_values[1:], height=0.1, distance=10)
    peaks += 1  # Adjust index (started from 1)

    print(f"\n  ACF 피크 (주기성 힌트):")
    for peak in peaks[:5]:  # Top 5 peaks
        print(f"    - Lag {peak} ({peak*5/60:.1f}시간): ACF = {acf_values[peak]:.3f}")

    return {
        'acf_values': acf_values,
        'significant_lags': significant_lags,
        'peaks': peaks,
        'conf_interval': conf_interval
    }


def analyze_periodicity(df_aligned: pd.DataFrame, target_sensor: str) -> dict:
    """
    주기성/계절성 분석
    """
    print(f"\n[3] 주기성/계절성 분석 (Target: {target_sensor})...")

    col = f'pressure_{target_sensor}'
    df_temp = df_aligned[['msrmt_dt', col]].dropna().copy()
    df_temp.set_index('msrmt_dt', inplace=True)

    # Add time features
    df_temp['hour'] = df_temp.index.hour
    df_temp['day_of_week'] = df_temp.index.dayofweek
    df_temp['day'] = df_temp.index.day
    df_temp['month'] = df_temp.index.month

    # Daily pattern (hourly average)
    hourly_pattern = df_temp.groupby('hour')[col].agg(['mean', 'std'])
    hourly_variance = hourly_pattern['mean'].var()

    print(f"\n  일일 패턴 (Hourly):")
    print(f"    - 시간별 평균 분산: {hourly_variance:.4f}")
    print(f"    - 최고 시간: {hourly_pattern['mean'].idxmax()}시 ({hourly_pattern['mean'].max():.3f})")
    print(f"    - 최저 시간: {hourly_pattern['mean'].idxmin()}시 ({hourly_pattern['mean'].min():.3f})")
    print(f"    - 일일 변동폭: {hourly_pattern['mean'].max() - hourly_pattern['mean'].min():.3f}")

    # Weekly pattern
    weekly_pattern = df_temp.groupby('day_of_week')[col].agg(['mean', 'std'])
    weekly_variance = weekly_pattern['mean'].var()

    print(f"\n  주간 패턴 (Day of week):")
    print(f"    - 요일별 평균 분산: {weekly_variance:.4f}")
    days_kr = ['월', '화', '수', '목', '금', '토', '일']
    print(f"    - 최고 요일: {days_kr[weekly_pattern['mean'].idxmax()]} ({weekly_pattern['mean'].max():.3f})")
    print(f"    - 최저 요일: {days_kr[weekly_pattern['mean'].idxmin()]} ({weekly_pattern['mean'].min():.3f})")

    # Monthly pattern
    monthly_pattern = df_temp.groupby('month')[col].agg(['mean', 'std'])
    monthly_variance = monthly_pattern['mean'].var()

    print(f"\n  월별 패턴:")
    print(f"    - 월별 평균 분산: {monthly_variance:.4f}")
    print(f"    - 최고 월: {monthly_pattern['mean'].idxmax()}월 ({monthly_pattern['mean'].max():.3f})")
    print(f"    - 최저 월: {monthly_pattern['mean'].idxmin()}월 ({monthly_pattern['mean'].min():.3f})")

    return {
        'hourly_pattern': hourly_pattern,
        'hourly_variance': hourly_variance,
        'weekly_pattern': weekly_pattern,
        'weekly_variance': weekly_variance,
        'monthly_pattern': monthly_pattern,
        'monthly_variance': monthly_variance
    }


def analyze_variance_stability(df_aligned: pd.DataFrame, target_sensor: str) -> dict:
    """
    분산 안정성 분석 (Variance over time)
    """
    print(f"\n[4] 분산 안정성 분석 (Target: {target_sensor})...")

    col = f'pressure_{target_sensor}'
    df_temp = df_aligned[['msrmt_dt', col]].dropna().copy()
    df_temp.set_index('msrmt_dt', inplace=True)

    # Rolling variance (1일 window)
    window = 288  # 1 day
    rolling_var = df_temp[col].rolling(window=window).var()

    print(f"  - 전체 분산: {df_temp[col].var():.4f}")
    print(f"  - 평균 rolling 분산 (1일): {rolling_var.mean():.4f}")
    print(f"  - 분산의 분산: {rolling_var.var():.6f}")

    # Check stationarity (Augmented Dickey-Fuller test)
    from statsmodels.tsa.stattools import adfuller
    adf_result = adfuller(df_temp[col].dropna())

    print(f"\n  정상성 검정 (ADF Test):")
    print(f"    - ADF Statistic: {adf_result[0]:.4f}")
    print(f"    - p-value: {adf_result[1]:.4f}")
    print(f"    - 정상성: {'✅ 정상' if adf_result[1] < 0.05 else '❌ 비정상'}")

    return {
        'total_variance': df_temp[col].var(),
        'rolling_variance_mean': rolling_var.mean(),
        'rolling_variance_var': rolling_var.var(),
        'rolling_var_series': rolling_var,
        'adf_statistic': adf_result[0],
        'adf_pvalue': adf_result[1],
        'is_stationary': adf_result[1] < 0.05
    }


def calculate_saits_suitability_score(
    corr_results: dict,
    acf_results: dict,
    periodicity_results: dict,
    variance_results: dict,
    data_length: int
) -> dict:
    """
    SAITS 적합성 점수 계산 (0-100점)

    평가 기준:
    1. 센서간 상관관계 (30점)
    2. 시간적 자기상관 (25점)
    3. 주기성/패턴 (25점)
    4. 데이터 길이 (10점)
    5. 분산 안정성 (10점)
    """
    print("\n[5] SAITS 적합성 점수 계산...")

    scores = {}

    # 1. 센서간 상관관계 (30점)
    mean_corr = corr_results['mean_correlation']
    if mean_corr >= 0.8:
        corr_score = 30
    elif mean_corr >= 0.6:
        corr_score = 30 * (mean_corr - 0.6) / 0.2 + 15
    elif mean_corr >= 0.4:
        corr_score = 15 * (mean_corr - 0.4) / 0.2
    else:
        corr_score = 0

    scores['cross_correlation'] = {
        'score': corr_score,
        'max': 30,
        'value': mean_corr,
        'reason': '센서간 상관도가 높을수록 SAITS가 효과적'
    }

    # 2. 시간적 자기상관 (25점)
    acf_1h = acf_results['acf_values'][12] if len(acf_results['acf_values']) > 12 else 0
    acf_24h = acf_results['acf_values'][288] if len(acf_results['acf_values']) > 288 else 0

    acf_strength = (abs(acf_1h) + abs(acf_24h)) / 2

    if acf_strength >= 0.7:
        acf_score = 25
    elif acf_strength >= 0.5:
        acf_score = 25 * (acf_strength - 0.5) / 0.2 + 12.5
    elif acf_strength >= 0.3:
        acf_score = 12.5 * (acf_strength - 0.3) / 0.2
    else:
        acf_score = 0

    scores['autocorrelation'] = {
        'score': acf_score,
        'max': 25,
        'value': acf_strength,
        'reason': '자기상관이 강할수록 attention이 시간 패턴 학습 가능'
    }

    # 3. 주기성/패턴 (25점)
    hourly_var = periodicity_results['hourly_variance']
    weekly_var = periodicity_results['weekly_variance']

    # Normalize by total variance
    total_var = variance_results['total_variance']
    hourly_var_norm = hourly_var / total_var if total_var > 0 else 0
    weekly_var_norm = weekly_var / total_var if total_var > 0 else 0

    pattern_strength = (hourly_var_norm + weekly_var_norm) / 2

    if pattern_strength >= 0.1:
        pattern_score = 25
    elif pattern_strength >= 0.05:
        pattern_score = 25 * (pattern_strength - 0.05) / 0.05 + 12.5
    elif pattern_strength >= 0.01:
        pattern_score = 12.5 * (pattern_strength - 0.01) / 0.04
    else:
        pattern_score = 0

    scores['periodicity'] = {
        'score': pattern_score,
        'max': 25,
        'value': pattern_strength,
        'reason': '주기적 패턴이 뚜렷할수록 attention이 효과적'
    }

    # 4. 데이터 길이 (10점)
    if data_length >= 200000:
        length_score = 10
    elif data_length >= 100000:
        length_score = 10 * (data_length - 100000) / 100000 + 5
    elif data_length >= 50000:
        length_score = 5 * (data_length - 50000) / 50000
    else:
        length_score = 0

    scores['data_length'] = {
        'score': length_score,
        'max': 10,
        'value': data_length,
        'reason': 'Long sequence일수록 attention이 유리'
    }

    # 5. 분산 안정성 (10점)
    rolling_var_cv = np.sqrt(variance_results['rolling_variance_var']) / variance_results['rolling_variance_mean']

    if rolling_var_cv <= 0.2:
        stability_score = 10
    elif rolling_var_cv <= 0.5:
        stability_score = 10 * (0.5 - rolling_var_cv) / 0.3
    else:
        stability_score = 0

    scores['variance_stability'] = {
        'score': stability_score,
        'max': 10,
        'value': rolling_var_cv,
        'reason': '분산이 안정적일수록 모델 학습 용이'
    }

    # Total score
    total_score = sum(s['score'] for s in scores.values())

    print(f"\n  점수 상세:")
    for key, value in scores.items():
        print(f"    - {key}: {value['score']:.1f}/{value['max']} (값: {value['value']:.3f})")
        print(f"      └─ {value['reason']}")

    print(f"\n  **총점: {total_score:.1f}/100**")

    # Interpretation
    if total_score >= 80:
        interpretation = "✅ SAITS 매우 적합 (강력 추천)"
        alternatives = []
    elif total_score >= 60:
        interpretation = "✅ SAITS 적합 (추천)"
        alternatives = ["BRITS (백업)"]
    elif total_score >= 40:
        interpretation = "⚠️ SAITS 보통 (시도 가능, 대안 병행)"
        alternatives = ["BRITS", "XGBoost+STL Hybrid", "Prophet"]
    else:
        interpretation = "❌ SAITS 부적합 (대안 우선)"
        alternatives = ["Prophet", "XGBoost+STL", "GP-VAE"]

    print(f"\n  평가: {interpretation}")
    if alternatives:
        print(f"  대안: {', '.join(alternatives)}")

    return {
        'scores': scores,
        'total_score': total_score,
        'interpretation': interpretation,
        'alternatives': alternatives
    }


def recommend_methods(saits_score: float, corr_results: dict, acf_results: dict) -> list:
    """
    데이터 특성에 기반한 방법론 추천
    """
    print("\n[6] 추천 방법론 순위...")

    recommendations = []

    mean_corr = corr_results['mean_correlation']
    acf_1h = acf_results['acf_values'][12] if len(acf_results['acf_values']) > 12 else 0

    # SAITS
    if saits_score >= 60:
        recommendations.append({
            'rank': 1,
            'method': 'SAITS',
            'expected_r2': '0.75-0.85',
            'reason': f'높은 적합성 점수 ({saits_score:.1f}/100)'
        })

    # BRITS
    if mean_corr >= 0.5 and abs(acf_1h) >= 0.5:
        recommendations.append({
            'rank': len(recommendations) + 1,
            'method': 'BRITS',
            'expected_r2': '0.70-0.80',
            'reason': f'센서 상관도 {mean_corr:.2f}, 자기상관 {acf_1h:.2f}'
        })

    # XGBoost + STL Hybrid
    if mean_corr >= 0.4:
        recommendations.append({
            'rank': len(recommendations) + 1,
            'method': 'XGBoost + STL Hybrid',
            'expected_r2': '0.70-0.80',
            'reason': f'센서 상관도 {mean_corr:.2f}, 기존 XGBoost 활용 가능'
        })

    # Prophet
    recommendations.append({
        'rank': len(recommendations) + 1,
        'method': 'Prophet',
        'expected_r2': '0.65-0.75',
        'reason': '간단한 구현, 추세/계절성 자동 탐지'
    })

    # GP-VAE
    if mean_corr >= 0.6:
        recommendations.append({
            'rank': len(recommendations) + 1,
            'method': 'GP-VAE',
            'expected_r2': '0.70-0.85',
            'reason': 'Smooth interpolation + 불확실성 정량화'
        })

    # Re-rank based on SAITS score
    if saits_score < 60:
        # Move Prophet up
        prophet_idx = next((i for i, r in enumerate(recommendations) if r['method'] == 'Prophet'), None)
        if prophet_idx and prophet_idx > 0:
            recommendations.insert(0, recommendations.pop(prophet_idx))

    # Update ranks
    for i, rec in enumerate(recommendations):
        rec['rank'] = i + 1

    print("\n  추천 순위:")
    for rec in recommendations[:5]:
        print(f"    {rec['rank']}. {rec['method']}")
        print(f"       - 예상 R²: {rec['expected_r2']}")
        print(f"       - 이유: {rec['reason']}")

    return recommendations


def generate_visualizations(
    df_aligned: pd.DataFrame,
    sensors: list,
    target_sensor: str,
    corr_results: dict,
    acf_results: dict,
    periodicity_results: dict,
    variance_results: dict,
    output_dir: Path
):
    """
    분석 결과 시각화
    """
    print("\n[7] 시각화 생성...")

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Correlation heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr_results['correlation_matrix'], annot=True, fmt='.3f',
                cmap='coolwarm', center=0, ax=ax, vmin=-1, vmax=1)
    ax.set_title('센서간 상관관계 매트릭스', fontsize=16, weight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'correlation_matrix.png', dpi=150)
    plt.close()
    print(f"  - Saved: correlation_matrix.png")

    # 2. Autocorrelation plot
    fig, ax = plt.subplots(figsize=(14, 6))
    lags = np.arange(len(acf_results['acf_values']))
    ax.stem(lags, acf_results['acf_values'], basefmt=' ')
    ax.axhline(acf_results['conf_interval'], color='r', linestyle='--', label='95% 신뢰구간')
    ax.axhline(-acf_results['conf_interval'], color='r', linestyle='--')
    ax.axhline(0, color='k', linestyle='-', linewidth=0.5)

    # Mark important lags
    ax.axvline(12, color='g', linestyle=':', alpha=0.5, label='1시간')
    ax.axvline(288, color='b', linestyle=':', alpha=0.5, label='24시간')

    ax.set_xlabel('Lag (5분 간격)', fontsize=12)
    ax.set_ylabel('Autocorrelation', fontsize=12)
    ax.set_title(f'자기상관 함수 (ACF) - {target_sensor}', fontsize=16, weight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'autocorrelation.png', dpi=150)
    plt.close()
    print(f"  - Saved: autocorrelation.png")

    # 3. Daily pattern
    fig, ax = plt.subplots(figsize=(12, 6))
    hourly = periodicity_results['hourly_pattern']
    ax.plot(hourly.index, hourly['mean'], marker='o', linewidth=2, markersize=6)
    ax.fill_between(hourly.index,
                     hourly['mean'] - hourly['std'],
                     hourly['mean'] + hourly['std'],
                     alpha=0.3)
    ax.set_xlabel('Hour of Day', fontsize=12)
    ax.set_ylabel('Pressure (Mean ± Std)', fontsize=12)
    ax.set_title(f'일일 패턴 - {target_sensor}', fontsize=16, weight='bold')
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'daily_pattern.png', dpi=150)
    plt.close()
    print(f"  - Saved: daily_pattern.png")

    # 4. Weekly pattern
    fig, ax = plt.subplots(figsize=(10, 6))
    weekly = periodicity_results['weekly_pattern']
    days_kr = ['월', '화', '수', '목', '금', '토', '일']
    ax.bar(range(7), weekly['mean'], yerr=weekly['std'], capsize=5,
           color=sns.color_palette("husl", 7))
    ax.set_xticks(range(7))
    ax.set_xticklabels(days_kr)
    ax.set_xlabel('Day of Week', fontsize=12)
    ax.set_ylabel('Pressure (Mean ± Std)', fontsize=12)
    ax.set_title(f'주간 패턴 - {target_sensor}', fontsize=16, weight='bold')
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'weekly_pattern.png', dpi=150)
    plt.close()
    print(f"  - Saved: weekly_pattern.png")

    # 5. Rolling variance
    fig, ax = plt.subplots(figsize=(14, 6))
    rolling_var = variance_results['rolling_var_series']
    ax.plot(rolling_var.index, rolling_var.values, linewidth=1, alpha=0.7)
    ax.axhline(rolling_var.mean(), color='r', linestyle='--',
               label=f'Mean: {rolling_var.mean():.4f}')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Variance (1-day rolling window)', fontsize=12)
    ax.set_title(f'분산 안정성 - {target_sensor}', fontsize=16, weight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'variance_stability.png', dpi=150)
    plt.close()
    print(f"  - Saved: variance_stability.png")

    print(f"\n  총 5개 시각화 파일 생성 완료: {output_dir}/")


def generate_report(
    sensors: list,
    target_sensor: str,
    data_length: int,
    corr_results: dict,
    acf_results: dict,
    periodicity_results: dict,
    variance_results: dict,
    suitability_results: dict,
    recommendations: list,
    output_path: Path
):
    """
    분석 리포트 생성 (Markdown)
    """
    print("\n[8] 분석 리포트 생성...")

    report = f"""# 압력 데이터 특성 분석 및 SAITS 적합성 평가 보고서

**분석 일자**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
**대상 센서**: {', '.join(sensors)}
**타겟 센서**: {target_sensor}
**데이터 길이**: {data_length:,} records

---

## 📊 Executive Summary

### SAITS 적합성 점수

**총점: {suitability_results['total_score']:.1f}/100**

{suitability_results['interpretation']}

### 추천 방법론 Top 3

"""

    for rec in recommendations[:3]:
        report += f"{rec['rank']}. **{rec['method']}** (예상 R²: {rec['expected_r2']})\n"
        report += f"   - {rec['reason']}\n\n"

    report += f"""
---

## 1. 센서간 상관관계 분석

### Pearson Correlation

- **평균 상관계수**: {corr_results['mean_correlation']:.3f}
- **최소 상관계수**: {min(corr_results['correlation_matrix'].where(np.triu(np.ones_like(corr_results['correlation_matrix'], dtype=bool), k=1)).stack()):.3f}
- **최대 상관계수**: {max(corr_results['correlation_matrix'].where(np.triu(np.ones_like(corr_results['correlation_matrix'], dtype=bool), k=1)).stack()):.3f}

### 평가

"""

    if corr_results['mean_correlation'] >= 0.7:
        report += "✅ **높은 상관도**: SAITS가 센서간 관계를 효과적으로 학습할 수 있습니다.\n"
    elif corr_results['mean_correlation'] >= 0.5:
        report += "✅ **중간 상관도**: SAITS 사용 가능하나, 성능은 중간 수준 예상.\n"
    else:
        report += "⚠️ **낮은 상관도**: SAITS 효과 제한적. 단변량 방법(SARIMA, Prophet) 고려 필요.\n"

    report += f"""
![Correlation Matrix](figures/correlation_matrix.png)

---

## 2. 시간적 자기상관 분석

### Autocorrelation Function (ACF)

"""

    acf_1h = acf_results['acf_values'][12] if len(acf_results['acf_values']) > 12 else 0
    acf_24h = acf_results['acf_values'][288] if len(acf_results['acf_values']) > 288 else 0

    report += f"- **ACF[12] (1시간 전)**: {acf_1h:.3f}\n"
    report += f"- **ACF[288] (24시간 전)**: {acf_24h:.3f}\n"
    report += f"- **유의미한 lag 개수**: {len(acf_results['significant_lags'])}\n"

    report += "\n### 주요 피크 (주기성)\n\n"
    for peak in acf_results['peaks'][:5]:
        report += f"- Lag {peak} ({peak*5/60:.1f}시간): ACF = {acf_results['acf_values'][peak]:.3f}\n"

    report += "\n### 평가\n\n"

    if abs(acf_1h) >= 0.7:
        report += "✅ **강한 자기상관**: Attention 메커니즘이 시간 패턴을 잘 학습할 수 있습니다.\n"
    elif abs(acf_1h) >= 0.5:
        report += "✅ **중간 자기상관**: 시간 패턴 학습 가능.\n"
    else:
        report += "⚠️ **약한 자기상관**: 시간적 의존성이 약함. 시계열 방법의 효과 제한적.\n"

    report += f"""
![Autocorrelation](figures/autocorrelation.png)

---

## 3. 주기성/계절성 분석

### 일일 패턴 (Hourly)

"""

    hourly = periodicity_results['hourly_pattern']
    report += f"- **시간별 평균 분산**: {periodicity_results['hourly_variance']:.4f}\n"
    report += f"- **최고 시간**: {hourly['mean'].idxmax()}시 ({hourly['mean'].max():.3f})\n"
    report += f"- **최저 시간**: {hourly['mean'].idxmin()}시 ({hourly['mean'].min():.3f})\n"
    report += f"- **일일 변동폭**: {hourly['mean'].max() - hourly['mean'].min():.3f}\n"

    report += "\n### 주간 패턴 (Day of Week)\n\n"

    weekly = periodicity_results['weekly_pattern']
    days_kr = ['월', '화', '수', '목', '금', '토', '일']
    report += f"- **요일별 평균 분산**: {periodicity_results['weekly_variance']:.4f}\n"
    report += f"- **최고 요일**: {days_kr[weekly['mean'].idxmax()]} ({weekly['mean'].max():.3f})\n"
    report += f"- **최저 요일**: {days_kr[weekly['mean'].idxmin()]} ({weekly['mean'].min():.3f})\n"

    report += "\n### 월별 패턴\n\n"

    monthly = periodicity_results['monthly_pattern']
    report += f"- **월별 평균 분산**: {periodicity_results['monthly_variance']:.4f}\n"
    report += f"- **최고 월**: {monthly['mean'].idxmax()}월 ({monthly['mean'].max():.3f})\n"
    report += f"- **최저 월**: {monthly['mean'].idxmin()}월 ({monthly['mean'].min():.3f})\n"

    report += "\n### 평가\n\n"

    total_var = variance_results['total_variance']
    pattern_ratio = periodicity_results['hourly_variance'] / total_var if total_var > 0 else 0

    if pattern_ratio >= 0.1:
        report += "✅ **뚜렷한 주기성**: Attention이 반복 패턴을 효과적으로 학습 가능.\n"
    elif pattern_ratio >= 0.05:
        report += "✅ **중간 주기성**: 일부 패턴 학습 가능.\n"
    else:
        report += "⚠️ **약한 주기성**: 주기적 패턴이 약해 시계열 방법 효과 제한적.\n"

    report += f"""
![Daily Pattern](figures/daily_pattern.png)
![Weekly Pattern](figures/weekly_pattern.png)

---

## 4. 분산 안정성 분석

### 통계량

- **전체 분산**: {variance_results['total_variance']:.4f}
- **평균 rolling 분산 (1일)**: {variance_results['rolling_variance_mean']:.4f}
- **분산의 분산**: {variance_results['rolling_variance_var']:.6f}
- **변동 계수 (CV)**: {np.sqrt(variance_results['rolling_variance_var']) / variance_results['rolling_variance_mean']:.3f}

### 정상성 검정 (ADF Test)

- **ADF Statistic**: {variance_results['adf_statistic']:.4f}
- **p-value**: {variance_results['adf_pvalue']:.4f}
- **결과**: {'✅ 정상 시계열' if variance_results['is_stationary'] else '❌ 비정상 시계열'}

### 평가

"""

    cv = np.sqrt(variance_results['rolling_variance_var']) / variance_results['rolling_variance_mean']

    if cv <= 0.2:
        report += "✅ **안정적 분산**: 모델 학습에 유리.\n"
    elif cv <= 0.5:
        report += "✅ **중간 안정성**: 학습 가능하나 전처리 고려.\n"
    else:
        report += "⚠️ **불안정 분산**: 데이터 정규화 또는 로그 변환 필요.\n"

    if not variance_results['is_stationary']:
        report += "\n⚠️ **비정상 시계열**: Differencing 또는 detrending 전처리 권장.\n"

    report += f"""
![Variance Stability](figures/variance_stability.png)

---

## 5. SAITS 적합성 점수 상세

| 항목 | 점수 | 만점 | 값 | 평가 |
|------|------|------|-----|------|
"""

    for key, value in suitability_results['scores'].items():
        status = "✅" if value['score'] >= value['max'] * 0.7 else "⚠️" if value['score'] >= value['max'] * 0.4 else "❌"
        report += f"| {key} | {value['score']:.1f} | {value['max']} | {value['value']:.3f} | {status} |\n"

    report += f"\n**총점: {suitability_results['total_score']:.1f}/100**\n"

    report += "\n### 점수별 의미\n\n"
    for key, value in suitability_results['scores'].items():
        report += f"- **{key}** ({value['score']:.1f}/{value['max']}): {value['reason']}\n"

    report += f"""
---

## 6. 추천 방법론

### 순위별 추천

"""

    for rec in recommendations:
        report += f"### {rec['rank']}위: {rec['method']}\n\n"
        report += f"- **예상 R²**: {rec['expected_r2']}\n"
        report += f"- **이유**: {rec['reason']}\n\n"

    report += f"""
---

## 7. 결론 및 제언

### 최종 판단

{suitability_results['interpretation']}

### 실행 계획

"""

    if suitability_results['total_score'] >= 60:
        report += """
1. **SAITS POC 구현** (최우선)
   ```bash
   pip install pypots torch
   python test_saits_interpolation.py
   ```

2. **성공 기준**: R² > 0.75, MAE < 0.1

3. **실패 시 대안**:
   - BRITS 시도
   - XGBoost + STL Hybrid

"""
    else:
        report += f"""
1. **대안 방법 우선 시도**:
   - {recommendations[0]['method']}
"""
        if len(recommendations) > 1:
            report += f"   - {recommendations[1]['method']}\n"

        report += """
2. **SAITS는 후순위** (적합성 점수 낮음)

3. **데이터 전처리 고려**:
   - 정규화/표준화
   - Differencing (비정상성 제거)
   - 이상치 제거

"""

    report += """
---

**보고서 끝**
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n  리포트 저장 완료: {output_path}")


def main():
    """Main execution"""
    print("=" * 80)
    print("압력 데이터 특성 분석 및 SAITS 적합성 검토")
    print("=" * 80)

    # Setup paths
    script_dir = Path(__file__).parent
    results_dir = script_dir / "results"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)

    # Load data
    print("\n[데이터 로딩]")
    sensors = ['0243', '0461', '0470']  # Target과 features
    target_sensor = '0243'

    data_dict = {}
    for sensor in sensors:
        df = load_pressure_data(sensor)
        print(f"  - {sensor}: {len(df):,} records")
        data_dict[sensor] = df

    # Align timestamps
    print("\n[타임스탬프 정렬]")
    common_timestamps = data_dict['0243']['msrmt_dt']
    for sensor in sensors[1:]:
        common_timestamps = common_timestamps[
            common_timestamps.isin(data_dict[sensor]['msrmt_dt'])
        ]

    df_aligned = pd.DataFrame({'msrmt_dt': common_timestamps})
    for sensor in sensors:
        df_sensor = data_dict[sensor].set_index('msrmt_dt')['wtrprsr']
        df_aligned[f'pressure_{sensor}'] = df_aligned['msrmt_dt'].map(df_sensor)

    print(f"  - 공통 타임스탬프: {len(df_aligned):,}")
    print(f"  - 기간: {df_aligned['msrmt_dt'].min()} ~ {df_aligned['msrmt_dt'].max()}")

    # Analysis
    corr_results = analyze_cross_correlation(df_aligned, sensors)
    acf_results = analyze_autocorrelation(df_aligned, target_sensor, max_lag=500)
    periodicity_results = analyze_periodicity(df_aligned, target_sensor)
    variance_results = analyze_variance_stability(df_aligned, target_sensor)

    suitability_results = calculate_saits_suitability_score(
        corr_results,
        acf_results,
        periodicity_results,
        variance_results,
        len(df_aligned)
    )

    recommendations = recommend_methods(
        suitability_results['total_score'],
        corr_results,
        acf_results
    )

    # Visualizations
    generate_visualizations(
        df_aligned,
        sensors,
        target_sensor,
        corr_results,
        acf_results,
        periodicity_results,
        variance_results,
        figures_dir
    )

    # Report
    generate_report(
        sensors,
        target_sensor,
        len(df_aligned),
        corr_results,
        acf_results,
        periodicity_results,
        variance_results,
        suitability_results,
        recommendations,
        results_dir / "DATA_ANALYSIS_REPORT.md"
    )

    # Final summary
    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)
    print(f"\n✅ SAITS 적합성 점수: {suitability_results['total_score']:.1f}/100")
    print(f"✅ {suitability_results['interpretation']}")
    print(f"\n✅ 추천 방법 1순위: {recommendations[0]['method']}")
    print(f"\n✅ 결과 저장:")
    print(f"   - 리포트: {results_dir / 'DATA_ANALYSIS_REPORT.md'}")
    print(f"   - 시각화: {figures_dir}/ (5개 파일)")
    print("=" * 80)


if __name__ == "__main__":
    main()
