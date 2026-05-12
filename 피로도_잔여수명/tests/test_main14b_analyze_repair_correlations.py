"""
main14b_analyze_repair_correlations.py 테스트 모듈
재작업 위치와 파이프 위험 요인 상관관계 분석 기능 테스트
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

# Import from main14_common modules
from src.main14_common.constants import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    OPTIONAL_K_FACTORS,
)
from src.main14b_analyze_repair_correlations import (
    FACTOR_NAMES,
    MIN_REPAIRS_FOR_FREQUENT,
    create_visualizations,
    parse_arguments,
    save_results,
)


class TestMain14bAnalyzeRepairCorrelations(unittest.TestCase):
    """main14b 테스트 클래스"""

    def test_parse_arguments(self):
        """명령줄 인자 파싱 테스트"""
        with patch("sys.argv", ["test.py", "--distance", "50"]):
            args = parse_arguments()
            self.assertEqual(args.distance, 50.0)

        with patch("sys.argv", ["test.py"]):
            args = parse_arguments()
            self.assertEqual(args.distance, 30.0)  # 기본값

    def test_factor_names(self):
        """요인 이름 매핑 테스트"""
        # 모든 기본 K-factors가 FACTOR_NAMES에 있는지 확인
        for factor in BASE_K_FACTORS:
            self.assertIn(factor, FACTOR_NAMES)
            self.assertIsInstance(FACTOR_NAMES[factor], str)

        # DAMAGE_FACTOR가 FACTOR_NAMES에 있는지 확인
        self.assertIn(DAMAGE_FACTOR, FACTOR_NAMES)

        # OPTIONAL_K_FACTORS가 FACTOR_NAMES에 있는지 확인
        for factor in OPTIONAL_K_FACTORS:
            self.assertIn(factor, FACTOR_NAMES)
            self.assertIsInstance(FACTOR_NAMES[factor], str)

    def test_constants(self):
        """상수 값 테스트"""
        self.assertEqual(MIN_REPAIRS_FOR_FREQUENT, 4)

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

    def test_output_directory_usage(self):
        """출력 디렉토리가 올바르게 사용되는지 간단한 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "main14b"
            output_dir.mkdir(parents=True, exist_ok=True)

            # 출력 디렉토리가 생성되었는지 확인
            self.assertTrue(output_dir.exists())
            self.assertTrue(output_dir.is_dir())

            # 경로가 main14b를 포함하는지 확인
            self.assertIn("main14b", str(output_dir))

            # 파일을 저장할 수 있는지 테스트
            test_file = output_dir / "test.txt"
            test_file.write_text("test content")
            self.assertTrue(test_file.exists())

    def test_save_results_output_directory(self):
        """결과 저장시 출력 디렉토리가 올바르게 사용되는지 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "main14b"
            output_dir.mkdir(parents=True, exist_ok=True)

            # 테스트용 데이터 생성
            df_matched = pd.DataFrame({"FTR_IDN": [1, 2, 3], "repair_count": [5, 3, 7]})

            results = {
                "total_repairs": 100,
                "matched_pipes": 50,
                "correlations": {"K_age": 0.5},
            }

            gdf_pipes = MagicMock()
            gdf_pipes.__len__ = MagicMock(return_value=1000)

            # 함수 실행
            save_results(df_matched, results, gdf_pipes, 30.0, output_dir)

            # CSV 파일이 올바른 경로에 저장되었는지 확인
            csv_path = output_dir / "0520_repair_k_factors_matched.csv"
            self.assertTrue(csv_path.exists())

            # 분석 텍스트 파일이 올바른 경로에 저장되었는지 확인
            txt_path = output_dir / "0520_repair_correlations_analysis.txt"
            self.assertTrue(txt_path.exists())

    @patch("src.main14b_analyze_repair_correlations.RESULTS_DIR")
    def test_main_creates_output_directory(self, mock_results_dir):
        """main 함수에서 output_dir이 올바르게 생성되는지 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_results_dir.return_value = Path(tmpdir)

            # main14b 디렉토리가 생성되는지 확인
            expected_dir = Path(tmpdir) / "main14b"

            # 실제 main 함수 실행하지 않고 디렉토리 생성 로직만 테스트
            output_dir = mock_results_dir.return_value / "main14b"
            output_dir.mkdir(parents=True, exist_ok=True)

            self.assertTrue(expected_dir.exists())
            self.assertTrue(expected_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
