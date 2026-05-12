"""Tests for main11a_chk_dup_repair.py"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
from io import StringIO

import pandas as pd
import pytest


# Instead of importing and calling main, we'll test the logic directly
def run_duplicate_check(file1_df, file2_df):
    """Run duplicate check logic similar to main11a_chk_dup_repair.py"""
    from collections import Counter

    # Filter out summary rows
    df1_filtered = file1_df[
        ~file1_df["지시번호"].astype(str).str.strip().isin(["계", "소계"])
    ]
    df2_filtered = file2_df[
        ~file2_df["지시번호"].astype(str).str.strip().isin(["계", "소계"])
    ]

    # Filter rows with receipt numbers
    df1_with_receipt = df1_filtered[
        df1_filtered["접수번호"].notna() & (df1_filtered["접수번호"] != "")
    ]
    df2_with_receipt = df2_filtered[
        df2_filtered["접수번호"].notna() & (df2_filtered["접수번호"] != "")
    ]

    # Get receipt numbers
    receipt_nums1 = df1_with_receipt["접수번호"].astype(str).tolist()
    receipt_nums2 = df2_with_receipt["접수번호"].astype(str).tolist()

    # Check internal duplicates
    counter1 = Counter(receipt_nums1)
    duplicates1 = {k: v for k, v in counter1.items() if v > 1}

    counter2 = Counter(receipt_nums2)
    duplicates2 = {k: v for k, v in counter2.items() if v > 1}

    # Check cross-file duplicates
    set1 = set(receipt_nums1)
    set2 = set(receipt_nums2)
    intersection = set1 & set2

    return {
        "file1_total": len(receipt_nums1),
        "file2_total": len(receipt_nums2),
        "file1_duplicates": duplicates1,
        "file2_duplicates": duplicates2,
        "cross_duplicates": intersection,
        "df1_filtered_count": len(df1_filtered),
        "df2_filtered_count": len(df2_filtered),
        "df1_original_count": len(file1_df),
        "df2_original_count": len(file2_df),
    }


class TestMain11aChkDupRepair:
    """Test suite for duplicate repair checking script"""

    @pytest.fixture
    def sample_repair_data1(self):
        """Create sample repair data without duplicates"""
        return pd.DataFrame(
            {
                "지시번호": ["A001", "A002", "A003", "계", "소계"],
                "접수번호": ["R001", "R002", "R003", "R004", "R005"],
                "주소": [
                    "서울시 강남구",
                    "서울시 서초구",
                    "서울시 송파구",
                    "총계",
                    "부분계",
                ],
                "접수일시": [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                ],
            }
        )

    @pytest.fixture
    def sample_repair_data2(self):
        """Create sample repair data with some duplicates"""
        return pd.DataFrame(
            {
                "지시번호": ["B001", "B002", "B003", "B004"],
                "접수번호": ["R006", "R007", "R008", "R009"],
                "주소": [
                    "경기도 성남시",
                    "경기도 수원시",
                    "경기도 용인시",
                    "경기도 안양시",
                ],
                "접수일시": ["2024-02-01", "2024-02-02", "2024-02-03", "2024-02-04"],
            }
        )

    @pytest.fixture
    def sample_repair_data_with_internal_dup(self):
        """Create sample repair data with internal duplicates"""
        return pd.DataFrame(
            {
                "지시번호": ["C001", "C002", "C003", "C004", "C005"],
                "접수번호": [
                    "R010",
                    "R011",
                    "R010",
                    "R012",
                    "R011",
                ],  # R010 and R011 are duplicated
                "주소": ["인천시", "부산시", "인천시", "대구시", "부산시"],
                "접수일시": [
                    "2024-03-01",
                    "2024-03-02",
                    "2024-03-03",
                    "2024-03-04",
                    "2024-03-05",
                ],
            }
        )

    @pytest.fixture
    def sample_repair_data_with_cross_dup(self):
        """Create sample repair data with cross-file duplicates"""
        return pd.DataFrame(
            {
                "지시번호": ["D001", "D002", "D003"],
                "접수번호": [
                    "R001",
                    "R002",
                    "R020",
                ],  # R001 and R002 overlap with data1
                "주소": ["서울시 강남구", "서울시 서초구", "제주시"],
                "접수일시": ["2024-01-01", "2024-01-02", "2024-04-01"],
            }
        )

    @pytest.fixture
    def sample_repair_data_with_empty_receipt(self):
        """Create sample repair data with empty receipt numbers"""
        return pd.DataFrame(
            {
                "지시번호": ["E001", "E002", "E003", "E004"],
                "접수번호": ["R030", None, "", "R031"],  # Some empty values
                "주소": ["광주시", "대전시", "울산시", "세종시"],
                "접수일시": ["2024-05-01", "2024-05-02", "2024-05-03", "2024-05-04"],
            }
        )

    def test_no_duplicates(self, sample_repair_data1, sample_repair_data2):
        """Test when there are no duplicates"""
        result = run_duplicate_check(sample_repair_data1, sample_repair_data2)

        assert result["file1_total"] == 3  # Excluding '계' and '소계'
        assert result["file2_total"] == 4
        assert len(result["file1_duplicates"]) == 0
        assert len(result["file2_duplicates"]) == 0
        assert len(result["cross_duplicates"]) == 0

    def test_with_internal_duplicates(
        self, sample_repair_data_with_internal_dup, sample_repair_data2
    ):
        """Test when there are internal duplicates within a file"""
        result = run_duplicate_check(
            sample_repair_data_with_internal_dup, sample_repair_data2
        )

        assert result["file1_total"] == 5
        assert len(result["file1_duplicates"]) == 2  # R010 and R011
        assert result["file1_duplicates"]["R010"] == 2
        assert result["file1_duplicates"]["R011"] == 2
        assert len(result["file2_duplicates"]) == 0

    def test_with_cross_file_duplicates(
        self, sample_repair_data1, sample_repair_data_with_cross_dup
    ):
        """Test when there are duplicates between two files"""
        result = run_duplicate_check(
            sample_repair_data1, sample_repair_data_with_cross_dup
        )

        assert len(result["cross_duplicates"]) == 2  # R001 and R002
        assert "R001" in result["cross_duplicates"]
        assert "R002" in result["cross_duplicates"]

    def test_filters_out_summary_rows(self, sample_repair_data1, sample_repair_data2):
        """Test that rows with '계' or '소계' are filtered out"""
        result = run_duplicate_check(sample_repair_data1, sample_repair_data2)

        # Original has 5 rows, filtered should have 3
        assert result["df1_original_count"] == 5
        assert result["df1_filtered_count"] == 3
        assert result["file1_total"] == 3

    def test_handles_empty_receipt_numbers(
        self, sample_repair_data_with_empty_receipt, sample_repair_data2
    ):
        """Test handling of empty or None receipt numbers"""
        result = run_duplicate_check(
            sample_repair_data_with_empty_receipt, sample_repair_data2
        )

        # Only rows with valid receipt numbers should be counted
        assert result["file1_total"] == 2  # Only R030 and R031

    def test_empty_dataframes(self):
        """Test with empty CSV files"""
        empty_df = pd.DataFrame(columns=["지시번호", "접수번호", "주소", "접수일시"])
        result = run_duplicate_check(empty_df, empty_df)

        assert result["file1_total"] == 0
        assert result["file2_total"] == 0
        assert len(result["file1_duplicates"]) == 0
        assert len(result["file2_duplicates"]) == 0

    def test_large_number_of_duplicates(self):
        """Test with many duplicates"""
        # Create data with many duplicates
        receipt_numbers = [
            f"R{i:03d}" for i in range(5)
        ] * 3  # 15 total, 5 unique, each appears 3 times
        large_dup_data = pd.DataFrame(
            {
                "지시번호": [f"F{i:03d}" for i in range(15)],
                "접수번호": receipt_numbers,
                "주소": ["도시"] * 15,
                "접수일시": ["2024-06-01"] * 15,
            }
        )

        normal_data = pd.DataFrame(
            {
                "지시번호": ["G001"],
                "접수번호": ["R100"],
                "주소": ["도시"],
                "접수일시": ["2024-06-02"],
            }
        )

        result = run_duplicate_check(large_dup_data, normal_data)

        assert (
            len(result["file1_duplicates"]) == 5
        )  # 5 unique duplicate receipt numbers
        for receipt_num in result["file1_duplicates"]:
            assert result["file1_duplicates"][receipt_num] == 3  # Each appears 3 times

    def test_main_function_imports(self):
        """Test that the main function can be imported"""
        try:
            from src.main11a_chk_dup_repair import main

            assert callable(main)
        except ImportError:
            pytest.fail("Could not import main function from main11a_chk_dup_repair")

    def test_main_with_mocked_files(self, tmp_path, monkeypatch):
        """Test main function with mocked file system"""
        from src.main11a_chk_dup_repair import main

        # Create test directory structure
        repair_dir = tmp_path / "data" / "repair"
        results_dir = tmp_path / "results"
        repair_dir.mkdir(parents=True)
        results_dir.mkdir(parents=True)

        # Create test CSV files
        df1 = pd.DataFrame(
            {
                "지시번호": ["A001", "A002"],
                "접수번호": ["R001", "R002"],
                "주소": ["서울", "부산"],
                "접수일시": ["2024-01-01", "2024-01-02"],
            }
        )

        df2 = pd.DataFrame(
            {
                "지시번호": ["B001", "B002"],
                "접수번호": ["R003", "R001"],  # R001 is duplicate
                "주소": ["대구", "광주"],
                "접수일시": ["2024-02-01", "2024-02-02"],
            }
        )

        df1.to_csv(repair_dir / "긴급복구.csv", index=False, encoding="utf-8-sig")
        df2.to_csv(
            repair_dir / "긴급복구공사관리(0520).csv", index=False, encoding="utf-8-sig"
        )

        # Patch Path to use our tmp directory
        import src.main11a_chk_dup_repair

        monkeypatch.setattr(
            src.main11a_chk_dup_repair,
            "__file__",
            str(tmp_path / "src" / "main11a_chk_dup_repair.py"),
        )

        # Capture output
        captured_output = StringIO()
        monkeypatch.setattr("sys.stdout", captured_output)

        # Run main
        main()

        # Check output
        output = captured_output.getvalue()
        assert "접수번호 중복 검사 시작" in output
        assert "파일 읽기" in output
        assert "R001" in output  # Should detect the duplicate

        # Check that CSV file was created
        csv_files = list(results_dir.glob("duplicate_check_*.csv"))
        assert len(csv_files) == 1

    def test_csv_output_format(self, tmp_path, monkeypatch):
        """Test the format of the output CSV file"""
        from src.main11a_chk_dup_repair import main

        # Create test directory structure
        repair_dir = tmp_path / "data" / "repair"
        results_dir = tmp_path / "results"
        repair_dir.mkdir(parents=True)
        results_dir.mkdir(parents=True)

        # Create test CSV with duplicates
        df = pd.DataFrame(
            {
                "지시번호": ["A001", "A002", "A003"],
                "접수번호": ["R001", "R001", "R002"],  # R001 is duplicate
                "주소": ["서울", "부산", "대구"],
                "접수일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
            }
        )

        df.to_csv(repair_dir / "긴급복구.csv", index=False, encoding="utf-8-sig")
        df.to_csv(
            repair_dir / "긴급복구공사관리(0520).csv", index=False, encoding="utf-8-sig"
        )

        # Patch Path and datetime
        import src.main11a_chk_dup_repair

        monkeypatch.setattr(
            src.main11a_chk_dup_repair,
            "__file__",
            str(tmp_path / "src" / "main11a_chk_dup_repair.py"),
        )
        monkeypatch.setattr(
            "src.main11a_chk_dup_repair.datetime",
            MagicMock(
                now=MagicMock(
                    return_value=MagicMock(
                        strftime=MagicMock(return_value="20240101_120000")
                    )
                )
            ),
        )

        # Redirect output
        monkeypatch.setattr("sys.stdout", StringIO())

        # Run main
        main()

        # Check CSV file
        output_file = results_dir / "duplicate_check_20240101_120000.csv"
        assert output_file.exists()

        result_df = pd.read_csv(output_file, encoding="utf-8-sig")

        # Check columns
        assert "중복유형" in result_df.columns
        assert "접수번호" in result_df.columns
        assert "중복횟수" in result_df.columns
        assert "파일명" in result_df.columns
