"""
Evaluation Metrics for Pressure Interpolation

This module provides performance evaluation functions for interpolation models.
"""

from typing import Dict, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Error.

    Args:
        y_true: True values
        y_pred: Predicted values

    Returns:
        MAE score
    """
    return np.mean(np.abs(y_true - y_pred))


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Root Mean Squared Error.

    Args:
        y_true: True values
        y_pred: Predicted values

    Returns:
        RMSE score
    """
    return np.sqrt(np.mean((y_true - y_pred) ** 2))


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Percentage Error.

    Args:
        y_true: True values
        y_pred: Predicted values

    Returns:
        MAPE score (percentage)
    """
    # Avoid division by zero
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def calculate_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate R² (coefficient of determination).

    Args:
        y_true: True values
        y_pred: Predicted values

    Returns:
        R² score (1.0 is perfect)
    """
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

    # Avoid division by zero
    if ss_tot == 0:
        return 0.0

    return 1 - (ss_res / ss_tot)


def evaluate(y_true: np.ndarray,
            y_pred: np.ndarray,
            metrics: Optional[list] = None) -> Dict[str, float]:
    """
    Calculate multiple evaluation metrics.

    Args:
        y_true: True values
        y_pred: Predicted values
        metrics: List of metrics to calculate.
                Default: ['mae', 'rmse', 'mape', 'r2']

    Returns:
        Dictionary of metric scores
    """
    if metrics is None:
        metrics = ['mae', 'rmse', 'mape', 'r2']

    results = {}

    if 'mae' in metrics:
        results['mae'] = calculate_mae(y_true, y_pred)

    if 'rmse' in metrics:
        results['rmse'] = calculate_rmse(y_true, y_pred)

    if 'mape' in metrics:
        results['mape'] = calculate_mape(y_true, y_pred)

    if 'r2' in metrics:
        results['r2'] = calculate_r2(y_true, y_pred)

    return results


def get_performance_grade(mae: float,
                         mape: float,
                         r2: float) -> str:
    """
    Get performance grade based on metrics.

    Grading criteria from TEST_PLAN:
    - S: MAE < 0.15, MAPE < 5%, R² > 0.85 (Excellent)
    - A: MAE 0.15-0.25, MAPE 5-8%, R² 0.75-0.85 (Good)
    - B: MAE 0.25-0.35, MAPE 8-12%, R² 0.65-0.75 (Fair)
    - C: MAE 0.35-0.50, MAPE 12-15%, R² 0.50-0.65 (Poor)
    - D: MAE > 0.50, MAPE > 15%, R² < 0.50 (Fail)

    Args:
        mae: Mean Absolute Error
        mape: Mean Absolute Percentage Error (%)
        r2: R² score

    Returns:
        Grade letter (S/A/B/C/D)
    """
    if mae < 0.15 and mape < 5 and r2 > 0.85:
        return 'S'
    elif mae < 0.25 and mape < 8 and r2 > 0.75:
        return 'A'
    elif mae < 0.35 and mape < 12 and r2 > 0.65:
        return 'B'
    elif mae < 0.50 and mape < 15 and r2 > 0.50:
        return 'C'
    else:
        return 'D'


def check_criteria(metrics: Dict[str, float],
                  mae_threshold: float = 0.2,
                  mape_threshold: float = 10.0,
                  r2_threshold: float = 0.7) -> Dict[str, bool]:
    """
    Check if metrics meet success criteria.

    Args:
        metrics: Dictionary of metric scores
        mae_threshold: MAE acceptance threshold
        mape_threshold: MAPE acceptance threshold (%)
        r2_threshold: R² acceptance threshold

    Returns:
        Dictionary of pass/fail for each criterion
    """
    results = {}

    if 'mae' in metrics:
        results['mae_pass'] = metrics['mae'] < mae_threshold

    if 'mape' in metrics:
        results['mape_pass'] = metrics['mape'] < mape_threshold

    if 'r2' in metrics:
        results['r2_pass'] = metrics['r2'] > r2_threshold

    results['all_pass'] = all(results.values())

    return results


def plot_comparison(y_true: np.ndarray,
                   y_pred: np.ndarray,
                   timestamps: Optional[pd.DatetimeIndex] = None,
                   gap_start: Optional[int] = None,
                   gap_end: Optional[int] = None,
                   title: str = "Original vs Predicted",
                   save_path: Optional[Path] = None,
                   show: bool = True) -> None:
    """
    Plot comparison of true vs predicted values.

    Args:
        y_true: True values
        y_pred: Predicted values
        timestamps: Datetime index for x-axis
        gap_start: Start index of gap region (for highlighting)
        gap_end: End index of gap region (for highlighting)
        title: Plot title
        save_path: Path to save figure
        show: Display plot
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # Convert inputs to numpy arrays if they're pandas Series
    if hasattr(y_true, 'values'):
        y_true = y_true.values
    if hasattr(y_pred, 'values'):
        y_pred = y_pred.values

    x_axis = timestamps if timestamps is not None else np.arange(len(y_true))

    # Full timeline
    ax1 = axes[0]
    ax1.plot(x_axis, y_true, label='Original', color='blue', alpha=0.7)
    ax1.plot(x_axis, y_pred, label='Predicted', color='red', alpha=0.7, linestyle='--')

    if gap_start is not None and gap_end is not None:
        # Use iloc for pandas Series, regular indexing for numpy
        if hasattr(x_axis, 'iloc'):
            gap_x_start = x_axis.iloc[gap_start]
            gap_x_end = x_axis.iloc[gap_end]
        else:
            gap_x_start = x_axis[gap_start]
            gap_x_end = x_axis[gap_end]
        ax1.axvspan(gap_x_start, gap_x_end, alpha=0.2, color='yellow', label='Gap Region')

    ax1.set_title(title)
    ax1.set_ylabel('Pressure')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Zoomed gap region
    if gap_start is not None and gap_end is not None:
        ax2 = axes[1]
        margin = int((gap_end - gap_start) * 0.1)  # 10% margin
        start_idx = max(0, gap_start - margin)
        end_idx = min(len(y_true), gap_end + margin)

        # Use iloc for pandas Series
        if hasattr(x_axis, 'iloc'):
            zoom_x = x_axis.iloc[start_idx:end_idx]
        else:
            zoom_x = x_axis[start_idx:end_idx]
        zoom_true = y_true[start_idx:end_idx]
        zoom_pred = y_pred[start_idx:end_idx]

        ax2.plot(zoom_x, zoom_true, label='Original', color='blue', marker='o', markersize=3)
        ax2.plot(zoom_x, zoom_pred, label='Predicted', color='red', marker='x', markersize=3)

        if hasattr(x_axis, 'iloc'):
            gap_x_start = x_axis.iloc[gap_start]
            gap_x_end = x_axis.iloc[gap_end-1]
        else:
            gap_x_start = x_axis[gap_start]
            gap_x_end = x_axis[gap_end-1]
        ax2.axvspan(gap_x_start, gap_x_end, alpha=0.2, color='yellow')

        ax2.set_title(f'{title} (Zoomed Gap Region)')
        ax2.set_ylabel('Pressure')
        ax2.set_xlabel('Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    else:
        # Residual plot if no gap specified
        ax2 = axes[1]
        residuals = y_true - y_pred
        ax2.scatter(x_axis, residuals, alpha=0.5, s=1)
        ax2.axhline(y=0, color='red', linestyle='--')
        ax2.set_title('Residuals (True - Predicted)')
        ax2.set_ylabel('Residual')
        ax2.set_xlabel('Time')
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")

    if show:
        plt.show()
    else:
        plt.close()


def generate_report(metrics: Dict[str, float],
                   criteria: Dict[str, bool],
                   method_name: str = "XGBoost",
                   save_path: Optional[Path] = None) -> str:
    """
    Generate evaluation report in markdown format.

    Args:
        metrics: Dictionary of metric scores
        criteria: Dictionary of pass/fail results
        method_name: Name of interpolation method
        save_path: Path to save report

    Returns:
        Report content as string
    """
    grade = get_performance_grade(
        metrics.get('mae', 999),
        metrics.get('mape', 999),
        metrics.get('r2', 0)
    )

    report = f"""# {method_name} Interpolation Performance Report

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| MAE | {metrics.get('mae', 0):.4f} | < 0.2 | {'✅ PASS' if criteria.get('mae_pass', False) else '❌ FAIL'} |
| RMSE | {metrics.get('rmse', 0):.4f} | < 0.3 | - |
| MAPE | {metrics.get('mape', 0):.2f}% | < 10% | {'✅ PASS' if criteria.get('mape_pass', False) else '❌ FAIL'} |
| R² | {metrics.get('r2', 0):.4f} | > 0.7 | {'✅ PASS' if criteria.get('r2_pass', False) else '❌ FAIL'} |

## Performance Grade

**Grade: {grade}**

- S: Excellent (실무 사용 권장)
- A: Good (조건부 사용)
- B: Fair (신중 사용)
- C: Poor (개선 필요)
- D: Fail (사용 불가)

## Overall Result

{'✅ **ALL CRITERIA PASSED**' if criteria.get('all_pass', False) else '❌ **SOME CRITERIA FAILED**'}

---

*Generated automatically by evaluation.py*
"""

    if save_path:
        save_path.write_text(report, encoding='utf-8')
        print(f"Report saved to {save_path}")

    return report


def compare_methods(results: Dict[str, Dict[str, float]],
                   save_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Create comparison table for multiple methods.

    Args:
        results: Dict of {method_name: metrics_dict}
        save_path: Path to save comparison table

    Returns:
        DataFrame with comparison results
    """
    df = pd.DataFrame(results).T
    df = df.sort_values('mae')  # Sort by MAE (lower is better)

    # Add grade column
    df['grade'] = df.apply(
        lambda row: get_performance_grade(row['mae'], row['mape'], row['r2']),
        axis=1
    )

    if save_path:
        df.to_csv(save_path, index=True)
        print(f"Comparison table saved to {save_path}")

    return df
