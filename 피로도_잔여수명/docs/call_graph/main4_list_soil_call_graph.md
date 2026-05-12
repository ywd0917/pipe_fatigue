# main4_list_soil.py 함수 호출 그래프

## 개요
이 문서는 `src/main4_list_soil.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── soil_loader.load_soil_data() [src.soil_loader]
    ├── soil_loader.analyze_lithoidx() [src.soil_loader]
    ├── soil_loader.generate_lithoidx_statistics() [src.soil_loader]
    │   └── LithoidxStatistics (dataclass) [src.soil_loader]
    │
    ├── print_summary_statistics() [--summary 옵션일 때]
    │
    ├── handle_search_mode() [--search 옵션일 때]
    │   ├── soil_loader.search_lithoidx() [src.soil_loader]
    │   └── print_lithoidx_info()
    │
    ├── print_lithoidx_info() [기본 모드일 때]
    │
    └── save_to_csv() [--csv 옵션일 때]

```