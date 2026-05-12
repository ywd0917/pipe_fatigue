# Geocoding 성능 최적화 가이드

## 개요
이 문서는 지오코딩 시스템의 성능 최적화 과정과 결과를 설명합니다.

## 최적화 내역

### 1. JSON 캐시에서 SQLite로 전환 (9.7배 성능 향상)

#### 문제점
- JSON 파일 기반 캐시는 전체 파일을 메모리에 로드
- 19,000개 이상의 캐시 항목 시 메모리 사용량 증가
- 파일 I/O로 인한 성능 저하

#### 해결책
- SQLite 데이터베이스 기반 캐시로 전환
- 인덱싱으로 빠른 검색 지원
- 메모리 효율적인 쿼리 기반 접근

#### 성능 측정 결과
```
JSON 캐시: 100개 주소 처리 시 31초
SQLite 캐시: 100개 주소 처리 시 3.2초
성능 향상: 9.7배
```

### 2. 싱글톤 패턴 적용

#### 구현 방식
```python
class GeocodingCacheSQLite:
    _instance = None
    _initialized = False
    
    def __new__(cls, db_file: Path = CACHE_DB):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

#### 효과
- 캐시 인스턴스 재사용으로 초기화 오버헤드 제거
- DB 연결 관리 최적화

### 3. API 재시도 로직 최적화

#### 지수 백오프 구현
```python
# geocoding_constants.py
MAX_RETRIES = 3
RETRY_BASE_WAIT_TIME = 5
RETRY_BACKOFF_FACTOR = 2

def calculate_retry_wait_time(attempt: int) -> int:
    return int(RETRY_BASE_WAIT_TIME * (RETRY_BACKOFF_FACTOR ** (attempt - 1)))
```

#### 재시도 전략
- 연결 오류: 5초 → 10초 → 20초
- 5xx 서버 오류: 재시도
- 4xx 클라이언트 오류: 재시도 안함

### 4. 캐시 재시도 로직

#### 시간 기반 재시도
```python
# not_found 캐시 확인
if cached["status"] == "not_found":
    days_passed = (current_time - cached_time) / (60 * 60 * 24)
    if days_passed >= CACHE_RETRY_DAYS:  # 1일
        # 재시도
    else:
        return None  # 패스
```

#### 효과
- 불필요한 API 호출 감소
- 주기적인 재확인으로 정확도 향상

## 성능 벤치마크

### 테스트 환경
- 데이터셋: 19,312개 주소
- 캐시 히트율: 약 80%
- API 지연: 0.1초/요청

### 측정 결과

| 구현 방식 | 처리 시간 | 메모리 사용량 | API 호출 수 |
|-----------|----------|--------------|------------|
| JSON 캐시 (v1) | 51분 | 450MB | 3,862 |
| SQLite 캐시 (v2) | 5.3분 | 85MB | 3,862 |
| SQLite + 재시도 로직 (v3) | 5.5분 | 85MB | 1,200 |

## 최적화 팁

### 1. 대량 처리 시
```bash
# API 지연 시간 조정
python src/main11_convert_addr2loc.py --api-delay 0.05

# 캐시 통계 확인
sqlite3 results/geocoding_cache_naver.db \
  "SELECT status, COUNT(*) FROM geocoding_cache GROUP BY status"
```

### 2. 메모리 효율
- SQLite는 필요한 데이터만 로드
- 대용량 CSV도 스트리밍 처리

### 3. 캐시 관리
```python
# 캐시 통계 확인
from src.common.geocoding_naver_sqlite import get_cache_stats
stats = get_cache_stats()
print(f"성공률: {stats['success_rate']:.1f}%")
```

## 향후 개선 사항

### 1. 병렬 처리
- 멀티스레딩으로 API 호출 병렬화
- SQLite WAL 모드 활용

### 2. 캐시 압축
- 오래된 캐시 항목 압축
- 캐시 크기 제한 옵션

### 3. 지능형 재시도
- 주소 패턴 학습
- 성공 가능성 예측

## 모니터링

### 로그 분석
```bash
# API 호출 통계
grep "API 호출" app.log | wc -l

# 캐시 히트율
grep "캐시에서 찾음" app.log | wc -l

# 재시도 현황
grep "재시도" app.log | grep -E "[0-9]+일 경과"
```

### 성능 프로파일링
```python
import cProfile
cProfile.run('main()', 'profile_stats')
```

## 관련 문서
- [geocoding_usage.md](geocoding_usage.md) - 사용 가이드
- [main11_convert_addr2loc_call_graph.md](call_graph/main11_convert_addr2loc_call_graph.md) - 함수 호출 구조