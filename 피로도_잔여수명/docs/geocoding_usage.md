# Geocoding 기능 사용 가이드

## 개요
`main11_convert_addr2loc.py` 스크립트는 복구 작업 CSV 파일의 주소를 실제 위도/경도 좌표로 변환합니다.
Naver Maps API (기본값) 또는 Kakao Maps API를 사용하여 정확한 좌표를 얻습니다.

## 주요 기능
- SQLite 데이터베이스 기반 고성능 캐시 (9.7배 성능 향상)
- API 연결 오류 시 지수 백오프 재시도 (5초, 10초, 20초)
- not_found 캐시 시간 기반 재시도 (1일 경과 시)
- Unicode NFC 정규화 및 특수 표기 자동 제거
- 실패 주소 별도 파일로 저장
- 진행률 표시 및 통계 제공

## 사전 준비

### 1. API 키 발급

#### Naver Maps API (권장)
1. [Naver Cloud Platform Console](https://console.ncloud.com) 접속
2. AI·Application Service > AI·NAVER API > Application 이동
3. 새 애플리케이션 생성 또는 기존 애플리케이션 선택
4. Maps > Geocoding 서비스 체크박스 활성화 및 저장
5. API Key ID와 API Key 확인

#### Kakao Maps API
1. [Kakao Developers](https://developers.kakao.com) 접속
2. 로그인 후 "내 애플리케이션" 클릭
3. "애플리케이션 추가하기" 클릭
4. 앱 정보 입력 후 생성
5. 생성된 앱 클릭 → "앱 키" 메뉴
6. **REST API 키** 복사

### 2. 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 API 키 입력
# Naver API (권장)
NAVER_API_KEY_ID=your_api_key_id_here
NAVER_API_KEY=your_api_key_secret_here

# Kakao API
KAKAO_API_KEY=your_kakao_rest_api_key_here
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

## 사용 방법

### 기본 사용 (Naver API)
```bash
python src/main11_convert_addr2loc.py
```

### 옵션
- `--geocoding-service`: 사용할 서비스 선택 (naver, kakao) - 기본값: naver
- `--no-cache`: 캐시를 사용하지 않고 모든 주소를 새로 변환
- `--api-delay`: API 호출 간 지연 시간 설정 (기본값: 0.1초)
- `--input-dir`: 입력 디렉토리 경로 (기본값: data/recovery2)
- `--output-dir`: 출력 디렉토리 경로 (기본값: results)
- `--quiet`: 최소 정보만 출력

### 예제
```bash
# Naver API 사용 (기본값)
python src/main11_convert_addr2loc.py

# Kakao API 사용
python src/main11_convert_addr2loc.py --geocoding-service kakao

# 특정 파일만 처리
python src/main11_convert_addr2loc.py 기타공사.csv 지상누수.csv

# 캐시 없이 실행
python src/main11_convert_addr2loc.py --no-cache

# API 호출 지연 시간 늘리기 (안정성 향상)
python src/main11_convert_addr2loc.py --api-delay 0.5
```

## 출력 파일
- 위치: `results/`
- 파일명: `{원본파일명}_위치추가.csv`
- 추가 컬럼:
  - `위도`: 변환된 위도 값
  - `경도`: 변환된 경도 값
- 실패 주소: `{원본파일명}_위치추가_실패주소.txt`

## 캐시 시스템

### SQLite 기반 고성능 캐시
- **Naver 캐시**: `results/geocoding_cache_naver.db`
- **Kakao 캐시**: `results/geocoding_cache_kakao_v2.db`
- 동일한 주소는 캐시에서 읽어 API 호출 최소화
- 인덱싱으로 빠른 검색 지원
- 서비스별로 별도 캐시 DB 사용

### 캐시 재시도 로직
- **성공한 주소**: 영구 캐시 (재호출 없음)
- **실패한 주소 (not_found)**:
  - 1일 미만: 재시도하지 않음
  - 1일 이상 경과: API 재호출 시도
- **오류 발생 주소**: 항상 재시도

### 캐시 통계 확인
스크립트 실행 완료 시 자동으로 캐시 통계 표시:
```
캐시 통계:
  - 총 캐시 항목: 18,159개
  - 성공: 15,000개 (82.6%)
  - 주소 못찾음: 3,000개
  - 오류: 159개
```

## API 재시도 로직

### 연결 오류 시
- 최대 3회 재시도
- 지수 백오프: 5초 → 10초 → 20초
- 적용 대상: ConnectionError, Timeout, 5xx 서버 오류

### 클라이언트 오류 시
- 4xx 오류는 재시도하지 않음
- 즉시 실패 처리

## 주소 전처리

자동으로 적용되는 전처리:
1. Unicode NFC 정규화
2. 특수 표기 제거 (B동, 79B 13L, 외91필지 등)
3. 날짜 패턴 제거
4. 괄호 및 슬래시 뒤 내용 제거
5. 시도명 자동 추가 (대구 지역)

## 성능 최적화

### 처리 속도
- SQLite 캐시: 9.7배 성능 향상
- 100개 단위 진행률 표시
- 500개마다 중간 통계 제공

### 메모리 효율
- 스트리밍 방식 CSV 처리
- 대용량 파일도 안정적 처리

## 문제 해결

### API 키 오류
```
[오류] NAVER/KAKAO API 키가 설정되지 않았습니다.
```
→ .env 파일이 있는지, API 키가 올바르게 설정되었는지 확인

### 401 인증 오류
- **Naver**: Client ID와 Secret이 올바른지 확인
- **Kakao**: REST API 키가 맞는지 확인 (JavaScript 키와 혼동 주의)

### 주소를 찾을 수 없음
- 도로명 주소 형식 사용 권장
- 시도명을 주소 앞에 포함
- 특수 문자나 부가 정보 제거

### 타임아웃 오류
```bash
# API 지연 시간 늘리기
python src/main11_convert_addr2loc.py --api-delay 1.0
```

## 서비스 비교

| 항목 | Naver Maps API | Kakao Maps API |
|------|----------------|----------------|
| 정확도 | 매우 높음 | 높음 |
| 무료 쿼터 | 일 100,000건 | 일 300,000건 |
| 인증 방식 | Client ID + Secret | REST API 키 |
| 재시도 지원 | O | O |
| 캐시 DB | geocoding_cache_naver.db | geocoding_cache_kakao_v2.db |

## 관련 파일
- 메인 스크립트: `src/main11_convert_addr2loc.py`
- Naver 모듈: `src/common/geocoding_naver_sqlite.py`
- Kakao 모듈: `src/common/geocoding_kakao_sqlite_v2.py`
- 공통 상수: `src/common/geocoding_constants.py`
- 테스트: `tests/test_main11_convert_addr2loc.py`

## 업데이트 내역
- 2025-08-04: SQLite 캐시 및 재시도 로직 추가
- 2025-08-04: not_found 캐시 시간 기반 재시도 기능 추가
- 2025-08-04: 지오코딩 상수 중앙 집중화