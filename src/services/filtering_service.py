"""
Filtering Service - Extracted from legacy_app.py
Handles all data filtering operations and UI visibility updates.
"""

from typing import Any, List, Tuple, Union

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

from src.common.logging_config import capture_exceptions, get_logger

# Import from our clean common modules
from src.common.mappings import resolve_station
from src.common.plotting import create_overall_status_chart, create_summary_chart

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
        df["Category"] = df.iloc[:, 0].astype(str) + "-" + df.iloc[:, 1].astype(str)
        # Drop the original index columns and rename
        df = df[["Category", "Count"]]
    else:
        # Single index case - rename columns
        df.columns = ["Category", "Count"]

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
        failed_df = df[
            (df["Overall status"] == "FAILURE")
            & (df["result_FAIL"].notna())
            & (df["result_FAIL"] != "")
        ]

        if failed_df.empty:
            return pd.DataFrame(columns=["Model", "error", "count"])

        # Group by Model and result_FAIL to get error counts
        error_counts = (
            failed_df.groupby(["Model", "result_FAIL"]).size().reset_index(name="count")
        )

        # Sort by count descending and get top_n
        top_errors = error_counts.sort_values("count", ascending=False).head(top_n)
        top_errors.columns = ["Model", "error", "count"]

        return top_errors
    except Exception as e:
        logger.error("Error analyzing top errors by model: %s", str(e))
        return pd.DataFrame(columns=["Model", "error", "count"])


def analyze_overall_status(df: pd.DataFrame) -> pd.Series:
    """
    Analyzes the overall status distribution from the DataFrame.

    Args:
        df: DataFrame containing test results

    Returns:
        Series with status counts
    """
    try:
        return df["Overall status"].value_counts()
    except Exception as e:
        logger.error("Error analyzing overall status: %s", str(e))
        return pd.Series()


def analyze_error_rates(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Analyzes the top errors based on error_code and error_message columns.

    Args:
        df: DataFrame containing test results
        top_n: Number of top errors to return

    Returns:
        DataFrame with error_code, error_message, count, and percentage columns
    """
    try:
        # Check if required columns exist
        if "error_code" not in df.columns or "error_message" not in df.columns:
            logger.warning("Missing error_code or error_message columns")
            return pd.DataFrame(
                columns=["error_code", "error_message", "count", "percentage"]
            )

        # Filter for records with error codes (non-null and non-zero)
        error_df = df[
            (df["error_code"].notna())
            & (df["error_code"] != 0)
            & (df["error_code"] != "0")
        ].copy()

        if error_df.empty:
            return pd.DataFrame(
                columns=["error_code", "error_message", "count", "percentage"]
            )

        # Group by error_code and error_message to get counts
        error_counts = (
            error_df.groupby(["error_code", "error_message"])
            .size()
            .reset_index(name="count")
        )

        # Calculate percentage of total tests
        total_tests = len(df)
        error_counts["percentage"] = (error_counts["count"] / total_tests * 100).round(
            2
        )

        # Sort by count descending and get top_n
        top_errors = error_counts.sort_values("count", ascending=False).head(top_n)

        return top_errors
    except Exception as e:
        logger.error("Error analyzing error rates: %s", str(e))
        return pd.DataFrame(
            columns=["error_code", "error_message", "count", "percentage"]
        )


@capture_exceptions(
    user_message="Failed to update filter visibility",
    return_value=(gr.update(), gr.update(), gr.update()),
)
def update_filter_visibility(
    filter_type: str,
) -> Tuple[Any, Any, Any]:
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
            gr.update(visible=False),  # station_id_filter
        )
    # Check if filtering by operator, show only relevant dropdowns
    elif filter_type == "Filter by Operator":
        return (
            gr.update(visible=True),  # operator_filter
            gr.update(visible=False),  # source_filter
            gr.update(visible=True),  # station_id_filter
        )
    else:  # Assume filtering by source if not by operator
        return (
            gr.update(visible=False),  # operator_filter
            gr.update(visible=True),  # source_filter
            gr.update(visible=True),  # station_id_filter
        )


@capture_exceptions(
    user_message="Failed to filter data. Please check your selections.",
    return_value=(None, None, None, None, None, None, None),
)
def filter_data(
    df: pd.DataFrame, filter_type: str, operator: Any, source: Any, station_id: Any
) -> Tuple[
    str, go.Figure, go.Figure, go.Figure, pd.DataFrame, pd.DataFrame, pd.DataFrame
]:
    """
    Filter a given DataFrame by Operator and/or Station ID with horizontal layout.

    Args:
        df: DataFrame to filter
        filter_type: Type of filter ("Filter by Operator", "Filter by Source", or "No Filter")
        operator: Operator selection (can be string or list)
        source: Source selection (can be string or list)
        station_id: Station ID selection (can be string or list)

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
    logger.info(
        "Filtering data: type=%s, operator=%s, source=%s, station_id=%s",
        filter_type,
        operator,
        source,
        station_id,
    )

    # Check if dataframe is empty or None
    if df is None or df.empty:
        return (
            """
            <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #06beb6 0%, #48b1bf 100%); border-radius: 15px; color: white;">
                <h2 style="margin: 0; font-size: 28px;">📊 No Data Loaded</h2>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Please upload a CSV file to begin filtering</p>
            </div>
            """,
            None,
            None,
            None,
            None,
            None,
            None,
        )

    filtered_df = df.copy()

    # Helper function to check if a filter should be applied
    def should_apply_filter(value):
        if value is None:
            return False
        if isinstance(value, list):
            return len(value) > 0 and value != ["All"] and "All" not in value
        return value != "All"

    # Apply filters based on selection
    if filter_type == "Filter by Operator" and should_apply_filter(operator):
        if isinstance(operator, list):
            filtered_df = filtered_df[filtered_df["Operator"].isin(operator)]
        else:
            filtered_df = filtered_df[filtered_df["Operator"] == operator]
    elif filter_type == "Filter by Source" and should_apply_filter(source):
        if isinstance(source, list):
            filtered_df = filtered_df[filtered_df["Source"].isin(source)]
        else:
            filtered_df = filtered_df[filtered_df["Source"] == source]

    # Apply Station ID filter if selected
    if should_apply_filter(station_id):
        if isinstance(station_id, list):
            filtered_df = filtered_df[filtered_df["Station ID"].isin(station_id)]
        else:
            filtered_df = filtered_df[filtered_df["Station ID"] == station_id]

    total_devices = filtered_df["IMEI"].nunique()
    total_tests = len(filtered_df)
    failures = filtered_df[filtered_df["Overall status"] == "FAILURE"]
    successes = filtered_df[filtered_df["Overall status"] == "SUCCESS"]

    # Format operator and station values for display
    def format_filter_value(value):
        if value is None:
            return "All"
        if isinstance(value, list):
            if not value or value == ["All"] or "All" in value:
                return "All"
            return ", ".join(str(v) for v in value[:3]) + (
                "..." if len(value) > 3 else ""
            )
        return str(value) if value != "All" else "All"

    # Calculate additional metrics for the beautiful UI
    success_rate = len(successes) / total_tests * 100 if total_tests else 0
    failure_rate = len(failures) / total_tests * 100 if total_tests else 0
    # Calculate error rate - need to find records with error_code (non-null and non-zero)
    errors = (
        filtered_df[
            (filtered_df.get("error_code", pd.Series()).notna())
            & (filtered_df.get("error_code", pd.Series()) != 0)
            & (filtered_df.get("error_code", pd.Series()) != "0")
        ]
        if "error_code" in filtered_df.columns
        else pd.DataFrame()
    )
    error_rate = len(errors) / total_tests * 100 if total_tests else 0

    # Get top failing models and test cases with their counts
    top_models_data = (
        filtered_df[filtered_df["Overall status"] == "FAILURE"]["Model"]
        .value_counts()
        .head()
    )
    top_test_cases_data = (
        filtered_df[filtered_df["Overall status"] == "FAILURE"]["result_FAIL"]
        .value_counts()
        .head()
    )

    # Get top failing stations
    top_stations_data = (
        filtered_df[filtered_df["Overall status"] == "FAILURE"]["Station ID"]
        .value_counts()
        .head()
    )

    # Calculate error rates (top 5)
    error_rates_data = analyze_error_rates(filtered_df, top_n=5)

    # Create beautiful HTML with floating cards and gradient headers
    summary = f"""
    <div style="padding: 20px;">
        <!-- Header Section -->
        <div style="background: linear-gradient(135deg, #06beb6 0%, #48b1bf 100%); padding: 25px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
            <h2 style="color: white; margin: 0 0 10px 0; font-size: 24px; text-align: center;">
                🔍 Custom Data Filtering Results
            </h2>
            <p style="color: white; margin: 0; text-align: center; opacity: 0.9; font-size: 14px;">
                Applied Filters: {format_filter_value(operator)} {('| ' + format_filter_value(station_id)) if format_filter_value(station_id) != 'All' else ''}
            </p>
        </div>

        <!-- Top Row: Key Metrics Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 25px;">

            <!-- Total Tests Card -->
            <div style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); transition: all 0.3s ease; border-top: 4px solid #3b82f6;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #666;">Total Tests Run</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold; color: #333;">{total_tests:,}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">🧪</div>
                </div>
            </div>

            <!-- Success Rate Card -->
            <div style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); transition: all 0.3s ease; border-top: 4px solid #10b981;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #666;">Success Rate</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold; color: #10b981;">{success_rate:.1f}%</h3>
                        <p style="margin: 8px 0 0 0; font-size: 13px; color: #999;">
                            {len(successes):,} passed tests
                        </p>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">✅</div>
                </div>
            </div>

            <!-- Failure Rate Card -->
            <div style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); transition: all 0.3s ease; border-top: 4px solid #ef4444;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #666;">Failure Rate</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold; color: #ef4444;">{failure_rate:.1f}%</h3>
                        <p style="margin: 8px 0 0 0; font-size: 13px; color: #999;">
                            {len(failures):,} failed tests
                        </p>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">❌</div>
                </div>
            </div>

            <!-- Error Rate Card -->
            <div style="background: white; padding: 20px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); transition: all 0.3s ease; border-top: 4px solid #f59e0b;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #666;">Error Rate</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold; color: #f59e0b;">{error_rate:.1f}%</h3>
                        <p style="margin: 8px 0 0 0; font-size: 13px; color: #999;">
                            {len(errors):,} error tests
                        </p>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">⚠️</div>
                </div>
            </div>

        </div>

        <!-- Second Row: Analysis Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 25px;">

            <!-- Top Failing Stations Card -->
            <div style="background: white; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); overflow: hidden; transition: all 0.3s ease;">
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 15px 20px;">
                    <h3 style="color: white; margin: 0; font-size: 18px; font-weight: 600;">
                        🏭 Top 5 Failing Stations
                    </h3>
                </div>
                <div style="padding: 20px;">
                    {f'''
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid #e5e7eb;">
                                <th style="text-align: left; padding: 10px 0; color: #666; font-weight: 600;">Station ID</th>
                                <th style="text-align: right; padding: 10px 0; color: #666; font-weight: 600;">Failures</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'<tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 12px 0; color: #333;"><div style="font-weight: 600; color: #333;">{station}</div><div style="font-size: 12px; color: #666; margin-top: 2px;">{resolve_station(station)}</div></td><td style="padding: 12px 0; text-align: right; font-weight: 600; color: #ef4444;">{count:,}</td></tr>' for station, count in top_stations_data.items()])}
                        </tbody>
                    </table>
                    ''' if not top_stations_data.empty else '<p style="text-align: center; color: #999; padding: 20px 0;">No failing stations found</p>'}
                </div>
            </div>

            <!-- Top Failing Models Card -->
            <div style="background: white; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); overflow: hidden; transition: all 0.3s ease;">
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 15px 20px;">
                    <h3 style="color: white; margin: 0; font-size: 18px; font-weight: 600;">
                        📊 Top 5 Failing Models
                    </h3>
                </div>
                <div style="padding: 20px;">
                    {f'''
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid #e5e7eb;">
                                <th style="text-align: left; padding: 10px 0; color: #666; font-weight: 600;">Model</th>
                                <th style="text-align: right; padding: 10px 0; color: #666; font-weight: 600;">Failures</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'<tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 12px 0; color: #333;">{model}</td><td style="padding: 12px 0; text-align: right; font-weight: 600; color: #ef4444;">{count:,}</td></tr>' for model, count in top_models_data.items()])}
                        </tbody>
                    </table>
                    ''' if not top_models_data.empty else '<p style="text-align: center; color: #999; padding: 20px 0;">No failing models found</p>'}
                </div>
            </div>

            <!-- Top Failing Test Cases Card -->
            <div style="background: white; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); overflow: hidden; transition: all 0.3s ease;">
                <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 15px 20px;">
                    <h3 style="color: white; margin: 0; font-size: 18px; font-weight: 600;">
                        🔬 Top 5 Failing Test Cases
                    </h3>
                </div>
                <div style="padding: 20px;">
                    {f'''
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid #e5e7eb;">
                                <th style="text-align: left; padding: 10px 0; color: #666; font-weight: 600;">Test Case</th>
                                <th style="text-align: right; padding: 10px 0; color: #666; font-weight: 600;">Failures</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'<tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 12px 0; color: #333; max-width: 300px; overflow: hidden; text-overflow: ellipsis;">{test}</td><td style="padding: 12px 0; text-align: right; font-weight: 600; color: #ef4444;">{count:,}</td></tr>' for test, count in top_test_cases_data.items()])}
                        </tbody>
                    </table>
                    ''' if not top_test_cases_data.empty else '<p style="text-align: center; color: #999; padding: 20px 0;">No failing test cases found</p>'}
                </div>
            </div>

        </div>

        <!-- Error Rate Card (new addition) -->
        <div style="background: white; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); overflow: hidden; transition: all 0.3s ease; margin-bottom: 25px;">
            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%); padding: 15px 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px; font-weight: 600;">
                    ⚠️ Top 5 Error Rates
                </h3>
            </div>
            <div style="padding: 20px;">
                {f'''
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid #e5e7eb;">
                            <th style="text-align: left; padding: 10px 0; color: #666; font-weight: 600;">Error Code</th>
                            <th style="text-align: left; padding: 10px 0; color: #666; font-weight: 600;">Error Message</th>
                            <th style="text-align: right; padding: 10px 0; color: #666; font-weight: 600;">Count</th>
                            <th style="text-align: right; padding: 10px 0; color: #666; font-weight: 600;">Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'<tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 12px 0; color: #333; font-weight: 600;">{row["error_code"]}</td><td style="padding: 12px 0; color: #666; max-width: 350px; overflow: hidden; text-overflow: ellipsis;" title="{row["error_message"]}">{row["error_message"]}</td><td style="padding: 12px 0; text-align: right; font-weight: 600; color: #f59e0b;">{row["count"]:,}</td><td style="padding: 12px 0; text-align: right; font-weight: 600; color: #ef4444;">{row["percentage"]:.2f}%</td></tr>' for _, row in error_rates_data.iterrows()])}
                    </tbody>
                </table>
                ''' if not error_rates_data.empty else '<p style="text-align: center; color: #999; padding: 20px 0;">No error data found</p>'}
            </div>
        </div>

        <!-- Filter Information Footer (with fixed text colors) -->
        <div style="margin-top: 25px; padding: 15px; background: rgba(107, 99, 246, 0.05); border-radius: 8px; border: 1px solid rgba(107, 99, 246, 0.2);">
            <h4 style="color: #667eea; margin: 0 0 10px 0; font-size: 16px;">🎯 Applied Filters</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <span style="color: #8b92a5; font-size: 13px;">Filter Type:</span>
                    <span style="font-weight: 600; color: #4a5568; margin-left: 8px;">{filter_type}</span>
                </div>
                <div>
                    <span style="color: #8b92a5; font-size: 13px;">Operator:</span>
                    <span style="font-weight: 600; color: #4a5568; margin-left: 8px;">{format_filter_value(operator)}</span>
                </div>
                <div>
                    <span style="color: #8b92a5; font-size: 13px;">Station ID:</span>
                    <span style="font-weight: 600; color: #4a5568; margin-left: 8px;">{format_filter_value(station_id)}</span>
                </div>
            </div>
        </div>
    </div>

    <style>
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        #custom_filter_summary > div > div {{
            animation: fadeIn 0.6s ease-out forwards;
        }}

        #custom_filter_summary > div > div:nth-child(2) > div {{
            animation: fadeIn 0.8s ease-out forwards;
        }}

        #custom_filter_summary > div > div:nth-child(2) > div:nth-child(2) {{
            animation-delay: 0.1s;
        }}

        #custom_filter_summary > div > div:nth-child(2) > div:nth-child(3) {{
            animation-delay: 0.2s;
        }}

        #custom_filter_summary > div > div:nth-child(2) > div:nth-child(4) {{
            animation-delay: 0.3s;
        }}

        #custom_filter_summary > div > div:nth-child(2) > div:nth-child(5) {{
            animation-delay: 0.4s;
        }}

        #custom_filter_summary > div > div > div:hover {{
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.12) !important;
        }}
    </style>
    """

    # Generate analysis data
    top_errors = analyze_top_errors_by_model(filtered_df)
    overall_status = analyze_overall_status(filtered_df)
    top_models = filtered_df["Model"].value_counts().head()
    top_test_cases = filtered_df["result_FAIL"].value_counts().head()

    # Create title suffix based on applied filters
    title_parts = []
    if should_apply_filter(operator):
        if isinstance(operator, list):
            title_parts.append(
                f"Operators: {', '.join(operator[:2])}{'...' if len(operator) > 2 else ''}"
            )
        else:
            title_parts.append(f"Operator: {operator}")
    if should_apply_filter(source):
        if isinstance(source, list):
            title_parts.append(
                f"Sources: {', '.join(source[:2])}{'...' if len(source) > 2 else ''}"
            )
        else:
            title_parts.append(f"Source: {source}")
    if should_apply_filter(station_id):
        if isinstance(station_id, list):
            title_parts.append(
                f"Stations: {', '.join(station_id[:2])}{'...' if len(station_id) > 2 else ''}"
            )
        else:
            title_parts.append(f"Station: {station_id}")

    title_suffix = f"({', '.join(title_parts)})" if title_parts else "(All Data)"

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

    # Format error rates data for display
    if not error_rates_data.empty:
        errors_df = error_rates_data[
            ["error_code", "error_message", "count", "percentage"]
        ].copy()
        errors_df.columns = ["Error Code", "Error Message", "Count", "Rate (%)"]
    else:
        errors_df = pd.DataFrame(
            columns=["Error Code", "Error Message", "Count", "Rate (%)"]
        )

    logger.info(
        "Filtering completed successfully. Filtered to %d rows", len(filtered_df)
    )

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
    return_value=(pd.DataFrame(), "Error applying filters"),
)
def apply_filter_and_sort(
    df: pd.DataFrame,
    sort_columns: List[str],
    operator: str,
    model: str,
    manufacturer: str,
    source: str,
    overall_status: str,
    station_id: str,
    result_fail: str,
) -> Tuple[pd.DataFrame, str]:
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
    filter_columns = [
        "Operator",
        "Model",
        "Manufacturer",
        "Source",
        "Overall status",
        "Station ID",
        "result_FAIL",
    ]
    filter_values = [
        operator,
        model,
        manufacturer,
        source,
        overall_status,
        station_id,
        result_fail,
    ]

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
    filter_columns = [
        "Operator",
        "Model",
        "Manufacturer",
        "Source",
        "Overall status",
        "Station ID",
        "result_FAIL",
    ]
    dropdowns = []

    for column in filter_columns:
        if column in df.columns:
            # Get unique values and add "All" option
            unique_values = ["All"] + get_unique_values(df, column)
            dropdown = gr.Dropdown(
                choices=unique_values, value="All", label=column, interactive=True
            )
            dropdowns.append(dropdown)

    return dropdowns
