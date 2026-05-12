# main20: 파라미터 최적화

**파일명**: `main20_optimize_parameters.py`

## 📋 개요
모든 공간분석 스크립트의 최적 파라미터를 자동으로 찾습니다. - Global Moran's I 최대화 - Ripley's K function - Knox test (시공간) - 교차 검증

## 🚀 사용법

```bash
python src/main20_optimize_parameters.py --method all
python src/main20_optimize_parameters.py --target main21
python src/main20_optimize_parameters.py --memory-limit 4
```

## 📤 출력 파일
- `results/spatial_analysis/optimal_parameters.json`

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main20_optimize_parameters_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main19*.py`](main19*.md)
- 다음: [`main20a*.py`](main20a*.md)
