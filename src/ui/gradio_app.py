"""
Gradio UI Layer for MonsterC CSV Analysis Tool.

This module implements the Strangler Fig pattern - creating a new UI shell that maintains
100% compatibility with the original while gradually introducing the new modular architecture.
"""

import atexit
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
    create_excel_style_error_pivot,
    create_excel_style_failure_pivot,
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

# Global variable to hold subprocess
dash_process = None  # Will be renamed to tabulator_process later


def cleanup_processes():
    """Cleanup function to terminate subprocess on exit."""
    global dash_process
    if dash_process and dash_process.poll() is None:
        logger.info("Terminating subprocess on exit.")
        dash_process.terminate()
        dash_process.wait()


atexit.register(cleanup_processes)


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
                    "🤖 Automation High Failures", variant="primary"
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
            # Main action buttons prominently displayed at the TOP
            with gr.Row():
                with gr.Column(scale=1):
                    generate_interactive_pivot_button = gr.Button(
                        "🤖 Automation High Failures",
                        variant="primary",
                        size="lg",
                    )
                with gr.Column(scale=1):
                    generate_error_analysis_button = gr.Button(
                        "🔍 Generate High Error Rates",
                        variant="secondary",
                        size="lg",
                    )

            # Configuration options in collapsible accordions
            with gr.Accordion("⚙️ Failure Counting Method", open=False):
                failure_counting_method = gr.Radio(
                    choices=[
                        "Pure Failures (Overall status = 'FAILURE')",
                        "Comprehensive (FAILURE or ERROR with result_FAIL)",
                    ],
                    label="Method Selection",
                    value="Pure Failures (Overall status = 'FAILURE')",
                    interactive=True,
                    info="Pure: Counts only FAILURE status | Comprehensive: Includes ERROR records with test data",
                )

            with gr.Accordion("🔍 Filter Options", open=False):
                interactive_operator_filter = gr.Dropdown(
                    label="Filter by Operator (Optional)",
                    choices=["All"],
                    value="All",
                    interactive=True,
                )

            with gr.Row():
                interactive_pivot_status = gr.Markdown(
                    value="📝 **Status:** Ready to generate interactive pivot table",
                    elem_classes=["markdown-body"],
                )

            # Prominent view selector buttons (hidden until data is generated)
            with gr.Row(visible=False) as view_selector_row:
                gr.HTML(
                    """
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin: 10px 0;">
                    <h3 style="color: white; margin-bottom: 15px; font-size: 18px;">🎯 Choose Your View</h3>
                    <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
                        <a href="http://127.0.0.1:8051" target="_blank" style="text-decoration: none;">
                            <div class="view-button classic-view">
                                <div style="background: #28a745; color: white; padding: 15px 25px; border-radius: 10px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3); transition: all 0.3s ease; border: none; cursor: pointer; min-width: 200px;">
                                    📊 Classic AG Grid View
                                    <div style="font-size: 12px; margin-top: 5px; opacity: 0.9;">Traditional Excel-style</div>
                                </div>
                            </div>
                        </a>
                        <a href="http://127.0.0.1:5001" target="_blank" style="text-decoration: none;">
                            <div class="view-button tabulator-view">
                                <div style="background: linear-gradient(45deg, #ff6b6b, #ffa500); color: white; padding: 15px 25px; border-radius: 10px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); transition: all 0.3s ease; border: none; cursor: pointer; min-width: 200px; animation: pulse-glow 2s infinite;">
                                    ✨ NEW: Collapsible Groups! ✨
                                    <div style="font-size: 12px; margin-top: 5px; opacity: 0.9;">Native tree view + heat maps</div>
                                </div>
                            </div>
                        </a>
                    </div>
                </div>

                <style>
                    @keyframes pulse-glow {
                        0% { box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }
                        50% { box-shadow: 0 6px 25px rgba(255, 107, 107, 0.8), 0 0 20px rgba(255, 165, 0, 0.6); }
                        100% { box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }
                    }

                    .view-button:hover > div {
                        transform: translateY(-3px) scale(1.05);
                        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3) !important;
                    }

                    .classic-view:hover > div {
                        background: #218838 !important;
                    }

                    .tabulator-view:hover > div {
                        background: linear-gradient(45deg, #ff5252, #ff9800) !important;
                    }
                </style>
                """
                )

            with gr.Row():
                interactive_pivot_iframe = gr.HTML(
                    value="", label="Interactive Pivot Table"
                )

            # Informational content in collapsible accordion at bottom
            with gr.Accordion("📚 Analysis Guide & Details", open=False):
                gr.Markdown(
                    """
                ## Excel-Style Hierarchical Pivot Analysis

                This feature provides **two main analysis workflows** that replicate Excel pivot functionality:

                ### 🤖 Automation High Failures
                - **Hierarchy:** Test Case → Model (2-level)
                - **Purpose:** Identify automation line failure patterns (4 operators only)
                - **Data:** FAILURE + ERROR with result_FAIL logic for automation operators
                - **Scope:** STN251_RED, STN252_RED, STN351_GRN, STN352_GRN (24 stations)
                - **✨ NEW:** Native collapsible groups with Tabulator.js ([Launch Tabulator Interface](http://127.0.0.1:5001))

                ### 🔍 Generate High Error Rates
                - **Hierarchy:** Model → Error Code → Error Message (3-level)
                - **Purpose:** Deep-dive error code analysis
                - **Data:** error_code and error_message field analysis

                ### ✨ Both Include:
                - 📋 **Expandable groups** with visual hierarchy (📁 📂 └─)
                - 🎨 **Smart color coding** (RED for highest per group, ORANGE per test case, YELLOW for top 3 models)
                - 📊 **Grand Total column** (sum of all station failures)
                - 🔍 **Interactive exploration** with collapsible groups
                - ⚡ **High performance** with large datasets

                **How to use:** Click the automation button above, then optionally explore the enhanced Tabulator interface!
                """
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
        """Wrapper for automation-only high failure detection with ERROR + result_FAIL logic."""
        logger.info("Generating automation-only high failure analysis")

        # Check if dataframe is loaded
        if df is None or df.empty:
            logger.warning("No data loaded. Please upload a CSV file first.")
            return pd.DataFrame({"Message": ["Please upload a CSV file first"]})

        logger.info(
            f"Input DataFrame shape: {df.shape}, Operator filter: {operator_filter}"
        )

        # Define automation operators based on business logic analysis
        automation_operators = [
            "STN251_RED(id:10089)",  # STN1_RED
            "STN252_RED(id:10090)",  # STN2_RED
            "STN351_GRN(id:10380)",  # STN1_GREEN
            "STN352_GRN(id:10381)",  # STN2_GREEN
        ]

        # Filter for automation operators only
        automation_df = df[df["Operator"].isin(automation_operators)]
        logger.info(
            f"Filtered to automation operators only: {automation_df.shape[0]} records"
        )

        if automation_df.empty:
            return pd.DataFrame({"Message": ["No automation operator data found"]})

        # Apply business logic: Count FAILURE OR (ERROR with result_FAIL populated)
        failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
            (automation_df["Overall status"] == "ERROR")
            & (automation_df["result_FAIL"].notna())
            & (automation_df["result_FAIL"].str.strip() != "")
        )

        automation_failures = automation_df[failure_conditions]
        logger.info(
            f"Found {len(automation_failures)} automation failures using FAILURE + ERROR with result_FAIL logic"
        )

        if automation_failures.empty:
            return pd.DataFrame({"Message": ["No automation failures found"]})

        # Create Excel-style pivot focused on automation failures only
        pivot_result = create_excel_style_failure_pivot(automation_failures, None)

        # Apply conditional formatting for high failure highlighting
        if not pivot_result.empty and "Error" not in pivot_result.columns:
            styled_result = apply_failure_highlighting(pivot_result)
            return styled_result

        return pivot_result

    # Global variable to hold the Dash subprocess
    dash_process = None

    @capture_exceptions(
        user_message="Interactive pivot generation failed",
        return_value=(
            "❌ **Error:** Failed to generate interactive pivot table",
            "",
            gr.Row(visible=False),
        ),
    )
    def generate_interactive_pivot_wrapped(
        df, operator_filter, failure_counting_method
    ):
        """Generate interactive automation-only high failure analysis using Tabulator."""
        global dash_process  # Will rename to tabulator_process later

        logger.info(
            f"Generating interactive failure analysis with method: {failure_counting_method}"
        )

        # Check if dataframe is loaded
        if df is None or df.empty:
            logger.warning("No data loaded for interactive pivot")
            return (
                "⚠️ **Error:** No data loaded. Please upload a CSV file first.",
                "",
                gr.Row(visible=False),
            )

        try:
            # Stop any previously running Dash app
            if dash_process and dash_process.poll() is None:
                logger.info("Stopping previous Dash process")
                dash_process.terminate()
                time.sleep(1)  # Give it time to stop

            # Debug: Check what operators exist in the data and their failure counts
            logger.info(
                f"🔍 All unique operators in data: {sorted(df['Operator'].unique())}"
            )

            # Check failure counts for ALL operators to see what Excel might be including
            all_operator_failures = (
                df[df["Overall status"] == "FAILURE"]
                .groupby("Operator")
                .size()
                .to_dict()
            )
            logger.info(f"🔍 Failure counts by ALL operators: {all_operator_failures}")

            # Also check if Excel might be filtering by Station ID patterns instead of Operator
            failure_data = df[df["Overall status"] == "FAILURE"]
            station_operator_mapping = (
                failure_data.groupby(["Station ID", "Operator"])
                .size()
                .reset_index(name="count")
            )
            logger.info(f"🔍 Station ID to Operator mapping for failures:")
            for _, row in station_operator_mapping.iterrows():
                logger.info(
                    f"   {row['Station ID']} -> {row['Operator']} ({row['count']} failures)"
                )

            # Check if there are automation station IDs with different operators
            automation_station_pattern = failure_data[
                failure_data["Station ID"].str.startswith("radi", na=False)
            ]
            if not automation_station_pattern.empty:
                unique_operators_for_radi = automation_station_pattern[
                    "Operator"
                ].unique()
                logger.info(
                    f"🔍 Operators found for RADI stations: {unique_operators_for_radi}"
                )

            # Define automation operators based on business logic analysis
            automation_operators = [
                "STN251_RED(id:10089)",  # STN1_RED
                "STN252_RED(id:10090)",  # STN2_RED
                "STN351_GRN(id:10380)",  # STN1_GREEN
                "STN352_GRN(id:10381)",  # STN2_GREEN
            ]

            # CRITICAL ANALYSIS: Compare counting methods to find data quality issues
            logger.info("🚨 INVESTIGATING DATA QUALITY DISCREPANCY:")

            # Method 1: Count by Overall status == "FAILURE" (our current method)
            method1_failures = df[
                (df["Operator"].isin(automation_operators))
                & (df["Overall status"] == "FAILURE")
            ]
            method1_by_station = method1_failures.groupby("Station ID").size().to_dict()
            logger.info(
                f"📊 Method 1 (Overall status=FAILURE): {sum(method1_by_station.values())} total failures"
            )

            # Method 2: Count by populated result_FAIL (customer's preferred method)
            method2_failures = df[
                (df["Operator"].isin(automation_operators))
                & (df["result_FAIL"].notna())
                & (df["result_FAIL"].str.strip() != "")
            ]
            method2_by_station = method2_failures.groupby("Station ID").size().to_dict()
            logger.info(
                f"📊 Method 2 (populated result_FAIL): {sum(method2_by_station.values())} total failures"
            )

            # Find discrepancies per station
            all_stations = set(
                list(method1_by_station.keys()) + list(method2_by_station.keys())
            )
            logger.info("🔍 STATION-BY-STATION COMPARISON:")
            for station in sorted(all_stations):
                count1 = method1_by_station.get(station, 0)
                count2 = method2_by_station.get(station, 0)
                diff = count1 - count2
                if diff != 0:
                    logger.error(
                        f"❌ {station}: Method1={count1}, Method2={count2}, Diff={diff}"
                    )
                else:
                    logger.info(f"✅ {station}: Both methods={count1}")

            # Identify the problematic records causing discrepancies
            logger.info("🔍 ANALYZING PROBLEMATIC RECORDS:")

            # Records with FAILURE status but no result_FAIL
            ghost_failures = df[
                (df["Operator"].isin(automation_operators))
                & (df["Overall status"] == "FAILURE")
                & ((df["result_FAIL"].isna()) | (df["result_FAIL"].str.strip() == ""))
            ]
            if not ghost_failures.empty:
                logger.warning(
                    f"👻 GHOST FAILURES: {len(ghost_failures)} records with FAILURE status but no result_FAIL"
                )
                ghost_by_station = ghost_failures.groupby("Station ID").size().to_dict()
                for station, count in ghost_by_station.items():
                    logger.warning(f"   👻 {station}: {count} ghost failures")

            # Records with result_FAIL but not FAILURE status
            phantom_results = df[
                (df["Operator"].isin(automation_operators))
                & (df["result_FAIL"].notna())
                & (df["result_FAIL"].str.strip() != "")
                & (df["Overall status"] != "FAILURE")
            ]
            if not phantom_results.empty:
                logger.warning(
                    f"👻 PHANTOM RESULTS: {len(phantom_results)} records with result_FAIL but not FAILURE status"
                )
                phantom_statuses = (
                    phantom_results["Overall status"].value_counts().to_dict()
                )
                logger.warning(f"   👻 Phantom statuses: {phantom_statuses}")
                phantom_by_station = (
                    phantom_results.groupby("Station ID").size().to_dict()
                )
                for station, count in phantom_by_station.items():
                    logger.warning(f"   👻 {station}: {count} phantom results")

            logger.info(f"🔍 Looking for automation operators: {automation_operators}")

            # Filter for automation operators only
            automation_df = df[df["Operator"].isin(automation_operators)]
            logger.info(
                f"Filtered to automation operators only: {automation_df.shape[0]} records"
            )

            if automation_df.empty:
                return (
                    "⚠️ **Error:** No automation operator data found.",
                    "",
                    gr.Row(visible=False),
                )

            # Apply user-selected counting method
            if "Comprehensive" in failure_counting_method:
                # Method B: Comprehensive Analysis - includes ERROR records with test data
                failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
                    (automation_df["Overall status"] == "ERROR")
                    & (automation_df["result_FAIL"].notna())
                    & (automation_df["result_FAIL"].str.strip() != "")
                )
                logger.info(
                    "Using Comprehensive failure counting method (FAILURE + ERROR with result_FAIL)"
                )
            else:
                # Method A: Pure Failures (Default) - Excel-compatible
                failure_conditions = automation_df["Overall status"] == "FAILURE"
                logger.info("Using Pure Failures counting method (FAILURE only)")

            automation_failures = automation_df[failure_conditions]
            logger.info(
                f"Found {len(automation_failures)} automation failures using {failure_counting_method}"
            )

            if automation_failures.empty:
                return (
                    "⚠️ **Warning:** No automation failures found with the current criteria.",
                    "",
                    gr.Row(visible=False),
                )

            # Save raw automation failure data for Tabulator (preserves concatenated test cases)
            temp_dir = tempfile.gettempdir()
            automation_data_file = os.path.join(
                temp_dir, "monsterc_automation_data.json"
            )
            # Convert datetime columns to strings for JSON serialization
            automation_failures_json = automation_failures.copy()
            for col in automation_failures_json.columns:
                # Check for datetime types and timestamp objects
                col_dtype = str(automation_failures_json[col].dtype).lower()
                if (
                    "datetime" in col_dtype
                    or "timestamp" in col_dtype
                    or automation_failures_json[col].dtype.name
                    in ["datetime64[ns]", "datetime64[ns, UTC]"]
                ):
                    automation_failures_json[col] = automation_failures_json[
                        col
                    ].astype(str)
                # Also check for object columns that might contain Timestamp objects
                elif automation_failures_json[col].dtype == "object":
                    try:
                        # Sample first non-null value to check if it's a Timestamp
                        sample_val = (
                            automation_failures_json[col].dropna().iloc[0]
                            if not automation_failures_json[col].dropna().empty
                            else None
                        )
                        if sample_val is not None and hasattr(sample_val, "timestamp"):
                            automation_failures_json[col] = automation_failures_json[
                                col
                            ].astype(str)
                    except (IndexError, AttributeError):
                        pass  # Not a timestamp column
            automation_json = automation_failures_json.to_dict("records")
            with open(automation_data_file, "w") as f:
                json.dump(automation_json, f)
            logger.info(f"📊 Saved raw automation data to: {automation_data_file}")
            logger.info(
                f"🔗 Raw data contains concatenated test cases like: {automation_failures['result_FAIL'].unique()[:3]}"
            )

            # Calculate device failure counts per station BEFORE filtering - this captures ALL failures like Excel
            # This counts actual device failures (not exploded test cases) for the TOTAL row
            device_failure_counts = (
                automation_failures.groupby("Station ID").size().to_dict()
            )
            total_device_failures = sum(device_failure_counts.values())
            logger.info(
                f"📊 Device failure counts per station (ALL failures): {device_failure_counts}"
            )
            logger.info(
                f"📊 Total device failures (Excel-compatible): {total_device_failures}"
            )
            logger.info(
                f"📊 Number of unique Station IDs: {len(device_failure_counts)} (expected: 24)"
            )
            logger.info(
                f"📊 Station IDs with failures: {sorted(device_failure_counts.keys())}"
            )

            # Filter to only failures with populated result_FAIL for detailed pivot analysis
            failures_with_test_cases = automation_failures[
                automation_failures["result_FAIL"].notna()
                & (automation_failures["result_FAIL"].str.strip() != "")
            ]
            logger.info(
                f"📊 Failures with test case details: {len(failures_with_test_cases)}"
            )
            logger.info(
                f"📊 Failures without test case details: {len(automation_failures) - len(failures_with_test_cases)}"
            )

            # Create the Excel-style pivot data using only failures with test case details
            # This creates detailed test case breakdown, totals will be calculated correctly in frontend
            pivot_result = create_excel_style_failure_pivot(
                failures_with_test_cases, None
            )

            if pivot_result.empty:
                logger.warning("Generated pivot table is empty")
                return (
                    "⚠️ **Warning:** No failure data found with the current filter settings.",
                    "",
                    gr.Row(visible=False),
                )

            logger.info(f"Generated pivot data with shape: {pivot_result.shape}")

            # Check if we have all expected automation stations
            if len(device_failure_counts) < 24:
                logger.warning(
                    f"⚠️ Missing stations! Only {len(device_failure_counts)}/24 stations have failures"
                )
                all_automation_stations = set(
                    automation_failures["Station ID"].unique()
                )
                stations_with_failures = set(device_failure_counts.keys())
                logger.info(
                    f"📊 All automation stations in data: {sorted(all_automation_stations)} (count: {len(all_automation_stations)})"
                )
                if len(all_automation_stations) > len(stations_with_failures):
                    stations_no_failures = (
                        all_automation_stations - stations_with_failures
                    )
                    logger.info(
                        f"📊 Stations with zero failures: {sorted(stations_no_failures)}"
                    )

            # Save the pivot data to a temporary file
            temp_dir = tempfile.gettempdir()
            data_file = os.path.join(temp_dir, "monsterc_pivot_data.json")
            device_counts_file = os.path.join(temp_dir, "monsterc_device_counts.json")

            # Convert to JSON format for Dash app (handle datetime columns)
            pivot_result_json = pivot_result.copy()
            for col in pivot_result_json.columns:
                # Check for datetime types and timestamp objects
                col_dtype = str(pivot_result_json[col].dtype).lower()
                if (
                    "datetime" in col_dtype
                    or "timestamp" in col_dtype
                    or pivot_result_json[col].dtype.name
                    in ["datetime64[ns]", "datetime64[ns, UTC]"]
                ):
                    pivot_result_json[col] = pivot_result_json[col].astype(str)
                # Also check for object columns that might contain Timestamp objects
                elif pivot_result_json[col].dtype == "object":
                    try:
                        # Sample first non-null value to check if it's a Timestamp
                        sample_val = (
                            pivot_result_json[col].dropna().iloc[0]
                            if not pivot_result_json[col].dropna().empty
                            else None
                        )
                        if sample_val is not None and hasattr(sample_val, "timestamp"):
                            pivot_result_json[col] = pivot_result_json[col].astype(str)
                    except (IndexError, AttributeError):
                        pass  # Not a timestamp column
            pivot_json = pivot_result_json.to_dict("records")
            with open(data_file, "w") as f:
                json.dump(pivot_json, f)

            # Save device failure counts for accurate total calculations
            with open(device_counts_file, "w") as f:
                json.dump(device_failure_counts, f)

            logger.info(f"Saved pivot data to: {data_file}")
            logger.info(f"Saved device counts to: {device_counts_file}")

            # Create data paths object for Tabulator app
            data_paths = {
                "pivot_data": data_file,
                "device_counts": device_counts_file,
                "automation_data": automation_data_file,
            }
            paths_arg = json.dumps(data_paths)

            # Launch the Tabulator app with data paths
            tabulator_script = os.path.join(
                os.path.dirname(__file__), "..", "tabulator_app.py"
            )
            dash_process = subprocess.Popen(
                ["python", tabulator_script, paths_arg],
                cwd=os.path.dirname(tabulator_script),
            )

            # Give the server time to start
            time.sleep(3)

            # Check if the process started successfully
            if dash_process.poll() is not None:
                logger.error("Dash process failed to start")
                return (
                    "❌ **Error:** Failed to start interactive pivot server.",
                    "",
                    gr.Row(visible=False),
                )

            # Create the iframe HTML with zoomed out view for quick snapshot
            iframe_html = f"""
            <div style="width: 100%; margin-top: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 8px 8px 0 0;">
                    <h3 style="color: white; margin: 0; text-align: center; font-size: 20px;">
                        📊 Interactive Pivot Table - Quick Snapshot View
                    </h3>
                    <p style="color: white; margin: 5px 0 0 0; text-align: center; font-size: 14px;">
                        💡 Tip: <a href="http://127.0.0.1:5001" target="_blank" style="color: #FFE66D; font-weight: bold; text-decoration: underline;">
                        Open in New Tab</a> for full analysis with zoom controls
                    </p>
                </div>
                <div style="border: 2px solid #667eea; border-top: none; border-radius: 0 0 8px 8px; overflow: hidden;">
                    <iframe
                        src="http://127.0.0.1:5001"
                        width="100%"
                        height="750px"
                        frameborder="0"
                        style="border: none;">
                    </iframe>
                </div>
            </div>
            """

            # Calculate percentages for better insights
            station_utilization_pct = round((len(device_failure_counts) / 24) * 100, 1)

            # Determine color coding based on values
            failure_status = (
                "🔴 HIGH"
                if total_device_failures > 800
                else "🟡 MEDIUM"
                if total_device_failures > 400
                else "🟢 LOW"
            )
            station_status = (
                "🔴 HIGH"
                if station_utilization_pct > 75
                else "🟡 MEDIUM"
                if station_utilization_pct > 50
                else "🟢 LOW"
            )

            # Calculate top performing metrics for summary cards
            top_station_id = "N/A"
            top_station_count = 0
            top_test_case = "N/A"
            top_test_case_count = 0
            top_model = "N/A"
            top_model_count = 0

            # Find top Station ID from device_failure_counts
            if device_failure_counts:
                top_station_id = max(
                    device_failure_counts, key=device_failure_counts.get
                )
                top_station_count = device_failure_counts[top_station_id]

            # Find top Test Case and Model from pivot_result
            if not pivot_result.empty and "result_FAIL" in pivot_result.columns:
                try:
                    # Group by test case and sum across all models and stations
                    test_case_counts = (
                        pivot_result.groupby("result_FAIL")
                        .sum(numeric_only=True)
                        .sum(axis=1)
                    )
                    if not test_case_counts.empty:
                        top_test_case = test_case_counts.idxmax()
                        top_test_case_count = int(test_case_counts.max())
                except Exception as e:
                    logger.warning(f"Error calculating top test case: {e}")

                # Group by model and sum across all test cases and stations
                if "Model" in pivot_result.columns:
                    try:
                        model_counts = (
                            pivot_result.groupby("Model")
                            .sum(numeric_only=True)
                            .sum(axis=1)
                        )
                        if not model_counts.empty:
                            top_model = model_counts.idxmax()
                            top_model_count = int(model_counts.max())
                    except Exception as e:
                        logger.warning(f"Error calculating top model: {e}")

            # HTML escape function for dynamic content
            import html

            # Create compact summary table as HTML for side-by-side layout
            summary_table_html = f"""
            <div style="background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 15px; height: fit-content;">
                <h4 style="color: #667eea; margin: 0 0 12px 0; font-size: 16px; font-weight: 600;">📊 Analysis Summary</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr>
                        <td style="padding: 6px 8px; border-bottom: 1px solid rgba(107, 99, 246, 0.2); font-weight: 600; color: #667eea;">Total Failures:</td>
                        <td style="padding: 6px 8px; border-bottom: 1px solid rgba(107, 99, 246, 0.2); font-weight: bold; color: {'#dc3545' if '🔴' in failure_status else '#ffc107' if '🟡' in failure_status else '#28a745'};">{total_device_failures:,}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 8px; border-bottom: 1px solid rgba(107, 99, 246, 0.2); font-weight: 600; color: #667eea;">Failure Types:</td>
                        <td style="padding: 6px 8px; border-bottom: 1px solid rgba(107, 99, 246, 0.2);">{pivot_result.shape[0]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 8px; border-bottom: 1px solid rgba(107, 99, 246, 0.2); font-weight: 600; color: #667eea;">Stations:</td>
                        <td style="padding: 6px 8px; border-bottom: 1px solid rgba(107, 99, 246, 0.2);">{len(device_failure_counts)}/24 ({station_utilization_pct}%)</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 8px; font-weight: 600; color: #667eea;">Method:</td>
                        <td style="padding: 6px 8px; font-size: 12px;">{"Pure Failures" if "Pure" in failure_counting_method else "Comprehensive"}</td>
                    </tr>
                </table>
            </div>
            """

            # Create compact summary cards - smaller and in a single row
            summary_cards_html = f"""
            <div style="display: flex; gap: 12px; flex: 1;">
                <!-- Top Station Card -->
                <div style="flex: 1; min-width: 180px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); border-radius: 8px; padding: 12px; color: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 18px; margin-right: 6px;">🏭</span>
                        <h4 style="margin: 0; font-size: 13px; font-weight: 600;">Top Station</h4>
                    </div>
                    <div style="font-size: 20px; font-weight: bold; margin-bottom: 2px;">{top_station_count:,}</div>
                    <div style="font-size: 11px; opacity: 0.9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{html.escape(str(top_station_id))}">{html.escape(str(top_station_id))}</div>
                </div>

                <!-- Top Test Case Card -->
                <div style="flex: 1; min-width: 180px; background: linear-gradient(135deg, #feca57 0%, #ff9ff3 100%); border-radius: 8px; padding: 12px; color: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 18px; margin-right: 6px;">🔬</span>
                        <h4 style="margin: 0; font-size: 13px; font-weight: 600;">Top Test Case</h4>
                    </div>
                    <div style="font-size: 20px; font-weight: bold; margin-bottom: 2px;">{top_test_case_count:,}</div>
                    <div style="font-size: 11px; opacity: 0.9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{html.escape(str(top_test_case))}">{html.escape(str(top_test_case))}</div>
                </div>

                <!-- Top Model Card -->
                <div style="flex: 1; min-width: 180px; background: linear-gradient(135deg, #5f27cd 0%, #341f97 100%); border-radius: 8px; padding: 12px; color: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 18px; margin-right: 6px;">📱</span>
                        <h4 style="margin: 0; font-size: 13px; font-weight: 600;">Top Model</h4>
                    </div>
                    <div style="font-size: 20px; font-weight: bold; margin-bottom: 2px;">{top_model_count:,}</div>
                    <div style="font-size: 11px; opacity: 0.9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{html.escape(str(top_model))}">{html.escape(str(top_model))}</div>
                </div>
            </div>
            """

            # Minimal status message
            status_message = f"""✅ **Success!** Interactive pivot table generated with **{failure_counting_method}** method

💡 **Tip:** <a href="http://127.0.0.1:5001" target="_blank" style="color: #667eea; font-weight: bold;">Open in New Tab</a> for full analysis controls
"""

            # Create horizontal layout with cards left, table right, then iframe below
            combined_html = f"""
            <div style="margin-bottom: 15px;">
                <div style="display: flex; gap: 20px; margin-bottom: 15px; align-items: flex-start;">
                    <div style="flex: 2; min-width: 600px;">
                        <h3 style="color: #333; margin: 0 0 12px 0; font-size: 16px;">🎯 Top Performance Metrics</h3>
                        {summary_cards_html}
                    </div>
                    <div style="flex: 1; min-width: 250px; max-width: 320px;">
                        {summary_table_html}
                    </div>
                </div>
            </div>
            {iframe_html}
            """

            return status_message, combined_html, gr.Row(visible=False)

        except Exception as e:
            logger.error(f"Error generating interactive pivot: {e}")
            return f"❌ **Error:** {str(e)}", "", gr.Row(visible=False)

    @capture_exceptions(
        user_message="Interactive error analysis generation failed",
        return_value=(
            "❌ **Error:** Failed to generate interactive error analysis",
            "",
            gr.Row(visible=False),
        ),
    )
    def generate_error_analysis_wrapped(df, operator_filter):
        """Generate interactive Excel-style error analysis table using Dash AG Grid."""
        global dash_process

        logger.info("Generating interactive Excel-style error analysis table")

        # Check if dataframe is loaded
        if df is None or df.empty:
            logger.warning("No data loaded for interactive error analysis")
            return (
                "⚠️ **Error:** No data loaded. Please upload a CSV file first.",
                "",
                gr.Row(visible=False),
            )

        # Check if required error columns exist
        if "error_code" not in df.columns or "error_message" not in df.columns:
            logger.warning("Required error columns not found")
            return (
                "⚠️ **Error:** Required columns 'error_code' and 'error_message' not found in data.",
                "",
                gr.Row(visible=False),
            )

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
                    gr.Row(visible=False),
                )

            logger.info(
                f"Generated error analysis data with shape: {pivot_result.shape}"
            )

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
                return (
                    "❌ **Error:** Failed to start interactive error analysis server.",
                    "",
                    gr.Row(visible=False),
                )

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

            status_message = f"""✅ **Success!** Interactive error analysis table generated successfully

📊 **Summary:** {pivot_result.shape[0]} error combinations across {pivot_result.shape[1]} stations/fields
💡 **Tip:** <a href="http://127.0.0.1:8051" target="_blank" style="color: #667eea; font-weight: bold;">Open in New Tab</a> for better navigation"""

            return status_message, iframe_html, gr.Row(visible=True)

        except Exception as e:
            logger.error(f"Error generating interactive error analysis: {e}")
            return f"❌ **Error:** {str(e)}", "", gr.Row(visible=False)

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
        inputs=[df, interactive_operator_filter, failure_counting_method],
        outputs=[interactive_pivot_status, interactive_pivot_iframe, view_selector_row],
    )

    generate_error_analysis_button.click(
        generate_error_analysis_wrapped,
        inputs=[df, interactive_operator_filter],
        outputs=[interactive_pivot_status, interactive_pivot_iframe, view_selector_row],
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
