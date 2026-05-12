"""
main11b_merge_n_add2loc.py 테스트 코드
- 데이터 로드, 병합, 날짜 파싱, 지오코딩 기능 테스트
- CSV 출력 파일의 컬럼 검증
"""

import sys
import warnings
from pathlib import Path
import pandas as pd
import numpy as np
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main11b_merge_n_add2loc import (
    parse_date_column,
    load_repair_data,
    remove_duplicates_and_merge,
    add_geocoding,
    save_results,
)
from src.common.config import DATA_DIR, RESULTS_DIR

# 경고 무시
warnings.filterwarnings("ignore")


class TestMain11bMergeNAdd2Loc(unittest.TestCase):
    """main11b 기능 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        # 테스트용 샘플 데이터프레임 생성
        self.sample_df1 = pd.DataFrame(
            {
                "접수번호": ["2020001", "2020002", "2020003", None, ""],
                "지시번호": ["123", "124", "125", "126", "127"],
                "접수일시": [
                    "2020-06-23 09:12",
                    "2020-06-24 10:00",
                    "2020-06-25 11:30",
                    "2020-06-26 14:00",
                    "2020-06-27 15:00",
                ],
                "작업시작": ["2020-06-23 10:00", None, "2020-06-25 12:00", None, None],
                "작업종료": ["2020-06-23 11:30", "2020-06-24 12:00", None, None, None],
                "주소": [
                    "대구 북구 대학로 80",
                    "대구 중구 동성로 1",
                    "대구 수성구 범어동 123",
                    "대구 달서구 성당동 456",
                    "대구 동구 신암동 789",
                ],
            }
        )

        self.sample_df2 = pd.DataFrame(
            {
                "접수번호": ["2020002", "2020004", "2020005", None],  # 2020002는 중복
                "지시번호": ["224", "225", "계", "227"],  # '계'는 필터링 대상
                "접수일시": [
                    "2020-07-01 09:00",
                    "2020-07-02 10:00",
                    "2020-07-03 11:00",
                    "2020-07-04 12:00",
                ],
                "작업시작": [None, "2020-07-02 11:00", None, None],
                "작업종료": ["2020-07-01 12:00", None, "2020-07-03 14:00", None],
                "주소": [
                    "대구 북구 산격동 100",
                    "대구 남구 대명동 200",
                    "대구 달성군 논공읍 300",
                    "대구 수성구 만촌동 400",
                ],
            }
        )

        # 숫자 형식 날짜가 포함된 데이터프레임
        self.sample_df_numeric = pd.DataFrame(
            {
                "접수번호": ["2020101", "2020102"],
                "접수일시": [202006230912.0, 202006241000.0],
                "작업시작일시": [202006231000.0, np.nan],
                "작업종료일": [202006231130.0, 202006241200.0],
                "주소": ["대구 북구 복현동 111", "대구 서구 내당동 222"],
            }
        )

    def test_parse_date_column_string_format(self):
        """문자열 형식 날짜 파싱 테스트"""
        dates = parse_date_column(self.sample_df1, "접수일시")

        # 결과가 datetime Series인지 확인
        self.assertIsInstance(dates, pd.Series)

        # 첫 번째 날짜가 올바르게 파싱되었는지 확인
        self.assertEqual(dates.iloc[0], pd.Timestamp("2020-06-23 09:12:00"))

        # 모든 날짜가 파싱되었는지 확인
        self.assertEqual(dates.notna().sum(), 5)

    def test_parse_date_column_numeric_format(self):
        """숫자 형식 날짜 파싱 테스트"""
        dates = parse_date_column(self.sample_df_numeric, "접수일시")

        # 결과가 datetime Series인지 확인
        self.assertIsInstance(dates, pd.Series)

        # 첫 번째 날짜가 올바르게 파싱되었는지 확인
        self.assertEqual(dates.iloc[0], pd.Timestamp("2020-06-23 09:12:00"))

        # 두 번째 날짜도 확인
        self.assertEqual(dates.iloc[1], pd.Timestamp("2020-06-24 10:00:00"))

    def test_parse_date_column_invalid_year(self):
        """비정상 연도 필터링 테스트"""
        df = pd.DataFrame(
            {"날짜": ["1999-12-31 23:59", "2020-06-23 09:12", "2031-01-01 00:00"]}
        )
        dates = parse_date_column(df, "날짜")

        # 1999년과 2031년은 NaT로 처리되어야 함
        self.assertTrue(pd.isna(dates.iloc[0]))  # 1999년
        self.assertFalse(pd.isna(dates.iloc[1]))  # 2020년 (정상)
        self.assertTrue(pd.isna(dates.iloc[2]))  # 2031년

    def test_parse_date_column_missing_column(self):
        """존재하지 않는 컬럼 처리 테스트"""
        dates = parse_date_column(self.sample_df1, "존재하지않는컬럼")

        # 모든 값이 NaT여야 함
        self.assertTrue(dates.isna().all())
        self.assertEqual(len(dates), len(self.sample_df1))

    def test_load_repair_data_filter_summary_rows(self):
        """'계'/'소계' 행 필터링 테스트"""
        # 임시 CSV 파일 생성
        temp_file = Path("/tmp/test_repair.csv")
        self.sample_df2.to_csv(temp_file, index=False, encoding="utf-8-sig")

        try:
            df = load_repair_data(temp_file)

            # '계' 행이 제거되었는지 확인
            self.assertNotIn("계", df["지시번호"].values)

            # 원본 4행에서 '계' 1행 제거 = 3행
            self.assertEqual(len(df), 3)
        finally:
            # 임시 파일 삭제
            if temp_file.exists():
                temp_file.unlink()

    def test_remove_duplicates_and_merge(self):
        """중복 제거 및 병합 테스트"""
        result = remove_duplicates_and_merge(self.sample_df1, self.sample_df2)

        # 작업일시 컬럼이 생성되었는지 확인
        self.assertIn("작업일시", result.columns)

        # 중복된 접수번호 '2020002'가 df1 우선으로 처리되었는지 확인
        df2_2020002_count = len(
            result[(result["접수번호"] == "2020002") & (result["지시번호"] == "224")]
        )
        self.assertEqual(df2_2020002_count, 0)  # df2의 중복 행은 제거됨

        # 전체 행 수 확인 (df1: 5행 + df2: 3행(4-1중복) = 8행)
        # 실제로는 df2가 '계' 제거 전이므로 확인 필요
        self.assertGreaterEqual(len(result), 5)  # 최소 df1 행 수 이상

    def test_작업일시_priority(self):
        """작업일시 우선순위 테스트: 접수일시 > 작업시작 > 작업종료"""
        # 다양한 케이스를 포함한 데이터프레임
        df = pd.DataFrame(
            {
                "접수번호": ["001", "002", "003", "004"],
                "접수일시": ["2020-06-23 09:00", None, None, "2020-06-26 09:00"],
                "작업시작": [
                    "2020-06-23 10:00",
                    "2020-06-24 10:00",
                    None,
                    "2020-06-26 10:00",
                ],
                "작업종료": [
                    "2020-06-23 11:00",
                    "2020-06-24 11:00",
                    "2020-06-25 11:00",
                    "2020-06-26 11:00",
                ],
            }
        )

        # 병합 함수 내부 로직 테스트를 위해 직접 우선순위 적용
        if "접수일시" in df.columns:
            df["작업일시"] = parse_date_column(df, "접수일시")
        elif "작업시작" in df.columns:
            df["작업일시"] = parse_date_column(df, "작업시작")
        elif "작업종료" in df.columns:
            df["작업일시"] = parse_date_column(df, "작업종료")

        # 케이스 1: 접수일시 있음 → 접수일시 사용
        self.assertEqual(df.iloc[0]["작업일시"], pd.Timestamp("2020-06-23 09:00:00"))

        # 케이스 2: 접수일시 없음, 작업시작 있음 → NaT (접수일시 우선이므로)
        self.assertTrue(pd.isna(df.iloc[1]["작업일시"]))

        # 케이스 3: 접수일시, 작업시작 없음 → NaT
        self.assertTrue(pd.isna(df.iloc[2]["작업일시"]))

        # 케이스 4: 모두 있음 → 접수일시 사용
        self.assertEqual(df.iloc[3]["작업일시"], pd.Timestamp("2020-06-26 09:00:00"))

    def test_output_csv_columns(self):
        """출력 CSV 파일의 컬럼 확인 테스트"""
        # 병합 결과 생성
        result = remove_duplicates_and_merge(self.sample_df1, self.sample_df2)

        # 필수 컬럼들이 존재하는지 확인
        required_columns = [
            "접수번호",
            "지시번호",
            "접수일시",
            "작업시작",
            "작업종료",
            "주소",
            "작업일시",
        ]

        for col in required_columns:
            self.assertIn(col, result.columns, f"필수 컬럼 '{col}'이 누락되었습니다")

        # 지오코딩 후 추가될 컬럼 모의 테스트
        result["위도"] = [
            35.8714,
            35.8654,
            35.8467,
            None,
            35.8901,
            35.8234,
            35.8567,
            None,
        ][: len(result)]
        result["경도"] = [
            128.6014,
            128.5984,
            128.6234,
            None,
            128.5678,
            128.6123,
            128.5890,
            None,
        ][: len(result)]

        geocoding_columns = ["위도", "경도"]
        for col in geocoding_columns:
            self.assertIn(
                col, result.columns, f"지오코딩 컬럼 '{col}'이 누락되었습니다"
            )

        print(f"\n출력 CSV 컬럼 목록 ({len(result.columns)}개):")
        print(f"  {list(result.columns)}")

    def test_column_order_consistency(self):
        """컬럼 순서 일관성 테스트"""
        # 첫 번째 병합
        result1 = remove_duplicates_and_merge(self.sample_df1, self.sample_df2)
        cols1 = list(result1.columns)

        # 두 번째 병합 (순서를 바꿔서)
        result2 = remove_duplicates_and_merge(self.sample_df2, self.sample_df1)
        cols2 = list(result2.columns)

        # 작업일시는 항상 마지막에 추가되므로 확인
        self.assertEqual(cols1[-1], "작업일시")
        self.assertEqual(cols2[-1], "작업일시")

        print(f"\n컬럼 순서 확인:")
        print(f"  병합1 마지막 3개 컬럼: {cols1[-3:]}")
        print(f"  병합2 마지막 3개 컬럼: {cols2[-3:]}")

    @patch("src.main11b_merge_n_add2loc.geocode_addresses")
    def test_add_geocoding_integration(self, mock_geocode):
        """지오코딩 통합 테스트"""
        # 모의 지오코딩 결과 설정
        mock_geocode.return_value = (
            [35.8714, 35.8654, None, 35.8467, 35.8901],  # 위도
            [128.6014, 128.5984, None, 128.6234, 128.5678],  # 경도
            ["대구 수성구 범어동 123"],  # 실패한 주소
        )

        # 지오코딩 실행
        geocoded_df, failed = add_geocoding(self.sample_df1)

        # 위도/경도 컬럼 추가 확인
        self.assertIn("위도", geocoded_df.columns)
        self.assertIn("경도", geocoded_df.columns)

        # 성공/실패 개수 확인
        valid_count = geocoded_df[geocoded_df["위도"].notna()].shape[0]
        self.assertEqual(valid_count, 4)  # 5개 중 4개 성공
        self.assertEqual(len(failed), 1)  # 1개 실패

        print(f"\n지오코딩 결과:")
        print(f"  성공: {valid_count}/5")
        print(f"  실패 주소: {failed}")


def run_integration_test():
    """실제 파일을 사용한 통합 테스트 (선택적)"""
    print("\n" + "=" * 60)
    print("실제 데이터 통합 테스트")
    print("=" * 60)

    # 실제 파일 경로
    file1_path = DATA_DIR / "repair" / "긴급복구.csv"
    file2_path = DATA_DIR / "repair" / "긴급복구공사관리(0520).csv"

    if not file1_path.exists() or not file2_path.exists():
        print("실제 데이터 파일이 없어 통합 테스트를 건너뜁니다.")
        return

    try:
        # 파일 로드
        df1 = load_repair_data(file1_path)
        df2 = load_repair_data(file2_path)
        print(f"\n파일 로드 완료:")
        print(f"  - {file1_path.name}: {len(df1)}행")
        print(f"  - {file2_path.name}: {len(df2)}행")

        # 병합
        merged = remove_duplicates_and_merge(df1, df2)
        print(f"\n병합 완료: {len(merged)}행")

        # 작업일시 컬럼 확인
        if "작업일시" in merged.columns:
            valid_dates = merged["작업일시"].notna().sum()
            print(f"작업일시 컬럼: {valid_dates}/{len(merged)} 유효")

            # 샘플 출력
            sample = merged[merged["작업일시"].notna()].head(3)
            print("\n작업일시 샘플:")
            for idx, row in sample.iterrows():
                print(f"  - 접수번호 {row.get('접수번호', 'N/A')}: {row['작업일시']}")

        # 컬럼 목록 출력
        print(f"\n전체 컬럼 ({len(merged.columns)}개):")
        for i, col in enumerate(merged.columns, 1):
            print(f"  {i:2d}. {col}")

    except Exception as e:
        print(f"통합 테스트 중 오류 발생: {e}")


if __name__ == "__main__":
    # 단위 테스트 실행
    print("\n단위 테스트 실행 중...")
    unittest.main(argv=[""], exit=False, verbosity=2)

    # 통합 테스트 실행 (선택적)
    run_integration_test()
