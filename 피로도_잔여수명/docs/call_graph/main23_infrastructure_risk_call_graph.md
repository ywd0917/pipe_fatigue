# main23_infrastructure_risk.py Call Graph

## Overview
main23_infrastructure_risk.py

핫스팟과 파이프 인프라(CNT_JNT, K-factors, D_final) 간의 상관관계 분석
Phase 2.5: Infrastructure Risk Correlation Analysis

## Main Entry Point
```
main()
├── add_argument()
├── parse_args()
├── ArgumentParser()
├── run_analysis()
├── InfrastructureCorrelationAnalyzer()
```

## Function Descriptions

### Core Functions
- `main()`: 메인 함수

### Classes
- `InfrastructureCorrelationAnalyzer`: Methods: __init__, load_hotspot_results, load_pipe_joint_data, load_fatigue_data, analyze_cnt_jnt_correlation ... (11 total)

## Dependencies
- External: pandas, pathlib, seaborn, warnings, os, json, datetime, common.korean_font_utils, common.shapefile_loader, numpy

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
