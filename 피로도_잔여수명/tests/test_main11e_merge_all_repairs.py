"""
main11e_merge_all_repairs.py 테스트
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open, call
from pathlib import Path
import pandas as pd
import numpy as np
import tempfile
import shutil
import sys
from io import StringIO

# 테스트 대상 모듈 import
from src.main11e_merge_all_repairs import (
    load_and_validate_files,
    merge_dataframes,
    analyze_data_quality,
    save_merged_data,
    TARGET_FILES,
    ID_COLUMN_MAPPING,
)


class TestTargetFiles(unittest.TestCase):
    """TARGET_FILES 상수 테스트"""

    def test_target_files_defined(self):
        """TARGET_FILES가 정의되어 있는지 확인"""
        self.assertIsNotNone(TARGET_FILES)
        self.assertIsInstance(TARGET_FILES, list)
        self.assertEqual(len(TARGET_FILES), 4)  # 기타공사가 주석 처리되어 4개

    def test_target_files_content(self):
        """TARGET_FILES 내용 확인"""
        expected_files = [
            "지상누수_위치추가.csv",
            "지하누수_위치추가.csv",
            # "기타공사_위치추가.csv",  # 현재 주석 처리됨
            "긴급공사_위치추가.csv",
            "관리대장_위치추가.csv",
        ]
        self.assertEqual(TARGET_FILES, expected_files)
    
    def test_id_column_mapping_defined(self):
        """ID_COLUMN_MAPPING이 정의되어 있는지 확인"""
        self.assertIsNotNone(ID_COLUMN_MAPPING)
        self.assertIsInstance(ID_COLUMN_MAPPING, dict)
        self.assertEqual(len(ID_COLUMN_MAPPING), 4)  # 4개 파일의 ID 매핑
        
    def test_id_column_mapping_content(self):
        """ID_COLUMN_MAPPING 내용 확인"""
        expected_mapping = {
            "지상누수_위치추가.csv": "긴급복구공사일련번호",
            "지하누수_위치추가.csv": "긴급복구공사일련번호",
            "긴급공사_위치추가.csv": "접수번호",
            "관리대장_위치추가.csv": "접수번호",
        }
        self.assertEqual(ID_COLUMN_MAPPING, expected_mapping)


class TestLoadAndValidateFiles(unittest.TestCase):
    """파일 로드 및 검증 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir()

    def tearDown(self):
        """테스트 환경 정리"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_missing_results_directory(self):
        """results 디렉토리가 없는 경우"""
        with patch("src.main11e_merge_all_repairs.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            with self.assertRaises(FileNotFoundError) as context:
                load_and_validate_files()

            self.assertIn("디렉토리를 찾을 수 없습니다", str(context.exception))

    @patch("src.main11e_merge_all_repairs.pd.read_csv")
    @patch("src.main11e_merge_all_repairs.Path")
    def test_missing_required_columns(self, mock_path_class, mock_read_csv):
        """필수 컬럼이 누락된 경우"""
        # Mock 설정
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True
        mock_path_class.return_value = mock_results_dir

        # 파일 경로 mock
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_results_dir.__truediv__ = MagicMock(return_value=mock_file)

        # 필수 컬럼이 없는 DataFrame
        df = pd.DataFrame({"주소": ["주소1", "주소2"], "공사명": ["공사1", "공사2"]})
        mock_read_csv.return_value = df

        # TARGET_FILES mock
        with patch(
            "src.main11e_merge_all_repairs.TARGET_FILES", ["지상누수_위치추가.csv"]
        ):
            with self.assertRaises(ValueError) as context:
                load_and_validate_files()

            error_msg = str(context.exception)
            self.assertIn("필수 컬럼 누락", error_msg)

    @patch("src.main11e_merge_all_repairs.pd.read_csv")
    @patch("src.main11e_merge_all_repairs.Path")
    def test_valid_files_loading(self, mock_path_class, mock_read_csv):
        """유효한 파일 로드"""
        # Mock 설정
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True
        mock_path_class.return_value = mock_results_dir

        # 파일 경로 mocks
        mock_file1 = MagicMock()
        mock_file1.exists.return_value = True
        mock_file2 = MagicMock()
        mock_file2.exists.return_value = True

        def truediv_side_effect(other):
            if "지상누수" in str(other):
                return mock_file1
            elif "지하누수" in str(other):
                return mock_file2
            return MagicMock()

        mock_results_dir.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        # DataFrame 설정
        df1 = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [35.8, 35.9],
                "경도": [128.5, 128.6],
                "주소": ["주소1", "주소2"],
            }
        )
        df2 = pd.DataFrame(
            {
                "작업일시": ["2024-01-03", "2024-01-04"],
                "위도": [35.7, 35.6],
                "경도": [128.4, 128.3],
                "주소": ["주소3", "주소4"],
            }
        )
        mock_read_csv.side_effect = [df1, df2]

        with patch(
            "src.main11e_merge_all_repairs.TARGET_FILES",
            ["지상누수_위치추가.csv", "지하누수_위치추가.csv"],
        ):
            dataframes, file_stats, filter_stats = load_and_validate_files()

            self.assertEqual(len(dataframes), 2)
            self.assertEqual(sum(file_stats.values()), 4)  # 각 파일 2행씩

    @patch("src.main11e_merge_all_repairs.pd.read_csv")
    @patch("src.main11e_merge_all_repairs.Path")
    def test_file_type_column_added(self, mock_path_class, mock_read_csv):
        """파일타입 컬럼 추가 확인"""
        # Mock 설정
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True
        mock_path_class.return_value = mock_results_dir

        # 파일 경로 mock
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_results_dir.__truediv__ = MagicMock(return_value=mock_file)

        # DataFrame 설정
        df = pd.DataFrame({"작업일시": ["2024-01-01"], "위도": [35.8], "경도": [128.5]})
        mock_read_csv.return_value = df

        with patch(
            "src.main11e_merge_all_repairs.TARGET_FILES", ["지상누수_위치추가.csv"]
        ):
            dataframes, _, _ = load_and_validate_files()

            self.assertEqual(len(dataframes), 1)
            self.assertIn("파일타입", dataframes[0].columns)
            self.assertEqual(dataframes[0]["파일타입"].iloc[0], "지상누수")
            self.assertNotIn(
                "원본파일", dataframes[0].columns
            )  # 원본파일 컬럼은 없어야 함

    @patch("src.main11e_merge_all_repairs.pd.read_csv")
    @patch("src.main11e_merge_all_repairs.Path")
    def test_id_column_added(self, mock_path_class, mock_read_csv):
        """ID 컬럼 추가 확인"""
        # Mock 설정
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True
        mock_path_class.return_value = mock_results_dir

        # 파일 경로 mock
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_results_dir.__truediv__ = MagicMock(return_value=mock_file)

        # DataFrame 설정 - ID 컬럼 포함
        df = pd.DataFrame({
            "작업일시": ["2024-01-01"], 
            "위도": [35.8], 
            "경도": [128.5],
            "긴급복구공사일련번호": ["202002836"]
        })
        mock_read_csv.return_value = df

        with patch(
            "src.main11e_merge_all_repairs.TARGET_FILES", ["지상누수_위치추가.csv"]
        ):
            dataframes, _, _ = load_and_validate_files()

            self.assertEqual(len(dataframes), 1)
            self.assertIn("ID", dataframes[0].columns)
            self.assertEqual(dataframes[0]["ID"].iloc[0], "202002836")


class TestMergeDataframes(unittest.TestCase):
    """DataFrame 병합 테스트"""

    def test_merge_single_dataframe(self):
        """단일 DataFrame 병합"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01"],
                "위도": [35.8],
                "경도": [128.5],
                "파일타입": ["지상누수"],
            }
        )

        merged = merge_dataframes([df])
        self.assertEqual(len(merged), 1)
        self.assertEqual(list(merged.columns), list(df.columns))

    def test_merge_multiple_dataframes(self):
        """여러 DataFrame 병합"""
        df1 = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [35.8, 35.9],
                "경도": [128.5, 128.6],
                "파일타입": ["지상누수", "지상누수"],
            }
        )

        df2 = pd.DataFrame(
            {
                "작업일시": ["2024-01-03"],
                "위도": [35.7],
                "경도": [128.4],
                "파일타입": ["지하누수"],
            }
        )

        merged = merge_dataframes([df1, df2])
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged["파일타입"].value_counts()["지상누수"], 2)
        self.assertEqual(merged["파일타입"].value_counts()["지하누수"], 1)

    def test_preserve_all_columns(self):
        """모든 컬럼 보존 확인"""
        df1 = pd.DataFrame(
            {
                "작업일시": ["2024-01-01"],
                "위도": [35.8],
                "경도": [128.5],
                "파일타입": ["지상누수"],
                "추가컬럼1": ["값1"],
            }
        )

        df2 = pd.DataFrame(
            {
                "작업일시": ["2024-01-02"],
                "위도": [35.9],
                "경도": [128.6],
                "파일타입": ["지하누수"],
                "추가컬럼2": ["값2"],
            }
        )

        merged = merge_dataframes([df1, df2])
        self.assertIn("추가컬럼1", merged.columns)
        self.assertIn("추가컬럼2", merged.columns)


class TestAnalyzeDataQuality(unittest.TestCase):
    """데이터 품질 분석 테스트"""

    def test_no_missing_values(self):
        """결측값이 없는 경우"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [35.8, 35.9],
                "경도": [128.5, 128.6],
                "파일타입": ["지상누수", "지상누수"],
            }
        )

        # 출력 캡처
        with patch("sys.stdout", new=StringIO()):
            analyze_data_quality(df)
            # 함수가 오류 없이 실행되는지만 확인

    def test_with_missing_values(self):
        """결측값이 있는 경우"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", None],
                "위도": [35.8, np.nan],
                "경도": [128.5, 128.6],
                "파일타입": ["지상누수", "지상누수"],
            }
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            analyze_data_quality(df)
            output = mock_stdout.getvalue()
            self.assertIn("결측", output)

    def test_invalid_coordinates(self):
        """유효하지 않은 좌표"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [35.8, 100],  # 100은 한국 범위 밖
                "경도": [128.5, 128.6],
                "파일타입": ["지상누수", "지상누수"],
            }
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            analyze_data_quality(df)
            output = mock_stdout.getvalue()
            self.assertIn("유효하지 않은 좌표", output)

    def test_duplicate_rows(self):
        """중복 행이 있는 경우"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01"],
                "위도": [35.8, 35.8],
                "경도": [128.5, 128.5],
                "파일타입": ["지상누수", "지상누수"],
            }
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            analyze_data_quality(df)
            output = mock_stdout.getvalue()
            self.assertIn("완전 중복 행", output)


class TestSaveMergedData(unittest.TestCase):
    """데이터 저장 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """테스트 환경 정리"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_csv_file(self):
        """CSV 파일 저장"""
        df = pd.DataFrame(
            {
                "ID": ["202002836", "201203297"],
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [35.8, 35.9],
                "경도": [128.5, 128.6],
                "파일타입": ["지상누수", "지하누수"],
                "공사명": ["공사1", "공사2"],  # 저장되어야 함
                "구군": ["서울시", "부산시"],  # 저장되어야 함
                "주소": ["주소1", "주소2"],  # 저장되어야 함
                "불필요한컬럼": ["데이터1", "데이터2"],  # 이 컬럼은 저장되지 않아야 함
            }
        )

        output_dir = self.test_dir / "output"
        save_merged_data(df, str(output_dir))

        # 파일 존재 확인
        csv_file = output_dir / "누수공사_통합_위치추가.csv"
        self.assertTrue(csv_file.exists())

        # 저장된 데이터 확인
        saved_df = pd.read_csv(csv_file, encoding="utf-8-sig")
        self.assertEqual(len(saved_df), 2)
        self.assertIn("ID", saved_df.columns)
        self.assertEqual(saved_df.columns[0], "ID")  # ID가 첫 번째 컬럼
        self.assertIn("파일타입", saved_df.columns)
        self.assertIn("작업일시", saved_df.columns)
        self.assertIn("위도", saved_df.columns)
        self.assertIn("경도", saved_df.columns)
        self.assertIn("공사명", saved_df.columns)  # 추가 컬럼 확인
        self.assertIn("구군", saved_df.columns)  # 추가 컬럼 확인
        self.assertIn("주소", saved_df.columns)  # 추가 컬럼 확인
        self.assertNotIn("원본파일", saved_df.columns)  # 원본파일 컬럼은 제외
        self.assertNotIn(
            "불필요한컬럼", saved_df.columns
        )  # 불필요한 컬럼은 제외되어야 함
        # 실제 존재하는 컬럼 개수 확인 (ID, 작업일시, 위도, 경도, 파일타입, 공사명, 구군, 주소)
        self.assertEqual(len(saved_df.columns), 8)

    def test_save_csv_file_with_all_columns(self):
        """모든 지원 컬럼이 있을 때 CSV 파일 저장"""
        df = pd.DataFrame(
            {
                "ID": ["202002836"],
                "작업일시": ["2024-01-01"],
                "위도": [35.8],
                "경도": [128.5],
                "파일타입": ["지상누수"],
                "공사명": ["공사1"],
                "공사개요": ["개요1"],
                "구군": ["서울시"],
                "주소": ["주소1"],
                "중구역번호": ["M001"],
                "소구역번호": ["S001"],
                "도로구분": ["일반도로"],
                "누수관경": ["200"],
                "누수량": ["10.5"],
                "용수구분": ["생활용수"],
                "용도구분": ["주거용"],
                "불필요한컬럼": ["데이터1"],  # 이 컬럼은 저장되지 않아야 함
            }
        )

        output_dir = self.test_dir / "output2"
        save_merged_data(df, str(output_dir))

        # 파일 존재 확인
        csv_file = output_dir / "누수공사_통합_위치추가.csv"
        self.assertTrue(csv_file.exists())

        # 저장된 데이터 확인
        saved_df = pd.read_csv(csv_file, encoding="utf-8-sig")
        self.assertEqual(len(saved_df), 1)
        # 모든 지정된 컬럼이 포함되어 있는지 확인
        expected_columns = [
            "ID", "작업일시", "위도", "경도", "파일타입",
            "공사명", "공사개요", "구군", "주소",
            "중구역번호", "소구역번호", "도로구분", "누수관경",
            "누수량", "용수구분", "용도구분"
        ]
        for col in expected_columns:
            self.assertIn(col, saved_df.columns)
        self.assertNotIn("불필요한컬럼", saved_df.columns)
        self.assertEqual(len(saved_df.columns), 16)  # 모든 지정된 컬럼

    def test_save_summary_file(self):
        """요약 파일 저장"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "위도": [35.8, 35.9, 35.7],
                "경도": [128.5, 128.6, 128.4],
                "파일타입": ["지상누수", "지상누수", "지하누수"],
                "공사명": ["공사1", "공사2", "공사3"],
                "구군": ["서울시", "부산시", "대구시"],
            }
        )

        output_dir = self.test_dir / "output"
        save_merged_data(df, str(output_dir))

        # 요약 파일 존재 확인
        summary_file = output_dir / "통합_요약.txt"
        self.assertTrue(summary_file.exists())

        # 요약 내용 확인
        with open(summary_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("누수공사 데이터 통합 요약", content)
            self.assertIn("총 레코드 수: 3행", content)
            self.assertIn("지상누수: 2행", content)
            self.assertIn("지하누수: 1행", content)
            self.assertIn("컬럼 목록:", content)  # 컬럼 목록이 포함되어야 함

    def test_create_output_directory(self):
        """출력 디렉토리 자동 생성"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01"],
                "위도": [35.8],
                "경도": [128.5],
                "파일타입": ["지상누수"],
            }
        )

        output_dir = self.test_dir / "nested" / "output"
        self.assertFalse(output_dir.exists())

        save_merged_data(df, str(output_dir))

        self.assertTrue(output_dir.exists())
        self.assertTrue((output_dir / "누수공사_통합_위치추가.csv").exists())


class TestIntegration(unittest.TestCase):
    """통합 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir()

    def tearDown(self):
        """테스트 환경 정리"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch("src.main11e_merge_all_repairs.pd.read_csv")
    @patch("src.main11e_merge_all_repairs.Path")
    @patch("src.main11e_merge_all_repairs.pd.DataFrame.to_csv")
    def test_end_to_end_workflow(self, mock_to_csv, mock_path_class, mock_read_csv):
        """전체 워크플로우 테스트"""
        # Mock 디렉토리 설정
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True
        mock_path_class.return_value = mock_results_dir

        # 파일 경로 mocks
        mock_file1 = MagicMock()
        mock_file1.exists.return_value = True
        mock_file2 = MagicMock()
        mock_file2.exists.return_value = True

        def truediv_side_effect(other):
            if "지상누수" in str(other):
                return mock_file1
            elif "지하누수" in str(other):
                return mock_file2
            elif "output" in str(other):
                output_dir = MagicMock()
                output_dir.mkdir = MagicMock()
                output_dir.__truediv__ = MagicMock()
                return output_dir
            return MagicMock()

        mock_results_dir.__truediv__ = MagicMock(side_effect=truediv_side_effect)

        # 테스트 데이터
        df1 = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [35.8, 35.9],
                "경도": [128.5, 128.6],
                "주소": ["주소1", "주소2"],
            }
        )
        df2 = pd.DataFrame(
            {
                "작업일시": ["2024-01-03"],
                "위도": [35.7],
                "경도": [128.4],
                "주소": ["주소3"],
            }
        )

        mock_read_csv.side_effect = [df1, df2]

        with patch(
            "src.main11e_merge_all_repairs.TARGET_FILES",
            ["지상누수_위치추가.csv", "지하누수_위치추가.csv"],
        ):
            # 파일 로드
            dataframes, file_stats, filter_stats = load_and_validate_files()
            self.assertEqual(len(dataframes), 2)

            # 병합
            merged = merge_dataframes(dataframes)
            self.assertEqual(len(merged), 3)

            # 저장 (mocked)
            with patch("builtins.open", create=True) as mock_open:
                save_merged_data(merged, "output")
                # to_csv 호출 확인
                mock_to_csv.assert_called()
                # 요약 파일 작성 확인
                mock_open.assert_called()


class TestErrorHandling(unittest.TestCase):
    """오류 처리 테스트"""

    def test_no_valid_files(self):
        """유효한 파일이 없는 경우"""
        with patch("src.main11e_merge_all_repairs.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            # 모든 파일이 존재하지 않는 것으로 설정
            mock_path.return_value.__truediv__.return_value.exists.return_value = False

            with self.assertRaises(ValueError) as context:
                load_and_validate_files()

            self.assertIn("병합할 유효한 파일이 없습니다", str(context.exception))

    @patch("src.main11e_merge_all_repairs.pd.read_csv")
    @patch("src.main11e_merge_all_repairs.Path")
    def test_csv_encoding_error(self, mock_path_class, mock_read_csv):
        """CSV 인코딩 오류"""
        # Mock 설정
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True
        mock_path_class.return_value = mock_results_dir

        # 파일 경로 mock
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_results_dir.__truediv__ = MagicMock(return_value=mock_file)

        # CSV 읽기 시 예외 발생
        mock_read_csv.side_effect = UnicodeDecodeError(
            "utf-8", b"", 0, 1, "invalid start byte"
        )

        with patch(
            "src.main11e_merge_all_repairs.TARGET_FILES", ["지상누수_위치추가.csv"]
        ):
            # 함수 호출 시 예외 발생 않음 (오류를 캐치하고 계속 진행)
            # 하지만 유효한 파일이 없으므로 ValueError 발생
            with self.assertRaises(ValueError) as context:
                load_and_validate_files()
            self.assertIn("병합할 유효한 파일이 없습니다", str(context.exception))


class TestMainFunction(unittest.TestCase):
    """main 함수 테스트"""

    @patch("src.main11e_merge_all_repairs.save_merged_data")
    @patch("src.main11e_merge_all_repairs.analyze_data_quality")
    @patch("src.main11e_merge_all_repairs.merge_dataframes")
    @patch("src.main11e_merge_all_repairs.load_and_validate_files")
    def test_main_success(self, mock_load, mock_merge, mock_analyze, mock_save):
        """main 함수 정상 실행"""
        # Mock 설정 - 3개의 반환값
        mock_load.return_value = ([MagicMock()], {"file1.csv": 10}, {})
        mock_merge.return_value = MagicMock()

        # main 함수 실행
        with patch("sys.argv", ["main11e_merge_all_repairs.py"]):
            from src.main11e_merge_all_repairs import main

            try:
                main()
            except SystemExit as e:
                # 성공적으로 종료된 경우 (exit code 0)
                if e.code != 0:
                    raise

            # 함수 호출 확인
            mock_load.assert_called_once()
            mock_merge.assert_called_once()
            mock_analyze.assert_called_once()
            mock_save.assert_called_once()

    @patch("src.main11e_merge_all_repairs.load_and_validate_files")
    def test_main_with_error(self, mock_load):
        """main 함수 오류 처리"""
        mock_load.side_effect = ValueError("테스트 오류")

        with patch("sys.argv", ["main11e_merge_all_repairs.py"]):
            from src.main11e_merge_all_repairs import main

            with self.assertRaises(SystemExit) as context:
                main()

            self.assertEqual(context.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
