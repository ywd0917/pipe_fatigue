# Step 1: 데이터 적합성 분석 상세 계획

**작성일**: 2025-12-11
**예상 시간**: 2-3시간
**목적**: LSTM/Transformer 적용 전 데이터 구조 적합성 객관적 검증

---

## 📋 분석 목적

1. **LSTM/Transformer 적용 가능성** 사전 검증
2. **객관적 지표**로 GO/NO-GO 판단 기준 마련
3. **최적 sequence length** 결정
4. Phase 5 본격 진행 전 **리스크 제거**

---

## 🔬 분석 항목 (5가지)

### 1. Stationarity 검증

#### 목적
시계열이 정상(stationary)인지 확인
- 정상: 평균/분산이 시간에 무관
- 비정상: 트렌드/계절성 존재

#### 방법
**ADF Test (Augmented Dickey-Fuller)**:
- H0: Unit root 존재 (비정상)
- p-value < 0.05 → H0 기각 → 정상 시계열

**KPSS Test**:
- H0: 정상 시계열
- p-value > 0.05 → H0 채택 → 정상 시계열

#### 판정 기준

| ADF | KPSS | 판정 | 점수 | 조치 |
|-----|------|------|------|------|
| p < 0.05 | p > 0.05 | ○ 정상 | 20점 | 그대로 사용 |
| p < 0.05 | p < 0.05 | △ 약한 비정상 | 10점 | 차분 고려 |
| p > 0.05 | - | × 강한 비정상 | 0점 | 차분 필수 |

#### 의미
- **LSTM은 비정상성에 robust** (RNN 구조상)
- 하지만 **너무 심한 비정상성**은 문제
- Transformer는 **정상성 선호**

#### 구현
```python
from statsmodels.tsa.stattools import adfuller, kpss

# ADF Test
adf_result = adfuller(data)
adf_pvalue = adf_result[1]

# KPSS Test
kpss_result = kpss(data, regression='c')
kpss_pvalue = kpss_result[1]
```

---

### 2. 자기상관 구조 분석 (PACF)

#### 목적
직접적인 시간 의존성 구조 파악

#### 방법
**PACF (Partial Autocorrelation Function)**:
- ACF와 달리 **간접 효과 제거**
- Lag k에서 직접적 상관관계만 측정
- LSTM lookback window 결정에 핵심

**Phase 1 기존 결과**:
- 전체 ACF: 0.145 (낮음)
- 저주파 ACF: 0.9997 (매우 높음)
- 고주파 ACF: 0.0746 (낮음)

**추가 분석**:
- PACF로 **유의한 lag 개수** 확인
- 최적 sequence length 추정

#### 판정 기준

| 유의 Lag 개수 | 판정 | 점수 | 권장 Sequence Length |
|---------------|------|------|----------------------|
| > 10개 | ○ 강한 자기상관 | 25점 | Lag × 3 |
| 5-10개 | △ 중간 자기상관 | 12.5점 | Lag × 2 |
| < 5개 | × 약한 자기상관 | 0점 | LSTM 의미 없음 |

**유의성 기준**: |PACF| > 1.96/√n (95% 신뢰구간)

#### 의미
- **유의 lag가 많을수록** LSTM 효과적
- **lag가 너무 적으면** LSTM이 Linear와 차이 없음
- Phase 4 실패: past_60만 사용 (유의 lag 무시)

#### 구현
```python
from statsmodels.tsa.stattools import pacf

# PACF 계산 (최대 100 lag)
pacf_values = pacf(data, nlags=100)

# 유의성 임계값
threshold = 1.96 / np.sqrt(len(data))

# 유의한 lag 개수
significant_lags = np.sum(np.abs(pacf_values[1:]) > threshold)
```

---

### 3. 정보 엔트로피 측정

#### 목적
시계열의 **복잡도 및 무작위성** 정량화
→ 예측 가능성의 이론적 상한 확인

#### 방법
**Sample Entropy (SampEn)**:
- 시계열 패턴의 반복성 측정
- 낮을수록 규칙적, 높을수록 무작위

**Approximate Entropy (ApEn)**:
- Sample Entropy의 간단 버전
- 계산 빠름

**Phase 3 기존 결과**:
- 고주파 Sample Entropy: 0.86 (낮은 무작위성)
- 하지만 예측 R² 0.0216 (예측 불가)
- **"낮은 무작위성" ≠ "예측 가능"**

#### 판정 기준

| Sample Entropy | 의미 | 판정 | 점수 |
|----------------|------|------|------|
| < 1.0 | 낮은 복잡도, 규칙적 | ○ 예측 가능 | 20점 |
| 1.0 - 1.5 | 중간 복잡도 | △ 예측 어려움 | 10점 |
| > 1.5 | 높은 복잡도, 무작위 | × 예측 불가 | 0점 |

#### 의미
- **낮은 엔트로피**: 패턴 반복 → LSTM 학습 가능
- **높은 엔트로피**: 무작위 → LSTM도 못함
- Phase 3 교훈: 엔트로피 낮아도 **학습 가능한 패턴인지 별개**

#### 구현
```python
from scipy.stats import entropy
import antropy  # pip install antropy

# Sample Entropy
sampen = antropy.sample_entropy(data, order=2, metric='chebyshev')

# Approximate Entropy
apen = antropy.app_entropy(data, order=2, metric='chebyshev')
```

---

### 4. Sequence Length 실험

#### 목적
Transformer에 필요한 **최소 sequence length** 충족 여부

#### 방법
다양한 window size에서 ACF 계산:
- 60 (Phase 4 사용)
- 128
- 256
- 512 (Transformer 표준)
- 1024

각 window에서:
1. 데이터를 window로 슬라이싱
2. Window 내 ACF 계산
3. ACF 유지 여부 확인

#### 판정 기준

| Window Size | ACF 유지 | 판정 | 점수 | 추천 모델 |
|-------------|----------|------|------|-----------|
| 512+ | ACF > 0.1 | ○ Transformer 가능 | 20점 | Transformer |
| 256-511 | ACF > 0.05 | △ LSTM 권장 | 10점 | LSTM |
| < 256 | ACF < 0.05 | × 짧은 의존성 | 0점 | 전통 방법 |

#### 의미
- **Transformer**: 최소 512 token 권장
- **LSTM**: 128-256으로도 가능
- 현재 데이터 (5분 간격):
  - 512 tokens = 42.6시간
  - 256 tokens = 21.3시간
  - 60 tokens = 5시간 (Phase 4)

#### 구현
```python
from statsmodels.tsa.stattools import acf

results = {}
for window_size in [60, 128, 256, 512, 1024]:
    # 윈도우 슬라이싱
    windows = [data[i:i+window_size]
               for i in range(0, len(data)-window_size, window_size)]

    # 각 윈도우 ACF 평균
    acf_values = [acf(w, nlags=1)[1] for w in windows]
    avg_acf = np.mean(acf_values)

    results[window_size] = avg_acf
```

---

### 5. Gap 분포 분석

#### 목적
학습 데이터로 사용 가능한 **연속 구간** 충분성 확인

#### 방법
1. Missing data 위치 식별
2. 연속 데이터 구간 길이 계산
3. 분포 분석 (평균, 중앙값, 최소/최대)
4. LSTM/Transformer 학습 가능성 판단

**중요**: 현재 데이터는 gap 없음 (231,372 연속)
→ 이 분석은 **미래 적용 시 일반화를 위한 체크**

#### 판정 기준

| 평균 연속 구간 | 판정 | 점수 | 의미 |
|----------------|------|------|------|
| > 1000 points | ○ 충분 | 15점 | 학습 가능 |
| 500-1000 | △ 부족 | 7.5점 | 신중 |
| < 500 | × 매우 부족 | 0점 | 학습 불가 |

#### 의미
- **짧은 연속 구간**: LSTM 학습 불가능
- **Gap이 너무 많으면**: 배치 생성 어려움
- 현재 데이터: 231,372 연속 → **완벽** ✅

#### 구현
```python
# Missing value 없다고 가정 (Phase 4 데이터)
# 하지만 일반화를 위해 체크

def analyze_gaps(data):
    # NaN 위치
    is_nan = pd.isna(data)

    # 연속 구간 길이
    continuous_lengths = []
    current_length = 0

    for is_missing in is_nan:
        if not is_missing:
            current_length += 1
        else:
            if current_length > 0:
                continuous_lengths.append(current_length)
            current_length = 0

    if current_length > 0:
        continuous_lengths.append(current_length)

    return {
        'mean': np.mean(continuous_lengths),
        'median': np.median(continuous_lengths),
        'min': np.min(continuous_lengths),
        'max': np.max(continuous_lengths)
    }
```

---

## 📊 종합 적합도 점수 산출

### 점수 체계

```
총점 = (Stationarity × 1.0) +
       (PACF × 1.0) +
       (Entropy × 1.0) +
       (Sequence Length × 1.0) +
       (Gap 분포 × 1.0)

최대: 100점
```

**가중치**:
- 각 항목 동일 가중치 (20%, 25%, 20%, 20%, 15%)
- PACF가 가장 중요 (25%)

### 최종 판정 기준

| 총점 | 판정 | LSTM | Transformer | 조치 |
|------|------|------|-------------|------|
| **80-100점** | **○ 적합** | ✅ 가능 | ✅ 가능 | Step 2 전체 진행 |
| **50-79점** | **△ 보통** | ✅ 가능 | ⚠️ 신중 | Step 2 LSTM만 |
| **0-49점** | **× 부적합** | ❌ 어려움 | ❌ 불가 | 중단 고려 |

### 개별 항목 필수 조건

다음 중 하나라도 × → **NO-GO**:
- PACF < 5개 유의 lag (자기상관 너무 약함)
- Gap 평균 < 500 points (연속 데이터 부족)

---

## 🔧 구현 방법

### 필요 라이브러리

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 통계 검정
from statsmodels.tsa.stattools import adfuller, kpss, acf, pacf

# 엔트로피
from scipy.stats import entropy
import antropy  # pip install antropy

# 프로젝트 utils
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

# 009 utils
utils_dir = Path(__file__).parent.parent / "009_prophet_poc" / "utils"
sys.path.insert(0, str(utils_dir))
import data_loader
```

### 실행 시간 예상

| 단계 | 시간 | 세부 내용 |
|------|------|-----------|
| 데이터 로드 | 5분 | 231,372 레코드 |
| Stationarity 검증 | 20분 | ADF + KPSS |
| PACF 분석 | 30분 | 100 lags, 시각화 |
| 엔트로피 측정 | 15분 | SampEn + ApEn |
| Sequence Length 실험 | 30분 | 5가지 크기 |
| Gap 분포 분석 | 10분 | 연속 구간 |
| 시각화 | 30분 | 6-8개 그래프 |
| 보고서 작성 | 1시간 | Markdown |
| **총 예상** | **2.5-3시간** | |

---

## 📄 출력 형식

### 산출물 1: results/suitability_analysis.md

```markdown
# 데이터 적합성 분석 결과

**분석 일시**: 2025-12-11
**데이터**: 0243 소구역 압력 (231,372 records)

---

## 1. Stationarity 검증

### ADF Test
- Test Statistic: -8.234
- p-value: **0.0001** < 0.05
- 판정: ✅ 정상 시계열

### KPSS Test
- Test Statistic: 0.145
- p-value: **0.15** > 0.05
- 판정: ✅ 정상 시계열

### 종합 판정: **○ 정상** (20점)
- 차분 불필요
- LSTM/Transformer 직접 적용 가능

---

## 2. PACF 분석

- 유의 Lag 개수: **15개**
- 최대 유의 Lag: 45
- 권장 Sequence Length: **135** (45 × 3)

### 종합 판정: **○ 강한 자기상관** (25점)
- LSTM 효과적
- 과거 60개만 사용 (Phase 4)은 부족

---

## 3. 정보 엔트로피

- Sample Entropy: **1.2**
- Approximate Entropy: 1.15
- 복잡도: 중간

### 종합 판정: **△ 중간 복잡도** (10점)
- 예측 가능하지만 어려움
- Phase 3 교훈: 낮은 엔트로피 ≠ 예측 가능

---

## 4. Sequence Length 실험

| Window Size | Avg ACF | 판정 |
|-------------|---------|------|
| 60 | 0.132 | △ |
| 128 | 0.118 | △ |
| 256 | 0.095 | △ |
| 512 | 0.078 | ⚠️ |
| 1024 | 0.052 | × |

### 종합 판정: **△ LSTM 권장** (10점)
- 512 이상에서 ACF 급감
- Transformer 어려움, LSTM 적합
- 권장 Sequence Length: **256**

---

## 5. Gap 분포

- 평균 연속 구간: **231,372 points**
- Gap 개수: 0
- 완전 연속 데이터 ✅

### 종합 판정: **○ 충분** (15점)
- 학습 데이터 완벽

---

## 📊 종합 점수

**총점: 80점 / 100점**

| 항목 | 판정 | 점수 | 가중치 |
|------|------|------|--------|
| Stationarity | ○ | 20 | 20% |
| PACF | ○ | 25 | 25% |
| Entropy | △ | 10 | 20% |
| Sequence Length | △ | 10 | 20% |
| Gap 분포 | ○ | 15 | 15% |

---

## 🎯 최종 판정

### ✅ **적합 (80점)**

- **LSTM**: ✅ **가능** (권장)
- **Transformer**: ⚠️ **신중** (Sequence length 한계)
- **권장 Sequence Length**: 256
- **GO 결정**: **Step 2 진행** (LSTM 우선)

### 이유

1. **Stationarity ○**: 차분 불필요, 직접 적용 가능
2. **PACF ○**: 15개 유의 lag, LSTM 효과적
3. **Entropy △**: 중간 복잡도, 예측 가능하지만 어려움
4. **Sequence Length △**: 256까지 효과적, Transformer는 한계
5. **Gap 분포 ○**: 완전 연속 데이터

### 주의사항

- **Transformer는 512+ 필요**하지만 ACF 0.078로 약함
- **LSTM (256)이 더 적합**
- Phase 4 실패 원인 (past_60)보다 **4배 긴 컨텍스트**

---

## 📚 참고: 기존 결과 비교

| 프로젝트 | Method | Sequence Length | R² |
|----------|--------|-----------------|-----|
| Phase 4 | XGBoost | 60 | -0.016 |
| **012 Step 2** | **LSTM** | **256** | **예상: 0.2-0.4** |

**근거**: PACF 15개 유의 lag를 256 길이로 충분히 커버

---

**작성일**: 2025-12-11
```

### 산출물 2: 시각화 (6-8개 그래프)

1. **ADF/KPSS 결과** (원본 vs 차분)
2. **ACF/PACF 비교** (lag 0-100)
3. **Sequence Length별 ACF** (60/128/256/512)
4. **Sample Entropy 분포** (window별)
5. **Gap 분포 히스토그램**
6. **종합 점수 레이더 차트**

---

## 🚦 GO/NO-GO 결정

### GO (Step 2 진행 조건)

✅ **다음 중 하나 이상**:
1. 종합 점수 ≥ 50점
2. PACF 유의 lag ≥ 5개
3. Gap 평균 ≥ 500 points

→ **LSTM Quick Test (Step 2) 진행**

### NO-GO (중단 고려 조건)

❌ **다음 중 하나라도**:
1. 종합 점수 < 50점
2. PACF 유의 lag < 5개 (자기상관 너무 약함)
3. Gap 평균 < 500 points (연속 데이터 부족)

→ **전통적 방법 고려** (Gap 허용, Linear 경고)

---

## 📅 다음 단계

### Step 1 완료 후

1. **GO 판정 시**:
   - Step 2: Simple LSTM Quick Test 진행
   - 10-step 비재귀 예측으로 핵심 검증

2. **NO-GO 판정 시**:
   - 원인 분석 (어느 항목이 문제?)
   - 대안 검토 (주파수 분리 포기, 전통 방법)
   - DECISION_REPORT 작성

---

**작성일**: 2025-12-11
**예상 시간**: 2-3시간
**핵심 질문**: 데이터가 LSTM/Transformer에 적합한가?
**답**: 실험으로 확인! 🔬
