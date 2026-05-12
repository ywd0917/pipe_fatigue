# main24_spacetime_cube.py Call Graph

## Overview
main22_spacetime_cube.py

시공간 큐브 분석을 통한 재작업 패턴의 시계열 분석.
계절성, 트렌드, Knox test 등을 수행합니다.

## Main Entry Point
```
main()
├── create_spacetime_cube()
├── items()
├── load_repair_data()
├── perform_seasonal_decomposition()
├── analyze_cnt_jnt_arima_forecast()
├── analyze_kfactors_dfinal_temporal_patterns()
├── SpaceTimeCubeAnalyzer()
├── visualize_kfactors_dfinal_timeseries()
├── getLogger()
├── add_argument()
```

## Function Descriptions

### Core Functions
- `load_optimal_parameters(use_optimal)`: 최적 파라미터 로드
- `load_repair_data()`: 520 지역 재작업 데이터 로드 및 K-factors/D_final 데이터 병합
- `main()`: 메인 함수

### Classes
- `SpaceTimeCubeAnalyzer`: Methods: __init__, _prepare_temporal_data, create_spacetime_cube, perform_seasonal_decomposition, perform_trend_analysis ... (15 total)

## Dependencies
- Local modules: src.common.spatial_utils, src.common.logging_utils, src.common.korean_font_utils, src.common.config
- External: scipy, pathlib, seaborn, warnings, json, statsmodels.tsa.stattools, statsmodels.stats.diagnostic, plotly.subplots, os, numpy

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
