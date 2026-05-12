# 주파수 분리 기반 Gap 보간 방법론

**작성일**: 2025-12-10
**V-valley 기준**: 553.5분 (main51/52/53에서 도출)

---

## 📖 개요

주파수 분리 기반 보간은 다음 가설에서 시작했습니다:

> **"전체 데이터 ACF 0.145로 예측 불가능하지만, 저주파/고주파를 분리하면 어느 한쪽이라도 예측 가능할 것이다"**

**결과**:
- ✅ Phase 1: 저주파 ACF 0.9997 발견 (가설 입증)
- ❌ Phase 2: 보간 실패 (저주파만으로는 부족)

---

## 🔄 전체 프로세스

```
원본 데이터 (gap 포함)
        ↓
[Gap 전 4096 points] ━━━ [Gap 구간 865 points] ━━━ [Gap 후 4096 points]
        ↓                                                    ↓
  Butterworth Filter                                  Butterworth Filter
  (V-valley=553.5분)                                  (V-valley=553.5분)
        ↓                                                    ↓
  저주파 전 + 고주파 전                                저주파 후 + 고주파 후
        ↓                                                    ↓
        └─────────────── 각각 보간 ───────────────────┘
                              ↓
                    저주파 보간 + 고주파 보간
                              ↓
                        최종 Gap 채움
```

---

## 📊 5단계 상세 프로세스

### 1단계: Gap 전후 데이터 추출

```python
# Gap 시작/끝 인덱스
gap_start_idx = 150000  # 예시
gap_end_idx = 150864    # 3일 gap (865 points)

# Gap 전 데이터 (4096 points)
before_start_idx = gap_start_idx - 4096  # 145904
before_data = df['wtrprsr'].iloc[before_start_idx:gap_start_idx]

# Gap 후 데이터 (4096 points)
after_end_idx = gap_end_idx + 4096  # 154960
after_data = df['wtrprsr'].iloc[gap_end_idx+1:after_end_idx]
```

**왜 4096 points?**
- Butterworth 필터는 FFT 기반 → 충분한 데이터 길이 필요
- 4096 = 2^12 (FFT 최적화 크기)
- 약 14.2일치 데이터 (4096 × 5분)

**시각화**:
```
Gap 시작                       Gap 끝
     ↓                             ↓
[....4096 points]  [865 points]  [4096 points....]
     ↑                                    ↑
  Gap 전                              Gap 후
  분석용                              분석용
```

### 2단계: 주파수 분리 (Butterworth Filter)

```python
from src.pass_filter import pass_filter

sampling_rate = 1 / 300  # 5분 간격 = 300초

# Gap 전 분리
low_before, high_before = pass_filter(before_data, sampling_rate, "temp_before")

# Gap 후 분리
low_after, high_after = pass_filter(after_data, sampling_rate, "temp_after")
```

**Butterworth 필터 특성**:
- **차수**: 4차 (80 dB/decade 감쇠)
- **타입**: Zero-phase (filtfilt) - 시간 지연 없음
- **Cutoff**: V-valley frequency = 553.5분 주기

**분리 결과** (3일 gap 예시):
```
Gap 전 원본 (4096 points):
  - std: 0.0709

분리 후:
  - 저주파 (low_before): std 0.0121 (17%)
  - 고주파 (high_before): std 0.0698 (98%)

합: 0.0121² + 0.0698² ≈ 0.0709² (에너지 보존 확인)
```

**주파수 대역**:
```
저주파 (Low Pass):  ≥553.5분 주기 = 장기 트렌드
고주파 (High Pass): <553.5분 주기 = 단기 변동

V-valley
    ↓
────┴───────────────→ 주파수
저주파│  고주파
(느림)│ (빠름)
```

### 3단계: 저주파 보간 (Cubic Spline)

```python
from scipy.interpolate import CubicSpline

# 저주파 끝점 추출
before_value = low_before[-1]  # Gap 직전 1개 점
after_value = low_after[0]     # Gap 직후 1개 점

# Spline 보간
x = [0, n_gap_points - 1]      # [0, 864]
y = [before_value, after_value] # 예: [1.8523, 1.8645]

cs = CubicSpline(x, y, bc_type='natural')
low_interpolated = cs(np.arange(n_gap_points))
```

**Cubic Spline 특성**:
- **Natural boundary**: 끝점에서 2차 미분 = 0 (자연스러운 곡선)
- **C² 연속성**: 2차 미분까지 연속 (매우 부드러움)
- **2점 보간**: 시작점과 끝점만 사용

**결과** (3일 gap 예시):
```
입력:
  - before_value: 1.8523
  - after_value: 1.8645

출력 (865 points):
  [1.8523, 1.8524, 1.8526, ..., 1.8643, 1.8645]

특성:
  - std: 0.0040 (매우 작음)
  - 부드러운 곡선 (2차 함수)
```

**시각화**:
```
저주파 (Low Pass Component)

Pressure
  1.865 ┤                                    ●
        │                              ╭──╯
        │                        ╭──╯
  1.860 ┤                  ╭──╯
        │            ╭──╯
  1.855 ┤      ╭──╯
        │ ╭──╯
  1.852 ┤●
        └────┴────┴────┴────┴────┴────┴────→ Time
       전     Gap 구간 (865 points)    후
```

**왜 2점만 사용?**
- 저주파 ACF 0.9997 → 매우 연속적
- 이론상 두 끝점만으로도 충분할 것으로 예상
- 하지만 **실제로는 트렌드 무시** → 문제 발생

### 4단계: 고주파 보간 (Mean)

```python
# 고주파 전후 평균 계산
window_size = min(288, len(high_before), len(high_after))  # 1일

mean_before = np.mean(high_before[-window_size:])  # 마지막 1일 평균
mean_after = np.mean(high_after[:window_size])     # 첫 1일 평균

# 두 평균의 평균
mean_value = (mean_before + mean_after) / 2

# Gap 전체를 이 값으로 채움
high_interpolated = np.full(n_gap_points, mean_value)
```

**결과** (3일 gap 예시):
```
입력:
  - mean_before: 0.0012
  - mean_after: -0.0008

출력 (865 points):
  [0.0002, 0.0002, 0.0002, ..., 0.0002, 0.0002]

특성:
  - std: 0.0000 (완전 평탄!)
  - 모든 점이 동일한 값
```

**시각화**:
```
고주파 (High Pass Component)

Pressure
  0.002 ┤
        │
  0.000 ┤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        │                ↑
 -0.002 ┤         모든 점 동일 (mean)
        │
        └────┴────┴────┴────┴────┴────┴────→ Time
       전     Gap 구간 (865 points)    후
```

**왜 Mean?**
- 고주파 ACF 0.0746 → 예측 불가능 (거의 랜덤)
- 예측 불가능한 신호의 최선 추정 = 평균
- 하지만 **변동성 완전 제거** → 문제 발생

### 5단계: 재조합 및 평가

```python
# 재조합
gap_interpolated = low_interpolated + high_interpolated

# 평가
y_true = df_gap_true['wtrprsr'].values  # 원본 gap 값
y_pred = gap_interpolated                # 예측 gap 값

metrics = calculate_metrics(y_true, y_pred)
```

**결과** (3일 gap 예시):
```
최종 보간:
  - std: 0.0040 (저주파와 거의 동일)
  - 거의 평평한 곡선

원본:
  - std: 0.0760 (큰 변동)

에너지 보존:
  - 보간 분산: 0.000016
  - 원본 분산: 0.005781
  - 보존율: 0.3% ❌

성능:
  - R²: -0.0279
  - MAE: 0.0506
  - 판정: 실패 ❌
```

**시각화**:
```
최종 결과 (저주파 + 고주파)

Pressure
  2.0 ┤
      │    실제 (큰 변동)
  1.9 ┤  ╱╲  ╱╲╱ ╲╱╲╱╲  ╱╲
      │ ╱  ╲╱         ╲╱  ╲
  1.8 ┤━━━━━━━━━━━━━━━━━━━━━━  예측 (평평)
      │
      └────┴────┴────┴────┴────→ Time
          Gap 구간 (865 points)
```

---

## 🔍 구체적 수치 예시

### 3일 Gap 전체 흐름

#### Step 1: 데이터 추출
```
Gap 전 4096 points:
  - 시작 인덱스: 145904
  - 끝 인덱스: 150000
  - 원본 std: 0.0709

Gap 865 points:
  - 시작 인덱스: 150000
  - 끝 인덱스: 150864
  - 원본 std: 0.0760

Gap 후 4096 points:
  - 시작 인덱스: 150865
  - 끝 인덱스: 154960
  - 원본 std: 0.0848
```

#### Step 2: 주파수 분리
```
Gap 전 분리:
  - 저주파 std: 0.0121 (17%)
  - 고주파 std: 0.0698 (98%)
  - 저주파 마지막 값: 1.8523
  - 고주파 마지막 1일 평균: 0.0012

Gap 후 분리:
  - 저주파 std: 0.0186
  - 고주파 std: 0.0824
  - 저주파 첫 값: 1.8645
  - 고주파 첫 1일 평균: -0.0008
```

#### Step 3: 저주파 보간
```
Cubic Spline:
  - 시작: 1.8523
  - 끝: 1.8645
  - 증가량: 0.0122
  - 점당 증가: 0.0122 / 865 ≈ 0.000014

생성된 값 (예시):
  [1.8523, 1.8524, 1.8526, 1.8528, ..., 1.8643, 1.8645]

특성:
  - std: 0.0040
  - 부드러운 증가 곡선
```

#### Step 4: 고주파 보간
```
Mean:
  - Gap 전 평균: 0.0012
  - Gap 후 평균: -0.0008
  - 최종 평균: (0.0012 + (-0.0008)) / 2 = 0.0002

생성된 값:
  [0.0002, 0.0002, 0.0002, ..., 0.0002, 0.0002]

특성:
  - std: 0.0000 (변동 없음)
```

#### Step 5: 재조합
```
최종 = 저주파 + 고주파:
  [1.8525, 1.8526, 1.8528, ..., 1.8645, 1.8647]

특성:
  - std: 0.0040 (저주파와 거의 동일)
  - 원본 std 0.0760의 5%만

평가:
  - R²: -0.0279 (실패)
  - MAE: 0.0506
  - MAPE: 2.68%
```

---

## ❌ 왜 실패했는가?

### 문제 1: 저주파 - 트렌드 무시

**사용한 정보**:
```
Gap 전: 마지막 1점만 (1.8523)
Gap 후: 첫 1점만 (1.8645)
```

**버린 정보**:
```
Gap 전 4095점: 트렌드, 패턴, 변화율
Gap 후 4095점: 트렌드, 패턴, 변화율
```

**결과**:
- 두 점을 연결한 부드러운 곡선
- Gap 전후의 트렌드 반영 못 함

**예시**:
```
실제 트렌드:
Gap 전: 1.85 → 1.86 → 1.87 → 1.88 (상승 추세)
Gap 후: 1.88 → 1.87 → 1.86 → 1.85 (하락 추세)

Spline (2점만 사용):
Gap 전 끝: 1.88
Gap 후 시작: 1.88
→ 평평한 선 (트렌드 무시)
```

### 문제 2: 고주파 - 변동성 제거

**사용한 정보**:
```
Gap 전: 1일 평균 (0.0012)
Gap 후: 1일 평균 (-0.0008)
```

**버린 정보**:
```
변동 패턴: -0.05 → +0.08 → -0.03 → +0.12
진폭: ±0.1 정도
주기: 불규칙하지만 존재
```

**결과**:
- 평균값으로 채움 (0.0002)
- 변동성 완전 제거 (std 0.0000)
- 원본 변동 (std 0.0754)과 완전히 다름

### 문제 3: 에너지 붕괴

**데이터 구조**:
```
원본 변동의 분해:
  - 저주파 기여: 17% (std 0.0133)
  - 고주파 기여: 98% (std 0.0754)
  - 전체: std 0.0760
```

**보간 결과**:
```
  - 저주파 보간: std 0.0040 (Spline, 평탄화)
  - 고주파 보간: std 0.0000 (Mean, 완전 평탄)
  - 전체: std 0.0040 (원본의 5%!)
```

**결론**:
- 고주파가 전체 변동의 98%를 차지
- 고주파를 복원하지 못하면 전체 복원 불가
- **저주파만 완벽해도 소용없음**

---

## 💡 시도하지 않은 대안들

### 저주파 개선 방안

#### Option 1: 더 많은 점 사용
```python
# 현재: 2점만 사용
x = [0, n_points - 1]
y = [low_before[-1], low_after[0]]

# 개선: 10점씩 사용
x = [-9, -8, ..., -1, 0, n_points, ..., n_points+9]
y = [low_before[-10:], low_after[:10]]

cs = CubicSpline(x, y)
low_interpolated = cs(np.arange(n_points))
```

**기대 효과**:
- Gap 전후 트렌드 반영
- 더 정확한 곡선

#### Option 2: 트렌드 외삽
```python
# Gap 전 트렌드 계산 (최근 100점)
trend_before = np.polyfit(range(100), low_before[-100:], deg=1)

# Gap 후 트렌드 계산 (처음 100점)
trend_after = np.polyfit(range(100), low_after[:100], deg=1)

# 트렌드를 고려한 보간
# (복잡하지만 더 정확)
```

### 고주파 개선 방안

#### Option 1: 패턴 복제
```python
# Gap 전 고주파 패턴 (최근 1일)
pattern = high_before[-288:]

# Gap 구간에 패턴 반복
n_repeats = int(np.ceil(n_gap_points / 288))
high_interpolated = np.tile(pattern, n_repeats)[:n_gap_points]
```

**기대 효과**:
- 변동성 보존
- 패턴 유지

**문제**:
- 고주파 ACF 0.0746 → 패턴이 지속되지 않음
- 패턴 반복이 부자연스러울 수 있음

#### Option 2: 노이즈 생성
```python
# Gap 전후 고주파의 통계
mean = np.mean([high_before, high_after])
std = np.std([high_before, high_after])

# 랜덤 노이즈 생성
high_interpolated = np.random.normal(mean, std, n_gap_points)
```

**기대 효과**:
- 변동성 보존
- 통계적으로 유사

**문제**:
- 랜덤이므로 재현성 없음
- 원본과 완전히 다를 수 있음

#### Option 3: VAE/GAN (딥러닝)
```python
# 고주파 패턴 학습
vae = VAE()
vae.fit(high_before, high_after)

# Gap 구간 생성
high_interpolated = vae.generate(n_gap_points)
```

**기대 효과**:
- 복잡한 패턴 학습
- 실제와 유사한 변동 생성

**문제**:
- 데이터 부족
- 검증 어려움
- 과적합 위험

---

## 📊 방법론 비교

| 방법 | 저주파 | 고주파 | 장점 | 단점 | R² (3일) |
|------|--------|--------|------|------|----------|
| **Freq Sep (현재)** | 2점 Spline | Mean | 단순 | 트렌드/변동 무시 | -0.03 |
| Freq Sep + 다점 | 20점 Spline | Mean | 트렌드 반영 | 여전히 변동 제거 | 예상 0~0.1 |
| Freq Sep + 패턴 | 2점 Spline | 패턴 복제 | 변동 보존 | 패턴 부자연스러움 | 예상 0.1~0.2 |
| Freq Sep + 노이즈 | 2점 Spline | 랜덤 생성 | 통계 유사 | 재현성 없음 | 예상 0~0.2 |
| **XGBoost** | - | - | 안정적 | 평균값만 | -0.15 |
| **Linear** | - | - | 단순 | 변동 무시 | -0.70 |

---

## 🎯 결론

### 방법론의 가치

✅ **이론적 가치**:
- 주파수 분리 효과 입증
- 데이터 구조 명확히 규명
- 저주파 ACF 0.9997 발견

❌ **실용적 한계**:
- R² < 0 (모든 gap 실패)
- 고주파 복원 불가
- 기존 방법 대비 개선 미미

### 핵심 교훈

> **"예측 가능한 성분(저주파, ACF 0.9997)을 완벽히 예측해도, 그 성분이 전체 변동의 1%만 차지하면 전체 예측은 실패한다"**

**일반화**:
- 주파수 분리 → 데이터 이해 향상 ✅
- 하지만 예측은 별개 문제 ❌
- **분석 ≠ 예측**

---

**작성 일시**: 2025-12-10
**관련 문서**:
- [PHASE1_RESULTS_SUMMARY.md](component_analysis/PHASE1_RESULTS_SUMMARY.md)
- [PHASE2_RESULTS_SUMMARY.md](PHASE2_RESULTS_SUMMARY.md)
- [FINAL_COMPARISON_REPORT.md](FINAL_COMPARISON_REPORT.md)
