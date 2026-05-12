# main11b: 긴급공사 데이터 병합 및 지오코딩

**파일명**: `main11b_merge_n_add2loc.py`

## 📋 개요
두 긴급공사 CSV 파일의 중복을 제거하고 병합한 후 지오코딩을 수행합니다.

## 🚀 사용법

```bash
python src/main11b_merge_n_add2loc.py  # API 호출하여 지오코딩 (기본: naver)
python src/main11b_merge_n_add2loc.py --geocoding-service kakao  # Kakao API 사용
python src/main11b_merge_n_add2loc.py --no-api  # 오프라인 모드 (캐시만 사용)
```

## 🎛️ 옵션
- `--no-api`: API 호출 없이 캐시만 사용 (오프라인 모드)
- `--geocoding-service`: 지오코딩 서비스 선택 (kakao/naver, 기본값: naver)

## 📥 입력 파일
- `data/repair/긴급복구.csv`: 긴급복구 데이터
- `data/repair/긴급복구공사관리(0520).csv`: 긴급복구공사관리 데이터

## 📤 출력 파일
- `results/긴급공사_위치추가.csv`: 병합 및 지오코딩된 데이터
  - 중복 제거된 전체 데이터
  - 위도/경도 컬럼 추가
  - 작업일시 통합 컬럼
- `results/긴급공사_위치추가_실패주소.txt`: 지오코딩 실패 주소 목록

## ✨ 주요 기능
- 접수번호 기준 중복 제거 (긴급복구.csv 우선)
- 두 파일 병합
- 작업일시 통합 (접수일시 > 작업시작 > 작업종료 우선순위)
- 주소 지오코딩 (Naver/Kakao API)
- 캐시 시스템으로 API 호출 최소화

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main11b_merge_n_add2loc_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main11a*.py`](main11a*.md)
- 다음: [`main11c*.py`](main11c*.md)
