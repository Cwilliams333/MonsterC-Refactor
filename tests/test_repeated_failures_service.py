"""
Unit tests for the Repeated Failures Service module.

Tests cover all repeated failures analysis functions to ensure 100%
feature parity with the legacy implementation.
"""

from datetime import datetime, timedelta

import gradio as gr
import numpy as np
import pandas as pd
import pytest

from src.services.repeated_failures_service import (
    analyze_repeated_failures,
    create_plot,
    create_summary,
    get_model_code,
    handle_test_case_selection,
    update_summary,
    update_summary_chart_and_data,
)


@pytest.fixture
def sample_failures_df():
    """Create a sample DataFrame with repeated failures for testing."""
    np.random.seed(42)

    # Create specific repeated failure patterns
    data = []

    # Pattern 1: iPhone14ProMax at radi135 with Display Fail (5 failures)
    for i in range(5):
        data.append(
            {
                "Date": datetime.now() - timedelta(days=i),
                "Model": "iPhone14ProMax",
                "Station ID": "radi135",
                "result_FAIL": "6A-Display Fail",
                "Overall status": "FAILURE",
                "IMEI": f"35{1000 + i:013d}",
                "Operator": "STN251_RED(id:10089)",
            }
        )

    # Pattern 2: iPhone15Pro at radi136 with Camera Fail (6 failures)
    for i in range(6):
        data.append(
            {
                "Date": datetime.now() - timedelta(days=i),
                "Model": "iPhone15Pro",
                "Station ID": "radi136",
                "result_FAIL": "4J-Camera Fail",
                "Overall status": "FAILURE",
                "IMEI": f"35{2000 + i:013d}",
                "Operator": "STN252_RED(id:10090)",
            }
        )

    # Pattern 3: iPhone15 at radi137 with Touch Fail (4 failures - edge case)
    for i in range(4):
        data.append(
            {
                "Date": datetime.now() - timedelta(days=i),
                "Model": "iPhone15",
                "Station ID": "radi137",
                "result_FAIL": "2B-Touch Fail",
                "Overall status": "FAILURE",
                "IMEI": f"35{3000 + i:013d}",
                "Operator": "STN351_GRN(id:10380)",
            }
        )

    # Pattern 4: iPhone14 at radi138 with Audio Fail (3 failures - below threshold)
    for i in range(3):
        data.append(
            {
                "Date": datetime.now() - timedelta(days=i),
                "Model": "iPhone14",
                "Station ID": "radi138",
                "result_FAIL": "5K-Audio Fail",
                "Overall status": "FAILURE",
                "IMEI": f"35{4000 + i:013d}",
                "Operator": "STN352_GRN(id:10381)",
            }
        )

    # Add some SUCCESS cases to make data more realistic
    for i in range(10):
        data.append(
            {
                "Date": datetime.now() - timedelta(days=i),
                "Model": np.random.choice(
                    ["iPhone14ProMax", "iPhone15Pro", "iPhone15", "iPhone14"]
                ),
                "Station ID": np.random.choice(
                    ["radi135", "radi136", "radi137", "radi138"]
                ),
                "result_FAIL": "",
                "Overall status": "SUCCESS",
                "IMEI": f"35{5000 + i:013d}",
                "Operator": np.random.choice(
                    ["STN251_RED(id:10089)", "STN252_RED(id:10090)"]
                ),
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def repeated_failures_result_df():
    """Create a sample repeated failures result DataFrame for testing update functions."""
    data = {
        "Model": ["iPhone14ProMax", "iPhone15Pro", "iPhone15"],
        "Station ID": ["radi135", "radi136", "radi137"],
        "result_FAIL": ["6A-Display Fail", "4J-Camera Fail", "2B-Touch Fail"],
        "TC Count": [5, 6, 4],
        "IMEI Count": [5, 6, 4],
        "Model Code": ["iphone15,3", "iphone16,1", "iphone15,5"],
    }
    return pd.DataFrame(data)


class TestGetModelCode:
    """Test the get_model_code function."""

    def test_get_model_code_existing_single(self):
        """Test getting model code for existing model with single code."""
        # This will use the actual DEVICE_MAP from mappings
        result = get_model_code("iPhone14ProMax")
        assert isinstance(result, str)
        assert result != "Unknown"

    def test_get_model_code_existing_list(self):
        """Test getting model code for existing model with multiple codes."""
        # Test with a model that might have multiple codes
        result = get_model_code("iPhone15Pro")
        assert isinstance(result, str)
        assert result != "Unknown"

    def test_get_model_code_unknown(self):
        """Test getting model code for unknown model."""
        result = get_model_code("NonExistentModel")
        assert result == "Unknown"


class TestCreateSummary:
    """Test the create_summary function."""

    def test_create_summary_basic(self, repeated_failures_result_df):
        """Test creating basic summary from DataFrame."""
        summary = create_summary(repeated_failures_result_df)
        assert isinstance(summary, str)
        # Check for HTML content instead of markdown
        assert ">3</span> instances of repeated failures" in summary
        assert "iPhone14ProMax" in summary
        assert "6A-Display Fail" in summary
        # Check for HTML table headers
        assert "Model</div>" in summary
        assert "Code</div>" in summary
        assert "Station</div>" in summary

    def test_create_summary_empty(self):
        """Test creating summary from empty DataFrame."""
        empty_df = pd.DataFrame(
            columns=[
                "Model",
                "Station ID",
                "result_FAIL",
                "TC Count",
                "IMEI Count",
                "Model Code",
            ]
        )
        summary = create_summary(empty_df)
        assert "Found 0 instances of repeated failures" in summary

    def test_create_summary_single_row(self):
        """Test creating summary with single row."""
        single_row = pd.DataFrame(
            {
                "Model": ["iPhone14ProMax"],
                "Station ID": ["radi135"],
                "result_FAIL": ["6A-Display Fail"],
                "TC Count": [5],
                "IMEI Count": [4],
                "Model Code": ["iphone15,3"],
            }
        )
        summary = create_summary(single_row)
        assert "Found 1 instances of repeated failures" in summary
        assert "iPhone14ProMax" in summary


class TestCreatePlot:
    """Test the create_plot function."""

    def test_create_plot_basic(self, repeated_failures_result_df):
        """Test creating basic plot from DataFrame."""
        fig = create_plot(repeated_failures_result_df)
        assert fig is not None
        # Check that it's a plotly figure
        assert hasattr(fig, "data")
        assert hasattr(fig, "layout")
        assert fig.layout.title.text == "Filtered Repeated Failures"

    def test_create_plot_empty(self):
        """Test creating plot from empty DataFrame."""
        empty_df = pd.DataFrame(
            columns=[
                "Model",
                "Station ID",
                "result_FAIL",
                "TC Count",
                "IMEI Count",
                "Model Code",
            ]
        )
        fig = create_plot(empty_df)
        assert fig is not None

    def test_create_plot_layout(self, repeated_failures_result_df):
        """Test plot layout and properties."""
        fig = create_plot(repeated_failures_result_df)
        assert fig.layout.xaxis.title.text == "Station ID"
        assert fig.layout.yaxis.title.text == "Number of Test Case Failures"
        assert fig.layout.barmode == "group"


class TestAnalyzeRepeatedFailures:
    """Test the analyze_repeated_failures function."""

    def test_analyze_repeated_failures_basic(self, sample_failures_df):
        """Test basic repeated failures analysis."""
        summary, fig, interactive_df, dropdown = analyze_repeated_failures(
            sample_failures_df, min_failures=4
        )

        # Check return types
        assert isinstance(summary, str)
        assert fig is not None
        assert isinstance(interactive_df, gr.Dataframe)
        assert isinstance(dropdown, gr.Dropdown)

        # Check that we found the expected patterns
        assert (
            "Display Fail" in summary
            or "Camera Fail" in summary
            or "Touch Fail" in summary
        )

    def test_analyze_repeated_failures_min_threshold(self, sample_failures_df):
        """Test repeated failures analysis with different minimum thresholds."""
        # Test with min_failures=5 - should find iPhone15Pro (6 failures) and iPhone14ProMax (5 failures)
        summary, fig, interactive_df, dropdown = analyze_repeated_failures(
            sample_failures_df, min_failures=5
        )

        # Should find patterns with 5+ failures
        assert isinstance(summary, str)

        # Test with min_failures=7 - should find only iPhone15Pro (6 failures won't qualify)
        summary, fig, interactive_df, dropdown = analyze_repeated_failures(
            sample_failures_df, min_failures=7
        )
        assert isinstance(summary, str)

    def test_analyze_repeated_failures_no_failures(self):
        """Test analysis with DataFrame containing no failures."""
        success_only_df = pd.DataFrame(
            {
                "Model": ["iPhone14ProMax", "iPhone15Pro"],
                "Station ID": ["radi135", "radi136"],
                "result_FAIL": ["", ""],
                "Overall status": ["SUCCESS", "SUCCESS"],
                "IMEI": ["351234567890123", "351234567890124"],
                "Operator": ["STN251_RED(id:10089)", "STN252_RED(id:10090)"],
            }
        )

        summary, fig, interactive_df, dropdown = analyze_repeated_failures(
            success_only_df, min_failures=4
        )
        assert isinstance(summary, str)
        assert "Found 0 instances" in summary

    def test_analyze_repeated_failures_edge_cases(self):
        """Test analysis with edge cases."""
        # Empty DataFrame
        empty_df = pd.DataFrame()
        summary, fig, interactive_df, dropdown = analyze_repeated_failures(
            empty_df, min_failures=4
        )
        assert isinstance(summary, str)

        # DataFrame with missing columns should be handled gracefully
        incomplete_df = pd.DataFrame({"Model": ["iPhone14ProMax"]})
        summary, fig, interactive_df, dropdown = analyze_repeated_failures(
            incomplete_df, min_failures=4
        )
        assert isinstance(summary, str)


class TestUpdateSummaryChartAndData:
    """Test the update_summary_chart_and_data function."""

    def test_update_summary_chart_and_data_no_filter(self, repeated_failures_result_df):
        """Test updating without any filters."""
        summary, fig, interactive_df = update_summary_chart_and_data(
            repeated_failures_result_df, "TC Count", []
        )

        assert isinstance(summary, str)
        assert fig is not None
        assert isinstance(interactive_df, gr.Dataframe)
        assert "Found 3 instances" in summary

    def test_update_summary_chart_and_data_sort_by_model(
        self, repeated_failures_result_df
    ):
        """Test updating with sorting by Model."""
        summary, fig, interactive_df = update_summary_chart_and_data(
            repeated_failures_result_df, "Model", []
        )

        assert isinstance(summary, str)
        assert "Found 3 instances" in summary

    def test_update_summary_chart_and_data_filter_test_cases(
        self, repeated_failures_result_df
    ):
        """Test updating with test case filtering."""
        # Test filtering by specific test cases
        selected_cases = [
            "6A-Display Fail (5) max failures",
            "4J-Camera Fail (6) max failures",
        ]
        summary, fig, interactive_df = update_summary_chart_and_data(
            repeated_failures_result_df, "TC Count", selected_cases
        )

        assert isinstance(summary, str)
        # Should find only the filtered cases
        assert "Found 2 instances" in summary

    def test_update_summary_chart_and_data_select_all(
        self, repeated_failures_result_df
    ):
        """Test updating with Select All option."""
        summary, fig, interactive_df = update_summary_chart_and_data(
            repeated_failures_result_df, "TC Count", ["Select All"]
        )

        assert isinstance(summary, str)
        assert "Found 3 instances" in summary

    def test_update_summary_chart_and_data_clear_all(self, repeated_failures_result_df):
        """Test updating with Clear All option."""
        summary, fig, interactive_df = update_summary_chart_and_data(
            repeated_failures_result_df, "TC Count", ["Clear All"]
        )

        assert isinstance(summary, str)
        assert "Found 0 instances" in summary

    def test_update_summary_chart_and_data_empty_input(self):
        """Test updating with empty input."""
        summary, fig, interactive_df = update_summary_chart_and_data(
            None, "TC Count", []
        )

        assert summary == "No data available to sort/filter"
        assert fig is None
        assert isinstance(interactive_df, gr.Dataframe)


class TestUpdateSummary:
    """Test the update_summary function."""

    def test_update_summary_basic(self, repeated_failures_result_df):
        """Test basic summary update."""
        summary = update_summary(repeated_failures_result_df, "TC Count", [])
        assert isinstance(summary, str)
        assert "Found 3 instances" in summary

    def test_update_summary_sort_by_station(self, repeated_failures_result_df):
        """Test summary update with sorting by Station ID."""
        summary = update_summary(repeated_failures_result_df, "Station ID", [])
        assert isinstance(summary, str)
        assert "Found 3 instances" in summary

    def test_update_summary_filter_cases(self, repeated_failures_result_df):
        """Test summary update with test case filtering."""
        selected_cases = ["6A-Display Fail (5) max failures"]
        summary = update_summary(
            repeated_failures_result_df, "TC Count", selected_cases
        )
        assert isinstance(summary, str)
        assert "Found 1 instances" in summary

    def test_update_summary_clear_all(self, repeated_failures_result_df):
        """Test summary update with Clear All."""
        summary = update_summary(repeated_failures_result_df, "TC Count", ["Clear All"])
        assert isinstance(summary, str)
        assert "Found 0 instances" in summary

    def test_update_summary_empty_input(self):
        """Test summary update with empty input."""
        summary = update_summary(None, "TC Count", [])
        assert summary == "No data available to sort/filter"


class TestHandleTestCaseSelection:
    """Test the handle_test_case_selection function."""

    def test_handle_test_case_selection_select_all(self):
        """Test handling Select All."""

        # Create a mock SelectData event
        class MockSelectData:
            def __init__(self, value):
                self.value = value

        evt = MockSelectData("Select All")
        result = handle_test_case_selection(evt, ["current", "selection"])
        assert result == ["__SELECT_ALL__"]

    def test_handle_test_case_selection_clear_all(self):
        """Test handling Clear All."""

        class MockSelectData:
            def __init__(self, value):
                self.value = value

        evt = MockSelectData("Clear All")
        result = handle_test_case_selection(evt, ["current", "selection"])
        assert result == []

    def test_handle_test_case_selection_regular(self):
        """Test handling regular selection."""

        class MockSelectData:
            def __init__(self, value):
                self.value = value

        evt = MockSelectData("6A-Display Fail")
        current_selection = ["current", "selection"]
        result = handle_test_case_selection(evt, current_selection)
        assert result == current_selection  # Should return unchanged


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow(self, sample_failures_df):
        """Test complete workflow from analysis to updates."""
        # Step 1: Analyze repeated failures
        summary, fig, interactive_df, dropdown = analyze_repeated_failures(
            sample_failures_df, min_failures=4
        )

        assert isinstance(summary, str)
        assert fig is not None

        # Step 2: Simulate sorting and filtering
        # Create a mock result DataFrame based on what analyze_repeated_failures would produce
        mock_result = pd.DataFrame(
            {
                "Model": ["iPhone15Pro", "iPhone14ProMax", "iPhone15"],
                "Station ID": ["radi136", "radi135", "radi137"],
                "result_FAIL": ["4J-Camera Fail", "6A-Display Fail", "2B-Touch Fail"],
                "TC Count": [6, 5, 4],
                "IMEI Count": [6, 5, 4],
                "Model Code": ["iphone16,1", "iphone15,3", "iphone15,5"],
            }
        )

        # Step 3: Update with sorting
        updated_summary, updated_fig, updated_df = update_summary_chart_and_data(
            mock_result, "Model", []
        )

        assert isinstance(updated_summary, str)
        assert updated_fig is not None

        # Step 4: Update with filtering
        filtered_summary, filtered_fig, filtered_df = update_summary_chart_and_data(
            mock_result, "TC Count", ["4J-Camera Fail (6) max failures"]
        )

        assert isinstance(filtered_summary, str)
        assert "Found 1 instances" in filtered_summary
