# main20_optimize_parameters.py Call Graph

## Overview
main20_optimize_parameters.py

공간 분석 스크립트들(main21-main25)을 위한 최적 파라미터를 찾는 스크립트.
520 지역 재작업 데이터를 사용하여 공간 및 시간 파라미터를 최적화합니다.

## Main Entry Point
```
main()
├── optimize_integrated()
├── dumps()
├── add_argument()
├── mkdir()
├── parse_args()
├── error()
├── optimize_temporal_parameters()
├── print()
├── optimize_spatial_parameters()
├── load_repair_data()
```

## Function Descriptions

### Core Functions
- `load_repair_data()`: 520 지역 재작업 데이터 로드
- `main()`: 메인 함수

### Classes
- `ParameterOptimizer`: Methods: __init__, optimize_spatial_parameters, optimize_temporal_parameters, optimize_emerging_parameters, cross_validate_parameters ... (6 total)

## Dependencies
- Local modules: src.common.spatial_utils, src.common.korean_font_utils, src.common.logging_utils
- External: pandas, pathlib, warnings, os, json, datetime, statsmodels.tsa.seasonal, scipy.spatial.distance, numpy, scipy.spatial

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
