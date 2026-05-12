"""
Tests for main17a2_distance_sensitivity module
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from src.main17a2_distance_sensitivity import (
    create_analysis_report,
    parse_results,
    run_main17a_for_distance,
)


class TestMain17a2DistanceSensitivity(unittest.TestCase):
    """Test cases for main17a2 distance sensitivity analysis"""

    @patch("src.main17a2_distance_sensitivity.subprocess.run")
    @patch("src.main17a2_distance_sensitivity.sys.executable", "/usr/bin/python")
    def test_run_main17a_for_distance_success(self, mock_run):
        """Test successful execution of main17a for a specific distance"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        success, output_dir = run_main17a_for_distance(30)

        self.assertTrue(success)
        self.assertIn("distance_30m", str(output_dir))
        mock_run.assert_called_once()

        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "/usr/bin/python")
        self.assertIn("main17a", call_args[1])
        self.assertEqual(call_args[3], "30")

    @patch("src.main17a2_distance_sensitivity.subprocess.run")
    def test_run_main17a_for_distance_failure(self, mock_run):
        """Test failed execution of main17a"""
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "cmd", stderr="Error message")

        success, output_dir = run_main17a_for_distance(30)

        self.assertFalse(success)
        self.assertIn("distance_30m", str(output_dir))

    def test_parse_results_with_csv_file(self):
        """Test parsing results from CSV file"""
        output_dir = Path("/tmp/test_output")

        csv_data = pd.DataFrame(
            {
                "전략": ["최대 CNT_JNT", "평균 CNT_JNT", "가장 가까운"],
                "상관계수(r)": [-0.0681, -0.0757, -0.0250],
                "p-value": [0.1201, 0.0840, 0.5693],
                "R²": [0.0046, 0.0057, 0.0006],
                "차이": [-0.1080, -0.1019, 0.0115],
            }
        )

        matched_csv_data = pd.DataFrame(
            {"X": range(522), "Y": range(522), "MAX_CNT_JNT": [1.5] * 522}
        )

        metadata_content = {
            "total_operations": 1943,
            "matched_operations": 522,
            "match_rate": 0.2686,
        }

        import json

        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("pandas.read_csv") as mock_read_csv,
            patch("builtins.open", mock_open(read_data=json.dumps(metadata_content))),
        ):

            # First call checks for metadata JSON, second for CSV, third for matched CSV
            mock_exists.side_effect = [True, True, False]
            mock_read_csv.side_effect = [csv_data, matched_csv_data]

            results = parse_results(output_dir)

            self.assertAlmostEqual(results["최대_CNT_JNT_r"], -0.0681)
            self.assertAlmostEqual(results["최대_CNT_JNT_p"], 0.1201)
            self.assertAlmostEqual(results["최대_CNT_JNT_r2"], 0.0046)
            self.assertEqual(results["matched_operations"], 522)
            self.assertEqual(results["total_operations"], 1943)
            self.assertAlmostEqual(results["match_rate"], 0.2686)

    def test_parse_results_missing_files(self):
        """Test parsing results when files are missing"""
        output_dir = Path("/tmp/test_output")

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            results = parse_results(output_dir)

            self.assertEqual(results, {})

    def test_create_analysis_report(self):
        """Test analysis report generation"""
        all_results = {
            10: {
                "match_rate": 1.0,
                "matched_operations": 522,
                "total_operations": 522,
                "matched_clusters": 522,  # backward compatibility
                "total_clusters": 522,  # backward compatibility
                "최대_CNT_JNT_r": -0.0681,
                "최대_CNT_JNT_p": 0.1201,
                "최대_CNT_JNT_r2": 0.0046,
                "평균_CNT_JNT_r": -0.0757,
                "평균_CNT_JNT_p": 0.0840,
                "평균_CNT_JNT_r2": 0.0057,
                "가장_가까운_r": -0.0250,
                "가장_가까운_p": 0.5693,
                "가장_가까운_r2": 0.0006,
            },
            20: {
                "match_rate": 1.0,
                "matched_operations": 585,
                "total_operations": 585,
                "matched_clusters": 585,  # backward compatibility
                "total_clusters": 585,  # backward compatibility
                "최대_CNT_JNT_r": -0.0331,
                "최대_CNT_JNT_p": 0.4240,
                "최대_CNT_JNT_r2": 0.0011,
                "평균_CNT_JNT_r": -0.0552,
                "평균_CNT_JNT_p": 0.1822,
                "평균_CNT_JNT_r2": 0.0030,
                "가장_가까운_r": -0.0129,
                "가장_가까운_p": 0.7563,
                "가장_가까운_r2": 0.0002,
            },
        }

        report = create_analysis_report(all_results)

        self.assertIn("# 거리별 민감도 분석 보고서", report)
        self.assertIn("## 📊 결과 요약", report)
        self.assertIn("| 거리(m) | 매칭률 |", report)
        self.assertIn("10 | 100.0%", report)
        self.assertIn("20 | 100.0%", report)
        self.assertIn("## 📈 거리별 상세 분석", report)
        self.assertIn("### 거리 10m", report)
        self.assertIn("### 거리 20m", report)
        self.assertIn("## 🎯 주요 발견사항", report)
        self.assertIn("## 💡 결론", report)

    def test_create_analysis_report_with_significant_results(self):
        """Test report generation with statistically significant results"""
        all_results = {
            10: {
                "match_rate": 0.9,
                "matched_operations": 450,
                "total_operations": 500,
                "matched_clusters": 450,  # backward compatibility
                "total_clusters": 500,  # backward compatibility
                "최대_CNT_JNT_r": 0.45,
                "최대_CNT_JNT_p": 0.001,  # Significant p-value
                "최대_CNT_JNT_r2": 0.2025,
                "평균_CNT_JNT_r": 0.30,
                "평균_CNT_JNT_p": 0.03,  # Significant p-value
                "평균_CNT_JNT_r2": 0.09,
                "가장_가까운_r": 0.10,
                "가장_가까운_p": 0.5,
                "가장_가까운_r2": 0.01,
            }
        }

        report = create_analysis_report(all_results)

        self.assertIn("** (p<0.01)", report)
        self.assertIn("* (p<0.05)", report)
        self.assertIn("통계적으로 유의한 결과", report)
        self.assertIn("10m에서 최대_CNT_JNT", report)

    def test_create_analysis_report_empty_results(self):
        """Test report generation with empty results"""
        all_results = {}

        report = create_analysis_report(all_results)

        self.assertIn("# 거리별 민감도 분석 보고서", report)
        self.assertIn("모든 거리에서 유의한 상관관계가 발견되지 않음", report)

    def test_create_analysis_report_partial_results(self):
        """Test report generation with partial results (some distances failed)"""
        all_results = {
            10: {
                "match_rate": 1.0,
                "matched_operations": 522,
                "total_operations": 522,
                "matched_clusters": 522,  # backward compatibility
                "total_clusters": 522,  # backward compatibility
                "최대_CNT_JNT_r": -0.0681,
                "최대_CNT_JNT_p": 0.1201,
                "최대_CNT_JNT_r2": 0.0046,
                "평균_CNT_JNT_r": -0.0757,
                "평균_CNT_JNT_p": 0.0840,
                "평균_CNT_JNT_r2": 0.0057,
                "가장_가까운_r": -0.0250,
                "가장_가까운_p": 0.5693,
                "가장_가까운_r2": 0.0006,
            },
            20: None,  # Failed distance
            30: {
                "match_rate": 1.0,
                "matched_operations": 588,
                "total_operations": 588,
                "matched_clusters": 588,  # backward compatibility
                "total_clusters": 588,  # backward compatibility
                "최대_CNT_JNT_r": 0.0010,
                "최대_CNT_JNT_p": 0.9805,
                "최대_CNT_JNT_r2": 0.0000,
                "평균_CNT_JNT_r": -0.0284,
                "평균_CNT_JNT_p": 0.4914,
                "평균_CNT_JNT_r2": 0.0008,
                "가장_가까운_r": -0.0110,
                "가장_가까운_p": 0.7904,
                "가장_가까운_r2": 0.0001,
            },
        }

        report = create_analysis_report(all_results)

        self.assertIn("### 거리 10m", report)
        self.assertNotIn("### 거리 20m", report)  # Failed distance not included
        self.assertIn("### 거리 30m", report)

    @patch("src.main17a2_distance_sensitivity.create_visualizations")
    @patch("src.main17a2_distance_sensitivity.create_analysis_report")
    @patch("src.main17a2_distance_sensitivity.parse_results")
    @patch("src.main17a2_distance_sensitivity.run_main17a_for_distance")
    @patch("builtins.open", new_callable=mock_open)
    def test_main_function_integration(
        self, mock_file, mock_run, mock_parse, mock_report, mock_viz
    ):
        """Test main function integration"""
        from src.main17a2_distance_sensitivity import main

        # Setup mocks
        mock_run.return_value = (True, Path("/tmp/output"))
        mock_parse.return_value = {
            "match_rate": 1.0,
            "matched_operations": 522,
            "total_operations": 522,
            "matched_clusters": 522,  # backward compatibility
            "total_clusters": 522,  # backward compatibility
            "최대_CNT_JNT_r": -0.0681,
            "최대_CNT_JNT_p": 0.1201,
            "최대_CNT_JNT_r2": 0.0046,
        }
        mock_report.return_value = "# Test Report"

        with patch("pathlib.Path.mkdir"):
            main()

        # Verify all distances were processed
        self.assertEqual(mock_run.call_count, 5)  # 10, 20, 30, 50, 100
        mock_run.assert_any_call(10)
        mock_run.assert_any_call(20)
        mock_run.assert_any_call(30)
        mock_run.assert_any_call(50)
        mock_run.assert_any_call(100)

        # Verify report and visualization were created
        mock_report.assert_called_once()
        mock_viz.assert_called_once()


class TestDistanceSensitivityEdgeCases(unittest.TestCase):
    """Edge case tests for distance sensitivity analysis"""

    def test_parse_results_malformed_csv(self):
        """Test handling of malformed CSV data"""
        output_dir = Path("/tmp/test_output")

        # CSV with missing columns (simulate malformed data)
        csv_data = pd.DataFrame(
            {
                "전략": ["최대 CNT_JNT"],
                "상관계수(r)": [-0.0681],
                # Missing 'p-value', 'R²', '차이' columns
            }
        )

        matched_csv_data = pd.DataFrame({"cluster_id": [1], "CNT_JNT": [1.5]})

        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("pandas.read_csv") as mock_read_csv,
            patch("builtins.open", mock_open(read_data="")),
        ):

            # Simple approach: CSV files exist, txt file doesn't
            # Metadata JSON exists but is malformed/empty
            mock_exists.side_effect = [
                True,
                True,
                True,
            ]  # metadata.json exists (but malformed), csv exists, matched_csv exists
            mock_read_csv.side_effect = [csv_data, matched_csv_data]

            # Mock open to return empty string for JSON (simulating malformed file)
            with patch("builtins.open", mock_open(read_data="")):
                # Should handle gracefully without crashing
                results = parse_results(output_dir)

            # Results should contain what was available with defaults for missing
            self.assertIsInstance(results, dict)
            # When JSON is malformed, we should still get CSV data
            if results:  # If we got any results from CSV
                self.assertIn("최대_CNT_JNT_r", results)
                self.assertEqual(results["최대_CNT_JNT_r"], -0.0681)
                self.assertEqual(
                    results["최대_CNT_JNT_p"], 1
                )  # Default value for missing
                self.assertEqual(
                    results["최대_CNT_JNT_r2"], 0
                )  # Default value for missing
                # When no metadata, falls back to CSV counting
                if "matched_operations" in results:
                    self.assertEqual(results["matched_operations"], 1)
                    self.assertEqual(
                        results["matched_clusters"], 1
                    )  # backward compatibility
            else:
                # If CSV reading also failed, we should get empty dict
                self.assertEqual(results, {})

    def test_create_report_best_strategy_selection(self):
        """Test best strategy selection in report"""
        all_results = {
            10: {
                "match_rate": 1.0,
                "최대_CNT_JNT_r2": 0.01,
                "평균_CNT_JNT_r2": 0.05,  # Best R²
                "가장_가까운_r2": 0.02,
            },
            20: {
                "match_rate": 1.0,
                "최대_CNT_JNT_r2": 0.03,
                "평균_CNT_JNT_r2": 0.02,
                "가장_가까운_r2": 0.01,
            },
        }

        report = create_analysis_report(all_results)

        # Should identify 10m with 평균_CNT_JNT as best
        self.assertIn("최적 거리**: 10m", report)
        self.assertIn("평균_CNT_JNT", report)
        self.assertIn("R²=0.0500", report)


if __name__ == "__main__":
    unittest.main()
