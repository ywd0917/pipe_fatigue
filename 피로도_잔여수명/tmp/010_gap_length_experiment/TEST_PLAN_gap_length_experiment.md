# TEST PLAN: Gap 기간별 보간 성능 실험

**작성일**: 2025-12-10
**작성자**: Claude Code
**버전**: 1.0

---

## 📋 1. 개요

### 1.1 목적

**보간 가능한 최대 Gap 길이를 실험적으로 찾기**

### 1.2 배경

#### XGBoost/Prophet 24일 Gap 실패
- XGBoost: R² -0.04 (MAE 0.06, MAPE 3.2%)
- Prophet: R² -4.37 (MAE 0.17, MAPE 9.17%)
- 공통 문제: 평균값 근처만 예측, 변동성 캡처 실패

#### 핵심 질문
> "24일은 실패했지만, 3일/7일/14일은 어떨까?"

**가설**: Gap이 짧을수록 전후 데이터의 영향이 강해져 보간 성능이 향상될 것

### 1.3 실무적 의미

**성공 시나리오**:
- 3일 gap R² > 0.7 → "3일 이하 gap은 XGBoost로 보간 가능"
- 7일 gap R² > 0.5 → "1주일 이하는 조건부 가능"

**활용**:
- main41 구현 시 gap 길이에 따른 경고 시스템
- 센서 유지보수 정책 (gap 발생 후 X일 내 복구 필수)

---

## 🧪 2. 실험 설계

### 2.1 실험 대상

**데이터**: 0243 지역 (결측 0개, 총 231,372 records)

**이유**:
- 원본 데이터 완전 → 예측과 정확한 비교 가능
- 24일 gap 실험 이미 완료 → 동일 조건 유지

### 2.2 실험 조건

#### Gap 시작 위치 (고정)
```
시작: 2025-05-19 13:40
(24일 실험과 동일, 비교 일관성 유지)
```

#### Gap 길이 (변수)
| 실험 | Gap 길이 | 종료 시점 | 레코드 수 | 상태 |
|------|----------|-----------|-----------|------|
| Exp 1 | 3일 | 2025-05-22 13:40 | 864 | 신규 |
| Exp 2 | 7일 | 2025-05-26 13:40 | 2,016 | 신규 |
| Exp 3 | 14일 | 2025-06-02 13:40 | 4,032 | 신규 |
| Exp 4 | 24일 | 2025-06-12 14:40 | 6,925 | 완료 ✅ |

**레코드 수 계산**: 288 records/day × days

#### 테스트 모델 (3가지)
1. **XGBoost** (Multi-sensor features)
2. **Prophet** (Single-sensor, daily/weekly seasonality)
3. **Linear Interpolation** (Baseline)

### 2.3 평가 지표

| 지표 | 설명 | 성공 기준 |
|------|------|-----------|
| **R²** | 분산 설명력 (핵심) | > 0.5 (양호), > 0.7 (우수) |
| **MAE** | 평균 절대 오차 | < 0.15 |
| **MAPE** | 평균 절대 백분율 오차 | < 10% |
| **RMSE** | 제곱근 평균 제곱 오차 | < 0.20 |

---

## 📊 3. 예상 결과

### 3.1 가설

**Gap 길이 ↑ → R² ↓ (보간 어려움 증가)**

```
이유:
- 짧은 gap: 전후 데이터 패턴 유지
- 긴 gap: 패턴 변화 가능성 증가
- 데이터 특성(ACF 0.145): 시간 의존성 약함 → 급격한 성능 하락 예상
```

### 3.2 예상 성능표

#### XGBoost (Multi-sensor)

| Gap 길이 | 예상 MAE | 예상 MAPE | 예상 R² | 판정 |
|----------|----------|-----------|---------|------|
| 3일 | 0.05-0.08 | 3-5% | 0.6-0.8 | 우수 ✅ |
| 7일 | 0.06-0.10 | 4-7% | 0.4-0.6 | 양호 ⚠️ |
| 14일 | 0.08-0.12 | 5-9% | 0.2-0.4 | 미흡 ❌ |
| 24일 | 0.0595 ✅ | 3.20% ✅ | -0.04 ❌ | 실패 ❌ (확인됨) |

#### Prophet (Single-sensor)

| Gap 길이 | 예상 MAE | 예상 MAPE | 예상 R² | 판정 |
|----------|----------|-----------|---------|------|
| 3일 | 0.08-0.12 | 5-8% | 0.5-0.7 | 양호 ⚠️ |
| 7일 | 0.10-0.15 | 6-10% | 0.3-0.5 | 미흡 ❌ |
| 14일 | 0.15-0.20 | 8-12% | 0.1-0.3 | 실패 ❌ |
| 24일 | 0.1703 ❌ | 9.17% ⚠️ | -4.37 ❌ | 실패 ❌ (확인됨) |

#### Linear Interpolation (Baseline)

| Gap 길이 | 예상 MAE | 예상 MAPE | 예상 R² | 판정 |
|----------|----------|-----------|---------|------|
| 3일 | 0.10-0.15 | 6-10% | 0.3-0.5 | 기준선 |
| 7일 | 0.15-0.20 | 8-12% | 0.2-0.4 | 기준선 |
| 14일 | 0.20-0.25 | 10-15% | 0.1-0.3 | 기준선 |
| 24일 | 미측정 | 미측정 | 0.2-0.4 (예상) | 기준선 |

### 3.3 예상 그래프

```
R² 성능 vs Gap 길이

1.0 ┤
0.8 ┤ XGBoost ●
0.6 ┤         ●
0.4 ┤    Linear ■──■──■──■
0.2 ┤         Prophet ▲──▲
0.0 ┼────────────────────●──────
   -0.5 ┤                    ▲
   -1.0 ┤
   -4.0 ┤                        ▲ Prophet
    ────┴────┴────┴────┴────
        3일  7일  14일 24일
```

---

## 🔬 4. 실험 절차

### 4.1 데이터 준비

```python
# 0243 지역 로드
df_0243 = load_pressure_data("0243")

# Gap 설정
gap_configs = [
    {"days": 3, "end": "2025-05-22 13:40"},
    {"days": 7, "end": "2025-05-26 13:40"},
    {"days": 14, "end": "2025-06-02 13:40"},
]

gap_start = "2025-05-19 13:40"  # 모든 실험 동일
```

### 4.2 실험 루프

```python
results = []

for gap_config in gap_configs:
    gap_end = gap_config["end"]
    gap_days = gap_config["days"]

    # 1. Gap 생성
    df_train, df_gap_true, gap_mask = create_artificial_gap(
        df_0243, gap_start, gap_end
    )

    # 2. XGBoost 예측
    xgb_metrics = test_xgboost(df_train, df_gap_true)

    # 3. Prophet 예측
    prophet_metrics = test_prophet(df_train, df_gap_true)

    # 4. Linear 예측
    linear_metrics = test_linear(df_train, df_gap_true)

    # 5. 결과 저장
    results.append({
        "gap_days": gap_days,
        "xgboost": xgb_metrics,
        "prophet": prophet_metrics,
        "linear": linear_metrics,
    })
```

### 4.3 비교 분석

```python
# 모델별 성능 곡선
plot_performance_curves(results)

# Gap 길이별 비교
for result in results:
    gap_days = result["gap_days"]
    print(f"\n=== {gap_days}일 Gap ===")
    compare_models(result)
```

---

## 📈 5. 출력물

### 5.1 개별 실험 보고서

- `results/gap_3days_report.md`
- `results/gap_7days_report.md`
- `results/gap_14days_report.md`

**각 보고서 포함 내용**:
- 실험 설정
- 3개 모델 성능 비교
- 시각화 (예측 vs 실제, 잔차 분석)
- 성공/실패 판정

### 5.2 통합 비교 보고서

`results/COMPARISON_REPORT.md`

**내용**:
- Gap 길이별 성능 추이 그래프
- 모델별 강점/약점 분석
- 최종 권장사항
- 의사결정 트리

### 5.3 시각화

**results/figures/ 에 저장**:
1. `performance_vs_gap_length.png` - R²/MAE/MAPE 추이
2. `gap_3days_forecast.png` - 3일 gap 예측
3. `gap_7days_forecast.png` - 7일 gap 예측
4. `gap_14days_forecast.png` - 14일 gap 예측
5. `model_comparison_heatmap.png` - 모델×길이 히트맵

---

## 🎯 6. 의사결정 기준

### 6.1 시나리오별 결론

#### 시나리오 A: 3일 gap 성공 (R² > 0.7)
```
결론: 짧은 gap은 보간 가능
조치:
- main41 구현 (3일 이하 gap에 XGBoost 적용)
- 경고: "3일 초과 gap은 정확도 저하"
- 센서 정책: Gap 발생 후 3일 내 복구 권장
```

#### 시나리오 B: 7일 gap만 성공 (R² > 0.5)
```
결론: 1주일 이하는 조건부 가능
조치:
- main41 구현 (7일 이하 gap에 적용, 신뢰구간 표시)
- 강한 경고: "7일 초과는 비권장"
- 센서 정책: 1주일 내 복구 필수
```

#### 시나리오 C: 모두 실패 (R² < 0.5)
```
결론: 이 데이터로는 보간 자체가 불가능
조치:
- 보간 포기
- Gap 허용 (분석 제외)
- Linear interpolation만 제공 (경고 포함)
- 센서 이중화 권장
```

### 6.2 의사결정 플로우차트

```
3일 gap 실험
    ├─ R² > 0.7 → ✅ main41 구현 (3일 이하 적용)
    │                 └─ 7일 gap 실험 (추가 검증)
    │                     ├─ R² > 0.5 → 7일까지 확장
    │                     └─ R² < 0.5 → 3일로 제한
    │
    └─ R² < 0.7 → 7일 gap 실험
        ├─ R² > 0.5 → ⚠️ 조건부 적용 (7일 이하)
        │                 └─ 신뢰구간 필수 표시
        │
        └─ R² < 0.5 → ❌ 보간 포기
                          └─ Gap 허용 전략
```

---

## ⏱ 7. 실행 계획

### 7.1 구현 단계

| 단계 | 작업 | 예상 시간 |
|------|------|-----------|
| 1 | 폴더 구조 생성 | 5분 |
| 2 | gap_length_experiment.py 구현 | 30분 |
| 3 | 3일 gap 실험 실행 | 5분 |
| 4 | 7일 gap 실험 실행 | 5분 |
| 5 | 14일 gap 실험 실행 | 5분 |
| 6 | 통합 비교 보고서 생성 | 20분 |
| 7 | 시각화 및 최종 정리 | 10분 |
| **합계** | | **1.5시간** |

### 7.2 실행 명령어

```bash
# 전체 실험 실행 (3/7/14일 gap)
python tmp/010_gap_length_experiment/gap_length_experiment.py --all

# 특정 길이만 실험
python tmp/010_gap_length_experiment/gap_length_experiment.py --gap-days 3
python tmp/010_gap_length_experiment/gap_length_experiment.py --gap-days 7
python tmp/010_gap_length_experiment/gap_length_experiment.py --gap-days 14

# 특정 모델만 실험
python tmp/010_gap_length_experiment/gap_length_experiment.py --model xgboost
python tmp/010_gap_length_experiment/gap_length_experiment.py --model prophet
python tmp/010_gap_length_experiment/gap_length_experiment.py --model linear
```

---

## 📚 8. 참고 자료

### 8.1 선행 연구

- **007_xgboost_interpolation_test**: XGBoost 24일 gap 실패 (R² -0.04)
- **009_prophet_poc**: Prophet 24일 gap 실패 (R² -4.37)
- **008_interpolation_methods_analysis**: 데이터 특성 분석 (ACF 0.145)

### 8.2 이론적 근거

**Gap 길이와 보간 성능의 관계**:
- 시계열 예측에서 일반적으로 예측 구간 ↑ → 정확도 ↓
- 우리 데이터의 ACF 0.145 → 시간 의존성 약함 → 급격한 성능 하락 예상
- 하지만 3일 정도면 최소한의 연속성은 기대 가능

---

## 🚀 9. 다음 단계

### 실험 성공 시
1. main41 구현
2. Gap 길이별 경고 시스템
3. 실무 가이드라인 작성

### 실험 실패 시
1. Kalman Smoothing 시도
2. Gap 허용 정책 수립
3. 센서 이중화 제안

---

**테스트 계획서 종료**

**다음 단계**: tmp/010_gap_length_experiment/ 스크립트 구현 및 실행
