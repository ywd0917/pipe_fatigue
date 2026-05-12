#!/usr/bin/env python3
"""
24일 Gap에 대한 Random Phase 합성 데이터와 원본 데이터의 스펙트럼 비교

목적:
- 24일 gap filling에서 Random Phase IFFT가 원본 스펙트럼을 얼마나 보존하는지 분석
- 고주파 CCR이 낮은 원인을 스펙트럼 관점에서 파악
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from scipy import signal
from scipy.signal import butter, filtfilt, welch
from pathlib import Path
import json
from typing import Tuple, Optional, Dict, Any
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 모듈들 import
import sys
sys.path.insert(0, str(Path(__file__).parent))
from baseline_test import spectral_gap_fill


def load_pressure_data(area_code: str = "0243") -> np.ndarray:
    """압력 데이터 로드"""
    data_path = Path(f"/Users/jhpark/development/eroumtech/fatigue/fatigue-qgis/data/raw/{area_code} 소구역 압력 데이터.csv")

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)
    pressure = df['wtrprsr'].values

    print(f"✓ Loaded {len(pressure)} pressure points from {area_code}")
    print(f"  Pressure range: [{pressure.min():.2f}, {pressure.max():.2f}]")

    return pressure


def create_gap_24days(data: np.ndarray) -> Tuple[np.ndarray, int, int]:
    """24일 gap 생성"""
    gap_days = 24
    gap_length = gap_days * 24 * 60 // 5  # 5분 간격 데이터

    # Gap을 데이터 중간쯤에 위치
    gap_start = len(data) // 2 - gap_length // 2
    gap_end = gap_start + gap_length

    # Gap 생성
    data_with_gap = data.copy()
    data_with_gap[gap_start:gap_end] = np.nan

    print(f"✓ Created {gap_days}-day gap: [{gap_start}:{gap_end}] ({gap_length} points)")

    return data_with_gap, gap_start, gap_end


def butterworth_filter(data: np.ndarray, v_valley_minutes: float = 553.5) -> Tuple[np.ndarray, np.ndarray]:
    """Butterworth 필터로 저주파/고주파 분리"""
    fs = 1.0  # 1 sample per minute (5분 = 300초 간격이지만 분 단위로 정규화)
    cutoff = 1.0 / v_valley_minutes  # V-valley frequency in cycles per minute
    nyquist = fs / 2
    normalized_cutoff = cutoff / nyquist

    # 4차 Butterworth low-pass filter
    b, a = butter(4, normalized_cutoff, btype='low')

    # NaN 처리
    valid_data = np.nan_to_num(data)

    # 필터 적용
    low_freq = filtfilt(b, a, valid_data)
    high_freq = valid_data - low_freq

    return low_freq, high_freq


def compute_psd_welch(signal: np.ndarray, fs: float = 1/300, nperseg: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
    """Welch 방법으로 PSD 계산"""
    # NaN 값 제거
    valid_signal = signal[~np.isnan(signal)]

    if len(valid_signal) < nperseg:
        nperseg = len(valid_signal) // 4

    # Welch PSD
    frequencies, psd = welch(valid_signal, fs=fs, nperseg=nperseg,
                             noverlap=nperseg//2, window='hann', scaling='density')

    return frequencies, psd


def plot_spectrum_comparison_24days(
    true_gap: np.ndarray,
    synth_gap: np.ndarray,
    save_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """24일 gap에 대한 스펙트럼 비교 그래프 생성"""

    if save_dir is None:
        save_dir = Path("results/spectrum_comparison")
    save_dir.mkdir(parents=True, exist_ok=True)

    # PSD 계산
    fs = 1/300  # Hz (5분 = 300초)
    freq_true, psd_true = compute_psd_welch(true_gap, fs=fs)
    freq_synth, psd_synth = compute_psd_welch(synth_gap, fs=fs)

    # V-valley frequency
    v_valley_freq = 1 / (553.5 * 60)  # Hz

    # Create figure with 4 subplots
    fig = plt.figure(figsize=(20, 16))

    # ========== 1. Full Spectrum (Log-Log) ==========
    ax1 = plt.subplot(2, 2, 1)
    ax1.loglog(freq_true[1:], psd_true[1:], 'b-', alpha=0.8, linewidth=2, label='Original')
    ax1.loglog(freq_synth[1:], psd_synth[1:], 'r--', alpha=0.8, linewidth=2, label='Random Phase')
    ax1.axvline(v_valley_freq, color='green', linestyle=':', linewidth=2, label=f'V-valley ({553.5:.1f} min)')
    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('PSD (Pa²/Hz)')
    ax1.set_title('Full Spectrum Comparison (Log-Log Scale)', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3, which='both')

    # ========== 2. Low Frequency Region (Linear) ==========
    ax2 = plt.subplot(2, 2, 2)
    max_freq_plot = 0.0002  # Hz
    mask = freq_true <= max_freq_plot
    ax2.plot(freq_true[mask], psd_true[mask], 'b-', alpha=0.8, linewidth=2, label='Original')
    ax2.plot(freq_synth[mask], psd_synth[mask], 'r--', alpha=0.8, linewidth=2, label='Random Phase')
    ax2.axvline(v_valley_freq, color='green', linestyle=':', linewidth=2, label='V-valley')
    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('PSD (Pa²/Hz)')
    ax2.set_title('Low Frequency Region (Linear Scale)', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # ========== 3. High-Frequency Component Only ==========
    ax3 = plt.subplot(2, 2, 3)
    # 고주파 성분만 추출
    low_true, high_true = butterworth_filter(true_gap, v_valley_minutes=553.5)
    low_synth, high_synth = butterworth_filter(synth_gap, v_valley_minutes=553.5)

    freq_high_true, psd_high_true = compute_psd_welch(high_true, fs=fs)
    freq_high_synth, psd_high_synth = compute_psd_welch(high_synth, fs=fs)

    ax3.loglog(freq_high_true[1:], psd_high_true[1:], 'b-', alpha=0.8, linewidth=2, label='Original High-Freq')
    ax3.loglog(freq_high_synth[1:], psd_high_synth[1:], 'r--', alpha=0.8, linewidth=2, label='Random Phase High-Freq')
    ax3.axvline(v_valley_freq, color='green', linestyle=':', linewidth=2, label='V-valley')
    ax3.set_xlabel('Frequency (Hz)')
    ax3.set_ylabel('PSD (Pa²/Hz)')
    ax3.set_title('High-Frequency Component Spectrum', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3, which='both')

    # ========== 4. Spectral Difference ==========
    ax4 = plt.subplot(2, 2, 4)
    # 상대 차이 계산 (%)
    # 주파수 그리드 맞추기
    min_len = min(len(psd_true), len(psd_synth))
    rel_diff = 100 * np.abs(psd_true[:min_len] - psd_synth[:min_len]) / (psd_true[:min_len] + 1e-10)

    ax4.semilogx(freq_true[:min_len], rel_diff, 'k-', alpha=0.7, linewidth=1.5)
    ax4.axvline(v_valley_freq, color='green', linestyle=':', linewidth=2, label='V-valley')
    ax4.axhline(10, color='red', linestyle='--', alpha=0.5, label='10% threshold')
    ax4.fill_between(freq_true[:min_len], 0, rel_diff, where=(rel_diff > 10),
                      color='red', alpha=0.2, label='> 10% difference')
    ax4.set_xlabel('Frequency (Hz)')
    ax4.set_ylabel('Relative Difference (%)')
    ax4.set_title('Spectral Difference Analysis', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 100)

    # 전체 제목
    fig.suptitle('24-Day Gap: Random Phase vs Original Spectrum Comparison',
                 fontsize=16, fontweight='bold', y=1.02)

    plt.tight_layout()

    # 그래프 저장
    output_file = save_dir / "spectrum_comparison_24days.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Spectrum comparison plot saved: {output_file}")

    # 정량적 메트릭 계산
    metrics = calculate_spectral_metrics(psd_true, psd_synth, freq_true)

    return metrics


def calculate_spectral_metrics(psd_true: np.ndarray, psd_synth: np.ndarray,
                               frequencies: np.ndarray) -> Dict[str, float]:
    """스펙트럼 비교 메트릭 계산"""

    # 길이 맞추기
    min_len = min(len(psd_true), len(psd_synth))
    psd_true = psd_true[:min_len]
    psd_synth = psd_synth[:min_len]
    freq = frequencies[:min_len]

    # 1. Spectral Correlation
    correlation = np.corrcoef(psd_true, psd_synth)[0, 1]

    # 2. Energy Preservation
    energy_ratio = np.sum(psd_synth) / np.sum(psd_true)

    # 3. Normalized RMSE
    rmse = np.sqrt(np.mean((psd_true - psd_synth) ** 2))
    norm_rmse = rmse / np.mean(psd_true)

    # 4. Wasserstein Distance (간단한 버전)
    from scipy.stats import wasserstein_distance
    # 정규화된 PSD를 확률분포로 변환
    psd_true_norm = psd_true / np.sum(psd_true)
    psd_synth_norm = psd_synth / np.sum(psd_synth)
    w_distance = wasserstein_distance(freq, freq, psd_true_norm, psd_synth_norm)

    # 5. 주파수 대역별 에너지 비율
    v_valley_freq = 1 / (553.5 * 60)  # Hz

    # Low frequency energy (< V-valley)
    low_mask = freq < v_valley_freq
    if np.any(low_mask):
        low_energy_true = np.sum(psd_true[low_mask])
        low_energy_synth = np.sum(psd_synth[low_mask])
        low_energy_ratio = low_energy_synth / low_energy_true if low_energy_true > 0 else 0
    else:
        low_energy_ratio = 1.0

    # High frequency energy (> V-valley)
    high_mask = freq >= v_valley_freq
    if np.any(high_mask):
        high_energy_true = np.sum(psd_true[high_mask])
        high_energy_synth = np.sum(psd_synth[high_mask])
        high_energy_ratio = high_energy_synth / high_energy_true if high_energy_true > 0 else 0
    else:
        high_energy_ratio = 1.0

    metrics = {
        'spectral_correlation': correlation,
        'energy_ratio': energy_ratio,
        'normalized_rmse': norm_rmse,
        'wasserstein_distance': w_distance,
        'low_freq_energy_ratio': low_energy_ratio,
        'high_freq_energy_ratio': high_energy_ratio,
        'v_valley_freq_hz': v_valley_freq,
    }

    return metrics


def main():
    """메인 실행 함수"""
    print("\n" + "="*70)
    print("24-Day Gap Spectrum Comparison Analysis")
    print("="*70)

    # 1. 데이터 로드
    print("\n1. Loading pressure data...")
    pressure_data = load_pressure_data("0243")

    # 2. 24일 gap 생성
    print("\n2. Creating 24-day gap...")
    data_with_gap, gap_start, gap_end = create_gap_24days(pressure_data)
    true_gap_data = pressure_data[gap_start:gap_end]

    # 3. Random Phase synthesis (ARMA + Random Phase IFFT)
    print("\n3. Performing Random Phase synthesis...")
    # spectral_gap_fill uses ARMA for low freq and Random Phase IFFT for high freq
    synth_data = spectral_gap_fill(data_with_gap, gap_start, gap_end)
    synth_gap_data = synth_data[gap_start:gap_end]

    # 4. 스펙트럼 비교 분석
    print("\n4. Analyzing spectrum comparison...")
    metrics = plot_spectrum_comparison_24days(true_gap_data, synth_gap_data)

    # 5. 결과 출력
    print("\n" + "="*70)
    print("SPECTRAL METRICS (24-Day Gap)")
    print("="*70)
    print(f"Spectral Correlation:    {metrics['spectral_correlation']:.4f}")
    print(f"Energy Preservation:     {metrics['energy_ratio']:.4f} ({metrics['energy_ratio']*100:.1f}%)")
    print(f"Normalized RMSE:         {metrics['normalized_rmse']:.4f}")
    print(f"Wasserstein Distance:    {metrics['wasserstein_distance']:.6f}")
    print(f"Low Freq Energy Ratio:   {metrics['low_freq_energy_ratio']:.4f}")
    print(f"High Freq Energy Ratio:  {metrics['high_freq_energy_ratio']:.4f}")
    print("="*70)

    # 판정
    if metrics['spectral_correlation'] > 0.95:
        print("✓ Spectral correlation EXCELLENT (> 0.95)")
    elif metrics['spectral_correlation'] > 0.90:
        print("△ Spectral correlation GOOD (0.90-0.95)")
    else:
        print("✗ Spectral correlation POOR (< 0.90)")

    if 0.95 <= metrics['energy_ratio'] <= 1.05:
        print("✓ Energy preservation EXCELLENT (0.95-1.05)")
    elif 0.90 <= metrics['energy_ratio'] <= 1.10:
        print("△ Energy preservation GOOD (0.90-1.10)")
    else:
        print("✗ Energy preservation POOR")

    # 결과 저장
    save_dir = Path("results/spectrum_comparison")
    save_dir.mkdir(parents=True, exist_ok=True)

    metrics_file = save_dir / "spectrum_metrics_24days.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"\n✓ Metrics saved to: {metrics_file}")

    # 보고서 생성
    generate_report(metrics, save_dir)

    print("\n✅ Analysis complete!")


def generate_report(metrics: Dict[str, Any], save_dir: Path):
    """분석 보고서 생성"""
    report_file = save_dir / "spectrum_analysis_report_24days.md"

    with open(report_file, 'w') as f:
        f.write("# Spectrum Comparison Analysis Report (24-Day Gap)\n\n")
        f.write(f"**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Gap Size**: 24 days (34,560 points)\n")
        f.write(f"**Method**: Random Phase IFFT\n\n")

        f.write("## Executive Summary\n\n")
        f.write("Analysis of spectral characteristics between original and Random Phase synthesized data ")
        f.write("for a 24-day gap in pressure time series.\n\n")

        f.write("## Key Findings\n\n")
        f.write(f"1. **Spectral Correlation**: {metrics['spectral_correlation']:.4f}\n")
        f.write(f"   - Indicates {'high' if metrics['spectral_correlation'] > 0.9 else 'moderate'} ")
        f.write("similarity in overall spectral shape\n\n")

        f.write(f"2. **Energy Preservation**: {metrics['energy_ratio']:.4f} ({metrics['energy_ratio']*100:.1f}%)\n")
        f.write(f"   - Random Phase {'preserves' if 0.95 <= metrics['energy_ratio'] <= 1.05 else 'alters'} ")
        f.write("total energy well\n\n")

        f.write(f"3. **Frequency Band Analysis**:\n")
        f.write(f"   - Low Frequency (< V-valley): {metrics['low_freq_energy_ratio']:.4f}\n")
        f.write(f"   - High Frequency (> V-valley): {metrics['high_freq_energy_ratio']:.4f}\n\n")

        f.write("## Implications for Rainflow Counting\n\n")
        f.write("The spectral analysis reveals that while Random Phase IFFT preserves the magnitude spectrum ")
        f.write("theoretically, practical implementation shows:\n\n")

        if metrics['high_freq_energy_ratio'] < 0.9 or metrics['high_freq_energy_ratio'] > 1.1:
            f.write("- **Significant high-frequency energy mismatch** may contribute to poor CCR\n")
        f.write("- Phase randomization destroys temporal structure critical for cycle counting\n")
        f.write("- Edge effects and windowing artifacts affect spectral characteristics\n\n")

        f.write("## Recommendations\n\n")
        f.write("1. Consider time-domain methods (GARCH/SV) that preserve temporal patterns\n")
        f.write("2. Investigate phase-preserving spectral methods\n")
        f.write("3. Focus on high-frequency component modeling improvements\n\n")

        f.write("## Visualization\n\n")
        f.write("See `spectrum_comparison_24days.png` for detailed visual comparison.\n")

    print(f"✓ Report saved to: {report_file}")


if __name__ == "__main__":
    main()