"""
Gradio UI Layer for MonsterC CSV Analysis Tool.

This module implements the Strangler Fig pattern - creating a new UI shell that maintains
100% compatibility with the original while gradually introducing the new modular architecture.
"""

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime

import gradio as gr
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Import from common modules (new architecture)
from common.io import load_data
from common.logging_config import capture_exceptions, get_logger

# Import data mappings from common module
from common.mappings import (
    DEVICE_MAP as device_map,
    STATION_TO_MACHINE as station_to_machine,
    TEST_TO_RESULT_FAIL_MAP as test_to_result_fail_map,
)

# Import from services (new architecture)
from services.analysis_service import perform_analysis
from services.filtering_service import (
    apply_filter_and_sort,
    filter_data,
    get_unique_values,
    update_filter_dropdowns,
    update_filter_visibility,
)
from services.imei_extractor_service import process_data
from services.pivot_service import (
    analyze_top_models,
    analyze_top_test_cases,
    apply_failure_highlighting,
    apply_filters,
    create_excel_style_failure_pivot,
    create_excel_style_error_pivot,
    create_pivot_table,
    find_top_failing_stations,
    generate_pivot_table_filtered,
)
from services.repeated_failures_service import (
    analyze_repeated_failures,
    handle_test_case_selection,
    update_summary_chart_and_data,
)
from services.wifi_error_service import analyze_wifi_errors

# Configure logging
logger = get_logger(__name__)


# Gradio UI Definition
with gr.Blocks(
    theme=gr.themes.Soft(),
    css="""
    /* Base styles for markdown content */
    .markdown-body {
        padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        max-width: 1200px;  /* Limit maximum width */
        margin: 0 auto;     /* Center the container */
    }

    /* Header styling */
    .markdown-body h2 {
        margin-top: 0;
        color: rgb(107, 99, 246);
        font-size: 1.25rem;
        font-weight: 600;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(107, 99, 246, 0.2);
    }

    /* Table styling */
    .markdown-body table,
    .custom-markdown table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        background: rgba(255, 255, 255, 0.05);
    }

    /* Table column width controls */
    .markdown-body table th:nth-child(1) { width: 15%; }  /* Model column */
    .markdown-body table th:nth-child(2) { width: 15%; }  /* Model Code column */
    .markdown-body table th:nth-child(3) { width: 15%; }  /* Station ID column */
    .markdown-body table th:nth-child(4) { width: 40%; }  /* Test Case column */
    .markdown-body table th:nth-child(5) { width: 15%; }  /* Count column */

    .markdown-body th {
        background: rgba(107, 99, 246, 0.1);
        color: rgb(107, 99, 246);
        font-weight: 600;
        text-align: left;
    }

    .markdown-body td,
    .markdown-body th {
        padding: 0.5rem 0.75rem;
        border: 1px solid rgba(107, 99, 246, 0.2);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 0;
    }

    /* Allow test case column to wrap if needed */
    .markdown-body td:nth-child(4) {
        white-space: normal;
        line-height: 1.2;
    }

    .markdown-body tr:nth-child(even) {
        background: rgba(107, 99, 246, 0.03);
    }

    /* Table container for scrolling */
    .markdown-body .table-container {
        overflow-x: auto;
        margin: 1rem 0;
    }

    /* Command section styling */
    .command-section {
        margin-bottom: 1.5rem;
        padding: 1rem;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.05);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Code styling */
    .custom-textbox,
    .command-box {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        line-height: 1.5;
        white-space: pre-wrap;
        background: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(107, 99, 246, 0.2) !important;
        border-radius: 4px;
        padding: 1rem;
        margin-bottom: 0.75rem !important;
        color: rgba(255, 255, 255, 0.9) !important;
    }

    /* Button styling */
    .primary-button {
        background: linear-gradient(135deg, rgb(107, 99, 246), rgb(99, 102, 241)) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }

    .primary-button:hover {
        background: linear-gradient(135deg, rgb(99, 102, 241), rgb(107, 99, 246)) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(107, 99, 246, 0.3) !important;
    }

    /* Input styling */
    .custom-dropdown,
    .custom-slider {
        border: 1px solid rgba(107, 99, 246, 0.3) !important;
        border-radius: 6px !important;
    }

    /* Container spacing */
    .container-spacing {
        margin: 1rem 0;
    }

    /* Spacing utilities */
    .markdown-body > *:first-child { margin-top: 0; }
    .markdown-body > *:last-child { margin-bottom: 0; }

    /* Responsive adjustments */
    @media (max-width: 768px) {
        .markdown-body {
            padding: 0.5rem;
        }

        .markdown-body td,
        .markdown-body th {
            padding: 0.4rem 0.5rem;
            font-size: 0.9rem;
        }
    }
""",
) as demo:
    gr.Markdown("# CSV Analysis Tool")

    with gr.Row():
        file_input = gr.File(label="Upload CSV File")

    df = gr.State()  # State to hold the DataFrame

    with gr.Tabs():
        with gr.TabItem("Analysis Results"):
            with gr.Row():
                analyze_button = gr.Button("Perform Analysis")
            with gr.Row():
                analysis_summary = gr.Textbox(label="Summary", lines=6)
            with gr.Row():
                overall_status_chart = gr.Plot(label="Overall Status Distribution")
                stations_chart = gr.Plot(label="Top Failing Stations")
                models_chart = gr.Plot(label="Top Failing Models")
                test_cases_chart = gr.Plot(label="Top Failing Test Cases")
            with gr.Row():
                stations_df = gr.Dataframe(
                    headers=["Station ID", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Stations",
                    interactive=False,
                )
                models_df = gr.Dataframe(
                    headers=["Model", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Models",
                    interactive=False,
                )
                test_cases_df = gr.Dataframe(
                    headers=["Test Case", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Test Cases",
                    interactive=False,
                )

        with gr.TabItem("Custom Data Filtering"):
            with gr.Row():
                filter_type = gr.Radio(
                    choices=["No Filter", "Filter by Operator", "Filter by Source"],
                    value="No Filter",
                    label="Select Filter Type",
                    interactive=True,
                )

            with gr.Row():
                operator_filter = gr.Dropdown(
                    label="Operator",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )
                source_filter = gr.Dropdown(
                    label="Source",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )
                station_id_filter = gr.Dropdown(
                    label="Station ID",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )

            with gr.Row():
                custom_filter_button = gr.Button("Filter Data")

            # Rest of the components remain the same
            with gr.Row():
                custom_filter_summary = gr.Markdown(
                    label="Filtered Summary", value="", elem_classes=["custom-markdown"]
                )
            with gr.Row():
                with gr.Column(scale=1):
                    custom_filter_chart1 = gr.Plot(label="Top 5 Failing Models")
                with gr.Column(scale=1):
                    custom_filter_chart2 = gr.Plot(label="Top 5 Failing Test Cases")
                with gr.Column(scale=1):
                    custom_filter_chart3 = gr.Plot(label="Overall Status")
            with gr.Row():
                with gr.Column(scale=1):
                    custom_filter_df1 = gr.Dataframe(label="Top 5 Failing Models")
                with gr.Column(scale=1):
                    custom_filter_df2 = gr.Dataframe(label="Top 5 Failing Test Cases")
                with gr.Column(scale=1):
                    custom_filter_df3 = gr.Dataframe(label="Top 5 Errors")

        with gr.TabItem("Pivot Table Builder"):
            with gr.Row():
                # Adding filter dropdowns for filtering before creating the pivot table with multiselect enabled
                filter_operator = gr.Dropdown(
                    label="Filter by Operator",
                    choices=["All"],
                    value="All",
                    multiselect=True,
                    interactive=True,
                )
                filter_station_id = gr.Dropdown(
                    label="Filter by Station ID",
                    choices=["All"],
                    value="All",
                    multiselect=True,
                    interactive=True,
                )
                filter_model = gr.Dropdown(
                    label="Filter by Model",
                    choices=["All"],
                    value="All",
                    multiselect=True,
                    interactive=True,
                )

            # Adding pivot table options after the filters
            with gr.Row():
                # Pivot table configuration
                pivot_rows = gr.Dropdown(
                    label="Select Row Fields (required)",
                    choices=[],
                    multiselect=True,
                    interactive=True,
                )
                pivot_columns = gr.Dropdown(
                    label="Select Column Fields (optional)",
                    choices=[],
                    multiselect=True,
                    interactive=True,
                )
                pivot_values = gr.Dropdown(
                    label="Select Values Field (required)", choices=[], interactive=True
                )
                pivot_aggfunc = gr.Dropdown(
                    label="Aggregation Function",
                    choices=["count", "sum", "mean", "median", "max", "min"],
                    value="count",
                    interactive=True,
                )

            with gr.Row():
                generate_pivot_button = gr.Button("Generate Pivot Table")
                catch_failures_button = gr.Button(
                    "🚨 Catch High Failures", variant="primary"
                )

            with gr.Row():
                pivot_table_output = gr.Dataframe(
                    label="Pivot Table Results", interactive=False
                )

        with gr.TabItem("Repeated Failures Analysis"):
            with gr.Row():
                min_failures = gr.Slider(
                    minimum=2, maximum=10, value=4, step=1, label="Minimum Failures"
                )
                analyze_failures_button = gr.Button("Analyze Repeated Failures")

            # Add sorting controls
            with gr.Row():
                sort_by = gr.Dropdown(
                    choices=["TC Count", "Model", "Station ID", "Test Case"],
                    value="TC Count",
                    label="Sort Results By",
                )
                test_case_filter = gr.Dropdown(
                    choices=["Select All", "Clear All"],
                    value=[],
                    label="Filter by Test Case",
                    multiselect=True,
                )

            with gr.Row():
                failures_summary = gr.Markdown(
                    value="", label="Repeated Failures Summary"
                )
            with gr.Row():
                failures_chart = gr.Plot(label="Repeated Failures Chart")
            with gr.Row():
                failures_df = gr.Dataframe(label="Repeated Failures Data")

        with gr.TabItem("WiFi Error Analysis"):
            with gr.Row():
                error_threshold = gr.Slider(
                    minimum=0, maximum=100, value=9, step=1, label="Error Threshold (%)"
                )

            analyze_wifi_button = gr.Button("Analyze WiFi Errors")

            with gr.Row():
                summary_table = gr.Dataframe(label="Summary Table")

            with gr.Accordion("Detailed Analysis for High Error Rates", open=False):
                with gr.Row():
                    error_heatmap = gr.Plot(label="Detailed WiFi Error Heatmap")

                with gr.Row():
                    hourly_trend_plot = gr.Plot(
                        label="Hourly Error Trends for High-Error Operators"
                    )

                with gr.Row():
                    pivot_table = gr.Dataframe(
                        label="Hourly Error Breakdown by Operator and Error Type"
                    )

        with gr.TabItem("🚨 Interactive Pivot Analysis"):
            gr.Markdown(
                """
            ## Excel-Style Hierarchical Pivot Analysis

            This feature provides **two main analysis workflows** that replicate Excel pivot functionality:

            ### 🚨 Catch High Failures
            - **Hierarchy:** Test Case → Model (2-level)
            - **Purpose:** Identify systemic failure patterns
            - **Data:** result_FAIL field analysis

            ### 🔍 Generate High Error Rates  
            - **Hierarchy:** Model → Error Code → Error Message (3-level)
            - **Purpose:** Deep-dive error code analysis
            - **Data:** error_code and error_message field analysis

            ### ✨ Both Include:
            - 📋 **Expandable groups** with visual hierarchy (📁 📂 └─)
            - 🎨 **Smart color coding** (RED for highest per group, YELLOW for highest per item)
            - 🔍 **Interactive exploration** with collapsible groups
            - ⚡ **High performance** with large datasets

            **How to use:** Choose your analysis type and click the corresponding button below.
            """
            )

            with gr.Row():
                interactive_operator_filter = gr.Dropdown(
                    label="Filter by Operator (Optional)",
                    choices=["All"],
                    value="All",
                    interactive=True,
                )

            with gr.Row():
                with gr.Column(scale=1):
                    generate_interactive_pivot_button = gr.Button(
                        "🚨 Catch High Failures",
                        variant="primary",
                        size="lg",
                    )
                with gr.Column(scale=1):
                    generate_error_analysis_button = gr.Button(
                        "🔍 Generate High Error Rates",
                        variant="secondary",
                        size="lg",
                    )

            with gr.Row():
                interactive_pivot_status = gr.Markdown(
                    value="📝 **Status:** Ready to generate interactive pivot table",
                    elem_classes=["markdown-body"],
                )

            with gr.Row():
                interactive_pivot_iframe = gr.HTML(
                    value="", label="Interactive Pivot Table"
                )

        with gr.TabItem("Advanced Filtering"):
            with gr.Row():
                advanced_operator_filter = gr.Dropdown(
                    label="Operator", choices=["All"], multiselect=True, value="All"
                )
                advanced_model_filter = gr.Dropdown(
                    label="Model", choices=["All"], multiselect=True, value="All"
                )
                advanced_manufacturer_filter = gr.Dropdown(
                    label="Manufacturer", choices=["All"], multiselect=True, value="All"
                )
                advanced_source_filter = gr.Dropdown(
                    label="Source", choices=["All"], multiselect=True, value="All"
                )
            with gr.Row():
                advanced_overall_status_filter = gr.Dropdown(
                    label="Overall status",
                    choices=["All"],
                    multiselect=True,
                    value="All",
                )
                advanced_station_id_filter = gr.Dropdown(
                    label="Station ID", choices=["All"], multiselect=True, value="All"
                )
                advanced_result_fail_filter = gr.Dropdown(
                    label="result_FAIL", choices=["All"], multiselect=True, value="All"
                )
            with gr.Row():
                sort_columns = gr.Dropdown(
                    choices=[
                        "Date Time",
                        "Operator",
                        "Model",
                        "IMEI",
                        "Manufacturer",
                        "Source",
                        "Overall status",
                        "Station ID",
                        "result_FAIL",
                        "error_code",
                        "error_message",
                    ],
                    label="Select columns to sort",
                    multiselect=True,
                )
            with gr.Row():
                apply_filter_button = gr.Button("Apply Filter and Sort")
            with gr.Row():
                filtered_data = gr.Dataframe(label="Filtered Data")
            with gr.Row():
                filter_summary = gr.Textbox(label="Filter Summary", lines=3)

        with gr.TabItem("IMEI Extractor"):
            with gr.Row():
                source = gr.Dropdown(
                    label="Source", choices=["All"], value="All", interactive=True
                )
                station_id = gr.Dropdown(
                    label="Station ID", choices=["All"], value="All", interactive=True
                )
                model_input = gr.Dropdown(
                    label="Model(s)",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    multiselect=True,
                )
                result_fail = gr.Dropdown(
                    label="Result Fail", choices=["All"], value="All", interactive=True
                )
                flexible_search = gr.Checkbox(
                    label="Enable Flexible Search", value=False
                )

            with gr.Row():
                process_button = gr.Button("Process Data", variant="primary")

            with gr.Column():
                # Group commands first
                with gr.Column(elem_classes=["command-section"]):
                    messages_output = gr.Code(
                        label="Messages Command",
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"],
                    )
                    raw_data_output = gr.Code(
                        label="Raw Data Command",
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"],
                    )
                    gauge_output = gr.Code(
                        label="Gauge Command",
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"],
                    )

                # Then show summary
                summary_output = gr.Markdown(
                    label="Query Results",
                    elem_classes=["markdown-body", "custom-markdown"],
                )

    # Event Handlers - Using decorated functions for error handling

    @capture_exceptions(
        user_message="Failed to load and update data", return_value=[None] * 22
    )
    def load_and_update_wrapped(file):
        """Load CSV file and update all filter dropdowns."""
        logger.info(f"Loading file: {getattr(file, 'name', 'unknown')}")

        # Load the data
        df = load_data(file)

        if df is None or df.empty:
            # Return empty values for all outputs - need to return proper dropdown updates
            empty_dropdown = gr.Dropdown(choices=["All"], value="All")
            return [
                None,  # df
                empty_dropdown,  # source
                empty_dropdown,  # station_id
                empty_dropdown,  # model
                gr.Dropdown(choices=[]),  # result_fail
                empty_dropdown,  # advanced_operator
                empty_dropdown,  # advanced_model
                empty_dropdown,  # advanced_manufacturer
                empty_dropdown,  # advanced_source
                empty_dropdown,  # advanced_overall_status
                empty_dropdown,  # advanced_station_id
                gr.Dropdown(choices=[]),  # advanced_result_fail
                gr.Dropdown(choices=[]),  # pivot_rows
                gr.Dropdown(choices=[]),  # pivot_columns
                gr.Dropdown(choices=[]),  # pivot_values
                empty_dropdown,  # filter_operator
                empty_dropdown,  # filter_station_id
                empty_dropdown,  # filter_model
                empty_dropdown,  # operator_filter
                empty_dropdown,  # source_filter
                empty_dropdown,  # station_id_filter
                empty_dropdown,  # interactive_operator_filter
            ]

        # Log columns for debugging
        logger.info(f"Available columns: {df.columns.tolist()}")

        # Get unique values for dropdowns using the correct column names from the CSV
        operators = (
            ["All"] + sorted(df["Operator"].dropna().unique().tolist())
            if "Operator" in df.columns
            else ["All"]
        )
        models = (
            ["All"] + sorted(df["Model"].dropna().unique().tolist())
            if "Model" in df.columns
            else ["All"]
        )
        sources = (
            ["All"] + sorted(df["Source"].dropna().unique().tolist())
            if "Source" in df.columns
            else ["All"]
        )
        station_ids = (
            ["All"] + sorted(df["Station ID"].dropna().unique().tolist())
            if "Station ID" in df.columns
            else ["All"]
        )
        result_fails = (
            sorted(df["result_FAIL"].dropna().unique().tolist())
            if "result_FAIL" in df.columns
            else []
        )
        manufacturers = (
            ["All"] + sorted(df["Manufacturer"].dropna().unique().tolist())
            if "Manufacturer" in df.columns
            else ["All"]
        )
        overall_statuses = (
            ["All"] + sorted(df["Overall status"].dropna().unique().tolist())
            if "Overall status" in df.columns
            else ["All"]
        )

        # Get column names for pivot table
        columns = df.columns.tolist()

        # Return all the updated values (22 total)
        # For dropdowns, we need to return gr.Dropdown.update(choices=...) to update the choices
        return [
            df,  # 1. The loaded dataframe
            gr.Dropdown(choices=sources, value="All"),  # 2. IMEI Extractor: Source
            gr.Dropdown(
                choices=station_ids, value="All"
            ),  # 3. IMEI Extractor: Station ID
            gr.Dropdown(choices=models, value="All"),  # 4. IMEI Extractor: Model(s)
            gr.Dropdown(choices=result_fails),  # 5. IMEI Extractor: Result Fail
            gr.Dropdown(choices=operators, value="All"),  # 6. Advanced Filter: Operator
            gr.Dropdown(choices=models, value="All"),  # 7. Advanced Filter: Model
            gr.Dropdown(
                choices=manufacturers, value="All"
            ),  # 8. Advanced Filter: Manufacturer
            gr.Dropdown(choices=sources, value="All"),  # 9. Advanced Filter: Source
            gr.Dropdown(
                choices=overall_statuses, value="All"
            ),  # 10. Advanced Filter: Overall Status
            gr.Dropdown(
                choices=station_ids, value="All"
            ),  # 11. Advanced Filter: Station ID
            gr.Dropdown(choices=result_fails),  # 12. Advanced Filter: Result Fail
            gr.Dropdown(choices=columns),  # 13. Pivot Table: Rows
            gr.Dropdown(choices=columns),  # 14. Pivot Table: Columns
            gr.Dropdown(choices=columns),  # 15. Pivot Table: Values
            gr.Dropdown(choices=operators, value="All"),  # 16. Pivot Filter: Operator
            gr.Dropdown(
                choices=station_ids, value="All"
            ),  # 17. Pivot Filter: Station ID
            gr.Dropdown(choices=models, value="All"),  # 18. Pivot Filter: Model
            gr.Dropdown(choices=operators, value="All"),  # 19. Custom Filter: Operator
            gr.Dropdown(choices=sources, value="All"),  # 20. Custom Filter: Source
            gr.Dropdown(
                choices=station_ids, value="All"
            ),  # 21. Custom Filter: Station ID
            gr.Dropdown(
                choices=operators, value="All"
            ),  # 22. Interactive Pivot: Operator
        ]

    @capture_exceptions(user_message="Analysis failed", return_value=None)
    def perform_analysis_wrapped(csv_file):
        """Wrapper for perform_analysis with error handling."""
        logger.info("Performing CSV analysis")
        # Convert file to DataFrame before passing to service
        df = load_data(csv_file)
        return perform_analysis(df)

    @capture_exceptions(user_message="Filter update failed", return_value=None)
    def update_filter_visibility_wrapped(filter_type):
        """Wrapper for update_filter_visibility with error handling."""
        logger.info(f"Updating filter visibility: {filter_type}")
        return update_filter_visibility(filter_type)

    @capture_exceptions(user_message="Data filtering failed", return_value=None)
    def filter_data_wrapped(df, filter_type, operator, source, station_id):
        """Wrapper for filter_data with error handling."""
        logger.info(f"Filtering data: {filter_type}")
        return filter_data(df, filter_type, operator, source, station_id)

    @capture_exceptions(user_message="WiFi analysis failed", return_value=None)
    def analyze_wifi_errors_wrapped(file, error_threshold):
        """Wrapper for analyze_wifi_errors with error handling."""
        logger.info(f"Analyzing WiFi errors with threshold: {error_threshold}")
        return analyze_wifi_errors(file, error_threshold)

    @capture_exceptions(
        user_message="Repeated failures analysis failed", return_value=None
    )
    def analyze_repeated_failures_wrapped(file, min_failures):
        """Wrapper for analyze_repeated_failures with error handling."""
        logger.info(f"Analyzing repeated failures with minimum: {min_failures}")
        return analyze_repeated_failures(file, min_failures)

    @capture_exceptions(user_message="Summary update failed", return_value=None)
    def update_summary_chart_and_data_wrapped(
        repeated_failures_df, sort_by, selected_test_cases
    ):
        """Wrapper for update_summary_chart_and_data with error handling."""
        logger.info(f"Updating summary: sort_by={sort_by}")
        return update_summary_chart_and_data(
            repeated_failures_df, sort_by, selected_test_cases
        )

    # Note: We don't wrap this function with @capture_exceptions because Gradio
    # automatically passes gr.SelectData as the first argument for .select() events
    def handle_test_case_selection_wrapped(evt: gr.SelectData, selected_test_cases):
        """Wrapper for handle_test_case_selection."""
        logger.info("Handling test case selection")
        try:
            return handle_test_case_selection(evt, selected_test_cases)
        except Exception as e:
            logger.error(f"Test case selection failed: {e}")
            return selected_test_cases  # Return current state on error

    @capture_exceptions(user_message="Advanced filtering failed", return_value=None)
    def apply_filter_and_sort_wrapped(
        df,
        sort_columns,
        operator,
        model,
        manufacturer,
        source,
        overall_status,
        station_id,
        result_fail,
    ):
        """Wrapper for apply_filter_and_sort with error handling."""
        logger.info("Applying advanced filters and sorting")
        return apply_filter_and_sort(
            df,
            sort_columns,
            operator,
            model,
            manufacturer,
            source,
            overall_status,
            station_id,
            result_fail,
        )

    @capture_exceptions(user_message="Pivot table generation failed", return_value=None)
    def generate_pivot_table_filtered_wrapped(
        df, rows, columns, values, aggfunc, operator, station_id, model
    ):
        """Wrapper for generate_pivot_table_filtered with error handling."""
        logger.info("Generating filtered pivot table")
        return generate_pivot_table_filtered(
            df, rows, columns, values, aggfunc, operator, station_id, model
        )

    @capture_exceptions(user_message="High failures analysis failed", return_value=None)
    def catch_high_failures_wrapped(df, operator_filter):
        """Wrapper for Excel-style failure pivot with highlighting."""
        logger.info("Generating Excel-style failure pivot with highlighting")

        # Check if dataframe is loaded
        if df is None or df.empty:
            logger.warning("No data loaded. Please upload a CSV file first.")
            return pd.DataFrame({"Message": ["Please upload a CSV file first"]})

        logger.info(
            f"Input DataFrame shape: {df.shape}, Operator filter: {operator_filter}"
        )

        # Create the Excel-style pivot
        pivot_result = create_excel_style_failure_pivot(df, operator_filter)

        # Apply conditional formatting for high failure highlighting
        if not pivot_result.empty and "Error" not in pivot_result.columns:
            styled_result = apply_failure_highlighting(pivot_result)
            return styled_result

        return pivot_result

    # Global variable to hold the Dash subprocess
    dash_process = None

    @capture_exceptions(
        user_message="Interactive pivot generation failed",
        return_value=("❌ **Error:** Failed to generate interactive pivot table", ""),
    )
    def generate_interactive_pivot_wrapped(df, operator_filter):
        """Generate interactive Excel-style pivot table using Dash AG Grid."""
        global dash_process

        logger.info("Generating interactive Excel-style pivot table")

        # Check if dataframe is loaded
        if df is None or df.empty:
            logger.warning("No data loaded for interactive pivot")
            return "⚠️ **Error:** No data loaded. Please upload a CSV file first.", ""

        try:
            # Stop any previously running Dash app
            if dash_process and dash_process.poll() is None:
                logger.info("Stopping previous Dash process")
                dash_process.terminate()
                time.sleep(1)  # Give it time to stop

            # Create the Excel-style pivot data
            pivot_result = create_excel_style_failure_pivot(df, operator_filter)

            if pivot_result.empty:
                logger.warning("Generated pivot table is empty")
                return (
                    "⚠️ **Warning:** No failure data found with the current filter settings.",
                    "",
                )

            logger.info(f"Generated pivot data with shape: {pivot_result.shape}")

            # Save the pivot data to a temporary file
            temp_dir = tempfile.gettempdir()
            data_file = os.path.join(temp_dir, "monsterc_pivot_data.json")

            # Convert to JSON format for Dash app
            pivot_json = pivot_result.to_dict("records")
            with open(data_file, "w") as f:
                json.dump(pivot_json, f)

            logger.info(f"Saved pivot data to: {data_file}")

            # Launch the Dash app with the data file
            dash_script = os.path.join(
                os.path.dirname(__file__), "..", "dash_pivot_app.py"
            )
            dash_process = subprocess.Popen(
                ["python", dash_script, data_file], cwd=os.path.dirname(dash_script)
            )

            # Give the server time to start
            time.sleep(3)

            # Check if the process started successfully
            if dash_process.poll() is not None:
                logger.error("Dash process failed to start")
                return "❌ **Error:** Failed to start interactive pivot server.", ""

            # Create the iframe HTML
            iframe_html = f"""
            <div style="width: 100%; height: 800px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <iframe
                    src="http://127.0.0.1:8051"
                    width="100%"
                    height="800px"
                    frameborder="0"
                    style="border: none;">
                </iframe>
            </div>
            <p style="text-align: center; margin-top: 10px; color: #666; font-size: 14px;">
                💡 If the pivot table doesn't load, <a href="http://127.0.0.1:8051" target="_blank">click here to open in a new tab</a>
            </p>
            """

            status_message = f"""
            ✅ **Success!** Interactive pivot table generated successfully

            📊 **Data Summary:**
            - **Rows:** {pivot_result.shape[0]} failure combinations
            - **Columns:** {pivot_result.shape[1]} stations/fields
            - **Filter Applied:** {operator_filter if operator_filter != "All" else "None (showing all operators)"}

            🎯 **Features Available:**
            - Click arrows to expand/collapse test case groups
            - Use column headers to sort and filter data
            - Hover over cells for detailed information
            """

            return status_message, iframe_html

        except Exception as e:
            logger.error(f"Error generating interactive pivot: {e}")
            return f"❌ **Error:** {str(e)}", ""

    @capture_exceptions(
        user_message="Interactive error analysis generation failed",
        return_value=("❌ **Error:** Failed to generate interactive error analysis", ""),
    )
    def generate_error_analysis_wrapped(df, operator_filter):
        """Generate interactive Excel-style error analysis table using Dash AG Grid."""
        global dash_process

        logger.info("Generating interactive Excel-style error analysis table")

        # Check if dataframe is loaded
        if df is None or df.empty:
            logger.warning("No data loaded for interactive error analysis")
            return "⚠️ **Error:** No data loaded. Please upload a CSV file first.", ""

        # Check if required error columns exist
        if "error_code" not in df.columns or "error_message" not in df.columns:
            logger.warning("Required error columns not found")
            return "⚠️ **Error:** Required columns 'error_code' and 'error_message' not found in data.", ""

        try:
            # Stop any previously running Dash app
            if dash_process and dash_process.poll() is None:
                logger.info("Stopping previous Dash process")
                dash_process.terminate()
                time.sleep(1)  # Give it time to stop

            # Create the Excel-style error analysis pivot data
            pivot_result = create_excel_style_error_pivot(df, operator_filter)

            if pivot_result.empty:
                logger.warning("Generated error analysis table is empty")
                return (
                    "⚠️ **Warning:** No error data found with the current filter settings.",
                    "",
                )

            logger.info(f"Generated error analysis data with shape: {pivot_result.shape}")

            # Save the pivot data to a temporary file
            temp_dir = tempfile.gettempdir()
            data_file = os.path.join(temp_dir, "monsterc_error_data.json")

            # Convert to JSON format for Dash app
            pivot_json = pivot_result.to_dict("records")
            with open(data_file, "w") as f:
                json.dump(pivot_json, f)

            logger.info(f"Saved error analysis data to: {data_file}")

            # Launch the Dash app with the data file
            dash_script = os.path.join(
                os.path.dirname(__file__), "..", "dash_pivot_app.py"
            )
            dash_process = subprocess.Popen(
                ["python", dash_script, data_file], cwd=os.path.dirname(dash_script)
            )

            # Give the server time to start
            time.sleep(3)

            # Check if the process started successfully
            if dash_process.poll() is not None:
                logger.error("Dash process failed to start")
                return "❌ **Error:** Failed to start interactive error analysis server.", ""

            # Create the iframe HTML
            iframe_html = f"""
            <div style="width: 100%; height: 800px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <iframe
                    src="http://127.0.0.1:8051"
                    width="100%"
                    height="800px"
                    frameborder="0"
                    style="border: none;">
                </iframe>
            </div>
            <p style="text-align: center; margin-top: 10px; color: #666; font-size: 14px;">
                💡 If the error analysis table doesn't load, <a href="http://127.0.0.1:8051" target="_blank">click here to open in a new tab</a>
            </p>
            """

            status_message = f"""
            ✅ **Success!** Interactive error analysis table generated successfully

            📊 **Data Summary:**
            - **Rows:** {pivot_result.shape[0]} error combinations (Model → Error Code → Error Message)
            - **Columns:** {pivot_result.shape[1]} stations/fields
            - **Filter Applied:** {operator_filter if operator_filter != "All" else "None (showing all operators)"}

            🎯 **3-Level Hierarchy Features:**
            - 📁 Model groups (top level)
            - 📂 Error Code subgroups (middle level)  
            - └─ Error Message details (bottom level)
            - RED highlighting for highest error counts per group
            - YELLOW highlighting for highest counts per error message
            """

            return status_message, iframe_html

        except Exception as e:
            logger.error(f"Error generating interactive error analysis: {e}")
            return f"❌ **Error:** {str(e)}", ""

    @capture_exceptions(user_message="Data processing failed", return_value=None)
    def process_data_wrapped(
        df, source, station_id, model_input, result_fail, flexible_search
    ):
        """Wrapper for process_data with error handling."""
        logger.info("Processing IMEI extraction data")
        return process_data(
            df, source, station_id, model_input, result_fail, flexible_search
        )

    # Wire up event handlers exactly as in the original
    file_input.change(
        load_and_update_wrapped,
        inputs=[file_input],
        outputs=[
            df,
            source,  # IMEI Extractor: Source
            station_id,  # IMEI Extractor: Station ID
            model_input,  # IMEI Extractor: Model(s)
            result_fail,  # IMEI Extractor: Result Fail
            advanced_operator_filter,
            advanced_model_filter,
            advanced_manufacturer_filter,
            advanced_source_filter,
            advanced_overall_status_filter,
            advanced_station_id_filter,
            advanced_result_fail_filter,
            pivot_rows,  # For Pivot Table Builder
            pivot_columns,
            pivot_values,
            filter_operator,  # Pivot Table Filters
            filter_station_id,
            filter_model,
            operator_filter,
            source_filter,
            station_id_filter,
            interactive_operator_filter,  # Interactive pivot filter
        ],
    )

    analyze_button.click(
        fn=perform_analysis_wrapped,
        inputs=[file_input],
        outputs=[
            analysis_summary,
            overall_status_chart,
            stations_chart,
            models_chart,
            test_cases_chart,
            stations_df,
            models_df,
            test_cases_df,
        ],
    )

    filter_type.change(
        update_filter_visibility_wrapped,
        inputs=[filter_type],
        outputs=[operator_filter, source_filter, station_id_filter],
    )

    custom_filter_button.click(
        filter_data_wrapped,
        inputs=[df, filter_type, operator_filter, source_filter, station_id_filter],
        outputs=[
            custom_filter_summary,
            custom_filter_chart1,
            custom_filter_chart2,
            custom_filter_chart3,
            custom_filter_df1,
            custom_filter_df2,
            custom_filter_df3,
        ],
    )

    analyze_wifi_button.click(
        analyze_wifi_errors_wrapped,
        inputs=[file_input, error_threshold],
        outputs=[summary_table, error_heatmap, pivot_table, hourly_trend_plot],
    )

    analyze_failures_button.click(
        analyze_repeated_failures_wrapped,
        inputs=[file_input, min_failures],
        outputs=[failures_summary, failures_chart, failures_df, test_case_filter],
    )

    sort_by.change(
        update_summary_chart_and_data_wrapped,
        inputs=[failures_df, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart, failures_df],
    )

    test_case_filter.change(
        update_summary_chart_and_data_wrapped,
        inputs=[failures_df, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart, failures_df],
    )

    # Add select/clear all handler
    test_case_filter.select(
        handle_test_case_selection_wrapped,
        inputs=[test_case_filter],
        outputs=[test_case_filter],
    )

    apply_filter_button.click(
        apply_filter_and_sort_wrapped,
        inputs=[
            df,
            sort_columns,
            advanced_operator_filter,
            advanced_model_filter,
            advanced_manufacturer_filter,
            advanced_source_filter,
            advanced_overall_status_filter,
            advanced_station_id_filter,
            advanced_result_fail_filter,
        ],
        outputs=[filtered_data, filter_summary],
    )

    generate_pivot_button.click(
        generate_pivot_table_filtered_wrapped,
        inputs=[
            df,
            pivot_rows,
            pivot_columns,
            pivot_values,
            pivot_aggfunc,
            filter_operator,
            filter_station_id,
            filter_model,
        ],
        outputs=[pivot_table_output],
    )

    catch_failures_button.click(
        catch_high_failures_wrapped,
        inputs=[df, filter_operator],
        outputs=[pivot_table_output],
    )

    generate_interactive_pivot_button.click(
        generate_interactive_pivot_wrapped,
        inputs=[df, interactive_operator_filter],
        outputs=[interactive_pivot_status, interactive_pivot_iframe],
    )

    generate_error_analysis_button.click(
        generate_error_analysis_wrapped,
        inputs=[df, interactive_operator_filter],
        outputs=[interactive_pivot_status, interactive_pivot_iframe],
    )

    process_button.click(
        process_data_wrapped,
        inputs=[
            df,
            source,
            station_id,
            model_input,
            result_fail,
            flexible_search,
        ],
        outputs=[messages_output, raw_data_output, gauge_output, summary_output],
    )


# Launch function for external use
def launch_app(share=False, **kwargs):
    """
    Launch the Gradio application.

    Args:
        share: Whether to create a public link
        **kwargs: Additional arguments to pass to demo.launch()
    """
    logger.info("Launching MonsterC Gradio application")
    return demo.launch(share=share, **kwargs)


if __name__ == "__main__":
    launch_app(share=False)
