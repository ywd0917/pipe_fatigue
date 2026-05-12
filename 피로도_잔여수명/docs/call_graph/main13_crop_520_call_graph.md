# main13_crop_520.py 함수 호출 그래프

## 개요
이 문서는 `src/main13_crop_520.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── parse_arguments()
    ├── setup_korean_font()
    │   └── korean_font_utils.setup_korean_font() [src.common.korean_font_utils]
    ├── load_mdlz_520_shapefile()
    │   └── load_zone_shapefile() [src.zone_loader]
    └── process_recovery_csv_files()
        ├── filter_points_in_mdlz_520()
        │   └── normalize_unicode_nfc()
        └── save_filtered_csv()

```