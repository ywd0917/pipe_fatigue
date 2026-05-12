"""
한글 폰트 설정 유틸리티
matplotlib에서 한글을 제대로 표시하기 위한 폰트 설정 함수들
"""

import os
import platform
from pathlib import Path
from typing import ClassVar

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt


class FontConfig:
    """폰트 설정 관련 상수 및 설정값"""

    # OS별 폰트 후보 목록
    FONT_CANDIDATES: ClassVar[dict[str, list[str]]] = {
        "Darwin": [  # macOS
            "Apple SD Gothic Neo",
            "AppleGothic",
            "Nanum Gothic",
            "Malgun Gothic",
            "Arial Unicode MS",
        ],
        "Windows": [
            "Malgun Gothic",
            "맑은 고딕",
            "NanumGothic",
            "Nanum Gothic",
            "Gulim",
            "굴림",
            "Dotum",
            "돋움",
            "Batang",
            "바탕",
            "Arial Unicode MS",
        ],
        "Linux": [  # WSL 포함
            "NanumGothic",
            "Nanum Gothic",
            "NanumBarunGothic",
            "NanumMyeongjo",
            "NanumSquare",
            "UnDotum",
            "DejaVu Sans",
            "Liberation Sans",
            "FreeSans",
            "Arial",
            "sans-serif",
        ],
    }

    # WSL Windows 폰트 경로
    WSL_FONT_PATHS: ClassVar[list[str]] = [
        "/mnt/c/Windows/Fonts/",
        "C:/Windows/Fonts/",
        "C:\\Windows\\Fonts\\",
    ]

    # 한글 폰트 키워드
    KOREAN_FONT_KEYWORDS: ClassVar[list[str]] = [
        "Gothic",
        "Nanum",
        "Malgun",
        "Apple",
        "굴림",
        "돋움",
        "바탕",
    ]

    # 기본 영문 폰트
    DEFAULT_FONT = "DejaVu Sans"
    FALLBACK_FONTS: ClassVar[list[str]] = ["DejaVu Sans", "sans-serif"]


class FontManager:
    """폰트 관리 클래스"""

    def __init__(self) -> None:
        self.debug_mode = os.environ.get("FONT_DEBUG", "").lower() == "true"
        self.system = platform.system()
        self.is_wsl = self._check_wsl()
        self._available_fonts_cache: dict[str, str] | None = None

    def _check_wsl(self) -> bool:
        """WSL 환경인지 확인"""
        proc_version = Path("/proc/version")
        if proc_version.exists():
            try:
                with proc_version.open() as f:
                    return "microsoft" in f.read().lower()
            except Exception:
                return False
        return False

    @property
    def available_fonts(self) -> dict[str, str]:
        """사용 가능한 폰트 목록 (캐싱)"""
        if self._available_fonts_cache is None:
            self._available_fonts_cache = {
                f.name.lower(): f.name for f in fm.fontManager.ttflist
            }
        return self._available_fonts_cache

    def get_font_candidates(self) -> list[str]:
        """현재 시스템에 맞는 폰트 후보 목록 반환"""
        return FontConfig.FONT_CANDIDATES.get(
            self.system, FontConfig.FONT_CANDIDATES["Linux"]
        )

    def find_matching_font(self, font_name: str) -> str | None:
        """폰트명 매칭 (대소문자, 공백 무시)"""
        font_lower = font_name.lower()

        # 정확한 매칭
        if font_lower in self.available_fonts:
            return self.available_fonts[font_lower]

        # 부분 매칭
        font_normalized = self._normalize_font_name(font_lower)
        for avail_font_lower, avail_font in self.available_fonts.items():
            avail_normalized = self._normalize_font_name(avail_font_lower)

            if (
                font_normalized in avail_normalized
                or avail_normalized in font_normalized
            ):
                return avail_font

        return None

    def _normalize_font_name(self, font_name: str) -> str:
        """폰트명 정규화 (공백, 하이픈, 언더스코어 제거)"""
        return font_name.replace(" ", "").replace("-", "").replace("_", "")

    def setup_matplotlib_font(self, font_name: str) -> bool:
        """matplotlib 폰트 설정"""
        try:
            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            font_sans_serif = plt.rcParams["font.sans-serif"]
            plt.rcParams["font.sans-serif"] = [font_name, *font_sans_serif]

            # 실제로 폰트가 설정되었는지 확인
            test_font = fm.FontProperties(family=font_name)
            if test_font.get_name() == font_name:
                if self.debug_mode:
                    print(f"한글 폰트 설정 성공: {font_name}")
                return True
        except Exception as e:
            if self.debug_mode:
                print(f"폰트 설정 실패 ({font_name}): {e}")
        return False

    def setup_wsl_fonts(self) -> str | None:
        """WSL 환경에서 Windows 폰트 설정"""
        for font_path_str in FontConfig.WSL_FONT_PATHS:
            font_path = Path(font_path_str)
            if not font_path.exists():
                continue

            try:
                malgun_fonts = list(font_path.glob("malgun*.ttf"))
                for font_file in malgun_fonts:
                    try:
                        fm.fontManager.addfont(str(font_file))
                        font_prop = fm.FontProperties(fname=str(font_file))
                        font_name = font_prop.get_name()

                        if self.setup_matplotlib_font(font_name):
                            if self.debug_mode:
                                print(f"WSL에서 Windows 한글 폰트 설정: {font_name}")
                            return font_name
                    except Exception:
                        continue
            except Exception as e:
                if self.debug_mode:
                    print(f"Windows 폰트 로드 실패: {e}")

        return None

    def setup_default_font(self) -> None:
        """기본 폰트 설정"""
        plt.rcParams["font.family"] = FontConfig.DEFAULT_FONT
        plt.rcParams["font.sans-serif"] = FontConfig.FALLBACK_FONTS
        plt.rcParams["axes.unicode_minus"] = False

        # matplotlib 경고 억제
        import matplotlib

        matplotlib.rcParams["text.usetex"] = False

        if self.debug_mode:
            if self.is_wsl:
                print("WSL 환경에서 한글 폰트를 찾지 못했습니다.")
                print("그래프 레이블을 영문으로 사용하는 것을 권장합니다.")
            else:
                print("한글 폰트를 찾지 못했습니다. 기본 폰트를 사용합니다.")
            print(
                f"사용 가능한 폰트 목록 (일부): {list(self.available_fonts.values())[:10]}"
            )


def setup_korean_font() -> str | None:
    """
    시스템에 맞는 한글 폰트를 자동으로 설정

    Returns:
        str: 설정된 폰트명 또는 None
    """
    manager = FontManager()

    # OS별 폰트 후보 시도
    for font in manager.get_font_candidates():
        matched_font = manager.find_matching_font(font)
        if matched_font and manager.setup_matplotlib_font(matched_font):
            return matched_font

    # WSL 환경에서 Windows 폰트 시도
    if manager.is_wsl:
        wsl_font = manager.setup_wsl_fonts()
        if wsl_font:
            return wsl_font

    # 기본 폰트 설정
    manager.setup_default_font()
    return None


def get_available_korean_fonts() -> list[str]:
    """
    시스템에서 사용 가능한 한글 폰트 목록 반환

    Returns:
        list: 사용 가능한 한글 폰트 목록
    """
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    korean_fonts = []
    for font in available_fonts:
        for keyword in FontConfig.KOREAN_FONT_KEYWORDS:
            if keyword in font:
                korean_fonts.append(font)
                break

    return list(set(korean_fonts))  # 중복 제거


def set_custom_font(font_name: str) -> bool:
    """
    사용자 지정 폰트 설정

    Args:
        font_name (str): 설정할 폰트명

    Returns:
        bool: 설정 성공 여부

    Raises:
        TypeError: font_name이 문자열이 아닌 경우
    """
    # 타입 검증
    if not isinstance(font_name, str):
        raise TypeError(f"폰트명은 문자열이어야 합니다. 입력된 타입: {type(font_name)}")

    manager = FontManager()

    # 폰트 존재 여부 확인
    if font_name not in [f.name for f in fm.fontManager.ttflist]:
        print(f"폰트를 찾을 수 없습니다: {font_name}")
        print(f"사용 가능한 한글 폰트: {get_available_korean_fonts()}")
        return False

    # 폰트 설정
    if manager.setup_matplotlib_font(font_name):
        print(f"폰트 설정 완료: {font_name}")
        return True

    return False


def reset_font_settings() -> None:
    """
    matplotlib 폰트 설정을 기본값으로 리셋
    """
    import matplotlib

    plt.rcParams.update(matplotlib.rcParamsDefault)
    print("폰트 설정이 기본값으로 리셋되었습니다.")


# 모듈 import 시 자동으로 한글 폰트 설정은 하지 않음
# 명시적으로 setup_korean_font()를 호출하도록 변경
