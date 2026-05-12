# 분석 도구 (Analysis Tools)

피로 손상 분석 시스템의 분석 도구 모음입니다.

## 📁 파일 목록 및 입출력

### 재작업 패턴 상관관계 분석
| 파일명 | 역할 | 입력 | 출력 |
|--------|------|------|------|
| `analyze_duplicate_cnt_jnt_correlation_v2.py` | CNT_JNT와 재작업 상관관계 분석 (통합 버전, 거리 매개변수 지원) | `results/shapefiles/*.shp`, `results/*_520_*.csv` | `results/0520_duplicate_cnt_jnt_analysis_v2.txt`, `*.png` |
| `analyze_repair_d_final_correlation.py` | D_final과 재작업 상관관계 분석 (거리 파라미터 지원, 기본값: 30m) | `data/pipe_fatigue/*.csv`, `results/*_520_*.csv` | `results/0520_repair_d_final_analysis.txt`, `*.png` |
| `analyze_repair_k_factors_correlation.py` | K-factors와 재작업 상관관계 분석 (STD_DIP 포함, 거리 30m) | `data/pipe_fatigue/*.csv`, `results/*_520_*.csv` | `results/0520_repair_k_factors_analysis.txt`, `*.png` |
| `test_coordinates.py` | 좌표계 변환 및 검증 | `results/shapefiles/*.shp` | 콘솔 출력 |

### GIS 데이터 분석
| 파일명 | 역할 | 입력 | 출력 |
|--------|------|------|------|
| `analyze_road_attributes.py` | 도로 속성 분석 | `data/raw/export_shp*/TL_SPRD_MANAGE.shp` | `results/road_attributes_analysis.txt` |
| `check_road_fields.py` | 도로 필드 검증 | 상동 | 콘솔 출력 |
| `ftr_cde.py` | FTR_CDE 코드 매핑 | `data/raw/export_shp*/*.shp` | 콘솔 출력 |
| `ftr_cde_distribution.py` | FTR_CDE 분포 통계 | 상동 | 통계 차트 |
| `valve_codes.py` | 밸브 코드 분석 | `data/raw/export_shp*/WTL_VALV_PS.shp` | 콘솔 출력 |
| `valve_ftc_relationship.py` | 밸브 FTC 관계 분석 | 상동 | 콘솔 출력 |
| `valve_material_relationship.py` | 밸브 재료 분석 | 상동 | 분석 리포트 |

### 파이프 세그먼트 분석
| 파일명 | 역할 | 입력 | 출력 |
|--------|------|------|------|
| `analyze_pipe_segments.py` | 파이프 세그먼트 길이 통계 | `data/raw/export_shp*/V_WTL_*.shp` | `results/pipe_segment_analysis/*.csv` |
| `visualize_short_segments.py` | 1m 이하 세그먼트 시각화 | 상동 | `results/pipe_segment_analysis/pipe_lm_short_segments_*.png` |
| `visualize_short_segments_hotspots.py` | 짧은 세그먼트 핫스팟 | 상동 | 핫스팟 맵 |
| `find_semicircular_segments.py` | 반원형 구조 탐지 | 상동 | `results/pipe_segment_analysis/pipe_lm_semicircular_*.png` |
| `find_small_semicircular_segments.py` | 소형 반원형 탐지 (0.5m 이하) | 상동 | 콘솔 출력 |
| `visualize_all_semicircles.py` | 반원형 통합 시각화 | 상동 | 분포도 |
| `verify_high_cnt_jnt.py` | 높은 CNT_JNT 검증 | `results/shapefiles/*.shp` | `results/high_cnt_jnt_verification/*.png` |

### 지오코딩 분석
| 파일명 | 역할 | 입력 | 출력 |
|--------|------|------|------|
| `analyze_geocoding_cache.py` | 캐시 파일 분석 | `results/geocoding_cache.db` | 분석 리포트 |
| `analyze_failed_addresses.py` | 실패 패턴 분석 | 상동 | 패턴 분석 결과 |
| `analyze_geocoding_failures.py` | 실패 심화 분석 | 상동 | 콘솔 출력 |
| `retry_failed_geocoding.py` | Kakao API 재시도 | 상동 | 업데이트된 캐시 |
| `retry_failed_geocoding_naver.py` | Naver API 재시도 | 상동 | 업데이트된 캐시 |

## 🔄 사용 방법

### 개별 스크립트 실행

#### GIS 데이터 분석
```bash
# 프로젝트 루트에서 실행
python src/analysis/analyze_road_attributes.py          # 도로 속성 분석
python src/analysis/ftr_cde.py                         # FTR_CDE 코드 분석
python src/analysis/ftr_cde_distribution.py            # FTR_CDE 분포 분석
python src/analysis/check_road_fields.py               # 도로 필드 검증
python src/analysis/valve_codes.py                     # 밸브 코드 분석
python src/analysis/valve_ftc_relationship.py          # 밸브 FTC 관계 분석
python src/analysis/valve_material_relationship.py     # 밸브 재료 관계 분석
```

#### 파이프 세그먼트 분석
```bash
python src/analysis/analyze_pipe_segments.py           # 파이프 세그먼트 길이 분석
python src/analysis/visualize_short_segments.py        # 짧은 세그먼트 시각화
python src/analysis/visualize_short_segments_hotspots.py # 짧은 세그먼트 핫스팟
python src/analysis/find_semicircular_segments.py      # 반원형 세그먼트 탐지
python src/analysis/find_small_semicircular_segments.py # 소형 반원형 분석
python src/analysis/visualize_all_semicircles.py       # 모든 반원형 시각화
python src/analysis/verify_high_cnt_jnt.py             # 높은 CNT_JNT 검증
```

#### 지오코딩 분석
```bash
python src/analysis/analyze_geocoding_cache.py         # 캐시 파일 분석
python src/analysis/analyze_failed_addresses.py        # 실패 주소 패턴 분석
python src/analysis/analyze_geocoding_failures.py      # 지오코딩 실패 심화 분석
python src/analysis/retry_failed_geocoding.py          # Kakao API 재시도
python src/analysis/retry_failed_geocoding_naver.py    # Naver API 재시도
```

#### 재작업 패턴 분석
```bash
python src/analysis/analyze_duplicate_cnt_jnt_correlation_v2.py  # CNT_JNT: 통합 버전 (기본 30m)
python src/analysis/analyze_repair_d_final_correlation.py        # D_final: 피로 손상 상관관계 (기본 30m)
python src/analysis/analyze_repair_k_factors_correlation.py      # K-factors: 7개 위험 요인 상관관계 (STD_DIP 포함)
python src/analysis/test_coordinates.py                          # 좌표계 검증
```

### 주요 실행 스크립트와의 연계

1. **기본 GIS 분석**
   - `main1_read_gis_files.py` → `ftr_cde.py`, `valve_codes.py`, `valve_ftc_relationship.py`

2. **파이프 분석**
   - `main2_draw_zone.py` → `analyze_pipe_segments.py`, `visualize_short_segments.py`, `find_semicircular_segments.py`

3. **도로 분석**
   - `main6_draw_road.py` → `analyze_road_attributes.py`, `check_road_fields.py`
   - `main7_pipe_traffic.py` → `analyze_road_attributes.py`

4. **복구 작업 및 지오코딩**
   - `main11_recovery2_convert_addr2pos.py` → `analyze_geocoding_cache.py`, `analyze_failed_addresses.py`
   - `main9_draw_recovery.py` → 지오코딩 분석 도구들

5. **연결점 검증**
   - `main8_verify_overlap_samples.py` → `verify_high_cnt_jnt.py`
   - `main15_extract_joint_data.py`, `main17_cmp_recovery2.py` → 파이프 세그먼트 및 연결점 분석

6. **재작업 패턴 분석**
   - `main18_analyze_duplicate_repairs.py` → `analyze_duplicate_cnt_jnt_correlation.py`
   - 중복 재작업 위치와 CNT_JNT 상관관계 분석

### 분석 워크플로우 예시

#### 1. 파이프 세그먼트 종합 분석
```bash
# 1단계: 기본 세그먼트 분석
python src/analysis/analyze_pipe_segments.py

# 2단계: 짧은 세그먼트 시각화
python src/analysis/visualize_short_segments.py

# 3단계: 반원형 패턴 탐지
python src/analysis/find_semicircular_segments.py

# 4단계: 연결점 검증
python src/analysis/verify_high_cnt_jnt.py
```

#### 2. 지오코딩 품질 개선 워크플로우
```bash
# 1단계: 캐시 현황 분석
python src/analysis/analyze_geocoding_cache.py

# 2단계: 실패 패턴 분석
python src/analysis/analyze_failed_addresses.py

# 3단계: 재시도 처리
python src/analysis/retry_failed_geocoding.py
python src/analysis/retry_failed_geocoding_naver.py

# 4단계: 결과 검증
python src/analysis/analyze_geocoding_failures.py
```

#### 3. 재작업 패턴 상관관계 분석
```bash
# 1단계: 파이프 세그먼트 데이터 생성 (사전 준비)
python src/main15_extract_joint_data.py

# 2단계: 중복 재작업 위치 분석
python src/main18_analyze_duplicate_repairs.py

# 3단계: CNT_JNT 상관관계 분석 (통합 버전)
python src/analysis/analyze_duplicate_cnt_jnt_correlation_v2.py            # 기본 30m 반경
python src/analysis/analyze_duplicate_cnt_jnt_correlation_v2.py --distance 20  # 20m 반경
python src/analysis/analyze_duplicate_cnt_jnt_correlation_v2.py --distance 50  # 50m 반경

# 5단계: 피로 손상(D_final) 상관관계 분석
python src/analysis/analyze_repair_d_final_correlation.py        # 기본 30m 반경
python src/analysis/analyze_repair_d_final_correlation.py --distance 10    # 10m 반경
python src/analysis/analyze_repair_d_final_correlation.py --distance 20    # 20m 반경

# 6단계: K-factors (위험 요인) 상관관계 분석
python src/analysis/analyze_repair_k_factors_correlation.py      # 7개 K-factors 분석 (STD_DIP 포함)

# 7단계: 결과 확인
# CNT_JNT 분석 결과:
#   - results/0520_duplicate_cnt_jnt_analysis.txt (V1)
#   - results/0520_duplicate_cnt_jnt_analysis_v2.txt (V2)
#   - results/duplicate_cnt_jnt_*.png
# D_final 분석 결과:
#   - results/0520_repair_d_final_analysis.txt (20m)
#   - results/0520_repair_d_final_analysis_10m.txt (10m)
#   - results/0520_d_final_10m_vs_20m_comparison.txt (비교)
#   - results/repair_d_final_*.png
# K-factors 분석 결과:
#   - results/0520_repair_k_factors_analysis.txt
#   - results/0520_repair_k_factors_matched.csv
#   - results/repair_k_factors_scatter.png (6개 factor 산점도)
#   - results/repair_k_factors_boxplot.png (그룹별 비교)
#   - results/repair_k_factors_heatmap.png (상관계수 히트맵)
```

## 📁 결과 파일

분석 결과는 다음 위치에 저장됩니다:

### 파이프 세그먼트 분석
- `results/pipe_segment_analysis/`: 파이프 세그먼트 분석 결과
  - `pipe_lm_segment_statistics.csv`, `sply_ls_segment_statistics.csv`
  - `pipe_lm_short_segments_*.png`, `pipe_lm_semicircular_*.png`
  - `pipe_lm_hotspots_*.png`

### 지오코딩 분석
- `results/geocoding_analysis/`: 지오코딩 분석 결과
- `results/geocoding_comparison/`: API 비교 분석 결과
- `results/high_cnt_jnt_verification/`: 연결점 검증 결과
  - `connection_analysis_*.png`, `connection_details_*.csv`

### GIS 데이터 분석
- `results/road_attributes_analysis.txt`: 도로 속성 분석 결과
- FTR_CDE 분포 통계 및 밸브 분석 리포트

### 재작업 패턴 분석

#### CNT_JNT 상관관계 분석 결과
- `results/0520_duplicate_cnt_jnt_analysis.txt`: V1 CNT_JNT 상관관계 분석 요약
- `results/0520_duplicate_cnt_jnt_analysis_v2.txt`: V2 CNT_JNT 상관관계 분석 요약  
- `results/0520_duplicate_cnt_jnt_matched.csv`: V1 클러스터-파이프 매칭 데이터
- `results/0520_duplicate_cnt_jnt_matched_v2.csv`: V2 클러스터-파이프 매칭 데이터
- `results/duplicate_cnt_jnt_statistics.csv`: 통계 테이블
- `results/duplicate_cnt_jnt_boxplot.png`: CNT_JNT별 재작업 횟수 박스플롯
- `results/duplicate_cnt_jnt_scatter.png`: CNT_JNT와 재작업 횟수 산점도
- `results/duplicate_cnt_jnt_histogram.png`: 그룹별 CNT_JNT 분포 히스토그램

#### D_final 상관관계 분석 결과
- `results/0520_repair_d_final_analysis.txt`: 20m 반경 분석 요약
- `results/0520_repair_d_final_analysis_10m.txt`: 10m 반경 분석 요약
- `results/0520_d_final_10m_vs_20m_comparison.txt`: 10m vs 20m 상세 비교
- `results/0520_repair_d_final_matched.csv`: 20m 클러스터-파이프 매칭 데이터
- `results/0520_repair_d_final_matched_10m.csv`: 10m 클러스터-파이프 매칭 데이터
- `results/repair_d_final_scatter.png`: 20m 3가지 전략별 산점도
- `results/repair_d_final_scatter_10m.png`: 10m 3가지 전략별 산점도
- `results/repair_d_final_boxplot.png`: 20m 그룹별 D_final 분포 비교
- `results/repair_d_final_boxplot_10m.png`: 10m 그룹별 D_final 분포 비교
- `results/repair_d_final_histogram.png`: 20m D_final 구간별 재작업 분포
- `results/repair_d_final_histogram_10m.png`: 10m D_final 구간별 재작업 분포

#### K-factors 상관관계 분석 결과
- `results/0520_repair_k_factors_analysis.txt`: K-factors 분석 요약
- `results/0520_repair_k_factors_matched.csv`: 클러스터-파이프 매칭 데이터
- `results/repair_k_factors_scatter.png`: 6개 K-factors 산점도 (2x3 그리드)
- `results/repair_k_factors_boxplot.png`: 재작업 빈도별 K-factors 분포 비교
- `results/repair_k_factors_heatmap.png`: K-factors와 재작업 횟수 상관계수 히트맵

## 🛠️ 개발 정보

- **개발 기간**: 2025년 7-8월 (지속적 업데이트)
- **주요 라이브러리**: geopandas, shapely, pandas, numpy, matplotlib, sqlite3, scipy
- **특수 기능**: 반원형 패턴 탐지, 연결점 검증, 지오코딩 재시도, 좌표계 변환
- **코딩 표준**: CODING_STANDARDS.md 참조
- **테스트**: pytest 기반 단위 테스트 (82.13% 커버리지)

## 🔧 분석 도구 특징

### 반원형 패턴 탐지
- **`src.common.semicircle_detection`** 모듈 활용
- 연속된 짧은 세그먼트의 각도 변화 분석
- 최소 3개 세그먼트, 최대 1m 길이 제한
- 90도 이상 회전 패턴 탐지

### 지오코딩 재시도 시스템
- SQLite 캐시 기반 효율적 처리
- API별 최적화된 재시도 전략
- 패턴 기반 전처리 개선
- 성공률 추적 및 모니터링

### 연결점 검증 알고리즘
- 공간 인덱스(STRtree) 활용한 고성능 검색
- 5가지 연결 유형 분류 (끝점, T자, +자, 겹침, 근접)
- tolerance 기반 정밀도 조정
- 상세 시각화 및 CSV 내보내기

## 📝 참고사항

- 모든 분석 도구는 한글 출력을 지원하며 `korean_font_utils` 사용
- 결과 파일은 UTF-8 인코딩으로 저장
- 대용량 데이터 처리 시 메모리 사용량 최적화 적용
- 지오코딩 API 사용 시 요청 제한 및 비용 고려 필요
- 반원형 패턴 분석은 `semicircle_detection` 공통 모듈에 의존
- 공간 분석은 EPSG:5179 좌표계 기준으로 수행

## 📈 재작업 패턴 분석 도구

### CNT_JNT 상관관계 분석 V1 (가장 가까운 파이프)
- **`analyze_duplicate_cnt_jnt_correlation.py`** (2025년 8월 개발)
  - **목적**: 중복 재작업 위치와 파이프 연결점 복잡도(CNT_JNT) 상관관계 분석
  - **기능**: 
    - 0520 지역 복구 데이터와 파이프 데이터 매칭
    - 4회 이상 재작업 그룹과 일반 그룹 간 CNT_JNT 비교
    - 통계적 검정 (t-test, Mann-Whitney U test)
    - 시각화: 박스플롯, 산점도, 히스토그램
    - 좌표계 변환 (EPSG:5179 → WGS84)
  - **연관 스크립트**: `main15_extract_joint_data.py`, `main17_cmp_repair2.py`, `main18_analyze_duplicate_repairs.py`
  - **출력**: 
    - `results/0520_duplicate_cnt_jnt_analysis.txt` - 분석 요약
    - `results/0520_duplicate_cnt_jnt_matched.csv` - 매칭 데이터
    - `results/duplicate_cnt_jnt_*.png` - 시각화 차트
  - **주요 결과**: 
    - 상관계수: -0.109 (음의 상관관계)
    - 100% 매칭률 달성 (251개 클러스터)
    - CNT_JNT가 낮은 곳(1-2)에서 오히려 더 많은 재작업 발생

### CNT_JNT 상관관계 분석 V2 (반경 내 모든 파이프)
- **`analyze_duplicate_cnt_jnt_correlation_v2.py`** (2025년 8월 개발)
  - **목적**: 지정 반경 내 모든 파이프를 고려한 종합적 분석
  - **기능**: 3가지 분석 전략 (최대값, 평균값, 가장 가까운 파이프)
  - **주요 결과 (10m 반경)**:
    - **최대 CNT_JNT 전략**: 상관계수 -0.047
      - 빈번한 재작업 그룹 평균: 3.14
      - 일반 그룹 평균: 3.36
    - **평균 CNT_JNT 전략**: 상관계수 -0.087
      - 빈번한 재작업 그룹 평균: 2.38
      - 일반 그룹 평균: 2.53
    - **가장 가까운 파이프**: 상관계수 -0.077
      - 빈번한 재작업 그룹 평균: 1.86
      - 일반 그룹 평균: 2.22
    - CNT_JNT가 높은 파이프 근처(10m 이내)에서 빈번한 재작업 비율: 3.3%
  - **주요 결과 (20m 반경)**:
    - **최대 CNT_JNT 전략**: 상관계수 -0.045
      - 빈번한 재작업 그룹 평균: 3.89
      - 일반 그룹 평균: 4.00
    - **평균 CNT_JNT 전략**: 상관계수 -0.090
      - 빈번한 재작업 그룹 평균: 2.53
      - 일반 그룹 평균: 2.67
    - **가장 가까운 파이프**: 상관계수 -0.064
      - 빈번한 재작업 그룹 평균: 1.89
      - 일반 그룹 평균: 2.20
    - 매칭률: 86.9% → 98.8% (10m → 20m)
    - CNT_JNT가 높은 파이프 근처(20m 이내)에서 빈번한 재작업 비율: 3.7%
  - **출력**:
    - `results/0520_duplicate_cnt_jnt_analysis_v2.txt` - V2 분석 요약
    - `results/0520_duplicate_cnt_jnt_matched_v2.csv` - V2 매칭 데이터
  - **결론**: 
    - 10m와 20m 모두 CNT_JNT와 재작업 빈도는 음의 상관관계
    - 반경을 20m로 확대해도 결론은 동일
    - **CNT_JNT는 빈번한 재작업의 원인이 아님** - 단순한 연결점에서 더 많은 재작업
    - 다른 요인(파이프 재질, 연령, 토양 조건, 교통량 등) 조사 필요

### 피로 손상(D_final) 상관관계 분석
- **`analyze_repair_d_final_correlation.py`** (2025년 8월 개발, 통합 버전)
  - **목적**: 재작업 위치와 파이프 피로 손상(D_final) 상관관계 분석 
  - **거리 파라미터 지원**: `--distance` 옵션으로 매칭 거리 조정 가능 (기본값: 30m)
  - **기능**:
    - 0520 지역 3개 복구 작업 CSV 파일 통합 분석
    - PIPE_LM과 SPLY_LS 피로 손상 데이터 통합
    - 재작업 위치 지정 반경 내 파이프 검색 (사용자 지정 가능)
    - 3가지 매칭 전략:
      * 가장 가까운 파이프의 D_final
      * 반경 내 최대 D_final
      * 반경 내 평균 D_final (거리 가중)
    - 통계적 검정 및 시각화
  - **연관 데이터**: 
    - `data/pipe_fatigue/fatigue_pipe_lm_by_age.csv`
    - `data/pipe_fatigue/fatigue_sply_ls_by_age.csv`
    - `results/shapefiles/PIPE_LM_JOINT.shp`, `SPLY_LS_JOINT.shp`
  - **출력**:
    - `results/0520_repair_d_final_analysis.txt` - 분석 요약 (기본값 30m)
    - `results/0520_repair_d_final_analysis_[거리]m.txt` - 특정 거리 분석 요약
    - `results/repair_d_final_scatter.png` - 산점도 (기본값)
    - `results/repair_d_final_scatter_[거리]m.png` - 특정 거리 산점도
    - 기타 시각화 파일
  - **주요 결과 (10m vs 20m 비교)**:
    - **매칭률**: 84.1% (10m) → 98.8% (20m)
    - **상관계수 (가장 가까운 파이프)**:
      * 10m: r = -0.0202 (p=0.5806)
      * 20m: r = -0.0245 (p=0.4676)
    - **빈번한 재작업 그룹 D_final 평균**:
      * 10m: 0.007169
      * 20m: 0.007030
    - **높은 D_final 지역 빈번한 재작업**: 
      * 10m: 0% (115개 중 0개)
      * 20m: 0% (138개 중 0개)
    - **결론**: 
      * 반경과 무관하게 피로 손상은 재작업의 원인이 아님
      * 오히려 D_final이 낮은 지역에서 더 많은 재작업 발생

### K-factors 상관관계 분석
- **`analyze_repair_k_factors_correlation.py`** (2025년 8월 개발)
  - **목적**: 재작업 위치와 파이프 K-factors (위험 요인) 상관관계 분석
  - **기능**:
    - 6개 K-factors 종합 분석:
      * K_age: 파이프 연령 계수
      * K_soil: 토양 조건 계수  
      * K_traffic: 교통 하중 계수
      * hoop_stress: 원주 응력
      * K_stress: 응력 계수
      * K_total: 총 위험도 계수
    - 동일한 클러스터링/매칭 방법 (10m 클러스터링, 20m 매칭)
    - 각 K-factor별 3가지 전략 적용 (nearest, max, avg)
    - 상관관계 분석 및 그룹 비교 (t-test)
  - **시각화**:
    - 6개 factor 산점도 (2x3 그리드)
    - 그룹별 박스플롯 비교
    - 상관계수 히트맵 (factor × 전략 매트릭스)
  - **연관 데이터**: 
    - `data/pipe_fatigue/fatigue_pipe_lm_by_age.csv`
    - `data/pipe_fatigue/fatigue_sply_ls_by_age.csv`
  - **출력**:
    - `results/0520_repair_k_factors_analysis.txt` - 분석 요약
    - `results/0520_repair_k_factors_matched.csv` - 매칭 데이터
    - `results/repair_k_factors_scatter.png` - 산점도
    - `results/repair_k_factors_boxplot.png` - 박스플롯
    - `results/repair_k_factors_heatmap.png` - 히트맵
  - **주요 결과**: 
    - 각 K-factor와 재작업 빈도의 상관관계 분석
    - 빈번한 재작업 그룹과 일반 그룹 간 K-factors 비교
    - 가장 강한 상관관계를 보이는 요인 식별

### 좌표계 테스트 도구
- **`test_coordinates.py`** (2025년 8월 개발)
  - **목적**: 파이프 데이터와 복구 데이터의 좌표계 검증
  - **기능**: 좌표계 확인, 변환 테스트, 영역 겹침 검증
  - **연관 스크립트**: `analyze_duplicate_cnt_jnt_correlation.py`

## 📊 재작업 패턴 분석 종합 결과

### 분석 개요
0520 지역의 재작업 패턴과 파이프 특성(CNT_JNT, D_final) 간의 상관관계를 다각도로 분석한 결과:

### 주요 발견사항

#### 1. CNT_JNT (파이프 연결점 복잡도) 분석
- **V1 (가장 가까운 파이프)**: r = -0.109, 매칭률 100%
- **V2 (10m 반경)**: r = -0.047 ~ -0.087, 매칭률 86.9%
- **V2 (20m 반경)**: r = -0.045 ~ -0.090, 매칭률 98.8%
- **결론**: CNT_JNT가 높은 복잡한 연결점에서는 오히려 재작업이 적음

#### 2. D_final (피로 손상) 분석
- **10m 반경**: r = -0.020 ~ -0.038, 매칭률 84.1%
- **20m 반경**: r = -0.024 ~ 0.004, 매칭률 98.8%
- **높은 D_final 지역 빈번한 재작업**: 0% (두 반경 모두)
- **결론**: 피로 손상이 큰 파이프에서는 재작업이 발생하지 않음

#### 3. K-factors (위험 요인) 분석
- **분석 대상**: 6개 K-factors (K_age, K_soil, K_traffic, hoop_stress, K_stress, K_total)
- **상관관계**: 모든 K-factor에서 약한 상관관계 또는 음의 상관관계
- **가장 강한 상관관계**: 요인별 차이는 있으나 전반적으로 낮음
- **결론**: K-factors도 재작업 빈도를 설명하지 못함

#### 4. 반경별 비교 인사이트
- 20m 반경이 더 높은 매칭률 제공 (14.7%p 증가)
- 반경과 무관하게 상관관계 패턴은 일관됨
- 더 넓은 반경에서도 결론은 변하지 않음

### 최종 결론

**빈번한 재작업의 원인은 파이프의 구조적 특성(CNT_JNT, D_final) 및 위험 요인(K-factors)이 아님:**

1. **역설적 패턴**: 
   - 단순한 연결점(낮은 CNT_JNT) 지역에서 더 많은 재작업 발생
   - 낮은 피로 손상(낮은 D_final) 지역에서 더 많은 재작업 발생
   - K-factors와도 일관된 상관관계 없음

2. **다른 요인 탐색 필요**:
   - 파이프 재질 및 연령
   - 토양 조건 및 지반 특성
   - 교통량 및 외부 하중
   - 시공 품질 및 유지보수 이력
   - 수압 변동 및 운영 조건

3. **분석 방법론의 강건성**: 다양한 반경(10m, 20m)과 매칭 전략(가장 가까운, 최대값, 평균값)을 적용해도 일관된 결과


## 📊 상관관계 분석 종합 결과 (2025-08-11 업데이트)

### 최종 결론: K_soil만 유일하게 설명력 있음

520 지역 재작업 데이터에 대한 종합 분석 결과, **15개 변수 중 K_soil (토양 조건 계수)만이 유일하게 경계선상의 통계적 유의성**을 보였습니다:

#### K_soil (토양 조건 계수) 상세 분석
- **상관계수**: r = 0.0356 ~ 0.0395 (양의 상관관계)
- **p-value**: 0.0529 (경계선 유의성, p < 0.05 기준에 근접)
- **그룹 비교**: 빈번한 재작업 지역에서 K_soil이 4.7% 높음
  - 빈번한 재작업 지역: K_soil = 1.0667
  - 일반 지역: K_soil = 1.0189
- **설명력**: R² = 0.0016 (0.16% - 매우 낮음)
- **의미**: 토양 조건이 약간 더 나쁜 곳에서 재작업이 더 자주 발생

#### 기타 변수들의 결과
| 변수 | 상관계수 | p-value | 결론 |
|------|----------|---------|------|
| CNT_JNT (연결점) | r < 0.06 | > 0.08 | 상관관계 없음 |
| D_final (피로손상) | \|r\| < 0.03 | > 0.4 | 상관관계 없음 |
| K_age (연령) | 계산 불가 | - | 데이터 품질 문제 |
| K_traffic (교통) | r = -0.058 | 0.087 | 상관관계 없음 |
| K_stress (응력) | r = -0.012 | > 0.5 | 상관관계 없음 |
| K_total (총위험도) | r = -0.025 | > 0.4 | 상관관계 없음 |
| STD_DIP (관경) | r = -0.010 | > 0.5 | 상관관계 없음 |
| 밸브 밀도 (50m) | r = -0.070 | 0.0375 | 유의미하나 음의 상관 |

#### 시사점
1. **K_soil의 중요성**: 토양 부식이 재작업의 유일한 예측 변수 (단, 설명력 0.16%로 매우 제한적)
2. **추가 연구 필요**: 토양 데이터 세분화 (pH, 염분, 수분 함량 등)
3. **실무 적용**: K_soil > 1.1인 지역 우선 점검 권장

## 📋 버전 이력

- **v1.0** (2025-07-01): 초기 버전 - 기본 분석 도구 구성
  - GIS 데이터 분석 도구 (도로, FTR_CDE, 밸브 분석)
  - 파이프 세그먼트 분석 도구
- **v1.1** (2025-07-15): 반원형 세그먼트 분석 도구 추가
  - find_semicircular_segments.py
  - find_small_semicircular_segments.py
  - visualize_all_semicircles.py
- **v1.2** (2025-07-20): 지오코딩 도구 추가
  - analyze_geocoding_cache.py
  - analyze_failed_addresses.py
  - retry_failed_geocoding.py (Kakao API)
  - retry_failed_geocoding_naver.py (Naver API)
- **v1.3** (2025-07-25): 파이프 연결점 검증 도구 추가
  - verify_high_cnt_jnt.py
  - 높은 CNT_JNT 값 검증 기능
- **v1.4** (2025-08-01): 밸브 분석 도구 확장
  - valve_ftc_relationship.py
  - valve_material_relationship.py
- **v1.5** (2025-08-07): 재작업 패턴 상관관계 분석 도구 추가
  - analyze_duplicate_cnt_jnt_correlation_v2.py - CNT_JNT 분석 (통합 버전, 거리 파라미터 지원)
  - analyze_repair_d_final_correlation.py - 피로 손상(D_final) 상관관계 분석 (거리 파라미터 지원)
  - analyze_repair_k_factors_correlation.py - K-factors (7개 위험 요인) 상관관계 분석 (STD_DIP 포함)
  - test_coordinates.py - 좌표계 변환 검증
  - 10m vs 20m 반경 비교 분석 추가
- **v1.6** (2025-08-08): 스크립트 통합 및 개선
  - CNT_JNT v1/v2 통합 완료 (거리 파라미터 추가)
  - D_final 분석 거리 파라미터 통합  
  - K-factors에 STD_DIP 추가 (관경 분석)
  - deprecated 파일 제거 (analyze_duplicate_cnt_jnt_correlation.py, analyze_repair_d_final_correlation_10m_deprecated.py)
- **v1.7** (2025-08-11): 상관관계 분석 종합 결과 추가
  - K_soil만 유일하게 경계선 유의성 확인 (p=0.053)
  - 15개 변수 종합 분석 결과 요약
  - 실무 적용 권장사항 추가
