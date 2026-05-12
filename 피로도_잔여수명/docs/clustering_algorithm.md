# 중복 위치 클러스터링 알고리즘 (Union-Find)

## 📋 개요

main12_draw_repair2.py와 main13_crop_520.py에서 사용되는 중복 위치 클러스터링 알고리즘을 설명합니다. 이 알고리즘은 10m 이내의 가까운 점들을 하나의 클러스터로 묶어 중복 작업 위치를 식별합니다.

## 🔍 알고리즘 원리

### Union-Find (Disjoint Set Union) 자료구조

Union-Find는 서로소 집합(disjoint sets)을 효율적으로 관리하는 자료구조입니다.

#### 주요 연산

1. **Find(x)**: 원소 x가 속한 집합의 대표(root)를 찾습니다
2. **Union(x, y)**: x가 속한 집합과 y가 속한 집합을 합칩니다

#### 구현 코드 (main12, main13에서 사용)

```python
def find_duplicate_clusters_ultra_fast(all_data):
    # 1. KDTree로 10m 이내 모든 점 쌍 찾기
    tree = cKDTree(coords_scaled)
    pairs = tree.query_pairs(r=DISTANCE_THRESHOLD, output_type="ndarray")
    
    # 2. Union-Find로 클러스터 구성
    parent = list(range(n))
    
    def find(x: int) -> int:
        if parent[x] != x:
            parent[x] = find(parent[x])  # 경로 압축
        return parent[x]
    
    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # 3. 모든 근접 쌍을 연결
    for i, j in pairs:
        union(i, j)
    
    # 4. 클러스터 구성
    for i in range(n):
        root = find(i)
        cluster_members[root].append(i)
```

## 🎯 알고리즘 특징

### 1. 배타성 (Exclusivity)
**한 점은 정확히 하나의 클러스터에만 속합니다.**

```
점 A는 클러스터 1 또는 클러스터 2 중 하나에만 속함
중복 소속 불가능
```

### 2. 전이성 (Transitivity)
**간접적으로 연결된 점들도 같은 클러스터가 됩니다.**

```
예시:
- A와 B의 거리: 8m (10m 이내)
- B와 C의 거리: 9m (10m 이내)  
- A와 C의 거리: 15m (10m 초과)

결과: A, B, C 모두 같은 클러스터
이유: A-B 연결, B-C 연결 → A-B-C 모두 연결
```

### 3. 체인 효과 (Chain Effect)
**연쇄적으로 연결된 점들이 하나의 큰 클러스터를 형성할 수 있습니다.**

```
A --9m-- B --9m-- C --9m-- D --9m-- E
         모두 하나의 클러스터
(A와 E의 직선거리는 36m이지만 같은 클러스터)
```

## 📊 시간 복잡도

| 단계 | 연산 | 시간 복잡도 |
|------|------|------------|
| KDTree 구축 | 좌표 인덱싱 | O(n log n) |
| 근접 쌍 찾기 | query_pairs | O(n log n) |
| Union-Find | union 연산 | O(α(n)) ≈ O(1) |
| 클러스터 구성 | find 연산 | O(n × α(n)) |
| **전체** | | **O(n log n)** |

*α(n)는 역 아커만 함수로 실질적으로 상수

## 🔄 프로세스 흐름

```
1. 데이터 준비
   ↓
2. 좌표를 미터 단위로 변환 (위도 ×111000, 경도 ×88000)
   ↓
3. KDTree 구축
   ↓
4. 10m 이내 모든 점 쌍 검색
   ↓
5. Union-Find로 점들을 연결
   ↓
6. 각 점의 최종 클러스터 ID 결정
   ↓
7. 2개 이상 점을 가진 클러스터만 반환
```

## 💡 실제 적용 예시

### 입력 데이터
```
지상누수: (37.5665, 126.9780)  # 점 A
지상누수: (37.5665, 126.9781)  # 점 B (A로부터 8m)
지하누수: (37.5666, 126.9781)  # 점 C (B로부터 9m)
긴급공사: (37.5668, 126.9785)  # 점 D (C로부터 30m)
```

### 처리 과정
```
1. KDTree.query_pairs(r=10) 결과:
   - (A, B) 쌍: 8m < 10m ✓
   - (B, C) 쌍: 9m < 10m ✓
   - (C, D) 쌍: 30m > 10m ✗

2. Union-Find 연결:
   - union(A, B) → A와 B 연결
   - union(B, C) → B와 C 연결 (A-B-C 모두 연결됨)

3. 최종 클러스터:
   - 클러스터 1: {A, B, C} - 3개 점
   - 클러스터 없음: {D} - 단독 점
```

### 출력 결과
```python
clusters = {
    0: [
        (37.5665, 126.9780, '지상누수'),
        (37.5665, 126.9781, '지상누수'),
        (37.5666, 126.9781, '지하누수')
    ]
}
# 점 D는 클러스터에 포함되지 않음 (단독)
```

## ⚠️ 주의사항

1. **거리 임계값 선택**: 10m는 도시 환경에서 적절하나, 지역 특성에 따라 조정 필요
2. **체인 효과 관리**: 긴 체인 형성 시 의도하지 않은 큰 클러스터 생성 가능
3. **좌표계 정확도**: WGS84를 미터로 근사 변환 시 약간의 오차 발생

## 🔗 관련 스크립트

- [main12_draw_repair2.py](scripts/main12_draw_repair2.md) - 복구 작업 위치 시각화
- [main13_crop_520.py](scripts/main13_crop_520.md) - 520 지역 중복 분석
- [main18_analyze_duplicate_repairs.py](scripts/main18_analyze_duplicate_repairs.md) - 시간적 중복 분석

## 📚 참고 자료

- [Union-Find 자료구조](https://en.wikipedia.org/wiki/Disjoint-set_data_structure)
- [scipy.spatial.cKDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html)
- [최적화 가이드](OPTIMIZATION_GUIDE.md) - KDTree 사용법