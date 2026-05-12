# main1_read_gis_files.py 함수 호출 그래프

## 개요
이 문서는 `src/main1_read_gis_files.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── find_shapefiles()
    ├── read_shapefile_info()
    │   └── load_shapefile() [src.gis_analyzer]
    └── print_all_records()
        ├── load_shapefile() [src.gis_analyzer]
        ├── print_records_without_ftr_idn() [FTR_IDN이 없을 때]
        │   ├── get_geometry_info() [src.gis_analyzer]
        │   │   └── GeometryInfo (dataclass) [src.gis_analyzer]
        │   └── format_attributes() [src.gis_analyzer]
        ├── analyze_ftr_groups() [src.gis_analyzer]
        │   ├── FtrStatistics (dataclass) [src.gis_analyzer]
        │   ├── extract_ftr_attributes() [src.gis_analyzer]
        │   └── get_geometry_info() [src.gis_analyzer]
        │       └── GeometryInfo (dataclass) [src.gis_analyzer]
        ├── print_ftr_group() [각 FTR_IDN에 대해]
        │   ├── get_geometry_info() [src.gis_analyzer]
        │   │   └── GeometryInfo (dataclass) [src.gis_analyzer]
        │   └── format_attributes() [src.gis_analyzer]
        ├── calculate_summary_statistics() [src.gis_analyzer]
        ├── group_by_ftr_cde() [src.gis_analyzer]
        └── print_statistics_summary() [src.common.visualization_utils]

```