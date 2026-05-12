# Phase 1 POC Results: XGBoost 기반 압력 데이터 보간 검증

**테스트 일자**: 2025-12-10
**스크립트**: `test_xgboost_interpolation.py`
**목적**: 24일 연속 결측 구간 보간 타당성 검증

---

## 📊 Executive Summary

### 테스트 개요
- **Target 센서**: 0243 (결측 0개 지역)
- **인위적 Gap 생성**: 2025-05-19 13:40 ~ 2025-06-12 14:40 (24일)
- **참조 센서**: 0461, 0470 (Multi-sensor approach)
- **Feature 전략**:
  - ✅ Multi-sensor features (타 센서 압력값)
  - ✅ Time features (hour, day, month 등)
  - ❌ Lag features (24일 gap에서 사용 불가)
  - ❌ Rolling features (복잡도 감소 위해 제외)

### 핵심 발견

| 항목 | 결과 | 평가 |
|------|------|------|
| **MAE** | 0.0595 | ✅ PASS (< 0.2) |
| **MAPE** | 3.20% | ✅ PASS (< 10%) |
| **R²** | -0.0400 | ❌ FAIL (> 0.7) |
| **Grade** | D | ❌ 사용 불가 |

### 주요 결론

1. **절대 오차는 우수** (MAE 0.06, MAPE 3.2%)
   - 예측값이 실제값과 평균적으로 매우 가까움
   - 상대 오차율도 3%로 실용적 수준

2. **설명력은 매우 부족** (R² -0.04)
   - 모델이 분산(variance)을 전혀 설명하지 못함
   - 평균값 예측보다도 나쁜 성능
   - **Root Cause**: 변동성(fluctuation) 캡처 실패

3. **Data Coverage 문제** (Gap size: 3,868 / 6,925 = 56%)
   - 0470 센서 데이터가 2025-06-01에 종료
   - Gap 후반부 11일(3,057 records) 평가 불가
   - 장기 예측 능력 검증 실패

---

## 🔧 Test Configuration

### 데이터 구성

```
Training Data:
├─ 0243 (target):  231,372 records → 인위적 gap 생성 후 201,293 records
├─ 0461 (feature): 231,372 records (전체 기간 커버)
└─ 0470 (feature): 205,164 records (2025-06-01까지만)

Gap Period:
├─ Start: 2025-05-19 13:40
├─ End:   2025-06-12 14:40
├─ Duration: 24 days (576 hours)
├─ Expected records: 6,925 (24 days × 288 records/day)
└─ Actual evaluated: 3,868 (56% coverage)
```

### Feature Engineering

**총 17개 Features**:

1. **Multi-sensor features (6개)**:
   - `pressure_0461`: 0461 센서 압력값
   - `pressure_0470`: 0470 센서 압력값
   - `pressure_other_mean`: 평균값
   - `pressure_other_std`: 표준편차
   - `pressure_other_max`: 최댓값
   - `pressure_other_min`: 최솟값

2. **Time features (11개)**:
   - `hour`, `hour_sin`, `hour_cos`: 시간 (0-23)
   - `day_of_week`, `dow_sin`, `dow_cos`: 요일 (0-6)
   - `month`, `month_sin`, `month_cos`: 월 (1-12)
   - `quarter`: 분기 (1-4)

### XGBoost Hyperparameters

```python
{
    'n_estimators': 2000,        # 충분한 학습 반복
    'max_depth': 8,              # 깊은 패턴 학습
    'learning_rate': 0.01,       # 세밀한 학습
    'subsample': 0.9,            # 90% 데이터 샘플링
    'colsample_bytree': 0.9,     # 90% 피처 샘플링
    'random_state': 42,
    'n_jobs': -1,
    'early_stopping_rounds': 50
}
```

---

## 📈 Performance Metrics

### Detailed Results

| Metric | Value | Threshold | Status | Interpretation |
|--------|-------|-----------|--------|----------------|
| **MAE** | 0.0595 | < 0.2 | ✅ PASS | 평균 절대 오차 0.06 (압력 단위) |
| **RMSE** | 0.0882 | < 0.3 | ✅ (참고) | 큰 오차도 제어됨 |
| **MAPE** | 3.20% | < 10% | ✅ PASS | 상대 오차율 3.2% |
| **R²** | -0.0400 | > 0.7 | ❌ FAIL | 분산 설명력 없음 (음수!) |

### 성적표 (Grading)

```
Grade: D (Fail - 사용 불가)

S: Excellent (실무 사용 권장)    - MAE < 0.05, MAPE < 3%, R² > 0.9
A: Good (조건부 사용)           - MAE < 0.1, MAPE < 5%, R² > 0.8
B: Fair (신중 사용)             - MAE < 0.15, MAPE < 7%, R² > 0.75
C: Poor (개선 필요)             - MAE < 0.2, MAPE < 10%, R² > 0.7
D: Fail (사용 불가)             - Any criterion failed
```

### MAE/MAPE는 좋은데 R²가 나쁜 이유

```
예시 시나리오:

실제값 (y_true): [1.5, 1.8, 1.4, 1.9, 1.3, 1.7, 1.6]
예측값 (y_pred): [1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55]  ← 거의 상수!

MAE  = mean(|1.5-1.55|, |1.8-1.55|, ...) = 0.15  ✅ 작음
MAPE = mean(|1.5-1.55|/1.5, ...) = 9.6%          ✅ 작음
R²   = 1 - SS_res/SS_tot = 1 - 0.25/0.06 = -3.2  ❌ 음수!
```

**현재 모델의 문제**:
- 평균값(mean) 근처의 거의 **상수값**을 예측
- 실제 압력의 **시간적 변동(fluctuation)**을 전혀 캡처하지 못함
- 절대 오차는 작지만 **패턴 학습 실패**

---

## 🔍 Gap Size Analysis

### "Gap size: 3,868"의 의미

많은 사람들이 오해하는 개념을 명확히 정리:

```
❌ 잘못된 해석: "보간 후에도 채워지지 않은 빈 공간이 3,868개"
✅ 올바른 해석: "피처 생성 후 예측 가능한 gap 레코드 수가 3,868개"
```

### Gap Size 변화 과정

```
Step 1: 인위적 Gap 생성
└─ 원래 gap 기간 (2025-05-19 ~ 2025-06-12):
   └─ 6,925 records (24 days × 288 records/day)

Step 2: Multi-sensor Feature 추가
└─ df_0243_gap.join(df_0461, how='left')  ✅ 성공 (0461은 전체 기간 커버)
└─ df_0243_gap.join(df_0470, how='left')  ⚠️ 부분 실패!
   └─ 0470 데이터: 2025-06-01까지만 존재
   └─ 2025-06-02 ~ 2025-06-12 (11일) → pressure_0470 = NaN

Step 3: Feature Engineering 중 dropna()
└─ X_full = create_features(...).dropna()
   └─ pressure_0470 = NaN인 행 모두 제거
   └─ 손실: 3,057 records (11일분)

Step 4: 최종 Gap Size
└─ 3,868 records = 6,925 - 3,057 (56%)
   └─ 이 3,868개는 모두 XGBoost로 예측되어 완전히 채워짐
   └─ Unfilled gaps = 0 (보간 성공)
   └─ Unevaluated gaps = 3,057 (평가 불가)
```

### Data Coverage Timeline

```
Gap Period:  |─────────────────────────────────|
             2025-05-19              2025-06-01  2025-06-12

0461 Data:   |═════════════════════════════════|  ✅ Full coverage
0470 Data:   |═════════════════════════|         ⚠️ Ends 2025-06-01

Evaluated:   |═════════════════════════|         56% (3,868 records)
Missing:                               |─────────| 44% (3,057 records)
```

### Impact on Evaluation

1. **편향된 평가** (Biased Evaluation):
   - Gap 초기 13일만 평가 (2025-05-19 ~ 2025-06-01)
   - Gap 후기 11일 미평가 (2025-06-02 ~ 2025-06-12)
   - 장기 예측 능력 검증 실패

2. **과소평가 가능성**:
   - Gap 초기: 모델이 상대적으로 쉬움 (학습 데이터와 가까움)
   - Gap 후기: 더 어려움 (시간적 거리 멀어짐)
   - 후기가 빠져서 실제보다 좋게 보일 수 있음

3. **0470 데이터 중요도**:
   - Feature Importance에서 0470이 직접 나타나지 않음 (Top 10 밖)
   - 하지만 aggregate features(mean, std, max, min)에 영향
   - 0470 없으면 0461 단일 센서로 감소 → 정보 손실

---

## 🎯 Feature Importance

### Top 10 Features

| Rank | Feature | Importance | Category | Interpretation |
|------|---------|------------|----------|----------------|
| 1 | `pressure_other_min` | 0.1158 | Multi-sensor | **타 센서 최솟값**이 가장 중요 |
| 2 | `pressure_other_std` | 0.1046 | Multi-sensor | 센서 간 변동성 |
| 3 | `month_cos` | 0.0983 | Time (seasonal) | 월별 계절 패턴 (cosine) |
| 4 | `month` | 0.0654 | Time (seasonal) | 월별 패턴 (linear) |
| 5 | `month_sin` | 0.0651 | Time (seasonal) | 월별 계절 패턴 (sine) |
| 6 | `dow_cos` | 0.0604 | Time (weekly) | 요일 패턴 (cosine) |
| 7 | `pressure_0461` | 0.0593 | Multi-sensor | 0461 센서 직접값 |
| 8 | `quarter` | 0.0560 | Time (seasonal) | 분기별 패턴 |
| 9 | `hour_sin` | 0.0488 | Time (daily) | 시간별 패턴 (sine) |
| 10 | `hour_cos` | 0.0447 | Time (daily) | 시간별 패턴 (cosine) |

### Key Insights

1. **Multi-sensor features가 핵심** (Top 1, 2, 7):
   - `pressure_other_min` (11.6%) + `pressure_other_std` (10.5%) + `pressure_0461` (5.9%)
   - 합계: **28.0%**의 설명력
   - **타 센서 데이터 없으면 예측 불가능**

2. **계절성 패턴 중요** (Top 3, 4, 5, 8):
   - Month 관련 features: **23.3%**
   - 압력 데이터에 월별 계절성 존재 확인
   - 겨울/여름 압력 차이 캡처

3. **일일 패턴은 상대적으로 약함** (Rank 9, 10):
   - Hour features: 9.4%
   - 시간대별 압력 변동이 크지 않음
   - 또는 모델이 이를 충분히 학습하지 못함

4. **0470 센서 직접값 미포함**:
   - Top 10에 `pressure_0470` 없음 (11위 이하)
   - 하지만 aggregate features(min, std, max, min)에 간접 기여
   - 0470 제거 시 성능 하락 예상

---

## 🔬 Root Cause Analysis: 왜 R²가 실패했는가?

### 1. 모델 예측 패턴 분석

시각화 파일: `results/figures/phase1_poc_comparison.png`

**관찰 사항** (추정):
- 예측값이 거의 **평탄한 선** (flat line)
- 실제값의 **진동(oscillation)** 캡처 실패
- 평균값 근처에서 작은 변동만 표현

### 2. 가능한 원인

#### (1) Feature 부족 (Lag/Rolling 제외)

```python
# 현재 사용
include_lags=False      # Lag features 제외
include_rolling=False   # Rolling window features 제외

# 결과
- 과거 압력값 정보 없음 (lag_1, lag_288, ...)
- 단기 추세 정보 없음 (rolling_mean, rolling_std, ...)
- 시간적 의존성 캡처 불가
```

**왜 제외했나?**:
- 24일 gap에서 lag features는 무용지물 (과거값도 NaN)
- Rolling features는 복잡도 증가

**문제**:
- 시계열의 핵심인 **자기상관(autocorrelation)** 무시
- 압력의 **momentum/inertia** 학습 불가

#### (2) 0470 데이터 조기 종료 (56% coverage)

```
평가 가능 구간: 2025-05-19 ~ 2025-06-01 (13일)
평가 불가 구간: 2025-06-02 ~ 2025-06-12 (11일)

- Gap 후기가 평가에서 제외됨
- 장기 예측 능력 검증 실패
- 실제 성능이 더 나쁠 가능성
```

#### (3) XGBoost의 근본적 한계

**Tree-based models의 특성**:
```
Decision Tree: if-else 규칙으로 분할
└─ 학습 데이터의 평균값으로 예측
└─ 훈련 데이터 범위 밖 외삽(extrapolation) 약함
└─ 시간 순서(temporal order) 무시

XGBoost: 여러 Tree의 앙상블
└─ Tree 한계를 다수결로 완화
└─ 하지만 근본적 한계는 여전
```

**시계열 예측에 불리한 이유**:
- 시간적 의존성(temporal dependency) 직접 모델링 안 함
- 과거→현재→미래 흐름 무시
- LSTM/SARIMA보다 시계열에 약함

#### (4) 24일 gap이 너무 길다

```
학습 데이터와 gap 사이 시간 격차:
└─ Gap 시작점: 2025-05-19 (학습 데이터 직후)
└─ Gap 중반점: 2025-05-31 (12일 후)
└─ Gap 종료점: 2025-06-12 (24일 후)

문제:
- 12일 후 압력 패턴은 학습 데이터와 다를 수 있음
- 날씨, 사용량 변화 등 외부 요인 반영 불가
- 타 센서만으로는 이런 변화 캡처 어려움
```

### 3. R² = -0.04의 의미

```
R² = 1 - (SS_res / SS_tot)

SS_res = Σ(y_true - y_pred)²  = 잔차 제곱합 (모델 오차)
SS_tot = Σ(y_true - y_mean)²  = 총 변동 (baseline 오차)

R² = -0.04 의미:
└─ SS_res > SS_tot
└─ 모델 오차 > Baseline(평균값) 오차
└─ 그냥 평균값을 예측하는 것보다 나쁨!
```

**구체적 시나리오**:
```python
y_true = [1.5, 1.8, 1.4, 1.9, 1.3, 1.7, 1.6]
y_mean = 1.60

# Baseline (평균값 예측)
y_baseline = [1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6]
SS_tot = (1.5-1.6)² + (1.8-1.6)² + ... = 0.36

# XGBoost 예측
y_pred = [1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55]
SS_res = (1.5-1.55)² + (1.8-1.55)² + ... = 0.375

R² = 1 - 0.375/0.36 = -0.042  ❌
```

현재 모델은 평균값(1.60) 대신 1.55를 예측하여 약간 벗어남.

### 4. MAE는 좋은데 R²가 나쁜 모순

```
MAE  = mean(|y_true - y_pred|)        → 절대 오차의 평균
R²   = 1 - var(y_true - y_pred)       → 분산 설명력
              ────────────────
                 var(y_true)
```

**현상**:
- MAE 0.06: 각 예측이 평균적으로 실제값에서 0.06만큼 떨어짐 ✅
- R² -0.04: 하지만 변동 패턴은 전혀 맞히지 못함 ❌

**비유**:
```
실제 압력: 1.5 → 1.8 → 1.4 → 1.9 → 1.3  (변동 큼)
XGBoost:   1.55 → 1.55 → 1.55 → 1.55 → 1.55  (평탄)

- 평균적으로 0.05 오차 (MAE 작음)
- 하지만 "언제 올라가고 내려갈지" 전혀 모름 (R² 나쁨)
```

---

## 🎬 Conclusions

### Phase 1 POC 판정

```
❌ PHASE 1 FAILED

이유:
1. R² < 0.7 (실제: -0.04)
2. Grade D (사용 불가)
3. 분산 설명력 전무
4. 평균값 예측보다 나쁜 성능
```

### 긍정적 측면

1. ✅ **절대 오차는 우수** (MAE 0.06, MAPE 3.2%)
2. ✅ **Multi-sensor approach 유효성 확인**
   - Feature importance 상위권이 모두 타 센서 관련
   - 0461 데이터 없으면 예측 불가능
3. ✅ **시간 패턴 학습 성공**
   - 월별 계절성 캡처 (23% importance)
   - 요일/시간대 패턴도 기여
4. ✅ **스크립트/파이프라인 구축 완료**
   - `utils/feature_engineering.py`
   - `utils/model_training.py`
   - `utils/evaluation.py`
5. ✅ **데이터 정렬 버그 5개 수정**
   - dropna() 타겟 보존
   - pressure_other_std NaN 처리
   - Index 보존 로직
   - Gap true values 분리 저장
   - Visualization indexing 수정

### 부정적 측면

1. ❌ **시간적 변동성 캡처 실패** (R² -0.04)
2. ❌ **Lag/Rolling features 사용 불가** (24일 gap)
3. ❌ **Data coverage 56%** (0470 조기 종료)
4. ❌ **XGBoost 단독으로는 부족**
5. ❌ **24일이 너무 긴 gap**

---

## 💡 Recommendations

### Option 1: Hybrid Approach (XGBoost + SARIMA) ⭐ 추천

**아이디어**:
```
Step 1: SARIMA로 시계열 패턴(추세, 계절성) 예측
Step 2: XGBoost로 SARIMA 잔차(residual)를 다른 센서로 보정
Step 3: SARIMA + Residual = 최종 예측
```

**장점**:
- SARIMA: 시간적 의존성, 계절성 캡처 ✅
- XGBoost: 타 센서 정보로 실시간 보정 ✅
- 두 방법의 장점 결합

**단점**:
- 복잡도 증가
- 계산 비용 증가
- SARIMA 파라미터 튜닝 필요

**구현**:
```python
# Step 1: SARIMA 훈련 (target 시계열만 사용)
sarima = SARIMAX(y_train, order=(5,1,2), seasonal_order=(1,1,1,288))
sarima_fit = sarima.fit()
y_sarima = sarima_fit.forecast(steps=len(gap))

# Step 2: SARIMA residual 계산
y_residual_train = y_train - sarima_fit.fittedvalues

# Step 3: XGBoost로 residual 예측 (타 센서 feature 사용)
xgb_residual = XGBRegressor()
xgb_residual.fit(X_train_sensors, y_residual_train)
y_residual_pred = xgb_residual.predict(X_gap_sensors)

# Step 4: 최종 예측
y_final = y_sarima + y_residual_pred
```

### Option 2: SARIMA 단독 사용

**방법**:
```python
sarima = SARIMAX(
    y_train,
    order=(5, 1, 2),
    seasonal_order=(1, 1, 1, 288),  # 288 = 5분 데이터의 1일 주기
    exog=X_train_sensors  # 타 센서를 exogenous variables로
)
```

**장점**:
- 시계열 전용 모델
- 시간적 의존성 직접 모델링
- 계절성/추세 자동 분해

**단점**:
- 학습 시간 오래 걸림 (288 seasonal period)
- 외생변수(exog) 효과 제한적
- Gap 내 타 센서 데이터 필요

### Option 3: LSTM/GRU (Deep Learning)

**방법**:
```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(lookback, n_features)),
    LSTM(32),
    Dense(1)
])

# Sliding window로 학습
X_train_seq, y_train_seq = create_sequences(df_train, lookback=288)
model.fit(X_train_seq, y_train_seq)
```

**장점**:
- 시계열 패턴 학습 강력
- 비선형 관계 캡처
- 다변량 시계열 처리 우수

**단점**:
- 대량 데이터 필요 (현재 201k records → 충분)
- 학습 시간 길고 GPU 필요
- 해석 가능성(interpretability) 낮음
- 오버피팅 위험

### Option 4: 0461 단독으로 재시도

**방법**:
- 0470 제외 (gap 기간 커버 안 됨)
- 0461만 사용 (전체 기간 커버)
- Gap size 6,925 → ~6,900 (거의 100%)

**장점**:
- Data coverage 100% 달성
- Gap 전체 기간 평가 가능
- 장기 예측 능력 검증

**단점**:
- Feature 수 감소 (17 → 13개)
- Multi-sensor diversity 손실
- 성능 하락 예상

### Option 5: Gap 기간 단축 (6일 or 12일)

**방법**:
```python
# 24일 → 6일로 단축
gap_start = "2025-05-19 13:40"
gap_end = "2025-05-25 13:40"  # 6일
```

**장점**:
- 단기 gap에서는 XGBoost 성능 향상 예상
- Lag features 사용 가능 (lag_288 = 1일)
- 0470 데이터 커버리지 문제 없음

**단점**:
- 실전 문제(24일 gap) 해결 안 됨
- Phase 2 적용 불가
- POC 목적 달성 실패

---

## 🚀 Next Steps

### Immediate Action (즉시 실행)

**Step 1**: 0461 단독으로 재테스트
```bash
# test_xgboost_interpolation.py 수정
df_others = {
    '0461': df_0461.set_index('msrmt_dt')[['wtrprsr']],
    # '0470' 제거
}

python test_xgboost_interpolation.py
```
**목적**: Data coverage 100% 확보하여 공정한 평가

---

**Step 2**: Hybrid Approach 구현 (Option 1)
```bash
# 새 스크립트 작성
vi test_xgboost_sarima_hybrid.py

# SARIMA + XGBoost residual correction
python test_xgboost_sarima_hybrid.py
```
**목적**: 시계열 패턴 + 타 센서 정보 결합

---

**Step 3**: 결과 비교 및 최종 결정
```
방법          | MAE  | R²   | 복잡도 | 실전 적용성
--------------|------|------|--------|------------
XGBoost 단독  | 0.06 | -0.04| 낮음   | ❌
0461 단독     | ?    | ?    | 낮음   | ?
SARIMA 단독   | ?    | ?    | 중간   | ?
Hybrid        | ?    | ?    | 높음   | ?
```

**판단 기준**:
- R² > 0.7: Phase 2 진행
- R² < 0.7: 대안 방법 검토 또는 프로젝트 중단

### Long-term Plan (장기 계획)

1. **Phase 2 준비** (R² 통과 시):
   - 실제 0480/0490 gap 데이터 로드
   - 0243, 0461, 0470, 0520을 feature로 사용
   - Cross-validation 추가
   - Production-ready 파이프라인 구축

2. **대안 탐색** (R² 실패 시):
   - Prophet (Facebook)
   - AutoML (AutoGluon, TPOT)
   - Ensemble (SARIMA + XGBoost + Prophet)
   - 보간 포기 및 결측 허용

---

## 📎 Appendix

### A. File Structure

```
tmp/007_xgboost_interpolation_test/
├── test_xgboost_interpolation.py       # Main script
├── utils/
│   ├── feature_engineering.py          # Feature 생성 (5 bugs fixed)
│   ├── model_training.py               # XGBoost 훈련
│   └── evaluation.py                   # 평가 및 시각화
├── results/
│   ├── metrics/
│   │   └── phase1_metrics.json         # 성능 지표 JSON
│   ├── figures/
│   │   └── phase1_poc_comparison.png   # 시각화
│   ├── phase1_poc_report.md            # 자동 생성 보고서
│   └── PHASE1_POC_RESULTS.md           # 본 문서
└── README.md                           # 사용 설명서
```

### B. Script Execution

```bash
# Phase 1 POC 실행
cd /Users/jhpark/development/eroumtech/fatigue/fatigue-qgis/tmp/007_xgboost_interpolation_test
python test_xgboost_interpolation.py

# 출력 예시
[Step 1] Loading pressure data...
[Step 2] Creating artificial gap...
[Step 3] Feature engineering...
[Step 4] Splitting train/test...
[Step 5] Training XGBoost model...
[Step 6] Predicting gap values...
[Step 7] Evaluating performance...
[Step 8] Generating visualizations...
[Step 9] Generating report...

FINAL RESULT
═══════════════════════════════════════
❌ PHASE 1 FAILED
```

### C. References

- **TEST_PLAN**: `docs/TEST_PLAN_xgboost_interpolation.md`
- **Data Quality Report**: `results/pressure_data_quality_report_20251210_121437.md`
- **Bug Analysis**: `docs/analysis/xgboost_data_alignment_issue.md` (696 lines)

---

**Document Version**: 1.0
**Generated**: 2025-12-10
**Author**: Claude Code
**Status**: Phase 1 Failed - Next steps required
