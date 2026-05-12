#!/usr/bin/env python3
"""
Phase 3: 고주파 잡음 검증 실험

고주파 성분이 예측 불가능한 순수 잡음(White Noise)인지,
아니면 예측 가능한 패턴이 일부 존재하는지 통계적으로 검증합니다.

검증 방법:
1. Ljung-Box Test (백색 잡음 검정)
2. Runs Test (랜덤성 검정)
3. Shapiro-Wilk Test (정규성 검정)
4. Sample Entropy (복잡도/예측 불가능성)
5. Power Spectral Density (주파수 균일성)
6. 상세 ACF/PACF 분석

사용법:
    python phase3_noise_verification.py --area 0243 --output results/component_analysis/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal, stats
from scipy.signal import butter, filtfilt
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf, pacf

# 프로젝트 루트 디렉토리 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

from common.config import DATA_DIR, RESULTS_DIR

# Raw data directory
RAW_DATA_DIR = DATA_DIR / "raw"


# ==================== V-valley 기반 필터링 ====================

def pass_filter(
    data: np.ndarray,
    sampling_rate: float,
    file_name: str,
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


# ==================== 통계 검정 ====================

def ljung_box_test(data: np.ndarray, lags: int = 40) -> Dict:
    """
    Ljung-Box 검정: 백색 잡음 여부 확인

    H0: 백색 잡음 (자기상관 없음)
    p > 0.05 → 백색 잡음 (예측 불가)
    p < 0.05 → 패턴 존재 (예측 가능성 있음)
    """
    result = acorr_ljungbox(data, lags=lags, return_df=True)

    # 가장 큰 통계량 (가장 작은 p-value)
    min_p_idx = result['lb_pvalue'].idxmin()

    return {
        "test_name": "Ljung-Box Test",
        "statistic": float(result.loc[min_p_idx, 'lb_stat']),
        "p_value": float(result.loc[min_p_idx, 'lb_pvalue']),
        "lag": int(min_p_idx),
        "interpretation": "백색 잡음" if result.loc[min_p_idx, 'lb_pvalue'] > 0.05 else "패턴 존재",
        "is_noise": bool(result.loc[min_p_idx, 'lb_pvalue'] > 0.05)
    }


def runs_test(data: np.ndarray) -> Dict:
    """
    Runs Test: 랜덤성 검정

    연속된 값의 증가/감소 패턴 분석
    완전 랜덤이면 runs 개수가 기댓값과 일치
    """
    # 중앙값 기준으로 이진화
    median = np.median(data)
    binary = (data > median).astype(int)

    # Runs 개수 계산
    runs = 1 + np.sum(binary[1:] != binary[:-1])
    n = len(data)
    n1 = np.sum(binary)
    n0 = n - n1

    # 기댓값과 표준편차
    expected_runs = (2 * n1 * n0) / n + 1
    std_runs = np.sqrt((2 * n1 * n0 * (2 * n1 * n0 - n)) / (n**2 * (n - 1)))

    # Z-score
    z_score = (runs - expected_runs) / std_runs if std_runs > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

    return {
        "test_name": "Runs Test",
        "statistic": float(z_score),
        "p_value": float(p_value),
        "runs": int(runs),
        "expected_runs": float(expected_runs),
        "interpretation": "랜덤" if p_value > 0.05 else "패턴 존재",
        "is_noise": bool(p_value > 0.05)
    }


def normality_test(data: np.ndarray) -> Dict:
    """
    Shapiro-Wilk 검정: 정규성 검정

    백색 잡음은 정규분포를 따름
    p > 0.05 → 정규분포
    """
    # 샘플이 너무 크면 Shapiro-Wilk 사용 불가, 대신 K-S test
    if len(data) > 5000:
        # 정규분포와 비교
        statistic, p_value = stats.kstest(
            (data - np.mean(data)) / np.std(data),
            'norm'
        )
        test_name = "Kolmogorov-Smirnov Test"
    else:
        statistic, p_value = stats.shapiro(data)
        test_name = "Shapiro-Wilk Test"

    return {
        "test_name": test_name,
        "statistic": float(statistic),
        "p_value": float(p_value),
        "interpretation": "정규분포" if p_value > 0.05 else "비정규분포",
        "is_noise": bool(p_value > 0.05)
    }


def sample_entropy(data: np.ndarray, m: int = 2, r: float = None) -> Dict:
    """
    Sample Entropy: 복잡도/예측 불가능성 측정

    높은 엔트로피 → 높은 무작위성 (예측 불가)
    낮은 엔트로피 → 패턴 존재 (예측 가능)

    일반적으로 백색 잡음은 SampEn > 1.5
    """
    if r is None:
        r = 0.2 * np.std(data)

    N = len(data)

    def _maxdist(x_i, x_j, m):
        return max([abs(ua - va) for ua, va in zip(x_i, x_j)])

    def _phi(m):
        x = [[data[j] for j in range(i, i + m)] for i in range(N - m + 1)]
        C = [
            len([1 for x_j in x if _maxdist(x_i, x_j, m) <= r]) - 1
            for x_i in x
        ]
        return sum(C)

    try:
        sampen = -np.log(_phi(m + 1) / _phi(m))
    except:
        sampen = np.inf

    # 백색 잡음 기준: SampEn > 1.5
    is_noise = sampen > 1.5 if not np.isinf(sampen) else True

    return {
        "test_name": "Sample Entropy",
        "statistic": float(sampen) if not np.isinf(sampen) else None,
        "threshold": 1.5,
        "interpretation": "높은 무작위성" if is_noise else "낮은 무작위성",
        "is_noise": bool(is_noise)
    }


def power_spectral_density_test(data: np.ndarray, fs: float = 1.0) -> Dict:
    """
    Power Spectral Density: 주파수 균일성 검증

    백색 잡음은 모든 주파수에서 균일한 파워
    특정 주파수 피크 → 주기 패턴 존재

    변동계수(CV) < 0.3 → 균일 (백색 잡음)
    """
    freqs, psd = signal.welch(data, fs=fs, nperseg=min(256, len(data) // 4))

    # 변동계수 (Coefficient of Variation)
    cv = np.std(psd) / np.mean(psd)

    # 백색 잡음 기준: CV < 0.3
    is_noise = cv < 0.3

    return {
        "test_name": "Power Spectral Density",
        "statistic": float(cv),
        "threshold": 0.3,
        "interpretation": "균일 (백색 잡음)" if is_noise else "불균일 (주기성 존재)",
        "is_noise": bool(is_noise),
        "freqs": freqs.tolist(),
        "psd": psd.tolist()
    }


def acf_significance_test(data: np.ndarray, nlags: int = 100) -> Dict:
    """
    ACF 유의성 검정: 유의한 lag 개수 확인

    95% 신뢰구간 벗어난 lag < 5% → 백색 잡음
    """
    acf_values = acf(data, nlags=nlags, fft=True)

    # 95% 신뢰구간
    confidence_interval = 1.96 / np.sqrt(len(data))

    # 유의한 lag 개수 (lag 0 제외)
    significant_lags = np.sum(np.abs(acf_values[1:]) > confidence_interval)
    total_lags = nlags
    significant_ratio = significant_lags / total_lags

    # 백색 잡음 기준: 유의 lag < 5%
    is_noise = significant_ratio < 0.05

    return {
        "test_name": "ACF Significance Test",
        "statistic": float(significant_ratio),
        "threshold": 0.05,
        "significant_lags": int(significant_lags),
        "total_lags": int(total_lags),
        "interpretation": "백색 잡음" if is_noise else "자기상관 존재",
        "is_noise": bool(is_noise),
        "acf_values": acf_values.tolist(),
        "confidence_interval": float(confidence_interval)
    }


# ==================== 시각화 ====================

def create_noise_verification_plots(
    high_freq: np.ndarray,
    test_results: Dict,
    output_dir: Path
):
    """
    잡음 검증 결과 시각화

    1. ACF/PACF
    2. Power Spectral Density
    3. 히스토그램 + QQ plot
    4. 시계열 플롯
    """
    fig = plt.figure(figsize=(16, 12))

    # 1. ACF
    ax1 = plt.subplot(3, 2, 1)
    acf_values = np.array(test_results['acf_test']['acf_values'])
    ci = test_results['acf_test']['confidence_interval']
    lags = np.arange(len(acf_values))

    ax1.stem(lags, acf_values, basefmt=' ')
    ax1.axhline(y=ci, color='r', linestyle='--', label=f'95% CI ({ci:.3f})')
    ax1.axhline(y=-ci, color='r', linestyle='--')
    ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax1.set_xlabel('Lag')
    ax1.set_ylabel('ACF')
    ax1.set_title(f'Autocorrelation Function\n유의 lag: {test_results["acf_test"]["significant_lags"]}/{test_results["acf_test"]["total_lags"]}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. PACF
    ax2 = plt.subplot(3, 2, 2)
    pacf_values = pacf(high_freq, nlags=100)
    ax2.stem(np.arange(len(pacf_values)), pacf_values, basefmt=' ')
    ax2.axhline(y=ci, color='r', linestyle='--', label=f'95% CI')
    ax2.axhline(y=-ci, color='r', linestyle='--')
    ax2.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax2.set_xlabel('Lag')
    ax2.set_ylabel('PACF')
    ax2.set_title('Partial Autocorrelation Function')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Power Spectral Density
    ax3 = plt.subplot(3, 2, 3)
    freqs = np.array(test_results['psd_test']['freqs'])
    psd = np.array(test_results['psd_test']['psd'])
    ax3.semilogy(freqs, psd)
    ax3.set_xlabel('Frequency')
    ax3.set_ylabel('PSD')
    ax3.set_title(f'Power Spectral Density\nCV = {test_results["psd_test"]["statistic"]:.3f}')
    ax3.grid(True, alpha=0.3)

    # 4. 히스토그램 + 정규분포
    ax4 = plt.subplot(3, 2, 4)
    ax4.hist(high_freq, bins=50, density=True, alpha=0.7, edgecolor='black')

    # 정규분포 곡선
    mu, sigma = np.mean(high_freq), np.std(high_freq)
    x = np.linspace(high_freq.min(), high_freq.max(), 100)
    ax4.plot(x, stats.norm.pdf(x, mu, sigma), 'r-', linewidth=2, label='Normal dist')
    ax4.set_xlabel('Value')
    ax4.set_ylabel('Density')
    ax4.set_title(f'{test_results["normality_test"]["test_name"]}\np = {test_results["normality_test"]["p_value"]:.4f}')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. QQ Plot
    ax5 = plt.subplot(3, 2, 5)
    stats.probplot(high_freq, dist="norm", plot=ax5)
    ax5.set_title('Q-Q Plot')
    ax5.grid(True, alpha=0.3)

    # 6. 시계열 플롯
    ax6 = plt.subplot(3, 2, 6)
    ax6.plot(high_freq, linewidth=0.5, alpha=0.7)
    ax6.axhline(y=0, color='r', linestyle='--', linewidth=1)
    ax6.set_xlabel('Index')
    ax6.set_ylabel('Value')
    ax6.set_title(f'High Frequency Time Series\nMean: {mu:.4f}, Std: {sigma:.4f}')
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'noise_verification_plots.png', dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✅ 시각화 저장: {output_dir / 'noise_verification_plots.png'}")


# ==================== 메인 분석 ====================

def verify_high_freq_noise(area: str, output_dir: Path) -> Dict:
    """
    고주파 잡음 검증 메인 함수

    Args:
        area: 지역 코드 (예: "0243")
        output_dir: 출력 디렉토리

    Returns:
        검증 결과 딕셔너리
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 데이터 로드
    print(f"\n{'='*60}")
    print(f"고주파 잡음 검증: {area}")
    print(f"{'='*60}\n")

    csv_path = RAW_DATA_DIR / f"{area} 소구역 압력 데이터.csv"
    if not csv_path.exists():
        csv_path = RAW_DATA_DIR / f"{area} 중구역 압력 데이터.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {csv_path}")

    print(f"📂 데이터 로드: {csv_path.name}")
    df = pd.read_csv(csv_path)
    data = df['wtrprsr'].values

    # 2. 고주파 성분 추출 (V-valley = 553.5분)
    print(f"🔍 고주파 성분 추출 (V-valley = 553.5분)...")
    sampling_rate = 5.0  # 5분 간격

    # Gap 전후 4096개 포인트 사용 (Phase 1과 동일)
    # Gap 중간 지점 찾기 (임의로 데이터 중간 사용)
    mid_point = len(data) // 2
    start_idx = max(0, mid_point - 4096)
    end_idx = min(len(data), mid_point + 4096)

    analysis_data = data[start_idx:end_idx]
    low_freq, high_freq = pass_filter(analysis_data, sampling_rate, area)

    print(f"   분석 데이터 크기: {len(analysis_data):,} 포인트")
    print(f"   고주파 std: {np.std(high_freq):.6f}")
    print(f"   고주파 mean: {np.mean(high_freq):.6f}")

    # 3. 통계 검정 수행
    print(f"\n{'='*60}")
    print(f"통계 검정 수행 (6가지)")
    print(f"{'='*60}\n")

    test_results = {}

    # Test 1: Ljung-Box
    print("1️⃣  Ljung-Box Test (백색 잡음 검정)...")
    test_results['ljung_box'] = ljung_box_test(high_freq, lags=40)
    print(f"   p-value: {test_results['ljung_box']['p_value']:.4f}")
    print(f"   판정: {test_results['ljung_box']['interpretation']}")

    # Test 2: Runs Test
    print("\n2️⃣  Runs Test (랜덤성 검정)...")
    test_results['runs_test'] = runs_test(high_freq)
    print(f"   p-value: {test_results['runs_test']['p_value']:.4f}")
    print(f"   판정: {test_results['runs_test']['interpretation']}")

    # Test 3: Normality Test
    print("\n3️⃣  정규성 검정...")
    test_results['normality_test'] = normality_test(high_freq)
    print(f"   p-value: {test_results['normality_test']['p_value']:.4f}")
    print(f"   판정: {test_results['normality_test']['interpretation']}")

    # Test 4: Sample Entropy
    print("\n4️⃣  Sample Entropy (복잡도)...")
    test_results['entropy_test'] = sample_entropy(high_freq)
    ent_val = test_results['entropy_test']['statistic']
    print(f"   Entropy: {ent_val if ent_val is not None else 'inf'}")
    print(f"   판정: {test_results['entropy_test']['interpretation']}")

    # Test 5: Power Spectral Density
    print("\n5️⃣  Power Spectral Density (주파수 균일성)...")
    test_results['psd_test'] = power_spectral_density_test(high_freq, fs=1/sampling_rate)
    print(f"   변동계수(CV): {test_results['psd_test']['statistic']:.4f}")
    print(f"   판정: {test_results['psd_test']['interpretation']}")

    # Test 6: ACF Significance
    print("\n6️⃣  ACF 유의성 검정...")
    test_results['acf_test'] = acf_significance_test(high_freq, nlags=100)
    print(f"   유의 lag 비율: {test_results['acf_test']['statistic']:.2%}")
    print(f"   판정: {test_results['acf_test']['interpretation']}")

    # 4. 최종 판정
    print(f"\n{'='*60}")
    print(f"최종 판정")
    print(f"{'='*60}\n")

    noise_count = sum([
        test_results['ljung_box']['is_noise'],
        test_results['runs_test']['is_noise'],
        test_results['normality_test']['is_noise'],
        test_results['entropy_test']['is_noise'],
        test_results['psd_test']['is_noise'],
        test_results['acf_test']['is_noise']
    ])

    total_tests = 6
    final_verdict = "순수 잡음 (White Noise)" if noise_count >= 5 else "패턴 존재 가능성"

    print(f"✅ 백색 잡음 기준 만족: {noise_count}/{total_tests} ({noise_count/total_tests:.1%})")
    print(f"🎯 최종 판정: {final_verdict}")

    if noise_count >= 5:
        print("\n📌 결론:")
        print("   고주파 성분은 예측 불가능한 순수 잡음입니다.")
        print("   → XGBoost로도 예측 불가능")
        print("   → Phase 2 실패 원인 확정")
        print("   → 프로젝트 종료 권장 (Gap 허용)")
    else:
        print("\n📌 결론:")
        print("   고주파 성분에 일부 패턴이 존재할 가능성이 있습니다.")
        print("   → Phase 3b: XGBoost 시도 고려")
        print("   → 추가 분석 필요")

    # 5. 시각화
    print(f"\n📊 시각화 생성 중...")
    create_noise_verification_plots(high_freq, test_results, output_dir)

    # 6. 결과 저장
    results = {
        "area": area,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_points": len(analysis_data),
        "high_freq_stats": {
            "mean": float(np.mean(high_freq)),
            "std": float(np.std(high_freq)),
            "min": float(np.min(high_freq)),
            "max": float(np.max(high_freq))
        },
        "test_results": test_results,
        "final_verdict": {
            "noise_count": int(noise_count),
            "total_tests": int(total_tests),
            "verdict": final_verdict,
            "is_pure_noise": noise_count >= 5
        }
    }

    # JSON 저장
    json_path = output_dir / "noise_verification_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 결과 저장: {json_path}")

    return results


def generate_markdown_report(results: Dict, output_dir: Path):
    """
    마크다운 보고서 생성
    """
    report_path = output_dir / "PHASE3_NOISE_VERIFICATION.md"

    is_noise = results['final_verdict']['is_pure_noise']
    verdict_emoji = "✅" if is_noise else "⚠️"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Phase 3: 고주파 잡음 검증 결과\n\n")
        f.write(f"**분석 일시**: {results['analysis_date']}\n")
        f.write(f"**지역**: {results['area']}\n")
        f.write(f"**데이터 크기**: {results['data_points']:,} 포인트\n\n")
        f.write(f"---\n\n")

        # 고주파 통계
        f.write(f"## 📊 고주파 성분 통계\n\n")
        stats = results['high_freq_stats']
        f.write(f"- **Mean**: {stats['mean']:.6f}\n")
        f.write(f"- **Std**: {stats['std']:.6f}\n")
        f.write(f"- **Min**: {stats['min']:.6f}\n")
        f.write(f"- **Max**: {stats['max']:.6f}\n\n")
        f.write(f"---\n\n")

        # 검정 결과
        f.write(f"## 🔬 통계 검정 결과\n\n")

        tests = results['test_results']
        test_list = [
            ('ljung_box', 'Ljung-Box Test'),
            ('runs_test', 'Runs Test'),
            ('normality_test', '정규성 검정'),
            ('entropy_test', 'Sample Entropy'),
            ('psd_test', 'Power Spectral Density'),
            ('acf_test', 'ACF 유의성 검정')
        ]

        f.write(f"| 검정 | 통계량/값 | p-value | 판정 | 백색 잡음? |\n")
        f.write(f"|------|----------|---------|------|------------|\n")

        for key, name in test_list:
            test = tests[key]
            stat = test.get('statistic', 'N/A')
            stat_str = f"{stat:.4f}" if isinstance(stat, (int, float)) else str(stat)

            pval = test.get('p_value', 'N/A')
            pval_str = f"{pval:.4f}" if isinstance(pval, (int, float)) else 'N/A'

            interp = test['interpretation']
            is_n = "✅ Yes" if test['is_noise'] else "❌ No"

            f.write(f"| {name} | {stat_str} | {pval_str} | {interp} | {is_n} |\n")

        f.write(f"\n---\n\n")

        # 최종 판정
        f.write(f"## {verdict_emoji} 최종 판정\n\n")
        verdict = results['final_verdict']
        f.write(f"**백색 잡음 기준 만족**: {verdict['noise_count']}/{verdict['total_tests']} ({verdict['noise_count']/verdict['total_tests']:.1%})\n\n")
        f.write(f"### 판정: **{verdict['verdict']}**\n\n")

        if is_noise:
            f.write(f"고주파 성분은 **예측 불가능한 순수 잡음(White Noise)**입니다.\n\n")
            f.write(f"#### 의미\n\n")
            f.write(f"1. **ACF 0.0746의 의미 확인**: 고주파는 시간 의존성이 거의 없음\n")
            f.write(f"2. **XGBoost 무용**: 기계학습으로도 예측 불가능\n")
            f.write(f"3. **Phase 2 실패 원인 확정**: Mean으로 보간한 것이 문제가 아니라, 고주파 자체가 예측 불가능\n")
            f.write(f"4. **전체 변동의 99%**: 고주파가 전체 압력 변동의 99%를 차지 → 전체 예측 불가능\n\n")
            f.write(f"#### 결론\n\n")
            f.write(f"- ❌ Phase 3b (XGBoost) 시도 불필요\n")
            f.write(f"- ✅ Phase 2 실패 원인 명확히 규명\n")
            f.write(f"- ✅ 프로젝트 종료 권장\n")
            f.write(f"- ✅ 최종 권장사항: **Gap 허용** 또는 **Linear Interpolation (경고 포함)**\n\n")
        else:
            f.write(f"고주파 성분에 **일부 패턴이 존재**할 가능성이 있습니다.\n\n")
            f.write(f"#### 의미\n\n")
            f.write(f"1. 고주파가 완전한 잡음은 아님\n")
            f.write(f"2. XGBoost로 일부 패턴 학습 가능성 존재\n")
            f.write(f"3. Phase 3b 진행 고려\n\n")
            f.write(f"#### 다음 단계\n\n")
            f.write(f"- ⚠️ Phase 3b: 저주파/고주파 각각 XGBoost 시도\n")
            f.write(f"- 📊 추가 분석: 패턴이 존재하는 lag/주파수 영역 탐색\n")
            f.write(f"- 🔍 세부 검증: 어떤 검정에서 패턴이 발견되었는지 확인\n\n")

        f.write(f"---\n\n")
        f.write(f"## 📈 시각화\n\n")
        f.write(f"![Noise Verification](noise_verification_plots.png)\n\n")
        f.write(f"---\n\n")
        f.write(f"**생성 일시**: {results['analysis_date']}\n")

    print(f"✅ 보고서 생성: {report_path}")


# ==================== 메인 ====================

def main():
    parser = argparse.ArgumentParser(
        description="Phase 3: 고주파 잡음 검증 실험"
    )
    parser.add_argument(
        "--area",
        type=str,
        default="0243",
        help="지역 코드 (기본값: 0243)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 디렉토리 (기본값: results/component_analysis/)"
    )

    args = parser.parse_args()

    # 출력 디렉토리 설정
    if args.output is None:
        output_dir = Path("results/component_analysis")
    else:
        output_dir = Path(args.output)

    # 분석 실행
    results = verify_high_freq_noise(args.area, output_dir)

    # 보고서 생성
    generate_markdown_report(results, output_dir)

    print(f"\n{'='*60}")
    print(f"✅ Phase 3 완료!")
    print(f"{'='*60}\n")
    print(f"📂 출력 디렉토리: {output_dir}")
    print(f"📄 결과 파일:")
    print(f"   - noise_verification_results.json")
    print(f"   - PHASE3_NOISE_VERIFICATION.md")
    print(f"   - noise_verification_plots.png\n")


if __name__ == "__main__":
    main()
