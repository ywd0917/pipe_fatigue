# main7: 파이프-도로 중첩 분석

**파일명**: `main7_pipe_traffic.py`

## 📋 개요
파이프라인과 도로의 공간적 중첩을 분석합니다.

## 🚀 사용법

```bash
python src/main7_pipe_traffic.py
python src/main7_pipe_traffic.py --output-dir results/traffic
python src/main7_pipe_traffic.py --quiet  # 최소 정보만 출력
```

## 📥 입력 파일
- `data/raw/export_shp_*/V_WTL_PIPE_LM.shp`: 파이프 데이터
- `data/raw/export_shp_*/V_WTL_SPLY_LS.shp`: 급수관 데이터
- `data/raw/export_shp_*/도로*.shp`: 도로 네트워크

## 📤 출력 파일
- `results/traffic/*_pipe_traffic.csv`: 파이프-도로 매칭 결과
- `results/traffic/*_sply_traffic.csv`: 급수관-도로 매칭 결과

## ✨ 주요 기능
- 파이프/급수관과 도로 네트워크 교차 분석
- 최소 거리 및 평균 교통량 계산
- 모든 export 디렉토리 자동 처리
- 버퍼 분석 (10m, 20m, 50m)

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main7_pipe_traffic_call_graph.md)
- [파이프-도로 중첩 분석](../pipe_road_overlap_analysis.md)

## 🔗 연관 스크립트
- 이전: [`main6_draw_road.py`](main6_draw_road.md) - 도로 네트워크 시각화
- 다음: [`main8_verify_overlap_samples.py`](main8_verify_overlap_samples.md) - 중첩 검증