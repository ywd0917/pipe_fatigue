# main40_analyze_pressure_gaps.py

## 📋 개요

### 목적
압력 데이터의 결측치 및 시간 간격 품질을 사전에 검사하고, Markdown 보고서와 시각화 차트를 생성하는 스크립트

### 실행 위치
main51-58 (주파수 분석 및 피로도 계산) 실행 **전** 사전 점검용

### 주요 기능
- ✅ **결측치 분석**: NaN 결측 + Time Gap 결측 (5분 간격 기준) 모두 탐지
- ✅ **시간 간격 검증**: 5분 간격 불일치, 중복 타임스탬프, 시간 순서 검증
- ⚠️ **임계값 기반 자동 경고**: 모든 지역에 동일한 기준 적용하여 문제 자동 감지

---

## 🎯 결측 데이터 정의 (중요!)

### 1. NaN 결측
- **정의**: 원본 CSV에 **행은 있지만 압력값(wtrprsr)이 NaN**인 경우
- **예시**:
  ```csv
  manage_id,msrmt_dt,wtrprsr
  0480,2023-03-18 05:05:00,
  0480,2023-03-18 05:10:00,NaN
  ```

### 2. Time Gap 결측 ⭐
- **정의**: **5분 간격이 빠진 시간대** (행 자체가 CSV에 없음)
- **예시**:
  ```csv
  manage_id,msrmt_dt,wtrprsr
  0480,2023-03-18 05:00:00,3.1
  0480,2023-03-18 05:05:00,3.2
  # 05:10 ~ 05:15가 누락됨
  0480,2023-03-18 05:20:00,3.3
  ```
  → 05:10, 05:15가 **Time Gap 결측**

### 3. 총 결측
- **정의**: NaN 결측 + Time Gap 결측
- **결측 비율** = 총 결측 / 예상 레코드 수 (5분 간격 기준)

---

## 💡 핵심 로직

### Time Gap 결측 탐지
```python
def detect_time_gap_missing(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """5분 간격 기준으로 빠진 시간대를 탐지"""

    # 1. 완전한 5분 간격 시계열 생성
    full_range = pd.date_range(
        start=df['msrmt_dt'].min(),
        end=df['msrmt_dt'].max(),
        freq='5min'
    )

    # 2. 원본 데이터와 병합 (빠진 시간대는 NaN)
    df_full = pd.DataFrame({'msrmt_dt': full_range})
    df_full = df_full.merge(df, on='msrmt_dt', how='left')

    # 3. Time Gap 결측 개수 계산
    original_nan = df['wtrprsr'].isna().sum()
    time_gap_missing = df_full['wtrprsr'].isna().sum() - original_nan

    return df_full, {
        'original_records': len(df),
        'expected_records': len(df_full),
        'original_nan': original_nan,
        'time_gap_missing': time_gap_missing,
        'total_missing': df_full['wtrprsr'].isna().sum(),
    }
```

---

## 📥 입력

### 필수 입력
- **압력 데이터 CSV 파일** (6개 지역)
  - 경로: `data/raw/{지역} 소구역 압력 데이터.csv`
  - 컬럼: `manage_id`, `msrmt_dt`, `wtrprsr`
  - 인코딩: `euc-kr`

### 설정 파일
- `src/common/config.py`의 `PRESSURE_DATA_FILES` 사용

---

## 📤 출력

### 1. Markdown 보고서
**파일**: `results/main40_data_quality/data_quality_report.md`

**구성**:
1. **Executive Summary**: 주요 발견사항, 경고 메시지
2. **결측치 분석 결과**:
   ```markdown
   | 지역 | 원본 레코드 | 예상 레코드 | NaN 결측 | Time Gap 결측 | 총 결측 | 결측 비율 | 최대 연속 결측 |
   |------|-------------|-------------|----------|---------------|---------|-----------|----------------|
   | 0480 | 216,383     | 223,308     | 6,925    | 0             | 6,925   | 3.10%     | 24.0일         |
   ```
3. **시간 간격 검증 결과**: 중복 타임스탬프, 불규칙 간격
4. **경고 및 권장사항**: 임계값 기반 자동 경고

### 2. 시각화 차트
**디렉토리**: `results/main40_data_quality/figures/`

- `missing_ratio_comparison.png`: 6개 지역 결측 비율 막대 그래프
- `missing_timeline_{area}.png`: 각 지역 타임라인 (전체 지역 생성)
- `time_interval_distribution.png`: 시간 간격 분포 히스토그램

### 3. 로그 파일
**파일**: `results/main40_data_quality/main40.log`

---

## 🚀 실행 방법

### 기본 실행
```bash
python src/main40_analyze_pressure_gaps.py
```

### 커스텀 임계값 설정
```bash
python src/main40_analyze_pressure_gaps.py \
    --missing-warning 0.5 \
    --missing-critical 2.0 \
    --gap-hours-warning 12 \
    --gap-days-critical 14
```

### 출력 디렉토리 지정
```bash
python src/main40_analyze_pressure_gaps.py \
    --output-dir results/custom_quality_check
```

---

## ⚙️ 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--output-dir` | 결과 저장 디렉토리 | `results/main40_data_quality/` |
| `--missing-warning` | 결측 비율 WARNING 임계값 (%) | 1.0 |
| `--missing-critical` | 결측 비율 CRITICAL 임계값 (%) | 3.0 |
| `--gap-hours-warning` | 연속 결측 WARNING 임계값 (시간) | 24 |
| `--gap-days-critical` | 연속 결측 CRITICAL 임계값 (일) | 7 |

---

## 📊 임계값 기반 경고

### 기본 임계값
```python
DEFAULT_THRESHOLDS = {
    'missing_ratio_warning': 1.0,      # 1% 이상 → WARNING
    'missing_ratio_critical': 3.0,     # 3% 이상 → CRITICAL
    'consecutive_hours_warning': 24,   # 24시간 이상 → WARNING
    'consecutive_days_critical': 7,    # 7일 이상 → CRITICAL
}
```

### 경고 메시지 예시
```
⚠️ WARNING: 0480 지역 결측 비율 1.50% (총 3,300개: NaN 100개 + Time Gap 3,200개, 임계값: 1.0%)
🔴 CRITICAL: 0490 지역 결측 비율 3.51% (총 7,800개: NaN 6,926개 + Time Gap 874개, 임계값: 3.0%)
🔴 CRITICAL: 0480 지역 최대 연속 결측 24.0일 (2025-05-19 ~ 2025-06-12)
```

---

## 🔧 재사용 코드

### src/common 유틸리티
```python
from src.common.config import get_config
from src.common.file_utils import ensure_directory_exists, validate_file_exists
from src.common.validation import validate_required_columns, validate_date_format
from src.common.logging_utils import setup_logging, log_execution_time, ProgressLogger
from src.common.visualization_utils import setup_korean_font, setup_plot_style
```

---

## 📝 권장 조치사항 (자동 생성)

| 결측 비율 | 권장 조치 |
|-----------|-----------|
| < 1% | ✅ 데이터 품질 양호. 그대로 사용 가능. |
| 1% ~ 3% | ⚠️ linear 보간 권장. main51 실행 전 `main41_fill_pressure_gaps.py` 실행. |
| ≥ 3% | 🔴 **time 또는 spline 보간 검토 필요**<br>- 연속 결측 구간이 긴 경우, 해당 기간을 분석에서 제외 권장<br>- main20-30 공간 분석 시 해당 지역 가중치 낮춤 고려 |

---

## 🧪 테스트 시나리오

### 1. 결측 탐지 테스트
- [ ] 0243 지역: 총 결측 0개 확인
- [ ] 0480 지역: NaN 결측 + Time Gap 결측 정확히 탐지
- [ ] 0490 지역: 결측 약 6,926개 확인
- [ ] 연속 결측 구간 정확히 탐지 (최대 24일)

### 2. Time Gap 탐지 검증
- [ ] 5분 간격이 빠진 시간대를 Time Gap 결측으로 분류
- [ ] 예상 레코드 수 = (종료 시간 - 시작 시간) / 5분
- [ ] Time Gap 결측 = 예상 레코드 수 - 원본 레코드 수 - NaN 개수

### 3. 보고서 검증
- [ ] Markdown 표에 NaN 결측, Time Gap 결측 구분 표시
- [ ] 경고 메시지에 결측 유형별 개수 포함
- [ ] 시각화 차트 한글 폰트 정상 표시

---

## 📂 출력 파일 구조

```
results/
└── main40_data_quality/
    ├── data_quality_report.md              # Markdown 통합 보고서
    ├── main40.log                          # 실행 로그
    └── figures/
        ├── missing_ratio_comparison.png    # 6개 지역 결측 비율 막대 그래프
        ├── missing_timeline_0243.png       # 0243 지역 타임라인
        ├── missing_timeline_0461.png       # 0461 지역 타임라인
        ├── missing_timeline_0470.png       # 0470 지역 타임라인
        ├── missing_timeline_0480.png       # 0480 지역 타임라인
        ├── missing_timeline_0490.png       # 0490 지역 타임라인
        ├── missing_timeline_0520.png       # 0520 지역 타임라인
        └── time_interval_distribution.png  # 시간 간격 히스토그램
```

---

## 🔗 관련 문서

- [TODO_main40_analyze_pressure_gaps.md](../TODO_main40_analyze_pressure_gaps.md) - 개발 체크리스트
- [GAP_INTERPOLATION_RESEARCH.md](../GAP_INTERPOLATION_RESEARCH.md) - Gap Interpolation 연구
- [workflows/workflow_main51-58_fatigue.md](../workflows/workflow_main51-58_fatigue.md) - 피로도 계산 워크플로우

---

## 📌 실행 순서 권장

```bash
# 1. 데이터 품질 검사 (main40)
python src/main40_analyze_pressure_gaps.py

# 2. 보고서 확인
cat results/main40_data_quality/data_quality_report.md

# 3. 필요시 Gap Filling (main41)
python src/main41_fill_pressure_gaps.py

# 4. 주파수 분석 (main51)
python src/main51_find_freq.py

# 5. 피로도 계산 (main52-58)
...
```

---

**작성일**: 2025-12-12
**작성자**: Claude Code
**버전**: 2.0 (Time Gap 결측 탐지 추가)
