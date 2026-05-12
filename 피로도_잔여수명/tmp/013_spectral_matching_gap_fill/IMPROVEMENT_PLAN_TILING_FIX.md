# 013 개선 계획: Tiling Issue 해결을 위한 Spectral Interpolation

**작성일**: 2025-12-11
**목적**: Random Phase Synthesis의 Tiling(단순 반복) 문제를 해결하여 긴 Gap에서도 비반복적인(Non-repetitive) 랜덤 신호 생성

---

## 🛑 현재 문제점 (Tiling Issue)

- **현상**: Reference 데이터(약 1,200개, 20시간)보다 Gap이 긴 경우(예: 3일, 4,320개), Reference 길이만큼 생성된 신호를 단순 복사+붙여넣기함.
- **영향**:
  - 20시간 주기의 인위적인 반복 패턴 발생
  - PSD 스펙트럼에서 기본 주파수의 배수(Harmonics) 성분 왜곡
  - Rainflow Counting 시 동일한 Cycle이 단순 복제됨 (다양성 부족)

---

## 💡 해결 방안: Spectral Interpolation

"Time Domain 반복" 대신 **"Frequency Domain 보간"**을 사용합니다.

### 핵심 알고리즘

1. **Reference PSD 추출**:
   - Reference 데이터($N_{ref}$)의 주파수 스펙트럼(Magnitude) 계산
   - 주파수 해상도: $\Delta f_{ref} = 1/N_{ref}$

2. **주파수 보간 (Interpolation)**:
   - 목표 Gap 길이($N_{gap}$)에 맞는 새로운 주파수 축 생성 ($0 \sim 0.5$)
   - Reference Magnitude를 새로운 주파수 축에 맞게 보간 (Linear or Cubic Interpolation)
   - 주파수 해상도: $\Delta f_{gap} = 1/N_{gap}$ (더 촘촘해짐)

3. **Full Synthesis**:
   - Gap 전체 길이($N_{gap}$)에 해당하는 Random Phase 생성
   - 보간된 Magnitude와 결합하여 IFFT 수행
   - 결과: 반복되지 않는 길이 $N_{gap}$의 신호

---

## 📋 구현 계획

### Task 1: 개선된 합성 모듈 구현
- **파일**: `random_phase_synthesis_v2.py`
- **함수**: `spectral_interpolation_synthesis(reference, target_length)`
- **내용**: 위 알고리즘 구현 (scipy.interpolate.interp1d 활용)

### Task 2: 비교 검증 스크립트 작성
- **파일**: `test_tiling_fix.py`
- **내용**:
  - 인위적인 긴 Gap (예: Reference의 3배 길이) 설정
  - Method A (Existing): Tiling 방식
  - Method B (New): Spectral Interpolation 방식
  - 비교 항목:
    - Time Series Plot (반복 패턴 유무 시각적 확인)
    - Autocorrelation (주기적 피크 유무 확인)

### Task 3: 3일 Gap 재검증 (선택사항)
- `spectral_gap_fill.py`를 수정하여 개선된 모듈 적용
- 3일 Gap에 대해 Rainflow Match 재산출 (근본적인 Interaction 문제가 해결되는지는 미지수이나, 품질 향상 여부 확인)

---

## 📊 기대 효과

| 항목 | 기존 (Tiling) | 개선 (Interpolation) |
|------|---------------|----------------------|
| **신호 패턴** | 20시간마다 정확히 반복 | **반복 없음 (True Random)** |
| **주파수 해상도** | 낮음 ($1/1200$) | **높음 ($1/4320$)** |
| **Autocorrelation** | 주기적 피크 발생 | **피크 없음 (자연스러운 감쇠)** |
| **Rainflow** | 동일 Cycle 반복 | **다양한 Cycle 생성** |

---

## 🚀 실행 명령

```bash
# 1. 개선된 모듈 구현 및 테스트
python test_tiling_fix.py

# 2. 결과 시각화 확인
open results/tiling_fix_comparison.png
```
