# 포팅 가이드: main51-57 스크립트

## 개요

이 문서는 `fatigue-damage` 프로젝트의 main51-57 스크립트들을 `fatigue-qgis` 프로젝트로 포팅하는 과정을 설명합니다.

### 포팅 대상
- **소스 프로젝트**: `/Users/jhpark/development/eroumtech/fatigue/fatigue-damage`
- **대상 프로젝트**: `/Users/jhpark/development/eroumtech/fatigue/fatigue-qgis`
- **포팅 범위**: main51_find_freq.py ~ main57_merge_fatigue.py (7개 스크립트)

### Not Goal

1. 리팩토링 - 가능한 원본 파일을 그대로 사용해줘.

## 포팅 전 준비사항

### 필요한 데이터 파일
다음 데이터 파일들을 `data/raw/` 디렉토리에 복사해야 합니다:

#### 압력 데이터
- `0243 소구역 압력 데이터.csv`
- `0461 소구역 압력 데이터.csv`
- `0470 소구역 압력 데이터.csv`
- `0480 소구역 압력 데이터.csv`
- `0490 소구역 압력 데이터.csv`
- `0520 중구역 압력 데이터.csv`

#### 파이프 데이터
- `PIPE_LM.csv`
- `SPLY_LS.csv`
- `PIPE_PROP.csv`

#### 토양 데이터
- `0520_pipe_soil.csv`
- `0520_supply_soil.csv`
- `0903_pipe_soil.csv`
- `0903_supply_soil.csv`

#### 교통량 데이터
- `data/traffic/0520_pipe_traffic.csv`
- `data/traffic/0520_sply_traffic.csv`
- `data/traffic/0903_pipe_traffic.csv`
- `data/traffic/0903_sply_traffic.csv`

## config.py 통합 가이드

### 주요 차이점

| 항목 | fatigue-damage | fatigue-qgis |
|------|---------------|--------------|
| 구조 | 상수 기반 | 클래스 기반 (ProjectConfig) |
| 설정 관리 | 하드코딩 | JSON 파일 + 환경변수 |
| 디렉토리 정의 | 직접 정의 | 메서드를 통한 접근 |

### 통합 시 주의사항

#### 1. 클래스 구조 유지
```python
# fatigue-qgis의 ProjectConfig 클래스 구조를 유지하면서
# fatigue-damage의 상수들을 추가
class ProjectConfig:
    def __init__(self):
        # 기존 코드...
        
        # fatigue-damage에서 추가할 항목들
        self.PRESSURE_DATA_DIR = self.RAW_DATA_DIR
        self.PRESSURE_DATA_FILES = []  # 압력 데이터 파일 리스트
        self.V_SHAPED_MIN_FREQ = 553.5  # V자 최저점 주파수
```

#### 2. 경로 호환성
```python
# fatigue-damage 스타일 (직접 경로)
SMALL_AREA_0470_PRESSURE_DATA_PATH = RAW_DATA_DIR / "0470 소구역 압력 데이터.csv"

# fatigue-qgis 스타일 (ProjectConfig 통합)
self.SMALL_AREA_0470_PRESSURE_DATA_PATH = self.RAW_DATA_DIR / "0470 소구역 압력 데이터.csv"
```

#### 3. 필수 추가 항목

```python
# ProjectConfig __init__ 메서드에 추가해야 할 항목들:

# 압력 데이터 파일 경로
self.SMALL_AREA_0243_PRESSURE_DATA_PATH = self.RAW_DATA_DIR / "0243 소구역 압력 데이터.csv"
self.SMALL_AREA_0461_PRESSURE_DATA_PATH = self.RAW_DATA_DIR / "0461 소구역 압력 데이터.csv"
self.SMALL_AREA_0470_PRESSURE_DATA_PATH = self.RAW_DATA_DIR / "0470 소구역 압력 데이터.csv"
self.SMALL_AREA_0480_PRESSURE_DATA_PATH = self.RAW_DATA_DIR / "0480 소구역 압력 데이터.csv"
self.SMALL_AREA_0490_PRESSURE_DATA_PATH = self.RAW_DATA_DIR / "0490 소구역 압력 데이터.csv"
self.MIDDLE_AREA_PRESSURE_DATA_PATH = self.RAW_DATA_DIR / "0520 중구역 압력 데이터.csv"

# 압력 데이터 파일 리스트
self.PRESSURE_DATA_FILES = [
    self.SMALL_AREA_0243_PRESSURE_DATA_PATH,
    self.SMALL_AREA_0461_PRESSURE_DATA_PATH,
    self.SMALL_AREA_0470_PRESSURE_DATA_PATH,
    self.SMALL_AREA_0480_PRESSURE_DATA_PATH,
    self.SMALL_AREA_0490_PRESSURE_DATA_PATH,
    self.MIDDLE_AREA_PRESSURE_DATA_PATH,
]

# 파이프 데이터 파일 경로
self.PIPE_LM_PATH = self.RAW_DATA_DIR / "PIPE_LM.csv"
self.PIPE_LM_NAME = "PIPE_LM"
self.SPLY_LS_PATH = self.RAW_DATA_DIR / "SPLY_LS.csv"
self.SPLY_LS_NAME = "SPLY_LS"

# 파이프 데이터 파일 리스트
self.PIPE_DATA_FILES = [
    (self.PIPE_LM_PATH, self.PIPE_LM_NAME),
    (self.SPLY_LS_PATH, self.SPLY_LS_NAME),
]

# 파이프 속성 파일 경로
self.PIPE_PROP_PATH = self.RAW_DATA_DIR / "PIPE_PROP.csv"

# 주파수 분석 관련 상수
self.V_SHAPED_MIN_FREQ = 553.5  # V자 최저점 주파수 (분)

# Rain Flow Counting 관련 상수
self.HIGH_FREQ_FATIGUE_MULTIPLIER = 10  # High 주파수 피로 한계 곱셈 계수

# 결과 파일명
self.RESULT_FILES = {
    "PIPE_LM": "fatigue_pipe_lm_by_age.csv",
    "SPLY_LS": "fatigue_sply_ls_by_age.csv",
}

# 데이터 처리 관련 상수
self.SAMPLING_INTERVAL_MINUTES = 5  # 샘플링 간격 (분)
self.SAMPLING_FREQUENCY = 1 / (self.SAMPLING_INTERVAL_MINUTES * 60)  # Hz

# 피로 한계 기본값
self.DEFAULT_FATIGUE_LIMIT = 1000000  # 10^6 사이클

# 기본 파이프 타입 (보수적 계산에 사용)
self.DEFAULT_PIPE_TYPE = "GP"  # 아연도금강관

# 디버그 모드 (기존 debug_mode와 별도)
self.FATIGUE_DEBUG = False
```

#### 4. 하위 호환성을 위한 변수 노출

```python
# config.py 파일 하단에 추가 (기존 코드와의 호환성)
config = get_config()

# fatigue-damage 스크립트들이 직접 참조하는 변수들
PRESSURE_DATA_FILES = config.PRESSURE_DATA_FILES
PIPE_DATA_FILES = config.PIPE_DATA_FILES
PIPE_PROP_PATH = config.PIPE_PROP_PATH
V_SHAPED_MIN_FREQ = config.V_SHAPED_MIN_FREQ
HIGH_FREQ_FATIGUE_MULTIPLIER = config.HIGH_FREQ_FATIGUE_MULTIPLIER
RESULT_FILES = config.RESULT_FILES
SAMPLING_INTERVAL_MINUTES = config.SAMPLING_INTERVAL_MINUTES
SAMPLING_FREQUENCY = config.SAMPLING_FREQUENCY
DEFAULT_FATIGUE_LIMIT = config.DEFAULT_FATIGUE_LIMIT
DEFAULT_PIPE_TYPE = config.DEFAULT_PIPE_TYPE
```

## 스크립트별 포팅 가이드

### main51_find_freq.py
**목적**: 주파수 성분 분석 및 V자 최저점 검출

**의존 모듈**:
- `analysis_base.py`: 주파수 분석 핵심 함수
- `utils.py`: NaN 값 보간 등 유틸리티
- `common/korean_font_utils.py`: 한글 폰트 설정

**import 경로 수정**:
```python
# 변경 전
from analysis_base import ...
from common.korean_font_utils import ...

# 변경 후  
from src.analysis_base import ...
from src.common.korean_font_utils import ...
```

**폰트 경고 해결**:
```python
# 한글 폰트 설정 후 matplotlib 마이너스 기호 설정 추가
setup_korean_font()

# matplotlib 설정 - 마이너스 기호 관련 경고 방지
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False
```

### main52_pass_filter.py
**목적**: 패스 필터 적용

**의존 모듈**:
- `pass_filter.py`: 필터 적용 로직
- `analysis_base.py`: 분석 결과 타입 정의

### main53_rainflow.py
**목적**: Rainflow counting 분석

**의존 모듈**:
- `rain_flow_counting.py`: Rainflow 알고리즘
- `rainflow_processing.py`: 후처리 로직

### main54_pipe_data.py
**목적**: 파이프 데이터 처리

**의존 모듈**:
- `pipe_data.py`: 파이프 데이터 로더
- `pipe_func.py`: 파이프 관련 함수
- `pipe_prop.py`: 파이프 속성 처리
- `pipe_thickness.py`: 두께 계산

### main55_calc_fatigure.py & main56_calc_fatigure.py
**목적**: 피로도 계산

**의존 모듈**:
- `fatigue_calculations.py`: 피로도 계산 로직
- `pipe_const.py`: 파이프 상수 정의
- `soil_loader.py`: 토양 데이터 로더
- `traffic_loader.py`: 교통량 데이터 로더

### main57_merge_fatigue.py
**목적**: 피로도 데이터 병합

**의존 모듈**: 최소 (주로 pandas 사용)

## 공통 이슈 해결 방법

### 1. 경로 관련 문제
```python
# 문제: ModuleNotFoundError
# 해결: sys.path에 프로젝트 루트 추가
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
```

### 2. 인코딩 문제
```python
# 문제: UnicodeDecodeError
# 해결: 인코딩 명시
df = pd.read_csv(file_path, encoding='utf-8')  # 또는 'euc-kr'
```

### 3. 데이터 파일 위치
```python
# 문제: FileNotFoundError
# 해결: 절대 경로 사용
from src.common.config import get_config
config = get_config()
file_path = config.RAW_DATA_DIR / "파일명.csv"
```

## 테스트 방법

### 개별 스크립트 테스트
```bash
# 프로젝트 루트에서 실행
python src/main51_find_freq.py
python src/main52_pass_filter.py
# ... 각 스크립트 실행
```

### 단위 테스트 실행
```bash
# 개별 테스트
python -m pytest tests/test_main51_find_freq.py -v
python -m pytest tests/test_main52_pass_filter.py -v

# 전체 테스트
python -m pytest tests/test_main5*.py -v
```

## 포팅 체크리스트

### 각 스크립트별 체크리스트

- [ ] **main51_find_freq.py**
  - [ ] 스크립트 파일 복사
  - [ ] analysis_base.py 복사
  - [ ] utils.py 복사 (또는 기존 파일에 필요 함수 추가)
  - [ ] 테스트 파일 복사 (test_main51_find_freq.py)
  - [ ] 문서 복사 (docs/scripts/main51_find_freq.md)
  - [ ] config.py에 PRESSURE_DATA_FILES 추가
  - [ ] import 경로 수정
  - [ ] 테스트 실행 및 통과

- [ ] **main52_pass_filter.py**
  - [ ] 스크립트 파일 복사
  - [ ] pass_filter.py 복사
  - [ ] 테스트 파일 복사
  - [ ] 문서 복사
  - [ ] import 경로 수정
  - [ ] 테스트 실행 및 통과

- [ ] **main53_rainflow.py**
  - [ ] 스크립트 파일 복사
  - [ ] rain_flow_counting.py 복사
  - [ ] rainflow_processing.py 복사
  - [ ] 테스트 파일 복사
  - [ ] 문서 복사
  - [ ] config.py에 HIGH_FREQ_FATIGUE_MULTIPLIER 추가
  - [ ] import 경로 수정
  - [ ] 테스트 실행 및 통과

- [ ] **main54_pipe_data.py**
  - [ ] 스크립트 파일 복사
  - [ ] pipe_data.py, pipe_func.py, pipe_prop.py, pipe_thickness.py 복사
  - [ ] 테스트 파일 복사
  - [ ] 문서 복사
  - [ ] config.py에 PIPE_DATA_FILES, PIPE_PROP_PATH 추가
  - [ ] import 경로 수정
  - [ ] 테스트 실행 및 통과

- [ ] **main55_calc_fatigure.py & main56_calc_fatigure.py**
  - [ ] 스크립트 파일들 복사
  - [ ] fatigue_calculations.py 복사
  - [ ] pipe_const.py 복사
  - [ ] soil_loader.py, traffic_loader.py 복사
  - [ ] 테스트 파일 복사
  - [ ] 문서 복사
  - [ ] config.py에 DEFAULT_FATIGUE_LIMIT, DEFAULT_PIPE_TYPE 추가
  - [ ] import 경로 수정
  - [ ] 테스트 실행 및 통과

- [ ] **main57_merge_fatigue.py**
  - [ ] 스크립트 파일 복사
  - [ ] 테스트 파일 복사
  - [ ] 문서 복사
  - [ ] import 경로 수정
  - [ ] 테스트 실행 및 통과

### 데이터 파일 체크리스트

- [ ] 압력 데이터 파일 복사 완료
- [ ] 파이프 데이터 파일 복사 완료
- [ ] 토양 데이터 파일 복사 완료
- [ ] 교통량 데이터 파일 복사 완료

### 문서 체크리스트

- [ ] docs/frequency_analysis_method.md 복사
- [ ] docs/pass_filter_method.md 복사
- [ ] docs/fatigue_calculation_formula.md 복사
- [ ] docs/k_traffic_table.csv 복사
- [ ] 각 스크립트별 문서 복사 (docs/scripts/main5*.md)
- [ ] docs/INDEX.md 업데이트

### 최종 확인

- [ ] 모든 스크립트 실행 가능
- [ ] 모든 테스트 통과
- [ ] 결과 파일 생성 확인
- [ ] 문서 업데이트 완료

## 참고사항

### 데이터 무결성
- 포팅 후 결과값이 원본 프로젝트와 일치하는지 확인
- 특히 피로도 계산 결과의 정확성 검증 필요

### 버전 관리
- 각 스크립트별로 별도 브랜치에서 작업
- PR을 통한 코드 리뷰 후 머지

### 성능 고려사항
- 대용량 압력 데이터 처리 시 메모리 사용량 모니터링
- 필요시 청크 단위 처리 고려

## 트러블슈팅

### 일반적인 오류와 해결 방법

1. **ImportError: No module named 'analysis_base'**
   - src 디렉토리를 Python 경로에 추가
   - `__init__.py` 파일 확인

2. **FileNotFoundError: 압력 데이터 파일을 찾을 수 없음**
   - data/raw 디렉토리에 파일 존재 확인
   - config.py의 경로 설정 확인

3. **ValueError: 날짜 형식 변환 실패**
   - CSV 파일의 날짜 형식 확인
   - pandas to_datetime의 format 파라미터 지정

4. **MemoryError: 메모리 부족**
   - 데이터를 청크 단위로 처리
   - 불필요한 변수 삭제 (del 사용)

5. **Font 'default' does not have a glyph for '\u2212' [U+2212] 경고**
   - matplotlib의 마이너스 기호 렌더링 문제
   - 해결: `plt.rcParams['axes.unicode_minus'] = False` 설정 추가
   ```python
   # 한글 폰트 설정 후 추가
   setup_korean_font()
   plt.rcParams['axes.unicode_minus'] = False
   ```

## 연락처

포팅 관련 문의사항이 있으시면 프로젝트 관리자에게 연락 바랍니다.

---

*최종 업데이트: 2025-01-04*