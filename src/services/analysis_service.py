"""
Analysis Service - Extracted from legacy_app.py
Handles main dashboard analysis and KPI generation.
"""

from datetime import datetime
from typing import Any, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Import from our clean common modules
from src.common.io import get_date_range
from src.common.logging_config import capture_exceptions, get_logger
from src.common.plotting import COLOR_SCHEME

logger = get_logger(__name__)


@capture_exceptions(
    user_message="Failed to analyze data. Please check your CSV format.",
    return_value=(None, None, None, None, None, [], [], []),
)
def perform_analysis(
    df: pd.DataFrame,
) -> Tuple[str, go.Figure, go.Figure, go.Figure, go.Figure, List, List, List]:
    """
    Analyze uploaded CSV data and generate dashboard KPIs.

    Args:
        df: Cleaned DataFrame from CSV upload

    Returns:
        Tuple containing:
        - summary_text: Analysis summary markdown
        - overall_status_chart: Pie chart of success/failure rates
        - stations_chart: Bar chart of top failing stations
        - models_chart: Bar chart of top failing models
        - test_cases_chart: Bar chart of top failing test cases
        - stations_data: List for stations dataframe
        - models_data: List for models dataframe
        - test_cases_data: List for test cases dataframe
    """
    logger.info("Starting perform_analysis with DataFrame of shape: %s", df.shape)

    def style_chart(fig, title, height=500):
        """
        Applies consistent styling to plotly figures.

        Args:
            fig: plotly figure object
            title: str, chart title
            height: int, chart height in pixels

        Returns:
            plotly figure object with applied styling
        """
        fig.update_layout(
            title=dict(
                text=title,  # Set the chart title
                font=dict(
                    size=16, color=COLOR_SCHEME["text"]
                ),  # Font size and color for title
                x=0.5,  # Center the title
                xanchor="center",
            ),
            plot_bgcolor=COLOR_SCHEME["background"],  # Set plot background color
            paper_bgcolor="white",  # Set paper background color
            font=dict(
                family="Arial",
                size=12,
                color=COLOR_SCHEME["text"],  # Set font color for the entire chart
            ),
            margin=dict(l=40, r=40, t=60, b=40),  # Define chart margins
            showlegend=True,  # Display legend
            legend=dict(
                orientation="h",  # Horizontal legend
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
            height=height,  # Set the height of the chart
            xaxis=dict(
                gridcolor=COLOR_SCHEME["gridlines"],  # Gridline color
                showline=True,
                linewidth=1,
                linecolor=COLOR_SCHEME["gridlines"],  # Line color
            ),
            yaxis=dict(
                gridcolor=COLOR_SCHEME["gridlines"],
                showline=True,
                linewidth=1,
                linecolor=COLOR_SCHEME["gridlines"],
            ),
        )
        return fig

    def handle_missing_data(df, column):
        """
        Checks and logs missing data in specified column.

        Args:
            df: pandas DataFrame
            column: str, column name to check

        Returns:
            int: number of missing values
        """
        missing = df[column].isna().sum()
        if missing > 0:
            logger.warning("Found %d missing values in %s", missing, column)
        return missing

    # List of required columns for analysis
    required_columns = ["Overall status", "Model", "Station ID", "result_FAIL", "Date"]
    # Check if any required columns are missing
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Check data quality for each required column
    for column in required_columns:
        if column in df.columns:
            handle_missing_data(df, column)

    # Calculate basic statistics from the data
    total_tests = len(df)  # Total number of tests
    valid_tests = len(df[df["Overall status"].notna()])  # Tests with non-null status
    failed_tests = len(df[df["Overall status"] == "FAILURE"])  # Count of failed tests
    error_tests = len(df[df["Overall status"] == "ERROR"])  # Count of error tests
    success_tests = len(
        df[df["Overall status"] == "SUCCESS"]
    )  # Count of successful tests
    pass_rate = (
        (success_tests / valid_tests * 100) if valid_tests > 0 else 0
    )  # Calculate pass rate

    logger.info(
        "Analysis stats - Total: %d, Valid: %d, Success: %d, Failed: %d, Errors: %d",
        total_tests,
        valid_tests,
        success_tests,
        failed_tests,
        error_tests,
    )

    # Create timestamp and date range info
    analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current timestamp
    date_range = get_date_range(df)  # Get date range from data

    # Analyze station failures
    station_failures = df[
        (df["Overall status"].isin(["FAILURE", "ERROR"]))
        & (df["Station ID"].notna())  # Filter for non-null station IDs
    ][
        "Station ID"
    ].value_counts()  # Count failures per station

    # Create bar chart for top 10 failing stations
    if len(station_failures) > 0:
        stations_fig = px.bar(
            x=station_failures.head(10).index,
            y=station_failures.head(10).values,
            title="Top 10 Failing Stations",
            labels={"x": "Station ID", "y": "Number of Failures"},
            color_discrete_sequence=[
                COLOR_SCHEME["FAILURE"]
            ],  # Use failure color for bars
        )
    else:
        # Create empty chart when no failures
        stations_fig = go.Figure()
        stations_fig.update_layout(
            title="Top 10 Failing Stations",
            xaxis_title="Station ID",
            yaxis_title="Number of Failures",
        )
    # Add text and hover information to the chart (only if there are traces)
    if len(station_failures) > 0:
        stations_fig.update_traces(
            texttemplate="%{y}",
            textposition="outside",
            hovertemplate="<b>Station:</b> %{x}<br><b>Failures:</b> %{y}<extra></extra>",
        )
    style_chart(stations_fig, "Top 10 Failing Stations")  # Apply styling

    # Analyze model failures
    model_failures = df[
        (df["Overall status"].isin(["FAILURE", "ERROR"]))
        & (df["Model"].notna())  # Filter for non-null models
        & (df["Model"] != "None")  # Exclude 'None' values
    ][
        "Model"
    ].value_counts()  # Count failures per model

    # Create bar chart for top 10 failing models
    if len(model_failures) > 0:
        models_fig = px.bar(
            x=model_failures.head(10).index,
            y=model_failures.head(10).values,
            title="Top 10 Failing Models",
            labels={"x": "Model", "y": "Number of Failures"},
            color_discrete_sequence=[COLOR_SCHEME["FAILURE"]],
        )
    else:
        # Create empty chart when no failures
        models_fig = go.Figure()
        models_fig.update_layout(
            title="Top 10 Failing Models",
            xaxis_title="Model",
            yaxis_title="Number of Failures",
        )
    # Add text and hover information to the chart (only if there are traces)
    if len(model_failures) > 0:
        models_fig.update_traces(
            texttemplate="%{y}",
            textposition="outside",
            hovertemplate="<b>Model:</b> %{x}<br><b>Failures:</b> %{y}<extra></extra>",
        )
    style_chart(models_fig, "Top 10 Failing Models")  # Apply styling

    # Analyze test case failures
    test_case_failures = df[
        df["result_FAIL"].notna()  # Filter for non-null test cases
        & (df["result_FAIL"] != "")  # Exclude empty strings
    ][
        "result_FAIL"
    ].value_counts()  # Count failures per test case

    # Create bar chart for top 10 failing test cases
    if len(test_case_failures) > 0:
        test_cases_fig = px.bar(
            x=test_case_failures.head(10).index,
            y=test_case_failures.head(10).values,
            title="Top 10 Failing Test Cases",
            labels={"x": "Test Case", "y": "Number of Failures"},
            color_discrete_sequence=[COLOR_SCHEME["FAILURE"]],
        )
    else:
        # Create empty chart when no failures
        test_cases_fig = go.Figure()
        test_cases_fig.update_layout(
            title="Top 10 Failing Test Cases",
            xaxis_title="Test Case",
            yaxis_title="Number of Failures",
        )
    # Add text and hover information to the chart (only if there are traces)
    if len(test_case_failures) > 0:
        test_cases_fig.update_traces(
            texttemplate="%{y}",
            textposition="outside",
            hovertemplate="<b>Test Case:</b> %{x}<br><b>Failures:</b> %{y}<extra></extra>",
        )
    style_chart(test_cases_fig, "Top 10 Failing Test Cases")  # Apply styling

    # Create overall status distribution pie chart
    status_counts = df["Overall status"].value_counts()  # Count test statuses
    overall_fig = px.pie(
        values=status_counts.values,
        names=status_counts.index,
        title="Overall Test Status Distribution",
        color=status_counts.index,
        color_discrete_map=COLOR_SCHEME,  # Map colors to statuses
        hole=0.4,  # Doughnut chart style
    )
    # Add text and hover information to the pie chart
    overall_fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>Status:</b> %{label}<br><b>Count:</b> %{value}<br><b>Percentage:</b> %{percent}<extra></extra>",
    )
    style_chart(overall_fig, "Overall Test Status Distribution")  # Apply styling

    # Prepare data for display in a tabular format for stations
    stations_data = [
        [station, count, round((count / valid_tests * 100), 2)]
        for station, count in station_failures.head(10).items()
    ]

    # Prepare data for display in a tabular format for models
    models_data = [
        [model, count, round((count / valid_tests * 100), 2)]
        for model, count in model_failures.head(10).items()
    ]

    # Prepare data for display in a tabular format for test cases
    test_cases_data = [
        [test, count, round((count / failed_tests * 100), 2) if failed_tests > 0 else 0]
        for test, count in test_case_failures.head(10).items()
    ]

    # Create a comprehensive summary of the analysis
    summary = [
        f"Analysis Time: {analysis_time}",  # Timestamp of the analysis
        f"Data Range: {date_range}",  # Date range of the data
        f"Total Tests: {total_tests:,}",  # Total number of tests
        f"Valid Tests: {valid_tests:,}",  # Total number of valid tests
        f"Success: {success_tests:,}",  # Number of successful tests
        f"Failures: {failed_tests:,}",  # Number of failed tests
        f"Errors: {error_tests:,}",  # Number of error tests
        f"Pass Rate: {pass_rate:.2f}%",  # Pass rate percentage
    ]

    logger.info("Analysis completed successfully")

    # Return the analysis results
    return (
        "\n".join(summary),  # Join the summary list into a single string
        overall_fig,  # Overall test status distribution chart
        stations_fig,  # Top failing stations chart
        models_fig,  # Top failing models chart
        test_cases_fig,  # Top failing test cases chart
        stations_data,  # Data for stations in tabular format
        models_data,  # Data for models in tabular format
        test_cases_data,  # Data for test cases in tabular format
    )
