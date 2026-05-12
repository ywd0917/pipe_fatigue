"""
Tests for main26_integrated_spatial.py - Integrated spatial analysis module
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from src.main26_integrated_spatial import IntegratedSpatialAnalyzer


class TestIntegratedSpatialAnalyzer:
    """Test suite for IntegratedSpatialAnalyzer class"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return IntegratedSpatialAnalyzer()

    @pytest.fixture
    def sample_hotspot_data(self):
        """Create sample hotspot GeoDataFrame"""
        data = {
            "grid_id": [1, 2, 3],
            "repair_count": [10, 5, 2],
            "gi_star_z": [3.5, 1.8, -0.5],
            "hotspot_type": ["Hot Spot 99%", "Hot Spot 90%", "Not Significant"],
            "geometry": [Point(127.0, 37.5), Point(127.1, 37.5), Point(127.2, 37.5)],
        }
        return gpd.GeoDataFrame(data, crs="EPSG:5179")

    @pytest.fixture
    def sample_infrastructure_data(self):
        """Create sample infrastructure DataFrame"""
        return pd.DataFrame(
            {
                "grid_id": [1, 2, 3],
                "cnt_jnt_mean": [15.5, 8.2, 3.1],
                "cnt_jnt_max": [25, 12, 5],
                "k_total_mean": [1.8, 1.2, 0.9],
                "d_final_mean": [0.75, 0.45, 0.25],
            }
        )

    @pytest.fixture
    def sample_spacetime_data(self):
        """Create sample space-time analysis data"""
        return pd.DataFrame(
            {
                "grid_id": [1, 2, 3],
                "temporal_trend": [0.15, 0.08, -0.02],
                "seasonal_amplitude": [2.3, 1.5, 0.8],
                "mann_kendall_stat": [2.5, 1.2, -0.5],
                "p_value": [0.01, 0.15, 0.62],
            }
        )

    @pytest.fixture
    def sample_emerging_data(self):
        """Create sample emerging hotspot DataFrame"""
        return pd.DataFrame(
            {
                "grid_id": [1, 2, 3],
                "pattern": ["Intensifying", "Persistent", "Never"],
                "trend_slope": [0.25, 0.05, 0.0],
                "consistency_score": [0.85, 0.92, 0.0],
                "months_active": [18, 24, 0],
            }
        )

    @pytest.fixture
    def sample_priority_data(self):
        """Create sample priority ranking DataFrame"""
        return pd.DataFrame(
            {
                "grid_id": [1, 2, 3],
                "cell_id": [1, 2, 3],  # Add cell_id
                "priority_score": [85.5, 62.3, 15.2],
                "total_score": [85.5, 62.3, 15.2],  # Add total_score
                "risk_category": ["Critical", "High", "Low"],
                "cost_benefit_ratio": [3.2, 2.1, 0.5],
                "pattern": ["Intensifying", "Persistent", "Never"],  # Add pattern
                "repair_count": [10, 5, 2],  # Add repair_count
                "recommended_action": [
                    "Immediate replacement",
                    "Schedule inspection",
                    "Monitor",
                ],
            }
        )

    def test_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert analyzer.hotspot_data is None
        assert analyzer.spacetime_data is None
        assert analyzer.emerging_data is None
        assert analyzer.priority_data is None

    @patch("pandas.read_csv")
    @patch("os.path.exists")
    def test_load_all_results_success(
        self,
        mock_exists,
        mock_read_csv,
        analyzer,
        sample_hotspot_data,
        sample_spacetime_data,
        sample_emerging_data,
        sample_priority_data,
    ):
        """Test successful loading of all results"""
        mock_exists.return_value = True

        # Configure mock returns in sequence
        mock_read_csv.side_effect = [
            sample_hotspot_data,  # hotspot data
            sample_spacetime_data,
            sample_emerging_data,
            sample_priority_data,
        ]

        analyzer.load_all_results("test_dir")

        assert analyzer.hotspot_data is not None
        assert analyzer.spacetime_data is not None
        assert analyzer.emerging_data is not None
        assert analyzer.priority_data is not None
        assert len(analyzer.hotspot_data) == 3

    @patch("os.path.exists")
    def test_load_all_results_missing_files(self, mock_exists, analyzer):
        """Test loading with missing files"""
        mock_exists.return_value = False

        # Should not raise, just leave data as None
        analyzer.load_all_results("nonexistent_dir")

        assert analyzer.hotspot_data is None
        assert analyzer.spacetime_data is None
        assert analyzer.emerging_data is None
        assert analyzer.priority_data is None

    def test_integrate_results_with_all_data(
        self,
        analyzer,
        sample_hotspot_data,
        sample_spacetime_data,
        sample_emerging_data,
        sample_priority_data,
    ):
        """Test integration of all results"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.spacetime_data = sample_spacetime_data
        analyzer.emerging_data = sample_emerging_data
        analyzer.priority_data = sample_priority_data

        result = analyzer.integrate_results()

        assert result is not None
        assert len(result) == 3
        # Priority data is used as base, so check for priority columns
        assert "priority_score" in result.columns
        assert "grid_id" in result.columns

    def test_integrate_results_missing_data(self, analyzer, sample_hotspot_data):
        """Test integration with missing data sources"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.spacetime_data = None
        analyzer.emerging_data = None
        analyzer.priority_data = None

        result = analyzer.integrate_results()

        assert result is not None
        assert len(result) == 3
        assert "gi_star_z" in result.columns

    def test_integrate_results_no_data(self, analyzer):
        """Test integration with no data"""
        result = analyzer.integrate_results()

        # Should return empty DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_create_priority_map(
        self, analyzer, sample_hotspot_data, sample_priority_data
    ):
        """Test priority map creation"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.priority_data = sample_priority_data
        # Add required integrated_results
        analyzer.integrated_results = sample_priority_data.copy()
        analyzer.integrated_results["grid_x"] = [127000, 127100, 127200]
        analyzer.integrated_results["grid_y"] = [37500, 37600, 37700]

        with patch("plotly.graph_objects.Figure") as mock_figure:
            with patch("plotly.graph_objects.Scattermapbox") as mock_scatter:
                mock_fig = MagicMock()
                mock_figure.return_value = mock_fig

                # Access the private method
                fig = analyzer._create_priority_map()

                assert fig == mock_fig

    def test_create_pattern_chart(self, analyzer, sample_emerging_data):
        """Test pattern chart creation"""
        analyzer.emerging_data = sample_emerging_data
        # Set integrated_results with pattern column
        analyzer.integrated_results = sample_emerging_data.copy()

        with patch("plotly.graph_objects.Figure") as mock_figure:
            mock_fig = MagicMock()
            mock_figure.return_value = mock_fig

            fig = analyzer._create_pattern_chart()

            assert mock_figure.called

    @patch("plotly.graph_objs.Figure")
    def test_create_timeseries_chart(
        self, mock_figure, analyzer, sample_spacetime_data
    ):
        """Test timeseries chart creation"""
        analyzer.spacetime_data = sample_spacetime_data

        fig = analyzer._create_timeseries_chart()

        assert fig is not None

    def test_create_priority_table(self, analyzer, sample_priority_data):
        """Test priority table creation"""
        analyzer.priority_data = sample_priority_data

        # Mock the entire dash module since it's not installed
        with patch("src.main26_integrated_spatial.DASH_AVAILABLE", False):
            # Since dash is not available, the method should return None
            table = analyzer._create_priority_table()

            # When dash is not available, the method returns None
            assert table is None

    def test_create_dashboard(
        self,
        analyzer,
        sample_hotspot_data,
        sample_priority_data,
        sample_emerging_data,
        sample_spacetime_data,
    ):
        """Test dashboard creation"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.priority_data = sample_priority_data
        analyzer.emerging_data = sample_emerging_data
        analyzer.spacetime_data = sample_spacetime_data

        # Since dash is not installed, test the no-dash scenario
        with patch("src.main26_integrated_spatial.DASH_AVAILABLE", False):
            # When dash is not available, the method should just print a message and return
            analyzer.create_dashboard(port=8050)
            # No assertion needed - just verify it doesn't crash

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_generate_executive_summary(
        self, mock_file, mock_mkdir, analyzer, sample_hotspot_data, sample_priority_data
    ):
        """Test executive summary generation"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.priority_data = sample_priority_data
        # Set integrated_results to avoid NoneType error
        analyzer.integrated_results = sample_priority_data.copy()

        analyzer.generate_executive_summary("test_output")

        assert mock_file.called

    @patch("pathlib.Path.mkdir")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.figure")
    def test_generate_pdf_report(
        self,
        mock_figure,
        mock_savefig,
        mock_mkdir,
        analyzer,
        sample_hotspot_data,
        sample_priority_data,
    ):
        """Test PDF report generation"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.priority_data = sample_priority_data
        analyzer.integrated_results = sample_priority_data  # Add integrated results

        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        analyzer.generate_pdf_report("test_output")

        assert mock_figure.called
        assert mock_savefig.called

    @patch("pathlib.Path.mkdir")
    def test_export_for_gis(self, mock_mkdir, analyzer, sample_hotspot_data):
        """Test GIS export functionality"""
        analyzer.hotspot_data = sample_hotspot_data
        # Add grid_x and grid_y columns to integrated_results
        analyzer.integrated_results = sample_hotspot_data.copy()
        analyzer.integrated_results["grid_x"] = [127000, 127100, 127200]
        analyzer.integrated_results["grid_y"] = [37500, 37600, 37700]

        with patch("geopandas.GeoDataFrame.to_file") as mock_to_file:
            analyzer.export_for_gis("test_output")

            assert mock_to_file.called

    @patch("pathlib.Path.mkdir")
    def test_save_integrated_results(
        self, mock_mkdir, analyzer, sample_hotspot_data, sample_priority_data
    ):
        """Test saving integrated results"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.priority_data = sample_priority_data
        analyzer.integrated_results = sample_priority_data

        with patch.object(sample_priority_data, "to_csv") as mock_to_csv:
            with patch("json.dump") as mock_json_dump:
                with patch("builtins.open", mock_open()) as mock_file:
                    analyzer.save_integrated_results("test_output")

                    assert mock_to_csv.called
                    assert mock_json_dump.called

    def test_handle_empty_dataframes(self, analyzer):
        """Test handling of empty DataFrames"""
        analyzer.hotspot_data = gpd.GeoDataFrame()
        analyzer.priority_data = pd.DataFrame()

        result = analyzer.integrate_results()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_merge_with_missing_columns(self, analyzer, sample_hotspot_data):
        """Test merging DataFrames with missing columns"""
        analyzer.hotspot_data = sample_hotspot_data

        # Create priority data with different columns
        analyzer.priority_data = pd.DataFrame(
            {"grid_id": [1, 2], "other_column": ["a", "b"]}
        )

        result = analyzer.integrate_results()

        assert result is not None
        assert "grid_id" in result.columns

    @patch("os.path.exists")
    def test_load_with_invalid_path(self, mock_exists, analyzer):
        """Test loading with invalid path"""
        mock_exists.return_value = False

        # Should not raise, just leave data as None
        analyzer.load_all_results("/invalid/path")

        assert analyzer.hotspot_data is None
        assert analyzer.priority_data is None

    def test_dashboard_without_dash(self, analyzer):
        """Test dashboard creation when Dash is not installed"""
        with patch("src.main26_integrated_spatial.DASH_AVAILABLE", False):
            # Should not raise, just print message and return
            analyzer.create_dashboard()
            # No assertion needed - just verify it doesn't crash

    def test_generate_summary_statistics(
        self, analyzer, sample_hotspot_data, sample_priority_data
    ):
        """Test summary statistics generation"""
        analyzer.hotspot_data = sample_hotspot_data
        analyzer.priority_data = sample_priority_data

        # Integration should calculate statistics
        result = analyzer.integrate_results()

        assert result is not None
        assert len(result) > 0

    def test_validate_data_consistency(
        self, analyzer, sample_hotspot_data, sample_priority_data
    ):
        """Test data consistency validation"""
        analyzer.hotspot_data = sample_hotspot_data

        # Create priority data with mismatched grid_ids
        analyzer.priority_data = pd.DataFrame(
            {
                "grid_id": [4, 5, 6],  # Different from hotspot grid_ids
                "priority_score": [50, 60, 70],
            }
        )

        result = analyzer.integrate_results()

        # Should handle mismatched data gracefully
        assert result is not None
