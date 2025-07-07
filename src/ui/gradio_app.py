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
from src.common.io import load_data
from src.common.logging_config import capture_exceptions, get_logger

# Import data mappings from common module
from src.common.mappings import (
    DEVICE_MAP as device_map,
    STATION_TO_MACHINE as station_to_machine,
    TEST_TO_RESULT_FAIL_MAP as test_to_result_fail_map,
)

# Import from services (new architecture)
from src.services.analysis_service import perform_analysis
from src.services.filtering_service import (
    apply_filter_and_sort,
    filter_data,
    get_unique_values,
    update_filter_dropdowns,
    update_filter_visibility,
)
from src.services.imei_extractor_service import get_test_from_result_fail, process_data
from src.services.pivot_service import (
    analyze_top_models,
    analyze_top_test_cases,
    apply_filters,
    create_excel_style_error_pivot,
    create_excel_style_failure_pivot,
    create_pivot_table,
    find_top_failing_stations,
)
from src.services.repeated_failures_service import (
    analyze_repeated_failures,
    generate_imei_commands,
    handle_test_case_selection,
    update_summary_chart_and_data,
)
from src.services.wifi_error_service import analyze_wifi_errors

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


def create_visual_summary_dashboard(summary_text):
    """
    Convert plain text summary into a beautiful visual dashboard with gradient cards and charts.

    Args:
        summary_text: Plain text summary from analysis_service

    Returns:
        HTML string with visual dashboard
    """
    if not summary_text or summary_text.strip() == "":
        return """
        <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
            <h2 style="margin: 0; font-size: 28px;">📊 Welcome to MonsterC Analysis</h2>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Upload a CSV file and click 'Perform Analysis' to begin</p>
        </div>
        """

    # Parse summary text
    lines = summary_text.strip().split("\n")
    data = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()

    # Extract numeric values
    total_tests = int(data.get("Total Tests", "0").replace(",", ""))
    valid_tests = int(data.get("Valid Tests", "0").replace(",", ""))
    success_tests = int(data.get("Success", "0").replace(",", ""))
    failures = int(data.get("Failures", "0").replace(",", ""))
    errors = int(data.get("Errors", "0").replace(",", ""))
    pass_rate = float(data.get("Pass Rate", "0").replace("%", ""))

    # Calculate additional metrics
    fail_rate = 100 - pass_rate if pass_rate > 0 else 0
    error_rate = (errors / valid_tests * 100) if valid_tests > 0 else 0
    invalid_tests = total_tests - valid_tests
    success_pct = (success_tests / valid_tests * 100) if valid_tests > 0 else 0
    test_coverage = (valid_tests / total_tests * 100) if total_tests > 0 else 0
    avg_tests_per_day = total_tests // 30 if total_tests > 0 else 0
    health_score = (
        min(100, int(pass_rate + (100 - error_rate) / 2)) if valid_tests > 0 else 0
    )

    # Determine status colors and icons
    pass_color = (
        "#10b981" if pass_rate >= 95 else "#f59e0b" if pass_rate >= 85 else "#ef4444"
    )
    pass_icon = "✅" if pass_rate >= 95 else "⚠️" if pass_rate >= 85 else "✖️"

    # Create donut chart data for mini visualization
    chart_data = f"{pass_rate},{fail_rate},{error_rate}"

    html = f"""
    <div style="padding: 20px;">
        <!-- Header Section -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
            <h2 style="color: white; margin: 0 0 10px 0; font-size: 24px; text-align: center;">
                🎯 Test Analysis Dashboard
            </h2>
            <p style="color: white; margin: 0; text-align: center; opacity: 0.9; font-size: 14px;">
                {data.get('Analysis Time', 'N/A')} | {data.get('Data Range', 'N/A')}
            </p>
        </div>

        <!-- Key Metrics Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 25px;">

            <!-- Total Tests Card -->
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Total Tests</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold;">{total_tests:,}</h3>
                        <p style="margin: 8px 0 0 0; font-size: 13px; opacity: 0.8;">
                            Valid: {valid_tests:,} | Invalid: {invalid_tests:,}
                        </p>
                    </div>
                    <div style="font-size: 54px; opacity: 1.0; filter: none; z-index: 10; position: relative;">📋</div>
                </div>
            </div>

            <!-- Pass Rate Card -->
            <div style="background: linear-gradient(135deg, {pass_color} 0%, {pass_color}dd 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 8px 20px rgba(0,0,0,0.15); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Pass Rate</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold;">{pass_rate:.1f}%</h3>
                        <div style="margin-top: 10px; background: rgba(255,255,255,0.2); border-radius: 10px; height: 8px; overflow: hidden;">
                            <div style="height: 100%; width: {pass_rate}%; background: rgba(255,255,255,0.8); border-radius: 10px; transition: width 1s ease;"></div>
                        </div>
                    </div>
                    <div style="font-size: 54px; opacity: 1.0; filter: none; z-index: 10; position: relative;">{pass_icon}</div>
                </div>
            </div>

            <!-- Success Tests Card -->
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Successful Tests</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold;">{success_tests:,}</h3>
                        <p style="margin: 8px 0 0 0; font-size: 13px; opacity: 0.8;">
                            {success_pct:.1f}% of valid tests
                        </p>
                    </div>
                    <div style="font-size: 54px; opacity: 1.0; filter: none; z-index: 10; position: relative;">✅</div>
                </div>
            </div>

            <!-- Failures Card -->
            <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 8px 20px rgba(239, 68, 68, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Failed Tests</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold;">{failures:,}</h3>
                        <p style="margin: 8px 0 0 0; font-size: 13px; opacity: 0.8;">
                            {fail_rate:.1f}% failure rate
                        </p>
                    </div>
                    <div style="font-size: 54px; opacity: 1.0; filter: none; z-index: 10; position: relative;">✖️</div>
                </div>
            </div>

            <!-- Errors Card -->
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 8px 20px rgba(245, 158, 11, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Error Tests</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold;">{errors:,}</h3>
                        <p style="margin: 8px 0 0 0; font-size: 13px; opacity: 0.8;">
                            {error_rate:.1f}% error rate
                        </p>
                    </div>
                    <div style="font-size: 54px; opacity: 1.0; filter: none; z-index: 10; position: relative;">⚠️</div>
                </div>
            </div>

            <!-- Health Score Card -->
            <div style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 8px 20px rgba(139, 92, 246, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Health Score</p>
                        <h3 style="margin: 0; font-size: 32px; font-weight: bold;">{health_score}/100</h3>
                        <div style="margin-top: 10px;">
                            <div style="display: flex; gap: 3px;">
                                {"".join(['<div style="width: 20px; height: 6px; background: rgba(255,255,255,0.8); border-radius: 3px;"></div>' if i < health_score//20 else '<div style="width: 20px; height: 6px; background: rgba(255,255,255,0.2); border-radius: 3px;"></div>' for i in range(5)])}
                            </div>
                        </div>
                    </div>
                    <div style="font-size: 54px; opacity: 1.0; filter: none; z-index: 10; position: relative;">💯</div>
                </div>
            </div>

        </div>

        <!-- Quick Insights Section -->
        <div style="background: rgba(107, 99, 246, 0.05); padding: 20px; border-radius: 12px; border: 1px solid rgba(107, 99, 246, 0.2); margin-bottom: 20px;">
            <h3 style="color: #667eea; margin: 0 0 15px 0; font-size: 18px;">🔍 Quick Insights</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="text-align: center;">
                    <p style="margin: 0; color: #999; font-size: 13px;">Test Coverage</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: #10b981;">{test_coverage:.1f}%</p>
                </div>
                <div style="text-align: center;">
                    <p style="margin: 0; color: #999; font-size: 13px;">Avg Tests/Day</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: #3b82f6;">{avg_tests_per_day:,}</p>
                </div>
                <div style="text-align: center;">
                    <p style="margin: 0; color: #999; font-size: 13px;">Quality Trend</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: {"#10b981" if pass_rate >= 90 else "#f59e0b" if pass_rate >= 80 else "#ef4444"};">
                        {"📈 Improving" if pass_rate >= 90 else "⚡ Stable" if pass_rate >= 80 else "📉 Needs Attention"}
                    </p>
                </div>
            </div>
        </div>

        <!-- Analysis Footer -->
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p style="margin: 0;">💡 Tip: Explore the charts below for detailed failure analysis by station, model, and test case</p>
        </div>
    </div>

    <style>
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        #visual-summary-dashboard > div > div {{
            animation: fadeIn 0.6s ease-out forwards;
        }}

        #visual-summary-dashboard > div > div:nth-child(2) > div {{
            animation: fadeIn 0.8s ease-out forwards;
        }}

        #visual-summary-dashboard > div > div:nth-child(2) > div:nth-child(2) {{
            animation-delay: 0.1s;
        }}

        #visual-summary-dashboard > div > div:nth-child(2) > div:nth-child(3) {{
            animation-delay: 0.2s;
        }}

        #visual-summary-dashboard > div > div:nth-child(2) > div:nth-child(4) {{
            animation-delay: 0.3s;
        }}

        #visual-summary-dashboard > div > div:nth-child(2) > div:nth-child(5) {{
            animation-delay: 0.4s;
        }}

        #visual-summary-dashboard > div > div:nth-child(2) > div:nth-child(6) {{
            animation-delay: 0.5s;
        }}

        #visual-summary-dashboard > div > div > div:hover {{
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.2) !important;
        }}
    </style>
    """

    return html


# JavaScript for handling row clicks and command generation
command_generation_js = """
<script>
window.monsterCData = window.monsterCData || {};

// Add a function to poll for changes and trigger command generation
window.checkForCommandGeneration = function() {
    const modelInput = document.querySelector('#hidden_model textarea');
    const stationInput = document.querySelector('#hidden_station textarea');
    const testCaseInput = document.querySelector('#hidden_test_case textarea');

    if (modelInput && stationInput && testCaseInput) {
        const model = modelInput.value;
        const station = stationInput.value;
        const testCase = testCaseInput.value;

        // Check if we have pending data and inputs match
        if (window.monsterCData.pendingGeneration &&
            model === window.monsterCData.pendingGeneration.model &&
            station === window.monsterCData.pendingGeneration.station &&
            testCase === window.monsterCData.pendingGeneration.testCase) {

            console.log('Values match pending generation, triggering button click...');
            const button = document.querySelector('#command_gen_button button');
            if (button) {
                button.click();
                window.monsterCData.pendingGeneration = null; // Clear pending

                // Also try to trigger change event on model input as backup
                setTimeout(() => {
                    if (modelInput.value) {
                        modelInput.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log('Triggered change event on model input');
                    }
                }, 100);
            }
        }
    }
};

// Set up periodic check
setInterval(window.checkForCommandGeneration, 250);

// Add direct backend trigger function
window.triggerCommandGeneration = function(model, station, testCase) {
    console.log('Direct trigger called:', { model, station, testCase });

    // Find Gradio app and trigger directly
    if (window.gradio_config && window.gradio_config.fn) {
        console.log('Found gradio_config.fn');
    }

    // Look for the button and manually trigger its event
    const button = document.querySelector('#command_gen_button button');
    if (button) {
        // Find if button has any event data attached
        const events = button._events || button.__events || getEventListeners?.(button);
        console.log('Button event data:', events);
    }
};

window.handleFailureRowClick = function(model, stationId, testCase, rowIdx) {
    console.log('=== handleFailureRowClick called ===');
    console.log('Parameters:', { model, stationId, testCase, rowIdx });

    // Try multiple selectors to find the components
    const findTextarea = (id) => {
        return document.querySelector(`#${id} textarea`) ||
               document.querySelector(`#${id} input`) ||
               document.querySelector(`[id="${id}"] textarea`) ||
               document.querySelector(`[id="${id}"] input`);
    };

    const findButton = (id) => {
        return document.querySelector(`#${id} button`) ||
               document.querySelector(`[id="${id}"] button`) ||
               document.querySelector(`#${id}`);
    };

    // Update the hidden Gradio components
    const modelInput = findTextarea('js_model');
    const stationInput = findTextarea('js_station');
    const testCaseInput = findTextarea('js_test_case');
    const triggerButton = findButton('js_trigger');

    console.log('Found components:', {
        modelInput: !!modelInput,
        stationInput: !!stationInput,
        testCaseInput: !!testCaseInput,
        triggerButton: !!triggerButton
    });

    if (modelInput && stationInput && testCaseInput && triggerButton) {
        // Set the values
        modelInput.value = model;
        stationInput.value = stationId;
        testCaseInput.value = testCase;

        // Force Gradio to recognize the change
        const inputEvent = new Event('input', { bubbles: true });
        const changeEvent = new Event('change', { bubbles: true });

        modelInput.dispatchEvent(inputEvent);
        stationInput.dispatchEvent(inputEvent);
        testCaseInput.dispatchEvent(inputEvent);

        modelInput.dispatchEvent(changeEvent);
        stationInput.dispatchEvent(changeEvent);
        testCaseInput.dispatchEvent(changeEvent);

        console.log('Values set, triggering button click...');

        // Small delay then click the trigger button
        setTimeout(() => {
            triggerButton.click();
            console.log('Button clicked');
        }, 200);
    } else {
        console.error('Could not find hidden components:', {
            modelInput: modelInput?.outerHTML?.substring(0, 50),
            stationInput: stationInput?.outerHTML?.substring(0, 50),
            testCaseInput: testCaseInput?.outerHTML?.substring(0, 50),
            triggerButton: triggerButton?.outerHTML?.substring(0, 50)
        });

        // Try to find any component with these IDs
        console.log('All js_model elements:', document.querySelectorAll('[id*="js_model"]'));
        console.log('All js_trigger elements:', document.querySelectorAll('[id*="js_trigger"]'));

        // Fallback: try the counter approach
        console.log('Trying alternative counter approach...');
        window.triggerCommandGeneration(model, stationId, testCase);
    }
};

// Monitor for command UI generation and move it to the injection point
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        // Check if command UI was added to the container
        const container = document.getElementById('command_generation_container');
        const commandUI = container ? container.querySelector('#command-ui') : null;
        const injectionPoint = document.getElementById('command_generation_injection_point');

        if (commandUI && injectionPoint && !injectionPoint.contains(commandUI)) {
            console.log('Moving command UI to injection point');
            // Move the command UI to the injection point
            injectionPoint.innerHTML = '';
            injectionPoint.appendChild(commandUI);
        }
    });
});

// Start observing the command generation container
setTimeout(() => {
    const container = document.getElementById('command_generation_container');
    if (container) {
        observer.observe(container, { childList: true, subtree: true });
    }
}, 1000);

// Debug: Check if handleFailureRowClick is available
console.log('handleFailureRowClick defined:', typeof window.handleFailureRowClick);

// Periodically check if the function is being called
setInterval(() => {
    const rows = document.querySelectorAll('tr[onclick*="handleFailureRowClick"]');
    if (rows.length > 0 && !window.debugRowsFound) {
        console.log('Found clickable rows:', rows.length);
        window.debugRowsFound = true;
    }
}, 2000);

// Store row data globally
window.selectedRowData = null;

// Alternative approach: store data and trigger via counter
window.triggerCommandGeneration = function(model, station, testCase) {
    window.selectedRowData = { model, station, testCase };

    // Find the counter and increment it
    const counter = document.querySelector('#js_counter input') ||
                   document.querySelector('#js_counter textarea');
    if (counter) {
        const currentValue = parseInt(counter.value) || 0;
        counter.value = currentValue + 1;
        counter.dispatchEvent(new Event('input', { bubbles: true }));
        counter.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('Counter incremented to:', counter.value);
    }
};

// Add CSS for hover effects
const style = document.createElement('style');
style.textContent = `
    #command-ui button:hover {
        background: #5a5fb8 !important;
        transform: scale(1.05);
        transition: all 0.2s ease;
    }

    #command-ui pre {
        padding-right: 80px;
    }

    #command_generation_container {
        transition: all 0.3s ease;
    }

    /* Keep hidden components technically visible but minimal */
    #hidden_components_row {
        position: fixed !important;
        bottom: 5px !important;
        right: 5px !important;
        width: 10px !important;
        height: 10px !important;
        opacity: 0.001 !important;
        overflow: hidden !important;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
</script>
"""

# Gradio UI Definition
with gr.Blocks(
    theme=gr.themes.Soft(),
    head=command_generation_js,
    css="""
    /* Keep hidden components technically visible but minimal */
    #hidden_components_row {
        position: fixed !important;
        bottom: 5px !important;
        right: 5px !important;
        width: 10px !important;
        height: 10px !important;
        opacity: 0.001 !important;
        pointer-events: none !important;
        overflow: hidden !important;
    }

    #hidden_components_row > * {
        width: 1px !important;
        height: 1px !important;
        font-size: 1px !important;
    }

    /* Allow the button to be clickable even when hidden */
    #command_gen_button {
        pointer-events: auto !important;
    }

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

    /* Command generation section styling */
    .command-generation-section {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    /* Copy button hover effect */
    .copy-button {
        transition: all 0.3s ease !important;
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        border: none !important;
        cursor: pointer !important;
    }

    .copy-button:hover {
        transform: scale(1.1) !important;
        box-shadow: 0 4px 12px rgba(107, 99, 246, 0.4) !important;
    }

    /* Command box enhanced styling */
    .command-box textarea {
        background: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(107, 99, 246, 0.3) !important;
        color: rgba(255, 255, 255, 0.95) !important;
        font-size: 13px !important;
        transition: all 0.3s ease !important;
    }

    .command-box textarea:hover {
        border-color: rgba(107, 99, 246, 0.5) !important;
        background: rgba(0, 0, 0, 0.4) !important;
    }

    /* Selected row highlight effect */
    .gradio-dataframe tbody tr.selected {
        background: linear-gradient(90deg, rgba(107, 99, 246, 0.2) 0%, rgba(107, 99, 246, 0.1) 100%) !important;
        box-shadow: 0 2px 8px rgba(107, 99, 246, 0.2);
    }
""",
) as demo:
    gr.Markdown("# CSV Analysis Tool")

    with gr.Row():
        file_input = gr.File(label="Upload CSV File")
        # Notification for auto-formatting
        format_notification = gr.Markdown(value="", visible=False)

    df = gr.State()  # State to hold the DataFrame

    with gr.Tabs():
        with gr.TabItem("Analysis Results"):
            with gr.Row():
                analyze_button = gr.Button("Perform Analysis", variant="primary")

            # Visual summary dashboard section
            with gr.Row():
                analysis_summary = gr.HTML(
                    value="""
                    <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                        <h2 style="margin: 0; font-size: 28px;">📊 Welcome to MonsterC Analysis</h2>
                        <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Upload a CSV file and click 'Perform Analysis' to begin</p>
                    </div>
                    """,
                    elem_id="visual-summary-dashboard",
                )

            # Hidden textbox to store raw summary data for processing
            analysis_summary_data = gr.Textbox(visible=False)

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
                    value=["All"],
                    interactive=True,
                    multiselect=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )
                source_filter = gr.Dropdown(
                    label="Source",
                    choices=["All"],
                    value=["All"],
                    interactive=True,
                    multiselect=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )
                station_id_filter = gr.Dropdown(
                    label="Station ID",
                    choices=["All"],
                    value=["All"],
                    interactive=True,
                    multiselect=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )

            with gr.Row():
                custom_filter_button = gr.Button("Filter Data")

            # Beautiful floating card summary with HTML component
            with gr.Row():
                custom_filter_summary = gr.HTML(
                    value="""
                    <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #06beb6 0%, #48b1bf 100%); border-radius: 15px; color: white;">
                        <h2 style="margin: 0; font-size: 28px;">🔍 Custom Data Filtering</h2>
                        <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Select filters above and click 'Filter Data' to analyze</p>
                    </div>
                    """,
                    elem_id="custom_filter_summary",
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

        with gr.TabItem("Repeated Failures Analysis"):
            with gr.Row():
                min_failures = gr.Slider(
                    minimum=2, maximum=10, value=4, step=1, label="Minimum Failures"
                )
                analyze_failures_button = gr.Button("Analyze Repeated Failures")

            # Add sorting controls
            with gr.Row():
                sort_by = gr.Dropdown(
                    choices=[
                        "TC Count",
                        "Model",
                        "Station ID",
                        "Operator",
                        "Test Case",
                        "Model Code",
                    ],
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
                failures_summary = gr.HTML(
                    value="""
                    <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); border-radius: 15px; color: white;">
                        <h2 style="margin: 0; font-size: 28px;">🔍 Repeated Failures Analysis</h2>
                        <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Click 'Analyze Repeated Failures' to begin</p>
                    </div>
                    """,
                    label="Repeated Failures Summary",
                )

            # Command Generation HTML - Will be populated dynamically between header and table
            command_generation_html = gr.HTML(
                value="", elem_id="command_generation_container"
            )

            # Hidden state to store the full dataframe for command generation
            full_df_state = gr.State()

            # State to store the repeated failures dataframe for filtering
            repeated_failures_state = gr.State()

            # State to store selected row data
            selected_row_state = gr.State(
                {"model": None, "station": None, "test_case": None}
            )

            # Hidden components for JavaScript interaction
            with gr.Row(visible=False):
                js_model = gr.Textbox(value="", elem_id="js_model", interactive=True)
                js_station = gr.Textbox(
                    value="", elem_id="js_station", interactive=True
                )
                js_test_case = gr.Textbox(
                    value="", elem_id="js_test_case", interactive=True
                )
                js_trigger = gr.Button("Trigger", elem_id="js_trigger")
                js_counter = gr.Number(value=0, elem_id="js_counter")

            with gr.Row():
                failures_chart = gr.Plot(label="Repeated Failures Chart")

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
        user_message="Failed to load and update data", return_value=[None] * 17
    )
    def load_and_update_wrapped(file, progress=gr.Progress()):
        """Load CSV file and update all filter dropdowns."""
        logger.info(f"Loading file: {getattr(file, 'name', 'unknown')}")

        # Show initial progress
        progress(0.1, desc="Reading CSV file...")

        # Load the data with auto-formatting disabled first to check if formatting is needed
        df_raw = load_data(file, auto_format=False)

        if df_raw is None or df_raw.empty:
            progress(1.0, desc="File is empty or invalid")
            # Return empty values for all outputs
            empty_dropdown = gr.update(choices=["All"], value="All")
            empty_dropdown_multi = gr.update(choices=["All"], value=["All"])
            return [
                None,  # df
                empty_dropdown,  # source
                empty_dropdown,  # station_id
                empty_dropdown,  # model
                gr.update(choices=[]),  # result_fail
                empty_dropdown,  # advanced_operator
                empty_dropdown,  # advanced_model
                empty_dropdown,  # advanced_manufacturer
                empty_dropdown,  # advanced_source
                empty_dropdown,  # advanced_overall_status
                empty_dropdown,  # advanced_station_id
                gr.update(choices=[]),  # advanced_result_fail
                empty_dropdown_multi,  # operator_filter
                empty_dropdown_multi,  # source_filter
                empty_dropdown_multi,  # station_id_filter
                empty_dropdown,  # interactive_operator_filter
                gr.update(value="", visible=False),  # notification
            ]

        # Check if formatting is needed
        original_cols = len(df_raw.columns)
        target_columns = [
            "Operator",
            "Date Time",
            "Date",
            "Hour",
            "Model",
            "IMEI",
            "App version",
            "Manufacturer",
            "OS",
            "OS name",
            "Source",
            "RADI app version",
            "Overall status",
            "Station ID",
            "result_FAIL",
            "LCD Grading 1",
            "error_code",
            "error_message",
            "BlindUnlockPerformed",
        ]

        needs_formatting = original_cols > len(target_columns) or not all(
            col in df_raw.columns for col in target_columns
        )

        if needs_formatting:
            progress(0.3, desc="Detected raw format. Analyzing columns...")
            progress(
                0.5,
                desc=f"Auto-formatting: Converting {original_cols} columns to {len(target_columns)} required columns...",
            )

            # Now load with auto-formatting
            df = load_data(file, auto_format=True)

            progress(0.7, desc="Formatting complete! Processing data...")
            notification_msg = f"✅ Auto-formatting applied: Reduced from {original_cols} to {len(target_columns)} columns"
        else:
            progress(0.5, desc="CSV already in correct format. Processing data...")
            df = df_raw
            notification_msg = "✅ CSV loaded successfully - no formatting needed"

        progress(0.8, desc="Updating filters...")

        if df is None or df.empty:
            # Return empty values for all outputs - need to return proper dropdown updates
            empty_dropdown = gr.update(choices=["All"], value="All")
            empty_dropdown_multi = gr.update(choices=["All"], value=["All"])
            return [
                None,  # df
                empty_dropdown,  # source
                empty_dropdown,  # station_id
                empty_dropdown,  # model
                gr.update(choices=[]),  # result_fail
                empty_dropdown,  # advanced_operator
                empty_dropdown,  # advanced_model
                empty_dropdown,  # advanced_manufacturer
                empty_dropdown,  # advanced_source
                empty_dropdown,  # advanced_overall_status
                empty_dropdown,  # advanced_station_id
                gr.update(choices=[]),  # advanced_result_fail
                empty_dropdown_multi,  # operator_filter
                empty_dropdown_multi,  # source_filter
                empty_dropdown_multi,  # station_id_filter
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

        progress(1.0, desc="Complete!")

        # Return all the updated values (17 total including notification)
        # For dropdowns, we need to return gr.update(choices=...) to update the choices
        return [
            df,  # 1. The loaded dataframe
            gr.update(choices=sources, value="All"),  # 2. IMEI Extractor: Source
            gr.update(
                choices=station_ids, value="All"
            ),  # 3. IMEI Extractor: Station ID
            gr.update(choices=models, value="All"),  # 4. IMEI Extractor: Model(s)
            gr.update(choices=result_fails),  # 5. IMEI Extractor: Result Fail
            gr.update(choices=operators, value="All"),  # 6. Advanced Filter: Operator
            gr.update(choices=models, value="All"),  # 7. Advanced Filter: Model
            gr.update(
                choices=manufacturers, value="All"
            ),  # 8. Advanced Filter: Manufacturer
            gr.update(choices=sources, value="All"),  # 9. Advanced Filter: Source
            gr.update(
                choices=overall_statuses, value="All"
            ),  # 10. Advanced Filter: Overall Status
            gr.update(
                choices=station_ids, value="All"
            ),  # 11. Advanced Filter: Station ID
            gr.update(choices=result_fails),  # 12. Advanced Filter: Result Fail
            gr.update(choices=operators, value=["All"]),  # 13. Custom Filter: Operator
            gr.update(choices=sources, value=["All"]),  # 14. Custom Filter: Source
            gr.update(
                choices=station_ids, value=["All"]
            ),  # 15. Custom Filter: Station ID
            gr.update(
                choices=operators, value="All"
            ),  # 16. Interactive Pivot: Operator
            gr.update(value=notification_msg, visible=True),  # 17. Notification
        ]

    @capture_exceptions(user_message="Analysis failed", return_value=None)
    def perform_analysis_wrapped(csv_file):
        """Wrapper for perform_analysis with error handling."""
        logger.info("Performing CSV analysis")
        # Convert file to DataFrame before passing to service
        df = load_data(csv_file)
        results = perform_analysis(df)

        # If analysis succeeded, create visual dashboard from summary text
        if results and len(results) > 0 and results[0]:
            summary_text = results[0]
            visual_html = create_visual_summary_dashboard(summary_text)
            # Return visual HTML as first element, raw summary as hidden element, then rest
            return (visual_html, summary_text) + results[1:]

        return results

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
        user_message="Repeated failures analysis failed",
        return_value=(None, None, None, None, None),
    )
    def analyze_repeated_failures_wrapped(file, min_failures):
        """Wrapper for analyze_repeated_failures with error handling."""
        logger.info(f"Analyzing repeated failures with minimum: {min_failures}")
        (
            summary,
            fig,
            dropdown,
            original_df,
            repeated_failures_df,
        ) = analyze_repeated_failures(file, min_failures)
        # Return all values including both dataframes
        return summary, fig, dropdown, original_df, repeated_failures_df

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

    @capture_exceptions(
        user_message="Command generation failed",
        return_value="<div style='color: red;'>Failed to generate commands</div>",
    )
    def generate_imei_commands_wrapped(full_df, model, station_id, test_case):
        """Wrapper for generate_imei_commands with error handling."""
        logger.info("=" * 60)
        logger.info("IMEI COMMAND GENERATION TRIGGERED!")
        logger.info(f"Model: {model}")
        logger.info(f"Station ID: {station_id}")
        logger.info(f"Test Case: {test_case}")
        logger.info(f"Full DF type: {type(full_df)}, is None: {full_df is None}")
        logger.info("=" * 60)

        # Add immediate response to show function was called
        import time

        logger.info(f"Function called at: {time.time()}")

        if not model or not station_id or not test_case:
            logger.warning(
                f"Missing parameters: model={model}, station_id={station_id}, test_case={test_case}"
            )
            return "<div style='color: red;'>Missing parameters for command generation</div>"

        if full_df is None:
            logger.error("Full dataframe is None")
            return "<div style='color: red;'>No data available for command generation. Please analyze repeated failures first.</div>"

        result = generate_imei_commands(full_df, model, station_id, test_case)
        logger.info(f"Command generation result length: {len(result) if result else 0}")
        return result

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
            operator_filter,
            source_filter,
            station_id_filter,
            interactive_operator_filter,  # Interactive pivot filter
            format_notification,  # Notification for auto-formatting
        ],
    )

    analyze_button.click(
        fn=perform_analysis_wrapped,
        inputs=[file_input],
        outputs=[
            analysis_summary,
            analysis_summary_data,
            overall_status_chart,
            stations_chart,
            models_chart,
            test_cases_chart,
            stations_df,
            models_df,
            test_cases_df,
        ],
    )

    @capture_exceptions(
        user_message="Failed to update station dropdown",
        return_value=gr.update(choices=["All"], value=["All"]),
    )
    def update_station_dropdown_based_on_operators(df, operators_selected):
        """Update station ID dropdown based on selected operators."""
        if df is None or df.empty:
            return gr.update(choices=["All"], value=["All"])

        # If "All" is selected or nothing is selected, show all stations
        if (
            not operators_selected
            or operators_selected == ["All"]
            or "All" in operators_selected
        ):
            station_ids = ["All"] + sorted(df["Station ID"].dropna().unique().tolist())
        else:
            # Filter dataframe by selected operators and get unique station IDs
            filtered_df = df[df["Operator"].isin(operators_selected)]
            station_ids = ["All"] + sorted(
                filtered_df["Station ID"].dropna().unique().tolist()
            )

        return gr.update(choices=station_ids, value=["All"], multiselect=True)

    filter_type.change(
        update_filter_visibility_wrapped,
        inputs=[filter_type],
        outputs=[operator_filter, source_filter, station_id_filter],
    )

    # Add handler to update station IDs when operators are selected
    operator_filter.change(
        update_station_dropdown_based_on_operators,
        inputs=[df, operator_filter],
        outputs=[station_id_filter],
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
        outputs=[
            failures_summary,
            failures_chart,
            test_case_filter,
            full_df_state,
            repeated_failures_state,
        ],
    ).then(
        lambda: "",  # Clear the command generation HTML
        outputs=[command_generation_html],
    )

    # Add select/clear all handler
    test_case_filter.select(
        handle_test_case_selection_wrapped,
        inputs=[test_case_filter],
        outputs=[test_case_filter],
    )

    # Add change handler to update the chart when test cases are filtered
    test_case_filter.change(
        update_summary_chart_and_data_wrapped,
        inputs=[repeated_failures_state, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart],
    )

    # Add change handler for sort_by dropdown
    sort_by.change(
        update_summary_chart_and_data_wrapped,
        inputs=[repeated_failures_state, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart],
    )

    # JavaScript event handling for HTML table row clicks
    def handle_row_click_event(model, station, test_case, full_df):
        """Handle row click from JavaScript event"""
        logger.info(f"Row clicked: {model}, {station}, {test_case}")
        if model and station and test_case and full_df is not None:
            commands_html = generate_imei_commands_wrapped(
                full_df, model, station, test_case
            )
            # Wrap the commands in a script to inject them into the right place
            return f"""
            {commands_html}
            <script>
                // Inject the command UI into the proper location
                setTimeout(() => {{
                    const commandHtml = document.getElementById('command-ui');
                    if (commandHtml) {{
                        const injectionPoint = document.getElementById('command_generation_injection_point');
                        if (injectionPoint) {{
                            injectionPoint.innerHTML = '';
                            injectionPoint.appendChild(commandHtml);
                        }}
                    }}
                }}, 100);
            </script>
            """
        return ""

    # Connect the JavaScript trigger
    js_trigger.click(
        handle_row_click_event,
        inputs=[js_model, js_station, js_test_case, full_df_state],
        outputs=[command_generation_html],
    )

    # Set up polling mechanism to check for row clicks
    polling_state = gr.State({"last_check": 0})

    def poll_for_row_clicks(polling_state, full_df):
        """Check if a row was clicked and generate commands if so"""
        import time

        current_time = time.time()

        # Only check every 0.5 seconds
        if current_time - polling_state.get("last_check", 0) < 0.5:
            return gr.update(), polling_state

        polling_state["last_check"] = current_time

        # JavaScript to check for selected row
        check_js = """
        <script>
        (function() {
            const data = window.selectedRowData;
            if (data && !window.processingCommand) {
                window.processingCommand = true;
                console.log('Processing row click:', data);

                // Call the command generation
                window.onFailureRowClick = function(model, station, testCase) {
                    // Set values in hidden inputs
                    const setInput = (id, value) => {
                        const elem = document.querySelector(`#${id} textarea`) || document.querySelector(`#${id} input`);
                        if (elem) {
                            elem.value = value;
                            elem.dispatchEvent(new Event('input', { bubbles: true }));
                            elem.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    };

                    setInput('js_model', model);
                    setInput('js_station', station);
                    setInput('js_test_case', testCase);

                    // Click the trigger button
                    setTimeout(() => {
                        const btn = document.querySelector('#js_trigger button');
                        if (btn) {
                            btn.click();
                            window.selectedRowData = null;
                            window.processingCommand = false;
                        }
                    }, 200);
                };

                // Trigger the handler
                if (window.onFailureRowClick) {
                    window.onFailureRowClick(data.model, data.station, data.testCase);
                }
            }
        })();
        </script>
        """

        return check_js, polling_state

    # Set up timer to poll every 500ms
    timer = gr.Timer(0.5)
    timer.tick(
        poll_for_row_clicks,
        inputs=[polling_state, full_df_state],
        outputs=[command_generation_html, polling_state],
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
