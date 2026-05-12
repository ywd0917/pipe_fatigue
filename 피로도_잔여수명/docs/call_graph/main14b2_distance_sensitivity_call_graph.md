# main14b2_distance_sensitivity.py 함수 호출 그래프

## 개요
이 문서는 `src/main14b2_distance_sensitivity.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    └── analyze_distance_sensitivity()
        ├── run_main14b_with_distance()
        │   └── subprocess.run() [main14b 실행]
        ├── ResultParser.parse_file() [main14_common.result_parser]
        ├── parse_matching_stats()
        ├── create_correlation_table()
        ├── create_matching_stats_table()
        ├── create_visualizations()
        │   └── setup_korean_font() [common.korean_font_utils]
        └── create_sensitivity_report()

```
