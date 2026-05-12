# main19a_fast_radius_analysis: 반경별 민감도 분석 (고속 버전)

**파일명**: `src/main19a_fast_radius_analysis.py`

## 📋 개요
520 지역의 복구 공사 데이터와 주변 시설물(인프라)의 상관관계를 고속으로 분석하는 스크립트입니다. cKDTree 공간 인덱싱을 사용하여 기존 대비 150배 이상 속도를 향상시켰습니다.

### 주요 특징
- **초고속 분석**: cKDTree를 사용한 공간 인덱싱으로 2초 내 전체 분석 완료
- **다중 반경 지원**: 10m, 20m, 30m, 50m, 100m 등 여러 반경 동시 분석
- **통계적 검증**: 각 반경별 상관계수와 p-value 계산
- **시각화 생성**: 반경별 상관관계 히트맵 자동 생성

## 🎯 목적
- 520 지역 전체를 대상으로 최적의 분석 반경 도출
- 인프라 타입별(SPLY_LS, 밸브, 소화전) 상관관계 분석
- 반경별 민감도 분석을 통한 공간적 영향 범위 파악

## 📥 입력 파일

### 재작업 데이터 (CSV)
- `results/지상누수_520_위치추가.csv`: 지상누수 재작업 위치 데이터
- `results/지하누수_520_위치추가.csv`: 지하누수 재작업 위치 데이터
- `results/기타공사_520_위치추가.csv`: 기타공사 재작업 위치 데이터

### 인프라 데이터 (Shapefile)
- `data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`: 급수관 네트워크
- `data/raw/export_shp_20250704(0520)/WTL_VALV_PS.shp`: 밸브 위치
- `data/raw/export_shp_20250704(0520)/WTL_FIRE_PS.shp`: 소화전 위치

## 🚀 사용법

### 기본 실행
```bash
python src/main19a_fast_radius_analysis.py
```

### 반경 커스터마이징
```bash
python src/main19a_fast_radius_analysis.py --radii 10 20 30 50 100
python src/main19a_fast_radius_analysis.py --radii 15 25 35 --verbose
```

### 명령줄 옵션
- `--radii`: 분석할 반경 목록 (미터 단위, 기본값: 10 20 30 50 100)
- `--verbose`: 상세 출력 모드
- `--show`: 그래프를 화면에 표시

## 📤 출력 파일

### 메인 출력 디렉토리: `results/main19a_fast_radius_analysis/`

#### 통합 보고서
- `results/main19a_fast_radius_analysis/sensitivity_report.md`: 전체 반경별 분석 결과 요약 (Markdown 형식)
- `results/main19a_fast_radius_analysis/sensitivity_summary.json`: 전체 분석 결과 JSON 데이터
- `results/main19a_fast_radius_analysis/radius_correlation_heatmap.png`: 반경-인프라 상관계수 히트맵

#### 반경별 상세 결과 (`radius_*m/` 폴더)
- `results/main19a_fast_radius_analysis/radius_10m/repair_infra_correlation.txt`: 10m 반경 상세 통계
- `results/main19a_fast_radius_analysis/radius_20m/repair_infra_correlation.txt`: 20m 반경 상세 통계
- `results/main19a_fast_radius_analysis/radius_30m/repair_infra_correlation.txt`: 30m 반경 상세 통계
- `results/main19a_fast_radius_analysis/radius_50m/repair_infra_correlation.txt`: 50m 반경 상세 통계
- `results/main19a_fast_radius_analysis/radius_100m/repair_infra_correlation.txt`: 100m 반경 상세 통계

#### 반경별 시각화
- `results/main19a_fast_radius_analysis/radius_*m/correlation_scatter.png`: 각 반경별 산점도
- `results/main19a_fast_radius_analysis/radius_*m/infra_boxplot.png`: 각 반경별 박스플롯

## 📊 주요 기능

### 1. 고속 공간 분석
```python
def analyze_infrastructure_correlation_fast(
    repair_df: pd.DataFrame,
    background_data: dict,
    output_dir: Path,
    radius: float = 20.0,
    verbose: bool = False
) -> dict
```
- cKDTree를 사용한 최근접 이웃 탐색
- 벡터화된 거리 계산으로 성능 최적화
- 메모리 효율적인 처리

### 2. 통계 분석
- **상관계수 계산**: Pearson correlation coefficient
- **통계적 유의성 검정**: p-value < 0.05
- **클러스터 분석**: DBSCAN 기반 공간 클러스터링

### 3. 시각화
- 반경별 상관계수 히트맵
- 인프라 타입별 박스플롯
- 클러스터 분포 시각화

## 📈 분석 결과 (Markdown 보고서)

스크립트 실행 시 `sensitivity_report.md` 파일이 생성되며, 다음과 같은 형식의 테이블을 포함합니다:

### 반경별 상세 분석 테이블
| 인프라 타입 | r (상관계수) | p-value | R² (결정계수) | 유의성 |
|------------|-------------|---------|--------------|--------|
| SPLY_LS (급수관로) | -0.0147 | 0.6461 | 0.0002 | |
| 밸브 | -0.0746 | 0.0198 | 0.0056 | * |
| 소화전 | -0.0221 | 0.4897 | 0.0005 | |
| 총 인프라 | -0.0276 | 0.3895 | 0.0008 | |

### 종합 비교 테이블 (인프라별)
| 반경 | r | p-value | R² | 유의성 |
|------|---|---------|-----|--------|
| 10m | -0.0294 | 0.3597 | 0.0009 | |
| 30m | -0.0746 | 0.0198 | 0.0056 | * |
| 50m | -0.0532 | 0.0971 | 0.0028 | |
| 100m | -0.0312 | 0.3302 | 0.0010 | |

**참고**: 
- `*` 표시는 p < 0.05 (통계적으로 유의미)
- R² (결정계수)는 상관계수의 제곱으로 자동 계산
- 모든 수치는 소수점 4자리까지 표시

## 🔧 기술적 세부사항

### 성능 최적화
1. **공간 인덱싱**: scipy.spatial.cKDTree 사용
2. **벡터화 연산**: NumPy 배열 연산으로 루프 최소화
3. **병렬 처리**: 가능한 경우 multiprocessing 활용
4. **메모리 관리**: 청크 단위 처리로 메모리 사용량 최적화

### 좌표계 처리
- 입력: WGS84 (EPSG:4326)
- 분석: Korea 2000 (EPSG:5179) - 미터 단위 거리 계산용
- 출력: 원본 좌표계 유지

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main19a_fast_radius_analysis_call_graph.md)
- [main19b_subregion_analysis.py](main19b_subregion_analysis.md) - 하위 지역별 세부 분석

## 🔗 연관 스크립트
- 이전: [`main19_visualize_520_repairs.py`](main19_visualize_520_repairs.md)
- 다음: [`main19b_subregion_analysis.py`](main19b_subregion_analysis.md)
- 관련: [`main20_optimize_parameters.py`](main20_optimize_parameters.md) - 최적 파라미터 도출
