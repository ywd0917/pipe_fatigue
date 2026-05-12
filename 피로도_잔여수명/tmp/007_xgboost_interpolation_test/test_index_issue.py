#!/usr/bin/env python3
"""
Test to identify index issue
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

df_0243 = pd.read_csv(cfg.SMALL_AREA_0243_PRESSURE_DATA_PATH)
df_0461 = pd.read_csv(cfg.SMALL_AREA_0461_PRESSURE_DATA_PATH)

df_0243['msrmt_dt'] = pd.to_datetime(df_0243['msrmt_dt'])
df_0461['msrmt_dt'] = pd.to_datetime(df_0461['msrmt_dt'])

print("Original df_0243 index:")
print(f"  Type: {type(df_0243.index)}")
print(f"  Range: {df_0243.index.min()} to {df_0243.index.max()}")
print(f"  First 5: {df_0243.index[:5].tolist()}")

# Create time features
df = df_0243.copy()
df['hour'] = df['msrmt_dt'].dt.hour

print("\nAfter adding time features:")
print(f"  Type: {type(df.index)}")
print(f"  Range: {df.index.min()} to {df.index.max()}")
print(f"  First 5: {df.index[:5].tolist()}")

# Set index to datetime
df_indexed = df.set_index('msrmt_dt')

print("\nAfter set_index('msrmt_dt'):")
print(f"  Type: {type(df_indexed.index)}")
print(f"  Index name: {df_indexed.index.name}")
print(f"  First 5 index: {df_indexed.index[:5].tolist()}")

# Reset index
df_reset = df_indexed.reset_index()

print("\nAfter reset_index():")
print(f"  Type: {type(df_reset.index)}")
print(f"  Range: {df_reset.index.min()} to {df_reset.index.max()}")
print(f"  First 5: {df_reset.index[:5].tolist()}")
print(f"  Columns: {df_reset.columns.tolist()}")

# The problem: original index (0, 1, 2, ..., 231371) is LOST after set_index + reset_index
# It gets replaced with a NEW RangeIndex(0, 231372)

print("\n=== THE PROBLEM ===")
print(f"Original gap index: 201296 (for example)")
print(f"After reset_index, index 201296 still exists: {201296 in df_reset.index}")
print(f"But it doesn't correspond to the SAME ROW anymore!")

# Solution: preserve original index
print("\n=== SOLUTION ===")
df_preserved = df.copy()
df_preserved['_original_index'] = df_preserved.index  # Save original index

# Work with datetime index
df_preserved = df_preserved.set_index('msrmt_dt')

# Join
df_0461_indexed = df_0461.set_index('msrmt_dt')[['wtrprsr']]
df_joined = df_preserved.join(df_0461_indexed.rename(columns={'wtrprsr': 'pressure_0461'}), how='left')

# Reset index and restore original
df_joined = df_joined.reset_index()
df_joined = df_joined.set_index('_original_index')
df_joined.index.name = None  # Remove index name

print(f"After preserving original index:")
print(f"  Type: {type(df_joined.index)}")
print(f"  Range: {df_joined.index.min()} to {df_joined.index.max()}")
print(f"  Index 201296 exists: {201296 in df_joined.index}")
print(f"  First 5: {df_joined.index[:5].tolist()}")
