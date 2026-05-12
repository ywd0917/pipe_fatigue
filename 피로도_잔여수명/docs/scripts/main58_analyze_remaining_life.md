# main58_analyze_remaining_life.py - D_final 분포 및 잔여 수명 분석

## 개요
main13c의 통합 피로 손상 데이터를 사용하여 D_final_org 값의 분포를 시각화하고 위험도별 파이프를 분류하는 스크립트입니다.
각 파이프의 실제 위치(zone)를 기반으로 정확한 피로도 분석을 수행합니다.

## 주요 기능

### 1. D_final_org 분포 분석
- 전체 4,569개 파이프의 분포 분석
- 실제 위치 기반 지역별(0243, 0461, 0470, 0480, 0490, 0520) 통계
- 파이프 타입별(PIPE_LM, SPLY_LS) 비교

### 2. 위험도 임계값 설정 (5단계 분류)
분포 최적화를 위한 5단계 분류:

- **즉시교체**: D_final_org ≥ 0.400 - 빨강 (#FF0000)
- **매우위험**: 0.150 ≤ D_final_org < 0.400 - 토마토 (#FF6347)
- **위험**: 0.030 ≤ D_final_org < 0.150 - 노랑 (#FFD700)
- **주의**: 0.010 ≤ D_final_org < 0.030 - 연두 (#9ACD32)
- **안전**: D_final_org < 0.010 - 초록 (#2E8B57)

### 3. 분포 특성
- 74.1%가 0.01 미만 (안전 수준)
- 25.7%가 0.01~0.1 (주의 필요)
- 0.2%만 0.1 이상 (위험 수준)
- 최대값 0.614 (극소수 이상치)

## 입력 파일

```
results/main13c_zone_fatigue_merge/
└── zone_fatigue_merged.csv  # 통합 피로 손상 데이터
```

### 주요 컬럼
- **DATA_SRC**: 파이프 타입 (PIPE_LM, SPLY_LS)
- **zone**: 파이프가 실제 위치한 구역 (0243, 0461, 0470, 0480, 0490, 0520)
- **D_final_org**: 해당 구역의 피로도 값
- **remaining_life_years**: 잔여 수명 (년)
- **FTR_IDN**: 파이프 고유 ID

## 출력 파일

```
results/main58_analyze_remaining_life/
├── d_final_distribution.png        # D_final 전체 분포 차트
├── d_final_distribution_by_region.png  # 지역별 상세 분포
├── risk_analysis.png               # 위험도 카테고리 분석
├── critical_pipes.csv             # 위험 파이프 목록
└── analysis_report.md             # 분석 보고서
```

## 시각화 내용

### 1. d_final_distribution.png
- 전체 히스토그램 (로그 스케일)
- 지역별 박스플롯
- 파이프 타입별 비교
- 범위별 파이 차트

### 2. d_final_distribution_by_region.png
- 6개 지역별 상세 히스토그램
- PIPE_LM vs SPLY_LS 비교
- 지역별 통계 정보

### 3. risk_analysis.png
- 위험도 카테고리 파이 차트 (범례에 개수 표시)
- 지역별 위험도 스택 바
- D_final vs 잔여수명 산점도
- 타입별 위험도 비교

## 사용 방법

### 기본 실행
```bash
python src/main58_analyze_remaining_life.py
```

### 전제 조건
main13c_zone_fatigue_merge가 먼저 실행되어 통합 데이터가 생성되어 있어야 합니다:
```bash
# 1. 피로 손상 계산 (선행 작업)
python src/main56_calc_fatigure.py

# 2. 구역별 피로 데이터 통합
python src/main13c_zone_fatigue_merge.py

# 3. 분포 분석
python src/main58_analyze_remaining_life.py
```

## 출력 예시

```
============================================================
main58_analyze_remaining_life.py - D_final 분포 및 잔여 수명 분석
============================================================

1. 데이터 파일 로드
  - 전체: 4,569 records
  - PIPE_LM: 978 records
  - SPLY_LS: 3,591 records
  - 구역별 분포:
    • 0243: 724 records
    • 0461: 918 records
    • 0470: 984 records
    • 0480: 759 records
    • 0490: 1,102 records
    • 0520: 82 records

2. D_final_org 분포 분석
  - 분석 완료: 12 region-type combinations

3. 분포 차트 생성
  - 저장: results/main58_analyze_remaining_life/d_final_distribution.png
  - 저장: results/main58_analyze_remaining_life/d_final_distribution_by_region.png

4. 위험도 분석 차트 생성
  - 저장: results/main58_analyze_remaining_life/risk_analysis.png

5. 위험 파이프 목록 생성
  - 위험 파이프: 161개
  - 저장: results/main58_analyze_remaining_life/critical_pipes.csv

6. 분석 보고서 생성
  - 저장: results/main58_analyze_remaining_life/analysis_report.md

============================================================
✅ 분석이 성공적으로 완료되었습니다!
============================================================
```

## 분석 결과 해석

### D_final_org 값의 의미
- **D_final_org**: K-factor 보정 전 원본 피로 손상도
- 값이 클수록 피로 손상이 심각
- 1.0에 가까울수록 파이프 수명 한계 접근

### 위험도 평가 기준
- **즉시교체**: D_final_org ≥ 0.400
- **매우위험**: 0.150 ≤ D_final_org < 0.400
- **위험**: 0.030 ≤ D_final_org < 0.150
- **주의**: 0.010 ≤ D_final_org < 0.030
- **안전**: D_final_org < 0.010

### 지역별 특성
- **0243 지역**: 평균 손상도 가장 높음 (PIPE_LM: 0.025)
- **0461 지역**: 가장 안정적 (평균 0.014)
- **0520 지역**: 주요 관심 지역 (재작업 데이터 多)

## 권장 조치사항

1. **즉시교체 (D_final_org ≥ 0.400)**
   - 즉시 교체 작업 실시
   - 긴급 안전 점검 필수

2. **매우위험 (0.150 ≤ D_final_org < 0.400)**
   - 월별 정밀 점검 실시
   - 단기 교체 계획 수립

3. **위험 (0.030 ≤ D_final_org < 0.150)**
   - 분기별 정기 점검
   - 중기 교체 계획 수립

4. **주의 (0.010 ≤ D_final_org < 0.030)**
   - 반기별 모니터링
   - 예방 정비 계획

5. **안전 (D_final_org < 0.010)**
   - 연간 정기 점검으로 충분
   - 통상적 유지보수

## 관련 문서

### 업스트림 스크립트 (입력 데이터 생성)
- [main56_calc_fatigure.md](main56_calc_fatigure.md) - 피로 손상 계산
- [main13c_zone_fatigue_merge.md](main13c_zone_fatigue_merge.md) - 구역별 피로 데이터 통합

### 관련 분석 스크립트
- [main58a_analyze_remaining_life_by_years.md](main58a_analyze_remaining_life_by_years.md) - 잔여 수명 기준 분석
- [main58b_analyze_overlap.md](main58b_analyze_overlap.md) - 위험도 중복 분석

### 이론적 배경
- [피로도 계산 공식](../fatigue_calculation_formula.md) - 이론적 배경

## 데이터 처리 방식

### 이전 방식 (main56 직접 사용)
- 각 파이프가 6개 지역별로 서로 다른 D_final_org 값 보유
- 파이프의 실제 위치와 무관하게 모든 지역 데이터 포함
- 과대평가된 위험 파이프 수

### 현재 방식 (main13c 통합 데이터)
- 각 파이프는 실제 위치한 구역의 D_final_org 값만 보유
- zone 컬럼으로 파이프의 물리적 위치 식별
- 더 정확한 위치 기반 피로도 분석
- DATA_SRC 컬럼으로 파이프 타입 구분

## 추가 개발 계획
- 시계열 트렌드 분석 기능
- 지리적 클러스터링 분석
- 비용-효과 분석 모듈
- 실시간 모니터링 대시보드