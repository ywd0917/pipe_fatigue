# main11: 주소 지오코딩

**파일명**: `main11_convert_addr2loc.py`

## 📋 개요
복구 작업 CSV 파일의 주소를 위도/경도로 변환하고 작업일시 컬럼을 통합합니다.

## 🚀 사용법

```bash
python src/main11_convert_addr2loc.py  # 모든 CSV 파일
python src/main11_convert_addr2loc.py 기타공사.csv 지상누수.csv  # 특정 파일
python src/main11_convert_addr2loc.py --geocoding-service kakao  # Kakao API
python src/main11_convert_addr2loc.py --no-cache  # 캐시 미사용
python src/main11_convert_addr2loc.py --no-api    # 오프라인 모드 (캐시만 사용)
```

## 🎛️ 옵션
- `--geocoding-service {naver,kakao}`: 지오코딩 서비스 선택 (기본: naver)
- `--no-cache`: 캐시 사용 안 함 (항상 API 호출)
- `--no-api`: API 호출 없이 SQLite 캐시만 사용 (오프라인 모드)
- 캐시에 없는 주소는 변환 실패로 처리
- API 키가 없어도 동작 가능
- 네트워크 연결 불필요
- `--api-delay`: API 호출 간 지연 시간 (초, 기본: 0.02)
- `--input-dir`: 입력 디렉토리 (기본: data/repair2)
- `--output-dir`: 출력 디렉토리 (기본: results)
- `--quiet`: 최소 정보만 출력

## 📥 입력 파일
- `data/repair2/*.csv`: 재작업 CSV 파일 (기타공사.csv, 지상누수.csv, 지하누수.csv 등)
- 필수 컬럼: 주소 (한글 주소)
- 날짜 컬럼: 접수일시, 작업시작일시, 작업종료일 (우선순위 순)
  - 지원 형식: 12자리(YYYYMMDDHHMM) 또는 14자리(YYYYMMDDHHMMSS)

## 📤 출력 파일
- `results/*_위치추가.csv`: 좌표 추가된 CSV
- 추가 컬럼: 위도, 경도, 작업일시
- `results/*_위치추가_실패주소.txt`: 실패 목록
- `results/geocoding_cache_*.db`: API 캐시

## ✨ 주요 기능
- **작업일시 컬럼 통합**: 날짜 우선순위에 따라 통합
  - 1순위: 접수일시
  - 2순위: 작업시작일시
  - 3순위: 작업종료일
- **다양한 날짜 형식 지원**:
  - 12자리: YYYYMMDDHHMM (분까지)
  - 14자리: YYYYMMDDHHMMSS (초 포함)
  - 13자리 등 비정상 형식: 자동 파싱 시도
  - 출력 형식: YYYY-MM-DD HH:MM:SS
- Naver/Kakao Maps API 지원
- SQLite 캐시로 9.7배 성능 향상
- 오프라인 모드 지원 (--no-api 옵션)
- Unicode NFC 정규화
- 지수 백오프 재시도

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main11_convert_addr2loc_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main10*.py`](main10*.md)
- 다음: [`main11a*.py`](main11a*.md)
