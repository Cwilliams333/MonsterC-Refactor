#!/usr/bin/env python3
"""
Tabulator.js Frontend for Collapsible Pivot Tables.

This creates a separate Flask app that serves a Tabulator.js interface
with native collapsible groups - exactly what we need!
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from flask import Flask, jsonify, render_template_string

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))  # Also add project root

from common.logging_config import get_logger  # noqa: E402
from dash_pivot_app import sort_stations_by_total_errors  # noqa: E402

# Configure logging
logger = get_logger(__name__)

# Global variable to store device failure counts for accurate totals
device_failure_counts = {}

# Global dict to hold data paths passed from Gradio
DATA_PATHS = {}

# Initialize Flask app
app = Flask(__name__)


def load_device_failure_counts():
    """Load device failure counts for accurate totals."""
    global device_failure_counts
    device_counts_file = "/tmp/monsterc_device_counts.json"
    try:
        with open(device_counts_file, "r") as f:
            device_failure_counts = json.load(f)
            logger.info(f"📊 Loaded device failure counts: {device_failure_counts}")
    except FileNotFoundError:
        logger.warning(f"Device counts file not found: {device_counts_file}")
        device_failure_counts = {}


def create_concatenated_failure_pivot(automation_data_file: str = None) -> pd.DataFrame:
    """
    Create pivot table that preserves concatenated test cases.

    Unlike create_excel_style_failure_pivot(), this does NOT split
    comma-separated test cases like "Camera Pictures,Camera Flash".
    """
    try:
        # Use provided path or fall back to default
        if automation_data_file is None:
            automation_data_file = "/tmp/monsterc_automation_data.json"

        if not os.path.exists(automation_data_file):
            logger.warning(
                "No raw automation data found, cannot create concatenated pivot"
            )
            return pd.DataFrame()

        # Load raw automation failures
        with open(automation_data_file, "r") as f:
            automation_data = json.load(f)

        automation_df = pd.DataFrame(automation_data)
        logger.info(f"📊 Loaded raw automation data: {automation_df.shape}")

        # Apply same filtering as main workflow (but WITHOUT splitting result_FAIL)
        filtered_df = automation_df[automation_df["result_FAIL"].notna()]
        filtered_df = filtered_df[filtered_df["result_FAIL"].str.strip() != ""]

        logger.info("🔗 Preserving concatenated test cases (no split/explode)")
        logger.info(f"DataFrame shape: {filtered_df.shape}")

        # Create pivot table with CONCATENATED result_FAIL values preserved
        pivot_result = pd.pivot_table(
            filtered_df,
            index=[
                "result_FAIL",
                "Model",
            ],  # Hierarchical rows - but result_FAIL stays concatenated!
            columns=["Station ID"],  # Columns like Excel
            values="Operator",  # Need something to count
            aggfunc="count",  # Count occurrences
            fill_value=0,  # Fill missing with 0
        )

        # Clean up column names and reset index
        pivot_result.columns.name = None
        pivot_result = pivot_result.reset_index()

        logger.info(f"✅ Created concatenated pivot table: {pivot_result.shape}")
        logger.info(f"📊 Sample test cases: {pivot_result['result_FAIL'].unique()[:5]}")

        return pivot_result

    except Exception as e:
        logger.error(f"Error creating concatenated pivot: {e}")
        return pd.DataFrame()


def transform_pivot_to_tabulator_tree_hybrid(
    original_pivot_df: pd.DataFrame, concatenated_pivot_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """HYBRID: Use original pivot for correct totals but concatenated for structure."""
    if original_pivot_df.empty:
        return []

    # Sort stations by total failures from ORIGINAL pivot (correct totals!)
    station_cols = sort_stations_by_total_errors(original_pivot_df)
    logger.info(f"🔥 Station columns from ORIGINAL pivot: {station_cols[:5]}")

    tabulator_data: List[Dict[str, Any]] = []

    # CREATE TOTAL ROW using ORIGINAL pivot totals
    total_row = {
        "hierarchy": "📊 TOTAL FAILURES",
        "isTotal": True,
        "expand_icon": False,
    }

    # Add station totals using device failure counts for accuracy
    global device_failure_counts
    max_value = 0
    max_station = ""
    grand_total_sum = 0

    # Debug: Log available device counts vs pivot columns
    logger.info(
        f"📊 Available device counts: {list(device_failure_counts.keys()) if device_failure_counts else 'None'}"
    )
    logger.info(f"📊 Station columns: {station_cols}")

    for col in station_cols:
        # Use device failure counts if available, otherwise fall back to pivot counts
        if device_failure_counts and col in device_failure_counts:
            total_value = device_failure_counts[col]
            logger.info(f"✅ Using device count for {col}: {total_value}")
        else:
            total_value = int(original_pivot_df[col].sum())
            logger.warning(
                f"⚠️ Using pivot count for {col}: {total_value} (device counts not available)"
            )

        total_row[col] = total_value
        grand_total_sum += total_value
        if total_value > max_value:
            max_value = total_value
            max_station = col

    # Add Grand Total column (sum of all stations horizontally)
    total_row["Grand_Total"] = grand_total_sum

    logger.info(f"🎯 Tabulator Grand total calculated: {grand_total_sum}")
    logger.info(
        f"🎯 Expected device total: {sum(device_failure_counts.values()) if device_failure_counts else 'N/A'}"
    )

    logger.info(
        f"🎯 CORRECT TOTALS - radi154: {total_row.get('radi154', 'N/A')}, "
        f"radi152: {total_row.get('radi152', 'N/A')}"
    )
    logger.info(f"🎯 Heat map max: {max_value} at {max_station}")
    logger.info(f"🎯 Grand Total: {grand_total_sum}")

    total_row["_maxValue"] = max_value
    total_row["_maxStation"] = max_station
    tabulator_data.append(total_row)

    # Group by CONCATENATED test cases from concatenated pivot
    grouped = concatenated_pivot_df.groupby("result_FAIL")

    # Sort test case groups by Grand Total (sum of all station failures)
    test_case_totals = {}
    for test_case_string, group in grouped:
        test_case_grand_total = sum(
            group[col].sum() for col in station_cols if col in group.columns
        )
        test_case_totals[test_case_string] = test_case_grand_total

    sorted_test_cases = sorted(
        test_case_totals.items(), key=lambda x: x[1], reverse=True
    )
    logger.info(
        f"📊 Concatenated test case groups: "
        f"{[tc for tc, _ in sorted_test_cases[:5]]}"
    )

    for test_case_string, test_case_total in sorted_test_cases:
        group = grouped.get_group(test_case_string)

        # Create parent row for concatenated test case
        parent_row: Dict[str, Any] = {
            "hierarchy": f"📁 {test_case_string}",
            "isGroup": True,
            "_children": [],
        }

        # Add aggregated station values and calculate Grand Total
        test_case_grand_total = 0
        for col in station_cols:
            if col in group.columns:
                station_value = int(group[col].sum())
                parent_row[col] = station_value
                test_case_grand_total += station_value
            else:
                parent_row[col] = 0

        # Add Grand Total for this test case (sum of all stations)
        parent_row["Grand_Total"] = test_case_grand_total

        # Create child rows (models)
        group_sorted = group.copy()
        group_sorted["test_case_model_failures"] = group_sorted[
            [col for col in station_cols if col in group_sorted.columns]
        ].sum(axis=1)
        group_sorted = group_sorted.sort_values(
            "test_case_model_failures", ascending=False
        )

        for _, row in group_sorted.iterrows():
            child_row = {"hierarchy": f"  └─ {row['Model']}", "isModel": True}

            # Add station values and calculate Grand Total for model
            model_grand_total = 0
            for col in station_cols:
                if col in row.index:
                    station_value = int(row[col]) if pd.notna(row[col]) else 0
                    child_row[col] = station_value
                    model_grand_total += station_value
                else:
                    child_row[col] = 0

            # Add Grand Total for this model
            child_row["Grand_Total"] = model_grand_total

            parent_row["_children"].append(child_row)

        tabulator_data.append(parent_row)

    logger.info(f"✅ Hybrid transformation complete: {len(tabulator_data)} rows")
    return tabulator_data


def transform_pivot_to_tabulator_tree(pivot_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Transform pivot data to Tabulator tree format with collapsible test case groups.

    IMPORTANT: Each unique result_FAIL string (including concatenated test cases like
    "Camera Pictures,Camera Flash") is treated as ONE test case group.

    Creates the exact structure you want:
    📁 Camera Pictures,Camera Flash (parent - collapsible)
      └─ iPhone14ProMax (child)
      └─ iPhone13ProMax (child)
    """
    if pivot_df.empty:
        return []

    # Sort stations by total failures (money columns first!)
    station_cols = sort_stations_by_total_errors(pivot_df)
    logger.info(f"🔥 Station columns sorted by failures: {station_cols[:5]}")

    tabulator_data: List[Dict[str, Any]] = []

    # CREATE TOTAL ROW (always expanded) - USE ORIGINAL PIVOT TOTALS
    total_row = {
        "hierarchy": "📊 TOTAL FAILURES",
        "isTotal": True,
        "expand_icon": False,  # No expand icon for total
    }

    # Add station totals and track max value for heat mapping
    max_value = 0
    max_station = ""
    for col in station_cols:
        total_value = int(pivot_df[col].sum())  # USE ORIGINAL PIVOT FOR CORRECT TOTALS
        total_row[col] = total_value
        if total_value > max_value:
            max_value = total_value
            max_station = col

    logger.info(f"🎯 CORRECT TOTALS - Max: {max_value} at {max_station}")
    logger.info(
        f"🎯 Total row values: radi154={total_row.get('radi154', 'N/A')}, "
        f"radi152={total_row.get('radi152', 'N/A')}"
    )

    # Mark the maximum value for heat map highlighting
    total_row["_maxValue"] = max_value
    total_row["_maxStation"] = max_station

    tabulator_data.append(total_row)

    # Group by EXACT result_FAIL string (including concatenated test cases)
    # Each unique string like "Camera Pictures,Camera Flash" becomes one group
    grouped = pivot_df.groupby("result_FAIL")

    # Sort test case groups by total failures (hottest first!)
    test_case_totals = {}
    for test_case_string, group in grouped:
        test_case_total = sum(group[col].sum() for col in station_cols)
        test_case_totals[test_case_string] = test_case_total

    sorted_test_cases = sorted(
        test_case_totals.items(), key=lambda x: x[1], reverse=True
    )
    logger.info("📊 Test case groups by total failures:")
    for test_case, total in sorted_test_cases[:5]:
        logger.info(f"  - '{test_case}': {total} failures")

    for test_case_string, test_case_total in sorted_test_cases:
        group = grouped.get_group(test_case_string)

        # Create parent row (test case group) with aggregated totals
        parent_row: Dict[str, Any] = {
            "hierarchy": f"📁 {test_case_string}",
            "isGroup": True,
            "_children": [],  # This is where Tabulator expects child rows!
        }

        # Add aggregated station values for this test case group
        for col in station_cols:
            parent_row[col] = int(group[col].sum())

        # Create child rows (models) sorted by failure count within this test case group
        group_sorted = group.copy()
        group_sorted["test_case_model_failures"] = group_sorted[station_cols].sum(
            axis=1
        )
        group_sorted = group_sorted.sort_values(
            "test_case_model_failures", ascending=False
        )

        for _, row in group_sorted.iterrows():
            child_row = {"hierarchy": f"  └─ {row['Model']}", "isModel": True}

            # Add individual station values
            for col in station_cols:
                child_row[col] = int(row[col]) if pd.notna(row[col]) else 0

            parent_row["_children"].append(child_row)

        tabulator_data.append(parent_row)

    logger.info(
        f"✅ Created {len(tabulator_data)} parent rows with collapsible children"
    )
    logger.info(f"🎯 Heat map: Max value {max_value} at station {max_station}")
    return tabulator_data


def create_tabulator_columns(station_cols: List[str]) -> List[Dict[str, Any]]:
    """Create Tabulator column definitions with proper formatting."""
    columns = []

    # Hierarchy column (with tree controls)
    columns.append(
        {
            "title": "Test Case → Model",
            "field": "hierarchy",
            "width": 350,
            "responsive": 0,  # Never hide this column
            "formatter": "html",  # Allow HTML content (for icons)
        }
    )

    # Station columns (sorted by failure count)
    for col in station_cols:
        columns.append(
            {
                "title": col,
                "field": col,
                "width": 100,
                "hozAlign": "center",
                # Note: Formatter and cellClick functions will be handled in JavaScript
            }
        )

    return columns


# HTML template for Tabulator interface
TABULATOR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 MonsterC - Collapsible Automation Failures</title>
    <link href="https://unpkg.com/tabulator-tables@6.3.0/dist/css/tabulator.min.css" rel="stylesheet">
    <script type="text/javascript" src="https://unpkg.com/tabulator-tables@6.3.0/dist/js/tabulator.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
            overflow-x: auto;                     /* 🔧 Allow horizontal scrolling on body */
        }
        .header {
            text-align: center;
            margin-bottom: 15px;
            color: #2c3e50;
        }
        .header h1 {
            margin-bottom: 5px;
            font-size: 1.8em;
        }
        .header h2 {
            margin-top: 0;
            font-size: 1.2em;
            color: #6c757d;
        }
        .controls {
            text-align: center;
            margin-bottom: 15px;
        }
        .btn {
            background-color: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .btn:hover {
            background-color: #218838;
        }
        .btn-secondary {
            background-color: #6c757d;
        }
        .btn-secondary:hover {
            background-color: #5a6268;
        }
        #pivot-table {
            border: 1px solid #dee2e6;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow-x: auto;                     /* 🔧 Enable horizontal scrolling */
            max-width: 100%;                      /* 🔧 Ensure container respects viewport */
        }
        /* Custom styling for hierarchy column */
        .tabulator .tabulator-cell[tabulator-field="hierarchy"] {
            font-weight: bold;
        }
        /* Total row styling */
        .total-row {
            background-color: #17a2b8 !important;
            color: white !important;
            font-weight: bold !important;
        }
        /* Group row styling */
        .group-row {
            background-color: #495057 !important;
            color: white !important;
            font-weight: bold !important;
        }
        /* Model row styling */
        .model-row {
            color: #6c757d;
            font-style: italic;
        }
        .compact-info {
            text-align: center;
            margin-bottom: 15px;
        }
        .info-toggle {
            background-color: #17a2b8;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: background-color 0.3s ease;
        }
        .info-toggle:hover {
            background-color: #138496;
        }
        .info-details {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 12px;
            border-radius: 5px;
            margin-top: 8px;
            text-align: left;
            font-size: 13px;
            line-height: 1.4;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
        .info-details p {
            margin: 6px 0;
        }

        /* Breathing animation for first test case hint */
        .breathing-hint {
            animation: breathe 2s ease-in-out infinite;
            cursor: pointer;
        }

        @keyframes breathe {
            0% {
                box-shadow: 0 0 10px rgba(40, 167, 69, 0.4);
                transform: scale(1);
            }
            50% {
                box-shadow: 0 0 20px rgba(40, 167, 69, 0.8), 0 0 30px rgba(40, 167, 69, 0.4);
                transform: scale(1.02);
            }
            100% {
                box-shadow: 0 0 10px rgba(40, 167, 69, 0.4);
                transform: scale(1);
            }
        }

        /* Loading spinner */
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #28a745;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Floating bounce animation for click hint */
        @keyframes float-bounce {
            0%, 100% {
                transform: translateY(0px) scale(1);
                opacity: 1;
            }
            50% {
                transform: translateY(-8px) scale(1.05);
                opacity: 0.9;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 MonsterC Automation Failures</h1>
        <h2>✨ Native Collapsible Groups with Tabulator.js ✨</h2>
    </div>

    <!-- Compact collapsible instructions -->
    <div class="compact-info">
        <button class="info-toggle" onclick="toggleInfo()">📋 Instructions & Legend</button>
        <div id="info-details" class="info-details" style="display: none;">
            <p><strong>🎯 Usage:</strong> Test cases start collapsed - Click test case names to expand!</p>
            <p><strong>🎨 Heat Map:</strong> 🔴 RED (overall max) | 🟠 ORANGE (test case max) | 🟡 YELLOW (top 3 models)</p>
            <p><strong>📊 Layout:</strong> Columns sorted by failures (highest left) | Grand Total = sum of all stations</p>
        </div>
    </div>

    <div class="controls">
        <button class="btn" id="expand-btn" onclick="expandAllWithLoading()">🔽 Expand All</button>
        <button class="btn btn-secondary" id="collapse-btn" onclick="collapseAllWithLoading()">🔼 Collapse All</button>
        <button class="btn btn-secondary" onclick="location.reload()">🔄 Refresh Data</button>

        <!-- Loading indicator -->
        <div id="loading-indicator" style="display: none; margin-top: 10px; text-align: center;">
            <div style="color: #28a745; font-weight: bold;">
                ⏳ Processing... Please wait...
                <div style="margin-top: 5px;">
                    <div class="spinner"></div>
                </div>
            </div>
        </div>
    </div>

    <div id="pivot-table"></div>

    <script>
        console.log('🚀 Initializing Tabulator with collapsible groups...');

        // First fetch the data to get columns, then initialize table
        fetch("/api/pivot-data")
            .then(response => response.json())
            .then(data => {
                console.log('📊 Received data:', data.length, 'rows');

                // Generate columns dynamically from first row
                var columns = [
                    {
                        title: "Test Case → Model",
                        field: "hierarchy",
                        width: 350,
                        minWidth: 300,                    // 🔧 Minimum width to prevent squeezing
                        responsive: 0,                    // Never hide this column
                        frozen: true,                     // 🔧 Pin this column to the left
                        formatter: "html"
                    }
                ];

                // Get station columns from data and sort them by total failures
                if (data.length > 0) {
                    var totalRow = data.find(row => row.isTotal);
                    if (totalRow) {
                        // Get all station columns and their totals
                        var stationColumns = [];
                        Object.keys(totalRow).forEach(function(key) {
                            if (key !== 'hierarchy' && key !== 'isTotal' && key !== 'isGroup' && key !== 'isModel' && key !== '_children' && key !== 'expand_icon' && key !== '_maxValue' && key !== '_maxStation' && key !== 'Grand_Total') {
                                stationColumns.push({
                                    station: key,
                                    total: totalRow[key] || 0
                                });
                            }
                        });

                        // Sort stations by total failures (highest first)
                        stationColumns.sort(function(a, b) {
                            return b.total - a.total;
                        });

                        console.log('📊 Station columns sorted by failures:', stationColumns.slice(0, 5));

                        // Store stationColumns globally for formatter access
                        window.stationColumns = stationColumns;

                        // Add Grand Total column right after hierarchy (for quick access)
                        columns.push({
                            title: "Grand Total",
                            field: "Grand_Total",
                            width: 120,
                            minWidth: 100,
                            hozAlign: "center",
                            headerStyle: {
                                backgroundColor: "#17a2b8",  // Blue header background
                                color: "white",
                                fontWeight: "bold"
                            },
                            formatter: function(cell, formatterParams, onRendered) {
                                var value = cell.getValue();
                                var rowData = cell.getRow().getData();

                                // Show all values (no zen zeros for Grand Total)
                                // Style Grand Total column with dark background and white text for visibility
                                cell.getElement().style.fontWeight = "bold";
                                cell.getElement().style.color = "white";
                                cell.getElement().style.backgroundColor = "#495057";  // Dark gray to match group rows
                                cell.getElement().style.borderLeft = "2px solid #6c757d";

                                return value || 0;
                            }
                        });

                        // Add columns in sorted order (highest failures on left)
                        stationColumns.forEach(function(stationInfo) {
                            columns.push({
                                title: stationInfo.station,
                                field: stationInfo.station,
                                width: 100,
                                minWidth: 80,                      // 🔧 Minimum width for station columns
                                hozAlign: "center",
                                formatter: function(cell, formatterParams, onRendered) {
                                    var value = cell.getValue();
                                    var rowData = cell.getRow().getData();

                                    // Zen zeros - hide zero values
                                    if (value === 0) return "";

                                    // 1. RED: Total row max value (overall highest)
                                    if (rowData.isTotal && rowData._maxStation === cell.getField() && value === rowData._maxValue) {
                                        cell.getElement().style.backgroundColor = "#ff6b6b";
                                        cell.getElement().style.color = "white";
                                        cell.getElement().style.fontWeight = "bold";
                                        return value;
                                    }

                                    // 2. ORANGE: Test case row max value (highest for each test case)
                                    if (rowData.isGroup) {
                                        // Find max value for this test case row
                                        var maxValueForRow = 0;
                                        var maxStationForRow = "";
                                        window.stationColumns.forEach(function(stationInfo) {
                                            var stationValue = rowData[stationInfo.station] || 0;
                                            if (stationValue > maxValueForRow) {
                                                maxValueForRow = stationValue;
                                                maxStationForRow = stationInfo.station;
                                            }
                                        });

                                        if (cell.getField() === maxStationForRow && value === maxValueForRow && value > 0) {
                                            cell.getElement().style.backgroundColor = "#ff9800";
                                            cell.getElement().style.color = "white";
                                            cell.getElement().style.fontWeight = "bold";
                                            return value;
                                        }
                                    }

                                    // 3. YELLOW: Top 3 models in each category max value
                                    if (rowData.isModel) {
                                        // Check if this is a top 3 model (based on row position within parent)
                                        var parentRow = cell.getRow().getTreeParent();
                                        if (parentRow) {
                                            var siblings = parentRow.getTreeChildren();
                                            var modelIndex = siblings.indexOf(cell.getRow());

                                            // Only highlight top 3 models (first 3 in sorted order)
                                            if (modelIndex < 3) {
                                                // Find max value for this model row
                                                var maxValueForModel = 0;
                                                var maxStationForModel = "";
                                                window.stationColumns.forEach(function(stationInfo) {
                                                    var stationValue = rowData[stationInfo.station] || 0;
                                                    if (stationValue > maxValueForModel) {
                                                        maxValueForModel = stationValue;
                                                        maxStationForModel = stationInfo.station;
                                                    }
                                                });

                                                if (cell.getField() === maxStationForModel && value === maxValueForModel && value > 0) {
                                                    cell.getElement().style.backgroundColor = "#ffc107";
                                                    cell.getElement().style.color = "#000";
                                                    cell.getElement().style.fontWeight = "bold";
                                                    return value;
                                                }
                                            }
                                        }
                                    }

                                    return value;
                                }
                            });
                        });

                        // Add Grand Total column at the very end (rightmost)
                        columns.push({
                            title: "Grand Total",
                            field: "Grand_Total",
                            width: 120,
                            minWidth: 100,                        // 🔧 Minimum width for Grand Total
                            hozAlign: "center",
                            headerStyle: {
                                backgroundColor: "#17a2b8",       // Blue header background to match first Grand Total
                                color: "white",
                                fontWeight: "bold"
                            },
                            formatter: function(cell, formatterParams, onRendered) {
                                var value = cell.getValue();
                                var rowData = cell.getRow().getData();

                                // Show all values (no zen zeros for Grand Total)
                                // Style Grand Total column with dark background and white text for visibility
                                cell.getElement().style.fontWeight = "bold";
                                cell.getElement().style.color = "white";
                                cell.getElement().style.backgroundColor = "#495057";  // Dark gray to match group rows
                                cell.getElement().style.borderLeft = "2px solid #6c757d";

                                return value || 0;
                            }
                        });
                    }
                }

                // Create Tabulator table with tree data
                var table = new Tabulator("#pivot-table", {
                    data: data,                        // Use fetched data directly
                    dataTree: true,                    // 🔑 Enable tree functionality!
                    dataTreeStartExpanded: false,      // 🎯 Start with groups COLLAPSED for clean view
                    dataTreeChildField: "_children",   // Field containing child rows
                    height: "600px",
                    layout: "fitData",                 // 🔧 Fixed: Use fitData instead of fitColumns for horizontal scrolling
                    responsiveLayout: false,           // 🔧 Fixed: Disable responsive layout that hides columns
                    placeholder: "Loading collapsible automation data...",
                    columns: columns,
                    rowFormatter: function(row) {
                        var data = row.getData();
                        if (data.isTotal) {
                            row.getElement().classList.add("total-row");
                        } else if (data.isGroup) {
                            row.getElement().classList.add("group-row");
                        } else if (data.isModel) {
                            row.getElement().classList.add("model-row");
                        }
                    },
                    dataTreeElementColumn: "hierarchy",  // Column to show tree controls
                });

                // Log when table is built and add UX enhancements
                table.on("tableBuilt", function() {
                    console.log('✅ Tabulator table built with tree data!');

                    // Add breathing animation to first test case (guide user)
                    setTimeout(function() {
                        addFirstTestCaseAnimation();
                    }, 500); // Small delay to ensure rendering is complete
                });

                // Function to add breathing animation and tooltip to first test case
                function addFirstTestCaseAnimation() {
                    var rows = table.getRows();
                    var firstTestCaseRow = null;

                    // Find first test case row (skip total row)
                    for (var i = 0; i < rows.length; i++) {
                        var rowData = rows[i].getData();
                        if (rowData.isGroup && !rowData.isTotal) {
                            firstTestCaseRow = rows[i];
                            break;
                        }
                    }

                    if (firstTestCaseRow) {
                        var element = firstTestCaseRow.getElement();

                        // Add breathing animation class
                        element.classList.add('breathing-hint');

                        // Add tooltip and click handler for entire cell
                        element.setAttribute('title', '💡 Click anywhere on this test case to expand and see all models!');

                        // Make the entire test case cell clickable (not just the checkbox)
                        addTestCaseClickHandler(firstTestCaseRow);

                        // Show floating notification
                        showClickHint(element);

                        // Remove animation and hint after 10 seconds (user gets the hint)
                        setTimeout(function() {
                            element.classList.remove('breathing-hint');
                            element.removeAttribute('title');
                            hideClickHint();
                        }, 10000);
                    }
                }

                // Function to show floating click hint
                function showClickHint(targetElement) {
                    // Create floating notification
                    var hint = document.createElement('div');
                    hint.id = 'click-hint';
                    hint.innerHTML = '👆 Click anywhere on this test case to expand!';
                    hint.style.cssText = `
                        position: absolute;
                        background: linear-gradient(45deg, #28a745, #20c997);
                        color: white;
                        padding: 8px 15px;
                        border-radius: 20px;
                        font-size: 14px;
                        font-weight: bold;
                        box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
                        z-index: 1000;
                        animation: float-bounce 2s ease-in-out infinite;
                        pointer-events: none;
                        white-space: nowrap;
                    `;

                    // Position above the target element
                    var rect = targetElement.getBoundingClientRect();
                    hint.style.left = (rect.left + rect.width / 2 - 100) + 'px';
                    hint.style.top = (rect.top - 50) + 'px';

                    document.body.appendChild(hint);
                }

                function hideClickHint() {
                    var hint = document.getElementById('click-hint');
                    if (hint) {
                        hint.remove();
                    }
                }

                // Function to add click handler to test case rows
                function addTestCaseClickHandler(row) {
                    var element = row.getElement();
                    var hierarchyCell = element.querySelector('[tabulator-field="hierarchy"]');

                    if (hierarchyCell) {
                        // Make the hierarchy cell clickable with visual feedback
                        hierarchyCell.style.cursor = 'pointer';
                        hierarchyCell.style.userSelect = 'none'; // Prevent text selection

                        // Add click event to toggle expansion
                        hierarchyCell.addEventListener('click', function(e) {
                            // Prevent event bubbling
                            e.stopPropagation();

                            // Toggle the tree expansion
                            if (row.isTreeExpanded()) {
                                row.treeCollapse();
                                console.log('🔼 Collapsed via cell click:', row.getData().hierarchy);
                            } else {
                                row.treeExpand();
                                console.log('🔽 Expanded via cell click:', row.getData().hierarchy);
                            }
                        });

                        // Add hover effects for better UX
                        hierarchyCell.addEventListener('mouseenter', function() {
                            hierarchyCell.style.backgroundColor = 'rgba(40, 167, 69, 0.1)';
                        });

                        hierarchyCell.addEventListener('mouseleave', function() {
                            hierarchyCell.style.backgroundColor = '';
                        });
                    }
                }

                // Make ALL test case rows clickable (not just the first one)
                function makeAllTestCasesClickable() {
                    var rows = table.getRows();

                    rows.forEach(function(row) {
                        var rowData = row.getData();
                        // Apply to all group rows (test cases) but not total row
                        if (rowData.isGroup && !rowData.isTotal) {
                            addTestCaseClickHandler(row);
                        }
                    });

                    console.log('✅ Made all test case rows clickable!');
                }

                // Apply click handlers to all test cases after table is built
                table.on("tableBuilt", function() {
                    setTimeout(function() {
                        makeAllTestCasesClickable();
                    }, 600); // Slight delay after animation setup
                });

                // Log expand/collapse events
                table.on("dataTreeRowExpanded", function(row, level) {
                    console.log('🔽 Expanded:', row.getData().hierarchy);
                });

                table.on("dataTreeRowCollapsed", function(row, level) {
                    console.log('🔼 Collapsed:', row.getData().hierarchy);
                });

                // Make table available globally for controls
                window.table = table;
            })
            .catch(error => {
                console.error('❌ Error loading data:', error);
            });

        console.log('🎉 Tabulator initialized! Click arrows to collapse/expand groups!');

        // Function to toggle instructions panel
        function toggleInfo() {
            var details = document.getElementById('info-details');
            var button = document.querySelector('.info-toggle');

            if (details.style.display === 'none') {
                details.style.display = 'block';
                button.innerHTML = '📋 Hide Instructions & Legend';
            } else {
                details.style.display = 'none';
                button.innerHTML = '📋 Instructions & Legend';
            }
        }

        // Functions for expand/collapse with loading indicators
        function expandAllWithLoading() {
            if (!window.table) return;

            showLoading('Expanding all test cases...');
            document.getElementById('expand-btn').disabled = true;
            document.getElementById('collapse-btn').disabled = true;

            // Use setTimeout to allow UI to update before processing
            setTimeout(function() {
                try {
                    window.table.getRows().forEach(row => row.treeExpand());
                    console.log('🔽 Expanded all test cases');
                } catch (error) {
                    console.error('Error expanding rows:', error);
                }
                hideLoading();
            }, 100);
        }

        function collapseAllWithLoading() {
            if (!window.table) return;

            showLoading('Collapsing all test cases...');
            document.getElementById('expand-btn').disabled = true;
            document.getElementById('collapse-btn').disabled = true;

            // Use setTimeout to allow UI to update before processing
            setTimeout(function() {
                try {
                    window.table.getRows().forEach(row => row.treeCollapse());
                    console.log('🔼 Collapsed all test cases');
                } catch (error) {
                    console.error('Error collapsing rows:', error);
                }
                hideLoading();
            }, 100);
        }

        function showLoading(message) {
            var indicator = document.getElementById('loading-indicator');
            if (indicator) {
                indicator.querySelector('div').firstChild.textContent = '⏳ ' + message;
                indicator.style.display = 'block';
            }
        }

        function hideLoading() {
            setTimeout(function() {
                var indicator = document.getElementById('loading-indicator');
                if (indicator) {
                    indicator.style.display = 'none';
                }
                document.getElementById('expand-btn').disabled = false;
                document.getElementById('collapse-btn').disabled = false;
            }, 500); // Small delay so user sees the completion
        }
    </script>
</body>
</html>
"""


@app.route("/")
def tabulator_interface():
    """Serve the Tabulator.js interface."""
    try:
        # Create sample columns for template (will be replaced by real data)
        sample_columns = [
            {"title": "Test Case → Model", "field": "hierarchy", "width": 350},
            {"title": "radi154", "field": "radi154", "width": 80},
            {"title": "radi152", "field": "radi152", "width": 80},
        ]

        return render_template_string(
            TABULATOR_HTML, columns=json.dumps(sample_columns)
        )
    except Exception as e:
        logger.error(f"Error serving Tabulator interface: {e}")
        return f"Error: {e}", 500


@app.route("/api/pivot-data")
def get_pivot_data():
    """Serve pivot data in Tabulator tree format."""
    try:
        # Use data paths passed from Gradio
        if not DATA_PATHS or "pivot_data" not in DATA_PATHS:
            # Fall back to default paths for standalone testing
            data_file = "/tmp/monsterc_pivot_data.json"
            device_counts_file = "/tmp/monsterc_device_counts.json"
            automation_data_file = "/tmp/monsterc_automation_data.json"
        else:
            data_file = DATA_PATHS["pivot_data"]
            device_counts_file = DATA_PATHS.get(
                "device_counts", "/tmp/monsterc_device_counts.json"
            )
            automation_data_file = DATA_PATHS.get(
                "automation_data", "/tmp/monsterc_automation_data.json"
            )

        if not os.path.exists(data_file):
            return (
                jsonify(
                    {
                        "error": (
                            "No pivot data available. "
                            "Please run 'Automation High Failures' first."
                        ),
                        "data": [],
                    }
                ),
                404,
            )

        # Load the pivot data
        with open(data_file, "r") as f:
            stored_data = json.load(f)

        pivot_df = pd.DataFrame(stored_data)
        logger.info(f"📊 Loaded pivot data: {pivot_df.shape}")

        # Load device failure counts for accurate totals
        global device_failure_counts
        if os.path.exists(device_counts_file):
            with open(device_counts_file, "r") as f:
                device_failure_counts = json.load(f)
                logger.info(
                    f"📊 Loaded device failure counts from: {device_counts_file}"
                )

        # Create CONCATENATED test case structure but use ORIGINAL totals
        concatenated_pivot = create_concatenated_failure_pivot(automation_data_file)
        if concatenated_pivot is not None and not concatenated_pivot.empty:
            logger.info("🔗 Creating hybrid: concatenated test cases + original totals")

            # Use concatenated data for test case structure, but original pivot for station totals
            tree_data = transform_pivot_to_tabulator_tree_hybrid(
                pivot_df, concatenated_pivot
            )
        else:
            logger.info("⚠️ Falling back to standard pivot data")
            tree_data = transform_pivot_to_tabulator_tree(pivot_df)

        # ALWAYS use original pivot data for column sorting (correct totals)
        # Only use concatenated data for test case grouping structure
        station_cols = sort_stations_by_total_errors(pivot_df)
        logger.info(f"🔥 Using ORIGINAL pivot for column sorting: {station_cols[:3]}")
        create_tabulator_columns(station_cols)

        logger.info(f"🚀 Serving {len(tree_data)} rows to Tabulator")
        return jsonify(tree_data)  # Return just the data array, not wrapped in object

    except Exception as e:
        logger.error(f"Error serving pivot data: {e}")
        return jsonify({"error": str(e), "data": []}), 500


if __name__ == "__main__":
    # Accept data paths from command line
    if len(sys.argv) > 1:
        try:
            # Load the JSON string of paths from the command line argument
            DATA_PATHS = json.loads(sys.argv[1])
            logger.info(f"🚀 Received data paths from Gradio: {DATA_PATHS}")
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Could not parse data paths from command line: {e}")
            # Fall back to default paths for standalone testing
            DATA_PATHS = {}
    else:
        logger.warning("No data paths provided via CLI, using defaults")
        DATA_PATHS = {}

    logger.info("🚀 Starting Tabulator.js frontend server...")
    logger.info("📊 Navigate to http://127.0.0.1:5001 for collapsible groups!")
    app.run(
        debug=False,  # IMPORTANT: Set to False for production
        host="127.0.0.1",
        port=5001,  # Different port from Gradio (7860) and Dash (8051)
        threaded=True,
    )
