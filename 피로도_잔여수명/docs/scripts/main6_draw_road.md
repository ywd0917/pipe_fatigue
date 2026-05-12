# main6: 도로 네트워크 시각화

**파일명**: `main6_draw_road.py`

## 📋 개요
도로 네트워크와 교통량 데이터를 시각화합니다.

## 🚀 사용법

```bash
python src/main6_draw_road.py          # 이미지 파일만 생성
python src/main6_draw_road.py --show   # 화면에도 표시
python src/main6_draw_road.py --prefix "test_"  # 파일명 접두사
```

## 📥 입력 파일
- `data/raw/export_shp_*/도로*.shp`: 도로 네트워크 데이터

## 📤 출력 파일
- `results/road_network.png`: 전체 도로 네트워크
- `results/road_network_center.png`: 도로 중심선

## ✨ 주요 기능
- 모든 지역의 도로 네트워크 시각화
- 도로 중심선 별도 표시
- 교통량 데이터 색상 코딩

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main6_draw_road_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main5_match_K_soil.py`](main5_match_K_soil.md) - 파이프-토양 매칭
- 다음: [`main7_pipe_traffic.py`](main7_pipe_traffic.md) - 파이프-도로 중첩 분석