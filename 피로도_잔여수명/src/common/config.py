"""
프로젝트 전체 설정 관리 모듈
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ProjectConfig:
    """프로젝트 설정 관리 클래스"""

    def __init__(self) -> None:
        # 프로젝트 루트 디렉토리
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent

        # 주요 디렉토리 경로
        self.DATA_DIR = self.PROJECT_ROOT / "data"
        self.RAW_DATA_DIR = self.DATA_DIR / "raw"
        self.RESULTS_DIR = self.PROJECT_ROOT / "results"
        self.SRC_DIR = self.PROJECT_ROOT / "src"
        self.TESTS_DIR = self.PROJECT_ROOT / "tests"
        self.DOCS_DIR = self.PROJECT_ROOT / "docs"

        # 피로도 데이터 파일 경로
        # self.PIPE_FATIGUE_DIR = self.DATA_DIR / "pipe_fatigue"
        # self.FATIGUE_PIPE_LM_CSV = self.PIPE_FATIGUE_DIR / "fatigue_pipe_lm_by_age.csv"
        # self.FATIGUE_SPLY_LS_CSV = self.PIPE_FATIGUE_DIR / "fatigue_sply_ls_by_age.csv"
        self.PIPE_FATIGUE_DIR = self.RESULTS_DIR / "main56_calc_fatigure"
        self.FATIGUE_PIPE_LM_CSV = self.PIPE_FATIGUE_DIR / "fatigue_pipe_lm.csv"
        self.FATIGUE_SPLY_LS_CSV = self.PIPE_FATIGUE_DIR / "fatigue_sply_ls.csv"

        # 재작업 데이터 파일 경로 (0520 지역)
        # 통합 CSV 파일 경로 (main13_crop_520 결과)
        self.UNIFIED_REPAIR_CSV = (
            self.RESULTS_DIR / "main13_crop_520" / "누수공사_통합_520_위치추가.csv"
        )

        # 재작업 유형별 색상 정의 (중앙 관리)
        self.REPAIR_COLORS = {
            "지상누수": ("#FF1493", "지상누수"),  # 진한 핑크
            "지하누수": ("#0000FF", "지하누수"),  # 파란색
            "긴급공사": ("#FF8C00", "긴급공사"),  # 다크 오렌지
            "관리대장": ("#008000", "관리대장"),  # 녹색
        }

        # 결과 디렉토리가 없으면 생성
        self.RESULTS_DIR.mkdir(exist_ok=True)

        # Export 디렉토리 지역 코드 패턴
        # 예: export_shp_20250704(0520) → 0520
        self.REGION_CODE_PATTERN = r"\((\d{4})\)"

        # 설정 파일 경로
        self.CONFIG_FILE = self.PROJECT_ROOT / "config.json"
        self.USER_CONFIG_FILE = self.PROJECT_ROOT / "config.user.json"

        # 기본 설정값
        self._default_config = {
            "encoding": "euc-kr",
            "crs": "EPSG:5179",
            "figure_size": [10, 8],
            "dpi": 300,
            "font_size": 12,
            "line_width": 1.5,
            "marker_size": 10,
            "color_palette": "viridis",
            "log_level": "INFO",
            "debug_mode": False,
        }

        # 환경 변수 설정 오버라이드
        self._env_overrides = {
            "LOG_LEVEL": "log_level",
            "DEBUG_MODE": "debug_mode",
            "FONT_DEBUG": "font_debug",
            "DATA_DIR": "data_dir",
            "RESULTS_DIR": "results_dir",
        }

        # 압력 데이터 파일 경로 (main51-57 포팅)
        self.SMALL_AREA_0243_PRESSURE_DATA_PATH = (
            self.RAW_DATA_DIR / "0243 소구역 압력 데이터.csv"
        )
        self.SMALL_AREA_0461_PRESSURE_DATA_PATH = (
            self.RAW_DATA_DIR / "0461 소구역 압력 데이터.csv"
        )
        self.SMALL_AREA_0470_PRESSURE_DATA_PATH = (
            self.RAW_DATA_DIR / "0470 소구역 압력 데이터.csv"
        )
        self.SMALL_AREA_0480_PRESSURE_DATA_PATH = (
            self.RAW_DATA_DIR / "0480 소구역 압력 데이터.csv"
        )
        self.SMALL_AREA_0490_PRESSURE_DATA_PATH = (
            self.RAW_DATA_DIR / "0490 소구역 압력 데이터.csv"
        )
        self.MIDDLE_AREA_PRESSURE_DATA_PATH = (
            self.RAW_DATA_DIR / "0520 중구역 압력 데이터.csv"
        )

        # 압력 데이터 파일 리스트 (순서 중요: 0470 → 0480 → 0490 → 0520)
        self.PRESSURE_DATA_FILES = [
            self.SMALL_AREA_0243_PRESSURE_DATA_PATH,
            self.SMALL_AREA_0461_PRESSURE_DATA_PATH,
            self.SMALL_AREA_0470_PRESSURE_DATA_PATH,  # 0470 소구역
            self.SMALL_AREA_0480_PRESSURE_DATA_PATH,  # 0480 소구역
            self.SMALL_AREA_0490_PRESSURE_DATA_PATH,  # 0490 소구역
            self.MIDDLE_AREA_PRESSURE_DATA_PATH,  # 0520 중구역
        ]

        # 주파수 분석 관련 상수
        self.V_SHAPED_MIN_FREQ = 553.5  # V자 최저점 주파수 (분)

        # 파이프 데이터 파일 경로 (main54 포팅)
        self.PIPE_LM_CSV = self.RAW_DATA_DIR / "PIPE_LM.csv"
        self.SPLY_LS_CSV = self.RAW_DATA_DIR / "SPLY_LS.csv"

        # 파이프 데이터 파일 리스트
        self.PIPE_DATA_FILES = [
            (self.PIPE_LM_CSV, "PIPE_LM"),
            (self.SPLY_LS_CSV, "SPLY_LS"),
        ]

        # main56 피로도 계산 관련 상수
        self.PIPE_PROP_PATH = self.RAW_DATA_DIR / "PIPE_PROP.csv"  # 파이프 속성 파일
        self.HIGH_FREQ_FATIGUE_MULTIPLIER = 10  # 고주파 피로 계수
        self.DEFAULT_FATIGUE_LIMIT = 1000000  # 기본 피로 한계 (10^6)
        self.DEFAULT_PIPE_TYPE = "GP"  # 기본 파이프 타입 (아연도강관)
        self.C_REPAIR = 10.0  # 수리 계수 가중치 상수

        # 설정 로드
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """설정 파일 로드 (우선순위: 환경변수 > 사용자 설정 > 기본 설정)"""
        config = self._default_config.copy()

        # 프로젝트 설정 파일 로드
        if self.CONFIG_FILE.exists():
            try:
                with self.CONFIG_FILE.open(encoding="utf-8") as f:
                    project_config = json.load(f)
                    config.update(project_config)
                    logger.debug("프로젝트 설정 로드: %s", self.CONFIG_FILE)
            except Exception as e:
                logger.warning("프로젝트 설정 파일 로드 실패: %s", e)

        # 사용자 설정 파일 로드 (git ignore 대상)
        if self.USER_CONFIG_FILE.exists():
            try:
                with self.USER_CONFIG_FILE.open(encoding="utf-8") as f:
                    user_config = json.load(f)
                    config.update(user_config)
                    logger.debug("사용자 설정 로드: %s", self.USER_CONFIG_FILE)
            except Exception as e:
                logger.warning("사용자 설정 파일 로드 실패: %s", e)

        # 환경 변수 오버라이드
        for env_key, config_key in self._env_overrides.items():
            env_value = os.environ.get(env_key)
            if env_value is not None:
                # 타입 변환
                if config_key in ["debug_mode", "font_debug"]:
                    config[config_key] = env_value.lower() in ["true", "1", "yes"]
                elif config_key in ["data_dir", "results_dir"]:
                    # 디렉토리 경로는 Path 객체로 변환
                    setattr(self, config_key.upper(), Path(env_value))
                else:
                    config[config_key] = env_value
                logger.debug("환경 변수 오버라이드: %s → %s", env_key, config_key)

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """설정값 가져오기"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """설정값 설정 (런타임에만 유효)"""
        self._config[key] = value

    def save_user_config(self, config_dict: dict[str, Any] | None = None) -> None:
        """사용자 설정 파일 저장"""
        if config_dict is None:
            # 현재 설정에서 기본값과 다른 것만 저장
            config_dict = {
                k: v
                for k, v in self._config.items()
                if k in self._default_config and v != self._default_config[k]
            }

        try:
            with self.USER_CONFIG_FILE.open("w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            logger.info("사용자 설정 저장: %s", self.USER_CONFIG_FILE)
        except Exception as e:
            logger.error("사용자 설정 파일 저장 실패: %s", e)

    def reset_to_defaults(self) -> None:
        """기본 설정으로 리셋"""
        self._config = self._default_config.copy()
        logger.info("설정을 기본값으로 리셋했습니다.")

    def get_all_config(self) -> dict[str, Any]:
        """전체 설정 반환"""
        return self._config.copy()

    def print_config(self) -> None:
        """현재 설정 출력"""
        print("=== 현재 설정 ===")
        for key, value in sorted(self._config.items()):
            print(f"{key}: {value}")
        print("================")

    # 자주 사용하는 설정에 대한 프로퍼티
    @property
    def encoding(self) -> str:
        """파일 인코딩"""
        return str(self._config["encoding"])

    @property
    def crs(self) -> str:
        """좌표계"""
        return str(self._config["crs"])

    @property
    def figure_size(self) -> list[int]:
        """Figure 크기"""
        result = self._config["figure_size"]
        return list(result) if isinstance(result, list) else [10, 8]

    @property
    def dpi(self) -> int:
        """DPI"""
        return int(self._config["dpi"])

    @property
    def debug_mode(self) -> bool:
        """디버그 모드"""
        return bool(self._config["debug_mode"])

    @property
    def log_level(self) -> str:
        """로그 레벨"""
        return str(self._config["log_level"])


# 싱글톤 인스턴스
_config_instance = None


def get_config() -> ProjectConfig:
    """프로젝트 설정 인스턴스 가져오기 (싱글톤)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ProjectConfig()
    return _config_instance


# 기존 코드와의 호환성을 위한 변수들
config = get_config()
PROJECT_ROOT = config.PROJECT_ROOT
DATA_DIR = config.DATA_DIR
RAW_DATA_DIR = config.RAW_DATA_DIR
RESULTS_DIR = config.RESULTS_DIR
SRC_DIR = config.SRC_DIR
REGION_CODE_PATTERN = config.REGION_CODE_PATTERN
PIPE_FATIGUE_DIR = config.PIPE_FATIGUE_DIR
FATIGUE_PIPE_LM_CSV = config.FATIGUE_PIPE_LM_CSV
FATIGUE_SPLY_LS_CSV = config.FATIGUE_SPLY_LS_CSV
UNIFIED_REPAIR_CSV = config.UNIFIED_REPAIR_CSV
REPAIR_COLORS = config.REPAIR_COLORS

# 하위 지역 매핑 (0520 내부 하위 지역)
SUBREGION_MAPPING = {
    "0243": {"parent": "0520", "label": "24-3"},
    "0461": {"parent": "0520", "label": "46-1"},
    "0470": {"parent": "0520", "label": "47"},
    "0480": {"parent": "0520", "label": "48"},
    "0490": {"parent": "0520", "label": "49"},
}

# main51-57 포팅을 위한 추가 변수들 (하위 호환성)
PRESSURE_DATA_FILES = config.PRESSURE_DATA_FILES
V_SHAPED_MIN_FREQ = config.V_SHAPED_MIN_FREQ
PIPE_DATA_FILES = config.PIPE_DATA_FILES
PIPE_PROP_PATH = config.PIPE_PROP_PATH
HIGH_FREQ_FATIGUE_MULTIPLIER = config.HIGH_FREQ_FATIGUE_MULTIPLIER
DEFAULT_FATIGUE_LIMIT = config.DEFAULT_FATIGUE_LIMIT
DEFAULT_PIPE_TYPE = config.DEFAULT_PIPE_TYPE
C_REPAIR = config.C_REPAIR
