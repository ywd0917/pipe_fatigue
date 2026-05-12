# main19b_subregion_analysis: 하위 지역별 반경 민감도 분석

**파일명**: `src/main19b_subregion_analysis.py`

## 📋 개요
520 지역의 하위 지역(0470, 0480, 0490)별로 복구 공사와 인프라의 상관관계를 다양한 반경에서 분석하는 스크립트입니다. main19a_fast_radius_analysis.py의 고속 분석 함수를 활용하여 각 지역별 최적 반경을 도출합니다.

### 주요 특징
- **하위 지역 분리 분석**: 0470, 0480, 0490 각 지역별 독립적 분석
- **다중 반경 비교**: 10m, 20m, 30m, 50m, 100m 반경별 민감도 분석
- **통계적 유의성 평가**: p-value 기반 유의미성 매트릭스 생성
- **최적 반경 도출**: 지역별 최적 분석 반경 자동 계산
- **시각화 통합**: 히트맵, P-value 매트릭스 등 비교 시각화

## 🎯 목적
- 하위 지역별 인프라 영향 범위의 차이 파악
- 지역 특성에 맞는 최적 분석 반경 도출
- 통계적으로 유의미한 상관관계 식별
- 지역별 유지보수 전략 수립 지원

## 📥 입력 파일

### 재작업 데이터 (CSV)
- `results/지상누수_520_위치추가.csv`: 지상누수 재작업 위치 데이터
- `results/지하누수_520_위치추가.csv`: 지하누수 재작업 위치 데이터
- `results/기타공사_520_위치추가.csv`: 기타공사 재작업 위치 데이터

### 인프라 데이터 (Shapefile)
- `data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`: 급수관 네트워크
- `data/raw/export_shp_20250704(0520)/WTL_VALV_PS.shp`: 밸브 위치
- `data/raw/export_shp_20250704(0520)/WTL_FIRE_PS.shp`: 소화전 위치

### 지역 경계 데이터
- `data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp`: 하위 지역 경계 (0470, 0480, 0490)

## 🚀 사용법

### 기본 실행 (모든 하위 지역)
```bash
python src/main19b_subregion_analysis.py
```

### 특정 지역만 분석
```bash
python src/main19b_subregion_analysis.py --regions 0470 0480
python src/main19b_subregion_analysis.py --regions 0490
```

### 반경 커스터마이징
```bash
python src/main19b_subregion_analysis.py --radii 15 30 45 60
```

### 명령줄 옵션
- `--regions`: 분석할 지역 목록 (기본값: 0470 0480 0490)
- `--radii`: 분석할 반경 목록 (미터 단위, 기본값: 10 20 30 50 100)
- `--verbose`: 상세 출력 모드
- `--show`: 그래프를 화면에 표시

## 📤 출력 파일

### 메인 출력 디렉토리: `results/main19b_subregion_analysis/`

#### 통합 분석 결과 (`comparative_analysis/`)
- `results/main19b_subregion_analysis/comparative_analysis/all_results.json`: 전체 분석 결과 JSON
- `results/main19b_subregion_analysis/comparative_analysis/significance_matrix.csv`: 통계적 유의성 매트릭스
- `results/main19b_subregion_analysis/comparative_analysis/correlation_heatmap.png`: 지역별 상관계수 히트맵
- `results/main19b_subregion_analysis/comparative_analysis/pvalue_matrix.png`: P-value 시각화
- `results/main19b_subregion_analysis/comparative_analysis/optimal_radius_report.md`: 최적 반경 분석 보고서

#### 지역별 상세 결과
- `results/main19b_subregion_analysis/0470/statistical_summary_0470.json`: 0470 지역 통계 요약
- `results/main19b_subregion_analysis/0480/statistical_summary_0480.json`: 0480 지역 통계 요약
- `results/main19b_subregion_analysis/0490/statistical_summary_0490.json`: 0490 지역 통계 요약

#### 지역별 반경별 상세 결과
- `results/main19b_subregion_analysis/{region_code}/radius_{n}m/`: 각 지역의 반경별 상세 분석 결과
  - 예: `results/main19b_subregion_analysis/0470/radius_10m/`
  - 예: `results/main19b_subregion_analysis/0480/radius_30m/`
  - 예: `results/main19b_subregion_analysis/0490/radius_50m/`

## 📊 주요 기능

### 1. 하위 지역 데이터 필터링
```python
def load_subregion_data(region_code: str, verbose: bool = True) -> pd.DataFrame
```
- WEA_SMLZ_AS.shp를 사용한 지역 경계 추출
- 공간 조인으로 해당 지역 내 데이터만 필터링

### 2. 다중 반경 분석
```python
def analyze_single_combination(
    region_code: str,
    radius: float,
    repair_df: pd.DataFrame,
    background_data: dict,
    output_dir: Path,
    verbose: bool = False
) -> dict
```
- main19a_fast_radius_analysis.py의 고속 분석 함수 활용
- 각 반경별 통계 결과 수집

### 3. 최적 반경 도출
```python
def find_optimal_radius(results: dict) -> dict
```
- 유의미한 상관관계 개수와 강도 종합 평가
- 점수 = 유의미한 개수 × 평균 상관계수

### 4. 시각화 생성
- **상관계수 히트맵**: 3개 지역 × 5개 반경 × 4개 인프라 타입
- **P-value 매트릭스**: 유의성 수준 표시 (*, **, ***)
- **비교 분석 보고서**: Markdown 형식의 종합 보고서

## 📈 분석 결과 예시

### 지역별 최적 반경
```
0470 지역: 30m (점수: 0.021)
0480 지역: 20m (점수: 0.018)
0490 지역: 10m (점수: 0.164) ⭐
```

### 유의미한 상관관계 (0490 지역)
```
10m 반경:
  밸브: r=0.164, p=0.032 (유의미) ✓
  
100m 반경:
  SPLY_LS: r=0.138, p=0.048 (유의미) ✓
```

## 🔧 기술적 세부사항

### 지역 경계 처리
1. **부모 지역 식별**: get_parent_region() 함수로 520 확인
2. **경계 추출**: WEA_SMLZ_AS.shp에서 LABEL 필드로 필터링
3. **공간 조인**: GeoPandas sjoin으로 경계 내 데이터 추출

### 통계 분석 방법
- **상관계수**: Pearson correlation coefficient
- **유의성 검정**: p-value < 0.05를 유의미로 판정
- **종합 점수**: 유의미한 개수 × 평균 |상관계수|

### 성능 최적화
- main19a_fast_radius_analysis.py의 cKDTree 기반 고속 분석 함수 재사용
- 병렬 처리 가능한 구조로 설계
- 메모리 효율적인 청크 단위 처리

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main19b_subregion_analysis_call_graph.md)
- [main19a_fast_radius_analysis.py](main19a_fast_radius_analysis.md) - 고속 반경별 분석 핵심 모듈
- [하위 지역 반경 민감도 분석 결과](../subregion_radius_sensitivity_analysis.md)

## 🔗 연관 스크립트
- 이전: [`main19a_fast_radius_analysis.py`](main19a_fast_radius_analysis.md) - 전체 지역 고속 분석
- 다음: [`main20_optimize_parameters.py`](main20_optimize_parameters.md) - 공간 분석 파라미터 최적화
- 관련: [`main14a_subregion_repair.py`](main14a_subregion_repair.md) - 하위 지역 복구 분석
