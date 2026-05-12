#!/usr/bin/env python3
"""
Debug script to identify feature creation issue
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

from common import config

# Load data
cfg = config.ProjectConfig()

print("Loading data...")
df_0243 = pd.read_csv(cfg.SMALL_AREA_0243_PRESSURE_DATA_PATH)
df_0461 = pd.read_csv(cfg.SMALL_AREA_0461_PRESSURE_DATA_PATH)

df_0243['msrmt_dt'] = pd.to_datetime(df_0243['msrmt_dt'])
df_0461['msrmt_dt'] = pd.to_datetime(df_0461['msrmt_dt'])

print(f"0243 shape: {df_0243.shape}")
print(f"0461 shape: {df_0461.shape}")
print(f"0243 date range: {df_0243['msrmt_dt'].min()} to {df_0243['msrmt_dt'].max()}")
print(f"0461 date range: {df_0461['msrmt_dt'].min()} to {df_0461['msrmt_dt'].max()}")
print(f"0243 missing: {df_0243['wtrprsr'].isna().sum()}")
print(f"0461 missing: {df_0461['wtrprsr'].isna().sum()}")

# Create artificial gap
gap_start = pd.to_datetime("2025-05-19 13:40")
gap_end = pd.to_datetime("2025-06-12 14:40")

gap_mask = (df_0243['msrmt_dt'] >= gap_start) & (df_0243['msrmt_dt'] <= gap_end)
gap_indices = df_0243[gap_mask].index.tolist()
print(f"\nGap indices: {len(gap_indices)} records")

df_0243_gap = df_0243.copy()
df_0243_gap.loc[gap_indices, 'wtrprsr'] = np.nan

# Test feature creation step by step
print("\n=== Testing feature creation ===")

# Step 1: Time features
df_test = df_0243_gap.copy()
df_test['hour'] = df_test['msrmt_dt'].dt.hour
df_test['day_of_week'] = df_test['msrmt_dt'].dt.dayofweek
print(f"After time features: {df_test.shape}")
print(f"Non-null rows: {df_test[['hour', 'day_of_week']].notna().all(axis=1).sum()}")

# Step 2: Set index
df_test = df_test.set_index('msrmt_dt')
print(f"After set_index: {df_test.shape}")

# Step 3: Join with other sensor
df_0461_indexed = df_0461.set_index('msrmt_dt')[['wtrprsr']]
print(f"\n0461 indexed shape: {df_0461_indexed.shape}")
print(f"0461 index range: {df_0461_indexed.index.min()} to {df_0461_indexed.index.max()}")

df_joined = df_test.join(df_0461_indexed.rename(columns={'wtrprsr': 'pressure_0461'}), how='left')
print(f"After join: {df_joined.shape}")
print(f"pressure_0461 non-null: {df_joined['pressure_0461'].notna().sum()}")
print(f"pressure_0461 null: {df_joined['pressure_0461'].isna().sum()}")

# Check if indices match
common_idx = df_test.index.intersection(df_0461_indexed.index)
print(f"\nCommon indices: {len(common_idx)}")
print(f"0243 unique indices: {len(df_test.index.unique())}")
print(f"0461 unique indices: {len(df_0461_indexed.index.unique())}")

# Sample check
print("\nSample of joined data:")
print(df_joined[['wtrprsr', 'pressure_0461', 'hour']].head(20))
print("\nSample with nulls:")
print(df_joined[df_joined['pressure_0461'].isna()][['wtrprsr', 'pressure_0461']].head(10))
