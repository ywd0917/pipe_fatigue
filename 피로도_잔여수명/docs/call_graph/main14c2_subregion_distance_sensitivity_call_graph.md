# main14c2_subregion_distance_sensitivity.py 함수 호출 그래프

## 개요
이 문서는 `src/main14c2_subregion_distance_sensitivity.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── analyze_regional_sensitivity() [각 지역별 분석]
    │   ├── run_main14c_with_params()
    │   │   └── subprocess.run() [main14c 실행]
    │   ├── ResultParser.parse_file() [main14_common.result_parser]
    │   └── parse_matching_stats_from_output()
    ├── compare_regions()
    ├── create_3d_visualizations()
    │   └── setup_korean_font() [common.korean_font_utils]
    ├── create_regional_comparison_charts()
    │   └── setup_korean_font() [common.korean_font_utils]
    ├── create_correlation_heatmap()
    │   └── setup_korean_font() [common.korean_font_utils]
    └── generate_comprehensive_report()

```
