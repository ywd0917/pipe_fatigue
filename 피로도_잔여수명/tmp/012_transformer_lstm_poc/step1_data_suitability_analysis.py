#!/usr/bin/env python3
"""
Step 1: 데이터 적합성 분석

LSTM/Transformer 적용 전 데이터 구조 적합성 검증
- Stationarity (ADF/KPSS)
- PACF (자기상관 구조)
- Sample Entropy (복잡도)
- Sequence Length 실험
- Gap 분포 분석

종합 점수 (100점) 산출 및 GO/NO-GO 판정
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import datetime
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 통계 검정
from statsmodels.tsa.stattools import adfuller, kpss, acf, pacf

# 엔트로피 (antropy가 없으면 scipy로 대체)
try:
    import antropy
    HAS_ANTROPY = True
except ImportError:
    HAS_ANTROPY = False
    print("Warning: antropy not installed. Using scipy entropy instead.")

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

# 009 utils 추가
utils_dir = Path(__file__).parent.parent / "009_prophet_poc" / "utils"
sys.path.insert(0, str(utils_dir))

import data_loader


# ==================== 1. Stationarity 검증 ====================

def test_stationarity(data: np.ndarray) -> Dict:
    """
    ADF/KPSS Test로 정상성 검증

    Returns:
        dict with adf_pvalue, kpss_pvalue, score (0/10/20), judgment
    """
    print("\n=== 1. Stationarity 검증 ===")

    # ADF Test
    adf_result = adfuller(data)
    adf_pvalue = adf_result[1]
    adf_statistic = adf_result[0]

    print(f"ADF Test:")
    print(f"  Statistic: {adf_statistic:.4f}")
    print(f"  p-value: {adf_pvalue:.4f}")

    # KPSS Test
    kpss_result = kpss(data, regression='c', nlags='auto')
    kpss_pvalue = kpss_result[1]
    kpss_statistic = kpss_result[0]

    print(f"KPSS Test:")
    print(f"  Statistic: {kpss_statistic:.4f}")
    print(f"  p-value: {kpss_pvalue:.4f}")

    # 판정
    if adf_pvalue < 0.05 and kpss_pvalue > 0.05:
        judgment = "○ 정상"
        score = 20
        message = "차분 불필요, LSTM/Transformer 직접 적용 가능"
    elif adf_pvalue < 0.05 and kpss_pvalue < 0.05:
        judgment = "△ 약한 비정상"
        score = 10
        message = "차분 고려"
    else:
        judgment = "× 강한 비정상"
        score = 0
        message = "차분 필수"

    print(f"  → 판정: {judgment} ({score}점)")
    print(f"  → {message}")

    return {
        'adf_statistic': float(adf_statistic),
        'adf_pvalue': float(adf_pvalue),
        'kpss_statistic': float(kpss_statistic),
        'kpss_pvalue': float(kpss_pvalue),
        'judgment': judgment,
        'score': score,
        'message': message
    }


# ==================== 2. PACF 분석 ====================

def analyze_pacf(data: np.ndarray, max_lags: int = 100) -> Dict:
    """
    PACF로 자기상관 구조 분석

    Returns:
        dict with significant_lags, max_lag, recommended_seq_len, score, judgment
    """
    print("\n=== 2. PACF 분석 ===")

    # PACF 계산
    pacf_values = pacf(data, nlags=max_lags, method='ywm')

    # 유의성 임계값 (95% 신뢰구간)
    threshold = 1.96 / np.sqrt(len(data))

    # 유의한 lag (0 제외)
    significant_lags = np.sum(np.abs(pacf_values[1:]) > threshold)

    # 최대 유의 lag
    sig_indices = np.where(np.abs(pacf_values[1:]) > threshold)[0] + 1
    max_sig_lag = int(sig_indices[-1]) if len(sig_indices) > 0 else 0

    # 권장 sequence length
    recommended_seq_len = max_sig_lag * 3 if max_sig_lag > 0 else 60

    print(f"유의 Lag 개수: {significant_lags}")
    print(f"최대 유의 Lag: {max_sig_lag}")
    print(f"권장 Sequence Length: {recommended_seq_len}")

    # 판정
    if significant_lags > 10:
        judgment = "○ 강한 자기상관"
        score = 25
        message = "LSTM 효과적"
    elif significant_lags >= 5:
        judgment = "△ 중간 자기상관"
        score = 12.5
        message = "LSTM 가능하지만 효과 제한적"
    else:
        judgment = "× 약한 자기상관"
        score = 0
        message = "LSTM 의미 없음"

    print(f"  → 판정: {judgment} ({score}점)")
    print(f"  → {message}")

    return {
        'pacf_values': pacf_values.tolist(),
        'threshold': float(threshold),
        'significant_lags': int(significant_lags),
        'max_sig_lag': int(max_sig_lag),
        'recommended_seq_len': int(recommended_seq_len),
        'judgment': judgment,
        'score': float(score),
        'message': message
    }


# ==================== 3. 정보 엔트로피 ====================

def measure_entropy(data: np.ndarray) -> Dict:
    """
    Sample Entropy로 복잡도 측정

    Returns:
        dict with sample_entropy, score, judgment
    """
    print("\n=== 3. 정보 엔트로피 ===")

    if HAS_ANTROPY:
        # Sample Entropy (antropy)
        sampen = antropy.sample_entropy(data, order=2, metric='chebyshev')
        apen = antropy.app_entropy(data, order=2, metric='chebyshev')

        print(f"Sample Entropy: {sampen:.4f}")
        print(f"Approximate Entropy: {apen:.4f}")

        entropy_value = sampen
    else:
        # 대체: 간단한 엔트로피 계산
        # 데이터를 10개 구간으로 binning
        hist, _ = np.histogram(data, bins=10)
        probs = hist / len(data)
        probs = probs[probs > 0]  # 0 제거
        entropy_value = -np.sum(probs * np.log2(probs))

        print(f"Binned Entropy: {entropy_value:.4f}")
        print(f"(antropy 미설치, 간단한 엔트로피 사용)")
        apen = None

    # 판정 (Sample Entropy 기준)
    if entropy_value < 1.0:
        judgment = "○ 낮은 복잡도"
        score = 20
        message = "규칙적, 예측 가능"
    elif entropy_value < 1.5:
        judgment = "△ 중간 복잡도"
        score = 10
        message = "예측 어려움"
    else:
        judgment = "× 높은 복잡도"
        score = 0
        message = "무작위, 예측 불가"

    print(f"  → 판정: {judgment} ({score}점)")
    print(f"  → {message}")

    result = {
        'sample_entropy': float(entropy_value),
        'judgment': judgment,
        'score': float(score),
        'message': message
    }

    if apen is not None:
        result['approximate_entropy'] = float(apen)

    return result


# ==================== 4. Sequence Length 실험 ====================

def experiment_sequence_lengths(data: np.ndarray,
                                lengths: list = [60, 128, 256, 512, 1024]) -> Dict:
    """
    다양한 sequence length에서 ACF 유지 여부 확인

    Returns:
        dict with results for each length, score, judgment
    """
    print("\n=== 4. Sequence Length 실험 ===")

    results = {}

    for length in lengths:
        if length > len(data):
            print(f"  {length}: 데이터 부족 (skip)")
            continue

        # 윈도우 슬라이싱
        num_windows = len(data) // length
        if num_windows == 0:
            continue

        # 각 윈도우의 ACF lag=1 계산
        acf_values = []
        for i in range(num_windows):
            window = data[i * length: (i + 1) * length]
            acf_val = acf(window, nlags=1, fft=True)[1]
            acf_values.append(acf_val)

        avg_acf = np.mean(acf_values)
        results[length] = float(avg_acf)

        print(f"  {length}: ACF = {avg_acf:.4f}")

    # 판정 (512 기준)
    acf_512 = results.get(512, 0.0)

    if acf_512 > 0.1:
        judgment = "○ Transformer 가능"
        score = 20
        message = "512 길이에서도 ACF 유지"
    elif acf_512 > 0.05 or results.get(256, 0.0) > 0.08:
        judgment = "△ LSTM 권장"
        score = 10
        message = "256까지 효과적, Transformer는 한계"
    else:
        judgment = "× 짧은 의존성"
        score = 0
        message = "LSTM도 어려움"

    print(f"  → 판정: {judgment} ({score}점)")
    print(f"  → {message}")

    return {
        'results': results,
        'judgment': judgment,
        'score': float(score),
        'message': message
    }


# ==================== 5. Gap 분포 분석 ====================

def analyze_gap_distribution(data: np.ndarray) -> Dict:
    """
    연속 데이터 구간 분석

    Returns:
        dict with mean_length, score, judgment
    """
    print("\n=== 5. Gap 분포 분석 ===")

    # NaN 확인
    is_nan = pd.isna(data)
    num_gaps = np.sum(is_nan)

    if num_gaps == 0:
        print(f"Gap 개수: 0")
        print(f"완전 연속 데이터 (총 {len(data)} points)")

        judgment = "○ 충분"
        score = 15
        message = "학습 데이터 완벽"

        return {
            'num_gaps': 0,
            'mean_continuous_length': int(len(data)),
            'median_continuous_length': int(len(data)),
            'min_continuous_length': int(len(data)),
            'max_continuous_length': int(len(data)),
            'judgment': judgment,
            'score': float(score),
            'message': message
        }

    # 연속 구간 길이 계산
    continuous_lengths = []
    current_length = 0

    for missing in is_nan:
        if not missing:
            current_length += 1
        else:
            if current_length > 0:
                continuous_lengths.append(current_length)
            current_length = 0

    if current_length > 0:
        continuous_lengths.append(current_length)

    mean_length = np.mean(continuous_lengths)
    median_length = np.median(continuous_lengths)
    min_length = np.min(continuous_lengths)
    max_length = np.max(continuous_lengths)

    print(f"Gap 개수: {num_gaps}")
    print(f"평균 연속 구간: {mean_length:.0f} points")
    print(f"중앙값: {median_length:.0f} points")
    print(f"최소/최대: {min_length}/{max_length} points")

    # 판정
    if mean_length > 1000:
        judgment = "○ 충분"
        score = 15
        message = "학습 데이터 충분"
    elif mean_length >= 500:
        judgment = "△ 부족"
        score = 7.5
        message = "신중하게 진행"
    else:
        judgment = "× 매우 부족"
        score = 0
        message = "학습 불가능"

    print(f"  → 판정: {judgment} ({score}점)")
    print(f"  → {message}")

    return {
        'num_gaps': int(num_gaps),
        'mean_continuous_length': float(mean_length),
        'median_continuous_length': float(median_length),
        'min_continuous_length': int(min_length),
        'max_continuous_length': int(max_length),
        'judgment': judgment,
        'score': float(score),
        'message': message
    }


# ==================== 종합 점수 및 판정 ====================

def calculate_final_score(results: Dict) -> Dict:
    """
    종합 점수 계산 및 최종 판정

    Returns:
        dict with total_score, final_judgment, recommendations
    """
    print("\n" + "=" * 80)
    print("종합 점수")
    print("=" * 80)

    scores = {
        'stationarity': results['stationarity']['score'],
        'pacf': results['pacf']['score'],
        'entropy': results['entropy']['score'],
        'sequence_length': results['sequence_length']['score'],
        'gap_distribution': results['gap_distribution']['score']
    }

    total_score = sum(scores.values())

    print(f"\n항목별 점수:")
    print(f"  1. Stationarity:     {scores['stationarity']:>5.1f} / 20")
    print(f"  2. PACF:             {scores['pacf']:>5.1f} / 25")
    print(f"  3. Entropy:          {scores['entropy']:>5.1f} / 20")
    print(f"  4. Sequence Length:  {scores['sequence_length']:>5.1f} / 20")
    print(f"  5. Gap Distribution: {scores['gap_distribution']:>5.1f} / 15")
    print(f"  " + "-" * 40)
    print(f"  총점:                {total_score:>5.1f} / 100")

    # 최종 판정
    if total_score >= 80:
        final_judgment = "○ 적합"
        lstm_ok = True
        transformer_ok = True
        decision = "GO - Step 2 전체 진행"
        message = "LSTM + Transformer 모두 가능"
    elif total_score >= 50:
        final_judgment = "△ 보통"
        lstm_ok = True
        transformer_ok = False
        decision = "GO - Step 2 LSTM만"
        message = "LSTM 가능, Transformer 신중"
    else:
        final_judgment = "× 부적합"
        lstm_ok = False
        transformer_ok = False
        decision = "NO-GO - 중단 고려"
        message = "전통적 방법 고려"

    # 필수 조건 체크
    if results['pacf']['significant_lags'] < 5:
        decision = "NO-GO - PACF 유의 lag < 5"
        lstm_ok = False
        transformer_ok = False

    if results['gap_distribution']['score'] == 0:
        decision = "NO-GO - 연속 데이터 부족"
        lstm_ok = False
        transformer_ok = False

    print(f"\n최종 판정: {final_judgment} ({total_score:.1f}점)")
    print(f"  - LSTM: {'✅ 가능' if lstm_ok else '❌ 어려움'}")
    print(f"  - Transformer: {'✅ 가능' if transformer_ok else '⚠️ 신중' if lstm_ok else '❌ 불가'}")
    print(f"  - 결정: {decision}")
    print(f"  - {message}")

    return {
        'scores': scores,
        'total_score': float(total_score),
        'final_judgment': final_judgment,
        'lstm_suitable': lstm_ok,
        'transformer_suitable': transformer_ok,
        'decision': decision,
        'message': message
    }


# ==================== 시각화 ====================

def visualize_results(data: np.ndarray, results: Dict, output_dir: Path):
    """
    분석 결과 시각화
    """
    print("\n=== 시각화 생성 ===")

    fig = plt.figure(figsize=(16, 12))

    # 1. 원본 데이터 (상단)
    ax1 = plt.subplot(3, 3, 1)
    ax1.plot(data[:5000], linewidth=0.5)
    ax1.set_title('Original Data (first 5000 points)', fontweight='bold')
    ax1.set_xlabel('Time Index')
    ax1.set_ylabel('Pressure')
    ax1.grid(True, alpha=0.3)

    # 2. ACF
    ax2 = plt.subplot(3, 3, 2)
    acf_vals = acf(data, nlags=100, fft=True)
    ax2.stem(acf_vals, linefmt='C0-', markerfmt='C0o', basefmt='k-')
    ax2.axhline(0, color='k', linestyle='--', linewidth=0.5)
    threshold = 1.96 / np.sqrt(len(data))
    ax2.axhline(threshold, color='r', linestyle='--', linewidth=1, label='95% CI')
    ax2.axhline(-threshold, color='r', linestyle='--', linewidth=1)
    ax2.set_title('ACF', fontweight='bold')
    ax2.set_xlabel('Lag')
    ax2.set_ylabel('ACF')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. PACF
    ax3 = plt.subplot(3, 3, 3)
    pacf_vals = results['pacf']['pacf_values']
    ax3.stem(pacf_vals[:101], linefmt='C1-', markerfmt='C1o', basefmt='k-')
    ax3.axhline(0, color='k', linestyle='--', linewidth=0.5)
    threshold = results['pacf']['threshold']
    ax3.axhline(threshold, color='r', linestyle='--', linewidth=1, label='95% CI')
    ax3.axhline(-threshold, color='r', linestyle='--', linewidth=1)
    ax3.set_title(f"PACF ({results['pacf']['significant_lags']} significant lags)", fontweight='bold')
    ax3.set_xlabel('Lag')
    ax3.set_ylabel('PACF')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Sequence Length별 ACF
    ax4 = plt.subplot(3, 3, 4)
    seq_results = results['sequence_length']['results']
    lengths = list(seq_results.keys())
    acfs = [seq_results[l] for l in lengths]
    ax4.plot(lengths, acfs, marker='o', linewidth=2, markersize=8)
    ax4.axhline(0.1, color='g', linestyle='--', label='Good (0.1)')
    ax4.axhline(0.05, color='orange', linestyle='--', label='Fair (0.05)')
    ax4.set_title('Sequence Length vs ACF', fontweight='bold')
    ax4.set_xlabel('Sequence Length')
    ax4.set_ylabel('Avg ACF (lag=1)')
    ax4.set_xscale('log', base=2)
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. 데이터 분포 (히스토그램)
    ax5 = plt.subplot(3, 3, 5)
    ax5.hist(data, bins=50, edgecolor='black', alpha=0.7)
    ax5.set_title('Data Distribution', fontweight='bold')
    ax5.set_xlabel('Pressure')
    ax5.set_ylabel('Frequency')
    ax5.grid(True, alpha=0.3)

    # 6. 종합 점수 (레이더 차트)
    ax6 = plt.subplot(3, 3, 6, projection='polar')
    categories = ['Stationarity\n(20)', 'PACF\n(25)', 'Entropy\n(20)', 'Seq Length\n(20)', 'Gap Dist\n(15)']
    scores = [
        results['stationarity']['score'] / 20 * 100,
        results['pacf']['score'] / 25 * 100,
        results['entropy']['score'] / 20 * 100,
        results['sequence_length']['score'] / 20 * 100,
        results['gap_distribution']['score'] / 15 * 100
    ]

    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    scores += scores[:1]
    angles += angles[:1]

    ax6.plot(angles, scores, 'o-', linewidth=2, label='Score')
    ax6.fill(angles, scores, alpha=0.25)
    ax6.set_xticks(angles[:-1])
    ax6.set_xticklabels(categories)
    ax6.set_ylim(0, 100)
    ax6.set_title('Score Radar Chart', fontweight='bold', pad=20)
    ax6.grid(True)

    # 7. 종합 점수 바 차트
    ax7 = plt.subplot(3, 3, 7)
    final_results = results['final']
    items = list(final_results['scores'].keys())
    item_scores = [final_results['scores'][item] for item in items]
    max_scores = [20, 25, 20, 20, 15]

    x = np.arange(len(items))
    width = 0.35

    ax7.bar(x - width/2, item_scores, width, label='Actual', color='steelblue')
    ax7.bar(x + width/2, max_scores, width, label='Maximum', color='lightgray', alpha=0.5)
    ax7.set_ylabel('Score')
    ax7.set_title(f"Total: {final_results['total_score']:.1f}/100 - {final_results['final_judgment']}",
                 fontweight='bold')
    ax7.set_xticks(x)
    ax7.set_xticklabels(['Stat', 'PACF', 'Entr', 'SeqLen', 'Gap'], rotation=45)
    ax7.legend()
    ax7.grid(True, alpha=0.3, axis='y')

    # 8. 판정 요약 (텍스트)
    ax8 = plt.subplot(3, 3, 8)
    ax8.axis('off')

    summary_text = f"""
Final Judgment: {final_results['final_judgment']}
Total Score: {final_results['total_score']:.1f} / 100

LSTM: {'✅ Suitable' if final_results['lstm_suitable'] else '❌ Not suitable'}
Transformer: {'✅ Suitable' if final_results['transformer_suitable'] else '⚠️ Careful' if final_results['lstm_suitable'] else '❌ Not suitable'}

Decision: {final_results['decision']}

Recommended Sequence Length:
  {results['pacf']['recommended_seq_len']}

{final_results['message']}
"""

    ax8.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # 9. ADF/KPSS 결과
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')

    stat_text = f"""
Stationarity Tests:

ADF Test:
  p-value: {results['stationarity']['adf_pvalue']:.4f}
  {'✅ Stationary' if results['stationarity']['adf_pvalue'] < 0.05 else '❌ Non-stationary'}

KPSS Test:
  p-value: {results['stationarity']['kpss_pvalue']:.4f}
  {'✅ Stationary' if results['stationarity']['kpss_pvalue'] > 0.05 else '❌ Non-stationary'}

Entropy:
  Sample Entropy: {results['entropy']['sample_entropy']:.4f}
  {results['entropy']['judgment']}
"""

    ax9.text(0.1, 0.5, stat_text, fontsize=10, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    plt.tight_layout()

    output_path = output_dir / "suitability_analysis_plots.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Visualization saved: {output_path}")


# ==================== 보고서 생성 ====================

def generate_report(results: Dict, output_dir: Path, area: str):
    """
    Markdown 보고서 생성
    """
    print("\n=== 보고서 생성 ===")

    report = f"""# 데이터 적합성 분석 결과

**분석 일시**: {results['timestamp']}
**데이터**: {area} 소구역 압력
**데이터 크기**: {results['data_size']:,} records

---

## 📊 종합 점수

**총점: {results['final']['total_score']:.1f} / 100점**

| 항목 | 판정 | 점수 | 최대 |
|------|------|------|------|
| Stationarity | {results['stationarity']['judgment']} | {results['stationarity']['score']:.1f} | 20 |
| PACF | {results['pacf']['judgment']} | {results['pacf']['score']:.1f} | 25 |
| Entropy | {results['entropy']['judgment']} | {results['entropy']['score']:.1f} | 20 |
| Sequence Length | {results['sequence_length']['judgment']} | {results['sequence_length']['score']:.1f} | 20 |
| Gap Distribution | {results['gap_distribution']['judgment']} | {results['gap_distribution']['score']:.1f} | 15 |

---

## 🎯 최종 판정

### {results['final']['final_judgment']}

- **LSTM**: {'✅ 적합' if results['final']['lstm_suitable'] else '❌ 부적합'}
- **Transformer**: {'✅ 적합' if results['final']['transformer_suitable'] else '⚠️ 신중' if results['final']['lstm_suitable'] else '❌ 부적합'}
- **권장 Sequence Length**: {results['pacf']['recommended_seq_len']}

### 결정: {results['final']['decision']}

**이유**: {results['final']['message']}

---

## 1. Stationarity 검증

### ADF Test
- Statistic: {results['stationarity']['adf_statistic']:.4f}
- p-value: **{results['stationarity']['adf_pvalue']:.4f}**
- 판정: {'✅ 정상 시계열' if results['stationarity']['adf_pvalue'] < 0.05 else '❌ 비정상 시계열'}

### KPSS Test
- Statistic: {results['stationarity']['kpss_statistic']:.4f}
- p-value: **{results['stationarity']['kpss_pvalue']:.4f}**
- 판정: {'✅ 정상 시계열' if results['stationarity']['kpss_pvalue'] > 0.05 else '❌ 비정상 시계열'}

### 종합 판정: **{results['stationarity']['judgment']}** ({results['stationarity']['score']:.1f}점)
- {results['stationarity']['message']}

---

## 2. PACF 분석

- 유의 Lag 개수: **{results['pacf']['significant_lags']}개**
- 최대 유의 Lag: {results['pacf']['max_sig_lag']}
- 권장 Sequence Length: **{results['pacf']['recommended_seq_len']}**

### 종합 판정: **{results['pacf']['judgment']}** ({results['pacf']['score']:.1f}점)
- {results['pacf']['message']}

---

## 3. 정보 엔트로피

- Sample Entropy: **{results['entropy']['sample_entropy']:.4f}**

### 종합 판정: **{results['entropy']['judgment']}** ({results['entropy']['score']:.1f}점)
- {results['entropy']['message']}

---

## 4. Sequence Length 실험

| Window Size | Avg ACF |
|-------------|---------|
"""

    for length, acf_val in results['sequence_length']['results'].items():
        report += f"| {length} | {acf_val:.4f} |\n"

    report += f"""
### 종합 판정: **{results['sequence_length']['judgment']}** ({results['sequence_length']['score']:.1f}점)
- {results['sequence_length']['message']}

---

## 5. Gap 분포

- Gap 개수: {results['gap_distribution']['num_gaps']}
- 평균 연속 구간: **{results['gap_distribution']['mean_continuous_length']:.0f} points**
- 중앙값: {results['gap_distribution']['median_continuous_length']:.0f} points
- 최소/최대: {results['gap_distribution']['min_continuous_length']} / {results['gap_distribution']['max_continuous_length']} points

### 종합 판정: **{results['gap_distribution']['judgment']}** ({results['gap_distribution']['score']:.1f}점)
- {results['gap_distribution']['message']}

---

## 📈 시각화

![Suitability Analysis](suitability_analysis_plots.png)

---

## 🚦 다음 단계

"""

    if results['final']['lstm_suitable']:
        report += """
### ✅ GO - Step 2 진행

**이유**: 데이터가 LSTM 학습에 적합합니다.

**다음 작업**:
1. Step 2: Simple LSTM Quick Test 진행
2. 10-step 비재귀 예측으로 핵심 검증
3. R² > 0.5 목표

**권장 설정**:
- Sequence Length: {recommended_seq_len}
- LSTM layers: 2-3
- Hidden dim: 128-256
""".format(recommended_seq_len=results['pacf']['recommended_seq_len'])
    else:
        report += """
### ❌ NO-GO - 중단 고려

**이유**: 데이터가 LSTM/Transformer 학습에 부적합합니다.

**문제점**:
"""
        if results['pacf']['significant_lags'] < 5:
            report += "- PACF 유의 lag < 5개 (자기상관 너무 약함)\n"
        if results['gap_distribution']['score'] == 0:
            report += "- 연속 데이터 부족 (학습 불가능)\n"

        report += """
**대안**:
- 전통적 보간 방법 (Linear, Spline)
- Gap 허용 정책 검토
- 다변량 데이터 확보 후 재시도
"""

    report += f"""
---

**작성일**: {results['timestamp']}
**분석 완료**
"""

    output_path = output_dir / "suitability_analysis.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Report saved: {output_path}")


# ==================== 메인 ====================

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='Step 1: 데이터 적합성 분석'
    )
    parser.add_argument('--area', default='0243', help='지역 코드 (기본값: 0243)')
    parser.add_argument('--output', default='results/', help='결과 저장 디렉토리')

    args = parser.parse_args()

    # 출력 디렉토리
    output_dir = Path(__file__).parent / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Step 1: 데이터 적합성 분석")
    print("=" * 80)
    print(f"Area: {args.area}")
    print(f"Output: {output_dir}")

    # 1. 데이터 로드
    print("\n--- 데이터 로드 ---")
    df = data_loader.load_pressure_data(args.area)
    data = df['wtrprsr'].values

    print(f"Loaded {len(data):,} records")
    print(f"Date range: {df['msrmt_dt'].min()} ~ {df['msrmt_dt'].max()}")

    # 2. 분석 실행
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'area': args.area,
        'data_size': len(data)
    }

    results['stationarity'] = test_stationarity(data)
    results['pacf'] = analyze_pacf(data)
    results['entropy'] = measure_entropy(data)
    results['sequence_length'] = experiment_sequence_lengths(data)
    results['gap_distribution'] = analyze_gap_distribution(data)

    # 3. 종합 점수
    results['final'] = calculate_final_score(results)

    # 4. 시각화
    visualize_results(data, results, output_dir)

    # 5. 보고서 생성
    generate_report(results, output_dir, args.area)

    # 6. JSON 저장
    output_json = output_dir / "suitability_analysis.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nJSON saved: {output_json}")

    # 7. 최종 요약
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"총점: {results['final']['total_score']:.1f} / 100")
    print(f"판정: {results['final']['final_judgment']}")
    print(f"LSTM: {'✅ 적합' if results['final']['lstm_suitable'] else '❌ 부적합'}")
    print(f"Transformer: {'✅ 적합' if results['final']['transformer_suitable'] else '⚠️ 신중' if results['final']['lstm_suitable'] else '❌ 부적합'}")
    print(f"결정: {results['final']['decision']}")
    print("=" * 80)


if __name__ == '__main__':
    main()
