# main12_draw_repair2.py 함수 호출 그래프

## 개요
이 문서는 `src/main12_draw_repair2.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 주요 변경사항 (2025-08-29)
- 긴급공사, 관리대장 데이터 표시 기능 추가 (4가지 복구 유형 모두 표시)
- 출력 디렉토리 구조 개선: `results/main12_draw_repair2/`로 변경

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_arguments()
    ├── load_all_repair2_data()
    │   ├── setup_korean_font()
    │   │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    │   └── normalize_unicode_nfc()
    │
    ├── load_all_mdlz_shapefiles()
    │   └── load_zone_shapefile() [src.zone_loader]
    │
    ├── plot_repair2_by_type() [기본 실행]
    │   ├── setup_plot_style() [src.common.visualization_utils]
    │   └── setup_korean_font()
    │       └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    │
    └── plot_repair2_locations() [--all 옵션일 때]
        ├── setup_plot_style() [src.common.visualization_utils]
        └── setup_korean_font()
            └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]

```