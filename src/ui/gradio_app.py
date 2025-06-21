"""
Gradio UI Layer for MonsterC CSV Analysis Tool.

This module implements the Strangler Fig pattern - creating a new UI shell that maintains
100% compatibility with the original while gradually introducing the new modular architecture.
"""

import gradio as gr
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Import from common modules (new architecture)
from common.io import load_data
from common.logging_config import capture_exceptions, get_logger

# Import from services (new architecture)
from services.analysis_service import perform_analysis
from services.filtering_service import (
    filter_data,
    update_filter_visibility, 
    apply_filter_and_sort,
    get_unique_values,
    update_filter_dropdowns
)
from services.pivot_service import (
    generate_pivot_table_filtered,
    create_pivot_table,
    apply_filters,
    find_top_failing_stations,
    analyze_top_models,
    analyze_top_test_cases
)
from services.repeated_failures_service import (
    analyze_repeated_failures,
    update_summary_chart_and_data,
    handle_test_case_selection
)
from services.wifi_error_service import (
    analyze_wifi_errors
)
from services.imei_extractor_service import (
    process_data
)

# Import legacy functions directly (temporary during migration)
from legacy_app import (
    
    # Data loading and processing
    load_and_update,
    
    # Data mappings (will be moved to common.mappings)
    test_to_result_fail_map,
    station_to_machine,
    device_map
)

# Configure logging
logger = get_logger(__name__)


# Gradio UI Definition
with gr.Blocks(theme=gr.themes.Soft(), css="""
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
""") as demo:
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
                    interactive=False
                )
                models_df = gr.Dataframe(
                    headers=["Model", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Models",
                    interactive=False
                )
                test_cases_df = gr.Dataframe(
                    headers=["Test Case", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Test Cases",
                    interactive=False
                )

        with gr.TabItem("Custom Data Filtering"):
            with gr.Row():
                filter_type = gr.Radio(
                    choices=["No Filter", "Filter by Operator", "Filter by Source"],
                    value="No Filter",
                    label="Select Filter Type",
                    interactive=True
                )
            
            with gr.Row():
                operator_filter = gr.Dropdown(
                    label="Operator", 
                    choices=["All"], 
                    value="All", 
                    interactive=True,
                    scale=1,
                    visible=False  # Initially hidden
                )
                source_filter = gr.Dropdown(
                    label="Source", 
                    choices=["All"], 
                    value="All", 
                    interactive=True,
                    scale=1,
                    visible=False  # Initially hidden
                )
                station_id_filter = gr.Dropdown(
                    label="Station ID", 
                    choices=["All"], 
                    value="All", 
                    interactive=True,
                    scale=1,
                    visible=False  # Initially hidden
                )
            
            with gr.Row():
                custom_filter_button = gr.Button("Filter Data")
            
            # Rest of the components remain the same
            with gr.Row():
                custom_filter_summary = gr.Markdown(
                    label="Filtered Summary",
                    value="",
                    elem_classes=["custom-markdown"]
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
                        interactive=True
                    )
                    filter_station_id = gr.Dropdown(
                        label="Filter by Station ID",
                        choices=["All"],
                        value="All",
                        multiselect=True,
                        interactive=True
                    )
                    filter_model = gr.Dropdown(
                        label="Filter by Model",
                        choices=["All"],
                        value="All",
                        multiselect=True,
                        interactive=True
                    )

                # Adding pivot table options after the filters
                with gr.Row():
                    # Pivot table configuration
                    pivot_rows = gr.Dropdown(
                        label="Select Row Fields (required)",
                        choices=[],
                        multiselect=True,
                        interactive=True
                    )
                    pivot_columns = gr.Dropdown(
                        label="Select Column Fields (optional)",
                        choices=[],
                        multiselect=True,
                        interactive=True
                    )
                    pivot_values = gr.Dropdown(
                        label="Select Values Field (required)",
                        choices=[],
                        interactive=True
                    )
                    pivot_aggfunc = gr.Dropdown(
                        label="Aggregation Function",
                        choices=['count', 'sum', 'mean', 'median', 'max', 'min'],
                        value='count',
                        interactive=True
                    )

                with gr.Row():
                    generate_pivot_button = gr.Button("Generate Pivot Table")

                with gr.Row():
                    pivot_table_output = gr.Dataframe(
                        label="Pivot Table Results",
                        interactive=False  
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
                    label="Sort Results By"
                )
                test_case_filter = gr.Dropdown(
                    choices=["Select All", "Clear All"],
                    value=[],
                    label="Filter by Test Case",
                    multiselect=True
                )
            
            with gr.Row():
                failures_summary = gr.Markdown(
                    value="",
                    label="Repeated Failures Summary"
                )
            with gr.Row():
                failures_chart = gr.Plot(label="Repeated Failures Chart")
            with gr.Row():
                failures_df = gr.Dataframe(label="Repeated Failures Data")



        with gr.TabItem("WiFi Error Analysis"):
            with gr.Row():
                error_threshold = gr.Slider(minimum=0, maximum=100, value=9, step=1, label="Error Threshold (%)")
            
            analyze_wifi_button = gr.Button("Analyze WiFi Errors")
            
            with gr.Row():
                summary_table = gr.Dataframe(label="Summary Table")
            
            with gr.Accordion("Detailed Analysis for High Error Rates", open=False):
                with gr.Row():
                    error_heatmap = gr.Plot(label="Detailed WiFi Error Heatmap")
                
                with gr.Row():
                    hourly_trend_plot = gr.Plot(label="Hourly Error Trends for High-Error Operators")
                
                with gr.Row():
                    pivot_table = gr.Dataframe(label="Hourly Error Breakdown by Operator and Error Type")
                        
        with gr.TabItem("Advanced Filtering"):
            with gr.Row():
                advanced_operator_filter = gr.Dropdown(label="Operator", choices=["All"], multiselect=True, value="All")
                advanced_model_filter = gr.Dropdown(label="Model", choices=["All"], multiselect=True, value="All")
                advanced_manufacturer_filter = gr.Dropdown(label="Manufacturer", choices=["All"], multiselect=True, value="All")
                advanced_source_filter = gr.Dropdown(label="Source", choices=["All"], multiselect=True, value="All")
            with gr.Row():
                advanced_overall_status_filter = gr.Dropdown(label="Overall status", choices=["All"], multiselect=True, value="All")
                advanced_station_id_filter = gr.Dropdown(label="Station ID", choices=["All"], multiselect=True, value="All")
                advanced_result_fail_filter = gr.Dropdown(label="result_FAIL", choices=["All"], multiselect=True, value="All")
            with gr.Row():
                sort_columns = gr.Dropdown(
                    choices=["Date Time", "Operator", "Model", "IMEI", "Manufacturer", "Source", 
                             "Overall status", "Station ID", "result_FAIL", "error_code", "error_message"],
                    label="Select columns to sort",
                    multiselect=True
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
                    label="Model(s)", choices=["All"], value="All", interactive=True, multiselect=True
                )
                result_fail = gr.Dropdown(
                    label="Result Fail", choices=["All"], value="All", interactive=True
                )
                flexible_search = gr.Checkbox(label="Enable Flexible Search", value=False)
            
            with gr.Row():
                process_button = gr.Button("Process Data", variant="primary")

            with gr.Column():
                # Group commands first
                with gr.Column(elem_classes=["command-section"]):
                    messages_output = gr.Code(
                        label="Messages Command", 
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"]
                    )
                    raw_data_output = gr.Code(
                        label="Raw Data Command", 
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"]
                    )
                    gauge_output = gr.Code(
                        label="Gauge Command", 
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"]
                    )
                
                # Then show summary
                summary_output = gr.Markdown(
                    label="Query Results", 
                    elem_classes=["markdown-body", "custom-markdown"]
                )
                
    # Event Handlers - Using decorated functions for error handling
    
    @capture_exceptions(user_message="Failed to load and update data", return_value=None)
    def load_and_update_wrapped(file):
        """Wrapper for load_and_update with error handling."""
        logger.info(f"Loading file: {getattr(file, 'name', 'unknown')}")
        return load_and_update(file)
    
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
    
    @capture_exceptions(user_message="Repeated failures analysis failed", return_value=None)
    def analyze_repeated_failures_wrapped(file, min_failures):
        """Wrapper for analyze_repeated_failures with error handling."""
        logger.info(f"Analyzing repeated failures with minimum: {min_failures}")
        return analyze_repeated_failures(file, min_failures)
    
    @capture_exceptions(user_message="Summary update failed", return_value=None)
    def update_summary_chart_and_data_wrapped(repeated_failures_df, sort_by, selected_test_cases):
        """Wrapper for update_summary_chart_and_data with error handling."""
        logger.info(f"Updating summary: sort_by={sort_by}")
        return update_summary_chart_and_data(repeated_failures_df, sort_by, selected_test_cases)
    
    @capture_exceptions(user_message="Test case selection failed", return_value=None)
    def handle_test_case_selection_wrapped(evt, selected_test_cases):
        """Wrapper for handle_test_case_selection with error handling."""
        logger.info("Handling test case selection")
        return handle_test_case_selection(evt, selected_test_cases)
    
    @capture_exceptions(user_message="Advanced filtering failed", return_value=None)
    def apply_filter_and_sort_wrapped(df, sort_columns, operator, model, manufacturer, source, overall_status, station_id, result_fail):
        """Wrapper for apply_filter_and_sort with error handling."""
        logger.info("Applying advanced filters and sorting")
        return apply_filter_and_sort(df, sort_columns, operator, model, manufacturer, source, overall_status, station_id, result_fail)
    
    @capture_exceptions(user_message="Pivot table generation failed", return_value=None)
    def generate_pivot_table_filtered_wrapped(df, rows, columns, values, aggfunc, operator, station_id, model):
        """Wrapper for generate_pivot_table_filtered with error handling."""
        logger.info("Generating filtered pivot table")
        return generate_pivot_table_filtered(df, rows, columns, values, aggfunc, operator, station_id, model)
    
    @capture_exceptions(user_message="Data processing failed", return_value=None)
    def process_data_wrapped(df, source, station_id, model_input, result_fail, flexible_search):
        """Wrapper for process_data with error handling."""
        logger.info("Processing IMEI extraction data")
        return process_data(df, source, station_id, model_input, result_fail, flexible_search)

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
            station_id_filter

        ]
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
            test_cases_df
        ]
    )

    filter_type.change(
        update_filter_visibility_wrapped,
        inputs=[filter_type],
        outputs=[operator_filter, source_filter, station_id_filter]
    )

    custom_filter_button.click(
        filter_data_wrapped,
        inputs=[
            df,
            filter_type,
            operator_filter,
            source_filter,
            station_id_filter
        ],
        outputs=[
            custom_filter_summary,
            custom_filter_chart1,
            custom_filter_chart2,
            custom_filter_chart3,
            custom_filter_df1,
            custom_filter_df2,
            custom_filter_df3,
        ]
    )

    analyze_wifi_button.click(
        analyze_wifi_errors_wrapped,
        inputs=[file_input, error_threshold],
        outputs=[summary_table, error_heatmap, pivot_table, hourly_trend_plot]
    )

    analyze_failures_button.click(
        analyze_repeated_failures_wrapped,
        inputs=[file_input, min_failures],
        outputs=[failures_summary, failures_chart, failures_df, test_case_filter]
    )

    sort_by.change(
        update_summary_chart_and_data_wrapped,
        inputs=[failures_df, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart, failures_df]
    )

    test_case_filter.change(
        update_summary_chart_and_data_wrapped,
        inputs=[failures_df, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart, failures_df]
    )

    # Add select/clear all handler
    test_case_filter.select(
        handle_test_case_selection_wrapped,
        inputs=[test_case_filter],
        outputs=[test_case_filter]
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
            advanced_result_fail_filter
        ],
        outputs=[filtered_data, filter_summary],
    )

    generate_pivot_button.click(
        generate_pivot_table_filtered_wrapped,
        inputs=[df, pivot_rows, pivot_columns, pivot_values, pivot_aggfunc, filter_operator, filter_station_id, filter_model],
        outputs=[pivot_table_output]
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