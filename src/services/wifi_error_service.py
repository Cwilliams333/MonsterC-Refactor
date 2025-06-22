"""
WiFi Error Service Module for MonsterC CSV Analysis Tool.

This module provides WiFi error analysis functionality,
extracted from the legacy monolith following the Strangler Fig pattern.
"""

from typing import Any, List, Optional, Tuple, Union

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.common.logging_config import capture_exceptions, get_logger

# Initialize logger
logger = get_logger(__name__)


@capture_exceptions(user_message="Failed to analyze WiFi errors")
def analyze_wifi_errors(
    file, error_threshold: int = 9
) -> Tuple[
    Optional[pd.DataFrame],
    Optional[go.Figure],
    Optional[pd.DataFrame],
    Optional[go.Figure],
]:
    """
    Analyzes WiFi errors in a given data file and returns a summary of the errors.
    Includes hourly breakdown and separate trend lines for each error type.

    Args:
        file: File object containing CSV data
        error_threshold: Threshold percentage for highlighting high error rates

    Returns:
        Tuple of (styled_results, heatmap_figure, styled_pivot, trend_figure)
    """
    # Enable copy on write mode
    pd.options.mode.copy_on_write = True

    # Load and prepare data
    try:
        # Load the data using file loading from common module
        if hasattr(file, "name"):
            df = pd.read_csv(file.name)
        else:
            # Handle case where file is already a DataFrame or path
            from src.common.io import load_data

            df = load_data(file)

        # Convert timestamp string to datetime
        df = df.assign(
            DateTime=pd.to_datetime(
                df["Date"] + " " + df["Hour"], format="%m/%d/%Y %H:%M:%S"
            ),
        )

        # Extract date and hour components
        df = df.assign(
            DateOnly=lambda x: x["DateTime"].dt.date,
            HourOfDay=lambda x: x["DateTime"].dt.hour,
        )

        # Get timeline bounds
        start_time = df["DateTime"].min()
        end_time = df["DateTime"].max()
        date_range = pd.date_range(start=start_time, end=end_time, freq="h")

    except pd.errors.ParserError as e:
        logger.error(f"Error parsing dates: {e}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"Error loading or processing data: {e}")
        return None, None, None, None

    # Define constants
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

    # Filter data and calculate overall statistics
    df_filtered = df[df["Operator"].isin(operators)].copy()

    # Calculate error statistics
    total_transactions = (
        df_filtered["Operator"].value_counts().reindex(operators, fill_value=0)
    )
    wifi_error_breakdown = (
        df_filtered[df_filtered["error_message"].isin(wifi_errors)]
        .groupby(["Operator", "error_message"])
        .size()
        .unstack(fill_value=0)
    )

    # Prepare summary results
    wifi_error_breakdown = wifi_error_breakdown.reindex(
        index=operators, columns=wifi_errors, fill_value=0
    )
    wifi_error_breakdown.loc["Total"] = wifi_error_breakdown.sum()
    wifi_error_counts = wifi_error_breakdown.sum(axis=1)

    total_transactions_with_total = pd.concat(
        [total_transactions, pd.Series({"Total": total_transactions.sum()})]
    )
    wifi_error_percentages = (
        wifi_error_counts / total_transactions_with_total * 100
    ).round(2)

    # Create summary results DataFrame
    results = pd.DataFrame(
        {
            "Operator": operators + ["Grand Total"],
            "Total Transactions": total_transactions_with_total.values,
            "WiFi Errors": wifi_error_counts.values,
            "Error Percentage": wifi_error_percentages.values,
        }
    )

    # Style the results
    def highlight_high_errors(s):
        is_high = s["Error Percentage"] > error_threshold
        return ["background-color: red; color: black" if is_high else "" for _ in s]

    styled_results = results.style.apply(highlight_high_errors, axis=1)

    # Identify high error operators
    high_error_operators = results[results["Error Percentage"] > error_threshold][
        "Operator"
    ].tolist()

    if not high_error_operators:
        logger.info("No high error operators found")
        return styled_results, None, None, None

    # Process data for high error operators
    df_high_errors = df[
        (df["Operator"].isin(high_error_operators))
        & (df["error_message"].isin(wifi_errors))
    ].copy()

    # Create hourly pivot table
    pivot = pd.pivot_table(
        df_high_errors,
        values="IMEI",
        index=["DateOnly", "HourOfDay"],
        columns=["Operator", "error_message"],
        aggfunc="count",
        fill_value=0,
    )

    # Ensure all hours are represented
    dates = sorted(df_high_errors["DateOnly"].unique())
    hours = range(24)
    all_hours = pd.MultiIndex.from_product(
        [dates, hours], names=["DateOnly", "HourOfDay"]
    )
    pivot = pivot.reindex(all_hours, fill_value=0)

    # Helper function for column naming
    def condense_column_name(operator, error):
        color = "Red" if "RED" in operator else "Green"
        primary_or_secondary = "2nd" if operator.split("_")[0][-1] == "2" else "Primary"
        if "DUT connection error" in error:
            error_short = "Connect Error"
        elif "DUT lost WIFI connection" in error:
            error_short = "Lost Wifi"
        else:
            error_short = "Closed socket"
        return f"{color} {primary_or_secondary} - {error_short}"

    # Prepare pivot table for display
    new_columns = [condense_column_name(op, err) for op, err in pivot.columns]
    pivot.columns = new_columns
    display_pivot = pivot.reset_index()
    display_pivot["DateOnly"] = display_pivot["DateOnly"].astype(str)
    display_pivot["Time"] = display_pivot["HourOfDay"].apply(lambda x: f"{x:02d}:00")

    # Style pivot table
    error_cols = [
        col
        for col in display_pivot.columns
        if any(err in col for err in ["Connect Error", "Lost Wifi", "Closed socket"])
    ]
    highlight_threshold = display_pivot[error_cols].mean().mean() * (
        1 + error_threshold / 100
    )

    def style_above_threshold(val):
        if isinstance(val, pd.Series) and val.name in error_cols:
            return [
                (
                    "background-color: yellow; color: black"
                    if v > highlight_threshold
                    else ""
                )
                for v in val
            ]
        return [""] * len(val)

    styled_pivot = display_pivot.style.apply(style_above_threshold)

    # Create heatmap
    heatmap_data = pivot.reset_index().melt(
        id_vars=["DateOnly", "HourOfDay"],
        var_name="Error Type",
        value_name="Error Count",
    )
    heatmap_data["DateTime"] = pd.to_datetime(
        heatmap_data["DateOnly"].astype(str)
        + " "
        + heatmap_data["HourOfDay"].astype(str)
        + ":00:00"
    )

    fig = px.density_heatmap(
        heatmap_data,
        x="Error Type",
        y="DateTime",
        z="Error Count",
        title=f'WiFi Error Heatmap ({start_time.strftime("%m/%d")} - {end_time.strftime("%m/%d")})',
        labels={"Error Count": "Number of Errors", "DateTime": "Time"},
        color_continuous_scale="RdBu_r",
    )

    # Create trend lines using pivot table data directly
    error_trends = pd.DataFrame()
    error_trends["DateTime"] = pd.to_datetime(
        display_pivot["DateOnly"] + " " + display_pivot["Time"]
    )

    # Add error counts from pivot table
    for col in error_cols:  # error_cols already contains our error column names
        error_trends[col] = display_pivot[col]

    # Create trend line plot with the pivot data
    hourly_summary_fig = px.line(
        error_trends,
        x="DateTime",
        y=error_cols,  # Use error columns directly
        title=f'WiFi Errors by Type ({start_time.strftime("%m/%d")} - {end_time.strftime("%m/%d")})',
        labels={
            "DateTime": "Time",
            "value": "Number of Errors",
            "variable": "Error Type",
        },
    )

    # Set custom colors for error types
    color_map = {
        "Connect Error": "rgb(239, 85, 59)",  # Red
        "Lost Wifi": "rgb(99, 110, 250)",  # Blue
        "Closed socket": "rgb(0, 204, 150)",  # Green
    }

    # Apply colors to lines
    for trace in hourly_summary_fig.data:
        for error_type, color in color_map.items():
            if error_type in trace.name:
                trace.line.color = color

    # Apply consistent styling to both plots
    for plot in [fig, hourly_summary_fig]:
        plot.update_layout(
            plot_bgcolor="rgba(255, 255, 255, 0.05)",
            paper_bgcolor="rgba(255, 255, 255, 0.05)",
            font=dict(color="rgba(255, 255, 255, 0.9)"),
            title_font=dict(size=16, color="rgb(107, 99, 246)"),
            xaxis=dict(
                title_font=dict(color="rgb(107, 99, 246)"),
                tickfont=dict(color="rgba(255, 255, 255, 0.9)"),
                gridcolor="rgba(107, 99, 246, 0.1)",
                showgrid=True,
                tickformat="%m/%d %H:%M",
            ),
            yaxis=dict(
                title="Number of Errors",
                title_font=dict(color="rgb(107, 99, 246)"),
                tickfont=dict(color="rgba(255, 255, 255, 0.9)"),
                gridcolor="rgba(107, 99, 246, 0.1)",
                showgrid=True,
            ),
            legend=dict(
                title_font=dict(color="rgb(107, 99, 246)"),
                font=dict(color="rgba(255, 255, 255, 0.9)"),
                bgcolor="rgba(255, 255, 255, 0.05)",
            ),
            margin=dict(t=50, l=50, r=50, b=50),
        )

    # Set specific heights for each plot
    fig.update_layout(height=800)
    hourly_summary_fig.update_layout(height=600)

    logger.info(
        f"Successfully analyzed WiFi errors: {len(high_error_operators)} high error operators found"
    )
    return styled_results, fig, styled_pivot, hourly_summary_fig
