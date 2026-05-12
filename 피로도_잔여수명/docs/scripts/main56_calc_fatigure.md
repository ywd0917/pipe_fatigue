# main56_calc_fatigure.py - 피로 손상 계산 (K_repair 적용, 최신 버전)

## 개요
main55_calc_fatigure.py를 기반으로 K_repair(수리 계수)를 추가한 최신 버전의 피로 손상 계산 스크립트입니다. 1m당 수리 횟수를 반영하여 더 정확한 피로 손상을 계산합니다.
`fatigue-qgis`프로젝트 쪽에서 계산된 파일을 가져와서 다시 계산함.

**피로도 계산 버전**: 버전 2 (K_repair 적용)  
피로도 계산 공식과 K_repair 적용 예제는 [피로도 계산 공식 문서 - 버전 2](../fatigue_calculation_formula.md#버전-2-k_repair-적용-피로도-계산-main56_calc_fatigurepy)를 참조하세요.

## 데이터 처리 흐름
1. 관망 데이터 로드 (PIPE_LM, SPLY_LS)
2. 파이프 속성 및 K 계수 데이터 로드
3. Rain Flow Counting 결과 적용
4. 재료 계수(K_material) 적용
   - K_soil: FTR_IDN별 토양 계수 매핑
   - K_traffic: 도로 폭에 따른 교통 계수 자동 계산
   - K_repair: 1m당 수리 횟수 적용
   - K_total: 모든 K 계수의 곱 × (1 + C_REPAIR × K_repair)
5. 피로 손상 계산 (D_base × K_total)
6. 결과 CSV 파일 생성 (results/main56_calc_fatigure/)

## 주요 기능
- **K_repair 계수 적용**: 1m당 수리 횟수(K_repair_per_m) 반영
- **C_REPAIR 상수 적용**: 수리 계수 가중치 (기본값 10.0)
- **향상된 피로 계산**: main55의 모든 기능 + 수리 이력 고려
- **별도 출력 디렉토리**: results/main56_calc_fatigure/
- **파일명 개선**: _by_age 제거로 간결한 파일명

## 입력 파일

### 기본 입력 (main55와 동일)

#### 압력 데이터
- `data/raw/0243 소구역 압력 데이터.csv` - 0243 지역 압력 시계열 데이터
- `data/raw/0461 소구역 압력 데이터.csv` - 0461 지역 압력 시계열 데이터
- `data/raw/0470 소구역 압력 데이터.csv` - 0470 지역 압력 시계열 데이터
- `data/raw/0480 소구역 압력 데이터.csv` - 0480 지역 압력 시계열 데이터
- `data/raw/0490 소구역 압력 데이터.csv` - 0490 지역 압력 시계열 데이터
- `data/raw/0520 중구역 압력 데이터.csv` - 0520 지역 압력 시계열 데이터
  - Rain Flow Counting 분석의 입력 데이터
  - 최신 1년 데이터를 추출하여 피로 사이클 계산

#### 관망 데이터
- `data/raw/PIPE_LM.csv` - 관망 라인 데이터
- `data/raw/SPLY_LS.csv` - 급수관 데이터

#### 파이프 속성 및 계수
- `data/raw/PIPE_PROP.csv` - 파이프 속성 데이터
- `data/soil/*_soil.csv` - 토양 계수 데이터
- `data/traffic/*_traffic.csv` - 교통 계수 데이터

### 추가 입력
- **K_repair 데이터** (results/main13a_k_repair/)
  - `repair_pipe_lm.csv` - PIPE_LM의 FTR_IDN별 수리 이력
  - `repair_sply_ls.csv` - SPLY_LS의 FTR_IDN별 수리 이력
  - 각 파일에는 K_repair_per_m (1m당 수리 횟수) 컬럼 포함
  
#### K_repair CSV 파일 구조
```csv
FTR_IDN,pipe_length,K_repair,K_repair_per_m,K_repair_ground,K_repair_ground_per_m,K_repair_under,K_repair_under_per_m,K_repair_emergency,K_repair_emergency_per_m,K_repair_management,K_repair_management_per_m
```
- **K_repair**: 총 수리 횟수
- **K_repair_per_m**: 1m당 수리 횟수 (사용되는 값)
- **K_repair_ground**: 지상 수리
- **K_repair_under**: 지하 수리  
- **K_repair_emergency**: 긴급 수리
- **K_repair_management**: 관리 수리

## 출력 파일

### 출력 디렉토리
`results/main56_calc_fatigure/`

### 출력 파일
- `fatigue_pipe_lm.csv` - PIPE_LM 피로 손상 결과
- `fatigue_sply_ls.csv` - SPLY_LS 피로 손상 결과

### 출력 컬럼 구조

main55와 동일한 구조 + K_repair 및 D_final_org 컬럼 추가:

#### 1-4. 기본 컬럼 구조 (main55와 동일)
- 원본 데이터 컬럼 (24개)
- 계산된 기본 컬럼 (9개)
- K 계수 컬럼 (8개 → 9개로 확장)
- 지역별 피로 분석 컬럼 (48개 → 56개)

#### 5. K_repair 및 D_final_org 관련 추가 컬럼
```
K_repair         # 1m당 수리 횟수 (K_repair_per_m 값 사용)
{region}_D_final_org    # K_repair 적용 전 피로 손상 (비교용)
```
- K_repair 컬럼이 K_total 바로 앞에 위치
- D_final_org 컬럼이 각 지역의 D_final 바로 앞에 위치
- **총 91개 컬럼** (기존 83개 + K_repair 1개 + D_final_org 6개 + 중복 제거 1개)

## K_repair 계산 방식

### K_repair 데이터 로드
- CSV 파일에서 FTR_IDN별 K_repair_per_m 값을 직접 읽어옴
- 이미 1m당 수리 횟수로 계산된 값 사용
- FTR_IDN이 없는 경우 0.0 반환

### 피로 손상 적용
```python
# K_repair 적용 전 값 보존 (계산용)
K_total_without_repair = K_total  # CSV에는 출력되지 않음

# K_repair 및 C_REPAIR 적용
K_total = K_total × (1 + C_REPAIR × K_repair)
# 여기서 K_repair는 K_repair_per_m 값 (1m당 수리 횟수)
# C_REPAIR는 수리 계수 가중치 상수 (기본값 10.0)

# K_repair 적용 전 피로 손상 (비교용)
D_final_org = D_base × K_total_without_repair

# 보정손상도 (K_repair 적용)
D_final = D_base × K_total
```

## 주요 개선사항 (main55 대비)

### 1. K_repair 적용
- FTR_IDN별 수리 이력을 CSV 파일에서 로드
- 이미 1m당 수리 횟수로 정규화된 값 사용
- 수리가 많은 구간의 피로 손상 증가 반영
- K_total 계산 시 (1 + C_REPAIR × K_repair) 곱셈 적용

### 2. 출력 구조 개선
- 별도 디렉토리로 결과 분리 (results/main56_calc_fatigure/)
- 파일명 간소화 (_by_age 제거)
- K_repair 컬럼 추가로 수리 이력 추적 가능

### 3. 모듈 구조
- repair_loader_k.py 모듈 추가
- load_k_repair_mapping() 함수
- apply_k_repair_to_dataframe() 함수
- print_k_repair_statistics() 함수

## 실행 방법

```bash
# 프로젝트 루트에서 실행
python -m main56_calc_fatigure

# main55와 별도로 실행 가능
# 결과는 results/main56_calc_fatigure/에 저장
```

## 처리 통계 예시

```
=== K_repair 적용 통계 ===
전체 레코드: 150,000
K_repair > 0인 레코드: 120,000 (80%)
K_repair = 0인 레코드: 30,000 (20%)

K_repair 분포 (1m당 수리 횟수):
- 0.00-0.01: 80,000건 (66.7%)
- 0.01-0.05: 30,000건 (25.0%)
- 0.05-0.10: 8,000건 (6.7%)
- 0.10 이상: 2,000건 (1.6%)
```

## 의존성
main55의 모든 의존성 + 추가 모듈:
- `repair_loader_k.py`: K_repair 매핑 및 적용

## 비교: main55 vs main56

| 항목 | main55 | main56 |
|------|-------|-------|
| K_repair | 미적용 | 적용 (1m당 수리 횟수) |
| C_REPAIR | 없음 | 10.0 (수리 계수 가중치) |
| K_repair 데이터 | 없음 | results/main13a_k_repair/ CSV 파일 |
| 출력 경로 | results/ | results/main56_calc_fatigure/ |
| 파일명 | *_by_age.csv | *.csv |
| K 계수 컬럼 | 8개 | 9개 (K_repair 추가) |
| 지역 개수 | 4개 (0470, 0480, 0490, 0520) | 6개 (0243, 0461, 0470, 0480, 0490, 0520) |
| 총 컬럼 수 | 84개 | 91개 |
| 정확도 | 기본 | 향상 (수리 이력 반영) |

## D_final_org 컬럼 설명

### 목적
- **D_final_org**: K_repair 적용 전 피로 손상 값
- **D_final**: K_repair 적용 후 피로 손상 값 (최종)
- 두 값의 비교로 수리 계수가 피로 손상에 미치는 영향 정량 평가

### 활용 방법
```python
# K_repair 영향 분석
repair_impact = (D_final - D_final_org) / D_final_org * 100  # 증가율(%)

# 수리 빈도가 높은 구간일수록 repair_impact가 크게 나타남
```

## 활용
- 수리 이력이 있는 관망의 정확한 피로 평가
- 유지보수 우선순위 결정
- 수리 빈도와 피로 손상의 상관관계 분석
- **D_final_org와 D_final 비교**를 통한 K_repair 효과 정량 분석

## 최근 주요 변경사항
1. **K_repair 적용**: FTR_IDN별 수리 이력을 1m당 수리 횟수로 정규화
2. **출력 경로 변경**: results/main56_calc_fatigure/ 별도 디렉토리
3. **파일명 개선**: _by_age 제거로 간결한 파일명
4. **D_final_org 컬럼 추가**: K_repair 적용 전 피로 손상 값으로 비교 분석 가능
5. **내부 계산 최적화**: K_total_without_repair는 계산용으로만 사용, CSV 출력에서 제외
6. **지역 확장**: 0243, 0461 지역 추가로 6개 지역 지원
7. **중복 컬럼 제거**: .1 suffix 중복 컬럼 자동 제거 로직 추가
8. **동적 지역 감지**: rainflow_processing.py에서 하드코딩된 지역 목록 대신 Rain Flow Counting 결과에서 자동으로 지역 감지

## 참고사항
- K_repair가 없는 FTR_IDN은 0으로 처리
- K_repair_per_m이 높을수록 피로 손상 증가
- main55 결과와 비교하여 수리 영향 평가 가능
- 결과 파일은 항상 프로젝트 루트의 `results/main56_calc_fatigure/` 디렉토리에 저장
- 모든 경로는 `common.config`의 절대 경로 설정 사용