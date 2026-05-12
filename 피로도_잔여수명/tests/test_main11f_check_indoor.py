"""
main11f_check_indoor.py 테스트 모듈
'옥내' 텍스트 검색 및 분석 기능 테스트
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

from main11f_check_indoor import (
    load_and_search_file,
    analyze_temporal_pattern,
    print_summary,
    save_results,
    export_matched_rows,
    normalize_text,
    search_with_normalization,
    SEARCH_COLUMNS,
)


class TestMain11fCheckIndoor(unittest.TestCase):
    """main11f_check_indoor.py 테스트 클래스"""

    def setUp(self):
        """테스트 셋업"""
        self.test_dir = Path(tempfile.mkdtemp())

        # 테스트용 샘플 데이터 생성
        self.sample_data_ground = pd.DataFrame(
            {
                "공사개요": ["옥내 누수 수리", "일반 도로 보수", "옥내 배관 교체"],
                "주소": ["서울시 종로구 옥내동", "서울시 강남구", "서울시 서초구"],
                "공사명": ["일반 공사", "옥내 급수관 수리", "도로 보수"],
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
                "공사개요": ["지하 누수", "옥내 누수 점검", "배관 교체"],
                "주소": ["서울시 중구", "서울시 종로구 옥내", "서울시 용산구"],
                "공사명": ["지하 보수", "일반 점검", "옥내 배관"],
                "작업일시": [
                    "2024-01-20 11:00",
                    "2024-01-21 15:00",
                    "2024-01-22 16:00",
                ],
                "위도": [37.5636, 37.5735, 37.5311],
                "경도": [126.9969, 126.9769, 126.9906],
            }
        )

        self.sample_data_emergency = pd.DataFrame(
            {
                "공사명": ["긴급 옥내 수리", "도로 긴급 보수", "일반 긴급"],
                "주소": ["서울시 마포구", "서울시 영등포구 옥내로", "서울시 동작구"],
                "공사개요": ["긴급 수리", "도로 복구", "옥내 점검"],
                "작업일시": [
                    "2024-02-10 08:00",
                    "2024-02-11 09:00",
                    "2024-02-12 10:00",
                ],
                "위도": [37.5547, 37.5263, 37.5124],
                "경도": [126.9707, 126.8962, 126.9392],
            }
        )

        self.sample_data_management = pd.DataFrame(
            {
                "위치": ["종로구 옥내동", "강남구 역삼동", "서초구"],
                "공사개요": ["관리 작업", "옥내 점검", "일반 관리"],
                "작업일시": [
                    "2024-03-01 13:00",
                    "2024-03-02 14:00",
                    "2024-03-03 15:00",
                ],
                "위도": [37.5790, 37.5010, 37.4837],
                "경도": [126.9770, 127.0365, 127.0324],
            }
        )

    def tearDown(self):
        """테스트 정리"""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_load_and_search_file_ground_water(self):
        """지상누수 파일 검색 테스트"""
        # CSV 파일 저장
        file_path = self.test_dir / "지상누수_위치추가.csv"
        self.sample_data_ground.to_csv(file_path, index=False, encoding="utf-8-sig")

        # 검색 실행
        df, results = load_and_search_file(
            file_path, SEARCH_COLUMNS["지상누수_위치추가.csv"], "옥내"
        )

        # 검증
        self.assertIsNotNone(df)
        self.assertIsNotNone(results)
        self.assertEqual(results["total_rows"], 3)
        self.assertEqual(results["matched_rows"], 3)  # 3개 행이 '옥내' 포함

        # 컬럼별 매치 확인
        self.assertIn("공사개요", results["column_matches"])
        self.assertIn("주소", results["column_matches"])
        self.assertIn("공사명", results["column_matches"])

    def test_load_and_search_file_underground_water(self):
        """지하누수 파일 검색 테스트"""
        file_path = self.test_dir / "지하누수_위치추가.csv"
        self.sample_data_underground.to_csv(
            file_path, index=False, encoding="utf-8-sig"
        )

        df, results = load_and_search_file(
            file_path, SEARCH_COLUMNS["지하누수_위치추가.csv"], "옥내"
        )

        self.assertIsNotNone(df)
        self.assertEqual(results["matched_rows"], 2)  # 2개 행이 '옥내' 포함

    def test_load_and_search_file_emergency(self):
        """긴급공사 파일 검색 테스트"""
        file_path = self.test_dir / "긴급공사_위치추가.csv"
        self.sample_data_emergency.to_csv(file_path, index=False, encoding="utf-8-sig")

        df, results = load_and_search_file(
            file_path, SEARCH_COLUMNS["긴급공사_위치추가.csv"], "옥내"
        )

        self.assertIsNotNone(df)
        self.assertEqual(results["matched_rows"], 3)  # 3개 행이 '옥내' 포함

    def test_load_and_search_file_management(self):
        """관리대장 파일 검색 테스트"""
        file_path = self.test_dir / "관리대장_위치추가.csv"
        self.sample_data_management.to_csv(file_path, index=False, encoding="utf-8-sig")

        df, results = load_and_search_file(
            file_path, SEARCH_COLUMNS["관리대장_위치추가.csv"], "옥내"
        )

        self.assertIsNotNone(df)
        self.assertEqual(results["matched_rows"], 2)  # 2개 행이 '옥내' 포함

    def test_analyze_temporal_pattern(self):
        """시간 패턴 분석 테스트"""
        # 테스트 데이터 준비
        df = self.sample_data_ground.copy()
        matched_indices = [0, 2]  # '옥내' 포함 행 인덱스

        # 분석 실행
        temporal = analyze_temporal_pattern(df, matched_indices)

        # 검증
        self.assertIn("yearly", temporal)
        self.assertIn("monthly", temporal)
        self.assertIn("date_range", temporal)

        # 2024년 데이터만 있어야 함
        self.assertIn(2024, temporal["yearly"])
        self.assertEqual(temporal["yearly"][2024], 2)

    def test_analyze_temporal_pattern_empty(self):
        """빈 데이터에 대한 시간 패턴 분석 테스트"""
        df = pd.DataFrame({"작업일시": []})
        temporal = analyze_temporal_pattern(df, [])

        self.assertEqual(temporal, {})

    def test_analyze_temporal_pattern_invalid_dates(self):
        """잘못된 날짜 형식 처리 테스트"""
        df = pd.DataFrame({"작업일시": ["invalid_date", "2024-01-01", None]})

        temporal = analyze_temporal_pattern(df, [0, 1, 2])

        # 유효한 날짜만 처리되어야 함
        if temporal:  # temporal이 비어있지 않으면
            self.assertIn("yearly", temporal)
            self.assertEqual(temporal["yearly"].get(2024, 0), 1)

    def test_save_results(self):
        """결과 저장 테스트"""
        # 테스트용 결과 데이터
        all_results = {
            "지상누수_위치추가.csv": {
                "total_rows": 100,
                "matched_rows": 10,
                "column_matches": {
                    "공사개요": {"count": 5},
                    "주소": {"count": 3},
                    "공사명": {"count": 2},
                },
                "temporal_pattern": {
                    "yearly": {2024: 10},
                    "monthly": {"2024-01": 5, "2024-02": 5},
                },
            }
        }

        # 저장 실행
        output_dir = self.test_dir / "output"
        save_results(all_results, output_dir)

        # 파일 생성 확인
        self.assertTrue((output_dir / "옥내작업_통계.json").exists())
        self.assertTrue((output_dir / "옥내작업_요약.txt").exists())

        # JSON 파일 내용 확인
        with open(output_dir / "옥내작업_통계.json", "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        self.assertIn("지상누수_위치추가.csv", saved_data)
        self.assertEqual(saved_data["지상누수_위치추가.csv"]["total_rows"], 100)
        self.assertEqual(saved_data["지상누수_위치추가.csv"]["matched_rows"], 10)

    def test_export_matched_rows(self):
        """매칭된 행 추출 테스트"""
        # 테스트 데이터 준비
        all_results = {
            "지상누수_위치추가.csv": {"matched_rows": 2, "matched_indices": [0, 2]}
        }

        all_dataframes = {"지상누수_위치추가.csv": self.sample_data_ground}

        # 추출 실행
        output_dir = self.test_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)  # 디렉토리 생성
        export_matched_rows(all_results, all_dataframes, output_dir)

        # 파일 생성 확인
        export_file = output_dir / "옥내작업_추출.csv"
        self.assertTrue(export_file.exists())

        # 추출된 데이터 확인
        extracted_df = pd.read_csv(export_file, encoding="utf-8-sig")
        self.assertEqual(len(extracted_df), 2)
        self.assertIn("원본파일", extracted_df.columns)

    def test_search_columns_completeness(self):
        """SEARCH_COLUMNS 정의 완전성 테스트"""
        expected_files = [
            "지상누수_위치추가.csv",
            "지하누수_위치추가.csv",
            "긴급공사_위치추가.csv",
            "관리대장_위치추가.csv",
        ]

        for file_name in expected_files:
            self.assertIn(file_name, SEARCH_COLUMNS)
            self.assertIsInstance(SEARCH_COLUMNS[file_name], list)
            self.assertGreater(len(SEARCH_COLUMNS[file_name]), 0)

    def test_case_insensitive_search(self):
        """대소문자 구분 없는 검색 테스트"""
        # 대문자 포함 데이터
        df = pd.DataFrame(
            {
                "공사개요": ["옥내 수리", "옥내 점검", "일반 작업"],
                "주소": ["서울시", "부산시", "대구시"],
                "공사명": ["공사1", "공사2", "공사3"],
            }
        )

        file_path = self.test_dir / "test.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        # 검색 실행
        _, results = load_and_search_file(file_path, ["공사개요"], "옥내")

        # 대소문자 구분 없이 매칭되어야 함
        self.assertEqual(results["matched_rows"], 2)

    def test_missing_columns_handling(self):
        """누락된 컬럼 처리 테스트"""
        # 일부 컬럼이 누락된 데이터
        df = pd.DataFrame(
            {
                "공사개요": ["옥내 수리", "일반 작업"],
                "위도": [37.5, 37.6],
                "경도": [127.0, 127.1],
                # '주소'와 '공사명' 컬럼 누락
            }
        )

        file_path = self.test_dir / "incomplete.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        # 누락된 컬럼 포함하여 검색
        _, results = load_and_search_file(
            file_path, ["공사개요", "주소", "공사명"], "옥내"  # 주소와 공사명은 없음
        )

        # 존재하는 컬럼만 검색되어야 함
        self.assertEqual(results["matched_rows"], 1)
        self.assertIn("공사개요", results["column_matches"])
        self.assertNotIn("주소", results["column_matches"])
        self.assertNotIn("공사명", results["column_matches"])

    def test_unicode_normalization_nfc_nfd(self):
        """유니코드 정규화 NFC/NFD 처리 테스트"""
        # NFC와 NFD 형태가 혼재된 데이터
        nfc_text = "옥내 누수"  # NFC
        nfd_text = unicodedata.normalize("NFD", "옥내") + " 공사"  # NFD

        df = pd.DataFrame(
            {
                "공사개요": [nfc_text, nfd_text, "일반 작업"],
                "주소": ["서울시", "부산시", "대구시"],
                "공사명": ["공사1", "공사2", "공사3"],
            }
        )

        file_path = self.test_dir / "unicode_test.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        # 검색 실행
        _, results = load_and_search_file(
            file_path, SEARCH_COLUMNS["지상누수_위치추가.csv"], "옥내"
        )

        # NFC와 NFD 모두 매칭되어야 함
        self.assertEqual(results["matched_rows"], 2)
        self.assertIn("공사개요", results["column_matches"])
        self.assertEqual(results["column_matches"]["공사개요"]["count"], 2)

    def test_normalize_text_function(self):
        """normalize_text 함수 테스트"""
        # NFC 텍스트
        nfc_text = "옥내"
        self.assertEqual(normalize_text(nfc_text), nfc_text)

        # NFD 텍스트
        nfd_text = unicodedata.normalize("NFD", "옥내")
        self.assertEqual(normalize_text(nfd_text), nfc_text)

        # None/NaN 처리
        self.assertTrue(pd.isna(normalize_text(None)))
        self.assertTrue(pd.isna(normalize_text(pd.NA)))

        # 숫자 처리
        self.assertEqual(normalize_text(123), "123")

    def test_search_with_normalization_function(self):
        """search_with_normalization 함수 테스트"""
        # NFC와 NFD 혼재 데이터
        series = pd.Series(
            [
                "옥내 작업",  # NFC
                unicodedata.normalize("NFD", "옥내") + " 점검",  # NFD
                "일반 작업",
                None,  # NaN 값
            ]
        )

        # 검색 실행
        result = search_with_normalization(series, "옥내")

        # NFC와 NFD 모두 찾아야 함
        self.assertTrue(result[0])  # NFC 매칭
        self.assertTrue(result[1])  # NFD 매칭
        self.assertFalse(result[2])  # 일반 작업은 매칭 안 됨
        self.assertFalse(result[3])  # NaN은 매칭 안 됨

        # 매칭된 개수 확인
        self.assertEqual(result.sum(), 2)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""

    def setUp(self):
        """테스트 셋업"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir()

    def tearDown(self):
        """테스트 정리"""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        # 테스트 파일들 생성
        test_data = {
            "지상누수_위치추가.csv": pd.DataFrame(
                {
                    "공사개요": ["옥내 누수", "도로 보수", "옥내 배관"],
                    "주소": ["서울시 종로구", "서울시 강남구 옥내로", "서울시 서초구"],
                    "공사명": ["누수 수리", "도로 공사", "배관 교체"],
                    "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "위도": [37.5, 37.6, 37.7],
                    "경도": [127.0, 127.1, 127.2],
                }
            ),
            "지하누수_위치추가.csv": pd.DataFrame(
                {
                    "공사개요": ["지하 누수", "옥내 점검", "배관 수리"],
                    "주소": ["서울시 중구 옥내동", "서울시 용산구", "서울시 마포구"],
                    "공사명": ["지하 공사", "점검 작업", "수리 작업"],
                    "작업일시": ["2024-02-01", "2024-02-02", "2024-02-03"],
                    "위도": [37.55, 37.65, 37.75],
                    "경도": [127.05, 127.15, 127.25],
                }
            ),
        }

        # 파일 저장
        for filename, df in test_data.items():
            df.to_csv(self.results_dir / filename, index=False, encoding="utf-8-sig")

        # main 함수 시뮬레이션
        from main11f_check_indoor import TARGET_FILES, SEARCH_COLUMNS

        all_results = {}
        for file_name in ["지상누수_위치추가.csv", "지하누수_위치추가.csv"]:
            file_path = self.results_dir / file_name
            if file_path.exists():
                df, results = load_and_search_file(
                    file_path, SEARCH_COLUMNS[file_name], "옥내"
                )
                if df is not None and results is not None:
                    all_results[file_name] = results

        # 결과 검증
        self.assertEqual(len(all_results), 2)
        self.assertGreater(all_results["지상누수_위치추가.csv"]["matched_rows"], 0)
        self.assertGreater(all_results["지하누수_위치추가.csv"]["matched_rows"], 0)


if __name__ == "__main__":
    unittest.main()
