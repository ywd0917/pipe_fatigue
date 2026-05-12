# Main41 구현 계획: 압력 데이터 Gap Filling

## 📋 요약

**목적**: `main41_fill_pressure_gaps.py` 스크립트를 생성하여 Project 014에서 검증된 방법론을 사용해 압력 데이터셋의 결측 구간을 체계적으로 채우고, main40의 데이터 품질 분석을 기반으로 구축

**컨텍스트**:
- **main40**: 데이터 품질 이슈 식별 (0480, 0490 지역은 24일 gap으로 ~3% 결측)
- **Project 014**: 성분별 gap filling 방법론 개발 및 테스트
- **main51-57**: 완전한 압력 데이터가 필요한 피로 분석 파이프라인

---

## 🎯 1. 스크립트 목적 및 목표

### 1.1 주요 목표
모든 gap이 있는 5개 지역(0461, 0470, 0480, 0490, 0520)의 압력 데이터 gap을 크기에 따라 다른 방법으로 채움:

#### Gap 크기별 처리 전략
- **단기 Gap (≤ 1시간)**: XGBoost 기계학습 보간
  - 대상: 0461 (1개), 0470 (2개), 0520 (3개)
  - 시계열 특징을 학습하여 정확한 예측

- **장기 Gap (> 1시간)**: Component-wise Spectral 방법
  - 대상: 0480 (24일), 0490 (24일)
  - **Butterworth 필터**: 주파수 분리 (V-valley: 553.5분)
  - **ARMA**: 저주파 성분용
  - **Random Phase IFFT**: 고주파 성분용

### 1.2 성공 기준
- 모든 중요 gap (결측률 ≥3%, 연속 ≥7일) 채움
- 채워진 데이터의 시간적 연속성 유지
- main51-57 피로 분석 파이프라인과 호환 가능한 출력
- 검증용 성능 메트릭 저장

### 1.3 워크플로우 위치
```
main40 (데이터 품질) → main41 (gap filling) → main51 (주파수 분석) → main52-57 (피로)
```

---

## 🔍 2. 현재 상태 분석

### 2.1 데이터 품질 현황 (main40 기준)

| 지역 | 전체 레코드 | 결측 개수 | 결측률 | 최대 Gap (시간) | 처리 방법 |
|------|------------|-----------|--------|-----------------|----------|
| 0243 | 231,372 | 0 | 0.000% | - | ✅ 건너뛰기 (결측 없음) |
| 0461 | 231,372 | 1 | 0.000% | 0.08 (5분) | 🟢 XGBoost |
| 0470 | 205,164 | 2 | 0.001% | 0.17 (10분) | 🟢 XGBoost |
| 0480 | 223,308 | 6,925 | 3.101% | 577.0 (24일) | 🔴 Spectral |
| 0490 | 197,100 | 6,926 | 3.514% | 577.1 (24일) | 🔴 Spectral |
| 0520 | 205,164 | 3 | 0.001% | 0.25 (15분) | 🟢 XGBoost |

**핵심 발견사항**:
- **장기 Gap (Spectral 필요)**: 0480, 0490 - 24일 연속 gap (2025년 5-6월)
- **단기 Gap (XGBoost 사용)**: 0461, 0470, 0520 - 단일 포인트 결측 (5-15분)

### 2.2 Gap 패턴
- **0480**: 2025-05-19 13:40부터 2025-06-12 14:40까지 단일 gap (6,925 포인트)
- **0490**: 2025-05-19 13:40부터 2025-06-12 14:45까지 단일 gap (6,926 포인트)
- **Gap 유형**: 센서 오작동 또는 데이터 수집 실패 (지역 간 동일한 타이밍)

### 2.3 데이터 형식
```csv
manage_id,msrmt_dt,wtrprsr
235,2022-08-20 00:05:00.000000,1.90
235,2022-08-20 00:10:00.000000,1.90
```
- **샘플링**: 5분 간격
- **인코딩**: euc-kr
- **컬럼**: manage_id, msrmt_dt (datetime), wtrprsr (float, 압력 MPa)

---

## 🛠️ 3. 기술 설계

### 3.1 Gap Filling 방법론 (적응적 선택)

#### 방법 1: XGBoost 기계학습 보간 (Gap ≤ 1시간)
```
원본 신호 → 시계열 특징 추출 → XGBoost 학습 → Gap 예측 → 채워진 신호
           (lag features,      (주변 데이터로)
            시간 특징)
```
- **특징**: 이전 N개 값, 시간 정보 (hour, day, weekday)
- **장점**: 짧은 gap에서 높은 정확도
- **적용**: 0461, 0470, 0520의 단일 포인트 결측

#### 방법 2: Component-wise Spectral Gap Filling (Gap > 1시간)
```
원본 신호 → Butterworth 필터 (V-valley: 553.5분) → 저주파 + 고주파
                                                        ↓         ↓
                                                   ARMA (10,10)  Random Phase IFFT
                                                        ↓         ↓
                                                   Edge 스무딩    Edge 스무딩
                                                        ↓         ↓
                                                   저주파 채움  +  고주파 채움
                                                              ↓
                                                         채워진 신호
```
- **적용**: 0480, 0490의 24일 장기 gap
- **이유**: 긴 gap은 주파수 도메인 접근이 효과적

#### 주요 파라미터
- **V-valley cutoff**: 553.5분 (main51 기준)
- **Butterworth 차수**: 4
- **ARMA 차수**: (10, 10)
- **Edge 스무딩 윈도우**: 60 포인트 (저주파), 20 포인트 (고주파)
- **참조 길이**: Random Phase용 10,080 포인트 (7일)

### 3.2 알려진 한계 (Project 014 기준)

#### 장기 Gap에서의 ARMA (24일)
- ⚠️ **문제**: ARMA가 매우 긴 gap에서 실패, 선형 보간으로 fallback
- **영향**: 저주파 에너지가 ~4배 증가 (테스트에서 391%)
- **대안**: gap 전 가용 데이터로 학습, 품질 저하 수용

#### 고주파에서의 Random Phase
- ⚠️ **문제**: CCR ~0.78 (목표: 0.95) - 시간 구조 손실
- **영향**: Rainflow 사이클 수가 실제 신호와 다름
- **수용**: 고주파 분산이 작음 (전체의 5%), 피로 분석에 허용 가능

### 3.3 출력 품질 메트릭
각 채워진 gap에 대해 저장:
- Gap 위치 (시작, 종료 인덱스 및 타임스탬프)
- Gap 길이 (일, 시간, 포인트)
- 전/후 저주파 성분 분산
- 전/후 고주파 성분 분산
- ARMA fit 상태 (성공/선형 fallback)
- 사용된 Edge 스무딩 파라미터

---

## 📁 4. 스크립트 구조

### 4.1 파일 구성
```
src/
├── main41_fill_pressure_gaps.py     # 메인 스크립트
└── common/
    ├── gap_fill_utils.py            # 재사용 가능한 gap filling 함수
    └── config.py                     # 설정 (이미 V_SHAPED_MIN_FREQ 포함)

results/
└── main41_gap_filling/
    ├── filled_data/                 # 채워진 CSV 파일
    │   ├── 0480_filled.csv
    │   └── 0490_filled.csv
    ├── quality_metrics/             # 지역별 메트릭
    │   ├── 0480_metrics.json
    │   └── 0490_metrics.json
    ├── visualizations/              # 전/후 플롯
    │   ├── 0480_gap_comparison.png
    │   └── 0490_gap_comparison.png
    └── gap_filling_report.md        # 요약 보고서
```

### 4.2 모듈 구조

#### `common/gap_fill_utils.py`
```python
# Project 014에서 추출한 핵심 함수
- butterworth_frequency_separation()
- arma_synthesis()
- random_phase_synthesis()
- edge_smoothing()
- spectral_gap_fill()
- validate_filled_data()
```

#### `main41_fill_pressure_gaps.py`
```python
# 메인 워크플로우
- detect_gaps() # main40에서 재사용
- apply_gap_filling()
- save_filled_data()
- generate_quality_metrics()
- create_visualizations()
- generate_report()
```

---

## 📊 5. 상세 구현 단계

### 5.1 Phase 1: 설정 및 준비
**예상 시간**: 30분

#### 작업:
1. ✅ `src/common/gap_fill_utils.py` 생성
   - Project 014 baseline_test.py에서 핵심 함수 추출
   - 포괄적인 docstring 추가
   - 파라미터 검증 포함

2. ✅ `src/main41_fill_pressure_gaps.py` 뼈대 생성
   - Import 문 (pandas, numpy, scipy, common 모듈)
   - Argument parser 설정
   - 로깅 구성
   - 출력 디렉토리 생성

3. ✅ `src/common/config.py` 업데이트
   - `GAP_FILL_RESULTS_DIR` 추가
   - gap filling 파라미터를 상수로 추가

#### 산출물:
- [ ] 6개 핵심 함수를 포함한 `gap_fill_utils.py`
- [ ] `main41_fill_pressure_gaps.py` 기본 구조
- [ ] 업데이트된 config.py

---

### 5.2 Phase 2: 핵심 Gap Filling 로직
**예상 시간**: 1시간

#### 작업:
1. ✅ Gap 탐지 구현
   ```python
   def detect_gaps(df: pd.DataFrame,
                   min_gap_hours: float = 1.0) -> List[Dict]:
       """
       연속적인 결측값 gap 탐지
       반환: gap 정보 리스트 (start_idx, end_idx, duration)
       """
   ```

2. ✅ 주파수 분리 구현
   ```python
   def separate_frequencies(data: np.ndarray,
                           v_valley_min: float = 553.5) -> Tuple:
       """
       Butterworth 필터로 저/고주파 분리
       config.V_SHAPED_MIN_FREQ 사용
       """
   ```

3. ✅ ARMA 합성 통합
   ```python
   def fill_low_frequency(low_freq: np.ndarray,
                         gap_start: int, gap_end: int) -> np.ndarray:
       """
       ARMA(10,10) 합성 with 선형 fallback
       """
   ```

4. ✅ Random Phase IFFT 통합
   ```python
   def fill_high_frequency(high_freq: np.ndarray,
                          gap_start: int, gap_end: int) -> np.ndarray:
       """
       참조 신호를 사용한 Random Phase IFFT
       """
   ```

5. ✅ Edge 스무딩 구현
   ```python
   def smooth_gap_edges(filled: np.ndarray,
                       gap_start: int, gap_end: int) -> np.ndarray:
       """
       gap 경계에서 코사인 테이퍼링
       """
   ```

#### 산출물:
- [ ] 테스트된 5개 gap filling 함수
- [ ] `tests/test_gap_fill_utils.py`의 단위 테스트

---

### 5.3 Phase 3: 데이터 I/O 및 검증
**예상 시간**: 45분

#### 작업:
1. ✅ 압력 데이터 로드
   ```python
   def load_pressure_data_for_filling(file_path: Path) -> pd.DataFrame:
       """
       main40 스타일 검증으로 로드
       main40 로직으로 gap 확인
       """
   ```

2. ✅ 채워진 데이터 저장
   ```python
   def save_filled_data(df: pd.DataFrame,
                       area_code: str,
                       output_dir: Path) -> Path:
       """
       원본과 동일한 형식으로 저장
       메타데이터 주석 헤더 추가
       """
   ```

3. ✅ 검증 확인
   ```python
   def validate_filled_data(original: pd.DataFrame,
                           filled: pd.DataFrame) -> Dict:
       """
       확인 사항:
       - 새로운 NaN 값 없음
       - gap 경계의 연속성
       - 분산 보존
       - 시계열 무결성
       """
   ```

#### 산출물:
- [ ] 데이터 로딩 함수 (main40과 호환)
- [ ] 데이터 저장 함수 (main51과 호환)
- [ ] 5개 체크를 포함한 검증 모음

---

### 5.4 Phase 4: 품질 메트릭 및 보고
**예상 시간**: 1시간

#### 작업:
1. ✅ 품질 메트릭 계산
   ```python
   def calculate_gap_metrics(original: np.ndarray,
                            filled: np.ndarray,
                            gap_start: int, gap_end: int) -> Dict:
       """
       메트릭:
       - 저/고주파 분산 비율
       - 스펙트럼 유사도 (해당하는 경우)
       - Edge 불연속성 측정
       - ARMA fit 품질
       """
   ```

2. ✅ 시각화 생성
   ```python
   def visualize_gap_filling(original: np.ndarray,
                            filled: np.ndarray,
                            gap_start: int, gap_end: int,
                            area_code: str) -> Path:
       """
       4패널 플롯:
       (1) gap이 강조된 원본
       (2) 채워진 저주파 성분
       (3) 채워진 고주파 성분
       (4) 결합된 채워진 신호
       """
   ```

3. ✅ Markdown 보고서 생성
   ```python
   def generate_gap_filling_report(results: Dict,
                                  output_dir: Path) -> Path:
       """
       보고서 섹션:
       - 요약
       - Gap별 분석
       - 품질 메트릭 테이블
       - 시각화
       - 권장사항
       """
   ```

#### 산출물:
- [ ] 메트릭 계산 함수
- [ ] 시각화 함수 (matplotlib)
- [ ] Markdown 보고서 생성기

---

### 5.5 Phase 5: 메인 워크플로우 통합
**예상 시간**: 45분

#### 작업:
1. ✅ 명령줄 인터페이스
   ```bash
   python src/main41_fill_pressure_gaps.py \
       --areas 0480 0490 \
       --method spectral \
       --output-dir results/main41_gap_filling \
       --visualize
   ```

2. ✅ 메인 처리 루프
   ```python
   def main(areas: List[str] = None,
           method: str = 'spectral',
           output_dir: Path = None,
           visualize: bool = True) -> None:
       """
       메인 워크플로우:
       1. main40 품질 보고서 로드
       2. filling이 필요한 지역 필터링
       3. 각 지역에 대해:
          - 데이터 로드
          - Gap 탐지
          - Gap filling 적용
          - 검증
          - 결과 저장
          - 메트릭 생성
       4. 요약 보고서 생성
       """
   ```

3. ✅ 기존 파이프라인과 통합
   - main40 품질 보고서를 읽어 지역 식별
   - 결측 <1% 지역 건너뛰기
   - main51용 호환 형식으로 채워진 데이터 저장

#### 산출물:
- [ ] 완성된 main41 스크립트
- [ ] 4개 옵션이 있는 CLI
- [ ] 통합 테스트

---

## 🎨 6. 출력 사양

### 6.1 채워진 데이터 CSV 형식
```csv
# Gap Filling 메타데이터
# 원본 파일: 0480 소구역 압력 데이터.csv
# 채워진 Gap: 1
# Gap 1: 2025-05-19 13:40 ~ 2025-06-12 14:40 (6925 포인트)
# 방법: Spectral Gap Fill (ARMA + Random Phase)
# 처리: main41_fill_pressure_gaps.py
# 일시: 2025-12-12 14:30:00
manage_id,msrmt_dt,wtrprsr
235,2022-08-20 00:05:00.000000,1.90
...
```

### 6.2 품질 메트릭 JSON
```json
{
  "area": "0480",
  "total_gaps_filled": 1,
  "gaps": [
    {
      "gap_id": 1,
      "start_time": "2025-05-19 13:40:00",
      "end_time": "2025-06-12 14:40:00",
      "duration_days": 24.04,
      "points_filled": 6925,
      "method": "spectral",
      "low_freq": {
        "method": "ARMA",
        "order": [10, 10],
        "fit_status": "fallback_linear",
        "variance_before": 0.18,
        "variance_after": 0.72,
        "variance_ratio": 4.0
      },
      "high_freq": {
        "method": "random_phase",
        "reference_length": 10080,
        "variance_before": 0.009,
        "variance_after": 0.009,
        "variance_ratio": 1.0
      },
      "validation": {
        "edge_continuity_left": 0.05,
        "edge_continuity_right": 0.03,
        "no_new_nans": true,
        "time_series_valid": true
      }
    }
  ],
  "timestamp": "2025-12-12T14:30:00"
}
```

### 6.3 Markdown 보고서
```markdown
# 압력 데이터 Gap Filling 보고서

**생성 일시**: 2025-12-12 14:30:00

---

## 1. 요약

### 처리 개요
- **처리 지역**: 0480, 0490 (2/6 지역)
- **건너뛴 지역**: 0243, 0461, 0470, 0520 (결측률 <1%)
- **총 Gap 수**: 2개
- **처리 방법**: Spectral Gap Fill (ARMA + Random Phase)

### 주요 결과
- ✅ 0480: 1개 Gap 처리 완료 (24일, 6,925 포인트)
- ✅ 0490: 1개 Gap 처리 완료 (24일, 6,926 포인트)

---

## 2. Gap 상세 분석

### 0480 지역

| 항목 | 값 |
|------|-----|
| Gap 시작 | 2025-05-19 13:40 |
| Gap 종료 | 2025-06-12 14:40 |
| 지속 시간 | 24.04일 (577.0시간) |
| 채운 포인트 | 6,925개 |

**성분별 처리**:
- 저주파: ARMA(10,10) → Linear Fallback (⚠️ 장기 Gap으로 인한 Fallback)
- 고주파: Random Phase IFFT (✅ 정상 처리)

**품질 지표**:
- 저주파 분산 비율: 4.0 (⚠️ 예상치보다 높음 - ARMA fallback 영향)
- 고주파 분산 비율: 1.0 (✅ 양호)
- Edge 연속성: 좌측 0.05, 우측 0.03 (✅ 양호)

![0480 Gap 비교](visualizations/0480_gap_comparison.png)

---

## 3. 권장 사항

### 0480, 0490 지역
- ⚠️ **주의**: 24일 장기 Gap으로 저주파 성분이 선형 보간됨
- ✅ **사용 가능**: 고주파 성분은 정상 처리, 피로 분석 진행 가능
- 💡 **권장**: main51-57 피로 분석 시 해당 기간 결과에 대한 신뢰도 검토

### 다음 단계
1. main51_find_freq.py 실행하여 주파수 분석
2. main52-57로 피로 분석 진행
3. 0480, 0490 지역의 2025년 5-6월 피로 분석 결과 별도 검토

---

**보고서 종료**
```

---

## ⚙️ 7. 구성 및 파라미터

### 7.1 기본 파라미터 (config.py)
```python
# Gap Filling 파라미터
GAP_FILL_V_VALLEY_MINUTES = 553.5  # main51 기준
GAP_FILL_BUTTERWORTH_ORDER = 4
GAP_FILL_ARMA_ORDER = (10, 10)
GAP_FILL_LOW_FREQ_EDGE_WINDOW = 60
GAP_FILL_HIGH_FREQ_EDGE_WINDOW = 20
GAP_FILL_REFERENCE_LENGTH = 10080  # 5분 간격으로 7일

# 임계값
GAP_FILL_MIN_GAP_HOURS = 1.0  # 1시간 이상 gap 처리
GAP_FILL_SKIP_MISSING_RATIO = 1.0  # <1% 결측 지역 건너뛰기
```

### 7.2 명령줄 인자
```python
parser.add_argument('--areas', nargs='+', help='처리할 지역 코드 (기본: main40에서 자동)')
parser.add_argument('--method', default='spectral', choices=['spectral', 'linear'], help='Gap filling 방법')
parser.add_argument('--output-dir', type=Path, default=None, help='출력 디렉토리')
parser.add_argument('--visualize', action='store_true', help='시각화 플롯 생성')
parser.add_argument('--skip-threshold', type=float, default=1.0, help='결측률 < 임계값(%)이면 건너뛰기')
parser.add_argument('--main40-report', type=Path, help='main40 품질 보고서 경로')
```

---

## 🧪 8. 테스트 전략

### 8.1 단위 테스트
```python
# tests/test_gap_fill_utils.py
def test_butterworth_separation()
def test_arma_synthesis()
def test_random_phase_synthesis()
def test_edge_smoothing()
def test_gap_detection()
def test_validation_checks()
```

### 8.2 통합 테스트
```python
# tests/test_main41_integration.py
def test_process_single_area()
def test_skip_low_missing_areas()
def test_output_format_compatibility()
def test_main40_integration()
def test_main51_compatibility()
```

### 8.3 검증 테스트
- 0243으로 테스트 (gap 없음) → 건너뛰어야 함
- 합성 7일 gap으로 테스트 → 메트릭 검증
- 0480 실제 데이터로 테스트 → Project 014 결과와 비교

---

## 📅 9. 구현 일정

| 단계 | 작업 | 시간 | 의존성 |
|------|-----|------|--------|
| **Phase 1** | 설정 및 준비 | 30분 | - |
| **Phase 2** | 핵심 로직 | 1시간 | Phase 1 |
| **Phase 3** | 데이터 I/O | 45분 | Phase 2 |
| **Phase 4** | 메트릭 및 시각화 | 1시간 | Phase 3 |
| **Phase 5** | 통합 | 45분 | Phase 4 |
| **테스트** | 단위 + 통합 | 1시간 | Phase 5 |
| **합계** | **5시간** | | |

---

## ⚠️ 10. 알려진 제한사항 및 위험

### 10.1 기술적 제한사항
1. **ARMA Fallback**: 24일 gap은 저주파에 선형 보간 사용
   - **영향**: 저주파 에너지 ~4배 증가
   - **완화**: 보고서에 문서화, 검토 플래그

2. **Random Phase CCR**: ~0.78 vs 목표 0.95
   - **영향**: Rainflow 사이클 수가 다를 수 있음
   - **완화**: 고주파가 전체 분산의 5%만 차지하므로 허용 가능

3. **Edge 불연속성**: gap 경계에서 작은 점프 가능
   - **영향**: 피로 분석에 최소 영향
   - **완화**: 코사인 테이퍼링으로 Edge 스무딩

### 10.2 데이터 위험
1. **새로운 gap**: 스크립트가 정적 main40 보고서를 가정
   - **완화**: 타임스탬프 확인 추가, 데이터 변경 시 경고

2. **인코딩 문제**: 파일명의 한글 문자
   - **완화**: unicodedata.normalize 사용 (이미 main40에 있음)

### 10.3 성능 위험
1. **메모리**: 대용량 데이터셋은 청킹 필요
   - **완화**: 지역을 병렬이 아닌 순차적으로 처리

2. **계산 시간**: ARMA fitting이 느릴 수 있음
   - **완화**: 합리적인 타임아웃 설정, 선형으로 fallback

---

## 📚 11. 참고자료 및 의존성

### 11.1 관련 스크립트
- **main40_analyze_pressure_gaps.py**: 데이터 품질 분석
- **main51_find_freq.py**: 주파수 분석 (V-valley 사용)
- **main52_pass_filter.py**: Butterworth 필터링
- **[Gap Interpolation 연구 프로젝트](GAP_INTERPOLATION_RESEARCH.md)**: tmp/007~014 연구 결과 종합 (XGBoost, Prophet, LSTM, Spectral 등 8개 프로젝트)

### 11.2 Python 의존성
```python
# 필수 패키지
pandas>=1.5.0
numpy>=1.23.0
scipy>=1.9.0
matplotlib>=3.5.0
statsmodels>=0.13.0  # ARMA용
xgboost>=1.7.0       # XGBoost 보간용
```

### 11.3 내부 의존성
```python
from src.common.config import get_config
from src.common.file_utils import ensure_directory_exists, validate_file_exists
from src.common.logging_utils import setup_logging, log_execution_time
from src.common.validation import validate_date_format, validate_required_columns
from src.common.visualization_utils import setup_korean_font, setup_plot_style
from src.common.gap_fill_utils import spectral_gap_fill  # 새 모듈
```

---

## ✅ 12. 성공 기준 체크리스트

### 기능 요구사항
- [ ] main40 로직으로 gap 탐지
- [ ] spectral gap filling 적용 (ARMA + Random Phase)
- [ ] 채워진 데이터 검증 (새 NaN 없음, 연속성)
- [ ] 원본 형식으로 채워진 데이터 저장
- [ ] 품질 메트릭 JSON 생성
- [ ] 시각화 생성 (전/후 플롯)
- [ ] Markdown 보고서 생성

### 품질 요구사항
- [ ] CODING_STANDARDS.md 준수
- [ ] 포괄적인 docstring
- [ ] 단위 테스트 커버리지 >80%
- [ ] 통합 테스트 통과
- [ ] 플롯에서 한글 폰트 지원
- [ ] 모든 edge case에 대한 오류 처리

### 통합 요구사항
- [ ] main40 출력과 호환
- [ ] main51이 읽을 수 있는 출력
- [ ] config.py 상수 사용
- [ ] logging_utils를 통한 로깅
- [ ] results/main41_gap_filling/에 결과 저장

### 문서화 요구사항
- [ ] 함수 docstring (Google 스타일)
- [ ] CLI 도움말 메시지
- [ ] docs/에 README 섹션
- [ ] 복잡한 로직에 인라인 주석
- [ ] 생성된 보고서가 사람이 읽기 쉬움

---

## 🚀 13. 구현 후 다음 단계

1. **즉시**:
   - 0480, 0490에 실행하여 중요 gap 채우기
   - 생성된 보고서 검토
   - main51로 출력 검증

2. **단기**:
   - docs/INDEX.md에 main41 항목 업데이트
   - 자동화된 테스트 스위트에 추가
   - docs/에 튜토리얼 생성

3. **장기**:
   - 채워진 기간의 피로 분석 결과 모니터링
   - Project 014 STEP 3/4의 개선된 방법 구현 고려
   - 대체 filling 방법을 위한 main42 생성 가능 (XGBoost, Prophet)

---

## 📝 14. 파일 경로 참조

```
입력:
  - /Users/jhpark/development/eroumtech/fatigue/fatigue-qgis/data/raw/0480 소구역 압력 데이터.csv
  - /Users/jhpark/development/eroumtech/fatigue/fatigue-qgis/data/raw/0490 소구역 압력 데이터.csv
  - /Users/jhpark/development/eroumtech/fatigue/fatigue-qgis/results/main40_data_quality/data_quality_report.md

출력:
  - results/main41_gap_filling/filled_data/0480_filled.csv
  - results/main41_gap_filling/filled_data/0490_filled.csv
  - results/main41_gap_filling/quality_metrics/0480_metrics.json
  - results/main41_gap_filling/quality_metrics/0490_metrics.json
  - results/main41_gap_filling/visualizations/0480_gap_comparison.png
  - results/main41_gap_filling/visualizations/0490_gap_comparison.png
  - results/main41_gap_filling/gap_filling_report.md
  - results/main41_gap_filling/main41.log
```

---

**계획 버전**: 1.0
**생성일**: 2025-12-12
**작성자**: Claude AI Assistant
**예상 구현 시간**: 5시간
**우선순위**: 높음 (0480, 0490 피로 분석 차단)
**복잡도**: 중간 (검증된 Project 014 코드 재사용)