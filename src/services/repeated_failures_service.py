"""
Repeated Failures Service Module for MonsterC CSV Analysis Tool.

This module provides repeated failures analysis functionality,
extracted from the legacy monolith following the Strangler Fig pattern.
"""

from typing import Any, List, Optional, Tuple, Union

import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.common.logging_config import capture_exceptions, get_logger
from src.common.mappings import DEVICE_MAP

# Initialize logger
logger = get_logger(__name__)


@capture_exceptions(user_message="Failed to get model code")
def get_model_code(model: str) -> str:
    """
    Helper function to get model code from device map.

    Args:
        model: Device model name

    Returns:
        Model code or 'Unknown' if not found
    """
    code = DEVICE_MAP.get(model, "Unknown")
    if isinstance(code, list):
        return code[0]  # Take first code if multiple exist
    return code


@capture_exceptions(user_message="Failed to create summary")
def create_summary(df: pd.DataFrame) -> str:
    """
    Create markdown summary of the dataframe.

    Args:
        df: DataFrame with repeated failures data

    Returns:
        Markdown formatted summary table
    """
    summary = f"Found {len(df)} instances of repeated failures:\n\n"
    summary += """| Model | Model Code | Station ID | Test Case | TC Count | IMEI Count |
|:------|:-----------|:-----------|:----------|--------:|----------:|
"""
    # Note the right alignment (--------:) for numeric columns
    for _, row in df.iterrows():
        summary += f"| {row['Model']} | {row['Model Code']} | {row['Station ID']} | {row['result_FAIL']} | {row['TC Count']} | {row['IMEI Count']} |\n"

    return summary


@capture_exceptions(user_message="Failed to create plot")
def create_plot(df: pd.DataFrame) -> go.Figure:
    """
    Create bar chart visualization of the data.

    Args:
        df: DataFrame with repeated failures data

    Returns:
        Plotly figure with bar chart
    """
    fig = px.bar(
        df,
        x="Station ID",
        y="TC Count",
        color="Model",
        hover_data=["result_FAIL", "IMEI Count"],
        title=f"Filtered Repeated Failures",
        labels={"TC Count": "Number of Test Case Failures"},
        height=600,
    )

    fig.update_layout(
        xaxis_title="Station ID",
        yaxis_title="Number of Test Case Failures",
        xaxis_tickangle=-45,
        legend_title="Model",
        barmode="group",
    )

    return fig


@capture_exceptions(user_message="Failed to analyze repeated failures")
def analyze_repeated_failures(
    df: pd.DataFrame, min_failures: int = 4
) -> Tuple[str, go.Figure, gr.Dataframe, gr.Dropdown]:
    """
    Analyzes repeated failures in test data and returns summary, chart, and interactive components.

    Args:
        df: Input DataFrame with test data
        min_failures: Minimum number of failures to be considered "repeated"

    Returns:
        Tuple of (summary_text, figure, interactive_dataframe, dropdown)
    """
    try:
        # If df is a file object, load it first
        if hasattr(df, "name"):
            from src.common.io import load_data

            df = load_data(df)

        # Filter for FAILURE in Overall status
        failure_df = df[df["Overall status"] == "FAILURE"]
        logger.info(f"Found {len(failure_df)} failures")

        # Create initial aggregation with both counts
        agg_df = (
            failure_df.groupby(["Model", "Station ID", "result_FAIL"])
            .agg({"IMEI": ["count", "nunique"]})
            .reset_index()
        )

        # Rename columns
        agg_df.columns = [
            "Model",
            "Station ID",
            "result_FAIL",
            "TC Count",
            "IMEI Count",
        ]

        # Filter for minimum test case failures threshold
        repeated_failures = agg_df[agg_df["TC Count"] >= min_failures].copy()
        logger.info(f"Found {len(repeated_failures)} instances of repeated failures")

        # Add Model Code column
        repeated_failures["Model Code"] = repeated_failures["Model"].apply(
            get_model_code
        )

        # Sort by TC Count in descending order
        repeated_failures = repeated_failures.sort_values("TC Count", ascending=False)

        # Create summary and plot
        summary = f"Found {len(repeated_failures)} instances of repeated failures:\n\n"
        summary += """<div class="table-container">
| Model | Code | Station ID | Test Case | TC Count | IMEI Count |
|:------|:-----|:-----------|:----------|--------:|----------:|
"""
        for index, row in repeated_failures.iterrows():
            try:
                summary_row = f"| {row['Model']} | {row['Model Code']} | {row['Station ID']} | {row['result_FAIL']} | {row['TC Count']} | {row['IMEI Count']} |\n"
                summary += summary_row
            except Exception as row_error:
                logger.error(f"Error on row {index}: {row_error}")
                raise row_error

        summary += "</div>"

        # Create bar chart
        fig = px.bar(
            repeated_failures,
            x="Station ID",
            y="TC Count",
            color="Model",
            hover_data=["result_FAIL", "IMEI Count"],
            title=f"Repeated Failures (≥{min_failures} times)",
            labels={"TC Count": "Number of Test Case Failures"},
            height=600,
        )

        fig.update_layout(
            xaxis_title="Station ID",
            yaxis_title="Number of Test Case Failures",
            xaxis_tickangle=-45,
            legend_title="Model",
            barmode="group",
        )

        # Create interactive dataframe with explicit column names
        interactive_df = gr.Dataframe(
            value=repeated_failures,
            headers=repeated_failures.columns.tolist(),
            interactive=True,
            type="pandas",  # Specify the type as pandas
            show_label=True,
            label="Repeated Failures Analysis",
            column_widths=None,
            wrap=True,  # Enable column reordering
        )

        # Get test cases for dropdown
        test_case_counts = repeated_failures.groupby("result_FAIL")["TC Count"].max()
        sorted_test_cases = test_case_counts.sort_values(ascending=False).index.tolist()

        dropdown_choices = ["Select All", "Clear All"] + [
            f"{test_case} ({test_case_counts[test_case]}) max failures"
            for test_case in sorted_test_cases
        ]

        logger.info("Successfully completed repeated failures analysis")
        return (
            summary,
            fig,
            interactive_df,
            gr.Dropdown(
                choices=dropdown_choices,
                value=dropdown_choices[2:],
                label="Filter by Test Case",
                multiselect=True,
            ),
        )

    except Exception as e:
        logger.error(f"Error in analyze_repeated_failures: {str(e)}")
        error_message = f"""<div class="table-container">
## Error Occurred
| Error Details |
|:--------------|
| {str(e)} |
Please check your input and try again.
</div>"""
        return error_message, None, None, None


@capture_exceptions(user_message="Failed to update summary chart and data")
def update_summary_chart_and_data(
    repeated_failures_df: pd.DataFrame, sort_by: str, selected_test_cases: List[str]
) -> Tuple[str, go.Figure, gr.Dataframe]:
    """
    Updates the summary chart, interactive dataframe, and test case filter options
    based on sorting and filtering preferences.

    Args:
        repeated_failures_df: Input dataframe with repeated failures data
        sort_by: Column name to sort by; one of "TC Count", "Model", "Station ID", "Test Case", or "Model Code"
        selected_test_cases: List of selected test cases to filter by

    Returns:
        Tuple of (summary_text, plotly_figure, interactive_dataframe)
    """

    # Check for no data
    if repeated_failures_df is None or len(repeated_failures_df) == 0:
        return "No data available to sort/filter", None, None

    # Make a copy of the dataframe so we don't modify the original
    df = repeated_failures_df.copy()

    # Handle test case filtering
    if selected_test_cases:
        # If the user chose "Select All", do nothing
        if "Select All" in selected_test_cases:
            pass
        # If the user chose "Clear All", filter out all test cases
        elif "Clear All" in selected_test_cases:
            df = df[df["result_FAIL"] == ""]
        # If the user chose specific test cases, filter for those
        else:
            # Convert the selected test cases to the actual test case names without counts
            selected_actual_cases = [
                test_case.split(" (")[0] for test_case in selected_test_cases
            ]
            # Filter the dataframe for the selected test cases
            df = df[df["result_FAIL"].isin(selected_actual_cases)]

    # Sort the dataframe by the selected column
    sort_column_map = {
        "TC Count": "TC Count",
        "Model": "Model",
        "Station ID": "Station ID",
        "Test Case": "result_FAIL",
        "Model Code": "Model Code",
    }

    df = df.sort_values(sort_column_map[sort_by], ascending=False)

    # Create an updated interactive dataframe with explicit column names
    interactive_df = gr.Dataframe(
        value=df,
        headers=df.columns.tolist(),
        interactive=True,
        wrap=True,
        show_label=True,
        column_widths=None,
        label="Filtered Repeated Failures",
    )

    # Return the updated summary text, plotly figure, and interactive dataframe
    return create_summary(df), create_plot(df), interactive_df


@capture_exceptions(user_message="Failed to update summary")
def update_summary(
    repeated_failures_df: pd.DataFrame, sort_by: str, selected_test_cases: List[str]
) -> str:
    """
    Updates the summary text based on sorting and filtering preferences.

    Args:
        repeated_failures_df: Input dataframe with repeated failures data
        sort_by: Column name to sort by
        selected_test_cases: List of selected test cases to filter by

    Returns:
        Updated summary text
    """
    try:
        if repeated_failures_df is None or len(repeated_failures_df) == 0:
            return "No data available to sort/filter"

        df = repeated_failures_df.copy()

        # Handle Select All/Clear All and apply test case filter
        if selected_test_cases:
            if "Select All" in selected_test_cases:
                # Include all test cases
                pass
            elif "Clear All" in selected_test_cases:
                # Clear all selections
                df = df[df["result_FAIL"] == ""]  # This will create an empty result
            else:
                # Filter for selected test cases
                selected_actual_cases = [
                    test_case.split(" (")[0] for test_case in selected_test_cases
                ]
                df = df[df["result_FAIL"].isin(selected_actual_cases)]

        # Apply sorting
        sort_column_map = {
            "TC Count": "TC Count",
            "Model": "Model",
            "Station ID": "Station ID",
            "Test Case": "result_FAIL",
            "Model Code": "Model Code",  # Add this line to support sorting by Model Code
        }
        df = df.sort_values(sort_column_map[sort_by], ascending=False)

        # Create summary with proper markdown table formatting
        summary = f"Found {len(df)} instances of repeated failures:\n\n"
        summary += "| Model              | Model Code       | Station ID    | Test Case                    | Count |\n"
        summary += "|:-------------------|:----------------|:--------------|:----------------------------|-------:|\n"

        for _, row in df.iterrows():
            summary += f"| {row['Model']:<17} | {row['Model Code']:<14} | {row['Station ID']:<12} | {row['result_FAIL']:<26} | {row['TC Count']:>5} |\n"

        return summary
    except Exception as e:
        logger.error(f"Error updating summary: {str(e)}")
        return f"Error updating summary: {str(e)}"


@capture_exceptions(user_message="Failed to handle test case selection")
def handle_test_case_selection(
    evt: gr.SelectData, selected_test_cases: List[str]
) -> List[str]:
    """
    Handles the Select All/Clear All functionality for test case filter.

    Args:
        evt: Gradio SelectData event
        selected_test_cases: Currently selected test cases

    Returns:
        Updated list of selected test cases
    """
    if evt.value == "Select All":
        # This needs to be handled by the UI layer as it needs access to test_case_filter.choices
        # Return a special marker that the UI can recognize
        return ["__SELECT_ALL__"]
    elif evt.value == "Clear All":
        return []
    return selected_test_cases
