"""
프로젝트 설정 관리 테스트
"""

import os
from pathlib import Path
from unittest.mock import mock_open, patch

from src.common.config import (
    DATA_DIR,
    PROJECT_ROOT,
    RAW_DATA_DIR,
    REGION_CODE_PATTERN,
    RESULTS_DIR,
    SRC_DIR,
    ProjectConfig,
    get_config,
)


class TestProjectConfig:
    """ProjectConfig 클래스 테스트"""

    def setup_method(self):
        """각 테스트 전에 싱글톤 리셋"""
        import src.common.config

        src.common.config._config_instance = None

    def test_init_directories(self):
        """디렉토리 초기화"""
        config = ProjectConfig()

        # 프로젝트 명에 의존하지 않고 구조만 확인
        assert config.PROJECT_ROOT.exists()
        assert config.DATA_DIR == config.PROJECT_ROOT / "data"
        assert config.RAW_DATA_DIR == config.DATA_DIR / "raw"
        assert config.RESULTS_DIR == config.PROJECT_ROOT / "results"
        assert config.SRC_DIR == config.PROJECT_ROOT / "src"
        assert config.TESTS_DIR == config.PROJECT_ROOT / "tests"
        assert config.DOCS_DIR == config.PROJECT_ROOT / "docs"

    def test_repair_colors_configuration(self):
        """REPAIR_COLORS 설정 테스트"""
        config = ProjectConfig()

        # REPAIR_COLORS가 정의되어 있는지 확인
        assert hasattr(config, "REPAIR_COLORS")
        assert isinstance(config.REPAIR_COLORS, dict)

        # 4가지 재작업 타입이 모두 정의되어 있는지 확인
        assert "지상누수" in config.REPAIR_COLORS
        assert "지하누수" in config.REPAIR_COLORS
        assert "긴급공사" in config.REPAIR_COLORS
        assert "관리대장" in config.REPAIR_COLORS

        # 각 색상이 올바른 형식인지 확인
        assert config.REPAIR_COLORS["지상누수"] == ("#FF1493", "지상누수")
        assert config.REPAIR_COLORS["지하누수"] == ("#0000FF", "지하누수")
        assert config.REPAIR_COLORS["긴급공사"] == ("#FF8C00", "긴급공사")
        assert config.REPAIR_COLORS["관리대장"] == ("#008000", "관리대장")

        # 각 색상 코드가 유효한 16진수 색상인지 확인
        for repair_type, (color, label) in config.REPAIR_COLORS.items():
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB 형식
            assert label == repair_type  # 라벨과 키가 일치

    @patch("pathlib.Path.exists")
    def test_default_config(self, mock_exists):
        """기본 설정값"""
        # 싱글톤 리셋
        import src.common.config

        src.common.config._config_instance = None

        # 설정 파일이 존재하지 않는 것으로 mock
        mock_exists.return_value = False

        config = ProjectConfig()

        assert config.get("encoding") == "euc-kr"
        assert config.get("crs") == "EPSG:5179"
        assert config.get("figure_size") == [10, 8]
        assert config.get("dpi") == 300
        assert config.get("debug_mode") is False

    def test_load_project_config(self):
        """프로젝트 설정 파일 로드"""
        # _load_config 메서드를 패치하여 특정 설정 반환
        with patch.object(ProjectConfig, "_load_config") as mock_load:
            # 설정 파일이 로드된 것처럼 설정
            test_config = {
                "encoding": "utf-8",
                "crs": "EPSG:5179",
                "figure_size": [10, 8],
                "dpi": 150,
                "font_size": 12,
                "line_width": 1.5,
                "marker_size": 10,
                "color_palette": "viridis",
                "log_level": "INFO",
                "debug_mode": False,
                "new_setting": "value",
            }
            mock_load.return_value = test_config

            config = ProjectConfig()

            assert config.get("encoding") == "utf-8"
            assert config.get("dpi") == 150
            assert config.get("new_setting") == "value"
            assert config.get("debug_mode") is False  # 기본값 유지

    def test_load_user_config(self):
        """사용자 설정 파일 로드"""
        # 싱글톤 리셋
        import src.common.config

        src.common.config._config_instance = None

        # 설정 파일 내용

        # _load_config 메서드를 직접 패치
        with patch.object(ProjectConfig, "_load_config") as mock_load:
            # 두 설정을 합친 결과를 반환
            merged_config = {
                "encoding": "utf-8",  # project_config
                "crs": "EPSG:5179",  # default
                "figure_size": [10, 8],  # default
                "dpi": 200,  # user_config (override)
                "font_size": 12,  # default
                "line_width": 1.5,  # default
                "marker_size": 10,  # default
                "color_palette": "viridis",  # default
                "log_level": "INFO",  # default
                "debug_mode": True,  # user_config
            }
            mock_load.return_value = merged_config

            config = ProjectConfig()

            assert config.get("encoding") == "utf-8"  # 프로젝트 설정
            assert config.get("dpi") == 200  # 사용자 설정으로 오버라이드
            assert config.get("debug_mode") is True  # 사용자 설정

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "DEBUG_MODE": "true"})
    def test_env_overrides(self):
        """환경 변수 오버라이드"""
        config = ProjectConfig()

        assert config.get("log_level") == "DEBUG"
        assert config.get("debug_mode") is True

    @patch.dict(os.environ, {"DEBUG_MODE": "false", "FONT_DEBUG": "1"})
    def test_env_boolean_conversion(self):
        """환경 변수 불리언 변환"""
        config = ProjectConfig()

        assert config.get("debug_mode") is False
        assert config.get("font_debug") is True

    def test_get_set_config(self):
        """설정값 가져오기/설정하기"""
        config = ProjectConfig()

        # 기존 값
        assert config.get("encoding") == "euc-kr"

        # 새 값 설정
        config.set("encoding", "utf-8")
        assert config.get("encoding") == "utf-8"

        # 없는 키에 대한 기본값
        assert config.get("nonexistent", "default") == "default"

    @patch("pathlib.Path.exists")
    @patch("json.dump")
    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_save_user_config(self, mock_path_open, mock_json_dump, mock_exists):
        """사용자 설정 저장"""
        # 싱글톤 리셋
        import src.common.config

        src.common.config._config_instance = None

        # 설정 파일이 존재하지 않는 것으로 mock
        mock_exists.return_value = False

        config = ProjectConfig()

        # 일부 설정 변경
        config.set("dpi", 600)
        config.set("debug_mode", True)

        # 저장
        config.save_user_config()

        # 파일 쓰기 확인
        mock_path_open.assert_called_once_with("w", encoding="utf-8")

        # json.dump 호출 확인
        mock_json_dump.assert_called_once()
        saved_config = mock_json_dump.call_args[0][0]

        assert saved_config["dpi"] == 600
        assert saved_config["debug_mode"] is True
        assert "encoding" not in saved_config  # 기본값과 동일하므로 저장 안함

    @patch("json.dump")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_user_config_custom_dict(self, mock_file, mock_json_dump):
        """커스텀 설정 딕셔너리 저장"""
        config = ProjectConfig()

        custom_config = {"custom_key": "custom_value", "dpi": 400}
        config.save_user_config(custom_config)

        # json.dump 호출 확인
        mock_json_dump.assert_called_once()
        saved_config = mock_json_dump.call_args[0][0]

        assert saved_config == custom_config

    def test_reset_to_defaults(self):
        """기본값으로 리셋"""
        config = ProjectConfig()

        # 설정 변경
        config.set("encoding", "utf-8")
        config.set("dpi", 600)

        # 리셋
        config.reset_to_defaults()

        assert config.get("encoding") == "euc-kr"
        assert config.get("dpi") == 300

    def test_get_all_config(self):
        """전체 설정 가져오기"""
        config = ProjectConfig()
        all_config = config.get_all_config()

        assert isinstance(all_config, dict)
        assert "encoding" in all_config
        assert "crs" in all_config
        assert all_config is not config._config  # 복사본이어야 함

    @patch("builtins.print")
    def test_print_config(self, mock_print):
        """설정 출력"""
        config = ProjectConfig()
        config.print_config()

        # print 호출 확인
        calls = [str(call[0][0]) for call in mock_print.call_args_list]
        assert any("=== 현재 설정 ===" in call for call in calls)
        assert any("encoding:" in call for call in calls)

    @patch("pathlib.Path.exists")
    def test_properties(self, mock_exists):
        """프로퍼티 접근"""
        # 싱글톤 리셋
        import src.common.config

        src.common.config._config_instance = None

        # 설정 파일이 존재하지 않는 것으로 mock
        mock_exists.return_value = False

        config = ProjectConfig()

        assert config.encoding == "euc-kr"
        assert config.crs == "EPSG:5179"
        assert config.figure_size == [10, 8]
        assert config.dpi == 300
        assert config.debug_mode is False
        assert config.log_level == "INFO"

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_config_file_load_error(self, mock_file, mock_exists):
        """설정 파일 로드 실패"""
        mock_exists.return_value = True
        mock_file.side_effect = Exception("File error")

        # 예외가 발생해도 기본 설정으로 초기화되어야 함
        config = ProjectConfig()
        assert config.get("encoding") == "euc-kr"


class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_config_singleton(self):
        """get_config 싱글톤"""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

        # 설정 변경이 공유되는지 확인
        config1.set("test_key", "test_value")
        assert config2.get("test_key") == "test_value"


class TestCompatibilityVariables:
    """호환성 변수 테스트"""

    def test_module_variables(self):
        """모듈 레벨 변수"""
        # PROJECT_ROOT.name은 프로젝트마다 다를 수 있으므로 검사하지 않음
        assert DATA_DIR == PROJECT_ROOT / "data"
        assert RAW_DATA_DIR == DATA_DIR / "raw"
        assert RESULTS_DIR == PROJECT_ROOT / "results"
        assert SRC_DIR == PROJECT_ROOT / "src"
        assert REGION_CODE_PATTERN == r"\((\d{4})\)"

    @patch.dict(os.environ, {"DATA_DIR": "/custom/data"})
    def test_env_override_directories(self):
        """환경 변수로 디렉토리 오버라이드"""
        # 새 config 인스턴스 생성을 위해 기존 싱글톤 제거
        import src.common.config

        src.common.config._config_instance = None

        # 새로 import하면 환경 변수가 적용됨
        from src.common.config import get_config as get_new_config

        new_config = get_new_config()

        assert Path("/custom/data") == new_config.DATA_DIR
