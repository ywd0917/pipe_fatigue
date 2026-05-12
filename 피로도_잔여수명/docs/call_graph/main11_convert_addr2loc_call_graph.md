# main11_convert_addr2loc.py 함수 호출 그래프

## 개요
이 문서는 `src/main11_convert_addr2loc.py` 내의 함수 호출 관계를 프로젝트 내부 함수만 포함하여 보여줍니다.

## 함수 호출 그래프 (텍스트 형식)

```
[스크립트 진입점]
│
└── main()
    ├── load_geocoding_service()
    │   └── [동적 로드: service에 따라 다름]
    │       ├── geocoding_kakao_sqlite_v2.geocode_address [src.common.geocoding_kakao_sqlite_v2]
    │       ├── geocoding_kakao_sqlite_v2.check_api_credentials [src.common.geocoding_kakao_sqlite_v2]
    │       ├── geocoding_kakao_sqlite_v2.GeocodingError [src.common.geocoding_kakao_sqlite_v2]
    │       └── OR
    │       ├── geocoding_naver_sqlite.geocode_address [src.common.geocoding_naver_sqlite]
    │       ├── geocoding_naver_sqlite.check_api_credentials [src.common.geocoding_naver_sqlite]
    │       └── geocoding_naver_sqlite.GeocodingError [src.common.geocoding_naver_sqlite]
    ├── check_api_credentials() [동적 바인딩]
    ├── get_recovery2_files()
    └── process_csv_file() [각 CSV 파일별로 반복]
        ├── preprocess_address() [각 주소별로 반복]
        ├── geocode_addresses()
        │   ├── check_api_credentials() [동적 바인딩]
        │   └── geocode_address() [동적 바인딩, 각 주소별로 반복]
        └── [선택적] get_cache_stats() [동적 바인딩, service에 따라 다름]

```
