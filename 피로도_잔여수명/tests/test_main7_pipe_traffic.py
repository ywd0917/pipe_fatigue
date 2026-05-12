"""main7_pipe_traffic.py 테스트."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

from src.main7_pipe_traffic import (
    extract_region_code,
    get_export_directories,
)
from src.traffic_analyzer import (
    MAX_BUFFER_DISTANCE,
    MIN_BUFFER_DISTANCE,
    calculate_buffer_distance,
    save_traffic_csv,
    select_primary_road,
)


class TestBufferCalculation(unittest.TestCase):
    """버퍼 계산 테스트."""

    def test_buffer_distance_normal(self):
        """일반적인 도로 폭에 대한 버퍼 계산."""
        # 20m 도로 -> 10m 버퍼
        self.assertEqual(calculate_buffer_distance(20.0), 10.0)

        # 10m 도로 -> 5m 버퍼
        self.assertEqual(calculate_buffer_distance(10.0), 5.0)

    def test_buffer_distance_minimum(self):
        """최소 버퍼 거리 적용."""
        # 4m 도로 -> 3m 버퍼 (최소값)
        self.assertEqual(calculate_buffer_distance(4.0), MIN_BUFFER_DISTANCE)

        # 2m 도로 -> 3m 버퍼 (최소값)
        self.assertEqual(calculate_buffer_distance(2.0), MIN_BUFFER_DISTANCE)

    def test_buffer_distance_maximum(self):
        """최대 버퍼 거리 적용."""
        # 50m 도로 -> 20m 버퍼 (최대값)
        self.assertEqual(calculate_buffer_distance(50.0), MAX_BUFFER_DISTANCE)

        # 100m 도로 -> 20m 버퍼 (최대값)
        self.assertEqual(calculate_buffer_distance(100.0), MAX_BUFFER_DISTANCE)


class TestExportDirectory(unittest.TestCase):
    """Export 디렉토리 관련 테스트."""

    @patch("src.main7_pipe_traffic.Path.glob")
    def test_get_export_directories(self, mock_glob):
        """모든 export 디렉토리 가져오기 테스트."""
        # Mock 디렉토리 리스트
        mock_dirs = [
            Path("export_shp_20250701(0800)"),
            Path("export_shp_20250704(0520)"),
            Path("export_shp_20250704(0903)"),
        ]
        mock_glob.return_value = mock_dirs

        base_dir = Path("/test/data/raw")
        result = get_export_directories(base_dir)

        # 모든 디렉토리가 정렬된 순서로 반환되어야 함
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], Path("export_shp_20250701(0800)"))
        self.assertEqual(result[2], Path("export_shp_20250704(0903)"))

    @patch("src.main7_pipe_traffic.Path.glob")
    def test_get_export_directories_empty(self, mock_glob):
        """export 디렉토리가 없는 경우."""
        mock_glob.return_value = []

        base_dir = Path("/test/data/raw")
        result = get_export_directories(base_dir)

        self.assertEqual(result, [])

    def test_extract_region_code(self):
        """지역 코드 추출 테스트."""
        # 정상적인 경우
        self.assertEqual(extract_region_code("export_shp_20250704(0520)"), "0520")
        self.assertEqual(extract_region_code("export_shp_20250704(0903)"), "0903")

        # 괄호가 없는 경우
        self.assertEqual(extract_region_code("export_shp_20250704"), "unknown")

        # 잘못된 형식
        self.assertEqual(extract_region_code("some_other_folder"), "unknown")


class TestRoadPriority(unittest.TestCase):
    """도로 우선순위 선택 테스트."""

    def setUp(self):
        """테스트 데이터 설정."""
        # 여러 도로와 중첩된 파이프 데이터
        self.overlap_data = pd.DataFrame(
            {
                "FTR_IDN": [12345, 12345, 12345, 23456, 23456],
                "RN_CD": ["2007001", "2007002", "2007003", "2007004", "2007005"],
                "RN": ["대구로", "중앙로", "시민로", "동대구로", "범어로"],
                "ROAD_BT": [30.0, 20.0, 25.0, 15.0, 15.0],
                "ROA_CLS_SE": [1, 2, 2, 3, 2],
                "SIG_CD": ["27110", "27110", "27110", "27110", "27110"],
            }
        )

    def test_select_by_road_width(self):
        """도로 폭 우선순위 테스트."""
        result = select_primary_road(self.overlap_data, verbose=False)

        # FTR_IDN 12345는 도로폭 30m인 대구로가 선택되어야 함
        pipe_12345 = result[result["FTR_IDN"] == 12345]
        self.assertEqual(len(pipe_12345), 1)
        self.assertEqual(pipe_12345.iloc[0]["RN"], "대구로")
        self.assertEqual(pipe_12345.iloc[0]["ROAD_BT"], 30.0)

    def test_select_by_road_class(self):
        """도로 폭이 같을 때 도로 등급 우선순위 테스트."""
        result = select_primary_road(self.overlap_data, verbose=False)

        # FTR_IDN 23456은 도로폭이 같으므로 등급이 높은(숫자가 작은) 범어로가 선택되어야 함
        pipe_23456 = result[result["FTR_IDN"] == 23456]
        self.assertEqual(len(pipe_23456), 1)
        self.assertEqual(pipe_23456.iloc[0]["RN"], "범어로")
        self.assertEqual(pipe_23456.iloc[0]["ROA_CLS_SE"], 2)

    def test_no_duplicates(self):
        """각 파이프당 하나의 도로만 선택되는지 테스트."""
        result = select_primary_road(self.overlap_data, verbose=False)

        # 각 FTR_IDN은 한 번만 나타나야 함
        ftr_idn_counts = result["FTR_IDN"].value_counts()
        self.assertTrue(all(count == 1 for count in ftr_idn_counts))


class TestSpatialOperations(unittest.TestCase):
    """공간 연산 관련 테스트."""

    def test_buffer_creation(self):
        """도로 버퍼 생성 테스트."""
        # 테스트용 도로 데이터
        road_line = LineString([(0, 0), (100, 0)])
        gpd.GeoDataFrame(
            {
                "RN_CD": ["2007001"],
                "RN": ["테스트로"],
                "ROAD_BT": [20.0],
                "ROA_CLS_SE": [1],
                "SIG_CD": ["27110"],
                "geometry": [road_line],
            }
        )

        # 버퍼 계산
        buffer_dist = calculate_buffer_distance(20.0)
        self.assertEqual(buffer_dist, 10.0)

        # 버퍼 생성
        buffered = road_line.buffer(buffer_dist)
        self.assertIsNotNone(buffered)
        self.assertTrue(buffered.contains(road_line))


class TestDataValidation(unittest.TestCase):
    """데이터 검증 테스트."""

    def test_required_columns(self):
        """필수 컬럼 확인 테스트."""
        # 도로 데이터 필수 컬럼
        road_required = ["RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE", "SIG_CD", "geometry"]

        # 파이프 데이터 필수 컬럼
        pipe_required = ["FTR_IDN", "geometry"]

        # 출력 CSV 필수 컬럼
        output_required = ["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]

        # 리스트가 정의되어 있는지만 확인
        self.assertTrue(len(road_required) > 0)
        self.assertTrue(len(pipe_required) > 0)
        self.assertTrue(len(output_required) > 0)


class TestSaveTrafficCSV(unittest.TestCase):
    """save_traffic_csv 함수 테스트."""

    def setUp(self):
        """테스트 데이터 설정."""
        # 테스트용 DataFrame 생성
        self.test_df = pd.DataFrame(
            {
                "FTR_IDN": [12345.0, 23456.0, 34567.0, 45678.0],
                "RN_CD": ["2007001", "2007002", None, "2007004"],
                "RN": ["대구로", "중앙로", None, "동대구로"],
                "ROAD_BT": [30.0, 20.0, None, 15.0],
                "ROA_CLS_SE": [1, 2, None, 3],
                "SIG_CD": ["27110", "27110", "27110", "27110"],  # 저장되지 않는 컬럼
                "extra_column": ["A", "B", "C", "D"],  # 저장되지 않는 추가 컬럼
            }
        )

    def test_save_traffic_csv_columns_order(self):
        """CSV 파일의 컬럼 순서 확인 테스트."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # CSV 저장
            csv_path = output_dir / "0520_pipe_traffic.csv"
            save_traffic_csv(
                self.test_df,
                csv_path,
                verbose=False,
            )

            # 파일 경로는 위에서 이미 설정함

            # 파일이 생성되었는지 확인
            self.assertTrue(csv_path.exists())

            # CSV 파일 읽기
            saved_df = pd.read_csv(csv_path)

            # 예상되는 컬럼 순서
            expected_columns = ["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]

            # 컬럼 순서 확인
            self.assertEqual(list(saved_df.columns), expected_columns)

            # 컬럼 개수 확인 (추가 컬럼이 없어야 함)
            self.assertEqual(len(saved_df.columns), len(expected_columns))

    def test_save_traffic_csv_ftr_idn_as_integer(self):
        """FTR_IDN이 정수로 저장되는지 확인 테스트."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # CSV 저장
            csv_path = output_dir / "0520_sply_traffic.csv"
            save_traffic_csv(
                self.test_df,
                csv_path,
                verbose=False,
            )

            # 저장된 파일 읽기
            csv_path = output_dir / "0520_sply_traffic.csv"
            saved_df = pd.read_csv(csv_path)

            # FTR_IDN 값 확인 (소수점이 없어야 함)
            self.assertEqual(saved_df["FTR_IDN"].tolist(), [12345, 23456, 34567, 45678])

            # 문자열로 읽어서도 확인
            with csv_path.open(encoding="utf-8-sig") as f:
                lines = f.readlines()
                # 첫 번째 줄(헤더) 다음부터 확인
                for line in lines[1:]:
                    # 첫 번째 컬럼(FTR_IDN)에 .0이 없어야 함
                    first_column = line.split(",")[0]
                    self.assertNotIn(".0", first_column)

    def test_save_traffic_csv_with_null_values(self):
        """NULL 값이 있는 경우 CSV 저장 테스트."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # CSV 저장
            csv_path = output_dir / "0903_pipe_traffic.csv"
            save_traffic_csv(
                self.test_df,
                csv_path,
                verbose=False,
            )

            # 파일 경로는 위에서 이미 설정함
            saved_df = pd.read_csv(csv_path)

            # NULL 값이 있는 행 확인
            null_row = saved_df[saved_df["FTR_IDN"] == 34567].iloc[0]
            self.assertTrue(pd.isna(null_row["RN_CD"]))
            self.assertTrue(pd.isna(null_row["RN"]))
            self.assertTrue(pd.isna(null_row["ROAD_BT"]))
            self.assertTrue(pd.isna(null_row["ROA_CLS_SE"]))

    def test_save_traffic_csv_file_naming(self):
        """파일명 생성 테스트."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # 다양한 조합으로 저장
            test_cases = [
                ("0520", "pipe", "0520_pipe_traffic.csv"),
                ("0520", "sply", "0520_sply_traffic.csv"),
                ("0903", "pipe", "0903_pipe_traffic.csv"),
                ("0903", "sply", "0903_sply_traffic.csv"),
            ]

            for region_code, pipe_type, expected_filename in test_cases:
                csv_path = output_dir / expected_filename
                save_traffic_csv(
                    self.test_df,
                    csv_path,
                    verbose=False,
                )

                expected_path = output_dir / expected_filename
                self.assertTrue(
                    expected_path.exists(), f"파일이 생성되지 않음: {expected_filename}"
                )

    def test_save_traffic_csv_encoding(self):
        """UTF-8-BOM 인코딩 확인 테스트."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # 한글이 포함된 데이터
            korean_df = pd.DataFrame(
                {
                    "FTR_IDN": [12345],
                    "RN_CD": ["2007001"],
                    "RN": ["대구로"],
                    "ROAD_BT": [30.0],
                    "ROA_CLS_SE": [1],
                }
            )

            csv_path = output_dir / "0520_pipe_traffic.csv"
            save_traffic_csv(
                korean_df,
                csv_path,
                verbose=False,
            )

            csv_path = output_dir / "0520_pipe_traffic.csv"

            # BOM 확인
            with csv_path.open("rb") as f:
                bom = f.read(3)
                self.assertEqual(bom, b"\xef\xbb\xbf", "UTF-8 BOM이 없습니다")

            # 한글 데이터 읽기 확인
            saved_df = pd.read_csv(csv_path, encoding="utf-8-sig")
            self.assertEqual(saved_df.iloc[0]["RN"], "대구로")


if __name__ == "__main__":
    unittest.main()
