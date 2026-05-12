#!/usr/bin/env python3
"""
Visualization utilities for Prophet POC
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional


def plot_forecast_with_gap(df_original: pd.DataFrame,
                           df_gap_true: pd.DataFrame,
                           forecast: pd.DataFrame,
                           gap_start: str,
                           gap_end: str,
                           save_path: Optional[Path] = None):
    """
    Plot original data, true gap values, and Prophet forecast.

    Args:
        df_original: Original complete DataFrame with 'msrmt_dt' and 'wtrprsr'
        df_gap_true: True values in gap period
        forecast: Prophet forecast DataFrame with 'ds', 'yhat', 'yhat_lower', 'yhat_upper'
        gap_start: Gap start datetime string
        gap_end: Gap end datetime string
        save_path: Path to save figure (optional)
    """
    fig, ax = plt.subplots(figsize=(16, 6))

    gap_start_dt = pd.to_datetime(gap_start)
    gap_end_dt = pd.to_datetime(gap_end)

    # Plot original data (excluding gap)
    df_train = df_original[
        (df_original['msrmt_dt'] < gap_start_dt) |
        (df_original['msrmt_dt'] > gap_end_dt)
    ]
    ax.plot(df_train['msrmt_dt'], df_train['wtrprsr'],
            'o', markersize=2, alpha=0.5, label='Training Data', color='gray')

    # Plot true gap values
    ax.plot(df_gap_true['msrmt_dt'], df_gap_true['wtrprsr'],
            'o', markersize=3, label='True Values (Gap)', color='blue', alpha=0.7)

    # Plot Prophet prediction
    ax.plot(forecast['ds'], forecast['yhat'],
            '-', linewidth=2, label='Prophet Prediction', color='red')

    # Plot prediction interval
    ax.fill_between(forecast['ds'],
                    forecast['yhat_lower'],
                    forecast['yhat_upper'],
                    alpha=0.2, color='red', label='95% Confidence Interval')

    # Mark gap region
    ax.axvline(gap_start_dt, color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.axvline(gap_end_dt, color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.axvspan(gap_start_dt, gap_end_dt, alpha=0.1, color='orange', label='Gap Period')

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Pressure (wtrprsr)', fontsize=12)
    ax.set_title('Prophet Interpolation - Full View', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved: {save_path}")

    plt.close()


def plot_gap_zoom(df_gap_true: pd.DataFrame,
                 forecast: pd.DataFrame,
                 gap_start: str,
                 gap_end: str,
                 save_path: Optional[Path] = None):
    """
    Plot zoomed view of gap period only.

    Args:
        df_gap_true: True values in gap period
        forecast: Prophet forecast DataFrame
        gap_start: Gap start datetime string
        gap_end: Gap end datetime string
        save_path: Path to save figure (optional)
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot true values
    ax.plot(df_gap_true['msrmt_dt'], df_gap_true['wtrprsr'],
            'o-', markersize=2, label='True Values', color='blue', alpha=0.7, linewidth=1)

    # Plot prediction
    ax.plot(forecast['ds'], forecast['yhat'],
            'o-', markersize=2, label='Prophet Prediction', color='red', alpha=0.7, linewidth=1)

    # Plot prediction interval
    ax.fill_between(forecast['ds'],
                    forecast['yhat_lower'],
                    forecast['yhat_upper'],
                    alpha=0.2, color='red', label='95% Confidence Interval')

    # Calculate residuals
    # Align forecast to df_gap_true by date
    forecast_aligned = forecast.set_index('ds').reindex(df_gap_true['msrmt_dt'])
    residuals = df_gap_true['wtrprsr'].values - forecast_aligned['yhat'].values

    # Add residual info to title
    rmse = np.sqrt(np.mean(residuals**2))
    mae = np.mean(np.abs(residuals))

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Pressure (wtrprsr)', fontsize=12)
    ax.set_title(f'Gap Period Zoom (MAE: {mae:.4f}, RMSE: {rmse:.4f})',
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    fig.autofmt_xdate()

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved: {save_path}")

    plt.close()


def plot_residuals(df_gap_true: pd.DataFrame,
                  forecast: pd.DataFrame,
                  save_path: Optional[Path] = None):
    """
    Plot residual analysis.

    Args:
        df_gap_true: True values in gap period
        forecast: Prophet forecast DataFrame
        save_path: Path to save figure (optional)
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Align forecast to df_gap_true
    forecast_aligned = forecast.set_index('ds').reindex(df_gap_true['msrmt_dt'])
    y_true = df_gap_true['wtrprsr'].values
    y_pred = forecast_aligned['yhat'].values

    residuals = y_true - y_pred

    # 1. Residuals over time
    axes[0, 0].plot(df_gap_true['msrmt_dt'], residuals, 'o-', markersize=2, alpha=0.6)
    axes[0, 0].axhline(0, color='red', linestyle='--', linewidth=1)
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('Residual')
    axes[0, 0].set_title('Residuals Over Time')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    fig.autofmt_xdate()

    # 2. Residual histogram
    axes[0, 1].hist(residuals, bins=50, edgecolor='black', alpha=0.7)
    axes[0, 1].axvline(0, color='red', linestyle='--', linewidth=1)
    axes[0, 1].set_xlabel('Residual')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title(f'Residual Distribution (Mean: {np.mean(residuals):.4f}, Std: {np.std(residuals):.4f})')
    axes[0, 1].grid(True, alpha=0.3)

    # 3. Predicted vs Actual
    axes[1, 0].scatter(y_pred, y_true, alpha=0.5, s=10)
    min_val = min(y_pred.min(), y_true.min())
    max_val = max(y_pred.max(), y_true.max())
    axes[1, 0].plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Perfect Fit')
    axes[1, 0].set_xlabel('Predicted')
    axes[1, 0].set_ylabel('Actual')
    axes[1, 0].set_title('Predicted vs Actual')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # 4. Residuals vs Predicted
    axes[1, 1].scatter(y_pred, residuals, alpha=0.5, s=10)
    axes[1, 1].axhline(0, color='red', linestyle='--', linewidth=1)
    axes[1, 1].set_xlabel('Predicted')
    axes[1, 1].set_ylabel('Residual')
    axes[1, 1].set_title('Residuals vs Predicted')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved: {save_path}")

    plt.close()
