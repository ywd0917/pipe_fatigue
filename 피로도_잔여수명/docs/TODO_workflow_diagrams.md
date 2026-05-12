# 워크플로우 다이어그램 작성 TODO

입력파일과 출력파일이 명확하게 연결된 스크립트들의 다이어그램을 작성합니다.

## 작성 대상

### 1. main51-58 시계열/피로도 분석 파이프라인 - ✅ 완료

**입출력 관계:**
- main51: 압력 데이터 → 주파수 분석 결과
- main52: 압력 데이터 → 필터링된 데이터
- main53: 필터링된 데이터 → Rainflow 결과
- main54: 관망 데이터 → 처리된 파이프 데이터
- main55: 토양/교통 데이터 → results/main55/fatigue_*.csv
- main56: 토양/교통 + K_repair → results/main56_calc_fatigure/fatigue_*.csv
- main57: main55/56 결과 → results/main57_merge_fatigue/merged_fatigue_analysis.csv
- main58 시리즈: 피로도 결과 → 위험도 분석 결과

**파일:** `docs/workflows/workflow_main51-58_fatigue.md`

### 2. main11 지오코딩 파이프라인 - ✅ 완료

**입출력 관계:**
- main11a: 긴급공사 파일들 → 병합된 긴급공사.csv
- main11b: 관리대장 파일들 → 병합된 관리대장.csv
- main11c: 주소 데이터 → 좌표 추가된 데이터
- main11e: 개별 복구 데이터 → 전체 병합 복구 데이터
- main11g: 복구 데이터 → 구역번호 수정된 데이터

**파일:** `docs/workflows/workflow_main11_geocoding.md`

### 3. main13 520 지역 분석 파이프라인 - ✅ 완료

**입출력 관계:**
- main13: 전체 데이터 → 520 지역 추출 데이터
- main13a: 복구 이력 → results/main13a_k_repair/repair_*.csv
- main13c: 피로도 결과 → results/main13c/zone_fatigue_merged.csv
- main13d: 병합된 결과 → 시각화 출력
- main13f: K_repair 결과 → 고위험 시각화

**파일:** `docs/workflows/workflow_main13_520_analysis.md`

### 4. main15-17 Joint 분석 파이프라인 - ✅ 완료

**입출력 관계:**
- main15: 관망 데이터 → results/main15_extract_joint_data/
- main16: main15 결과 → 검증 보고서
- main17: Joint 데이터 + 복구 데이터 → 비교 분석 결과

**파일:** `docs/workflows/workflow_main15-17_joint.md`

### 5. main20-30 공간 통계 분석 파이프라인 - ✅ 완료

**입출력 관계:**
- main20: 파라미터 → 최적화된 설정
- main21: 피로도 데이터 → 그리드 데이터
- main22: 그리드 데이터 → 핫스팟 결과
- main24: 시계열 데이터 → 시공간 큐브
- main30: 분석 결과들 → 검증 보고서

**파일:** `docs/workflows/workflow_main20-30_spatial.md`

## 제외 대상

다음은 시각화 전용이거나 입출력 파일 연결이 불명확하여 제외:

- main1-5: 대부분 시각화 또는 단순 읽기
- main6-10: 시각화 중심
- main14 시리즈: 분석/시각화 중심
- main18-19: 시각화 중심

## 작업 순서

1. [x] TODO 파일 작성
2. [x] main51-58 다이어그램 작성
3. [x] main11 다이어그램 작성
4. [x] main13 다이어그램 작성
5. [x] main15-17 다이어그램 작성
6. [x] main20-30 다이어그램 작성
7. [x] INDEX.md에 다이어그램 링크 추가

## 파일 위치

모든 다이어그램은 `docs/workflows/` 디렉토리에 저장합니다.
