"""
main14_common/constants.py 테스트
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main14_common.constants import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    DEFAULT_DISTANCE,
    OPTIONAL_K_FACTORS,
    PARENT_REGION,
    P_VALUE_THRESHOLD,
    FACTOR_NAMES,
)


def test_k_factor_constants():
    """K-factor 상수 정의 테스트"""
    # BASE_K_FACTORS는 7개여야 함
    assert len(BASE_K_FACTORS) == 7
    assert "STD_DIP" in BASE_K_FACTORS
    assert "K_age" in BASE_K_FACTORS
    assert "K_total" in BASE_K_FACTORS

    # OPTIONAL_K_FACTORS
    assert "K_repair" in OPTIONAL_K_FACTORS

    # DAMAGE_FACTOR
    assert DAMAGE_FACTOR == "D_final"


def test_default_values():
    """기본값 상수 테스트"""
    assert DEFAULT_DISTANCE == 30
    assert PARENT_REGION == "0520"
    assert P_VALUE_THRESHOLD == 0.05


def test_factor_names():
    """K-factor 이름 매핑 테스트"""
    # 모든 BASE_K_FACTORS가 FACTOR_NAMES에 있는지 확인
    for factor in BASE_K_FACTORS:
        assert factor in FACTOR_NAMES

    # 모든 OPTIONAL_K_FACTORS가 FACTOR_NAMES에 있는지 확인
    for factor in OPTIONAL_K_FACTORS:
        assert factor in FACTOR_NAMES

    # DAMAGE_FACTOR도 FACTOR_NAMES에 있는지 확인
    assert DAMAGE_FACTOR in FACTOR_NAMES
