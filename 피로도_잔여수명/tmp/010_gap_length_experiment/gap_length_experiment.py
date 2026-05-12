#!/usr/bin/env python3
"""
Gap 기간별 보간 성능 실험

목적: 보간 가능한 최대 Gap 길이 찾기
실험: 3일/7일/14일 gap에 대해 XGBoost/Prophet/Linear 성능 비교
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add paths
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import utilities from 009
utils_dir = script_dir.parent / "009_prophet_poc" / "utils"
sys.path.insert(0, str(utils_dir))

import data_loader
import evaluation
import visualization

# XGBoost
import xgboost as xgb

# Prophet
try:
    from prophet import Prophet
except ImportError:
    print("Installing Prophet...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "prophet"])
    from prophet import Prophet


def test_xgboost_interpolation(df_train, df_gap_true, gap_days):
    """
    XGBoost로 gap 보간 테스트

    Args:
        df_train: 훈련 데이터
        df_gap_true: Gap 기간 실제 데이터
        gap_days: Gap 길이 (일)

    Returns:
        metrics dict
    """
    print(f"  🤖 XGBoost 테스트 중...")

    # Feature engineering (간단 버전)
    # 시간 features만 사용 (다른 센서 데이터 없음)
    def create_time_features(df):
        df = df.copy()
        df['hour'] = df['msrmt_dt'].dt.hour
        df['day_of_week'] = df['msrmt_dt'].dt.dayofweek
        df['month'] = df['msrmt_dt'].dt.month
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        return df

    df_train_features = create_time_features(df_train)
    df_gap_features = create_time_features(df_gap_true)

    feature_cols = ['hour', 'day_of_week', 'month', 'hour_sin', 'hour_cos']

    X_train = df_train_features[feature_cols]
    y_train = df_train_features['wtrprsr']

    X_gap = df_gap_features[feature_cols]
    y_true = df_gap_features['wtrprsr'].values

    # XGBoost 모델 훈련
    model = xgb.XGBRegressor(
        n_estimators=1000,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train, verbose=False)

    # 예측
    y_pred = model.predict(X_gap)

    # 평가
    metrics = evaluation.calculate_metrics(y_true, y_pred)
    metrics['model'] = 'XGBoost'

    return metrics, y_pred


def test_prophet_interpolation(df_train, df_gap_true, gap_days):
    """
    Prophet으로 gap 보간 테스트

    Args:
        df_train: 훈련 데이터
        df_gap_true: Gap 기간 실제 데이터
        gap_days: Gap 길이 (일)

    Returns:
        metrics dict
    """
    print(f"  🔮 Prophet 테스트 중...")

    # Prophet 포맷
    df_prophet_train = pd.DataFrame({
        'ds': df_train['msrmt_dt'],
        'y': df_train['wtrprsr']
    })

    # Prophet 모델
    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        interval_width=0.95,
    )

    model.add_seasonality(
        name='intraday_5min',
        period=1,
        fourier_order=10
    )

    model.fit(df_prophet_train)

    # 예측
    future_gap = pd.DataFrame({
        'ds': df_gap_true['msrmt_dt']
    })

    forecast = model.predict(future_gap)

    y_true = df_gap_true['wtrprsr'].values
    y_pred = forecast['yhat'].values
    yhat_lower = forecast['yhat_lower'].values
    yhat_upper = forecast['yhat_upper'].values

    # 평가
    metrics = evaluation.calculate_metrics(y_true, y_pred, yhat_lower, yhat_upper)
    metrics['model'] = 'Prophet'

    return metrics, y_pred, forecast


def test_linear_interpolation(df_train, df_gap_true, gap_days):
    """
    Linear Interpolation으로 gap 보간 테스트

    Args:
        df_train: 훈련 데이터
        df_gap_true: Gap 기간 실제 데이터
        gap_days: Gap 길이 (일)

    Returns:
        metrics dict
    """
    print(f"  📏 Linear Interpolation 테스트 중...")

    # Gap 전 마지막 값
    last_value_before = df_train[df_train['msrmt_dt'] < df_gap_true['msrmt_dt'].min()]['wtrprsr'].iloc[-1]
    last_time_before = df_train[df_train['msrmt_dt'] < df_gap_true['msrmt_dt'].min()]['msrmt_dt'].iloc[-1]

    # Gap 후 첫 값
    first_value_after = df_train[df_train['msrmt_dt'] > df_gap_true['msrmt_dt'].max()]['wtrprsr'].iloc[0]
    first_time_after = df_train[df_train['msrmt_dt'] > df_gap_true['msrmt_dt'].max()]['msrmt_dt'].iloc[0]

    # Linear interpolation
    total_seconds = (first_time_after - last_time_before).total_seconds()

    y_pred = []
    for t in df_gap_true['msrmt_dt']:
        elapsed_seconds = (t - last_time_before).total_seconds()
        ratio = elapsed_seconds / total_seconds
        value = last_value_before + ratio * (first_value_after - last_value_before)
        y_pred.append(value)

    y_pred = np.array(y_pred)
    y_true = df_gap_true['wtrprsr'].values

    # 평가
    metrics = evaluation.calculate_metrics(y_true, y_pred)
    metrics['model'] = 'Linear'

    return metrics, y_pred


def run_experiment(gap_days):
    """
    특정 gap 길이에 대한 실험 실행

    Args:
        gap_days: Gap 길이 (일)

    Returns:
        results dict
    """
    print(f"\n{'='*70}")
    print(f"🧪 실험 시작: {gap_days}일 Gap")
    print(f"{'='*70}")

    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    df_0243 = data_loader.load_pressure_data("0243")

    # Gap 설정
    gap_start = "2025-05-19 13:40"
    gap_start_dt = pd.to_datetime(gap_start)
    gap_end_dt = gap_start_dt + timedelta(days=gap_days)
    gap_end = gap_end_dt.strftime("%Y-%m-%d %H:%M")

    print(f"\n🔧 Gap 생성 중...")
    print(f"  - 시작: {gap_start}")
    print(f"  - 종료: {gap_end}")
    print(f"  - 길이: {gap_days}일")

    df_train, df_gap_true, gap_mask = data_loader.create_artificial_gap(
        df_0243, gap_start, gap_end
    )

    # 결과 저장
    results = {
        'gap_days': gap_days,
        'gap_start': gap_start,
        'gap_end': gap_end,
        'gap_records': len(df_gap_true),
        'models': {}
    }

    # XGBoost 테스트
    print(f"\n{'─'*70}")
    xgb_metrics, xgb_pred = test_xgboost_interpolation(df_train, df_gap_true, gap_days)
    results['models']['xgboost'] = xgb_metrics
    print(f"  ✓ XGBoost R²: {xgb_metrics['r2']:.4f}, MAE: {xgb_metrics['mae']:.4f}")

    # Prophet 테스트
    print(f"{'─'*70}")
    prophet_metrics, prophet_pred, prophet_forecast = test_prophet_interpolation(df_train, df_gap_true, gap_days)
    results['models']['prophet'] = prophet_metrics
    print(f"  ✓ Prophet R²: {prophet_metrics['r2']:.4f}, MAE: {prophet_metrics['mae']:.4f}")

    # Linear 테스트
    print(f"{'─'*70}")
    linear_metrics, linear_pred = test_linear_interpolation(df_train, df_gap_true, gap_days)
    results['models']['linear'] = linear_metrics
    print(f"  ✓ Linear R²: {linear_metrics['r2']:.4f}, MAE: {linear_metrics['mae']:.4f}")

    # 시각화
    print(f"\n📈 시각화 생성 중...")
    figures_dir = script_dir / 'results' / 'figures'

    # Gap 기간 확대 플롯
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(df_gap_true['msrmt_dt'], df_gap_true['wtrprsr'],
            'o-', markersize=2, label='실제값', color='blue', alpha=0.7, linewidth=1)
    ax.plot(df_gap_true['msrmt_dt'], xgb_pred,
            'o-', markersize=2, label='XGBoost', color='red', alpha=0.7, linewidth=1)
    ax.plot(df_gap_true['msrmt_dt'], prophet_pred,
            'o-', markersize=2, label='Prophet', color='green', alpha=0.7, linewidth=1)
    ax.plot(df_gap_true['msrmt_dt'], linear_pred,
            'o-', markersize=2, label='Linear', color='orange', alpha=0.7, linewidth=1)

    ax.set_xlabel('날짜', fontsize=12)
    ax.set_ylabel('압력 (wtrprsr)', fontsize=12)
    ax.set_title(f'{gap_days}일 Gap 보간 비교', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(figures_dir / f'gap_{gap_days}days_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  ✓ 저장: gap_{gap_days}days_comparison.png")

    return results


def generate_individual_report(results, output_path):
    """개별 실험 보고서 생성"""

    gap_days = results['gap_days']

    # 모델별 성능
    xgb = results['models']['xgboost']
    prophet = results['models']['prophet']
    linear = results['models']['linear']

    # 최고 성능 모델
    models_list = [
        ('XGBoost', xgb['r2']),
        ('Prophet', prophet['r2']),
        ('Linear', linear['r2'])
    ]
    best_model = max(models_list, key=lambda x: x[1])[0]

    # 성공/실패 판정
    best_r2 = max(xgb['r2'], prophet['r2'], linear['r2'])
    if best_r2 > 0.7:
        verdict = "✅ 우수 (실무 사용 권장)"
        grade = "A"
    elif best_r2 > 0.5:
        verdict = "⚠️ 양호 (조건부 사용)"
        grade = "B"
    elif best_r2 > 0.3:
        verdict = "❌ 미흡 (신중 사용)"
        grade = "C"
    else:
        verdict = "❌ 실패 (사용 불가)"
        grade = "D"

    report = f"""# {gap_days}일 Gap 보간 실험 결과

**실험 일자**: {datetime.now().strftime('%Y-%m-%d')}
**Gap 기간**: {results['gap_start']} ~ {results['gap_end']}
**Gap 길이**: {gap_days}일 ({results['gap_records']:,} records)

---

## 📊 성능 요약

### 최종 판정: {verdict}

### 모델별 성능

| 모델 | MAE | MAPE | R² | 등급 |
|------|-----|------|----|------|
| **XGBoost** | {xgb['mae']:.4f} | {xgb['mape']:.2f}% | **{xgb['r2']:.4f}** | {evaluation.grade_performance(xgb)} |
| **Prophet** | {prophet['mae']:.4f} | {prophet['mape']:.2f}% | **{prophet['r2']:.4f}** | {evaluation.grade_performance(prophet)} |
| **Linear** | {linear['mae']:.4f} | {linear['mape']:.2f}% | **{linear['r2']:.4f}** | {evaluation.grade_performance(linear)} |

**최고 성능**: {best_model} (R² {best_r2:.4f})

---

## 📈 시각화

![{gap_days}일 Gap 비교](figures/gap_{gap_days}days_comparison.png)

---

## 🔍 분석

### R² 기준 평가
- **R² > 0.7**: 우수 (실무 사용 권장)
- **R² > 0.5**: 양호 (조건부 사용 가능)
- **R² > 0.3**: 미흡 (신중 사용)
- **R² < 0.3**: 실패 (사용 불가)

### {gap_days}일 Gap 결과
- 최고 R²: {best_r2:.4f} → **등급 {grade}**
- {verdict}

---

**보고서 생성**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"  ✓ 보고서 저장: {output_path.name}")


def main():
    """메인 실행 함수"""

    print("="*70)
    print("🔬 Gap 기간별 보간 성능 실험")
    print("="*70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 실험 설정
    gap_lengths = [3, 7, 14]  # 24일은 이미 완료

    # 결과 디렉토리
    results_dir = script_dir / 'results'
    results_dir.mkdir(exist_ok=True)
    (results_dir / 'figures').mkdir(exist_ok=True)

    # 전체 결과
    all_results = []

    # 각 gap 길이별 실험
    for gap_days in gap_lengths:
        results = run_experiment(gap_days)
        all_results.append(results)

        # 개별 보고서 생성
        report_path = results_dir / f'gap_{gap_days}days_report.md'
        generate_individual_report(results, report_path)

    # JSON 저장
    with open(results_dir / 'all_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print("✅ 모든 실험 완료!")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # 요약 출력
    print("\n📊 실험 결과 요약:")
    print(f"\n{'Gap 길이':<10} {'XGBoost R²':<15} {'Prophet R²':<15} {'Linear R²':<15} {'최고 성능'}")
    print("─" * 70)

    for result in all_results:
        gap_days = result['gap_days']
        xgb_r2 = result['models']['xgboost']['r2']
        prophet_r2 = result['models']['prophet']['r2']
        linear_r2 = result['models']['linear']['r2']

        best_r2 = max(xgb_r2, prophet_r2, linear_r2)
        if best_r2 == xgb_r2:
            best = "XGBoost"
        elif best_r2 == prophet_r2:
            best = "Prophet"
        else:
            best = "Linear"

        status = "✅" if best_r2 > 0.5 else "❌"

        print(f"{gap_days}일{'':<7} {xgb_r2:>10.4f}{'':>5} {prophet_r2:>10.4f}{'':>5} {linear_r2:>10.4f}{'':>5} {best} {status}")

    print(f"\n다음 단계: results/COMPARISON_REPORT.md 확인")


if __name__ == "__main__":
    main()
