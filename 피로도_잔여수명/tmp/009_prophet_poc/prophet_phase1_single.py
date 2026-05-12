#!/usr/bin/env python3
"""
Phase 1: Prophet Single-Sensor Interpolation POC

This script validates Prophet's ability to interpolate 24-day gap:
- Create artificial 24-day gap in 0243 area (which has no missing data)
- Train Prophet using only time-based features (no other sensors)
- Predict the gap and compare with original data
- Evaluate performance using MAE, RMSE, MAPE, R², Coverage

Success Criteria:
- R² > 0.5 (XGBoost failed with -0.04)
- MAPE < 10%
- Visual quality: natural connection, preserved periodicity
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Add paths
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import utilities
from utils import data_loader, evaluation, visualization

# Prophet
try:
    from prophet import Prophet
except ImportError:
    print("❌ Prophet not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "prophet"])
    from prophet import Prophet


def main():
    """Main execution function"""

    print("="*70)
    print("🔮 PROPHET PHASE 1: Single-Sensor Interpolation POC")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Configuration
    TARGET_AREA = '0243'
    GAP_START = "2025-05-19 13:40"
    GAP_END = "2025-06-12 14:40"

    results_dir = script_dir / 'results'
    figures_dir = results_dir / 'figures'
    metrics_dir = results_dir / 'metrics'

    # ========================================================================
    # 1. Load Data
    # ========================================================================
    print("\n📂 Step 1: Load Pressure Data")
    print("-" * 70)

    df_0243 = data_loader.load_pressure_data(TARGET_AREA)

    # ========================================================================
    # 2. Create Artificial Gap
    # ========================================================================
    print("\n🔧 Step 2: Create Artificial Gap")
    print("-" * 70)

    df_train, df_gap_true, gap_mask = data_loader.create_artificial_gap(
        df_0243,
        gap_start=GAP_START,
        gap_end=GAP_END
    )

    # ========================================================================
    # 3. Prepare Prophet Format
    # ========================================================================
    print("\n🔄 Step 3: Convert to Prophet Format")
    print("-" * 70)

    # Prophet requires 'ds' (datestamp) and 'y' (value) columns
    df_prophet_train = pd.DataFrame({
        'ds': df_train['msrmt_dt'],
        'y': df_train['wtrprsr']
    })

    print(f"  ✓ Prophet training data shape: {df_prophet_train.shape}")
    print(f"  ✓ Date range: {df_prophet_train['ds'].min()} to {df_prophet_train['ds'].max()}")
    print(f"  ✓ Value range: {df_prophet_train['y'].min():.4f} to {df_prophet_train['y'].max():.4f}")

    # ========================================================================
    # 4. Train Prophet Model
    # ========================================================================
    print("\n🤖 Step 4: Train Prophet Model")
    print("-" * 70)

    print("  ⚙️ Model configuration:")
    print("    - Daily seasonality: True")
    print("    - Weekly seasonality: True")
    print("    - Yearly seasonality: False")
    print("    - Interval width: 95%")
    print("    - Custom seasonality: 5-minute (Fourier order 10)")

    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.05,  # Default
        seasonality_prior_scale=10.0,   # Default
    )

    # Add custom 5-minute seasonality
    # (Prophet default daily seasonality is for hourly data)
    model.add_seasonality(
        name='intraday_5min',
        period=1,  # 1 day
        fourier_order=10  # Captures high-frequency patterns
    )

    print("\n  🏋️ Training...")
    model.fit(df_prophet_train)
    print("  ✓ Training complete!")

    # ========================================================================
    # 5. Make Predictions
    # ========================================================================
    print("\n🔮 Step 5: Predict Gap Period")
    print("-" * 70)

    # Create future dataframe for gap period
    future_gap = pd.DataFrame({
        'ds': df_gap_true['msrmt_dt']
    })

    print(f"  ✓ Predicting {len(future_gap):,} time points...")
    forecast = model.predict(future_gap)
    print(f"  ✓ Forecast complete!")

    # Extract predictions
    y_pred = forecast['yhat'].values
    yhat_lower = forecast['yhat_lower'].values
    yhat_upper = forecast['yhat_upper'].values

    # ========================================================================
    # 6. Evaluate Performance
    # ========================================================================
    print("\n📊 Step 6: Evaluate Performance")
    print("-" * 70)

    y_true = df_gap_true['wtrprsr'].values

    metrics = evaluation.calculate_metrics(
        y_true, y_pred,
        yhat_lower, yhat_upper
    )

    grade = evaluation.grade_performance(metrics)

    evaluation.print_metrics(metrics, grade)

    # ========================================================================
    # 7. Check Pass Criteria
    # ========================================================================
    print("\n✅ Step 7: Check Pass Criteria")
    print("-" * 70)

    passed, reasons = evaluation.check_pass_criteria(metrics)

    for reason in reasons:
        print(f"  {reason}")

    print("\n" + "="*70)
    if passed:
        print("🎉 PHASE 1 PASSED! Prophet achieves R² > 0.5 AND MAPE < 10%")
        print("   → Proceed to Phase 2/3")
    else:
        print("⚠️ PHASE 1 FAILED. Review results and consider alternatives.")
        print("   → May need to adjust approach or accept 24-day gap as too long")
    print("="*70)

    # ========================================================================
    # 8. Visualizations
    # ========================================================================
    print("\n📈 Step 8: Generate Visualizations")
    print("-" * 70)

    # Full view
    print("  📊 Plotting full forecast...")
    visualization.plot_forecast_with_gap(
        df_0243, df_gap_true, forecast,
        GAP_START, GAP_END,
        save_path=figures_dir / 'prophet_phase1_forecast.png'
    )

    # Zoom view
    print("  🔍 Plotting gap zoom...")
    visualization.plot_gap_zoom(
        df_gap_true, forecast,
        GAP_START, GAP_END,
        save_path=figures_dir / 'prophet_phase1_gap_zoom.png'
    )

    # Residuals
    print("  📉 Plotting residual analysis...")
    visualization.plot_residuals(
        df_gap_true, forecast,
        save_path=figures_dir / 'prophet_phase1_residuals.png'
    )

    # Prophet components
    print("  🧩 Plotting Prophet components...")
    from prophet.plot import plot_components_plotly
    fig_components = model.plot_components(forecast)
    fig_components.savefig(
        figures_dir / 'prophet_phase1_components.png',
        dpi=150,
        bbox_inches='tight'
    )
    print(f"  ✓ Saved: {figures_dir / 'prophet_phase1_components.png'}")

    # ========================================================================
    # 9. Save Metrics
    # ========================================================================
    print("\n💾 Step 9: Save Metrics")
    print("-" * 70)

    metrics_output = {
        'config': {
            'target_area': TARGET_AREA,
            'gap_start': GAP_START,
            'gap_end': GAP_END,
            'gap_duration_days': (pd.to_datetime(GAP_END) - pd.to_datetime(GAP_START)).days,
            'gap_records': len(df_gap_true),
        },
        'metrics': {
            'mae': float(metrics['mae']),
            'rmse': float(metrics['rmse']),
            'mape': float(metrics['mape']),
            'r2': float(metrics['r2']),
            'coverage': float(metrics['coverage']),
        },
        'grade': grade,
        'passed': passed,
        'timestamp': datetime.now().isoformat(),
    }

    metrics_file = metrics_dir / 'phase1_metrics.json'
    with open(metrics_file, 'w') as f:
        json.dump(metrics_output, f, indent=2)

    print(f"  ✓ Saved: {metrics_file}")

    # ========================================================================
    # 10. Generate Report
    # ========================================================================
    print("\n📝 Step 10: Generate Report")
    print("-" * 70)

    report_path = results_dir / 'phase1_report.md'
    generate_report(metrics_output, report_path)
    print(f"  ✓ Saved: {report_path}")

    print("\n" + "="*70)
    print(f"✅ PHASE 1 COMPLETE at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    return metrics_output


def generate_report(metrics_output: dict, report_path: Path):
    """Generate markdown report"""

    config = metrics_output['config']
    metrics = metrics_output['metrics']
    grade = metrics_output['grade']
    passed = metrics_output['passed']

    grade_desc = {
        'A': '우수 (실무 사용 권장)',
        'B': '양호 (조건부 사용)',
        'C': '보통 (신중 사용)',
        'D': '불합격 (사용 불가)'
    }

    report = f"""# Phase 1: Prophet Single-Sensor Interpolation Results

**Test Date**: {metrics_output['timestamp'][:10]}
**Target Area**: {config['target_area']}
**Gap Period**: {config['gap_start']} ~ {config['gap_end']} ({config['gap_duration_days']} days)

---

## 📊 Executive Summary

### Performance Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| **MAE** | {metrics['mae']:.4f} | < 0.15 | {'✅ PASS' if metrics['mae'] < 0.15 else '❌ FAIL'} |
| **MAPE** | {metrics['mape']:.2f}% | < 10% | {'✅ PASS' if metrics['mape'] < 10 else '❌ FAIL'} |
| **R²** | {metrics['r2']:.4f} | > 0.5 | {'✅ PASS' if metrics['r2'] > 0.5 else '❌ FAIL'} |
| **RMSE** | {metrics['rmse']:.4f} | - | - |
| **Coverage** | {metrics['coverage']:.2%} | > 80% | {'✅ PASS' if metrics['coverage'] > 0.8 else '❌ FAIL'} |

### Grade: {grade} - {grade_desc.get(grade, '')}

### Final Verdict: {'✅ PASSED' if passed else '❌ FAILED'}

---

## 🔧 Experiment Setup

### Prophet Configuration
- **Daily seasonality**: True
- **Weekly seasonality**: True
- **Yearly seasonality**: False
- **Custom seasonality**: 5-minute intraday (Fourier order 10)
- **Interval width**: 95%
- **Changepoint prior scale**: 0.05 (default)
- **Seasonality prior scale**: 10.0 (default)

### Data
- **Training records**: {config['gap_records']:,} records excluded from gap
- **Gap records**: {config['gap_records']:,} records (for evaluation)
- **Gap duration**: {config['gap_duration_days']} days

---

## 📈 Visualizations

### Full Forecast View
![Full Forecast](figures/prophet_phase1_forecast.png)

### Gap Period Zoom
![Gap Zoom](figures/prophet_phase1_gap_zoom.png)

### Prophet Components
![Components](figures/prophet_phase1_components.png)

### Residual Analysis
![Residuals](figures/prophet_phase1_residuals.png)

---

## 🔍 Analysis

### What Prophet Captures
- **Trend**: {'Strong' if metrics['r2'] > 0.7 else 'Moderate' if metrics['r2'] > 0.5 else 'Weak'} long-term trend
- **Daily seasonality**: {'Detected' if metrics['r2'] > 0.5 else 'Limited'}
- **Weekly seasonality**: {'Detected' if metrics['r2'] > 0.5 else 'Limited'}

### Comparison with XGBoost Phase 1

| Metric | XGBoost | Prophet | Winner |
|--------|---------|---------|--------|
| MAE | 0.0595 | {metrics['mae']:.4f} | {'Prophet' if metrics['mae'] < 0.0595 else 'XGBoost'} |
| MAPE | 3.20% | {metrics['mape']:.2f}% | {'Prophet' if metrics['mape'] < 3.20 else 'XGBoost'} |
| **R²** | **-0.0400** ❌ | **{metrics['r2']:.4f}** {'✅' if metrics['r2'] > 0 else '❌'} | **{'Prophet' if metrics['r2'] > -0.04 else 'XGBoost'}** |

**Key Insight**: Prophet {'successfully captures variance' if metrics['r2'] > 0.5 else 'shows improved variance capture compared to XGBoost'}, while XGBoost predicted nearly constant values.

---

## 🎯 Conclusion

"""

    if passed:
        report += f"""
✅ **Phase 1 PASSED**

Prophet achieves:
- R² = {metrics['r2']:.4f} (> 0.5 ✅)
- MAPE = {metrics['mape']:.2f}% (< 10% ✅)
- Coverage = {metrics['coverage']:.2%} (> 80% ✅)

**Recommendation**:
- ✅ Proceed to Phase 2 (multi-sensor exogenous regressors)
- ✅ Proceed to Phase 3 (real 0480/0490 interpolation)
- ✅ Consider Prophet as primary method for main41

Prophet demonstrates superior variance explanation compared to XGBoost, validating the data analysis (008) recommendation.
"""
    else:
        report += f"""
⚠️ **Phase 1 FAILED**

Prophet achieves:
- R² = {metrics['r2']:.4f} ({'< 0.5 ❌' if metrics['r2'] <= 0.5 else '> 0.5 ✅'})
- MAPE = {metrics['mape']:.2f}% ({'> 10% ❌' if metrics['mape'] >= 10 else '< 10% ✅'})
- Coverage = {metrics['coverage']:.2%}

**Possible Reasons**:
- 24-day gap is fundamentally too long for interpolation
- Data characteristics (weak temporal patterns, ACF 0.145) limit all methods
- Sensors are too independent (correlation 0.039)

**Recommendations**:
- 🔄 Try shorter gap periods (3-7-14 days) to find feasible limit
- 🔄 Accept gap as uninterpolatable → exclude from analysis
- 🔄 Focus on gap prevention (sensor redundancy)
"""

    report += f"""

---

**Report generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)


if __name__ == "__main__":
    metrics_output = main()
