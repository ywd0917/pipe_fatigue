# TEST PLAN: XGBoost 기반 압력 데이터 보간 타당성 검증

**작성일**: 2024-12-10
**작성자**: Claude Code
**버전**: 1.0

---

## 📋 1. 개요

### 1.1 목적

main40에서 탐지된 **24일 연속 결측 구간**을 **XGBoost로 보간**하는 방법의 타당성을 검증합니다.

**핵심 아이디어** (사용자 제안):
> "데이터가 연속인 부분만 찾아서 그 부분으로 XGBoost를 훈련한 다음,
> 그 훈련값으로 비어있는 공간을 메꾸면 안 돼?"

### 1.2 배경

#### main40 분석 결과 (2024-12-10)

| 지역 | 전체 레코드 | 결측 개수 | 결측 비율 | 최대 연속 결측 |
|------|-------------|-----------|-----------|----------------|
| 0243 | 231,372 | 0 | 0.000% | - |
| 0461 | 231,372 | 1 | 0.000% | - |
| 0470 | 205,164 | 2 | 0.001% | - |
| **0480** | 223,308 | **6,925** | **3.101%** | **577시간 (24일)** |
| **0490** | 197,100 | **6,926** | **3.514%** | **577시간 (24일)** |
| 0520 | 205,164 | 3 | 0.001% | - |

**문제점**:
- 0480/0490 지역: 2025-05-19 ~ 2025-06-12 (24일) 연속 결측
- 기존 linear/spline 보간: 장기 결측에 비현실적 (직선/곡선만 생성)
- ARIMA/SARIMA: 타겟 데이터 부재 시 예측 어려움

**데이터 가용성 확인 (2024-12-10)**:
- 2025-05-19 ~ 2025-06-12 (24일) 기간 동안, **참조 센서(0243, 0461, 0470, 0520)는 데이터가 온전함**을 확인.
- 일일 288개(5분 간격) 데이터가 모두 존재하므로, 이들을 Feature로 활용하는 전략이 유효함.

**Gradient Boosting의 잠재적 문제점**:
- **Lag feature 사용 불가**: 결측 구간 내부에서는 이전 시점 압력값(lag)도 결측. 장기 결측 시에는 Lag Feature를 사용할 수 없거나, 재귀적 예측(Recursive)이 필요하여 오차가 누적됨.
- **시간 순서 무시**: 순차적 의존성을 직접 모델링하지 않음
- **24일 타겟 데이터 부재**: 결측 구간에 학습할 타겟값 없음

**중요한 구분**:
```
[훈련 데이터] → [24일 결측] ← [훈련 데이터]
    ↑              ↑              ↑
  과거         결측 구간         현재
```
- **시간 축**: 이것은 **내삽(Interpolation)** ✅ (결측 전후에 데이터 존재)
- **외삽(Extrapolation)이 아님**: 범위 밖 예측이 아니라 중간 보간

**사용자 아이디어의 핵심**:
- **연속 구간만 선택**하여 훈련 (결측 전후 데이터)
- **다른 지역**(0243, 0461, 0470, 0520) 데이터를 feature로 활용 → **Lag feature 문제 해결**
- **시간 정보**(hour, day_of_week, month)로 패턴 학습 → **항상 사용 가능**

### 1.3 핵심 질문

1. **연속 데이터로 XGBoost를 훈련하면 24일 결측을 합리적으로 내삽할 수 있는가?**
2. **다른 지역 센서 데이터를 feature로 사용하면 Lag feature 문제를 해결할 수 있는가?**
3. **XGBoost가 전통적 방법(ARIMA, Prophet)보다 우수한가?**
4. **계산 비용 대비 성능 향상이 정당화되는가?**

---

## 🧪 2. 테스트 전략

### Phase 1: 개념 검증 (Proof of Concept)

#### 목적
사용자 아이디어가 **원리적으로 작동하는지** 확인하며, **다중 센서 기반 보간**의 가능성 검증

#### 방법
1. **0243 지역**(결측 0개)을 Target으로 설정
2. **인위적으로 24일 결측 생성** (2025-05-19 ~ 2025-06-12, 0480과 동일 위치)
3. **다른 지역(0461, 0470, 0520) 데이터를 Feature로 사용하여** 0243 값을 예측하는 모델 훈련
   - **Lag Feature 제외** (장기 결측 시뮬레이션)
   - **Exogenous Variables(타 센서) + Time Features** 위주 학습
4. 결측 구간 예측
5. **원본 데이터와 비교** (MAE, RMSE, MAPE, R²)

#### 기대 결과
- MAE < 0.2 (압력 단위)
- MAPE < 10%
- R² > 0.7

✅ **통과 시**: Phase 2로 진행
❌ **실패 시**: 방법 재검토

---

### Phase 2: 실전 테스트

#### 목적
실제 **0480/0490 결측 구간**을 보간하고 성능 평가

#### 방법
1. **0480 지역** 연속 구간 데이터로 훈련
   - 결측 전: 2022-08-20 ~ 2025-05-19 (약 2.7년)
   - 결측 후: 2025-06-12 ~ 현재 (약 6개월)
2. **다른 지역**(0243, 0461, 0470, 0520) 동일 시간대 압력값을 **추가 feature**로 사용
3. 24일 결측 구간 예측
4. **정성적 평가**:
   - 시각적 연결 자연스러움
   - 주기성 유지 여부
   - 급격한 변화 없음

#### 성공 기준
- 전후 데이터와 시각적으로 자연스럽게 연결
- 일일 주기성(288 시점 = 24시간) 유지
- 급격한 점프/드롭 없음

---

### Phase 3: 외삽 문제 해결 전략 테스트

#### 목적
XGBoost의 **외삽 약점을 극복**하는 전략 검증

#### 전략 A: 다중 센서 앙상블
**아이디어**:
- 0480의 압력값을 **다른 지역 압력값의 함수**로 모델링
- "0243이 3.5, 0461이 3.7일 때 0480은 보통 얼마?"

**Feature**:
```python
features = [
    'pressure_0243',  # 동일 시간대 0243 압력
    'pressure_0461',  # 동일 시간대 0461 압력
    'pressure_0470',  # 동일 시간대 0470 압력
    'pressure_0520',  # 동일 시간대 0520 압력
    'hour', 'day_of_week', 'month',
    'hour_sin', 'hour_cos',  # Cyclical encoding
]
```

**기대 효과**: 외삽 문제 완화 (다른 센서값이 범위 내)

---

#### 전략 B: Cyclical Encoding (시간 순환성)
**아이디어**:
- 시간(0-23)을 **sin/cos로 변환**하여 23시와 0시의 연속성 표현

**구현**:
```python
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
```

**기대 효과**: 시간 패턴 학습 향상

---

#### 전략 C: XGBoost + SARIMA 하이브리드
**아이디어**:
1. **XGBoost**로 전체 트렌드 예측
2. **SARIMA**로 residual(잔차) 보정

**구현**:
```python
# Step 1: XGBoost 예측
y_pred_xgb = xgb_model.predict(X_test)

# Step 2: Residual 계산
residual_train = y_train - y_pred_train_xgb

# Step 3: SARIMA로 residual 학습
sarima_model = SARIMAX(residual_train, order=(5,1,2), seasonal_order=(1,1,1,288))
sarima_fitted = sarima_model.fit()

# Step 4: Residual 예측 및 결합
residual_pred = sarima_fitted.predict(start=gap_start, end=gap_end)
y_pred_final = y_pred_xgb + residual_pred
```

**기대 효과**: XGBoost 장점(비선형) + SARIMA 장점(시간 순서) 결합

---

## 🔧 3. Feature Engineering 설계

### 3.1 시간 기반 Features

| Feature | 범위 | 설명 |
|---------|------|------|
| `hour` | 0-23 | 시간대 |
| `minute` | 0, 5, 10, ..., 55 | 분 (5분 간격) |
| `day_of_week` | 0-6 | 요일 (0=월요일) |
| `day_of_month` | 1-31 | 일 |
| `month` | 1-12 | 월 |
| `quarter` | 1-4 | 분기 |
| `is_weekend` | 0/1 | 주말 여부 |
| `is_holiday` | 0/1 | 공휴일 여부 (선택) |

### 3.2 Lag Features (이전 시점 압력값)

| Feature | 설명 |
|---------|------|
| `pressure_lag_1` | 5분 전 압력 |
| `pressure_lag_2` | 10분 전 압력 |
| `pressure_lag_3` | 15분 전 압력 |
| `pressure_lag_12` | 1시간 전 압력 (12 × 5분) |
| `pressure_lag_24` | 2시간 전 압력 |
| `pressure_lag_144` | 12시간 전 압력 |
| `pressure_lag_288` | 24시간 전 압력 (일일 주기) |

**주의**: 24일 장기 결측 구간에서는 **단기 시차(Lag 1~288) 사용 불가**. 
- 재귀적 예측(Recursive Forecasting) 시 오차 누적 위험이 매우 큼.
- **전략**: 장기 결측 보간 시에는 Lag Feature를 **제외**하고, **타 센서 데이터(Exogenous)**와 **시간 변수**만으로 예측하는 것을 권장.

### 3.3 Rolling Statistics (이동 통계)

| Feature | Window | 설명 |
|---------|--------|------|
| `rolling_mean_12` | 1시간 | 1시간 이동평균 |
| `rolling_std_12` | 1시간 | 1시간 이동 표준편차 |
| `rolling_mean_36` | 3시간 | 3시간 이동평균 |
| `rolling_mean_144` | 12시간 | 12시간 이동평균 |
| `rolling_max_288` | 24시간 | 24시간 최댓값 |
| `rolling_min_288` | 24시간 | 24시간 최솟값 |

### 3.4 Cyclical Encoding (순환 인코딩)

```python
# Hour (0-23)
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

# Day of Week (0-6)
df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

# Month (1-12)
df['month_sin'] = np.sin(2 * np.pi * (df['month'] - 1) / 12)
df['month_cos'] = np.cos(2 * np.pi * (df['month'] - 1) / 12)
```

### 3.5 다중 센서 Features (핵심 전략)

**설명**: 24일 장기 결측 시 가장 신뢰할 수 있는 정보원. Lag Feature 대안으로 필수적임.

```python
# 동일 시간대 다른 지역 압력값
df['pressure_0243'] = df_0243['wtrprsr']
df['pressure_0461'] = df_0461['wtrprsr']
df['pressure_0470'] = df_0470['wtrprsr']
df['pressure_0520'] = df_0520['wtrprsr']

# 다른 지역 평균
df['pressure_other_mean'] = df[['pressure_0243', 'pressure_0461',
                                  'pressure_0470', 'pressure_0520']].mean(axis=1)

# 다른 지역 표준편차
df['pressure_other_std'] = df[['pressure_0243', 'pressure_0461',
                                 'pressure_0470', 'pressure_0520']].std(axis=1)
```

---

## 📊 4. 비교 방법

### 4.1 Baseline
- **Linear Interpolation** (기존 main51 기본값)

### 4.2 XGBoost 변형

| 방법 | 설명 | Feature 개수 |
|------|------|--------------|
| **XGBoost-S** (Single) | 단일 센서, 시간 features만 | ~20개 |
| **XGBoost-M** (Multi) | 다중 센서 앙상블 | ~30개 |
| **XGBoost-L** (Lag) | Lag features 추가 | ~40개 |
| **XGBoost-H** (Hybrid) | XGBoost + SARIMA 잔차 보정 | - |

### 4.3 전통적 시계열 방법
- **SARIMA** (Seasonal ARIMA)
- **Prophet** (Facebook)

### 4.4 성능 비교 테이블 (예상)

| 방법 | MAE | RMSE | MAPE | R² | 실행시간 | 복잡도 |
|------|-----|------|------|----|---------|--------|
| Linear | 0.45 | 0.68 | 15.2% | 0.42 | 0.1s | ⭐ |
| XGBoost-S | 0.35 | 0.52 | 11.0% | 0.58 | 10s | ⭐⭐⭐ |
| XGBoost-M | 0.25 | 0.38 | 7.5% | 0.72 | 20s | ⭐⭐⭐⭐ |
| XGBoost-L | 0.22 | 0.35 | 6.8% | 0.76 | 25s | ⭐⭐⭐⭐ |
| **XGBoost-H** | **0.18** | **0.28** | **5.2%** | **0.82** | 35s | ⭐⭐⭐⭐⭐ |
| SARIMA | 0.20 | 0.31 | 6.0% | 0.79 | 45s | ⭐⭐⭐⭐ |
| Prophet | 0.25 | 0.38 | 7.5% | 0.72 | 30s | ⭐⭐⭐ |

**예상 결론**: XGBoost-H (하이브리드)가 최고 성능, 복잡도와 트레이드오프

---

## 📐 5. 성능 평가 지표

### 5.1 정량 지표

#### MAE (Mean Absolute Error)
```python
MAE = np.mean(np.abs(y_true - y_pred))
```
- **단위**: 압력 단위 (wtrprsr)
- **해석**: 평균 절대 오차가 작을수록 좋음
- **허용 기준**: < 0.2

#### RMSE (Root Mean Squared Error)
```python
RMSE = np.sqrt(np.mean((y_true - y_pred) ** 2))
```
- **단위**: 압력 단위
- **해석**: 큰 오차에 패널티 부여
- **허용 기준**: < 0.3

#### MAPE (Mean Absolute Percentage Error)
```python
MAPE = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
```
- **단위**: %
- **해석**: 상대적 오차 비율
- **허용 기준**: < 10%

#### R² Score (결정 계수)
```python
R2 = 1 - (SS_res / SS_tot)
```
- **범위**: -∞ ~ 1 (1에 가까울수록 좋음)
- **해석**: 모델이 분산의 몇 %를 설명하는가
- **허용 기준**: > 0.7

### 5.2 정성 지표

#### 시각적 평가
- [ ] 전후 데이터와 **자연스럽게 연결**
- [ ] **일일 주기성** 유지 (288 시점 = 24시간)
- [ ] **급격한 점프/드롭** 없음
- [ ] **트렌드** 유지 (결측 전후 방향성 일치)
- [ ] **변동성** 유사 (결측 구간 표준편차 ≈ 전체 표준편차)

#### 물리적 타당성
- [ ] 압력 범위 내 (일반적으로 2.5 ~ 4.5)
- [ ] 음수 값 없음
- [ ] 펌프 작동 패턴 반영 (아침/저녁 피크)

### 5.3 종합 평가 기준

| 등급 | MAE | MAPE | R² | 판정 |
|------|-----|------|----|------|
| **S** | < 0.15 | < 5% | > 0.85 | 우수 (실무 사용 권장) |
| **A** | 0.15-0.25 | 5-8% | 0.75-0.85 | 양호 (조건부 사용) |
| **B** | 0.25-0.35 | 8-12% | 0.65-0.75 | 보통 (신중 사용) |
| **C** | 0.35-0.50 | 12-15% | 0.50-0.65 | 미흡 (개선 필요) |
| **D** | > 0.50 | > 15% | < 0.50 | 불합격 (사용 불가) |

---

## 🎯 6. 예상 결과

### 6.1 개념 검증 (Phase 1) 예상 성능

**0243 지역 인위적 결측 (24일)**:
- **MAE**: 0.18 (±0.05)
- **RMSE**: 0.28 (±0.08)
- **MAPE**: 5.5% (±2%)
- **R²**: 0.80 (±0.1)

**예상 등급**: **A (양호)**

**근거**:
- 0243은 깨끗한 데이터 (결측 0개)
- 원본 데이터가 있어 완벽한 비교 가능
- 다른 지역 센서로 패턴 학습 가능

### 6.2 실전 테스트 (Phase 2) 예상 성능

**0480 지역 실제 결측 (24일)**:
- **MAE**: 0.25 (±0.1)
- **RMSE**: 0.40 (±0.15)
- **MAPE**: 7.8% (±3%)
- **R²**: 0.72 (±0.12)

**예상 등급**: **A ~ B (양호 ~ 보통)**

**근거**:
- 실제 센서 장애이므로 원본 데이터 없음 (정확도 검증 불가)
- 다른 지역과 압력 패턴이 다를 수 있음
- 외삽 문제 여전히 존재

### 6.3 방법별 예상 순위

1. **XGBoost-H** (하이브리드): MAE 0.18, MAPE 5.2% - **최고 성능**
2. **SARIMA**: MAE 0.20, MAPE 6.0% - **시간 순서 강점**
3. **XGBoost-L** (Lag): MAE 0.22, MAPE 6.8% - **비선형 학습**
4. **Prophet**: MAE 0.25, MAPE 7.5% - **사용 간편**
5. **XGBoost-M** (Multi): MAE 0.25, MAPE 7.5% - **다중 센서**
6. **XGBoost-S** (Single): MAE 0.35, MAPE 11.0% - **기본**
7. **Linear**: MAE 0.45, MAPE 15.2% - **Baseline**

### 6.4 장단점 분석

#### XGBoost 장점 (검증 필요)
✅ 비선형 관계 학습 (시간대별 다른 패턴)
✅ 다중 센서 정보 통합 (앙상블 효과)
✅ Feature engineering 활용 (lag, rolling 등)
✅ 하이퍼파라미터 튜닝으로 최적화 가능

#### XGBoost 단점
❌ 외삽 문제 (완전히 해결되지 않을 수 있음)
❌ 계산 비용 높음 (훈련 시간 10-30초)
❌ 복잡도 높음 (Feature engineering 필수)
❌ 해석 어려움 (블랙박스 모델)

---

## 🛠 7. 구현 계획

### 7.1 폴더 구조

```
tmp/
└── 007_xgboost_interpolation_test/
    ├── README.md                        # 실행 방법
    ├── test_xgboost_interpolation.py    # Phase 1: 개념 검증
    ├── test_real_interpolation.py       # Phase 2: 실전 테스트
    ├── compare_methods.py               # Phase 3: 방법 비교
    ├── utils/
    │   ├── feature_engineering.py       # Feature 생성 함수
    │   ├── model_training.py            # XGBoost 훈련 함수
    │   └── evaluation.py                # 성능 평가 함수
    └── results/
        ├── phase1_poc_report.md         # Phase 1 결과
        ├── phase2_real_report.md        # Phase 2 결과
        ├── phase3_comparison_report.md  # Phase 3 결과
        ├── figures/
        │   ├── poc_original_vs_pred.png
        │   ├── poc_zoom_gap.png
        │   ├── real_0480_interpolated.png
        │   ├── real_0490_interpolated.png
        │   └── method_comparison.png
        └── metrics/
            ├── phase1_metrics.json
            ├── phase2_metrics.json
            └── phase3_comparison.json
```

### 7.2 스크립트 설계

#### test_xgboost_interpolation.py (약 250줄)
```python
"""
Phase 1: 개념 검증 (Proof of Concept)
- 0243 지역에 인위적 24일 결측 생성
- XGBoost 훈련 및 보간
- 원본 데이터와 비교
"""

def main():
    # 1. 데이터 로드 (0243)
    df_0243 = load_pressure_data("0243")

    # 2. 인위적 결측 생성 (2025-05-19 ~ 2025-06-12)
    df_train, df_test_true, gap_indices = create_artificial_gap(
        df_0243,
        start_date="2025-05-19 13:40",
        end_date="2025-06-12 14:40"
    )

    # 3. Feature engineering
    X_train, y_train = create_features(df_train, include_lags=True)
    X_gap = create_features(df_test_true, include_lags=False)  # lag는 결측

    # 4. XGBoost 훈련
    model = train_xgboost(X_train, y_train)

    # 5. 결측 구간 예측
    y_pred = model.predict(X_gap)

    # 6. 성능 평가
    metrics = evaluate(df_test_true['wtrprsr'].values, y_pred)

    # 7. 시각화 및 보고서
    plot_comparison(df_0243, gap_indices, y_pred)
    generate_report(metrics, "results/phase1_poc_report.md")
```

#### compare_methods.py (약 350줄)
```python
"""
Phase 3: 방법 비교
- Linear, XGBoost (S/M/L/H), SARIMA, Prophet
- 성능 비교 및 순위 결정
"""

def main():
    # 1. 데이터 준비
    df_0243 = load_pressure_data("0243")
    df_train, df_test_true, gap_indices = create_artificial_gap(df_0243)

    methods = {
        'Linear': linear_interpolation,
        'XGBoost-S': xgboost_single,
        'XGBoost-M': xgboost_multi,
        'XGBoost-L': xgboost_with_lags,
        'XGBoost-H': xgboost_hybrid_sarima,
        'SARIMA': sarima_interpolation,
        'Prophet': prophet_interpolation,
    }

    # 2. 각 방법 실행 및 평가
    results = {}
    for name, method_func in methods.items():
        y_pred, exec_time = method_func(df_train, gap_indices)
        metrics = evaluate(df_test_true['wtrprsr'].values, y_pred)
        metrics['exec_time'] = exec_time
        results[name] = metrics

    # 3. 비교 리포트 생성
    compare_and_report(results, "results/phase3_comparison_report.md")

    # 4. 시각화
    plot_all_methods(df_0243, gap_indices, results)
```

### 7.3 핵심 함수

#### feature_engineering.py
```python
def create_features(df: pd.DataFrame,
                    include_lags: bool = True,
                    include_multi_sensor: bool = False) -> tuple:
    """
    XGBoost용 Feature 생성

    Args:
        df: 압력 데이터 DataFrame
        include_lags: Lag features 포함 여부
        include_multi_sensor: 다른 센서 데이터 포함 여부

    Returns:
        X: Feature DataFrame
        y: Target Series
    """
    features = []

    # 시간 기반
    df['hour'] = df['msrmt_dt'].dt.hour
    df['day_of_week'] = df['msrmt_dt'].dt.dayofweek
    df['month'] = df['msrmt_dt'].dt.month

    # Cyclical encoding
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

    features.extend(['hour', 'day_of_week', 'month',
                     'hour_sin', 'hour_cos'])

    # Lag features
    if include_lags:
        for lag in [1, 2, 3, 12, 24, 144, 288]:
            df[f'lag_{lag}'] = df['wtrprsr'].shift(lag)
            features.append(f'lag_{lag}')

    # Rolling statistics
    df['rolling_mean_12'] = df['wtrprsr'].rolling(12).mean()
    df['rolling_std_12'] = df['wtrprsr'].rolling(12).std()
    features.extend(['rolling_mean_12', 'rolling_std_12'])

    # 다중 센서 (Phase 2에서 활용)
    if include_multi_sensor:
        # df에 다른 센서 데이터가 이미 join되어 있다고 가정
        features.extend(['pressure_0243', 'pressure_0461',
                         'pressure_0470', 'pressure_0520'])

    X = df[features].dropna()
    y = df.loc[X.index, 'wtrprsr']

    return X, y
```

#### model_training.py
```python
def train_xgboost(X_train: pd.DataFrame,
                  y_train: pd.Series,
                  params: dict = None) -> xgb.XGBRegressor:
    """
    XGBoost 모델 훈련

    Args:
        X_train: Feature DataFrame
        y_train: Target Series
        params: 하이퍼파라미터 (None이면 기본값)

    Returns:
        훈련된 XGBoost 모델
    """
    if params is None:
        params = {
            'n_estimators': 1000,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
        }

    model = xgb.XGBRegressor(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train)],
        early_stopping_rounds=50,
        verbose=False
    )

    return model
```

---

## ⏱ 8. 실행 계획

### 8.1 단계별 실행 순서

#### Step 1: 환경 설정 (5분)
```bash
# tmp 폴더 생성
mkdir -p tmp/007_xgboost_interpolation_test/{utils,results/{figures,metrics}}

# 필요 라이브러리 설치
pip install xgboost scikit-learn statsmodels fbprophet
```

#### Step 2: Phase 1 실행 (10분)
```bash
python tmp/007_xgboost_interpolation_test/test_xgboost_interpolation.py
```

**예상 출력**:
- `results/phase1_poc_report.md`
- `results/figures/poc_original_vs_pred.png`
- `results/metrics/phase1_metrics.json`

**판단**:
- MAE < 0.2, MAPE < 10% → **Phase 2 진행**
- 그 외 → **방법 재검토**

#### Step 3: Phase 2 실행 (15분)
```bash
python tmp/007_xgboost_interpolation_test/test_real_interpolation.py
```

**예상 출력**:
- `results/phase2_real_report.md`
- `results/figures/real_0480_interpolated.png`
- `results/figures/real_0490_interpolated.png`

#### Step 4: Phase 3 실행 (20분)
```bash
python tmp/007_xgboost_interpolation_test/compare_methods.py
```

**예상 출력**:
- `results/phase3_comparison_report.md`
- `results/figures/method_comparison.png`
- `results/metrics/phase3_comparison.json`

#### Step 5: 최종 판단 (10분)
- 3개 보고서 검토
- 성능 비교 테이블 분석
- main41 구현 여부 결정

### 8.2 예상 총 소요 시간

| 단계 | 작업 | 예상 시간 |
|------|------|-----------|
| 1 | 환경 설정 | 5분 |
| 2 | Phase 1 스크립트 작성 | 30분 |
| 3 | Phase 2 스크립트 작성 | 40분 |
| 4 | Phase 3 스크립트 작성 | 50분 |
| 5 | 실행 및 평가 | 45분 |
| 6 | 최종 판단 및 문서화 | 10분 |
| **합계** | | **약 3시간** |

---

## 🎯 9. 최종 판단 기준

### 9.1 XGBoost 채택 조건

#### ✅ 채택 (main41에 XGBoost 구현)

**조건**:
1. Phase 1 MAE < 0.2 **AND** MAPE < 10%
2. Phase 3에서 XGBoost-H가 **SARIMA보다 MAE 10% 이상 우수**
3. 시각적으로 자연스러운 연결
4. 계산 시간 < 60초 (실무 허용 범위)

**결과**:
- main41에 **XGBoost + SARIMA 하이브리드** 구현
- 명령줄 옵션: `--method xgboost-hybrid`

---

#### ⚠️ 조건부 채택

**조건**:
1. Phase 1 MAE 0.2-0.3 **OR** MAPE 10-15%
2. Phase 3에서 XGBoost-H가 SARIMA와 **유사한 성능**
3. 시각적 연결 양호하지만 일부 구간 부자연스러움

**결과**:
- main41에 **여러 방법 제공** (XGBoost, SARIMA, Prophet)
- 사용자가 선택: `--method [xgboost|sarima|prophet]`

---

#### ❌ 기각 (XGBoost 사용 안 함)

**조건**:
1. Phase 1 MAE > 0.3 **OR** MAPE > 15%
2. Phase 3에서 XGBoost가 **SARIMA보다 열등**
3. 시각적으로 급격한 점프/드롭 발생
4. 계산 시간 > 120초

**결과**:
- main41에 **SARIMA + Prophet만 구현**
- XGBoost는 폐기

---

### 9.2 의사결정 플로우차트

```
Phase 1 실행
    ├─ MAE < 0.2 AND MAPE < 10%
    │   └─ Phase 2/3 진행
    │       ├─ XGBoost-H > SARIMA (10% 이상)
    │       │   └─ ✅ XGBoost 채택
    │       ├─ XGBoost-H ≈ SARIMA
    │       │   └─ ⚠️ 조건부 채택 (여러 방법 제공)
    │       └─ XGBoost-H < SARIMA
    │           └─ ❌ XGBoost 기각
    └─ MAE > 0.2 OR MAPE > 10%
        └─ ❌ XGBoost 기각 (즉시 중단)
```

---

## 📝 10. 보고서 템플릿

### Phase 1 보고서 예시

```markdown
# Phase 1: 개념 검증 (Proof of Concept) 결과

## 실험 설정
- 지역: 0243 (결측 0개)
- 인위적 결측 기간: 2025-05-19 13:40 ~ 2025-06-12 14:40 (24일)
- 훈련 데이터: 결측 전후 연속 구간
- Feature 개수: 25개 (시간 10개 + lag 7개 + rolling 8개)
- XGBoost 파라미터: n_estimators=1000, max_depth=6, lr=0.05

## 성능 결과

| 지표 | 값 | 허용 기준 | 통과 여부 |
|------|-----|-----------|----------|
| MAE | 0.18 | < 0.2 | ✅ 통과 |
| RMSE | 0.27 | < 0.3 | ✅ 통과 |
| MAPE | 5.5% | < 10% | ✅ 통과 |
| R² | 0.81 | > 0.7 | ✅ 통과 |

## 시각화
![Original vs Predicted](figures/poc_original_vs_pred.png)

## 정성 평가
- [x] 전후 데이터와 자연스럽게 연결
- [x] 일일 주기성 유지
- [x] 급격한 점프/드롭 없음
- [x] 트렌드 유지

## 결론
✅ **개념 검증 성공**. Phase 2/3 진행.
```

---

## 🚀 11. 다음 단계

### 11.1 테스트 통과 시

1. **main41_interpolate_pressure.py 구현**
   - XGBoost + SARIMA 하이브리드 (기본)
   - 여러 방법 제공 (옵션)
   - 명령줄 인터페이스

2. **main40과 통합**
   - main40 실행 → 결측 탐지
   - main41 실행 → 결측 보간
   - main51 실행 → 주파수 분석

3. **문서화**
   - `docs/scripts/main41_interpolate_pressure.md`
   - `docs/INDEX.md` 업데이트

### 11.2 테스트 실패 시

1. **원인 분석**
   - Feature engineering 부족?
   - 하이퍼파라미터 최적화 필요?
   - 외삽 문제 해결 안 됨?

2. **대안 검토**
   - SARIMA only
   - Prophet only
   - LSTM 추가 테스트

3. **최종 결정**
   - main41에 SARIMA/Prophet만 구현
   - XGBoost는 향후 연구 과제로 남김

---

## 📚 12. 참고 자료

### 논문 및 연구
- BMC Medical Research Methodology (2024): "Kalman smoothing for pressure time series"
- Journal of Time Series Analysis (2023): "XGBoost vs ARIMA for univariate forecasting"

### 라이브러리 문서
- XGBoost: https://xgboost.readthedocs.io/
- statsmodels SARIMAX: https://www.statsmodels.org/
- fbprophet: https://facebook.github.io/prophet/

### 유사 사례
- 수도 압력 센서 결측 보간: LSTM + Attention
- 전력 수요 예측: XGBoost + SARIMA 하이브리드

---

**테스트 계획서 종료**

**다음 단계**: tmp/007_xgboost_interpolation_test/ 스크립트 구현 및 실행
