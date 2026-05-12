# 피로도 계산 공식 및 예제

## 개요
이 문서는 파이프의 피로도를 계산하는 공식과 실제 계산 예제를 설명합니다.
피로도 계산은 **2023년 1년간의 압력 데이터(2023-01-01 ~ 2023-12-31)**를 기반으로 합니다.

## 피로도 계산 버전
현재 시스템은 두 가지 버전의 피로도 계산을 제공합니다:

### 버전 1: 기본 피로도 계산 (main55_calc_fatigure.py)
- K_repair 계수를 포함하지 않음
- K_total = K_diameter × K_age × K_soil × K_traffic × K_vibration × K_material × K_stress
- 출력 경로: results/
- 출력 파일: fatigue_pipe_lm_by_age.csv, fatigue_sply_ls_by_age.csv

### 버전 2: K_repair 적용 피로도 계산 (main56_calc_fatigure.py)
- K_repair 계수 추가 적용 (1m당 수리 횟수 기반)
- K_total = K_diameter × K_age × K_soil × K_traffic × K_vibration × K_material × K_stress × (1 + C_REPAIR × K_repair)
- C_REPAIR = 10.0 (수리 계수 가중치 상수)
- K_repair는 FTR_IDN별로 매핑되며, data/main13a_k_repair/의 K_repair_per_m 컬럼 사용
- 출력 경로: results/main56_calc_fatigure/
- 출력 파일: fatigue_pipe_lm.csv, fatigue_sply_ls.csv (_by_age 접미사 제거)

## 계산 데이터 기간

### Rain Flow Counting 분석 기간
- **데이터 범위**: 2023-01-01 00:00:00 ~ 2023-12-31 23:59:59 (1년)
- **압력 데이터**: 각 지역의 5분 간격 압력 측정값
- **연간 사이클 수**: 이 1년간의 데이터에서 계산된 사이클 수를 "연간 사이클 수"로 사용
- **데이터의 품질 문제**: main41 프로젝트에서 보여줬듯이, 원 데이터 자체가 선형보간된 데이터임. 그래서 모든 구역에서 보간 안 된 데이터가 존재하는 구간이 2023년 데이터임.

### 가정
- 2023년의 압력 변동 패턴이 대표적인 1년의 패턴을 반영한다고 가정
- 잔여 수명 계산 시, 이 연간 피로 증가율이 미래에도 동일하게 유지된다고 가정

### 데이터 전처리
- NaN 값 보간 처리
- Butterworth 필터를 사용한 저주파/고주파 분리

## 피로도 계산 공식

### 1. Low 주파수 피로도 계산 (중간값)
```
Low 피로도 (중간값) = Low 주파수 사이클 수 / 피로한계
```

### 2. High 주파수 피로도 계산 (중간값)
```
High 피로도 (중간값) = High 주파수 사이클 수 / (피로한계 × High 주파수 곱셈 계수)
```

### 3. 기본손상도 (D_base) 계산
```
D_base = Low 피로도 중간값 + High 피로도 중간값
```

### 4. K 계수 계산
피로 손상에 영향을 미치는 다양한 계수들:
- **K_diameter**: 관경 계수
- **K_age**: 노후도 계수 (K_age = 1 + 0.02 × 사용년수)
- **K_soil**: 토양 계수 (FTR_IDN별 매핑)
- **K_traffic**: 교통량 계수 (도로 폭에 따라 자동 계산)
  - 광로(30m 이상): 1.6
  - 중로(15m 이상): 1.4
  - 소로(8m 이상): 1.2
  - 보행로(8m 미만): 1.0
- **K_vibration**: 진동 계수
- **K_material**: 재료 계수
- **K_stress**: 응력 집중 계수
- **K_repair**: 보수 계수 (버전 2에서만 적용, FTR_IDN별 1m당 수리 횟수 매핑)
- **K_total**: 모든 K 계수의 곱

#### 버전 1 (main5): 기본 K_total 계산
```
K_total = K_diameter × K_age × K_soil × K_traffic × K_vibration × K_material × K_stress
```

#### 버전 2 (main6): K_repair 적용 K_total 계산
```
K_total = K_diameter × K_age × K_soil × K_traffic × K_vibration × K_material × K_stress × (1 + C_REPAIR × K_repair)
```
- C_REPAIR = 10.0 (수리 계수 가중치 상수)

#### 파이프 사용 시작일 (BEG_YMD) 결정 규칙
파이프의 나이 계산을 위한 사용 시작일은 다음 규칙에 따라 결정됩니다:
1. IST_YMD(설치일)와 FNS_YMD(준공일) 중 더 최근 날짜 사용
2. IST_YMD만 있는 경우: IST_YMD 사용
3. FNS_YMD만 있는 경우: FNS_YMD 사용
4. **IST_YMD와 FNS_YMD가 모두 없는 경우: 1989년 1월 1일로 설정**
   - 이는 약 36년의 사용 기간을 의미하며, K_age ≈ 1.72가 됨

### 5. 보정손상도 (D_final) 계산
```
D_final = D_base × K_total
```

### 6. 잔여 수명 계산
```
# D_final (보정손상도)를 기반으로 잔여 수명 계산
잔여 수명(년) = (1 - D_final) / D_final  (D_final < 1인 경우)
잔여 수명(년) = 0  (D_final ≥ 1인 경우)
```
- D_final < 1: 정상적인 잔여 수명 계산
- D_final ≥ 1: 보정손상도가 100% 이상으로 수명 초과

## 상수 값
- **High 주파수 피로 한계 곱셈 계수**: 10


## 실제 계산 예제

### 예제 데이터 (ST 파이프) - 버전 1 (K_repair 미적용)
- 파이프 타입: ST (강관)
- K_material: 0.9
- 피로한계 (fatigue_limit): 1,000,000 (10⁶)
- 나이: 14,439일 ≈ 39.54년
- 관경: 100mm (K_diameter = 1.0)
- K_age: 1 + 0.02 × 39.54 = 1.791

### 0470 소구역 계산

#### 1. Low 주파수 피로도 (중간값)
- **입력값**:
  - Low 주파수 사이클 수 (연간): 1,387.16
  - 피로한계: 1,000,000

- **계산**:
  ```
  Low 피로도 (중간값) = 1,387.16 / 1,000,000
                      = 0.00138716
  ```

#### 2. High 주파수 피로도 (중간값)
- **입력값**:
  - High 주파수 사이클 수 (연간): 37,806.57
  - 피로한계: 1,000,000
  - High 주파수 곱셈 계수: 10

- **계산**:
  ```
  High 피로도 (중간값) = 37,806.57 / (1,000,000 × 10)
                      = 37,806.57 / 10,000,000
                      = 0.00378066
  ```

#### 3. 기본손상도 (D_base)
- **입력값**:
  - Low 피로도 중간값: 0.00138716
  - High 피로도 중간값: 0.00378066

- **계산**:
  ```
  D_base = Low 피로도 중간값 + High 피로도 중간값
         = 0.00138716 + 0.00378066
         = 0.00516782
  ```

#### 4. K 계수 계산
- **개별 K 계수**:
  - K_diameter: 1.0 (관경 100mm)
  - K_age: 1.791 (1 + 0.02 × 39.54)
  - K_soil: 1.2
  - K_traffic: 1.2 (도로 폭 10m → 소로)
  - K_vibration: 1.05
  - K_material: 0.9 (ST 파이프)
  - K_stress: 1.0

- **K_total 계산**:
  ```
  K_total = 1.0 × 1.791 × 1.2 × 1.2 × 1.05 × 0.9 × 1.0
          = 2.4390216
  ```

#### 5. 보정손상도 (D_final)
- **계산**:
  ```
  D_final = D_base × K_total
          = 0.00516782 × 2.4390216
          = 0.01260488 (보정손상도)
  ```

#### 6. 잔여 수명 계산
```
D_final = 0.01260488 (보정손상도)

D_final < 1이므로:
잔여 수명 = (1 - D_final) / D_final
          = (1 - 0.01260488) / 0.01260488
          = 0.98739512 / 0.01260488
          = 78.3년
```

### 0520 중구역 계산

#### 1. Low 주파수 피로도 (중간값)
- **입력값**:
  - Low 주파수 사이클 수 (연간): 1,294.79
  - 피로한계: 1,000,000

- **계산**:
  ```
  Low 피로도 (중간값) = 1,294.79 / 1,000,000
                      = 0.00129479
  ```

#### 2. High 주파수 피로도 (중간값)
- **입력값**:
  - High 주파수 사이클 수 (연간): 28,633.59
  - 피로한계: 1,000,000
  - High 주파수 곱셈 계수: 10

- **계산**:
  ```
  High 피로도 (중간값) = 28,633.59 / (1,000,000 × 10)
                      = 28,633.59 / 10,000,000
                      = 0.00286336
  ```

#### 3. 기본손상도 (D_base)
- **입력값**:
  - Low 피로도 중간값: 0.00129479
  - High 피로도 중간값: 0.00286336

- **계산**:
  ```
  D_base = Low 피로도 중간값 + High 피로도 중간값
         = 0.00129479 + 0.00286336
         = 0.00415815
  ```

#### 4. 보정손상도 (D_final)
- **계산**:
  ```
  D_final = D_base × K_total
          = 0.00415815 × 2.4390216  (동일한 K_total 사용)
          = 0.01014525 (보정손상도)
  ```

### 예제: 버전 2 (K_repair 적용)
위와 동일한 파이프에 K_repair = 0.1 (1m당 0.1회 수리)이 적용된 경우:

#### K_total 계산 (K_repair 포함)
```
K_total_base = 1.0 × 1.791 × 1.2 × 1.2 × 1.05 × 0.9 × 1.0
            = 2.4390216

K_repair = 0.1
C_REPAIR = 10.0

K_total_base = 2.4390216

K_total = K_total_base × (1 + C_REPAIR × K_repair)
        = 2.4390216 × (1 + 10.0 × 0.1)
        = 2.4390216 × (1 + 1.0)
        = 2.4390216 × 2.0
        = 4.878043
```

#### 보정손상도 (D_final)
```
D_final = D_base × K_total
        = 0.00516782 × 26.829238  (0470 구역)
        = 0.1386537 (보정손상도)

잔여 수명 = (1 - 0.1386537) / 0.1386537
          = 6.2년 (K_repair 적용 전 78.3년에서 크게 감소)
```

K_repair 계수 적용으로 인해 K_total이 증가하여 피로 손상이 커지고, 결과적으로 잔여 수명이 감소합니다.

## 코드 구현

### Low 주파수 피로도 중간값
```python
# Low 주파수 피로도 계산
fatigue_damage = actual_cycles / fatigue_limit
```

### High 주파수 피로도 중간값
```python
# High 주파수에 곱셈 계수 적용
fatigue_damage = actual_cycles / (fatigue_limit * HIGH_FREQ_FATIGUE_MULTIPLIER)
```

### D_base 계산
```python
# 기본손상도 (D_base) = Low 피로도 + High 피로도
D_base_col = f'{region}_D_base'
result_df[D_base_col] = result_df[high_fatigue_col] + result_df[low_fatigue_col]
```

### K_total 계산

#### 버전 1 (main5): 기본 K_total
```python
# 모든 K 계수의 곱
result_df['K_total'] = (result_df['K_diameter'] * 
                      result_df['K_age'] * 
                      result_df['K_soil'] * 
                      result_df['K_traffic'] * 
                      result_df['K_vibration'] * 
                      result_df['K_material'] * 
                      result_df['K_stress'])
```

#### 버전 2 (main6): K_repair 적용 K_total
```python
# K_repair 데이터 로드 및 적용
from repair_loader_k import apply_k_repair_to_dataframe

# DataFrame에 K_repair 추가 및 K_total 재계산
result_df = apply_k_repair_to_dataframe(result_df, pipe_type, repair_data)
# 내부적으로: K_total = K_total * C_REPAIR * (1 + K_repair)
```

### D_final 계산
```python
# 보정손상도 (D_final) = D_base × K_total
D_final_col = f'{region}_D_final'
result_df[D_final_col] = result_df[D_base_col] * result_df['K_total']
```

## 해석
- 이 파이프는 39.54년 사용했으며, 기본손상도(D_base)가 약 0.52% (0470 구역) 및 0.42% (0520 구역)입니다.
- K 계수들을 적용한 보정손상도(D_final)는 약 1.26% (0470 구역) 및 1.01% (0520 구역)입니다.
- 보정손상도가 1.26%이므로, 현재 속도로 계속 사용하면 약 78.3년을 더 사용할 수 있습니다.
- Low 주파수는 High 주파수보다 피로 손상에 더 큰 영향을 미칩니다 (곱셈 계수가 없음).

## 주요 특징
1. **주파수별 차별화**: High 주파수는 10배의 곱셈 계수를 적용하여 피로 영향을 감소시킵니다.
2. **다중 K 계수 적용**: 관경, 노후도, 토양, 교통량, 진동, 재료, 응력 등 다양한 환경 요인을 고려합니다.
3. **2단계 피로 손상 계산**: 
   - D_base: 순수한 주파수 기반 기본손상도
   - D_final: 모든 환경 계수를 적용한 보정손상도
4. **누적 피로**: Low와 High 주파수의 피로도를 합산하여 기본손상도를 계산합니다.
5. **선형 외삽**: 잔여 수명은 현재까지의 피로 증가율이 미래에도 동일하게 유지된다고 가정합니다.

## 계산 체계 변경 사항
- **이전**: 파이프 타입별 수명계수(fatigue_coefficient)만 적용
- **버전 1 (main5)**: 7개의 개별 K 계수를 곱한 K_total을 적용하여 더 정밀한 피로 손상 평가
- **버전 2 (main6)**: 버전 1에 K_repair 계수와 C_REPAIR 상수 추가 적용으로 보수 이력을 반영한 피로 손상 평가
- **효과**: 파이프의 실제 사용 환경과 조건을 더 세밀하게 반영
- **주요 변경**: 
  - Rain Flow Counting 결과를 연간 사이클 수로 직접 사용 (나이에 비례하지 않음)
  - K_soil: FTR_IDN별 매핑 데이터 사용
  - K_traffic: 도로 폭(ROAD_BT)에 따라 자동 계산 (IntEnum 활용)
  - K_repair: FTR_IDN별 1m당 수리 횟수 매핑 (버전 2에서만 적용)

## 실행 명령어
```bash
# 버전 1: 기본 피로도 계산 (K_repair 미적용)
python -m main55_calc_fatigure
# 또는
fatigue-calc

# 버전 2: K_repair 적용 피로도 계산
python -m main56_calc_fatigure
# 또는
fatigue-calc-repair
```