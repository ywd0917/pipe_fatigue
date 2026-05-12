# main17_cmp_repair2.py 함수 호출 그래프

## 개요
이 문서는 `src/main17_cmp_repair2.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── setup_korean_font() [src.common.korean_font_utils]
    ├── parse_arguments()
    ├── load_pipe_joint_shapefiles()
    ├── load_repair_csv_files()
    ├── create_visualization() [각 수리 타입별]
    │   ├── setup_plot_style() [src.common.visualization_utils]
    │   ├── plot_pipes()
    │   ├── plot_repair_points()
    │   ├── add_cnt_jnt_legend()
    │   ├── add_repair_legend()
    │   ├── set_plot_limits()
    │   └── add_title_and_stats()
    └── create_combined_visualization() [--all 옵션]
        ├── setup_plot_style() [src.common.visualization_utils]
        ├── plot_pipes()
        ├── plot_all_repair_points()
        ├── add_cnt_jnt_legend()
        ├── add_combined_repair_legend()
        ├── set_plot_limits()
        └── add_combined_title_and_stats()

```