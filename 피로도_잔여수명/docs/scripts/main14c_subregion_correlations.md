# main14c: 하위 지역별 K-factors 상관관계 분석

**파일명**: `main14c_subregion_correlations.py`

## 📋 개요
하위 지역별(0470, 0480, 0490) 재작업과 위험요인의 상관관계를 분석합니다. - **실행 시간**: 60-90초 → 0.16초 (**400-500배 향상**) - **최적화 기법**: scipy.spatial.cKDTree를 활용한 공간 인덱싱 - **시간 복잡도**: O(n×m) → O(n×log(m)) - **좌표계 통일**: EPSG:5179 (Korea 2000 / Central Belt 2010) 사용 - **공통 모듈 분리**: `main14_common` 모듈로 코드 중복 제거 - **거리 계산**: Haversine → Euclidean (투영 좌표계 활용) - **공통 모듈 사용**: main14b와 동일한 데이터 로더 및 분석 함수 - **오류 처리**: 상수 배열 처리 로직 추가

## 🚀 사용법

```bash
# 개별 지역 분석
python src/main14c_subregion_correlations.py --region 0470
python src/main14c_subregion_correlations.py --region 0480
python src/main14c_subregion_correlations.py --region 0490
# 모든 지역 분석 및 비교
```

## 📥 입력 파일
- `results/지상누수_520_위치추가.csv`: 지상누수 재작업 위치
- `results/지하누수_520_위치추가.csv`: 지하누수 재작업 위치
- `results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv`: 파이프 K-factors 및 D_final 데이터
- `results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv`: 급수관 K-factors 및 D_final 데이터
- `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`: 파이프 LineString geometry

## 📤 출력 파일
- `results/main14c/{지역}/repair_k_factors_matched.csv`
- `results/main14c/{지역}/correlation_analysis.txt`
- `results/main14c/{지역}/metadata.json`: 매칭 통계 메타데이터 (main14c2에서 사용)
- `results/main14c/{지역}/scatter_plot.png`
- `results/main14c/{지역}/boxplot.png`

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main14c_subregion_correlations_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main14b*.py`](main14b*.md)
- 다음: [`main14d*.py`](main14d*.md)
