# main14b2/main14c2 공통 모듈화 가이드

## 개요

main14b2와 main14c2 스크립트의 중복 코드를 제거하고 공통 모듈로 통합하여 유지보수성과 코드 재사용성을 향상시킨 프로젝트입니다.

## 구조

```
src/
├── main14_common/              # 공통 모듈 디렉토리
│   ├── __init__.py
│   ├── constants.py            # 공통 상수 정의
│   ├── correlation.py          # 상관관계 분석
│   ├── data_loader.py          # 데이터 로딩
│   ├── distance_sensitivity.py # 거리 민감도 분석 (신규)
│   ├── k_factors.py            # K-factor 처리
│   ├── reporting.py            # 보고서 생성
│   ├── result_parser.py        # 결과 파싱 (신규)
│   └── visualization.py        # 시각화 (확장)
├── main14b2_distance_sensitivity.py     # 단일 거리 민감도 분석
└── main14c2_subregion_distance_sensitivity.py  # 다중 지역 거리 민감도 분석
```

## 주요 공통 모듈

### 1. DistanceSensitivityAnalyzer (distance_sensitivity.py)

거리 민감도 분석을 위한 핵심 클래스입니다.

```python
from src.main14_common.distance_sensitivity import DistanceSensitivityAnalyzer

analyzer = DistanceSensitivityAnalyzer()

# 스크립트 실행
result = analyzer.run_analysis_script(
    script_path="src/main14b.py",
    params={"distance": 100},
    timeout=60
)

# 결과 파싱
parsed = analyzer.parse_execution_output(result["stdout"], output_dir)

# 최적 거리 찾기
optimal = analyzer.find_optimal_distance(results, criteria="max_correlation")

# 보고서 생성
report = analyzer.generate_sensitivity_report(distances, results)
```

**주요 기능:**
- 분석 스크립트 실행 및 모니터링
- 실행 결과 파싱
- 최적 거리 탐색
- 민감도 분석 보고서 생성

### 2. ResultParser (result_parser.py)

분석 결과 파싱을 위한 유틸리티 클래스입니다.

```python
from src.main14_common.result_parser import ResultParser

# 상관계수 파싱
correlations = ResultParser.parse_correlations(text, factors)

# 매칭 통계 파싱
stats = ResultParser.parse_matching_stats(text)

# 최적 factor 추출
best = ResultParser.extract_best_factor(text)
```

**주요 기능:**
- 상관계수 및 p-value 파싱
- 매칭 통계 추출
- 최적 factor 식별

### 3. KFactorVisualizer 확장 (visualization.py)

기존 시각화 클래스에 거리 민감도 분석용 메서드를 추가했습니다.

```python
from src.main14_common.visualization import KFactorVisualizer

viz = KFactorVisualizer()

# 거리별 상관계수 트렌드
viz.plot_distance_correlation_trends(results_df, factors)

# 거리별 매칭률
viz.plot_matching_rate_by_distance(results_df)

# 3D 민감도 표면
viz.create_3d_sensitivity_surface(results_df, x_col="distance", 
                                  y_col="region", z_col="correlation")
```

**새로운 메서드:**
- `plot_distance_correlation_trends()`: 거리별 상관계수 변화 시각화
- `plot_matching_rate_by_distance()`: 거리별 매칭률 그래프
- `create_3d_sensitivity_surface()`: 3D 민감도 표면 플롯

## 리팩토링 효과

### 코드 감소
- main14b2: 691줄 → 183줄 (73% 감소)
- main14c2: 769줄 → 264줄 (66% 감소)
- 전체: 1,460줄 → 447줄 + 공통 모듈 430줄 = 877줄 (40% 감소)

### 장점
1. **코드 재사용성**: 공통 로직을 모듈로 분리하여 재사용
2. **유지보수성**: 버그 수정 시 한 곳만 수정하면 됨
3. **확장성**: 새로운 거리 민감도 분석 스크립트 쉽게 추가 가능
4. **테스트 용이성**: 모듈별 단위 테스트 가능

## 사용 예제

### main14b2 사용 예제

```bash
# 기본 실행 (거리 10, 30, 50, 100, 150m)
python src/main14b2_distance_sensitivity.py

# 특정 거리만 테스트
python src/main14b2_distance_sensitivity.py --distances 50 100 150

# 다른 스크립트 사용
python src/main14b2_distance_sensitivity.py --script main14b_alt.py

# 시각화 없이 실행
python src/main14b2_distance_sensitivity.py --no-plots
```

### main14c2 사용 예제

```bash
# 모든 지역 분석
python src/main14c2_subregion_distance_sensitivity.py

# 특정 지역만 분석
python src/main14c2_subregion_distance_sensitivity.py --regions lrgz mrz

# 3D 시각화 포함
python src/main14c2_subregion_distance_sensitivity.py --create-3d

# 사용자 정의 출력 디렉토리
python src/main14c2_subregion_distance_sensitivity.py --output-dir results/custom
```

## 테스트

### 공통 모듈 테스트

```bash
# 모든 공통 모듈 테스트
pytest tests/test_main14_common/ -v

# 특정 모듈 테스트
pytest tests/test_distance_sensitivity.py -v
pytest tests/test_result_parser.py -v
```

### 리팩토링 테스트

```bash
# main14b2 리팩토링 테스트
pytest tests/test_main14b2_refactored.py -v

# main14c2 리팩토링 테스트
pytest tests/test_main14c2_refactored.py -v
```

## 마이그레이션 가이드

기존 스크립트를 공통 모듈 사용으로 전환하는 방법:

### 1. Import 변경

```python
# 기존
from src.main14b2_distance_sensitivity import (
    setup_korean_font,
    parse_analysis_results,
    run_main14b_with_distance
)

# 변경 후
from src.main14_common.distance_sensitivity import DistanceSensitivityAnalyzer
from src.main14_common.result_parser import ResultParser
from src.main14_common.visualization import KFactorVisualizer
from src.common.korean_font_utils import setup_korean_font
```

### 2. 함수 호출 변경

```python
# 기존
result = run_main14b_with_distance(distance, output_dir)
parsed = parse_analysis_results(result_file)

# 변경 후
analyzer = DistanceSensitivityAnalyzer()
result = analyzer.run_analysis_script(
    script_path="src/main14b.py",
    params={"distance": distance}
)
parsed = analyzer.parse_execution_output(result["stdout"], output_dir)
```

### 3. 시각화 변경

```python
# 기존
create_visualizations(df_results, output_dir)

# 변경 후
viz = KFactorVisualizer()
viz.plot_distance_correlation_trends(df_results, save_path=output_dir/"trends.png")
viz.plot_matching_rate_by_distance(df_results, save_path=output_dir/"matching.png")
```

## 향후 개선 사항

1. **비동기 실행**: 여러 거리를 병렬로 실행하여 성능 향상
2. **캐싱**: 반복 실행 시 이전 결과 재사용
3. **설정 파일**: YAML/JSON 설정 파일로 파라미터 관리
4. **웹 인터페이스**: 대시보드 형태의 결과 시각화
5. **자동 최적화**: 베이지안 최적화 등을 통한 최적 거리 자동 탐색

## API 레퍼런스

자세한 API 문서는 다음 파일을 참조하세요:
- [DistanceSensitivityAnalyzer API](api/distance_sensitivity.md)
- [ResultParser API](api/result_parser.md)
- [KFactorVisualizer API](api/visualization.md)

## 문제 해결

### 일반적인 문제

1. **ImportError**: 공통 모듈을 찾을 수 없는 경우
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **TimeoutError**: 스크립트 실행 시간 초과
   ```python
   analyzer.run_analysis_script(..., timeout=120)  # 타임아웃 증가
   ```

3. **한글 폰트 문제**: 시각화에서 한글이 깨지는 경우
   ```python
   from src.common.korean_font_utils import setup_korean_font
   setup_korean_font()
   ```

## 기여 가이드라인

1. 새로운 공통 기능은 `main14_common/` 디렉토리에 추가
2. 각 모듈에 대한 단위 테스트 작성 필수
3. 문서화 주석(docstring) 포함
4. 타입 힌트 사용 권장

## 라이선스

내부 프로젝트 - 무단 배포 금지