# 📈 최적화 가이드

Fatigue QGIS 프로젝트의 성능 최적화 기법과 사례를 문서화합니다.

## 목차

1. [공간 데이터 최적화](#공간-데이터-최적화)
2. [main14b/c 최적화 사례](#main14bc-최적화-사례)
3. [최적화 기법 상세](#최적화-기법-상세)
4. [성능 측정 방법](#성능-측정-방법)

---

## 공간 데이터 최적화

### 1. 공간 인덱싱 (Spatial Indexing)

공간 데이터 검색의 시간 복잡도를 개선하는 핵심 기법입니다.

#### cKDTree 사용
```python
from scipy.spatial import cKDTree
import numpy as np

# 좌표 배열 준비
coords = np.array([[x, y] for x, y in zip(df['lon'], df['lat'])])

# KDTree 구축 - O(n log n)
tree = cKDTree(coords)

# 반경 검색 - O(log n)
neighbors = tree.query_ball_point(query_point, r=radius)

# k-최근접 이웃 - O(log n)
distances, indices = tree.query(query_point, k=5)
```

#### 좌표계 변환
지리적 좌표(WGS84)를 투영 좌표(EPSG:5179)로 변환하여 정확한 미터 단위 계산:

```python
import geopandas as gpd
from shapely.geometry import Point

# WGS84 → EPSG:5179 변환
geometry = [Point(lon, lat) for lon, lat in zip(df['경도'], df['위도'])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
gdf = gdf.to_crs("EPSG:5179")  # 한국 TM 좌표계

# 미터 단위 좌표 추출
coords = np.array([[geom.x, geom.y] for geom in gdf.geometry])
```

### 2. 벡터화 (Vectorization)

반복문을 NumPy 벡터 연산으로 대체:

```python
# 비효율적 - O(n)
distances = []
for point in points:
    dist = haversine(center, point)
    distances.append(dist)

# 효율적 - 벡터화
lat_rad = np.radians(points[:, 0])
lon_rad = np.radians(points[:, 1])
dlat = np.radians(points[:, 0] - center[0])
dlon = np.radians(points[:, 1] - center[1])

a = np.sin(dlat/2)**2 + np.cos(np.radians(center[0])) * \
    np.cos(lat_rad) * np.sin(dlon/2)**2
distances = 6371000 * 2 * np.arcsin(np.sqrt(a))
```

---

## main14b/c 최적화 사례

### 문제 상황
- **main14b**: 895개 클러스터 × 4,569개 파이프 = 약 400만 거리 계산
- **main14c**: 3개 지역별 동일 작업 반복
- **실행 시간**: main14b 78초, main14c 60-90초

### 최적화 전 코드
```python
def match_clusters_to_pipes(df_clusters, df_pipes, distance_threshold):
    matched_data = []
    
    # O(n × m) 복잡도
    for _, cluster in tqdm(df_clusters.iterrows(), total=len(df_clusters)):
        pipes_nearby = []
        
        for _, pipe in df_pipes.iterrows():
            # 각 조합마다 거리 계산
            dist = calculate_haversine_distance(
                cluster["avg_lat"], cluster["avg_lon"],
                pipe["위도"], pipe["경도"]
            )
            
            if dist <= distance_threshold:
                pipes_nearby.append(pipe)
        
        # 결과 처리...
    
    return pd.DataFrame(matched_data)
```

### 최적화 후 코드
```python
def match_clusters_to_pipes(df_clusters, df_pipes, distance_threshold):
    # 빈 데이터 처리
    if len(df_clusters) == 0 or len(df_pipes) == 0:
        return pd.DataFrame()
    
    # 1. 좌표 변환 (WGS84 → EPSG:5179)
    pipe_gdf = gpd.GeoDataFrame(
        df_pipes, 
        geometry=[Point(lon, lat) for lon, lat in zip(df_pipes["경도"], df_pipes["위도"])],
        crs="EPSG:4326"
    ).to_crs("EPSG:5179")
    pipe_coords = np.array([[geom.x, geom.y] for geom in pipe_gdf.geometry])
    
    cluster_gdf = gpd.GeoDataFrame(
        df_clusters,
        geometry=[Point(lon, lat) for lon, lat in zip(df_clusters["avg_lon"], df_clusters["avg_lat"])],
        crs="EPSG:4326"
    ).to_crs("EPSG:5179")
    cluster_coords = np.array([[geom.x, geom.y] for geom in cluster_gdf.geometry])
    
    # 2. cKDTree 구축 - O(m log m)
    pipe_tree = cKDTree(pipe_coords)
    
    # 3. 반경 검색 - O(n × log m)
    neighbors = pipe_tree.query_ball_point(cluster_coords, r=distance_threshold, workers=-1)
    
    # 4. 가장 가까운 파이프 찾기
    nearest_dists, nearest_indices = pipe_tree.query(cluster_coords, k=1)
    
    # 5. 결과 처리
    matched_data = []
    for cluster_idx, pipe_indices in enumerate(neighbors):
        if pipe_indices:
            # 매칭된 파이프들 처리...
            pass
    
    return pd.DataFrame(matched_data)
```

### 성능 개선 결과

| 스크립트 | 최적화 전 | 최적화 후 | 개선율 |
|----------|-----------|-----------|--------|
| main14b  | 78초      | 0.31초    | 250배  |
| main14c  | 60-90초   | 0.16초    | 400-500배 |

---

## 최적화 기법 상세

### 1. 시간 복잡도 분석

| 작업 | 단순 구현 | cKDTree | 개선 |
|------|-----------|---------|------|
| 모든 거리 계산 | O(n×m) | - | - |
| Tree 구축 | - | O(m log m) | 1회만 |
| 반경 검색 | O(m) | O(log m) | n번 반복 |
| 전체 | O(n×m) | O(m log m + n log m) | 큰 개선 |

### 2. 메모리 최적화

```python
# 메모리 효율적인 청크 처리
def process_in_chunks(df, chunk_size=1000):
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        yield process_chunk(chunk)

# 결과 병합
results = pd.concat(process_in_chunks(large_df), ignore_index=True)
```

### 3. 병렬 처리

```python
# cKDTree의 내장 병렬 처리
neighbors = tree.query_ball_point(points, r=radius, workers=-1)  # 모든 CPU 코어 사용

# multiprocessing 활용
from multiprocessing import Pool

with Pool() as pool:
    results = pool.map(process_function, data_chunks)
```

---

## 성능 측정 방법

### 1. 시간 측정
```python
import time

start_time = time.time()
# 코드 실행
result = match_clusters_to_pipes(df_clusters, df_pipes, 30.0)
elapsed = time.time() - start_time

print(f"실행 시간: {elapsed:.2f}초")
```

### 2. 프로파일링
```python
import cProfile
import pstats

# 프로파일링 실행
profiler = cProfile.Profile()
profiler.enable()

# 분석할 코드
result = main_function()

profiler.disable()

# 결과 분석
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # 상위 10개 함수
```

### 3. 메모리 프로파일링
```bash
# memory_profiler 설치
pip install memory-profiler

# 데코레이터 사용
from memory_profiler import profile

@profile
def memory_intensive_function():
    # 메모리 사용 추적
    pass

# 실행
python -m memory_profiler script.py
```

### 4. 벤치마크 자동화
```python
def benchmark_function(func, *args, iterations=5):
    """함수 성능 벤치마크"""
    times = []
    
    for _ in range(iterations):
        start = time.time()
        result = func(*args)
        elapsed = time.time() - start
        times.append(elapsed)
    
    return {
        'mean': np.mean(times),
        'std': np.std(times),
        'min': np.min(times),
        'max': np.max(times),
        'result': result
    }

# 사용 예
stats = benchmark_function(match_clusters_to_pipes, df_clusters, df_pipes, 30.0)
print(f"평균 실행시간: {stats['mean']:.2f}초 (±{stats['std']:.2f})")
```

---

## 최적화 체크리스트

### 코드 최적화 전 확인사항
- [ ] 현재 성능 병목 지점 파악 (프로파일링)
- [ ] 시간 복잡도 분석
- [ ] 메모리 사용량 측정
- [ ] 테스트 케이스 준비

### 최적화 기법 적용
- [ ] 공간 인덱싱 (cKDTree, R-tree)
- [ ] 벡터화 (NumPy, Pandas)
- [ ] 병렬 처리 (multiprocessing, joblib)
- [ ] 캐싱 (functools.lru_cache)
- [ ] 청크 처리 (대용량 데이터)

### 최적화 후 검증
- [ ] 결과 정확성 검증
- [ ] 성능 개선 측정
- [ ] 엣지 케이스 테스트
- [ ] 문서화 업데이트

---

## 참고 자료

- [scipy.spatial.cKDTree 문서](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html)
- [GeoPandas 좌표계 변환](https://geopandas.org/en/stable/docs/user_guide/projections.html)
- [NumPy 벡터화](https://numpy.org/doc/stable/user/basics.broadcasting.html)
- [Python 프로파일링](https://docs.python.org/3/library/profile.html)