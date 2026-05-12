# Joint 연결 수 계산 (CNT_JNT)

## 개요

`main15_extract_joint_data.py`는 파이프 네트워크에서 각 세그먼트의 연결점(Joint) 개수를 계산하여 `CNT_JNT` 컬럼으로 저장합니다. 이는 파이프 네트워크의 구조적 복잡성과 스트레스 집중 지점을 파악하는 데 중요한 지표입니다.

## 코드 구조

### 메인 스크립트
- **`src/main15_extract_joint_data.py`**: Joint 계산 및 세그먼트 분리 메인 로직
  - `split_linestring_with_semicircle_detection()`: LineString을 세그먼트로 분리
  - `calculate_joint_counts()`: Joint 연결 수 계산
  - `process_pipe_segments()`: 파이프 세그먼트 처리
  - `process_all_pipes_jointly()`: PIPE_LM과 SPLY_LS 통합 처리

### 공통 모듈
- **`src/common/semicircle_detection.py`**: 반원형 패턴 감지 모듈
  - `is_semicircular_pattern()`: 반원형 패턴 판별
  - `calculate_angle()`: 두 점 사이의 각도 계산
  - `angle_difference()`: 각도 차이 계산
  - 상수 정의: `MIN_SEGMENTS_FOR_SEMICIRCLE`, `MAX_ANGLE_VARIATION` 등

## CNT_JNT 계산 규칙

### 기본 원칙
- 파이프 끝단에서 다른 파이프와 만날 때: **+1**
- 파이프 중간에서 T자로 만날 때: **+1**
- 파이프 중간에서 +자(십자)로 만날 때: **+2**

### 제외 사항
1. **같은 파이프 내 연속 세그먼트**: 같은 원본 파이프(ORIG_FTR_IDN)의 연속된 세그먼트 간 연결은 계산하지 않음
2. **반원형 세그먼트의 T/+ 연결**: 반원형 세그먼트(IS_SEMICIRCULAR=True)는 끝점 연결만 계산하고, T자 및 +자 연결은 제외

## 연결 타입별 상세 설명

### 1. 끝단 연결 (End-to-End Connection)
```
파이프 A: ────●
              │
파이프 B: ────●
```
- 두 파이프의 끝점이 만나는 경우
- 각 파이프에 CNT_JNT +1

### 2. T자 연결 (T-Junction)
```
파이프 A: ──────┬──────
                │
파이프 B: ──────●
```
- 한 파이프의 끝점이 다른 파이프의 중간에 연결
- 파이프 A: CNT_JNT +1 (중간 연결)
- 파이프 B: CNT_JNT +1 (끝단 연결)

### 3. +자 연결 (Cross Junction)
```
파이프 A: ──────┼──────
                │
파이프 B: ──────┼──────
```
- 두 파이프가 중간에서 교차
- 각 파이프에 CNT_JNT +2

## 계산 알고리즘

### 1. 공간 인덱싱 (`calculate_joint_counts` in main15)
```python
# STRtree를 사용한 효율적인 공간 검색
spatial_index = STRtree(list(segments_gdf.geometry))
```

### 2. 연결점 감지 (`calculate_joint_counts` in main15)
```python
# 1mm 버퍼를 사용하여 근접 세그먼트 찾기
buffer = current_geom.buffer(0.001)
nearby_indices = spatial_index.query(buffer)
```

### 3. 연결 타입 판별
- **끝점 거리 확인**: 0.001m (1mm) 이내면 연결로 판단
- **교차점 분석**: Shapely의 `intersects()` 및 `intersection()` 사용
- **중간점 판별**: 교차점이 세그먼트의 끝점에서 1mm 이상 떨어져 있으면 중간 연결

## 반원형 패턴 처리

### 반원형 감지 조건 (`src/common/semicircle_detection.py`)
- 최소 4개 이상의 연속된 짧은 세그먼트 (`MIN_SEGMENTS_FOR_SEMICIRCLE = 4`)
- 세그먼트 길이 ≤1m (`MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE = 1.0`)
- 일정한 곡률 (각도 변화 표준편차 < 0.3 라디안, `MAX_ANGLE_VARIATION = 0.3`)
- 전체 회전각 60° ~ 270° (`MIN_TOTAL_ANGLE = π/3`, `MAX_TOTAL_ANGLE = 1.5π`)

### 세그먼트 처리 (`split_linestring_with_semicircle_detection` in main15)
```python
# 반원형 패턴은 별도의 독립된 세그먼트로 병합
is_semi, _ = is_semicircular_pattern(test_segments)
if is_semi:
    # 여러 짧은 세그먼트를 하나의 긴 세그먼트로 병합
    merged_line = LineString(all_coords)
    # IS_SEMICIRCULAR=True 플래그로 표시
    merged_segment_indices.add(len(result_segments) - 1)
```

### 연결 계산 특수 처리
- **끝점 연결**: 반원형 세그먼트도 정상적으로 계산
- **T자/+자 연결**: 반원형 세그먼트는 제외 (IS_SEMICIRCULAR=True인 경우 스킵)

## 출력 결과

### CSV 파일 구조
```csv
FTR_IDN,ORIG_FTR_IDN,SUB_IDN,SEGMENT_LENGTH,IS_SEMICIRCULAR,CNT_JNT
107322_1,107322,1,11.00,False,1
107322_2,107322,2,4.55,False,2
143879_14,143879,14,79.47,True,2
```

### CNT_JNT 분포 예시 (0520 지역 PIPE_LM - 2025년 갱신)
- CNT_JNT = 0: 0.0% (모든 세그먼트가 최소 1개 연결)
- CNT_JNT = 1: 5.9% (단순 연결)
- CNT_JNT = 2: 66.4% (T자 또는 양끝 연결)
- CNT_JNT ≥ 3: 27.7% (복잡한 연결부)

## 활용 방안

1. **스트레스 분석**: Joint가 많은 지점은 구조적 스트레스가 집중될 가능성이 높음
2. **유지보수 우선순위**: CNT_JNT가 높은 구간을 중점 관리 대상으로 선정
3. **네트워크 복잡도**: 전체 네트워크의 연결 복잡성 평가
4. **피로 손상 예측**: Joint 수와 피로 손상의 상관관계 분석

## CNT_JNT 검증 및 문제점

### 높은 CNT_JNT 값 검증 사례

실제 운영 과정에서 CNT_JNT 값이 비정상적으로 높은 경우가 발견될 수 있습니다.

**검증 사례: 세그먼트 178213_18**
- **기록된 CNT_JNT**: 22개
- **계산된 CNT_JNT**: 10개 (T자 연결)
- **차이**: 12개 (중복 세그먼트로 인한 과대 계산)

### 중복 세그먼트 문제

**발견된 문제점**:
- 동일한 좌표 `(1099601.189, 1766510.537)`에 **12개의 세그먼트가 완전히 겹쳐 있음**
- 시각적으로는 5개 정도로 보이지만, 실제로는 다음과 같은 중복 구조:
  - 원본 파이프 178213의 10개 세그먼트
  - 다른 파이프들(246345, 4788, 455022)의 2개 세그먼트

**중복 세그먼트 목록**:
```
178213_1, 178213_2, 178213_6, 178213_9, 178213_10, 
178213_11, 178213_12, 178213_15, 178213_17, 246345_1, 
4788_1, 455022_2
```

### 검증 도구

**1. Joint 연결 검증 시각화 (`main16_verify_joint_counts.py`)**
```bash
python src/main16_verify_joint_counts.py
```
- 각 CNT_JNT 값별로 샘플 시각화
- 연결점과 연결 타입을 명확히 표시
- 시각적 검증을 통한 정확성 확인

**2. 높은 CNT_JNT 값 검증 (`src/analysis/verify_high_cnt_jnt.py`)**
```bash
python src/analysis/verify_high_cnt_jnt.py
```
- CNT_JNT ≥ 15인 세그먼트 자동 식별
- 연결점별 상세 분석 (끝점, T자, +자, 중복)
- 시각화 및 CSV 상세 정보 내보내기
- 기록된 값과 계산된 값 비교 검증

## 문제 원인 및 해결 방안

### 데이터 품질 이슈

**가능한 원인**:
1. **좌표 정밀도 문제**: 동일한 위치에 여러 세그먼트가 중복 생성
2. **데이터 처리 오류**: 세그먼트 분할 과정에서 중복 데이터 발생
3. **지리 정보 시스템 변환 문제**: 좌표계 변환 시 정밀도 손실

### 검증 방법

**정기적 검증 절차**:
1. **임계값 기반 검색**: CNT_JNT ≥ 15인 세그먼트 식별
2. **수동 검증**: 시각화를 통한 실제 연결 상태 확인
3. **중복 세그먼트 탐지**: 동일 좌표(허용 오차 0.1mm)에 위치한 세그먼트 식별
4. **계산 검증**: 실제 연결 개수와 기록된 CNT_JNT 비교

### 권장 사항

**데이터 품질 관리**:
- CNT_JNT > 10인 세그먼트에 대한 정기적 검증
- 중복 세그먼트 자동 탐지 및 제거 프로세스 구축
- 데이터 처리 파이프라인에 품질 검사 단계 추가

**분석 시 주의사항**:
- 높은 CNT_JNT 값은 검증 없이 신뢰하지 말 것
- 시각화를 통한 실제 구조 확인 필요
- 중복 세그먼트로 인한 과대 평가 가능성 고려

## 주의 사항

- CNT_JNT는 물리적 연결 개수이며, 실제 응력 집중도와는 다를 수 있음
- 반원형 세그먼트는 T자/+자 연결 계산에서 제외되므로 구조적 복잡성이 과소평가될 수 있음
- 1mm 임계값은 데이터 정밀도에 따라 조정이 필요할 수 있음
- **중복 세그먼트로 인한 CNT_JNT 과대 계산 가능성**을 항상 고려해야 함
- **CNT_JNT > 10인 경우 반드시 검증 스크립트를 통한 수동 확인** 권장

## 반원형 세그먼트 통계

### 0520 지역 PIPE_LM 기준
- **반원형 패턴**: 66개 파이프에서 78개 반원형 세그먼트 생성
- **평균 길이**: 일반 세그먼트 6.43m vs 반원형 세그먼트 38.88m
- **CNT_JNT 분포**: 대부분 CNT_JNT=2 (양 끝에서만 연결)

## 관련 파일

### 실행 스크립트
- `src/main15_extract_joint_data.py`: 메인 Joint 계산 스크립트
- `src/main16_verify_joint_counts.py`: Joint 검증 시각화

### 공통 모듈
- `src/common/semicircle_detection.py`: 반원형 패턴 감지 모듈
- `src/common/shapefile_loader.py`: Shapefile 로드 유틸리티

### 분석 도구
- `src/analysis/verify_high_cnt_jnt.py`: 높은 CNT_JNT 값 검증

### 출력 파일
- `results/PIPE_LM_JOINT.csv`: 파이프 Joint 데이터
- `results/SPLY_LS_JOINT.csv`: 급수관 Joint 데이터
- `results/shapefiles/PIPE_LM_JOINT.shp`: 파이프 세그먼트 shapefile
- `results/shapefiles/SPLY_LS_JOINT.shp`: 급수관 세그먼트 shapefile
- `results/joint_verification/*.png`: Joint 검증 이미지