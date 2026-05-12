#!/usr/bin/env python3
"""
Spectral Matching Gap Fill - Main Integration Pipeline

주파수 스펙트럼 보존 기반 Gap 채우기
- 저주파: ARMA synthesis
- 고주파: Random Phase IFFT
- Edge smoothing
- 재조합
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.signal import butter, filtfilt
from typing import Tuple, Optional
import argparse
import json
from datetime import datetime

# Import our modules
from arma_synthesis import arma_spectral_synthesis
from random_phase_synthesis import random_phase_synthesis
from edge_smoothing import edge_smoothing


def frequency_separation(data: np.ndarray,
                         v_valley_minutes: float = 553.5,
                         sampling_rate: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    주파수 분리 (저주파/고주파)

    Butterworth low-pass/high-pass filter 사용

    Args:
        data: 시계열 데이터
        v_valley_minutes: V-valley cutoff (분 단위)
        sampling_rate: 샘플링 주파수 (1.0 = 1분)

    Returns:
        (low_freq, high_freq): 저주파 성분, 고주파 성분
    """
    print(f"\n=== Frequency Separation ===")
    print(f"Data length: {len(data)}")
    print(f"V-valley: {v_valley_minutes} minutes")

    # Nyquist frequency
    nyquist_freq = 0.5 * sampling_rate

    # Cutoff frequency (cycles per minute)
    cutoff_freq = 1.0 / v_valley_minutes
    normalized_cutoff = cutoff_freq / nyquist_freq

    print(f"Cutoff frequency: {cutoff_freq:.6f} cycles/min")
    print(f"Normalized cutoff: {normalized_cutoff:.6f}")

    # Butterworth filter (order 4)
    order = 4

    # Low-pass filter
    b_low, a_low = butter(order, normalized_cutoff, btype='low')
    low_freq = filtfilt(b_low, a_low, data)

    # High-pass filter
    b_high, a_high = butter(order, normalized_cutoff, btype='high')
    high_freq = filtfilt(b_high, a_high, data)

    print(f"\n✓ Frequency separation complete")
    print(f"  Low-freq - Mean: {np.mean(low_freq):.4f}, Std: {np.std(low_freq):.4f}")
    print(f"  High-freq - Mean: {np.mean(high_freq):.4f}, Std: {np.std(high_freq):.4f}")

    # Verification
    reconstructed = low_freq + high_freq
    reconstruction_error = np.mean(np.abs(data - reconstructed))
    print(f"  Reconstruction error: {reconstruction_error:.6f}")

    return low_freq, high_freq


def spectral_matching_gap_fill(data: np.ndarray,
                                gap_start: int,
                                gap_end: int,
                                v_valley: float = 553.5,
                                arma_order: Optional[Tuple[int, int]] = None,
                                edge_window_low: int = 60,
                                edge_window_high: int = 20,
                                random_seed: Optional[int] = None) -> np.ndarray:
    """
    Spectral Matching Gap Fill - Main Pipeline

    Args:
        data: 전체 시계열 데이터 (gap 포함)
        gap_start: Gap 시작 인덱스
        gap_end: Gap 끝 인덱스
        v_valley: V-valley cutoff (분)
        arma_order: ARMA 차수 (None이면 자동)
        edge_window_low: 저주파 edge smoothing window
        edge_window_high: 고주파 edge smoothing window
        random_seed: Random seed

    Returns:
        Gap이 채워진 시계열
    """
    print("="*70)
    print("SPECTRAL MATCHING GAP FILL")
    print("="*70)
    print(f"Total data length: {len(data)}")
    print(f"Gap: [{gap_start}:{gap_end}], length: {gap_end - gap_start}")

    gap_length = gap_end - gap_start

    # Data 분할
    before = data[:gap_start]
    after = data[gap_end:]

    print(f"\nBefore: {len(before)} points")
    print(f"After: {len(after)} points")

    # =================================================================
    # Step 1: 주파수 분리
    # =================================================================
    print(f"\n{'='*70}")
    print("STEP 1: Frequency Separation")
    print(f"{'='*70}")

    # Before/After 데이터 결합 (reference)
    reference = np.concatenate([before[-600:], after[:600]])  # 전후 600 points
    print(f"Reference length: {len(reference)}")

    low_ref, high_ref = frequency_separation(reference, v_valley)

    # =================================================================
    # Step 2: 저주파 ARMA 합성
    # =================================================================
    print(f"\n{'='*70}")
    print("STEP 2: Low-Frequency ARMA Synthesis")
    print(f"{'='*70}")

    # Before/After 저주파 성분
    low_before, _ = frequency_separation(before, v_valley)
    low_after, _ = frequency_separation(after, v_valley)

    # ARMA 합성
    low_gap = arma_spectral_synthesis(
        before=low_before[-300:],  # 마지막 300개
        after=low_after[:300],      # 처음 300개
        gap_length=gap_length,
        order=arma_order
    )

    # =================================================================
    # Step 3: 고주파 Random Phase 합성
    # =================================================================
    print(f"\n{'='*70}")
    print("STEP 3: High-Frequency Random Phase Synthesis")
    print(f"{'='*70}")

    # High-frequency reference
    high_gap = random_phase_synthesis(
        reference=high_ref,
        gap_length=gap_length,
        preserve_psd=True,
        seed=random_seed
    )

    # =================================================================
    # Step 4: Edge Smoothing
    # =================================================================
    print(f"\n{'='*70}")
    print("STEP 4: Edge Smoothing")
    print(f"{'='*70}")

    # 저주파 edge smoothing
    print("\n4.1 Low-frequency edge smoothing")
    low_gap_smoothed = edge_smoothing(
        gap=low_gap,
        before=low_before,
        after=low_after,
        window_size=edge_window_low,
        window_type='kaiser'
    )

    # 고주파 edge smoothing
    print("\n4.2 High-frequency edge smoothing")
    _, high_before = frequency_separation(before, v_valley)
    _, high_after = frequency_separation(after, v_valley)

    high_gap_smoothed = edge_smoothing(
        gap=high_gap,
        before=high_before,
        after=high_after,
        window_size=edge_window_high,
        window_type='kaiser'
    )

    # =================================================================
    # Step 5: 재조합
    # =================================================================
    print(f"\n{'='*70}")
    print("STEP 5: Recombination")
    print(f"{'='*70}")

    gap_filled = low_gap_smoothed + high_gap_smoothed

    print(f"\nFilled gap statistics:")
    print(f"  Mean: {np.mean(gap_filled):.4f}")
    print(f"  Std: {np.std(gap_filled):.4f}")
    print(f"  Min/Max: [{np.min(gap_filled):.4f}, {np.max(gap_filled):.4f}]")

    # 전체 데이터 재구성
    filled_data = data.copy()
    filled_data[gap_start:gap_end] = gap_filled

    print(f"\n{'='*70}")
    print("✓ Spectral matching gap fill COMPLETE")
    print(f"{'='*70}")

    return filled_data


def load_pressure_data(area: str, data_path: Optional[Path] = None) -> pd.DataFrame:
    """
    압력 데이터 로드

    Args:
        area: 소구역 (e.g., "0243")
        data_path: 데이터 경로 (None이면 자동)

    Returns:
        압력 데이터 DataFrame
    """
    if data_path is None:
        data_path = Path(__file__).parent.parent.parent / "data" / "raw"

    csv_file = data_path / f"{area} 소구역 압력 데이터.csv"

    if not csv_file.exists():
        raise FileNotFoundError(f"Data file not found: {csv_file}")

    df = pd.read_csv(csv_file)
    print(f"✓ Loaded: {csv_file}")
    print(f"  Rows: {len(df):,}")

    return df


def extract_pressure_series(df: pd.DataFrame) -> np.ndarray:
    """
    DataFrame에서 압력 시계열 추출

    Args:
        df: 압력 데이터 DataFrame

    Returns:
        압력 시계열 (numpy array)
    """
    # 압력 컬럼 찾기
    pressure_col = None
    for col in ['wtrprsr', '압력', 'pressure', 'PRESSURE', 'Pressure', '압력(kPa)']:
        if col in df.columns:
            pressure_col = col
            break

    if pressure_col is None:
        raise ValueError(f"Pressure column not found. Available: {df.columns.tolist()}")

    pressure = df[pressure_col].values
    print(f"✓ Extracted pressure series: {len(pressure):,} points")
    print(f"  Mean: {np.mean(pressure):.2f} kPa")
    print(f"  Std: {np.std(pressure):.2f} kPa")
    print(f"  Range: [{np.min(pressure):.2f}, {np.max(pressure):.2f}] kPa")

    return pressure


def create_artificial_gap(pressure: np.ndarray,
                          gap_days: int,
                          gap_start_ratio: float = 0.4) -> Tuple[int, int]:
    """
    인위적 Gap 생성 (테스트용)

    Args:
        pressure: 압력 시계열
        gap_days: Gap 일수
        gap_start_ratio: Gap 시작 위치 (전체의 몇 %에서 시작)

    Returns:
        (gap_start, gap_end): Gap 시작/끝 인덱스
    """
    # 1분 간격 가정
    points_per_day = 1440
    gap_points = gap_days * points_per_day

    gap_start = int(len(pressure) * gap_start_ratio)
    gap_end = gap_start + gap_points

    # 범위 검증
    if gap_end >= len(pressure):
        raise ValueError(f"Gap too large: end {gap_end} >= data length {len(pressure)}")

    print(f"\n=== Artificial Gap Created ===")
    print(f"Gap days: {gap_days}")
    print(f"Gap points: {gap_points:,}")
    print(f"Gap: [{gap_start}:{gap_end}]")
    print(f"Gap position: {gap_start_ratio*100:.0f}% of data")

    return gap_start, gap_end


def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description="Spectral Matching Gap Fill")
    parser.add_argument("--area", type=str, default="0243", help="소구역")
    parser.add_argument("--gap-days", type=int, default=3, help="Gap 일수 (3, 7, 14, 24)")
    parser.add_argument("--v-valley", type=float, default=553.5, help="V-valley cutoff (분)")
    parser.add_argument("--edge-window-low", type=int, default=60, help="저주파 edge window")
    parser.add_argument("--edge-window-high", type=int, default=20, help="고주파 edge window")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="출력 디렉토리")

    args = parser.parse_args()

    # Output directory
    if args.output is None:
        output_dir = Path(__file__).parent / "results" / f"gap_{args.gap_days}days"
    else:
        output_dir = Path(args.output)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("SPECTRAL MATCHING GAP FILL - TEST")
    print("="*70)
    print(f"Area: {args.area}")
    print(f"Gap days: {args.gap_days}")
    print(f"V-valley: {args.v_valley} minutes")
    print(f"Output: {output_dir}")
    print("="*70)

    # Load data
    df = load_pressure_data(args.area)
    pressure = extract_pressure_series(df)

    # Create artificial gap
    gap_start, gap_end = create_artificial_gap(pressure, args.gap_days)

    # Save original gap (ground truth)
    gap_true = pressure[gap_start:gap_end].copy()

    # Fill gap
    pressure_filled = spectral_matching_gap_fill(
        data=pressure,
        gap_start=gap_start,
        gap_end=gap_end,
        v_valley=args.v_valley,
        edge_window_low=args.edge_window_low,
        edge_window_high=args.edge_window_high,
        random_seed=args.seed
    )

    gap_pred = pressure_filled[gap_start:gap_end]

    # Save results
    results = {
        "area": args.area,
        "gap_days": args.gap_days,
        "gap_start": int(gap_start),
        "gap_end": int(gap_end),
        "gap_length": int(gap_end - gap_start),
        "v_valley_minutes": args.v_valley,
        "edge_window_low": args.edge_window_low,
        "edge_window_high": args.edge_window_high,
        "random_seed": args.seed,
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "gap_true": {
                "mean": float(np.mean(gap_true)),
                "std": float(np.std(gap_true)),
                "min": float(np.min(gap_true)),
                "max": float(np.max(gap_true))
            },
            "gap_pred": {
                "mean": float(np.mean(gap_pred)),
                "std": float(np.std(gap_pred)),
                "min": float(np.min(gap_pred)),
                "max": float(np.max(gap_pred))
            },
            "comparison": {
                "mean_diff": float(abs(np.mean(gap_true) - np.mean(gap_pred))),
                "std_ratio": float(np.std(gap_pred) / np.std(gap_true)),
                "variance_ratio": float(np.var(gap_pred) / np.var(gap_true))
            }
        }
    }

    results_file = output_dir / "spectral_gap_fill_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Results saved: {results_file}")

    # Save filled data
    np.save(output_dir / "pressure_filled.npy", pressure_filled)
    np.save(output_dir / "gap_true.npy", gap_true)
    np.save(output_dir / "gap_pred.npy", gap_pred)

    print(f"✓ Data saved: {output_dir}")

    print("\n" + "="*70)
    print("STATISTICS SUMMARY")
    print("="*70)
    print(f"Gap True  - Mean: {np.mean(gap_true):.4f}, Std: {np.std(gap_true):.4f}")
    print(f"Gap Pred  - Mean: {np.mean(gap_pred):.4f}, Std: {np.std(gap_pred):.4f}")
    print(f"Mean Diff: {abs(np.mean(gap_true) - np.mean(gap_pred)):.4f}")
    print(f"Std Ratio: {np.std(gap_pred) / np.std(gap_true):.4f}")
    print("="*70)


if __name__ == "__main__":
    main()
