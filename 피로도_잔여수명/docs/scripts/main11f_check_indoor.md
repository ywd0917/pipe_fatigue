# main11f: '옥내' 텍스트 검색

**파일명**: `main11f_check_indoor.py`

## 📋 개요
누수 복구 작업 데이터에서 '옥내' 관련 작업을 식별하고 통계 분석합니다.

## 🚀 사용법

```bash
python src/main11f_check_indoor.py  # 기본 실행
python src/main11f_check_indoor.py --verbose  # 상세 정보 출력
python src/main11f_check_indoor.py --export-matches  # '옥내' 포함 행을 별도 CSV로 추출
python src/main11f_check_indoor.py --output-dir custom_dir  # 출력 디렉토리 지정
```

## 📥 입력 파일
- `results/지상누수_위치추가.csv`: 지상누수 작업 데이터
- `results/지하누수_위치추가.csv`: 지하누수 작업 데이터
- `results/긴급공사_위치추가.csv`: 긴급공사 작업 데이터
- `results/관리대장_위치추가.csv`: 관리대장 작업 데이터
- 지상누수/지하누수: 공사개요, 주소, 공사명

## 📤 출력 파일
- `results/main11f_check_indoor/옥내작업_통계.json`: 전체 통계 데이터
- `results/main11f_check_indoor/옥내작업_요약.txt`: 분석 요약 보고서
- `results/main11f_check_indoor/옥내작업_추출.csv`: '옥내' 포함 행 (--export-matches 옵션 시)

## ✨ 주요 기능
- 파일별 '옥내' 텍스트 포함 행 수 및 비율 계산
- **유니코드 정규화 지원** (NFC/NFD 형태 모두 검색)
- 컬럼별 '옥내' 텍스트 분포 분석
- 연도별/월별 '옥내' 작업 추이 분석
- 결과를 JSON, 텍스트, CSV 형식으로 저장

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main11f_check_indoor_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main11e*.py`](main11e*.md)
- 다음: [`main12*.py`](main12*.md)
