# main5_match_K_soil.py 함수 호출 그래프

## 개요
이 문서는 `src/main5_match_K_soil.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── soil_loader.load_soil_data() [src.soil_loader]
    ├── soil_loader.load_k_soil_data() [src.soil_loader]
    └── process_regions()
        ├── get_export_directories()
        └── process_pipe_type() [파이프 타입별로 반복]
            ├── load_pipe_shapefile() [src.common.shapefile_loader]
            ├── soil_loader.spatial_join_with_soil() [src.soil_loader]
            └── soil_loader.save_soil_matching_result() [src.soil_loader]

```