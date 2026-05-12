# main55_calc_fatigure.py - 피로 손상 계산 (K_repair 미적용)

## 개요

관망 데이터(PIPE_LM, SPLY_LS)에 대해 Rain Flow Counting 결과를 적용하여 피로 손상을 계산하고 잔여 수명을 예측하는 스크립트입니다. K_repair 계수는 적용하지 않는 기본 버전입니다.

**피로도 계산 버전**: 버전 1 (K_repair 미적용)
피로도 계산 공식과 상세한 예제는 [피로도 계산 공식 문서 - 버전 1](../fatigue_calculation_formula.md#버전-1-기본-피로도-계산-main55_calc_fatigurepy)을 참조하세요.

## 데이터 처리 흐름

1. 관망 데이터 로드 (PIPE_LM, SPLY_LS)
2. 파이프 속성 및 K 계수 데이터 로드
3. Rain Flow Counting 결과 적용
4. 재료 계수(K_material) 적용
   - K_soil: FTR_IDN별 토양 계수 매핑
   - K_traffic: 도로 폭에 따른 교통 계수 자동 계산
   - K_total: 모든 K 계수의 곱
5. 피로 손상 계산 (D_base × K_total)
6. 결과 CSV 파일 생성

## 주요 기능

- **S-N 곡선 기반 피로 계산**: 재료별 피로 특성 곡선 적용
- **누적 손상 계산**: Palmgren-Miner 법칙 기반
- **수명 예측**: 피로 수명 및 잔여 수명 계산
- **K 계수 적용**: 직경, 나이, 토양, 교통, 진동, 응력 계수
- **지역별 분석**: 0243, 0461, 0470, 0480, 0490, 0520 각 지역별 계산
- **성분별 분석**: 저대역/고대역 피로 손상 개별 계산
- **통합 피로 손상**: 저대역 + 고대역 피로 손상 합산

## 입력 파일

### 압력 데이터

- `data/raw/0243 소구역 압력 데이터.csv` - 0243 지역 압력 시계열 데이터
- `data/raw/0461 소구역 압력 데이터.csv` - 0461 지역 압력 시계열 데이터
- `data/raw/0470 소구역 압력 데이터.csv` - 0470 지역 압력 시계열 데이터
- `data/raw/0480 소구역 압력 데이터.csv` - 0480 지역 압력 시계열 데이터
- `data/raw/0490 소구역 압력 데이터.csv` - 0490 지역 압력 시계열 데이터
- `data/raw/0520 중구역 압력 데이터.csv` - 0520 지역 압력 시계열 데이터
  - Rain Flow Counting 분석의 입력 데이터
  - 최신 1년 데이터를 추출하여 피로 사이클 계산

### 관망 데이터

- `data/raw/PIPE_LM.csv` - 관망 라인 데이터
- `data/raw/SPLY_LS.csv` - 급수관 데이터

### 파이프 속성

- `data/raw/PIPE_PROP.csv` - 파이프 속성 데이터
  - 재료별 설계 압력, 두께, 피로 한계 등

### 토양/교통 데이터

- `data/raw/*_soil.csv` - FTR_IDN별 토양 계수
- `results/traffic/*_traffic.csv` - 도로 폭별 교통 계수

### Rain Flow Counting 결과 (내장)

- 2023년 최신 1년 데이터 기반
- 지역별 저대역/고대역 사이클 수
- 압력 데이터 파일에서 자동 계산

## 출력 파일

출력 디렉토리: `results/main55_calc_fatigure/`

### fatigue_pipe_lm_by_age.csv (84개 컬럼)

PIPE_LM 데이터의 피로 손상 계산 결과

### fatigue_sply_ls_by_age.csv (84개 컬럼)

SPLY_LS 데이터의 피로 손상 계산 결과

### 출력 컬럼 구조

#### 1. 원본 데이터 컬럼 (24개)

```
FTR_CDE, FTR_IDN, HJD_CDE, SHT_NUM, MNG_CDE, MOP_CDE,
STD_DIP, BYC_LEN, JHT_CDE, LOW_DEP, HGH_DEP, CNT_NUM,
SYS_CHK, PIP_LBL, IQT_CDE(PIPE_LM만), GIS_IDN, FTC_CDE,
CLS_YMD, MET_IDN(SPLY_LS만), GU_CDE, SMZ_NUM, MDZ_NUM,
LGZ_NUM, AVG_DEP, WTP_CDE, PIP_TYPE
```

#### 2. 계산된 기본 컬럼 (9개)

```
design_pressure    # 설계 압력
thickness         # 파이프 두께
K_material        # 재료 계수
fatigue_limit     # 피로 한계 (10^6 사이클)
IST_YMD          # 설치 날짜
FNS_YMD          # 완공 날짜
BEG_YMD          # 시작 날짜
DAYS_SINCE_BEG   # 경과 일수
YEARS_SINCE_BEG  # 경과 년수
```

#### 3. K 계수 컬럼 (8개)

```
K_diameter       # 직경 계수 (1 + 0.5 × (STD_DIP/100 - 1))
K_age           # 나이 계수 (1 + 0.01 × YEARS_SINCE_BEG)
K_soil          # 토양 계수 (FTR_IDN 매핑)
K_traffic       # 교통 계수 (도로 폭 기반)
K_vibration     # 진동 계수 (기본값 1.0)
hoop_stress     # 후프 응력
K_stress        # 응력 계수 (1 + 0.2 × (hoop_stress/design_pressure - 1))
K_total         # 총 계수 (모든 K 계수의 곱)
```

#### 4. 지역별 피로 분석 컬럼 (42개)

각 지역(0243, 0461, 0470, 0480, 0490, 0520)별로 7개 컬럼:

```
{region}_low_total_cycles      # 저주파 연간 사이클 수
{region}_high_total_cycles     # 고주파 연간 사이클 수
{region}_low_fatigue_damage    # 저주파 피로 손상
{region}_high_fatigue_damage   # 고주파 피로 손상
{region}_D_base               # 기본손상도 (저주파 + 고주파)
{region}_D_final              # 보정손상도 (K_total 적용)
{region}_remaining_life_years  # 잔여 수명(년)
```

## 피로 계산 공식

### 재료 계수 (K_material)

```python
K_material = {
    "ST": 0.9,     # 강관
    "STS": 0.7,    # 스테인리스강관
    기타: 1.0      # 기본값
}
```

### 피로 손상 계산

```python
# 저대역 피로 손상
low_damage = (low_cycles × K_material) / fatigue_limit

# 고대역 피로 손상 (10배 가중치)
high_damage = (high_cycles × K_material × 10) / fatigue_limit

# 기본손상도
D_base = low_damage + high_damage

# 보정손상도
D_final = D_base × K_total

# 잔여 수명
remaining_life = pipe_age / D_final
```

### K_traffic 동적 매핑

도로 폭(ROAD_BT)에 따른 교통 계수 자동 적용:

```python
도로 폭 >= 30m: K_traffic = 1.6  # 광로
도로 폭 >= 15m: K_traffic = 1.4  # 중로
도로 폭 >= 8m:  K_traffic = 1.2  # 소로
도로 폭 < 8m:   K_traffic = 1.0  # 보행로
```

## Rain Flow Counting 데이터

모든 지역의 Rain Flow Counting 데이터는 **압력 데이터 파일에서 자동으로 계산**됩니다.

### 처리 방식

- 각 압력 데이터 파일의 최신 1년 데이터를 분석
- High Pass/Low Pass 필터 적용 후 Rain Flow Counting 알고리즘 실행
- 실행 시마다 실시간으로 계산되므로 데이터 업데이트가 자동 반영

### 지원 지역

- **0243 지역**: 압력 데이터 파일에서 자동 계산
- **0461 지역**: 압력 데이터 파일에서 자동 계산
- **0470 지역**: 압력 데이터 파일에서 자동 계산
- **0480 지역**: 압력 데이터 파일에서 자동 계산
- **0490 지역**: 압력 데이터 파일에서 자동 계산
- **0520 지역**: 압력 데이터 파일에서 자동 계산

## 실행 방법

```bash
# 프로젝트 루트에서 실행
python src/main55_calc_fatigure.py
```

## 처리 성능

- 처리 속도: 약 10,000 레코드/분
- 메모리 사용: 최대 2GB
- 출력 파일 크기: 각 10-50MB

## 의존성

- `pandas`: 데이터 처리
- `numpy`: 수치 계산
- `datetime`: 날짜 계산
- `pathlib`: 파일 경로 처리

## 관련 모듈

### 코드 리팩토링

main55_calc_fatigure.py를 3개 모듈로 분리:

- `fatigue_calculations.py`: K 계수 및 피로 손상 계산 로직
- `rainflow_processing.py`: Rain Flow Counting 및 데이터 처리 로직
- `main55_calc_fatigure.py`: 메인 실행 로직만 유지

### 추가 모듈

- `pipe_prop.py`: 파이프 속성 로드
- `soil_loader.py`: K_soil 매핑
- `traffic_loader.py`: K_traffic 매핑
- `abnormal_mop_tracker.py`: 비정상 MOP_CDE 추적

## 주요 변경사항

1. **통합 피로 손상**: 고대역/저대역 피로 손상을 합친 총 피로 손상 계산
2. **잔여 수명 계산**: 총 피로 손상 기반으로 통합된 잔여 수명 계산
3. **컬럼 정렬**: 지역(0243→0520) → 성분(low→high→total→remaining_life) 순서
4. **Rain Flow 컬럼 순서**: low_total_cycles가 high_total_cycles보다 먼저 표시
5. **동적 지역 감지**: 하드코딩된 지역 목록 대신 Rain Flow Counting 결과에서 자동으로 지역 감지
6. **지역 확장**: 0243, 0461 지역 추가로 6개 지역 모두 지원

## 특징

- K_repair 계수 미적용 (기본 버전)
- 보수적 계산을 위해 null/ETC 타입은 GP 값 사용
- 고대역 성분에 10배 가중치로 피로 영향 강조
- 결과 파일은 `results/main55/` 디렉토리에 저장
- 모든 경로는 `common.config`의 절대 경로 설정 사용

## 참고사항

- 피로 한계는 10^6 사이클 기준
- S-N 곡선은 재료별로 다르게 적용
- 잔여 수명이 음수면 이미 피로 한계 초과
