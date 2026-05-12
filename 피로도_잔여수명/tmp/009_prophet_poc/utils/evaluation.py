#!/usr/bin/env python3
"""
Evaluation utilities for Prophet POC
"""

import numpy as np
import pandas as pd
from typing import Dict


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                     yhat_lower: np.ndarray = None,
                     yhat_upper: np.ndarray = None) -> Dict[str, float]:
    """
    Calculate performance metrics for interpolation.

    Args:
        y_true: True values
        y_pred: Predicted values
        yhat_lower: Lower bound of prediction interval (optional)
        yhat_upper: Upper bound of prediction interval (optional)

    Returns:
        Dictionary with metrics:
        - mae: Mean Absolute Error
        - rmse: Root Mean Squared Error
        - mape: Mean Absolute Percentage Error (%)
        - r2: R² Score
        - coverage: Prediction interval coverage (if intervals provided)
    """
    # Remove NaN values
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        raise ValueError("No valid data points after removing NaNs")

    # MAE
    mae = np.mean(np.abs(y_true - y_pred))

    # RMSE
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

    # MAPE (%)
    # Avoid division by zero
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100

    # R²
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / (ss_tot + 1e-10))

    metrics = {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
    }

    # Coverage (if prediction intervals provided)
    if yhat_lower is not None and yhat_upper is not None:
        yhat_lower = yhat_lower[mask]
        yhat_upper = yhat_upper[mask]
        coverage = np.mean((y_true >= yhat_lower) & (y_true <= yhat_upper))
        metrics['coverage'] = coverage

    return metrics


def grade_performance(metrics: Dict[str, float]) -> str:
    """
    Assign grade based on performance metrics.

    Grading criteria:
    - A: MAE < 0.10 AND MAPE < 5% AND R² > 0.7
    - B: MAE < 0.15 AND MAPE < 10% AND R² > 0.5
    - C: MAE < 0.25 AND MAPE < 15% AND R² > 0.3
    - D: Otherwise

    Args:
        metrics: Dictionary with 'mae', 'mape', 'r2' keys

    Returns:
        Grade string ('A', 'B', 'C', or 'D')
    """
    mae = metrics['mae']
    mape = metrics['mape']
    r2 = metrics['r2']

    if mae < 0.10 and mape < 5 and r2 > 0.7:
        return 'A'
    elif mae < 0.15 and mape < 10 and r2 > 0.5:
        return 'B'
    elif mae < 0.25 and mape < 15 and r2 > 0.3:
        return 'C'
    else:
        return 'D'


def print_metrics(metrics: Dict[str, float], grade: str = None):
    """
    Print metrics in a formatted table.

    Args:
        metrics: Dictionary with metric values
        grade: Performance grade (optional)
    """
    print("\n" + "="*60)
    print("📊 PERFORMANCE METRICS")
    print("="*60)

    print(f"MAE  (Mean Absolute Error)    : {metrics['mae']:.4f}")
    print(f"RMSE (Root Mean Squared Error): {metrics['rmse']:.4f}")
    print(f"MAPE (Mean Absolute % Error)  : {metrics['mape']:.2f}%")
    print(f"R²   (Coefficient of Determination): {metrics['r2']:.4f}")

    if 'coverage' in metrics:
        print(f"Coverage (95% interval)       : {metrics['coverage']:.2%}")

    if grade:
        print(f"\n📈 GRADE: {grade}")

        # Grade interpretation
        grade_desc = {
            'A': '우수 (실무 사용 권장)',
            'B': '양호 (조건부 사용)',
            'C': '보통 (신중 사용)',
            'D': '불합격 (사용 불가)'
        }
        print(f"   {grade_desc.get(grade, '')}")

    print("="*60)


def check_pass_criteria(metrics: Dict[str, float]) -> tuple:
    """
    Check if metrics pass the success criteria.

    Success criteria:
    - R² > 0.5 (primary)
    - MAPE < 10% (secondary)

    Args:
        metrics: Dictionary with metric values

    Returns:
        Tuple of (passed: bool, reasons: list)
    """
    passed = True
    reasons = []

    # Primary criterion: R²
    if metrics['r2'] <= 0.5:
        passed = False
        reasons.append(f"❌ R² = {metrics['r2']:.4f} (required > 0.5)")
    else:
        reasons.append(f"✅ R² = {metrics['r2']:.4f} (> 0.5)")

    # Secondary criterion: MAPE
    if metrics['mape'] >= 10:
        passed = False
        reasons.append(f"❌ MAPE = {metrics['mape']:.2f}% (required < 10%)")
    else:
        reasons.append(f"✅ MAPE = {metrics['mape']:.2f}% (< 10%)")

    # Additional info: MAE
    if metrics['mae'] < 0.15:
        reasons.append(f"✅ MAE = {metrics['mae']:.4f} (< 0.15)")
    else:
        reasons.append(f"⚠️ MAE = {metrics['mae']:.4f} (>= 0.15)")

    return passed, reasons
