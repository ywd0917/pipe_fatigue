# main13f: K_repair_per_m 상위 파이프 시각화

**파일명**: `main13f_visualize_high_k_repair.py`

## 📋 개요
K_repair_per_m 값이 가장 높은 파이프들을 개별적으로 시각화하여 비정상적으로 높은 수치가 정상적인지 확인하는 스크립트입니다.

## 🎯 목적
- **K_repair 이상치 검증**: 지나치게 높아 보이는 K_repair_per_m 값이 정상적인지 시각적으로 확인
- **누수 패턴 분석**: 각 파이프 주변 30m 내 누수 지점의 공간적 분포 파악
- **클러스터 식별**: 누수 클러스터 위치 및 밀도 분석
- **개별 파이프 진단**: 상위 파이프별 상세 분석 자료 제공

## 🚀 사용법

### 기본 실행
```bash
# PIPE_LM 상위 5개 파이프 시각화
python src/main13f_visualize_high_k_repair.py

# SPLY_LS 상위 3개 파이프 시각화
python src/main13f_visualize_high_k_repair.py --pipe-type SPLY_LS --top-n 3

# 클러스터 표시 포함
python src/main13f_visualize_high_k_repair.py --show-clusters

# 사용자 정의 설정
python src/main13f_visualize_high_k_repair.py \
  --pipe-type PIPE_LM \
  --top-n 10 \
  --distance 50 \
  --show-clusters \
  --cluster-radius 15 \
  --scale 1.5
```

## ⚙️ 명령줄 옵션

| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--pipe-type` | str | `PIPE_LM` | 파이프 종류 (PIPE_LM, SPLY_LS) |
| `--top-n` | int | `5` | 상위 N개 파이프 선택 |
| `--distance` | float | `30.0` | 누수 지점 매칭 거리 (미터) |
| `--show-clusters` | flag | `False` | 누수 클러스터 표시 여부 |
| `--cluster-radius` | float | `10.0` | 클러스터 반경 (미터) |
| `--output-dir` | Path | 자동 설정 | 출력 디렉토리 |
| `--scale` | float | `1.0` | 이미지 크기 배율 |
| `--debug` | flag | `False` | 디버그 모드 |

## 📥 입력 파일

### 1. K_repair 데이터 (main13a 결과)
- `results/main13a_k_repair/repair_pipe_lm.csv`: PIPE_LM K_repair 결과
- `results/main13a_k_repair/repair_sply_ls.csv`: SPLY_LS K_repair 결과
- **핵심 컬럼**: `FTR_IDN`, `pipe_length`, `K_repair`, `K_repair_per_m`

### 2. 파이프 Shapefile
- `data/raw/export_shp_*0520*/V_WTL_PIPE_LM.shp`: PIPE_LM geometry
- `data/raw/export_shp_*0520*/V_WTL_SPLY_LS.shp`: SPLY_LS geometry
- **핵심 컬럼**: `FTR_IDN`, `geometry`

### 3. 누수 위치 데이터
- `results/main13_crop_520/누수공사_통합_520_위치추가.csv`: 통합 누수 데이터
- **핵심 컬럼**: `파일타입`, `위도`, `경도`

## 📤 출력 파일

### 디렉토리 구조
```
results/main13f_high_k_repair/
├── PIPE_LM_top5/                    # PIPE_LM 상위 5개 시각화
│   ├── rank1_FTR_IDN_xxxxx.png     # 1위 파이프 시각화
│   ├── rank2_FTR_IDN_xxxxx.png     # 2위 파이프 시각화
│   ├── rank3_FTR_IDN_xxxxx.png     # 3위 파이프 시각화
│   ├── rank4_FTR_IDN_xxxxx.png     # 4위 파이프 시각화
│   └── rank5_FTR_IDN_xxxxx.png     # 5위 파이프 시각화
├── SPLY_LS_top5/                   # SPLY_LS 상위 5개 시각화
│   └── ...
├── PIPE_LM_high_k_repair_report.md # PIPE_LM 분석 보고서
└── SPLY_LS_high_k_repair_report.md # SPLY_LS 분석 보고서
```

### 시각화 이미지 내용
- **파이프**: 빨간색 굵은 선 (linewidth=3)
- **30m 버퍼**: 연한 노란색 투명 영역
- **누수 지점**: 유형별 색상 구분 (config.py의 REPAIR_COLORS)
  - 지상누수: #4ECDC4 (청록색)
  - 지하누수: #45B7D1 (하늘색)  
  - 긴급공사: #FF6B6B (연한 빨간색)
  - 관리대장: #FFA500 (주황색)
- **클러스터 원**: 노란색 배경, 주황색 점선 테두리
- **통계 정보 박스**: 좌측 상단에 K_repair 정보 표시

### 분석 보고서 내용
- **상위 파이프 목록**: 순위, FTR_IDN, 길이, K_repair, K_repair_per_m
- **통계 요약**: 평균값, 최댓값, 분포 정보
- **시각화 이미지**: 각 파이프별 이미지 링크
- **분석 결과**: 이상치 파이프 식별 및 권고사항

## ✨ 주요 기능

### 1. 데이터 로드 및 전처리
- main13a 결과 CSV에서 K_repair 데이터 로드
- Export 디렉토리에서 파이프 shapefile 자동 탐색 및 로드
- 누수 위치 데이터 로드 및 좌표계 변환 (WGS84 → EPSG:5179)

### 2. 상위 파이프 선택
```python
def find_top_k_repair_pipes(k_repair_df, top_n):
    # K_repair_per_m 기준 내림차순 정렬
    top_pipes = k_repair_df.nlargest(top_n, "K_repair_per_m")
    return top_pipes
```

### 3. 공간 분석
- **주변 누수 탐지**: 파이프 중심에서 지정 거리 내 누수 지점 검색
- **클러스터 탐지**: STRtree 기반 효율적인 공간 인덱싱으로 누수 클러스터 식별

### 4. 시각화
- **개별 파이프 시각화**: 각 파이프마다 독립적인 이미지 생성
- **다중 레이어 표시**: 버퍼, 파이프, 누수 지점, 클러스터 순서대로 표시
- **정보 오버레이**: 파이프 정보, 누수 통계, 범례 표시

### 5. 보고서 생성
- **마크다운 형식**: 구조화된 분석 보고서
- **이미지 연동**: 시각화 결과와 연결된 종합 보고서
- **권고사항 제시**: K_repair 이상치에 대한 실행 가능한 권고안

## 🎨 시각화 스타일 (visualization_rules.md 준수)

### 점(Point) 표시
- **크기**: 50 (고정)
- **투명도**: 0.8
- **엣지 색상**: white, 너비 0.5

### 클러스터 원
- **반경**: 10m (사용자 설정 가능)
- **배경색**: yellow, 투명도 0.2
- **테두리**: orange 점선, 너비 1

### 레이어 순서 (zorder)
1. 30m 버퍼: zorder=1
2. 클러스터 원: zorder=2  
3. 파이프: zorder=3
4. 누수 지점: zorder=4
5. 클러스터 텍스트: zorder=5

## 📊 사용 시나리오

### 시나리오 1: PIPE_LM 이상치 조사
```bash
# 1. K_repair_per_m 상위 10개 PIPE_LM 시각화
python src/main13f_visualize_high_k_repair.py --pipe-type PIPE_LM --top-n 10

# 2. 보고서에서 매우 높음(>1.0) 파이프 식별
# 3. 각 시각화 이미지에서 누수 패턴 분석
# 4. 클러스터가 있는 경우 집중 관리 계획 수립
```

### 시나리오 2: 짧은 파이프의 높은 K_repair 검증
```bash
# 짧은 거리에서 높은 K_repair가 나온 경우 검증
python src/main13f_visualize_high_k_repair.py \
  --pipe-type SPLY_LS \
  --top-n 5 \
  --distance 20 \
  --show-clusters
```

### 시나리오 3: 클러스터 중심 분석
```bash
# 클러스터 표시로 누수 집중 지역 분석
python src/main13f_visualize_high_k_repair.py \
  --show-clusters \
  --cluster-radius 15
```

## 🔗 관련 문서
- [main13a_calculate_k_repair.py](main13a_calculate_k_repair.md) - K_repair 계산 (선행 작업)
- [visualization_rules.md](../visualization_rules.md) - 시각화 스타일 가이드
- [main13_crop_520.py](main13_crop_520.md) - 520 지역 누수 데이터 생성

## 📈 성능 및 제약사항

### 성능 지표
- **실행 시간**: 파이프 5개 기준 약 30초-1분
- **메모리 사용량**: 약 200-500MB (데이터 크기에 따라)
- **출력 이미지**: PNG 형식, 300 DPI 고해상도

### 제약사항
- main13a 실행 결과가 선행 필요
- 파이프 shapefile과 K_repair 데이터의 FTR_IDN 일치 필요
- 누수 위치 데이터의 좌표 정확도에 의존

## 💡 해석 가이드

### K_repair_per_m 수치 해석
- **> 1.0**: ⚠️ 매우 높음 - 1미터당 1회 이상 재작업, 즉시 점검 필요
- **0.5-1.0**: 🟡 높음 - 정기 점검 및 예방 정비 고려  
- **0.1-0.5**: 🟢 보통 - 일반적인 관리 수준
- **< 0.1**: 🔵 낮음 - 양호한 상태

### 시각화 패턴 해석
1. **집중 클러스터**: 특정 지점 집중 → 지역적 문제 (토양, 교통)
2. **균등 분포**: 파이프 전체 분포 → 파이프 자체 문제 (노후, 재질)
3. **희소 분포**: 소수 누수 → 우발적 사고 가능성

## ⚠️ 주의사항
- **좌표계 일치**: 모든 공간 데이터가 EPSG:5179로 변환되어 처리됨
- **거리 계산**: 미터 단위 유클리드 거리 사용
- **클러스터 탐지**: 단순 거리 기반이므로 복잡한 클러스터는 수동 분석 필요
- **데이터 품질**: 누수 위치 좌표의 정확도가 분석 결과에 직접 영향

---

최종 업데이트: 2025-01-03 (main13f 스크립트 구현)