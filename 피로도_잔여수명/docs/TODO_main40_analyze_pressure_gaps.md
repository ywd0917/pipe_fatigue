# TODO: main40_analyze_pressure_gaps.py

## 📋 개요

### 목적
압력 데이터의 결측치 및 시간 간격 품질을 사전에 검사하고, Markdown 보고서와 시각화 차트를 생성하는 스크립트

### 실행 위치
main51-58 (주파수 분석 및 피로도 계산) 실행 **전** 사전 점검용

### 주요 기능
- ✅ **결측치 분석** (우선순위 1): 빈 값, NaN, 연속 결측 구간 탐지
- ✅ **시간 간격 검증** (우선순위 2): 5분 간격 불일치, 중복 타임스탬프, 시간 순서 검증
- ⚠️ **임계값 기반 자동 경고**: 모든 지역에 동일한 기준 적용하여 문제 자동 감지 (자동 보간은 하지 않음)

### 출력 형식
- Markdown 보고서 (`data_quality_report.md`)
- 시각화 차트 (PNG: 결측 비율 비교, 타임라인, 간격 분포 등)
- 선택적 JSON 출력 (`--export-json` 옵션)

---

## 🎯 개발 단계별 체크리스트

### Phase 1: 기본 구조 및 데이터 로딩
- [ ] **1.1 프로젝트 구조 설정**
  - [ ] `src/main40_analyze_pressure_gaps.py` 파일 생성
  - [ ] 필요한 import 추가 (pandas, numpy, matplotlib, pathlib 등)
  - [ ] src/common 유틸리티 import

- [ ] **1.2 설정 초기화**
  - [ ] `get_config()`로 Config 인스턴스 생성
  - [ ] 압력 데이터 파일 경로 가져오기 (`config.PRESSURE_DATA_FILES`)
  - [ ] 출력 디렉토리 설정 (`results/main40_data_quality/`)

- [ ] **1.3 로깅 설정**
  - [ ] `setup_logging()`으로 로거 초기화
  - [ ] 로그 파일 경로 설정 (`main40.log`)
  - [ ] 실행 시작/종료 로그 메시지

- [ ] **1.4 한글 폰트 설정**
  - [ ] `setup_korean_font()` 호출
  - [ ] 폰트 설정 성공 여부 로그 기록

- [ ] **1.5 데이터 로딩 함수 구현**
  ```python
  @log_execution_time
  def load_pressure_data(file_path: Path) -> pd.DataFrame:
      """
      압력 데이터 CSV 로드
      - config.encoding 사용 ("euc-kr")
      - 필수 컬럼 검증: manage_id, msrmt_dt, wtrprsr
      - msrmt_dt를 datetime으로 변환
      - 시간순 정렬
      """
  ```
  - [ ] 파일 경로 확인 시 Unicode 정규화(NFC) 처리 (macOS 호환성)
  - [ ] CSV 파일 로드 (encoding="euc-kr")
  - [ ] `validate_required_columns(df, ["manage_id", "msrmt_dt", "wtrprsr"])`
  - [ ] `validate_date_format(df["msrmt_dt"])` 로 datetime 변환
  - [ ] `df.sort_values("msrmt_dt")` 시간순 정렬
  - [ ] 에러 처리 (파일 없음, 컬럼 누락 등)

- [ ] **1.6 지역명 추출 함수**
  ```python
  def extract_area_name(file_path: Path) -> str:
      """
      파일명에서 지역 번호 추출
      - 정규식 r"(\d{4})" 사용 (소구역/중구역 모두 대응)
      예: "0470 소구역 압력 데이터.csv" -> "0470"
      예: "0520 중구역 압력 데이터.csv" -> "0520"
      """
  ```

---

### Phase 2: 결측치 분석 (우선순위 1)

- [ ] **2.1 결측치 탐지 함수 구현**
  ```python
  def detect_missing_values(df: pd.DataFrame, area_name: str) -> dict:
      """
      결측치 패턴 분석

      Returns:
      {
          "area": "0470",
          "total_records": 205164,
          "empty_string_count": 0,
          "nan_count": 2,
          "missing_ratio": 0.001,
          "consecutive_gaps": [
              {"start": "2023-05-10 13:00", "end": "2023-05-10 13:30", "duration_hours": 0.5},
          ],
          "max_gap_duration": 0.5,
      }
      """
  ```
  - [ ] 빈 문자열 개수 계산 (`df["wtrprsr"] == ""`).sum()
  - [ ] NaN 개수 계산 (`df["wtrprsr"].isna().sum()`)
  - [ ] 전체 레코드 수 대비 비율 계산
  - [ ] 연속 결측 구간 탐지 (아래 함수 활용)

- [ ] **2.2 연속 결측 구간 탐지 함수**
  ```python
  def find_consecutive_gaps(df: pd.DataFrame) -> list[dict]:
      """
      연속된 결측 구간 찾기

      Returns:
      [
          {
              "start_time": pd.Timestamp,
              "end_time": pd.Timestamp,
              "duration_hours": float,
              "missing_count": int,
          },
          ...
      ]
      """
  ```
  - [ ] 결측 마스크 생성 (`missing_mask = df["wtrprsr"].isna()`)
  - [ ] 연속 구간 그룹화 (`missing_mask.ne(missing_mask.shift()).cumsum()`)
  - [ ] 각 구간의 시작/종료 시간, 기간 계산
  - [ ] 최소 3개 이상 연속된 구간만 포함

- [ ] **2.3 결측 통계 요약 함수**
  ```python
  def summarize_missing_stats(all_results: dict) -> pd.DataFrame:
      """
      6개 지역 결측 통계를 DataFrame으로 요약

      Columns: area, total_records, missing_count, missing_ratio, max_gap_hours
      """
  ```

---

### Phase 3: 시간 간격 검증 (우선순위 2)

- [ ] **3.1 시간 간격 검증 함수 구현**
  ```python
  def validate_time_intervals(df: pd.DataFrame, expected_interval_sec: int = 300) -> dict:
      """
      시간 간격 검증

      Returns:
      {
          "duplicate_timestamps": 0,
          "out_of_order": False,
          "irregular_intervals": [
              {"time": "2023-05-10 13:00", "actual_interval_sec": 600},
          ],
          "interval_distribution": {300: 205000, 600: 50, 900: 10},
      }
      """
  ```
  - [ ] 중복 타임스탬프 탐지 (`df["msrmt_dt"].duplicated().sum()`)
  - [ ] 시간 순서 검증 (`df["msrmt_dt"].is_monotonic_increasing`)
  - [ ] 시간 간격 계산 (`df["msrmt_dt"].diff().dt.total_seconds()`)
  - [ ] 5분(300초)이 아닌 간격 추출
  - [ ] 간격 분포 히스토그램 데이터 생성

- [ ] **3.2 간격 분포 분석 함수**
  ```python
  def analyze_interval_distribution(intervals: pd.Series) -> dict:
      """
      시간 간격 분포 통계
      - 정상 간격(300초) 비율
      - 불규칙 간격 유형별 개수
      """
  ```

---

### Phase 4: 임계값 기반 자동 경고 시스템

- [ ] **4.1 경고 임계값 정의**
  ```python
  DEFAULT_THRESHOLDS = {
      'missing_ratio_warning': 1.0,      # 1% 이상 → WARNING
      'missing_ratio_critical': 3.0,     # 3% 이상 → CRITICAL
      'consecutive_hours_warning': 24,   # 24시간 이상 → WARNING
      'consecutive_days_critical': 7,    # 7일 이상 → CRITICAL
  }
  ```
  - [ ] 기본 임계값 상수 정의
  - [ ] 명령줄 옵션으로 임계값 커스터마이징 가능하도록 설계

- [ ] **4.2 경고 생성 함수 구현**
  ```python
  def generate_warnings(results: dict, thresholds: dict = None) -> list[str]:
      """
      모든 지역에 동일한 임계값 적용하여 자동 경고 생성

      Args:
          results: 각 지역별 분석 결과
          thresholds: 경고 임계값 (None이면 DEFAULT_THRESHOLDS 사용)

      Returns:
          임계값 초과한 모든 지역의 경고 메시지 리스트
          예:
          [
              "⚠️ WARNING: 0480 지역 결측 비율 3.10% (임계값: 1.0%)",
              "🔴 CRITICAL: 0480 지역 결측 비율 3.10% (임계값: 3.0%)",
              "🔴 CRITICAL: 0490 지역 최대 연속 결측 24일 (임계값: 7일)",
          ]
      """
  ```
  - [ ] 모든 지역 순회하며 임계값 검사
  - [ ] 결측 비율 검사 (WARNING: 1% 이상, CRITICAL: 3% 이상)
  - [ ] 연속 결측 기간 검사 (WARNING: 24시간 이상, CRITICAL: 7일 이상)
  - [ ] 임계값 초과 시 자동으로 경고 메시지 생성
  - [ ] 이모지로 심각도 표시 (⚠️ WARNING, 🔴 CRITICAL)

- [ ] **4.3 권장 조치사항 함수**
  ```python
  def generate_recommendations(area_results: dict, thresholds: dict) -> list[str]:
      """
      각 지역별 결측 비율에 따른 권장 조치사항

      Args:
          area_results: 특정 지역의 분석 결과
          thresholds: 임계값

      Returns:
          권장 조치사항 리스트
      """
  ```
  - [ ] 결측 비율별 권장사항 자동 생성:
    - 결측 < 1%: "데이터 품질 양호, 그대로 사용 가능"
    - 1% ≤ 결측 < 3%: "linear 보간 권장"
    - 결측 ≥ 3%: "time 또는 spline 보간 검토 필요. 해당 기간 분석 제외 고려"
  - [ ] 연속 결측 기간에 따른 추가 권장사항

---

### Phase 5: 시각화 생성

- [ ] **5.1 결측 비율 비교 막대 그래프**
  ```python
  def plot_missing_comparison(results: dict, output_dir: Path, thresholds: dict):
      """
      모든 지역 결측 비율 비교 막대 그래프

      출력: figures/missing_ratio_comparison.png

      - X축: 지역 (0243, 0461, 0470, 0480, 0490, 0520)
      - Y축: 결측 비율 (%)
      - 임계값 기준선 표시:
        - 1% 기준선 (노란색 점선) - WARNING
        - 3% 기준선 (빨간색 점선) - CRITICAL
      - 임계값 초과 지역만 색상 강조 (자동):
        - 1~3%: 노란색
        - 3% 이상: 빨간색
      """
  ```
  - [ ] `setup_plot_style()` 사용
  - [ ] `get_color_palette()` 로 색상 설정
  - [ ] 막대 그래프 그리기 (`ax.bar()`)
  - [ ] 임계값 기준선 추가 (1%, 3%)
  - [ ] 결측 비율에 따라 막대 색상 자동 설정
  - [ ] 한글 레이블 (제목, 축 레이블)
  - [ ] PNG 저장 (dpi=300)

- [ ] **5.2 결측 타임라인 그래프 (임계값 초과 지역만)**
  ```python
  def plot_missing_timeline(df: pd.DataFrame, area_name: str, output_dir: Path):
      """
      결측 시점을 타임라인으로 시각화 (임계값 초과 지역만)

      출력: figures/missing_timeline_{area}.png

      - X축: 시간 (전체 기간)
      - Y축: 압력값 (결측 구간은 빨간색 세로선으로 표시)
      - 연속 결측 구간 강조 (빨간색 박스)
      - 임계값 초과한 지역만 자동으로 생성
      """
  ```
  - [ ] 결측 비율 >= 1% 지역만 타임라인 생성
  - [ ] 압력값 시계열 플롯
  - [ ] 결측 시점에 세로선 표시 (`ax.axvline()`)
  - [ ] 연속 결측 구간 박스 표시 (`ax.axvspan()`)
  - [ ] 범례 추가 (정상 데이터 / 결측)

- [ ] **5.3 시간 간격 분포 히스토그램**
  ```python
  def plot_interval_distribution(interval_stats: dict, output_dir: Path):
      """
      시간 간격 분포 히스토그램

      출력: figures/time_interval_distribution.png

      - X축: 시간 간격 (초)
      - Y축: 빈도수 (로그 스케일)
      - 300초(5분) 정상 간격 강조
      """
  ```
  - [ ] 히스토그램 그리기
  - [ ] 정상 간격(300초) 막대만 초록색
  - [ ] 나머지는 회색
  - [ ] 로그 스케일 y축

---

### Phase 6: Markdown 보고서 생성

- [ ] **6.1 보고서 생성 함수 구현**
  ```python
  def generate_markdown_report(
      results: dict,
      warnings: list[str],
      recommendations: list[str],
      output_dir: Path
  ):
      """
      Markdown 통합 보고서 생성

      출력: data_quality_report.md

      구성:
      1. Executive Summary
      2. 결측치 분석 결과
      3. 시간 간격 검증 결과
      4. 경고 및 권장사항
      5. 지역별 상세 통계 테이블
      6. 첨부 차트 링크
      """
  ```

- [ ] **6.2 보고서 섹션별 내용**
  - [ ] **1. Executive Summary**
    - 전체 분석 개요
    - 주요 발견사항 (임계값 초과 지역 자동 탐지)
    - 권장 조치사항 요약

  - [ ] **2. 결측치 분석 결과**
    - 6개 지역 통계 테이블 (Markdown 표)
    - 결측 비율 상위 지역 강조
    - 연속 결측 구간 리스트

  - [ ] **3. 시간 간격 검증 결과**
    - 중복 타임스탬프 개수
    - 시간 순서 역전 여부
    - 불규칙 간격 통계

  - [ ] **4. 경고 및 권장사항**
    - WARNING/CRITICAL 메시지 리스트
    - 보간 방법 추천 (linear/time/spline)
    - 분석 제외 구간 제안

  - [ ] **5. 지역별 상세 통계**
    ```markdown
    | 지역 | 전체 레코드 | 결측 개수 | 결측 비율 | 최대 연속 결측 |
    |------|-------------|-----------|-----------|----------------|
    | 0243 | 231,372     | 0         | 0.000%    | -              |
    | 0480 | 223,308     | 6,925     | 3.10%     | 24일           |
    ```

  - [ ] **6. 첨부 차트**
    - 이미지 링크 (상대 경로)
    - 각 차트 설명

- [ ] **6.3 보고서 파일 저장**
  - [ ] UTF-8 인코딩으로 저장
  - [ ] 파일 경로: `results/main40_data_quality/data_quality_report.md`

---

### Phase 7: 테스트 및 문서화

- [ ] **7.1 단위 테스트**
  - [ ] 6개 압력 CSV 파일 모두 정상 로드 확인
  - [ ] 결측치 탐지 정확도 검증 (0480/0490 결측 개수)
  - [ ] 시간 간격 검증 로직 검증
  - [ ] 경고 메시지 생성 확인

- [ ] **7.2 통합 테스트**
  - [ ] main40 전체 실행 성공
  - [ ] 결과 디렉토리 생성 확인
  - [ ] 5개 PNG 파일 생성 확인
  - [ ] Markdown 보고서 생성 확인
  - [ ] 로그 파일 기록 확인

- [ ] **7.3 시각화 테스트**
  - [ ] 한글 폰트 정상 표시
  - [ ] 차트 레이아웃 깔끔함
  - [ ] 색상 구분 명확함
  - [ ] 범례 정확성

- [ ] **7.4 보고서 검토**
  - [ ] Markdown 문법 정확성
  - [ ] 통계 수치 정확성
  - [ ] 이미지 링크 작동
  - [ ] 가독성

- [ ] **7.5 스크립트 문서 작성**
  - [ ] `docs/scripts/main40_analyze_pressure_gaps.md` 생성
  - [ ] 스크립트 목적, 입력, 출력 설명
  - [ ] 명령줄 옵션 문서화
  - [ ] 실행 예제 추가

- [ ] **7.6 INDEX.md 업데이트**
  - [ ] main40 항목 추가
  - [ ] 적절한 카테고리 배치 (데이터 품질 검사)
  - [ ] 링크 확인

---

## 📊 기능 요구사항 상세

### A. 결측치 분석 상세 명세

#### 탐지 대상 ⭐ **[2025-12-12 업데이트]**
1. **NaN 결측**: 원본 CSV에 행은 있지만 `wtrprsr` 값이 NaN인 경우
   - 빈 문자열 (`""`)
   - `pd.isna(df["wtrprsr"])` = True
   - NULL 문자열: "nan", "NaN", "null", "NULL", "None" (현재 데이터에는 없음)

2. **Time Gap 결측** ⭐ **[신규]**: 5분 간격이 빠진 시간대 (행 자체가 CSV에 없음)
   - 완전한 5분 간격 시계열 생성 (`pd.date_range(freq='5min')`)
   - 원본 데이터와 병합하여 빠진 시간대 식별
   - Time Gap 결측 = 예상 레코드 수 - 원본 레코드 수 - NaN 개수

3. **총 결측**: NaN 결측 + Time Gap 결측

#### 연속 결측 정의
- **연속**: 5분 간격으로 연속된 결측 (시간 건너뛰기 없음)
- **최소 길이**: 3개 이상 (15분 이상)
- **출력**: 시작 시간, 종료 시간, 기간(시간), 개수
- **중요**: 완전한 5분 간격 시계열 기준으로 탐지

#### 통계 지표 ⭐ **[2025-12-12 업데이트]**
- 원본 레코드 수 (CSV에 실제 있는 행 수)
- 예상 레코드 수 (5분 간격 기준 전체 기간)
- NaN 결측 개수
- Time Gap 결측 개수
- 총 결측 개수 (NaN + Time Gap)
- 결측 비율 (%) = 총 결측 / 예상 레코드 수
- 연속 결측 구간 개수
- 최대 연속 결측 기간 (시간 또는 일)

---

### B. 시간 간격 검증 상세 명세

#### 검증 항목
1. **정상 간격**: 300초 (5분)
2. **중복 타임스탬프**: 동일 시간에 여러 레코드
3. **시간 순서**: `msrmt_dt`가 단조 증가하는지 (`is_monotonic_increasing`)
4. **불규칙 간격**: 300초가 아닌 간격 (예: 600초, 900초)

#### 간격 분류
- **정상**: 300초
- **짧음**: < 300초 (데이터 중복 가능성)
- **긴 간격**: 600초 (10분, 1번 누락), 900초 (15분, 2번 누락), ...
- **매우 긴 간격**: > 3600초 (1시간 이상, 센서 장애 의심)

#### 출력
- 중복 타임스탬프 개수
- 시간 순서 역전 여부 (True/False)
- 간격 분포 (히스토그램 데이터)
- 불규칙 간격 리스트 (시간, 실제 간격)

---

### C. 임계값 기반 자동 경고 전략

#### 기본 임계값 설정
```python
DEFAULT_THRESHOLDS = {
    'missing_ratio_warning': 1.0,      # 1% 이상 → WARNING
    'missing_ratio_critical': 3.0,     # 3% 이상 → CRITICAL
    'consecutive_hours_warning': 24,   # 24시간 이상 → WARNING
    'consecutive_days_critical': 7,    # 7일 이상 → CRITICAL
}
```

#### 경고 자동 생성 규칙 (모든 지역 동일 적용)

| 검사 항목 | 임계값 | 레벨 | 메시지 형식 |
|-----------|--------|------|-------------|
| 결측 비율 | ≥ 1% | WARNING | "⚠️ WARNING: {area} 지역 결측 비율 {ratio}% (임계값: 1.0%)" |
| 결측 비율 | ≥ 3% | CRITICAL | "🔴 CRITICAL: {area} 지역 결측 비율 {ratio}% (임계값: 3.0%)" |
| 연속 결측 | ≥ 24시간 | WARNING | "⚠️ WARNING: {area} 지역 최대 연속 결측 {hours}시간 (임계값: 24시간)" |
| 연속 결측 | ≥ 7일 | CRITICAL | "🔴 CRITICAL: {area} 지역 최대 연속 결측 {days}일 ({start} ~ {end})" |

#### 자동 경고 로직
```python
warnings = []
for area, result in results.items():
    missing_ratio = result['missing_ratio']
    max_gap_days = result['max_gap_duration'] / 24  # hours -> days

    # 결측 비율 검사
    if missing_ratio >= thresholds['missing_ratio_critical']:
        warnings.append(f"🔴 CRITICAL: {area} 지역 결측 비율 {missing_ratio:.2f}%")
    elif missing_ratio >= thresholds['missing_ratio_warning']:
        warnings.append(f"⚠️ WARNING: {area} 지역 결측 비율 {missing_ratio:.2f}%")

    # 연속 결측 검사
    if max_gap_days >= thresholds['consecutive_days_critical']:
        warnings.append(f"🔴 CRITICAL: {area} 지역 최대 연속 결측 {max_gap_days:.1f}일")
    elif result['max_gap_duration'] >= thresholds['consecutive_hours_warning']:
        warnings.append(f"⚠️ WARNING: {area} 지역 최대 연속 결측 {result['max_gap_duration']:.1f}시간")
```

#### 권장 조치사항 (결측 비율 기반)
| 결측 비율 | 권장 조치 |
|-----------|-----------|
| < 1% | ✅ 데이터 품질 양호. 그대로 사용 가능. |
| 1% ~ 3% | ⚠️ linear 보간 권장. main51 실행 전 `interpolate_nan_values(method='linear')` 사용. |
| ≥ 3% | 🔴 **time 또는 spline 보간 검토 필요**<br>- 연속 결측 구간이 긴 경우, 해당 기간을 분석에서 제외하는 것을 권장<br>- main20-30 공간 분석 시 해당 지역 가중치 낮춤 고려 |

#### 확장성
- **임계값 커스터마이징**: 명령줄 옵션으로 조정 가능
  ```bash
  python src/main40_analyze_pressure_gaps.py \
      --missing-warning 0.5 \
      --missing-critical 2.0 \
      --gap-days-critical 14
  ```
- **새 지역 추가 시**: 코드 수정 불필요, 자동으로 동일 기준 적용
- **특정 지역 하드코딩 제거**: 유지보수성 향상

---

## 🔧 재사용할 src/common 코드

### config.py
```python
from src.common.config import get_config

config = get_config()
pressure_files = config.PRESSURE_DATA_FILES  # 6개 파일 경로
encoding = config.encoding  # "euc-kr"
results_dir = config.RESULTS_DIR  # Path("results/")
```

### file_utils.py
```python
from src.common.file_utils import ensure_directory_exists, validate_file_exists

output_dir = ensure_directory_exists(Path("results/main40_data_quality"))
figures_dir = ensure_directory_exists(output_dir / "figures")

if validate_file_exists(file_path, raise_error=False):
    df = pd.read_csv(file_path)
```

### validation.py
```python
from src.common.validation import (
    validate_required_columns,
    validate_date_format,
    validate_numeric_range
)

# 필수 컬럼 검증
validate_required_columns(df, ["manage_id", "msrmt_dt", "wtrprsr"])

# 날짜 변환
df["msrmt_dt"] = validate_date_format(df["msrmt_dt"])

# 압력값 범위 검증 (선택적)
is_valid, stats = validate_numeric_range(df["wtrprsr"], min_value=0.0, max_value=10.0)
```

### logging_utils.py
```python
from src.common.logging_utils import setup_logging, log_execution_time, ProgressLogger

logger = setup_logging(log_file=output_dir / "main40.log")

@log_execution_time
def load_all_files():
    pass

progress = ProgressLogger(total=6, desc="압력 데이터 로딩")
for file in files:
    # 로드
    progress.update(1)
progress.finish()
```

### visualization_utils.py
```python
from src.common.visualization_utils import (
    setup_korean_font,
    setup_plot_style,
    get_color_palette,
    create_legend_elements
)

setup_korean_font()
fig, ax = setup_plot_style(figsize=(14, 6), dpi=100)
colors = get_color_palette("default")
```

---

## 📂 예상 출력 파일 구조

```
results/
└── main40_data_quality/
    ├── data_quality_report.md              # Markdown 통합 보고서
    ├── main40.log                          # 실행 로그
    ├── figures/
    │   ├── missing_ratio_comparison.png    # 6개 지역 결측 비율 막대 그래프
    │   ├── missing_timeline_0480.png       # 0480 지역 결측 타임라인
    │   ├── missing_timeline_0490.png       # 0490 지역 결측 타임라인
    │   └── time_interval_distribution.png  # 시간 간격 히스토그램
    └── (선택적) json/
        ├── 0243_quality.json               # 지역별 상세 JSON
        ├── 0461_quality.json
        ├── 0470_quality.json
        ├── 0480_quality.json
        ├── 0490_quality.json
        └── 0520_quality.json
```

---

## 🧪 테스트 시나리오

### 1. 파일 로딩 테스트
- [ ] 6개 압력 CSV 파일 모두 정상 로드
- [ ] 인코딩 오류 없음 (euc-kr)
- [ ] 필수 컬럼 존재 확인
- [ ] 날짜 변환 성공

### 2. 결측치 탐지 테스트
- [ ] 0243 지역: 결측 0개 확인
- [ ] 0480 지역: 결측 약 6,925개 확인
- [ ] 0490 지역: 결측 약 6,926개 확인
- [ ] 연속 결측 구간 정확히 탐지
- [ ] 최대 연속 결측 기간 계산 정확

### 3. 시간 간격 검증 테스트
- [ ] 정상 간격(300초) 비율 > 99%
- [ ] 중복 타임스탬프 개수 확인
- [ ] 시간 순서 역전 없음 확인
- [ ] 간격 분포 히스토그램 생성

### 4. 경고 메시지 테스트
- [ ] 결측 비율 ≥ 1% 지역 자동 감지 및 WARNING
- [ ] 결측 비율 ≥ 3% 지역 자동 감지 및 CRITICAL
- [ ] 연속 결측 ≥ 7일 지역 자동 감지
- [ ] 임계값 미달 지역: 경고 없음 (0243, 0461, 0470, 0520 등)
- [ ] 권장 조치사항 자동 생성 확인

### 5. 시각화 테스트
- [ ] PNG 파일 개수 확인 (기본 비교 차트 1개 + 임계값 초과 지역별 타임라인)
- [ ] 한글 폰트 정상 표시
- [ ] 차트 레이블 정확
- [ ] 색상 구분 명확
- [ ] 임계값 초과 지역만 자동으로 색상 강조 (노란색/빨간색)
- [ ] 임계값 기준선 표시 (1%, 3%)

### 6. 보고서 테스트
- [ ] Markdown 파일 생성 확인
- [ ] 6개 섹션 모두 포함
- [ ] 통계 수치 정확성
- [ ] 이미지 링크 작동
- [ ] UTF-8 인코딩

---

## ⏱ 예상 소요 시간

| Phase | 작업 내용 | 예상 시간 |
|-------|-----------|-----------|
| Phase 1 | 기본 구조 및 데이터 로딩 | 15분 |
| Phase 2 | 결측치 분석 | 15분 |
| Phase 3 | 시간 간격 검증 | 10분 |
| Phase 4 | 경고 시스템 | 10분 |
| Phase 5 | 시각화 생성 | 20분 |
| Phase 6 | Markdown 보고서 | 15분 |
| Phase 7 | 테스트 및 문서화 | 25분 |
| **합계** | | **약 1시간 50분** |

---

## 📝 참고 사항

### 압력 데이터 파일 정보
- **파일 개수**: 6개
- **레코드 수**: 약 200,000 ~ 231,000개/파일
- **기간**: 약 2년치 (2022-08-20 ~ 현재)
- **샘플링 간격**: 5분 (300초)
- **컬럼**: manage_id, msrmt_dt, wtrprsr

### 알려진 이슈
- **0480 소구역**: 6,925개 결측 (3.10%)
- **0490 소구역**: 6,926개 결측 (3.51%)
- **연속 결측**: 약 24일간 데이터 손실 구간 존재

### 실행 순서 권장
```bash
# 1. 데이터 품질 검사 (main40)
python src/main40_analyze_pressure_gaps.py

# 2. 보고서 확인
cat results/main40_data_quality/data_quality_report.md

# 3. 주파수 분석 (main51)
python src/main51_find_freq.py

# 4. 피로도 계산 (main52-58)
...
```

---

## ✅ 완료 조건

- [ ] TODO 문서 작성 완료 (`docs/TODO_main40_analyze_pressure_gaps.md`)
- [ ] `src/main40_analyze_pressure_gaps.py` 구현 완료
- [ ] 6개 압력 데이터 파일 모두 분석 성공
- [ ] 임계값 기반 자동 경고 시스템 정상 작동
- [ ] 모든 지역에 동일한 기준 적용 확인
- [ ] Markdown 보고서 생성 확인
- [ ] 시각화 차트 (PNG) 생성 (비교 차트 + 임계값 초과 지역별 타임라인)
- [ ] `docs/scripts/main40_analyze_pressure_gaps.md` 작성
- [ ] `docs/INDEX.md` 업데이트
- [ ] 모든 테스트 시나리오 통과

---

**문서 작성일**: 2024-12-10
**작성자**: Claude Code
**버전**: 1.0
