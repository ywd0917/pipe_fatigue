# main9: 복구 작업 시각화

**파일명**: `main9_draw_recovery.py`

## 📋 개요
복구 작업 위치를 지도에 시각화합니다.

## 🚀 사용법

```bash
python src/main9_draw_recovery.py           # 전체 위치 표시
python src/main9_draw_recovery.py --separate  # 타입별 개별 이미지
python src/main9_draw_recovery.py --show    # 화면 표시
```

## 📤 출력 파일
- `results/all_recovery_locations.png`: 전체 통합
- `results/*_locations.png`: 타입별 개별 이미지

## ✨ 주요 기능
- 복구 작업 타입별 색상 구분
- MDLZ 배경 지도 표시
- 전체 또는 개별 타입별 시각화
- `data/repair/긴급복구.csv` - 원본 데이터에 좌표가 들어있다.

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main9_draw_recovery_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main8*.py`](main8*.md)
- 다음: [`main9a*.py`](main9a*.md)
