# 테스트 커버리지 개선 계획

## 📊 현재 상황 분석
- **현재 커버리지**: 8.95% (목표: 80%)
- **총 테스트 수**: 1,205개
- **테스트 파일**: 66개 (tests/)
- **메인 스크립트**: 44개 (src/main*.py)
- **분석 스크립트**: 25개 (src/analysis/*.py)
- **라인 커버리지**: 1,485/16,585 lines

## 🎯 커버리지 목표
- **단기 목표 (1주)**: 30% 달성
- **중기 목표 (2주)**: 50% 달성  
- **장기 목표 (1개월)**: 80% 달성

## 📝 우선순위별 테스트 작성 계획

### 🔴 최우선 (커버리지 0-15% 파일)

#### 1. Core Utilities (Week 1)
- [ ] `src/check_data_quality.py` (0% → 80%)
  - [ ] 데이터 유효성 검증 테스트
  - [ ] 누락 데이터 검사 테스트
  - [ ] 이상치 탐지 테스트

- [ ] `src/common/spatial_utils.py` (8% → 80%)
  - [ ] 공간 가중치 행렬 생성 테스트
  - [ ] 거리 계산 함수 테스트
  - [ ] 그리드 생성 테스트
  - [ ] 좌표 변환 테스트

- [ ] `src/common/validation.py` (13% → 80%)
  - [ ] 입력 데이터 검증 테스트
  - [ ] 파일 경로 검증 테스트
  - [ ] 데이터 타입 검증 테스트

- [ ] `src/common/geocoding_kakao_sqlite_v2.py` (14% → 70%)
  - [ ] API 호출 모킹 테스트
  - [ ] 캐시 저장/조회 테스트
  - [ ] 에러 처리 테스트

#### 2. Main Scripts - Data I/O (Week 1)
- [ ] `src/main2_draw_zone.py` (12% → 60%)
  - [ ] Zone 시각화 테스트
  - [ ] 경계 처리 테스트
  - [ ] 색상 매핑 테스트

- [ ] `src/main3_draw_soil.py` (15% → 60%)
  - [ ] 토양 데이터 로드 테스트
  - [ ] 시각화 생성 테스트
  - [ ] 범례 생성 테스트

- [ ] `src/main4_list_soil.py` (15% → 60%)
  - [ ] 토양 목록 생성 테스트
  - [ ] 정렬 및 필터링 테스트

### 🟡 중간 우선순위 (커버리지 15-30% 파일)

#### 3. Main Scripts - Infrastructure (Week 2)
- [ ] `src/main6_draw_road.py` (26% → 70%)
  - [ ] 도로 데이터 로드 테스트
  - [ ] 도로 네트워크 시각화 테스트
  - [ ] 교통량 매핑 테스트

- [ ] `src/main7_pipe_traffic.py` (22% → 70%)
  - [ ] 파이프-교통량 매칭 테스트
  - [ ] K_traffic 계산 테스트
  - [ ] 결과 저장 테스트

- [ ] `src/main8_verify_overlap_samples.py` (19% → 70%)
  - [ ] 중복 검증 로직 테스트
  - [ ] 샘플 추출 테스트
  - [ ] 통계 계산 테스트

#### 4. Main Scripts - Repair Analysis (Week 2)
- [ ] `src/main9_draw_repair.py` (21% → 70%)
  - [ ] 재작업 데이터 로드 테스트
  - [ ] 클러스터링 테스트
  - [ ] 시각화 테스트

- [ ] `src/main10_cmp_repair.py` (17% → 70%)
  - [ ] 비교 분석 로직 테스트
  - [ ] 통계 계산 테스트
  - [ ] 보고서 생성 테스트

### 🟢 낮은 우선순위 (커버리지 30%+ 파일)

#### 5. Common Modules (Week 3)
- [ ] `src/common/config.py` (66% → 90%)
  - [ ] 환경변수 로드 테스트
  - [ ] 설정 파일 파싱 테스트

- [ ] `src/common/geocoding_constants.py` (77% → 90%)
  - [ ] 상수 값 검증 테스트

#### 6. Analysis Scripts (Week 3-4)
- [ ] `src/analysis/analysis11_check_missing_dates.py` (신규)
  - [ ] 날짜 파싱 테스트
  - [ ] 누락 검사 로직 테스트
  - [ ] 보고서 생성 테스트

- [ ] `src/analysis/analyze_duplicate_cnt_jnt_correlation_v2.py`
  - [ ] 상관관계 계산 테스트
  - [ ] 중복 탐지 테스트

### 🔵 공간 통계 분석 스크립트 (Week 3-4)

#### 7. Spatial Analysis Scripts (main20-30)
- [ ] `src/main20_optimize_parameters.py`
  - [ ] 파라미터 최적화 알고리즘 테스트
  - [ ] 교차 검증 테스트
  - [ ] 민감도 분석 테스트

- [ ] `src/main22_spatial_hotspots.py`
  - [ ] Getis-Ord Gi* 계산 테스트
  - [ ] Moran's I 계산 테스트
  - [ ] 핫스팟 분류 테스트

- [ ] `src/main24_spacetime_cube.py`
  - [ ] 시공간 큐브 생성 테스트
  - [ ] 시계열 분석 테스트
  - [ ] Knox test 테스트

## 🛠️ 테스트 개선 전략

### 1. 테스트 구조 개선
- [ ] pytest fixtures 표준화
  - [ ] 공통 테스트 데이터 fixture 생성
  - [ ] 임시 파일 관리 fixture
  - [ ] 모킹 헬퍼 fixture

- [ ] conftest.py 최적화
  - [ ] 전역 fixture 정의
  - [ ] 테스트 데이터 경로 설정
  - [ ] 공통 assertion 헬퍼

### 2. 모킹 및 격리
- [ ] 외부 의존성 모킹
  - [ ] API 호출 (Kakao/Naver Maps)
  - [ ] 데이터베이스 연결
  - [ ] 파일 I/O 작업

- [ ] 테스트 데이터셋 생성
  - [ ] 최소 크기 샘플 데이터
  - [ ] 엣지 케이스 데이터
  - [ ] 성능 테스트용 대용량 데이터

### 3. 테스트 유형별 구성
- [ ] 단위 테스트 (Unit Tests)
  - [ ] 각 함수별 독립적 테스트
  - [ ] 입력 검증 테스트
  - [ ] 에러 처리 테스트

- [ ] 통합 테스트 (Integration Tests)
  - [ ] 모듈 간 상호작용 테스트
  - [ ] 데이터 플로우 테스트
  - [ ] 파이프라인 테스트

- [ ] 회귀 테스트 (Regression Tests)
  - [ ] 알려진 버그 수정 확인
  - [ ] 기능 변경 시 기존 기능 보장

### 4. 커버리지 측정 개선
- [ ] coverage 설정 최적화
  - [ ] `.coveragerc` 파일 구성
  - [ ] 제외 패턴 정의
  - [ ] 브랜치 커버리지 활성화

- [ ] CI/CD 파이프라인 통합
  - [ ] GitHub Actions 설정
  - [ ] 커버리지 리포트 자동 생성
  - [ ] PR별 커버리지 변화 추적

## 📈 예상 커버리지 진행도

| 주차 | 목표 커버리지 | 주요 작업 |
|------|--------------|----------|
| Week 1 | 30% | Core utilities + Data I/O |
| Week 2 | 50% | Infrastructure + Repair |
| Week 3 | 65% | Analysis scripts |
| Week 4 | 80% | Spatial analysis + 최적화 |

## 🚀 실행 계획

### Week 1: 기초 다지기
1. 가장 낮은 커버리지 파일부터 시작
2. 공통 fixture 및 헬퍼 함수 작성
3. 핵심 유틸리티 모듈 테스트 완성

### Week 2: 메인 스크립트 집중
1. main1-10 스크립트 테스트 작성
2. 통합 테스트 추가
3. 모킹 전략 구현

### Week 3: 분석 모듈 강화
1. analysis 디렉토리 테스트
2. 공간 통계 모듈 테스트
3. 데이터 검증 테스트

### Week 4: 마무리 및 최적화
1. main20-30 스크립트 테스트
2. 성능 테스트 추가
3. CI/CD 파이프라인 구성

## 📋 체크리스트

### 테스트 작성 원칙
- [ ] 각 함수당 최소 3개 테스트 케이스 (정상, 경계, 에러)
- [ ] 모든 예외 처리 경로 테스트
- [ ] 엣지 케이스 포함
- [ ] 테스트 독립성 보장
- [ ] 명확한 테스트 명명 규칙

### 품질 기준
- [ ] 단일 테스트 실행 시간 < 1초
- [ ] 전체 테스트 실행 시간 < 5분
- [ ] 테스트 flakiness 제로
- [ ] 코드 리뷰 후 머지

## 📚 참고 자료
- pytest 공식 문서: https://docs.pytest.org/
- coverage.py 문서: https://coverage.readthedocs.io/
- 테스트 주도 개발 (TDD) 가이드
- Python Testing Best Practices

## 🎉 마일스톤
- [ ] 30% 커버리지 달성 🎯
- [ ] 50% 커버리지 달성 🎯
- [ ] 80% 커버리지 달성 🏆
- [ ] CI/CD 파이프라인 구축 완료 ✅
- [ ] 모든 PR에 테스트 필수화 📝