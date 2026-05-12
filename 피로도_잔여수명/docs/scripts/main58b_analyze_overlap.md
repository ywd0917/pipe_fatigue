# main58b_analyze_overlap.py

## 개요
main13c_zone_fatigue_merge 통합 데이터를 사용하여 D_final_org와 잔여수명 기준으로 분류된 위험 파이프의 중복을 분석하고 시각화하는 스크립트

## 주요 기능
- D_final_org 상위 35개 위험 파이프 추출
- remaining_life_years 하위 35개 즉시교체 파이프 추출
- 두 기준의 교집합 파이프 식별
- 파이프 실제 위치 구역(zone) 기반 분석
- 3가지 카테고리별 시각화 (main58만, main58a만, 양쪽 모두)
- Shapefile 기반 실제 파이프 경로 시각화
- 소구역 경계(WEA_SMLZ_AS) 표시

## 데이터 구조 이해
### 이전 방식 (main56 직접 로드)
- 각 파이프가 6개 지역별로 서로 다른 D_final_org 값 보유
- 총 35개 레코드 = 6개 파이프 × 약 6개 지역
- 파이프의 실제 위치와 무관하게 모든 지역 데이터 처리

### 현재 방식 (main13c 통합 데이터) 
- 각 파이프는 실제 위치한 구역의 D_final_org 값만 보유
- zone 컬럼으로 파이프의 물리적 위치 식별
- 더 정확한 위치 기반 피로도 분석

### 데이터 처리 로직
- `filter_and_merge_data()`: D_final 상위 35개와 remaining_life 하위 35개를 **모두 포함**
- 두 집합의 합집합(union)을 시각화 데이터로 사용
- 중복 제거를 통해 동일 파이프는 한 번만 표시
- 이를 통해 3가지 카테고리 (main58_only, main58a_only, overlap) 모두 시각화 가능

## 입력 파일
- `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv` - 통합 피로 데이터 (필수)
  - DATA_SRC: 파이프 타입 (PIPE_LM/SPLY_LS)
  - zone: 파이프가 위치한 구역 (0243/0461/0470/0480/0490/0520)
  - D_final_org: 해당 구역의 피로도 값
  - remaining_life_years: 잔여 수명
- `raw_data/export_shp_*/V_WTL_PIPE_LM.shp` - PIPE_LM shapefile (선택사항)
- `raw_data/export_shp_*/V_WTL_SPLY_LS.shp` - SPLY_LS shapefile (선택사항)
- `raw_data/export_shp_*/WEA_SMLZ_AS.shp` - 소구역 경계 shapefile (선택사항)

## 출력 파일
- `results/main58b_analyze_overlap/overlap_visualization.png` - 통합 시각화 (4개 차트)
- `results/main58b_analyze_overlap/venn_diagram.png` - 벤다이어그램 (선택사항)
- `results/main58b_analyze_overlap/scatter_plot.png` - 산점도
- `results/main58b_analyze_overlap/bar_chart.png` - 지역별 막대 그래프
- `results/main58b_analyze_overlap/geographic_map.png` - 파이프 지리적 분포 맵
- `results/main58b_analyze_overlap/overlap_pipes.csv` - 중복 파이프 목록
- `results/main58b_analyze_overlap/analysis_report.md` - 분석 보고서

## 시각화 차트

### 1. 벤다이어그램
- main58 기준 위험 파이프 집합
- main58a 기준 즉시교체 파이프 집합
- 교집합 영역 표시

### 2. 산점도
- X축: D_final_org 값 (log scale)
- Y축: remaining_life_years 값
- 색상: 카테고리별 구분 (main58만/main58a만/중복)
- 임계선: 상위 35개 최소값 (세로선), 하위 35개 최대값 (가로선)

### 3. 지역별 막대 그래프
- 6개 지역별 (0243, 0461, 0470, 0480, 0490, 0520)
- 스택 바: 3가지 카테고리
- 색상: main58(파란색), main58a(빨간색), 중복(보라색)

### 4. 지리적 분포 맵
- Shapefile에서 로드한 실제 파이프 경로 (LineString)
- 위험 파이프 카테고리별 색상 표시:
  - main58_only: 파란색
  - main58a_only: 빨간색
  - overlap: 보라색
- PIPE_LM (기본 두께) / SPLY_LS (더 얇게)
- 일반 파이프는 회색으로 표시

## 사용 예시

### 기본 실행
```bash
python src/main58b_analyze_overlap.py
```

### 옵션 지정
```bash
python src/main58b_analyze_overlap.py \
    --threshold 0.15 \
    --life-limit 5 \
    --region 0520 \
    --output-dir results/main58b_analyze_overlap
```

## 명령행 옵션
- `--threshold`: D_final_org 임계값 (기본값: 0.15, 현재 미사용 - 상위 35개 자동 선정)
- `--life-limit`: 잔여수명 임계값 (기본값: 5년, 현재 미사용 - 하위 35개 자동 선정)
- `--region`: 분석할 지역 코드 (기본값: 0520)
- `--output-dir`: 출력 디렉토리 (기본값: results/main58b_analyze_overlap)
- `--no-venn`: 벤다이어그램 생성 안 함
- `--no-scatter`: 산점도 생성 안 함
- `--no-bar`: 막대 그래프 생성 안 함

## 색상 설정
```python
PIPE_COLORS = {
    "main58_only": "#0000FF",    # 파란색 (D_final 상위 35개만)
    "main58a_only": "#FF0000",   # 빨간색 (remaining_life 하위 35개만)
    "overlap": "#800080"          # 보라색 (양쪽 모두)
}
```

## 분석 결과 예시
```
=== 중복 분석 결과 ===
- D_final_org 상위 35개: 35개 (최소값: 0.0494)
- remaining_life 하위 35개: 35개 (최대값: 9.35년)
- 중복 파이프: 8개 (22.9% 중복률)

=== 카테고리별 분포 ===
- main58만 해당: 27개
- main58a만 해당: 27개
- 양쪽 모두 해당: 8개

=== 지역별 분포 ===
0243: main58만(6), main58a만(9), 중복(1)
0461: main58만(4), main58a만(0), 중복(1)
0470: main58만(3), main58a만(10), 중복(3)
0480: main58만(0), main58a만(2), 중복(0)
0490: main58만(4), main58a만(6), 중복(1)
0520: main58만(10), main58a만(0), 중복(2)
```

## 의존성
- pandas >= 1.5.0
- numpy >= 1.23.0
- matplotlib >= 3.6.0
- seaborn >= 0.12.0
- geopandas >= 0.13.0
- shapely >= 2.0.0
- matplotlib_venn >= 0.11.0 (선택사항)

## 참고 스크립트
- [main58_analyze_remaining_life.py](main58_analyze_remaining_life.md) - D_final 기준 분석
- [main58a_analyze_remaining_life_by_years.py](main58a_analyze_remaining_life_by_years.md) - 잔여수명 기준 분석
- [main13d_visualize_zone_fatigue.py](main13d_visualize_zone_fatigue.md) - 구역별 파이프 시각화
- [main19_visualize_520_repairs.py](main19_visualize_520_repairs.md) - LineCollection 패턴