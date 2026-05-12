# Phase 4: 저주파/고주파 XGBoost 보간 실험 계획

**작성일**: 2025-12-10
**작성자**: Claude Code
**버전**: 1.0

---

## 📋 1. 배경 및 동기

### 1.1 Phase 3 핵심 발견

**고주파는 순수 잡음이 아님!**

```
통계 검정 결과 (6개):
✅ Ljung-Box Test: p < 0.0001 → 패턴 존재
✅ Runs Test: p < 0.0001 → 비랜덤
✅ 정규성 검정: p < 0.0001 → 비정규분포
✅ Sample Entropy: 0.86 < 1.5 → 낮은 무작위성
❌ PSD: CV 0.231 < 0.3 → 균일 (백색 잡음)
✅ ACF 유의성: 16% > 5% → 자기상관 존재

판정: 패턴 존재 가능성 (5/6 검정에서 패턴 신호)
```

### 1.2 Phase 2 실패 원인 재분석

**Phase 2 (Spline+Mean) 실패**:
```
저주파: Cubic Spline (2점 연결)
        → Gap 전후 8190개 점 무시
        → 트렌드 반영 못함

고주파: Mean (평균값)
        → std 0.0000 (완전 평탄)
        → 전체 변동의 99% 손실

결과: R² -0.03 ~ -0.62 (실패)
```

**문제점**:
1. 저주파 Spline: 2점만 사용 → 과거 패턴 무시
2. 고주파 Mean: 변동성 완전 제거 → 에너지 손실

### 1.3 XGBoost 시도 정당화

**근거**:

1. **저주파 ACF 0.9997**
   - 거의 완벽한 시간 의존성
   - past_60 features로 예측 가능성 높음
   - Spline(2점)보다 XGBoost(과거 패턴 학습)가 나을 수 있음

2. **고주파 ACF 16% 유의 lag**
   - 완전한 잡음은 아님 (5/6 검정에서 패턴)
   - 시간 자기상관 존재
   - Mean(std=0)보다 XGBoost가 나을 가능성

3. **기존 전체 XGBoost 실패 이유**:
   ```
   전체 데이터 ACF: 0.145 (낮음)
   전체 XGBoost: R² -0.15 (실패)

   문제: 저주파(ACF 0.9997) + 고주파(ACF 0.0746) 섞임
        → 전체 예측 불가능

   해결: 분리 후 각각 XGBoost
        → 저주파는 성공 가능
        → 고주파는 일부 개선 가능
   ```

### 1.4 Phase 4 목표

**최소 목표**:
- 3일 gap R² > 0 (기존 모든 방법 실패)

**희망 목표**:
- 3일 gap R² > 0.3 (실용적 수준)
- 고주파 std > 0 (Phase 2는 0이었음)

**과학적 목표**:
- 주파수 분리 + XGBoost 효과 검증
- 컴포넌트별 XGBoost 성능 분석

---

## 🧪 2. 실험 설계

### 2.1 전체 파이프라인

```
┌─────────────────────────────────────────────────────────┐
│ 1. 데이터 준비                                           │
│    - Gap 전 14.2일 (학습용)                             │
│    - Gap 후 14.2일 (검증용)                             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. 주파수 분리 (V-valley=553.5분)                       │
│    - Butterworth 4차 필터                               │
│    - Zero-phase (filtfilt)                              │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌──────────────────┐              ┌──────────────────┐
│ 3a. 저주파 XGBoost│              │ 3b. 고주파 XGBoost│
│  - ACF 0.9997    │              │  - ACF 16% 유의  │
│  - past_60       │              │  - past_60       │
│  - 학습 → 예측   │              │  - 학습 → 예측   │
└──────────────────┘              └──────────────────┘
        │                                   │
        └─────────────────┬─────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. 재조합                                                │
│    gap_filled = low_pred + high_pred                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 5. 평가                                                  │
│    - R², MAE, MAPE, RMSE                                │
│    - 에너지 보존율                                       │
│    - Phase 2/전체 XGBoost 대비 비교                     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 저주파 XGBoost 전략

**특성**:
- ACF: **0.9997** (거의 완벽한 시간 의존성)
- 표준편차: 0.0133 (작은 변동)
- 전체 변동 기여: 1%

**Feature Engineering**:
```python
def create_features_low_freq(low_component):
    """
    저주파 XGBoost features

    - past_60: 지난 5시간 (300분)
    - ACF 0.9997 → 과거 패턴 강력히 반영
    """
    features = []
    for i in range(60, len(low_component)):
        past_60 = low_component[i-60:i]  # 지난 60개
        features.append(past_60)

    return np.array(features)
```

**하이퍼파라미터** (010 프로젝트 재사용):
```python
low_xgb_params = {
    'n_estimators': 100,
    'max_depth': 6,
    'learning_rate': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'objective': 'reg:squarederror',
    'random_state': 42
}
```

**기대 성능**:
- 저주파 예측 R² > 0.8 (ACF 0.9997 기반)
- Spline(2점)보다 훨씬 우수 예상

### 2.3 고주파 XGBoost 전략

**특성**:
- ACF: 0.0746 (낮음, 하지만 16% 유의 lag 존재)
- 표준편차: 0.0754 (큰 변동)
- 전체 변동 기여: 99%

**Feature Engineering**:
```python
def create_features_high_freq(high_component):
    """
    고주파 XGBoost features

    - past_60: 지난 5시간
    - ACF 낮지만 16% 유의 lag → 일부 패턴
    """
    features = []
    for i in range(60, len(high_component)):
        past_60 = high_component[i-60:i]
        features.append(past_60)

    return np.array(features)
```

**하이퍼파라미터**:
```python
high_xgb_params = {
    'n_estimators': 100,
    'max_depth': 4,  # 저주파보다 얕게 (과적합 방지)
    'learning_rate': 0.05,  # 더 작게 (안정성)
    'subsample': 0.7,
    'colsample_bytree': 0.7,
    'objective': 'reg:squarederror',
    'random_state': 42
}
```

**기대 성능**:
- 고주파 예측 R² ≈ 0.1-0.2 (ACF 16% 유의 lag 기반)
- Mean(std=0)보다는 나을 것
- 하지만 완벽한 복원은 불가능

### 2.4 재조합 전략

```python
def recombine_components(low_pred, high_pred, original_data):
    """
    저주파/고주파 예측 재조합

    Args:
        low_pred: 저주파 XGBoost 예측값
        high_pred: 고주파 XGBoost 예측값
        original_data: Gap 전후 원본 (에너지 보존 검증용)

    Returns:
        combined: 재조합된 예측값
        conservation_rate: 에너지 보존율
    """
    # 단순 합
    combined = low_pred + high_pred

    # 에너지 보존 검증
    orig_var = np.var(original_data)
    low_var = np.var(low_pred)
    high_var = np.var(high_pred)

    conservation_rate = (low_var + high_var) / orig_var * 100

    return combined, conservation_rate
```

---

## 📊 3. 구현 계획

### 3.1 phase4_xgboost_interpolation.py 구조

```python
#!/usr/bin/env python3
"""
Phase 4: 저주파/고주파 XGBoost 보간

주요 기능:
1. 주파수 분리 (V-valley=553.5분)
2. 저주파 XGBoost 학습 및 예측
3. 고주파 XGBoost 학습 및 예측
4. 재조합 및 평가
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.signal import butter, filtfilt

# 주요 함수:
def pass_filter(data, sampling_rate, v_valley_minutes=553.5):
    """주파수 분리"""
    pass

def create_features(component, lookback=60):
    """past_60 features 생성"""
    pass

def train_xgboost_model(X_train, y_train, params):
    """XGBoost 모델 학습"""
    pass

def predict_gap(model, features):
    """Gap 구간 예측"""
    pass

def xgboost_freq_separation_interpolation(df, gap_start, gap_end, area):
    """
    메인 파이프라인

    Returns:
        {
            'gap_filled': 재조합 예측값,
            'low_component': 저주파 예측,
            'high_component': 고주파 예측,
            'metrics': 성능 지표,
            'conservation_rate': 에너지 보존율,
            'low_model_r2': 저주파 모델 R²,
            'high_model_r2': 고주파 모델 R²
        }
    """
    # 1. Gap 전 데이터 (학습용)
    before_gap = df[gap_start - timedelta(days=14.2):gap_start]

    # 2. 주파수 분리
    low_before, high_before = pass_filter(before_gap['wtrprsr'].values, ...)

    # 3. Features 생성
    X_low, y_low = create_features(low_before, lookback=60)
    X_high, y_high = create_features(high_before, lookback=60)

    # 4. 모델 학습
    low_model = train_xgboost_model(X_low, y_low, low_xgb_params)
    high_model = train_xgboost_model(X_high, y_high, high_xgb_params)

    # 5. Gap 예측
    low_pred = predict_gap(low_model, gap_features_low)
    high_pred = predict_gap(high_model, gap_features_high)

    # 6. 재조합
    gap_filled = low_pred + high_pred

    # 7. 평가
    metrics = evaluate(gap_filled, gap_true)

    return results
```

### 3.2 코드 재사용

**009 프로젝트에서**:
```python
# data_loader, evaluation, visualization
import sys
from pathlib import Path
utils_dir = Path(__file__).parent.parent / "009_prophet_poc" / "utils"
sys.path.insert(0, str(utils_dir))

import data_loader
import evaluation
import visualization
```

**010 프로젝트에서**:
```python
# XGBoost feature engineering 참고
# tmp/010_gap_interpolation/xgboost_interpolation.py
```

**phase2에서**:
```python
# pass_filter 함수 재사용
from phase2_adaptive_interpolation import pass_filter
```

---

## 🎯 4. 테스트 시나리오

### 4.1 테스트 Gap

| Gap | 시작 | 종료 | 레코드 수 | 기대 성능 |
|-----|------|------|----------|-----------|
| 3일  | 2025-05-19 13:40 | 2025-05-22 13:40 | 865 | R² > 0 |
| 7일  | 2025-05-19 13:40 | 2025-05-26 13:40 | 2,016 | R² ≈ 0 |
| 14일 | 2025-05-19 13:40 | 2025-06-02 13:40 | 4,033 | R² < 0 |
| 24일 | 2025-05-19 13:40 | 2025-06-12 14:40 | 6,925 | R² < 0 |

### 4.2 비교 기준

**Phase 2 (Spline+Mean)**:
```
3일:  R² -0.0279, MAE 0.0506
7일:  R² -0.0054, MAE 0.0555
14일: R² -0.0317, MAE 0.0648
24일: R² -0.6239, MAE 0.1255
```

**전체 XGBoost (010)**:
```
3일:  R² -0.15
7일:  R² -0.09
14일: R² -0.05
24일: R² -0.04
```

**Phase 4 목표**:
```
3일:  R² > 0 (최소), R² > 0.3 (희망)
7일:  R² ≥ 0
14일: R² > -0.05 (XGBoost 이상)
24일: R² > -0.10 (Phase 2보다 나음)
```

### 4.3 성공 기준

| 레벨 | 조건 | 의미 |
|------|------|------|
| **완전 성공** | 3일 R² > 0.3 | 실용적 사용 가능 |
| **부분 성공** | 3일 R² > 0 | 개선 효과 확인 |
| **미미한 개선** | 3일 R² > -0.05 | Phase 2보다 나음 |
| **실패** | 3일 R² < -0.05 | 개선 없음 |

**추가 기준**:
- 고주파 std > 0 (Phase 2는 0)
- 에너지 보존 > 30% (Phase 2는 0.3%)
- 저주파 모델 R² > 0.8 (ACF 0.9997 기반)

---

## 📈 5. 예상 결과 및 대응

### 5.1 시나리오 A: 부분 성공 (가능성 60%)

**예상**:
```
3일 gap:
  - 저주파 XGBoost R²: 0.85 (ACF 0.9997)
  - 고주파 XGBoost R²: 0.15 (ACF 16% 유의)
  - 재조합 R²: 0.1-0.3
  - MAE: 0.04-0.05

7일 gap:
  - 재조합 R²: 0.0-0.2

14일 gap:
  - 재조합 R²: -0.05-0.1
```

**대응**:
- ✅ Phase 2 대비 개선 확인
- ✅ 주파수 분리 + XGBoost 효과 입증
- ✅ 단기 gap(3일) 실용 가능성
- 📄 성공 보고서 작성
- 🔄 main41 적용 검토

### 5.2 시나리오 B: 미미한 개선 (가능성 30%)

**예상**:
```
3일 gap:
  - 재조합 R²: -0.01-0.05
  - MAE: 0.05-0.06

저주파: XGBoost 성공 (R² > 0.8)
고주파: XGBoost 실패 (R² < 0.1)
```

**대응**:
- ⚠️ 통계적 개선은 있으나 실용성 낮음
- 📊 컴포넌트별 분석 (저주파 vs 고주파)
- 📝 "고주파 99% 문제" 재확인
- 🔚 Gap 허용 권장

### 5.3 시나리오 C: 실패 (가능성 10%)

**예상**:
```
3일 gap:
  - 재조합 R²: < -0.05
  - Phase 2와 비슷하거나 더 나쁨

원인: 고주파 XGBoost도 과적합/평균 회귀
```

**대응**:
- ❌ 최종 결론: "모든 합리적 방법 실패"
- 📄 FINAL_COMPARISON_REPORT 업데이트
- 🚫 보간 포기, Gap 허용 정책
- 🔧 센서 이중화 권고

### 5.4 시나리오별 문서화

**성공 시**:
- PHASE4_XGBOOST_RESULTS.md (성공 분석)
- 방법론 논문/보고서
- main41 구현 가이드

**실패 시**:
- PHASE4_XGBOOST_RESULTS.md (실패 분석)
- FINAL_COMPARISON_REPORT 보완
- "보간 불가능" 최종 결론

---

## ⚙️ 6. 실행 계획

### 6.1 구현 단계

| 단계 | 작업 | 예상 시간 | 누적 |
|------|------|-----------|------|
| 1 | PHASE4_XGBOOST_PLAN.md 작성 | 30분 | 30분 |
| 2 | phase4_xgboost_interpolation.py 구현 | 1.5시간 | 2시간 |
| 3 | 3일 gap 테스트 실행 | 5분 | 2시간 5분 |
| 4 | 3일 결과 검토 및 계속 여부 판단 | 10분 | 2시간 15분 |
| 5 | 7/14/24일 gap 테스트 | 15분 | 2시간 30분 |
| 6 | PHASE4_XGBOOST_RESULTS.md 작성 | 40분 | 3시간 10분 |
| 7 | FINAL_COMPARISON_REPORT 업데이트 | 20분 | 3시간 30분 |
| 8 | README.md, TEST_PLAN 업데이트 | 10분 | 3시간 40분 |
| 9 | 커밋 | 10분 | 3시간 50분 |

**총 예상 시간**: 약 4시간

### 6.2 실행 명령어

```bash
# Phase 4 실행 (3일 gap)
python tmp/011_frequency_separation_interpolation/phase4_xgboost_interpolation.py \
    --area 0243 \
    --gap-days 3 \
    --output results/interpolation_xgboost/

# 결과 확인
cat results/interpolation_xgboost/gap_3days/results.json

# 전체 gap 테스트 (성공 시)
for gap in 3 7 14 24; do
    python tmp/011_frequency_separation_interpolation/phase4_xgboost_interpolation.py \
        --area 0243 \
        --gap-days $gap \
        --output results/interpolation_xgboost/
done
```

### 6.3 중단 기준

**3일 gap 실패 시**:
- R² < -0.05 (Phase 2와 비슷)
- MAE > 0.06 (Phase 2와 비슷)
→ 7/14/24일 실행 중단, 실패 보고서 작성

**3일 gap 성공 시**:
- R² > 0
→ 전체 gap 테스트 계속 진행

---

## 📁 7. 산출물

### 7.1 코드

```
tmp/011_frequency_separation_interpolation/
├── phase4_xgboost_interpolation.py (신규)
└── results/
    └── interpolation_xgboost/
        ├── gap_3days/
        │   ├── results.json
        │   ├── forecast_comparison.png
        │   ├── component_breakdown.png
        │   └── model_performance.json
        ├── gap_7days/
        ├── gap_14days/
        └── gap_24days/
```

### 7.2 문서

- **PHASE4_XGBOOST_RESULTS.md**: Phase 4 상세 결과 분석
  - 저주파 모델 성능
  - 고주파 모델 성능
  - 재조합 결과
  - Phase 2/전체 XGBoost 대비 비교

- **FINAL_COMPARISON_REPORT.md 업데이트**:
  - Phase 4 결과 추가
  - 전체 방법 최종 비교
  - 최종 권장사항

- **README.md 업데이트**:
  - Phase 4 완료 상태 반영
  - 실행 명령어 추가

---

## 🔬 8. 기대 효과 및 한계

### 8.1 기대 효과

**저주파 XGBoost**:
- ACF 0.9997 → 거의 완벽한 예측
- 2점 Spline보다 훨씬 우수
- 과거 패턴 충분히 활용

**고주파 XGBoost**:
- ACF 16% 유의 lag → 일부 패턴 학습
- Mean(std=0)보다 개선
- 변동성 일부 복원

**재조합**:
- 저주파(1%) + 고주파(99%)
- 고주파 개선만으로도 전체 개선 가능
- R² > 0 달성 가능성

### 8.2 한계 인식

**고주파 99% 문제**:
- 고주파가 전체 변동의 99% 차지
- 고주파 XGBoost R² < 0.2 예상
- 완벽한 복원은 불가능

**Gap 길이**:
- 3일: 개선 가능성 높음
- 14일 이상: 여전히 어려움

**근본적 한계**:
- 고주파 ACF 0.0746 (낮음)
- 예측 불가능한 성분 지배적
- 일부 개선은 가능하나 완벽한 해결은 불가

---

## 📊 9. 검증 체크리스트

### Phase 4 실행 전

- [ ] phase4_xgboost_interpolation.py 구현 완료
- [ ] 010 프로젝트 XGBoost 코드 참조
- [ ] pass_filter 함수 재사용 확인
- [ ] 하이퍼파라미터 설정 확인

### Phase 4 실행 중

- [ ] 저주파 모델 학습 성공 (R² > 0.8)
- [ ] 고주파 모델 학습 완료
- [ ] 재조합 에너지 보존 > 30%
- [ ] 3일 gap 결과 확인 후 계속 여부 판단

### Phase 4 실행 후

- [ ] 전체 gap 테스트 완료
- [ ] Phase 2/전체 XGBoost 대비 비교
- [ ] 시각화 생성 (forecast_comparison, component_breakdown)
- [ ] PHASE4_XGBOOST_RESULTS.md 작성
- [ ] FINAL_COMPARISON_REPORT 업데이트
- [ ] README.md, TEST_PLAN 업데이트
- [ ] 커밋 및 정리

---

## 🎯 10. 최종 목표

### 과학적 목표

1. **주파수 분리 + XGBoost 효과 검증**
   - 컴포넌트별 맞춤 모델의 우월성
   - Phase 2 (Spline+Mean) 대비 개선

2. **저주파/고주파 XGBoost 성능 분석**
   - ACF vs XGBoost R² 관계
   - 컴포넌트별 예측 가능성 한계

3. **전체 실험 종합**
   - Linear, XGBoost, Prophet, Freq Sep (Phase 2), Freq XGBoost (Phase 4)
   - 5가지 방법 완전 비교
   - 최종 결론 도출

### 실용적 목표

**성공 시**:
- 단기 gap(3일) 보간 가능
- main41 구현 옵션 추가
- 센서 유지보수 정책 개선

**실패 시**:
- "모든 합리적 방법 실패" 확정
- Gap 허용 정책 수립
- 센서 이중화 권고

---

**작성 완료**: 2025-12-10
**다음 단계**: phase4_xgboost_interpolation.py 구현

