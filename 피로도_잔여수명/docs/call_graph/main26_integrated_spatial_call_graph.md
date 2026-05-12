# main26_integrated_spatial.py Call Graph

## Overview
main25_integrated_spatial.py

모든 공간 분석 결과를 통합하여 대시보드와 종합 보고서를 생성합니다.
Interactive Plotly/Dash 대시보드와 PDF 보고서를 제공합니다.

## Main Entry Point
```
main()
├── add_argument()
├── mkdir()
├── parse_args()
├── save_integrated_results()
├── export_for_gis()
├── error()
├── print()
├── str()
├── basicConfig()
├── integrate_results()
```

## Function Descriptions

### Core Functions
- `main()`: 메인 함수

### Classes
- `IntegratedSpatialAnalyzer`: Methods: __init__, load_all_results, integrate_results, create_dashboard, _create_priority_map ... (12 total)

## Dependencies
- Local modules: src.common.korean_font_utils
- External: pandas, pathlib, plotly.subplots, seaborn, warnings, os, json, datetime, numpy, matplotlib.pyplot

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
