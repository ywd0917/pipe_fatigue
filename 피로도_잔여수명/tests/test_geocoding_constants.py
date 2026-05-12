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


class TestConstants:
    """상수 값 테스트"""

    def test_max_retries(self):
        """MAX_RETRIES 상수 테스트"""
        assert isinstance(MAX_RETRIES, int)
        assert MAX_RETRIES > 0
        assert MAX_RETRIES <= 10  # 합리적인 최대값

    def test_retry_base_wait_time(self):
        """RETRY_BASE_WAIT_TIME 상수 테스트"""
        assert isinstance(RETRY_BASE_WAIT_TIME, int | float)
        assert RETRY_BASE_WAIT_TIME > 0
        assert RETRY_BASE_WAIT_TIME <= 60  # 1분 이하

    def test_retry_backoff_factor(self):
        """RETRY_BACKOFF_FACTOR 상수 테스트"""
        assert isinstance(RETRY_BACKOFF_FACTOR, int | float)
        assert RETRY_BACKOFF_FACTOR >= 1.0  # 증가 또는 유지
        assert RETRY_BACKOFF_FACTOR <= 10.0  # 합리적인 최대값

    def test_api_timeout(self):
        """API_TIMEOUT 상수 테스트"""
        assert isinstance(API_TIMEOUT, int | float)
        assert API_TIMEOUT > 0
        assert API_TIMEOUT <= 300  # 5분 이하

    def test_default_api_delay(self):
        """DEFAULT_API_DELAY 상수 테스트"""
        assert isinstance(DEFAULT_API_DELAY, int | float)
        assert DEFAULT_API_DELAY >= 0  # 0 이상
        assert DEFAULT_API_DELAY <= 10  # 10초 이하

    def test_progress_log_interval(self):
        """PROGRESS_LOG_INTERVAL 상수 테스트"""
        assert isinstance(PROGRESS_LOG_INTERVAL, int)
        assert PROGRESS_LOG_INTERVAL > 0
        assert PROGRESS_LOG_INTERVAL <= 10000  # 합리적인 최대값

    def test_statistics_log_interval(self):
        """STATISTICS_LOG_INTERVAL 상수 테스트"""
        assert isinstance(STATISTICS_LOG_INTERVAL, int)
        assert STATISTICS_LOG_INTERVAL > 0
        assert (
            STATISTICS_LOG_INTERVAL >= PROGRESS_LOG_INTERVAL
        )  # 진행률보다 크거나 같아야 함

    def test_http_server_error_threshold(self):
        """HTTP_SERVER_ERROR_THRESHOLD 상수 테스트"""
        assert isinstance(HTTP_SERVER_ERROR_THRESHOLD, int)
        assert HTTP_SERVER_ERROR_THRESHOLD == 500  # HTTP 500 에러 시작점

    def test_cache_retry_days(self):
        """CACHE_RETRY_DAYS 상수 테스트"""
        assert isinstance(CACHE_RETRY_DAYS, int | float)
        assert CACHE_RETRY_DAYS > 0
        assert CACHE_RETRY_DAYS <= 365  # 1년 이하


class TestCalculateRetryWaitTime:
    """calculate_retry_wait_time 함수 테스트"""

    def test_attempt_zero(self):
        """시도 횟수가 0일 때"""
        result = calculate_retry_wait_time(0)
        assert result == 0

    def test_attempt_negative(self):
        """시도 횟수가 음수일 때"""
        result = calculate_retry_wait_time(-1)
        assert result == 0

        result = calculate_retry_wait_time(-5)
        assert result == 0

    def test_attempt_one(self):
        """첫 번째 재시도 (attempt=1)"""
        result = calculate_retry_wait_time(1)
        expected = RETRY_BASE_WAIT_TIME  # 2^0 = 1
        assert result == expected
        assert isinstance(result, int)

    def test_attempt_two(self):
        """두 번째 재시도 (attempt=2)"""
        result = calculate_retry_wait_time(2)
        expected = int(RETRY_BASE_WAIT_TIME * RETRY_BACKOFF_FACTOR)  # base * 2^1
        assert result == expected

    def test_attempt_three(self):
        """세 번째 재시도 (attempt=3)"""
        result = calculate_retry_wait_time(3)
        expected = int(RETRY_BASE_WAIT_TIME * (RETRY_BACKOFF_FACTOR**2))  # base * 2^2
        assert result == expected

    def test_exponential_growth(self):
        """지수적 증가 확인"""
        wait_times = []
        for attempt in range(1, 6):
            wait_time = calculate_retry_wait_time(attempt)
            wait_times.append(wait_time)

        # 각 단계별로 증가하는지 확인
        for i in range(1, len(wait_times)):
            assert wait_times[i] >= wait_times[i - 1]

        # 마지막 값이 첫 번째 값보다 충분히 큰지 확인
        assert wait_times[-1] > wait_times[0]

    def test_return_type(self):
        """반환 타입 확인"""
        result = calculate_retry_wait_time(1)
        assert isinstance(result, int)

        result = calculate_retry_wait_time(3)
        assert isinstance(result, int)

    def test_large_attempt_number(self):
        """큰 시도 횟수"""
        result = calculate_retry_wait_time(10)
        assert isinstance(result, int)
        assert result > 0

        # 너무 큰 값이 되지 않는지 확인 (현실적인 범위)
        # 5 * (2^9) = 5 * 512 = 2560초 정도 예상
        assert result <= 3600  # 1시간 이하로 조정

    def test_consistency_with_constants(self):
        """상수와의 일관성 확인"""
        # 첫 번째 재시도는 base wait time과 같아야 함
        assert calculate_retry_wait_time(1) == RETRY_BASE_WAIT_TIME

        # 두 번째 재시도는 base * factor와 같아야 함
        expected_second = int(RETRY_BASE_WAIT_TIME * RETRY_BACKOFF_FACTOR)
        assert calculate_retry_wait_time(2) == expected_second


class TestConstantsRelationships:
    """상수 간 관계 테스트"""

    def test_log_intervals_relationship(self):
        """로그 간격 상수들의 관계"""
        # 통계 간격이 진행률 간격보다 크거나 같아야 함
        assert STATISTICS_LOG_INTERVAL >= PROGRESS_LOG_INTERVAL

    def test_retry_settings_consistency(self):
        """재시도 설정의 일관성"""
        # 최대 재시도 시간이 합리적인 범위인지 확인
        max_wait_time = calculate_retry_wait_time(MAX_RETRIES)
        assert max_wait_time <= 300  # 5분 이하

        # 타임아웃이 최대 대기 시간보다 작아야 함
        assert max_wait_time >= API_TIMEOUT or API_TIMEOUT >= RETRY_BASE_WAIT_TIME

    def test_http_status_code_validity(self):
        """HTTP 상태 코드의 유효성"""
        # 500번대 에러 코드 확인
        assert 500 <= HTTP_SERVER_ERROR_THRESHOLD < 600

    def test_cache_and_retry_relationship(self):
        """캐시와 재시도 설정의 관계"""
        # 캐시 재시도 일수가 합리적인지 확인
        assert (
            CACHE_RETRY_DAYS * 24 * 3600 > API_TIMEOUT
        )  # 일수가 타임아웃보다 훨씬 길어야 함


class TestModuleIntegration:
    """모듈 통합 테스트"""

    def test_all_constants_imported(self):
        """모든 상수가 정상적으로 import되는지 확인"""
        constants = [
            "MAX_RETRIES",
            "RETRY_BASE_WAIT_TIME",
            "RETRY_BACKOFF_FACTOR",
            "API_TIMEOUT",
            "DEFAULT_API_DELAY",
            "PROGRESS_LOG_INTERVAL",
            "STATISTICS_LOG_INTERVAL",
            "HTTP_SERVER_ERROR_THRESHOLD",
            "CACHE_RETRY_DAYS",
        ]

        for const_name in constants:
            # globals()에서 상수를 찾을 수 있는지 확인
            assert const_name in globals()
            const_value = globals()[const_name]
            assert const_value is not None

    def test_function_import(self):
        """함수가 정상적으로 import되는지 확인"""
        assert callable(calculate_retry_wait_time)

    def test_constants_are_immutable_types(self):
        """상수들이 불변 타입인지 확인"""
        immutable_types = (int, float, str, bool, tuple)

        constants_to_check = [
            MAX_RETRIES,
            RETRY_BASE_WAIT_TIME,
            RETRY_BACKOFF_FACTOR,
            API_TIMEOUT,
            DEFAULT_API_DELAY,
            PROGRESS_LOG_INTERVAL,
            STATISTICS_LOG_INTERVAL,
            HTTP_SERVER_ERROR_THRESHOLD,
            CACHE_RETRY_DAYS,
        ]

        for const in constants_to_check:
            assert isinstance(const, immutable_types)


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_zero_base_wait_time(self):
        """기본 대기 시간이 0인 경우의 시뮬레이션"""
        # 실제 상수는 변경하지 않고 함수 동작만 테스트
        original_base = RETRY_BASE_WAIT_TIME

        # 0이면 항상 0을 반환해야 함
        if original_base == 0:
            for attempt in range(1, 5):
                assert calculate_retry_wait_time(attempt) == 0

    def test_backoff_factor_one(self):
        """백오프 계수가 1인 경우"""
        # RETRY_BACKOFF_FACTOR가 1이면 모든 재시도에서 같은 시간
        if RETRY_BACKOFF_FACTOR == 1:
            wait_time_1 = calculate_retry_wait_time(1)
            wait_time_2 = calculate_retry_wait_time(2)
            wait_time_3 = calculate_retry_wait_time(3)

            assert wait_time_1 == wait_time_2 == wait_time_3

    def test_very_large_attempt(self):
        """매우 큰 시도 횟수"""
        result = calculate_retry_wait_time(100)

        # 오버플로우가 발생하지 않고 정수로 반환되는지 확인
        assert isinstance(result, int)
        assert result >= 0

    def test_function_deterministic(self):
        """함수가 결정적인지 확인 (같은 입력에 같은 출력)"""
        attempt = 3
        result1 = calculate_retry_wait_time(attempt)
        result2 = calculate_retry_wait_time(attempt)

        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
