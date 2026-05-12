# main10_cmp_repair.py 함수 호출 그래프

## 개요
이 문서는 `src/main10_cmp_repair.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_arguments()
    ├── load_pipe_fatigue_data()
    │   └── load_fatigue_data() [src.fatigue_loader]
    ├── load_repair_data_if_needed()
    │   └── load_all_repair_data() [src.repair_loader]
    └── process_region() [각 지역별로 반복]
        ├── load_pipe_shapefiles()
        │   └── load_pipe_shapefile() [src.common.shapefile_loader]
        ├── get_fatigue_by_ftr_idn() [src.fatigue_loader]
        ├── get_smlz_shapefile_path() [src.common.shapefile_loader]
        └── plot_pipe_fatigue_with_repair()
            ├── setup_korean_font()
            │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
            ├── prepare_fatigue_data() [src.fatigue_visualizer]
            ├── setup_plot_style() [src.common.visualization_utils]
            ├── plot_smlz_background() [src.fatigue_visualizer]
            ├── create_fatigue_colormap() [src.fatigue_visualizer]
            ├── create_log_norm() [src.fatigue_visualizer]
            ├── plot_fatigue_pipes() [src.fatigue_visualizer]
            ├── add_fatigue_colorbar() [src.fatigue_visualizer]
            ├── calculate_fatigue_statistics() [src.fatigue_visualizer]
            ├── plot_repair_points_on_pipe() [src.repair_visualizer]
            └── format_fatigue_stats_text() [src.fatigue_visualizer]

```