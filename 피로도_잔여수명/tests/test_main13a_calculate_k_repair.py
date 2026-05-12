"""
test_main13a_calculate_k_repair.py

main13a_calculate_k_repair.py 모듈 테스트
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

# src 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main13a_calculate_k_repair import (
    MIN_PIPE_LENGTH,
    calculate_k_repair_with_strtree,
    convert_repairs_to_geodataframe,
    load_pipe_shapefile,
    load_unified_repair_csv,
    parse_arguments,
    print_k_repair_statistics,
)


class TestMain13aCalculateKRepair(unittest.TestCase):
    """main13a_calculate_k_repair 모듈 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """테스트 정리"""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_parse_arguments(self):
        """명령줄 인자 파싱 테스트"""
        with patch("sys.argv", ["prog", "--distance", "50", "--verbose"]):
            args = parse_arguments()
            self.assertEqual(args.distance, 50.0)
            self.assertTrue(args.verbose)
            self.assertFalse(args.no_cache)

    def test_load_pipe_shapefile_not_found(self):
        """존재하지 않는 shapefile 로드 테스트"""
        result = load_pipe_shapefile("PIPE_LM", self.test_dir, verbose=False)
        self.assertIsNone(result)

    @patch("geopandas.read_file")
    def test_load_pipe_shapefile_success(self, mock_read_file):
        """shapefile 로드 성공 테스트"""
        # export 디렉토리 생성
        export_dir = self.test_dir / "export_shp_0520"
        export_dir.mkdir()
        shp_file = export_dir / "V_WTL_PIPE_LM.shp"
        shp_file.touch()

        # mock GeoDataFrame
        mock_gdf = gpd.GeoDataFrame(
            {"FTR_IDN": ["001", "002"]},
            geometry=[LineString([(0, 0), (10, 0)]), LineString([(20, 0), (30, 0)])],
            crs="EPSG:5179",
        )
        mock_read_file.return_value = mock_gdf

        result = load_pipe_shapefile("PIPE_LM", self.test_dir, verbose=False)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_load_unified_repair_csv_not_found(self):
        """존재하지 않는 통합 CSV 로드 테스트"""
        result = load_unified_repair_csv(self.test_dir, verbose=False)
        self.assertIsNone(result)

    def test_load_unified_repair_csv_success(self):
        """통합 CSV 로드 성공 테스트"""
        # main13_crop_520 디렉토리 생성
        crop_dir = self.test_dir / "main13_crop_520"
        crop_dir.mkdir(parents=True)

        # 테스트 CSV 생성
        csv_file = crop_dir / "누수공사_통합_520_위치추가.csv"
        test_data = pd.DataFrame(
            {
                "작업일시": [
                    "2023-01-01 10:00:00",
                    "2023-01-02 11:00:00",
                    "2023-01-03 12:00:00",
                    "2023-01-04 13:00:00",
                ],
                "위도": [37.5, 37.6, 37.7, 37.8],
                "경도": [127.0, 127.1, 127.2, 127.3],
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
            }
        )
        test_data.to_csv(csv_file, index=False, encoding="utf-8-sig")

        result = load_unified_repair_csv(self.test_dir, verbose=False)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertIn("repair_type", result.columns)
        self.assertEqual(
            result["repair_type"].tolist(),
            ["지상누수", "지하누수", "긴급공사", "관리대장"],
        )
        self.assertEqual(result["repair_type"].iloc[0], "지상누수")

    def test_convert_repairs_to_geodataframe(self):
        """DataFrame을 GeoDataFrame으로 변환 테스트"""
        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6],
                "경도": [127.0, 127.1],
                "주소": ["서울시 강남구", "서울시 서초구"],
            }
        )

        gdf = convert_repairs_to_geodataframe(df, verbose=False)
        self.assertIsInstance(gdf, gpd.GeoDataFrame)
        self.assertEqual(len(gdf), 2)
        self.assertEqual(gdf.crs, "EPSG:5179")

    def test_calculate_k_repair_with_strtree_empty_repairs(self):
        """재작업이 없는 경우 K_repair 계산 테스트"""
        # 파이프 데이터
        pipes_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["001", "002"],
                "geometry": [
                    LineString([(0, 0), (10, 0)]),
                    LineString([(20, 0), (30, 0)]),
                ],
            },
            crs="EPSG:5179",
        )

        # 빈 재작업 데이터
        repairs_gdf = gpd.GeoDataFrame(
            columns=["repair_type", "geometry"], crs="EPSG:5179"
        )

        result = calculate_k_repair_with_strtree(
            pipes_gdf, repairs_gdf, 30.0, verbose=False
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result["K_repair"].sum(), 0)

    def test_calculate_k_repair_with_strtree_with_repairs(self):
        """재작업이 있는 경우 K_repair 계산 테스트 (선형 가중치)"""
        # 파이프 데이터
        pipes_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["001", "002"],
                "geometry": [
                    LineString([(0, 0), (10, 0)]),
                    LineString([(100, 0), (110, 0)]),
                ],
            },
            crs="EPSG:5179",
        )

        # 재작업 데이터 (첫 번째 파이프 근처에만)
        repairs_gdf = gpd.GeoDataFrame(
            {
                "repair_type": ["지상누수", "지하누수", "긴급공사", "관리대장"],
                "geometry": [
                    Point(5, 5),  # 첫 번째 파이프에서 5m → 가중치 0.83
                    Point(5, 10),  # 첫 번째 파이프에서 10m → 가중치 0.67
                    Point(5, 15),  # 첫 번째 파이프에서 15m → 가중치 0.50
                    Point(5, 20),  # 첫 번째 파이프에서 20m → 가중치 0.33
                ],
            },
            crs="EPSG:5179",
        )

        result = calculate_k_repair_with_strtree(
            pipes_gdf, repairs_gdf, 30.0, verbose=False
        )
        self.assertEqual(len(result), 2)
        # 첫 번째 파이프: 선형 가중치 합계 (0.83 + 0.67 + 0.50 + 0.33 ≈ 2.33)
        self.assertAlmostEqual(result.loc[0, "K_repair"], 2.33, places=1)
        self.assertEqual(result.loc[1, "K_repair"], 0)
        self.assertAlmostEqual(result.loc[0, "K_repair_ground"], 0.83, places=1)
        self.assertAlmostEqual(result.loc[0, "K_repair_under"], 0.67, places=1)
        self.assertAlmostEqual(result.loc[0, "K_repair_emergency"], 0.50, places=1)
        self.assertAlmostEqual(result.loc[0, "K_repair_management"], 0.33, places=1)

    def test_print_k_repair_statistics(self):
        """K_repair 통계 출력 테스트"""
        df = pd.DataFrame(
            {
                "FTR_IDN": ["001", "002", "003", "004"],
                "K_repair": [0, 2, 3, 1],
                "K_repair_ground": [0, 1, 1, 0],
                "K_repair_under": [0, 0, 1, 0],
                "K_repair_emergency": [0, 1, 1, 0],
                "K_repair_management": [0, 0, 0, 1],
                "pipe_length": [10.0, 20.0, 30.0, 40.0],
                "K_repair_per_m": [0.0, 0.1, 0.1, 0.025],
                "K_repair_ground_per_m": [0.0, 0.05, 0.033, 0.0],
                "K_repair_under_per_m": [0.0, 0.0, 0.033, 0.0],
                "K_repair_emergency_per_m": [0.0, 0.05, 0.033, 0.0],
                "K_repair_management_per_m": [0.0, 0.0, 0.0, 0.025],
            }
        )

        # 출력 테스트 (에러 없이 실행되는지만 확인)
        with patch("builtins.print"):
            print_k_repair_statistics(df, "PIPE_LM")

    def test_load_pipe_shapefile_no_ftr_idn(self):
        """FTR_IDN 컬럼이 없는 shapefile 테스트"""
        # export 디렉토리 생성
        export_dir = self.test_dir / "export_shp_0520"
        export_dir.mkdir()
        shp_file = export_dir / "V_WTL_PIPE_LM.shp"
        shp_file.touch()

        with patch("geopandas.read_file") as mock_read_file:
            # FTR_IDN 컬럼이 없는 GeoDataFrame
            mock_gdf = gpd.GeoDataFrame(
                {"OTHER_COL": ["001", "002"]},
                geometry=[
                    LineString([(0, 0), (10, 0)]),
                    LineString([(20, 0), (30, 0)]),
                ],
                crs="EPSG:5179",
            )
            mock_read_file.return_value = mock_gdf

            result = load_pipe_shapefile("PIPE_LM", self.test_dir, verbose=True)
            self.assertIsNone(result)

    def test_load_pipe_shapefile_crs_conversion(self):
        """CRS 변환 테스트"""
        # export 디렉토리 생성
        export_dir = self.test_dir / "export_shp_0520"
        export_dir.mkdir()
        shp_file = export_dir / "V_WTL_PIPE_LM.shp"
        shp_file.touch()

        with patch("geopandas.read_file") as mock_read_file:
            # 다른 CRS를 가진 GeoDataFrame
            mock_gdf = gpd.GeoDataFrame(
                {"FTR_IDN": ["001", "002"]},
                geometry=[
                    LineString([(0, 0), (10, 0)]),
                    LineString([(20, 0), (30, 0)]),
                ],
                crs="EPSG:4326",
            )
            mock_read_file.return_value = mock_gdf

            result = load_pipe_shapefile("PIPE_LM", self.test_dir, verbose=False)
            self.assertIsNotNone(result)
            # to_crs가 호출되었는지 확인
            self.assertEqual(len(result), 2)

    def test_load_unified_repair_csv_no_coordinates(self):
        """위도/경도 컬럼이 없는 통합 CSV 테스트"""
        # main13_crop_520 디렉토리 생성
        crop_dir = self.test_dir / "main13_crop_520"
        crop_dir.mkdir(parents=True)

        # 테스트 CSV 생성
        csv_file = crop_dir / "누수공사_통합_520_위치추가.csv"
        test_data = pd.DataFrame(
            {
                "주소": ["서울시 강남구", "서울시 서초구"],
                "파일타입": ["지상누수", "지하누수"],
            }
        )
        test_data.to_csv(csv_file, index=False, encoding="utf-8-sig")

        result = load_unified_repair_csv(self.test_dir, verbose=True)
        self.assertIsNone(result)

    def test_load_unified_repair_csv_no_filetype_column(self):
        """파일타입 컬럼이 없는 통합 CSV 테스트"""
        # main13_crop_520 디렉토리 생성
        crop_dir = self.test_dir / "main13_crop_520"
        crop_dir.mkdir(parents=True)

        # 테스트 CSV 생성 (파일타입 컬럼 없음)
        csv_file = crop_dir / "누수공사_통합_520_위치추가.csv"
        test_data = pd.DataFrame(
            {
                "위도": [37.5, 37.6],
                "경도": [127.0, 127.1],
                "주소": ["서울시 강남구", "서울시 서초구"],
            }
        )
        test_data.to_csv(csv_file, index=False, encoding="utf-8-sig")

        result = load_unified_repair_csv(self.test_dir, verbose=False)
        self.assertIsNone(result)

    def test_calculate_k_repair_with_verbose_progress(self):
        """verbose 모드에서 진행률 표시 테스트"""
        # 1001개의 파이프 데이터 (진행률 표시를 트리거하기 위해)
        pipes_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": [f"{i:04d}" for i in range(1001)],
                "geometry": [
                    LineString([(i * 10, 0), (i * 10 + 10, 0)]) for i in range(1001)
                ],
            },
            crs="EPSG:5179",
        )

        # 재작업 데이터
        repairs_gdf = gpd.GeoDataFrame(
            {"repair_type": ["지상누수"], "geometry": [Point(5, 5)]}, crs="EPSG:5179"
        )

        with patch("builtins.print"):
            result = calculate_k_repair_with_strtree(
                pipes_gdf, repairs_gdf, 30.0, verbose=True
            )
            self.assertEqual(len(result), 1001)

    @patch("src.main13a_calculate_k_repair.load_pipe_shapefile")
    @patch("src.main13a_calculate_k_repair.load_unified_repair_csv")
    @patch("src.main13a_calculate_k_repair.get_config")
    def test_main_function_no_data(self, mock_config, mock_load_csv, mock_load_shp):
        """메인 함수 테스트 - 데이터 없는 경우"""
        from src.main13a_calculate_k_repair import main

        # Mock 설정
        mock_config.return_value = {
            "DATA_DIR": str(self.test_dir),
            "RESULTS_DIR": str(self.test_dir),
        }
        mock_load_shp.return_value = None
        mock_load_csv.return_value = None

        with patch("sys.argv", ["prog", "--output-dir", str(self.test_dir)]):
            with patch("builtins.print"):
                main()  # 에러 없이 종료되어야 함

    @patch("src.main13a_calculate_k_repair.calculate_k_repair_with_strtree")
    @patch("src.main13a_calculate_k_repair.convert_repairs_to_geodataframe")
    @patch("src.main13a_calculate_k_repair.load_unified_repair_csv")
    @patch("src.main13a_calculate_k_repair.load_pipe_shapefile")
    @patch("src.main13a_calculate_k_repair.get_config")
    def test_main_function_with_data(
        self, mock_config, mock_load_shp, mock_load_csv, mock_convert, mock_calculate
    ):
        """메인 함수 테스트 - 데이터 있는 경우"""
        from src.main13a_calculate_k_repair import main

        # Mock 설정
        mock_config.return_value = {
            "DATA_DIR": str(self.test_dir),
            "RESULTS_DIR": str(self.test_dir),
        }

        # 파이프 데이터
        mock_pipes_gdf = gpd.GeoDataFrame(
            {"FTR_IDN": ["001", "002"]},
            geometry=[LineString([(0, 0), (10, 0)]), LineString([(20, 0), (30, 0)])],
            crs="EPSG:5179",
        )
        mock_load_shp.return_value = mock_pipes_gdf

        # 재작업 데이터
        mock_repairs_df = pd.DataFrame({"위도": [37.5], "경도": [127.0]})
        mock_load_csv.return_value = mock_repairs_df

        # 변환된 GeoDataFrame
        mock_repairs_gdf = gpd.GeoDataFrame(
            {"repair_type": ["지상누수"]}, geometry=[Point(5, 5)], crs="EPSG:5179"
        )
        mock_convert.return_value = mock_repairs_gdf

        # K_repair 계산 결과
        mock_k_repair = pd.DataFrame(
            {
                "FTR_IDN": ["001", "002"],
                "K_repair": [1, 0],
                "K_repair_ground": [1, 0],
                "K_repair_under": [0, 0],
            }
        )
        mock_calculate.return_value = mock_k_repair

        with patch("sys.argv", ["prog", "--output-dir", str(self.test_dir)]):
            with patch("builtins.print"):
                main()

        # 결과 파일 확인
        output_file = self.test_dir / "repair_pipe_lm.csv"
        self.assertTrue(output_file.exists())

    def test_min_pipe_length_constant(self):
        """MIN_PIPE_LENGTH 상수 테스트"""
        self.assertEqual(MIN_PIPE_LENGTH, 10.0)

    def test_calculate_k_repair_with_short_pipes(self):
        """짧은 파이프에 대한 K_repair 정규화 테스트"""
        # 짧은 파이프 데이터 (0.5m, 5m, 15m)
        pipes_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["short1", "short2", "normal"],
                "geometry": [
                    LineString([(0, 0), (0.5, 0)]),    # 0.5m 파이프
                    LineString([(10, 0), (15, 0)]),    # 5m 파이프  
                    LineString([(20, 0), (35, 0)]),    # 15m 파이프
                ],
            },
            crs="EPSG:5179",
        )
        
        # 각 파이프 근처에 1개씩 재작업
        repairs_gdf = gpd.GeoDataFrame(
            {
                "repair_type": ["지상누수", "지상누수", "지상누수"],
                "geometry": [
                    Point(0.25, 1),  # 첫 번째 파이프 근처
                    Point(12.5, 1),  # 두 번째 파이프 근처
                    Point(27.5, 1),  # 세 번째 파이프 근처
                ],
            },
            crs="EPSG:5179",
        )
        
        result = calculate_k_repair_with_strtree(
            pipes_gdf, repairs_gdf, 5.0, verbose=False
        )
        
        # 결과 확인
        self.assertEqual(len(result), 3)
        
        # 파이프 길이는 실제 길이로 저장되어야 함
        short1_row = result[result["FTR_IDN"] == "short1"].iloc[0]
        short2_row = result[result["FTR_IDN"] == "short2"].iloc[0]
        normal_row = result[result["FTR_IDN"] == "normal"].iloc[0]
        
        self.assertAlmostEqual(short1_row["pipe_length"], 0.5, places=1)
        self.assertAlmostEqual(short2_row["pipe_length"], 5.0, places=1)  
        self.assertAlmostEqual(normal_row["pipe_length"], 15.0, places=1)
        
        # K_repair는 거리가 1m 정도이므로 가중치 0.8 (1 - 1/5)
        # 거리 임계값이 5m이고, 재작업이 1m 떨어져 있음
        self.assertAlmostEqual(short1_row["K_repair"], 0.8, places=1)
        self.assertAlmostEqual(short2_row["K_repair"], 0.8, places=1) 
        self.assertAlmostEqual(normal_row["K_repair"], 0.8, places=1)
        
        # K_repair_per_m은 최소 10m 기준으로 계산되어야 함
        # 0.5m, 5m 파이프는 10m로 정규화, 15m는 그대로
        self.assertAlmostEqual(short1_row["K_repair_per_m"], 0.8/10.0, places=3)  # 0.08
        self.assertAlmostEqual(short2_row["K_repair_per_m"], 0.8/10.0, places=3)  # 0.08
        self.assertAlmostEqual(normal_row["K_repair_per_m"], 0.8/15.0, places=3)  # 0.053

    def test_linear_weighting_calculation(self):
        """선형 가중치 계산 정확도 테스트"""
        # 파이프 데이터 - 원점에 위치
        pipes_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["test"],
                "geometry": [LineString([(0, 0), (10, 0)])],  # 10m 파이프
            },
            crs="EPSG:5179",
        )
        
        # 정확한 거리의 재작업들
        repairs_gdf = gpd.GeoDataFrame(
            {
                "repair_type": ["지상누수", "지상누수", "지상누수", "지상누수"],
                "geometry": [
                    Point(5, 0),    # 파이프 위 (거리 0m) → 가중치 1.0
                    Point(5, 10),   # 10m 거리 → 가중치 0.67
                    Point(5, 20),   # 20m 거리 → 가중치 0.33
                    Point(5, 30),   # 30m 거리 → 가중치 0.0
                ],
            },
            crs="EPSG:5179",
        )
        
        result = calculate_k_repair_with_strtree(
            pipes_gdf, repairs_gdf, 30.0, verbose=False
        )
        
        # 예상 K_repair = 1.0 + 0.67 + 0.33 + 0.0 = 2.0
        self.assertAlmostEqual(result.iloc[0]["K_repair"], 2.0, places=1)
        self.assertAlmostEqual(result.iloc[0]["K_repair_ground"], 2.0, places=1)

    def test_calculate_k_repair_empty_repairs_with_short_pipes(self):
        """재작업이 없는 짧은 파이프 테스트"""
        # 짧은 파이프 데이터
        pipes_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["short"],
                "geometry": [LineString([(0, 0), (2, 0)])],  # 2m 파이프
            },
            crs="EPSG:5179",
        )
        
        # 빈 재작업 데이터
        repairs_gdf = gpd.GeoDataFrame(
            {"repair_type": [], "geometry": []}, crs="EPSG:5179"
        )
        
        result = calculate_k_repair_with_strtree(
            pipes_gdf, repairs_gdf, 30.0, verbose=False
        )
        
        # 결과 확인
        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        
        # 실제 길이 저장
        self.assertAlmostEqual(row["pipe_length"], 2.0, places=1)
        
        # K_repair는 모두 0
        self.assertEqual(row["K_repair"], 0)
        self.assertEqual(row["K_repair_per_m"], 0)


if __name__ == "__main__":
    unittest.main()
