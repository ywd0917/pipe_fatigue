# analyze13_short_pipes: 1미터 미만 파이프 분석

**파일명**: `analyze13_short_pipes.py`

## 📋 개요
PIPE_LM과 SPLY_LS에서 길이가 1미터 미만인 파이프들을 조사하고 상세한 길이 분포 통계를 생성하는 분석 스크립트입니다.

## 🎯 목적
- **데이터 품질 검증**: 비정상적으로 짧은 파이프 식별
- **길이 분포 분석**: 0.1m 단위 상세 구간별 분포 파악
- **비교 분석**: PIPE_LM과 SPLY_LS 간 패턴 차이 분석
- **이상 데이터 탐지**: 0 길이 또는 극단적으로 짧은 파이프 플래그

## 🚀 사용법

### 기본 실행
```bash
# 기본 분석 (요약 보고서만)
python src/analysis/analyze13_short_pipes.py

# 모든 옵션 활성화
python src/analysis/analyze13_short_pipes.py \
  --export-csv \
  --visualize \
  --verbose \
  --output-dir results/custom_short_pipes
```

### 명령줄 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--output-dir` | Path | `results/analyze13_short_pipes` | 출력 디렉토리 |
| `--export-csv` | flag | `False` | 짧은 파이프 목록을 CSV로 내보내기 |
| `--visualize` | flag | `False` | 시각화 이미지 생성 |
| `--verbose` | flag | `False` | 상세 진행 상황 출력 |

## 📥 입력 데이터

### 데이터 소스
- `data/raw/export_shp_*0520*/V_WTL_PIPE_LM.shp`: PIPE_LM shapefile
- `data/raw/export_shp_*0520*/V_WTL_SPLY_LS.shp`: SPLY_LS shapefile

### 필수 컬럼
- `FTR_IDN`: 파이프 식별자
- `geometry`: LineString geometry (길이 계산용)

### 좌표계 요구사항
- **입력**: 자동으로 EPSG:5179로 변환
- **길이 계산**: EPSG:5179 투영 좌표계 기준 (미터 단위)

## 📤 출력 구조

```
results/analyze13_short_pipes/
├── short_pipes_summary.md          # 📊 요약 통계 보고서
├── pipe_lm_short_pipes.csv        # 📄 PIPE_LM 1m 미만 목록 (--export-csv 시)
├── sply_ls_short_pipes.csv        # 📄 SPLY_LS 1m 미만 목록 (--export-csv 시)
├── length_distribution.png        # 📈 길이 분포 히스토그램 (--visualize 시)
├── comparison_boxplot.png         # 📊 비교 박스플롯 (--visualize 시)
└── cumulative_distribution.png    # 📉 누적 분포 함수 (--visualize 시)
```

## 📊 분석 기준

### 길이 임계값
- **주요 분석**: 길이 < 1.0m
- **극단 케이스**: 길이 < 0.05m (5cm 미만)
- **이상 데이터**: 길이 = 0m

### 구간 설정
- **구간 크기**: 0.1m 단위
- **구간 수**: 10개 (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
- **경계값 처리**: include_lowest=True (0.0 포함)

## 📈 출력 예시

### 요약 통계 보고서 (short_pipes_summary.md)
```markdown
# 1미터 미만 파이프 분석 결과

## 📊 PIPE_LM 통계
- **전체 파이프**: 980개
- **1m 미만 파이프**: 45개 (4.59%)
- **평균 길이**: 0.623m
- **중간값**: 0.654m
- **최소/최대**: 0.028m / 0.998m
- **표준편차**: 0.287m
- **0 길이**: 0개
- **극단적으로 짧음** (< 0.05m): 2개

### 길이 구간별 분포
| 구간 (m) | 개수 | 비율 (%) |
|----------|------|----------|
| 0.0-0.1  | 3    | 6.7      |
| 0.1-0.2  | 2    | 4.4      |
| 0.2-0.3  | 4    | 8.9      |
| ...      | ...  | ...      |
```

### CSV 출력 (pipe_lm_short_pipes.csv)
```csv
FTR_IDN,pipe_length
P001234,0.0876
P005678,0.1234
P009012,0.2345
...
```

## 🎨 시각화 출력

### 1. 길이 분포 히스토그램 (length_distribution.png)
- **구조**: 2개 서브플롯 (PIPE_LM, SPLY_LS)
- **x축**: 파이프 길이 (m)
- **y축**: 개수
- **구간**: 0.1m 단위
- **색상**: PIPE_LM (파란색), SPLY_LS (주황색)

### 2. 비교 박스플롯 (comparison_boxplot.png)
- **비교 대상**: PIPE_LM vs SPLY_LS
- **통계**: 사분위수, 이상치 표시
- **색상**: PIPE_LM (연한 파란색), SPLY_LS (연한 빨간색)

### 3. 누적 분포 함수 (cumulative_distribution.png)
- **x축**: 파이프 길이 (m)
- **y축**: 누적 확률 (0-1)
- **용도**: 분포 패턴 비교 분석

## 🔍 해석 가이드

### 통계 지표 의미
- **1m 미만 비율**: 전체 파이프 중 짧은 파이프 비율 → 데이터 품질 지표
- **평균 길이**: 짧은 파이프들의 평균적인 길이
- **극단적으로 짧은 파이프**: 측정 오류 가능성이 높은 파이프

### 주의 깊게 봐야 할 케이스
1. **0 길이 파이프**: 확실한 데이터 오류 → 즉시 수정 필요
2. **0.05m 미만**: 실제로는 더 긴 파이프일 가능성 → 현장 확인 권장
3. **특정 구간 집중**: 측정 장비나 방법론의 체계적 오류 가능성

### 비교 분석 해석
- **PIPE_LM vs SPLY_LS 비율 차이**: 파이프 종류별 특성 또는 측정 방식 차이
- **분포 패턴 차이**: 설치 환경이나 용도의 차이 반영
- **극값 차이**: 데이터 품질 수준 차이

## ⚡ 성능 및 제약사항

### 처리 성능
- **PIPE_LM (980개)**: ~5초
- **SPLY_LS (3,599개)**: ~15초
- **메모리 사용량**: ~100MB (시각화 포함)

### 제약사항
- **좌표계 의존**: EPSG:5179 변환 필요 (자동 처리)
- **geometry 의존**: 유효한 LineString geometry 필요
- **FTR_IDN 필수**: 파이프 식별을 위한 필수 컬럼

### 에러 처리
- **파일 없음**: 우아한 실패 및 오류 메시지
- **잘못된 geometry**: 0 길이로 처리하고 플래그
- **메모리 부족**: 시각화 옵션 비활성화 권장

## 💡 실제 활용 사례

### 1. 데이터 품질 검증
```bash
# 기본 검증
python src/analysis/analyze13_short_pipes.py --verbose
```
**결과 활용**: 
- 0 길이 파이프 → GIS 데이터 수정
- 극단적으로 짧은 파이프 → 현장 재측정 목록 생성

### 2. 상세 분석
```bash
# 완전한 분석
python src/analysis/analyze13_short_pipes.py --export-csv --visualize
```
**결과 활용**:
- CSV → 현장 팀에 검증 요청 목록 제공
- 시각화 → 보고서 작성 및 패턴 분석

### 3. 정기 모니터링
```bash
# 스케줄 실행 (cron 등)
python src/analysis/analyze13_short_pipes.py --output-dir results/monthly_check/$(date +%Y%m)
```
**결과 활용**:
- 월별 데이터 품질 트렌드 모니터링
- 새로운 이상 데이터 조기 발견

## 🔗 관련 스크립트

### 선행 스크립트
- **main13a_calculate_k_repair.py**: shapefile 로드 함수 참조
- **src/analysis/analyze_pipe_segments.py**: 파이프 분석 패턴 참조

### 후속 활용 가능
- **main13f_visualize_high_k_repair.py**: 이상 파이프 시각화
- **데이터 정제 스크립트**: 식별된 이상 데이터 수정

## 🧪 테스트 및 검증

### 단위 테스트
```bash
pytest tests/analysis/test_analyze13_short_pipes.py -v
```

### 테스트 커버리지
- 15개 테스트 케이스
- 주요 함수 100% 커버리지
- 엣지 케이스 및 에러 조건 포함

### 검증 방법
1. **알려진 데이터셋**: 수동 계산 결과와 비교
2. **경계값 테스트**: 정확히 1.0m 파이프 제외 확인
3. **통계 정확도**: pandas 계산 결과와 대조

## 📝 문제 해결

### 자주 발생하는 문제

1. **"export 디렉토리를 찾을 수 없습니다"**
   ```bash
   # 해결: export_shp_*0520* 패턴의 디렉토리 존재 확인
   ls data/raw/export_shp_*
   ```

2. **"FTR_IDN 컬럼이 없습니다"**
   ```bash
   # 해결: shapefile 구조 확인
   ogrinfo -so data/raw/export_shp_*/V_WTL_PIPE_LM.shp V_WTL_PIPE_LM
   ```

3. **한글 깨짐**
   ```bash
   # 해결: 인코딩 확인 (자동으로 euc-kr 사용)
   python src/analysis/analyze13_short_pipes.py --verbose
   ```

### 디버깅 팁
- `--verbose` 옵션으로 상세 진행 상황 확인
- 로그 메시지를 통한 단계별 진행 추적
- 중간 결과를 CSV로 내보내서 수동 검증

---

최종 업데이트: 2025-01-03 (analyze13_short_pipes 구현)