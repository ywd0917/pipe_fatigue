# K_SOIL 값 추출 방법

## 1. K_SOIL 정의와 목적

K_SOIL은 토양 계수(Soil Coefficient)로, 파이프라인의 피로 손상 분석에서 토양 특성이 미치는 영향을 반영하는 계수입니다.

- **목적**: 토양의 물리적 특성(강도, 밀도, 수분 함량 등)에 따른 파이프라인 응력 변화를 고려
- **활용**: 피로 손상 계산 시 토양별 가중치로 사용
- **범위**: 일반적으로 1.0 ~ 2.0 사이의 값

## 2. 사용된 GIS 데이터

### 토양(암반) 데이터
- **파일**: `data/soil/Geology_250K_Litho.shp`
- **축척**: 1:250,000
- **내용**: 한국 지질도의 암상(lithology) 정보
- **주요 필드**:
  - `lithoidx`: 암상 인덱스 (246개 고유값)
  - `lithoname`: 암상명 (한글)
  - `age`: 지질 시대
  - `geometry`: 폴리곤 형태의 공간 정보
- **좌표계**: EPSG:5179 (Korea 2000)

### 파이프라인 데이터
- **파일**:
  - `data/raw/export_*/V_WTL_PIPE_LM.shp` (파이프라인)
  - `data/raw/export_*/V_WTL_SPLY_LS.shp` (공급관로)
- **주요 필드**:
  - `FTR_IDN`: 시설물 고유 ID
  - `geometry`: 라인 형태의 공간 정보
- **좌표계**: EPSG:5179

## 3. 공간 매칭 프로세스

### 3.1 GeoPandas를 이용한 공간 조인
```python
# 공간 조인 수행
joined = gpd.sjoin(
    pipeline_gdf[["FTR_IDN", "geometry"]],
    soil_gdf[["lithoidx", "geometry"]],
    how="left",
    predicate="intersects"
)
```

- **방법**: Spatial Join (공간 조인)
- **조건**: `intersects` - 파이프라인과 토양 폴리곤이 교차하는 경우
- **결과**: 각 파이프라인이 통과하는 모든 토양 타입 목록

### 3.2 공간 매칭 원리
1. 파이프라인의 라인 지오메트리와 토양의 폴리곤 지오메트리 비교
2. 교차(intersection)가 발생하는 모든 조합 추출
3. 하나의 파이프라인이 여러 토양 타입을 통과할 수 있음

## 4. 중복 처리 방법

### 4.1 문제 상황
- 긴 파이프라인은 여러 토양 타입을 통과
- 각 파이프라인(FTR_IDN)에 하나의 대표 토양 타입 할당 필요

### 4.2 해결 방법: 최빈값(Mode) 선택
```python
for ftr_idn, group in joined.groupby("FTR_IDN"):
    if "lithoidx" in group.columns and not group["lithoidx"].isna().all():
        # 가장 빈번한 lithoidx 선택
        lithoidx_counts = group["lithoidx"].value_counts()
        if not lithoidx_counts.empty:
            most_common_lithoidx = lithoidx_counts.index[0]
            result.append({
                "FTR_IDN": ftr_idn, 
                "lithoidx": most_common_lithoidx
            })
```

### 4.3 선택 기준
1. **빈도 기반**: 파이프라인이 가장 많이 교차하는 토양 타입 선택
2. **동점 처리**: 동일한 빈도일 경우 첫 번째 값 선택 (pandas의 기본 정렬 순서)
3. **NULL 처리**: 매칭되지 않은 경우 빈 값으로 처리

## 5. K_SOIL 값 할당

### 5.1 매핑 테이블
- **파일**: `results/lithoidx_list_with_K_SOIL.csv`
- **구조**:
  ```csv
  lithoidx,lithoname,K_SOIL
  Jgr,화강암,1.0
  Qa,충적층,1.3
  ...
  ```

### 5.2 현재 할당된 K_SOIL 값
- **일반 암반**: K_SOIL = 1.0 (대부분의 암석)
- **충적층(Qa)**: K_SOIL = 1.3 (연약 지반)

### 5.3 병합 과정
```python
# K_SOIL 정보 병합
if k_soil_df is not None:
    result_df = result_df.merge(
        k_soil_df, 
        on="lithoidx", 
        how="left"
    )
```

## 6. 실행 방법

### 6.1 전체 처리
```bash
python src/main5_match_K_soil.py
```

### 6.2 특정 버전만 처리
```bash
python src/main5_match_K_soil.py --version 0520
```

### 6.3 특정 타입만 처리
```bash
# 파이프라인만
python src/main5_match_K_soil.py --type pipe

# 공급관로만
python src/main5_match_K_soil.py --type supply
```

## 7. 출력 파일

### 7.1 파일 위치 및 형식
- **위치**: `results/` 디렉토리
- **명명 규칙**: `{version}_{type}_soil.csv`
  - 예: `0520_pipe_soil.csv`, `0520_supply_soil.csv`

### 7.2 출력 컬럼
| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| FTR_IDN | 시설물 고유 ID | 490041 |
| lithoidx | 암상 인덱스 | Km1 |
| lithoname | 암상명 | 경상누층군신동층군낙동층 |
| K_SOIL | 토양 계수 | 1.0 |

### 7.3 통계 정보 (콘솔 출력)
```
CSV 저장 완료: results/0520_pipe_soil.csv
  - 총 1234개 FTR_IDN
  - 매칭된 항목: 1200개
  - 매칭 안됨: 34개
```

## 8. K_SOIL 값 수정 방법

### 8.1 수정 절차
1. `results/lithoidx_list_with_K_SOIL.csv` 파일 열기
2. 해당 lithoidx의 K_SOIL 값 수정
3. 파일 저장 (UTF-8 with BOM 인코딩 유지)
4. `main5_match_K_soil.py` 재실행

### 8.2 새로운 암상 추가
```csv
# 예시: 새로운 암상 추가
NEW1,신규암상명,1.5
```

### 8.3 K_SOIL 값 결정 가이드라인
- **1.0**: 단단한 암반 (화강암, 편마암 등)
- **1.1-1.2**: 중간 강도 암반
- **1.3-1.5**: 연약 지반 (충적층, 풍화토 등)
- **1.5 이상**: 매우 연약한 지반

## 9. 주의사항

### 9.1 데이터 처리 한계
- **단순화**: 파이프라인 전체를 하나의 토양 타입으로 대표
- **정확도**: 실제로는 구간별로 다른 토양을 통과하나, 최빈값으로 단순화
- **경계부**: 토양 경계부에서의 세밀한 변화는 반영되지 않음

### 9.2 좌표계 처리
- 모든 데이터는 EPSG:5179로 통일
- 다른 좌표계의 경우 자동 변환되나, 정확도 확인 필요

### 9.3 매칭 실패 원인
- 파이프라인이 토양 데이터 범위 밖에 위치
- 좌표계 불일치로 인한 위치 오류
- 토양 데이터의 공백 지역

## 10. 개선 방향

### 10.1 정밀도 향상
- 파이프라인을 세그먼트로 분할하여 구간별 토양 타입 할당
- 교차 길이를 가중치로 사용한 가중 평균 계산

### 10.2 K_SOIL 값 정밀화
- 토양 물성 데이터 기반 K_SOIL 값 산정
- 현장 측정 데이터와의 보정

### 10.3 시각화
- 파이프라인별 토양 타입 분포 지도
- K_SOIL 값의 공간적 분포 표시