# 파이프-도로 중첩 분석 (Pipe-Road Overlap Analysis)

## 개요

이 문서는 상수도 파이프(배수관 및 급수관)와 도로의 공간적 중첩을 분석하는 방법을 설명합니다. 분석의 목적은 각 파이프가 어떤 도로 아래에 매설되어 있는지 파악하여 도로 교통량에 의한 파이프 피로 손상 분석의 기초 데이터를 생성하는 것입니다.

## 기술적 접근

### 1. 공간 버퍼 기반 분석

파이프와 도로의 중첩을 판단하기 위해 다음과 같은 접근 방법을 사용합니다:

1. **도로 버퍼 생성**: 도로 중심선에 도로 폭을 기반으로 버퍼를 생성
2. **공간 조인**: 버퍼된 도로와 파이프 간의 공간적 교차(intersects) 확인
3. **우선순위 선택**: 여러 도로와 중첩되는 경우 도로 폭 기준으로 선택

### 2. 매개변수 정의

```python
# 버퍼 설정
ROAD_BUFFER_RATIO = 0.5      # 도로 폭의 절반을 버퍼로 사용
MIN_BUFFER_DISTANCE = 3.0    # 최소 버퍼 거리 (미터) - GPS 오차 고려
MAX_BUFFER_DISTANCE = 20.0   # 최대 버퍼 거리 (미터) - 95% 도로 커버

# 공간 조인 설정
SPATIAL_PREDICATE = 'intersects'  # 공간 조인 방법
BUFFER_CAP_STYLE = 'round'        # 버퍼 끝부분 스타일

# 출력 설정
OUTPUT_ENCODING = 'utf-8-sig'     # CSV 출력 인코딩 (한글 지원)
```

### 3. 버퍼 계산 로직

각 도로에 대한 버퍼 거리는 다음과 같이 계산됩니다:

```python
buffer_distance = ROAD_BT * ROAD_BUFFER_RATIO
buffer_distance = max(MIN_BUFFER_DISTANCE, buffer_distance)
buffer_distance = min(MAX_BUFFER_DISTANCE, buffer_distance)
```

예시:
- 도로 폭 4m: 버퍼 3m (최소값 적용)
- 도로 폭 20m: 버퍼 10m (20 × 0.5)
- 도로 폭 50m: 버퍼 20m (최대값 적용)

## 중복 도로 처리

하나의 파이프가 여러 도로와 중첩될 경우, 다음 우선순위에 따라 하나의 도로를 선택합니다:

### 우선순위 규칙

1. **도로 폭 (ROAD_BT)**: 가장 넓은 도로 선택 (내림차순)
2. **도로 등급 (ROA_CLS_SE)**: 도로 폭이 같은 경우, 등급이 높은 도로 선택 (오름차순)
   - 1: 고속도로/주간선도로
   - 2: 보조간선도로
   - 3: 집산도로
   - 4: 국지도로
3. **도로 코드 (RN_CD)**: 위 조건이 모두 같은 경우, 코드가 작은 도로 선택

### 선택 근거

도로 폭을 최우선 기준으로 하는 이유:
- 넓은 도로일수록 교통량이 많고 중차량 통행이 빈번함
- 파이프에 가해지는 하중이 더 크므로 피로 손상 분석에 중요
- 주요 간선 파이프는 일반적으로 큰 도로 아래에 매설됨

## 입력 데이터

### 1. 도로 데이터
- 파일: `data/road/TL_SPRD_MANAGE.shp`
- 주요 필드:
  - `RN_CD`: 도로 코드
  - `RN`: 도로명
  - `ROAD_BT`: 도로 폭 (미터)
  - `ROA_CLS_SE`: 도로 등급
  - `SIG_CD`: 시군구 코드
  - `geometry`: 도로 중심선

### 2. 파이프 데이터
- 배수관: `data/raw/export_*/V_WTL_PIPE_LM.shp`
- 급수관: `data/raw/export_*/V_WTL_SPLY_LS.shp`
- 주요 필드:
  - `FTR_IDN`: 시설물 식별번호
  - `geometry`: 파이프 위치

## 출력 데이터

### 파일 형식
- `{region_code}_pipe_traffic.csv`: 배수관-도로 매칭 결과
- `{region_code}_sply_traffic.csv`: 급수관-도로 매칭 결과

여기서 region_code는 export 폴더명에서 추출한 4자리 지역 코드입니다.
예: export_shp_20250704(0520) → 0520

### CSV 구조
```csv
FTR_IDN,RN_CD,RN,ROAD_BT,ROA_CLS_SE
12345,2007001,대구로,30.0,1
23456,2007002,중앙로,25.0,2
34567,2007003,시민로,20.0,2
```

### 필드 설명
- `FTR_IDN`: 파이프 시설물 식별번호 (정수형, .0 없음)
- `RN_CD`: 매칭된 도로의 코드
- `RN`: 매칭된 도로의 이름
- `ROAD_BT`: 매칭된 도로의 폭 (미터)
- `ROA_CLS_SE`: 매칭된 도로의 등급

**참고**: FTR_IDN은 정수형으로 저장되어 불필요한 소수점(.0)이 제거됩니다.

## 알고리즘 상세

### 1. 데이터 로드
```python
# 도로 데이터 로드
road_gdf = load_road_data(RAW_DATA_DIR)

# 모든 export 폴더에서 파이프 데이터 로드
for export_dir in get_all_export_dirs(RAW_DATA_DIR):
    region_code = extract_region_code(export_dir.name)
    pipe_gdf = load_pipe_data(export_dir, "V_WTL_PIPE_LM.shp")
    sply_gdf = load_pipe_data(export_dir, "V_WTL_SPLY_LS.shp")
```

### 2. 버퍼 생성
```python
# 각 도로에 대해 버퍼 생성
road_gdf['buffer_dist'] = road_gdf['ROAD_BT'].apply(calculate_buffer_distance)
road_gdf['buffered_geometry'] = road_gdf.apply(
    lambda row: row.geometry.buffer(row['buffer_dist']), axis=1
)
```

### 3. 공간 조인
```python
# 파이프와 버퍼된 도로 간 공간 조인 (left join으로 모든 파이프 포함)
overlaps = gpd.sjoin(
    pipe_gdf,
    road_buffered_gdf,
    how='left',
    predicate='intersects'
)
```

### 4. 우선순위 적용
```python
# 도로 폭 기준으로 정렬 후 중복 제거
result = overlaps.sort_values(
    by=['FTR_IDN', 'ROAD_BT', 'ROA_CLS_SE', 'RN_CD'],
    ascending=[True, False, True, True]
).drop_duplicates(subset=['FTR_IDN'], keep='first')
```

## 사용 예시

### 기본 실행
```bash
python src/main7_pipe_traffic.py
```

### 옵션 지정
```bash
# 출력 디렉토리 지정
python src/main7_pipe_traffic.py --output-dir results/traffic

# 조용한 모드 (최소 정보만 출력)
python src/main7_pipe_traffic.py --quiet
```

**참고**: 스크립트는 자동으로 모든 export 폴더를 처리합니다.

## 주의사항

1. **좌표계 일치**: 모든 데이터가 동일한 좌표계(EPSG:5179)를 사용해야 함
2. **메모리 사용**: 대용량 데이터 처리 시 충분한 메모리 필요
3. **처리 시간**: 공간 조인은 계산 집약적이므로 시간이 소요될 수 있음
4. **데이터 품질**: 
   - 도로 중심선이 정확해야 함
   - 파이프 위치 데이터의 정확도가 결과에 영향
   - NULL geometry는 자동으로 제외됨

## 결과 검증

생성된 CSV 파일을 검증하는 방법:
1. 샘플 FTR_IDN을 선택하여 GIS 소프트웨어에서 시각적 확인
2. 도로 폭 분포가 합리적인지 확인
3. 각 CSV 파일의 레코드 수가 원본 shapefile의 파이프 수와 일치하는지 확인
4. 매칭되지 않은 파이프는 도로 정보가 비어있는지 확인

## 후속 분석

이 분석 결과는 다음과 같은 후속 분석에 활용됩니다:
- 도로별 교통량 데이터와 결합
- 파이프 피로 손상 예측 모델 입력
- 유지보수 우선순위 결정
- 위험도 평가

## 변경 사항 (v2.0)

### 주요 변경
1. **모든 export 폴더 자동 처리**: --export-dir 옵션 제거, 자동으로 모든 폴더 처리
2. **파일명 형식 변경**: {SIG_CD} → {region_code} (export 폴더에서 추출)
3. **모든 파이프 포함**: left join 사용으로 매칭되지 않은 파이프도 포함
4. **지역 통합**: 시군구별 분리 제거, 지역 코드별로 하나의 파일 생성

### 결과
- 원본 shapefile과 동일한 수의 레코드 보장
- 매칭되지 않은 파이프는 도로 정보가 비어있음

## 검증 도구

### main8_verify_overlap_samples.py
파이프-도로 매칭 결과를 시각적으로 검증하는 도구입니다:
- 샘플링 기반으로 개별 파이프와 주변 도로 표시
- 매칭된 파이프(빨간색) vs 매칭 안된 파이프(파란색) 구분
- 도로 버퍼 영역 시각화
- CSV 읽기 시 FTR_IDN을 정수형으로 처리

### 검증 스크립트
- `main8_verify_test.sh`: 특정 지역 코드 조합 테스트
- `main8_verify_all.sh`: 모든 지역 및 파이프 유형 조합 테스트

## 문서 이력

- 최초 작성일: 2025-07-30
- 수정일: 
  - 2025-07-30 v2.0: 모든 export 폴더 처리, left join 적용, 파일명 형식 변경
  - 2025-07-31 v2.1: FTR_IDN 정수형 저장 및 검증 도구 정보 추가
- 버전: 2.1