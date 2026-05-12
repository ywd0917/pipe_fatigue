#!/usr/bin/env python3
"""
Validation Module for Spectral Gap Fill

검증 메트릭:
1. PSD Similarity > 95%
2. Variance Ratio 0.9-1.1
3. ACF Correlation > 0.9
4. Rainflow Match > 0.95 (최종 목표)
"""

import numpy as np
from scipy.fft import fft
from scipy.signal import welch
from scipy.stats import pearsonr
from statsmodels.tsa.stattools import acf
from typing import Dict, Tuple
import json
from pathlib import Path


def validate_psd_similarity(signal_true: np.ndarray,
                            signal_pred: np.ndarray,
                            fs: float = 1.0,
                            nperseg: int = 256) -> Dict:
    """
    PSD (Power Spectral Density) 유사도 검증

    Args:
        signal_true: 원본 신호
        signal_pred: 예측 신호
        fs: 샘플링 주파수
        nperseg: Welch method segment 길이

    Returns:
        PSD validation metrics
    """
    print(f"\n=== PSD Similarity Validation ===")

    # Welch method로 PSD 계산
    nperseg = min(nperseg, min(len(signal_true), len(signal_pred)) // 4)

    freqs_true, psd_true = welch(signal_true, fs=fs, nperseg=nperseg)
    freqs_pred, psd_pred = welch(signal_pred, fs=fs, nperseg=nperseg)

    # Frequency 범위 맞추기
    min_len = min(len(freqs_true), len(freqs_pred))
    freqs_true = freqs_true[:min_len]
    freqs_pred = freqs_pred[:min_len]
    psd_true = psd_true[:min_len]
    psd_pred = psd_pred[:min_len]

    # PSD 상관계수
    psd_corr, psd_pval = pearsonr(psd_true, psd_pred)

    # PSD similarity (normalized)
    # Cosine similarity
    psd_similarity = np.dot(psd_true, psd_pred) / (
        np.linalg.norm(psd_true) * np.linalg.norm(psd_pred)
    )

    # Energy preservation
    energy_true = np.sum(psd_true)
    energy_pred = np.sum(psd_pred)
    energy_ratio = energy_pred / energy_true

    results = {
        "psd_correlation": float(psd_corr),
        "psd_pvalue": float(psd_pval),
        "psd_similarity": float(psd_similarity),
        "energy_ratio": float(energy_ratio),
        "energy_preservation_pct": float(energy_ratio * 100)
    }

    print(f"  PSD Correlation: {psd_corr:.4f} (p={psd_pval:.4e})")
    print(f"  PSD Similarity: {psd_similarity:.4f}")
    print(f"  Energy Ratio: {energy_ratio:.4f} ({energy_ratio*100:.2f}%)")

    # 판정
    if psd_similarity > 0.95:
        print(f"  ✓ PSD Similarity PASS (> 0.95)")
    elif psd_similarity > 0.90:
        print(f"  △ PSD Similarity MARGINAL (> 0.90)")
    else:
        print(f"  ✗ PSD Similarity FAIL (< 0.90)")

    return results


def validate_variance_ratio(signal_true: np.ndarray,
                            signal_pred: np.ndarray) -> Dict:
    """
    분산 비율 검증

    Args:
        signal_true: 원본 신호
        signal_pred: 예측 신호

    Returns:
        Variance validation metrics
    """
    print(f"\n=== Variance Ratio Validation ===")

    var_true = np.var(signal_true)
    var_pred = np.var(signal_pred)
    var_ratio = var_pred / var_true

    std_true = np.std(signal_true)
    std_pred = np.std(signal_pred)
    std_ratio = std_pred / std_true

    results = {
        "variance_true": float(var_true),
        "variance_pred": float(var_pred),
        "variance_ratio": float(var_ratio),
        "std_true": float(std_true),
        "std_pred": float(std_pred),
        "std_ratio": float(std_ratio)
    }

    print(f"  Variance True: {var_true:.6f}")
    print(f"  Variance Pred: {var_pred:.6f}")
    print(f"  Variance Ratio: {var_ratio:.4f}")
    print(f"  Std Ratio: {std_ratio:.4f}")

    # 판정 (목표: 0.9-1.1)
    if 0.9 <= var_ratio <= 1.1:
        print(f"  ✓ Variance Ratio PASS (0.9-1.1)")
    elif 0.8 <= var_ratio <= 1.2:
        print(f"  △ Variance Ratio MARGINAL (0.8-1.2)")
    else:
        print(f"  ✗ Variance Ratio FAIL (< 0.8 or > 1.2)")

    return results


def validate_acf_correlation(signal_true: np.ndarray,
                             signal_pred: np.ndarray,
                             nlags: int = 100) -> Dict:
    """
    ACF (Autocorrelation Function) 상관관계 검증

    Args:
        signal_true: 원본 신호
        signal_pred: 예측 신호
        nlags: ACF lag 수

    Returns:
        ACF validation metrics
    """
    print(f"\n=== ACF Correlation Validation ===")

    # ACF 계산
    nlags = min(nlags, min(len(signal_true), len(signal_pred)) // 2)

    acf_true = acf(signal_true, nlags=nlags, fft=True)
    acf_pred = acf(signal_pred, nlags=nlags, fft=True)

    # ACF 상관계수
    acf_corr, acf_pval = pearsonr(acf_true, acf_pred)

    # ACF RMSE
    acf_rmse = np.sqrt(np.mean((acf_true - acf_pred)**2))

    results = {
        "acf_correlation": float(acf_corr),
        "acf_pvalue": float(acf_pval),
        "acf_rmse": float(acf_rmse),
        "nlags": int(nlags)
    }

    print(f"  ACF Correlation: {acf_corr:.4f} (p={acf_pval:.4e})")
    print(f"  ACF RMSE: {acf_rmse:.4f}")
    print(f"  Lags: {nlags}")

    # 판정 (목표: > 0.9)
    if acf_corr > 0.9:
        print(f"  ✓ ACF Correlation PASS (> 0.9)")
    elif acf_corr > 0.8:
        print(f"  △ ACF Correlation MARGINAL (> 0.8)")
    else:
        print(f"  ✗ ACF Correlation FAIL (< 0.8)")

    return results


def simple_rainflow_count(signal: np.ndarray) -> np.ndarray:
    """
    간단한 Rainflow Counting 구현 (4-point algorithm)

    Args:
        signal: 시계열 신호

    Returns:
        Rainflow cycles (amplitude, mean)
    """
    # 1. Peak/valley 추출
    peaks_valleys = extract_peaks_valleys(signal)

    if len(peaks_valleys) < 4:
        return np.array([])

    # 2. Rainflow counting (4-point algorithm)
    cycles = []
    stack = []

    for point in peaks_valleys:
        stack.append(point)

        while len(stack) >= 4:
            # X, Y, Z 분석
            X = abs(stack[-3] - stack[-2])
            Y = abs(stack[-2] - stack[-1])

            # Rainflow 조건: Y >= X
            if Y >= X:
                # Cycle 추출
                amplitude = X / 2
                mean_val = (stack[-3] + stack[-2]) / 2
                cycles.append((amplitude, mean_val))

                # Stack에서 제거
                stack.pop(-2)
                stack.pop(-2)
            else:
                break

    # Remaining cycles (residue)
    while len(stack) >= 3:
        X = abs(stack[0] - stack[1])
        amplitude = X / 2
        mean_val = (stack[0] + stack[1]) / 2
        cycles.append((amplitude, mean_val))
        stack.pop(0)

    return np.array(cycles)


def extract_peaks_valleys(signal: np.ndarray) -> np.ndarray:
    """
    Peak와 Valley 추출

    Args:
        signal: 시계열 신호

    Returns:
        Peak/valley 값들
    """
    peaks_valleys = [signal[0]]

    for i in range(1, len(signal) - 1):
        # Local maximum
        if signal[i] > signal[i-1] and signal[i] > signal[i+1]:
            peaks_valleys.append(signal[i])
        # Local minimum
        elif signal[i] < signal[i-1] and signal[i] < signal[i+1]:
            peaks_valleys.append(signal[i])

    peaks_valleys.append(signal[-1])

    return np.array(peaks_valleys)


def validate_rainflow_matching(signal_true: np.ndarray,
                                signal_pred: np.ndarray,
                                n_bins: int = 20) -> Dict:
    """
    Rainflow Counting 매칭 검증

    Args:
        signal_true: 원본 신호
        signal_pred: 예측 신호
        n_bins: Histogram bin 수

    Returns:
        Rainflow validation metrics
    """
    print(f"\n=== Rainflow Matching Validation ===")

    # Rainflow counting
    cycles_true = simple_rainflow_count(signal_true)
    cycles_pred = simple_rainflow_count(signal_pred)

    print(f"  Cycles True: {len(cycles_true)}")
    print(f"  Cycles Pred: {len(cycles_pred)}")

    if len(cycles_true) == 0 or len(cycles_pred) == 0:
        print("  ⚠ No cycles detected, skipping rainflow validation")
        return {
            "rainflow_match": 0.0,
            "cycles_true": 0,
            "cycles_pred": 0,
            "status": "insufficient_cycles"
        }

    # Amplitude histogram 비교
    amplitudes_true = cycles_true[:, 0]
    amplitudes_pred = cycles_pred[:, 0]

    # Histogram 생성
    bins = np.linspace(
        min(amplitudes_true.min(), amplitudes_pred.min()),
        max(amplitudes_true.max(), amplitudes_pred.max()),
        n_bins
    )

    hist_true, _ = np.histogram(amplitudes_true, bins=bins)
    hist_pred, _ = np.histogram(amplitudes_pred, bins=bins)

    # Normalize
    hist_true_norm = hist_true / (hist_true.sum() + 1e-10)
    hist_pred_norm = hist_pred / (hist_pred.sum() + 1e-10)

    # Histogram correlation
    hist_corr, hist_pval = pearsonr(hist_true_norm, hist_pred_norm)

    # Histogram similarity (cosine)
    hist_similarity = np.dot(hist_true_norm, hist_pred_norm) / (
        np.linalg.norm(hist_true_norm) * np.linalg.norm(hist_pred_norm) + 1e-10
    )

    # Chi-square distance
    chi2_dist = np.sum((hist_true_norm - hist_pred_norm)**2 / (hist_true_norm + hist_pred_norm + 1e-10))

    # Rainflow match score (weighted)
    rainflow_match = 0.7 * hist_similarity + 0.3 * hist_corr

    results = {
        "rainflow_match": float(rainflow_match),
        "hist_correlation": float(hist_corr),
        "hist_pvalue": float(hist_pval),
        "hist_similarity": float(hist_similarity),
        "chi2_distance": float(chi2_dist),
        "cycles_true": int(len(cycles_true)),
        "cycles_pred": int(len(cycles_pred)),
        "amplitude_mean_true": float(amplitudes_true.mean()),
        "amplitude_mean_pred": float(amplitudes_pred.mean()),
        "amplitude_std_true": float(amplitudes_true.std()),
        "amplitude_std_pred": float(amplitudes_pred.std())
    }

    print(f"  Rainflow Match: {rainflow_match:.4f}")
    print(f"  Hist Correlation: {hist_corr:.4f}")
    print(f"  Hist Similarity: {hist_similarity:.4f}")
    print(f"  Chi2 Distance: {chi2_dist:.4f}")
    print(f"  Amplitude Mean - True: {amplitudes_true.mean():.4f}, Pred: {amplitudes_pred.mean():.4f}")

    # 판정 (목표: > 0.95)
    if rainflow_match > 0.95:
        print(f"  ✓✓✓ Rainflow Match EXCELLENT (> 0.95) ⭐")
    elif rainflow_match > 0.90:
        print(f"  ✓✓ Rainflow Match GOOD (> 0.90)")
    elif rainflow_match > 0.85:
        print(f"  ✓ Rainflow Match MARGINAL (> 0.85)")
    else:
        print(f"  ✗ Rainflow Match FAIL (< 0.85)")

    return results


def validate_spectral_gap_fill(gap_true: np.ndarray,
                                gap_pred: np.ndarray,
                                output_dir: Path = None) -> Dict:
    """
    Spectral Gap Fill 전체 검증

    Args:
        gap_true: 원본 gap 데이터
        gap_pred: 예측 gap 데이터
        output_dir: 결과 저장 디렉토리

    Returns:
        모든 검증 메트릭
    """
    print("="*70)
    print("SPECTRAL GAP FILL VALIDATION")
    print("="*70)

    # 1. PSD Similarity
    psd_metrics = validate_psd_similarity(gap_true, gap_pred)

    # 2. Variance Ratio
    var_metrics = validate_variance_ratio(gap_true, gap_pred)

    # 3. ACF Correlation
    acf_metrics = validate_acf_correlation(gap_true, gap_pred)

    # 4. Rainflow Matching
    rainflow_metrics = validate_rainflow_matching(gap_true, gap_pred)

    # 통합 결과
    results = {
        "psd": psd_metrics,
        "variance": var_metrics,
        "acf": acf_metrics,
        "rainflow": rainflow_metrics,
        "overall_judgment": determine_overall_judgment(
            psd_metrics, var_metrics, acf_metrics, rainflow_metrics
        )
    }

    # 저장
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        validation_file = output_dir / "validation_results.json"
        with open(validation_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Validation results saved: {validation_file}")

    print("\n" + "="*70)
    print("OVERALL JUDGMENT")
    print("="*70)
    print(results["overall_judgment"]["summary"])
    print("="*70)

    return results


def determine_overall_judgment(psd_metrics: Dict,
                                var_metrics: Dict,
                                acf_metrics: Dict,
                                rainflow_metrics: Dict) -> Dict:
    """
    전체 판정

    Args:
        psd_metrics: PSD 메트릭
        var_metrics: Variance 메트릭
        acf_metrics: ACF 메트릭
        rainflow_metrics: Rainflow 메트릭

    Returns:
        전체 판정 결과
    """
    # 점수 계산
    scores = {
        "psd": psd_metrics["psd_similarity"],
        "variance": 1.0 - abs(1.0 - var_metrics["variance_ratio"]),
        "acf": acf_metrics["acf_correlation"],
        "rainflow": rainflow_metrics.get("rainflow_match", 0.0)
    }

    # 가중 평균 (Rainflow가 가장 중요)
    overall_score = (
        0.2 * scores["psd"] +
        0.2 * scores["variance"] +
        0.2 * scores["acf"] +
        0.4 * scores["rainflow"]  # Rainflow 40%
    )

    # 판정
    if overall_score > 0.95 and rainflow_metrics.get("rainflow_match", 0) > 0.95:
        judgment = "EXCELLENT"
        summary = "✓✓✓ 완전 성공 - Fatigue 계산 사용 가능 ⭐"
    elif overall_score > 0.90 and rainflow_metrics.get("rainflow_match", 0) > 0.90:
        judgment = "GOOD"
        summary = "✓✓ 부분 성공 - 통계 분석 사용 가능"
    elif overall_score > 0.85:
        judgment = "MARGINAL"
        summary = "✓ 한계적 성공 - 신중한 사용 필요"
    else:
        judgment = "FAIL"
        summary = "✗ 실패 - Gap 허용 정책 수립 필요"

    return {
        "overall_score": float(overall_score),
        "scores": scores,
        "judgment": judgment,
        "summary": summary
    }


if __name__ == "__main__":
    # Test validation
    print("Testing validation module...")

    # Load test data
    test_dir = Path(__file__).parent / "results" / "gap_3days"
    if not test_dir.exists():
        print(f"⚠ Test data not found: {test_dir}")
        print("Run spectral_gap_fill.py first to generate test data")
    else:
        gap_true = np.load(test_dir / "gap_true.npy")
        gap_pred = np.load(test_dir / "gap_pred.npy")

        results = validate_spectral_gap_fill(gap_true, gap_pred, test_dir)
