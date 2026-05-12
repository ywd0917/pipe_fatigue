# main11e: 재작업 데이터 통합

**파일명**: `main11e_merge_all_repairs.py`

## 📋 개요
여러 위치추가 CSV 파일들을 하나의 통합 파일로 병합합니다. 3개의 형식이 다른 CSV 파일들을 하나로 통합하는 스크립트.

## 📥 입력 파일
- `results/지상누수_위치추가.csv`: 지상누수 작업 데이터 (ID: 긴급복구공사일련번호)
- `results/지하누수_위치추가.csv`: 지하누수 작업 데이터 (ID: 긴급복구공사일련번호)
- `results/기타공사_위치추가.csv`: 기타공사 작업 데이터 (사용 안함. 주석 처리됨)
- `results/긴급공사_위치추가.csv`: 긴급공사 작업 데이터 (ID: 접수번호)
- `results/관리대장_위치추가.csv`: 관리대장 작업 데이터 (ID: 접수번호)

## 🚀 사용법

```bash
python src/main11e_merge_all_repairs.py  # 기본 실행 (옥내 필터링 ON)
python src/main11e_merge_all_repairs.py --no-filter-indoor  # 옥내 필터링 OFF
python src/main11e_merge_all_repairs.py --verbose  # 상세 정보 출력
python src/main11e_merge_all_repairs.py --output-dir custom_dir  # 출력 디렉토리 지정
```

## 🎛️ 옵션
- `--output-dir`: 출력 디렉토리 (기본값: results/main11e_merge_all_repairs)
- `--verbose`: 상세 정보 출력
- `--no-filter-indoor`: '옥내' 텍스트 필터링 비활성화 (기본: 필터링 활성화)

## 📤 출력 파일
- `results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv`: 통합된 데이터
  - ID: 각 원본 파일의 고유 식별자 (첫 번째 컬럼)
  - 작업일시: 통합된 날짜 정보 (main11에서 생성)
  - 위도, 경도: 지오코딩된 좌표
  - 파일타입: 원본 파일 구분 (지상누수, 지하누수 등)
  - **추가된 공통 컬럼**: `공사명`, `공사개요`, `구군`, `주소`, `중구역번호`, `소구역번호`, `도로구분`, `누수관경`, `누수량`, `용수구분`, `용도구분`
- `results/main11e_merge_all_repairs/통합_요약.txt`: 통합 통계

## ✨ 주요 기능
- TARGET_FILES 리스트의 모든 CSV 파일 병합
- **3단계 데이터 처리 프로세스**:
- **'옥내' 텍스트 필터링** (기본 활성화)
- main11f의 SEARCH_COLUMNS 매핑 활용
- 유니코드 정규화 지원 (NFC/NFD 모두 검색)
- `--no-filter-indoor` 옵션으로 비활성화 가능
- 필수 컬럼 검증 (작업일시, 위도, 경도)
- 작업일시: main11 스크립트들이 생성한 통합 날짜 컬럼
- 위도/경도: 지오코딩된 좌표
- 누락된 컬럼이 있으면 파일명과 함께 오류 표시

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main11e_merge_all_repairs_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main11d*.py`](main11d*.md)
- 다음: [`main11f*.py`](main11f*.md)
