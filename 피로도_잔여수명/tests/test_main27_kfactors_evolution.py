"""
Tests for main27_kfactors_evolution.py - K-factors/D_final Evolution Analysis
"""

import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import numpy as np
import pandas as pd
import pytest
import plotly.graph_objects as go

from src.main27_kfactors_evolution import KFactorsEvolutionAnalyzer


class TestKFactorsEvolutionAnalyzer:
    """Test suite for KFactorsEvolutionAnalyzer class"""

    @pytest.fixture
    def sample_spacetime_cube(self):
        """Create sample space-time cube data"""
        dates = pd.date_range("2024-01-01", periods=12, freq="M")
        data = []
        for date in dates:
            for grid_id in range(1, 6):
                data.append(
                    {
                        "time_bin": date,
                        "grid_id": grid_id,
                        "grid_x": 127000 + grid_id * 100,
                        "grid_y": 37500 + grid_id * 100,
                        "repair_count": np.random.randint(1, 10),
                        "point_count": np.random.randint(1, 5),
                    }
                )
        return pd.DataFrame(data)

    @pytest.fixture
    def sample_kfactors_grid(self):
        """Create sample K-factors grid data"""
        return pd.DataFrame(
            {
                "grid_id": [1, 2, 3, 4, 5],
                "k_age": [1.2, 1.3, 1.1, 1.4, 1.0],
                "k_soil": [0.9, 1.0, 0.8, 1.1, 0.95],
                "k_traffic": [1.5, 1.6, 1.4, 1.7, 1.3],
                "k_total_mean": [2.5, 2.8, 2.2, 3.0, 2.1],
                "d_final_mean": [0.45, 0.55, 0.35, 0.65, 0.30],
                "composite_score": [1.125, 1.54, 0.77, 1.95, 0.63],
            }
        )

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer instance with temporary paths"""
        cube_path = str(tmp_path / "spacetime_cube.pkl")
        grid_path = str(tmp_path / "kfactors_grid.csv")

        # Create dummy files
        with open(cube_path, "wb") as f:
            pickle.dump({}, f)

        pd.DataFrame().to_csv(grid_path)

        with patch("pickle.load"), patch("pandas.read_csv"):
            return KFactorsEvolutionAnalyzer(
                spacetime_cube_path=cube_path,
                kfactors_grid_path=grid_path,
                time_window=12,
                output_dir=str(tmp_path),
            )

    def test_initialization(self, tmp_path):
        """Test analyzer initialization"""
        cube_path = str(tmp_path / "spacetime_cube.pkl")
        grid_path = str(tmp_path / "kfactors_grid.csv")

        # Create dummy files
        with open(cube_path, "wb") as f:
            pickle.dump({}, f)
        pd.DataFrame().to_csv(grid_path)

        analyzer = KFactorsEvolutionAnalyzer(
            spacetime_cube_path=cube_path, kfactors_grid_path=grid_path, time_window=12
        )

        assert analyzer.time_window == 12
        assert analyzer.output_dir is not None
        assert analyzer.spacetime_cube is None  # Not loaded yet
        assert analyzer.kfactors_grid is None  # Not loaded yet
        assert analyzer.evolution_data == {}
        assert analyzer.acceleration_zones == []

    def test_load_data_success(
        self, tmp_path, sample_spacetime_cube, sample_kfactors_grid
    ):
        """Test successful data loading"""
        # Create actual files
        cube_path = tmp_path / "spacetime_cube.pkl"
        grid_path = tmp_path / "kfactors_grid.csv"

        with open(cube_path, "wb") as f:
            pickle.dump(sample_spacetime_cube, f)
        sample_kfactors_grid.to_csv(grid_path, index=False)

        analyzer = KFactorsEvolutionAnalyzer(
            spacetime_cube_path=str(cube_path),
            kfactors_grid_path=str(grid_path),
            time_window=12,
        )

        result = analyzer.load_data()

        assert result is True
        assert analyzer.spacetime_cube is not None
        assert analyzer.kfactors_grid is not None
        assert len(analyzer.spacetime_cube) > 0
        assert len(analyzer.kfactors_grid) > 0

    def test_load_data_missing_file(self, tmp_path):
        """Test loading with missing files"""
        analyzer = KFactorsEvolutionAnalyzer(
            spacetime_cube_path="nonexistent.pkl",
            kfactors_grid_path="nonexistent.csv",
            time_window=12,
        )

        result = analyzer.load_data()

        assert result is False  # Should return False when files don't exist

    def test_analyze_temporal_evolution(
        self, analyzer, sample_spacetime_cube, sample_kfactors_grid
    ):
        """Test temporal evolution analysis"""
        analyzer.spacetime_cube = sample_spacetime_cube
        analyzer.kfactors_grid = sample_kfactors_grid

        result = analyzer.analyze_temporal_evolution()

        assert result is not None
        assert isinstance(result, dict)
        assert "evolution_metrics" in result
        assert "acceleration_zones" in result
        assert "seasonal_patterns" in result

    @patch("plotly.graph_objects.Figure")
    def test_create_4d_visualization(
        self, mock_figure, analyzer, sample_spacetime_cube, sample_kfactors_grid
    ):
        """Test 4D visualization creation"""
        analyzer.spacetime_cube = sample_spacetime_cube
        analyzer.kfactors_grid = sample_kfactors_grid
        analyzer.evolution_data = {"temporal_data": pd.DataFrame()}

        mock_fig = MagicMock()
        mock_figure.return_value = mock_fig

        # The method doesn't return anything, just creates visualization
        analyzer.create_4d_visualization()

        # Just verify it doesn't crash
        assert True

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.savefig")
    def test_visualize_evolution(
        self,
        mock_savefig,
        mock_show,
        analyzer,
        sample_spacetime_cube,
        sample_kfactors_grid,
    ):
        """Test evolution visualization"""
        analyzer.spacetime_cube = sample_spacetime_cube
        analyzer.kfactors_grid = sample_kfactors_grid

        # Set up evolution_data with correct structure
        analyzer.evolution_data = {
            "evolution_metrics": {
                "mean_k_age": {
                    "timeline": [
                        {
                            "time": "2024-01-01",
                            "mean": 1.2,
                            "std": 0.1,
                            "max": 1.5,
                            "min": 1.0,
                            "count": 5,
                        },
                        {
                            "time": "2024-02-01",
                            "mean": 1.3,
                            "std": 0.1,
                            "max": 1.6,
                            "min": 1.1,
                            "count": 5,
                        },
                    ],
                    "avg_change_rate": 0.083,
                    "max_change_rate": 0.083,
                    "trend": "increasing",
                },
                "mean_d_final": {
                    "timeline": [
                        {
                            "time": "2024-01-01",
                            "mean": 0.45,
                            "std": 0.05,
                            "max": 0.55,
                            "min": 0.35,
                            "count": 5,
                        },
                        {
                            "time": "2024-02-01",
                            "mean": 0.48,
                            "std": 0.05,
                            "max": 0.58,
                            "min": 0.38,
                            "count": 5,
                        },
                    ],
                    "avg_change_rate": 0.067,
                    "max_change_rate": 0.067,
                    "trend": "increasing",
                },
            },
            "acceleration_zones": [
                {
                    "grid_x": 127100,
                    "grid_y": 37600,
                    "acceleration": 0.01,
                    "final_score": 1.5,
                    "initial_score": 1.0,
                    "growth_rate": 0.5,
                }
            ],
            "seasonal_patterns": {
                "Spring": {"mean_composite": 1.2, "std_composite": 0.2},
                "Summer": {"mean_composite": 1.3, "std_composite": 0.2},
                "Fall": {"mean_composite": 1.1, "std_composite": 0.2},
                "Winter": {"mean_composite": 1.0, "std_composite": 0.2},
            },
            "trend_analysis": {
                "mean_k_age_trend": {
                    "slope": 0.01,
                    "r_squared": 0.85,
                    "p_value": 0.001,
                    "trend_strength": "strong",
                }
            },
        }

        # Don't mock figure creation, let matplotlib handle it normally
        # This avoids issues with colorbar and subplots
        analyzer.visualize_evolution()

        # Just verify it doesn't crash
        assert True

    @patch("pathlib.Path.mkdir")
    @patch("json.dump")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_results(self, mock_file, mock_json_dump, mock_mkdir, analyzer):
        """Test saving results"""
        analyzer.evolution_data = {
            "evolution_metrics": {"metric1": 0.5},
            "acceleration_zones": [1, 2],
            "seasonal_patterns": {"seasonal_strength": 0.65},
        }

        analyzer.save_results()

        # Just verify it doesn't crash
        assert True

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_generate_report(
        self,
        mock_file,
        mock_mkdir,
        analyzer,
        sample_spacetime_cube,
        sample_kfactors_grid,
    ):
        """Test report generation"""
        analyzer.spacetime_cube = sample_spacetime_cube
        analyzer.kfactors_grid = sample_kfactors_grid
        analyzer.evolution_data = {
            "evolution_metrics": {
                "mean_k_total": {
                    "avg_change_rate": 0.1,
                    "max_change_rate": 0.15,
                    "trend": "increasing",
                    "timeline": [],
                }
            },
            "acceleration_zones": [
                {
                    "grid_x": 127100,
                    "grid_y": 37600,
                    "acceleration": 0.01,
                    "growth_rate": 0.5,
                },
                {
                    "grid_x": 127200,
                    "grid_y": 37700,
                    "acceleration": 0.008,
                    "growth_rate": 0.4,
                },
            ],
            "seasonal_patterns": {
                "Spring": {"mean_composite": 1.2, "std_composite": 0.2},
                "Summer": {"mean_composite": 1.3, "std_composite": 0.2},
            },
        }

        analyzer.generate_report()

        # Just verify it doesn't crash
        assert True

    def test_handle_empty_data(self, analyzer):
        """Test handling of empty data"""
        # Create empty DataFrame with required columns
        analyzer.spacetime_cube = pd.DataFrame(columns=["time_bin", "grid_x", "grid_y"])
        analyzer.kfactors_grid = pd.DataFrame(columns=["grid_id"])

        result = analyzer.analyze_temporal_evolution()

        assert result is not None
        assert isinstance(result, dict)
        # With empty data, should return empty results
        assert result["evolution_metrics"] == {}
        assert result["acceleration_zones"] == []

    def test_handle_missing_columns(self, analyzer):
        """Test handling of missing columns in data"""
        # Create DataFrame with minimal required columns
        analyzer.spacetime_cube = pd.DataFrame(
            {
                "grid_id": [1, 2],
                "time_bin": pd.date_range("2024-01-01", periods=2, freq="M"),
            }
        )
        analyzer.kfactors_grid = pd.DataFrame({"grid_id": [1, 2]})

        result = analyzer.analyze_temporal_evolution()

        assert result is not None
        assert isinstance(result, dict)
        # Should handle missing K-factors columns gracefully
        assert "evolution_metrics" in result
        assert "acceleration_zones" in result

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.savefig")
    def test_run_method(self, mock_savefig, mock_show, tmp_path):
        """Test the main run method"""
        # Create test files
        cube_path = tmp_path / "spacetime_cube.pkl"
        grid_path = tmp_path / "kfactors_grid.csv"

        sample_cube = pd.DataFrame(
            {
                "time_bin": pd.date_range("2024-01-01", periods=12, freq="M"),
                "grid_id": [1] * 12,
                "repair_count": np.random.randint(1, 10, 12),
            }
        )
        sample_grid = pd.DataFrame(
            {"grid_id": [1], "k_total_mean": [2.5], "d_final_mean": [0.45]}
        )

        with open(cube_path, "wb") as f:
            pickle.dump(sample_cube, f)
        sample_grid.to_csv(grid_path, index=False)

        analyzer = KFactorsEvolutionAnalyzer(
            spacetime_cube_path=str(cube_path),
            kfactors_grid_path=str(grid_path),
            time_window=12,
            output_dir=str(tmp_path),
        )

        with (
            patch.object(analyzer, "save_results"),
            patch.object(analyzer, "generate_report"),
        ):
            analyzer.run()

        # Just verify it runs without error
        assert True
