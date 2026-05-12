# main18_analyze_duplicate_repairs.py 함수 호출 그래프

## 개요
이 문서는 `src/main18_analyze_duplicate_repairs.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.
복구 작업 중복 위치를 분석하고 시간 간격 패턴을 시각화하는 스크립트입니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── setup_korean_font() [src.common.korean_font_utils]
    ├── load_recovery_data()
    │   └── pd.to_datetime() [날짜 파싱]
    ├── find_duplicate_clusters()
    │   ├── _find_duplicate_clusters_simple() [데이터 < 5000]
    │   │   └── calculate_haversine_distance()
    │   └── _find_duplicate_clusters_optimized() [데이터 >= 5000]
    │       └── calculate_haversine_distance()
    ├── analyze_duplicate_patterns()
    │   └── [시간 간격 및 통계 계산]
    ├── analyze_duplicate_patterns_filtered()
    │   └── [4회 이상 재작업 필터링]
    ├── generate_report()
    ├── save_results()
    │   ├── create_repair_count_pie_chart()
    │   │   └── setup_korean_font()
    │   ├── create_interval_histogram()
    │   │   └── setup_korean_font()
    │   └── create_cluster_interval_histogram()
    │       └── setup_korean_font()

```
