# Gap Interpolation 연구 프로젝트 (tmp/007~014)

**연구 기간**: 2025-12-10 ~ 2025-12-12
**목적**: 압력 데이터의 24일 연속 결측 구간을 보간하기 위한 최적 방법론 탐색

---

## 📋 연구 배경

### 문제 정의
main40에서 탐지된 **24일 연속 결측 구간** (0480, 0490 지역)을 어떻게 채울 것인가?

**⭐ 결측 데이터 정의** (2025-12-12 업데이트):
- **NaN 결측**: 원본 CSV에 행은 있지만 압력값(wtrprsr)이 NaN인 경우
- **Time Gap 결측**: 5분 간격이 빠진 시간대 (행 자체가 CSV에 없음)
- **총 결측**: NaN 결측 + Time Gap 결측

| 지역 | 총 결측 개수 | 결측 비율 | 최대 연속 결측 |
|------|-------------|-----------|----------------|
| 0243 | 0 | 0.000% | - |
| 0461 | 1 | 0.000% | - |
| 0470 | 2 | 0.001% | - |
| **0480** | **6,925** | **3.101%** | **24일** |
| **0490** | **6,926** | **3.514%** | **24일** |
| 0520 | 3 | 0.001% | - |

**주의**: 위 통계는 NaN 결측 + Time Gap 결측을 모두 포함한 수치입니다.

### 연구 목표
피로 분석(Rainflow counting)에 사용 가능한 수준의 보간 달성
- **목표 지표**: R² > 0.5 또는 Rainflow Match > 0.95

---

## 🔬 연구 프로젝트 요약

### Project 007: XGBoost 기반 보간 PoC
**결과**: ❌ 실패 (R² = -0.04)

| 지표 | 결과 | 목표 |
|------|------|------|
| MAE | 0.06 | < 0.2 ✅ |
| MAPE | 3.2% | < 10% ✅ |
| R² | **-0.04** | > 0.7 ❌ |

**실패 원인**: 변동성(fluctuation) 캡처 실패 → 평균값 예측만 수행

---

### Project 008: 보간 방법론 비교 분석
**핵심 발견**: 데이터 특성이 고급 보간에 부적합

| 특성 | 측정값 | 의미 |
|------|--------|------|
| 센서간 상관도 | 0.039 | 독립적 (다중센서 무용) |
| ACF | 0.145 | 시간 패턴 약함 |
| 주기성 | 0.003 | 계절성 거의 없음 |

**결론**: 14가지 방법론 중 Prophet 1순위 추천 (예상 R² 0.5-0.7)

---

### Project 009: Prophet 기반 보간
**결과**: ❌ 완전 실패 (R² = -4.37)

| 지표 | XGBoost | Prophet | 비교 |
|------|---------|---------|------|
| MAE | 0.0595 | 0.1703 | XGBoost 승 |
| MAPE | 3.20% | 9.17% | XGBoost 승 |
| R² | -0.04 | **-4.37** | XGBoost 승 |

**실패 원인**: Trend component가 잘못된 방향 학습, 노이즈 학습

---

### Project 010: Gap 길이별 실험
**가설**: Gap 길이 ↓ → R² ↑

| Gap 길이 | 예상 R² | 실제 R² |
|----------|---------|---------|
| 3일 | 0.6-0.8 | < 0 ❌ |
| 7일 | 0.4-0.6 | < 0 ❌ |
| 14일 | 0.2-0.4 | < 0 ❌ |
| 24일 | -0.04 | -0.04 ❌ |

**결론**: Gap 길이와 무관하게 모두 실패 → 데이터 특성의 근본적 한계

---

### Project 011: 주파수 분리 기반 보간
**접근**: 저주파/고주파 분리 후 컴포넌트별 맞춤 보간

#### Phase 1: 예측 가능성 분석 ✅
| 성분 | ACF | 예측 가능성 |
|------|-----|-------------|
| 저주파 | **0.9997** | ✅ 매우 높음 |
| 고주파 | 0.0746 | ❌ 낮음 |

#### Phase 2-4: 보간 시도 ❌
| 방법 | Gap | R² | 에너지 보존 |
|------|-----|-----|-------------|
| Spline+Mean | 3일 | -0.028 | 0.3% |
| XGBoost | 3일 | -0.016 | 0.32% |
| XGBoost | 24일 | -0.003 | 0.04% |

**핵심 발견**: Recursive prediction 오류 누적 (Validation R² 0.9984 → Gap R² < 0)

---

### Project 012: Transformer/LSTM 적합성 검증
**목적**: 딥러닝 방법 적용 가능성 빠른 검증

#### Step 1: 데이터 적합성 ✅
- 적합도: **70점** (△ 보통)
- PACF: 89개 유의 lag (Phase 4의 60은 부족)
- 권장 Sequence Length: **300**

#### Step 2: LSTM Quick Test ❌
| 예측 거리 | R² |
|-----------|-----|
| Step 2 (2분) | 0.283 ✅ |
| Step 3 (3분) | -0.350 ❌ |
| 10-step | **-0.238** ❌ |

**핵심 발견**:
- **비재귀 예측도 실패** → Recursive prediction이 근본 원인 아님
- **데이터가 본질적으로 2분 이상 예측 불가능**

**결정**: ❌ Phase 5 (Transformer/LSTM) 포기

---

### Project 013: 주파수 스펙트럼 보존 기반 합성
**새로운 접근**: 정확한 값 예측 대신 **동일한 주파수 스펙트럼**을 가진 합성 데이터 생성

#### 방법론
```
저주파 (ACF 0.9997) → ARMA Synthesis
고주파 (ACF 0.0746) → Random Phase IFFT
           ↓
      Edge Smoothing
           ↓
      재조합 + 검증
```

#### 결과
| Gap | Rainflow Match | PSD Sim | 판정 |
|-----|----------------|---------|------|
| 3일 | 0.700 | 0.953 | ❌ |
| 7일 | 0.718 | 0.919 | ❌ |
| 14일 | 0.848 | 0.948 | ⚠️ |
| 24일 | 0.861 | 0.937 | ⚠️ |

**핵심 발견**:
- **PSD 보존 ⊄ Rainflow 보존**
- Phase 정보 필수 → 예측 필요 → 불가능
- 초과 cycle의 **58.6%**가 재조합(Interaction)에서 발생

---

### Project 014: 성분별 피로 분석 평가
**목적**: 피로 분석 워크플로우와 일관된 평가 기준 적용

#### 평가 기준 재정립
- ✅ **저주파 Rainflow**: 독립 평가
- ✅ **고주파 Rainflow**: 독립 평가
- ❌ ~~전체 신호 Rainflow~~: 피로 분석에서 미사용

#### 결과 (Baseline)
| 성분 | CCR | 목표 | 상태 |
|------|-----|------|------|
| 저주파 | ~0.95 | ≥0.95 | ⚠️ |
| 고주파 | ~0.78 | ≥0.95 | ❌ |

**핵심 발견**:
- ARMA: 24일 gap에서 실패 → 선형 보간 fallback
- Random Phase: Temporal structure 파괴 → CCR 저하
- Spectral Correlation: 0.39 (목표 > 0.95)

---

## 📊 최종 결론

### 연구 결과 요약

| 프로젝트 | 방법 | 결과 | 핵심 발견 |
|----------|------|------|-----------|
| 007 | XGBoost | ❌ R² -0.04 | 변동성 캡처 실패 |
| 008 | 방법론 분석 | - | 센서간 독립(0.039), ACF 0.145 |
| 009 | Prophet | ❌ R² -4.37 | XGBoost보다 109배 나쁨 |
| 010 | Gap 길이 실험 | ❌ 모두 실패 | 데이터 특성 한계 |
| 011 | 주파수 분리 | ❌ R² < 0 | Recursive 오류 누적 |
| 012 | LSTM | ❌ R² -0.238 | 2분 이상 예측 불가 |
| 013 | Spectral | ⚠️ RF 0.86 | PSD ≠ Rainflow |
| 014 | 성분별 평가 | ⚠️ CCR 0.78 | 고주파 temporal 손실 |

### 근본적 한계
1. **데이터 특성**: 센서간 독립(0.039), 약한 시간 패턴(ACF 0.145)
2. **예측 한계**: 본질적으로 2분 이상 예측 불가능
3. **Phase 정보**: PSD 보존만으로 Rainflow 특성 재현 불가

### 권장사항
1. **Gap 허용 정책 수립**: 긴 gap(≥ 24일)은 보간 포기
2. **단기 gap만 보간**: ≤ 1시간 gap은 XGBoost 사용 가능
3. **데이터 품질 메타데이터**: Gap 위치/길이 기록, 신뢰도 플래그
4. **분석 시 명시**: Gap 구간을 피로 분석에서 제외 또는 별도 표기

---

## 📁 프로젝트 파일 구조

```
tmp/
├── 007_xgboost_interpolation_test/
│   ├── TEST_PLAN_xgboost_interpolation.md
│   └── results/
├── 008_interpolation_methods_analysis/
│   ├── INTERPOLATION_METHODS_COMPARISON.md
│   ├── data_characteristics_analysis.py
│   └── results/DATA_ANALYSIS_REPORT.md
├── 009_prophet_poc/
│   ├── TEST_PLAN_prophet_interpolation.md
│   ├── prophet_phase1_single.py
│   └── results/phase1_report.md
├── 010_gap_length_experiment/
│   ├── TEST_PLAN_gap_length_experiment.md
│   └── gap_length_experiment.py
├── 011_frequency_separation_interpolation/
│   ├── TEST_PLAN_frequency_separation.md
│   ├── phase1_component_analysis.py
│   ├── phase2_adaptive_interpolation.py
│   ├── phase3_noise_verification.py
│   ├── phase4_xgboost_interpolation.py
│   └── results/
├── 012_transformer_lstm_poc/
│   ├── STEP1_DATA_SUITABILITY_PLAN.md
│   ├── STEP2_LSTM_QUICK_TEST_PLAN.md
│   ├── step1_data_suitability_analysis.py
│   ├── step2_simple_lstm_test.py
│   └── results/
├── 013_spectral_matching_gap_fill/
│   ├── spectral_gap_fill.py
│   ├── arma_synthesis.py
│   ├── random_phase_synthesis.py
│   ├── validation.py
│   ├── ANALYSIS.md
│   └── results/
└── 014_component_wise_gap_fill/
    ├── STEP1_PLAN.md
    ├── STEP2_PLAN.md
    ├── SPECTRUM_COMPARISON_PLAN.md
    ├── scripts/
    └── results/
```

---

## 🔗 관련 문서

### main40-41 관련
- [TODO_main40_analyze_pressure_gaps.md](TODO_main40_analyze_pressure_gaps.md) - 데이터 품질 분석 계획
- [MAIN41_PLAN.md](MAIN41_PLAN.md) - Gap filling 구현 계획

### 피로 분석 워크플로우
- [workflow_main51-58_fatigue.md](workflows/workflow_main51-58_fatigue.md) - 주파수 분석 ~ 위험도 분석
- [scripts/main51_find_freq.md](scripts/main51_find_freq.md) - 주파수 분석 (V-valley 기준)

### 입출력 참조
- [SCRIPT_IO_REFERENCE.md](SCRIPT_IO_REFERENCE.md) - 스크립트 입출력 통합 문서

---

**최종 업데이트**: 2025-12-12
**작성자**: Claude AI Assistant
