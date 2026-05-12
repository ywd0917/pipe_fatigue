# 스크립트 입출력 파일 통합 레퍼런스

이 문서는 프로젝트의 모든 main 스크립트의 입력/출력 파일을 한 곳에 정리한 통합 레퍼런스입니다.

> **최종 업데이트**: 2025-12-12

---

## 스크립트 입출력 통합 표

| 스크립트 | 설명 | 입력 파일 | 출력 파일 |
|---------|------|----------|----------|
| **main1_read_gis_files.py** | GIS shapefile 읽기 | `data/raw/export_shp_20250704(0520)/` | 콘솔 출력 |
| **main2_draw_zone.py** | Zone 영역 시각화 | `data/raw/export_shp_20250704(0520)/WEA_LRGZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SCDZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp` | `results/zone_lrgz.png`<br>`results/zone_mdlz.png`<br>`results/zone_scdz.png`<br>`results/zone_smlz.png`<br>`results/0520_PIPE_LM.png` |
| **main3_draw_soil.py** | 지질 데이터 시각화 | `data/soil/Geology_250K_Litho.shp`<br>`data/soil/Geology_250K_Boudary.shp`<br>`data/soil/Geology_250K_Fault.shp`<br>`data/soil/Geology_250K_Frame.shp` | `results/soil_100K.png`<br>`results/soil_50K.png`<br>`results/soil_250K.png`<br>`results/soil_integrated.png` |
| **main4_list_soil.py** | 지질 데이터 분석 | `data/soil/Geology_250K_Litho.shp` | `results/lithoidx_list.csv` |
| **main5_match_K_soil.py** | 파이프-토양 K_SOIL 매칭 | `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/soil/Geology_250K_Litho.shp` | `results/lithoidx_list_with_K_SOIL.csv`<br>`results/0520_pipe_soil.csv`<br>`results/0520_supply_soil.csv` |
| **main6_draw_road.py** | 도로 네트워크 시각화 | `data/road/TL_SPRD_MANAGE.shp` | `results/road_network.png`<br>`results/road_network_center.png` |
| **main7_pipe_traffic.py** | 파이프-도로 중첩 분석 | `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/road/TL_SPRD_MANAGE.shp` | `results/traffic/0520_pipe_traffic.csv`<br>`results/traffic/0520_sply_traffic.csv` |
| **main8_verify_overlap_samples.py** | 파이프-도로 중첩 검증 | `results/traffic/0520_pipe_traffic.csv`<br>`results/traffic/0520_sply_traffic.csv` | `results/overlap_verification/verification_0520_pipe_samples.png`<br>`results/overlap_verification/verification_0520_sply_samples.png` |
| **main9_draw_recovery.py** | 복구 작업 위치 시각화 | `data/repair/긴급복구.csv` | `results/all_recovery_locations.png`<br>`results/지상누수_locations.png`<br>`results/지하누수_locations.png` |
| **main10_cmp_recovery.py** | 피로 손상-복구 통합 시각화 | 피로 손상 데이터<br>shapefiles | `results/0520_pipe_fatigue_recovery.png`<br>`results/0520_pipe_fatigue_damage.png` |
| **main10a_cmp_repair.py** | 피로 손상 시각화 (K_repair) | `results/main56_calc_fatigure/fatigue_pipe_lm.csv`<br>`results/main56_calc_fatigure/fatigue_sply_ls.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp` | `results/main10a/0243_pipe_fatigue_with_repair.png`<br>`results/main10a/0461_pipe_fatigue_with_repair.png`<br>`results/main10a/0470_pipe_fatigue_with_repair.png`<br>`results/main10a/0480_pipe_fatigue_with_repair.png`<br>`results/main10a/0490_pipe_fatigue_with_repair.png`<br>`results/main10a/0520_pipe_fatigue_with_repair.png` |
| **main11_convert_addr2loc.py** | 주소→좌표 변환 (지오코딩) | `data/repair2/기타공사.csv`<br>`data/repair2/지상누수.csv`<br>`data/repair2/지하누수.csv` | `results/기타공사_위치추가.csv`<br>`results/지상누수_위치추가.csv`<br>`results/지하누수_위치추가.csv`<br>`results/기타공사_위치추가_실패주소.txt`<br>`results/geocoding_cache_naver.db` |
| **main11a_chk_dup_repair.py** | 긴급공사 중복 검사 | `data/repair/긴급복구.csv`<br>`data/repair/긴급복구공사관리(0520).csv` | `results/duplicate_check_20250704.csv` |
| **main11b_merge_n_add2loc.py** | 긴급공사 병합+지오코딩 | `data/repair/긴급복구.csv`<br>`data/repair/긴급복구공사관리(0520).csv` | `results/긴급공사_위치추가.csv`<br>`results/긴급공사_위치추가_실패주소.txt` |
| **main11c_cvrt_addr2loc.py** | 공사관리대장 지오코딩 | `data/repair3/공사관리대장(0520).csv` | `results/관리대장_위치추가.csv` |
| **main11d_cmp_dup.py** | 중복 작업 검출 | `results/지상누수_위치추가.csv`<br>`results/지하누수_위치추가.csv`<br>`results/기타공사_위치추가.csv`<br>`results/긴급공사_위치추가.csv`<br>`results/관리대장_위치추가.csv` | `results/중복분석_상세.csv` |
| **main11e_merge_all_repairs.py** | 재작업 데이터 통합 | `results/지상누수_위치추가.csv`<br>`results/지하누수_위치추가.csv`<br>`results/긴급공사_위치추가.csv`<br>`results/관리대장_위치추가.csv` | `results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv`<br>`results/main11e_merge_all_repairs/통합_요약.txt` |
| **main11f_check_indoor.py** | '옥내' 텍스트 검색 | `results/지상누수_위치추가.csv`<br>`results/지하누수_위치추가.csv`<br>`results/긴급공사_위치추가.csv`<br>`results/관리대장_위치추가.csv` | `results/main11f_check_indoor/옥내작업_통계.json`<br>`results/main11f_check_indoor/옥내작업_요약.txt`<br>`results/main11f_check_indoor/옥내작업_추출.csv` |
| **main11g_fix_area_no.py** | 좌표 기반 구역번호 수정 | `data/main11e_fix_error/누수공사_통합_위치추가.csv`<br>`data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp` | `results/main11g_fix_area_no/누수공사_통합_위치추가_구역수정.csv` |
| **main12_draw_repair2.py** | 복구 작업 시각화 | `results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv` | `results/main12_draw_repair2/all_repair2_ultra_fast.png`<br>`results/main12_draw_repair2/all_repair2_ultra_fast_min2.png`<br>`results/main12_draw_repair2/all_repair2_ultra_fast_min4.png` |
| **main13_crop_520.py** | 520 영역 데이터 추출 | `results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv`<br>`data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp` | `results/main13_crop_520/누수공사_통합_520_위치추가.csv`<br>`results/main13_crop_520/누수공사_통합_520_위치추가.png`<br>`results/main13_crop_520/처리통계.txt` |
| **main13a_calculate_k_repair.py** | K_repair 계산 | `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`results/main13_crop_520/누수공사_통합_520_위치추가.csv` | `results/main13a_k_repair/repair_pipe_lm.csv`<br>`results/main13a_k_repair/repair_sply_ls.csv` |
| **main13c_zone_fatigue_merge.py** | 구역별 피로 데이터 병합 | `results/main56_calc_fatigure/fatigue_pipe_lm.csv`<br>`results/main56_calc_fatigure/fatigue_sply_ls.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp` | `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv` |
| **main13d_visualize_zone_fatigue.py** | 구역별 피로 시각화 | `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv`<br>`data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp` | `results/main13d_visualize_zone_fatigue/zone_fatigue_map.png` |
| **main13f_visualize_high_k_repair.py** | K_repair 상위 파이프 시각화 | `results/main13a_k_repair/repair_pipe_lm.csv`<br>`results/main13a_k_repair/repair_sply_ls.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`results/main13_crop_520/누수공사_통합_520_위치추가.csv` | `results/main13f_high_k_repair/PIPE_LM_top10/rank1_FTR_IDN_12345.png`<br>`results/main13f_high_k_repair/PIPE_LM_high_k_repair_report.md` |
| **main14_cmp_repair2.py** | 피로-재작업 통합 시각화 | `results/main13_crop_520/누수공사_통합_520_위치추가.csv`<br>`results/main56_calc_fatigure/fatigue_pipe_lm.csv`<br>`results/main56_calc_fatigure/fatigue_sply_ls.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp` | `results/main14/all_repair_520_pipe_fatigue.png`<br>`results/main14/지상누수_520_pipe_fatigue.png`<br>`results/main14/지하누수_520_pipe_fatigue.png` |
| **main14a_subregion_repair.py** | 하위 지역 피로 시각화 | `results/main13_crop_520/누수공사_통합_520_위치추가.csv`<br>`results/main56_calc_fatigure/fatigue_pipe_lm.csv`<br>`results/main56_calc_fatigure/fatigue_sply_ls.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp` | `results/main14a/all_repair_0470_pipe_fatigue.png`<br>`results/main14a/all_repair_0480_pipe_fatigue.png`<br>`results/main14a/all_repair_0490_pipe_fatigue.png` |
| **main14b_analyze_repair_correlations.py** | 재작업-K-factors 상관관계 | `results/main13_crop_520/누수공사_통합_520_위치추가.csv`<br>`results/main56_calc_fatigure/fatigue_pipe_lm.csv`<br>`results/main56_calc_fatigure/fatigue_sply_ls.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp` | `results/main14b/0520_repair_k_factors_matched.csv`<br>`results/main14b/0520_repair_correlations_analysis.txt`<br>`results/main14b/metadata.json`<br>`results/main14b/repair_k_factors_scatter.png`<br>`results/main14b/repair_k_factors_boxplot.png`<br>`results/main14b/repair_k_factors_heatmap.png` |
| **main14c_subregion_correlations.py** | 하위 지역 K-factors 상관관계 | `results/지상누수_520_위치추가.csv`<br>`results/지하누수_520_위치추가.csv`<br>`results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv`<br>`results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp` | `results/main14c/0470/repair_k_factors_matched.csv`<br>`results/main14c/0470/correlation_analysis.txt`<br>`results/main14c/0470/metadata.json`<br>`results/main14c/0470/scatter_plot.png`<br>`results/main14c/0470/boxplot.png` |
| **main15_extract_joint_data.py** | Joint 연결 수 계산 | `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp` | `results/main15_extract_joint_data/PIPE_LM_JOINT.csv`<br>`results/main15_extract_joint_data/SPLY_LS_JOINT.csv`<br>`results/main15_extract_joint_data/shapefiles/PIPE_LM_JOINT.shp`<br>`results/main15_extract_joint_data/shapefiles/SPLY_LS_JOINT.shp` |
| **main16_verify_joint_counts.py** | Joint 수 검증 | `results/main15_extract_joint_data/PIPE_LM_JOINT.csv`<br>`results/main15_extract_joint_data/SPLY_LS_JOINT.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp` | `results/main16/pipe_cnt_1_sample_1.png`<br>`results/main16/pipe_cnt_2_sample_1.png`<br>`results/main16/pipe_cnt_3_sample_1.png` |
| **main17_cmp_recovery2.py** | Joint-복구 통합 시각화 | `results/main15_extract_joint_data/shapefiles/PIPE_LM_JOINT.shp`<br>`results/main15_extract_joint_data/shapefiles/SPLY_LS_JOINT.shp`<br>`results/지상누수_520_위치추가.csv`<br>`results/지하누수_520_위치추가.csv`<br>`results/기타공사_520_위치추가.csv` | `results/pipe_repair_지상누수.png`<br>`results/pipe_repair_지하누수.png`<br>`results/pipe_repair_기타공사.png`<br>`results/pipe_repair_all.png` |
| **main17a_duplicate_cnt_jnt_correlation.py** | 재작업-CNT_JNT 상관관계 | `results/main15_extract_joint_data/shapefiles/PIPE_LM_JOINT.shp`<br>`results/main15_extract_joint_data/shapefiles/SPLY_LS_JOINT.shp`<br>`results/main13_crop_520/누수공사_통합_520_위치추가.csv` | `results/main17a_duplicate_cnt_jnt_correlation/duplicate_cnt_jnt_strategy_comparison.png`<br>`results/main17a_duplicate_cnt_jnt_correlation/duplicate_cnt_jnt_correlation_scatter_v2.png`<br>`results/main17a_duplicate_cnt_jnt_correlation/0520_duplicate_cnt_jnt_matched_v2.csv`<br>`results/main17a_duplicate_cnt_jnt_correlation/0520_cnt_jnt_strategy_comparison.csv`<br>`results/main17a_duplicate_cnt_jnt_correlation/0520_duplicate_cnt_jnt_analysis_v2.txt`<br>`results/main17a_duplicate_cnt_jnt_correlation/analysis_metadata.json` |
| **main17a2_distance_sensitivity.py** | 거리별 민감도 분석 | main17a 간접 실행 | `results/main17a2_distance_sensitivity/distance_sensitivity_report.md`<br>`results/main17a2_distance_sensitivity/distance_sensitivity_results.json`<br>`results/main17a2_distance_sensitivity/distance_sensitivity_analysis.png`<br>`results/main17a2_distance_sensitivity/correlation_heatmap.png`<br>`results/main17a2_distance_sensitivity/distance_10m/`<br>`results/main17a2_distance_sensitivity/distance_50m/`<br>`results/main17a2_distance_sensitivity/distance_100m/` |
| **main18_analyze_duplicate_repairs.py** | 중복 위치 시간 분석 | `results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv` | `results/main18_duplicate_analysis/duplicate_repairs_analysis.csv`<br>`results/main18_duplicate_analysis/duplicate_summary.csv`<br>`results/main18_duplicate_analysis/duplicate_cluster_intervals.csv`<br>`results/main18_duplicate_analysis/duplicate_statistics.txt`<br>`results/main18_duplicate_analysis/duplicate_4plus_statistics.txt`<br>`results/main18_duplicate_analysis/duplicate_repair_counts_pie.png`<br>`results/main18_duplicate_analysis/duplicate_interval_histogram.png` |
| **main19_visualize_520_repairs.py** | 520 재작업 통합 시각화 | `results/main13_crop_520/누수공사_통합_520_위치추가.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/raw/export_shp_20250704(0520)/WTL_VALV_PS.shp`<br>`data/raw/export_shp_20250704(0520)/WTL_FIRE_PS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp` | `results/main19_visualize_520_repairs/520_repairs_with_background.png`<br>`results/main19_visualize_520_repairs/520_repairs_type_comparison.png`<br>`results/main19_visualize_520_repairs/520_repairs_density_heatmap.png`<br>`results/main19_visualize_520_repairs/520_infrastructure_correlation_valv.png`<br>`results/main19_visualize_520_repairs/520_infrastructure_correlation_fire.png`<br>`results/main19_visualize_520_repairs/520_repair_infrastructure_data.csv`<br>`results/main19_visualize_520_repairs/520_repairs_summary.csv`<br>`results/main19_visualize_520_repairs/520_repairs_statistics.txt` |
| **main19a_fast_radius_analysis.py** | 반경별 민감도 분석 | `results/지상누수_520_위치추가.csv`<br>`results/지하누수_520_위치추가.csv`<br>`results/기타공사_520_위치추가.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/raw/export_shp_20250704(0520)/WTL_VALV_PS.shp`<br>`data/raw/export_shp_20250704(0520)/WTL_FIRE_PS.shp` | `results/main19a_fast_radius_analysis/sensitivity_report.md`<br>`results/main19a_fast_radius_analysis/sensitivity_summary.json`<br>`results/main19a_fast_radius_analysis/radius_correlation_heatmap.png`<br>`results/main19a_fast_radius_analysis/radius_10m/`<br>`results/main19a_fast_radius_analysis/radius_30m/`<br>`results/main19a_fast_radius_analysis/radius_50m/` |
| **main19b_subregion_analysis.py** | 하위 지역 반경 분석 | `results/지상누수_520_위치추가.csv`<br>`results/지하누수_520_위치추가.csv`<br>`results/기타공사_520_위치추가.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/raw/export_shp_20250704(0520)/WTL_VALV_PS.shp`<br>`data/raw/export_shp_20250704(0520)/WTL_FIRE_PS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp` | `results/main19b_subregion_analysis/comparative_analysis/all_results.json`<br>`results/main19b_subregion_analysis/comparative_analysis/significance_matrix.csv`<br>`results/main19b_subregion_analysis/comparative_analysis/correlation_heatmap.png`<br>`results/main19b_subregion_analysis/comparative_analysis/optimal_radius_report.md`<br>`results/main19b_subregion_analysis/0470/statistical_summary_0470.json`<br>`results/main19b_subregion_analysis/0480/statistical_summary_0480.json`<br>`results/main19b_subregion_analysis/0490/statistical_summary_0490.json` |
| **main20_optimize_parameters.py** | 공간 분석 파라미터 최적화 | - | `results/spatial_analysis/optimal_parameters.json` |
| **main21_kfactors_dfinal_grid.py** | K-factors/D_final 그리드 생성 | - | `results/spatial_analysis/0520_kfactors_dfinal_grid.csv` |
| **main22_spatial_hotspots.py** | 공간 핫스팟 분석 (Getis-Ord Gi*) | `results/지상누수_520_위치추가.csv`<br>`results/지하누수_520_위치추가.csv`<br>`results/기타공사_520_위치추가.csv`<br>`results/spatial_analysis/optimal_parameters.json` | `results/spatial_analysis/hotspots/hotspot_results.csv`<br>`results/spatial_analysis/hotspots/hotspot_results.geojson`<br>`results/spatial_analysis/hotspots/hotspot_analysis.png`<br>`results/spatial_analysis/hotspots/hotspot_analysis_report.md` |
| **main23_infrastructure_risk.py** | 인프라 위험도 평가 | `results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv`<br>`results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp` | `results/spatial_analysis/infrastructure_risk/` |
| **main24_spacetime_cube.py** | 시공간 큐브 분석 | - | `results/spatial_analysis/spacetime/spacetime_cube.pkl` |
| **main25_emerging_hotspots.py** | 출현 핫스팟 탐지 | - | `results/spatial_analysis/emerging/` |
| **main26_maintenance_priority.py** | 유지보수 우선순위 설정 | - | `results/spatial_analysis/priority/` |
| **main26_integrated_spatial.py** | 통합 공간 분석 대시보드 | - | `results/spatial_analysis/integration/` |
| **main27_kfactors_evolution.py** | K-factors 진화 분석 (4D) | - | `results/spatial_analysis/evolution/` |
| **main28_kfactors_prediction.py** | K-factors 예측 모델 | - | `results/spatial_analysis/predictions/` |
| **main29_integrated_priority.py** | 통합 우선순위 시스템 | - | `results/spatial_analysis/integrated_priority/` |
| **main30_validation_report.py** | 검증 및 보고서 생성 | - | `results/spatial_analysis/validation/` |
| **main40_analyze_pressure_gaps.py** | 압력 데이터 결측 분석 | `data/raw/0243 소구역 압력 데이터.csv`<br>`data/raw/0461 소구역 압력 데이터.csv`<br>`data/raw/0470 소구역 압력 데이터.csv`<br>`data/raw/0480 소구역 압력 데이터.csv`<br>`data/raw/0490 소구역 압력 데이터.csv`<br>`data/raw/0520 중구역 압력 데이터.csv` | `results/main40_data_quality/data_quality_report.md`<br>`results/main40_data_quality/figures/missing_ratio_comparison.png`<br>`results/main40_data_quality/figures/missing_timeline_0480.png`<br>`results/main40_data_quality/figures/missing_timeline_0490.png`<br>`results/main40_data_quality/main40.log` |
| **main41_fill_pressure_gaps.py** | 압력 데이터 Gap Filling | `data/raw/0480 소구역 압력 데이터.csv`<br>`data/raw/0490 소구역 압력 데이터.csv`<br>`results/main40_data_quality/data_quality_report.md` | `results/main41_gap_filling/filled_data/0480_filled.csv`<br>`results/main41_gap_filling/filled_data/0490_filled.csv`<br>`results/main41_gap_filling/quality_metrics/0480_metrics.json`<br>`results/main41_gap_filling/quality_metrics/0490_metrics.json`<br>`results/main41_gap_filling/visualizations/0480_gap_comparison.png`<br>`results/main41_gap_filling/visualizations/0490_gap_comparison.png`<br>`results/main41_gap_filling/gap_filling_report.md` |
| **main51_find_freq.py** | 압력 데이터 주파수 분석 | `data/raw/0470 소구역 압력 데이터.csv`<br>`data/raw/0520 중구역 압력 데이터.csv` | `results/main51_find_freq/frequency_spectrum_0470_소구역_압력_데이터.png`<br>`results/main51_find_freq/frequency_spectrum_0520_중구역_압력_데이터.png`<br>`results/main51_find_freq/component_separation_analysis.png` |
| **main52_pass_filter.py** | V자 최저점 Pass Filter | `data/raw/0470 소구역 압력 데이터.csv`<br>`data/raw/0520 중구역 압력 데이터.csv` | `results/main52_pass_filter/valley_based_filter_0470_소구역_압력_데이터.png`<br>`results/main52_pass_filter/valley_based_filter_0520_중구역_압력_데이터.png` |
| **main53_rainflow.py** | Rainflow 계수법 피로 분석 | `data/raw/0470 소구역 압력 데이터.csv`<br>`data/raw/0520 중구역 압력 데이터.csv` | `results/main53_rainflow/rainflow_histogram_0470_소구역_압력_데이터.png`<br>`results/main53_rainflow/rainflow_histogram_0520_중구역_압력_데이터.png`<br>`results/main53_rainflow/cumulative_damage_0470_소구역_압력_데이터.png`<br>`results/main53_rainflow/cumulative_damage_0520_중구역_압력_데이터.png`<br>`results/main53_rainflow/fatigue_comparison.csv` |
| **main54_pipe_data.py** | 관망 데이터 샘플 생성 | `data/raw/PIPE_LM.csv`<br>`data/raw/SPLY_LS.csv` | `results/main54_pipe_data/pipe_lm_sample.csv`<br>`results/main54_pipe_data/sply_ls_sample.csv` |
| **main55_calc_fatigure.py** | 피로 손상 계산 (K_repair 미적용) | `data/raw/0243 소구역 압력 데이터.csv`<br>`data/raw/0461 소구역 압력 데이터.csv`<br>`data/raw/0470 소구역 압력 데이터.csv`<br>`data/raw/0480 소구역 압력 데이터.csv`<br>`data/raw/0490 소구역 압력 데이터.csv`<br>`data/raw/0520 중구역 압력 데이터.csv`<br>`data/raw/PIPE_LM.csv`<br>`data/raw/SPLY_LS.csv`<br>`data/raw/PIPE_PROP.csv`<br>`data/raw/0520_pipe_soil.csv`<br>`data/raw/0520_supply_soil.csv`<br>`data/traffic/0520_pipe_traffic.csv`<br>`data/traffic/0520_sply_traffic.csv` | `results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv`<br>`results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv` |
| **main56_calc_fatigure.py** | 피로 손상 계산 (K_repair 적용) | `data/raw/0243 소구역 압력 데이터.csv`<br>`data/raw/0461 소구역 압력 데이터.csv`<br>`data/raw/0470 소구역 압력 데이터.csv`<br>`data/raw/0480 소구역 압력 데이터.csv`<br>`data/raw/0490 소구역 압력 데이터.csv`<br>`data/raw/0520 중구역 압력 데이터.csv`<br>`data/raw/PIPE_LM.csv`<br>`data/raw/SPLY_LS.csv`<br>`data/raw/PIPE_PROP.csv`<br>`data/raw/0520_pipe_soil.csv`<br>`data/raw/0520_supply_soil.csv`<br>`data/traffic/0520_pipe_traffic.csv`<br>`data/traffic/0520_sply_traffic.csv`<br>`results/main13a_k_repair/repair_pipe_lm.csv`<br>`results/main13a_k_repair/repair_sply_ls.csv` | `results/main56_calc_fatigure/fatigue_pipe_lm.csv`<br>`results/main56_calc_fatigure/fatigue_sply_ls.csv` |
| **main57_merge_fatigue.py** | 피로 손상 결과 통합 | `results/main56_calc_fatigure/fatigue_pipe_lm.csv`<br>`results/main56_calc_fatigure/fatigue_sply_ls.csv` | `results/main57_merge_fatigue/merged_fatigue_analysis.csv`<br>`results/main57_merge_fatigue/merged_fatigue_analysis_20250704_120000.csv` |
| **main58_analyze_remaining_life.py** | D_final_org 기준 위험도 분석 | `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv` | `results/main58_analyze_remaining_life/d_final_distribution.png`<br>`results/main58_analyze_remaining_life/d_final_distribution_by_region.png`<br>`results/main58_analyze_remaining_life/risk_analysis.png`<br>`results/main58_analyze_remaining_life/critical_pipes.csv`<br>`results/main58_analyze_remaining_life/analysis_report.md` |
| **main58a_analyze_remaining_life_by_years.py** | 잔여수명 기준 위험도 분석 | `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv` | `results/main58a_analyze_remaining_life_by_years/remaining_life_distribution.png`<br>`results/main58a_analyze_remaining_life_by_years/remaining_life_by_region.png`<br>`results/main58a_analyze_remaining_life_by_years/risk_analysis_by_years.png`<br>`results/main58a_analyze_remaining_life_by_years/critical_pipes_by_years.csv`<br>`results/main58a_analyze_remaining_life_by_years/analysis_report_by_years.md` |
| **main58b_analyze_overlap.py** | 위험 파이프 중복 분석 | `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv`<br>`data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`<br>`data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`<br>`data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp` | `results/main58b_analyze_overlap/overlap_visualization.png`<br>`results/main58b_analyze_overlap/venn_diagram.png`<br>`results/main58b_analyze_overlap/scatter_plot.png`<br>`results/main58b_analyze_overlap/bar_chart.png`<br>`results/main58b_analyze_overlap/geographic_map.png`<br>`results/main58b_analyze_overlap/overlap_pipes.csv`<br>`results/main58b_analyze_overlap/analysis_report.md` |
| **main58c_analyze_d_final.py** | D_final 기반 5단계 위험도 분석 | `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv` | `results/main58c_analyze_d_final/critical_pipes.csv`<br>`results/main58c_analyze_d_final/regional_statistics.csv`<br>`results/main58c_analyze_d_final/analysis_report.md`<br>`results/main58c_analyze_d_final/risk_analysis.png`<br>`results/main58c_analyze_d_final/d_final_distribution_by_region.png`<br>`results/main58c_analyze_d_final/d_final_distribution.png` |

---

## 주요 데이터 흐름

### 1. 복구 작업 데이터 파이프라인
```
data/repair2/지상누수.csv
data/repair2/지하누수.csv
data/repair2/기타공사.csv
    ↓ main11 (지오코딩)
results/지상누수_위치추가.csv
results/지하누수_위치추가.csv
results/기타공사_위치추가.csv
    ↓ main11e (통합)
results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv
    ↓ main13 (520 필터링)
results/main13_crop_520/누수공사_통합_520_위치추가.csv
    ↓ main13a (K_repair 계산)
results/main13a_k_repair/repair_pipe_lm.csv
results/main13a_k_repair/repair_sply_ls.csv
```

### 2. 피로도 계산 파이프라인
```
data/raw/0243 소구역 압력 데이터.csv
data/raw/0461 소구역 압력 데이터.csv
data/raw/0470 소구역 압력 데이터.csv
data/raw/0480 소구역 압력 데이터.csv
data/raw/0490 소구역 압력 데이터.csv
data/raw/0520 중구역 압력 데이터.csv
    + data/raw/PIPE_LM.csv
    + data/raw/SPLY_LS.csv
    ↓ main55/main56 (피로 계산)
results/main56_calc_fatigure/fatigue_pipe_lm.csv
results/main56_calc_fatigure/fatigue_sply_ls.csv
    ↓ main13c (구역별 병합)
results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv
    ↓ main58 시리즈 (위험도 분석)
results/main58_analyze_remaining_life/analysis_report.md
```

### 3. 공간 분석 파이프라인
```
results/main13_crop_520/누수공사_통합_520_위치추가.csv
    + data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp
    + data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp
    ↓ main20-30 (공간 분석)
results/spatial_analysis/hotspots/
results/spatial_analysis/spacetime/
results/spatial_analysis/emerging/
results/spatial_analysis/priority/
```

---

## 관련 문서

- [문서 인덱스](INDEX.md) - 전체 문서 목록
- [워크플로우 다이어그램](workflows/) - 스크립트 간 연결 관계 시각화
- [피로도 계산 공식](fatigue_calculation_formula.md) - 계산 공식 상세 설명
