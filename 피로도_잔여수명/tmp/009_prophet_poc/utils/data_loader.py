#!/usr/bin/env python3
"""
Data loading utilities for Prophet POC
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from common import config


def load_pressure_data(area: str) -> pd.DataFrame:
    """
    Load pressure data for a specific area.

    Args:
        area: Area code (e.g., '0243', '0461', '0470', '0480', '0490')

    Returns:
        DataFrame with columns: msrmt_dt, wtrprsr
    """
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

    print(f"📂 Loading {area} data from: {file_path.name}")

    df = pd.read_csv(file_path)

    # Parse datetime
    df['msrmt_dt'] = pd.to_datetime(df['msrmt_dt'])

    # Sort by time
    df = df.sort_values('msrmt_dt').reset_index(drop=True)

    print(f"  ✓ Loaded {len(df):,} records")
    print(f"  ✓ Date range: {df['msrmt_dt'].min()} to {df['msrmt_dt'].max()}")
    print(f"  ✓ Missing count: {df['wtrprsr'].isna().sum()}")

    return df


def create_artificial_gap(df: pd.DataFrame,
                         gap_start: str = "2025-05-19 13:40",
                         gap_end: str = "2025-06-12 14:40") -> tuple:
    """
    Create artificial gap by splitting data into train and test sets.

    Args:
        df: Original DataFrame with 'msrmt_dt' and 'wtrprsr' columns
        gap_start: Gap start datetime string (YYYY-MM-DD HH:MM)
        gap_end: Gap end datetime string (YYYY-MM-DD HH:MM)

    Returns:
        Tuple of (df_train, df_gap_true, gap_mask)
        - df_train: Training data (excludes gap period)
        - df_gap_true: True values in gap period (for evaluation)
        - gap_mask: Boolean mask indicating gap indices in original df
    """
    gap_start_dt = pd.to_datetime(gap_start)
    gap_end_dt = pd.to_datetime(gap_end)

    print(f"\n🔧 Creating artificial gap:")
    print(f"  - Gap start: {gap_start_dt}")
    print(f"  - Gap end: {gap_end_dt}")
    print(f"  - Gap duration: {(gap_end_dt - gap_start_dt).days} days")

    # Create gap mask
    gap_mask = (df['msrmt_dt'] >= gap_start_dt) & (df['msrmt_dt'] <= gap_end_dt)

    # Training data (excludes gap)
    df_train = df[~gap_mask].copy()

    # True values in gap (for evaluation)
    df_gap_true = df[gap_mask].copy()

    print(f"  ✓ Training data: {len(df_train):,} records")
    print(f"  ✓ Gap data: {len(df_gap_true):,} records")
    print(f"  ✓ Gap ratio: {len(df_gap_true) / len(df) * 100:.2f}%")

    return df_train, df_gap_true, gap_mask
