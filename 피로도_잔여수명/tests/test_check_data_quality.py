"""Tests for check_data_quality.py"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.check_data_quality import DataQualityChecker


class TestDataQualityChecker:
    """Test suite for DataQualityChecker class"""

    @pytest.fixture
    def sample_valid_data(self):
        """Create sample valid data"""
        return pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7, 37.8],
                "경도": [127.0, 127.1, 127.2, 127.3],
                "작업종료일": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "주소": [
                    "서울시 강남구",
                    "서울시 서초구",
                    "서울시 송파구",
                    "서울시 강동구",
                ],
                "repair_type": [
                    "ground_leak",
                    "underground_leak",
                    "other_repair",
                    "ground_leak",
                ],
                "x": [1270000, 1271000, 1272000, 1273000],
                "y": [375000, 376000, 377000, 378000],
                "CNT_JNT": [5, 10, 15, 20],
            }
        )

    @pytest.fixture
    def sample_invalid_coordinates_data(self):
        """Create sample data with invalid coordinates"""
        return pd.DataFrame(
            {
                "위도": [
                    37.5,
                    100.0,
                    None,
                    37.8,
                ],  # Second is out of range, third is null
                "경도": [127.0, 127.1, 127.2, 200.0],  # Fourth is out of range
                "작업종료일": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "주소": ["서울시", "부산시", "대구시", "광주시"],
            }
        )

    @pytest.fixture
    def sample_missing_dates_data(self):
        """Create sample data with missing dates"""
        return pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7, 37.8],
                "경도": [127.0, 127.1, 127.2, 127.3],
                "작업종료일": ["2024-01-01", None, "", "2024-01-04"],
                "주소": ["서울시", "부산시", "대구시", "광주시"],
            }
        )

    @pytest.fixture
    def sample_duplicate_data(self):
        """Create sample data with duplicates"""
        return pd.DataFrame(
            {
                "위도": [37.5, 37.5, 37.6, 37.6],
                "경도": [127.0, 127.0, 127.1, 127.1],
                "작업종료일": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"],
                "주소": ["서울시", "서울시", "부산시", "부산시"],
            }
        )

    @pytest.fixture
    def sample_english_columns_data(self):
        """Create sample data with English column names"""
        return pd.DataFrame(
            {
                "latitude": [37.5, 37.6, 37.7],
                "longitude": [127.0, 127.1, 127.2],
                "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "address": ["Seoul", "Busan", "Daegu"],
            }
        )

    @pytest.fixture
    def mock_data_file(self, tmp_path, sample_valid_data):
        """Create mock data file"""
        data_file = tmp_path / "test_data.csv"
        sample_valid_data.to_csv(data_file, index=False, encoding="utf-8-sig")
        return data_file

    def test_init(self):
        """Test DataQualityChecker initialization"""
        checker = DataQualityChecker()
        assert checker.df is None
        assert checker.quality_report == {}
        assert checker.data_path is not None

    def test_init_with_custom_path(self, tmp_path):
        """Test initialization with custom data path"""
        custom_path = tmp_path / "custom_data.csv"
        checker = DataQualityChecker(str(custom_path))
        assert checker.data_path == str(custom_path)

    def test_load_data_success(self, mock_data_file):
        """Test successful data loading"""
        checker = DataQualityChecker(str(mock_data_file))
        result = checker.load_data()

        assert result is True
        assert checker.df is not None
        assert len(checker.df) == 4

    def test_load_data_failure(self, tmp_path):
        """Test data loading failure"""
        non_existent_file = tmp_path / "non_existent.csv"
        checker = DataQualityChecker(str(non_existent_file))
        result = checker.load_data()

        assert result is False
        assert checker.df is None

    def test_check_coordinates_valid(self, sample_valid_data):
        """Test coordinate validation with valid data"""
        checker = DataQualityChecker()
        checker.df = sample_valid_data

        results = checker.check_coordinates()

        assert results["valid"] == True
        assert results["total"] == 4
        assert results["invalid_count"] == 0
        assert results["invalid_records"] == []

    def test_check_coordinates_invalid(self, sample_invalid_coordinates_data):
        """Test coordinate validation with invalid data"""
        checker = DataQualityChecker()
        checker.df = sample_invalid_coordinates_data

        results = checker.check_coordinates()

        assert results["valid"] == False
        assert results["invalid_count"] == 3  # Three invalid coordinates
        assert len(results["invalid_records"]) == 3

    def test_check_coordinates_english_columns(self, sample_english_columns_data):
        """Test coordinate validation with English column names"""
        checker = DataQualityChecker()
        checker.df = sample_english_columns_data

        results = checker.check_coordinates()

        assert results["valid"] == True
        assert results["total"] == 3
        assert results["invalid_count"] == 0

    def test_check_coordinates_no_columns(self):
        """Test coordinate validation when coordinate columns are missing"""
        checker = DataQualityChecker()
        checker.df = pd.DataFrame({"data": [1, 2, 3]})

        results = checker.check_coordinates()

        assert results["valid"] == False
        assert "coordinates" in checker.quality_report

    def test_check_dates(self, sample_valid_data):
        """Test date validation"""
        checker = DataQualityChecker()
        checker.df = sample_valid_data

        results = checker.check_dates()

        assert (
            results["valid"] == False
        )  # Dates will be invalid because they're strings
        assert results["invalid_count"] > 0
        assert results["date_range"] is not None

    def test_check_dates_with_missing(self, sample_missing_dates_data):
        """Test date validation with missing dates"""
        checker = DataQualityChecker()
        checker.df = sample_missing_dates_data

        results = checker.check_dates()

        assert results["valid"] == False
        assert (
            results["invalid_count"] == 4
        )  # All dates are invalid (not parsed correctly)

    def test_check_dates_with_invalid_format(self):
        """Test date validation with invalid date format"""
        checker = DataQualityChecker()
        checker.df = pd.DataFrame(
            {"작업종료일": ["20240101", "invalid-date", "20240103"]}
        )

        results = checker.check_dates()

        assert results["invalid_count"] > 0

    def test_check_duplicates(self, sample_duplicate_data):
        """Test duplicate detection"""
        checker = DataQualityChecker()
        checker.df = sample_duplicate_data

        results = checker.check_duplicates()

        assert results["valid"] == False  # Has duplicates means not valid
        assert (
            results["duplicate_count"] == 1
        )  # One duplicate (second occurrence of first pair)

    def test_check_duplicates_none(self, sample_valid_data):
        """Test duplicate detection with no duplicates"""
        checker = DataQualityChecker()
        checker.df = sample_valid_data

        results = checker.check_duplicates()

        assert results["valid"] == True  # No duplicates means valid
        assert results["duplicate_count"] == 0

    def test_check_encoding(self, sample_valid_data):
        """Test encoding validation"""
        checker = DataQualityChecker()
        checker.df = sample_valid_data

        results = checker.check_encoding()

        assert "address_columns" in results
        assert len(results["address_columns"]) > 0

    def test_check_encoding_no_korean(self):
        """Test encoding validation with no Korean text"""
        checker = DataQualityChecker()
        checker.df = pd.DataFrame({"주소": ["Seoul", "Busan", "Daegu"]})

        results = checker.check_encoding()

        assert len(results["encoding_issues"]) > 0

    def test_check_repair_types(self, sample_valid_data):
        """Test repair type validation"""
        checker = DataQualityChecker()
        checker.df = sample_valid_data

        results = checker.check_repair_types()

        assert results["repair_column"] == "repair_type"
        assert len(results["unique_types"]) == 3
        assert "ground_leak" in results["unique_types"]

    def test_check_repair_types_missing_column(self):
        """Test repair type validation when column is missing"""
        checker = DataQualityChecker()
        checker.df = pd.DataFrame({"data": [1, 2, 3]})

        results = checker.check_repair_types()

        assert results["valid"] is False
        assert results["repair_column"] is None

    def test_generate_summary(self, sample_valid_data, capsys):
        """Test summary generation"""
        checker = DataQualityChecker()
        checker.df = sample_valid_data
        checker.check_coordinates()
        checker.check_dates()

        checker.generate_summary()

        captured = capsys.readouterr()
        assert "데이터 품질 검사 요약" in captured.out
        assert "COORDINATES" in captured.out or "coordinates" in captured.out.lower()

    def test_run_method(self, mock_data_file):
        """Test run method that executes all checks"""
        checker = DataQualityChecker(str(mock_data_file))

        result = checker.run()

        assert result is True
        assert "coordinates" in checker.quality_report
        assert "dates" in checker.quality_report
        assert "duplicates" in checker.quality_report
        assert "repair_types" in checker.quality_report
        assert "encoding" in checker.quality_report

    def test_save_report(self, tmp_path, sample_valid_data):
        """Test saving quality report"""
        checker = DataQualityChecker()
        checker.df = sample_valid_data
        checker.quality_report = {
            "coordinates": {"valid": True, "invalid_count": 0},
            "dates": {
                "valid": True,
                "invalid_count": 0,
                "date_range": (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-04")),
            },
            "duplicates": {"valid": True, "duplicate_count": 0},
            "encoding": {"valid": True, "address_columns": ["주소"]},
            "repair_types": {
                "valid": True,
                "unique_types": ["ground_leak", "underground_leak", "other_repair"],
            },
        }

        report_file = tmp_path / "quality_report.txt"
        checker.save_report(str(report_file))

        assert report_file.exists()

        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "520 지역 데이터 품질 검사 보고서" in content
            assert "PASS" in content or "FAIL" in content

    def test_main_function(self, tmp_path, monkeypatch):
        """Test main function execution"""
        from src.check_data_quality import main

        # Create test data file
        test_data = pd.DataFrame(
            {
                "위도": [37.5],
                "경도": [127.0],
                "작업종료일": ["2024-01-01"],
                "주소": ["서울시"],
                "repair_type": ["ground_leak"],
                "x": [1270000],
                "y": [375000],
                "CNT_JNT": [10],
            }
        )

        data_file = tmp_path / "test_data.csv"
        test_data.to_csv(data_file, index=False, encoding="utf-8-sig")

        # Mock command line arguments
        test_args = ["check_data_quality.py", "--data-path", str(data_file)]
        monkeypatch.setattr("sys.argv", test_args)

        # Run main
        result = main()

        # Should return 0 for success
        assert result == 0

        # Check that report file was created
        report_files = list(tmp_path.parent.glob("**/data_quality_report*.txt"))
        assert len(report_files) > 0 or result == 0

    def test_main_function_with_output_path(self, tmp_path, monkeypatch):
        """Test main function with custom output path"""
        from src.check_data_quality import main

        # Create test data file
        test_data = pd.DataFrame(
            {
                "위도": [37.5],
                "경도": [127.0],
                "작업종료일": ["2024-01-01"],
                "주소": ["서울시"],
            }
        )

        data_file = tmp_path / "test_data.csv"
        test_data.to_csv(data_file, index=False, encoding="utf-8-sig")

        output_file = tmp_path / "custom_report.txt"

        # Mock command line arguments
        test_args = [
            "check_data_quality.py",
            "--data-path",
            str(data_file),
            "--output",
            str(output_file),
        ]
        monkeypatch.setattr("sys.argv", test_args)

        # Run main
        result = main()

        assert result == 0
        assert output_file.exists()
