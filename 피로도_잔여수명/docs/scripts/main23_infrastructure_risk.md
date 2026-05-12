# main23: 인프라 위험도

**파일명**: `main23_infrastructure_risk.py`

## 📋 개요
인프라 밀도와 재작업 위험도의 관계를 분석합니다.

## 🚀 사용법

```bash
python src/main23_infrastructure_risk.py
```

## 📥 입력 파일

### 피로 손상 데이터
- `results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv` - PIPE_LM 피로 손상 데이터
  - K-factors 및 D_final 값 포함
  - 지역별(0243, 0461, 0470, 0480, 0490, 0520) 피로 분석 결과
- `results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv` - SPLY_LS 피로 손상 데이터
  - K-factors 및 D_final 값 포함
  - 지역별 피로 분석 결과

### GIS 데이터
- `data/raw/export_shp_*/` - GIS shapefile 데이터

## 📤 출력 파일
- `results/spatial_analysis/infrastructure_risk/`

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main23_infrastructure_risk_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main22*.py`](main22*.md)
- 다음: [`main23a*.py`](main23a*.md)
