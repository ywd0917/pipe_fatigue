#!/usr/bin/env python3
"""
Step by step feature creation debugging
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

from common import config
import utils.feature_engineering as fe

# Load data
cfg = config.ProjectConfig()

df_0243 = pd.read_csv(cfg.SMALL_AREA_0243_PRESSURE_DATA_PATH)
df_0461 = pd.read_csv(cfg.SMALL_AREA_0461_PRESSURE_DATA_PATH)

df_0243['msrmt_dt'] = pd.to_datetime(df_0243['msrmt_dt'])
df_0461['msrmt_dt'] = pd.to_datetime(df_0461['msrmt_dt'])

# Create gap
gap_start = pd.to_datetime("2025-05-19 13:40")
gap_end = pd.to_datetime("2025-06-12 14:40")
gap_mask = (df_0243['msrmt_dt'] >= gap_start) & (df_0243['msrmt_dt'] <= gap_end)
gap_indices = df_0243[gap_mask].index.tolist()

df_0243_gap = df_0243.copy()
df_0243_gap.loc[gap_indices, 'wtrprsr'] = np.nan

print(f"Original df_0243_gap index: {df_0243_gap.index.min()} to {df_0243_gap.index.max()}")
print(f"Gap indices: {gap_indices[0]} to {gap_indices[-1]}")

# Step 1: Time features
print("\n=== Step 1: Time features ===")
df_step1 = fe.create_time_features(df_0243_gap, datetime_col='msrmt_dt')
print(f"After time features: shape={df_step1.shape}, index={df_step1.index.min()} to {df_step1.index.max()}")
print(f"Index type: {type(df_step1.index)}")
print(f"Gap index 201296 exists: {201296 in df_step1.index}")

# Step 2: Multi-sensor features
print("\n=== Step 2: Multi-sensor features ===")
df_others = {'0461': df_0461.set_index('msrmt_dt')[['wtrprsr']]}
df_step2 = fe.add_multi_sensor_features(df_step1, df_others, datetime_col='msrmt_dt', pressure_col='wtrprsr')
print(f"After multi-sensor: shape={df_step2.shape}, index={df_step2.index.min()} to {df_step2.index.max()}")
print(f"Index type: {type(df_step2.index)}")
print(f"Gap index 201296 exists: {201296 in df_step2.index}")
print(f"Columns: {df_step2.columns.tolist()}")
print(f"pressure_0461 NaN count: {df_step2['pressure_0461'].isna().sum()}")

# Step 3: Select features and dropna
print("\n=== Step 3: dropna on features ===")
feature_cols = [
    'hour', 'day_of_week', 'month', 'quarter', 'is_weekend',
    'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'month_sin', 'month_cos',
    'pressure_0461', 'pressure_other_mean', 'pressure_other_std',
    'pressure_other_max', 'pressure_other_min'
]

print(f"Feature cols: {feature_cols}")
df_features_only = df_step2[feature_cols]
print(f"Before dropna: shape={df_features_only.shape}")
print(f"NaN count per column:")
for col in feature_cols:
    nan_count = df_features_only[col].isna().sum()
    if nan_count > 0:
        print(f"  {col}: {nan_count}")

df_features_clean = df_features_only.dropna()
print(f"After dropna: shape={df_features_clean.shape}")
print(f"Index: {df_features_clean.index.min()} to {df_features_clean.index.max()}")
print(f"Gap index 201296 exists: {201296 in df_features_clean.index}")
