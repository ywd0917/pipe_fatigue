# main58a_analyze_remaining_life_by_years.py

## 개요
main13c의 통합 피로 손상 데이터에서 잔여 수명(remaining_life_years) 데이터를 직접 분석하여 위험도를 평가하는 스크립트입니다.
각 파이프의 실제 위치(zone)를 기반으로 정확한 잔여 수명 분석을 수행합니다.

## 주요 기능
1. **잔여 수명 기반 위험도 평가**
   - 5단계 분류 체계
   - 연도별 색상 그라데이션 적용

2. **통계 분석**
   - 지역별, 파이프 타입별 통계
   - 분포 분석 및 시각화

3. **위험 파이프 식별**
   - 5년 이하 잔여 수명 파이프 추출
   - 우선 순위 목록 생성

## 위험도 분류 기준

| 구분 | 잔여 수명 범위 | 색상 | 설명 |
|------|--------------|------|------|
| 즉시교체 | 0-5년 | 빨강 (#FF0000) | 즉시 교체 필요 |
| 위험 | 5-10년 | 주황 (#FF6347) | 긴급 점검 및 교체 계획 필요 |
| 주의 | 10-20년 | 노랑 (#FFD700) | 정기 모니터링 필요 |
| 안전 | 20-50년 | 연두 (#9ACD32) | 예방 정비 계획 수립 |
| 매우안전 | 50년 초과 | 초록 (#2E8B57) | 정상 운영 |

## 입력 파일

```
results/main13c_zone_fatigue_merge/
└── zone_fatigue_merged.csv  # 통합 피로 손상 데이터
```

### 주요 컬럼
- **DATA_SRC**: 파이프 타입 (PIPE_LM, SPLY_LS)
- **zone**: 파이프가 실제 위치한 구역 (243, 461, 470, 480, 490, 520)
- **D_final_org**: 해당 구역의 피로도 값
- **remaining_life_years**: 잔여 수명 (년)
- **FTR_IDN**: 파이프 고유 ID
- **IST_YMD**: 설치일
- **PIP_DIP**: 파이프 직경

## 출력 파일
```
results/main58a_analyze_remaining_life_by_years/
├── remaining_life_distribution.png    # 전체 분포 히스토그램
├── remaining_life_by_region.png       # 지역별 분포 차트
├── risk_analysis_by_years.png         # 위험도 분석 종합 차트
├── critical_pipes_by_years.csv        # 위험 파이프 목록 (5년 이하)
└── analysis_report_by_years.md        # 분석 보고서
```

## 전제 조건

main13c_zone_fatigue_merge가 먼저 실행되어 통합 데이터가 생성되어 있어야 합니다:

```bash
# 1. 피로 손상 계산 (선행 작업)
python src/main56_calc_fatigure.py

# 2. 잔여 수명 계산
python src/main57_calc_remaining_life.py

# 3. 구역별 피로 데이터 통합 (필수)
python src/main13c_zone_fatigue_merge.py

# 4. 잔여 수명 분석
python src/main58a_analyze_remaining_life_by_years.py
```

## 사용법

### 기본 실행
```bash
python src/main58a_analyze_remaining_life_by_years.py
```

### 작업 흐름
```
main56 (피로 계산) → main57 (잔여수명 계산) → main13c (통합) → main58a (분석)
```

### 실행 예시
```
============================================================
main58a_analyze_remaining_life_by_years.py - 잔여 수명 기준 분석
============================================================

1. 데이터 파일 로드
  - 전체: 4,569 records
  - PIPE_LM: 978 records
  - SPLY_LS: 3,591 records
  - 구역별 분포:
    • 243: 724 records
    • 461: 918 records
    • 470: 984 records
    • 480: 759 records
    • 490: 1,102 records
    • 520: 82 records

2. remaining_life_years 분포 분석
  - 분석 완료: 12 region-type combinations

3. 분포 차트 생성
  - 저장: results/main58a_analyze_remaining_life_by_years/remaining_life_distribution.png
  - 저장: results/main58a_analyze_remaining_life_by_years/remaining_life_by_region.png

4. 위험도 분석 차트 생성
  - 저장: results/main58a_analyze_remaining_life_by_years/risk_analysis_by_years.png

5. 위험 파이프 목록 생성
  - 위험 파이프 (5년 이하): 8개
  - 저장: results/main58a_analyze_remaining_life_by_years/critical_pipes_by_years.csv

6. 분석 보고서 생성
  - 저장: results/main58a_analyze_remaining_life_by_years/analysis_report_by_years.md

============================================================
✅ 분석이 성공적으로 완료되었습니다!
============================================================
```

## 위험도 분류 체계
- **5단계 고정 색상 체계**: 각 위험도 레벨별로 고정된 색상 사용
- **명확한 임계값**: 5, 10, 20, 50년을 기준으로 구분
- **시각적 구별**: 빨강(즉시교체)에서 초록(매우안전)까지 단계적 색상 변화

## 주요 차트 설명

### 1. 잔여 수명 분포 히스토그램
- X축: 잔여 수명 (년)
- Y축: 파이프 개수
- 임계값 표시: 5, 10, 20, 50년 수직선

### 2. 지역별 분포 차트
- 각 지역별 PIPE_LM과 SPLY_LS 분포
- 박스플롯으로 통계값 표시

### 3. 위험도 종합 분석
- 파이 차트: 5단계 위험도 분포 (범례에 개수 표시)
- 지역별 스택 바: 각 지역의 위험도 구성
- 피로손상 vs 잔여수명 산점도
- 타입별 위험도 비교 바 차트

## 분석 결과 활용
1. **즉시교체 (0-5년)**: 긴급 교체 작업 실시
2. **위험 (5-10년)**: 분기별 정밀 점검 및 교체 계획 수립
3. **주의 (10-20년)**: 반기별 정기 점검 실시
4. **안전 (20-50년)**: 연간 정기 점검으로 관리
5. **매우안전 (50년 초과)**: 통상적 유지보수로 충분

## 데이터 처리 방식

### 통합 데이터 사용의 장점
- **정확한 위치 기반 분석**: 각 파이프가 실제 위치한 구역의 데이터만 사용
- **중복 제거**: 파이프당 하나의 레코드만 존재 (이전: 6개 지역 × 파이프 수)
- **효율적 처리**: 데이터 크기 감소로 처리 속도 향상
- **실제적 위험 평가**: 물리적 위치 기반의 정확한 위험도 산정

### 데이터 구조
- **통합 전**: 각 파이프가 6개 지역별로 서로 다른 값 보유 (과대평가)
- **통합 후**: 각 파이프는 실제 위치(zone)의 값만 보유 (정확한 평가)

## 참고사항
- 잔여 수명은 remaining_life_years = (1 - D_final_org) / 년간피로도 공식으로 계산
- 5단계 고정 색상 체계로 명확한 구분 제공
- main58과 main58a 모두 main13c 통합 데이터 사용
  - main58: D_final_org 직접 분석
  - main58a: remaining_life_years 분석
- 파이 차트에서 2% 미만 구간은 레이블 생략하여 가독성 향상
- zone 값은 정수형 (243, 461, 470, 480, 490, 520)으로 처리

## 관련 문서

### 업스트림 스크립트 (입력 데이터 생성)
- [main56_calc_fatigure.md](main56_calc_fatigure.md) - 피로 손상 계산
- [main57_calc_remaining_life.md](main57_calc_remaining_life.md) - 잔여 수명 계산
- [main13c_zone_fatigue_merge.md](main13c_zone_fatigue_merge.md) - 구역별 피로 데이터 통합

### 관련 분석 스크립트
- [main58_analyze_remaining_life.md](main58_analyze_remaining_life.md) - D_final_org 기준 분석
- [main58b_analyze_overlap.md](main58b_analyze_overlap.md) - 위험도 중복 분석