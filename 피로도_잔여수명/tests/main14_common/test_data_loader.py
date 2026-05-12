"""
main14_common/data_loader.py 테스트
데이터 로딩 공통 함수 모듈 테스트
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main14_common.data_loader import (
    load_fatigue_csv,
    load_pipe_shapefiles,
    load_repair_csv_files,
    load_unified_repair_csv,
)


class TestDataLoader(unittest.TestCase):
    """데이터 로더 함수 테스트"""

    def setUp(self):
        """테스트용 임시 디렉토리 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """임시 파일 정리"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("src.main14_common.data_loader.UNIFIED_REPAIR_CSV")
    def test_load_unified_repair_csv_success(self, mock_csv_path):
        """통합 재작업 CSV 파일 로드 성공 테스트"""
        # 테스트용 통합 CSV 파일 생성
        csv_file = self.temp_path / "test_unified.csv"
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "위도": [37.5, 37.4, 37.6, 37.3],
                "경도": [127.0, 127.1, 127.2, 127.3],
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
            }
        )
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        mock_csv_path.exists.return_value = True
        mock_csv_path.__str__ = lambda _: str(csv_file)

        # pd.read_csv를 패치하여 실제 파일을 읽도록
        with patch("src.main14_common.data_loader.pd.read_csv", return_value=df):
            result = load_unified_repair_csv()

        # 결과 확인
        self.assertEqual(len(result), 4)
        self.assertIn("작업타입", result.columns)
        self.assertEqual(
            result["작업타입"].tolist(),
            ["지상누수", "지하누수", "긴급공사", "관리대장"],
        )

    @patch("src.main14_common.data_loader.UNIFIED_REPAIR_CSV")
    def test_load_unified_repair_csv_with_columns(self, mock_csv_path):
        """통합 CSV 특정 컬럼만 선택 테스트"""
        # 테스트용 통합 CSV 파일 생성
        csv_file = self.temp_path / "test_unified.csv"
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [37.5, 37.4],
                "경도": [127.0, 127.1],
                "파일타입": ["지상누수", "지하누수"],
                "기타정보": ["A", "B"],
            }
        )
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        mock_csv_path.exists.return_value = True
        mock_csv_path.__str__ = lambda _: str(csv_file)

        with patch("src.main14_common.data_loader.pd.read_csv", return_value=df):
            result = load_unified_repair_csv(required_columns=["위도", "경도"])

        # 결과 확인
        self.assertIn("작업타입", result.columns)  # 작업타입은 자동 포함
        self.assertIn("위도", result.columns)
        self.assertIn("경도", result.columns)
        self.assertNotIn("기타정보", result.columns)

    @patch("src.main14_common.data_loader.UNIFIED_REPAIR_CSV")
    def test_load_unified_repair_csv_file_not_exists(self, mock_csv_path):
        """통합 CSV 파일이 없을 때 SystemExit 테스트"""
        mock_csv_path.exists.return_value = False

        with self.assertRaises(SystemExit):
            load_unified_repair_csv()

    @patch("src.main14_common.data_loader.UNIFIED_REPAIR_CSV")
    def test_load_repair_csv_files_with_unified_csv(self, mock_csv_path):
        """통합 CSV가 있을 때 우선 사용 테스트"""
        # 통합 CSV 파일이 존재한다고 설정
        mock_csv_path.exists.return_value = True

        # load_unified_repair_csv를 모킹
        with patch(
            "src.main14_common.data_loader.load_unified_repair_csv"
        ) as mock_load_unified:
            mock_load_unified.return_value = pd.DataFrame(
                {
                    "작업타입": ["지상누수", "지하누수"],
                    "위도": [37.5, 37.6],
                    "경도": [127.0, 127.1],
                }
            )

            result = load_repair_csv_files(["위도", "경도"])

            # load_unified_repair_csv가 호출되었는지 확인
            mock_load_unified.assert_called_once_with(["위도", "경도"])
            self.assertEqual(len(result), 2)
            self.assertIn("작업타입", result.columns)

    @patch("src.main14_common.data_loader.UNIFIED_REPAIR_CSV")
    def test_load_repair_csv_files_missing(self, mock_csv_path):
        """통합 CSV 파일이 없을 때 SystemExit 발생 테스트"""
        # 통합 CSV 파일이 없다고 설정
        mock_csv_path.exists.return_value = False

        with self.assertRaises(SystemExit) as cm:
            load_repair_csv_files()

        self.assertEqual(cm.exception.code, 1)

    def test_load_fatigue_csv_success(self):
        """피로 손상 CSV 파일 로드 성공 테스트"""
        # 테스트용 CSV 파일 생성
        df_pipe = pd.DataFrame(
            {
                "FTR_IDN": [1, 2],
                "K_age": [1.5, 1.6],
                "K_soil": [1.1, 1.2],
                "K_repair": [1.0, 1.1],
            }
        )
        df_sply = pd.DataFrame(
            {
                "FTR_IDN": [3, 4],
                "K_age": [1.7, 1.8],
                "K_soil": [1.3, 1.4],
                "K_repair": [1.2, 1.3],
            }
        )

        pipe_csv = self.temp_path / "pipe_lm.csv"
        sply_csv = self.temp_path / "sply_ls.csv"
        df_pipe.to_csv(pipe_csv, index=False)
        df_sply.to_csv(sply_csv, index=False)

        # 함수 실행
        result_pipe, result_sply, has_k_repair = load_fatigue_csv(pipe_csv, sply_csv)

        # 검증
        self.assertIsInstance(result_pipe, pd.DataFrame)
        self.assertIsInstance(result_sply, pd.DataFrame)
        self.assertEqual(len(result_pipe), 2)
        self.assertEqual(len(result_sply), 2)
        self.assertTrue(has_k_repair)

    def test_load_fatigue_csv_without_k_repair(self):
        """K_repair 컬럼이 없는 CSV 파일 로드 테스트"""
        # K_repair 없는 CSV 파일 생성
        df_pipe = pd.DataFrame(
            {"FTR_IDN": [1, 2], "K_age": [1.5, 1.6], "K_soil": [1.1, 1.2]}
        )
        df_sply = pd.DataFrame(
            {"FTR_IDN": [3, 4], "K_age": [1.7, 1.8], "K_soil": [1.3, 1.4]}
        )

        pipe_csv = self.temp_path / "pipe_lm.csv"
        sply_csv = self.temp_path / "sply_ls.csv"
        df_pipe.to_csv(pipe_csv, index=False)
        df_sply.to_csv(sply_csv, index=False)

        # 함수 실행
        _, _, has_k_repair = load_fatigue_csv(pipe_csv, sply_csv)

        # 검증
        self.assertFalse(has_k_repair)

    def test_load_fatigue_csv_missing_files(self):
        """피로 손상 CSV 파일이 없을 때 SystemExit 발생 테스트"""
        pipe_csv = self.temp_path / "없는파일1.csv"
        sply_csv = self.temp_path / "없는파일2.csv"

        with self.assertRaises(SystemExit) as cm:
            load_fatigue_csv(pipe_csv, sply_csv)

        self.assertEqual(cm.exception.code, 1)

    @patch("geopandas.read_file")
    def test_load_pipe_shapefiles_success(self, mock_read_file):
        """파이프 Shapefile 로드 성공 테스트"""
        # Mock GeoDataFrame 생성
        mock_pipe_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_pipe_gdf.__len__ = MagicMock(return_value=100)
        mock_sply_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_sply_gdf.__len__ = MagicMock(return_value=200)

        mock_read_file.side_effect = [mock_pipe_gdf, mock_sply_gdf]

        # 테스트용 경로 (실제로는 존재하지 않아도 됨)
        pipe_shp = Path("/fake/path/pipe.shp")
        sply_shp = Path("/fake/path/sply.shp")

        # 파일 존재 여부를 모킹
        with patch.object(Path, "exists", return_value=True):
            result_pipe, result_sply = load_pipe_shapefiles(pipe_shp, sply_shp)

        # 검증
        self.assertEqual(result_pipe, mock_pipe_gdf)
        self.assertEqual(result_sply, mock_sply_gdf)
        self.assertEqual(mock_read_file.call_count, 2)

    def test_load_pipe_shapefiles_missing(self):
        """Shapefile이 없을 때 SystemExit 발생 테스트"""
        pipe_shp = self.temp_path / "없는파일.shp"
        sply_shp = self.temp_path / "없는파일2.shp"

        with self.assertRaises(SystemExit) as cm:
            load_pipe_shapefiles(pipe_shp, sply_shp)

        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
