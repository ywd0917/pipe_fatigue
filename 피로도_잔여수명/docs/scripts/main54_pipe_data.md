# main54_pipe_data.py - 관망 데이터 처리 및 샘플 생성

## 개요
대용량 관망 데이터(PIPE_LM, SPLY_LS)를 효율적으로 처리하고, 파이프 타입을 추출/검증하며, 분석용 샘플 데이터를 생성하는 스크립트입니다.

## 주요 기능
- **대용량 데이터 처리**: 청크 단위 메모리 효율적 처리
- **파이프 타입 자동 추출**: PIP_LBL에서 PIP_TYPE 자동 추출
- **데이터 품질 검증**: Literal 타입 기반 PIP_TYPE 유효성 검증
- **날짜 필드 처리**: 자동 날짜 형식 변환 및 BEG_YMD 생성
- **샘플 데이터 생성**: 분석용 샘플 데이터 자동 저장

## 입력 파일

### PIPE_LM.csv (관망 라인 데이터)
- **위치**: `data/raw/PIPE_LM.csv`
- **크기**: 약 100MB 이상
- **레코드 수**: 수십만 건
- **주요 필드**:
  - PIP_LBL: 파이프 라벨 (PIP_TYPE 추출원)
  - FTR_IDN: 피처 ID
  - STD_DIP: 표준 직경
  - IST_YMD, FNS_YMD: 설치/완공 날짜

### SPLY_LS.csv (급수관 데이터)
- **위치**: `data/raw/SPLY_LS.csv`
- **크기**: 약 50MB 이상
- **레코드 수**: 수십만 건
- **주요 필드**:
  - MOP_CDE: 재료 코드 (PIP_TYPE 매핑원)
  - FTR_IDN: 피처 ID
  - STD_DIP: 표준 직경
  - IST_YMD, FNS_YMD: 설치/완공 날짜

## 출력 파일

### 샘플 데이터
- `results/main54_pipe_data/pipe_lm_sample.csv`
  - PIPE_LM 데이터의 대표 샘플 (1000건)
  - PIP_TYPE 필드 추가됨
  - BEG_YMD 필드 계산됨

- `results/main54_pipe_data/sply_ls_sample.csv`
  - SPLY_LS 데이터의 대표 샘플 (1000건)
  - PIP_TYPE 필드 추가됨
  - BEG_YMD 필드 계산됨

### 샘플 데이터 구조
```csv
FTR_CDE,FTR_IDN,PIP_LBL,PIP_TYPE,STD_DIP,IST_YMD,FNS_YMD,BEG_YMD,...
SA117,12345,관경300mm_STS,STS,300,2010-01-15,2010-03-20,2010-03-20,...
```

## 파이프 타입 처리

### 유효한 파이프 타입 (14개)
```python
PipeType = Literal[
    "STS", "EPS", "ST", "CI", "GP", "PE", 
    "PFP", "DTC", "DT", "PVC", "PB", "DTEP", 
    "HIVP", "SPOL"
]
```

### 비정상 MOP_CDE 처리
- MOP_CDE=99는 'ETC' 타입으로 매핑
- 'ETC'와 null 값은 보수적 계산을 위해 GP(아연도강관) 값 사용
- 프로그램 종료 시 비정상 MOP_CDE 경고 출력

### PIPE_LM 타입 추출 규칙
- PIP_LBL에서 "_" 이후 문자열 추출
- 예: "관경300mm_STS" → "STS"

### SPLY_LS 타입 매핑
```python
MOP_CDE_TO_PIP_TYPE = {
    1: "ST",    # 강관
    2: "CI",    # 주철관
    3: "PVC",   # PVC관
    4: "STS",   # 스테인리스강관
    5: "PE",    # PE관
    # ... (총 14개 매핑)
}
```

### 유효성 검증
- 추출/매핑된 타입을 Literal 타입으로 검증
- 유효하지 않은 값은 NaN으로 변경
- 검증 통계 및 무효 값 리포트 제공

## 날짜 처리

### BEG_YMD 계산 로직
1. FNS_YMD (완공일) 우선 사용
2. FNS_YMD가 없으면 IST_YMD (설치일) 사용
3. 둘 다 없으면 NaT (Not a Time)

### 날짜 형식 자동 변환
- 다양한 형식 자동 인식 (YYYY-MM-DD, YYYYMMDD 등)
- pandas.to_datetime()으로 표준화

## 처리 성능

### 청크 처리
- **청크 크기**: 10,000 레코드
- **메모리 사용**: 최대 500MB 이하 유지
- **처리 속도**: 약 100,000 레코드/분

### 최적화 기법
- dtype 명시로 메모리 절약
- 필요한 컬럼만 선택적 로드
- 청크별 진행 상황 표시

## 실행 방법

```bash
# 프로젝트 루트에서 실행
python -m main54_pipe_data

# 또는 설치된 명령어 사용
fatigue-pipe-data
```

## 처리 통계 예시

```
=== PIPE_LM 처리 통계 ===
전체 레코드: 150,000
유효한 PIP_TYPE: 145,000 (96.7%)
무효한 PIP_TYPE: 5,000 (3.3%)

무효한 값들:
- 'UNKNOWN': 2,000건
- 'STEEL': 1,500건
- '': 1,500건

=== SPLY_LS 처리 통계 ===
전체 레코드: 80,000
유효한 PIP_TYPE: 78,000 (97.5%)
무효한 MOP_CDE: 2,000 (2.5%)
```

## 의존성
- `pandas`: 대용량 데이터 처리
- `numpy`: 수치 계산
- `pathlib`: 파일 경로 처리
- `typing`: 타입 힌트 및 Literal 타입

## 관련 모듈
- `pipe_data.py`: 데이터 처리 핵심 함수
- `pipe_const.py`: 파이프 타입 상수 정의
- `pipe_func.py`: 타입 검증 및 변환 함수
- `common/config.py`: 파일 경로 설정

## 활용
- 생성된 샘플 데이터는 테스트 및 개발에 활용
- PIP_TYPE 필드는 main5, main6에서 피로 계산에 사용
- BEG_YMD는 파이프 나이 계산의 기준일

## 참고사항
- 대용량 파일 처리 시 충분한 메모리 확보 필요
- 샘플 데이터는 전체 데이터의 대표성 확보
- 무효한 PIP_TYPE은 보수적 계산을 위해 GP(아연도강관) 값 사용