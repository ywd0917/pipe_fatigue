# main21_kfactors_dfinal_grid.py Call Graph

## Overview
K-factors/D_final 공간 그리드 데이터 생성
520 지역 파이프의 K-factors와 D_final을 60m × 60m 그리드에 매핑

## Main Entry Point
```
main()
├── KFactorsDfinalGridGenerator()
├── add_argument()
├── parse_args()
├── str()
├── run()
├── ArgumentParser()
```

## Function Descriptions

### Core Functions
- `main()`: 메인 실행 함수

### Classes
- `KFactorsDfinalGridGenerator`: Methods: __init__, load_pipe_data, _merge_pipe_data, _generate_dummy_kfactors, _generate_dummy_data_simple ... (11 total)

## Dependencies
- Local modules: src.common.shapefile_loader, src.common.korean_font_utils, src.common.config
- External: pandas, pathlib, warnings, shapely.geometry, numpy, geopandas, typing, sys

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
