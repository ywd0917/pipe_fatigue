# main8_verify_overlap_samples.py 함수 호출 그래프

## 개요
이 문서는 `src/main8_verify_overlap_samples.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── get_region_code()
    │   └── find_available_regions()
    ├── setup_plot_style()
    │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    ├── load_all_data()
    │   ├── load_road_data() [src.road_loader]
    │   ├── load_pipe_shapefile() [src.common.shapefile_loader]
    │   └── load_traffic_results()
    ├── select_sample_pipes() [src.overlap_verifier]
    ├── create_verification_plot()
    │   ├── visualize_pipe_sample() [src.overlap_verifier]
    │   └── create_legend_elements() [src.overlap_verifier]
    ├── save_and_show_plot()
    ├── calculate_verification_stats() [src.overlap_verifier]
    └── print_statistics()

```