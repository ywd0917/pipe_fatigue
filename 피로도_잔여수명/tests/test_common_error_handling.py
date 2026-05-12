"""
에러 처리 유틸리티 테스트
"""

from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.common.error_handling import (
    ConfigurationError,
    DataProcessingError,
    ErrorContext,
    ValidationError,
    create_error_report,
    format_error_message,
    handle_errors,
    retry_on_error,
    safe_execute,
    validate_input,
)

# FileNotFoundError를 별도로 import (Python 내장 예외와 충돌 방지)
from src.common.error_handling import FileNotFoundError as CustomFileNotFoundError


class TestCustomExceptions:
    """커스텀 예외 클래스 테스트"""

    def test_data_processing_error(self):
        """DataProcessingError 예외"""
        with pytest.raises(DataProcessingError) as excinfo:
            raise DataProcessingError("Test error")

        assert str(excinfo.value) == "Test error"
        assert isinstance(excinfo.value, Exception)

    def test_file_not_found_error(self):
        """FileNotFoundError 예외"""
        with pytest.raises(CustomFileNotFoundError) as excinfo:
            raise CustomFileNotFoundError("File missing")

        assert str(excinfo.value) == "File missing"
        assert isinstance(excinfo.value, DataProcessingError)

    def test_validation_error(self):
        """ValidationError 예외"""
        with pytest.raises(ValidationError) as excinfo:
            raise ValidationError("Invalid data")

        assert str(excinfo.value) == "Invalid data"
        assert isinstance(excinfo.value, DataProcessingError)

    def test_configuration_error(self):
        """ConfigurationError 예외"""
        with pytest.raises(ConfigurationError) as excinfo:
            raise ConfigurationError("Bad config")

        assert str(excinfo.value) == "Bad config"
        assert isinstance(excinfo.value, DataProcessingError)


class TestHandleErrors:
    """handle_errors 데코레이터 테스트"""

    @patch("src.common.error_handling.logger")
    def test_default_error_handling(self, mock_logger):
        """기본 에러 처리"""

        @handle_errors(default_return=None)
        def failing_func():
            raise ValueError("Test error")

        result = failing_func()

        assert result is None
        mock_logger.error.assert_called_once()
        log_msg = mock_logger.error.call_args[0][0]
        assert "Error in failing_func" in log_msg
        assert "Test error" in log_msg

    def test_custom_default_return(self):
        """커스텀 기본 반환값"""

        @handle_errors(default_return="default_value")
        def failing_func():
            raise RuntimeError("Error")

        result = failing_func()

        assert result == "default_value"

    @patch("src.common.error_handling.logger")
    def test_custom_log_level(self, mock_logger):
        """커스텀 로그 레벨"""

        @handle_errors(log_level="WARNING")
        def failing_func():
            raise Exception("Warning level error")

        failing_func()

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    def test_reraise_errors(self):
        """에러 재발생"""

        @handle_errors(reraise=True)
        def failing_func():
            raise ValueError("Should reraise")

        with pytest.raises(ValueError) as excinfo:
            failing_func()

        assert str(excinfo.value) == "Should reraise"

    def test_specific_error_types(self):
        """특정 에러 타입만 처리"""

        @handle_errors(default_return="handled", error_types=(ValueError, TypeError))
        def multi_error_func(error_type):
            if error_type == "value":
                raise ValueError("Value error")
            if error_type == "runtime":
                raise RuntimeError("Runtime error")
            return "success"

        # ValueError는 처리됨
        assert multi_error_func("value") == "handled"

        # RuntimeError는 처리 안됨
        with pytest.raises(RuntimeError):
            multi_error_func("runtime")

        # 정상 실행
        assert multi_error_func("none") == "success"

    def test_successful_execution(self):
        """정상 실행"""

        @handle_errors(default_return="error")
        def success_func(x, y):
            return x + y

        result = success_func(2, 3)

        assert result == 5


class TestRetryOnError:
    """retry_on_error 데코레이터 테스트"""

    @patch("time.sleep")
    def test_retry_success_after_failures(self, mock_sleep):
        """실패 후 성공"""
        call_count = 0

        @retry_on_error(max_attempts=3, delay=1.0)
        def unstable_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary error")
            return "success"

        result = unstable_func()

        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # 2번 재시도

    @patch("time.sleep")
    @patch("src.common.error_handling.logger")
    def test_max_attempts_exceeded(self, mock_logger, mock_sleep):
        """최대 시도 횟수 초과"""

        @retry_on_error(max_attempts=2, delay=0.1)
        def always_failing():
            raise ValueError("Persistent error")

        with pytest.raises(ValueError):
            always_failing()

        # 에러 로그 확인
        error_calls = list(mock_logger.error.call_args_list)
        assert len(error_calls) == 1
        # 로그 형식이 "%s failed after %d attempts: %s" 이므로 파라미터 확인
        assert error_calls[0][0][0] == "%s failed after %d attempts: %s"
        assert error_calls[0][0][1] == "always_failing"  # 함수명
        assert error_calls[0][0][2] == 2  # 시도 횟수

    @patch("time.sleep")
    def test_backoff_delay(self, mock_sleep):
        """백오프 지연"""

        @retry_on_error(max_attempts=4, delay=1.0, backoff=2.0)
        def failing_func():
            raise Exception("Error")

        with pytest.raises(Exception, match="Error"):
            failing_func()

        # 지연 시간 확인: 1, 2, 4
        sleep_calls = mock_sleep.call_args_list
        assert sleep_calls[0][0][0] == 1.0
        assert sleep_calls[1][0][0] == 2.0
        assert sleep_calls[2][0][0] == 4.0

    def test_specific_exceptions_only(self):
        """특정 예외만 재시도"""

        @retry_on_error(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
        def selective_retry(error_type):
            if error_type == "connection":
                raise ConnectionError("Retry this")
            raise ValueError("Don't retry this")

        # ValueError는 재시도 없이 즉시 발생
        with pytest.raises(ValueError):
            selective_retry("value")

        # ConnectionError는 재시도됨
        with pytest.raises(ConnectionError):
            selective_retry("connection")

    def test_immediate_success(self):
        """첫 시도에서 성공"""

        @retry_on_error(max_attempts=3)
        def success_func():
            return "immediate success"

        result = success_func()

        assert result == "immediate success"


class TestSafeExecute:
    """safe_execute 함수 테스트"""

    def test_successful_execution(self):
        """성공적인 실행"""
        result = safe_execute(int, "123")
        assert result == 123

    def test_error_with_default(self):
        """에러 시 기본값 반환"""
        result = safe_execute(int, "not_a_number", default=0)
        assert result == 0

    @patch("src.common.error_handling.logger")
    def test_custom_error_message(self, mock_logger):
        """커스텀 에러 메시지"""
        safe_execute(int, "abc", default=None, error_msg="Failed to parse integer")

        mock_logger.error.assert_called_once()
        # 로그 형식이 "%s: %s" 이므로 파라미터 확인
        assert mock_logger.error.call_args[0][0] == "%s: %s"
        assert mock_logger.error.call_args[0][1] == "Failed to parse integer"

    @patch("src.common.error_handling.logger")
    def test_default_error_message(self, mock_logger):
        """기본 에러 메시지"""
        safe_execute(len, None, default=0)

        mock_logger.error.assert_called_once()
        # 로그 형식이 "Error executing %s: %s" 이므로 파라미터 확인
        assert mock_logger.error.call_args[0][0] == "Error executing %s: %s"
        assert mock_logger.error.call_args[0][1] == "len"

    def test_with_args_and_kwargs(self):
        """인자와 키워드 인자 사용"""

        def custom_func(a, b, c=3):
            return a + b + c

        result = safe_execute(custom_func, 1, 2, c=4, default=0)
        assert result == 7

        # 에러 케이스
        result = safe_execute(custom_func, "a", "b", default=-1)
        assert result == -1


class TestValidateInput:
    """validate_input 데코레이터 테스트"""

    def test_valid_input(self):
        """유효한 입력"""

        @validate_input(lambda x: x > 0, "Value must be positive")
        def sqrt(x):
            return x**0.5

        result = sqrt(4)
        assert result == 2.0

    def test_invalid_input(self):
        """유효하지 않은 입력"""

        @validate_input(lambda x: x > 0, "Value must be positive")
        def sqrt(x):
            return x**0.5

        with pytest.raises(ValidationError) as excinfo:
            sqrt(-1)

        assert "Value must be positive: -1" in str(excinfo.value)

    def test_with_self_parameter(self):
        """self 파라미터가 있는 메서드"""

        class Calculator:
            @validate_input(lambda x: isinstance(x, int | float), "Must be number")
            def double(self, x):
                return x * 2

        calc = Calculator()
        assert calc.double(5) == 10

        with pytest.raises(ValidationError):
            calc.double("string")

    def test_multiple_arguments(self):
        """여러 인자 - 첫 번째만 검증"""

        @validate_input(lambda x: x != 0, "Cannot divide by zero")
        def divide(x, y):
            return y / x

        result = divide(2, 10)
        assert result == 5.0

        # 첫 번째 인자만 검증됨
        with pytest.raises(ValidationError):
            divide(0, 10)


class TestErrorContext:
    """ErrorContext 컨텍스트 매니저 테스트"""

    @patch("logging.getLogger")
    def test_successful_context(self, mock_get_logger):
        """성공적인 컨텍스트 실행"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with ErrorContext("Test operation"):
            result = 1 + 1

        assert result == 2
        mock_logger.error.assert_not_called()

    @patch("logging.getLogger")
    def test_error_handling_default(self, mock_get_logger):
        """에러 처리 - 기본 동작"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with ErrorContext("Failed operation"):
            raise ValueError("Test error")

        # 에러가 억제됨
        mock_logger.error.assert_called_once()
        log_msg = mock_logger.error.call_args[0][0]
        assert "Error during Failed operation" in log_msg
        assert "ValueError" in log_msg

    @patch("logging.getLogger")
    def test_error_with_reraise(self, mock_get_logger):
        """에러 재발생"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with pytest.raises(RuntimeError), ErrorContext("Operation", reraise=True):
            raise RuntimeError("Should reraise")

        # 로그는 기록되지만 예외는 전파됨
        mock_logger.error.assert_called_once()

    @patch("logging.getLogger")
    def test_custom_log_level(self, mock_get_logger):
        """커스텀 로그 레벨"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with ErrorContext("Warning operation", log_level="WARNING"):
            raise Exception("Warning level")

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    def test_context_with_default(self):
        """기본값과 함께 사용"""
        result = None

        with ErrorContext("Get value", default="default"):
            result = int("not_a_number")  # 에러 발생

        # 에러가 억제되므로 result는 None 유지
        assert result is None


class TestFormatErrorMessage:
    """format_error_message 함수 테스트"""

    def test_basic_formatting(self):
        """기본 에러 메시지 포맷팅"""
        error = ValueError("Test error message")

        message = format_error_message(error)

        assert "Error Type: ValueError" in message
        assert "Message: Test error message" in message

    def test_with_context(self):
        """컨텍스트 정보 포함"""
        error = RuntimeError("Operation failed")
        context = {"operation": "data_processing", "file": "input.csv", "line": 42}

        message = format_error_message(error, context=context)

        assert "Context:" in message
        assert "operation: data_processing" in message
        assert "file: input.csv" in message
        assert "line: 42" in message

    @patch("traceback.format_exc")
    def test_with_traceback(self, mock_traceback):
        """트레이스백 포함"""
        mock_traceback.return_value = "Traceback details..."
        error = Exception("Error with traceback")

        message = format_error_message(error, include_traceback=True)

        assert "Traceback:" in message
        assert "Traceback details..." in message

    def test_multiline_output(self):
        """여러 줄 출력"""
        error = KeyError("missing_key")
        context = {"action": "lookup"}

        message = format_error_message(error, context=context)

        lines = message.split("\n")
        assert len(lines) >= 4  # Type, Message, Context header, context item


class TestCreateErrorReport:
    """create_error_report 함수 테스트"""

    @patch("src.common.error_handling.sys")
    def test_basic_report_generation(self, mock_sys):
        """기본 에러 리포트 생성"""
        mock_sys.version = "3.9.0"
        mock_sys.platform = "linux"

        error = ValueError("Test error")

        report = create_error_report(
            error=error, operation="test_operation", input_data={"param": "value"}
        )

        assert "timestamp" in report
        assert report["operation"] == "test_operation"
        assert report["error"]["type"] == "ValueError"
        assert report["error"]["message"] == "Test error"
        assert "traceback" in report["error"]
        assert report["input_data"] == {"param": "value"}
        assert report["environment"]["python_version"] == "3.9.0"
        assert report["environment"]["platform"] == "linux"

    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch("src.common.error_handling.logger")
    def test_save_report_to_file(self, mock_logger, mock_path_open):
        """파일로 리포트 저장"""
        error = RuntimeError("Save test")

        _ = create_error_report(
            error=error, operation="save_test", output_file="error_report.json"
        )

        # 파일 쓰기 확인
        mock_path_open.assert_called_once_with("w", encoding="utf-8")

        # 로그 확인
        mock_logger.info.assert_called_once()
        # 로그 형식이 "Error report saved to %s" 이므로 파라미터 확인
        assert mock_logger.info.call_args[0][0] == "Error report saved to %s"
        assert mock_logger.info.call_args[0][1] == "error_report.json"

    def test_timestamp_format(self):
        """타임스탬프 형식"""
        error = Exception("Time test")

        report = create_error_report(error, "time_op")

        # ISO 형식 타임스탬프 확인
        timestamp = report["timestamp"]
        parsed_time = datetime.fromisoformat(timestamp)
        assert isinstance(parsed_time, datetime)

    def test_empty_input_data(self):
        """빈 입력 데이터"""
        error = Exception("Empty test")

        report = create_error_report(error, "empty_op")

        assert report["input_data"] == {}
