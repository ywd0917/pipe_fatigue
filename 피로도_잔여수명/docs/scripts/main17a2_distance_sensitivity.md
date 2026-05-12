# main17a2: 거리별 민감도 분석

**파일명**: `main17a2_distance_sensitivity.py`

## 📋 개요
main17a를 여러 거리 임계값(10m, 20m, 30m, 50m, 100m)으로 실행하여 CNT_JNT와 재작업 빈도 간 상관관계가 거리 설정에 따라 어떻게 변화하는지 분석합니다.
각 거리별로 r, p-value, R² 통계를 수집하고 종합적인 분석 보고서를 생성합니다.

**⚠️ 주요 변경사항 (2025.09.02)**: main17a가 개별 작업 기반으로 변경됨에 따라 호환성 유지

## 🎯 주요 기능
- 다중 거리 임계값 자동 실행 (10m, 20m, 30m, 50m, 100m)
- 거리별 상관관계 통계 수집 및 비교
- 매칭률 추이 분석
- 종합 마크다운 보고서 생성
- 상관관계 추이 시각화

## 📥 입력 (main17a 실행을 통해 자동 처리)

### 간접 입력 (main17a가 사용하는 파일들)
- `results/main15_extract_joint_data/shapefiles/PIPE_LM_JOINT.shp`
- `results/main15_extract_joint_data/shapefiles/SPLY_LS_JOINT.shp`
- `results/main13_crop_520/누수공사_통합_520_위치추가.csv`

## 🚀 사용법

```bash
# 기본 실행 (10m, 20m, 30m, 50m, 100m 분석)
python src/main17a2_distance_sensitivity.py
```

### 분석 프로세스
1. 각 거리(10m, 20m, 30m, 50m, 100m)에 대해 main17a 실행
2. 각 실행 결과에서 통계 정보 추출
3. 종합 분석 보고서 생성
4. 시각화 파일 생성

## 📤 출력 파일

모든 출력은 `results/main17a2_distance_sensitivity/` 폴더에 저장됩니다.

### 메인 출력 파일
- `distance_sensitivity_report.md`: 종합 분석 보고서
- `distance_sensitivity_results.json`: 거리별 상세 통계 데이터
- `distance_sensitivity_analysis.png`: 거리별 상관관계 추이 그래프
- `correlation_heatmap.png`: 상관계수 히트맵

### 거리별 하위 폴더
- `distance_10m/`: 10m 분석 결과
- `distance_20m/`: 20m 분석 결과
- `distance_30m/`: 30m 분석 결과
- `distance_50m/`: 50m 분석 결과
- `distance_100m/`: 100m 분석 결과

각 하위 폴더에는 main17a의 모든 출력 파일이 포함됩니다:
- `0520_duplicate_cnt_jnt_matched_v2.csv`: 매칭된 개별 작업 데이터
- `0520_cnt_jnt_strategy_comparison.csv`: 전략별 통계 요약
- `0520_duplicate_cnt_jnt_analysis_v2.txt`: 상세 분석 결과
- `analysis_metadata.json`: 분석 메타데이터
- 시각화 파일들

## 📊 분석 내용

### 1. 거리별 상관관계 비교
- 최대 CNT_JNT 전략의 거리별 r, p, R² 변화
- 평균 CNT_JNT 전략의 거리별 r, p, R² 변화
- 가장 가까운 CNT_JNT 전략의 거리별 r, p, R² 변화

### 2. 매칭률 분석
- 거리별 클러스터-파이프 매칭률 변화
- 매칭된 클러스터 수 vs 전체 클러스터 수

### 3. 통계적 유의성
- p < 0.05인 유의한 결과 식별
- 최적 거리 및 전략 도출

## 📈 출력 예시

### 마크다운 보고서 예시
```markdown
# 거리별 민감도 분석 보고서

## 📊 결과 요약

| 거리(m) | 매칭률 | 최대 CNT_JNT r | p-value | R² |
|---------|--------|----------------|---------|-----|
| 10      | 88.3%  | -0.0681        | 0.1201  | 0.0046 |
| 20      | 98.8%  | -0.0331        | 0.4240  | 0.0011 |
| 30      | 99.5%  | 0.0010         | 0.9805  | 0.0000 |
| 50      | 100.0% | -0.0115        | 0.7803  | 0.0001 |
| 100     | 100.0% | 0.0539         | 0.1906  | 0.0029 |

## 🎯 주요 발견사항
1. 최적 거리: 10m (평균 CNT_JNT 전략에서 R²=0.0057)
2. 매칭률 범위: 88.3% ~ 100.0%
3. 통계적 유의성: 모든 거리에서 유의한 상관관계가 발견되지 않음
```

### 콘솔 출력
```
============================================================
main17a2: 거리별 민감도 분석
============================================================

거리 10m로 분석 실행 중...
✓ 10m 분석 완료

거리 20m로 분석 실행 중...
✓ 20m 분석 완료

...

분석 보고서 생성 중...
✓ 분석 보고서 저장: results/main17a2_distance_sensitivity/distance_sensitivity_report.md

시각화 생성 중...
시각화 파일 생성 완료

============================================================
분석 완료!
결과 디렉토리: results/main17a2_distance_sensitivity
============================================================
```

## ✨ 주요 특징

### 자동화
- subprocess를 통한 main17a 자동 실행
- 각 거리별 독립적인 출력 디렉토리 생성
- 결과 파일 자동 파싱 및 통계 추출

### 종합 분석
- 모든 거리의 결과를 하나의 보고서로 통합
- 거리별 추이 시각화
- 최적 거리 및 전략 자동 식별

### 시각화
- 4개 패널 그래프 (r, p-value, R², 매칭률)
- 상관계수 히트맵
- matplotlib/seaborn 기반 고품질 차트

## 🔗 연관 스크립트
- **필수**: [`main17a_duplicate_cnt_jnt_correlation.py`](main17a_duplicate_cnt_jnt_correlation.md) - 기본 분석 스크립트
- **필수 선행**: [`main13_crop_520.py`](main13_crop_520.md) - 통합 복구 데이터 생성
- **필수 선행**: [`main15_extract_joint_data.py`](main15_extract_joint_data.md) - Joint 데이터 생성

## 📚 관련 문서
- [거리별 민감도 분석 결과](../../results/main17a2_distance_sensitivity/distance_sensitivity_report.md)