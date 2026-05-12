"""
로깅 설정 및 유틸리티

이 모듈은 표준화된 로깅 설정과 유틸리티 함수를 제공합니다.
"""

import logging
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


def setup_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    log_format: str | None = None,
    add_timestamp: bool = True,
) -> logging.Logger:
    """
    로깅 설정 초기화

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (None이면 콘솔만 출력)
        log_format: 로그 포맷 문자열
        add_timestamp: 파일명에 타임스탬프 추가 여부

    Returns:
        설정된 루트 로거
    """
    # 기본 포맷
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 루트 로거 가져오기
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 기존 핸들러 제거
    root_logger.handlers.clear()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 파일 핸들러
    if log_file:
        if add_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_file.parent / f"{log_file.stem}_{timestamp}{log_file.suffix}"

        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """
    모듈별 로거 가져오기

    Args:
        name: 로거 이름 (보통 __name__)
        level: 로그 레벨 (None이면 부모 로거 설정 사용)

    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)

    if level:
        logger.setLevel(getattr(logging, level.upper()))

    return logger


def log_function_call(func: Callable[..., T]) -> Callable[..., T]:
    """
    함수 호출 로깅 데코레이터

    사용 예:
        @log_function_call
        def my_function(arg1, arg2):
            return result
    """

    def wrapper(*args: Any, **kwargs: Any) -> T:
        logger = logging.getLogger(func.__module__)
        func_name = func.__name__

        # 인자 로깅
        args_str = ", ".join([repr(arg) for arg in args])
        kwargs_str = ", ".join([f"{k}={v!r}" for k, v in kwargs.items()])
        all_args = ", ".join(filter(None, [args_str, kwargs_str]))

        logger.debug("Calling %s(%s)", func_name, all_args)

        try:
            result = func(*args, **kwargs)
            logger.debug("%s completed successfully", func_name)
            return result
        except Exception as e:
            logger.error("%s failed: %s", func_name, e)
            raise

    return wrapper


def log_execution_time(func: Callable[..., T]) -> Callable[..., T]:
    """
    함수 실행 시간 로깅 데코레이터

    사용 예:
        @log_execution_time
        def slow_function():
            time.sleep(1)
    """
    import time

    def wrapper(*args: Any, **kwargs: Any) -> T:
        logger = logging.getLogger(func.__module__)
        func_name = func.__name__

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.info("%s took %.2f seconds", func_name, elapsed_time)
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("%s failed after %.2f seconds: %s", func_name, elapsed_time, e)
            raise

    return wrapper


def log_dataframe_info(
    df: Any, name: str = "DataFrame", logger: logging.Logger | None = None
) -> None:
    """
    데이터프레임 정보 로깅

    Args:
        df: pandas DataFrame 또는 GeoDataFrame
        name: 데이터프레임 이름
        logger: 사용할 로거 (None이면 루트 로거)
    """
    if logger is None:
        logger = logging.getLogger()

    logger.info("%s shape: %s", name, df.shape)
    logger.debug("%s columns: %s", name, list(df.columns))

    # 메모리 사용량
    memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024
    logger.debug("%s memory usage: %.2f MB", name, memory_usage)

    # GeoDataFrame인 경우 추가 정보
    if hasattr(df, "geometry"):
        if df.crs:
            logger.debug("%s CRS: %s", name, df.crs)
        if not df.empty:
            geom_types = df.geometry.geom_type.value_counts().to_dict()
            logger.debug("%s geometry types: %s", name, geom_types)


class ProgressLogger:
    """
    진행 상황 로깅 헬퍼

    사용 예:
        progress = ProgressLogger(total=100, logger=logger)
        for i in range(100):
            # 작업 수행
            progress.update(1)
    """

    def __init__(
        self,
        total: int,
        desc: str = "Processing",
        logger: logging.Logger | None = None,
        log_interval: int = 10,
    ):
        self.total = total
        self.desc = desc
        self.logger = logger or logging.getLogger()
        self.log_interval = log_interval
        self.current = 0
        self.last_logged_percent = 0

    def update(self, n: int = 1) -> None:
        """진행 상황 업데이트"""
        self.current += n
        percent = int(self.current * 100 / self.total)

        if percent >= self.last_logged_percent + self.log_interval:
            self.logger.info(
                "%s: %d%% (%d/%d)", self.desc, percent, self.current, self.total
            )
            self.last_logged_percent = percent

    def finish(self) -> None:
        """작업 완료"""
        if self.current < self.total:
            self.current = self.total
        self.logger.info(
            "%s: 100%% completed (%d/%d)", self.desc, self.total, self.total
        )


def create_file_logger(
    name: str, log_file: Path, level: str = "INFO", format_string: str | None = None
) -> logging.Logger:
    """
    파일 전용 로거 생성

    Args:
        name: 로거 이름
        log_file: 로그 파일 경로
        level: 로그 레벨
        format_string: 로그 포맷

    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 파일 핸들러 추가
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")

    if format_string is None:
        format_string = "%(asctime)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 부모 로거로 전파 방지
    logger.propagate = False

    return logger
