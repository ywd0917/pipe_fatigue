# main17a: 개별 작업 기반 파이프 CNT_JNT 상관관계 분석

**파일명**: `main17a_duplicate_cnt_jnt_correlation.py`

## 📋 개요
개별 재작업 위치와 파이프 연결점 복잡도(CNT_JNT) 간의 상관관계를 분석합니다.
main15에서 생성한 Joint 데이터와 main13에서 생성한 통합 복구 데이터를 사용하여,
파이프 연결 복잡도가 높은 지역에서 재작업이 빈번한지 통계적으로 검증합니다.

**⚠️ 주요 변경사항 (2025.09.02)**: 클러스터 기반 분석에서 개별 작업 기반 분석으로 전환
- 기존: 591개 클러스터만 분석 (단일 작업 위치 384개 제외)
- 개선: 1,943개 모든 개별 작업 분석 (100% 데이터 커버리지)

## 🎯 주요 기능
- 개별 작업 위치별 재작업 횟수 계산 (10m 이내)
- 파이프 CNT_JNT와 재작업 빈도 상관관계 분석
- 다양한 CNT_JNT 선택 전략 비교 (최대값, 평균값, 최근접)
- KD-Tree를 이용한 효율적인 공간 매칭
- 통계적 검정 (t-test, 상관계수)

## 📥 입력 파일

### Joint Shapefile (필수)
- `results/main15_extract_joint_data/shapefiles/PIPE_LM_JOINT.shp`: PIPE_LM Joint shapefile
- `results/main15_extract_joint_data/shapefiles/SPLY_LS_JOINT.shp`: SPLY_LS Joint shapefile
  - main15_extract_joint_data.py 실행 후 생성된 파일
  - CNT_JNT 필드 포함 (연결 복잡도)

### 복구 작업 데이터 (필수)
- `results/main13_crop_520/누수공사_통합_520_위치추가.csv`: 통합 복구 작업 데이터
  - **포함된 복구 타입**: 지상누수, 지하누수, 긴급공사, 관리대장
  - **제외된 타입**: 기타공사 (자동 필터링됨)
  - main13_crop_520.py 실행 후 생성된 파일
  - 필수 필드: 위도, 경도, 파일타입, 작업종료일

## 🚀 사용법

```bash
# 기본 실행 (30m 거리 임계값)
python src/main17a_duplicate_cnt_jnt_correlation.py

# 거리 임계값 지정
python src/main17a_duplicate_cnt_jnt_correlation.py --distance 50

# 100m 거리로 분석
python src/main17a_duplicate_cnt_jnt_correlation.py --distance 100
```

### 명령줄 옵션
- `--distance`: 파이프 매칭 거리 임계값 (미터, 기본값: 30m)
  - 재작업 위치에서 지정 거리 이내의 모든 파이프를 고려

## 📤 출력 파일

모든 출력 파일은 `results/main17a_duplicate_cnt_jnt_correlation/` 폴더에 저장됩니다.

### 시각화 파일
- `duplicate_cnt_jnt_strategy_comparison.png`: CNT_JNT 선택 전략별 비교 박스플롯
- `duplicate_cnt_jnt_correlation_scatter_v2.png`: CNT_JNT와 재작업 횟수 산점도 (3가지 전략)
- `duplicate_nearby_pipe_count_distribution.png`: 근처 파이프 수 분포 히스토그램

### 데이터 파일
- `0520_duplicate_cnt_jnt_matched_v2.csv`: 매칭된 개별 작업 데이터
- `0520_cnt_jnt_strategy_comparison.csv`: 전략별 통계 요약 테이블
- `0520_duplicate_cnt_jnt_analysis_v2.txt`: 상세 분석 결과 텍스트 보고서
- `analysis_metadata.json`: 분석 메타데이터 (총 작업 수, 매칭률 등)

## 📊 분석 방법

### 1. 개별 작업 분석
- 모든 개별 작업 위치를 분석 (1,943개)
- 각 위치에서 10m 이내 재작업 횟수 계산 (REPAIR_COUNT_AT_LOCATION)
- 4회 이상 재작업된 위치를 "빈번한 재작업"으로 분류 (IS_FREQUENT)

### 2. CNT_JNT 매칭 전략
- **최대 CNT_JNT**: 지정 거리 내 가장 높은 CNT_JNT 값
- **평균 CNT_JNT**: 지정 거리 내 모든 파이프의 평균 CNT_JNT
- **최근접 CNT_JNT**: 가장 가까운 파이프의 CNT_JNT 값

### 3. 통계 분석
- 빈번 vs 일반 그룹 간 CNT_JNT 차이 검정 (t-test)
- CNT_JNT와 재작업 횟수 간 상관계수 계산 (Pearson r, p-value, R²)
- 높은 CNT_JNT(≥3) 근처 빈번 재작업 비율 분석

## ✨ 주요 특징

### 성능 최적화
- KD-Tree를 사용한 효율적인 최근접 이웃 탐색
- Haversine 공식을 이용한 정확한 거리 계산

### 통계적 검증
- t-test를 통한 그룹 간 유의성 검정
- Pearson 상관계수로 선형 관계 측정
- 다양한 전략으로 강건성 확인

### 파라미터 유연성
- 거리 임계값 조정 가능 (기본 30m)
- 빈번 재작업 기준 조정 가능 (기본 4회)

## 📈 출력 예시

### 콘솔 출력
```
=== 파이프 데이터 로드 중 ===
  PIPE_LM_JOINT 로드: 8,814개 세그먼트
  SPLY_LS_JOINT 로드: 3,991개 세그먼트
  
=== 0520 지역 복구 작업 데이터 로드 중 ===
  지상누수: 650개 로드
  지하누수: 419개 로드
  긴급공사: 874개 로드
  전체 복구 작업: 1,943개
  
  같은 위치 작업 횟수 계산 중...
  
  4회 이상 재작업된 위치의 작업: 488개
  
=== 개별 작업-파이프 매칭 중 ===
  매칭된 작업: 1,721개 / 1,943개
  매칭률: 88.6%
  
=== CNT_JNT 상관관계 분석 ===
  최대 CNT_JNT 전략:
    - 빈번 그룹 평균: 3.43
    - 일반 그룹 평균: 3.45
    - 상관계수(r): -0.018 (p=0.464, R²=0.0003)
```

## 🎆 주요 개선사항

### 데이터 커버리지 향상
- **기존**: 591개 클러스터 (2회 이상 재작업 위치만)
- **개선**: 1,943개 개별 작업 (모든 작업 포함)
- **효과**: 3.3배 더 많은 데이터 포인트로 통계적 신뢰성 향상

### 주요 함수 변경
- `load_and_find_duplicate_clusters()` → `load_520_repair_operations()`
- `match_clusters_to_pipes_v2()` → `match_operations_to_pipes_v2()`
- 분석 단위: 클러스터 → 개별 작업

## 🔗 연관 스크립트
- **필수 선행**: [`main13_crop_520.py`](main13_crop_520.md) - 통합 복구 데이터 생성
- **필수 선행**: [`main15_extract_joint_data.py`](main15_extract_joint_data.md) - Joint 데이터 생성
- 관련: [`main17_cmp_repair2.py`](main17_cmp_repair2.md) - 파이프와 복구 위치 시각화

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main17a_duplicate_cnt_jnt_correlation_call_graph.md)