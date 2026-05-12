# main30_validation_report.py Call Graph

## Overview
main30_validation_report.py

Phase 12: Automated Validation and Reporting
- 자동화된 분석 검증 및 종합 보고서 생성
- 모든 분석 결과 통합
- 품질 검증 및 일관성 체크
- Executive Summary 생성

## Main Entry Point
```
main()
├── validate_all_analyses()
├── add_argument()
├── parse_args()
├── create_validation_dashboard()
├── get()
├── print_exc()
├── ArgumentParser()
├── save_results()
├── print()
├── exit()
```

## Function Descriptions

### Core Functions
- `main()`: 

### Classes
- `ValidationReporter`: Methods: __init__, validate_all_analyses, _validate_data_quality, _validate_analysis_consistency, _validate_spatial_coverage ... (26 total)

## Dependencies
- External: pandas, pathlib, seaborn, matplotlib, shapely.geometry, datetime, json, common.korean_font_utils, argparse, matplotlib.pyplot

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
