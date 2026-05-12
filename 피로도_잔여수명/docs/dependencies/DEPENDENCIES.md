# 프로젝트 의존성 분석

pydeps를 사용하여 생성된 프로젝트 의존성 분석 결과입니다.

## 생성된 의존성 그래프

1. **deps_internal.svg** - 내부 모듈 간 의존성만 표시
2. **deps_all.svg** - 외부 라이브러리 포함 전체 의존성
3. **deps_common.svg** - common 모듈의 의존성
4. **deps_analysis.svg** - analysis 모듈의 의존성

## 주요 발견사항

### 핵심 의존 모듈
- `src.common.config`: 거의 모든 모듈에서 사용하는 중앙 설정 모듈
- `src.common`: 공통 유틸리티 모듈로 전체 프로젝트에서 참조

### 외부 라이브러리 의존성
- **geopandas**: GIS 데이터 처리 (대부분의 main 모듈에서 사용)
- **matplotlib**: 시각화 (main2, main3, main6, main8, main9, main10에서 사용)
- **pandas**: 데이터 처리 (fatigue_loader, recovery_loader 등에서 사용)
- **numpy**: 수치 계산 (main10에서 직접 사용)
- **shapely**: 지리 객체 처리 (main10에서 사용)

### 모듈 구조
1. **common 모듈**: 재사용 가능한 로더와 유틸리티
   - config.py: 프로젝트 설정
   - 각종 loader: 데이터 로딩 담당
   - korean_font_utils: 한글 폰트 처리

2. **analysis 모듈**: 데이터 분석 스크립트
   - 모두 common.config에 의존
   - 독립적으로 실행 가능

3. **main 모듈**: 주요 실행 스크립트
   - common 모듈의 loader들을 활용
   - 시각화가 필요한 경우 matplotlib 사용

### 순환 의존성
- 순환 의존성 없음 (pydeps --show-cycles 결과)

## 의존성 그래프 보기

SVG 파일들을 웹 브라우저나 이미지 뷰어로 열어서 시각적으로 확인할 수 있습니다:

```bash
open deps_internal.svg  # macOS
```

## pydeps 사용법

```bash
# 내부 의존성만 보기
pydeps src --max-bacon 2 --cluster --only src -o docs/dependencies/deps_internal.svg

# 전체 의존성 보기
pydeps src --max-bacon 2 --cluster -o docs/dependencies/deps_all.svg

# 순환 의존성 확인
pydeps src --show-cycles

# 텍스트로 의존성 보기
pydeps src --show-deps --only src --no-output
```