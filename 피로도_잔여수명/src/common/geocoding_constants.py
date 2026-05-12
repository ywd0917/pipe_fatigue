"""
Geocoding 관련 공통 상수 정의
"""

# API 재시도 설정
MAX_RETRIES = 3  # 최대 재시도 횟수
RETRY_BASE_WAIT_TIME = 5  # 기본 대기 시간 (초)
RETRY_BACKOFF_FACTOR = 2  # 지수 백오프 계수
API_TIMEOUT = 5  # API 요청 타임아웃 (초)

# API 호출 간 지연 시간
DEFAULT_API_DELAY = 0.1  # 기본 API 호출 간 지연 시간 (초)

# 진행 상황 표시 간격
PROGRESS_LOG_INTERVAL = 100  # 진행률 표시 간격 (처리 개수)
STATISTICS_LOG_INTERVAL = 500  # 중간 통계 표시 간격 (처리 개수)

# HTTP 상태 코드
HTTP_SERVER_ERROR_THRESHOLD = 500  # 서버 오류 시작 코드

# 캐시 재시도 설정
CACHE_RETRY_DAYS = 1  # not_found 캐시 재시도 일수 (1일)


def calculate_retry_wait_time(attempt: int) -> int:
    """
    재시도 대기 시간 계산

    Args:
        attempt: 시도 횟수 (0부터 시작)

    Returns:
        대기 시간 (초)
    """
    if attempt <= 0:
        return 0
    return int(RETRY_BASE_WAIT_TIME * (RETRY_BACKOFF_FACTOR ** (attempt - 1)))
