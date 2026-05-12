# main10: 피로 손상 통합 시각화

**파일명**: `main10_cmp_recovery.py`

## 📋 개요
파이프 피로 손상(D_final)과 복구 작업을 통합 시각화합니다.

## 🚀 사용법

```bash
python src/main10_cmp_recovery.py  # 기본: 0520, 0903
python src/main10_cmp_recovery.py --regions 0520  # 특정 지역
python src/main10_cmp_recovery.py --no-recovery  # 복구 작업 제외
```

## 📤 출력 파일
- `results/*_pipe_fatigue_recovery.png`: 통합 이미지
- `results/*_pipe_fatigue_damage.png`: 피로 손상만
- --

## ✨ 주요 기능
- D_final 값에 따른 파이프 색상 코딩
- 로그 스케일 컬러맵 적용
- 복구 작업 위치 오버레이

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main10_cmp_recovery_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main9*.py`](main9*.md)
- 다음: [`main10a*.py`](main10a*.md)
