# main2_draw_zone.py 함수 호출 그래프

## 개요
이 문서는 `src/main2_draw_zone.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── process_zone_visualization() [--zone 옵션일 때]
    │   ├── get_all_zone_files() [src.zone_visualizer]
    │   ├── load_zone_data() [src.zone_visualizer]
    │   └── plot_zones()
    │       ├── setup_korean_font()
    │       │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    │       ├── setup_plot_style() [src.common.visualization_utils]
    │       ├── get_zone_metadata() [src.zone_visualizer]
    │       ├── plot_zone_labels() [src.zone_visualizer]
    │       ├── calculate_bounds_with_margin() [src.zone_visualizer]
    │       └── create_zone_legend_elements() [src.zone_visualizer]
    │
    └── process_ftr_visualization() [--file 옵션일 때]
        └── plot_shapefile_by_ftr_idn()
            ├── setup_korean_font()
            │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
            ├── load_shapefile_with_validation() [src.ftr_visualizer]
            ├── analyze_ftr_idn() [src.ftr_visualizer]
            ├── generate_distinct_colors() [src.ftr_visualizer]
            ├── setup_plot_style() [src.common.visualization_utils]
            ├── load_background_smlz() [src.ftr_visualizer]
            ├── plot_geometry_by_type() [src.ftr_visualizer]
            └── calculate_plot_bounds() [src.ftr_visualizer]

```