# main16_verify_joint_counts.py 함수 호출 그래프

## 개요
이 문서는 `src/main16_verify_joint_counts.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── setup_korean_font() [src.common.korean_font_utils]
    ├── load_joint_data() [각 CSV 파일에 대해]
    ├── select_diverse_samples()
    ├── load_pipe_shapefile() [src.common.shapefile_loader]
    ├── load_segment_geometries()
    └── visualize_segment() [각 샘플에 대해]
        ├── setup_plot_style() [src.common.visualization_utils]
        ├── find_connected_segments()
        ├── get_connection_label()
        └── add_connection_info()

```