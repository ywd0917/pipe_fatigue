# main29_integrated_priority.py Call Graph

## Overview
Phase 11: Enhanced Priority System with K-factors/D_final Integration
통합 우선순위 시스템 - 모든 분석 결과를 종합한 최종 우선순위 결정

## Main Entry Point
```
main()
├── add_argument()
├── parse_args()
├── IntegratedPriorityAnalyzer()
├── run()
├── ArgumentParser()
```

## Function Descriptions

### Core Functions
- `main()`: 메인 함수

### Classes
- `IntegratedPriorityAnalyzer`: Methods: __init__, load_all_results, calculate_integrated_scores, perform_cost_benefit_analysis, create_decision_matrix ... (9 total)

## Dependencies
- Local modules: src.common.korean_font_utils, src.common.config
- External: pandas, pathlib, seaborn, warnings, datetime, json, numpy, matplotlib.pyplot, plotly.graph_objects, sys

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
