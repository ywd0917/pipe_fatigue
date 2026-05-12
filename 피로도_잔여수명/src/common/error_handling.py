"""
에러 처리 공통 유틸리티

이 모듈은 표준화된 에러 처리와 예외 관리 기능을 제공합니다.
"""

import functools
import logging
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DataProcessingError(Exception):
    """데이터 처리 중 발생하는 일반적인 오류"""


class FileNotFoundError(DataProcessingError):
    """파일을 찾을 수 없을 때 발생하는 오류"""


class ValidationError(DataProcessingError):
    """데이터 검증 실패시 발생하는 오류"""


class ConfigurationError(DataProcessingError):
    """설정 관련 오류"""


def handle_errors(
    default_return: Any = None,
    log_level: str = "ERROR",
    reraise: bool = False,
    error_types: tuple[type[Exception], ...] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T | Any]]:
    """
    함수의 에러를 처리하는 데코레이터

    Args:
        default_return: 에러 발생시 반환할 기본값
        log_level: 로그 레벨 (ERROR, WARNING, INFO, DEBUG)
        reraise: 에러를 다시 발생시킬지 여부
        error_types: 처리할 에러 타입들 (None이면 모든 Exception)

    사용 예:
        @handle_errors(default_return=None, log_level="WARNING")
        def risky_function():
            return 1 / 0
    """
    if error_types is None:
        error_types = (Exception,)

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T | Any:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                # 로깅
                log_func = getattr(logger, log_level.lower())
                log_func(
                    f"Error in {func.__name__}: {e}\n"
                    f"Traceback:\n{traceback.format_exc()}"
                )

                # 재발생
                if reraise:
                    raise

                # 기본값 반환
                return default_return

        return wrapper

    return decorator


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """
    에러 발생시 재시도하는 데코레이터

    Args:
        max_attempts: 최대 시도 횟수
        delay: 재시도 간 대기 시간 (초)
        backoff: 대기 시간 증가 배수
        exceptions: 재시도할 예외 타입들

    사용 예:
        @retry_on_error(max_attempts=3, delay=1.0)
        def unstable_network_call():
            return requests.get("http://example.com")
    """
    import time

    if exceptions is None:
        exceptions = (Exception,)

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T | None:
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            e,
                        )
                        raise

                    logger.warning(
                        "%s attempt %d failed: %s. Retrying in %s seconds...",
                        func.__name__,
                        attempt,
                        e,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
            return None

        return wrapper

    return decorator


def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default: Any = None,
    error_msg: str | None = None,
    **kwargs: Any,
) -> T | Any:
    """
    함수를 안전하게 실행하고 에러시 기본값 반환

    Args:
        func: 실행할 함수
        *args: 함수 인자
        default: 에러시 반환할 기본값
        error_msg: 에러 메시지 커스터마이징
        **kwargs: 함수 키워드 인자

    Returns:
        함수 실행 결과 또는 기본값

    사용 예:
        result = safe_execute(int, "123", default=0)  # 123
        result = safe_execute(int, "abc", default=0)  # 0
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_msg:
            logger.error("%s: %s", error_msg, e)
        else:
            logger.error("Error executing %s: %s", func.__name__, e)
        return default


def validate_input(
    validation_func: Callable[[Any], bool], error_msg: str = "Input validation failed"
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    입력값 검증 데코레이터

    Args:
        validation_func: 검증 함수 (True/False 반환)
        error_msg: 검증 실패시 에러 메시지

    사용 예:
        @validate_input(lambda x: x > 0, "Value must be positive")
        def sqrt(x):
            return x ** 0.5
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # 첫 번째 인자에 대해서만 검증
            # self가 있는 메서드인지 확인
            if args:
                # 클래스 메서드인 경우 (첫 인자가 self)
                if (
                    len(args) > 1
                    and hasattr(args[0], "__class__")
                    and hasattr(args[0].__class__, func.__name__)
                ):
                    check_value = args[1]
                else:
                    # 일반 함수인 경우
                    check_value = args[0]

                if not validation_func(check_value):
                    raise ValidationError(f"{error_msg}: {check_value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


class ErrorContext:
    """
    에러 컨텍스트 관리자

    사용 예:
        with ErrorContext("Processing data", default=None):
            result = process_data()
    """

    def __init__(
        self,
        operation: str,
        default: Any = None,
        log_level: str = "ERROR",
        reraise: bool = False,
    ):
        self.operation = operation
        self.default = default
        self.log_level = log_level
        self.reraise = reraise
        self.logger = logging.getLogger()

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(
        self, exc_type: type[Exception] | None, exc_val: Exception | None, exc_tb: Any
    ) -> bool:
        if exc_type is not None:
            log_func = getattr(self.logger, self.log_level.lower())
            log_func(
                f"Error during {self.operation}: {exc_val}\n"
                f"Type: {exc_type.__name__}\n"
                f"Traceback:\n{''.join(traceback.format_tb(exc_tb))}"
            )

            if not self.reraise:
                return True  # 예외 억제

        return False  # 예외 전파


def format_error_message(
    error: Exception,
    context: dict[str, Any] | None = None,
    include_traceback: bool = False,
) -> str:
    """
    에러 메시지를 표준 형식으로 포맷팅

    Args:
        error: 예외 객체
        context: 추가 컨텍스트 정보
        include_traceback: 트레이스백 포함 여부

    Returns:
        포맷된 에러 메시지
    """
    parts = [f"Error Type: {type(error).__name__}", f"Message: {error!s}"]

    if context:
        context_str = "\n".join([f"  {k}: {v}" for k, v in context.items()])
        parts.append(f"Context:\n{context_str}")

    if include_traceback:
        parts.append(f"Traceback:\n{traceback.format_exc()}")

    return "\n".join(parts)


def create_error_report(
    error: Exception,
    operation: str,
    input_data: dict[str, Any] | None = None,
    output_file: str | None = None,
) -> dict[str, Any]:
    """
    에러 리포트 생성

    Args:
        error: 예외 객체
        operation: 수행 중이던 작업
        input_data: 입력 데이터 정보
        output_file: 리포트 저장 파일 경로

    Returns:
        에러 리포트 딕셔너리
    """
    import json
    from datetime import datetime

    report = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc().split("\n"),
        },
        "input_data": input_data or {},
        "environment": {"python_version": sys.version, "platform": sys.platform},
    }

    if output_file:
        output_path = Path(output_file)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("Error report saved to %s", output_file)

    return report
