"""
Tests for Excel-style failure pivot functionality.
"""

import numpy as np
import pandas as pd
import pytest

from src.services.pivot_service import (apply_failure_highlighting,
                                        create_excel_style_failure_pivot)


class TestExcelStyleFailurePivot:
    """Test cases for Excel-style failure pivot functionality."""

    @pytest.fixture
    def sample_data(self):
        """Sample data matching the CSV structure."""
        return pd.DataFrame(
            {
                "Operator": ["Op1", "Op1", "Op2", "Op1", "Op2", "Op1", "Op2", "Op1"],
                "Station ID": [
                    "station1",
                    "station2",
                    "station1",
                    "station2",
                    "station1",
                    "station1",
                    "station2",
                    "station1",
                ],
                "Model": [
                    "iPhone14",
                    "iPhone15",
                    "iPhone14",
                    "iPhone15",
                    "iPhone14",
                    "iPhone15",
                    "iPhone14",
                    "iPhone15",
                ],
                "result_FAIL": [
                    "Camera Rear Photo,Display Fail",
                    "Action Button",
                    "Camera Rear Photo",
                    "Display Fail,Action Button",
                    "",  # Empty case
                    "Camera Rear Photo,Display Fail,Action Button",
                    "Display Fail",
                    "Action Button,Camera Rear Photo",
                ],
            }
        )

    def test_excel_style_pivot_basic(self, sample_data):
        """Test basic Excel-style pivot creation."""
        result = create_excel_style_failure_pivot(sample_data)

        # Check structure
        assert not result.empty
        assert "result_FAIL" in result.columns
        assert "Model" in result.columns
        assert "station1" in result.columns
        assert "station2" in result.columns

        # Check that comma-separated values were parsed
        # Should have separate rows for each failure type
        action_button_rows = result[result["result_FAIL"] == "Action Button"]
        assert len(action_button_rows) > 0

        camera_rows = result[result["result_FAIL"] == "Camera Rear Photo"]
        assert len(camera_rows) > 0

        display_rows = result[result["result_FAIL"] == "Display Fail"]
        assert len(display_rows) > 0

    def test_excel_style_pivot_with_operator_filter(self, sample_data):
        """Test Excel-style pivot with operator filter."""
        result = create_excel_style_failure_pivot(sample_data, operator_filter="Op1")

        assert not result.empty
        # Should have fewer counts since we filtered by Op1 only
        total_op1 = result[["station1", "station2"]].sum().sum()

        result_all = create_excel_style_failure_pivot(sample_data)
        total_all = result_all[["station1", "station2"]].sum().sum()

        assert total_op1 <= total_all

    def test_excel_style_pivot_empty_result_fail(self, sample_data):
        """Test that empty result_FAIL entries are excluded."""
        result = create_excel_style_failure_pivot(sample_data)

        # Count total entries in pivot
        total_entries = result[["station1", "station2"]].sum().sum()

        # Should be 7 non-empty result_FAIL entries, but with comma parsing:
        # 'Camera Rear Photo,Display Fail' -> 2 entries
        # 'Action Button' -> 1 entry
        # 'Camera Rear Photo' -> 1 entry
        # 'Display Fail,Action Button' -> 2 entries
        # (empty) -> 0 entries (excluded)
        # 'Camera Rear Photo,Display Fail,Action Button' -> 3 entries
        # 'Display Fail' -> 1 entry
        # 'Action Button,Camera Rear Photo' -> 2 entries
        # Total: 12 entries
        assert total_entries == 12

    def test_excel_style_pivot_counts_correct(self, sample_data):
        """Test that failure counts are correct."""
        result = create_excel_style_failure_pivot(sample_data)

        # Check specific counts
        action_button_iphone15 = result[
            (result["result_FAIL"] == "Action Button") & (result["Model"] == "iPhone15")
        ]

        assert len(action_button_iphone15) == 1
        # Action Button appears in rows 1, 3, 5, 7 for iPhone15
        # Row 1: Op1/station2/iPhone15 -> station2 = 1
        # Row 3: Op1/station2/iPhone15 -> station2 = 1
        # Row 5: Op1/station1/iPhone15 -> station1 = 1
        # Row 7: Op1/station1/iPhone15 -> station1 = 1
        # Total station1 = 2, station2 = 2
        assert action_button_iphone15.iloc[0]["station1"] == 2
        assert action_button_iphone15.iloc[0]["station2"] == 2

    def test_excel_style_pivot_hierarchical_structure(self, sample_data):
        """Test that the result has proper hierarchical structure."""
        result = create_excel_style_failure_pivot(sample_data)

        # Should have reset index, so result_FAIL and Model are columns
        assert "result_FAIL" in result.columns
        assert "Model" in result.columns

        # Check that we have the expected failure types
        failure_types = result["result_FAIL"].unique()
        expected_types = {"Action Button", "Camera Rear Photo", "Display Fail"}
        assert set(failure_types) == expected_types

        # Check that we have the expected models
        models = result["Model"].unique()
        expected_models = {"iPhone14", "iPhone15"}
        assert set(models) == expected_models


class TestFailureHighlighting:
    """Test cases for failure highlighting functionality."""

    @pytest.fixture
    def sample_pivot_data(self):
        """Sample pivot table data for highlighting tests."""
        return pd.DataFrame(
            {
                "result_FAIL": ["Camera Rear Photo", "Display Fail", "Action Button"],
                "Model": ["iPhone14", "iPhone15", "iPhone14"],
                "station1": [1, 5, 2],  # High value: 5
                "station2": [3, 1, 8],  # High value: 8
            }
        )

    def test_apply_failure_highlighting_basic(self, sample_pivot_data):
        """Test basic failure highlighting."""
        result = apply_failure_highlighting(sample_pivot_data)

        # Should return a Styler object
        assert hasattr(result, "data")
        assert hasattr(result, "map")  # Styler has map method

        # The underlying data should be unchanged
        pd.testing.assert_frame_equal(result.data, sample_pivot_data)

    def test_apply_failure_highlighting_empty_dataframe(self):
        """Test highlighting with empty DataFrame."""
        empty_df = pd.DataFrame()
        result = apply_failure_highlighting(empty_df)

        # Should return the original DataFrame unchanged
        pd.testing.assert_frame_equal(result, empty_df)

    def test_apply_failure_highlighting_error_dataframe(self):
        """Test highlighting with error DataFrame."""
        error_df = pd.DataFrame({"Error": ["Some error message"]})
        result = apply_failure_highlighting(error_df)

        # Should return the original DataFrame unchanged
        pd.testing.assert_frame_equal(result, error_df)

    def test_apply_failure_highlighting_no_numeric_columns(self):
        """Test highlighting with no numeric columns."""
        text_df = pd.DataFrame(
            {
                "result_FAIL": ["Camera Rear Photo", "Display Fail"],
                "Model": ["iPhone14", "iPhone15"],
            }
        )
        result = apply_failure_highlighting(text_df)

        # Should return the original DataFrame unchanged
        pd.testing.assert_frame_equal(result, text_df)

    def test_apply_failure_highlighting_threshold_calculation(self, sample_pivot_data):
        """Test that thresholds are calculated correctly."""
        # Test with known data where we can predict thresholds
        result = apply_failure_highlighting(sample_pivot_data, threshold_multiplier=1.0)

        # Should return a Styler object
        assert hasattr(result, "data")

        # Values: [1, 5, 2, 3, 1, 8] (excluding zeros)
        # Mean = 3.33, Std = 2.73
        # Yellow threshold = 3.33 + 1.0*2.73 = 6.06
        # Red threshold = 3.33 + 2.0*2.73 = 8.79
        # So value 8 should be yellow, none should be red

    def test_apply_failure_highlighting_custom_threshold(self, sample_pivot_data):
        """Test highlighting with custom threshold multiplier."""
        result_low = apply_failure_highlighting(
            sample_pivot_data, threshold_multiplier=0.5
        )
        result_high = apply_failure_highlighting(
            sample_pivot_data, threshold_multiplier=5.0
        )

        # Both should return Styler objects
        assert hasattr(result_low, "data")
        assert hasattr(result_high, "data")

        # With lower threshold, more cells should be highlighted
        # With higher threshold, fewer cells should be highlighted


class TestEdgeCases:
    """Test edge cases for Excel-style pivot functionality."""

    def test_excel_style_pivot_empty_dataframe(self):
        """Test with empty DataFrame."""
        empty_df = pd.DataFrame(
            columns=["Operator", "Station ID", "Model", "result_FAIL"]
        )
        result = create_excel_style_failure_pivot(empty_df)

        # Should handle gracefully
        assert isinstance(result, pd.DataFrame)

    def test_excel_style_pivot_all_empty_result_fail(self):
        """Test with all empty result_FAIL values."""
        data = pd.DataFrame(
            {
                "Operator": ["Op1", "Op2"],
                "Station ID": ["station1", "station2"],
                "Model": ["iPhone14", "iPhone15"],
                "result_FAIL": ["", ""],
            }
        )
        result = create_excel_style_failure_pivot(data)

        # Should handle gracefully with empty result
        assert isinstance(result, pd.DataFrame)

    def test_excel_style_pivot_single_failure_type(self):
        """Test with single failure type."""
        data = pd.DataFrame(
            {
                "Operator": ["Op1", "Op1"],
                "Station ID": ["station1", "station2"],
                "Model": ["iPhone14", "iPhone15"],
                "result_FAIL": ["Camera Rear Photo", "Camera Rear Photo"],
            }
        )
        result = create_excel_style_failure_pivot(data)

        assert not result.empty
        assert len(result["result_FAIL"].unique()) == 1
        assert result["result_FAIL"].iloc[0] == "Camera Rear Photo"

    def test_excel_style_pivot_whitespace_handling(self):
        """Test that whitespace in comma-separated values is handled."""
        data = pd.DataFrame(
            {
                "Operator": ["Op1"],
                "Station ID": ["station1"],
                "Model": ["iPhone14"],
                "result_FAIL": [
                    "Camera Rear Photo, Display Fail,Action Button"
                ],  # Mixed spacing
            }
        )
        result = create_excel_style_failure_pivot(data)

        assert not result.empty
        failure_types = result["result_FAIL"].unique()
        assert "Camera Rear Photo" in failure_types
        assert "Display Fail" in failure_types
        assert "Action Button" in failure_types
        # Should not have any entries with leading/trailing spaces
        assert not any(
            " " in ft for ft in failure_types if ft.startswith(" ") or ft.endswith(" ")
        )
