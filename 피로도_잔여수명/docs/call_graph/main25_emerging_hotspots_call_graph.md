# main25_emerging_hotspots.py Call Graph

## Overview
main23_emerging_hotspots.py

시공간 큐브 분석 결과를 기반으로 진화하는 핫스팟 패턴을 식별합니다.
New, Intensifying, Persistent, Diminishing, Sporadic 등의 패턴을 분류합니다.

## Main Entry Point
```
main()
├── visualize_pattern_evolution()
├── classify_hotspot_patterns()
├── items()
├── analyze_kfactors_dfinal_evolution()
├── calculate_hotspots_by_time()
├── visualize_kfactors_dfinal_evolution()
├── getLogger()
├── add_argument()
├── print()
├── save_results()
```

## Function Descriptions

### Core Functions
- `load_optimal_parameters(use_optimal)`: 최적 파라미터 로드
- `load_spacetime_cube(input_dir)`: 시공간 큐브 데이터 로드
- `main()`: 메인 함수

### Classes
- `EmergingHotspotAnalyzer`: Methods: __init__, _prepare_temporal_data, calculate_hotspots_by_time, classify_hotspot_patterns, _classify_pattern ... (15 total)

## Dependencies
- Local modules: src.common.spatial_utils, src.common.logging_utils, src.common.korean_font_utils, src.common.config
- External: pickle, pandas, pathlib, plotly.subplots, seaborn, warnings, os, json, datetime, numpy

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
