"""
Pivot Service Module for MonsterC CSV Analysis Tool.

This module provides pivot table generation and analysis functionality,
extracted from the legacy monolith following the Strangler Fig pattern.
"""

from typing import List, Optional, Union

import numpy as np
import pandas as pd

from src.common.logging_config import capture_exceptions, get_logger

# Initialize logger
logger = get_logger(__name__)


@capture_exceptions(user_message="Failed to apply filters to data")
def apply_filters(
    df: pd.DataFrame,
    operator: Union[str, List[str]],
    station_id: Union[str, List[str]],
    model: Union[str, List[str]],
) -> pd.DataFrame:
    """
    Apply filters to the DataFrame before creating pivot table.

    Args:
        df: Input DataFrame to filter
        operator: Operator(s) to filter by
        station_id: Station ID(s) to filter by
        model: Model(s) to filter by

    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()

    # Handle operator filter
    if operator and "All" not in operator:
        filtered_df = filtered_df[filtered_df["Operator"].isin(operator)]

    # Handle station_id filter
    if station_id and "All" not in station_id:
        filtered_df = filtered_df[filtered_df["Station ID"].isin(station_id)]

    # Handle model filter
    if model and "All" not in model:
        filtered_df = filtered_df[filtered_df["Model"].isin(model)]

    logger.info(
        f"Applied filters - rows before: {len(df)}, rows after: {len(filtered_df)}"
    )
    return filtered_df


@capture_exceptions(user_message="Failed to create pivot table")
def create_pivot_table(
    df: pd.DataFrame,
    rows: List[str],
    columns: Optional[List[str]],
    values: str,
    aggfunc: str = "count",
) -> pd.DataFrame:
    """
    Creates a pivot table from the given DataFrame based on user selections.

    Args:
        df: Input DataFrame
        rows: Columns to use as row indices
        columns: Columns to use as column indices (optional)
        values: Column to aggregate
        aggfunc: Aggregation function to use

    Returns:
        Pivot table as DataFrame
    """
    try:
        if not rows or not values:
            logger.warning("Missing required fields for pivot table")
            return (
                pd.DataFrame()
            )  # Return empty DataFrame if required fields are missing

        # Handle the aggregation function
        if aggfunc == "count":
            aggfunc = "size"

        # Create pivot table
        pivot = pd.pivot_table(
            df,
            index=rows,
            columns=columns if columns else None,
            values=values if aggfunc != "size" else None,
            aggfunc=aggfunc,
            fill_value=0,
        )

        # Reset index for better display
        pivot = pivot.reset_index()

        # Flatten column names if they're multi-level
        if isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = [
                f"{col[0]}_{col[1]}" if isinstance(col, tuple) else col
                for col in pivot.columns
            ]

        logger.info(f"Created pivot table with shape: {pivot.shape}")
        return pivot

    except Exception as e:
        logger.error(f"Error creating pivot table: {str(e)}")
        return pd.DataFrame({"Error": [str(e)]})


@capture_exceptions(user_message="Failed to generate filtered pivot table")
def generate_pivot_table_filtered(
    df: pd.DataFrame,
    rows: List[str],
    columns: Optional[List[str]],
    values: str,
    aggfunc: str,
    operator: Union[str, List[str]],
    station_id: Union[str, List[str]],
    model: Union[str, List[str]],
) -> pd.DataFrame:
    """
    Generate a filtered pivot table based on user selections.

    Args:
        df: Input DataFrame
        rows: Columns to use as row indices
        columns: Columns to use as column indices (optional)
        values: Column to aggregate
        aggfunc: Aggregation function to use
        operator: Operator(s) to filter by
        station_id: Station ID(s) to filter by
        model: Model(s) to filter by

    Returns:
        Filtered pivot table as DataFrame
    """
    try:
        # First apply filters
        filtered_df = apply_filters(df, operator, station_id, model)

        # Then create pivot table
        result = create_pivot_table(filtered_df, rows, columns, values, aggfunc)

        return result

    except Exception as e:
        logger.error(f"Error generating filtered pivot table: {str(e)}")
        return pd.DataFrame({"Error": [str(e)]})


@capture_exceptions(user_message="Failed to find top failing stations")
def find_top_failing_stations(pivot: pd.DataFrame, top_n: int = 5) -> pd.Series:
    """
    Finds the top failing stations based on the provided pivot table.

    Args:
        pivot: A Pandas DataFrame with a pivot table structure, where the
               index is the model, the columns are the test cases, and the
               values are the counts of failures for each test case
        top_n: The number of top failing stations to return

    Returns:
        A Series with the top failing stations and their failure counts
    """
    # Get the sum of all failures for each station
    station_failures = pivot.sum().fillna(0)

    # Get the top N failing stations
    return station_failures.nlargest(top_n)


@capture_exceptions(user_message="Failed to analyze top models")
def analyze_top_models(
    pivot: pd.DataFrame, top_stations: pd.Series, top_n: int = 5
) -> pd.Series:
    """
    Analyzes the top models based on the provided pivot table and top failing stations.

    This function takes a pivot table as input, which should be a DataFrame with the following structure:

        | Model | Station ID | Test Case | Count |
        |-------|------------|-----------|-------|
        |   A   |    1       |   1       |   10  |
        |   A   |    1       |   2       |   5   |
        |   B   |    2       |   1       |   8   |
        |   B   |    2       |   2       |   3   |

    The function also takes a Series of top failing stations as input, which should have the station IDs as
    the index and the total number of failures for each station as the values.

    Args:
        pivot: Pivot table DataFrame
        top_stations: Series with top failing stations
        top_n: Number of top models to return

    Returns:
        Series with top models and their failure counts
    """
    # Filter the pivot table to only include the top failing stations
    top_models_pivot = pivot[top_stations.index]

    # Sum up the counts for each model
    top_models = top_models_pivot.sum(axis=1).fillna(0)

    # Return the top N models with the highest total counts
    top_models = top_models.nlargest(top_n)

    # Rename the index to include the result (SUCCESS/FAILURE) for each model
    top_models.index = [f"{model} - {result}" for model, result in top_models.index]

    return top_models


@capture_exceptions(user_message="Failed to analyze top test cases")
def analyze_top_test_cases(
    pivot: pd.DataFrame, top_stations: pd.Series, top_n: int = 5
) -> pd.Series:
    """
    Analyzes the top test cases based on the provided pivot table and top failing stations.

    The pivot table is filtered to only include the top failing stations. Then, the test cases are grouped
    by their result (SUCCESS/FAILURE), and the sum of each group is calculated. This gives us the total
    number of test cases that failed for each station.

    Args:
        pivot: Pivot table DataFrame
        top_stations: Series with top failing stations
        top_n: Number of top test cases to return

    Returns:
        Series with top test cases and their failure counts
    """
    # Filter the pivot table to only include the top failing stations
    top_stations_pivot = pivot[top_stations.index]

    # Group the test cases by their result (SUCCESS/FAILURE) and calculate the sum of each group
    test_case_failures = (
        top_stations_pivot.groupby("result_FAIL").sum().sum(axis=1).fillna(0)
    )

    # Return the top N test cases, sorted by their failure count in descending order
    return test_case_failures.nlargest(top_n)


@capture_exceptions(user_message="Failed to create Excel-style failure pivot table")
def create_excel_style_failure_pivot(
    df: pd.DataFrame, operator_filter: Union[str, List[str], None] = None
) -> pd.DataFrame:
    """
    Creates a pivot table that exactly replicates the Excel configuration used daily:
    - Filters: Operator (applied before pivot)
    - Columns: Station ID
    - Rows: result_FAIL, Model (hierarchical)
    - Values: Count of result_FAIL

    This function handles comma-separated result_FAIL values by parsing and exploding them
    into individual failure types before creating the pivot table.

    Args:
        df: Input DataFrame with columns: Operator, Station ID, Model, result_FAIL
        operator_filter: Optional filter for Operator column (single string or list)

    Returns:
        Pivot table DataFrame with hierarchical index (result_FAIL, Model) and Station ID columns
    """
    try:
        # Step 1: Apply operator filter (like Excel filter)
        filtered_df = df.copy()

        # Handle operator filter - can be string, list, or None
        if operator_filter:
            # Convert to list if string
            if isinstance(operator_filter, str):
                filter_list = [operator_filter]
            else:
                filter_list = operator_filter

            # Only filter if not "All" or ["All"]
            if filter_list != ["All"] and "All" not in filter_list:
                filtered_df = filtered_df[filtered_df["Operator"].isin(filter_list)]

        # Log filter status
        logger.info(
            f"Operator filter: {operator_filter}, DataFrame shape after filter: {filtered_df.shape}"
        )

        # Step 2: Remove empty result_FAIL entries
        filtered_df = filtered_df[filtered_df["result_FAIL"].notna()]
        filtered_df = filtered_df[filtered_df["result_FAIL"].str.strip() != ""]

        logger.info(
            f"DataFrame shape after removing empty result_FAIL: {filtered_df.shape}"
        )

        # Step 3: Explode comma-separated result_FAIL values
        # This is the key enhancement - parsing comma-separated failure types
        filtered_df = filtered_df.copy()
        filtered_df["result_FAIL"] = filtered_df["result_FAIL"].str.split(",")
        exploded_df = filtered_df.explode("result_FAIL")
        exploded_df["result_FAIL"] = exploded_df["result_FAIL"].str.strip()

        # Step 4: Create pivot table with hierarchical rows (result_FAIL, Model)
        pivot_result = pd.pivot_table(
            exploded_df,
            index=["result_FAIL", "Model"],  # Hierarchical rows like Excel
            columns=["Station ID"],  # Columns like Excel
            values="Operator",  # Need something to count
            aggfunc="count",  # Count occurrences
            fill_value=0,  # Fill missing with 0
        )

        # Step 5: Clean up column names and reset index for Gradio compatibility
        pivot_result.columns.name = None  # Remove 'Station ID' header
        pivot_result = (
            pivot_result.reset_index()
        )  # Make hierarchical index into columns

        # Note: This creates a basic pivot table for Gradio display.
        # For true Excel-style hierarchical grouping, use the interactive Dash AG Grid
        # implementation which supports native tree data and collapsible groups.

        logger.info(
            f"Created Excel-style failure pivot table with shape: {pivot_result.shape}"
        )
        return pivot_result

    except Exception as e:
        logger.error(f"Error creating Excel-style failure pivot table: {str(e)}")
        return pd.DataFrame({"Error": [str(e)]})


@capture_exceptions(
    user_message="Failed to apply conditional formatting for high failures"
)
def apply_failure_highlighting(
    df: pd.DataFrame, threshold_multiplier: float = 2.0
) -> pd.DataFrame:
    """
    Apply statistical threshold-based conditional formatting to highlight high failure counts.

    Args:
        df: Pivot table DataFrame from create_excel_style_failure_pivot
        threshold_multiplier: Multiplier for standard deviation (2.0 = 2σ for yellow, 3.0 for red)

    Returns:
        Styled DataFrame with conditional formatting
    """
    try:
        if df.empty or "Error" in df.columns:
            return df

        # Identify numeric columns (station IDs)
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) == 0:
            return df

        # Calculate statistical thresholds across all numeric data
        all_values = df[numeric_cols].values.flatten()
        all_values = all_values[all_values > 0]  # Exclude zeros

        if len(all_values) == 0:
            return df

        mean_val = np.mean(all_values)
        std_val = np.std(all_values)

        yellow_threshold = mean_val + (threshold_multiplier * std_val)
        red_threshold = mean_val + ((threshold_multiplier + 1) * std_val)

        def highlight_failures(val):
            """Apply color based on failure count thresholds."""
            if pd.isna(val) or val == 0:
                return ""
            elif val >= red_threshold:
                return "background-color: #ffcccc; font-weight: bold"  # Light red
            elif val >= yellow_threshold:
                return "background-color: #fff2cc; font-weight: bold"  # Light yellow
            else:
                return ""

        # Apply styling only to numeric columns
        styled_df = df.style.map(highlight_failures, subset=numeric_cols)

        logger.info(
            f"Applied failure highlighting with thresholds: yellow={yellow_threshold:.1f}, red={red_threshold:.1f}"
        )
        return styled_df

    except Exception as e:
        logger.error(f"Error applying failure highlighting: {str(e)}")
        return df


@capture_exceptions(
    user_message="Failed to create Excel-style error analysis pivot table"
)
def create_excel_style_error_pivot(
    df: pd.DataFrame, operator_filter: Union[str, List[str], None] = None
) -> pd.DataFrame:
    """
    Create Excel-style error analysis pivot table with 3-level hierarchy.

    - Filters: Operator (applied before pivot)
    - Columns: Station ID
    - Rows: Model, error_code, error_message (3-level hierarchical)
    - Values: Count of errors

    Args:
        df: Input DataFrame with columns: Operator, Station ID, Model, error_code, error_message
        operator_filter: Optional filter for Operator column (single string or list)

    Returns:
        Pivot table DataFrame with 3-level hierarchical index and Station ID columns
    """
    try:
        # Step 1: Apply operator filter (like Excel filter)
        filtered_df = df.copy()

        # Handle operator filter - can be string, list, or None
        if operator_filter:
            # Convert to list if string
            if isinstance(operator_filter, str):
                filter_list = [operator_filter]
            else:
                filter_list = operator_filter

            # Only filter if not "All" or ["All"]
            if filter_list != ["All"] and "All" not in filter_list:
                filtered_df = filtered_df[filtered_df["Operator"].isin(filter_list)]

        # Log filter status
        logger.info(
            f"Operator filter: {operator_filter}, DataFrame shape after filter: {filtered_df.shape}"
        )

        # Step 2: Remove rows with missing critical error fields
        # Keep rows that have at least an error code OR error message (not completely empty)
        filtered_df = filtered_df[
            (
                filtered_df["error_code"].notna()
                & (filtered_df["error_code"].astype(str).str.strip() != "")
            )
            | (
                filtered_df["error_message"].notna()
                & (filtered_df["error_message"].astype(str).str.strip() != "")
            )
        ]

        logger.info(
            f"DataFrame shape after removing empty error fields: {filtered_df.shape}"
        )

        # Step 3: Fill missing values and ensure proper data types
        filtered_df = filtered_df.copy()
        filtered_df["error_code"] = (
            filtered_df["error_code"].fillna("(blank)").astype(str)
        )
        filtered_df["error_message"] = (
            filtered_df["error_message"].fillna("(blank)").astype(str)
        )
        filtered_df["Model"] = filtered_df["Model"].fillna("(unknown)").astype(str)

        # Step 4: Create pivot table with correct hierarchy: error_code → Model
        # This creates unique error codes with models nested underneath
        pivot_result = pd.pivot_table(
            filtered_df,
            index=[
                "error_code",
                "error_message",
                "Model",
            ],  # Correct hierarchy: Error Code → Model
            columns=["Station ID"],  # Columns like Excel
            values="Operator",  # Count by Operator field (avoids self-grouping issues)
            aggfunc="count",  # Count occurrences
            fill_value=0,  # Fill missing with 0
        )

        # Step 5: Clean up column names and reset index for Gradio compatibility
        pivot_result.columns.name = None  # Remove 'Station ID' header
        pivot_result = (
            pivot_result.reset_index()
        )  # Make hierarchical index into columns

        logger.info(
            f"Created Excel-style error analysis pivot table with shape: {pivot_result.shape}"
        )
        return pivot_result

    except Exception as e:
        logger.error(f"Error creating Excel-style error analysis pivot table: {str(e)}")
        return pd.DataFrame({"Error": [str(e)]})
