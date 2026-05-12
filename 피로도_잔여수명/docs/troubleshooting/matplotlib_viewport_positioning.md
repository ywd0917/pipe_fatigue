# Matplotlib 뷰포트 위치 문제 해결 가이드

## 문제 설명

### 증상
`main12_draw_repair2.py` 스크립트에서 `--bounds-type` 옵션을 사용하여 특정 복구 유형(예: ground, underground)의 데이터만으로 표시 영역을 설정할 때, 그래프가 Figure의 우하단 구석으로 밀려나는 현상이 발생했습니다.

```bash
# 문제 발생 명령
python src/main12_draw_repair2.py --bounds-type ground
```

### 영향받은 스크립트
- `src/main12_draw_repair2.py`
- 특히 `plot_repair2_locations_ultra_fast()` 함수

### 시각적 증상
```
의도한 레이아웃:                    실제 발생한 레이아웃:
┌─────────────────────────┐        ┌─────────────────────────┐
│                         │        │                         │
│    ┌─────────────┐     │        │                         │  
│    │   그래프    │     │        │                         │
│    │   (중앙)    │     │        │              ┌──────┐   │
│    └─────────────┘     │        │              │그래프│   │
│                         │        └──────────────└──────┘───┘
└─────────────────────────┘                          ↑ 우하단
```

## 근본 원인 분석

### 1. 문제 발생 메커니즘

문제의 근본 원인은 **matplotlib의 레이아웃 시스템과 aspect ratio 설정 간의 상호작용**에 있었습니다.

#### 원래 코드의 문제점
```python
# 문제가 있던 코드
ax.set_aspect('equal')  # 기본값: adjustable='datalim'
plt.tight_layout()
plt.savefig(output_path, dpi=300, bbox_inches='tight')
```

### 2. 세 가지 충돌 요소

#### a) `set_aspect('equal')` with default `adjustable='datalim'`
- 이 설정은 데이터 범위(xlim, ylim)를 조정하여 aspect ratio를 맞춥니다
- 지도 데이터처럼 x, y 범위가 크게 다른 경우, matplotlib이 aspect ratio를 맞추기 위해 데이터 영역을 확장하려 합니다
- 좌표계 데이터 예시:
  - X 범위: 1077000-1113000 (약 36,000)
  - Y 범위: 1735000-1778000 (약 43,000)

#### b) `plt.tight_layout()`
- Figure 내의 모든 요소(axes, labels, title)를 자동으로 재배치
- Axes의 위치와 크기를 조정하여 여백을 최소화
- aspect ratio가 설정된 상태에서 axes를 재배치하면 예상치 못한 위치로 이동

#### c) `bbox_inches='tight'`
- 저장 시 Figure의 빈 공간을 제거하고 내용물만 저장
- 이미 tight_layout으로 변형된 axes를 다시 한 번 조정
- 결과적으로 axes가 우하단으로 밀려남

### 3. 문제 발생 과정 (상세)

1. **초기 상태**: 16x12 Figure에 axes 생성
2. **데이터 플롯 후 xlim/ylim 설정**: 지상누수 데이터만의 범위로 축소
3. **aspect='equal' 적용**: x, y 축 비율을 1:1로 맞추려 시도
4. **tight_layout()**: axes를 Figure 중앙에 배치하려 하지만, aspect ratio 때문에 실패
5. **bbox_inches='tight'**: 빈 공간 제거하면서 axes를 다시 이동
6. **결과**: 그래프가 우하단 구석으로 밀려남

### 4. 왜 우하단으로 밀렸나?

지상누수 데이터의 경우:
- X 범위: 1077457 ~ 1113767 (폭: 36,310)
- Y 범위: 1735040 ~ 1778358 (폭: 43,318)
- Y 범위가 X보다 약 1.2배 큼

Figure 크기는 16:12 비율인데, 데이터는 Y가 더 긴 형태입니다.

#### 문제 발생 순서:

1. **`set_aspect('equal')`** 적용 시:
   - Matplotlib이 1:1 비율을 맞추기 위해 X 또는 Y 범위를 확장
   - 하지만 axes box 크기는 Figure 내에서 고정

2. **`tight_layout()`** 호출 시:
   - Axes를 Figure 중앙에 배치하려 시도
   - 그런데 aspect ratio 제약 때문에 axes가 정상 위치에서 벗어남
   - **axes의 anchor point가 우하단으로 이동**

3. **`bbox_inches='tight'`** 저장 시:
   - Figure의 빈 공간을 잘라내면서
   - 이미 우하단으로 이동한 axes 위치가 고정됨

### 5. adjustable 파라미터의 차이

- **`adjustable='datalim'`** (기본값):
  - 데이터 limits(xlim, ylim)를 변경하여 aspect ratio 맞춤
  - 우리가 설정한 bounds를 무시하고 확장할 수 있음
  
- **`adjustable='box'`**:
  - Axes box의 크기를 조정하여 aspect ratio 맞춤
  - 데이터 limits는 그대로 유지
  - 지도 시각화에 적합

## 해결 방법

### 수정된 코드
```python
# 1. limits 설정 후 aspect ratio 설정
ax.set_xlim(x_min - x_margin, x_max + x_margin)
ax.set_ylim(y_min - y_margin, y_max + y_margin)

# 2. adjustable='box'로 axes box 자체를 조정
ax.set_aspect('equal', adjustable='box')  # 핵심 변경!

# 3. tight_layout 대신 수동으로 여백 조정
plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

# 4. bbox_inches='tight' 제거
plt.savefig(output_path, dpi=300)  # bbox_inches 없음
```

### 해결책이 작동한 이유

- `adjustable='box'`: 데이터 범위는 그대로 두고, **axes box 크기를 조정**
- `subplots_adjust()`: axes 위치를 **명시적으로 중앙에 고정**
- `bbox_inches` 제거: 추가적인 자동 조정 방지

이렇게 하면 axes가 Figure의 중앙에 안정적으로 위치하게 됩니다.

## 테스트 코드

문제를 재현하고 해결책을 검증하기 위한 테스트 코드:

```python
import matplotlib.pyplot as plt
import numpy as np

def test_viewport_issue():
    """문제 재현 테스트"""
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # 실제 데이터와 유사한 범위
    x_min, x_max = 1077457.14, 1113767.10
    y_min, y_max = 1735040.19, 1778358.70
    
    # 샘플 데이터
    np.random.seed(42)
    x = np.random.uniform(x_min, x_max, 100)
    y = np.random.uniform(y_min, y_max, 100)
    
    ax.scatter(x, y, s=20, c='purple', alpha=0.5)
    
    # 문제가 있던 방식
    ax.set_aspect('equal')  # adjustable='datalim' (기본값)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    
    plt.tight_layout()
    plt.savefig('problem.png', dpi=100, bbox_inches='tight')
    plt.close()

def test_viewport_fixed():
    """해결된 코드 테스트"""
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # 실제 데이터와 유사한 범위
    x_min, x_max = 1077457.14, 1113767.10
    y_min, y_max = 1735040.19, 1778358.70
    
    # 샘플 데이터
    np.random.seed(42)
    x = np.random.uniform(x_min, x_max, 100)
    y = np.random.uniform(y_min, y_max, 100)
    
    ax.scatter(x, y, s=20, c='green', alpha=0.5)
    
    # 해결된 방식
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal', adjustable='box')  # 핵심!
    
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    plt.savefig('fixed.png', dpi=100)  # bbox_inches 제거
    plt.close()
```

## 주요 교훈

1. **지도 시각화에서는 `adjustable='box'` 사용**: 지리 좌표계 데이터는 x, y 스케일이 다르므로 box 조정이 적합
2. **자동 레이아웃 기능 신중히 사용**: `tight_layout()`과 `bbox_inches='tight'`는 편리하지만 예상치 못한 부작용 가능
3. **aspect ratio 설정 순서 중요**: limits 설정 후 aspect ratio 적용
4. **명시적 제어 선호**: 자동 조정보다 `subplots_adjust()`로 명시적 제어가 안정적

## 관련 이슈 및 PR

- Issue #20: Add display bounds option to main12_draw_repair2.py
- PR #21: feat: add --bounds-type option for viewport control

## 참고 자료

- [Matplotlib aspect ratio documentation](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.set_aspect.html)
- [Understanding matplotlib's coordinate systems](https://matplotlib.org/stable/tutorials/advanced/transforms_tutorial.html)