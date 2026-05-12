# main22_spatial_hotspots.py Call Graph

## Overview
main21_spatial_hotspots.py

520 지역의 공간 핫스팟 분석 스크립트.
Getis-Ord Gi*와 Moran's I를 사용하여 재작업 핫스팟을 식별합니다.

## Main Entry Point
```
main()
├── items()
├── load_repair_data()
├── getLogger()
├── visualize_hotspots()
├── add_argument()
├── print()
├── calculate_getis_ord_gi()
├── save_results()
├── calculate_global_morans_i()
├── analyze_cnt_jnt_correlation()
```

## Function Descriptions

### Core Functions
- `load_optimal_parameters(use_optimal)`: 최적 파라미터 로드
- `load_repair_data()`: 520 지역 재작업 데이터 로드
- `main()`: 메인 함수

### Classes
- `SpatialHotspotAnalyzer`: Methods: __init__, create_grid_aggregation, calculate_global_morans_i, calculate_getis_ord_gi, analyze_cnt_jnt_correlation ... (9 total)

## Dependencies
- Local modules: src.common.spatial_utils, src.common.korean_font_utils, src.common.logging_utils
- External: pandas, pathlib, seaborn, warnings, os, json, datetime, numpy, matplotlib.pyplot, sys

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
