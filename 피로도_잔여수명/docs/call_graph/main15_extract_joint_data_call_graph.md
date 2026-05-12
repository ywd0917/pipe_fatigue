# main15_extract_joint_data.py 함수 호출 그래프

## 개요
이 문서는 `src/main15_extract_joint_data.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    └── process_all_pipes_jointly()
        ├── load_pipe_shapefile() [src.common.shapefile_loader]
        ├── process_geometry() [각 파이프에 대해]
        │   └── split_linestring_with_semicircle_detection()
        │       └── is_semicircular_pattern() [src.common.semicircle_detection]
        ├── identify_connection_types()
        │   ├── get_line_endpoints()
        │   └── build_spatial_index()
        ├── analyze_connection_type() [각 연결점에 대해]
        └── save_joint_data()
            └── save_to_shapefile()

```