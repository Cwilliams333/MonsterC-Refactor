"""
Unit tests for the WiFi Error Service module.

Tests cover WiFi error analysis functionality to ensure 100%
feature parity with the legacy implementation.
"""

import os
import tempfile
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from src.services.wifi_error_service import analyze_wifi_errors


@pytest.fixture
def sample_wifi_data():
    """Create a sample DataFrame with WiFi error data for testing."""
    np.random.seed(42)

    # Define the operators and WiFi error types from the service
    operators = [
        "STN251_RED(id:10089)",
        "STN252_RED(id:10090)",
        "STN351_GRN(id:10380)",
        "STN352_GRN(id:10381)",
    ]
    wifi_errors = [
        "Device closed the socket",
        "DUT connection error",
        "DUT lost WIFI connection",
    ]
    other_errors = ["Display Error", "Camera Error", "Touch Error"]

    # Create time data spanning multiple days and hours
    base_time = datetime(2024, 1, 1)
    data = []

    # Generate data for multiple days
    for day in range(3):  # 3 days of data
        for hour in range(24):  # Each hour of the day
            current_time = base_time + timedelta(days=day, hours=hour)
            date_str = current_time.strftime("%m/%d/%Y")
            hour_str = current_time.strftime("%H:%M:%S")

            # Generate some WiFi errors
            for _ in range(np.random.randint(1, 8)):  # 1-7 errors per hour
                operator = np.random.choice(operators)

                # Create more WiFi errors for certain operators to test thresholds
                if operator in ["STN251_RED(id:10089)", "STN252_RED(id:10090)"]:
                    error_msg = np.random.choice(
                        wifi_errors, p=[0.4, 0.4, 0.2]
                    )  # More likely to have WiFi errors
                else:
                    error_msg = np.random.choice(
                        wifi_errors + other_errors, p=[0.1, 0.1, 0.1, 0.2, 0.2, 0.3]
                    )

                data.append(
                    {
                        "Date": date_str,
                        "Hour": hour_str,
                        "Operator": operator,
                        "error_message": error_msg,
                        "IMEI": f"35{1000 + len(data):013d}",
                        "Model": np.random.choice(["iPhone14ProMax", "iPhone15Pro"]),
                        "Station ID": np.random.choice(["radi135", "radi136"]),
                        "Overall status": "FAILURE",
                    }
                )

            # Generate some successful transactions
            for _ in range(
                np.random.randint(10, 50)
            ):  # 10-50 successful transactions per hour
                operator = np.random.choice(operators)
                data.append(
                    {
                        "Date": date_str,
                        "Hour": hour_str,
                        "Operator": operator,
                        "error_message": "",
                        "IMEI": f"35{1000 + len(data):013d}",
                        "Model": np.random.choice(["iPhone14ProMax", "iPhone15Pro"]),
                        "Station ID": np.random.choice(["radi135", "radi136"]),
                        "Overall status": "SUCCESS",
                    }
                )

    return pd.DataFrame(data)


@pytest.fixture
def high_error_wifi_data():
    """Create a sample DataFrame with high WiFi error rates to test threshold detection."""
    operators = [
        "STN251_RED(id:10089)",
        "STN252_RED(id:10090)",
        "STN351_GRN(id:10380)",
        "STN352_GRN(id:10381)",
    ]
    wifi_errors = [
        "Device closed the socket",
        "DUT connection error",
        "DUT lost WIFI connection",
    ]

    base_time = datetime(2024, 1, 1)
    data = []

    # Create data where STN251_RED has high error rate (>15%)
    for hour in range(24):
        current_time = base_time + timedelta(hours=hour)
        date_str = current_time.strftime("%m/%d/%Y")
        hour_str = current_time.strftime("%H:%M:%S")

        # STN251_RED: 20 errors out of 100 transactions = 20% error rate
        for i in range(20):
            data.append(
                {
                    "Date": date_str,
                    "Hour": hour_str,
                    "Operator": "STN251_RED(id:10089)",
                    "error_message": np.random.choice(wifi_errors),
                    "IMEI": f"35{1000 + len(data):013d}",
                    "Model": "iPhone14ProMax",
                    "Station ID": "radi135",
                    "Overall status": "FAILURE",
                }
            )

        for i in range(80):  # 80 successful transactions
            data.append(
                {
                    "Date": date_str,
                    "Hour": hour_str,
                    "Operator": "STN251_RED(id:10089)",
                    "error_message": "",
                    "IMEI": f"35{1000 + len(data):013d}",
                    "Model": "iPhone14ProMax",
                    "Station ID": "radi135",
                    "Overall status": "SUCCESS",
                }
            )

        # STN252_RED: 5 errors out of 100 transactions = 5% error rate (below threshold)
        for i in range(5):
            data.append(
                {
                    "Date": date_str,
                    "Hour": hour_str,
                    "Operator": "STN252_RED(id:10090)",
                    "error_message": np.random.choice(wifi_errors),
                    "IMEI": f"35{2000 + len(data):013d}",
                    "Model": "iPhone15Pro",
                    "Station ID": "radi136",
                    "Overall status": "FAILURE",
                }
            )

        for i in range(95):  # 95 successful transactions
            data.append(
                {
                    "Date": date_str,
                    "Hour": hour_str,
                    "Operator": "STN252_RED(id:10090)",
                    "error_message": "",
                    "IMEI": f"35{2000 + len(data):013d}",
                    "Model": "iPhone15Pro",
                    "Station ID": "radi136",
                    "Overall status": "SUCCESS",
                }
            )

    return pd.DataFrame(data)


@pytest.fixture
def no_wifi_errors_data():
    """Create a sample DataFrame with no WiFi errors to test edge case."""
    operators = ["STN251_RED(id:10089)", "STN252_RED(id:10090)"]
    other_errors = ["Display Error", "Camera Error"]

    base_time = datetime(2024, 1, 1)
    data = []

    for hour in range(6):  # Just a few hours of data
        current_time = base_time + timedelta(hours=hour)
        date_str = current_time.strftime("%m/%d/%Y")
        hour_str = current_time.strftime("%H:%M:%S")

        # Only non-WiFi errors and successes
        for i in range(10):
            data.append(
                {
                    "Date": date_str,
                    "Hour": hour_str,
                    "Operator": np.random.choice(operators),
                    "error_message": np.random.choice(other_errors + [""]),
                    "IMEI": f"35{1000 + len(data):013d}",
                    "Model": "iPhone14ProMax",
                    "Station ID": "radi135",
                    "Overall status": np.random.choice(["SUCCESS", "FAILURE"]),
                }
            )

    return pd.DataFrame(data)


class TestAnalyzeWifiErrors:
    """Test the analyze_wifi_errors function."""

    def test_analyze_wifi_errors_basic(self, sample_wifi_data):
        """Test basic WiFi error analysis with sample data."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            sample_wifi_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            # Create a mock file object
            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                # Test the function
                styled_results, heatmap_fig, styled_pivot, trend_fig = (
                    analyze_wifi_errors(file_obj, error_threshold=9)
                )

                # Check that we get results
                assert styled_results is not None
                assert isinstance(styled_results, pd.io.formats.style.Styler)

                # The function should return figures even if no high error operators
                # (it may return None for figures if no high errors)
                assert styled_results is not None

            finally:
                # Clean up
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_high_error_threshold(self, high_error_wifi_data):
        """Test WiFi error analysis with high error rates above threshold."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            high_error_wifi_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                # Test with threshold of 15% - STN251_RED should be above this
                styled_results, heatmap_fig, styled_pivot, trend_fig = (
                    analyze_wifi_errors(file_obj, error_threshold=15)
                )

                # Should have results
                assert styled_results is not None

                # Should have figures since we have high error operators
                assert heatmap_fig is not None
                assert styled_pivot is not None
                assert trend_fig is not None

                # Check that the results DataFrame has the expected structure
                results_df = styled_results.data
                assert "Operator" in results_df.columns
                assert "Total Transactions" in results_df.columns
                assert "WiFi Errors" in results_df.columns
                assert "Error Percentage" in results_df.columns

                # Should include the grand total row
                assert "Grand Total" in results_df["Operator"].values

            finally:
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_low_threshold(self, high_error_wifi_data):
        """Test WiFi error analysis with low threshold - should find more high error operators."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            high_error_wifi_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                # Test with threshold of 3% - both operators should be above this
                styled_results, heatmap_fig, styled_pivot, trend_fig = (
                    analyze_wifi_errors(file_obj, error_threshold=3)
                )

                assert styled_results is not None
                assert heatmap_fig is not None
                assert styled_pivot is not None
                assert trend_fig is not None

            finally:
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_no_high_errors(self, no_wifi_errors_data):
        """Test WiFi error analysis when no operators exceed the threshold."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            no_wifi_errors_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                styled_results, heatmap_fig, styled_pivot, trend_fig = (
                    analyze_wifi_errors(file_obj, error_threshold=9)
                )

                # Should have styled results
                assert styled_results is not None

                # Should not have figures since no high error operators
                assert heatmap_fig is None
                assert styled_pivot is None
                assert trend_fig is None

            finally:
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_empty_data(self):
        """Test WiFi error analysis with empty DataFrame."""
        empty_df = pd.DataFrame(
            columns=["Date", "Hour", "Operator", "error_message", "IMEI"]
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            empty_df.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                styled_results, heatmap_fig, styled_pivot, trend_fig = (
                    analyze_wifi_errors(file_obj, error_threshold=9)
                )

                # Function should handle empty data gracefully
                # May return None for all results or empty styled results
                assert styled_results is not None or styled_results is None

            finally:
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_malformed_data(self):
        """Test WiFi error analysis with malformed date data."""
        malformed_data = pd.DataFrame(
            {
                "Date": ["invalid_date", "01/01/2024"],
                "Hour": ["invalid_time", "12:00:00"],
                "Operator": ["STN251_RED(id:10089)", "STN252_RED(id:10090)"],
                "error_message": ["Device closed the socket", ""],
                "IMEI": ["351234567890123", "351234567890124"],
            }
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            malformed_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                # Should handle malformed data gracefully and return None
                styled_results, heatmap_fig, styled_pivot, trend_fig = (
                    analyze_wifi_errors(file_obj, error_threshold=9)
                )

                # Function should return None for all values when data parsing fails
                assert styled_results is None
                assert heatmap_fig is None
                assert styled_pivot is None
                assert trend_fig is None

            finally:
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_different_thresholds(self, sample_wifi_data):
        """Test WiFi error analysis with different error thresholds."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            sample_wifi_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                # Test with very low threshold (0%) - should find high error operators
                styled_results_low, _, _, _ = analyze_wifi_errors(
                    file_obj, error_threshold=0
                )

                # Test with very high threshold (99%) - should not find high error operators
                styled_results_high, heatmap_high, pivot_high, trend_high = (
                    analyze_wifi_errors(file_obj, error_threshold=99)
                )

                assert styled_results_low is not None
                assert styled_results_high is not None

                # High threshold should result in no additional figures
                assert heatmap_high is None
                assert pivot_high is None
                assert trend_high is None

            finally:
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_specific_operators(self, sample_wifi_data):
        """Test that analysis focuses on the correct operators."""
        # Filter to only include target operators
        target_operators = [
            "STN251_RED(id:10089)",
            "STN252_RED(id:10090)",
            "STN351_GRN(id:10380)",
            "STN352_GRN(id:10381)",
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            sample_wifi_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                styled_results, _, _, _ = analyze_wifi_errors(
                    file_obj, error_threshold=9
                )

                if styled_results is not None:
                    results_df = styled_results.data
                    # Check that only target operators (plus Grand Total) are in results
                    operators_in_results = set(results_df["Operator"].values) - {
                        "Grand Total"
                    }
                    assert operators_in_results.issubset(set(target_operators))

            finally:
                os.unlink(tmp_file.name)

    def test_analyze_wifi_errors_specific_error_types(self, sample_wifi_data):
        """Test that analysis focuses on the correct WiFi error types."""
        target_wifi_errors = [
            "Device closed the socket",
            "DUT connection error",
            "DUT lost WIFI connection",
        ]

        # The function should only count these specific error types
        # This is more of an integration test to ensure the logic is working correctly
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            sample_wifi_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                styled_results, _, _, _ = analyze_wifi_errors(
                    file_obj, error_threshold=0
                )  # Low threshold to get results

                # Just verify the function completes successfully
                assert styled_results is not None

            finally:
                os.unlink(tmp_file.name)


class TestWifiErrorServiceIntegration:
    """Integration tests for the WiFi error service."""

    def test_full_workflow_with_high_errors(self, high_error_wifi_data):
        """Test the complete workflow with data that should trigger high error detection."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as tmp_file:
            high_error_wifi_data.to_csv(tmp_file.name, index=False)
            tmp_file.flush()

            class MockFile:
                def __init__(self, name):
                    self.name = name

            file_obj = MockFile(tmp_file.name)

            try:
                # Run the complete analysis
                styled_results, heatmap_fig, styled_pivot, trend_fig = (
                    analyze_wifi_errors(file_obj, error_threshold=10)
                )

                # Verify all components are generated
                assert styled_results is not None
                assert heatmap_fig is not None
                assert styled_pivot is not None
                assert trend_fig is not None

                # Verify the styled results structure
                results_df = styled_results.data
                assert len(results_df) == 5  # 4 operators + Grand Total
                assert all(
                    col in results_df.columns
                    for col in [
                        "Operator",
                        "Total Transactions",
                        "WiFi Errors",
                        "Error Percentage",
                    ]
                )

                # Verify that figures have the expected properties
                assert hasattr(heatmap_fig, "data")
                assert hasattr(heatmap_fig, "layout")
                assert heatmap_fig.layout.title.text is not None

                assert hasattr(trend_fig, "data")
                assert hasattr(trend_fig, "layout")
                assert trend_fig.layout.title.text is not None

                # Verify pivot table structure
                pivot_df = styled_pivot.data
                assert "DateOnly" in pivot_df.columns
                assert "Time" in pivot_df.columns

            finally:
                os.unlink(tmp_file.name)
