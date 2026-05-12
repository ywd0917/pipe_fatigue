# TEST PLAN: Prophet 기반 압력 데이터 보간 검증

**작성일**: 2025-12-10
**작성자**: Claude Code
**버전**: 1.0

---

## 📋 1. 개요

### 1.1 목적

**24일 연속 결측 구간**을 **Prophet**으로 보간하는 방법의 타당성을 검증합니다.

### 1.2 왜 Prophet인가?

#### XGBoost Phase 1 실패 교훈
- **MAE 0.06 ✅, MAPE 3.2% ✅** but **R² -0.04 ❌**
- 원인: 변동성(fluctuation) 캡처 실패
- 센서간 독립적 (correlation 0.039)
- 시간 패턴 약함 (ACF 0.145)

#### 데이터 분석 결과 (008 분석)
```
SAITS 적합성: 10/100 (부적합)
BRITS 적합성: 15/100 (부적합)
XGBoost+SARIMA: 25/100 (부적합)
Prophet 적합성: 50/100 (최선)

이유:
- 센서간 상관도: 0.039 → 다중 센서 접근 무용
- 시간 자기상관: 0.145 → LSTM/SARIMA 무용
- 주기성 약함: 0.003 → 고급 모델 무용
- Prophet: 요구사항 낮음 → 작동 가능
```

#### Prophet의 장점
✅ **단순 추세 모델**: 약한 패턴도 추출 시도
✅ **구현 간단**: 5-15초 실행, 30분 구현
✅ **낮은 요구사항**: 센서 상관/시간 패턴 약해도 작동
✅ **계절성 자동 탐지**: STL decomposition 내장
✅ **불확실성 구간**: 예측 신뢰구간 제공

#### Prophet의 한계 (인지하고 시작)
⚠️ **예상 성능**: R² 0.5-0.7 (중간)
⚠️ **데이터 특성상 한계**: 약한 패턴 → 제한적 성능
⚠️ **24일 Gap**: 여전히 어려운 문제

### 1.3 핵심 질문

1. **Prophet이 XGBoost보다 R²이 높은가?** (목표: R² > 0.5)
2. **예측 신뢰구간이 현실적인가?** (너무 넓지 않은가?)
3. **계절성 분해가 유의미한가?** (주기성 0.003이지만 추출 가능한가?)
4. **실무 사용 가능한가?** (시각적 자연스러움, 계산 시간)

---

## 🧪 2. 테스트 전략

### Phase 1: 개념 검증 (Proof of Concept) - 단일 센서

#### 목적
Prophet이 **단일 센서 데이터로** 24일 결측을 보간할 수 있는지 검증

#### 방법
1. **0243 지역**(결측 0개)을 Target으로 설정
2. **인위적으로 24일 결측 생성** (2025-05-19 ~ 2025-06-12)
3. **Prophet 훈련** (결측 전후 데이터만 사용)
   - 추세(trend) 학습
   - 일일 계절성(daily seasonality) 학습
   - 주간 계절성(weekly seasonality) 학습
4. 결측 구간 예측
5. **원본 데이터와 비교** (MAE, RMSE, MAPE, R²)

#### Feature
```python
# Prophet은 ds(날짜)와 y(값)만 필요
df_prophet = pd.DataFrame({
    'ds': df['msrmt_dt'],  # 시간
    'y': df['wtrprsr']     # 압력
})
```

#### 기대 결과
- **MAE**: 0.05-0.10 (XGBoost 0.06보다 양호)
- **MAPE**: 3-7% (XGBoost 3.2%와 유사)
- **R²**: 0.5-0.7 (XGBoost -0.04보다 훨씬 우수) ← **핵심 목표**
- **Grade**: B-A (보통-양호)

✅ **통과 기준**: R² > 0.5 AND MAPE < 10%
❌ **실패 시**: 24일 gap 보간 자체가 불가능 → 다른 접근 필요

---

### Phase 2: 다중 센서 Exogenous Regressors (선택)

#### 목적
다른 센서를 **외생 변수(exogenous regressor)**로 추가하여 성능 향상 가능한지 검증

**주의**: 데이터 분석 결과 센서간 상관도 0.039이므로 **효과 제한적 예상**. Phase 1 성공 시에만 시도.

#### 방법
```python
# Prophet에 다른 센서 추가
df_prophet['pressure_0461'] = df_0461['wtrprsr']
df_prophet['pressure_0470'] = df_0470['wtrprsr']

model = Prophet()
model.add_regressor('pressure_0461')
model.add_regressor('pressure_0470')
model.fit(df_prophet)
```

#### 기대 결과
- **R² 개선**: 0.5-0.7 → 0.55-0.75 (+0.05 정도, 미미)
- **이유**: 센서간 독립적 (상관 0.039)

#### 결정 로직
```
IF Phase 2 R² - Phase 1 R² > 0.1:
    → 다중 센서 사용
ELSE:
    → 단일 센서만 사용 (복잡도 감소)
```

---

### Phase 3: 실전 테스트 (0480/0490)

#### 목적
실제 **0480/0490 결측 구간**을 보간하고 정성적 평가

#### 방법
1. **0480 지역** 연속 구간 데이터로 훈련
   - 결측 전: 2022-08-20 ~ 2025-05-19
   - 결측 후: 2025-06-12 ~ 현재
2. Prophet 예측
3. **정성적 평가**:
   - 시각적 연결 자연스러움
   - 주기성 유지 여부
   - 급격한 변화 없음
   - 예측 신뢰구간 현실적

#### 성공 기준
- 전후 데이터와 시각적으로 자연스럽게 연결
- 일일 주기성(288 시점 = 24시간) 유지
- 급격한 점프/드롭 없음
- 95% 신뢰구간이 합리적 (너무 넓지 않음)

---

## 🔧 3. Prophet 설정

### 3.1 기본 설정

```python
from prophet import Prophet

model = Prophet(
    # 일일 계절성 (5분 간격 → 288 주기)
    daily_seasonality=True,

    # 주간 계절성
    weekly_seasonality=True,

    # 연간 계절성 (데이터 기간 짧으면 False)
    yearly_seasonality=False,

    # 변화점 탐지 (트렌드 전환점)
    changepoint_prior_scale=0.05,  # 기본값, 필요 시 조정

    # 계절성 강도
    seasonality_prior_scale=10.0,  # 기본값

    # 불확실성 구간
    interval_width=0.95,  # 95% 신뢰구간

    # 성장 모델
    growth='linear',  # 'logistic'도 가능하지만 압력 데이터는 linear
)
```

### 3.2 Custom Seasonality (5분 간격 대응)

```python
# Prophet은 기본적으로 1시간 간격 daily seasonality
# 5분 간격(288 points/day)을 위한 커스텀 설정

model.add_seasonality(
    name='5min',
    period=1,  # 1일 주기
    fourier_order=10,  # 10개 푸리에 항 (세밀도 조절)
)
```

### 3.3 Hyperparameter Tuning (선택)

**Grid Search 대상**:
- `changepoint_prior_scale`: [0.001, 0.01, 0.05, 0.5]
- `seasonality_prior_scale`: [0.01, 0.1, 1.0, 10.0]
- `fourier_order` (daily): [5, 10, 15, 20]

**예상 시간**: 4 × 4 × 4 = 64 조합 × 15초 = 16분

**결정**: Phase 1 성공 시에만 시도 (기본값으로 충분할 가능성)

---

## 📊 4. 성능 평가 지표

### 4.1 정량 지표

#### MAE (Mean Absolute Error)
```python
MAE = np.mean(np.abs(y_true - y_pred))
```
- **허용 기준**: < 0.15 (XGBoost 0.06보다 다소 높아도 허용)

#### MAPE (Mean Absolute Percentage Error)
```python
MAPE = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
```
- **허용 기준**: < 10% (XGBoost 3.2%와 유사)

#### R² Score (결정 계수)
```python
R2 = 1 - (SS_res / SS_tot)
```
- **핵심 지표**: > 0.5 (XGBoost -0.04 극복)
- **목표**: 0.5-0.7

#### Coverage (Prediction Interval)
```python
# 95% 신뢰구간이 실제값을 얼마나 포함하는가?
coverage = np.mean((y_true >= yhat_lower) & (y_true <= yhat_upper))
```
- **기대**: 90-100% (95% 신뢰구간이면)
- **문제**: < 80% (신뢰구간이 부정확)

### 4.2 정성 지표

#### 시각적 평가
- [ ] 전후 데이터와 **자연스럽게 연결**
- [ ] **일일 주기성** 유지 (288 시점 = 24시간)
- [ ] **급격한 점프/드롭** 없음
- [ ] **트렌드** 유지
- [ ] **신뢰구간** 현실적 (너무 넓지 않음)

#### 계절성 분해 평가
- [ ] Trend component가 합리적
- [ ] Daily seasonality가 추출됨 (약하더라도)
- [ ] Weekly seasonality가 의미 있음

### 4.3 종합 평가 기준

| 등급 | MAE | MAPE | R² | 판정 |
|------|-----|------|----|------|
| **A** | < 0.10 | < 5% | > 0.7 | 우수 (실무 사용 권장) |
| **B** | 0.10-0.15 | 5-10% | 0.5-0.7 | 양호 (조건부 사용) ← **목표** |
| **C** | 0.15-0.25 | 10-15% | 0.3-0.5 | 보통 (신중 사용) |
| **D** | > 0.25 | > 15% | < 0.3 | 불합격 (사용 불가) |

---

## 🎯 5. 예상 결과

### 5.1 Phase 1 예상 성능

**0243 지역 인위적 결측 (24일)**:
- **MAE**: 0.08-0.12
- **MAPE**: 4-7%
- **R²**: 0.5-0.7 ← **핵심**
- **Coverage**: 85-95%

**예상 등급**: **B (양호)**

**근거**:
- Prophet은 약한 추세/계절성도 추출
- 단순 모델이지만 분산 설명 가능
- XGBoost보다 시간 순서 고려

### 5.2 Phase 2 예상 성능 (Multi-sensor)

**개선 폭**: +0.0-0.05 R² (미미)

**이유**: 센서간 독립 (상관 0.039)

**결정**: 효과 없으면 Phase 1만 사용

### 5.3 Phase 3 예상 결과 (실전)

**0480 지역**:
- 시각적 연결: 양호
- 주기성 유지: 부분적 (약한 주기성이지만 Prophet이 추출)
- 신뢰구간: 넓지만 합리적

**0490 지역**:
- 0480과 유사한 결과 예상

---

## 🔬 6. XGBoost vs Prophet 비교

### 6.1 예상 성능 비교

| 지표 | XGBoost (Phase 1 실제) | Prophet (예상) | 승자 |
|------|------------------------|----------------|------|
| **MAE** | 0.0595 | 0.08-0.12 | XGBoost |
| **MAPE** | 3.20% | 4-7% | XGBoost |
| **R²** | -0.0400 ❌ | 0.5-0.7 ✅ | **Prophet** |
| **실행 시간** | 15초 | 5-15초 | 유사 |
| **구현 복잡도** | 높음 (17 features) | 낮음 (2 컬럼) | **Prophet** |

### 6.2 왜 Prophet이 R²이 높을 것으로 예상되는가?

#### XGBoost 실패 원인
```python
# XGBoost 예측 결과
y_pred = [1.88, 1.88, 1.88, ...]  # 거의 상수

# 원본 데이터
y_true = [1.85, 1.92, 1.87, 1.90, ...]  # 변동 있음

# R² = 1 - Var(residual) / Var(y_true)
#     = 1 - Var(y_true - 1.88) / Var(y_true)
#     ≈ 1 - 1.05  # residual 분산이 원본 분산보다 큼
#     = -0.05 ❌
```

#### Prophet 작동 원리
```python
# Prophet 예측 (분해)
y_pred = trend + daily_seasonal + weekly_seasonal + noise

# Trend: 장기 추세 (있다면)
# Daily: 시간대별 패턴 (약하더라도 추출 시도)
# Weekly: 요일별 패턴 (약하더라도 추출 시도)

# 결과: 평균값이 아닌 변동 패턴 캡처
# R² = 1 - Var(residual) / Var(y_true) > 0
```

**핵심**: Prophet은 **시간 구조**(계절성)를 명시적으로 모델링 → 변동성 설명 가능

---

## 🛠 7. 구현 계획

### 7.1 폴더 구조

```
tmp/
└── 009_prophet_poc/
    ├── README.md
    ├── TEST_PLAN_prophet_interpolation.md  # 이 파일
    ├── prophet_phase1_single.py            # Phase 1: 단일 센서
    ├── prophet_phase2_multi.py             # Phase 2: 다중 센서
    ├── prophet_phase3_real.py              # Phase 3: 실전 (0480/0490)
    ├── utils/
    │   ├── data_loader.py                  # 데이터 로드 함수
    │   ├── evaluation.py                   # 성능 평가 함수
    │   └── visualization.py                # 시각화 함수
    └── results/
        ├── phase1_report.md
        ├── phase2_report.md
        ├── phase3_report.md
        ├── figures/
        │   ├── prophet_phase1_forecast.png
        │   ├── prophet_phase1_components.png
        │   ├── prophet_phase1_zoom_gap.png
        │   ├── prophet_phase3_0480.png
        │   └── prophet_phase3_0490.png
        └── metrics/
            ├── phase1_metrics.json
            ├── phase2_metrics.json
            └── phase3_metrics.json
```

### 7.2 스크립트 설계

#### prophet_phase1_single.py (약 150줄)
```python
"""
Phase 1: Prophet 단일 센서 보간 검증
- 0243 지역 인위적 결측 생성
- Prophet 훈련 및 예측
- 성능 평가
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt

def main():
    # 1. 데이터 로드
    df_0243 = load_pressure_data("0243")

    # 2. 인위적 결측 생성
    gap_start = "2025-05-19 13:40"
    gap_end = "2025-06-12 14:40"

    df_train = df_0243[
        (df_0243['msrmt_dt'] < gap_start) |
        (df_0243['msrmt_dt'] > gap_end)
    ]
    df_gap_true = df_0243[
        (df_0243['msrmt_dt'] >= gap_start) &
        (df_0243['msrmt_dt'] <= gap_end)
    ]

    # 3. Prophet 포맷으로 변환
    df_prophet = pd.DataFrame({
        'ds': df_train['msrmt_dt'],
        'y': df_train['wtrprsr']
    })

    # 4. Prophet 모델 훈련
    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        interval_width=0.95
    )

    # 5분 간격 커스텀 계절성
    model.add_seasonality(
        name='intraday',
        period=1,
        fourier_order=10
    )

    model.fit(df_prophet)

    # 5. 예측
    future = model.make_future_dataframe(
        periods=len(df_gap_true),
        freq='5T',
        include_history=False
    )
    forecast = model.predict(future)

    # 6. 성능 평가
    y_true = df_gap_true['wtrprsr'].values
    y_pred = forecast['yhat'].values

    metrics = {
        'mae': np.mean(np.abs(y_true - y_pred)),
        'rmse': np.sqrt(np.mean((y_true - y_pred) ** 2)),
        'mape': np.mean(np.abs((y_true - y_pred) / y_true)) * 100,
        'r2': 1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - y_true.mean()) ** 2),
    }

    # Coverage
    coverage = np.mean(
        (y_true >= forecast['yhat_lower'].values) &
        (y_true <= forecast['yhat_upper'].values)
    )
    metrics['coverage'] = coverage

    # 7. 시각화
    fig = model.plot(forecast)
    plt.savefig('results/figures/prophet_phase1_forecast.png')

    fig = model.plot_components(forecast)
    plt.savefig('results/figures/prophet_phase1_components.png')

    # 8. 보고서 생성
    generate_report(metrics, 'results/phase1_report.md')

    print(f"MAE: {metrics['mae']:.4f}")
    print(f"MAPE: {metrics['mape']:.2f}%")
    print(f"R²: {metrics['r2']:.4f}")
    print(f"Coverage: {metrics['coverage']:.2%}")

    # 9. 판정
    if metrics['r2'] > 0.5 and metrics['mape'] < 10:
        print("✅ Phase 1 PASS → Phase 2 진행")
        return True
    else:
        print("❌ Phase 1 FAIL → 재검토")
        return False

if __name__ == "__main__":
    main()
```

#### prophet_phase2_multi.py (약 180줄)
```python
"""
Phase 2: Prophet 다중 센서 Exogenous Regressors
- 0461, 0470을 외생 변수로 추가
- Phase 1과 성능 비교
"""

def main():
    # 1-3. Phase 1과 동일

    # 4. Prophet 모델 (Exogenous Regressors 추가)
    df_prophet = pd.DataFrame({
        'ds': df_train['msrmt_dt'],
        'y': df_train['wtrprsr'],
        'pressure_0461': df_0461.loc[df_train.index, 'wtrprsr'],
        'pressure_0470': df_0470.loc[df_train.index, 'wtrprsr']
    })

    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        interval_width=0.95
    )

    model.add_regressor('pressure_0461')
    model.add_regressor('pressure_0470')

    model.fit(df_prophet)

    # 5-9. Phase 1과 동일

    # 추가: Phase 1과 비교
    print(f"R² improvement: {r2_phase2 - r2_phase1:.4f}")

    if r2_phase2 - r2_phase1 > 0.1:
        print("✅ Multi-sensor 사용")
    else:
        print("⚠️ Single-sensor로 충분")
```

---

## ⏱ 8. 실행 계획

### 8.1 단계별 실행 순서

#### Step 1: 환경 설정 (5분)
```bash
# 폴더 생성
mkdir -p tmp/009_prophet_poc/{utils,results/{figures,metrics}}

# Prophet 설치
pip install prophet
```

#### Step 2: Phase 1 실행 (10분)
```bash
python tmp/009_prophet_poc/prophet_phase1_single.py
```

**예상 출력**:
```
MAE: 0.0950
MAPE: 5.20%
R²: 0.6500
Coverage: 92%

✅ Phase 1 PASS → Phase 2 진행
```

**판단**:
- R² > 0.5 AND MAPE < 10% → **Phase 2/3 진행**
- 그 외 → **24일 gap 보간 불가능** (방향 전환 필요)

#### Step 3: Phase 2 실행 (선택, 10분)
```bash
python tmp/009_prophet_poc/prophet_phase2_multi.py
```

**예상 출력**:
```
R² improvement: +0.02
⚠️ Single-sensor로 충분
```

#### Step 4: Phase 3 실행 (10분)
```bash
python tmp/009_prophet_poc/prophet_phase3_real.py
```

**예상 출력**:
- `results/figures/prophet_phase3_0480.png`
- `results/figures/prophet_phase3_0490.png`

#### Step 5: 최종 판단 (5분)
- 3개 보고서 검토
- XGBoost vs Prophet 비교
- main41 구현 여부 결정

### 8.2 예상 총 소요 시간

| 단계 | 작업 | 예상 시간 |
|------|------|-----------|
| 1 | 환경 설정 | 5분 |
| 2 | Phase 1 스크립트 작성 | 20분 |
| 3 | Phase 1 실행 | 10분 |
| 4 | Phase 2 스크립트 작성 (선택) | 15분 |
| 5 | Phase 3 스크립트 작성 | 15분 |
| 6 | Phase 3 실행 | 10분 |
| 7 | 최종 판단 및 문서화 | 10분 |
| **합계** | | **약 1.5시간** (XGBoost 3시간의 절반) |

---

## 🎯 9. 최종 판단 기준

### 9.1 Prophet 채택 조건

#### ✅ 채택 (main41에 Prophet 구현)

**조건**:
1. Phase 1 **R² > 0.5** AND **MAPE < 10%**
2. Phase 3에서 시각적으로 자연스러운 연결
3. 신뢰구간이 현실적 (너무 넓지 않음)

**결과**:
- main41에 **Prophet** 구현
- 명령줄 옵션: `--method prophet`

---

#### ⚠️ 조건부 채택

**조건**:
1. Phase 1 **R² 0.3-0.5** OR **MAPE 10-15%**
2. 시각적 연결 양호하지만 신뢰구간 넓음

**결과**:
- main41에 **여러 방법 제공** (Prophet + Linear)
- 사용자가 선택: `--method [prophet|linear]`
- 경고 메시지: "24일 gap은 보간 정확도가 제한적"

---

#### ❌ 기각 (보간 포기)

**조건**:
1. Phase 1 **R² < 0.3** OR **MAPE > 15%**
2. 시각적으로 급격한 점프/드롭 발생
3. 신뢰구간이 비현실적으로 넓음

**결과**:
- **24일 gap 보간 자체를 포기**
- 대안:
  - Gap 기간 단축 (3-7일)
  - Gap 예방 (센서 이중화)
  - 결측 허용 (해당 기간 분석 제외)

---

### 9.2 의사결정 플로우차트

```
Phase 1 실행
    ├─ R² > 0.5 AND MAPE < 10%
    │   └─ Phase 2/3 진행
    │       ├─ 시각적 양호
    │       │   └─ ✅ Prophet 채택
    │       └─ 시각적 부자연스러움
    │           └─ ⚠️ 조건부 채택 (경고 포함)
    └─ R² < 0.5 OR MAPE > 10%
        ├─ R² 0.3-0.5
        │   └─ ⚠️ 조건부 채택
        └─ R² < 0.3
            └─ ❌ 보간 포기 (방향 전환)
```

---

## 📝 10. 예상 보고서

### Phase 1 보고서 예시

```markdown
# Phase 1: Prophet 단일 센서 보간 검증 결과

## 실험 설정
- 지역: 0243
- 인위적 결측: 2025-05-19 ~ 2025-06-12 (24일)
- Prophet 설정:
  - Daily seasonality: True (Fourier order 10)
  - Weekly seasonality: True
  - Interval width: 95%

## 성능 결과

| 지표 | 값 | 허용 기준 | 통과 여부 |
|------|-----|-----------|----------|
| MAE | 0.095 | < 0.15 | ✅ 통과 |
| MAPE | 5.2% | < 10% | ✅ 통과 |
| R² | 0.65 | > 0.5 | ✅ 통과 |
| Coverage | 92% | > 80% | ✅ 통과 |
| Grade | B | - | 양호 |

## XGBoost vs Prophet

| 지표 | XGBoost | Prophet | 승자 |
|------|---------|---------|------|
| MAE | 0.060 | 0.095 | XGBoost |
| MAPE | 3.2% | 5.2% | XGBoost |
| **R²** | **-0.04** | **0.65** | **Prophet** ✅ |

**핵심**: Prophet이 변동성을 설명 (R² 0.65), XGBoost는 실패 (-0.04)

## 계절성 분해

![Components](figures/prophet_phase1_components.png)

- **Trend**: 약한 상승 추세
- **Daily**: 피크 15시, 최저 2시 (일일 변동폭 0.02)
- **Weekly**: 요일별 차이 미미

## 결론

✅ **Phase 1 성공**. Prophet이 XGBoost보다 R² 0.69 높음.
→ Phase 2/3 진행 권장.
```

---

## 🚀 11. 다음 단계

### 11.1 Prophet 채택 시

1. **main41_interpolate_pressure.py 구현**
   - Prophet 기본 (권장)
   - Linear interpolation (대조군)
   - 명령줄 인터페이스

2. **문서화**
   - `docs/scripts/main41_interpolate_pressure.md`
   - `docs/INDEX.md` 업데이트

### 11.2 Prophet 실패 시

1. **Gap 기간 실험**
   - 3일 gap 보간: R² 0.7-0.8 예상
   - 7일 gap 보간: R² 0.6-0.7 예상
   - 14일 gap 보간: R² 0.5-0.6 예상
   - 24일 gap 보간: R² 0.3-0.5 (한계)

2. **방향 전환 검토**
   - Gap 예방 (센서 이중화)
   - 결측 허용 (해당 기간 분석 제외)
   - 다른 분석 방법 (결측 전후만 분석)

---

## 📚 12. 참고 자료

### Prophet 문서
- [Prophet 공식 문서](https://facebook.github.io/prophet/)
- [Prophet 논문 (Taylor & Letham, 2018)](https://peerj.com/preprints/3190/)

### 유사 사례
- 전력 수요 예측: Prophet으로 24시간 예측
- 트래픽 예측: Prophet daily/weekly seasonality
- **압력 센서 결측**: Kalman smoothing (의료 분야)

---

**테스트 계획서 종료**

**다음 단계**: tmp/009_prophet_poc/ 스크립트 구현 및 실행
