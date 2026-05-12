# Project 014: Component-Wise Gap Filling for Fatigue Analysis

## 📌 프로젝트 목적

**핵심**: 피로 분석(main51-55)과 일관된 성분별 Gap filling 구현

### 올바른 평가 기준
- ✅ **저주파 Rainflow Count 일치도** (독립적으로 평가)
- ✅ **고주파 Rainflow Count 일치도** (독립적으로 평가)
- ❌ ~~전체 신호 Rainflow Count~~ (피로 분석에서 사용하지 않음)

### 피로 분석 워크플로우와의 일관성
```
실제 신호 → Butterworth 필터 → 저주파/고주파 분리
                ↓                      ↓
         저주파 Rainflow         고주파 Rainflow
                ↓                      ↓
         저주파 피로 손상        고주파 피로 손상
                     ↓
                총 피로 손상
```

## 🎯 목표

### 평가 지표 정의

#### 1. Rainflow Cycle Count Ratio (CCR)
```python
CCR = min(cycles_pred/cycles_true, cycles_true/cycles_pred)
```
- 범위: [0, 1], 1이 완벽한 일치
- 목표: CCR ≥ 0.95

#### 2. Amplitude Distribution Similarity (ADS)
```python
ADS = 1 - wasserstein_distance(amp_dist_true, amp_dist_pred)
```
- 진폭 분포의 Wasserstein 거리 기반
- 목표: ADS ≥ 0.90

#### 3. Fatigue Damage Ratio (FDR)
```python
FDR = damage_pred / damage_true
```
- Palmgren-Miner 규칙으로 계산된 피로 손상
- 목표: FDR ∈ [0.95, 1.05]

### 종합 성공 기준
각 성분(저주파/고주파)별로 **모든** 지표 달성:
1. **Cycle Count**: CCR ≥ 0.95
2. **진폭 분포**: ADS ≥ 0.90
3. **피로 손상**: FDR ∈ [0.95, 1.05]

## 🔍 Project 013에서 배운 교훈

### 1. 평가 기준 오류
- **문제**: 전체 신호로 평가 (Rainflow 0.700 ~ 0.861)
- **원인**: 피로 분석이 성분별로 진행된다는 점 간과
- **해결**: 성분별 독립 평가로 변경

### 2. 고주파 성분의 도전 과제
- **저주파 성공**: ARMA로 Rainflow 0.99+ 달성
- **고주파 실패**: Random Phase로 Rainflow 2배 차이
- **원인**: 고주파 자체의 시계열 패턴 재현 실패

### 3. Interaction Effect는 무관함
- **Project 013의 오해**: 전체 신호 평가에서만 나타나는 현상
- **성분별 독립 평가의 장점**: 저주파-고주파 상호작용 무시 가능
- **결론**: 각 성분을 독립적으로 최적화하면 충분

## 📋 개선 계획

### Phase 1: 평가 시스템 재구성
```python
# 올바른 평가 방식
def evaluate_component_wise(true_signal, pred_signal):
    # 1. 신호 분리 (main51과 동일한 필터)
    low_true, high_true = butterworth_filter(true_signal)
    low_pred, high_pred = butterworth_filter(pred_signal)

    # 2. 성분별 평가 (독립적으로)
    results = {}
    for name, true, pred in [('low', low_true, low_pred),
                              ('high', high_true, high_pred)]:
        # Rainflow 계산
        cycles_true, amps_true = rainflow_count(true)
        cycles_pred, amps_pred = rainflow_count(pred)

        # 평가 지표
        ccr = min(cycles_pred/cycles_true, cycles_true/cycles_pred)
        ads = 1 - wasserstein_distance(amps_true, amps_pred)
        fdr = calculate_damage(pred) / calculate_damage(true)

        results[name] = {
            'CCR': ccr,        # 목표: ≥ 0.95
            'ADS': ads,        # 목표: ≥ 0.90
            'FDR': fdr,        # 목표: 0.95-1.05
            'pass': ccr >= 0.95 and ads >= 0.90 and 0.95 <= fdr <= 1.05
        }

    return results
```

### Phase 2: 고주파 성분 개선 방법론

#### Option A: Direct Time-Domain Modeling
- LSTM/Transformer로 고주파 직접 예측
- 시계열 패턴 학습
- End-to-end 학습

#### Option B: Improved Spectral Matching
- PSD 매칭 + 시간 도메인 제약
- Reference 데이터에서 통계적 특성 추출
- Rainflow 특성 보존

#### Option C: Wavelet-based Approach
- Wavelet 변환으로 다중 스케일 분해
- 각 스케일별 독립 모델링
- 시간-주파수 특성 보존

#### Option D: Hybrid Statistical Model
- 고주파의 통계적 특성 모델링
- GARCH 또는 SV 모델 적용
- 변동성 패턴 재현

### Phase 3: 단계별 구현 계획

#### STEP 1: Baseline 측정 및 평가 시스템 구축
- **작업 내용**:
  - 성분별 평가 시스템 구현 (CCR, ADS, FDR 계산)
  - 저주파: 기존 ARMA 모델 재사용 (Project 013에서 이미 성공)
  - 고주파: Random Phase IFFT로 Baseline 설정
- **목표**: 현재 상태 정확히 파악
- **완료 조건**: 평가 시스템 작동 확인

#### STEP 2: 고주파 개선 - 1차 시도
- **방법**: Option D (Hybrid Statistical Model - GARCH/SV)
- **선택 이유**: 구현 간단, 빠른 검증 가능
- **진행 조건**: STEP 1에서 고주파 CCR < 0.95
- **성공 기준**: 고주파 모든 지표 달성 (CCR ≥ 0.95, ADS ≥ 0.90, FDR ∈ [0.95, 1.05])

#### STEP 3: 고주파 개선 - 2차 시도
- **방법**: Option B (Improved Spectral Matching)
- **선택 이유**: Rainflow 특성을 직접 목표 함수에 포함
- **진행 조건**: STEP 2에서 성공 기준 미달성
- **성공 기준**: 고주파 모든 지표 달성

#### STEP 4: 고주파 개선 - 최종 시도
- **방법**: Option A (Direct Time-Domain Modeling - LSTM/Transformer)
- **선택 이유**: 근본적으로 다른 접근법
- **진행 조건**: STEP 3에서 성공 기준 미달성
- **주의사항**: 대량 데이터 필요, 긴 학습 시간

## 📁 프로젝트 구조

```
014_component_wise_gap_fill/
├── README.md                    # 이 문서
├── EVALUATION_CRITERIA.md       # 상세 평가 기준
├── scripts/
│   ├── evaluate_component.py    # 성분별 평가 시스템
│   ├── baseline_test.py        # ARMA + Random Phase 기준선
│   ├── direct_modeling.py      # Option A 구현
│   ├── spectral_improved.py    # Option B 구현
│   ├── hybrid_statistical.py   # Option D 구현
│   └── compare_methods.py      # 방법론 비교
├── results/
│   ├── baseline/               # 기준선 결과
│   ├── direct_modeling/        # Option A 결과
│   ├── spectral_improved/      # Option B 결과
│   ├── hybrid_statistical/     # Option D 결과
│   └── comparison/             # 비교 분석
└── docs/
    ├── theory.md              # 이론적 배경
    └── implementation.md      # 구현 세부사항
```

## 📈 진행 현황 (2025-12-12)

### ✅ 완료된 작업

#### STEP 1: Baseline 측정 ✓
- [계획 문서](STEP1_PLAN.md)
- [결과 보고서](results/baseline/baseline_report.md)
- **결과**: 모든 성분 실패 (고주파 CCR ~0.78)

#### STEP 2: IAAFT 테스트 ✓
- [계획 문서](STEP2_PLAN.md)
- [결과 보고서](results/step2/step2_report.md)
- **결과**: 개선 미미 (CCR +0.2%), 목표 미달성

#### 스펙트럼 분석: 24일 Gap 심층 분석 ✓
- [계획 문서](SPECTRUM_COMPARISON_PLAN.md)
- [분석 보고서](results/spectrum_comparison/spectrum_analysis_report_24days.md)
- [스펙트럼 비교 그래프](results/spectrum_comparison/spectrum_comparison_24days.png)
- **핵심 발견사항**:
  - Spectral Correlation: 0.39 (목표 > 0.95) ❌
  - 저주파 에너지: 391% (ARMA 실패) ❌
  - 고주파 에너지: 100.6% (양호) ✅
  - **결론**: Random Phase + ARMA 방법의 근본적 한계 확인

### 📊 주요 결과 요약

| 방법 | 고주파 CCR (7일) | 고주파 CCR (14일) | 고주파 CCR (24일) | 상태 |
|------|-----------------|-------------------|-------------------|------|
| Baseline (Random Phase) | 0.793 | 0.786 | 0.781 | ❌ |
| IAAFT | 0.795 | 0.793 | 0.781 | ❌ |
| **목표** | **≥0.95** | **≥0.95** | **≥0.95** | - |

### 🔍 핵심 발견사항

1. **저주파 문제**: ARMA fitting 실패로 선형 보간 사용 → FDR 매우 높음 (14~36)
   - 24일 gap 스펙트럼 분석: 저주파 에너지 391% (원본 대비 ~4배)
   - ARMA가 장기 gap 예측 불가, 선형 보간 fallback

2. **고주파 문제**:
   - Variance 매우 작음 (0.009 vs 저주파 0.18)
   - 이미 가우시안 노이즈에 가까운 특성
   - 스펙트럼 기반 방법으로 개선 어려움
   - Random Phase가 temporal structure 완전 파괴 → CCR 저하

3. **스펙트럼 분석 결과** (24일 gap):
   - Spectral Correlation: 0.39 (심각한 불일치)
   - Phase randomization이 peak-valley sequence 파괴
   - 스펙트럼 magnitude 보존만으로는 Rainflow 특성 재현 불가

### ⚠️ 현재 상태
**스펙트럼 기반 접근법의 한계 확인**
- Random Phase, IAAFT 모두 실패
- CCR 목표 (0.95) 달성 불가능
- 근본적으로 다른 접근법 필요

## 🚀 다음 단계

### 남은 옵션
1. ~~성분별 평가 시스템 구현~~ ✓
2. ~~Project 013 데이터로 기준선 설정~~ ✓
3. ~~고주파 개선 방법 선택 및 구현 (IAAFT)~~ ✓ 실패
4. [ ] STEP 3: GARCH/SV (시간 도메인 모델링)
5. [ ] STEP 4: LSTM/Transformer (딥러닝)

## 📊 성공 기준

### 필수 달성 목표 (각 성분별)
| 지표 | 저주파 | 고주파 | 설명 |
|------|--------|---------|------|
| CCR | ≥ 0.95 | ≥ 0.95 | 사이클 수 비율 |
| ADS | ≥ 0.90 | ≥ 0.90 | 진폭 분포 유사도 |
| FDR | 0.95-1.05 | 0.95-1.05 | 피로 손상 비율 |

### 추가 목표
- 계산 효율성 확보
- 메모리 사용량 최적화
- 모든 Gap 길이에서 일관된 성능

## 📝 참고 문헌

1. **피로 분석**
   - Rainflow Counting Algorithm (ASTM E1049)
   - Miner's Rule for Fatigue Damage

2. **시계열 모델링**
   - ARMA/ARIMA Models
   - GARCH/Stochastic Volatility
   - Deep Learning for Time Series

3. **관련 프로젝트**
   - Project 013: Spectral Matching 시도와 한계
   - main51-55: 피로 분석 파이프라인
   - main41-42: 주파수 분리 기준 (V-valley)

## ⚠️ 주의사항

1. **평가는 반드시 성분별로**: 전체 신호 평가는 의미 없음
2. **main51과 동일한 필터 사용**: 일관성 유지 필수
3. **성분 간 독립성**: 저주파와 고주파는 독립적으로 최적화
4. **계산 효율성**: 실시간 처리 가능해야 함

## 💡 교훈 및 시사점

### 압력 데이터 고주파 특성
- **매우 낮은 분산**: 전체 신호의 ~5%만 차지
- **노이즈에 가까운 특성**: 이미 랜덤에 가까워 개선 어려움
- **Rainflow 민감성**: 작은 변화도 cycle count에 큰 영향

### 스펙트럼 분석에서 확인된 문제점
- **Phase의 중요성**: Magnitude spectrum 보존만으로는 불충분
- **ARMA의 한계**: 24일 같은 장기 gap에서 완전 실패 (저주파 에너지 4배)
- **Spectral Correlation 0.39**: 원본과 합성 데이터의 스펙트럼 형태가 근본적으로 다름
- **Temporal structure**: Phase randomization이 시간적 패턴 완전 파괴

### 평가 기준의 엄격함
- CCR 0.95는 매우 높은 기준
- 실제 피로 분석에서 이 정도 정확도 필요한지 재검토 필요
- FDR이 더 중요할 수 있음 (피로 손상 관점)
- **Gap 길이별 차별화된 목표 설정 필요**

### 접근법 재고
- 스펙트럼 기반: 한계 확인됨 (특히 24일 gap)
- 시계열 직접 모델링 고려 필요 (GARCH/SV, LSTM)
- 또는 목표 수정 검토 (gap 길이에 따른 적응적 목표)

---

**프로젝트 시작일**: 2025-12-11
**최종 업데이트**: 2025-12-12
**담당자**: Claude AI Assistant
**현재 상태**: STEP 2 완료, 추가 접근법 검토 중
**관련 이슈**: #TBD