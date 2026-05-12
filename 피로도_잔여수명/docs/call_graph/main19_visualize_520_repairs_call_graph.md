# main19_visualize_520_repairs.py Call Graph

## Overview
520 지역의 복구 공사 데이터와 주변 시설물(인프라)의 상관관계를 분석
- 지상누수_520_위치추가.csv
- 지하누수_520_위치추가.csv
- 기타공사_520_위치추가.csv
3개 파일의 위치 데이터를 통합하여 지도에 시각화

## Main Entry Point
```
main()
├── parse_arguments()
├── append()
├── setup_korean_font()
├── load_background_data()
├── create_density_heatmap()
├── analyze_infrastructure_correlation()
├── generate_statistics_report()
├── copy()
├── Path()
├── to_csv()
```

## Function Descriptions

### Core Functions
- `calculate_haversine_distance(lat1, lon1, lat2, lon2)`: 두 지점 간의 거리를 Haversine 공식으로 계산 (미터 단위)
- `setup_korean_font()`: 한글 폰트 설정
- `load_520_csv_files(results_dir, verbose)`: 520 복구 작업 CSV 파일들 로드 및 통합
- `load_background_data(data_dir, verbose)`: 520 지역의 배경 데이터 로드 (파이프, 행정구역 등)
- `visualize_520_repairs_with_background(repair_df, title, output_path, show_grid, show_background, show_buffers, radius, verbose)`: 520 복구 작업 데이터 시각화 (배경 지도 포함)
- `create_type_comparison_plots(repair_df, output_dir)`: 복구 타입별 비교 플롯 생성
- `create_density_heatmap(repair_df, output_dir)`: 복구 작업 밀도 히트맵 생성
- `generate_statistics_report(repair_df, output_dir)`: 통계 보고서 생성
- `analyze_infrastructure_correlation(repair_df, background_data, output_dir, radius, verbose)`: 사고 위치와 지정된 반경 내 인프라 상관관계 분석
- `create_repair_clusters(df_infra)`: 재작업 위치 클러스터링 (10m 이내)
- ... and 6 more functions

## Dependencies
- Local modules: src.common.visualization_utils, src.common.config, src.common
- External: pandas, math, pathlib, seaborn, warnings, shapely.geometry, matplotlib.pyplot, numpy, scipy, matplotlib.patches

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
