# 결측 구간 파형 분해 시각화 계획

**작성일**: 2025-12-11
**목적**: "Interaction 58.6%" 결과의 의미를 시각적으로 검증

---

## 🎯 배경 및 동기

### 현재 상황

주파수 성분별 Rainflow Count 분석 결과:

| 성분 | 초과분 기여도 |
|------|--------------|
| 저주파 | 0.3% |
| 고주파 | 41.0% |
| **상호작용** | **58.6%** ⚠️ |

**Tiling 문제 해결 시도**:
- Spectral Interpolation으로 Tiling artifacts 제거 성공 (87% 감소)
- 하지만 **Interaction 58.6%는 변하지 않음** (Tiling과 무관)
- 근본 원인은 다른 곳에 있음

### 의문점

1. **"상호작용(Interaction)"이 정확히 무엇인가?**
   - 재조합 과정의 문제인가?
   - 아니면 Rainflow의 비선형성 때문인가?

2. **저주파 + 고주파가 원본을 완벽히 재구성하는가?**
   - Butterworth filter는 완벽한 재구성 보장
   - 하지만 실제로 검증 필요

3. **왜 Pred에서 더 많은 Peak가 생기는가?**
   - Random Phase의 영향?
   - 저주파-고주파 위상 관계?

---

## ❓ 핵심 질문

### Q1: 재조합의 정확성
```python
reconstruction_error = |original - (low_freq + high_freq)|
Expected: error < 1e-10 (부동소수점 오차 수준)
```

### Q2: True와 Pred의 차이
```python
correlation_true = pearsonr(low_true, high_true)
correlation_pred = pearsonr(low_pred, high_pred)

Expected:
- True: 상관관계 있음 (물리적 과정)
- Pred: 상관관계 ~0 (Random Phase)
```

### Q3: Peak 생성 메커니즘
```python
peaks_original = find_peaks(original)
peaks_combined = find_peaks(low + high)

True:  peaks_combined ≈ peaks_original (일치)
Pred:  peaks_combined >> peaks_original (과다 생성)
```

### Q4: "Interaction"의 의미
```python
interaction_excess = total_excess - (low_excess + high_excess)
```

이것이 측정하는 것:
- A: 재조합 과정의 오류? (unlikely)
- B: Rainflow의 비선형성? (likely)
- C: 저주파-고주파 위상 관계 차이? (most likely)

---

## 📊 시각화 계획

### 1. 전체 구조

**4개 Gap × 2개 서브플롯 (True/Pred) = 총 8개 패널**

각 서브플롯:
```
┌─────────────────────────────────────────┐
│ Gap X days - True (or Pred)             │
├─────────────────────────────────────────┤
│ [상단] 파형 Overlay                      │
│   - 원본 (검은색, 굵게)                  │
│   - 저주파 (파란색)                      │
│   - 고주파 (빨간색)                      │
│   - 재조합 (녹색, 점선)                  │
│                                         │
│ [하단] 재조합 오차                       │
│   - |원본 - (저주파 + 고주파)|          │
│   - Max 오차 표시                       │
└─────────────────────────────────────────┘
```

### 2. 스크립트 설계

**파일명**: `visualize_gap_waveforms.py`

**데이터 로드 경로**:
```python
# 실제 데이터 경로 명확화
gap_dir = Path(__file__).parent / "results" / f"gap_{gap_days}days"
gap_true = np.load(gap_dir / "gap_true.npy")
gap_pred = np.load(gap_dir / "gap_pred.npy")
low_true = np.load(gap_dir / "low_freq_true.npy")
high_true = np.load(gap_dir / "high_freq_true.npy")
low_pred = np.load(gap_dir / "low_freq_pred.npy")
high_pred = np.load(gap_dir / "high_freq_pred.npy")
```

**한글 폰트 설정 필수**:
```python
# 한글 깨짐 방지
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.common.korean_font_utils import setup_korean_font
setup_korean_font()
```

**주요 함수**:

```python
def plot_waveform_decomposition(gap_days: int, data_type: str):
    """
    단일 gap의 파형 분해 시각화

    Args:
        gap_days: Gap 일수 (3, 7, 14, 24)
        data_type: "true" 또는 "pred"

    Plots:
        - 4개 파형 overlay
        - 재조합 오차
    """

def verify_reconstruction(original, low, high):
    """
    재조합 정확도 검증

    Returns:
        max_error: 최대 재조합 오차
        assert max_error < 1e-10
    """

def analyze_correlation(low, high):
    """
    저주파-고주파 상관관계 분석

    Returns:
        pearson_r: Pearson 상관계수
        coherent_pct: 같은 방향 움직임 비율
    """

def compare_peaks(original, low, high):
    """
    Peak 개수 비교

    Returns:
        peaks_original: 원본 peak 개수
        peaks_low: 저주파 peak 개수
        peaks_high: 고주파 peak 개수
        peaks_combined: 재조합 peak 개수
    """

def analyze_peak_directions(low, high):
    """
    Peak 방향 분석 (추가)

    Returns:
        same_direction: 같은 방향 peak 비율
        opposite_direction: 반대 방향 peak 비율
        cancellation_ratio: 상쇄 비율
    """
```

### 3. 확대 그래프

각 Gap별로 2개의 확대 그래프 추가:
- **처음 500 points**: 경계 효과 확인
- **중간 500 points**: 대표적 패턴 확인

---

## 🔬 분석 계획

### 1. 재조합 정확도 측정

```python
# 각 Gap별 True/Pred에 대해
reconstruction_error = np.max(np.abs(original - (low + high)))

Expected:
- 모든 경우: error < 1e-10
- Butterworth filter는 완벽한 재구성 보장
```

### 2. 저주파-고주파 상관관계

```python
# Pearson correlation
corr_true, p_true = pearsonr(low_true, high_true)
corr_pred, p_pred = pearsonr(low_pred, high_pred)

# 같은 방향 움직임 비율
def coherent_movement(low, high):
    low_diff = np.diff(low)
    high_diff = np.diff(high)
    same_direction = np.sum((low_diff * high_diff) > 0)
    return same_direction / len(low_diff) * 100

Expected:
- True: 상관관계 있음 (물리적 상관성)
- Pred: 상관관계 ~0 (Random Phase)
```

### 3. Peak 개수 비교

```python
from scipy.signal import find_peaks

# 각 성분별 peak 검출
peaks_original, _ = find_peaks(original, prominence=0.01)
peaks_low, _ = find_peaks(low, prominence=0.01)
peaks_high, _ = find_peaks(high, prominence=0.01)
peaks_combined, _ = find_peaks(low + high, prominence=0.01)

Expected:
- True: len(peaks_combined) ≈ len(peaks_original)
- Pred: len(peaks_combined) >> len(peaks_original)
```

### 4. Rainflow 비선형성 검증

```python
# Rainflow는 비선형!
rainflow(low + high) ≠ rainflow(low) + rainflow(high)

# 구체적 예시:
# True:  low(↑) + high(↓) = total(~) → Peak 적음
# Pred:  low(↑) + high(↑) = total(↑↑) → Peak 많음
```

---

## 💡 예상 결과 및 가설

### 가설 1: 재조합은 완벽함

**주장**: `low + high = original` (완벽한 재구성)

**근거**:
- Butterworth filter는 선형 필터
- 저주파 + 고주파 = 원본 (수학적으로 보장)
- 재조합 과정 자체는 문제 없음

**검증 방법**:
```python
max_error = np.max(np.abs(original - (low + high)))
assert max_error < 1e-10  # 부동소수점 오차 수준
```

**예상 결과**: ✅ 통과

---

### 가설 2: True와 Pred의 위상 관계 차이

**주장**: True는 저주파-고주파 상관관계 있음, Pred는 무작위

**근거**:
- **True**: 실제 압력 변동은 물리적 과정
  - 압력이 서서히 올라갈 때(저주파 ↑) → 작은 변동 감소(고주파 ↓)
  - 압력이 안정적일 때(저주파 ~) → 작은 변동 증가(고주파 ↑)
  - 결과: **음의 상관관계** 예상

- **Pred**: Random Phase IFFT로 합성
  - 저주파: ARMA (일부 예측성)
  - 고주파: Random Phase (완전 무작위)
  - 결과: **상관관계 ~0**

**검증 방법**:
```python
corr_true = pearsonr(low_true, high_true)
corr_pred = pearsonr(low_pred, high_pred)

# True:  corr < 0 (음의 상관관계)
# Pred:  corr ≈ 0 (무상관)
```

**예상 결과**: ✅ True와 Pred의 명확한 차이 발견

---

### 가설 3: "Interaction"의 진짜 의미

**주장**: "Interaction"은 재조합 오류가 아니라, **Rainflow 비선형성 + 위상 관계 차이**를 측정

**수식**:
```python
# 정의
interaction_excess = total_excess - (low_excess + high_excess)

# 의미
= [rainflow(total_pred) - rainflow(total_true)]
  - [rainflow(low_pred) - rainflow(low_true)]
  - [rainflow(high_pred) - rainflow(high_true)]

= Rainflow의 비선형성으로 인한 효과
```

**왜 Pred에서 더 큰가?**

1. **True 신호**:
   ```
   시각 t1: low(↑) + high(↓) = total(~)  → 평평 → Peak 생성 안 됨
   시각 t2: low(~) + high(↑) = total(↑)  → 상승 → Peak 생성

   결과: 저주파-고주파가 서로 상쇄 → Peak 적음
   ```

2. **Pred 신호**:
   ```
   시각 t1: low(↑) + high(↑) = total(↑↑) → 급상승 → 큰 Peak
   시각 t2: low(↑) + high(↓) = total(~)  → 평평 → Peak 생성 안 됨
   시각 t3: low(~) + high(↑) = total(↑)  → 상승 → Peak 생성

   결과: Random Phase로 무작위 간섭 → Spurious peak 생성
   ```

**Tiling Fix와의 관계**:
- Spectral Interpolation은 Tiling 문제를 해결 (ACF 87% 개선)
- 하지만 Random Phase 자체는 그대로 → 위상 관계 무작위성 유지
- 따라서 Interaction 58.6%는 변하지 않음
- **결론**: Tiling과 Interaction은 독립적인 문제

**검증 방법**:
- 파형 시각화로 실제 패턴 확인
- Peak 개수 비교
- 상관관계 분석

**예상 결과**: ✅ "Interaction"은 위상 관계 차이를 측정함을 확인

---

### 가설 4: 개별 성분도 문제 있음

**주장**: 저주파/고주파 개별적으로도 과다 cycle 생성 (41.3%)

**근거**:
- 저주파: 0.3% (거의 문제없음)
- 고주파: 41.0% (중간 수준 문제)

**왜 고주파에서 문제가 생기나?**
- Random Phase로 인한 spurious peak
- True의 고주파는 물리적 제약 (압력 변동 범위)
- Pred의 고주파는 PSD만 맞춤 (제약 없음)

**검증 방법**:
```python
peaks_high_true = find_peaks(high_true)
peaks_high_pred = find_peaks(high_pred)

len(peaks_high_pred) / len(peaks_high_true)
# Expected: ~1.26배 (41% 기여도와 일치)
```

**예상 결과**: ✅ 고주파 자체도 일부 문제 확인

---

## 📁 출력 파일

### 1. 전체 구간 그래프

각 Gap별 파형 분해:
- `results/gap_3days/waveform_decomposition_true.png`
- `results/gap_3days/waveform_decomposition_pred.png`
- `results/gap_7days/waveform_decomposition_true.png`
- `results/gap_7days/waveform_decomposition_pred.png`
- `results/gap_14days/waveform_decomposition_true.png`
- `results/gap_14days/waveform_decomposition_pred.png`
- `results/gap_24days/waveform_decomposition_true.png`
- `results/gap_24days/waveform_decomposition_pred.png`

### 2. 확대 그래프

각 Gap별 2개:
- `results/gap_Xdays/waveform_detail_start.png` (처음 500 points)
- `results/gap_Xdays/waveform_detail_middle.png` (중간 500 points)

### 3. 분석 요약

- `results/WAVEFORM_ANALYSIS_SUMMARY.md`
  - 재조합 정확도 (모든 gap)
  - 상관관계 비교 (True vs Pred)
  - Peak 개수 비교
  - "Interaction"의 의미 해석
  - 최종 결론

---

## 🚀 구현 단계

### Step 1: 스크립트 작성
- `visualize_gap_waveforms.py` 작성 (약 250줄)
- 한글 폰트 설정 포함 (`korean_font_utils.setup_korean_font()`)
- 데이터 로드 경로 확인 (results/gap_*days/*.npy)

### Step 2: 단일 Gap 테스트
- Gap 3일로 먼저 테스트
- 재조합 정확도 검증 (< 1e-10)
- 파형이 제대로 나오는지 확인

### Step 3: 전체 실행
- 4개 Gap 모두 실행 (3, 7, 14, 24일)
- True/Pred 각각 분석
- 그래프 생성 확인

### Step 4: 분석 및 문서화
- 위상 관계 차이 정량화
- Peak 개수 비교 통계
- WAVEFORM_ANALYSIS_SUMMARY.md 작성
- 기존 COMPONENT_ANALYSIS_RESULTS.md 업데이트
- README.md에 시각화 결과 추가

---

## 📝 기대 효과

### 1. "Interaction"의 명확한 이해
- 재조합 과정의 문제가 **아님**을 시각적 확인 (low + high = original 완벽)
- Rainflow 비선형성 + 위상 관계 차이임을 입증
- **58.6% 기여도의 원인 규명**

### 2. Tiling Fix와의 독립성 확인
- Tiling 문제: 주기적 반복 패턴 (해결됨 ✅)
- Interaction 문제: 위상 무작위성 (미해결, 근본 문제)
- 두 문제가 **독립적**임을 확인

### 3. Spectral Matching 실패 원인의 시각적 증명
- True: 저주파-고주파 물리적 상관 → 상쇄 효과 → Peak 적음
- Pred: Random Phase → 무작위 간섭 → Spurious peak 과다 생성
- **Peak 개수 차이 정량화**

### 4. 정확한 용어 사용 및 문서 개선
- ~~"재조합 문제"~~ → "위상 관계 차이로 인한 Rainflow 비선형 효과"
- ~~"Tiling 문제가 주범"~~ → "Interaction이 주범 (58.6%)"
- 기술적으로 정확한 설명으로 전체 문서 업데이트

---

## ⚠️ 주의사항

### 1. 재조합 완벽성
- `low + high = original`은 **항상 성립**
- 이것이 안 되면 코드 버그임

### 2. "Interaction"의 의미
- 재조합 과정의 문제가 **아님**
- Rainflow(A + B) ≠ Rainflow(A) + Rainflow(B)의 비선형성

### 3. 상관관계 해석
- Pearson correlation만으로는 부족
- 시각적 확인 필수
- 같은 방향 움직임 비율도 함께 분석

---

**계획 작성일**: 2025-12-11
**예상 소요시간**: 2-3시간
**우선순위**: 높음 (현재 결론의 정확성 검증)
