# 📚 프로젝트 문서 인덱스

Fatigue QGIS 프로젝트의 모든 문서와 스크립트를 카테고리별로 정리한 인덱스입니다.

## 📜 스크립트 문서

프로젝트는 main1부터 main30까지 30개 이상의 분석 스크립트를 포함하고 있습니다.

<details>
<summary><b>📊 데이터 입출력 (main1-5)</b> - GIS 데이터 읽기, Zone/지질 시각화, 파이프-토양 매칭</summary>

- **[main1_read_gis_files.py](scripts/main1_read_gis_files.md)** - GIS shapefile 데이터를 읽고 검증
- **[main2_draw_zone.py](scripts/main2_draw_zone.md)** - Zone 영역을 지도에 시각화
- **[main3_draw_soil.py](scripts/main3_draw_soil.md)** - 지질 데이터를 지도에 시각화
- **[main4_list_soil.py](scripts/main4_list_soil.md)** - 지질 데이터의 고유 값과 속성 분석
- **[main5_match_K_soil.py](scripts/main5_match_K_soil.md)** - 파이프와 토양 조건 매칭

</details>

<details>
<summary><b>🏗 인프라 분석 (main6-10)</b> - 도로 네트워크, 파이프-도로 중첩, 피로 손상 분석</summary>

- **[main6_draw_road.py](scripts/main6_draw_road.md)** - 도로 네트워크를 지도에 시각화
- **[main7_pipe_traffic.py](scripts/main7_pipe_traffic.md)** - 파이프와 도로 중첩 분석
- **[main8_verify_overlap_samples.py](scripts/main8_verify_overlap_samples.md)** - 파이프-도로 중첩 결과 검증
- **[main9_draw_recovery.py](scripts/main9_draw_recovery.md)** - 복구 작업 위치 시각화
- **[main10_cmp_recovery.py](scripts/main10_cmp_recovery.md)** - 피로 손상과 복구 작업 통합 시각화
  - **[main10a_cmp_repair.py](scripts/main10a_cmp_repair.md)** - 피로 손상 통합 시각화 (누수공사 반영 K_repair)

</details>

<details>
<summary><b>🔧 복구 작업 분석 (main11-19)</b> - 지오코딩, 520 지역 분석, K_repair 계산</summary>

- **[main11_convert_addr2loc.py](scripts/main11_convert_addr2loc.md)** - 주소를 좌표로 변환 (지상누수, 지하누수, 기타공사)
  - **[main11a_chk_dup_repair.py](scripts/main11a_chk_dup_repair.md)** - 긴급공사 파일들 머징(중복 검사 포함) + 좌표 변환
  - **[main11b_merge_n_add2loc.py](scripts/main11b_merge_n_add2loc.md)** - 관리대장 파일 병합 및 주소 변환
  - **[main11c_cvrt_addr2loc.py](scripts/main11c_cvrt_addr2loc.md)** - 주소 지오코딩
  - **[main11d_cmp_dup.py](scripts/main11d_cmp_dup.md)** - 중복 비교 분석
  - **[main11e_merge_all_repairs.py](scripts/main11e_merge_all_repairs.md)** - 전체 복구 작업 병합
  - **[main11f_check_indoor.py](scripts/main11f_check_indoor.md)** - 실내 위치 검증
  - **[main11g_fix_area_no.py](scripts/main11g_fix_area_no.md)** - 좌표 기반 중구역/소구역 번호 수정
- **[main12_draw_repair2.py](scripts/main12_draw_repair2.md)** - 복구 작업 상세 시각화
- **[main13_crop_520.py](scripts/main13_crop_520.md)** - 520 지역 데이터 추출
  - **[main13a_calculate_k_repair.py](scripts/main13a_calculate_k_repair.md)** - K_repair 계산
  - **[main13b_workflow_instruction.py](scripts/main13b_workflow_instruction.md)** - 피로도 계산 워크플로우 안내
  - **[main13c_zone_fatigue_merge.py](scripts/main13c_zone_fatigue_merge.md)** - 구역별 피로 손상 데이터 병합. 파이프 종류, 지역번호 컬럼을 추가하고 해당하는 하나의 D_final 만 남김.
  - **[main13d_visualize_zone_fatigue.py](scripts/main13d_visualize_zone_fatigue.md)** - 구역별 피로 손상 데이터 시각화
  - **[main13f_visualize_high_k_repair.py](scripts/main13f_visualize_high_k_repair.md)** - K_repair_per_m 상위 파이프 시각화
- **[main14_cmp_repair2.py](scripts/main14_cmp_repair2.md)** - 복구 작업 비교 분석
  - **[main14a_subregion_repair.py](scripts/main14a_subregion_repair.md)** - 소지역 복구 분석
  - **[main14b_analyze_repair_correlations.py](scripts/main14b_analyze_repair_correlations.md)** - 복구 상관관계 분석
  - **[main14c_subregion_correlations.py](scripts/main14c_subregion_correlations.md)** - 소지역 상관관계
- **[main15_extract_joint_data.py](scripts/main15_extract_joint_data.md)** - 조인트 데이터 추출 (출력: results/main15_extract_joint_data/)
- **[main16_verify_joint_counts.py](scripts/main16_verify_joint_counts.md)** - 조인트 수 검증 (입력: results/main15_extract_joint_data/)
- **[main17_cmp_recovery2.py](scripts/main17_cmp_recovery2.md)** - 조인트 데이터와 복구 작업 심층 비교
  - **[main17a_duplicate_cnt_jnt_correlation.py](scripts/main17a_duplicate_cnt_jnt_correlation.md)** - 중복 재작업과 파이프 CNT_JNT 상관관계 분석
  - **[main17a2_distance_sensitivity.py](scripts/main17a2_distance_sensitivity.md)** - 거리별 민감도 분석 (10m~100m)
- **[main18_analyze_duplicate_repairs.py](scripts/main18_analyze_duplicate_repairs.md)** - 중복 복구 분석
- **[main19_visualize_520_repairs.py](scripts/main19_visualize_520_repairs.md)** - 520 지역 복구 시각화
  - **[main19a_fast_radius_analysis.py](scripts/main19a_fast_radius_analysis.md)** - 반경별 민감도 분석 (고속 버전)
  - **[main19b_subregion_analysis.py](scripts/main19b_subregion_analysis.md)** - 하위 지역별 반경 민감도 분석

</details>

<details>
<summary><b>📈 공간 통계 분석 (main20-30)</b> - 핫스팟, Space-Time 큐브, 예측 모델</summary>

- **[main20_optimize_parameters.py](scripts/main20_optimize_parameters.md)** - 공간 분석 파라미터 최적화
- **[main21_kfactors_dfinal_grid.py](scripts/main21_kfactors_dfinal_grid.md)** - K-factors/D_final 그리드 생성
- **[main22_spatial_hotspots.py](scripts/main22_spatial_hotspots.md)** - 공간 핫스팟 분석
- **[main23_infrastructure_risk.py](scripts/main23_infrastructure_risk.md)** - 인프라 위험도 평가
- **[main24_spacetime_cube.py](scripts/main24_spacetime_cube.md)** - 시공간 큐브 분석
- **[main25_emerging_hotspots.py](scripts/main25_emerging_hotspots.md)** - 출현 핫스팟 탐지
- **[main26_maintenance_priority.py](scripts/main26_maintenance_priority.md)** - 유지보수 우선순위 설정
- **[main26_integrated_spatial.py](scripts/main26_integrated_spatial.md)** - 통합 공간 분석 대시보드
- **[main27_kfactors_evolution.py](scripts/main27_kfactors_evolution.md)** - K-factors 진화 분석
- **[main28_kfactors_prediction.py](scripts/main28_kfactors_prediction.md)** - K-factors 예측 모델
- **[main29_integrated_priority.py](scripts/main29_integrated_priority.md)** - 통합 우선순위 시스템
- **[main30_validation_report.py](scripts/main30_validation_report.md)** - 검증 및 보고서 생성

</details>

<details>
<summary><b>📊 데이터 품질 및 Gap Filling (main40-41)</b> - 압력 데이터 품질 검사 및 결측 보간</summary>

- **[main40_analyze_pressure_gaps.py](scripts/main40_analyze_pressure_gaps.md)** - 압력 데이터 결측치 분석 및 품질 보고서 생성
  - NaN 결측 + Time Gap 결측 (5분 간격 기준) 탐지 ⭐
  - 임계값 기반 자동 경고 시스템
  - Markdown 보고서 및 시각화 차트 생성
  - 개발 체크리스트: [TODO_main40_analyze_pressure_gaps.md](TODO_main40_analyze_pressure_gaps.md)
- **[main41_fill_pressure_gaps.py](MAIN41_PLAN.md)** - Gap filling 구현 (XGBoost/Spectral 방법)
- **[Gap Interpolation 연구 프로젝트](GAP_INTERPOLATION_RESEARCH.md)** - tmp/007~014 연구 결과 종합 🆕

</details>

<details>
<summary><b>🔬 피로도 계산 (main51-58)</b> - 압력 데이터의 주파수 분석 및 피로도 계산</summary>

> **Note**: 이 섹션의 스크립트들은 원래 별도의 `fatigue-damage` 프로젝트에 존재했으나,
> 통합 관리를 위해 이 프로젝트로 포팅되었습니다.

- **[main51_find_freq.py](scripts/main51_find_freq.md)** - 압력 데이터의 주파수 성분 분석
- **[main52_pass_filter.py](scripts/main52_pass_filter.md)** - V자 최저점 기준 Pass Filter 적용
- **[main53_rainflow.py](scripts/main53_rainflow.md)** - Rainflow 계수법 피로 분석
- **[main54_pipe_data.py](scripts/main54_pipe_data.md)** - 관망 데이터 처리 및 샘플 생성
- **[main55_calc_fatigure.py](scripts/main55_calc_fatigure.md)** - 날짜 범위 기반 Rain Flow Counting 분석
- **[main56_calc_fatigure.py](scripts/main56_calc_fatigure.md)** - 피로 손상 계산 (K_repair 적용 버전)
- **[main57_merge_fatigue.py](scripts/main57_merge_fatigue.md)** - 피로 손상 결과 파일 통합
- **[main58_analyze_remaining_life.py](scripts/main58_analyze_remaining_life.md)** - D_final_org 기준 위험도 분석
- **[main58a_analyze_remaining_life_by_years.py](scripts/main58a_analyze_remaining_life_by_years.md)** - 잔여수명 기준 위험도 분석
- **[main58b_analyze_overlap.py](scripts/main58b_analyze_overlap.md)** - D_final_org과 잔여수명 기준 위험 파이프 중복 분석
- **[main58c_analyze_d_final.py](scripts/main58c_analyze_d_final.md)** - D_final 기반 위험도 분석 (5단계 분류)

</details>

## 📋 스크립트 입출력 참조

- **[📋 스크립트 입출력 통합 문서](SCRIPT_IO_REFERENCE.md)** - 모든 스크립트의 입력/출력 파일을 한눈에 정리 🆕

## 🔄 워크플로우 다이어그램

스크립트 간 입출력 파일 연결 관계를 시각화한 다이어그램입니다.

- [시계열/피로도 분석 (main51-58)](workflows/workflow_main51-58_fatigue.md) - 주파수 분석부터 위험도 분석까지
- [지오코딩 파이프라인 (main11)](workflows/workflow_main11_geocoding.md) - 복구 데이터 주소→좌표 변환
- [520 지역 분석 (main13)](workflows/workflow_main13_520_analysis.md) - K_repair 계산 및 구역별 분석
- [Joint 분석 (main15-17)](workflows/workflow_main15-17_joint.md) - Joint 데이터 추출 및 상관관계
- [공간 통계 분석 (main20-30)](workflows/workflow_main20-30_spatial.md) - 핫스팟, 시공간 큐브, 예측 모델

## 📖 기술 가이드 문서

### GIS 데이터 처리
- [GIS 데이터 필드 정의](GIS_DATA_FIELDS.md) - GIS 데이터 필드 정의 및 FTR_CDE 코드 체계
- [지질 데이터 분석](soil_data_analysis.md) - 지질 데이터 상세 분석 및 lithoidx 목록
- [K_SOIL 추출 방법](K_SOIL_extraction_method.md) - K_SOIL 값 추출 및 공간 매칭 방법

### 인프라 분석
- [파이프-도로 중첩 분석](pipe_road_overlap_analysis.md) - 파이프-도로 중첩 분석 방법 및 알고리즘
- [파이프-점 매칭 방법](pipe_point_matching_method.md) - 파이프(LineString)와 점(Point) 간 공간 매칭 방법론
- [매칭 전략 가이드](matching_strategies.md) - 파이프 매칭 시 nearest, max, avg 전략 상세 설명 🆕
- [Joint 연결 수 계산](joint_calculation.md) - 파이프 세그먼트의 Joint 연결 분석 방법
- [피로도 계산 공식](fatigue_calculation_formula.md) - 파이프 피로도 계산 공식 및 예제

### 지오코딩
- [지오코딩 사용법](geocoding_usage.md) - Naver/Kakao Maps API 지오코딩 가이드
- [지오코딩 최적화](geocoding_optimization.md) - 지오코딩 성능 최적화 및 캐시 전략

### 시각화
- [시각화 출력 규칙](visualization_rules.md) - 복구 작업 시각화 표준 스타일 가이드 🆕

### 주파수 분석
- [주파수 분석 방법](frequency_analysis_method.md) - 압력 데이터의 주파수 분석 방법론

### 클러스터링
- [클러스터링 알고리즘](clustering_algorithm.md) - 공간 데이터 클러스터링 알고리즘

## 🔬 분석 결과 문서

- **[📊 분석 결과 요약](analysis_results_summary.md)** - 주요 발견사항 및 실무 시사점 (종합) 🆕
- [통계 개념 쉽게 이해하기](statistical_concepts_explained.md) - r, p, R² 등 통계 지표 일반인 설명 🆕
- [상관관계 분석 결과](correlation_analysis_results.md) - K-factors와 재작업 상관관계 상세 통계
- [공간분석 완료 보고서](spatial_analysis_completion_report.md) - main20-30 공간분석 구현 내역
- [하위 지역 반경 민감도 분석](subregion_radius_sensitivity_analysis.md) - 0470/0480/0490 지역별 반경 분석
- [짧은 파이프 분석](analysis/analyze13_short_pipes.md) - 10m 미만 짧은 파이프 분석

## 📊 함수 호출 그래프

각 main 스크립트의 함수 호출 관계를 시각화한 문서입니다.

### 데이터 입출력 (main1-5)
- [main1: GIS 파일 읽기](call_graph/main1_read_gis_files_call_graph.md)
- [main2: Zone 시각화](call_graph/main2_draw_zone_call_graph.md)
- [main3: 지질 데이터 시각화](call_graph/main3_draw_soil_call_graph.md)
- [main4: 지질 데이터 분석](call_graph/main4_list_soil_call_graph.md)
- [main5: 파이프-토양 매칭](call_graph/main5_match_K_soil_call_graph.md)

### 인프라 분석 (main6-10)
- [main6: 도로 네트워크 시각화](call_graph/main6_draw_road_call_graph.md)
- [main7: 파이프-도로 중첩 분석](call_graph/main7_pipe_traffic_call_graph.md)
- [main8: 중첩 검증](call_graph/main8_verify_overlap_samples_call_graph.md)
- [main9: 복구 작업 시각화](call_graph/main9_draw_repair_call_graph.md)
- [main10: 피로 손상 통합 시각화](call_graph/main10_cmp_repair_call_graph.md)

### 공간 통계 분석 (main20-30)
- [main20: 파라미터 최적화](call_graph/main20_optimize_parameters_call_graph.md)
- [main21: K-factors/D_final 그리드](call_graph/main21_kfactors_dfinal_grid_call_graph.md)
- [main22: 공간 핫스팟 분석](call_graph/main22_spatial_hotspots_call_graph.md)
- [main23: 인프라 위험도 평가](call_graph/main23_infrastructure_risk_call_graph.md)
- [main24: 시공간 큐브 분석](call_graph/main24_spacetime_cube_call_graph.md)
- [main25: 출현 핫스팟 탐지](call_graph/main25_emerging_hotspots_call_graph.md)
- [main26: 유지보수 우선순위](call_graph/main26_maintenance_priority_call_graph.md)
- [main26: 통합 공간 분석](call_graph/main26_integrated_spatial_call_graph.md)
- [main27: K-factors 진화 분석](call_graph/main27_kfactors_evolution_call_graph.md)
- [main28: K-factors 예측 모델](call_graph/main28_kfactors_prediction_call_graph.md)
- [main29: 통합 우선순위 시스템](call_graph/main29_integrated_priority_call_graph.md)
- [main30: 검증 보고서](call_graph/main30_validation_report_call_graph.md)

### 복구 작업 분석 (main11-19)
- [main11: 주소 지오코딩](call_graph/main11_convert_addr2loc_call_graph.md)
- [main12: 위치추가 CSV 시각화](call_graph/main12_draw_repair2_call_graph.md)
- [main13: 520 영역 추출 및 중복 분석](call_graph/main13_crop_520_call_graph.md)
- [main14: 520 지역 통합 시각화](call_graph/main14_cmp_repair2_call_graph.md)
- [main14a: 소지역 복구 분석](call_graph/main14a_subregion_repair_call_graph.md)
- [main14b: 복구 상관관계 분석](call_graph/main14b_analyze_repair_correlations_call_graph.md)
- [main14b2: 거리 민감도 분석](call_graph/main14b2_distance_sensitivity_call_graph.md)
- [main14c: 소지역 상관관계](call_graph/main14c_subregion_correlations_call_graph.md)
- [main14c2: 소지역 거리 민감도](call_graph/main14c2_subregion_distance_sensitivity_call_graph.md)
- [main15: 파이프 세그먼트 분리](call_graph/main15_extract_joint_data_call_graph.md)
- [main16: Joint 연결 검증](call_graph/main16_verify_joint_counts_call_graph.md)
- [main17: 파이프 네트워크 통합](call_graph/main17_cmp_repair2_call_graph.md)
- [main17a: 중복 재작업과 CNT_JNT 상관관계](call_graph/main17a_duplicate_cnt_jnt_correlation_call_graph.md)
- [main18: 중복 위치 분석](call_graph/main18_analyze_duplicate_repairs_call_graph.md)
- [main19: 520 지역 복구 시각화](call_graph/main19_visualize_520_repairs_call_graph.md)
- [main19a: 반경별 민감도 분석](call_graph/main19a_fast_radius_analysis_call_graph.md)
- [main19b: 하위 지역별 반경 분석](call_graph/main19b_subregion_analysis_call_graph.md)

## 🔧 개발 문서

### 프로젝트 관리
- [최적화 가이드](OPTIMIZATION_GUIDE.md) - 성능 최적화 가이드라인
- [포팅 가이드](PORTING.md) - 프로젝트 간 코드 포팅 가이드
- [공통화 가이드](main14_commonization_guide.md) - main14 공통화 가이드

### 의존성 분석
- [의존성 분석 README](dependencies/README.md) - pydeps를 사용한 의존성 분석 결과
- [의존성 분석 상세](dependencies/DEPENDENCIES.md) - 의존성 구조 상세 분석

### 리팩토링
- [리팩토링 README](refactoring/README.md) - 리팩토링 문서 개요
- [리팩토링 가이드](refactoring/GUIDE.md) - 코드 리팩토링 핵심 가이드라인
- [리팩토링 상세 계획](refactoring/REFACTORING_DETAILS.md) - 구체적인 리팩토링 계획
- [분리 수준 가이드](refactoring/SEPARATION_GUIDE.md) - 코드 분리 수준 결정 가이드
- [리팩토링 결과](refactoring/RESULT.md) - 리팩토링 완료 항목
- [리팩토링 TODO](refactoring/TODO.md) - 리팩토링 작업 목록

### 트러블슈팅
- [matplotlib viewport 위치 문제](troubleshooting/matplotlib_viewport_positioning.md) - matplotlib 창 위치 조정 문제 해결

## 📁 문서 구조

```
docs/
├── INDEX.md (이 파일)
├── SCRIPT_IO_REFERENCE.md (스크립트 입출력 통합 문서) 🆕
│
├── 스크립트 문서
│   └── scripts/
│       ├── main1_read_gis_files.md ~ main30_validation_report.md (30개 파일)
│       └── main11a ~ main19a 등 서브스크립트 문서
│
├── 기술 가이드
│   ├── GIS_DATA_FIELDS.md
│   ├── K_SOIL_extraction_method.md
│   ├── pipe_road_overlap_analysis.md
│   ├── pipe_point_matching_method.md
│   ├── matching_strategies.md
│   ├── soil_data_analysis.md
│   ├── joint_calculation.md
│   ├── geocoding_usage.md
│   └── geocoding_optimization.md
│
├── 분석 결과
│   ├── analysis_results_summary.md
│   ├── statistical_concepts_explained.md
│   ├── correlation_analysis_results.md
│   ├── spatial_analysis_completion_report.md
│   └── subregion_radius_sensitivity_analysis.md
│
├── 함수 호출 그래프
│   └── call_graph/
│       └── main*_call_graph.md (18개 파일)
│
└── 개발 문서
    ├── dependencies/
    │   ├── README.md
    │   ├── DEPENDENCIES.md
    │   └── *.svg (시각화 파일)
    └── refactoring/
        ├── README.md
        ├── GUIDE.md
        ├── REFACTORING_DETAILS.md
        ├── SEPARATION_GUIDE.md
        ├── RESULT.md
        └── TODO.md
```

## 🔍 문서 검색 팁

1. **특정 주제 찾기**: Ctrl+F (또는 Cmd+F)로 키워드 검색
2. **스크립트 관련 문서**: main 번호로 검색 (예: "main14")
3. **기술 문서**: 기술명으로 검색 (예: "K_SOIL", "지오코딩")

## 📝 문서 관리

- **새 문서 추가 시**: 이 INDEX.md 파일을 업데이트해주세요
- **문서 수정 시**: 관련 링크가 여전히 유효한지 확인해주세요
- **문서 삭제 시**: 이 인덱스에서도 제거해주세요

---

최종 업데이트: 2025-12-12