# 주파수 성분별 Rainflow Count 분석 계획

**작성일**: 2025-12-11
**목적**: 저주파/고주파 성분별 Rainflow count를 분리 분석하여 cycle 과다생성의 근본 원인 파악
**예상 시간**: 2-3시간

---

## 🎯 배경 및 동기

### 현재 문제

**Rainflow matching 실패의 핵심 증상**:
```
모든 gap에서 cycle 수 약 2배 과다생성:
- 3일:  True 740   → Pred 1,441  (1.95배)
- 7일:  True 1,734 → Pred 3,446  (1.99배)
- 14일: True 3,394 → Pred 6,928  (2.04배)
- 24일: True 5,754 → Pred 12,013 (2.09배)
```

### 핵심 질문

**Q1**: 저주파 ARMA synthesis가 문제인가?
**Q2**: 고주파 Random Phase가 문제인가?
**Q3**: 재조합 과정에서 문제가 생기는가?

### 분석 필요성

현재는 **재조합된 전체 신호**만 분석:
```
Total = Low-freq (ARMA) + High-freq (Random Phase)
```

**문제**:
- 어느 성분이 cycle 과다생성의 주범인지 불명확
- 개선 방향 설정 불가능
- Root cause 파악 불가

**해결**:
- 각 성분을 **독립적으로** rainflow counting
- 성분별 기여도 정량화
- 근본 원인 식별

---

## 📋 분석 방법

### Step 1: 데이터 준비

각 gap (3, 7, 14, 24일)에서:

```python
# 1. 원본 데이터 로드
gap_true = np.load(f"results/gap_{gap_days}days/gap_true.npy")
gap_pred = np.load(f"results/gap_{gap_days}days/gap_pred.npy")

# 2. 주파수 분리 (Butterworth filter, V-valley 553.5분)
low_true, high_true = frequency_separation(gap_true, v_valley=553.5)
low_pred, high_pred = frequency_separation(gap_pred, v_valley=553.5)
```

**결과**: 각 gap당 6개 시계열
- `low_true`, `high_true`, `total_true`
- `low_pred`, `high_pred`, `total_pred`

### Step 2: 성분별 Rainflow Counting

```python
from validation import simple_rainflow_count

# True 성분
cycles_low_true = simple_rainflow_count(low_true)
cycles_high_true = simple_rainflow_count(high_true)
cycles_total_true = simple_rainflow_count(gap_true)

# Pred 성분
cycles_low_pred = simple_rainflow_count(low_pred)
cycles_high_pred = simple_rainflow_count(high_pred)
cycles_total_pred = simple_rainflow_count(gap_pred)
```

### Step 3: 메트릭 계산

각 성분별로:

```python
metrics = {
    "cycles_count": len(cycles),
    "amplitude_mean": cycles[:, 0].mean(),
    "amplitude_std": cycles[:, 0].std(),
    "amplitude_max": cycles[:, 0].max(),
    "mean_value_mean": cycles[:, 1].mean(),
    "mean_value_std": cycles[:, 1].std()
}
```

### Step 4: 비교 분석

**4.1 Cycle 수 분해**
```
Total Pred cycles = Low Pred + High Pred + Interaction
Interaction = Total - (Low + High)
```

**4.2 비율 계산**
```
Low ratio = Low Pred / Low True
High ratio = High Pred / High True
Total ratio = Total Pred / Total True
```

**4.3 기여도 분석**
```
Low contribution = (Low Pred - Low True) / (Total Pred - Total True)
High contribution = (High Pred - High True) / (Total Pred - Total True)
```

---

## 🔬 구현 계획

### 파일: `analyze_frequency_components.py`

```python
#!/usr/bin/env python3
"""
주파수 성분별 Rainflow Count 분석

각 gap에서 저주파/고주파 성분을 분리하여
rainflow counting 결과를 비교 분석
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.signal import butter, filtfilt
from validation import simple_rainflow_count
import json


def frequency_separation(data, v_valley=553.5, fs=1.0):
    """주파수 분리 (spectral_gap_fill.py와 동일)"""
    # Butterworth low-pass/high-pass filter
    # ...
    return low_freq, high_freq


def analyze_component_rainflow(gap_days: int, results_dir: Path):
    """
    단일 gap의 성분별 rainflow 분석

    Returns:
        dict: 성분별 메트릭
    """
    print(f"\n{'='*70}")
    print(f"Analyzing Gap: {gap_days} days")
    print(f"{'='*70}")

    # 1. 데이터 로드
    gap_dir = results_dir / f"gap_{gap_days}days"
    gap_true = np.load(gap_dir / "gap_true.npy")
    gap_pred = np.load(gap_dir / "gap_pred.npy")

    # 2. 주파수 분리
    low_true, high_true = frequency_separation(gap_true)
    low_pred, high_pred = frequency_separation(gap_pred)

    # 3. Rainflow counting
    results = {
        "gap_days": gap_days,
        "low_true": analyze_single_component(low_true, "Low True"),
        "low_pred": analyze_single_component(low_pred, "Low Pred"),
        "high_true": analyze_single_component(high_true, "High True"),
        "high_pred": analyze_single_component(high_pred, "High Pred"),
        "total_true": analyze_single_component(gap_true, "Total True"),
        "total_pred": analyze_single_component(gap_pred, "Total Pred")
    }

    # 4. 비교 분석
    results["analysis"] = compare_components(results)

    return results


def analyze_single_component(signal, name):
    """단일 성분 rainflow 분석"""
    cycles = simple_rainflow_count(signal)

    if len(cycles) == 0:
        return {
            "name": name,
            "cycles_count": 0,
            "amplitude_mean": 0,
            "amplitude_std": 0
        }

    return {
        "name": name,
        "cycles_count": len(cycles),
        "amplitude_mean": float(cycles[:, 0].mean()),
        "amplitude_std": float(cycles[:, 0].std()),
        "amplitude_max": float(cycles[:, 0].max()),
        "mean_value_mean": float(cycles[:, 1].mean()),
        "mean_value_std": float(cycles[:, 1].std())
    }


def compare_components(results):
    """성분별 비교 분석"""
    low_t = results["low_true"]["cycles_count"]
    low_p = results["low_pred"]["cycles_count"]
    high_t = results["high_true"]["cycles_count"]
    high_p = results["high_pred"]["cycles_count"]
    total_t = results["total_true"]["cycles_count"]
    total_p = results["total_pred"]["cycles_count"]

    # Cycle 수 분해
    interaction = total_p - (low_p + high_p)

    # 비율
    low_ratio = low_p / low_t if low_t > 0 else 0
    high_ratio = high_p / high_t if high_t > 0 else 0
    total_ratio = total_p / total_t if total_t > 0 else 0

    # 기여도
    total_excess = total_p - total_t
    low_excess = low_p - low_t
    high_excess = high_p - high_t

    low_contribution = (low_excess / total_excess * 100) if total_excess > 0 else 0
    high_contribution = (high_excess / total_excess * 100) if total_excess > 0 else 0
    interaction_contribution = (interaction / total_excess * 100) if total_excess > 0 else 0

    return {
        "cycle_decomposition": {
            "low_true": low_t,
            "low_pred": low_p,
            "low_excess": low_excess,
            "high_true": high_t,
            "high_pred": high_p,
            "high_excess": high_excess,
            "total_true": total_t,
            "total_pred": total_p,
            "total_excess": total_excess,
            "interaction": interaction
        },
        "ratios": {
            "low_ratio": low_ratio,
            "high_ratio": high_ratio,
            "total_ratio": total_ratio
        },
        "contributions": {
            "low_pct": low_contribution,
            "high_pct": high_contribution,
            "interaction_pct": interaction_contribution
        }
    }


def analyze_all_gaps(results_dir: Path):
    """전체 gap 분석 및 비교"""
    all_results = []

    for gap_days in [3, 7, 14, 24]:
        result = analyze_component_rainflow(gap_days, results_dir)
        all_results.append(result)

    # 비교표 생성
    comparison_df = create_comparison_table(all_results)

    # 저장
    output_dir = results_dir
    comparison_df.to_csv(output_dir / "component_rainflow_comparison.csv", index=False)

    # JSON 저장
    with open(output_dir / "component_analysis_results.json", 'w') as f:
        json.dump(all_results, f, indent=2)

    # 분석 보고서 생성
    generate_analysis_report(all_results, output_dir)

    return all_results, comparison_df


def create_comparison_table(all_results):
    """비교표 생성"""
    rows = []

    for result in all_results:
        gap_days = result["gap_days"]

        # 각 성분별 row
        for component in ["low_true", "low_pred", "high_true", "high_pred", "total_true", "total_pred"]:
            comp_data = result[component]
            rows.append({
                "gap_days": gap_days,
                "component": comp_data["name"],
                "cycles_count": comp_data["cycles_count"],
                "amplitude_mean": comp_data["amplitude_mean"],
                "amplitude_std": comp_data["amplitude_std"]
            })

    return pd.DataFrame(rows)


def generate_analysis_report(all_results, output_dir):
    """분석 보고서 생성 (Markdown)"""
    # COMPONENT_ANALYSIS_RESULTS.md 생성
    # ...
    pass


if __name__ == "__main__":
    results_dir = Path(__file__).parent / "results"
    all_results, comparison_df = analyze_all_gaps(results_dir)

    print("\n" + "="*70)
    print("COMPONENT ANALYSIS COMPLETE")
    print("="*70)
    print(f"\n{comparison_df.to_string(index=False)}")
```

### 시각화: `visualize_component_analysis.py`

```python
def plot_component_comparison(all_results):
    """
    성분별 비교 시각화

    - Cycle 수 비교 (stacked bar)
    - Amplitude 분포 비교 (box plot)
    - 기여도 분석 (pie chart)
    """
    pass
```

---

## 📊 예상 결과

### 예상 출력 1: 비교표

```
Gap  | Component   | Cycles | Amp Mean | Amp Std
-----|-------------|--------|----------|--------
3일  | Low True    | ???    | ???      | ???
3일  | Low Pred    | ???    | ???      | ???
3일  | High True   | ???    | ???      | ???
3일  | High Pred   | ???    | ???      | ???
3일  | Total True  | 740    | 0.054    | 0.059
3일  | Total Pred  | 1441   | 0.083    | 0.060
...
```

### 예상 출력 2: 분해 분석

```
Gap 3일:
┌─────────────────────────────────────┐
│ Cycle 수 분해                        │
├─────────────────────────────────────┤
│ Low True:      XXX                  │
│ Low Pred:      XXX  (비율: X.XX배)  │
│ Low Excess:    +XXX                 │
│                                     │
│ High True:     XXX                  │
│ High Pred:     XXX  (비율: X.XX배)  │
│ High Excess:   +XXX                 │
│                                     │
│ Total True:    740                  │
│ Total Pred:    1441 (비율: 1.95배)  │
│ Total Excess:  +701                 │
│                                     │
│ Interaction:   +XXX                 │
└─────────────────────────────────────┘

기여도 분석:
- 저주파 기여:    XX%
- 고주파 기여:    XX%
- 상호작용 기여:  XX%
```

---

## 🎯 예상 시나리오 및 해석

### 시나리오 1: 고주파가 주범 (예상 확률: 70%)

**결과 패턴**:
```
Low Pred / Low True  ≈ 1.0 ~ 1.2  (양호)
High Pred / High True ≈ 2.5 ~ 3.0  (매우 높음)
```

**해석**:
- Random Phase synthesis가 spurious peaks 과다 생성
- 고주파 성분의 phase randomization이 문제
- PSD는 보존하지만 peak 구조는 왜곡

**개선 방향**:
- 고주파 edge smoothing window 증가 (20분 → 60분)
- Random phase 대신 다른 고주파 합성 방법 검토
- 하지만 근본적 해결 어려움 (PSD ⊄ Rainflow)

### 시나리오 2: 저주파가 주범 (예상 확률: 15%)

**결과 패턴**:
```
Low Pred / Low True  ≈ 2.0 ~ 2.5  (매우 높음)
High Pred / High True ≈ 1.0 ~ 1.2  (양호)
```

**해석**:
- ARMA synthesis가 over-oscillating
- Forward/Backward blending이 추가 cycles 생성
- ARMA order가 부적절

**개선 방향**:
- ARMA order 재조정 (현재 auto-detect)
- Blending window 조정
- ARMA 대신 다른 저주파 합성 방법

### 시나리오 3: 양쪽 모두 문제 (예상 확률: 10%)

**결과 패턴**:
```
Low Pred / Low True  ≈ 1.5 ~ 1.8
High Pred / High True ≈ 1.5 ~ 1.8
Total Pred / Total True ≈ 2.0
```

**해석**:
- 양쪽 성분 모두 cycle 과다생성
- 재조합 시 상호작용으로 더 증폭

**개선 방향**:
- 전체 접근법 재검토 필요
- Spectral matching 자체의 한계

### 시나리오 4: 재조합 문제 (예상 확률: 5%)

**결과 패턴**:
```
Low Pred + High Pred < Total Pred
Interaction > 20% of excess
```

**해석**:
- 재조합 과정에서 새로운 peaks 생성
- 저주파 + 고주파의 간섭 효과

**개선 방향**:
- 재조합 알고리즘 개선
- Additive 대신 다른 결합 방법

---

## 🔍 의사결정 기준

### 판단 기준

**저주파/고주파 비율 해석**:
```
비율 < 1.2:  ✅ 양호
비율 1.2-1.5: △ 보통
비율 1.5-2.0: ⚠️ 문제
비율 > 2.0:  ❌ 심각
```

**기여도 해석**:
```
한쪽 성분 기여도 > 70%: 주범 식별 완료
양쪽 비슷 (40-60%): 공동 문제
상호작용 > 30%: 재조합 문제
```

### 의사결정 트리

```
분석 결과
    ↓
High ratio > 2.0?
    ├─ Yes → "고주파 Random Phase가 주범"
    │         → Edge smoothing 개선 시도
    │         → 하지만 근본적 해결 어려움
    │
    └─ No → Low ratio > 2.0?
            ├─ Yes → "저주파 ARMA가 주범"
            │         → ARMA 파라미터 조정
            │
            └─ No → 양쪽 모두 문제 or 재조합 문제
                     → 전체 접근법 한계 확인
```

### 최종 판단

**어떤 시나리오든 결론은 동일**:

```
개별 성분 개선 가능성 < 10%
→ Rainflow match 0.86 → 0.95 달성 불가능
→ Spectral matching의 근본적 한계 재확인
→ Gap 허용 정책 유지
```

**하지만 분석의 가치**:
- 실패 원인의 정량적 규명
- 향후 연구 방향 제시
- 문서화 및 지식 축적

---

## 📁 산출물

### 파일 목록

1. **`analyze_frequency_components.py`** - 분석 스크립트
2. **`visualize_component_analysis.py`** - 시각화 스크립트
3. **`results/component_rainflow_comparison.csv`** - 비교표
4. **`results/component_analysis_results.json`** - 상세 결과
5. **`results/COMPONENT_ANALYSIS_RESULTS.md`** - 분석 보고서
6. **`results/component_analysis_*.png`** - 시각화 그래프

### 보고서 구조

**COMPONENT_ANALYSIS_RESULTS.md**:
```markdown
# 주파수 성분별 Rainflow Count 분석 결과

## 요약
- 주범: 저주파 / 고주파 / 양쪽
- 기여도: XX% / XX%

## 상세 결과
### Gap 3일
### Gap 7일
### Gap 14일
### Gap 24일

## 결론 및 권장사항
```

---

## ⏱️ 예상 소요 시간

| 단계 | 작업 | 시간 |
|------|------|------|
| 1 | `analyze_frequency_components.py` 구현 | 1시간 |
| 2 | 4개 gap 분석 실행 | 10분 |
| 3 | `visualize_component_analysis.py` 구현 | 30분 |
| 4 | 시각화 생성 | 5분 |
| 5 | `COMPONENT_ANALYSIS_RESULTS.md` 작성 | 30분 |
| 6 | 검토 및 수정 | 30분 |

**총 예상 시간**: 2.5 ~ 3시간

---

## ✅ 성공 기준

### 분석 완료 기준

1. ✅ 4개 gap 모두 성분별 분석 완료
2. ✅ 비교표 생성 (CSV)
3. ✅ 시각화 생성 (PNG)
4. ✅ 분석 보고서 작성 (Markdown)

### 품질 기준

1. ✅ 주범 성분 명확히 식별
2. ✅ 기여도 정량화 (%)
3. ✅ 개선 방향 제시 (실현 가능성과 무관하게)
4. ✅ 결론의 논리적 타당성

---

**작성 완료**: 2025-12-11
**다음 단계**: 사용자 승인 후 구현 시작
