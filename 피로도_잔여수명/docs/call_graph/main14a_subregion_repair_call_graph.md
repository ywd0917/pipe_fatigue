# main14a_subregion_repair.py 함수 호출 그래프

## 개요
이 문서는 `src/main14a_subregion_repair.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_arguments()
    ├── setup_korean_font() [common.korean_font_utils]
    ├── load_repair_data_for_region()
    │   ├── load_520_repair_csv()
    │   └── convert_wgs84_to_geodataframe()
    ├── plot_repair_points_520()
    │   ├── load_pipe_shapefile() [common.shapefile_loader]
    │   ├── filter_pipes_by_region()
    │   ├── is_subregion() [common.shapefile_loader]
    │   ├── get_parent_region() [common.shapefile_loader]
    │   ├── get_subregion_boundary() [common.shapefile_loader]
    │   ├── get_subregion_label() [common.shapefile_loader]
    │   ├── load_fatigue_data() [fatigue_loader]
    │   ├── prepare_fatigue_data() [fatigue_visualizer]
    │   │   └── get_fatigue_by_ftr_idn() [fatigue_loader]
    │   ├── plot_fatigue_pipes() [fatigue_visualizer]
    │   │   ├── create_log_norm() [fatigue_visualizer]
    │   │   └── create_fatigue_colormap() [fatigue_visualizer]
    │   ├── plot_smlz_background() [fatigue_visualizer]
    │   │   └── get_smlz_shapefile_path() [common.shapefile_loader]
    │   ├── add_fatigue_colorbar() [fatigue_visualizer]
    │   ├── calculate_fatigue_statistics() [fatigue_visualizer]
    │   └── format_fatigue_stats_text() [fatigue_visualizer]
    └── generate_summary_report()

```