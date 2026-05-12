# main26_maintenance_priority.py Call Graph

## Overview
main24_maintenance_priority.py

공간 분석 결과를 통합하여 유지보수 우선순위를 생성합니다.
핫스팟, 진화 패턴, K-factors를 결합한 종합 점수를 계산합니다.

## Main Entry Point
```
main()
├── items()
├── MaintenancePriorityAnalyzer()
├── perform_cost_benefit_analysis()
├── getLogger()
├── add_argument()
├── print()
├── sum()
├── save_results()
├── join()
├── calculate_priority_scores()
```

## Function Descriptions

### Core Functions
- `main()`: 메인 함수

### Classes
- `MaintenancePriorityAnalyzer`: Methods: __init__, load_analysis_results, calculate_priority_scores, generate_recommendations, _get_priority_level ... (10 total)

## Dependencies
- Local modules: src.common.korean_font_utils, src.common.logging_utils
- External: pandas, pathlib, seaborn, warnings, os, json, datetime, numpy, matplotlib.pyplot, sys

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
