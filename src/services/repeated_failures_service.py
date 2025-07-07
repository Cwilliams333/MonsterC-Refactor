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

        <!-- Command Generation Container - Commands will be injected here dynamically -->
        <div id="command_generation_injection_point"></div>

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
                                <span style="opacity: 0.8;">👤</span> Operator
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
        operator_escaped = html.escape(str(row["Operator"]))
        result_fail_escaped = html.escape(str(row["result_FAIL"]))

        # Escape single quotes for JavaScript
        model_js_escaped = model_escaped.replace("'", "\\'")
        station_js_escaped = station_id_escaped.replace("'", "\\'")
        result_fail_js_escaped = result_fail_escaped.replace("'", "\\'")

        html_content += f"""
                    <tr style="background: {row_bg}; transition: all 0.2s ease; cursor: pointer;"
                        onmouseover="this.style.background='linear-gradient(90deg, {severity_bg} 0%, rgba(255,255,255,0) 100%)'; this.style.transform='translateX(5px)';"
                        onmouseout="this.style.background='{row_bg}'; this.style.transform='translateX(0)';"
                        onclick="window.handleFailureRowClick('{model_js_escaped}', '{station_js_escaped}', '{result_fail_js_escaped}', {idx})">
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 21px; font-weight: 500; color: #333;">
                            {model_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #6c757d; font-family: monospace;">
                            {model_code_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #495057;">
                            {station_id_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #495057;">
                            {operator_escaped}
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

        /* Highlight selected row */
        tr.selected-row {
            background: linear-gradient(90deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
        }
    </style>

    <script>
        // Global variable to store the current selected row
        window.selectedRowIndex = null;

        // Function to handle row clicks from the HTML table
        window.handleFailureRowClick = function(model, station, testCase, rowIndex) {
            console.log('Row clicked:', model, station, testCase, rowIndex);

            // Remove previous selection highlight
            document.querySelectorAll('tr.selected-row').forEach(row => {
                row.classList.remove('selected-row');
            });

            // Add selection highlight to clicked row
            const clickedRow = document.querySelectorAll('tbody tr')[rowIndex];
            if (clickedRow) {
                clickedRow.classList.add('selected-row');
            }

            // Store selected row index and data
            window.selectedRowIndex = rowIndex;
            window.selectedRowData = { model, station, testCase };

            // Show loading state in injection point
            const injectionPoint = document.getElementById('command_generation_injection_point');
            if (injectionPoint) {
                injectionPoint.innerHTML = '<div style="text-align: center; padding: 20px;"><div style="display: inline-block; width: 40px; height: 40px; border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite;"></div><p style="margin-top: 10px; color: #667eea;">Generating commands...</p></div>';
            }

            // Call the external handler if it exists
            if (window.onFailureRowClick) {
                window.onFailureRowClick(model, station, testCase);
            }
        };

        // Function to inject command UI into the proper location
        window.injectCommandUI = function(commandHtml) {
            const injectionPoint = document.getElementById('command_generation_injection_point');
            if (injectionPoint) {
                injectionPoint.innerHTML = commandHtml;
                // Scroll to the command UI smoothly
                injectionPoint.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        };
    </script>
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
        hover_data=["result_FAIL", "Operator", "IMEI Count"],
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
) -> Tuple[str, Any, Any, Any, pd.DataFrame]:
    """
    Analyzes repeated failures in test data and returns summary, chart, and interactive components.

    Args:
        df: Input DataFrame with test data
        min_failures: Minimum number of failures to be considered "repeated"

    Returns:
        Tuple of (summary_text, figure, interactive_dataframe, dropdown, original_dataframe)
    """
    try:
        # If df is a file object, load it first
        if hasattr(df, "name"):
            from src.common.io import load_data

            df = load_data(df)

        # Filter for FAILURE in Overall status
        failure_df = df[df["Overall status"] == "FAILURE"]
        logger.info(f"Found {len(failure_df)} failures")

        # Create initial aggregation with both counts and operator info
        agg_df = (
            failure_df.groupby(["Model", "Station ID", "result_FAIL", "Operator"])
            .agg({"IMEI": ["count", "nunique"]})
            .reset_index()
        )

        # Rename columns
        agg_df.columns = [
            "Model",
            "Station ID",
            "result_FAIL",
            "Operator",
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
            hover_data=["result_FAIL", "Operator", "IMEI Count"],
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
            gr.Dropdown(
                choices=dropdown_choices,
                value=dropdown_choices[2:],
                label="Filter by Test Case",
                multiselect=True,
            ),
            df,  # Return the original dataframe for command generation
            repeated_failures,  # Return the repeated failures dataframe for filtering
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
        return error_message, None, None, None, None


@capture_exceptions(user_message="Failed to update summary chart and data")
def update_summary_chart_and_data(
    repeated_failures_df: pd.DataFrame, sort_by: str, selected_test_cases: List[str]
) -> Tuple[str, go.Figure]:
    """
    Updates the summary chart based on sorting and filtering preferences.

    Args:
        repeated_failures_df: Input dataframe with repeated failures data
        sort_by: Column name to sort by; one of "TC Count", "Model", "Station ID", "Test Case", or "Model Code"
        selected_test_cases: List of selected test cases to filter by

    Returns:
        Tuple of (summary_text, plotly_figure)
    """

    # Check for no data
    if repeated_failures_df is None or len(repeated_failures_df) == 0:
        return "No data available to sort/filter", None

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
        "Operator": "Operator",
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

    # Return the updated summary text and plotly figure
    return create_summary(df), create_plot(df)


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
            "Operator": "Operator",
            "Test Case": "result_FAIL",
            "Model Code": "Model Code",
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


@capture_exceptions(user_message="Failed to generate IMEI commands")
def generate_imei_commands(
    full_df: pd.DataFrame, model: str, station_id: str, test_case: str
) -> str:
    """
    Generate db-export commands for failed IMEIs based on the selected row.

    Args:
        full_df: The original full dataframe with all test data
        model: The model from the clicked row
        station_id: The station ID from the clicked row
        test_case: The test case (result_FAIL) from the clicked row

    Returns:
        HTML string containing the command generation UI with proper db-export commands
    """
    logger.info("=" * 60)
    logger.info("generate_imei_commands called!")
    logger.info(f"Model: {model}")
    logger.info(f"Station ID: {station_id}")
    logger.info(f"Test Case: {test_case}")
    logger.info(f"Full DF shape: {full_df.shape if full_df is not None else 'None'}")
    logger.info("=" * 60)

    try:
        if full_df is None or full_df.empty:
            logger.warning("No data available in full_df")
            return (
                '<div style="color: red;">No data available to generate commands.</div>'
            )

        # Filter the dataframe for matching failures
        filtered_df = full_df[
            (full_df["Model"] == model)
            & (full_df["Station ID"] == station_id)
            & (full_df["result_FAIL"] == test_case)
            & (full_df["Overall status"] == "FAILURE")
        ]

        logger.info(f"Filtered dataframe shape: {filtered_df.shape}")

        if filtered_df.empty:
            logger.warning("No matching failures found")
            return '<div style="color: red;">No matching failures found for the selected criteria.</div>'

        # Check if IMEI column exists
        if "IMEI" not in filtered_df.columns:
            logger.error("IMEI column not found in dataframe")
            logger.info(f"Available columns: {filtered_df.columns.tolist()}")
            return '<div style="color: red;">IMEI column not found in the data. Please ensure your CSV has an IMEI column.</div>'

        # Get unique IMEIs
        imeis = filtered_df["IMEI"].dropna().unique().tolist()
        logger.info(f"Found {len(imeis)} unique IMEIs")

        # Convert IMEIs to strings (handle float IMEIs)
        imeis = [
            str(int(float(imei))) if isinstance(imei, (int, float)) else str(imei)
            for imei in imeis
        ]
        imei_count = len(imeis)
        logger.info(f"Converted IMEIs: {imeis[:5]}...")  # Log first 5

        # Handle case with no IMEIs
        if not imeis:
            logger.warning("No valid IMEIs found after conversion")
            return '<div style="color: red;">No valid IMEIs found for the selected criteria.</div>'

        # Generate the db-export commands
        imei_args = " ".join([f"--dut {imei}" for imei in imeis])

        # Create the three commands
        messages_cmd = f"db-export messages {imei_args}"
        gauge_cmd = f'db-export gauge --test "{test_case}" {imei_args}'
        raw_data_cmd = f'db-export raw_data --test "{test_case}" {imei_args}'

        # Escape for JavaScript - need to escape backticks and quotes
        messages_cmd_js = (
            messages_cmd.replace("\\", "\\\\").replace("`", "\\`").replace('"', '\\"')
        )
        gauge_cmd_js = (
            gauge_cmd.replace("\\", "\\\\").replace("`", "\\`").replace('"', '\\"')
        )
        raw_data_cmd_js = (
            raw_data_cmd.replace("\\", "\\\\").replace("`", "\\`").replace('"', '\\"')
        )

        # Create the HTML response with sleek markdown-style design
        html_content = f"""
        <div id="command-ui" style="margin: 15px 0; animation: slideDown 0.4s ease-out;">
            <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 10px; padding: 20px;">
                <div style="margin-bottom: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #495057; font-size: 18px; font-weight: 600;">
                        🔧 IMEI Extractor Commands
                    </h4>
                    <p style="margin: 0; color: #6c757d; font-size: 14px;">
                        <strong>Selected:</strong> {html.escape(model)} | {html.escape(station_id)} | {html.escape(test_case)}<br>
                        <strong>Found:</strong> {imei_count} failed IMEIs
                    </p>
                </div>

                <!-- Messages Command -->
                <div style="margin-bottom: 12px;">
                    <p style="margin: 0 0 6px 0; color: #495057; font-size: 14px; font-weight: 500;">📨 Messages Command:</p>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <code style="flex: 1; background: #2d3748; color: #e2e8f0; padding: 12px 16px; border-radius: 6px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; overflow-x: auto; white-space: nowrap; display: block;">
                            {html.escape(messages_cmd)}
                        </code>
                        <button onclick='navigator.clipboard.writeText(`{messages_cmd_js}`).then(() => {{ this.innerHTML = "✓"; setTimeout(() => this.innerHTML = "📋", 2000); }})'
                                style="background: #667eea; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0;"
                                onmouseover="this.style.background='#5a67d8'" onmouseout="this.style.background='#667eea'">
                            📋
                        </button>
                    </div>
                </div>

                <!-- Gauge Command -->
                <div style="margin-bottom: 12px;">
                    <p style="margin: 0 0 6px 0; color: #495057; font-size: 14px; font-weight: 500;">📊 Gauge Command:</p>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <code style="flex: 1; background: #2d3748; color: #e2e8f0; padding: 12px 16px; border-radius: 6px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; overflow-x: auto; white-space: nowrap; display: block;">
                            {html.escape(gauge_cmd)}
                        </code>
                        <button onclick='navigator.clipboard.writeText(`{gauge_cmd_js}`).then(() => {{ this.innerHTML = "✓"; setTimeout(() => this.innerHTML = "📋", 2000); }})'
                                style="background: #667eea; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0;"
                                onmouseover="this.style.background='#5a67d8'" onmouseout="this.style.background='#667eea'">
                            📋
                        </button>
                    </div>
                </div>

                <!-- Raw Data Command -->
                <div>
                    <p style="margin: 0 0 6px 0; color: #495057; font-size: 14px; font-weight: 500;">💾 Raw Data Command:</p>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <code style="flex: 1; background: #2d3748; color: #e2e8f0; padding: 12px 16px; border-radius: 6px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; overflow-x: auto; white-space: nowrap; display: block;">
                            {html.escape(raw_data_cmd)}
                        </code>
                        <button onclick='navigator.clipboard.writeText(`{raw_data_cmd_js}`).then(() => {{ this.innerHTML = "✓"; setTimeout(() => this.innerHTML = "📋", 2000); }})'
                                style="background: #667eea; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0;"
                                onmouseover="this.style.background='#5a67d8'" onmouseout="this.style.background='#667eea'">
                            📋
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <style>
            @keyframes slideDown {{
                from {{ opacity: 0; transform: translateY(-10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
        </style>
        """

        return html_content

    except Exception as e:
        logger.error(f"Error generating IMEI commands: {str(e)}")
        return f'<div style="color: red;">Error generating commands: {html.escape(str(e))}</div>'
