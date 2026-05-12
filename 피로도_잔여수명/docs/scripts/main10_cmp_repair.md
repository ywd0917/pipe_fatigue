# main10: 피로 손상 통합 시각화

**파일명**: `main10_cmp_repair.py`

## 📋 개요
파이프 피로 손상(D_final)과 복구 작업을 통합 시각화합니다.

## 🚀 사용법

```bash
python src/main10_cmp_repair.py  # 기본: 0520, 0903
python src/main10_cmp_repair.py --regions 0520  # 특정 지역
python src/main10_cmp_repair.py --no-recovery  # 복구 작업 제외
```

## 🎛️ 옵션
- `--regions`: 분석할 지역 코드
- `--no-recovery`: 복구 작업 표시 제외

## 📥 입력 파일
- `data/fatigue/fatigue_pipe_lm_by_age.csv`: 파이프 피로 손상 데이터
- `data/fatigue/fatigue_sply_ls_by_age.csv`: 급수관 피로 손상 데이터
- `data/repair/*.csv`: 복구 작업 데이터

## 📤 출력 파일
- `results/*_pipe_fatigue_recovery.png`: 통합 이미지
- `results/*_pipe_fatigue_damage.png`: 피로 손상만

## ✨ 주요 기능
- D_final 값에 따른 파이프 색상 코딩
- 로그 스케일 컬러맵 적용
- 복구 작업 위치 오버레이
- 지역별 통합 분석

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main10_cmp_repair_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main9_draw_repair.py`](main9_draw_repair.md) - 복구 작업 시각화
- 다음: [`main11_convert_addr2loc.py`](main11_convert_addr2loc.md) - 주소 지오코딩