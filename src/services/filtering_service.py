"""
Filtering Service - Extracted from legacy_app.py
Handles all data filtering operations and UI visibility updates.
"""

from typing import Tuple, List, Dict, Any, Union
import pandas as pd
import plotly.graph_objects as go
import gradio as gr

# Import from our clean common modules
from src.common.mappings import resolve_station
from src.common.plotting import create_summary_chart, create_overall_status_chart
from src.common.logging_config import capture_exceptions, get_logger

logger = get_logger(__name__)


def get_unique_values(df: pd.DataFrame, column: str) -> List[str]:
    """
    Returns a sorted list of unique values in a given column of a pandas DataFrame.
    
    Args:
        df: pandas DataFrame
        column: column name to extract unique values from
        
    Returns:
        List of sorted unique string values (excluding None/NaN)
    """
    unique_values = df[column].unique()
    # Convert to strings and remove None/NaN values
    unique_values = [
        str(val) for val in unique_values if val is not None and not pd.isna(val)
    ]
    return sorted(unique_values)


def format_dataframe(data) -> pd.DataFrame:
    """
    Formats a given dataframe for display.

    The purpose of this function is to take an input DataFrame and format it
    in a way that is easy to display. The output DataFrame should have two
    columns: "Category" and "Count".
    """
    df = pd.DataFrame({"Count": data})
    # Reset index to create a new column for the index
    df = df.reset_index()
    
    # Check if we have a MultiIndex
    if len(df.columns) == 3:  # MultiIndex case
        # Create a new column called "Category" that combines the two index columns
        df['Category'] = df.iloc[:, 0].astype(str) + "-" + df.iloc[:, 1].astype(str)
        # Drop the original index columns and rename
        df = df[['Category', 'Count']]
    else:
        # Single index case - rename columns
        df.columns = ['Category', 'Count']
    
    return df


def analyze_top_errors_by_model(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Analyzes the top errors by model from the DataFrame.
    
    Args:
        df: DataFrame containing test results
        top_n: Number of top errors to return
        
    Returns:
        DataFrame with Model, error, and count columns
    """
    try:
        # Filter for failures and non-empty result_FAIL
        failed_df = df[(df['Overall status'] == 'FAILURE') & 
                      (df['result_FAIL'].notna()) & 
                      (df['result_FAIL'] != '')]
        
        if failed_df.empty:
            return pd.DataFrame(columns=['Model', 'error', 'count'])
        
        # Group by Model and result_FAIL to get error counts
        error_counts = failed_df.groupby(['Model', 'result_FAIL']).size().reset_index(name='count')
        
        # Sort by count descending and get top_n
        top_errors = error_counts.sort_values('count', ascending=False).head(top_n)
        top_errors.columns = ['Model', 'error', 'count']
        
        return top_errors
    except Exception as e:
        logger.error("Error analyzing top errors by model: %s", str(e))
        return pd.DataFrame(columns=['Model', 'error', 'count'])


def analyze_overall_status(df: pd.DataFrame) -> pd.Series:
    """
    Analyzes the overall status distribution from the DataFrame.
    
    Args:
        df: DataFrame containing test results
        
    Returns:
        Series with status counts
    """
    try:
        return df['Overall status'].value_counts()
    except Exception as e:
        logger.error("Error analyzing overall status: %s", str(e))
        return pd.Series()


@capture_exceptions(
    user_message="Failed to update filter visibility",
    return_value=(gr.update(), gr.update(), gr.update())
)
def update_filter_visibility(filter_type: str) -> Tuple[gr.update, gr.update, gr.update]:
    """
    Updates the visibility of filter dropdowns based on the selected filter type.

    Args:
        filter_type: The type of filter to apply, which determines which dropdowns are visible.

    Returns:
        Tuple of (operator_filter_update, source_filter_update, station_id_filter_update)
    """
    logger.info("Updating filter visibility for type: %s", filter_type)
    
    # Check if no filter is selected, hide all dropdowns
    if filter_type == "No Filter":
        return (
            gr.update(visible=False),  # operator_filter
            gr.update(visible=False),  # source_filter
            gr.update(visible=False)   # station_id_filter
        )
    # Check if filtering by operator, show only relevant dropdowns
    elif filter_type == "Filter by Operator":
        return (
            gr.update(visible=True),   # operator_filter
            gr.update(visible=False),  # source_filter
            gr.update(visible=True)    # station_id_filter
        )
    else:  # Assume filtering by source if not by operator
        return (
            gr.update(visible=False),  # operator_filter
            gr.update(visible=True),   # source_filter
            gr.update(visible=True)    # station_id_filter
        )


@capture_exceptions(
    user_message="Failed to filter data. Please check your selections.",
    return_value=(None, None, None, None, None, None, None)
)
def filter_data(df: pd.DataFrame, filter_type: str, operator: str, source: str, station_id: str) -> Tuple[str, go.Figure, go.Figure, go.Figure, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Filter a given DataFrame by Operator and/or Station ID with horizontal layout.
    
    Args:
        df: DataFrame to filter
        filter_type: Type of filter ("Filter by Operator", "Filter by Source", or "No Filter")
        operator: Operator selection
        source: Source selection  
        station_id: Station ID selection
        
    Returns:
        Tuple containing:
        - summary: Formatted summary markdown
        - models_chart: Chart of top failing models
        - test_cases_chart: Chart of top failing test cases
        - status_chart: Overall status distribution chart
        - models_df: DataFrame of top models
        - test_cases_df: DataFrame of top test cases
        - errors_df: DataFrame of top errors
    """
    logger.info("Filtering data: type=%s, operator=%s, source=%s, station_id=%s", 
                filter_type, operator, source, station_id)
    
    filtered_df = df.copy()

    # Apply filters based on selection
    if filter_type == "Filter by Operator" and operator != "All":
        filtered_df = filtered_df[filtered_df["Operator"] == operator]
    elif filter_type == "Filter by Source" and source != "All":
        filtered_df = filtered_df[filtered_df["Source"] == source]
    
    # Apply Station ID filter if selected
    if station_id != "All":
        filtered_df = filtered_df[filtered_df["Station ID"] == station_id]

    total_devices = filtered_df['IMEI'].nunique()
    total_tests = len(filtered_df)
    failures = filtered_df[filtered_df['Overall status'] == 'FAILURE']
    successes = filtered_df[filtered_df['Overall status'] == 'SUCCESS']

    # Use flexbox for layout and keep markdown intact
    summary = """<div style='display: flex; flex-wrap: wrap; gap: 20px; justify-content: space-between;'>

<div style='flex: 1; min-width: 300px;'>

## Overall Statistics

| Metric              | Value                |
|:--------------------|:--------------------|
| Total Unique Devices | {devices:<18} |
| Total Tests         | {tests:<18} |

## Filter Settings

| Filter    | Value                |
|:----------|:--------------------|
| Operator  | {operator:<18} |
| Station ID| {station_id:<18} |

## Test Results

| Result    | Count    | Percentage         |
|:----------|:---------|:------------------|
| Successes | {successes:<8} | {success_rate:>6.2f}% |
| Failures  | {failures:<8} | {failure_rate:>6.2f}% |

</div>

<div style='flex: 1; min-width: 300px;'>

## Top 5 Failing Models

| Model              | Failure Count       |
|:-------------------|:-------------------|
{model_rows}

## Top 5 Failing Test Cases

| Test Case                    | Failure Count       |
|:----------------------------|:-------------------|
{test_rows}

</div>

<div style='flex: 1; min-width: 300px;'>

## Active Station IDs

| Station ID         | Machine            |
|:------------------|:------------------|
{station_rows}

</div>

</div>""".format(
        devices=total_devices,
        tests=total_tests,
        operator=operator if operator != "All" else "All",
        station_id=station_id if station_id != "All" else "All",
        successes=len(successes),
        failures=len(failures),
        success_rate=len(successes)/total_tests*100 if total_tests else 0,
        failure_rate=len(failures)/total_tests*100 if total_tests else 0,
        model_rows="\n".join(
            f"| {model:<17} | {count:<17} |"
            for model, count in filtered_df[filtered_df['Overall status'] == 'FAILURE']['Model'].value_counts().head().items()
        ),
        test_rows="\n".join(
            f"| {test:<26} | {count:<17} |"
            for test, count in filtered_df[filtered_df['Overall status'] == 'FAILURE']['result_FAIL'].value_counts().head().items()
        ),
        station_rows="\n".join(
            f"| {station:<16} | {resolve_station(station):<17} |"
            for station in sorted(filtered_df['Station ID'].unique())
        )
    )

    # Generate analysis data
    top_errors = analyze_top_errors_by_model(filtered_df)
    overall_status = analyze_overall_status(filtered_df)
    top_models = filtered_df["Model"].value_counts().head()
    top_test_cases = filtered_df["result_FAIL"].value_counts().head()

    title_suffix = f"for Operator {operator}" if operator != "All" else f"for Station {station_id}" if station_id != "All" else "(All Data)"

    models_chart = create_summary_chart(
        top_models, f"Top 5 Failing Models {title_suffix}"
    )
    test_cases_chart = create_summary_chart(
        top_test_cases, f"Top 5 Failing Test Cases {title_suffix}"
    )
    status_chart = create_overall_status_chart(
        overall_status, f"Overall Status {title_suffix}"
    )

    models_df = format_dataframe(top_models)
    test_cases_df = format_dataframe(top_test_cases)
    errors_df = top_errors[["Model", "error", "count"]]

    logger.info("Filtering completed successfully. Filtered to %d rows", len(filtered_df))

    return (
        summary,
        models_chart,
        test_cases_chart,
        status_chart,
        models_df,
        test_cases_df,
        errors_df,
    )


@capture_exceptions(
    user_message="Failed to apply filters and sorting",
    return_value=(pd.DataFrame(), "Error applying filters")
)
def apply_filter_and_sort(df: pd.DataFrame, sort_columns: List[str], operator: str, model: str, 
                         manufacturer: str, source: str, overall_status: str, station_id: str, 
                         result_fail: str) -> Tuple[pd.DataFrame, str]:
    """
    Applies filters and sorting to a pandas DataFrame.

    Args:
        df: The original DataFrame to be filtered and sorted.
        sort_columns: A list of column names to sort the DataFrame by.
        operator: The operator to filter by.
        model: The model to filter by.
        manufacturer: The manufacturer to filter by.
        source: The source to filter by.
        overall_status: The overall status to filter by.
        station_id: The station id to filter by.
        result_fail: The result fail to filter by.

    Returns:
        Tuple of (filtered_df, summary_string)
    """
    logger.info("Applying filters and sorting")
    
    # Start with a copy of the original DataFrame to avoid modifying the original data.
    filtered_df = df.copy()

    # Define the columns to filter and their corresponding values.
    filter_columns = ["Operator", "Model", "Manufacturer", "Source", "Overall status", "Station ID", "result_FAIL"]
    filter_values = [operator, model, manufacturer, source, overall_status, station_id, result_fail]
    
    # Iterate over filter columns and their corresponding values.
    for column, value in zip(filter_columns, filter_values):
        # Check if the value is not None, not "All", and not ["All"].
        if value and value != "All" and value != ["All"]:
            # Check if the value is a list, indicating multiselect filters.
            if isinstance(value, list):
                # Filter the DataFrame to include only rows where the column value is in the list.
                filtered_df = filtered_df[filtered_df[column].isin(value)]
            else:
                # Filter the DataFrame to include only rows where the column value matches exactly.
                filtered_df = filtered_df[filtered_df[column].astype(str) == value]

    # Check if there are columns to sort by.
    if sort_columns:
        # Sort the DataFrame by the specified columns.
        filtered_df = filtered_df.sort_values(by=sort_columns)

    # Prepare a summary of the number of rows after filtering.
    summary = f"Filtered data: {len(filtered_df)} rows\n"
    applied_filters = []
    
    # Create a list of applied filters for the summary.
    for k, v in zip(filter_columns, filter_values):
        if v and v != "All" and v != ["All"]:
            if isinstance(v, list):
                # Append the filter to the summary if it's a list.
                applied_filters.append(f"{k}={', '.join(v)}")
            else:
                # Append the filter to the summary if it's a single value.
                applied_filters.append(f"{k}={v}")
    
    # Add the applied filters and sorting information to the summary.
    summary += f"Applied filters: {', '.join(applied_filters) if applied_filters else 'None'}\n"
    summary += f"Sorted by: {', '.join(sort_columns) if sort_columns else 'None'}"

    logger.info("Filtering and sorting completed. Result: %d rows", len(filtered_df))
    
    # Return the filtered and sorted DataFrame along with the summary.
    return filtered_df, summary


def update_filter_dropdowns(df: pd.DataFrame) -> List[gr.Dropdown]:
    """
    Generate a list of dropdown widgets for each filter column in the provided DataFrame.

    Args:
        df: The DataFrame to generate dropdown widgets for.
        
    Returns:
        List of Gradio dropdown widgets
    """
    logger.info("Updating filter dropdowns")
    
    # Define the columns that we want to create dropdowns for
    filter_columns = ["Operator", "Model", "Manufacturer", "Source", "Overall status", "Station ID", "result_FAIL"]
    dropdowns = []
    
    for column in filter_columns:
        if column in df.columns:
            # Get unique values and add "All" option
            unique_values = ["All"] + get_unique_values(df, column)
            dropdown = gr.Dropdown(
                choices=unique_values,
                value="All",
                label=column,
                interactive=True
            )
            dropdowns.append(dropdown)
    
    return dropdowns