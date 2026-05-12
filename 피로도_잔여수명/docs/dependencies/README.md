# 의존성 분석 결과

이 폴더는 pydeps를 사용하여 생성된 프로젝트 의존성 분석 결과를 포함합니다.

## 📁 파일 구조

### 시각화 파일 (SVG)
- `deps_internal.svg` - 내부 모듈 간 의존성 그래프
- `deps_all.svg` - 외부 라이브러리 포함 전체 의존성 그래프
- `deps_common.svg` - common 모듈의 의존성 그래프
- `deps_analysis.svg` - analysis 모듈의 의존성 그래프
- `src.svg` - src 패키지 전체 의존성 그래프

### 분석 리포트
- `DEPENDENCIES.md` - 의존성 분석 요약 및 주요 발견사항
- `dependency_structure.txt` - 텍스트 형식의 의존성 구조
- `dependency_structure.json` - JSON 형식의 의존성 구조
- `raw_dependencies.json` - 원시 의존성 데이터 (상세)

## 🔍 의존성 분석 재실행

프로젝트 루트에서 다음 명령을 실행하여 의존성 분석을 다시 수행할 수 있습니다:

```bash
python analyze_dependencies.py
```

또는 개별 명령:

```bash
# 내부 의존성만
pydeps src --max-bacon 2 --cluster --only src -o docs/dependencies/deps_internal.svg

# 전체 의존성
pydeps src --max-bacon 2 --cluster -o docs/dependencies/deps_all.svg
```

## 📊 시각화 보기

SVG 파일은 웹 브라우저에서 직접 열어볼 수 있습니다:

```bash
open deps_internal.svg  # macOS
xdg-open deps_internal.svg  # Linux
start deps_internal.svg  # Windows
```

## 🛠️ 필요 도구

- Python 3.11+
- pydeps (`pip install pydeps`)
- graphviz (`brew install graphviz` on macOS)