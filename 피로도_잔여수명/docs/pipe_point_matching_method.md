# 파이프-점 매칭 방법론

파이프(LineString)와 점(Point) 위치 간의 공간적 매칭을 수행하는 방법론에 대한 상세 가이드입니다.

## 📋 목차

1. [개요](#개요)
2. [매칭 방식 비교](#매칭-방식-비교)
3. [최단거리 방식 구현](#최단거리-방식-구현)
4. [성능 최적화](#성능-최적화)
5. [사용 예시](#사용-예시)
6. [주의사항](#주의사항)

## 개요

파이프 네트워크와 점 데이터(재작업 위치, 밸브, 소화전 등)를 매칭하는 것은 인프라 분석의 핵심 작업입니다. 정확한 매칭 방식의 선택은 분석 결과의 신뢰성에 직접적인 영향을 미칩니다.

### 주요 적용 사례
- 재작업 위치와 파이프 매칭 (main14b, main14c)
- 파이프별 재작업 횟수 계산 (main13a)
- 인프라 상관관계 분석 (main19)

## 매칭 방식 비교

### 1. 중심점 방식 (Centroid Method) ❌

```python
# 파이프를 중심점으로 변환
pipe_centroid = pipe.geometry.centroid
distance = pipe_centroid.distance(point)
```

**문제점:**
- 긴 파이프(600m+)의 경우 심각한 왜곡 발생
- 파이프 끝부분 근처 점들이 매칭에서 제외됨
- 실제 거리와 계산 거리의 차이가 매우 큼

**예시:**
```
600m 파이프:
- 시작점 근처 재작업: 실제 5m → 계산 295m (59배 오차)
- 끝점 근처 재작업: 실제 8m → 계산 292m (36배 오차)
```

### 2. 버퍼 방식 (Buffer Method) ⚠️

```python
# 파이프 주변에 버퍼 생성
pipe_buffer = pipe.geometry.buffer(distance_threshold)
if point.within(pipe_buffer):
    # 매칭 성공
```

**문제점:**
- 긴 파이프가 과도하게 넓은 영역 커버
- 중복 카운트 발생 (여러 파이프가 같은 점 포함)
- 670m 파이프 + 30m 버퍼 = 약 40,200m² 영역

### 3. 최단거리 방식 (Shortest Distance Method) ✅

```python
# Shapely의 distance 메서드 사용
distance = pipe_linestring.distance(point)
```

**장점:**
- LineString의 모든 세그먼트 고려
- 점에서 선까지의 실제 최단거리 계산
- 파이프 길이와 무관하게 정확한 거리
- Shapely 내장 최적화로 빠른 계산

## 최단거리 방식 구현

### 기본 구현

```python
import geopandas as gpd
from shapely.geometry import Point

def match_point_to_pipes(
    point: Point,
    pipes_gdf: gpd.GeoDataFrame,
    distance_threshold: float
) -> dict:
    """점과 파이프 매칭 - 최단거리 방식"""
    
    matches = []
    for idx, pipe in pipes_gdf.iterrows():
        # Shapely의 distance 메서드 - 자동으로 최단거리 계산
        distance = pipe.geometry.distance(point)
        
        if distance <= distance_threshold:
            matches.append({
                'pipe_id': pipe['FTR_IDN'],
                'distance': distance,
                'pipe_data': pipe
            })
    
    # 거리순 정렬
    matches.sort(key=lambda x: x['distance'])
    return matches
```

### STRtree를 사용한 최적화

```python
from shapely.strtree import STRtree

def match_points_to_pipes_optimized(
    points_gdf: gpd.GeoDataFrame,
    pipes_gdf: gpd.GeoDataFrame,
    distance_threshold: float
) -> pd.DataFrame:
    """대량 점 데이터의 효율적 매칭"""
    
    # 공간 인덱스 생성
    pipe_tree = STRtree(pipes_gdf.geometry.tolist())
    
    matched_data = []
    for idx, point_row in points_gdf.iterrows():
        point = point_row.geometry
        
        # 거리 임계값보다 넓은 버퍼로 후보 필터링
        buffer = point.buffer(distance_threshold * 1.5)
        candidate_indices = pipe_tree.query(buffer)
        
        # 실제 거리 계산 (후보만)
        for pipe_idx in candidate_indices:
            pipe = pipes_gdf.iloc[pipe_idx]
            distance = pipe.geometry.distance(point)
            
            if distance <= distance_threshold:
                matched_data.append({
                    'point_id': idx,
                    'pipe_id': pipe['FTR_IDN'],
                    'distance': distance
                })
    
    return pd.DataFrame(matched_data)
```

## 성능 최적화

### 1. 좌표계 통일

```python
# EPSG:5179 (미터 단위) 사용
points_gdf = points_gdf.to_crs("EPSG:5179")
pipes_gdf = pipes_gdf.to_crs("EPSG:5179")
```

### 2. 공간 인덱싱

- **STRtree**: O(n×m) → O(n×log(m))
- **cKDTree**: 점 데이터 전용 최적화

### 3. 벡터화 연산

```python
# NumPy 벡터화로 거리 계산
import numpy as np

distances = np.array([
    pipe.geometry.distance(point) 
    for pipe in pipes_gdf.geometry
])
within_threshold = distances <= distance_threshold
matched_pipes = pipes_gdf[within_threshold]
```

## 사용 예시

### main14b: 재작업 클러스터와 파이프 매칭

```python
# 10m 클러스터링 후 파이프 매칭
df_clusters = create_repair_clusters(df_repairs)
df_matched = match_clusters_to_pipes(
    df_clusters, 
    gdf_pipes, 
    distance_threshold=30.0  # 30m 임계값
)

# 결과
# - 매칭률: 77.4% (30m)
# - 처리 시간: 0.13초 (4,560개 파이프)
```

### main13a: 파이프별 재작업 횟수 계산

```python
# 각 재작업을 가장 가까운 파이프에 할당
for repair_point in repair_points:
    nearest_pipe = find_nearest_pipe(repair_point, pipes_gdf)
    if nearest_pipe['distance'] <= 30:
        pipe_repair_count[nearest_pipe['id']] += 1
```

## 주의사항

### 1. 거리 임계값 선택

| 임계값 | 매칭률 | 정확도 | 권장 사용 |
|--------|--------|--------|-----------|
| 10m | 84.4% | 높음 | 정밀 분석 |
| 30m | 99.6% | 중간 | **일반 분석** |
| 50m | 100% | 낮음 | 포괄 분석 |

### 2. 파이프 타입별 처리

```python
# PIPE_LM과 SPLY_LS 별도 처리
pipe_lm_matches = match_to_pipes(points, pipe_lm_gdf, 30)
sply_ls_matches = match_to_pipes(points, sply_ls_gdf, 30)

# 가장 가까운 것 선택
if pipe_lm_matches[0]['distance'] < sply_ls_matches[0]['distance']:
    best_match = pipe_lm_matches[0]
else:
    best_match = sply_ls_matches[0]
```

### 3. 메모리 관리

- 대량 데이터(>10,000 파이프)는 청크 단위 처리
- 불필요한 컬럼 제거 후 계산
- 결과를 즉시 디스크에 저장

## 성능 비교

| 방식 | 시간 복잡도 | 4,560개 파이프 | 정확도 |
|------|------------|---------------|--------|
| 중심점 | O(n×m) | 0.08초 | 낮음 |
| 버퍼 | O(n×m) | 1.2초 | 중간 |
| **최단거리** | O(n×m) | 0.25초 | **높음** |
| **최단거리+STRtree** | O(n×log(m)) | **0.13초** | **높음** |

## 관련 스크립트

- `main13a_calculate_k_repair.py`: 파이프별 재작업 횟수 계산
- `main14b_analyze_repair_correlations.py`: 재작업-K-factors 상관관계
- `main14c_subregion_correlations.py`: 하위 지역별 상관관계
- `main19_visualize_520_repairs.py`: 인프라 상관관계 분석

## 참고 자료

- [Shapely Documentation - Distance](https://shapely.readthedocs.io/en/stable/manual.html#object.distance)
- [STRtree Spatial Indexing](https://shapely.readthedocs.io/en/stable/manual.html#str-packed-r-tree)
- [GeoPandas Spatial Joins](https://geopandas.org/en/stable/docs/user_guide/mergingdata.html)

---

최종 업데이트: 2025-08-20