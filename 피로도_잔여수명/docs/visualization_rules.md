# 시각화 출력 규칙

**작성일**: 2025-01-01  
**관련 스크립트**: main12_draw_repair2.py, main13_crop_520.py

## 📋 개요
복구 작업 위치를 지도에 표시할 때 일관된 시각화 스타일을 적용하기 위한 규칙입니다.

## 🎨 점(Point) 표시 규칙

### 기본 속성
- **크기**: 50 (고정)
- **엣지 색상**: white
- **엣지 너비**: 0.5
- **투명도(alpha)**: 0.8

### 색상 코드
복구 작업 유형별 표준 색상 (config.py의 REPAIR_COLORS):
- **지상누수**: #4ECDC4 (청록색)
- **지하누수**: #45B7D1 (하늘색)
- **긴급공사**: #FF6B6B (연한 빨간색)
- **관리대장**: #FFA500 (주황색)

## 🔄 중복 클러스터 표시 규칙

### 클러스터 원
- **반경**: 10m (고정)
- **배경색**: yellow
- **투명도**: 0.2
- **테두리 색상**: orange
- **테두리 스타일**: 점선 (linestyle="--")
- **테두리 너비**: 1

### 중복 횟수 텍스트
- **폰트 크기**: 10
- **폰트 굵기**: bold
- **텍스트 색상**: black
- **배경 박스**:
  - 스타일: round (둥근 모서리)
  - 패딩: 0.05
  - 배경색: white
  - 테두리 색상: darkred
  - 테두리 너비: 0.5
  - 투명도: 0.9

## 📊 레이어 순서 (zorder)
낮은 값이 뒤에, 높은 값이 앞에 표시됩니다:
1. **배경 (MDLZ)**: zorder=0
2. **파이프 네트워크**: zorder=2
3. **클러스터 원**: zorder=2
4. **복구 작업 점**: zorder=3
5. **중복 횟수 텍스트**: zorder=5

## 📐 이미지 크기

### 기본 설정
- **기본 크기**: 16×12 inch (base) × scale 배율
- **DPI**: 300 (고정값)
- **레이아웃 조정**: subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

### --scale 옵션
명령줄에서 이미지 크기를 동적으로 조정할 수 있습니다:
```bash
python src/main12_draw_repair2.py --scale 0.5   # 8×6 inch (작은 크기)
python src/main13_crop_520.py --scale 2         # 32×24 inch (2배 크기)
```

### 스케일 값 예시
- **scale=0.5**: 8×6 inch (2,400×1,800 픽셀) - 작은 크기
- **scale=1**: 16×12 inch (4,800×3,600 픽셀) - 기본값
- **scale=2**: 32×24 inch (9,600×7,200 픽셀) - 2배 크기
- **scale=4**: 64×48 inch (19,200×14,400 픽셀) - 4배 크기
- **scale=8**: 128×96 inch (38,400×28,800 픽셀) - 고해상도

**참고**: scale 값은 양의 실수 모두 가능합니다 (예: 0.25, 1.5, 3.14 등)

### 적용 스크립트
- main12_draw_repair2.py
- main13_crop_520.py

## 🗺️ 좌표계
- **입력 좌표**: EPSG:5179 가 아니면 EPSG:5179로 변환한 후 계산
- **표시 좌표**: EPSG:5179 (Korea 2000 / Central Belt)
- **거리 계산**: 미터 단위

## 📝 범례 표시
- 각 복구 유형별 개수 표시
- 형식: "{유형명} ({개수}건)"
- 위치: 우측 상단

## 📊 통계 정보 박스
- 위치: 좌측 상단
- 내용:
  - MDLZ 지역 정보
  - 총 복구 작업 개수
  - 중복 클러스터 개수
  - 파이프 개수 (있는 경우)

## 🔗 관련 문서
- [main12_draw_repair2.py](scripts/main12_draw_repair2.md) - 전체 지역 시각화
- [main13_crop_520.py](scripts/main13_crop_520.md) - MDLZ 0520 지역 시각화
- [matplotlib 뷰포트 위치 문제 해결](troubleshooting/matplotlib_viewport_positioning.md)

## 💡 적용 예시
```python
# 점 표시
ax.scatter(
    x_coords,
    y_coords,
    s=50,  # 고정 크기
    c=color,
    alpha=0.8,
    edgecolors="white",
    linewidths=0.5,
    zorder=3
)

# 클러스터 원
circle = Circle(
    (x, y),
    10.0,
    facecolor="yellow",
    alpha=0.2,
    edgecolor="orange",
    linewidth=1,
    linestyle="--",
    zorder=2
)

# 중복 횟수 텍스트
ax.text(
    x, y, str(count),
    fontsize=10,
    fontweight="bold",
    color="black",
    ha="center",
    va="center",
    bbox=dict(
        boxstyle="round,pad=0.05",
        facecolor="white",
        edgecolor="darkred",
        linewidth=0.5,
        alpha=0.9
    ),
    zorder=5
)
```

## 🚀 향후 개선 사항
- [ ] 동적 크기 조정 옵션 추가 검토
- [ ] 색상 테마 커스터마이징 기능
- [ ] 인터랙티브 시각화 (plotly) 버전