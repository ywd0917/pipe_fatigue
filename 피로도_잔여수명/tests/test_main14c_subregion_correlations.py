"""
main14c_subregion_correlations.py 테스트
하위 지역별 K-factors 상관관계 분석 테스트
"""

import unittest
from pathlib import Path
from unittest.mock import patch

# Import from main14_common modules
from src.main14_common.constants import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    OPTIONAL_K_FACTORS,
)
from src.main14c_subregion_correlations import parse_arguments


class TestMain14cSubregionCorrelations(unittest.TestCase):
    """main14c 테스트 클래스"""

    def test_parse_arguments(self):
        """명령줄 인자 파싱 테스트"""
        # Test with custom arguments
        with patch("sys.argv", ["test.py", "--region", "0470", "--distance", "50"]):
            args = parse_arguments()
            self.assertEqual(args.region, "0470")
            self.assertEqual(args.distance, 50.0)

        # Test with default arguments
        with patch("sys.argv", ["test.py"]):
            args = parse_arguments()
            self.assertEqual(args.distance, 30.0)  # 기본값
            self.assertIsNone(args.region)  # 기본값은 None

    def test_constants(self):
        """상수 값 테스트"""
        # BASE_K_FACTORS 테스트
        self.assertEqual(len(BASE_K_FACTORS), 7)
        self.assertEqual(BASE_K_FACTORS[0], "STD_DIP")  # 첫 번째 요소
        self.assertIn("K_age", BASE_K_FACTORS)
        self.assertIn("K_soil", BASE_K_FACTORS)
        self.assertIn("K_traffic", BASE_K_FACTORS)
        self.assertIn("hoop_stress", BASE_K_FACTORS)
        self.assertIn("K_stress", BASE_K_FACTORS)
        self.assertIn("K_total", BASE_K_FACTORS)

        # OPTIONAL_K_FACTORS 테스트
        self.assertEqual(len(OPTIONAL_K_FACTORS), 1)
        self.assertEqual(OPTIONAL_K_FACTORS[0], "K_repair")

        # DAMAGE_FACTOR 테스트
        self.assertEqual(DAMAGE_FACTOR, "D_final")


if __name__ == "__main__":
    unittest.main()
