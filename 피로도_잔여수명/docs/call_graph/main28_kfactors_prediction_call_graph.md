# main28_kfactors_prediction.py Call Graph

## Overview
Phase 10: K-factors/D_final Prediction
K-factors/D_final 트렌드 기반 예측 유지보수

## Main Entry Point
```
main()
├── add_argument()
├── parse_args()
├── KFactorsPredictionAnalyzer()
├── run()
├── ArgumentParser()
```

## Function Descriptions

### Core Functions
- `main()`: 메인 함수

### Classes
- `KFactorsPredictionAnalyzer`: Methods: __init__, load_data, predict_kfactors_trends, analyze_risk_patterns, generate_early_warnings ... (10 total)

## Dependencies
- Local modules: src.common.korean_font_utils, src.common.config
- External: pickle, pandas, pathlib, seaborn, warnings, datetime, json, sklearn.linear_model, numpy, matplotlib.pyplot

## Error Handling
- Exception handling and validation included
- Data type checking and conversion

## Output
- Results saved to specified output directory
- Various formats supported (CSV, JSON, plots)
