# main7_pipe_traffic.py 함수 호출 그래프

## 개요
이 문서는 `src/main7_pipe_traffic.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── load_and_buffer_roads()
    │   ├── load_road_data() [src.road_loader]
    │   └── create_road_buffers() [src.traffic_analyzer]
    ├── get_export_directories()
    ├── process_region() [각 지역별로 반복]
    │   ├── extract_region_code()
    │   ├── load_pipe_shapefile() [src.common.shapefile_loader] - PIPE_LM
    │   ├── analyze_pipe_traffic() [src.traffic_analyzer] - PIPE_LM
    │   ├── save_traffic_csv() [src.traffic_analyzer] - PIPE_LM
    │   ├── load_pipe_shapefile() [src.common.shapefile_loader] - SPLY_LS
    │   ├── analyze_pipe_traffic() [src.traffic_analyzer] - SPLY_LS
    │   └── save_traffic_csv() [src.traffic_analyzer] - SPLY_LS
    └── print_final_statistics()

```