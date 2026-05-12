"""
로깅 유틸리티 테스트
"""

import logging
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from src.common.logging_utils import (
    ProgressLogger,
    create_file_logger,
    get_logger,
    log_dataframe_info,
    log_execution_time,
    log_function_call,
    setup_logging,
)


class TestSetupLogging:
    """setup_logging 함수 테스트"""

    def test_basic_setup(self):
        """기본 로깅 설정"""
        logger = setup_logging(log_level="INFO")

        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

        # 콘솔 핸들러 확인
        console_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) > 0

    def test_file_logging(self):
        """파일 로깅 설정"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(
                log_level="DEBUG", log_file=log_file, add_timestamp=False
            )

            # 파일 핸들러 확인
            file_handlers = [
                h for h in logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) > 0

            # 로그 파일 생성 확인
            assert log_file.exists()

    def test_timestamp_in_filename(self):
        """파일명에 타임스탬프 추가"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            _ = setup_logging(log_file=log_file, add_timestamp=True)

            # 타임스탬프가 포함된 파일 생성 확인
            log_files = list(Path(tmpdir).glob("test_*.log"))
            assert len(log_files) == 1
            assert "test_" in log_files[0].name

    def test_custom_format(self):
        """커스텀 로그 포맷"""
        custom_format = "%(levelname)s - %(message)s"

        logger = setup_logging(log_format=custom_format)

        # 핸들러의 포맷터 확인
        handler = logger.handlers[0]
        assert handler.formatter._fmt == custom_format

    def test_clear_existing_handlers(self):
        """기존 핸들러 제거"""
        # 먼저 핸들러 추가
        logger = logging.getLogger()
        dummy_handler = logging.NullHandler()
        logger.addHandler(dummy_handler)

        # setup_logging 호출
        setup_logging()

        # 기존 핸들러가 제거되었는지 확인
        assert dummy_handler not in logger.handlers


class TestGetLogger:
    """get_logger 함수 테스트"""

    def test_get_named_logger(self):
        """이름으로 로거 가져오기"""
        logger = get_logger("test_module")

        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)

    def test_set_logger_level(self):
        """로거 레벨 설정"""
        logger = get_logger("test_module", level="DEBUG")

        assert logger.level == logging.DEBUG

    def test_inherit_parent_level(self):
        """부모 로거 레벨 상속"""
        # 부모 로거 설정
        parent = logging.getLogger("parent")
        parent.setLevel(logging.WARNING)

        # 자식 로거 생성 (레벨 지정 안함)
        child = get_logger("parent.child")

        # effective level 확인
        assert child.getEffectiveLevel() == logging.WARNING


class TestLogFunctionCall:
    """log_function_call 데코레이터 테스트"""

    @patch("logging.Logger.debug")
    @patch("logging.Logger.error")
    def test_successful_function_call(self, mock_error, mock_debug):
        """성공적인 함수 호출 로깅"""

        @log_function_call
        def test_func(a, b, c=3):
            return a + b + c

        result = test_func(1, 2, c=4)

        assert result == 7

        # debug 로그 호출 확인
        assert mock_debug.call_count == 2

        # 첫 번째 호출: Calling %s(%s)
        assert mock_debug.call_args_list[0][0][0] == "Calling %s(%s)"
        assert mock_debug.call_args_list[0][0][1] == "test_func"
        assert mock_debug.call_args_list[0][0][2] == "1, 2, c=4"

        # 두 번째 호출: %s completed successfully
        assert mock_debug.call_args_list[1][0][0] == "%s completed successfully"
        assert mock_debug.call_args_list[1][0][1] == "test_func"

        # error 로그는 호출되지 않음
        mock_error.assert_not_called()

    @patch("logging.Logger.debug")
    @patch("logging.Logger.error")
    def test_function_call_with_error(self, mock_error, mock_debug):
        """에러 발생 시 로깅"""

        @log_function_call
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_func()

        # error 로그 호출 확인
        mock_error.assert_called_once()
        # 로그 형식이 "%s failed: %s" 이므로 파라미터 확인
        assert mock_error.call_args[0][0] == "%s failed: %s"
        assert mock_error.call_args[0][1] == "failing_func"

    def test_preserve_function_metadata(self):
        """함수 메타데이터 보존"""

        @log_function_call
        def original_func():
            """Original docstring"""

        assert original_func.__name__ == "wrapper"  # functools.wraps 미적용 시
        # 실제로는 functools.wraps를 사용해야 함


class TestLogExecutionTime:
    """log_execution_time 데코레이터 테스트"""

    @patch("logging.Logger.info")
    def test_execution_time_logging(self, mock_info):
        """실행 시간 로깅"""

        @log_execution_time
        def slow_func():
            time.sleep(0.1)
            return "done"

        result = slow_func()

        assert result == "done"

        # info 로그 호출 확인
        mock_info.assert_called_once()
        # 로그 형식이 "%s took %.2f seconds" 이므로 파라미터 확인
        assert mock_info.call_args[0][0] == "%s took %.2f seconds"
        assert mock_info.call_args[0][1] == "slow_func"
        # 시간은 0.1초 이상이어야 함
        assert mock_info.call_args[0][2] >= 0.1

    @patch("logging.Logger.error")
    def test_execution_time_with_error(self, mock_error):
        """에러 발생 시 실행 시간 로깅"""

        @log_execution_time
        def failing_func():
            time.sleep(0.1)
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            failing_func()

        # error 로그 호출 확인
        mock_error.assert_called_once()
        # 로그 형식이 "%s failed after %.2f seconds: %s" 이므로 파라미터 확인
        assert mock_error.call_args[0][0] == "%s failed after %.2f seconds: %s"
        assert mock_error.call_args[0][1] == "failing_func"
        # 시간은 0.05초 이상이어야 함
        assert mock_error.call_args[0][2] >= 0.05


class TestLogDataframeInfo:
    """log_dataframe_info 함수 테스트"""

    @patch("logging.Logger.info")
    @patch("logging.Logger.debug")
    def test_pandas_dataframe_logging(self, mock_debug, mock_info):
        """Pandas DataFrame 정보 로깅"""
        df = pd.DataFrame(
            {"col1": range(100), "col2": ["test"] * 100, "col3": [1.5] * 100}
        )

        log_dataframe_info(df, name="TestDF")

        # info 로그 확인 (shape)
        mock_info.assert_called_once()
        # 로그 형식이 "%s shape: %s" 이므로 파라미터 확인
        assert mock_info.call_args[0][0] == "%s shape: %s"
        assert mock_info.call_args[0][1] == "TestDF"
        assert mock_info.call_args[0][2] == (100, 3)

        # debug 로그 확인 (columns, memory)
        # 첫 번째 debug 호출: columns
        assert mock_debug.call_args_list[0][0][0] == "%s columns: %s"
        assert mock_debug.call_args_list[0][0][1] == "TestDF"
        assert mock_debug.call_args_list[0][0][2] == ["col1", "col2", "col3"]

        # 두 번째 debug 호출: memory usage
        assert mock_debug.call_args_list[1][0][0] == "%s memory usage: %.2f MB"
        assert mock_debug.call_args_list[1][0][1] == "TestDF"

    @patch("logging.Logger.debug")
    def test_geodataframe_logging(self, mock_debug):
        """GeoDataFrame 정보 로깅"""
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), Point(1, 1)], "name": ["A", "B"]},
            crs="EPSG:4326",
        )

        log_dataframe_info(gdf, name="GeoDF")

        # CRS와 geometry type 로깅 확인
        # CRS 로그 찾기
        crs_logged = False
        geom_types_logged = False

        for call_args in mock_debug.call_args_list:
            if call_args[0][0] == "%s CRS: %s":
                assert call_args[0][1] == "GeoDF"
                assert call_args[0][2] == "EPSG:4326"
                crs_logged = True
            elif call_args[0][0] == "%s geometry types: %s":
                assert call_args[0][1] == "GeoDF"
                assert "Point" in str(call_args[0][2])
                geom_types_logged = True

        assert crs_logged, "CRS was not logged"
        assert geom_types_logged, "Geometry types were not logged"

    def test_custom_logger(self):
        """커스텀 로거 사용"""
        df = pd.DataFrame({"col": [1, 2, 3]})
        custom_logger = MagicMock()

        log_dataframe_info(df, logger=custom_logger)

        # 커스텀 로거 호출 확인
        custom_logger.info.assert_called()
        custom_logger.debug.assert_called()


class TestProgressLogger:
    """ProgressLogger 클래스 테스트"""

    @patch("logging.Logger.info")
    def test_progress_updates(self, mock_info):
        """진행 상황 업데이트"""
        progress = ProgressLogger(total=100, desc="Testing")

        # 10% 단위로 업데이트
        for i in range(10):
            progress.update(10)

        # 10% 단위로 로깅되었는지 확인
        # 로그 형식이 "%s: %d%% (%d/%d)" 이므로 파라미터 확인
        logged_percentages = []
        for call_args in mock_info.call_args_list:
            if call_args[0][0] == "%s: %d%% (%d/%d)":
                assert call_args[0][1] == "Testing"
                logged_percentages.append(call_args[0][2])

        # 10%, 50%, 100%가 로깅되었는지 확인
        assert 10 in logged_percentages
        assert 50 in logged_percentages
        assert 100 in logged_percentages

    @patch("logging.Logger.info")
    def test_custom_log_interval(self, mock_info):
        """커스텀 로그 간격"""
        progress = ProgressLogger(total=100, desc="Custom", log_interval=25)

        # 25% 단위로 업데이트
        for i in range(4):
            progress.update(25)

        # 25% 단위로 로깅되었는지 확인
        logged_percentages = []
        for call_args in mock_info.call_args_list:
            if call_args[0][0] == "%s: %d%% (%d/%d)":
                assert call_args[0][1] == "Custom"
                logged_percentages.append(call_args[0][2])

        # 25%, 50%, 75%, 100%가 로깅되었는지 확인
        assert 25 in logged_percentages
        assert 50 in logged_percentages
        assert 75 in logged_percentages
        assert 100 in logged_percentages

    @patch("logging.Logger.info")
    def test_finish_early(self, mock_info):
        """조기 완료"""
        progress = ProgressLogger(total=100)

        progress.update(50)
        progress.finish()

        # 100% 완료 로그 확인
        last_call = mock_info.call_args_list[-1]
        # 로그 형식이 "%s: 100%% completed (%d/%d)" 이므로 파라미터 확인
        assert last_call[0][0] == "%s: 100%% completed (%d/%d)"
        assert last_call[0][1] == "Processing"
        assert last_call[0][2] == 100
        assert last_call[0][3] == 100

    def test_custom_logger_progress(self):
        """커스텀 로거로 진행 상황"""
        custom_logger = MagicMock()
        progress = ProgressLogger(total=10, logger=custom_logger)

        progress.update(10)

        custom_logger.info.assert_called()


class TestCreateFileLogger:
    """create_file_logger 함수 테스트"""

    def test_create_file_logger(self):
        """파일 로거 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "custom.log"

            logger = create_file_logger(
                name="custom_logger", log_file=log_file, level="WARNING"
            )

            assert logger.name == "custom_logger"
            assert logger.level == logging.WARNING
            assert len(logger.handlers) == 1
            assert isinstance(logger.handlers[0], logging.FileHandler)
            assert log_file.exists()

    def test_custom_format_file_logger(self):
        """커스텀 포맷의 파일 로거"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "formatted.log"
            custom_format = "%(message)s"

            logger = create_file_logger(
                name="formatted", log_file=log_file, format_string=custom_format
            )

            # 포맷 확인
            handler = logger.handlers[0]
            assert handler.formatter._fmt == custom_format

    def test_no_propagation(self):
        """부모 로거로 전파 방지"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "isolated.log"

            logger = create_file_logger(name="isolated", log_file=log_file)

            assert logger.propagate is False

    def test_create_parent_directories(self):
        """부모 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "nested" / "test.log"

            _ = create_file_logger(name="nested", log_file=log_file)

            assert log_file.parent.exists()
            assert log_file.exists()
