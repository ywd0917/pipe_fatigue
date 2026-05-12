"""
geocoding_constants.py 테스트
지오코딩 관련 상수 및 유틸리티 함수 테스트
"""

import pytest

from src.common.geocoding_constants import (
    API_TIMEOUT,
    CACHE_RETRY_DAYS,
    DEFAULT_API_DELAY,
    HTTP_SERVER_ERROR_THRESHOLD,
    MAX_RETRIES,
    PROGRESS_LOG_INTERVAL,
    RETRY_BACKOFF_FACTOR,
    RETRY_BASE_WAIT_TIME,
    STATISTICS_LOG_INTERVAL,
    calculate_retry_wait_time,
)


class TestGeocodingConstants:
    """지오코딩 상수 테스트"""

    def test_api_settings_constants(self):
        """API 설정 상수 값 검증"""
        assert MAX_RETRIES == 3
        assert RETRY_BASE_WAIT_TIME == 5
        assert RETRY_BACKOFF_FACTOR == 2
        assert API_TIMEOUT == 5
        assert DEFAULT_API_DELAY == 0.1

    def test_progress_settings_constants(self):
        """진행 상황 표시 상수 값 검증"""
        assert PROGRESS_LOG_INTERVAL == 100
        assert STATISTICS_LOG_INTERVAL == 500

    def test_http_and_cache_constants(self):
        """HTTP 및 캐시 관련 상수 값 검증"""
        assert HTTP_SERVER_ERROR_THRESHOLD == 500
        assert CACHE_RETRY_DAYS == 1

    def test_constants_types(self):
        """상수 타입 검증"""
        assert isinstance(MAX_RETRIES, int)
        assert isinstance(RETRY_BASE_WAIT_TIME, int)
        assert isinstance(RETRY_BACKOFF_FACTOR, int)
        assert isinstance(API_TIMEOUT, int)
        assert isinstance(DEFAULT_API_DELAY, float)
        assert isinstance(PROGRESS_LOG_INTERVAL, int)
        assert isinstance(STATISTICS_LOG_INTERVAL, int)
        assert isinstance(HTTP_SERVER_ERROR_THRESHOLD, int)
        assert isinstance(CACHE_RETRY_DAYS, int)

    def test_constants_positive_values(self):
        """모든 상수가 양수인지 검증"""
        assert MAX_RETRIES > 0
        assert RETRY_BASE_WAIT_TIME > 0
        assert RETRY_BACKOFF_FACTOR > 0
        assert API_TIMEOUT > 0
        assert DEFAULT_API_DELAY > 0
        assert PROGRESS_LOG_INTERVAL > 0
        assert STATISTICS_LOG_INTERVAL > 0
        assert HTTP_SERVER_ERROR_THRESHOLD > 0
        assert CACHE_RETRY_DAYS > 0


class TestCalculateRetryWaitTime:
    """calculate_retry_wait_time 함수 테스트"""

    def test_zero_attempt(self):
        """시도 횟수가 0일 때"""
        assert calculate_retry_wait_time(0) == 0

    def test_negative_attempt(self):
        """시도 횟수가 음수일 때"""
        assert calculate_retry_wait_time(-1) == 0
        assert calculate_retry_wait_time(-10) == 0

    def test_first_attempt(self):
        """첫 번째 재시도"""
        # 5 * (2 ** 0) = 5
        assert calculate_retry_wait_time(1) == 5

    def test_second_attempt(self):
        """두 번째 재시도"""
        # 5 * (2 ** 1) = 10
        assert calculate_retry_wait_time(2) == 10

    def test_third_attempt(self):
        """세 번째 재시도"""
        # 5 * (2 ** 2) = 20
        assert calculate_retry_wait_time(3) == 20

    def test_exponential_backoff(self):
        """지수 백오프 패턴 검증"""
        # 각 시도마다 대기 시간이 2배씩 증가
        wait_times = [calculate_retry_wait_time(i) for i in range(1, 6)]
        expected = [5, 10, 20, 40, 80]
        assert wait_times == expected

    def test_return_type(self):
        """반환 타입이 정수인지 확인"""
        assert isinstance(calculate_retry_wait_time(0), int)
        assert isinstance(calculate_retry_wait_time(1), int)
        assert isinstance(calculate_retry_wait_time(5), int)

    @pytest.mark.parametrize(
        "attempt,expected",
        [
            (0, 0),
            (1, 5),
            (2, 10),
            (3, 20),
            (4, 40),
            (5, 80),
            (10, 2560),
        ],
    )
    def test_various_attempts(self, attempt, expected):
        """다양한 시도 횟수에 대한 테스트"""
        assert calculate_retry_wait_time(attempt) == expected

    def test_large_attempt_number(self):
        """큰 시도 횟수에 대한 처리"""
        # 큰 수에서도 정상 작동하는지 확인
        result = calculate_retry_wait_time(20)
        assert isinstance(result, int)
        assert result > 0
        # 5 * (2 ** 19) = 2621440
        assert result == 2621440
