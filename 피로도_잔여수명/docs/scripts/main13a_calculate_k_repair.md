# main13a: 파이프별 재작업 횟수 계산

**파일명**: `main13a_calculate_k_repair.py`

## 📋 개요
파이프와 재작업 위치 간 거리를 분석하여 각 파이프의 재작업 횟수(K_repair)를 계산합니다.

> **📌 입력 파일 변경**: 이전에는 개별 CSV 파일을 사용했지만, 현재는 main13에서 생성한 통합 CSV 파일을 사용합니다.

### 📊 처리 결과 요약

#### **PIPE_LM (980개 파이프)**
- **파이프 길이**: 평균 57.7m (최소 0.2m, 최대 683.3m)
- **K_repair 평균**: 17.90회 (최대 392회)
- **1m당 K_repair**: 평균 0.72회 (최대 54.03회)
- **재작업 있는 파이프**: 938개 (95.7%)
- **재작업 유형별 비율**:
  - 긴급공사: 45.6% (8,004건)
  - 지상누수: 33.1% (5,807건)
  - 지하누수: 21.3% (3,734건)

#### **SPLY_LS (3,599개 급수관)**
- **파이프 길이**: 평균 4.9m (최소 0.8m, 최대 83.6m)
- **K_repair 평균**: 9.67회 (최대 36회)
- **1m당 K_repair**: 평균 2.59회 (최대 20.41회)
- **재작업 있는 파이프**: 3,536개 (98.2%)
- **재작업 유형별 비율**:
  - 긴급공사: 45.5% (15,828건)
  - 지상누수: 32.7% (11,389건)
  - 지하누수: 21.8% (7,573건)

## 🚀 사용법

```bash
# 기본 실행 (30m 거리)
python src/main13a_calculate_k_repair.py

# 거리 옵션 지정
python src/main13a_calculate_k_repair.py --distance 50

# 상세 출력
python src/main13a_calculate_k_repair.py --verbose
```

## 🎛️ 옵션
- `--distance`: 매칭 거리 임계값 (미터, 기본값: 30)
- `--output-dir`: 출력 디렉토리 (기본값: results/main13a_k_repair/)
- `--verbose`: 상세 출력 모드

## 📥 입력 파일
- `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`: 파이프 네트워크 shapefile (980개)
- `data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`: 급수관 네트워크 shapefile (3,599개)
- `results/main13_crop_520/누수공사_통합_520_위치추가.csv`: 520 지역 통합 재작업 위치 (1,943개)
  - 지상누수: 650개
  - 지하누수: 419개
  - 긴급공사: 874개
  - 필수 컬럼: 위도, 경도, 파일타입

## 📤 출력 파일

### repair_pipe_lm.csv (파이프별 K_repair)
- **FTR_IDN**: 파이프 ID
- **pipe_length**: 파이프 길이 (m)
- **K_repair**: 총 재작업 횟수
- **K_repair_per_m**: 1m당 재작업 횟수
- **K_repair_ground**: 지상누수 횟수
- **K_repair_ground_per_m**: 1m당 지상누수
- **K_repair_under**: 지하누수 횟수
- **K_repair_under_per_m**: 1m당 지하누수
- **K_repair_emergency**: 긴급공사 횟수
- **K_repair_emergency_per_m**: 1m당 긴급공사
- **K_repair_management**: 관리대장 횟수
- **K_repair_management_per_m**: 1m당 관리대장

### repair_sply_ls.csv (급수관별 K_repair)
- 동일한 컬럼 구조로 3,599개 급수관 데이터 포함

## ✨ 주요 기능
- 파이프 shapefile 로드 (V_WTL_PIPE_LM, V_WTL_SPLY_LS)
- 통합 재작업 CSV 파일 로드 (지상누수, 지하누수, 긴급공사, 관리대장)
- STRtree 공간 인덱싱으로 거리 기반 매칭
- **선형 거리 가중치 적용**: 재작업 위치와 파이프 간 거리에 따라 선형적으로 감소하는 가중치
- 재작업 유형별 가중 합계 (K_repair_ground, K_repair_under, K_repair_emergency, K_repair_management)
- **파이프 길이별 정규화 (K_repair_per_m)**: 최소 10m 길이 기준 적용으로 짧은 파이프의 과도한 per-meter 값 방지

## 🔧 계산 로직

### 선형 거리 가중치 (Linear Distance Weighting)
**배경**: 단순 카운트 대신 재작업 위치와 파이프 간 거리를 고려한 가중치 적용으로 더 정확한 위험도 평가

**가중치 공식**:
```
weight = max(0, 1 - (distance / max_distance))
```
- distance: 재작업 위치와 파이프 간 최단 거리 (미터)
- max_distance: 버퍼 거리 (기본값 30m)
- 0m에서 가중치 1.0, 30m에서 가중치 0.0으로 선형 감소

**적용 예시**:
| 거리 | 가중치 | 설명 |
|------|--------|------|
| 0m   | 1.00   | 파이프 바로 위 |
| 10m  | 0.67   | 가까운 위치 |
| 20m  | 0.33   | 중간 거리 |
| 30m  | 0.00   | 버퍼 경계 |

### 최소 파이프 길이 제약 (MIN_PIPE_LENGTH = 10.0m)
**배경**: 매우 짧은 파이프(예: 0.5m)에서 재작업이 발생할 경우 비현실적으로 높은 per-meter 값이 계산되는 문제 해결

**적용 방식**:
- **실제 파이프 길이**: CSV 출력에는 정확한 geometry.length 저장
- **정규화 계산**: K_repair_per_m 계산 시 `max(actual_length, 10.0)` 사용
- **영향 범위**: 10m 미만 파이프만 영향받음, 10m 이상 파이프는 기존과 동일

**효과 예시**:
| 실제 길이 | K_repair | 기존 per-m | 새로운 per-m |
|-----------|----------|------------|--------------|
| 0.5m      | 1.5      | 3.0        | 0.15         |
| 5.0m      | 2.3      | 0.46       | 0.23         |
| 15.0m     | 3.0      | 0.2        | 0.2 (동일)   |

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main13a_calculate_k_repair_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main13*.py`](main13*.md)
- 다음: [`main13b*.py`](main13b*.md)
