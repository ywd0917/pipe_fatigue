"""
프로젝트 전체 설정 관리 모듈 (최소화 버전 - rainflow 분석용)
"""

from pathlib import Path

# ============================================================================
# 프로젝트 경로 설정
# ============================================================================

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# 주요 디렉토리 경로
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RESULTS_DIR = PROJECT_ROOT / "results"

# 결과 디렉토리 생성
RESULTS_DIR.mkdir(exist_ok=True)

# ============================================================================
# 압력 데이터 파일 경로
# ============================================================================

# 개별 파일 경로 (6개)
SMALL_AREA_0243_PRESSURE_DATA_PATH = RAW_DATA_DIR / "0243 소구역 압력 데이터.csv"
SMALL_AREA_0461_PRESSURE_DATA_PATH = RAW_DATA_DIR / "0461 소구역 압력 데이터.csv"
SMALL_AREA_0470_PRESSURE_DATA_PATH = RAW_DATA_DIR / "0470 소구역 압력 데이터.csv"
SMALL_AREA_0480_PRESSURE_DATA_PATH = RAW_DATA_DIR / "0480 소구역 압력 데이터.csv"
SMALL_AREA_0490_PRESSURE_DATA_PATH = RAW_DATA_DIR / "0490 소구역 압력 데이터.csv"
MIDDLE_AREA_PRESSURE_DATA_PATH = RAW_DATA_DIR / "0520 중구역 압력 데이터.csv"

# 압력 데이터 파일 리스트 (순서 중요: 0243 → 0461 → 0470 → 0480 → 0490 → 0520)
PRESSURE_DATA_FILES = [
    SMALL_AREA_0243_PRESSURE_DATA_PATH,
    SMALL_AREA_0461_PRESSURE_DATA_PATH,
    SMALL_AREA_0470_PRESSURE_DATA_PATH,
    SMALL_AREA_0480_PRESSURE_DATA_PATH,
    SMALL_AREA_0490_PRESSURE_DATA_PATH,
    MIDDLE_AREA_PRESSURE_DATA_PATH,
]

# ============================================================================
# 주파수 분석 관련 상수
# ============================================================================

# V자 최저점 주파수 (분)
V_SHAPED_MIN_FREQ = 553.5
