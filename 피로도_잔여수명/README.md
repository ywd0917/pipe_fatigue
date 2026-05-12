# Fatigue QGIS - 피로 손상 분석 시스템

GIS 데이터를 활용하여 수도관망의 구역 정보와 지질 데이터를 시각화하고 분석하는 도구입니다.

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [설치 방법](#설치-방법)
- [사용 방법](#사용-방법)

## 프로젝트 소개

수도관망의 구역(Zone) 정보와 지질 데이터를 시각화하고 분석하는 GIS 기반 도구입니다. 압력 데이터의 주파수 성분을 분석하여 구조물의 피로 손상을 평가하는 시스템의 일부입니다.

### 주요 데이터
- **Zone 데이터**: 대블록(LRGZ), 중블록(MDLZ), 2차구역(SCDZ), 소블록(SMLZ)
- **관망 데이터**: 상수관로(PIPE_LM), 급수관로(SPLY_LS), 밸브(VALV_PS), 소화전(FIRE_PS)
- **지질 데이터**: 암상(Litho), 지질경계(Boundary), 단층(Fault), 도엽(Frame)
- **도로 데이터**: 대구광역시 도로 네트워크 (TL_SPRD_MANAGE)
- **좌표계**: EPSG:5179 (Korea 2000 / Central Belt 2010) - 모든 공간 분석의 기준 좌표계

## 주요 기능

프로젝트는 main1부터 main30까지 30개 이상의 분석 스크립트를 포함하고 있습니다.

- **📊 데이터 입출력 (main1-5)**: GIS 데이터 읽기, Zone/지질 시각화, 파이프-토양 매칭
- **🏗 인프라 분석 (main6-10)**: 도로 네트워크, 파이프-도로 중첩, 피로 손상 분석
- **🔧 복구 작업 분석 (main11-19)**: 지오코딩, 520 지역 분석, K_repair 계산
- **📈 공간 통계 분석 (main20-30)**: 핫스팟, Space-Time 큐브, 예측 모델

📚 **전체 스크립트 목록과 상세 설명은 [문서 인덱스](docs/INDEX.md#스크립트-문서)를 참조하세요.**

### 워크플로우 다이어그램

주요 분석 파이프라인의 상세 워크플로우는 별도 문서를 참조하세요:

- **[시계열/피로도 분석 (main51-58)](docs/workflows/workflow_main51-58_fatigue.md)** - 주파수 분석 → 피로도 계산 → 위험도 분석
- **[지오코딩 (main11)](docs/workflows/workflow_main11_geocoding.md)** - 복구 데이터 병합 → 주소→좌표 변환
- **[520 지역 분석 (main13)](docs/workflows/workflow_main13_520_analysis.md)** - K_repair 계산 → 구역별 피로 손상
- **[Joint 분석 (main15-17)](docs/workflows/workflow_main15-17_joint.md)** - Joint 데이터 추출 → 상관관계 분석
- **[공간 통계 분석 (main20-30)](docs/workflows/workflow_main20-30_spatial.md)** - 핫스팟 → 시공간 큐브 → 예측

## 설치 방법

### 요구사항
- Python 3.11 이상
- 가상환경 사용 권장

1. 개발 모드 설치 (이것을 꼭 실행해야 합니다. 안 그러면 import에서 오류 발생.)
```bash
pip install -e .
```

## 테스트

프로젝트는 포괄적인 테스트 스위트를 포함하고 있습니다:

```bash
# 모든 테스트 실행
pytest

# 특정 테스트 파일 실행
pytest tests/test_main14b2_distance_sensitivity.py

# 커버리지 없이 빠른 테스트
pytest --no-cov
```

## 📚 프로젝트 문서

### 핵심 문서
- **[프로젝트 구조](CLAUDE.md)** - AI 도구 가이드 및 프로젝트 구조
- **[코딩 표준](CODING_STANDARDS.md)** - 코딩 표준 및 개발 가이드
- **[분석 도구](src/analysis/README.md)** - GIS 데이터, 파이프 세그먼트, 지오코딩 분석 도구

### 기술 문서
- **[GIS 데이터 필드](docs/GIS_DATA_FIELDS.md)** - GIS 데이터 필드 정의 및 FTR_CDE 코드 체계
- **[지질 데이터 분석](docs/soil_data_analysis.md)** - 지질 데이터 상세 분석 및 lithoidx 목록
- **[K_SOIL 추출 방법](docs/K_SOIL_extraction_method.md)** - K_SOIL 값 추출 및 공간 매칭 방법
- **[파이프-도로 중첩 분석](docs/pipe_road_overlap_analysis.md)** - 파이프-도로 중첩 분석 방법

### 분석 결과
- **[📊 분석 결과 요약](docs/analysis_results_summary.md)** - 주요 발견사항 및 실무 시사점
- **[상관관계 상세 분석](docs/correlation_analysis_results.md)** - K-factors 통계 상세
- **[공간분석 보고서](docs/spatial_analysis_completion_report.md)** - main20-30 구현 내역
- **[하위 지역 분석](docs/subregion_radius_sensitivity_analysis.md)** - 0470/0480/0490 지역별 분석

### 📖 전체 문서 목록
모든 문서, 함수 호출 그래프, 개발 문서는 **[📚 문서 인덱스](docs/INDEX.md)**를 참조하세요.


## 주요 분석 결과

520 지역 재작업 데이터(2020-2024)와 파이프 위험 요인의 상관관계를 종합 분석한 결과, **K-factors의 설명력이 매우 낮음(R² < 3%)** 을 확인했습니다. 이는 재작업 패턴의 97% 이상이 K-factors 외 다른 요인(시공 품질, 유지보수 이력, 외부 충격 등)에 의해 결정됨을 시사합니다.

### 파이프-누수 매칭 방법론
- **좌표계**: EPSG:5179 (Korea 2000 / Central Belt 2010) 투영 좌표계 사용
- **매칭 방식**: 누수/재작업 지점에서 가장 가까운 파이프 LineString까지의 최단거리 계산
- **거리 계산**: Euclidean 거리 (투영 좌표계 내에서 직선 거리)
- **검색 반경**: 30m (최적 거리)
- **위험도 계산**: 반경 내 모든 파이프 중 **최대값(max)** 사용 - 최악의 경우(worst case) 시나리오 적용
- **매칭률**: 30m 반경에서 99.8% 매칭 성공
- 📚 **상세 방법론**: [상관관계 분석 결과](docs/correlation_analysis_results.md#매칭-방법론)

### 핵심 발견사항
- **최적 분석 거리**: 30m (매칭률 99.6%)
- **지역별 차이**: 0490 지역이 가장 많은 재작업(28.6%)과 유의미한 상관관계
- **K_soil 역설**: 토양 조건이 나쁜 곳(K_soil>1.0)보다 일반 토양에서 재작업 집중
- **성능 개선**: cKDTree 최적화로 분석 속도 250-500배 향상

📊 **상세 분석 결과는 [분석 결과 요약](docs/analysis_results_summary.md)을 참조하세요.**

## 문서 이력

- 최초 작성일: 2025-07-25
- 최종 수정일: 2025-08-21
- 버전: 3.8