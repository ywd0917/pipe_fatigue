# main9: 복구 작업 시각화

**파일명**: `main9_draw_repair.py`

## 📋 개요
data/repair 폴더의 누수공사 파일 작업 위치를 지도에 시각화합니다 (EPSG:5179).

## 🚀 사용법

```bash
python src/main9_draw_repair.py           # 전체 위치 표시
python src/main9_draw_repair.py --separate  # 타입별 개별 이미지
python src/main9_draw_repair.py --show    # 화면 표시
```

## 🎛️ 옵션
- `--separate`: 타입별 개별 이미지 생성
- `--show`: 화면에 표시

## 📥 입력 파일
- `data/repair/긴급복구.csv`: 원본 데이터 (좌표 포함)
- 기타 누수공사 CSV 파일들

## 📤 출력 파일
- `results/all_recovery_locations.png`: 전체 통합
- `results/*_locations.png`: 타입별 개별 이미지

## ✨ 주요 기능
- 복구 작업 타입별 색상 구분
- MDLZ 배경 지도 표시
- 전체 또는 개별 타입별 시각화
- EPSG:5179 좌표계 처리

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main9_draw_repair_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main8_verify_overlap_samples.py`](main8_verify_overlap_samples.md) - 중첩 검증
- 다음: [`main10_cmp_repair.py`](main10_cmp_repair.md) - 피로 손상 통합 시각화