# main9_draw_repair.py 함수 호출 그래프

## 개요
이 문서는 `src/main9_draw_repair.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_repair_arguments()
    ├── load_repair_data_with_option()
    │   └── load_all_repair_data() [src.repair_loader]
    ├── load_all_mdlz_shapefiles() [src.common.shapefile_loader]
    ├── plot_repair_locations() [전체 통합 이미지]
    │   ├── setup_korean_font()
    │   │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    │   ├── setup_plot_style() [src.common.visualization_utils]
    │   ├── plot_mdlz_background() [src.repair_visualizer]
    │   ├── plot_repair_points() [src.repair_visualizer]
    │   └── calculate_repair_bounds() [src.repair_visualizer]
    │
    └── plot_repair_by_type() [--separate 옵션일 때]
        ├── get_repair_colors() [src.repair_visualizer]
        └── plot_repair_locations() [각 유형별 반복]
            ├── setup_korean_font()
            │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
            ├── setup_plot_style() [src.common.visualization_utils]
            ├── plot_mdlz_background() [src.repair_visualizer]
            ├── plot_repair_points() [src.repair_visualizer]
            └── calculate_repair_bounds() [src.repair_visualizer]

```