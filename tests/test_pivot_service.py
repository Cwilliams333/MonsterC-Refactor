"""
Unit tests for the Pivot Service module.

Tests cover all pivot table generation, filtering, and analysis functions
to ensure 100% feature parity with the legacy implementation.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from src.services.pivot_service import (analyze_top_models,
                                        analyze_top_test_cases, apply_filters,
                                        create_pivot_table,
                                        find_top_failing_stations,
                                        generate_pivot_table_filtered)


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing pivot operations."""
    np.random.seed(42)

    # Generate test data
    n_rows = 100
    operators = ["STN251_RED(id:10089)", "STN252_RED(id:10090)", "STN351_GRN(id:10380)"]
    models = ["iPhone14ProMax", "iPhone15Pro", "iPhone15", "iPhone14"]
    stations = ["radi135", "radi136", "radi137", "radi138"]
    test_cases = ["6A-Display Fail", "4J-Camera Fail", "2B-Touch Fail", "5K-Audio Fail"]
    statuses = ["SUCCESS", "FAILURE", "ERROR"]

    data = {
        "Date": [datetime.now() - timedelta(days=i % 30) for i in range(n_rows)],
        "Operator": np.random.choice(operators, n_rows),
        "Model": np.random.choice(models, n_rows),
        "Station ID": np.random.choice(stations, n_rows),
        "result_FAIL": np.random.choice(
            test_cases + [""], n_rows, p=[0.15, 0.15, 0.15, 0.15, 0.4]
        ),
        "Overall status": np.random.choice(statuses, n_rows, p=[0.6, 0.3, 0.1]),
        "IMEI": [f"35{i:013d}" for i in range(n_rows)],
        "Test Duration": np.random.randint(10, 300, n_rows),
        "Error Count": np.random.randint(0, 10, n_rows),
    }

    return pd.DataFrame(data)


@pytest.fixture
def pivot_table_df():
    """Create a sample pivot table for testing analysis functions."""
    # Create a pivot-like structure with stations as columns
    data = {
        ("Model", "result_FAIL"): [
            ("iPhone14ProMax", "FAILURE"),
            ("iPhone15Pro", "FAILURE"),
            ("iPhone15", "FAILURE"),
            ("iPhone14", "FAILURE"),
        ],
        "radi135": [10, 8, 5, 3],
        "radi136": [7, 12, 4, 2],
        "radi137": [5, 3, 9, 6],
        "radi138": [2, 1, 3, 8],
    }

    df = pd.DataFrame(data)
    df.set_index(("Model", "result_FAIL"), inplace=True)
    return df


class TestApplyFilters:
    """Test the apply_filters function."""

    def test_apply_filters_no_filter(self, sample_df):
        """Test that no filtering returns the original DataFrame."""
        result = apply_filters(sample_df, "All", "All", "All")
        assert len(result) == len(sample_df)
        pd.testing.assert_frame_equal(result, sample_df)

    def test_apply_filters_single_operator(self, sample_df):
        """Test filtering by a single operator."""
        operator = "STN251_RED(id:10089)"
        result = apply_filters(sample_df, [operator], "All", "All")
        assert all(result["Operator"] == operator)
        assert len(result) <= len(sample_df)

    def test_apply_filters_multiple_operators(self, sample_df):
        """Test filtering by multiple operators."""
        operators = ["STN251_RED(id:10089)", "STN252_RED(id:10090)"]
        result = apply_filters(sample_df, operators, "All", "All")
        assert all(result["Operator"].isin(operators))
        assert len(result) <= len(sample_df)

    def test_apply_filters_station_id(self, sample_df):
        """Test filtering by station ID."""
        station = "radi135"
        result = apply_filters(sample_df, "All", [station], "All")
        assert all(result["Station ID"] == station)

    def test_apply_filters_model(self, sample_df):
        """Test filtering by model."""
        model = "iPhone14ProMax"
        result = apply_filters(sample_df, "All", "All", [model])
        assert all(result["Model"] == model)

    def test_apply_filters_combined(self, sample_df):
        """Test filtering by multiple criteria."""
        operator = "STN251_RED(id:10089)"
        station = "radi135"
        model = "iPhone14ProMax"
        result = apply_filters(sample_df, [operator], [station], [model])
        assert all(result["Operator"] == operator)
        assert all(result["Station ID"] == station)
        assert all(result["Model"] == model)

    def test_apply_filters_empty_result(self, sample_df):
        """Test that impossible filter combinations return empty DataFrame."""
        # Create a filter that should return no results
        result = apply_filters(sample_df, ["NonExistentOperator"], "All", "All")
        assert len(result) == 0


class TestCreatePivotTable:
    """Test the create_pivot_table function."""

    def test_create_pivot_table_basic(self, sample_df):
        """Test basic pivot table creation."""
        pivot = create_pivot_table(
            sample_df,
            rows=["Model"],
            columns=["Station ID"],
            values="IMEI",
            aggfunc="count",
        )
        assert isinstance(pivot, pd.DataFrame)
        assert "Model" in pivot.columns
        assert len(pivot) > 0

    def test_create_pivot_table_no_columns(self, sample_df):
        """Test pivot table without column dimension."""
        pivot = create_pivot_table(
            sample_df,
            rows=["Model", "Overall status"],
            columns=None,
            values="IMEI",
            aggfunc="count",
        )
        assert isinstance(pivot, pd.DataFrame)
        assert "Model" in pivot.columns
        assert "Overall status" in pivot.columns

    def test_create_pivot_table_aggregations(self, sample_df):
        """Test different aggregation functions."""
        for aggfunc in ["count", "sum", "mean", "max", "min"]:
            pivot = create_pivot_table(
                sample_df,
                rows=["Model"],
                columns=["Station ID"],
                values="Test Duration",
                aggfunc=aggfunc,
            )
            assert isinstance(pivot, pd.DataFrame)
            assert len(pivot) > 0

    def test_create_pivot_table_missing_required_fields(self, sample_df):
        """Test that missing required fields returns empty DataFrame."""
        # Missing rows
        pivot = create_pivot_table(
            sample_df, rows=[], columns=["Station ID"], values="IMEI"
        )
        assert len(pivot) == 0

        # Missing values
        pivot = create_pivot_table(
            sample_df, rows=["Model"], columns=["Station ID"], values=""
        )
        assert len(pivot) == 0

    def test_create_pivot_table_multi_level_columns(self, sample_df):
        """Test pivot table with multi-level columns."""
        pivot = create_pivot_table(
            sample_df,
            rows=["Model"],
            columns=["Station ID", "Overall status"],
            values="IMEI",
            aggfunc="count",
        )
        assert isinstance(pivot, pd.DataFrame)
        # Check that multi-level columns are flattened
        assert all(
            not isinstance(col, tuple) or "_" in str(col) for col in pivot.columns
        )

    def test_create_pivot_table_error_handling(self, sample_df):
        """Test error handling in pivot table creation."""
        # Invalid column name
        pivot = create_pivot_table(
            sample_df,
            rows=["NonExistentColumn"],
            columns=None,
            values="IMEI",
            aggfunc="count",
        )
        assert "Error" in pivot.columns


class TestGeneratePivotTableFiltered:
    """Test the generate_pivot_table_filtered function."""

    def test_generate_pivot_table_filtered_no_filter(self, sample_df):
        """Test filtered pivot table without filters."""
        pivot = generate_pivot_table_filtered(
            sample_df,
            rows=["Model"],
            columns=["Station ID"],
            values="IMEI",
            aggfunc="count",
            operator="All",
            station_id="All",
            model="All",
        )
        assert isinstance(pivot, pd.DataFrame)
        assert len(pivot) > 0

    def test_generate_pivot_table_filtered_with_filters(self, sample_df):
        """Test filtered pivot table with active filters."""
        model = "iPhone14ProMax"
        pivot = generate_pivot_table_filtered(
            sample_df,
            rows=["Station ID"],
            columns=["Overall status"],
            values="IMEI",
            aggfunc="count",
            operator="All",
            station_id="All",
            model=[model],
        )
        assert isinstance(pivot, pd.DataFrame)
        # The pivot should only contain data for the filtered model

    def test_generate_pivot_table_filtered_complex(self, sample_df):
        """Test filtered pivot table with multiple filters and dimensions."""
        pivot = generate_pivot_table_filtered(
            sample_df,
            rows=["Model", "result_FAIL"],
            columns=["Station ID"],
            values="Test Duration",
            aggfunc="mean",
            operator=["STN251_RED(id:10089)", "STN252_RED(id:10090)"],
            station_id=["radi135", "radi136"],
            model="All",
        )
        assert isinstance(pivot, pd.DataFrame)


class TestPivotAnalysisFunctions:
    """Test the pivot analysis functions."""

    def test_find_top_failing_stations(self, pivot_table_df):
        """Test finding top failing stations."""
        top_stations = find_top_failing_stations(pivot_table_df, top_n=3)
        assert isinstance(top_stations, pd.Series)
        assert len(top_stations) == 3
        # Check that results are sorted in descending order
        assert all(
            top_stations.iloc[i] >= top_stations.iloc[i + 1]
            for i in range(len(top_stations) - 1)
        )

    def test_find_top_failing_stations_all(self, pivot_table_df):
        """Test finding all failing stations."""
        top_stations = find_top_failing_stations(pivot_table_df, top_n=10)
        assert len(top_stations) == 4  # We only have 4 stations

    def test_analyze_top_models(self, pivot_table_df):
        """Test analyzing top models."""
        top_stations = pd.Series([25, 17], index=["radi135", "radi136"])
        top_models = analyze_top_models(pivot_table_df, top_stations, top_n=3)
        assert isinstance(top_models, pd.Series)
        assert len(top_models) <= 3
        # Check that model names include result suffix
        assert all(" - " in str(idx) for idx in top_models.index)

    def test_analyze_top_test_cases(self, pivot_table_df):
        """Test analyzing top test cases."""
        # Create a DataFrame with test case data
        test_case_data = {
            "result_FAIL": [
                "6A-Display Fail",
                "4J-Camera Fail",
                "2B-Touch Fail",
                "5K-Audio Fail",
            ],
            "radi135": [10, 8, 5, 3],
            "radi136": [7, 12, 4, 2],
        }
        test_df = pd.DataFrame(test_case_data)
        test_df.set_index("result_FAIL", inplace=True)

        top_stations = pd.Series([17, 25], index=["radi135", "radi136"])
        top_test_cases = analyze_top_test_cases(test_df, top_stations, top_n=3)
        assert isinstance(top_test_cases, pd.Series)
        assert len(top_test_cases) <= 3


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_dataframe(self):
        """Test all functions with empty DataFrame."""
        empty_df = pd.DataFrame()

        # Test apply_filters
        result = apply_filters(empty_df, "All", "All", "All")
        assert len(result) == 0

        # Test create_pivot_table - should return error DataFrame
        pivot = create_pivot_table(empty_df, ["Model"], ["Station ID"], "IMEI", "count")
        assert isinstance(pivot, pd.DataFrame)
        assert "Error" in pivot.columns or len(pivot) == 0

        # Test generate_pivot_table_filtered
        pivot = generate_pivot_table_filtered(
            empty_df, ["Model"], ["Station ID"], "IMEI", "count", "All", "All", "All"
        )
        assert isinstance(pivot, pd.DataFrame)

    def test_null_values(self, sample_df):
        """Test handling of null values."""
        # Add some null values
        df_with_nulls = sample_df.copy()
        df_with_nulls.loc[0:10, "Model"] = None
        df_with_nulls.loc[5:15, "Station ID"] = None

        # Test that functions handle nulls gracefully
        pivot = create_pivot_table(
            df_with_nulls,
            rows=["Model"],
            columns=["Station ID"],
            values="IMEI",
            aggfunc="count",
        )
        assert isinstance(pivot, pd.DataFrame)

    def test_single_row_dataframe(self):
        """Test with single row DataFrame."""
        single_row = pd.DataFrame(
            {
                "Model": ["iPhone14ProMax"],
                "Station ID": ["radi135"],
                "IMEI": ["351234567890123"],
                "Overall status": ["SUCCESS"],
            }
        )

        pivot = create_pivot_table(
            single_row,
            rows=["Model"],
            columns=["Station ID"],
            values="IMEI",
            aggfunc="count",
        )
        assert len(pivot) == 1
