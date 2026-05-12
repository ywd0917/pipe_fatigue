[korean_font_utils.py](../quality-predict/src/common/korean_font_utils.py)# 코딩 표준 (Coding Standards)

본 문서는 피로 손상 분석 프로젝트의 코딩 표준을 정의합니다.

## 목차
1. [일반 코딩 표준](#일반-코딩-표준)
2. [Python 특화 표준](#python-특화-표준)

---

## 일반 코딩 표준

### 1. 함수 설계 원칙
- 각 함수는 하나의 명확한 책임만 가져야 합니다
- 함수명으로 기능을 명확히 알 수 있어야 합니다
- 함수 길이는 50줄 이하를 권장합니다

### 2. 명명 규칙
- **함수명**: 동사_명사 형태 (예: `calculate_frequency`, `filter_signal`)
- **불린 함수**: `is_`, `has_`, `can_` 접두사 사용
- **상수**: 대문자와 언더스코어 (예: `DEFAULT_SAMPLING_FREQ`)

### 3. 문서화 표준
- 복잡한 함수에는 docstring 작성
- 핵심 알고리즘이나 비즈니스 로직에 주석 추가
- 매직 넘버 사용 금지 (상수로 정의)
- 모든 main*.py 파일에 대한 함수 호출 그래프 작성 필수

### 4. 테스트 원칙
- 핵심 기능에 대한 단위 테스트 작성
- 테스트 파일명 규칙:
  - 일반 모듈: `tests/test_[소스파일명].py`
  - 공통 모듈: `tests/[모듈명]/test_[파일명].py`
  - 예: `src/main14_common/data_loader.py` → `tests/main14_common/test_data_loader.py`
- 테스트 디렉토리 구조는 소스 디렉토리 구조를 따름
- 버그 발생 시 해당 케이스 테스트 추가

---

## Python 특화 표준

### 1. 타입 힌트 (필수)
- 함수 파라미터와 반환값에 타입 명시
- `typing` 모듈 활용으로 복잡한 타입 표현
- **Python 3.10+ Union 타입**: `Optional[T]` 대신 `T | None` 사용 권장
- **dataclass 활용**: 복잡한 딕셔너리 대신 dataclass로 타입 안전성 확보
- **matplotlib 타입**: matplotlib 관련 타입은 `Any` 사용 (타입 지원 미흡으로 인한 mypy 오류 방지)

### 2. Docstring 표준 (Google Style)
- 복잡한 함수에 Args, Returns, Raises 섹션 포함
- 간단한 함수는 한 줄 설명만으로 충분

### 3. Python 테스트 표준 (pytest)
- 테스트 클래스로 관련 테스트 그룹화
- Given-When-Then 패턴 사용
- 예외 테스트는 `pytest.raises()` 활용

### 4. Python 코딩 컨벤션 (PEP 8)

#### 4.1 Import 순서
1. 표준 라이브러리
2. 서드파티 라이브러리 
3. 로컬 모듈

#### 4.2 명명 규칙
- **클래스명**: PascalCase (예: `FrequencyAnalyzer`)
- **함수명/변수명**: snake_case (예: `calculate_power_spectrum`)
- **상수명**: UPPER_SNAKE_CASE (예: `DEFAULT_SAMPLING_FREQ`)
- **Enum**: PascalCase (예: `RoadClass`)


### 5. 데이터 구조 표준

#### 5.1 dataclass 사용
- **복잡한 데이터 구조**: Dict[str, Any] 대신 dataclass 사용
- **타입 안전성**: 각 필드에 명확한 타입 정의
- **기본값 처리**: field(default_factory=...) 사용
- **문서화**: dataclass에 docstring으로 용도 설명

#### 5.2 dataclass 사용 시점
- 3개 이상의 관련된 필드를 가진 데이터 구조
- 함수 간에 전달되는 복잡한 데이터
- Any 타입을 피하고 명확한 타입 정의가 필요한 경우

### 6. 설정 관리 표준

#### 6.1 중앙화된 설정 관리
- **설정 파일 위치**: `src/common/config.py`에서 모든 설정 중앙 관리
- **명확한 상수명**: 설정의 목적을 명확히 나타내는 이름 사용
- **설정 분류**: 경로, 설정값, 상수를 논리적으로 그룹화
- **Path 객체 사용**: 모든 파일 경로는 pathlib.Path 객체로 정의
- **Import 규칙**: 모든 모듈은 `from common.config import` 사용

#### 6.2 설정 관리 모범 사례
✅ **현재 구현된 사항**:
- common/config.py를 통한 중앙화된 설정 관리
- 명확하고 설명적인 상수명 사용
- 경로, 설정, 상수의 논리적 분리
- 파일 경로에 Path 객체 사용
- 모든 모듈에서 common.config 임포트

📋 **향후 개선 사항**:
1. **환경 변수 지원**: 환경 변수를 통한 경로 오버라이드 허용
2. **설정 검증**: 경로 존재 여부 확인 함수 추가
3. **설정 클래스**: 관련 설정을 dataclass나 Pydantic으로 그룹화

#### 6.3 설정 추가 가이드라인
새로운 설정 추가 시:
1. `src/common/config.py`에 추가
2. 관련 섹션에 그룹화 (경로, 상수, 설정 등)
3. 명확한 주석으로 용도 설명
4. 타입 힌트 사용 (Path, int, float, str 등)

### 7. 좌표계 처리
- **좌표계**: EPSG:5179 (Korea 2000 / Central Belt 2010) 투영 좌표계로 변환후 처리

### 8. 스크립트 간 데이터 전달
- 스크립트에서 다른 스크립트를 호출하는 경우, 데이터 전달은 csv 나 json 으로 된 metadata를 통해서 처리

### 9. 한글 처리 표준

#### 9.1 matplotlib 한글 폰트 설정
- **그래프 한글 표시**: matplotlib 사용 시 `korean_font_utils.setup_korean_font()` 호출 필수
- **호출 시점**: 그래프 생성 전, 스크립트 초기화 단계에서 한 번만 호출
- **위치**: `from common.korean_font_utils import setup_korean_font`

#### 9.2 한글 처리 모범 사례
- 파일 인코딩은 UTF-8 사용
- 한글 문자열 처리 시 유니코드 정규화 고려 (NFC/NFD)
- CSV 파일 읽기/쓰기 시 `encoding='utf-8-sig'` 옵션 사용 (BOM 처리)

### 10. 파일 입출력 표준

#### 10.1 입력 파일 검증 패턴
- **검증 방식**: FileNotFoundError exception 사용
- **처리 위치**: 
  - 개별 모듈: 파일을 읽는 시점에서 FileNotFoundError raise
  - main 함수: exception catch 및 사용자 친화적 메시지 출력
- **장점**: 일관된 오류 처리, 중앙화된 오류 메시지 관리

#### 10.2 구현 예시

**모듈에서 (예: data_loader.py)**
```python
def load_data(file_path: Path) -> pd.DataFrame:
    """데이터 파일 로드
    
    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
    """
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))
    return pd.read_csv(file_path)
```

**main 함수에서**
```python
def main():
    try:
        data = load_data(DATA_PATH)
        # 정상 처리...
    except FileNotFoundError as e:
        missing_file = Path(str(e))
        print(f"❌ 오류: 필수 파일을 찾을 수 없습니다: {missing_file}")
        print(f"📁 파일 용도: ...")
        print(f"🔧 해결 방법: ...")
        sys.exit(1)
```

#### 10.3 오류 메시지 가이드라인
- **필수 포함 사항**:
  - 누락된 파일의 전체 경로
  - 파일의 용도와 형식 설명
  - 구체적인 해결 방법 제시
  - 관련 스크립트 실행 명령 (있는 경우)
- **메시지 형식**:
  - 이모지 사용으로 가독성 향상 (❌, 📁, 🔧)
  - 계층적 정보 구조 (오류 → 용도 → 해결)
  - 명확한 구분선으로 시각적 강조

#### 10.4 선택적 파일 처리
- **원칙**: 선택적 파일은 경고만 출력하고 기본값으로 진행
- **구현**:
```python
if optional_file.exists():
    data = pd.read_csv(optional_file)
else:
    print(f"경고: 선택적 파일 {optional_file}을 찾을 수 없습니다. 기본값 사용.")
    data = get_default_data()
```

---

## 핵심 준수 사항

### 필수 사항
1. **타입 힌트**: 함수 파라미터와 반환값에 타입 명시
2. **핵심 기능 테스트**: 중요한 알고리즘과 비즈니스 로직 테스트
3. **명확한 명명**: 함수와 변수명으로 목적을 알 수 있도록 작성
4. **인터페이스 호환성**: 
   - 명령행 옵션을 변경하지 않음 (필요시 별칭 추가)
   - CSV 파일의 컬럼명과 순서를 유지 (새 컬럼은 뒤에 추가)
   - 클래스명, 함수명, 변수명은 역할이 바뀌지 않는 한 유지

---

## 도구 설정

### 현재 프로젝트 도구
- **코드 포맷터**: black
- **코드 스타일 검사**: ruff
- **타입 체커**: mypy
- **테스트**: pytest
- **커버리지**: pytest-cov

### 코드 품질 관리 프로세스

#### Git Commit 전 필수 단계
모든 코드 변경사항은 commit 전에 다음 3단계 검사를 통과해야 합니다:

1. **코드 포맷팅 (black)**
   ```bash
   black src/ tests/
   ```
   - 코드를 일관된 스타일로 자동 포맷팅
   - 파일이 수정되므로 포맷팅 후 변경사항 확인 필요

2. **코드 스타일 검사 (ruff)**
   ```bash
   ruff check src/ tests/
   ```
   - PEP 8 스타일 가이드 준수 확인
   - 미사용 import, 긴 줄 등 검사

3. **타입 검사 (mypy)**
   ```bash
   mypy src/
   ```
   - 타입 힌트 일관성 검증
   - 타입 관련 잠재적 오류 발견

💡 **Tip**: `python run_tests.py --check` 명령으로 모든 검사를 한번에 실행할 수 있습니다.

📝 **Git Commit 메시지**: 작성된 commit 메시지는 별도의 검증 없이 그대로 사용됩니다. 프로젝트에 맞는 적절한 메시지를 작성해주세요.

#### 도구별 설정
- **black**: 기본 설정 사용 (line-length 88)
- **ruff**: 
  - 최대 줄 길이: 88자 (black과 일치)
  - pyproject.toml의 [tool.ruff] 섹션으로 관리
  - 다양한 린팅 규칙 활성화 (E, W, F, I, N, UP, B 등)
  - E203, E501 등 Black과의 호환성을 위한 규칙 무시
- **mypy**: strict 모드 권장

---

## 함수 호출 그래프 문서화

### 작성 규칙
- **대상**: 모든 main*.py 파일
- **위치**: `docs/[main파일명]_call_graph.md`
- **형식**: 텍스트 기반 트리 구조 (프로젝트 내부 함수만 포함)
- **주의**: 함수 호출 구조 이외에 상세 내용은 추가하지 않음

### 예시
```
[스크립트 진입점]
│
└── main()
    ├── parse_arguments()
    ├── load_data() [src.data_loader]
    └── process_data()
        └── save_results() [src.file_utils]

외부 의존성:
- CONFIG_VAR from src.common.config
```
