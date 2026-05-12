"""
한글 폰트 유틸리티 테스트
"""

from unittest.mock import Mock, patch

import pytest

from src.common.korean_font_utils import (
    FontConfig,
    FontManager,
    get_available_korean_fonts,
    reset_font_settings,
    set_custom_font,
    setup_korean_font,
)


class TestFontConfig:
    """FontConfig 클래스 테스트"""

    def test_font_candidates(self):
        """OS별 폰트 후보 목록 확인"""
        assert "Apple SD Gothic Neo" in FontConfig.FONT_CANDIDATES["Darwin"]
        assert "Malgun Gothic" in FontConfig.FONT_CANDIDATES["Windows"]
        assert "NanumGothic" in FontConfig.FONT_CANDIDATES["Linux"]

    def test_wsl_font_paths(self):
        """WSL 폰트 경로 확인"""
        assert "/mnt/c/Windows/Fonts/" in FontConfig.WSL_FONT_PATHS

    def test_korean_font_keywords(self):
        """한글 폰트 키워드 확인"""
        assert "Gothic" in FontConfig.KOREAN_FONT_KEYWORDS
        assert "Nanum" in FontConfig.KOREAN_FONT_KEYWORDS


class TestFontManager:
    """FontManager 클래스 테스트"""

    @patch.dict("os.environ", {"FONT_DEBUG": "true"})
    def test_debug_mode(self):
        """디버그 모드 확인"""
        manager = FontManager()
        assert manager.debug_mode is True

    @patch("platform.system")
    def test_system_detection(self, mock_system):
        """시스템 감지"""
        mock_system.return_value = "Darwin"
        manager = FontManager()
        assert manager.system == "Darwin"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open")
    def test_wsl_detection(self, mock_open, mock_exists):
        """WSL 감지"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "microsoft"

        manager = FontManager()
        assert manager.is_wsl is True

    def test_font_name_normalization(self):
        """폰트명 정규화"""
        manager = FontManager()

        assert manager._normalize_font_name("Apple SD Gothic Neo") == "AppleSDGothicNeo"
        assert manager._normalize_font_name("Nanum-Gothic") == "NanumGothic"
        assert manager._normalize_font_name("Malgun_Gothic") == "MalgunGothic"

    @patch("matplotlib.font_manager.fontManager")
    def test_available_fonts_caching(self, mock_fm):
        """사용 가능한 폰트 목록 캐싱"""
        # Mock 폰트 목록
        mock_font1 = Mock()
        mock_font1.name = "Font One"
        mock_font2 = Mock()
        mock_font2.name = "Font Two"
        mock_fm.ttflist = [mock_font1, mock_font2]

        manager = FontManager()

        # 첫 번째 호출
        fonts1 = manager.available_fonts
        # 두 번째 호출 (캐시 사용)
        fonts2 = manager.available_fonts

        assert fonts1 is fonts2  # 같은 객체여야 함
        assert "font one" in fonts1
        assert "font two" in fonts1

    @patch("platform.system")
    def test_get_font_candidates(self, mock_system):
        """시스템별 폰트 후보 목록"""
        mock_system.return_value = "Windows"
        manager = FontManager()

        candidates = manager.get_font_candidates()
        assert "Malgun Gothic" in candidates
        assert "맑은 고딕" in candidates

    @patch("matplotlib.font_manager.fontManager")
    def test_find_matching_font(self, mock_fm):
        """폰트 매칭"""
        # Mock 폰트 목록
        mock_font = Mock()
        mock_font.name = "Apple SD Gothic Neo"
        mock_fm.ttflist = [mock_font]

        manager = FontManager()

        # 정확한 매칭
        assert (
            manager.find_matching_font("Apple SD Gothic Neo") == "Apple SD Gothic Neo"
        )

        # 대소문자 무시
        assert (
            manager.find_matching_font("apple sd gothic neo") == "Apple SD Gothic Neo"
        )

        # 부분 매칭
        assert manager.find_matching_font("AppleSDGothicNeo") == "Apple SD Gothic Neo"

        # 매칭 실패
        assert manager.find_matching_font("NonExistent Font") is None

    @patch("matplotlib.pyplot.rcParams", new_callable=dict)
    @patch("matplotlib.font_manager.FontProperties")
    def test_setup_matplotlib_font_success(self, mock_font_props, mock_rcparams):
        """matplotlib 폰트 설정 성공"""
        # Mock 설정
        mock_font_instance = Mock()
        mock_font_instance.get_name.return_value = "Test Font"
        mock_font_props.return_value = mock_font_instance

        # rcParams에 font.sans-serif 기본값 설정
        mock_rcparams["font.sans-serif"] = []

        manager = FontManager()
        manager.debug_mode = False

        result = manager.setup_matplotlib_font("Test Font")

        assert result is True
        assert mock_rcparams["font.family"] == "Test Font"
        assert mock_rcparams["axes.unicode_minus"] is False

    @patch("matplotlib.pyplot.rcParams", new_callable=dict)
    @patch("matplotlib.font_manager.FontProperties")
    def test_setup_matplotlib_font_failure(self, mock_font_props, mock_rcparams):
        """matplotlib 폰트 설정 실패"""
        # Mock 설정 - 다른 폰트명 반환
        mock_font_instance = Mock()
        mock_font_instance.get_name.return_value = "Different Font"
        mock_font_props.return_value = mock_font_instance

        manager = FontManager()
        manager.debug_mode = False

        result = manager.setup_matplotlib_font("Test Font")

        assert result is False

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("matplotlib.font_manager.fontManager")
    def test_setup_wsl_fonts(self, mock_fm, mock_glob, mock_exists):
        """WSL 폰트 설정"""
        # 첫 번째 경로만 존재 (폰트 디렉토리와 각 폰트 파일의 존재 여부)
        mock_exists.side_effect = [
            True,
            True,
            False,
            False,
        ]  # 디렉토리 존재 + 폰트 파일 존재

        # malgun 폰트 파일 목록
        mock_font_path = Mock()
        mock_font_path.name = "malgun.ttf"
        mock_font_path.as_posix.return_value = "/mnt/c/Windows/Fonts/malgun.ttf"
        mock_glob.return_value = iter([mock_font_path])  # iterator로 반환

        # FontProperties mock
        with patch("matplotlib.font_manager.FontProperties") as mock_font_props:
            mock_font_instance = Mock()
            mock_font_instance.get_name.return_value = "Malgun Gothic"
            mock_font_props.return_value = mock_font_instance

            manager = FontManager()
            manager.debug_mode = False
            manager.setup_matplotlib_font = Mock(return_value=True)

            result = manager.setup_wsl_fonts()

            assert result == "Malgun Gothic"
            mock_fm.addfont.assert_called()

    @patch("matplotlib.pyplot.rcParams", new_callable=dict)
    @patch("matplotlib.rcParams", new_callable=dict)
    def test_setup_default_font(self, mock_mpl_rcparams, mock_rcparams):
        """기본 폰트 설정"""
        manager = FontManager()
        manager.debug_mode = False
        manager.is_wsl = False

        manager.setup_default_font()

        assert mock_rcparams["font.family"] == FontConfig.DEFAULT_FONT
        assert mock_rcparams["font.sans-serif"] == FontConfig.FALLBACK_FONTS
        assert mock_rcparams["axes.unicode_minus"] is False
        assert mock_mpl_rcparams["text.usetex"] is False


class TestModuleFunctions:
    """모듈 레벨 함수 테스트"""

    @patch("src.common.korean_font_utils.FontManager")
    def test_setup_korean_font_success(self, mock_font_manager_class):
        """한글 폰트 설정 성공"""
        # Mock FontManager 인스턴스
        mock_manager = Mock()
        mock_manager.get_font_candidates.return_value = ["Test Font"]
        mock_manager.find_matching_font.return_value = "Test Font"
        mock_manager.setup_matplotlib_font.return_value = True
        mock_manager.is_wsl = False
        mock_font_manager_class.return_value = mock_manager

        result = setup_korean_font()

        assert result == "Test Font"

    @patch("src.common.korean_font_utils.FontManager")
    def test_setup_korean_font_wsl_fallback(self, mock_font_manager_class):
        """WSL 환경에서 Windows 폰트 사용"""
        # Mock FontManager 인스턴스
        mock_manager = Mock()
        mock_manager.get_font_candidates.return_value = ["Test Font"]
        mock_manager.find_matching_font.return_value = None
        mock_manager.setup_matplotlib_font.return_value = False
        mock_manager.is_wsl = True
        mock_manager.setup_wsl_fonts.return_value = "WSL Font"
        mock_font_manager_class.return_value = mock_manager

        result = setup_korean_font()

        assert result == "WSL Font"

    @patch("src.common.korean_font_utils.FontManager")
    def test_setup_korean_font_default_fallback(self, mock_font_manager_class):
        """기본 폰트로 폴백"""
        # Mock FontManager 인스턴스
        mock_manager = Mock()
        mock_manager.get_font_candidates.return_value = []
        mock_manager.is_wsl = False
        mock_manager.setup_default_font.return_value = None
        mock_font_manager_class.return_value = mock_manager

        result = setup_korean_font()

        assert result is None
        mock_manager.setup_default_font.assert_called_once()

    @patch("matplotlib.font_manager.fontManager")
    def test_get_available_korean_fonts(self, mock_fm):
        """사용 가능한 한글 폰트 목록"""
        # Mock 폰트 목록
        fonts = []
        for name in ["Apple SD Gothic Neo", "Arial", "Malgun Gothic", "Times"]:
            font = Mock()
            font.name = name
            fonts.append(font)
        mock_fm.ttflist = fonts

        korean_fonts = get_available_korean_fonts()

        assert "Apple SD Gothic Neo" in korean_fonts
        assert "Malgun Gothic" in korean_fonts
        assert "Arial" not in korean_fonts
        assert "Times" not in korean_fonts

    def test_set_custom_font_invalid_type(self):
        """잘못된 타입의 폰트명"""
        with pytest.raises(TypeError) as excinfo:
            set_custom_font(123)

        assert "폰트명은 문자열이어야 합니다" in str(excinfo.value)

    @patch("matplotlib.font_manager.fontManager")
    @patch("src.common.korean_font_utils.FontManager")
    def test_set_custom_font_not_found(self, mock_font_manager_class, mock_fm):
        """존재하지 않는 폰트"""
        # Mock 폰트 목록
        font = Mock()
        font.name = "Existing Font"
        mock_fm.ttflist = [font]

        # Mock FontManager
        mock_manager = Mock()
        mock_font_manager_class.return_value = mock_manager

        result = set_custom_font("NonExistent Font")

        assert result is False

    @patch("matplotlib.font_manager.fontManager")
    @patch("src.common.korean_font_utils.FontManager")
    def test_set_custom_font_success(self, mock_font_manager_class, mock_fm):
        """폰트 설정 성공"""
        # Mock 폰트 목록
        font = Mock()
        font.name = "Test Font"
        mock_fm.ttflist = [font]

        # Mock FontManager
        mock_manager = Mock()
        mock_manager.setup_matplotlib_font.return_value = True
        mock_font_manager_class.return_value = mock_manager

        result = set_custom_font("Test Font")

        assert result is True
        mock_manager.setup_matplotlib_font.assert_called_with("Test Font")

    @patch("matplotlib.pyplot.rcParams")
    @patch("matplotlib.rcParamsDefault", {"test": "default"})
    def test_reset_font_settings(self, mock_rcparams):
        """폰트 설정 리셋"""
        reset_font_settings()

        mock_rcparams.update.assert_called_with({"test": "default"})
