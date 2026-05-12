#!/usr/bin/env python3
"""
Test feature creation to debug the issue
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add paths
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(script_dir))

# Import utilities
import utils.feature_engineering as fe
from common import config

# Load data
cfg = config.ProjectConfig()

print("Loading data...")
df_0243 = pd.read_csv(cfg.SMALL_AREA_0243_PRESSURE_DATA_PATH)
df_0461 = pd.read_csv(cfg.SMALL_AREA_0461_PRESSURE_DATA_PATH)

df_0243['msrmt_dt'] = pd.to_datetime(df_0243['msrmt_dt'])
df_0461['msrmt_dt'] = pd.to_datetime(df_0461['msrmt_dt'])

print(f"0243 shape: {df_0243.shape}, missing: {df_0243['wtrprsr'].isna().sum()}")
print(f"0461 shape: {df_0461.shape}, missing: {df_0461['wtrprsr'].isna().sum()}")

# Create artificial gap
gap_start = pd.to_datetime("2025-05-19 13:40")
gap_end = pd.to_datetime("2025-06-12 14:40")

gap_mask = (df_0243['msrmt_dt'] >= gap_start) & (df_0243['msrmt_dt'] <= gap_end)
gap_indices = df_0243[gap_mask].index.tolist()
print(f"\nGap indices: {len(gap_indices)} records")

df_0243_gap = df_0243.copy()
df_0243_gap.loc[gap_indices, 'wtrprsr'] = np.nan
print(f"After creating gap, missing: {df_0243_gap['wtrprsr'].isna().sum()}")

# Align other sensor data
df_others = {
    '0461': df_0461.set_index('msrmt_dt')[['wtrprsr']],
}

print("\n=== Creating features ===")
X_full, y_full = fe.create_features(
    df_0243_gap,
    include_lags=False,
    include_rolling=False,
    include_multi_sensor=True,
    df_others=df_others,
    target_col='wtrprsr',
    datetime_col='msrmt_dt'
)

print(f"X_full shape: {X_full.shape}")
print(f"y_full shape: {y_full.shape}")
print(f"X_full index type: {type(X_full.index)}")
print(f"X_full index min/max: {X_full.index.min()} to {X_full.index.max()}")
print(f"y_full NaN count: {y_full.isna().sum()}")
print(f"y_full non-NaN count: {y_full.notna().sum()}")

# Check gap indices in X_full
print(f"\n=== Checking gap indices ===")
print(f"Original gap_indices[0]: {gap_indices[0]}")
print(f"Original gap_indices[-1]: {gap_indices[-1]}")
print(f"gap_indices type: {type(gap_indices)}")

# Try to find gap indices in X_full
gap_indices_in_X = [idx for idx in gap_indices if idx in X_full.index]
print(f"Gap indices found in X_full: {len(gap_indices_in_X)}")

# Check y_full values for gap
if gap_indices_in_X:
    print(f"Sample gap indices in X_full:")
    for idx in gap_indices_in_X[:5]:
        print(f"  idx={idx}, y_full={y_full.loc[idx]}")
