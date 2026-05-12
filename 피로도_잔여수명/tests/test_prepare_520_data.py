"""Tests for prepare_520_data.py"""

import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from src.prepare_520_data import prepare_520_repair_data


class TestPrepare520RepairData:
    """Test suite for prepare_520_repair_data function"""

    @pytest.fixture
    def sample_ground_leak_data(self):
        """Create sample ground leak data"""
        return pd.DataFrame(
            {
                "경도": [127.0, 127.1, 127.2, None, 127.3],
                "위도": [37.5, 37.6, 37.7, 37.8, None],
                "작업종료일": [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                ],
                "주소": [
                    "서울시 강남구",
                    "서울시 서초구",
                    "서울시 송파구",
                    "서울시 강동구",
                    "서울시 광진구",
                ],
            }
        )

    @pytest.fixture
    def sample_underground_leak_data(self):
        """Create sample underground leak data"""
        return pd.DataFrame(
            {
                "경도": [126.9, 127.0, 200.0],  # Last one is invalid
                "위도": [37.4, 37.5, 37.6],
                "작업종료일": ["2024-02-01", "2024-02-02", "2024-02-03"],
                "주소": ["서울시 동작구", "서울시 관악구", "서울시 구로구"],
            }
        )

    @pytest.fixture
    def sample_other_repair_data(self):
        """Create sample other repair data"""
        return pd.DataFrame(
            {
                "경도": [127.1, 127.2],
                "위도": [37.3, 37.4],
                "작업종료일": ["2024-03-01", "2024-03-02"],
                "주소": ["경기도 성남시", "경기도 수원시"],
            }
        )

    @pytest.fixture
    def mock_csv_files(
        self,
        tmp_path,
        sample_ground_leak_data,
        sample_underground_leak_data,
        sample_other_repair_data,
    ):
        """Create mock CSV files in temporary directory"""
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # Save sample data to CSV files
        sample_ground_leak_data.to_csv(
            results_dir / "지상누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )
        sample_underground_leak_data.to_csv(
            results_dir / "지하누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )
        sample_other_repair_data.to_csv(
            results_dir / "기타공사_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        return results_dir

    def test_prepare_520_repair_data_success(
        self, tmp_path, mock_csv_files, monkeypatch
    ):
        """Test successful data preparation with all files present"""
        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        # Mock the output directory creation
        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        # Mock Transformer to avoid actual coordinate transformation
        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            mock_transformer.transform.side_effect = lambda lon, lat: (
                lon * 10000,
                lat * 10000,
            )
            mock_transformer_class.from_crs.return_value = mock_transformer

            # Run the function
            result = prepare_520_repair_data()

            # Assertions
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
            assert "repair_type" in result.columns
            assert "x" in result.columns
            assert "y" in result.columns
            assert "CNT_JNT" in result.columns

            # Check repair types
            assert set(result["repair_type"].unique()) <= {
                "ground_leak",
                "underground_leak",
                "other_repair",
            }

            # Check coordinate transformation was called
            assert mock_transformer.transform.called

            # Check output file was created
            output_file = (
                tmp_path / "data" / "520_area" / "repairs_with_location_520_v3.csv"
            )
            assert output_file.exists()

    def test_prepare_520_repair_data_missing_files(self, tmp_path, monkeypatch):
        """Test handling of missing input files"""
        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        # Create only one file
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        sample_data = pd.DataFrame(
            {
                "경도": [127.0],
                "위도": [37.5],
                "작업종료일": ["2024-01-01"],
                "주소": ["서울시"],
            }
        )
        sample_data.to_csv(
            results_dir / "지상누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        # Mock output directory
        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            mock_transformer.transform.return_value = (1270000, 375000)
            mock_transformer_class.from_crs.return_value = mock_transformer

            # Run the function - should handle missing files gracefully
            result = prepare_520_repair_data()

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1
            assert result["repair_type"].iloc[0] == "ground_leak"

    def test_prepare_520_repair_data_invalid_coordinates(self, tmp_path, monkeypatch):
        """Test filtering of invalid coordinates"""
        monkeypatch.chdir(tmp_path)

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # Create data with invalid coordinates
        invalid_data = pd.DataFrame(
            {
                "경도": [127.0, 200.0, 50.0, None, 127.5],  # Some invalid
                "위도": [37.5, 37.6, 37.7, 37.8, None],  # Some invalid
                "작업종료일": ["2024-01-01"] * 5,
                "주소": ["서울시"] * 5,
            }
        )
        invalid_data.to_csv(
            results_dir / "지상누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            mock_transformer.transform.return_value = (1270000, 375000)
            mock_transformer_class.from_crs.return_value = mock_transformer

            result = prepare_520_repair_data()

            # Only valid Korean coordinates should be processed
            assert len(result) == 1  # Only the first row has valid Korean coordinates

    def test_prepare_520_repair_data_repair_type_assignment(
        self, tmp_path, monkeypatch
    ):
        """Test correct assignment of repair types"""
        monkeypatch.chdir(tmp_path)

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # Create files for each type
        data = pd.DataFrame(
            {
                "경도": [127.0],
                "위도": [37.5],
                "작업종료일": ["2024-01-01"],
                "주소": ["서울시"],
            }
        )

        for filename, expected_type in [
            ("지상누수_520_위치추가.csv", "ground_leak"),
            ("지하누수_520_위치추가.csv", "underground_leak"),
            ("기타공사_520_위치추가.csv", "other_repair"),
        ]:
            data.to_csv(results_dir / filename, index=False, encoding="utf-8-sig")

        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            mock_transformer.transform.return_value = (1270000, 375000)
            mock_transformer_class.from_crs.return_value = mock_transformer

            result = prepare_520_repair_data()

            # Check all repair types are present
            assert set(result["repair_type"].unique()) == {
                "ground_leak",
                "underground_leak",
                "other_repair",
            }
            assert len(result) == 3

    def test_prepare_520_repair_data_cnt_jnt_addition(self, tmp_path, monkeypatch):
        """Test CNT_JNT column addition with random values"""
        monkeypatch.chdir(tmp_path)

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        data = pd.DataFrame(
            {
                "경도": [127.0, 127.1],
                "위도": [37.5, 37.6],
                "작업종료일": ["2024-01-01", "2024-01-02"],
                "주소": ["서울시", "경기도"],
            }
        )
        data.to_csv(
            results_dir / "지상누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            mock_transformer.transform.side_effect = lambda lon, lat: (
                lon * 10000,
                lat * 10000,
            )
            mock_transformer_class.from_crs.return_value = mock_transformer

            # Set random seed for reproducibility
            np.random.seed(42)
            result = prepare_520_repair_data()

            # Check CNT_JNT column
            assert "CNT_JNT" in result.columns
            assert result["CNT_JNT"].min() >= 1
            assert result["CNT_JNT"].max() < 20
            assert len(result["CNT_JNT"]) == len(result)

    def test_prepare_520_repair_data_coordinate_transformation_error(
        self, tmp_path, monkeypatch
    ):
        """Test handling of coordinate transformation errors"""
        monkeypatch.chdir(tmp_path)

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        data = pd.DataFrame(
            {
                "경도": [127.0, 127.1],
                "위도": [37.5, 37.6],
                "작업종료일": ["2024-01-01", "2024-01-02"],
                "주소": ["서울시", "경기도"],
            }
        )
        data.to_csv(
            results_dir / "지상누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            # Make transform raise an exception for some calls
            mock_transformer.transform.side_effect = [
                (1270000, 375000),  # First call succeeds
                Exception("Transformation error"),  # Second call fails
            ]
            mock_transformer_class.from_crs.return_value = mock_transformer

            result = prepare_520_repair_data()

            # Should handle the error gracefully and process valid data
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1  # Only first row should be processed

    def test_prepare_520_repair_data_output_columns(self, tmp_path, monkeypatch):
        """Test that output has all required columns"""
        monkeypatch.chdir(tmp_path)

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        data = pd.DataFrame(
            {
                "경도": [127.0],
                "위도": [37.5],
                "작업종료일": ["2024-01-01"],
                "주소": ["서울시"],
                "기타컬럼": ["데이터"],
            }
        )
        data.to_csv(
            results_dir / "지상누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            mock_transformer.transform.return_value = (1270000, 375000)
            mock_transformer_class.from_crs.return_value = mock_transformer

            result = prepare_520_repair_data()

            # Check required columns
            required_columns = [
                "경도",
                "위도",
                "작업종료일",
                "주소",
                "repair_type",
                "x",
                "y",
                "CNT_JNT",
            ]
            for col in required_columns:
                assert col in result.columns

            # Check original columns are preserved
            assert "기타컬럼" in result.columns

    def test_main_execution(self, tmp_path, monkeypatch, capsys):
        """Test main execution block"""
        monkeypatch.chdir(tmp_path)

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        data = pd.DataFrame(
            {
                "경도": [127.0, 127.1],
                "위도": [37.5, 37.6],
                "작업종료일": ["2024-01-01", "2024-02-01"],
                "주소": ["서울시", "경기도"],
            }
        )
        data.to_csv(
            results_dir / "지상누수_520_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        output_dir = tmp_path / "data" / "520_area"
        output_dir.mkdir(parents=True)

        with patch("src.prepare_520_data.Transformer") as mock_transformer_class:
            mock_transformer = MagicMock()
            mock_transformer.transform.side_effect = lambda lon, lat: (
                lon * 10000,
                lat * 10000,
            )
            mock_transformer_class.from_crs.return_value = mock_transformer

            # Execute the main block directly
            import sys
            from src.prepare_520_data import prepare_520_repair_data

            # Simulate running as main
            df = prepare_520_repair_data()

            # Capture the output
            captured = capsys.readouterr()

            # Check that summary is printed (would be in main block)
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2

            # Check that output file exists
            output_file = (
                tmp_path / "data" / "520_area" / "repairs_with_location_520_v3.csv"
            )
            assert output_file.exists()
