# main22: 핫스팟 분석

**파일명**: `main22_spatial_hotspots.py`

## 📋 개요
Getis-Ord Gi* 통계로 재작업 집중 지역을 식별합니다.

## 🚀 사용법

```bash
python src/main22_spatial_hotspots.py
python src/main22_spatial_hotspots.py --grid-size 30
python src/main22_spatial_hotspots.py --use-optimal
```

## 📥 입력 파일
- `results/지상누수_520_위치추가.csv`: 지상누수 재작업 위치
- `results/지하누수_520_위치추가.csv`: 지하누수 재작업 위치
- `results/기타공사_520_위치추가.csv`: 기타공사 재작업 위치
- `results/spatial_analysis/optimal_parameters.json`: 최적 파라미터 (--use-optimal 사용시)
- 60m × 60m 그리드

## 📤 출력 파일
- `results/spatial_analysis/hotspots/hotspot_results.csv`: 핫스팟 데이터
- `results/spatial_analysis/hotspots/hotspot_results.geojson`: GIS 형식
- `results/spatial_analysis/hotspots/hotspot_analysis.png`: 시각화
- `results/spatial_analysis/hotspots/hotspot_analysis_report.md`: 보고서

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main22_spatial_hotspots_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main21*.py`](main21*.md)
- 다음: [`main22a*.py`](main22a*.md)
