# main14_cmp_repair2.py 함수 호출 그래프

## 개요
이 문서는 `src/main14_cmp_repair2.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_arguments()
    ├── load_pipe_fatigue_data()
    │   └── load_fatigue_data() [fatigue_loader]
    ├── load_pipe_shapefiles_520()
    │   └── load_pipe_shapefile() [common.shapefile_loader]
    ├── load_520_repair_data()
    │   ├── load_520_repair_csv()
    │   └── get_repair_colors()
    ├── process_repair_type() [별도 타입별 처리]
    │   ├── prepare_fatigue_data() [fatigue_visualizer]
    │   ├── get_fatigue_by_ftr_idn() [fatigue_loader]
    │   ├── get_smlz_shapefile_path() [common.shapefile_loader]
    │   ├── create_log_norm() [fatigue_visualizer]
    │   ├── create_fatigue_colormap() [fatigue_visualizer]
    │   ├── setup_plot_style() [common.visualization_utils]
    │   ├── plot_smlz_background() [fatigue_visualizer]
    │   ├── plot_fatigue_pipes() [fatigue_visualizer]
    │   ├── calculate_fatigue_statistics() [fatigue_visualizer]
    │   ├── format_fatigue_stats_text() [fatigue_visualizer]
    │   └── add_fatigue_colorbar() [fatigue_visualizer]
    └── plot_all_repair_types() [전체 통합 처리]
        ├── prepare_fatigue_data() [fatigue_visualizer]
        ├── get_fatigue_by_ftr_idn() [fatigue_loader]
        ├── get_smlz_shapefile_path() [common.shapefile_loader]
        ├── create_log_norm() [fatigue_visualizer]
        ├── create_fatigue_colormap() [fatigue_visualizer]
        ├── setup_plot_style() [common.visualization_utils]
        ├── plot_smlz_background() [fatigue_visualizer]
        ├── plot_fatigue_pipes() [fatigue_visualizer]
        ├── calculate_fatigue_statistics() [fatigue_visualizer]
        ├── format_fatigue_stats_text() [fatigue_visualizer]
        └── add_fatigue_colorbar() [fatigue_visualizer]

```