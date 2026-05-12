# main19a.py Call Graph

## Overview
520 지역의 복구 공사 데이터와 주변 시설물(인프라)의 상관관계를 분석
main19_visualize_...py의 개선버전.
반경별 민감도 분석 - 고속 버전 (cKDTree 공간 인덱싱)
520 지역 재작업과 인프라 상관관계를 다양한 반경에서 분석
cKDTree를 사용하여 150배 이상 속도 향상 (2초 내 전체 분석 완료)

## Main Entry Point
```
main()
├── parse_arguments()
├── append()
├── setup_korean_font()
├── load_background_data()
├── time()
├── generate_summary_report()
├── load_520_csv_files()
├── print()
├── analyze_single_radius_fast()
├── mkdir()
```

## Function Descriptions

### Core Functions
- `setup_korean_font()`: 한글 폰트 설정
- `haversine_distance_vectorized(lat1, lon1, lat2, lon2)`: 벡터화된 Haversine 거리 계산 (미터 단위)
- `analyze_infrastructure_correlation_fast(repair_df, background_data, output_dir, radius, verbose)`: 고속 인프라 상관관계 분석 (BallTree 사용)
- `create_repair_clusters_fast(df_infra)`: 빠른 재작업 위치 클러스터링 (KDTree 사용)
- `perform_statistical_analysis(df_infra, df_clusters)`: 통계적 상관관계 분석
- `analyze_single_radius_fast(radius, repair_df, background_data, output_dir, verbose)`: 단일 반경에 대한 고속 분석
- `generate_summary_report(all_results, output_dir)`: 종합 보고서 생성
- `parse_arguments()`: 명령줄 인자 파싱
- `main()`: 메인 실행 함수

## Dependencies
- Local modules: src.main19_visualize_520_repairs, src.common.config, src.common
- External: pandas, pathlib, time, seaborn, warnings, datetime, json, matplotlib.pyplot, numpy, scipy.spatial

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
