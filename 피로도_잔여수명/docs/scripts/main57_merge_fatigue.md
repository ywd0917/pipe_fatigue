# main57_merge_fatigue.py - 피로 손상 계산 결과 파일 통합

## 개요
main56_calc_fatigure.py에서 생성된 두 개의 CSV 파일을 하나의 통합 파일로 병합하는 스크립트입니다.

**입력 파일**:
- `results/main56_calc_fatigure/fatigue_pipe_lm.csv` (PIPE_LM 데이터)
- `results/main56_calc_fatigure/fatigue_sply_ls.csv` (SPLY_LS 데이터)

**출력 파일**:
- `results/main57_merge_fatigue/merged_fatigue_analysis.csv` (통합 데이터)
- `results/main57_merge_fatigue/merged_fatigue_analysis_YYYYMMDD_HHMMSS.csv` (타임스탬프 버전)

## 병합 전략

### 옵션 1 채택: 모든 컬럼 유지
- 두 파일의 모든 고유 컬럼 유지
- `DATA_SOURCE` 컬럼 추가로 데이터 출처 구분
- 총 72개 컬럼 (기존 71개 + DATA_SOURCE)

### 컬럼 차이 처리
- **PIPE_LM 고유**: `IQT_CDE` (공사코드)
- **SPLY_LS 고유**: `MET_IDN` (계량기 ID)
- 해당 데이터 타입에 없는 컬럼은 NaN으로 처리

## 컬럼 구조 (72개)

### 1. 메타데이터 (1개)
```
DATA_SOURCE  # 'PIPE_LM' 또는 'SPLY_LS'
```

### 2. 기본 속성 (24개)
```
FTR_CDE, FTR_IDN           # 식별자
HJD_CDE ~ PIP_LBL          # 기본 속성
IQT_CDE                    # PIPE_LM 전용
GIS_IDN, FTC_CDE, CLS_YMD # 공통
MET_IDN                    # SPLY_LS 전용
GU_CDE ~ WTP_CDE          # 지역 정보
```

### 3. 파이프 정보 (9개)
```
PIP_TYPE                   # 파이프 타입
IST_YMD, FNS_YMD, BEG_YMD # 날짜 정보
DAYS_SINCE_BEG, YEARS_SINCE_BEG  # 경과 시간
design_pressure, thickness # 물리적 속성
K_material, fatigue_limit # 재료 속성
```

### 4. K 계수 (9개)
```
K_diameter  # 직경 계수
K_age       # 나이 계수
K_soil      # 토양 계수
K_traffic   # 교통 계수
K_vibration # 진동 계수
hoop_stress # 후프 응력
K_stress    # 응력 계수
K_repair    # 수리 계수
K_total     # 총 계수
```

### 5. 지역별 피로 분석 (28개)
각 지역(0470, 0480, 0490, 0520)별 7개 컬럼:
```
{region}_low_total_cycles      # 저주파 연간 사이클
{region}_high_total_cycles     # 고주파 연간 사이클
{region}_low_fatigue_damage    # 저주파 피로 손상
{region}_high_fatigue_damage   # 고주파 피로 손상
{region}_D_base               # 기본손상도
{region}_D_final              # 보정손상도
{region}_remaining_life_years  # 잔여 수명
```

## 주요 기능

### 1. 데이터 읽기
- main6 출력 파일 자동 탐색
- DATA_SOURCE 컬럼 추가

### 2. 데이터 병합
- 행 방향 결합 (concat)
- 누락 컬럼 NaN 처리
- 컬럼 순서 재정렬

### 3. 통계 출력
- 데이터 소스별 레코드 수
- 고유 컬럼 데이터 현황
- 파이프 타입별 분포
- K_repair 적용 통계
- 지역별 피로 손상 요약

## 사용 방법

### 기본 실행
```bash
python src/main57_merge_fatigue.py
```

### 전제 조건
main56_calc_fatigure.py가 먼저 실행되어 필요한 파일이 생성되어 있어야 합니다:
```bash
# 먼저 main6 실행
python src/main56_calc_fatigure.py

# 그 다음 main7 실행
python src/main57_merge_fatigue.py
```

## 출력 예시

```
============================================================
main57_merge_fatigue.py - 피로 손상 결과 파일 통합
============================================================

1. 데이터 파일 읽기
PIPE_LM 데이터 로드 완료: 5,432개 레코드
SPLY_LS 데이터 로드 완료: 12,876개 레코드

2. 데이터 병합 수행

병합 완료:
- PIPE_LM 레코드: 5,432개
- SPLY_LS 레코드: 12,876개
- 총 레코드: 18,308개
- 총 컬럼: 72개

3. 결과 파일 저장

파일 저장 완료: results/main57_merge_fatigue/merged_fatigue_analysis_20250102_143025.csv
최신 파일 링크: results/main57_merge_fatigue/merged_fatigue_analysis.csv

============================================================
병합 데이터 통계
============================================================

데이터 소스별 레코드 수:
  - PIPE_LM: 5,432개
  - SPLY_LS: 12,876개

고유 컬럼 데이터 현황:
  - IQT_CDE (PIPE_LM): 5,432개 레코드
  - MET_IDN (SPLY_LS): 12,876개 레코드

파이프 타입별 분포:
  - PIPE_LM / ST: 2,156개
  - PIPE_LM / CI: 1,832개
  - PIPE_LM / PE: 1,444개
  - SPLY_LS / PE: 8,234개
  - SPLY_LS / ST: 4,642개

K_repair 적용 레코드:
  - PIPE_LM: 234개
  - SPLY_LS: 567개

피로 손상 (D_final) 요약:

  0470 지역:
    - 평균: 0.012345
    - 최소: 0.001234
    - 최대: 0.045678
    - 중앙값: 0.011234

============================================================
✅ 파일 병합이 성공적으로 완료되었습니다!
============================================================
```

## 테스트

### 테스트 실행
```bash
pytest tests/test_main57_merge_fatigue.py -v
```

### 테스트 항목
- **컬럼 순서 검증**: 72개 컬럼의 정확한 순서
- **데이터 병합**: PIPE_LM과 SPLY_LS 데이터 결합
- **고유 컬럼 처리**: IQT_CDE, MET_IDN의 NaN 처리
- **통계 출력**: 각종 통계 정보 생성

## 관련 파일
- [main56_calc_fatigure.md](main56_calc_fatigure.md) - 입력 파일 생성
- [피로도 계산 공식](../fatigue_calculation_formula.md) - 계산 방법 설명

## 향후 개선 사항
- 추가 데이터 소스 병합 지원
- 데이터 검증 강화
- 시각화 기능 추가
- 병합 옵션 선택 기능