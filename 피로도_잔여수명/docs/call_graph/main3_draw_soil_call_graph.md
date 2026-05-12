# main3_draw_soil.py 함수 호출 그래프

## 개요
이 문서는 `src/main3_draw_soil.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_soil_arguments()
    ├── get_soil_files() [src.soil_visualizer]
    ├── process_individual_file() [--file 옵션일 때]
    │   ├── get_soil_files() [src.soil_visualizer]
    │   └── plot_individual_file()
    │       ├── setup_korean_font()
    │       │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    │       ├── load_soil_layer() [src.soil_visualizer]
    │       ├── soil_loader.get_file_type_from_path() [src.soil_loader]
    │       ├── analyze_layer_data() [src.soil_visualizer]
    │       ├── setup_plot_style() [src.common.visualization_utils]
    │       ├── plot_frame_background() [src.soil_visualizer]
    │       └── plot_layer_by_group() [src.soil_visualizer]
    │
    └── process_all_layers() [기본 옵션일 때]
        ├── get_soil_files() [src.soil_visualizer]
        └── plot_all_layers()
            ├── setup_korean_font()
            │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
            ├── setup_plot_style() [src.common.visualization_utils]
            └── plot_integrated_layers() [src.soil_visualizer]

```