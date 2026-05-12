# main19a_subregion_analysis.py Call Graph

## Overview
복구 공사 데이터와 주변 시설물(인프라)의 상관관계를 분석
하위 지역별 반경 민감도 분석 (통계적 유의미성 조사)
0470, 0480, 0490 각 지역에서 10m, 20m, 30m, 50m, 100m 반경별 상관관계 분석

## Main Entry Point
```
main()
├── parse_arguments()
├── setup_korean_font()
├── time()
├── items()
├── create_pvalue_matrix_plot()
├── generate_comparative_report()
├── create_correlation_heatmap()
├── to_csv()
├── int()
├── save_results()
```

## Function Descriptions

### Core Functions
- `load_subregion_data(region_code, verbose)`: 하위 지역 복구 데이터 로드 및 필터링
- `load_subregion_infrastructure(region_code, verbose)`: 하위 지역 인프라 데이터 로드 및 필터링
- `analyze_single_combination(region_code, radius, repair_df, background_data, output_dir, verbose)`: 단일 지역-반경 조합 분석
- `analyze_subregion_radius_sensitivity()`: 모든 하위 지역의 반경별 민감도 분석
- `create_significance_matrix(results)`: 통계적 유의미성 매트릭스 생성
- `find_optimal_radius(results)`: 각 지역별 최적 반경 도출
- `create_correlation_heatmap(results, output_path, show_plot)`: 상관계수 히트맵 생성
- `create_pvalue_matrix_plot(results, output_path, show_plot)`: P-value 매트릭스 플롯 생성
- `generate_comparative_report(results, optimal_radii, matrix_df, output_path)`: 비교 분석 보고서 생성
- `save_results(results, output_dir)`: 분석 결과를 JSON 파일로 저장
- ... and 2 more functions

## Dependencies
- Local modules: src.main19a, src.common, src.common.config, src.common.shapefile_loader, src.main19_visualize_520_repairs
- External: pandas, pathlib, time, seaborn, warnings, datetime, json, matplotlib.pyplot, numpy, scipy

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
