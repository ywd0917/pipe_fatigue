# main18: 중복 위치 시간 분석

**파일명**: `main18_analyze_duplicate_repairs.py`

## 📋 개요
같은 위치에서 반복된 복구 작업을 시간적으로 분석합니다.

### 주요 분석 기능
- **중복 탐지**: 10m 반경 내 같은 위치의 작업들을 자동 그룹화
- **시간 분석**: 재작업 간격 계산 및 패턴 분석
- **작업 타입 전환**: 지상누수 → 지하누수 등 작업 타입 변화 추적
- **빈도 분석**: 4회 이상 반복 위치 특별 분석
- **우선순위 기반 날짜 처리**:
  - 기존 '작업일시' 컬럼 우선 사용
  - 없을 경우 접수일시 → 작업시작일시 → 작업종료일 순으로 사용
  - 민원 접수 시점을 우선하여 실제 문제 발생 시점 파악

### 날짜 처리 특징
- 숫자 형식 자동 인식: `202206230912.0` → `2022-06-23 09:12`
- 공통 함수 `parse_numeric_date_column()`으로 날짜 파싱 로직 일원화
- 모든 날짜를 '작업일시'라는 통일된 이름으로 저장하여 분석

## 🚀 사용법

```bash
# 기본 실행 (결과는 results/main18_duplicate_analysis/ 폴더에 저장)
python src/main18_analyze_duplicate_repairs.py

# 출력 디렉토리 지정
python src/main18_analyze_duplicate_repairs.py --output-dir path/to/output

# 최적화된 cKDTree 알고리즘 사용 (가장 빠름)
python src/main18_analyze_duplicate_repairs.py --algorithm ckdtree

# DBSCAN 클러스터링 사용
python src/main18_analyze_duplicate_repairs.py --algorithm dbscan

# 성능 벤치마크 실행
python src/main18_analyze_duplicate_repairs.py --benchmark
```

## 🎛️ 옵션
- `--output-dir`: 출력 디렉토리 경로 (기본값: `results/main18_duplicate_analysis/`)
- `--algorithm`: 사용할 알고리즘 선택 (기본값: `auto`)
  - `auto`: 자동 선택 (cKDTree 사용 가능시 자동 사용)
  - `ckdtree`: cKDTree 기반 공간 인덱싱 (최적화, 가장 빠름)
  - `dbscan`: DBSCAN 클러스터링 알고리즘
  - `grid`: 그리드 기반 알고리즘
  - `simple`: 단순 알고리즘 (작은 데이터용)
- `--benchmark`: 성능 벤치마크 모드 (여러 알고리즘 비교)

## 📥 입력 파일
- `results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv`: 통합 복구 작업 데이터
  - 지상누수, 지하누수, 긴급공사, 관리대장 데이터 포함
  - `파일타입` 컬럼으로 작업 유형 구분

### 필수 컬럼
- `위도`, `경도`: 작업 위치
- `파일타입`: 작업 유형 (지상누수, 지하누수, 긴급공사, 관리대장)
- 날짜 관련 컬럼 중 하나 이상:
  - `작업일시` (우선순위 1)
  - `접수일시` (우선순위 2)
  - `작업시작일시` (우선순위 3)
  - `작업종료일` (우선순위 4)

## 📤 출력 파일
모든 파일은 `results/main18_duplicate_analysis/` 폴더에 저장됩니다.

### 데이터 파일
- `duplicate_repairs_analysis.csv`: 중복 그룹별 상세 정보
  - cluster_id: 그룹 번호
  - cluster_size: 그룹 내 작업 수
  - repair_id, 작업타입, 작업일시, 주소, 위도, 경도
- `duplicate_summary.csv`: 전체 요약 통계
- `duplicate_cluster_intervals.csv`: 클러스터별 평균 재작업 간격
  - 평균/최소/최대 간격, 작업타입 패턴, 대표 주소
- `duplicate_interval_distribution.csv`: 시간 간격 분포 테이블

### 보고서 파일
- `duplicate_statistics.txt`: 상세 통계 보고서
- `duplicate_4plus_statistics.txt`: 4회 이상 중복 위치 특별 보고서

### 시각화 파일
- `duplicate_repair_counts_pie.png`: 재작업 횟수별 비중 파이 차트
- `duplicate_interval_histogram.png`: 재작업 간격 히스토그램
- `duplicate_cluster_interval_histogram.png`: 클러스터별 평균 간격 히스토그램

## ✨ 주요 기능

### 1. 중복 위치 탐지
- Haversine 공식으로 정확한 거리 계산
- 10m 반경 내 작업들을 하나의 클러스터로 그룹화
- 각 클러스터의 크기(작업 횟수) 및 기간 분석

### 2. 시간 간격 분석
- 같은 위치의 연속된 작업 간 날짜 차이 계산
- 예: 2020-01-01 접수 후 2020-02-01 재접수 → 간격 31일
- 평균 재작업 간격으로 해당 위치의 문제 심각도 판단

### 3. 작업 타입 패턴 분석
- 작업 타입 전환 패턴 추적 (예: 지상누수 → 지하누수 → 긴급공사)
- 타입별 재작업 비율 계산
- 동일 타입 반복 vs 다른 타입 전환 비율

### 4. 통계 분석
- 전체 중복 비율
- 평균/중앙값/최소/최대 재작업 간격
- 30일/3개월/6개월/1년 이내 재작업 비율
- 구군별 중복 분포

### 5. 4회 이상 중복 특별 분석
- MIN_CLUSTER_SIZE_FOR_ANALYSIS = 4
- 빈번한 재작업 위치 식별
- 별도 보고서 및 통계 생성

## 🔧 설정 가능한 상수
```python
DISTANCE_THRESHOLD = 10.0  # 중복 판단 거리 (미터)
MIN_TIME_INTERVAL_DAYS = 30  # 의미있는 재공사 최소 간격 (일)
MIN_CLUSTER_SIZE_FOR_ANALYSIS = 4  # 상세 분석 대상 최소 중복 횟수
```

## 📊 출력 예시

### 통계 보고서 내용
```
===== 복구 작업 중복 위치 분석 보고서 =====

[기본 정보]
- 총 복구 작업: 92,611건
- 중복 위치 그룹: 15,823개
- 중복에 해당하는 복구 작업: 44,712건 (48.3%)

[시간 간격 분석]
- 평균 재작업 간격: 178.5일
- 중앙값: 89일
- 30일 이내 재작업: 2,134건 (15.2%)
- 3개월 이내: 5,678건 (40.5%)
- 6개월 이내: 8,234건 (58.7%)
```

## 🚀 성능 최적화

### cKDTree 기반 최적화 (2024-08-31)
- **기존 문제**: O(n²) 복잡도로 90,000개 이상 데이터 처리 시 2분 이상 소요
- **해결 방법**: 
  - scipy.spatial.cKDTree를 사용한 공간 인덱싱
  - 좌표계 변환 (WGS84 → EPSG:5179)으로 정확한 미터 단위 거리 계산
  - DBSCAN 알고리즘 옵션 추가 (병렬 처리 지원)
- **성능 개선**: 
  - 92,722개 데이터를 **0.8초**에 처리 (약 150배 향상)
  - 시간 복잡도: O(n²) → O(n log n)

### 알고리즘별 성능 비교
| 알고리즘 | 데이터 크기 | 실행 시간 | 속도 향상 |
|---------|------------|----------|----------|
| 그리드 기반 | 92,722개 | 120초+ | 1x |
| cKDTree | 92,722개 | 0.81초 | 148x |
| DBSCAN | 92,722개 | 0.75초 | 160x |

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main18_analyze_duplicate_repairs_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main17*.py`](main17*.md) - 피로도 분석
- 다음: [`main18a*.py`](main18a*.md)
- 관련: [`main19*.py`](main19*.md) - 520 지역 시각화