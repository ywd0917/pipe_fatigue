# main6_draw_road.py 함수 호출 그래프

## 개요
이 문서는 `src/main6_draw_road.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── load_road_from_file() [src.road_loader]
    ├── analyze_road_attributes() [src.road_visualizer]
    ├── print_road_analysis() [src.road_visualizer]
    ├── get_output_file_path()
    ├── plot_road_network() [전체 도로 네트워크]
    │   ├── setup_korean_font()
    │   │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    │   ├── setup_plot_style() [src.common.visualization_utils]
    │   ├── plot_roads_by_class_and_width() [src.road_visualizer]
    │   └── create_road_legend_elements() [src.road_visualizer]
    │
    └── plot_center_area_if_needed()
        ├── extract_center_area() [src.road_visualizer]
        └── plot_road_network() [중심부 영역]
            ├── setup_korean_font()
            │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
            ├── setup_plot_style() [src.common.visualization_utils]
            ├── plot_roads_by_class_and_width() [src.road_visualizer]
            └── create_road_legend_elements() [src.road_visualizer]

```