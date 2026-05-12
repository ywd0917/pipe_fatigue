# 리팩토링 가이드

## 개요

이 문서는 fatigue-qgis 프로젝트의 코드 품질 개선을 위한 리팩토링 가이드입니다.
GUIDE.md의 3단계 코드 재편성을 중심으로 체계적인 리팩토링을 진행합니다.

### 리팩토링 범위
- **주요 대상**: `src/main*.py` 파일들과 `src/common/` 모듈
- **제외 대상**: `src/analysis/` 폴더 (임시 분석 스크립트)

## 최우선 과제: 3단계 코드 재편성

현재 프로젝트의 가장 큰 문제는 모든 코드가 제대로 분류되지 않고 섞여 있다는 점입니다.
GUIDE.md에 따라 모든 코드를 다음 3개 범주로 재구성하는 것이 최우선 과제입니다.

### 1. 공통 코드 (Common Code) - `src/common/`
**현재 상태**: 부분적으로 구현됨
- ✅ 이미 분리된 모듈: config.py, korean_font_utils.py, shapefile_loader.py 등
- ❌ 추가 분리 필요: main*.py 파일들에 산재한 유틸리티 함수들

### 2. 특화 코드 (Specialized Code) - `src/`에 생성 필요
**현재 상태**: 존재하지 않음
- ❌ main*.py 파일들 내부의 도메인 로직이 분리되지 않음
- ❌ 파이프, 토양, 도로, 복구 등 각 도메인별 비즈니스 로직이 메인 파일에 혼재
- ❌ 현재 `src/common/`에 특화 로더들이 잘못 위치함

**구현 방향**: 
- 특화 코드는 `src/` 직하에 위치
- `src/common/`의 특화 로더들을 `src/`로 이동
- `src/common/`에는 순수한 공통 유틸리티만 남김

### 3. 프로젝트 코드 (Project Code) - `src/main*.py`
**현재 상태**: 너무 복잡함
- ❌ 메인 함수가 세부 구현을 직접 담당
- ❌ 전체 흐름을 한눈에 파악하기 어려움
- ❌ 방사형 구조가 아닌 복잡한 호출 관계

## 리팩토링 원칙

1. **단계적 접근**: 한 번에 하나의 main*.py 파일씩 리팩토링
2. **Phase 완료 원칙**: **각 Phase가 100% 완료되지 않으면 다음 Phase로 넘어가지 않음**
   - Phase 1이 완전히 끝나야 Phase 2 시작
   - Phase 2가 완전히 끝나야 Phase 3 시작
   - Phase 3이 완전히 끝나야 Phase 4 시작
   - 모든 테스트 통과 및 커버리지 80% 이상 달성이 Phase 완료 기준
3. **테스트 우선**: 리팩토링 프로세스의 핵심 원칙
   - **리팩토링 전**: 기존 코드의 동작을 검증하는 테스트 확보
   - **리팩토링 중**: 변경사항에 맞춰 테스트 코드 수정
   - **리팩토링 후**: 모든 테스트 통과 확인
   - **커밋 전 필수**: 테스트 커버리지 확인 및 누락된 테스트 보완
   - **중요**: 테스트가 모두 통과해야만 커밋 진행
4. **기능 동일성**: 외부 동작은 변경하지 않음
5. **문서화**: 변경 사항은 반드시 문서화
6. **코드 재편성 우선**: 복잡도 감소보다 3단계 구조 확립이 우선
7. **적절한 균형**: 과도한 분리는 가독성을 해치므로 적절한 수준 유지

## 코드 분리의 균형점

### ⚖️ 분리와 통합의 기준

#### 분리해야 할 때
1. **재사용성이 높은 로직**
   - 여러 main*.py에서 공통으로 사용
   - 독립적인 기능 단위로 명확히 구분 가능
   
2. **복잡도가 높은 로직**
   - 20줄 이상의 복잡한 처리 과정
   - 여러 단계의 데이터 변환이 필요한 경우
   
3. **도메인 특화 비즈니스 규칙**
   - 파이프 분석의 핵심 알고리즘
   - 토양 데이터의 특수한 처리 방식

#### 통합을 유지해야 할 때
1. **단순한 설정이나 초기화**
   ```python
   # 분리 불필요 - main에 유지
   fig, ax = plt.subplots(figsize=(12, 8))
   ax.set_title("분석 결과")
   ```

2. **한 곳에서만 사용되는 짧은 로직**
   ```python
   # 분리 불필요 - 5줄 이하의 단순 처리
   if zone_type == "A":
       color = "red"
   else:
       color = "blue"
   ```

3. **메인 흐름의 직접적인 부분**
   - 주요 실행 순서와 직결된 코드
   - 전체 맥락 이해에 필요한 코드

### 📏 적절한 분리 수준 예시

#### ❌ 과도한 분리 (피해야 할 패턴)
```python
# utilities.py
def get_figure_size():
    return (12, 8)

def get_color_for_zone(zone):
    return "red" if zone == "A" else "blue"

def create_subplot():
    return plt.subplots(figsize=get_figure_size())

# main.py
fig, ax = create_subplot()  # 오히려 가독성 저하
```

#### ✅ 적절한 분리
```python
# soil_loader.py
def analyze_soil_layers(shapefile_path: str, target_layers: List[str]) -> pd.DataFrame:
    """토양 레이어별 분석을 수행하는 의미 있는 단위의 함수"""
    # 20-30줄의 복잡한 로직
    # 데이터 로딩, 변환, 분석 포함
    return analyzed_data

# main3_draw_soil.py
def main():
    # 설정은 main에 유지
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 복잡한 분석은 모듈로 위임
    soil_data = analyze_soil_layers(path, ["Layer1", "Layer2"])
    
    # 간단한 시각화 설정은 main에 유지
    ax.set_title("토양 분석 결과")
    plt.show()
```

### 🎯 목표 구조

```
main*.py (10-20줄)
├─> 설정 및 초기화 (main에 유지)
├─> 핵심 비즈니스 로직 (로더 모듈로 분리)
├─> 결과 처리 (간단하면 main, 복잡하면 분리)
└─> 출력/저장 (main에 유지)
```

## 리팩토링 전략

### Phase 1: 특화 코드 분리 (최우선)
1. **특화 모듈 위치 재구성**
   현재 `src/common/`에 잘못 위치한 특화 로더들을 `src/`로 이동:
   - `fatigue_loader.py` - 피로 분석 비즈니스 로직 → `src/`로 이동
   - `soil_loader.py` - 토양 처리 및 분석 로직 → `src/`로 이동
   - `road_loader.py` - 도로 네트워크 처리 로직 → `src/`로 이동
   - `recovery_loader.py` - 복구 분석 및 비교 로직 → `src/`로 이동
   
   `src/common/`에 유지할 공통 모듈:
   - `config.py` - 설정 관리 (공통)
   - `korean_font_utils.py` - 한글 폰트 처리 (공통)
   - `shapefile_loader.py` - GIS 데이터 로딩 기본 기능 (공통)
   
   **중요**: 
   - 각 도메인 파일은 단일 파일로 시작하고, 300줄을 초과할 때만 분리
   - 특화 코드는 `src/` 직하에, 공통 코드는 `src/common/`에 위치

2. **main*.py에서 비즈니스 로직 추출**
   - 복잡한 데이터 처리 로직 → `src/`의 각 로더 모듈로 이동
   - 도메인 특화 계산 → 해당 도메인 로더로
   - 시각화 공통 로직 → `src/common/visualization_utils.py`로 (새로 생성)

### Phase 2: 프로젝트 코드 단순화
1. **메인 함수를 "목차"로 변환**
   ```python
   # Before: 복잡한 구현이 메인에 있음
   def main():
       # 100줄의 복잡한 로직...
   
   # After: 명확한 흐름만 표현
   def main():
       config = load_configuration()
       data = load_pipe_data(config)
       analysis = analyze_fatigue(data)
       visualize_results(analysis)
       save_outputs(analysis)
   ```

2. **방사형 호출 구조 확립**
   - 메인 함수 → 특화 함수들 (단방향)
   - 특화 함수 간 직접 호출 최소화

### Phase 3: 공통 코드 강화
1. **유틸리티 함수 추가 추출**
   - 파일 I/O 패턴 통합
   - 데이터 변환 유틸리티
   - 로깅 및 에러 처리 표준화

2. **기존 공통 모듈 개선**
   - 더 일반적이고 재사용 가능하게
   - 도메인 의존성 제거

## 리팩토링 체크리스트

**상세한 작업 목록은 [TODO.md](./TODO.md)를 참조하세요.**

### 핵심 진행 원칙
- 테스트 우선: 리팩토링 전 테스트 작성 → 리팩토링 → 테스트 통과 → 커밋
- Phase별 100% 완료: 각 Phase가 완전히 끝나야 다음 Phase 시작
- 커버리지 80% 이상: 모든 Phase 완료 시 필수 달성

## 성공 지표

**성공 지표와 진행 상황은 [TODO.md](./TODO.md)의 "🎯 성공 지표" 섹션을 참조하세요.**

## 도구 활용

### 코드 분석
```bash
# 현재 구조 파악
find src -name "*.py" -type f | head -20

# 함수 의존성 분석
python analyze_dependencies.py

# 복잡도 측정 (참고용)
python -m ruff check src/ --select=C90
```

### 리팩토링 도구
```bash
# Import 정리
ruff check --select I --fix

# 코드 포맷팅
black src/

# 타입 체크
mypy src/ --strict
```

## 참고 자료

- [Refactoring by Martin Fowler](https://refactoring.com/)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [SEPARATION_GUIDE.md](./SEPARATION_GUIDE.md) - 적절한 코드 분리 수준 가이드