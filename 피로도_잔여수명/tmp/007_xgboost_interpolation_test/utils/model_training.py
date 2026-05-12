"""
Model Training for XGBoost-based Pressure Interpolation

This module provides training functions for XGBoost and baseline models.
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


def train_xgboost(X_train: pd.DataFrame,
                  y_train: pd.Series,
                  params: Optional[Dict[str, Any]] = None,
                  verbose: bool = False) -> Any:
    """
    Train XGBoost model for pressure interpolation.

    Args:
        X_train: Feature DataFrame
        y_train: Target Series
        params: Hyperparameters (None for defaults)
        verbose: Print training progress

    Returns:
        Trained XGBoost model

    Raises:
        ImportError: If xgboost is not installed
    """
    try:
        import xgboost as xgb
    except ImportError:
        raise ImportError(
            "xgboost is required. Install with: pip install xgboost"
        )

    if params is None:
        params = {
            'n_estimators': 2000,       # Increased for better learning
            'max_depth': 8,             # Increased for deeper patterns
            'learning_rate': 0.01,      # Decreased for finer learning
            'subsample': 0.9,           # Relaxed regularization
            'colsample_bytree': 0.9,    # Relaxed regularization
            'random_state': 42,
            'n_jobs': -1,
            'early_stopping_rounds': 50,  # Move to constructor in newer XGBoost
        }

    model = xgb.XGBRegressor(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train)],
        verbose=verbose
    )

    return model


def train_linear_baseline(X_train: pd.DataFrame,
                          y_train: pd.Series) -> LinearRegression:
    """
    Train linear regression baseline model.

    Args:
        X_train: Feature DataFrame
        y_train: Target Series

    Returns:
        Trained LinearRegression model
    """
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model


def train_sarima(y_train: pd.Series,
                order: tuple = (5, 1, 2),
                seasonal_order: tuple = (1, 1, 1, 288),
                verbose: bool = False) -> Any:
    """
    Train SARIMA model for pressure time series.

    Args:
        y_train: Target Series (must be datetime-indexed)
        order: (p, d, q) order of ARIMA
        seasonal_order: (P, D, Q, s) seasonal order
                       s=288 for 5-minute data (24h cycle)
        verbose: Print training progress

    Returns:
        Fitted SARIMA model

    Raises:
        ImportError: If statsmodels is not installed
    """
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        raise ImportError(
            "statsmodels is required. Install with: pip install statsmodels"
        )

    model = SARIMAX(
        y_train,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False
    )

    fitted = model.fit(disp=verbose)
    return fitted


def train_prophet(df_train: pd.DataFrame,
                 datetime_col: str = 'msrmt_dt',
                 target_col: str = 'wtrprsr',
                 yearly_seasonality: bool = False,
                 weekly_seasonality: bool = True,
                 daily_seasonality: bool = True) -> Any:
    """
    Train Prophet model for pressure time series.

    Args:
        df_train: Training DataFrame
        datetime_col: Name of datetime column
        target_col: Name of target column
        yearly_seasonality: Enable yearly seasonality
        weekly_seasonality: Enable weekly seasonality
        daily_seasonality: Enable daily seasonality

    Returns:
        Fitted Prophet model

    Raises:
        ImportError: If prophet is not installed
    """
    try:
        from prophet import Prophet
    except ImportError:
        raise ImportError(
            "prophet is required. Install with: pip install prophet"
        )

    # Prophet requires specific column names
    df_prophet = df_train[[datetime_col, target_col]].copy()
    df_prophet.columns = ['ds', 'y']

    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        daily_seasonality=daily_seasonality
    )

    model.fit(df_prophet)
    return model


def predict_xgboost(model: Any,
                   X_test: pd.DataFrame) -> np.ndarray:
    """
    Predict using trained XGBoost model.

    Args:
        model: Trained XGBoost model
        X_test: Test features

    Returns:
        Predicted values
    """
    return model.predict(X_test)


def predict_sarima(model: Any,
                  start: int,
                  end: int) -> pd.Series:
    """
    Predict using fitted SARIMA model.

    Args:
        model: Fitted SARIMA model
        start: Start index for prediction
        end: End index for prediction

    Returns:
        Predicted values
    """
    return model.predict(start=start, end=end)


def predict_prophet(model: Any,
                   future_df: pd.DataFrame) -> np.ndarray:
    """
    Predict using fitted Prophet model.

    Args:
        model: Fitted Prophet model
        future_df: Future DataFrame with 'ds' column (datetime)

    Returns:
        Predicted values (yhat)
    """
    forecast = model.predict(future_df)
    return forecast['yhat'].values


def get_feature_importance(model: Any,
                          feature_names: list) -> pd.DataFrame:
    """
    Get feature importance from XGBoost model.

    Args:
        model: Trained XGBoost model
        feature_names: List of feature names

    Returns:
        DataFrame with feature importance scores
    """
    try:
        import xgboost as xgb
    except ImportError:
        raise ImportError("xgboost is required")

    if not isinstance(model, xgb.XGBRegressor):
        raise ValueError("Model must be XGBRegressor")

    importance = model.feature_importances_
    df_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

    return df_importance
