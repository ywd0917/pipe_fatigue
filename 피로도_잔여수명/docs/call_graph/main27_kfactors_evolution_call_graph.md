# main27_kfactors_evolution.py Call Graph

## Overview
Phase 9: K-factors/D_final Evolution Analysis
K-factors와 D_final의 시간적 변화 추적 및 4D 시각화

## Main Entry Point
```
main()
├── add_argument()
├── parse_args()
├── KFactorsEvolutionAnalyzer()
├── run()
├── ArgumentParser()
```

## Function Descriptions

### Core Functions
- `main()`: 메인 함수

### Classes
- `KFactorsEvolutionAnalyzer`: Methods: __init__, load_data, analyze_temporal_evolution, create_4d_visualization, visualize_evolution ... (8 total)

## Dependencies
- Local modules: src.common.korean_font_utils, src.common.config
- External: pickle, pandas, pathlib, seaborn, warnings, datetime, json, numpy, matplotlib.pyplot, plotly.graph_objects

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
