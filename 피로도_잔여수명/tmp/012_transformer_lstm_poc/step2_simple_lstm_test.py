#!/usr/bin/env python3
"""
Step 2: Simple LSTM Quick Test

3가지 핵심 테스트:
- Test A: 1-step-ahead 예측 (Baseline)
- Test B: 10-step 비재귀 예측 ⭐ 핵심
- Test C: 고주파 예측 가능성

실행 방법:
    python step2_simple_lstm_test.py --area 0243
    python step2_simple_lstm_test.py --area 0243 --seq-length 256
    python step2_simple_lstm_test.py --area 0243 --test B  # Test B만 실행
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import signal, stats
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# TensorFlow/Keras imports
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, callbacks, models
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    print(f"TensorFlow version: {tf.__version__}")
except ImportError:
    print("ERROR: TensorFlow not installed. Install with: pip install tensorflow")
    sys.exit(1)

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Step 2: Simple LSTM Quick Test"
    )
    parser.add_argument(
        "--area",
        type=str,
        default="0243",
        help="소구역 코드 (기본값: 0243)"
    )
    parser.add_argument(
        "--seq-length",
        type=int,
        default=300,
        help="Sequence length (기본값: 300, Step 1 권장값)"
    )
    parser.add_argument(
        "--test",
        type=str,
        choices=["A", "B", "C", "all"],
        default="all",
        help="실행할 테스트 (A: 1-step, B: 10-step, C: 고주파, all: 전체)"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="학습 에포크 수 (기본값: 50)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="배치 크기 (기본값: 32)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="결과 저장 디렉토리 (기본값: results)"
    )
    parser.add_argument(
        "--v-valley",
        type=float,
        default=553.5,
        help="V-valley 주파수 (분, 기본값: 553.5)"
    )
    return parser.parse_args()


def load_pressure_data(area: str) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    압력 데이터 로드 (원시 데이터 사용)

    Returns:
        df: 원본 DataFrame
        pressure: 압력 값 numpy array
    """
    # Raw data path
    data_path = Path(__file__).parent.parent.parent / "data" / "raw"
    csv_file = data_path / f"{area} 소구역 압력 데이터.csv"

    if not csv_file.exists():
        raise FileNotFoundError(
            f"Data file not found: {csv_file}\n"
            f"Available area codes: 0243, 0461, 0470, 0480, 0490, etc."
        )

    df = pd.read_csv(csv_file, encoding='utf-8')

    # The raw data has different column names, check possible variations
    pressure_col = None
    for col in ['wtrprsr', '압력', 'pressure', 'PRESSURE', 'Pressure', '압력(kPa)']:
        if col in df.columns:
            pressure_col = col
            break

    if pressure_col is None:
        raise ValueError(
            f"Pressure column not found in {csv_file}.\n"
            f"Available columns: {list(df.columns)}"
        )

    pressure = df[pressure_col].values

    # Check for NaN values
    if np.any(np.isnan(pressure)):
        print(f"⚠️  Warning: Found {np.sum(np.isnan(pressure)):,} NaN values, removing them...")
        pressure = pressure[~np.isnan(pressure)]

    print(f"✓ Loaded {len(pressure):,} pressure points from {csv_file}")
    print(f"  Pressure range: [{np.min(pressure):.2f}, {np.max(pressure):.2f}]")

    return df, pressure


def create_sequences(data: np.ndarray,
                     seq_length: int,
                     output_steps: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    """
    시계열 데이터를 LSTM 입력 시퀀스로 변환

    Args:
        data: 원본 시계열 데이터
        seq_length: 입력 시퀀스 길이
        output_steps: 출력 스텝 수 (1-step or multi-step)

    Returns:
        X: (n_samples, seq_length, 1)
        y: (n_samples, output_steps)
    """
    X, y = [], []

    for i in range(len(data) - seq_length - output_steps + 1):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length:i + seq_length + output_steps])

    X = np.array(X)
    y = np.array(y)

    # Reshape for LSTM: (samples, timesteps, features)
    X = X.reshape((X.shape[0], X.shape[1], 1))

    if output_steps == 1:
        y = y.flatten()

    return X, y


def split_train_val_test(X: np.ndarray,
                          y: np.ndarray,
                          train_ratio: float = 0.7,
                          val_ratio: float = 0.15) -> Tuple:
    """
    데이터를 train/val/test로 분할 (시계열 순서 유지)

    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test
    """
    n = len(X)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    X_train = X[:train_end]
    X_val = X[train_end:val_end]
    X_test = X[val_end:]

    y_train = y[:train_end]
    y_val = y[train_end:val_end]
    y_test = y[val_end:]

    print(f"  Train: {len(X_train):,} samples")
    print(f"  Val:   {len(X_val):,} samples")
    print(f"  Test:  {len(X_test):,} samples")

    return X_train, X_val, X_test, y_train, y_val, y_test


def build_lstm_model(seq_length: int,
                     output_steps: int = 1,
                     lstm_units: int = 256,
                     dropout_rate: float = 0.2) -> keras.Model:
    """
    LSTM 모델 생성

    Args:
        seq_length: 입력 시퀀스 길이
        output_steps: 출력 스텝 수
        lstm_units: LSTM 유닛 수
        dropout_rate: Dropout 비율

    Returns:
        Compiled Keras model
    """
    model = Sequential([
        LSTM(lstm_units,
             input_shape=(seq_length, 1),
             return_sequences=False),
        Dropout(dropout_rate),
        Dense(128, activation='relu'),
        Dropout(dropout_rate),
        Dense(output_steps)
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )

    return model


def train_model(model: keras.Model,
                X_train: np.ndarray,
                y_train: np.ndarray,
                X_val: np.ndarray,
                y_val: np.ndarray,
                epochs: int = 50,
                batch_size: int = 32,
                patience: int = 10) -> keras.callbacks.History:
    """
    모델 학습

    Returns:
        Training history
    """
    early_stop = callbacks.EarlyStopping(
        monitor='val_loss',
        patience=patience,
        restore_best_weights=True
    )

    reduce_lr = callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-6,
        verbose=1
    )

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )

    return history


def evaluate_model(model: keras.Model,
                   X_test: np.ndarray,
                   y_test: np.ndarray,
                   output_steps: int = 1) -> Dict:
    """
    모델 평가

    Returns:
        Dict with metrics
    """
    y_pred = model.predict(X_test, verbose=0)

    if output_steps == 1:
        # Single-step prediction
        r2 = r2_score(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mse)

        return {
            "r2": float(r2),
            "mse": float(mse),
            "rmse": float(rmse),
            "mae": float(mae),
            "n_samples": len(y_test)
        }
    else:
        # Multi-step prediction
        results = {
            "overall": {},
            "per_step": []
        }

        # Overall metrics (flatten all predictions)
        y_test_flat = y_test.flatten()
        y_pred_flat = y_pred.flatten()

        results["overall"] = {
            "r2": float(r2_score(y_test_flat, y_pred_flat)),
            "mse": float(mean_squared_error(y_test_flat, y_pred_flat)),
            "rmse": float(np.sqrt(mean_squared_error(y_test_flat, y_pred_flat))),
            "mae": float(mean_absolute_error(y_test_flat, y_pred_flat)),
            "n_samples": len(y_test)
        }

        # Per-step metrics
        for step in range(output_steps):
            y_true_step = y_test[:, step]
            y_pred_step = y_pred[:, step]

            results["per_step"].append({
                "step": step + 1,
                "r2": float(r2_score(y_true_step, y_pred_step)),
                "mae": float(mean_absolute_error(y_true_step, y_pred_step))
            })

        return results


def test_a_one_step_ahead(pressure: np.ndarray,
                          seq_length: int,
                          epochs: int,
                          batch_size: int) -> Dict:
    """
    Test A: 1-step-ahead 예측 (Baseline)

    목표: R² > 0.99 (XGBoost와 비교)
    """
    print("\n" + "="*70)
    print("🧪 Test A: 1-step-ahead 예측 (Baseline)")
    print("="*70)

    # Normalize
    scaler = StandardScaler()
    pressure_scaled = scaler.fit_transform(pressure.reshape(-1, 1)).flatten()

    # Create sequences
    print(f"\n1. Creating sequences (seq_length={seq_length}, output=1)...")
    X, y = create_sequences(pressure_scaled, seq_length, output_steps=1)
    print(f"  Created {len(X):,} sequences")

    # Split data
    print("\n2. Splitting data (70% train, 15% val, 15% test)...")
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(X, y)

    # Build model
    print("\n3. Building LSTM model...")
    model = build_lstm_model(seq_length, output_steps=1)
    print(model.summary())

    # Train
    print("\n4. Training model...")
    history = train_model(
        model, X_train, y_train, X_val, y_val,
        epochs=epochs, batch_size=batch_size
    )

    # Evaluate
    print("\n5. Evaluating on test set...")
    metrics = evaluate_model(model, X_test, y_test, output_steps=1)

    print(f"\n📊 Test A Results:")
    print(f"  R²:   {metrics['r2']:.6f}")
    print(f"  RMSE: {metrics['rmse']:.6f}")
    print(f"  MAE:  {metrics['mae']:.6f}")

    # Judgment
    if metrics['r2'] > 0.99:
        judgment = "✅ 성공"
        message = "LSTM 기본 성능 확인"
    elif metrics['r2'] > 0.95:
        judgment = "⚠️ 보통"
        message = "XGBoost보다 낮음"
    else:
        judgment = "❌ 실패"
        message = "LSTM 기본 성능 부족"

    print(f"\n🎯 판정: {judgment} - {message}")

    return {
        "test_name": "Test A: 1-step-ahead",
        "target": "R² > 0.99",
        "metrics": metrics,
        "judgment": judgment,
        "message": message,
        "history": {
            "loss": [float(x) for x in history.history['loss']],
            "val_loss": [float(x) for x in history.history['val_loss']],
            "epochs": len(history.history['loss'])
        },
        "scaler_mean": float(scaler.mean_[0]),
        "scaler_std": float(scaler.scale_[0])
    }


def test_b_ten_step_nonrecursive(pressure: np.ndarray,
                                  seq_length: int,
                                  epochs: int,
                                  batch_size: int) -> Dict:
    """
    Test B: 10-step 비재귀 예측 ⭐ 핵심 테스트

    목표: R² > 0.5
    의미: Recursive prediction 회피 효과 검증
    """
    print("\n" + "="*70)
    print("🧪 Test B: 10-step 비재귀 예측 ⭐ 핵심")
    print("="*70)

    # Normalize
    scaler = StandardScaler()
    pressure_scaled = scaler.fit_transform(pressure.reshape(-1, 1)).flatten()

    # Create sequences
    output_steps = 10
    print(f"\n1. Creating sequences (seq_length={seq_length}, output={output_steps})...")
    X, y = create_sequences(pressure_scaled, seq_length, output_steps=output_steps)
    print(f"  Created {len(X):,} sequences")

    # Split data
    print("\n2. Splitting data (70% train, 15% val, 15% test)...")
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(X, y)

    # Build model
    print("\n3. Building Multi-output LSTM model...")
    model = build_lstm_model(seq_length, output_steps=output_steps)
    print(model.summary())

    # Train
    print("\n4. Training model...")
    history = train_model(
        model, X_train, y_train, X_val, y_val,
        epochs=epochs, batch_size=batch_size
    )

    # Evaluate
    print("\n5. Evaluating on test set...")
    metrics = evaluate_model(model, X_test, y_test, output_steps=output_steps)

    print(f"\n📊 Test B Results:")
    print(f"  Overall R²:   {metrics['overall']['r2']:.6f}")
    print(f"  Overall RMSE: {metrics['overall']['rmse']:.6f}")
    print(f"  Overall MAE:  {metrics['overall']['mae']:.6f}")

    print(f"\n  Per-step R²:")
    for step_result in metrics['per_step']:
        print(f"    Step {step_result['step']:2d}: R² = {step_result['r2']:.6f}, "
              f"MAE = {step_result['mae']:.6f}")

    # Judgment (CRITICAL!)
    r2 = metrics['overall']['r2']
    if r2 > 0.5:
        judgment = "✅ 성공"
        message = "Phase 5 진행 권장 (성공 확률: 60-70%)"
        decision = "GO"
    elif r2 > 0.3:
        judgment = "⚠️ 보통"
        message = "Step 3 확인 후 결정 (성공 확률: 40-60%)"
        decision = "CAUTIOUS"
    elif r2 > 0.1:
        judgment = "△ 미흡"
        message = "근본적 한계 가능성 (성공 확률: 20-40%)"
        decision = "RISKY"
    else:
        judgment = "❌ 실패"
        message = "Transformer/LSTM 포기 권장"
        decision = "NO-GO"

    print(f"\n🎯 판정: {judgment} - {message}")
    print(f"   결정: {decision}")

    return {
        "test_name": "Test B: 10-step 비재귀",
        "target": "R² > 0.5",
        "metrics": metrics,
        "judgment": judgment,
        "message": message,
        "decision": decision,
        "history": {
            "loss": [float(x) for x in history.history['loss']],
            "val_loss": [float(x) for x in history.history['val_loss']],
            "epochs": len(history.history['loss'])
        },
        "scaler_mean": float(scaler.mean_[0]),
        "scaler_std": float(scaler.scale_[0])
    }


def apply_frequency_separation(pressure: np.ndarray,
                                v_valley: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    주파수 분리 (Phase 4와 동일)

    Args:
        pressure: 원본 압력 데이터
        v_valley: V-valley 주파수 (분)

    Returns:
        low_freq: 저주파 성분
        high_freq: 고주파 성분
    """
    from scipy.fft import rfft, rfftfreq, irfft

    # FFT
    fft_vals = rfft(pressure)
    freqs = rfftfreq(len(pressure), d=1.0)  # 1분 샘플링

    # Cutoff frequency
    cutoff_freq = 1 / v_valley

    # Low-pass filter
    low_pass = fft_vals.copy()
    low_pass[freqs > cutoff_freq] = 0
    low_freq = irfft(low_pass, n=len(pressure))

    # High-pass filter
    high_pass = fft_vals.copy()
    high_pass[freqs <= cutoff_freq] = 0
    high_freq = irfft(high_pass, n=len(pressure))

    return low_freq, high_freq


def test_c_high_frequency(pressure: np.ndarray,
                          seq_length: int,
                          epochs: int,
                          batch_size: int,
                          v_valley: float) -> Dict:
    """
    Test C: 고주파 예측 가능성

    목표: R² > 0.1 (Phase 4: 0.0216)
    의미: 고주파가 예측 가능한지 검증
    """
    print("\n" + "="*70)
    print("🧪 Test C: 고주파 예측 가능성")
    print("="*70)

    # Frequency separation
    print(f"\n1. Frequency separation (V-valley: {v_valley:.1f} min)...")
    low_freq, high_freq = apply_frequency_separation(pressure, v_valley)

    print(f"  Low-freq variance:  {np.var(low_freq):.4f}")
    print(f"  High-freq variance: {np.var(high_freq):.4f}")
    print(f"  High-freq %: {100 * np.var(high_freq) / np.var(pressure):.2f}%")

    # Normalize high-freq
    scaler = StandardScaler()
    high_freq_scaled = scaler.fit_transform(high_freq.reshape(-1, 1)).flatten()

    # Create sequences
    print(f"\n2. Creating sequences (seq_length={seq_length}, output=1)...")
    X, y = create_sequences(high_freq_scaled, seq_length, output_steps=1)
    print(f"  Created {len(X):,} sequences")

    # Split data
    print("\n3. Splitting data (70% train, 15% val, 15% test)...")
    X_train, X_val, X_test, y_train, y_val, y_test = split_train_val_test(X, y)

    # Build model (smaller model for high-freq)
    print("\n4. Building LSTM model...")
    model = build_lstm_model(seq_length, output_steps=1, lstm_units=128)

    # Train
    print("\n5. Training model...")
    history = train_model(
        model, X_train, y_train, X_val, y_val,
        epochs=epochs, batch_size=batch_size, patience=15
    )

    # Evaluate
    print("\n6. Evaluating on test set...")
    metrics = evaluate_model(model, X_test, y_test, output_steps=1)

    print(f"\n📊 Test C Results:")
    print(f"  R²:   {metrics['r2']:.6f}")
    print(f"  RMSE: {metrics['rmse']:.6f}")
    print(f"  MAE:  {metrics['mae']:.6f}")

    # Compare with Phase 4
    phase4_r2 = 0.0216
    improvement = metrics['r2'] - phase4_r2

    print(f"\n  Phase 4 고주파 R²: {phase4_r2:.4f}")
    print(f"  Improvement:      {improvement:+.4f}")

    # Judgment
    if metrics['r2'] > 0.1:
        judgment = "✅ 성공"
        message = "고주파 예측 가능, 주파수 분리 효과적"
    elif metrics['r2'] > 0.05:
        judgment = "△ 보통"
        message = "약간의 예측 가능성"
    else:
        judgment = "❌ 실패"
        message = "고주파 본질적으로 예측 불가"

    print(f"\n🎯 판정: {judgment} - {message}")

    return {
        "test_name": "Test C: 고주파 예측",
        "target": "R² > 0.1",
        "metrics": metrics,
        "phase4_r2": phase4_r2,
        "improvement": float(improvement),
        "judgment": judgment,
        "message": message,
        "high_freq_variance_pct": float(100 * np.var(high_freq) / np.var(pressure)),
        "history": {
            "loss": [float(x) for x in history.history['loss']],
            "val_loss": [float(x) for x in history.history['val_loss']],
            "epochs": len(history.history['loss'])
        },
        "scaler_mean": float(scaler.mean_[0]),
        "scaler_std": float(scaler.scale_[0])
    }


def visualize_test_results(results: Dict, output_dir: Path):
    """
    테스트 결과 시각화
    """
    print("\n" + "="*70)
    print("📊 Generating visualizations...")
    print("="*70)

    fig = plt.figure(figsize=(16, 12))

    # Test A
    if "test_a" in results:
        ax1 = plt.subplot(3, 3, 1)
        history = results["test_a"]["history"]
        epochs = range(1, len(history["loss"]) + 1)
        ax1.plot(epochs, history["loss"], 'b-', label='Train Loss', alpha=0.7)
        ax1.plot(epochs, history["val_loss"], 'r-', label='Val Loss', alpha=0.7)
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss (MSE)')
        ax1.set_title('Test A: 1-step Training History')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2 = plt.subplot(3, 3, 2)
        metrics = results["test_a"]["metrics"]
        labels = ['R²', 'RMSE', 'MAE']
        values = [metrics['r2'], metrics['rmse'], metrics['mae']]
        colors = ['green' if metrics['r2'] > 0.99 else 'orange', 'blue', 'purple']
        ax2.bar(labels, values, color=colors, alpha=0.7)
        ax2.set_title('Test A: Metrics')
        ax2.set_ylabel('Value')
        ax2.grid(True, alpha=0.3, axis='y')

        ax3 = plt.subplot(3, 3, 3)
        judgment = results["test_a"]["judgment"]
        message = results["test_a"]["message"]
        ax3.text(0.5, 0.6, f"판정: {judgment}", ha='center', va='center',
                fontsize=16, weight='bold')
        ax3.text(0.5, 0.4, message, ha='center', va='center',
                fontsize=12, wrap=True)
        ax3.text(0.5, 0.2, f"R² = {metrics['r2']:.6f}", ha='center', va='center',
                fontsize=14, family='monospace')
        ax3.axis('off')
        ax3.set_title('Test A: 판정')

    # Test B (Most Important!)
    if "test_b" in results:
        ax4 = plt.subplot(3, 3, 4)
        history = results["test_b"]["history"]
        epochs = range(1, len(history["loss"]) + 1)
        ax4.plot(epochs, history["loss"], 'b-', label='Train Loss', alpha=0.7)
        ax4.plot(epochs, history["val_loss"], 'r-', label='Val Loss', alpha=0.7)
        ax4.set_xlabel('Epoch')
        ax4.set_ylabel('Loss (MSE)')
        ax4.set_title('Test B: 10-step Training History')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        ax5 = plt.subplot(3, 3, 5)
        per_step = results["test_b"]["metrics"]["per_step"]
        steps = [s["step"] for s in per_step]
        r2_values = [s["r2"] for s in per_step]
        ax5.plot(steps, r2_values, 'o-', color='darkgreen', linewidth=2, markersize=8)
        ax5.axhline(y=0.5, color='red', linestyle='--', label='Target: 0.5')
        ax5.set_xlabel('Prediction Step')
        ax5.set_ylabel('R²')
        ax5.set_title('Test B: Per-Step R²')
        ax5.legend()
        ax5.grid(True, alpha=0.3)

        ax6 = plt.subplot(3, 3, 6)
        overall_r2 = results["test_b"]["metrics"]["overall"]["r2"]
        judgment = results["test_b"]["judgment"]
        decision = results["test_b"]["decision"]
        message = results["test_b"]["message"]

        color = 'green' if overall_r2 > 0.5 else 'orange' if overall_r2 > 0.3 else 'red'
        ax6.text(0.5, 0.7, f"판정: {judgment}", ha='center', va='center',
                fontsize=16, weight='bold', color=color)
        ax6.text(0.5, 0.55, f"결정: {decision}", ha='center', va='center',
                fontsize=14, weight='bold')
        ax6.text(0.5, 0.4, message, ha='center', va='center',
                fontsize=10, wrap=True)
        ax6.text(0.5, 0.2, f"Overall R² = {overall_r2:.6f}", ha='center', va='center',
                fontsize=14, family='monospace')
        ax6.axis('off')
        ax6.set_title('Test B: 판정 ⭐ 핵심')

    # Test C
    if "test_c" in results:
        ax7 = plt.subplot(3, 3, 7)
        history = results["test_c"]["history"]
        epochs = range(1, len(history["loss"]) + 1)
        ax7.plot(epochs, history["loss"], 'b-', label='Train Loss', alpha=0.7)
        ax7.plot(epochs, history["val_loss"], 'r-', label='Val Loss', alpha=0.7)
        ax7.set_xlabel('Epoch')
        ax7.set_ylabel('Loss (MSE)')
        ax7.set_title('Test C: 고주파 Training History')
        ax7.legend()
        ax7.grid(True, alpha=0.3)

        ax8 = plt.subplot(3, 3, 8)
        metrics = results["test_c"]["metrics"]
        phase4_r2 = results["test_c"]["phase4_r2"]
        improvement = results["test_c"]["improvement"]

        ax8.bar(['Phase 4', 'Test C'], [phase4_r2, metrics['r2']],
               color=['gray', 'green' if improvement > 0 else 'red'],
               alpha=0.7)
        ax8.axhline(y=0.1, color='blue', linestyle='--', label='Target: 0.1')
        ax8.set_ylabel('R²')
        ax8.set_title(f'Test C: R² Comparison (Δ={improvement:+.4f})')
        ax8.legend()
        ax8.grid(True, alpha=0.3, axis='y')

        ax9 = plt.subplot(3, 3, 9)
        judgment = results["test_c"]["judgment"]
        message = results["test_c"]["message"]
        ax9.text(0.5, 0.6, f"판정: {judgment}", ha='center', va='center',
                fontsize=16, weight='bold')
        ax9.text(0.5, 0.4, message, ha='center', va='center',
                fontsize=12, wrap=True)
        ax9.text(0.5, 0.2, f"R² = {metrics['r2']:.6f}", ha='center', va='center',
                fontsize=14, family='monospace')
        ax9.axis('off')
        ax9.set_title('Test C: 판정')

    plt.tight_layout()

    output_file = output_dir / "lstm_test_results.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Saved visualization: {output_file}")
    plt.close()


def generate_markdown_report(results: Dict, output_dir: Path):
    """
    마크다운 보고서 생성
    """
    report_file = output_dir / "lstm_test_results.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# LSTM Quick Test 결과\n\n")
        f.write(f"**실행 일시**: {results['timestamp']}\n")
        f.write(f"**데이터**: {results['area']} 소구역\n")
        f.write(f"**Sequence Length**: {results['seq_length']}\n\n")
        f.write("---\n\n")

        # Test A
        if "test_a" in results:
            f.write("## Test A: 1-step-ahead 예측 (Baseline)\n\n")
            f.write("**목표**: R² > 0.99\n\n")

            metrics = results["test_a"]["metrics"]
            f.write("### 결과\n\n")
            f.write("| 지표 | 값 |\n")
            f.write("|------|-----|\n")
            f.write(f"| R² | **{metrics['r2']:.6f}** |\n")
            f.write(f"| RMSE | {metrics['rmse']:.6f} |\n")
            f.write(f"| MAE | {metrics['mae']:.6f} |\n")
            f.write(f"| Test samples | {metrics['n_samples']:,} |\n\n")

            f.write(f"### 판정: {results['test_a']['judgment']}\n\n")
            f.write(f"{results['test_a']['message']}\n\n")
            f.write("---\n\n")

        # Test B (CRITICAL)
        if "test_b" in results:
            f.write("## Test B: 10-step 비재귀 예측 ⭐ 핵심\n\n")
            f.write("**목표**: R² > 0.5\n")
            f.write("**의미**: Recursive prediction 회피 효과 검증\n\n")

            overall = results["test_b"]["metrics"]["overall"]
            f.write("### 전체 결과\n\n")
            f.write("| 지표 | 값 |\n")
            f.write("|------|-----|\n")
            f.write(f"| Overall R² | **{overall['r2']:.6f}** |\n")
            f.write(f"| Overall RMSE | {overall['rmse']:.6f} |\n")
            f.write(f"| Overall MAE | {overall['mae']:.6f} |\n")
            f.write(f"| Test samples | {overall['n_samples']:,} |\n\n")

            f.write("### Step별 R²\n\n")
            f.write("| Step | R² | MAE |\n")
            f.write("|------|-----|-----|\n")
            for step in results["test_b"]["metrics"]["per_step"]:
                f.write(f"| {step['step']} | {step['r2']:.6f} | {step['mae']:.6f} |\n")
            f.write("\n")

            f.write(f"### 판정: {results['test_b']['judgment']}\n\n")
            f.write(f"**결정**: {results['test_b']['decision']}\n\n")
            f.write(f"{results['test_b']['message']}\n\n")

            # Decision explanation
            r2 = overall['r2']
            f.write("### 의사결정\n\n")
            if r2 > 0.5:
                f.write("✅ **Phase 5 진행 권장**\n\n")
                f.write("- 10-step 비재귀 예측이 R² > 0.5 달성\n")
                f.write("- Recursive prediction 문제 회피 가능성 확인\n")
                f.write("- Transformer/LSTM 접근법 유망\n")
                f.write("- 성공 확률: 60-70%\n\n")
            elif r2 > 0.3:
                f.write("⚠️ **Step 3 확인 후 신중히 결정**\n\n")
                f.write("- 10-step R²가 목표에 미달하나 가능성 있음\n")
                f.write("- Step 3 양방향 보간 결과 확인 필요\n")
                f.write("- 성공 확률: 40-60%\n\n")
            else:
                f.write("❌ **Phase 5 진행 불권장**\n\n")
                f.write("- 10-step 비재귀 예측 실패\n")
                f.write("- Transformer/LSTM도 근본적 한계 존재\n")
                f.write("- 다른 접근법 모색 필요\n\n")

            f.write("---\n\n")

        # Test C
        if "test_c" in results:
            f.write("## Test C: 고주파 예측 가능성\n\n")
            f.write("**목표**: R² > 0.1 (Phase 4: 0.0216)\n")
            f.write("**의미**: 고주파 성분이 예측 가능한지 검증\n\n")

            metrics = results["test_c"]["metrics"]
            f.write("### 결과\n\n")
            f.write("| 지표 | 값 |\n")
            f.write("|------|-----|\n")
            f.write(f"| R² | **{metrics['r2']:.6f}** |\n")
            f.write(f"| RMSE | {metrics['rmse']:.6f} |\n")
            f.write(f"| MAE | {metrics['mae']:.6f} |\n")
            f.write(f"| 고주파 분산 비중 | {results['test_c']['high_freq_variance_pct']:.2f}% |\n\n")

            f.write("### Phase 4 비교\n\n")
            f.write("| | Phase 4 | Test C | 개선 |\n")
            f.write("|--|---------|--------|------|\n")
            phase4_r2 = results["test_c"]["phase4_r2"]
            improvement = results["test_c"]["improvement"]
            f.write(f"| R² | {phase4_r2:.4f} | {metrics['r2']:.4f} | {improvement:+.4f} |\n\n")

            f.write(f"### 판정: {results['test_c']['judgment']}\n\n")
            f.write(f"{results['test_c']['message']}\n\n")
            f.write("---\n\n")

        # Summary
        f.write("## 📊 종합 결과\n\n")

        # Create summary table
        f.write("| Test | 목표 | 결과 | 판정 |\n")
        f.write("|------|------|------|------|\n")

        if "test_a" in results:
            r2 = results["test_a"]["metrics"]["r2"]
            f.write(f"| Test A (1-step) | R² > 0.99 | {r2:.6f} | "
                   f"{results['test_a']['judgment']} |\n")

        if "test_b" in results:
            r2 = results["test_b"]["metrics"]["overall"]["r2"]
            f.write(f"| **Test B (10-step)** ⭐ | **R² > 0.5** | **{r2:.6f}** | "
                   f"**{results['test_b']['judgment']}** |\n")

        if "test_c" in results:
            r2 = results["test_c"]["metrics"]["r2"]
            f.write(f"| Test C (고주파) | R² > 0.1 | {r2:.6f} | "
                   f"{results['test_c']['judgment']} |\n")

        f.write("\n")

        # Final recommendation
        if "test_b" in results:
            decision = results["test_b"]["decision"]
            f.write("## 🎯 최종 권고사항\n\n")

            if decision == "GO":
                f.write("### ✅ Phase 5 진행 권장\n\n")
                f.write("**근거**:\n")
                f.write("- Test B에서 10-step 비재귀 예측 성공 (R² > 0.5)\n")
                f.write("- Recursive prediction 문제 회피 가능성 확인\n")
                f.write("- LSTM/Transformer 접근법이 Phase 4 문제 해결 가능\n\n")
                f.write("**다음 단계**:\n")
                f.write("1. Step 3: Bidirectional Interpolation POC 실행\n")
                f.write("2. 양방향 효과 확인 후 Phase 5 본격 진행\n")
                f.write("3. Phase 5-A: Bidirectional LSTM Interpolation 구현\n\n")
            elif decision == "CAUTIOUS":
                f.write("### ⚠️ 신중한 검토 필요\n\n")
                f.write("**근거**:\n")
                f.write("- Test B 결과가 목표에 약간 미달\n")
                f.write("- 하이퍼파라미터 튜닝으로 개선 가능성 있음\n")
                f.write("- Step 3 결과 확인 후 최종 결정\n\n")
                f.write("**다음 단계**:\n")
                f.write("1. Step 3: Bidirectional Interpolation POC 실행 (필수)\n")
                f.write("2. R² > 0.1이면 Phase 5 진행 고려\n")
                f.write("3. R² < 0이면 포기 검토\n\n")
            else:
                f.write("### ❌ Phase 5 진행 불권장\n\n")
                f.write("**근거**:\n")
                f.write("- Test B에서 10-step 비재귀 예측 실패\n")
                f.write("- LSTM도 Phase 4와 동일한 한계 존재\n")
                f.write("- Transformer/LSTM 접근법으로 문제 해결 불가능\n\n")
                f.write("**대안**:\n")
                f.write("1. Gap 허용 정책 수립 (현실적 접근)\n")
                f.write("2. 다른 데이터 소스 확보\n")
                f.write("3. 물리 모델 기반 접근 검토\n\n")

        f.write("---\n\n")
        f.write(f"**보고서 생성**: {results['timestamp']}\n")
        f.write(f"**결과 파일**: lstm_test_results.json, lstm_test_results.png\n")

    print(f"✓ Saved report: {report_file}")


def main():
    args = parse_args()

    print("="*70)
    print("Step 2: Simple LSTM Quick Test")
    print("="*70)
    print(f"Area: {args.area}")
    print(f"Sequence Length: {args.seq_length}")
    print(f"Test: {args.test}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch Size: {args.batch_size}")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Load data
    print("\n" + "="*70)
    print("Loading data...")
    print("="*70)
    df, pressure = load_pressure_data(args.area)

    # Results dictionary
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "area": args.area,
        "seq_length": args.seq_length,
        "data_size": len(pressure),
        "epochs": args.epochs,
        "batch_size": args.batch_size
    }

    # Run tests
    if args.test in ["A", "all"]:
        results["test_a"] = test_a_one_step_ahead(
            pressure, args.seq_length, args.epochs, args.batch_size
        )

    if args.test in ["B", "all"]:
        results["test_b"] = test_b_ten_step_nonrecursive(
            pressure, args.seq_length, args.epochs, args.batch_size
        )

    if args.test in ["C", "all"]:
        results["test_c"] = test_c_high_frequency(
            pressure, args.seq_length, args.epochs, args.batch_size, args.v_valley
        )

    # Save results
    print("\n" + "="*70)
    print("Saving results...")
    print("="*70)

    json_file = output_dir / "lstm_test_results.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved JSON: {json_file}")

    # Visualize
    visualize_test_results(results, output_dir)

    # Generate report
    generate_markdown_report(results, output_dir)

    # Final summary
    print("\n" + "="*70)
    print("🎉 Step 2 완료!")
    print("="*70)

    if "test_b" in results:
        r2 = results["test_b"]["metrics"]["overall"]["r2"]
        decision = results["test_b"]["decision"]
        print(f"\n⭐ 핵심 결과 (Test B):")
        print(f"   10-step R² = {r2:.6f}")
        print(f"   결정: {decision}")

        if decision == "GO":
            print(f"\n✅ Phase 5 진행 권장")
        elif decision == "CAUTIOUS":
            print(f"\n⚠️ Step 3 확인 후 결정")
        else:
            print(f"\n❌ Phase 5 진행 불권장")

    print(f"\n📁 결과 파일:")
    print(f"   - {json_file}")
    print(f"   - {output_dir / 'lstm_test_results.md'}")
    print(f"   - {output_dir / 'lstm_test_results.png'}")


if __name__ == "__main__":
    main()
