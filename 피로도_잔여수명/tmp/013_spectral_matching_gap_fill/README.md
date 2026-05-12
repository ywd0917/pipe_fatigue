# 013: 주파수 스펙트럼 보존 기반 Gap Filling

**작성일**: 2025-12-11
**목적**: 정확한 값 예측 대신 동일한 주파수 스펙트럼을 가진 합성 데이터로 Gap 채우기
**예상 시간**: 15시간 (2일)

---

## 🎯 배경

프로젝트 011/012 결과:
- **Phase 4 (XGBoost)**: Gap R² < 0, 에너지 보존 0.32%
- **Step 2 (LSTM)**: 10-step R² -0.238 (비재귀 예측도 실패)
- **근본 원인**: 데이터가 본질적으로 2분 이상 예측 불가능

**새로운 접근**:
- ❌ 정확한 값 예측 (불가능)
- ✅ **동일한 주파수 스펙트럼만 가진 합성 데이터** 생성
- ✅ Fatigue 계산 목적 달성 (Rainflow counting 보존)

---

## 💡 핵심 아이디어

### Hybrid Spectral Synthesis

```
입력: Gap 전후 데이터
  ↓
주파수 분리 (V-valley 553.5분)
  ↓                    ↓
저주파 (ACF 0.9997)    고주파 (ACF 0.0746)
ARMA Synthesis         Random Phase IFFT
  ↓                    ↓
Edge Smoothing         Edge Smoothing
  ↓                    ↓
      재조합: low + high
              ↓
         검증 (Rainflow)
```

### 왜 이 방법인가?

| 기존 방법 (Phase 4) | 새 방법 (Spectral Matching) |
|---------------------|----------------------------|
| ❌ 정확한 값 예측 시도 | ✅ 통계적 특성만 보존 |
| ❌ Recursive prediction | ✅ 비재귀 (양방향 + Random) |
| ❌ 고주파 평균값 (std=0) | ✅ 고주파 PSD 보존 (std 유지) |
| ❌ 에너지 보존 0.32% | ✅ 에너지 보존 ~100% |
| ❌ R² 검증 (부적합) | ✅ Rainflow 검증 (적합) |

---

## 📋 구현 단계

### ✅ Phase 4 분석 재사용

| Phase 4 발견 | 013에서 활용 |
|--------------|--------------|
| V-valley 553.5분 | ✅ 동일한 cutoff 사용 |
| 저주파 ACF 0.9997 | ✅ ARMA 모델로 활용 |
| 저주파 Validation R² 0.9984 | ✅ One-step-ahead 가능 |
| 고주파 예측 불가 (R² 0.0216) | ✅ 예측 포기 → PSD 매칭 |
| 고주파 = 변동성 99% | ✅ PSD 보존으로 에너지 유지 |

### Step 1: ARMA 저주파 합성

**구현**: `arma_synthesis.py`

```python
def arma_spectral_synthesis(before, after, gap_length):
    """
    ARMA 모델로 gap 전후를 부드럽게 연결

    - Forward ARMA: before → gap
    - Backward ARMA: after → gap (역방향)
    - Weighted blending
    """
```

**핵심**: 저주파는 ACF 0.9997로 예측 가능 → ARMA로 smooth trajectory

### Step 2: Random Phase 고주파 합성

**구현**: `random_phase_synthesis.py`

```python
def random_phase_synthesis(reference, gap_length):
    """
    동일한 PSD를 가지는 랜덤 신호 생성

    1. Reference PSD 계산
    2. Random Phase 생성
    3. Magnitude 보존 + Random Phase
    4. IFFT로 시간 영역 신호 생성
    """
```

**핵심**: 고주파는 예측 불가능 → PSD만 보존 (위상 랜덤화)

### Step 3: Edge Smoothing

**구현**: `edge_smoothing.py`

```python
def edge_smoothing(gap, before, after, window=60):
    """
    Gap 경계 부드럽게 연결 (불연속 제거)

    Kaiser-Bessel window 사용
    """
```

### Step 4: 통합 파이프라인

**구현**: `spectral_gap_fill.py`

```python
def spectral_matching_gap_fill(data, gap_start, gap_end, v_valley=553.5):
    # 1. 주파수 분리
    low_freq, high_freq = frequency_separation(data, v_valley)

    # 2. 저주파 ARMA 합성
    low_gap = arma_spectral_synthesis(...)

    # 3. 고주파 Random Phase 합성
    high_gap = random_phase_synthesis(...)

    # 4. Edge Smoothing
    low_gap = edge_smoothing(low_gap, window=60)
    high_gap = edge_smoothing(high_gap, window=20)

    # 5. 재조합
    return low_gap + high_gap
```

### Step 5: 검증

**구현**: `validation.py`

```python
def validate_spectral_matching(original, gap_filled, gap_start, gap_end):
    """
    검증 메트릭:
    1. PSD Similarity > 95%
    2. Variance Ratio 0.9-1.1
    3. ACF Correlation > 0.9
    4. ⭐ Rainflow Match > 0.95 (최종 목표)
    """
```

---

## ✅ 성공 기준

| 메트릭 | 최소 | 목표 | 의미 |
|--------|------|------|------|
| **Rainflow Match** | **> 0.9** | **> 0.95** | **Fatigue 목적 달성** ⭐ |
| PSD Similarity | > 90% | > 95% | 주파수 특성 보존 |
| Variance Ratio | 0.8-1.2 | 0.9-1.1 | 에너지 보존 |
| ACF Correlation | > 0.8 | > 0.9 | 시간 구조 보존 |

**최종 판정**:
- Rainflow > 0.95 → ✅ **완전 성공** (Fatigue 계산 사용 가능)
- Rainflow > 0.90 → △ **부분 성공** (통계 분석 사용 가능)
- Rainflow < 0.90 → ❌ **실패** (Gap 허용 정책 수립)

---

## 🔬 테스트 계획

### Gap 테스트 (Phase 4와 동일)

| Gap | 일수 | Points | 테스트 목적 |
|-----|------|--------|-------------|
| 1 | 3일 | 865 | 짧은 gap (ARMA 유리) |
| 2 | 7일 | 2,016 | 중간 gap |
| 3 | 14일 | 4,033 | 긴 gap (Random Phase 중요) |
| 4 | 24일 | 6,925 | 매우 긴 gap (한계 테스트) |

### 검증 절차

```python
for gap in test_gaps:
    # 1. Spectral matching gap fill
    filled = spectral_matching_gap_fill(data, gap_start, gap_end)

    # 2. PSD 검증
    psd_sim = validate_psd_similarity(original, filled)

    # 3. Rainflow 검증 ⭐
    rf_match = validate_rainflow_matching(original, filled)

    # 4. 시각화
    plot_spectral_comparison(original, filled)
```

---

## 📊 기대 결과

### Phase 4와 비교

| 메트릭 | Phase 4 | 목표 (013) |
|--------|---------|------------|
| Gap R² | < 0 | N/A (검증 안 함) |
| 에너지 보존 | 0.32% | ~100% |
| 저주파 보존 | ✅ | ✅ |
| 고주파 보존 | ❌ (std=0) | ✅ (PSD 매칭) |
| Rainflow | N/A | > 0.95 ⭐ |

### 적용 가능 분석

| 분석 목적 | 적용 가능? |
|-----------|-----------|
| ✅ Rainflow counting | 완전히 가능 |
| ✅ Fatigue 누적 | 완전히 가능 |
| ✅ 통계 분석 | 완전히 가능 |
| ✅ 장기 트렌드 | 가능 |
| ❌ 특정 시점 압력 | 불가능 |
| ❌ 실시간 모니터링 | 불가능 |

---

## 📁 파일 구조

```
013_spectral_matching_gap_fill/
├── README.md                      (이 파일)
├── spectral_gap_fill.py           (메인 파이프라인)
├── arma_synthesis.py              (저주파 ARMA 합성)
├── random_phase_synthesis.py      (고주파 Random Phase)
├── edge_smoothing.py              (경계 처리)
├── validation.py                  (PSD/Rainflow 검증)
├── test_all_gaps.py               (4개 gap 테스트)
└── results/
    ├── gap_3days/
    │   ├── spectral_comparison.png
    │   ├── rainflow_comparison.png
    │   └── metrics.json
    ├── gap_7days/
    ├── gap_14days/
    ├── gap_24days/
    └── FINAL_REPORT.md
```

---

## 📊 실험 결과

**상태**: ✅ 완료 (2025-12-11)

### 최종 결과 요약

| Gap | Rainflow Match | PSD Sim | ACF Corr | 판정 |
|-----|----------------|---------|----------|------|
| 3일 | 0.700 | 0.953 | 0.962 | ❌ FAIL |
| 7일 | 0.718 | 0.919 | 0.946 | ❌ FAIL |
| 14일 | 0.848 | 0.948 | 0.963 | ⚠️ MARGINAL |
| 24일 | 0.861 | 0.937 | 0.955 | ⚠️ MARGINAL |

**최종 판정**: ❌ **실패** - Rainflow match < 0.90 (목표: > 0.95)

### 상세 문서

- 📄 **[FINAL_REPORT.md](results/FINAL_REPORT.md)** - 4개 gap 테스트 종합 결과
- 📄 **[ANALYSIS.md](ANALYSIS.md)** - 종합 분석 및 결론
- 📊 **[gap_test_comparison.csv](results/gap_test_comparison.csv)** - 메트릭 비교표
- 📈 **[all_gaps_summary.png](results/all_gaps_summary.png)** - 전체 요약 그래프
- 🔬 **[COMPONENT_ANALYSIS_RESULTS.md](results/COMPONENT_ANALYSIS_RESULTS.md)** - 주파수 성분별 분석 (원인 규명)

### 각 Gap별 상세 결과

- **3일 Gap**: [results/gap_3days/](results/gap_3days/)
- **7일 Gap**: [results/gap_7days/](results/gap_7days/)
- **14일 Gap**: [results/gap_14days/](results/gap_14days/)
- **24일 Gap**: [results/gap_24days/](results/gap_24days/)

### 핵심 발견

1. **Random phase synthesis의 한계** ([상세 분석 보고서](results/COMPONENT_ANALYSIS_RESULTS.md))
   - PSD 보존 성공 (0.92 ~ 0.95) ✅
   - Rainflow cycle 구조 보존 실패 ❌
   - Cycle 수 과다 생성 (True의 약 2배)
   - Amplitude 과대평가 (30-50%)

2. **주파수 성분별 원인 규명** 🔬 ([상세 분석](results/COMPONENT_ANALYSIS_RESULTS.md))
   - **재조합(Interaction)이 압도적 주범**:
     - 초과 cycle의 **58.6%**가 재조합 과정에서 발생 ⚠️
     - 고주파 성분: 41.0% 기여
     - 저주파 성분: 0.3% 기여 (거의 무시 가능)
   - **핵심 발견**:
     - 고주파 성분 자체는 전체 cycle의 99% 차지 (저주파의 162-220배)
     - 하지만 **개별 성분보다 재조합 과정이 더 큰 문제**
     - Low + High → Total 합성 시 spurious peak 대량 생성
   - **결론**:
     - ARMA 저주파 합성 ✅ 정상 작동
     - Random Phase 고주파 합성 ⚠️ 일부 문제 (41%)
     - **저주파 + 고주파 재조합 ❌ 주요 문제 (59%)**

3. **근본적 한계 확인**
   ```
   PSD 보존 ⊄ Rainflow 보존

   PSD = 주파수별 에너지 (위상 무시)
   Rainflow = Peak-valley 패턴 (위상 필수)
   → Phase 보존 필요 → 예측 필요 → 불가능
   ```

4. **권장사항**
   - Gap 허용 정책 수립 (≥ 2분 gap은 보간 포기)
   - 데이터 품질 메타데이터 추가
   - 장기적 센서 인프라 개선

### 추가 개선 시도

**Tiling 문제 해결** ([상세 결과](results/TILING_FIX_RESULTS.md))

- **배경**: Reference(1,200점) < Gap(4,320점)일 때 단순 반복(Tiling) 발생
- **해결**: Spectral Interpolation 기반 Random Phase Synthesis v2 구현
- **결과**: ✅ **성공** - ACF 피크 87% 감소 (0.7166 → 0.0964)
- **한계**: ⚠️ 근본 문제(Interaction 58.6%) 미해결
- **판정**: ⏸️ **보류** - 실제 Rainflow 개선 미미할 것으로 예상

**관련 문서**:
- 📋 **[IMPROVEMENT_PLAN_TILING_FIX.md](IMPROVEMENT_PLAN_TILING_FIX.md)** - 개선 계획서
- 📊 **[TILING_FIX_RESULTS.md](results/TILING_FIX_RESULTS.md)** - 검증 결과

**파형 분해 시각화 분석** ([상세 결과](results/WAVEFORM_ANALYSIS_SUMMARY.md))

- **배경**: Interaction 58.6% 기여도의 메커니즘 규명 필요
- **방법**: 저주파/고주파 성분 분해 및 상관관계 분석
- **핵심 발견**:
  - True: 70% 반대 방향 움직임 → 상쇄 효과 → Peak 감소
  - Pred: 50% 무작위 방향 → 상쇄 부족 → Peak 1.36배 과다
  - 재조합 과정 정확 확인 (low + high ≈ original)
- **결론**: **위상 정보가 피로 분석의 핵심**
- **시사점**: PSD 일치만으로는 피로 특성 재현 불가

**관련 문서**:
- 📋 **[WAVEFORM_VISUALIZATION_PLAN.md](WAVEFORM_VISUALIZATION_PLAN.md)** - 분석 계획서
- 📊 **[WAVEFORM_ANALYSIS_SUMMARY.md](results/WAVEFORM_ANALYSIS_SUMMARY.md)** - 분석 결과

---

## 🚀 실행 방법

```bash
# 단일 gap 테스트
python spectral_gap_fill.py --area 0243 --gap-days 3

# 전체 gap 테스트 (3, 7, 14, 24일)
python test_all_gaps.py --area 0243

# 시각화
python plot_results.py --gap-days 3
```

---

## 📚 참고 문헌

1. **MIARMA Method**: Gap filling with spectral preservation (Astronomy & Astrophysics, 2015)
2. **Spectral Gap Filling**: IEEE 2017
3. **Rainflow Spectral Methods**: Ocean Engineering, 2024
4. **Random Vibration Synthesis**: ResearchGate discussion

---

## ⚠️ 중요 발견: 평가 기준 오류

### 문제점 발견 (2025-12-11)

**핵심 오해**: Project 013은 **피로 분석을 위한 Gap filling**인데, 평가를 **전체 신호 Rainflow 매칭**으로 했음

### 올바른 평가 기준
피로 분석 워크플로우(main51-55)와 일치해야 함:
- ✅ **성분별 독립적 Rainflow counting** (저주파/고주파 각각)
- ❌ ~~전체 신호 Rainflow 매칭~~ (피로 분석에서 사용 안 함)

### 성분별 재평가 결과

| 성분 | Cycle 비율 | 초과분 기여도 | 판정 |
|------|-----------|-------------|------|
| **저주파 (ARMA)** | 1.26-1.67배 | **0.3%** | ✅ **성공** |
| **고주파 (Random Phase)** | 1.20-1.30배 | **41.0%** | △ 부분 성공 |
| **재조합 Interaction** | - | **58.6%** | 평가 불필요 |

### 수정된 판정
- **기존**: ❌ 실패 (전체 Rainflow < 0.90)
- **수정**: ⚠️ **재평가 필요** (저주파 성공, 고주파 부분 성공)

### 교훈
- **평가 기준은 목적에 맞아야 함**
- 피로 분석용 → 성분별 평가
- 신호 복원용 → 전체 신호 평가

---

## 🎯 결론 및 다음 단계

### 최종 결론

**Project 013: ❌ 실패** - Rainflow match < 0.90 (잘못된 평가 기준)

**실패 원인**:
- Spectral matching의 근본적 한계 확인
- PSD 보존 ⊄ Rainflow 보존
- Phase information 필수 → 예측 필요 → 불가능

### 즉시 조치사항

1. **Gap 허용 정책 수립** ✅ 최우선
   - 짧은 gap (< 2분): 보간 가능
   - 긴 gap (≥ 2분): 보간 불가능 → Gap 구간 제외
   - Fatigue 분석 시: Gap 메타데이터 명시

2. **데이터 품질 메타데이터**
   - Gap 위치/길이 기록
   - Fatigue 분석 신뢰도 플래그

### 장기 검토사항

- 물리 모델 기반 접근 (3개월 후 재평가)
- 센서 인프라 개선 (redundancy, 통신 강화)

### 프로젝트 타임라인

- **Project 011** (Phase 1-4): ❌ 모든 보간 방법 실패
- **Project 012** (LSTM): ❌ 비재귀 예측 실패 (R² -0.238)
- **Project 013** (Spectral): ❌ Rainflow 목표 미달 (< 0.90) - **평가 기준 오류 발견**
- **Project 014** (Component-based): 📝 계획 중 - 올바른 평가 기준 적용

**결론**: 평가 기준 재정립 필요 → Project 014에서 성분별 평가로 재시도

---

**최종 완료일**: 2025-12-11
**실제 소요시간**: 약 12시간 (예상 15시간)
