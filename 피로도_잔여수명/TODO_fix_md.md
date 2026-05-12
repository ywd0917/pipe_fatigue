# fatigue-qgis 마크다운 문서 수정 TODO

fatigue-damage에서 가져온 스크립트(main51~57)의 문서가 fatigue-qgis 환경에 맞게 업데이트되지 않은 항목들을 정리합니다.

## 1. docs/scripts/main55_calc_fatigure.md - ✅ 완료

**문제**: fatigue-qgis의 main55 문서가 "날짜 범위 기반 Rain Flow Counting 분석"으로 되어 있으나, 실제 스크립트는 "피로 손상 계산 (K_repair 미적용)" 기능을 수행함.

**해결**: fatigue-damage/docs/scripts/main55_calc_fatigure.md 내용을 fatigue-qgis에 맞게 수정하여 반영

**커밋**: `24d7856 docs: main55_calc_fatigure.md 문서 내용 수정`

## 2. docs/scripts/main56_calc_fatigure.md - ✅ 이미 최신

**상태**: 이미 fatigue-qgis 환경에 맞게 업데이트됨

- [x] `repair_loader.py` → `repair_loader_k.py` (이미 반영됨)
- [x] `C_REPAIR = 10.0` 상수 설명 추가 (이미 반영됨)
- [x] K_repair 데이터 경로: `data/main13a_k_repair/` → `results/main13a_k_repair/` (이미 반영됨)

## 3. docs/scripts/main57_merge_fatigue.md - ✅ 이미 최신

**상태**: 이미 fatigue-qgis 표준 용어 사용 중

- [x] "기본 피로 손상" → "기본손상도" (이미 반영됨)
- [x] "최종 피로 손상" → "보정손상도" (이미 반영됨)

## 4. docs/fatigue_calculation_formula.md - 역방향 동기화 필요 (별도 작업)

**문제**: fatigue-qgis가 최신 버전이고, fatigue-damage는 구버전임

**fatigue-qgis에 추가된 내용** (역방향 동기화 필요):

- C_REPAIR = 10.0 상수 추가
- 용어 변경: "피로 손상" → "기본손상도/보정손상도"
- `repair_loader.py` → `repair_loader_k.py`

**작업**: fatigue-damage/docs/fatigue_calculation_formula.md를 fatigue-qgis 버전으로 업데이트

## 5. docs/pass_filter_method.md - ✅ 완료

**문제**: fatigue-damage에 있는 pass_filter_method.md가 fatigue-qgis에 없음

**해결**: fatigue-damage/docs/pass_filter_method.md를 fatigue-qgis/docs/에 복사

**커밋**: `57eaab7 docs: pass_filter_method.md 문서 추가`

## 작업 요약

| 항목 | 상태 |
|------|------|
| main55_calc_fatigure.md | ✅ 완료 |
| main56_calc_fatigure.md | ✅ 이미 최신 |
| main57_merge_fatigue.md | ✅ 이미 최신 |
| fatigue_calculation_formula.md | ⏳ 역방향 동기화 필요 (별도 작업) |
| pass_filter_method.md | ✅ 완료 |

## 참고: 동일한 문서 (수정 불필요)

- docs/scripts/main51_find_freq.md - 동일
- docs/scripts/main52_pass_filter.md - 동일
- docs/scripts/main53_rainflow.md - 동일
- docs/scripts/main54_pipe_data.md - 동일
- docs/frequency_analysis_method.md - 동일
