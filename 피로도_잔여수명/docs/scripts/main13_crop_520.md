# main13: 520 영역 추출 및 중복 분석

**파일명**: `main13_crop_520.py`

## 📋 개요
- MDLZ 0520 영역 내 데이터 추출과 중복 위치 분석을 통합한 스크립트입니다.
- **원본 데이터 통계 (총 92,611개)**:
  - 지상누수: 56,170개
  - 지하누수: 32,959개
  - 긴급공사: 910개
  - 관리대장: 2,572개
- **MDLZ 0520 지역 필터링 후 (총 1,943개, 전체의 2.1%)**:
  - 지상누수: 650개 (전체의 1.2%)
  - 지하누수: 419개 (전체의 1.3%)
  - 긴급공사: 874개 (전체의 96.0%)
  - 관리대장: 0개 (전체의 0.0%)
- **중복 위치 분석 결과**:
  - 582개 클러스터 발견 (10m 반경 내)
  - 1,377개 점이 중복 위치에 해당 (전체의 70.9%)
- **주요 특징**:
  - 긴급공사의 96%가 520 지역에 집중
  - 관리대장 작업은 520 지역에 없음
  - NumPy 벡터화 연산으로 고성능 처리

## 🚀 사용법

```bash
# 기본 실행 (520 영역 추출 + 중복 분석 + 시각화)
python src/main13_crop_520.py

# 최소 중복 횟수 지정 (4회 이상 중복만 표시)
python src/main13_crop_520.py --min-duplicates 4

# 중복 분석 건너뛰기 (단순 위치 표시만)
python src/main13_crop_520.py --skip-duplicates
# 이미지 크기 조정
python src/main13_crop_520.py --scale 2  # 2배 크기 (32×24 inch)
python src/main13_crop_520.py --scale 0.5  # 0.5배 크기 (8×6 inch)
# 화면에 표시
python src/main13_crop_520.py --show
```

## 📥 입력 파일
- `results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv`: 통합된 복구 작업 데이터
  - 지상누수, 지하누수, 긴급공사, 관리대장 데이터 포함
  - 파일타입 컬럼으로 구분
- `data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`: MDLZ 0520 영역 경계
- `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`: 파이프 네트워크

## ✨ 주요 기능
- 통합 CSV 파일에서 4가지 작업 타입 구분 (지상누수, 지하누수, 긴급공사, 관리대장)
- 위치 정보가 없는 행 자동 필터링
- MDLZ 0520 영역 내 데이터만 추출
- KDTree 기반 10m 이내 중복 위치 클러스터링
- 파이프 네트워크와 함께 시각화
- **동적 이미지 크기 조정** (--scale 옵션)

## 🎛️ 옵션
- `--scale`: 이미지 크기 배율 (기본값: 1)
  - 1: 16×12 inch (기본 크기)
  - 2: 32×24 inch (기존 크기)
  - 0.5: 8×6 inch (작은 크기)
- `--min-duplicates`: 표시할 최소 중복 횟수 (0: 모두, 2: 중복만, 4: 4회 이상)
- `--skip-duplicates`: 중복 분석 건너뛰기
- `--output-dir`: 출력 디렉토리 경로 (기본값: results/main13_crop_520)
- `--show`: 생성된 그래프를 화면에 표시
- `--no-interactive`: 비대화형 모드로 실행

## 출력 파일
- `results/main13_crop_520/누수공사_통합_520_위치추가.csv`: 520 영역 내 필터링된 데이터
- `results/main13_crop_520/누수공사_통합_520_위치추가.png`: 중복 위치 분석 시각화
- `results/main13_crop_520/누수공사_통합_520_위치추가_min{n}.png`: 최소 n회 이상 중복 시각화
- `results/main13_crop_520/처리통계.txt`: 상세 통계 보고서

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main13_crop_520_call_graph.md)
- [시각화 출력 규칙](../visualization_rules.md) - 복구 작업 시각화 표준 스타일 가이드
- [클러스터링 알고리즘](../clustering_algorithm.md) - Union-Find 기반 중복 위치 클러스터링 원리

## 🔗 연관 스크립트
- 이전: [`main12*.py`](main12*.md)
- 다음: [`main13a*.py`](main13a*.md)
