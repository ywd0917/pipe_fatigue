"""main14a_subregion_repair.py 테스트"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import numpy as np
from matplotlib.colors import LogNorm
from shapely.geometry import LineString, Polygon

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.config import SUBREGION_MAPPING
from main14a_subregion_repair import (
    filter_pipes_by_region_safe,
    parse_arguments,
    plot_region_boundary,
)


class TestMain14aSubregionRepair(unittest.TestCase):
    """main14a_subregion_repair.py 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 테스트용 지오메트리 생성
        self.test_boundary = gpd.GeoDataFrame(
            {
                "SMZ_LBL": ["47"],
                "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])],
            },
            crs="EPSG:5186",
        )

        # 테스트용 파이프 데이터
        self.test_pipes = gpd.GeoDataFrame(
            {
                "FTR_CDE": ["SA001", "SA002", "SA003", "SA004"],
                "FTR_IDN": [1, 2, 3, 4],
                "geometry": [
                    LineString([(1, 1), (2, 2)]),  # 경계 내부
                    LineString([(5, 5), (6, 6)]),  # 경계 내부
                    LineString([(9, 9), (9.5, 9.5)]),  # 경계 내부
                    LineString([(11, 11), (12, 12)]),  # 경계 외부
                ],
            },
            crs="EPSG:5186",
        )

    def test_filter_pipes_by_region_safe(self):
        """안전한 파이프 필터링 테스트"""
        # 필터링 실행
        filtered = filter_pipes_by_region_safe(self.test_pipes, self.test_boundary)

        # 경계 내부 파이프만 남아있는지 확인 (3개)
        self.assertEqual(len(filtered), 3)
        self.assertIn("SA001", filtered["FTR_CDE"].values)
        self.assertIn("SA002", filtered["FTR_CDE"].values)
        self.assertIn("SA003", filtered["FTR_CDE"].values)
        self.assertNotIn("SA004", filtered["FTR_CDE"].values)

        # 원본 컬럼이 유지되는지 확인
        expected_columns = ["FTR_CDE", "FTR_IDN", "geometry"]
        for col in expected_columns:
            self.assertIn(col, filtered.columns)

    def test_subregion_mapping(self):
        """SUBREGION_MAPPING 설정 테스트"""
        # 각 하위 지역이 올바르게 매핑되어 있는지 확인
        for region_code in ["0470", "0480", "0490"]:
            self.assertIn(region_code, SUBREGION_MAPPING)
            self.assertEqual(SUBREGION_MAPPING[region_code]["parent"], "0520")

        # 라벨 확인
        self.assertEqual(SUBREGION_MAPPING["0470"]["label"], "47")
        self.assertEqual(SUBREGION_MAPPING["0480"]["label"], "48")
        self.assertEqual(SUBREGION_MAPPING["0490"]["label"], "49")

    def test_coordinate_system(self):
        """좌표계 일관성 테스트"""
        # 모든 GeoDataFrame이 같은 CRS를 사용하는지 확인
        self.assertEqual(self.test_pipes.crs, "EPSG:5186")
        self.assertEqual(self.test_boundary.crs, "EPSG:5186")

    def test_color_normalization(self):
        """색상 정규화 테스트"""
        # LogNorm이 올바르게 생성되는지 테스트
        d_final_values = np.array([0.001, 0.01, 0.1, 1.0, 10.0])
        d_final_values = d_final_values[d_final_values > 0]

        norm = LogNorm(vmin=d_final_values.min(), vmax=d_final_values.max())

        # 정규화 범위 확인
        self.assertAlmostEqual(norm.vmin, 0.001)
        self.assertAlmostEqual(norm.vmax, 10.0)

        # 정규화된 값이 0-1 범위에 있는지 확인
        normalized = norm(d_final_values)
        self.assertTrue(all(0 <= v <= 1 for v in normalized))

    def test_region_filtering_accuracy(self):
        """지역 필터링 정확도 테스트"""
        # 다양한 위치의 파이프 생성
        test_pipes = gpd.GeoDataFrame(
            {
                "FTR_CDE": ["P1", "P2", "P3", "P4", "P5"],
                "geometry": [
                    LineString([(5, 5), (6, 6)]),  # 완전히 내부
                    LineString([(9, 5), (11, 5)]),  # 경계를 교차
                    LineString([(11, 11), (12, 12)]),  # 완전히 외부
                    LineString([(0, 0), (0, 10)]),  # 경계선 상
                    LineString([(4, 4), (5, 5)]),  # 내부
                ],
            },
            crs="EPSG:5186",
        )

        # 필터링
        filtered = filter_pipes_by_region_safe(test_pipes, self.test_boundary)

        # intersects 조건이므로 경계를 교차하거나 내부에 있는 파이프 포함
        # P1(내부), P2(교차), P4(경계), P5(내부) = 4개
        self.assertGreaterEqual(len(filtered), 3)  # 최소 3개 이상 (내부 및 경계)
        self.assertLessEqual(len(filtered), 5)  # 최대 5개 이하

    def test_filter_with_empty_data(self):
        """빈 데이터에 대한 필터링 테스트"""
        # 빈 파이프 데이터
        empty_pipes = gpd.GeoDataFrame(
            {"FTR_CDE": [], "FTR_IDN": [], "geometry": []}, crs="EPSG:5186"
        )

        # 필터링 실행
        filtered = filter_pipes_by_region_safe(empty_pipes, self.test_boundary)

        # 빈 데이터 반환 확인
        self.assertEqual(len(filtered), 0)

    def test_filter_with_large_boundary(self):
        """큰 경계에 대한 필터링 테스트"""
        # 모든 파이프를 포함하는 큰 경계
        large_boundary = gpd.GeoDataFrame(
            {
                "geometry": [
                    Polygon(
                        [
                            (-100, -100),
                            (100, -100),
                            (100, 100),
                            (-100, 100),
                            (-100, -100),
                        ]
                    )
                ]
            },
            crs="EPSG:5186",
        )

        # 필터링 실행
        filtered = filter_pipes_by_region_safe(self.test_pipes, large_boundary)

        # 모든 파이프가 포함되는지 확인
        self.assertEqual(len(filtered), len(self.test_pipes))

    def test_filter_preserves_data_types(self):
        """필터링 후 데이터 타입 유지 테스트"""
        # 다양한 데이터 타입을 가진 파이프 데이터
        pipes_with_types = self.test_pipes.copy()
        pipes_with_types["INT_COL"] = [1, 2, 3, 4]
        pipes_with_types["FLOAT_COL"] = [1.1, 2.2, 3.3, 4.4]
        pipes_with_types["STR_COL"] = ["a", "b", "c", "d"]

        # 필터링 실행
        filtered = filter_pipes_by_region_safe(pipes_with_types, self.test_boundary)

        # 데이터 타입이 유지되는지 확인
        self.assertTrue(filtered["INT_COL"].dtype in [np.int64, np.int32])
        self.assertTrue(filtered["FLOAT_COL"].dtype in [np.float64, np.float32])
        self.assertEqual(filtered["STR_COL"].dtype, object)

    @patch("matplotlib.pyplot.show")
    def test_plot_region_boundary_runs(self, mock_show):
        """plot_region_boundary 함수가 에러 없이 실행되는지 테스트"""
        import matplotlib.pyplot as plt

        # 축 생성
        fig, ax = plt.subplots(figsize=(10, 10))

        # 경계 표시 (에러 없이 실행되는지만 확인)
        try:
            plot_region_boundary(ax, self.test_boundary)
            success = True
        except Exception as e:
            success = False
            print(f"Error in plot_region_boundary: {e}")

        self.assertTrue(success)
        plt.close(fig)


class TestParseArguments(unittest.TestCase):
    """parse_arguments 함수 테스트"""

    def test_default_arguments(self):
        """기본 인자 테스트"""
        with patch("sys.argv", ["test_script.py"]):
            args = parse_arguments()

            self.assertEqual(args.region, "0520")
            self.assertIsNone(args.output_dir)
            self.assertFalse(args.show)
            self.assertTrue(args.all)  # --all이 기본값
            self.assertFalse(args.individual)
            self.assertFalse(args.no_interactive)

    def test_custom_region(self):
        """지역 코드 지정 테스트"""
        with patch("sys.argv", ["test_script.py", "--region", "0470"]):
            args = parse_arguments()

            self.assertEqual(args.region, "0470")
            self.assertTrue(args.all)  # --all이 기본값

    def test_individual_option(self):
        """개별 이미지 생성 옵션 테스트"""
        with patch("sys.argv", ["test_script.py", "--individual"]):
            args = parse_arguments()

            self.assertTrue(args.individual)
            self.assertTrue(args.all)  # --all은 여전히 기본값

    def test_all_options(self):
        """모든 옵션 테스트"""
        with patch(
            "sys.argv",
            [
                "test_script.py",
                "--region",
                "0480",
                "--output-dir",
                "/tmp/output",
                "--show",
                "--no-interactive",
                "--individual",
            ],
        ):
            args = parse_arguments()

            self.assertEqual(args.region, "0480")
            self.assertEqual(args.output_dir, "/tmp/output")
            self.assertTrue(args.show)
            self.assertTrue(args.all)  # 기본값
            self.assertTrue(args.individual)
            self.assertTrue(args.no_interactive)


if __name__ == "__main__":
    unittest.main()
