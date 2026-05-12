# main19: 520 지역 재작업 통합 시각화 및 인프라 상관관계 분석

**파일명**: `main19_visualize_520_repairs.py`

## 📋 개요
520 지역의 재작업 데이터를 통합 시각화하고 주변 인프라와의 공간적 상관관계를 분석합니다.

## 🚀 사용법

```bash
# 기본 실행
python src/main19_visualize_520_repairs.py

# 분석 반경 지정 (기본값: 20m)
python src/main19_visualize_520_repairs.py --radius 30

# 특정 분석 건너뛰기
python src/main19_visualize_520_repairs.py --skip-comparison  # 타입별 비교 건너뛰기
python src/main19_visualize_520_repairs.py --skip-heatmap    # 밀도 히트맵 건너뛰기
python src/main19_visualize_520_repairs.py --skip-correlation # 상관관계 분석 건너뛰기

# 그리드 없이 표시
python src/main19_visualize_520_repairs.py --no-grid

# 입출력 경로 지정
python src/main19_visualize_520_repairs.py --input-dir path/to/input --output-dir path/to/output
```

## 🎛️ 옵션
- `--radius`: 인프라 상관관계 분석 반경 (미터, 기본값: 20)
- `--input-dir`: 입력 디렉토리 경로 (기본값: results/)
- `--output-dir`: 출력 디렉토리 경로 (기본값: results/main19_visualize_520_repairs/)
- `--no-grid`: 그리드 표시하지 않음
- `--skip-comparison`: 타입별 비교 플롯 생성 건너뛰기
- `--skip-heatmap`: 밀도 히트맵 생성 건너뛰기
- `--skip-correlation`: 인프라 상관관계 분석 건너뛰기

## 📥 입력 파일

### 재작업 데이터
- `results/main13_crop_520/누수공사_통합_520_위치추가.csv`: 520 지역 재작업 위치 데이터
  - main13_crop_520.py에서 생성
  - 파일타입 컬럼으로 지상누수/지하누수/긴급공사/관리대장 구분
  - 520 지역 데이터만 포함 (약 1,944건)

### 인프라 데이터 (Shapefile)
- `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`: 파이프 라인
- `data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`: 급수관 네트워크
- `data/raw/export_shp_20250704(0520)/WTL_VALV_PS.shp`: 밸브 위치
- `data/raw/export_shp_20250704(0520)/WTL_FIRE_PS.shp`: 소화전 위치
- `data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`: MDLZ 0520 경계

### D_final 상관관계 분석용 데이터
- `results/main17_fatigue/fatigue_pipe_lm_by_age.csv`: 파이프 피로도 데이터
- `results/main17_fatigue/fatigue_sply_ls_by_age.csv`: 급수관 피로도 데이터

## 📤 출력 파일

### 메인 출력 디렉토리: `results/main19_visualize_520_repairs/`

#### 시각화 파일
- `results/main19_visualize_520_repairs/520_repairs_with_background.png`: 전체 통합 시각화 (배경 지도 포함)
- `results/main19_visualize_520_repairs/520_repairs_type_comparison.png`: 재작업 타입별 비교 플롯
- `results/main19_visualize_520_repairs/520_repairs_density_heatmap.png`: 재작업 밀도 히트맵

#### 상관관계 분석 시각화
- `results/main19_visualize_520_repairs/520_infrastructure_correlation_scatter.png`: 인프라 상관관계 산점도
- `results/main19_visualize_520_repairs/520_infrastructure_correlation_boxplot.png`: 인프라 상관관계 박스플롯
- `results/main19_visualize_520_repairs/520_infrastructure_correlation_heatmap.png`: 인프라 상관관계 히트맵
- `results/main19_visualize_520_repairs/520_d_final_correlation_{radius}m.png`: D_final 상관관계 시각화

#### 데이터 및 보고서
- `results/main19_visualize_520_repairs/520_repair_infrastructure_data.csv`: 인프라 상관 데이터
- `results/main19_visualize_520_repairs/520_repairs_summary.csv`: 재작업 데이터 요약
- `results/main19_visualize_520_repairs/520_repairs_statistics.txt`: 통계 보고서
- `results/main19_visualize_520_repairs/520_infrastructure_correlation_report.txt`: 인프라 상관관계 분석 보고서
- `results/main19_visualize_520_repairs/520_d_final_correlation_report.txt`: D_final 상관관계 분석 보고서

## ✨ 주요 기능

### 1. 데이터 통합 및 시각화
- 통합 CSV 파일의 파일타입별 데이터 시각화
- 재작업 타입별 색상 구분 (지상누수: 핑크, 지하누수: 파란색, 긴급공사: 갈색, 관리대장: 녹색)
- 배경 인프라 데이터와 함께 시각화

### 2. 공간 분석
- 재작업 밀도 분석 및 히트맵 생성
- 타입별 공간 분포 비교
- 지정된 반경 내 버퍼 영역 표시

### 3. 인프라 상관관계 분석
- 재작업 위치 주변 인프라 요소 검색 (밸브, 소화전, 파이프)
- 빈번한 재작업 지점과 인프라 거리 상관관계 계산
- 통계적 유의성 검정 (t-test, Mann-Whitney U test)

### 4. D_final 상관관계 분석
- 재작업 위치와 가장 가까운 파이프의 D_final 값 매칭
- 재작업 빈도와 D_final 값의 상관관계 분석
- 시각화 및 통계 보고서 생성

### 5. 통계 보고서
- 재작업 타입별 통계 (개수, 비율)
- 지역별 분포 분석
- 시간대별 패턴 분석 (작업일시 데이터가 있는 경우)

## 🔧 기술적 세부사항

### 좌표계
- 입력 CSV: WGS84 (EPSG:4326) - 위도/경도
- Shapefile: Korea 2000 / Central Belt (EPSG:5179)
- 내부 처리: 자동 좌표계 변환

### 시각화 설정
- Figure 크기: 32×24 inch
- DPI: 300 (고해상도)
- 재작업 점 크기: 50
- 재작업 점 투명도: 0.3
- 파이프 라인 투명도: 0.7

### 상관관계 분석 파라미터
- 기본 검색 반경: 20m
- 클러스터링 거리: 10m
- 빈번한 재작업 판단 기준: 4회 이상

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main19_visualize_520_repairs_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main18_analyze_duplicate_repairs.py`](main18_analyze_duplicate_repairs.md) - 중복 재작업 분석
- 다음: [`main19a_fast_radius_analysis.py`](main19a_fast_radius_analysis.md) - 고속 반경별 분석
- 관련: [`main17_cmp_recovery2.py`](main17_cmp_recovery2.md) - D_final 데이터 생성