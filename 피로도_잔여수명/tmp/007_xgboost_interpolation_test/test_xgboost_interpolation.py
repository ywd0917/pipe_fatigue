#!/usr/bin/env python3
"""
Phase 1: Proof of Concept (POC) for XGBoost-based Pressure Interpolation

This script validates the core idea:
- Create artificial 24-day gap in 0243 area (which has no missing data)
- Train XGBoost using other sensors (0461, 0470, 0520) as features
- Predict the gap and compare with original data
- Evaluate performance using MAE, RMSE, MAPE, R²

Success Criteria:
- MAE < 0.2
- MAPE < 10%
- R² > 0.7
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Add paths
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(script_dir))

# Import utilities
import utils.feature_engineering as fe
import utils.model_training as mt
import utils.evaluation as ev

# Import common modules
from common import config


def load_pressure_data(area: str) -> pd.DataFrame:
    """
    Load pressure data for a specific area.

    Args:
        area: Area code (e.g., '0243')

    Returns:
        DataFrame with pressure data
    """
    # Get pressure file path from config
    cfg = config.ProjectConfig()

    pressure_paths = {
        '0243': cfg.SMALL_AREA_0243_PRESSURE_DATA_PATH,
        '0461': cfg.SMALL_AREA_0461_PRESSURE_DATA_PATH,
        '0470': cfg.SMALL_AREA_0470_PRESSURE_DATA_PATH,
        '0480': cfg.SMALL_AREA_0480_PRESSURE_DATA_PATH,
        '0490': cfg.SMALL_AREA_0490_PRESSURE_DATA_PATH,
    }

    if area not in pressure_paths:
        raise ValueError(f"Unknown area: {area}. Available: {list(pressure_paths.keys())}")

    file_path = pressure_paths[area]

    if not file_path.exists():
        raise FileNotFoundError(f"Pressure data not found: {file_path}")

    print(f"Loading {area} data from: {file_path.name}")

    df = pd.read_csv(file_path)

    # Parse datetime
    df['msrmt_dt'] = pd.to_datetime(df['msrmt_dt'])

    # Sort by time
    df = df.sort_values('msrmt_dt').reset_index(drop=True)

    print(f"  - Loaded {len(df):,} records")
    print(f"  - Date range: {df['msrmt_dt'].min()} to {df['msrmt_dt'].max()}")
    print(f"  - Missing count: {df['wtrprsr'].isna().sum()}")

    return df


def create_artificial_gap(df: pd.DataFrame,
                         gap_start: str = "2025-05-19 13:40",
                         gap_end: str = "2025-06-12 14:40") -> tuple:
    """
    Create artificial gap by removing data in specified period.

    Args:
        df: Original DataFrame
        gap_start: Gap start datetime string
        gap_end: Gap end datetime string

    Returns:
        Tuple of (df_with_gap, df_gap_true, gap_indices)
    """
    gap_start_dt = pd.to_datetime(gap_start)
    gap_end_dt = pd.to_datetime(gap_end)

    # Find gap indices
    gap_mask = (df['msrmt_dt'] >= gap_start_dt) & (df['msrmt_dt'] <= gap_end_dt)
    gap_indices = df[gap_mask].index.tolist()

    print(f"\nCreating artificial gap:")
    print(f"  - Start: {gap_start}")
    print(f"  - End: {gap_end}")
    print(f"  - Gap size: {len(gap_indices):,} records ({len(gap_indices)/288:.1f} days)")

    # Save gap data for comparison
    df_gap_true = df.loc[gap_indices].copy()

    # Create DataFrame with gap (set gap values to NaN)
    df_with_gap = df.copy()
    df_with_gap.loc[gap_indices, 'wtrprsr'] = np.nan

    return df_with_gap, df_gap_true, gap_indices


def main():
    """Main execution function."""
    print("=" * 80)
    print("Phase 1: XGBoost Interpolation - Proof of Concept")
    print("=" * 80)

    # Setup paths
    results_dir = Path(__file__).parent / "results"
    figures_dir = results_dir / "figures"
    metrics_dir = results_dir / "metrics"

    figures_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # ========================================
    # Step 1: Load Data
    # ========================================
    print("\n[Step 1] Loading pressure data...")

    # Target: 0243 (no missing data)
    df_0243 = load_pressure_data("0243")

    # Other sensors (to be used as features)
    # Use only sensors with full coverage for gap period (2025-05-19 ~ 2025-06-12)
    # 0461, 0470: available in config and have full coverage
    # 0520: not available in current config (skip for now)
    # 0480, 0490: excluded (have same 24-day gap)
    df_0461 = load_pressure_data("0461")
    df_0470 = load_pressure_data("0470")

    # ========================================
    # Step 2: Create Artificial Gap
    # ========================================
    print("\n[Step 2] Creating artificial gap...")

    df_0243_gap, df_gap_true, gap_indices = create_artificial_gap(
        df_0243,
        gap_start="2025-05-19 13:40",
        gap_end="2025-06-12 14:40"
    )

    # ========================================
    # Step 3: Feature Engineering
    # ========================================
    print("\n[Step 3] Feature engineering...")

    # Align other sensor data by datetime
    df_others = {
        '0461': df_0461.set_index('msrmt_dt')[['wtrprsr']],
        '0470': df_0470.set_index('msrmt_dt')[['wtrprsr']],
    }

    # Create features for full dataset
    print("  - Creating features (multi-sensor + time, NO lags for long gap scenario)...")
    X_full, y_full = fe.create_features(
        df_0243_gap,
        include_lags=False,  # NO lags - they cause data loss in 24-day gap
        include_rolling=False,  # Keep rolling OFF for simplicity
        include_multi_sensor=True,  # YES - KEY strategy (multi-sensor approach)
        df_others=df_others,
        target_col='wtrprsr',
        datetime_col='msrmt_dt'
    )

    print(f"  - Total features: {X_full.shape[1]}")
    print(f"  - Feature columns: {list(X_full.columns)}")

    # ========================================
    # Step 4: Split Train/Test
    # ========================================
    print("\n[Step 4] Splitting train/test...")

    # Train: all non-gap data
    train_mask = ~df_0243_gap.index.isin(gap_indices)
    train_indices = df_0243_gap[train_mask].index

    # Get valid indices that exist in X_full (after dropna in feature creation)
    valid_train_indices = train_indices.intersection(X_full.index)
    valid_gap_indices = pd.Index(gap_indices).intersection(X_full.index)

    X_train = X_full.loc[valid_train_indices]
    y_train = y_full.loc[valid_train_indices]

    X_gap = X_full.loc[valid_gap_indices]
    # Use original gap data (before setting to NaN) for evaluation
    y_gap_true_full = df_gap_true.set_index(df_gap_true.index)['wtrprsr']
    # Align with valid_gap_indices
    y_gap_true = y_gap_true_full.loc[y_gap_true_full.index.isin(valid_gap_indices)]

    print(f"  - Train size: {len(X_train):,} records")
    print(f"  - Gap size: {len(X_gap):,} records")
    print(f"  - True gap values available: {len(y_gap_true):,} records")

    # ========================================
    # Step 5: Train XGBoost
    # ========================================
    print("\n[Step 5] Training XGBoost model...")

    model = mt.train_xgboost(X_train, y_train, verbose=False)

    print("  - Training completed")
    print(f"  - Best iteration: {model.best_iteration if hasattr(model, 'best_iteration') else 'N/A'}")

    # Feature importance
    feature_importance = mt.get_feature_importance(model, list(X_train.columns))
    print("\n  Top 10 important features:")
    for idx, row in feature_importance.head(10).iterrows():
        print(f"    {row['feature']:30s}: {row['importance']:.4f}")

    # ========================================
    # Step 6: Predict Gap
    # ========================================
    print("\n[Step 6] Predicting gap values...")

    y_gap_pred = mt.predict_xgboost(model, X_gap)

    print(f"  - Predicted {len(y_gap_pred):,} values")
    print(f"  - Prediction range: [{y_gap_pred.min():.3f}, {y_gap_pred.max():.3f}]")
    print(f"  - True range: [{y_gap_true.min():.3f}, {y_gap_true.max():.3f}]")

    # ========================================
    # Step 7: Evaluate Performance
    # ========================================
    print("\n[Step 7] Evaluating performance...")

    metrics = ev.evaluate(y_gap_true.values, y_gap_pred)

    print("\n  Performance Metrics:")
    print(f"    MAE:  {metrics['mae']:.4f}  (threshold: < 0.2)")
    print(f"    RMSE: {metrics['rmse']:.4f}  (threshold: < 0.3)")
    print(f"    MAPE: {metrics['mape']:.2f}%  (threshold: < 10%)")
    print(f"    R²:   {metrics['r2']:.4f}  (threshold: > 0.7)")

    # Check criteria
    criteria = ev.check_criteria(
        metrics,
        mae_threshold=0.2,
        mape_threshold=10.0,
        r2_threshold=0.7
    )

    print("\n  Criteria Check:")
    for key, passed in criteria.items():
        if key == 'all_pass':
            continue
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {key}: {status}")

    grade = ev.get_performance_grade(metrics['mae'], metrics['mape'], metrics['r2'])
    print(f"\n  **Performance Grade: {grade}**")

    # ========================================
    # Step 8: Visualization
    # ========================================
    print("\n[Step 8] Generating visualizations...")

    # Reconstruct full prediction array for plotting
    y_pred_full = df_0243['wtrprsr'].copy()
    # Use loc to avoid indexing issues
    for idx in valid_gap_indices:
        idx_pos = list(valid_gap_indices).index(idx)
        y_pred_full.iloc[idx] = y_gap_pred[idx_pos]

    ev.plot_comparison(
        y_true=df_0243['wtrprsr'],
        y_pred=y_pred_full,
        timestamps=df_0243['msrmt_dt'],
        gap_start=gap_indices[0],
        gap_end=gap_indices[-1],
        title="Phase 1 POC: Original vs XGBoost Predicted (0243 Area)",
        save_path=figures_dir / "phase1_poc_comparison.png",
        show=False
    )

    # ========================================
    # Step 9: Generate Report
    # ========================================
    print("\n[Step 9] Generating report...")

    report = ev.generate_report(
        metrics=metrics,
        criteria=criteria,
        method_name="XGBoost (Multi-Sensor)",
        save_path=results_dir / "phase1_poc_report.md"
    )

    # Save metrics as JSON
    # Convert numpy bool to Python bool for JSON serialization
    criteria_serializable = {k: bool(v) for k, v in criteria.items()}

    metrics_data = {
        'metrics': metrics,
        'criteria': criteria_serializable,
        'grade': grade,
        'feature_count': int(X_full.shape[1]),
        'train_size': int(len(X_train)),
        'gap_size': int(len(X_gap)),
        'feature_importance': feature_importance.head(10).to_dict('records'),
        'timestamp': datetime.now().isoformat()
    }

    with open(metrics_dir / "phase1_metrics.json", 'w') as f:
        json.dump(metrics_data, f, indent=2)

    # ========================================
    # Step 10: Final Decision
    # ========================================
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)

    if criteria['all_pass']:
        print("✅ **PHASE 1 PASSED**")
        print("\nConclusion:")
        print("  - XGBoost with multi-sensor features can successfully interpolate")
        print("    24-day gaps with acceptable accuracy")
        print("  - MAE, MAPE, and R² all meet the success criteria")
        print("  - Proceed to Phase 2 (real gap interpolation)")
    else:
        print("❌ **PHASE 1 FAILED**")
        print("\nConclusion:")
        print("  - XGBoost did not meet one or more success criteria")
        print("  - Consider:")
        print("    1. Adjusting hyperparameters")
        print("    2. Adding more features (lag, rolling)")
        print("    3. Using alternative methods (SARIMA, Prophet)")

    print("\nResults saved to:")
    print(f"  - Report: {results_dir / 'phase1_poc_report.md'}")
    print(f"  - Metrics: {metrics_dir / 'phase1_metrics.json'}")
    print(f"  - Figure: {figures_dir / 'phase1_poc_comparison.png'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
