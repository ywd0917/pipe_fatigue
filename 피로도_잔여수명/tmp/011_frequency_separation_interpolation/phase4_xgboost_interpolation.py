#!/usr/bin/env python3
"""
Phase 4: XGBoost 기반 주파수 분리 보간

Phase 3 결과 (고주파 패턴 존재) 기반:
- 저주파: XGBoost (ACF 0.9997, 높은 예측 가능성)
- 고주파: XGBoost (ACF 0.0746, 패턴 존재하나 약함)
- 재조합: low_freq + high_freq
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import timedelta
from typing import Tuple, Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.signal import butter, filtfilt

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

# 009 utils 추가
utils_dir = Path(__file__).parent.parent / "009_prophet_poc" / "utils"
sys.path.insert(0, str(utils_dir))

# Imports
import data_loader
import evaluation
import visualization

# V-valley constants
VALLEY_PERIOD = 553.5  # minutes


def pass_filter(
    data: np.ndarray,
    sampling_rate: float,
    file_name: str = "temp",
    v_valley_minutes: float = 553.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    V-valley 지점 기준으로 저주파/고주파 분리 (Butterworth filter)

    Args:
        data: 압력 데이터
        sampling_rate: 샘플링 주기 (분 단위)
        file_name: 파일 이름 (로그용)
        v_valley_minutes: V-valley 지점 (분 단위, 기본값 553.5)

    Returns:
        (low_pass, high_pass) 튜플
    """
    nyquist_freq = 1 / (2 * sampling_rate)
    cutoff_freq = 1 / v_valley_minutes

    if cutoff_freq >= nyquist_freq:
        print(f"경고: Cutoff 주파수({cutoff_freq:.6f})가 Nyquist 주파수({nyquist_freq:.6f})보다 높습니다.")
        cutoff_freq = nyquist_freq * 0.99

    normalized_cutoff = cutoff_freq / nyquist_freq

    # 4차 Butterworth 필터
    b_low, a_low = butter(4, normalized_cutoff, btype="low")
    b_high, a_high = butter(4, normalized_cutoff, btype="high")

    # Zero-phase filtering
    low_pass = filtfilt(b_low, a_low, data)
    high_pass = filtfilt(b_high, a_high, data)

    return low_pass, high_pass


def create_features_past_n(data: np.ndarray, n: int = 60) -> Tuple[np.ndarray, np.ndarray]:
    """
    Past N개 레코드를 feature로 사용

    Args:
        data: 시계열 데이터 (1D array)
        n: 과거 몇 개 레코드를 사용할지 (기본값: 60 = 5시간)

    Returns:
        X: (len(data) - n, n) shape의 feature matrix
        y: (len(data) - n,) shape의 target vector
    """
    X = []
    y = []

    for i in range(n, len(data)):
        X.append(data[i-n:i])
        y.append(data[i])

    return np.array(X), np.array(y)


def train_xgboost_model(X_train: np.ndarray,
                        y_train: np.ndarray,
                        X_val: np.ndarray = None,
                        y_val: np.ndarray = None) -> xgb.XGBRegressor:
    """
    XGBoost 회귀 모델 학습

    Args:
        X_train: 학습 feature matrix
        y_train: 학습 target vector
        X_val: 검증 feature matrix (optional)
        y_val: 검증 target vector (optional)

    Returns:
        학습된 XGBoost 모델
    """
    # 하이퍼파라미터 (010 프로젝트 최적값 참조)
    params = {
        'n_estimators': 300,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 3,
        'gamma': 0.1,
        'random_state': 42,
        'n_jobs': -1,
        'verbosity': 0
    }

    model = xgb.XGBRegressor(**params)

    # 학습 (early stopping 제거 - 버전 호환성)
    model.fit(X_train, y_train)

    return model


def predict_gap_recursive(model: xgb.XGBRegressor,
                          before_context: np.ndarray,
                          n_points: int,
                          past_n: int = 60) -> np.ndarray:
    """
    Gap 구간을 recursive하게 예측

    Args:
        model: 학습된 XGBoost 모델
        before_context: Gap 직전 past_n개 레코드
        n_points: Gap 길이
        past_n: feature 개수

    Returns:
        예측된 Gap 값들
    """
    predictions = []
    context = before_context.copy()

    for _ in range(n_points):
        # 마지막 past_n개를 feature로 사용
        X = context[-past_n:].reshape(1, -1)

        # 예측
        pred = model.predict(X)[0]
        predictions.append(pred)

        # Context 업데이트 (rolling window)
        context = np.append(context, pred)

    return np.array(predictions)


def xgboost_freq_separation_interpolation(df: pd.DataFrame,
                                          gap_start: str,
                                          gap_end: str,
                                          area: str = '0243',
                                          past_n: int = 60) -> dict:
    """
    XGBoost 기반 주파수 분리 보간

    Args:
        df: 전체 압력 데이터
        gap_start: Gap 시작 시간
        gap_end: Gap 종료 시간
        area: 지역 코드
        past_n: Feature로 사용할 과거 레코드 수

    Returns:
        dict with interpolated data and metrics
    """
    print(f"\n=== XGBoost Frequency Separation Interpolation ===")
    print(f"Gap: {gap_start} ~ {gap_end}")
    print(f"Past N features: {past_n}")

    # 1. 원본 데이터 준비
    df_with_gap = df.copy()
    gap_mask = (df_with_gap['datetime'] >= gap_start) & (df_with_gap['datetime'] <= gap_end)

    # Ground truth 저장
    ground_truth = df_with_gap.loc[gap_mask, 'pressure'].values
    n_gap_points = len(ground_truth)

    print(f"Gap size: {n_gap_points} points ({n_gap_points * 5 / 60:.1f} hours)")

    # Gap 생성
    df_with_gap.loc[gap_mask, 'pressure'] = np.nan

    # Gap 직전/직후 인덱스
    gap_start_idx = df_with_gap[df_with_gap['datetime'] == gap_start].index[0]
    gap_end_idx = df_with_gap[df_with_gap['datetime'] == gap_end].index[0]

    # Gap 직전 데이터만 사용 (학습 데이터)
    train_data = df.iloc[:gap_start_idx]

    if len(train_data) < past_n + 1000:
        raise ValueError(f"학습 데이터가 부족합니다 (필요: {past_n + 1000}, 실제: {len(train_data)})")

    print(f"Training data size: {len(train_data)} points")

    # 2. 주파수 분리 (학습 데이터)
    pressure_train = train_data['pressure'].values

    print("\n--- Frequency Separation ---")
    low_train, high_train = pass_filter(
        pressure_train,
        sampling_rate=5.0,  # 5분 간격
        file_name=area,
        v_valley_minutes=VALLEY_PERIOD
    )

    print(f"Low freq: mean={np.mean(low_train):.4f}, std={np.std(low_train):.4f}")
    print(f"High freq: mean={np.mean(high_train):.6f}, std={np.std(high_train):.4f}")

    # 3. 저주파 XGBoost 학습
    print("\n--- Low Frequency XGBoost ---")
    X_low_train, y_low_train = create_features_past_n(low_train, n=past_n)

    # Train/validation split (마지막 20%를 validation)
    n_train = int(len(X_low_train) * 0.8)
    X_low_tr, X_low_val = X_low_train[:n_train], X_low_train[n_train:]
    y_low_tr, y_low_val = y_low_train[:n_train], y_low_train[n_train:]

    print(f"Training samples: {len(X_low_tr)}, Validation: {len(X_low_val)}")

    model_low = train_xgboost_model(X_low_tr, y_low_tr, X_low_val, y_low_val)

    # Validation 성능
    y_low_val_pred = model_low.predict(X_low_val)
    r2_low_val = r2_score(y_low_val, y_low_val_pred)
    mae_low_val = mean_absolute_error(y_low_val, y_low_val_pred)

    print(f"Low freq validation: R²={r2_low_val:.4f}, MAE={mae_low_val:.4f}")

    # 4. 고주파 XGBoost 학습
    print("\n--- High Frequency XGBoost ---")
    X_high_train, y_high_train = create_features_past_n(high_train, n=past_n)

    n_train = int(len(X_high_train) * 0.8)
    X_high_tr, X_high_val = X_high_train[:n_train], X_high_train[n_train:]
    y_high_tr, y_high_val = y_high_train[:n_train], y_high_train[n_train:]

    print(f"Training samples: {len(X_high_tr)}, Validation: {len(X_high_val)}")

    model_high = train_xgboost_model(X_high_tr, y_high_tr, X_high_val, y_high_val)

    # Validation 성능
    y_high_val_pred = model_high.predict(X_high_val)
    r2_high_val = r2_score(y_high_val, y_high_val_pred)
    mae_high_val = mean_absolute_error(y_high_val, y_high_val_pred)

    print(f"High freq validation: R²={r2_high_val:.4f}, MAE={mae_high_val:.4f}")

    # 5. Gap 예측
    print("\n--- Gap Prediction ---")

    # Gap 직전 past_n개 context
    low_before_context = low_train[-(past_n + 100):][-past_n:]  # 안전하게
    high_before_context = high_train[-(past_n + 100):][-past_n:]

    # Recursive prediction
    low_gap_pred = predict_gap_recursive(model_low, low_before_context, n_gap_points, past_n)
    high_gap_pred = predict_gap_recursive(model_high, high_before_context, n_gap_points, past_n)

    # 재조합
    interpolated = low_gap_pred + high_gap_pred

    print(f"Predicted gap: mean={np.mean(interpolated):.4f}, std={np.std(interpolated):.4f}")
    print(f"Ground truth: mean={np.mean(ground_truth):.4f}, std={np.std(ground_truth):.4f}")

    # 6. 평가
    print("\n--- Evaluation ---")

    # 전체 재조합 성능
    mse = mean_squared_error(ground_truth, interpolated)
    mae = mean_absolute_error(ground_truth, interpolated)
    r2 = r2_score(ground_truth, interpolated)

    print(f"Overall: R²={r2:.4f}, MAE={mae:.4f}, MSE={mse:.6f}")

    # 에너지 보존 (variance)
    energy_original = np.var(ground_truth)
    energy_interpolated = np.var(interpolated)
    energy_preservation = (energy_interpolated / energy_original * 100) if energy_original > 0 else 0

    print(f"Energy preservation: {energy_preservation:.2f}%")

    # 저주파/고주파 각각의 성능
    # Ground truth도 주파수 분리
    full_pressure = df['pressure'].values
    low_full, high_full = pass_filter(
        full_pressure,
        sampling_rate=5.0,
        file_name=area,
        v_valley_minutes=VALLEY_PERIOD
    )

    low_gt = low_full[gap_start_idx:gap_end_idx+1]
    high_gt = high_full[gap_start_idx:gap_end_idx+1]

    r2_low = r2_score(low_gt, low_gap_pred)
    mae_low = mean_absolute_error(low_gt, low_gap_pred)

    r2_high = r2_score(high_gt, high_gap_pred)
    mae_high = mean_absolute_error(high_gt, high_gap_pred)

    print(f"\nLow freq gap: R²={r2_low:.4f}, MAE={mae_low:.4f}")
    print(f"High freq gap: R²={r2_high:.4f}, MAE={mae_high:.4f}")

    # 7. 결과 반환
    return {
        'interpolated': interpolated,
        'ground_truth': ground_truth,
        'low_pred': low_gap_pred,
        'high_pred': high_gap_pred,
        'low_gt': low_gt,
        'high_gt': high_gt,
        'metrics': {
            'r2': r2,
            'mae': mae,
            'mse': mse,
            'energy_preservation': energy_preservation,
            'r2_low': r2_low,
            'mae_low': mae_low,
            'r2_high': r2_high,
            'mae_high': mae_high,
            'r2_low_val': r2_low_val,
            'mae_low_val': mae_low_val,
            'r2_high_val': r2_high_val,
            'mae_high_val': mae_high_val
        },
        'gap_start': gap_start,
        'gap_end': gap_end,
        'n_gap_points': n_gap_points,
        'method': 'XGBoost Frequency Separation',
        'past_n': past_n
    }


def visualize_results(result: dict, output_path: Path):
    """
    결과 시각화

    Args:
        result: xgboost_freq_separation_interpolation 반환값
        output_path: 저장 경로
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    x = np.arange(result['n_gap_points'])

    # 1. 전체 재조합
    ax = axes[0]
    ax.plot(x, result['ground_truth'], 'k-', label='Ground Truth', linewidth=2, alpha=0.7)
    ax.plot(x, result['interpolated'], 'r--', label='XGBoost Interpolation', linewidth=2)
    ax.set_title(f"Full Signal (R²={result['metrics']['r2']:.4f}, MAE={result['metrics']['mae']:.4f})", fontsize=12, fontweight='bold')
    ax.set_xlabel('Time Index (5min intervals)')
    ax.set_ylabel('Pressure')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. 저주파 성분
    ax = axes[1]
    ax.plot(x, result['low_gt'], 'k-', label='Low Freq GT', linewidth=2, alpha=0.7)
    ax.plot(x, result['low_pred'], 'b--', label='Low Freq Predicted', linewidth=2)
    ax.set_title(f"Low Frequency (R²={result['metrics']['r2_low']:.4f}, MAE={result['metrics']['mae_low']:.4f})", fontsize=12, fontweight='bold')
    ax.set_xlabel('Time Index (5min intervals)')
    ax.set_ylabel('Pressure')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. 고주파 성분
    ax = axes[2]
    ax.plot(x, result['high_gt'], 'k-', label='High Freq GT', linewidth=2, alpha=0.7)
    ax.plot(x, result['high_pred'], 'g--', label='High Freq Predicted', linewidth=2)
    ax.set_title(f"High Frequency (R²={result['metrics']['r2_high']:.4f}, MAE={result['metrics']['mae_high']:.4f})", fontsize=12, fontweight='bold')
    ax.set_xlabel('Time Index (5min intervals)')
    ax.set_ylabel('Pressure')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\nVisualization saved: {output_path}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='Phase 4: XGBoost 기반 주파수 분리 보간'
    )
    parser.add_argument('--area', default='0243', help='지역 코드 (기본값: 0243)')
    parser.add_argument('--gap-days', type=int, default=3, help='Gap 길이 (일, 기본값: 3)')
    parser.add_argument('--past-n', type=int, default=60, help='Feature 개수 (기본값: 60)')
    parser.add_argument('--output', default='results/phase4_xgboost/', help='결과 저장 디렉토리')

    args = parser.parse_args()

    # 출력 디렉토리 생성
    output_dir = Path(__file__).parent / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Phase 4: XGBoost 기반 주파수 분리 보간")
    print("=" * 80)
    print(f"Area: {args.area}")
    print(f"Gap days: {args.gap_days}")
    print(f"Past N features: {args.past_n}")
    print(f"Output: {output_dir}")

    # 1. 데이터 로드
    print("\n--- Loading Data ---")
    df = data_loader.load_pressure_data(args.area)

    # 컬럼명 변경 (msrmt_dt -> datetime, wtrprsr -> pressure)
    df = df.rename(columns={'msrmt_dt': 'datetime', 'wtrprsr': 'pressure'})

    print(f"Loaded {len(df)} records")
    print(f"Date range: {df['datetime'].min()} ~ {df['datetime'].max()}")

    # 2. Gap 정의
    gap_days = args.gap_days
    total_days = (df['datetime'].max() - df['datetime'].min()).days

    # 중간 지점에서 gap 생성
    middle_date = df['datetime'].min() + timedelta(days=total_days // 2)
    gap_start = middle_date.strftime('%Y-%m-%d %H:%M:%S')
    gap_end = (middle_date + timedelta(days=gap_days)).strftime('%Y-%m-%d %H:%M:%S')

    # 3. XGBoost 보간 실행
    result = xgboost_freq_separation_interpolation(
        df,
        gap_start,
        gap_end,
        area=args.area,
        past_n=args.past_n
    )

    # 4. 시각화
    output_plot = output_dir / f"xgboost_gap_{gap_days}days.png"
    visualize_results(result, output_plot)

    # 5. 결과 저장 (JSON)
    output_json = output_dir / f"xgboost_gap_{gap_days}days.json"

    result_serializable = {
        'gap_start': result['gap_start'],
        'gap_end': result['gap_end'],
        'n_gap_points': result['n_gap_points'],
        'method': result['method'],
        'past_n': result['past_n'],
        'metrics': result['metrics']
    }

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(result_serializable, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved: {output_json}")

    # 6. 요약
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Method: XGBoost Frequency Separation (past_{args.past_n})")
    print(f"Gap: {gap_days} days ({result['n_gap_points']} points)")
    print(f"\nOverall Performance:")
    print(f"  R²: {result['metrics']['r2']:.4f}")
    print(f"  MAE: {result['metrics']['mae']:.4f}")
    print(f"  Energy Preservation: {result['metrics']['energy_preservation']:.2f}%")
    print(f"\nComponent Performance:")
    print(f"  Low Freq:  R²={result['metrics']['r2_low']:.4f}, MAE={result['metrics']['mae_low']:.4f}")
    print(f"  High Freq: R²={result['metrics']['r2_high']:.4f}, MAE={result['metrics']['mae_high']:.4f}")
    print(f"\nValidation Performance:")
    print(f"  Low Freq:  R²={result['metrics']['r2_low_val']:.4f}, MAE={result['metrics']['mae_low_val']:.4f}")
    print(f"  High Freq: R²={result['metrics']['r2_high_val']:.4f}, MAE={result['metrics']['mae_high_val']:.4f}")

    # 성공 판정
    if result['metrics']['r2'] > 0.3:
        print("\n✅ SUCCESS: R² > 0.3 (목표 달성)")
    elif result['metrics']['r2'] > 0:
        print("\n⚠️ PARTIAL: R² > 0 (최소 기준 달성)")
    else:
        print("\n❌ FAILURE: R² < 0 (기준 미달)")

    print("=" * 80)


if __name__ == '__main__':
    main()
