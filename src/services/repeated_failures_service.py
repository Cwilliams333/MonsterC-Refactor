"""
Repeated Failures Service Module for MonsterC CSV Analysis Tool.

This module provides repeated failures analysis functionality,
extracted from the legacy monolith following the Strangler Fig pattern.
"""

import html
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
    Create beautiful HTML summary of the dataframe with enhanced styling.

    Args:
        df: DataFrame with repeated failures data

    Returns:
        HTML formatted summary with beautiful styling
    """
    # Calculate severity levels based on failure counts
    max_tc_count = df["TC Count"].max() if len(df) > 0 else 0

    # Create HTML with enhanced styling
    html_content = f"""
    <div style="padding: 20px;">
        <!-- Header Section -->
        <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
            <h2 style="color: white; margin: 0 0 10px 0; font-size: 24px; text-align: center;">
                🔍 Repeated Failures Analysis
            </h2>
            <p style="color: white; margin: 0; text-align: center; opacity: 0.9; font-size: 16px;">
                Found <span style="font-size: 28px; font-weight: bold;">{len(df)}</span> instances of repeated failures
            </p>
        </div>

        <!-- Table Container -->
        <div style="background: white; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.08); overflow: hidden;">
            <table style="width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <!-- Table Header -->
                <thead>
                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">📱</span> Model
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">🔤</span> Code
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">🏭</span> Station
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">🧪</span> Test Case
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: center; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span style="opacity: 0.8;">📊</span> Count
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: center; color: white; font-weight: 600; font-size: 21px;">
                            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span style="opacity: 0.8;">📱</span> IMEIs
                            </div>
                        </th>
                    </tr>
                </thead>
                <!-- Table Body -->
                <tbody>
    """

    # Add table rows with enhanced styling
    for idx, row in df.iterrows():
        # Determine severity color based on TC Count
        tc_count = row["TC Count"]
        if tc_count >= max_tc_count * 0.8:
            severity_color = "#dc3545"  # Critical (Red)
            severity_bg = "rgba(220, 53, 69, 0.1)"
            severity_icon = "🔴"
        elif tc_count >= max_tc_count * 0.5:
            severity_color = "#fd7e14"  # High (Orange)
            severity_bg = "rgba(253, 126, 20, 0.1)"
            severity_icon = "🟠"
        elif tc_count >= max_tc_count * 0.3:
            severity_color = "#ffc107"  # Medium (Yellow)
            severity_bg = "rgba(255, 193, 7, 0.1)"
            severity_icon = "🟡"
        else:
            severity_color = "#28a745"  # Low (Green)
            severity_bg = "rgba(40, 167, 69, 0.1)"
            severity_icon = "🟢"

        # Alternate row background
        row_bg = "#f8f9fa" if idx % 2 == 0 else "#ffffff"

        # Escape HTML special characters
        model_escaped = html.escape(str(row["Model"]))
        model_code_escaped = html.escape(str(row["Model Code"]))
        station_id_escaped = html.escape(str(row["Station ID"]))
        result_fail_escaped = html.escape(str(row["result_FAIL"]))

        html_content += f"""
                    <tr style="background: {row_bg}; transition: all 0.2s ease;"
                        onmouseover="this.style.background='linear-gradient(90deg, {severity_bg} 0%, rgba(255,255,255,0) 100%)'; this.style.transform='translateX(5px)';"
                        onmouseout="this.style.background='{row_bg}'; this.style.transform='translateX(0)';">
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 21px; font-weight: 500; color: #333;">
                            {model_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #6c757d; font-family: monospace;">
                            {model_code_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #495057;">
                            {station_id_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #333; max-width: 300px;">
                            <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #333;" title="{result_fail_escaped}">
                                {result_fail_escaped}
                            </div>
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; text-align: center;">
                            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span style="font-size: 18px;">{severity_icon}</span>
                                <span style="font-size: 24px; font-weight: bold; color: {severity_color};">
                                    {row['TC Count']}
                                </span>
                            </div>
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; text-align: center;">
                            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 6px 16px; border-radius: 20px; font-size: 19.5px; font-weight: 500;">
                                {row['IMEI Count']}
                            </span>
                        </td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>
        </div>

        <!-- Summary Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px;">
    """

    # Calculate summary statistics
    if len(df) > 0:
        total_failures = df["TC Count"].sum()
        total_imeis = df["IMEI Count"].sum()
        unique_models = df["Model"].nunique()
        unique_stations = df["Station ID"].nunique()

        html_content += f"""
            <!-- Total Failures Card -->
            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Total Failures</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{total_failures:,}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">🚨</div>
                </div>
            </div>

            <!-- Affected IMEIs Card -->
            <div style="background: linear-gradient(135deg, #5f27cd 0%, #341f97 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(95, 39, 205, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Affected IMEIs</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{total_imeis:,}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">📱</div>
                </div>
            </div>

            <!-- Unique Models Card -->
            <div style="background: linear-gradient(135deg, #00d2d3 0%, #01a3a4 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(0, 210, 211, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Unique Models</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{unique_models}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">📊</div>
                </div>
            </div>

            <!-- Test Stations Card -->
            <div style="background: linear-gradient(135deg, #feca57 0%, #ff9ff3 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(254, 202, 87, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Test Stations</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{unique_stations}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">🏭</div>
                </div>
            </div>
        """

    html_content += """
        </div>

        <!-- Legend -->
        <div style="margin-top: 20px; padding: 15px; background: rgba(107, 99, 246, 0.05); border-radius: 10px; border: 1px solid rgba(107, 99, 246, 0.2);">
            <h4 style="margin: 0 0 10px 0; color: #667eea; font-size: 24px;">📊 Severity Legend</h4>
            <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 19.5px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🔴</span> <span style="color: #dc3545; font-weight: 500;">Critical</span> <span style="color: #6c757d;">(≥80% of max)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🟠</span> <span style="color: #fd7e14; font-weight: 500;">High</span> <span style="color: #6c757d;">(≥50% of max)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🟡</span> <span style="color: #ffc107; font-weight: 500;">Medium</span> <span style="color: #6c757d;">(≥30% of max)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🟢</span> <span style="color: #28a745; font-weight: 500;">Low</span> <span style="color: #6c757d;">(<30% of max)</span>
                </div>
            </div>
        </div>
    </div>

    <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Apply animation to all cards */
        div[style*="grid-template-columns"] > div {
            animation: fadeIn 0.6s ease-out forwards;
        }

        div[style*="grid-template-columns"] > div:nth-child(2) {
            animation-delay: 0.1s;
        }

        div[style*="grid-template-columns"] > div:nth-child(3) {
            animation-delay: 0.2s;
        }

        div[style*="grid-template-columns"] > div:nth-child(4) {
            animation-delay: 0.3s;
        }

        /* Hover effect for cards */
        div[style*="grid-template-columns"] > div:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
        }
    </style>
    """

    return html_content


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
) -> Tuple[str, Any, Any, Any]:
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

        # Create summary using the beautiful HTML format
        summary = create_summary(repeated_failures)

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
        error_message = f"""
        <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); border-radius: 15px; color: white;">
            <h3 style="margin: 0; font-size: 24px;">⚠️ Error Occurred</h3>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{html.escape(str(e))}</p>
            <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.7;">Please check your input and try again.</p>
        </div>
        """
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
        return "No data available to sort/filter", None, gr.Dataframe()

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
            return """
            <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                <h3 style="margin: 0; font-size: 24px;">📊 No Data Available</h3>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">No data available to sort/filter</p>
            </div>
            """

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

        # Use the beautiful create_summary function
        return create_summary(df)
    except Exception as e:
        logger.error(f"Error updating summary: {str(e)}")
        return f"""
        <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); border-radius: 15px; color: white;">
            <h3 style="margin: 0; font-size: 24px;">⚠️ Error Occurred</h3>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Error updating summary: {str(e)}</p>
        </div>
        """


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
