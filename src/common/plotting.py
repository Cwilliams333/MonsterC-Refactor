"""
Plotting utilities for Monster CSV analysis.

This module contains all plotting and visualization functions used for
analyzing test results, including color schemes, styling functions, and
chart creation utilities.
"""

from typing import Any, Dict, Optional, Union

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objs import Figure

# Define color scheme for consistent styling across charts
COLOR_SCHEME: Dict[str, str] = {
    "SUCCESS": "#2ECC71",  # Green for success
    "FAILURE": "#E74C3C",  # Red for failures
    "ERROR": "#F39C12",  # Orange for errors
    "background": "#F7F9FB",  # Light background
    "gridlines": "#E0E6ED",  # Light gridlines
    "text": "#2C3E50",  # Dark blue text
    "highlight": "#3498DB",  # Light blue for highlights
}


def style_chart(fig: Figure, title: str, height: int = 500) -> Figure:
    """
    Applies consistent styling to plotly figures.

    This function standardizes the appearance of all charts by applying
    a consistent color scheme, layout, and styling options.

    Args:
        fig: Plotly figure object to style
        title: Chart title to display
        height: Chart height in pixels (default: 500)

    Returns:
        Plotly figure object with applied styling

    Example:
        >>> fig = px.bar(data, x='category', y='value')
        >>> styled_fig = style_chart(fig, 'Sales by Category', height=600)
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


def create_summary_chart(data: Union[pd.Series, pd.DataFrame], title: str) -> Figure:
    """
    Creates a summary bar chart based on the provided data with enhanced styling.

    This function generates a bar chart with consistent styling, value labels,
    and color scheme. It's designed for displaying categorical summary data.

    Args:
        data: Pandas Series or DataFrame containing the data to plot.
              Index will be used as x-axis categories, values as y-axis.
        title: Chart title to display

    Returns:
        Plotly figure object containing the styled bar chart

    Example:
        >>> failure_counts = pd.Series({'Model A': 10, 'Model B': 15, 'Model C': 5})
        >>> fig = create_summary_chart(failure_counts, 'Failures by Model')
    """
    # Create local color scheme (for backward compatibility)
    color_scheme = {
        "SUCCESS": "#2ECC71",  # Green
        "FAILURE": "#E74C3C",  # Red
        "ERROR": "#F39C12",  # Orange
        "background": "#F7F9FB",
        "gridlines": "#E0E6ED",
    }

    # Create the bar chart with enhanced styling
    fig = px.bar(
        x=data.index.astype(str),
        y=data.values,
        title=title,
        labels={"x": "Category", "y": "Count"},
        color_discrete_sequence=[color_scheme["FAILURE"]],  # Use failure color for bars
    )

    # Add value labels on top of bars
    fig.update_traces(texttemplate="%{y}", textposition="outside")

    # Apply consistent styling
    fig.update_layout(
        plot_bgcolor=color_scheme["background"],
        paper_bgcolor="white",
        font=dict(size=12),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(
            title="Category",
            tickangle=-45,
            showgrid=True,
            gridwidth=1,
            gridcolor=color_scheme["gridlines"],
            showline=True,
            linewidth=2,
            linecolor=color_scheme["gridlines"],
        ),
        yaxis=dict(
            title="Count",
            showgrid=True,
            gridwidth=1,
            gridcolor=color_scheme["gridlines"],
            showline=True,
            linewidth=2,
            linecolor=color_scheme["gridlines"],
        ),
    )

    return fig


def create_top_errors_chart(data: pd.DataFrame, title: str) -> Figure:
    """
    Creates a bar chart displaying the top errors by model.

    This function generates a grouped bar chart showing error counts
    by model, with different colors for each error type.

    Args:
        data: DataFrame containing error data with columns:
              - 'Model': Model identifier
              - 'count': Error count
              - 'error': Error type/category
        title: Chart title to display

    Returns:
        Plotly figure object containing the styled bar chart

    Example:
        >>> error_data = pd.DataFrame({
        ...     'Model': ['A', 'A', 'B', 'B'],
        ...     'error': ['Error1', 'Error2', 'Error1', 'Error2'],
        ...     'count': [10, 5, 8, 12]
        ... })
        >>> fig = create_top_errors_chart(error_data, 'Top Errors by Model')
    """
    fig = px.bar(
        data,
        x="Model",
        y="count",
        color="error",
        title=title,
        labels={"count": "Error Count", "error": "Error Type"},
    )
    fig.update_layout(xaxis_title="Model", yaxis_title="Count", xaxis_tickangle=-45)
    return fig


def create_overall_status_chart(
    data: Union[pd.Series, pd.DataFrame], title: str
) -> Figure:
    """
    Creates an enhanced status pie chart with custom styling and interactivity.

    This function generates a pie chart showing the distribution of different
    statuses (SUCCESS, FAILURE, ERROR) with custom colors and styling.

    Args:
        data: DataFrame or Series containing the status counts.
              Index should contain status names, values should be counts.
        title: Chart title to display

    Returns:
        Plotly figure object containing the styled pie chart

    Example:
        >>> status_counts = pd.Series({'SUCCESS': 150, 'FAILURE': 30, 'ERROR': 20})
        >>> fig = create_overall_status_chart(status_counts, 'Test Results Distribution')
    """
    # Create a base pie chart with Plotly Express using custom colors for each status
    fig = px.pie(
        values=data.values,  # Values for the pie chart slices
        names=data.index,  # Names/labels for each slice
        title=title,  # Title of the pie chart
        color=data.index,  # Color the slices based on their names
        color_discrete_map={  # Define custom colors for specific statuses
            "SUCCESS": "#00C853",  # Brighter green for success
            "FAILURE": "#D50000",  # Deeper red for failures
            "ERROR": "#FF9100",  # Vibrant orange for errors
        },
    )

    # Update trace properties for enhanced styling and interactivity
    fig.update_traces(
        textposition="inside",  # Display text inside the slices
        textinfo="percent+label",  # Show both percentage and label inside slices
        hovertemplate="<b>%{label}</b><br>"  # Customize hover information
        + "Count: %{value}<br>"  # Show count of each status
        + "Percentage: %{percent}<extra></extra>",  # Show percentage
        marker=dict(line=dict(color="white", width=2)),  # White border around slices
        pull=[0.1, 0.1, 0.1],  # Slightly separate each slice for emphasis
        rotation=90,  # Rotate the starting point of the chart to the top
    )

    # Customize overall layout settings
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",  # Bold the chart title
            x=0.5,  # Center the title horizontally
            y=0.95,  # Position title near the top
            xanchor="center",  # Anchor title to center
            yanchor="top",  # Anchor title to the top
            font=dict(size=20),  # Set font size of the title
        ),
        showlegend=True,  # Display legend on the chart
        legend=dict(
            orientation="h",  # Set legend to be horizontal
            yanchor="bottom",  # Anchor legend to the bottom
            y=-0.2,  # Position legend below the chart
            xanchor="center",  # Center the legend horizontally
            x=0.5,  # Center the legend on the x-axis
        ),
        margin=dict(t=80, b=80, l=40, r=40),  # Set margins around the chart
        paper_bgcolor="rgba(0,0,0,0)",  # Set paper background to be transparent
        plot_bgcolor="rgba(0,0,0,0)",  # Set plot background to be transparent
    )

    return fig  # Return the fully customized figure


def handle_missing_data(df: pd.DataFrame, column: str) -> int:
    """
    Checks and logs missing data in specified column.

    This helper function identifies missing values in a DataFrame column
    and prints a warning if any are found.

    Args:
        df: Pandas DataFrame to check
        column: Column name to check for missing values

    Returns:
        Number of missing values found

    Example:
        >>> missing_count = handle_missing_data(df, 'Overall status')
        Warning: Found 5 missing values in Overall status
        >>> print(missing_count)
        5
    """
    missing = df[column].isna().sum()
    if missing > 0:
        print(f"Warning: Found {missing} missing values in {column}")
    return missing


# Additional utility functions for enhanced plotting capabilities


def create_time_series_chart(
    df: pd.DataFrame,
    date_column: str,
    value_column: str,
    title: str,
    group_by: Optional[str] = None,
) -> Figure:
    """
    Creates a time series line chart with optional grouping.

    Args:
        df: DataFrame containing the time series data
        date_column: Name of the column containing dates
        value_column: Name of the column containing values to plot
        title: Chart title
        group_by: Optional column name to group data by (creates multiple lines)

    Returns:
        Plotly figure object containing the time series chart
    """
    if group_by:
        fig = px.line(df, x=date_column, y=value_column, color=group_by, title=title)
    else:
        fig = px.line(df, x=date_column, y=value_column, title=title)

    # Apply consistent styling
    return style_chart(fig, title)


def create_heatmap(
    pivot_data: pd.DataFrame, title: str, color_scale: str = "RdYlGn_r"
) -> Figure:
    """
    Creates a heatmap visualization from pivot table data.

    Args:
        pivot_data: Pivot table DataFrame with values to visualize
        title: Chart title
        color_scale: Plotly color scale to use (default: 'RdYlGn_r' for red-yellow-green reversed)

    Returns:
        Plotly figure object containing the heatmap
    """
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale=color_scale,
            hoverongaps=False,
        )
    )

    fig.update_layout(title=title, xaxis_title="", yaxis_title="")

    return style_chart(fig, title)
