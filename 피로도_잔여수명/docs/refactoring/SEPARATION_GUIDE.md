# 코드 분리 수준 가이드

이 문서는 리팩토링 시 적절한 코드 분리 수준을 판단하는 기준을 제공합니다.

## 🎯 핵심 원칙

> **"분리는 가독성과 재사용성을 위한 수단이지 목적이 아니다"**

과도한 분리는 오히려 코드를 이해하기 어렵게 만듭니다. 
적절한 균형점을 찾는 것이 중요합니다.

## 📊 분리 결정 체크리스트

### ✅ 분리가 필요한 경우

| 기준 | 설명 | 예시 |
|------|------|------|
| **재사용성** | 2개 이상의 파일에서 사용 | 한글 폰트 설정, 데이터 로딩 |
| **복잡도** | 20줄 이상의 로직 | 복잡한 데이터 변환, 분석 알고리즘 |
| **독립성** | 명확한 입출력과 단일 책임 | 파일 파싱, 좌표 변환 |
| **테스트 필요성** | 단위 테스트가 필요한 로직 | 계산 로직, 데이터 검증 |
| **도메인 특화** | 특정 도메인의 핵심 규칙 | 피로도 계산, 토양 분석 |

### ❌ 분리가 불필요한 경우

| 기준 | 설명 | 예시 |
|------|------|------|
| **단순 설정** | 1-2줄의 설정 코드 | `plt.figure()`, 변수 초기화 |
| **일회성 사용** | 한 곳에서만 사용되는 5줄 이하 | 간단한 조건문, 출력 포맷 |
| **흐름 제어** | 메인 실행 흐름의 일부 | if __name__ == "__main__" 블록 |
| **직관적 코드** | 함수명보다 코드가 더 명확 | `x * 2`, `data[data > 0]` |

## 🔍 실제 사례 분석

### Case 1: 색상 설정 로직

#### ❌ 과도한 분리
```python
# color_utils.py
def get_zone_color(zone_type):
    colors = {"A": "red", "B": "blue", "C": "green"}
    return colors.get(zone_type, "gray")

# main.py
from color_utils import get_zone_color
color = get_zone_color(zone)  # 오히려 복잡해짐
```

#### ✅ 적절한 처리
```python
# main.py
zone_colors = {"A": "red", "B": "blue", "C": "green"}
color = zone_colors.get(zone, "gray")  # 직관적이고 명확
```

### Case 2: 데이터 처리 로직

#### ✅ 분리가 필요한 경우
```python
# soil_loader.py
def process_soil_data(gdf: gpd.GeoDataFrame, 
                     depth_range: Tuple[float, float]) -> pd.DataFrame:
    """
    토양 데이터를 깊이별로 분석하고 집계
    - 깊이별 필터링
    - 통계 계산
    - 이상치 제거
    - 결과 집계
    """
    # 30줄 이상의 복잡한 처리
    filtered = gdf[gdf['depth'].between(*depth_range)]
    stats = filtered.groupby('soil_type').agg({...})
    # ... 더 많은 처리
    return processed_data

# main.py
soil_analysis = process_soil_data(gdf, (0, 100))
```

### Case 3: 시각화 설정

#### ❌ 과도한 분리
```python
# viz_config.py
class PlotConfig:
    def __init__(self):
        self.figsize = (12, 8)
        self.dpi = 100
        self.title_size = 14
    
    def create_figure(self):
        return plt.figure(figsize=self.figsize, dpi=self.dpi)

# main.py
config = PlotConfig()
fig = config.create_figure()  # 불필요한 추상화
```

#### ✅ 적절한 수준
```python
# visualization_utils.py
def setup_korean_plot(title: str, figsize=(12, 8)):
    """한글 제목과 기본 설정을 포함한 플롯 생성"""
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title(title, fontsize=14)
    # 한글 폰트 설정 등 공통 작업
    return fig, ax

# main.py
fig, ax = setup_korean_plot("토양 분석 결과")  # 의미 있는 추상화
```

## 📐 분리 수준 결정 플로우차트

```
코드 블록 발견
    ↓
재사용 가능한가? ─Yes→ 모듈로 분리
    ↓ No
20줄 이상인가? ─Yes→ 함수로 분리 검토
    ↓ No           ↓
테스트 필요한가? ─Yes─┘
    ↓ No
현재 위치 유지
```

## 💡 실용적 조언

1. **의심스러울 때는 분리하지 마세요**
   - 나중에 필요하면 분리할 수 있습니다
   - 조기 추상화는 잘못된 추상화로 이어집니다

2. **실제 중복이 발생할 때까지 기다리세요**
   - 첫 번째 사용: 인라인 유지
   - 두 번째 사용: 분리 고려
   - 세 번째 사용: 확실히 분리

3. **함수명이 코드보다 길다면 분리하지 마세요**
   ```python
   # Bad
   def calculate_double(x):
       return x * 2
   
   # Good - 그냥 인라인으로
   result = value * 2
   ```

4. **컨텍스트를 고려하세요**
   - 관련 코드가 가까이 있으면 이해하기 쉽습니다
   - 너무 많은 파일 간 이동은 가독성을 해칩니다

## 📏 도메인 모듈 관리 전략

### 단일 파일 우선 원칙

특정 도메인의 특화 코드는 **처음에는 하나의 파일로 시작**하는 것이 좋습니다.

```python
# soil_loader.py - 토양 관련 모든 로직을 하나로
def load_soil_data(...): ...
def process_soil_layers(...): ...
def analyze_soil_composition(...): ...
def visualize_soil_data(...): ...
```

### 파일 분리 시점

다음 기준 중 하나라도 해당하면 분리를 고려하세요:

| 기준 | 임계값 | 분리 방법 |
|------|--------|----------|
| **파일 크기** | 300줄 초과 | 기능별로 분리 |
| **함수 개수** | 10개 초과 | 역할별로 분리 |
| **클래스 크기** | 200줄 초과 | 책임별로 분리 |
| **Import 복잡도** | 순환 참조 발생 | 의존성 정리 |

### 분리 예시

```python
# Before: soil_loader.py (400줄)
# 모든 토양 관련 로직이 한 파일에

# After: 기능별 분리
soil/
├── __init__.py
├── loader.py      # 데이터 로딩 (100줄)
├── processor.py   # 데이터 처리 (150줄)
└── analyzer.py    # 분석 로직 (150줄)
```

### 점진적 확장 패턴

```
1단계: soil_loader.py (단일 파일)
   ↓ (300줄 초과 시)
2단계: soil_loader.py + soil_analyzer.py
   ↓ (더 복잡해지면)
3단계: soil/ 폴더로 모듈화
```

## 🎯 목표

리팩토링의 목표는 **"완벽한 분리"가 아닌 "이해하기 쉬운 코드"** 입니다.

- 메인 함수를 읽으면 전체 흐름이 보여야 합니다
- 세부 구현이 궁금할 때만 모듈을 봐도 충분해야 합니다
- 디버깅할 때 여러 파일을 오가지 않아도 되어야 합니다
- **시작은 단순하게, 필요할 때 분리하세요**