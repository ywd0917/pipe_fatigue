# main11c: 공사관리대장 지오코딩

**파일명**: `main11c_cvrt_addr2loc.py`

## 📋 개요
공사관리대장 CSV 파일에서 주소를 좌표로 변환하고 작업일시를 추가합니다.

## 🚀 사용법

```bash
python src/main11c_cvrt_addr2loc.py  # API 호출하여 지오코딩 (기본: naver)
python src/main11c_cvrt_addr2loc.py --geocoding-service kakao  # Kakao API 사용
python src/main11c_cvrt_addr2loc.py --no-api  # 오프라인 모드 (캐시만 사용)
python src/main11c_cvrt_addr2loc.py --test  # 테스트 모드 (작은 데이터셋)
```

## 🎛️ 옵션
- `--no-api`: API 호출 없이 캐시만 사용 (오프라인 모드)
- `--geocoding-service`: 지오코딩 서비스 선택 (kakao/naver, 기본값: naver)
- `--no-cache`: 캐시 사용 안함 (항상 API 호출)
- `--test`: 테스트 모드 (test_10.csv 파일 사용)

## 📥 입력 파일
- `data/repair3/공사관리대장(0520).csv`: 공사관리대장 데이터

## 📤 출력 파일
- `results/관리대장_위치추가.csv`: 지오코딩된 데이터
- 원본 데이터 + 작업일시 컬럼

## ✨ 주요 기능
- '계'/'소계' 행 자동 제외 (지시번호 기준)
- 작업일시 컬럼 생성:
- 접수번호(YYYYMMDD-NNNN)에서 년도 추출
- 공사일자(MM-DD)와 조합하여 YYYY-MM-DD 형식 생성
- 접수번호가 없거나 '-'인 경우 이전 유효 년도 사용
- 위치 컬럼을 위도/경도로 지오코딩
- 캐시 시스템으로 API 호출 최소화

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main11c_cvrt_addr2loc_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main11b*.py`](main11b*.md)
- 다음: [`main11d*.py`](main11d*.md)
