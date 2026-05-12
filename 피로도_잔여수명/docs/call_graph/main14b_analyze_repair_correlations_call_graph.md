# main14b_analyze_repair_correlations.py 함수 호출 그래프

## 개요
재작업 위치와 파이프 위험 요인 상관관계 통합 분석 (EPSG:5179 좌표계)

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_arguments()
    ├── load_repair_data()
    │   └── load_repair_csv_files() [src.main14_common.data_loader]
    │       └── convert_to_epsg5179() [src.common.spatial_utils]
    ├── load_pipe_factors_data()
    │   ├── load_fatigue_csv() [src.main14_common.data_loader]
    │   └── load_pipe_shapefiles() [src.main14_common.data_loader]
    ├── create_repair_clusters() [src.main14_common.clustering]
    ├── match_clusters_to_pipes() [src.main14_common.clustering]
    ├── analyze_correlation() [src.main14_common.correlation_analysis]
    ├── create_visualizations()
    ├── save_results()
    └── print()
```
