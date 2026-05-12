"""
Feature Engineering for XGBoost-based Pressure Interpolation

This module provides feature creation functions for time series pressure data,
including time-based features, lag features, rolling statistics, and multi-sensor features.
"""

from typing import Tuple, List, Optional
import pandas as pd
import numpy as np


def create_time_features(df: pd.DataFrame, datetime_col: str = 'msrmt_dt') -> pd.DataFrame:
    """
    Create time-based features from datetime column.

    Args:
        df: DataFrame with datetime column
        datetime_col: Name of datetime column

    Returns:
        DataFrame with added time features
    """
    df = df.copy()

    # Ensure datetime type
    if not pd.api.types.is_datetime64_any_dtype(df[datetime_col]):
        df[datetime_col] = pd.to_datetime(df[datetime_col])

    # Basic time features
    df['hour'] = df[datetime_col].dt.hour
    df['minute'] = df[datetime_col].dt.minute
    df['day_of_week'] = df[datetime_col].dt.dayofweek
    df['day_of_month'] = df[datetime_col].dt.day
    df['month'] = df[datetime_col].dt.month
    df['quarter'] = df[datetime_col].dt.quarter
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    # Cyclical encoding (preserves continuity: 23h -> 0h)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * (df['month'] - 1) / 12)
    df['month_cos'] = np.cos(2 * np.pi * (df['month'] - 1) / 12)

    return df


def create_lag_features(df: pd.DataFrame,
                       target_col: str = 'wtrprsr',
                       lags: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Create lag features (previous timestep values).

    WARNING: For long-term gaps (>24 days), lag features will be missing
    in the gap region, leading to recursive prediction errors.

    Args:
        df: DataFrame with target column
        target_col: Name of target column
        lags: List of lag periods. Default: [1, 2, 3, 12, 24, 144, 288]
              (5min, 10min, 15min, 1h, 2h, 12h, 24h for 5-minute interval data)

    Returns:
        DataFrame with added lag features
    """
    df = df.copy()

    if lags is None:
        # Default lags for 5-minute interval data
        lags = [1, 2, 3, 12, 24, 144, 288]

    for lag in lags:
        df[f'lag_{lag}'] = df[target_col].shift(lag)

    return df


def create_rolling_features(df: pd.DataFrame,
                           target_col: str = 'wtrprsr',
                           windows: Optional[List[int]] = None) -> pd.DataFrame:
    """
    Create rolling statistics features.

    Args:
        df: DataFrame with target column
        target_col: Name of target column
        windows: List of window sizes. Default: [12, 36, 144, 288]
                (1h, 3h, 12h, 24h for 5-minute interval data)

    Returns:
        DataFrame with added rolling features
    """
    df = df.copy()

    if windows is None:
        windows = [12, 36, 144, 288]

    for window in windows:
        df[f'rolling_mean_{window}'] = df[target_col].rolling(window).mean()
        df[f'rolling_std_{window}'] = df[target_col].rolling(window).std()
        df[f'rolling_max_{window}'] = df[target_col].rolling(window).max()
        df[f'rolling_min_{window}'] = df[target_col].rolling(window).min()

    return df


def add_multi_sensor_features(df_target: pd.DataFrame,
                              df_others: dict,
                              datetime_col: str = 'msrmt_dt',
                              pressure_col: str = 'wtrprsr') -> pd.DataFrame:
    """
    Add pressure values from other sensors as features.

    This is the KEY STRATEGY for solving the lag feature problem in long-term gaps.
    Other sensor data is always available even during the target sensor's gap period.

    Args:
        df_target: Target sensor DataFrame
        df_others: Dict of {area_name: DataFrame} for other sensors
                  e.g., {'0243': df_0243, '0461': df_0461, ...}
        datetime_col: Name of datetime column
        pressure_col: Name of pressure column

    Returns:
        DataFrame with added multi-sensor features
    """
    df = df_target.copy()

    # Store original index to preserve it through set_index/reset_index operations
    was_indexed = df.index.name == datetime_col
    original_index = df.index.copy()

    if not was_indexed:
        # Save original index as a column
        df['_original_index'] = original_index
        df = df.set_index(datetime_col)

    # Add each sensor's pressure value
    for area_name, df_other in df_others.items():
        # df_other is already indexed by datetime_col
        # Use join to preserve target index
        df = df.join(df_other.rename(columns={pressure_col: f'pressure_{area_name}'}), how='left')

    # Aggregate statistics across other sensors
    pressure_cols = [f'pressure_{name}' for name in df_others.keys()]
    if pressure_cols:
        df['pressure_other_mean'] = df[pressure_cols].mean(axis=1)
        # For std, pandas returns NaN when there's only 1 value (single sensor)
        # Fill with 0.0 in that case
        if len(pressure_cols) == 1:
            df['pressure_other_std'] = 0.0
        else:
            df['pressure_other_std'] = df[pressure_cols].std(axis=1)
        df['pressure_other_max'] = df[pressure_cols].max(axis=1)
        df['pressure_other_min'] = df[pressure_cols].min(axis=1)

    # Restore original index if it wasn't originally datetime-indexed
    if not was_indexed:
        df = df.reset_index()
        # Set the original index back
        df = df.set_index('_original_index')
        df.index.name = None  # Remove the temporary index name

    return df


def create_features(df: pd.DataFrame,
                   include_lags: bool = True,
                   include_rolling: bool = True,
                   include_multi_sensor: bool = False,
                   df_others: Optional[dict] = None,
                   target_col: str = 'wtrprsr',
                   datetime_col: str = 'msrmt_dt') -> Tuple[pd.DataFrame, pd.Series]:
    """
    Create all features for XGBoost model.

    Args:
        df: Input DataFrame with pressure data
        include_lags: Include lag features (NOT recommended for long gaps)
        include_rolling: Include rolling statistics
        include_multi_sensor: Include other sensor data (RECOMMENDED for long gaps)
        df_others: Dict of other sensor DataFrames (required if include_multi_sensor=True)
        target_col: Name of target column
        datetime_col: Name of datetime column

    Returns:
        X: Feature DataFrame
        y: Target Series

    Raises:
        ValueError: If include_multi_sensor=True but df_others is None
    """
    if include_multi_sensor and df_others is None:
        raise ValueError("df_others must be provided when include_multi_sensor=True")

    df = df.copy()

    # 1. Time features (always included)
    df = create_time_features(df, datetime_col)

    feature_cols = [
        'hour', 'day_of_week', 'month', 'quarter', 'is_weekend',
        'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'month_sin', 'month_cos'
    ]

    # 2. Lag features (optional, not recommended for long gaps)
    if include_lags:
        df = create_lag_features(df, target_col)
        lag_cols = [col for col in df.columns if col.startswith('lag_')]
        feature_cols.extend(lag_cols)

    # 3. Rolling features (optional)
    if include_rolling:
        df = create_rolling_features(df, target_col)
        rolling_cols = [col for col in df.columns if col.startswith('rolling_')]
        feature_cols.extend(rolling_cols)

    # 4. Multi-sensor features (KEY for long gaps)
    if include_multi_sensor:
        df = add_multi_sensor_features(df, df_others, datetime_col, target_col)
        multi_sensor_cols = [col for col in df.columns if col.startswith('pressure_')]
        feature_cols.extend(multi_sensor_cols)

    # Remove rows with NaN in FEATURES only (NOT target)
    # This is critical for interpolation tasks where target may have intentional NaN (gaps)
    df_features = df[feature_cols].dropna()

    # Align target with valid feature indices
    X = df_features
    y = df.loc[df_features.index, target_col]

    # NOTE: y may contain NaN (e.g., gap period for prediction)
    # This is intentional for interpolation tasks

    return X, y


def get_feature_names(include_lags: bool = True,
                     include_rolling: bool = True,
                     include_multi_sensor: bool = False,
                     other_sensor_names: Optional[List[str]] = None) -> List[str]:
    """
    Get list of feature names for given configuration.

    Args:
        include_lags: Include lag features
        include_rolling: Include rolling features
        include_multi_sensor: Include multi-sensor features
        other_sensor_names: List of other sensor area names (e.g., ['0243', '0461'])

    Returns:
        List of feature names
    """
    features = [
        'hour', 'day_of_week', 'month', 'quarter', 'is_weekend',
        'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'month_sin', 'month_cos'
    ]

    if include_lags:
        lags = [1, 2, 3, 12, 24, 144, 288]
        features.extend([f'lag_{lag}' for lag in lags])

    if include_rolling:
        windows = [12, 36, 144, 288]
        for window in windows:
            features.extend([
                f'rolling_mean_{window}',
                f'rolling_std_{window}',
                f'rolling_max_{window}',
                f'rolling_min_{window}'
            ])

    if include_multi_sensor and other_sensor_names:
        for name in other_sensor_names:
            features.append(f'pressure_{name}')
        features.extend([
            'pressure_other_mean',
            'pressure_other_std',
            'pressure_other_max',
            'pressure_other_min'
        ])

    return features
