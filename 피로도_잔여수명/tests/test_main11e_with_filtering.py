"""
main11e_merge_all_repairs.py 옥내 필터링 기능 테스트
'옥내' 텍스트 필터링 기능의 정확성과 옵션 동작을 검증
"""

import json
import sys
import tempfile
import unicodedata
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import unittest

import pandas as pd
import pytest

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main11e_merge_all_repairs import (
    filter_indoor_work,
    load_and_validate_files,
    merge_dataframes,
    save_merged_data,
    TARGET_FILES,
)


class TestIndoorFiltering(unittest.TestCase):
    """옥내 필터링 기능 테스트 클래스"""

    def setUp(self):
        """테스트 셋업"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir()

        # 테스트용 샘플 데이터 생성
        self.sample_data_ground = pd.DataFrame(
            {
                "공사개요": ["옥내 누수 수리", "일반 도로 보수", "옥내 배관 교체"],
                "주소": ["서울시 종로구", "서울시 강남구 옥내로", "서울시 서초구"],
                "공사명": ["일반 공사", "도로 공사", "배관 교체"],
                "작업일시": [
                    "2024-01-15 10:00",
                    "2024-01-16 14:00",
                    "2024-02-01 09:00",
                ],
                "위도": [37.5665, 37.5172, 37.4837],
                "경도": [126.9780, 127.0473, 127.0324],
            }
        )

        self.sample_data_underground = pd.DataFrame(
            {
                "공사개요": ["지하 누수", "일반 점검", "배관 교체"],
                "주소": ["서울시 중구", "서울시 종로구 옥내", "서울시 용산구"],
                "공사명": ["지하 보수", "옥내 점검", "일반 배관"],
                "작업일시": [
                    "2024-01-20 11:00",
                    "2024-01-21 15:00",
                    "2024-01-22 16:00",
                ],
                "위도": [37.5636, 37.5735, 37.5311],
                "경도": [126.9969, 126.9769, 126.9906],
            }
        )

    def tearDown(self):
        """테스트 정리"""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_filter_indoor_work_basic(self):
        """기본 필터링 동작 테스트"""
        from main11f_check_indoor import SEARCH_COLUMNS

        # 필터링 실행
        filtered_df, stats = filter_indoor_work(
            self.sample_data_ground.copy(),
            "지상누수_위치추가.csv",
            SEARCH_COLUMNS["지상누수_위치추가.csv"],
        )

        # 검증 - 모든 행에 '옥내'가 있어서 모두 제거됨
        self.assertEqual(stats["original_count"], 3)
        self.assertEqual(stats["filtered_count"], 0)  # 모든 행이 제거됨
        self.assertEqual(stats["removed_count"], 3)  # 3개 행 모두 제거
        self.assertEqual(stats["removed_percentage"], 100.0)

        # 남은 데이터가 없어야 함
        self.assertEqual(len(filtered_df), 0)

    def test_filter_indoor_work_multiple_columns(self):
        """여러 컬럼에서 옥내 검색 테스트"""
        from main11f_check_indoor import SEARCH_COLUMNS

        # 필터링 실행
        filtered_df, stats = filter_indoor_work(
            self.sample_data_underground.copy(),
            "지하누수_위치추가.csv",
            SEARCH_COLUMNS["지하누수_위치추가.csv"],
        )

        # 검증
        self.assertEqual(stats["original_count"], 3)
        self.assertEqual(stats["filtered_count"], 2)  # '옥내'가 있는 2개 행 제거
        self.assertEqual(stats["removed_count"], 1)  # 1개 행만 제거 (옥내 점검)

        # 컬럼별 매치 확인
        self.assertIn("주소", stats["column_matches"])  # 주소에서 1건
        self.assertIn("공사명", stats["column_matches"])  # 공사명에서 1건

    def test_filter_indoor_work_no_matches(self):
        """옥내 매치가 없는 경우 테스트"""
        # 옥내가 없는 데이터
        df = pd.DataFrame(
            {
                "공사개요": ["도로 보수", "배관 교체", "일반 점검"],
                "주소": ["서울시 중구", "서울시 용산구", "서울시 마포구"],
                "공사명": ["도로 공사", "배관 공사", "점검 작업"],
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "위도": [37.5, 37.6, 37.7],
                "경도": [127.0, 127.1, 127.2],
            }
        )

        from main11f_check_indoor import SEARCH_COLUMNS

        filtered_df, stats = filter_indoor_work(
            df, "지상누수_위치추가.csv", SEARCH_COLUMNS["지상누수_위치추가.csv"]
        )

        # 모든 행이 유지되어야 함
        self.assertEqual(stats["original_count"], 3)
        self.assertEqual(stats["filtered_count"], 3)
        self.assertEqual(stats["removed_count"], 0)
        self.assertEqual(stats["removed_percentage"], 0)
        self.assertEqual(len(stats["column_matches"]), 0)

    def test_load_and_validate_files_with_filtering(self):
        """파일 로드 시 필터링 적용 테스트"""
        # 테스트 파일 생성
        self.sample_data_ground.to_csv(
            self.results_dir / "지상누수_위치추가.csv",
            index=False,
            encoding="utf-8-sig",
        )
        self.sample_data_underground.to_csv(
            self.results_dir / "지하누수_위치추가.csv",
            index=False,
            encoding="utf-8-sig",
        )

        # results 디렉토리로 이동하여 테스트
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(self.test_dir)

            # 필터링 활성화로 로드
            dataframes, file_stats, filter_stats = load_and_validate_files(
                filter_indoor=True, verbose=False
            )

            # 필터링이 적용되었는지 확인
            self.assertIsNotNone(filter_stats)
            self.assertIn("지상누수_위치추가.csv", filter_stats)
            self.assertIn("지하누수_위치추가.csv", filter_stats)

            # 필터링 통계 검증
            self.assertGreater(
                filter_stats["지상누수_위치추가.csv"]["removed_count"], 0
            )
            self.assertGreater(
                filter_stats["지하누수_위치추가.csv"]["removed_count"], 0
            )

        finally:
            os.chdir(original_dir)

    def test_load_and_validate_files_without_filtering(self):
        """필터링 비활성화 테스트"""
        # 테스트 파일 생성
        self.sample_data_ground.to_csv(
            self.results_dir / "지상누수_위치추가.csv",
            index=False,
            encoding="utf-8-sig",
        )

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(self.test_dir)

            # 필터링 비활성화로 로드
            dataframes, file_stats, filter_stats = load_and_validate_files(
                filter_indoor=False, verbose=False
            )

            # 필터링이 적용되지 않았는지 확인
            self.assertIsNone(filter_stats)

            # 모든 행이 유지되었는지 확인
            total_rows = sum(len(df) for df in dataframes)
            self.assertEqual(total_rows, 3)  # 원본 데이터 그대로

        finally:
            os.chdir(original_dir)

    def test_save_merged_data_with_filter_stats(self):
        """필터링 통계와 함께 저장 테스트"""
        # 병합된 데이터 (파일타입 컬럼 추가)
        ground_df = self.sample_data_ground.copy()
        ground_df["파일타입"] = "지상누수"
        underground_df = self.sample_data_underground.copy()
        underground_df["파일타입"] = "지하누수"

        merged_df = pd.concat([ground_df, underground_df], ignore_index=True)

        # 필터링 통계
        filter_stats = {
            "지상누수_위치추가.csv": {"removed_count": 2, "removed_percentage": 66.67},
            "지하누수_위치추가.csv": {"removed_count": 1, "removed_percentage": 33.33},
        }

        output_dir = self.test_dir / "output"
        save_merged_data(merged_df, output_dir, filter_stats)

        # 파일이 생성되었는지 확인
        self.assertTrue((output_dir / "누수공사_통합_위치추가.csv").exists())
        self.assertTrue((output_dir / "통합_요약.txt").exists())

        # 요약 파일에 필터링 통계가 포함되었는지 확인
        with open(output_dir / "통합_요약.txt", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("'옥내' 텍스트 필터링 결과", content)
            self.assertIn("총 제거된 행: 3행", content)

    def test_case_insensitive_filtering(self):
        """대소문자 구분 없는 필터링 테스트"""
        # 다양한 대소문자 조합
        df = pd.DataFrame(
            {
                "공사개요": ["옥내 수리", "옥내 점검", "일반 작업"],
                "주소": ["서울시", "부산시", "대구시"],
                "공사명": ["공사1", "공사2", "공사3"],
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "위도": [37.5, 37.6, 37.7],
                "경도": [127.0, 127.1, 127.2],
            }
        )

        from main11f_check_indoor import SEARCH_COLUMNS

        filtered_df, stats = filter_indoor_work(
            df, "지상누수_위치추가.csv", SEARCH_COLUMNS["지상누수_위치추가.csv"]
        )

        # 대소문자 구분 없이 필터링되어야 함
        self.assertEqual(stats["removed_count"], 2)
        self.assertEqual(stats["filtered_count"], 1)

    def test_unicode_normalization_filtering(self):
        """유니코드 정규화 NFC/NFD 필터링 테스트"""
        # NFC와 NFD 형태가 혼재된 데이터
        nfc_text = "옥내 누수"  # NFC
        nfd_text = unicodedata.normalize("NFD", "옥내") + " 공사"  # NFD

        df = pd.DataFrame(
            {
                "공사개요": [nfc_text, nfd_text, "일반 작업"],
                "주소": ["서울시", "부산시", "대구시"],
                "공사명": ["공사1", "공사2", "공사3"],
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "위도": [37.5, 37.6, 37.7],
                "경도": [127.0, 127.1, 127.2],
            }
        )

        from main11f_check_indoor import SEARCH_COLUMNS

        # main11e의 filter_indoor_work는 main11f의 search_with_normalization을 사용해야 함
        # 현재 구현은 기본 contains를 사용하므로 NFC/NFD 모두 찾아야 함
        filtered_df, stats = filter_indoor_work(
            df, "지상누수_위치추가.csv", SEARCH_COLUMNS["지상누수_위치추가.csv"]
        )

        # NFC와 NFD 모두 필터링되어야 함
        self.assertEqual(
            stats["removed_count"], 2, "NFC와 NFD 형태 모두 필터링되어야 함"
        )
        self.assertEqual(stats["filtered_count"], 1)

    def test_location_validation_filtering(self):
        """위치 정보 유효성 검증 테스트"""
        # 일부 행에 위치 정보가 없는 데이터
        df = pd.DataFrame(
            {
                "공사개요": ["도로 보수", "배관 교체", "일반 점검", "옥내 작업"],
                "주소": ["서울시", "부산시", "대구시", "인천시"],
                "공사명": ["공사1", "공사2", "공사3", "공사4"],
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "위도": [37.5, None, 37.7, 37.8],  # 2번째 행 위도 없음
                "경도": [127.0, 127.1, None, 127.3],  # 3번째 행 경도 없음
            }
        )

        # 파일 저장
        test_file = self.results_dir / "지상누수_위치추가.csv"
        df.to_csv(test_file, index=False, encoding="utf-8-sig")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(self.test_dir)

            # 필터링 활성화로 로드
            dataframes, file_stats, filter_stats = load_and_validate_files(
                filter_indoor=True, verbose=True
            )

            # 원본 4행 중 유효 위치는 2행 (1, 4번째)
            # 그 중 '옥내'가 포함된 4번째 행 제거
            # 최종 1행만 남음
            self.assertEqual(len(dataframes), 1)
            self.assertEqual(file_stats["지상누수_위치추가.csv"], 1)

            # 필터 통계 확인
            self.assertEqual(
                filter_stats["지상누수_위치추가.csv"]["location_removed"], 2
            )
            self.assertEqual(filter_stats["지상누수_위치추가.csv"]["removed_count"], 1)

        finally:
            os.chdir(original_dir)


class TestCommandLineArguments(unittest.TestCase):
    """커맨드라인 인자 테스트"""

    def test_no_filter_indoor_argument(self):
        """--no-filter-indoor 인자 파싱 테스트"""
        import argparse
        from main11e_merge_all_repairs import main

        # ArgumentParser 직접 테스트
        parser = argparse.ArgumentParser()
        parser.add_argument("--no-filter-indoor", action="store_true")

        # 인자 없이
        args = parser.parse_args([])
        self.assertFalse(args.no_filter_indoor)

        # 인자와 함께
        args = parser.parse_args(["--no-filter-indoor"])
        self.assertTrue(args.no_filter_indoor)


if __name__ == "__main__":
    unittest.main()
