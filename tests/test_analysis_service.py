"""
Unit tests for Analysis Service
Tests the extracted perform_analysis functionality.
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.services.analysis_service import perform_analysis


class TestAnalysisService:
    """Test suite for the analysis service."""

    @pytest.fixture
    def sample_test_data(self):
        """Create sample test data matching actual CSV format."""
        return pd.DataFrame(
            {
                "Overall status": [
                    "SUCCESS",
                    "FAILURE",
                    "SUCCESS",
                    "ERROR",
                    "FAILURE",
                    "SUCCESS",
                ],
                "Station ID": [
                    "radi135",
                    "radi138",
                    "radi135",
                    "radi162",
                    "radi138",
                    "radi135",
                ],
                "Model": [
                    "iPhone14ProMax",
                    "iPhone15Pro",
                    "iPhone14ProMax",
                    "iPhone16",
                    "iPhone15Pro",
                    "iPhone14ProMax",
                ],
                "result_FAIL": [
                    "",
                    "Camera Pictures",
                    "",
                    "6A-Display Fail",
                    "AQA_Microphone",
                    "",
                ],
                "Date": [
                    "1/2/2025",
                    "1/2/2025",
                    "1/2/2025",
                    "1/2/2025",
                    "1/2/2025",
                    "1/3/2025",
                ],
                "Serial Number": [
                    "ABC123",
                    "DEF456",
                    "GHI789",
                    "JKL012",
                    "MNO345",
                    "PQR678",
                ],
                "Operator": [
                    "TestOp1",
                    "TestOp2",
                    "TestOp1",
                    "TestOp3",
                    "TestOp2",
                    "TestOp1",
                ],
            }
        )

    @pytest.fixture
    def empty_dataframe(self):
        """Create an empty DataFrame for error testing."""
        return pd.DataFrame()

    @pytest.fixture
    def missing_columns_data(self):
        """Create DataFrame with missing required columns."""
        return pd.DataFrame(
            {
                "Overall status": ["SUCCESS", "FAILURE"],
                "Model": ["iPhone14ProMax", "iPhone15Pro"],
                # Missing Station ID, result_FAIL, Date columns
            }
        )

    def test_perform_analysis_basic_functionality(self, sample_test_data):
        """Test that perform_analysis returns expected structure."""
        result = perform_analysis(sample_test_data)

        # Should return 8-item tuple
        assert len(result) == 8

        (
            summary,
            overall_chart,
            stations_chart,
            models_chart,
            test_cases_chart,
            stations_data,
            models_data,
            test_cases_data,
        ) = result

        # Validate summary
        assert isinstance(summary, str)
        assert "Total Tests: 6" in summary
        assert "Pass Rate:" in summary
        assert "Valid Tests: 6" in summary
        assert "Success: 3" in summary
        assert "Failures: 2" in summary
        assert "Errors: 1" in summary

        # Calculate expected pass rate: 3 successes out of 6 valid tests = 50%
        assert "Pass Rate: 50.00%" in summary

        # Validate charts are not None
        assert overall_chart is not None
        assert isinstance(overall_chart, go.Figure)
        assert stations_chart is not None
        assert isinstance(stations_chart, go.Figure)
        assert models_chart is not None
        assert isinstance(models_chart, go.Figure)
        assert test_cases_chart is not None
        assert isinstance(test_cases_chart, go.Figure)

        # Validate data lists
        assert isinstance(stations_data, list)
        assert isinstance(models_data, list)
        assert isinstance(test_cases_data, list)

        # Validate data structure - each item should be a list with 3 elements: [name, count, percentage]
        if stations_data:  # Only check if there's data
            assert len(stations_data[0]) == 3
            assert isinstance(stations_data[0][0], str)  # Station name
            assert isinstance(stations_data[0][1], (int, np.integer))  # Count
            assert isinstance(stations_data[0][2], (float, int))  # Percentage

        if models_data:
            assert len(models_data[0]) == 3
            assert isinstance(models_data[0][0], str)  # Model name
            assert isinstance(models_data[0][1], (int, np.integer))  # Count
            assert isinstance(models_data[0][2], (float, int))  # Percentage

    def test_empty_dataframe_handling(self, empty_dataframe):
        """Test graceful handling of empty DataFrame."""
        # With @capture_exceptions decorator, this should return default error value instead of raising
        result = perform_analysis(empty_dataframe)

        # Should return the error tuple from @capture_exceptions
        expected_error_result = (None, None, None, None, None, [], [], [])
        assert result == expected_error_result

    def test_missing_required_columns(self, missing_columns_data):
        """Test handling of DataFrame with missing required columns."""
        # With @capture_exceptions decorator, this should return default error value instead of raising
        result = perform_analysis(missing_columns_data)

        # Should return the error tuple from @capture_exceptions
        expected_error_result = (None, None, None, None, None, [], [], [])
        assert result == expected_error_result

    def test_data_quality_with_nulls(self):
        """Test handling of null values in data."""
        df_with_nulls = pd.DataFrame(
            {
                "Overall status": ["SUCCESS", None, "FAILURE", "ERROR"],
                "Station ID": ["radi135", "radi138", None, "radi162"],
                "Model": ["iPhone14ProMax", None, "iPhone15Pro", "iPhone16"],
                "result_FAIL": ["", "Camera Pictures", "AQA_Microphone", ""],
                "Date": ["1/2/2025", "1/2/2025", None, "1/2/2025"],
            }
        )

        result = perform_analysis(df_with_nulls)
        summary = result[0]

        # Should handle nulls gracefully
        assert "Total Tests: 4" in summary
        assert "Valid Tests: 3" in summary  # Only 3 have non-null status

    def test_analysis_with_no_failures(self):
        """Test analysis when all tests are successful."""
        success_only_data = pd.DataFrame(
            {
                "Overall status": ["SUCCESS", "SUCCESS", "SUCCESS"],
                "Station ID": ["radi135", "radi138", "radi135"],
                "Model": ["iPhone14ProMax", "iPhone15Pro", "iPhone14ProMax"],
                "result_FAIL": ["", "", ""],
                "Date": ["1/2/2025", "1/2/2025", "1/2/2025"],
            }
        )

        result = perform_analysis(success_only_data)

        # Check if error occurred (result would be None tuple)
        if result == (None, None, None, None, None, [], [], []):
            pytest.fail(
                "Analysis failed when it should have succeeded with no failures"
            )

        summary = result[0]

        assert "Total Tests: 3" in summary
        assert "Success: 3" in summary
        assert "Failures: 0" in summary
        assert "Errors: 0" in summary
        assert "Pass Rate: 100.00%" in summary

        # Data lists should be empty since there are no failures
        stations_data, models_data, test_cases_data = result[5], result[6], result[7]
        assert len(stations_data) == 0
        assert len(models_data) == 0

    def test_analysis_with_large_dataset(self):
        """Test analysis performance with larger dataset."""
        # Create a larger dataset (1000 rows)
        large_data = pd.DataFrame(
            {
                "Overall status": ["SUCCESS", "FAILURE", "ERROR"] * 334,  # 1002 total
                "Station ID": [f"radi{i%10}" for i in range(1002)],
                "Model": ["iPhone14ProMax", "iPhone15Pro", "iPhone16"] * 334,
                "result_FAIL": ["", "Camera Pictures", "6A-Display Fail"] * 334,
                "Date": ["1/2/2025"] * 1002,
            }
        )

        result = perform_analysis(large_data)
        summary = result[0]

        assert "Total Tests: 1,002" in summary
        # Should complete without errors and return valid structure
        assert len(result) == 8

    def test_chart_titles_and_structure(self, sample_test_data):
        """Test that charts have correct titles and structure."""
        result = perform_analysis(sample_test_data)

        (
            summary,
            overall_chart,
            stations_chart,
            models_chart,
            test_cases_chart,
            stations_data,
            models_data,
            test_cases_data,
        ) = result

        # Check chart titles
        assert "Overall Test Status Distribution" in overall_chart.layout.title.text
        assert "Top 10 Failing Stations" in stations_chart.layout.title.text
        assert "Top 10 Failing Models" in models_chart.layout.title.text
        assert "Top 10 Failing Test Cases" in test_cases_chart.layout.title.text

        # Check that charts have data
        assert len(overall_chart.data) > 0
        assert len(stations_chart.data) > 0
        assert len(models_chart.data) > 0
        assert len(test_cases_chart.data) > 0

    def test_date_range_in_summary(self, sample_test_data):
        """Test that date range is correctly included in summary."""
        result = perform_analysis(sample_test_data)
        summary = result[0]

        # Should contain date range information
        assert "Data Range:" in summary
        # Should contain analysis timestamp
        assert "Analysis Time:" in summary

        # Verify timestamp format (should be recent)
        lines = summary.split("\n")
        analysis_time_line = [
            line for line in lines if line.startswith("Analysis Time:")
        ][0]
        timestamp_str = analysis_time_line.split("Analysis Time: ")[1]

        # Should be able to parse the timestamp
        parsed_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        assert isinstance(parsed_time, datetime)

    def test_percentage_calculations(self, sample_test_data):
        """Test that percentage calculations in data tables are correct."""
        result = perform_analysis(sample_test_data)

        (
            summary,
            overall_chart,
            stations_chart,
            models_chart,
            test_cases_chart,
            stations_data,
            models_data,
            test_cases_data,
        ) = result

        # From sample data: 6 total tests, 2 failures + 1 error = 3 failing tests
        # Station failures: radi138 (2 times), radi162 (1 time)
        # Model failures: iPhone15Pro (2 times), iPhone16 (1 time)

        if stations_data:
            # Check that percentages are calculated correctly
            for station_row in stations_data:
                station_name, count, percentage = station_row
                expected_percentage = round((count / 6 * 100), 2)  # 6 valid tests
                assert percentage == expected_percentage

        if models_data:
            for model_row in models_data:
                model_name, count, percentage = model_row
                expected_percentage = round((count / 6 * 100), 2)  # 6 valid tests
                assert percentage == expected_percentage

        if test_cases_data:
            for test_row in test_cases_data:
                test_name, count, percentage = test_row
                # Test case percentages are calculated against failed tests (2 failures total)
                expected_percentage = round((count / 2 * 100), 2) if 2 > 0 else 0
                assert percentage == expected_percentage


# Import numpy for type checking in tests
import numpy as np
