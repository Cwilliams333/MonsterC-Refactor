#!/usr/bin/env python3
"""
Standalone Dash application with AG Grid for Excel-style hierarchical pivot tables.

This app provides true hierarchical grouping with expandable/collapsible test case
groups, exactly like Excel pivot tables. It runs as a separate process and
communicates with the main Gradio app via temporary files.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import dash
import dash_ag_grid as dag
import pandas as pd
from dash import Input, Output, State, callback, clientside_callback, dcc, html

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from common.logging_config import get_logger  # noqa: E402

# Configure logging
logger = get_logger(__name__)

# Initialize Dash app with custom CSS
app = dash.Dash(__name__)

# Add custom CSS for highlighting
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
        .max-value-highlight {
            background-color: #ffc107 !important;
            font-weight: bold !important;
            color: #000 !important;
            border: 2px solid #ff9800 !important;
        }
        .max-total-highlight {
            background-color: #dc3545 !important;
            font-weight: bold !important;
            color: #fff !important;
            border: 2px solid #c82333 !important;
        }
        .total-row-highlight {
            background-color: #17a2b8 !important;
            font-weight: bold !important;
            color: #fff !important;
            border: 2px solid #138496 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
        }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# Global variable to store current data
current_data = None

app.layout = html.Div(
    [
        html.Div(
            [
                html.H2(
                    "📊 Excel-Style Pivot Analysis",
                    style={
                        "textAlign": "center",
                        "color": "#2c3e50",
                        "marginBottom": "20px",
                    },
                ),
                html.P(
                    (
                        "Interactive hierarchical pivot table with "
                        "expandable test case groups"
                    ),
                    style={
                        "textAlign": "center",
                        "color": "#7f8c8d",
                        "marginBottom": "30px",
                    },
                ),
            ]
        ),
        dcc.Store(id="pivot-data-store"),
        dcc.Store(
            id="collapsed-groups-store", data={}
        ),  # Track which test cases are collapsed
        # Summary Dashboard Panel
        html.Div(
            id="summary-panel",
            children=[
                html.H3(
                    "🎯 Troubleshooting Dashboard",
                    style={
                        "textAlign": "center",
                        "color": "#495057",
                        "marginBottom": "15px",
                        "fontWeight": "bold",
                    },
                ),
                html.Div(
                    [
                        # Highest Model Offender
                        html.Div(
                            [
                                html.H4(
                                    "🏆 Highest Model Cell Value",
                                    style={
                                        "color": "#dc3545",
                                        "marginBottom": "8px",
                                        "fontSize": "16px",
                                    },
                                ),
                                html.P(
                                    id="highest-model-text",
                                    children="Loading...",
                                    style={
                                        "fontSize": "14px",
                                        "marginBottom": "0px",
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                            style={
                                "backgroundColor": "#f8f9fa",
                                "padding": "15px",
                                "borderRadius": "8px",
                                "border": "2px solid #dc3545",
                                "marginBottom": "10px",
                            },
                        ),
                        # Highest Test Case
                        html.Div(
                            [
                                html.H4(
                                    "📊 Highest Test Case Cell Value",
                                    style={
                                        "color": "#fd7e14",
                                        "marginBottom": "8px",
                                        "fontSize": "16px",
                                    },
                                ),
                                html.P(
                                    id="highest-test-case-text",
                                    children="Loading...",
                                    style={
                                        "fontSize": "14px",
                                        "marginBottom": "0px",
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                            style={
                                "backgroundColor": "#f8f9fa",
                                "padding": "15px",
                                "borderRadius": "8px",
                                "border": "2px solid #fd7e14",
                                "marginBottom": "10px",
                            },
                        ),
                        # Highest Station
                        html.Div(
                            [
                                html.H4(
                                    "🔧 Highest Station Cell Value",
                                    style={
                                        "color": "#6f42c1",
                                        "marginBottom": "8px",
                                        "fontSize": "16px",
                                    },
                                ),
                                html.P(
                                    id="highest-station-text",
                                    children="Loading...",
                                    style={
                                        "fontSize": "14px",
                                        "marginBottom": "0px",
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                            style={
                                "backgroundColor": "#f8f9fa",
                                "padding": "15px",
                                "borderRadius": "8px",
                                "border": "2px solid #6f42c1",
                                "marginBottom": "20px",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "row",
                        "justifyContent": "space-between",
                        "gap": "15px",
                        "flexWrap": "wrap",
                    },
                ),
            ],
            style={
                "margin": "20px",
                "padding": "20px",
                "backgroundColor": "#ffffff",
                "borderRadius": "12px",
                "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
                "border": "1px solid #dee2e6",
            },
        ),
        html.Div(
            [
                dag.AgGrid(
                    id="hierarchical-pivot-grid",
                    # Grid options will be set dynamically by callback for collapsible groups
                    dashGridOptions={},
                    # Column sizing
                    columnSize="sizeToFit",
                    # Default column properties
                    defaultColDef={
                        "resizable": True,
                        "sortable": False,  # Disable sorting to preserve hierarchy
                        "filter": False,  # Disable filtering to preserve hierarchy
                        "floatingFilter": False,
                    },
                    # Grid styling
                    style={"height": "700px", "width": "100%"},
                    className="ag-theme-alpine",
                )
            ],
            style={"margin": "20px"},
        ),
        html.Div(
            [
                html.P(
                    (
                        "💡 Tips: Hierarchy preserved - sorting/filtering "
                        "disabled to maintain structure."
                    ),
                    style={
                        "textAlign": "center",
                        "color": "#95a5a6",
                        "fontSize": "14px",
                        "marginTop": "20px",
                    },
                )
            ]
        ),
        # Color Legend
        html.Div(
            [
                html.H4(
                    "🎨 Color Legend",
                    style={
                        "textAlign": "center",
                        "marginBottom": "15px",
                        "color": "#495057",
                    },
                ),
                html.Div(
                    [
                        # Blue highlight explanation (total row)
                        html.Div(
                            [
                                html.Div(
                                    style={
                                        "width": "20px",
                                        "height": "20px",
                                        "backgroundColor": "#17a2b8",
                                        "display": "inline-block",
                                        "marginRight": "8px",
                                        "verticalAlign": "middle",
                                        "border": "2px solid #138496",
                                    }
                                ),
                                html.Span(
                                    "Total failures - highest station overall",
                                    style={
                                        "verticalAlign": "middle",
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                            style={"marginBottom": "8px"},
                        ),
                        # Red highlight explanation
                        html.Div(
                            [
                                html.Div(
                                    style={
                                        "width": "20px",
                                        "height": "20px",
                                        "backgroundColor": "#dc3545",
                                        "display": "inline-block",
                                        "marginRight": "8px",
                                        "verticalAlign": "middle",
                                        "border": "2px solid #c82333",
                                    }
                                ),
                                html.Span(
                                    "Highest failure count per test case",
                                    style={"verticalAlign": "middle"},
                                ),
                            ],
                            style={"marginBottom": "8px"},
                        ),
                        # Yellow highlight explanation
                        html.Div(
                            [
                                html.Div(
                                    style={
                                        "width": "20px",
                                        "height": "20px",
                                        "backgroundColor": "#ffc107",
                                        "display": "inline-block",
                                        "marginRight": "8px",
                                        "verticalAlign": "middle",
                                        "border": "2px solid #ff9800",
                                    }
                                ),
                                html.Span(
                                    "Highest failure count per model",
                                    style={"verticalAlign": "middle"},
                                ),
                            ],
                            style={"marginBottom": "8px"},
                        ),
                        # Dark row explanation
                        html.Div(
                            [
                                html.Div(
                                    style={
                                        "width": "20px",
                                        "height": "20px",
                                        "backgroundColor": "#495057",
                                        "display": "inline-block",
                                        "marginRight": "8px",
                                        "verticalAlign": "middle",
                                    }
                                ),
                                html.Span(
                                    "Test case summary rows (folder icon)",
                                    style={"verticalAlign": "middle"},
                                ),
                            ]
                        ),
                    ],
                    style={
                        "textAlign": "left",
                        "maxWidth": "400px",
                        "margin": "0 auto",
                    },
                ),
            ],
            style={
                "margin": "30px 20px",
                "padding": "20px",
                "backgroundColor": "#f8f9fa",
                "borderRadius": "8px",
            },
        ),
    ]
)


def transform_pivot_to_tree_data(pivot_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Transform a standard pivot table into hierarchical display using community AG Grid features.

    Creates visual hierarchy using text formatting and styling instead of enterprise
    row grouping features. Adds TOTAL ROW at top and sorts everything for maximum impact
    in top-left corner (Excel-style pivot behavior).

    Args:
        pivot_df: DataFrame with columns ['result_FAIL', 'Model', station_columns...]

    Returns:
        List of dictionaries with visual hierarchy formatting
    """
    if pivot_df.empty:
        return []

    hierarchical_data = []

    # Sort stations by total failures (highest first) - show the money columns first!
    station_cols = sort_stations_by_total_errors(pivot_df)

    # CREATE TOTAL ROW AT THE TOP (Excel-style)
    total_row = {"hierarchy": "📊 TOTAL FAILURES", "isGroup": True, "isTotal": True}
    station_totals = {}
    grand_total_sum = 0
    for col in station_cols:
        total_val = pivot_df[col].sum()
        total_row[col] = total_val
        station_totals[col] = total_val
        grand_total_sum += total_val

    # Add Grand Total column (sum of all stations horizontally)
    total_row["Grand_Total"] = grand_total_sum

    # Find the highest station total(s) for red highlighting
    if station_totals:
        max_total = max(station_totals.values())
        max_cols = [
            col for col, val in station_totals.items() if val == max_total and val > 0
        ]
        total_row["maxTotalFields"] = max_cols
    else:
        total_row["maxTotalFields"] = []

    hierarchical_data.append(total_row)
    logger.info(
        f"Added TOTAL ROW with station totals: {[(col, station_totals[col]) for col in station_cols[:5]]}"
    )

    # Calculate model failure totals for smart sorting
    calculate_model_failure_totals(pivot_df)

    # Group by test case to create hierarchy
    grouped = pivot_df.groupby("result_FAIL")

    # Sort test cases by their TOTAL failures (not max model)
    test_case_totals = {}
    for test_case, group in grouped:
        # Calculate total failures for this test case across all stations
        test_case_total = sum(group[col].sum() for col in station_cols)
        test_case_totals[test_case] = test_case_total

    # Sort test cases by total failures (descending) - hottest test cases first!
    sorted_test_cases = sorted(
        test_case_totals.items(), key=lambda x: x[1], reverse=True
    )
    logger.info(f"Test case totals (sorted): {sorted_test_cases[:5]}...")

    for test_case, test_case_total in sorted_test_cases:
        group = grouped.get_group(test_case)
        # Create parent row (group header) with aggregated totals
        group_row = {"hierarchy": f"📁 {test_case}", "isGroup": True}

        # Add aggregated station values and find max for red highlighting
        station_totals = {}
        test_case_grand_total = 0
        for col in station_cols:
            total_val = group[col].sum()
            group_row[col] = total_val  # cellRenderer will handle zero display
            station_totals[col] = total_val
            test_case_grand_total += total_val

        # Add Grand Total for this test case
        group_row["Grand_Total"] = test_case_grand_total

        # Find the highest station total(s) for red highlighting
        if station_totals:
            max_total = max(station_totals.values())
            # Find all columns that have the max value (handles ties)
            max_cols = [
                col
                for col, val in station_totals.items()
                if val == max_total and val > 0
            ]
            group_row["maxTotalFields"] = max_cols
        else:
            group_row["maxTotalFields"] = []

        hierarchical_data.append(group_row)

        # Create child rows for each model, sorted by model failure count
        # WITHIN THIS TEST CASE (descending)
        group_sorted = group.copy()
        # Calculate failures within this test case for each model
        group_sorted["test_case_model_failures"] = group_sorted[station_cols].sum(
            axis=1
        )
        group_sorted = group_sorted.sort_values(
            "test_case_model_failures", ascending=False
        )

        for _, row in group_sorted.iterrows():
            child_row = {"hierarchy": f"  └─ {row['Model']}", "isGroup": False}

            # Add individual station values and calculate Grand Total
            station_values = {}
            model_grand_total = 0
            for col in station_cols:
                child_row[col] = row[col]  # cellRenderer will handle zero display
                station_values[col] = row[col]
                model_grand_total += row[col]

            # Add Grand Total for this model
            child_row["Grand_Total"] = model_grand_total

            # Find the column with max value for highlighting
            if station_values:
                max_col = max(station_values.keys(), key=lambda k: station_values[k])
                max_val = station_values[max_col]
                # Only mark max if value > 0
                if max_val > 0:
                    child_row["maxField"] = max_col
                else:
                    child_row["maxField"] = None
            else:
                child_row["maxField"] = None

            hierarchical_data.append(child_row)

    logger.info(
        f"Created hierarchical display with {len(hierarchical_data)} rows ({len(grouped)} groups)"
    )
    return hierarchical_data


def debug_pivot_calculations(pivot_df: pd.DataFrame) -> None:
    """Debug function to trace calculation issues."""
    logger.info("=== DEBUGGING PIVOT CALCULATIONS ===")
    logger.info(f"Pivot DataFrame shape: {pivot_df.shape}")
    logger.info(f"Pivot DataFrame columns: {list(pivot_df.columns)}")

    # Show first few rows
    logger.info("First 5 rows of pivot data:")
    for i, (idx, row) in enumerate(pivot_df.head().iterrows()):
        if i < 5:
            logger.info(f"Row {i}: {dict(row)}")

    # Get station columns
    excluded_cols = {"error_code", "error_message", "Model", "result_FAIL"}
    station_cols = [col for col in pivot_df.columns if col not in excluded_cols]
    logger.info(f"Station columns ({len(station_cols)}): {station_cols[:10]}...")

    # Debug model calculations
    logger.info("\n=== MODEL CALCULATIONS ==")
    model_stats = {}
    for _, row in pivot_df.iterrows():
        model = row["Model"]
        test_case = row.get("result_FAIL", "Unknown")
        station_failures = row[station_cols].sum()

        if model not in model_stats:
            model_stats[model] = 0
        model_stats[model] += station_failures

        # Log details for iPhone14ProMax
        if model == "iPhone14ProMax":
            logger.info(
                f"iPhone14ProMax - Test: {test_case}, Station failures: {station_failures}, Running total: {model_stats[model]}"
            )

    # Show top 5 models
    sorted_models = sorted(model_stats.items(), key=lambda x: x[1], reverse=True)
    logger.info("\nTop 5 models by failure count:")
    for i, (model, count) in enumerate(sorted_models[:5]):
        logger.info(f"{i+1}. {model}: {count} failures")

    # Debug test case calculations
    logger.info("\n=== TEST CASE CALCULATIONS ====")
    test_case_stats = {}
    for _, row in pivot_df.iterrows():
        test_case = row.get("result_FAIL", "Unknown")
        station_failures = row[station_cols].sum()

        if test_case not in test_case_stats:
            test_case_stats[test_case] = 0
        test_case_stats[test_case] += station_failures

        # Log details for Camera Pictures
        if test_case == "Camera Pictures":
            logger.info(
                f"Camera Pictures - Model: {row['Model']}, Station failures: {station_failures}, Running total: {test_case_stats[test_case]}"
            )

    # Show top 5 test cases
    sorted_test_cases = sorted(
        test_case_stats.items(), key=lambda x: x[1], reverse=True
    )
    logger.info("\nTop 5 test cases by failure count:")
    for i, (test_case, count) in enumerate(sorted_test_cases[:5]):
        logger.info(f"{i+1}. {test_case}: {count} failures")

    # Debug station calculations
    logger.info("\n=== STATION CALCULATIONS ====")
    station_stats = {}
    for col in station_cols:
        station_stats[col] = pivot_df[col].sum()

    # Show top 5 stations
    sorted_stations = sorted(station_stats.items(), key=lambda x: x[1], reverse=True)
    logger.info("\nTop 5 stations by failure count:")
    for i, (station, count) in enumerate(sorted_stations[:5]):
        logger.info(f"{i+1}. {station}: {count} failures")

        # Show breakdown for radi056
        if station == "radi056":
            logger.info("radi056 breakdown:")
            for _, row in pivot_df.iterrows():
                if row[station] > 0:
                    logger.info(
                        f"  {row['result_FAIL']} - {row['Model']}: {row[station]} failures"
                    )


def calculate_pivot_summary_stats(pivot_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate key summary statistics.

    Shows the highest INDIVIDUAL cell values visible in the pivot table.

    Args:
        pivot_df: DataFrame with failure analysis data

    Returns:
        Dictionary with highest individual cell values that match
        what's visible in the pivot table
    """
    try:
        if pivot_df.empty:
            return {
                "highest_model": {
                    "name": "No data",
                    "count": 0,
                    "test_case": "N/A",
                    "station": "N/A",
                },
                "highest_test_case": {
                    "name": "No data",
                    "count": 0,
                    "model": "N/A",
                    "station": "N/A",
                },
                "highest_station": {
                    "name": "No data",
                    "count": 0,
                    "test_case": "N/A",
                    "model": "N/A",
                },
            }

        # Get station columns (exclude metadata columns)
        excluded_cols = {"error_code", "error_message", "Model", "result_FAIL"}
        station_cols = [col for col in pivot_df.columns if col not in excluded_cols]

        # Find the highest individual cell value for each dimension
        max_cell_value = 0

        # Find the overall highest cell value
        for _, row in pivot_df.iterrows():
            for station in station_cols:
                cell_value = row[station]
                if cell_value > max_cell_value:
                    max_cell_value = cell_value

        # 1. Highest Model: Find the model+test_case combination with highest individual cell value
        model_max = {"name": "", "count": 0, "test_case": "", "station": ""}
        for _, row in pivot_df.iterrows():
            model = row["Model"]
            test_case = row.get("result_FAIL", "Unknown")
            for station in station_cols:
                cell_value = row[station]
                if cell_value > model_max["count"]:
                    model_max = {
                        "name": model,
                        "count": cell_value,
                        "test_case": test_case,
                        "station": station,
                    }

        # 2. Highest Test Case: Find the test_case+model combination with highest individual cell value
        test_case_max = {"name": "", "count": 0, "model": "", "station": ""}
        for _, row in pivot_df.iterrows():
            test_case = row.get("result_FAIL", "Unknown")
            model = row["Model"]
            for station in station_cols:
                cell_value = row[station]
                if cell_value > test_case_max["count"]:
                    test_case_max = {
                        "name": test_case,
                        "count": cell_value,
                        "model": model,
                        "station": station,
                    }

        # 3. Highest Station: Find the station with highest individual cell value
        station_max = {"name": "", "count": 0, "test_case": "", "model": ""}
        for station in station_cols:
            for _, row in pivot_df.iterrows():
                cell_value = row[station]
                if cell_value > station_max["count"]:
                    station_max = {
                        "name": station,
                        "count": cell_value,
                        "test_case": row.get("result_FAIL", "Unknown"),
                        "model": row["Model"],
                    }

        logger.info(
            f"Max cell values - Model: {model_max['name']} "
            f"({model_max['count']} in {model_max['test_case']} at "
            f"{model_max['station']}), Test: {test_case_max['name']} "
            f"({test_case_max['count']} with {test_case_max['model']} at "
            f"{test_case_max['station']}), Station: {station_max['name']} "
            f"({station_max['count']} for {station_max['test_case']} "
            f"with {station_max['model']})"
        )

        return {
            "highest_model": {
                "name": model_max["name"],
                "count": model_max["count"],
                "test_case": model_max["test_case"],
                "station": model_max["station"],
            },
            "highest_test_case": {
                "name": test_case_max["name"],
                "count": test_case_max["count"],
                "model": test_case_max["model"],
                "station": test_case_max["station"],
            },
            "highest_station": {
                "name": station_max["name"],
                "count": station_max["count"],
                "test_case": station_max["test_case"],
                "model": station_max["model"],
            },
        }

    except Exception as e:
        logger.error(f"Error calculating summary stats: {e}")
        return {
            "highest_model": {
                "name": "Error",
                "count": 0,
                "test_case": "N/A",
                "station": "N/A",
            },
            "highest_test_case": {
                "name": "Error",
                "count": 0,
                "model": "N/A",
                "station": "N/A",
            },
            "highest_station": {
                "name": "Error",
                "count": 0,
                "test_case": "N/A",
                "model": "N/A",
            },
        }


def calculate_model_failure_totals(pivot_df: pd.DataFrame) -> Dict[str, int]:
    """
    Calculate total failures per model for test failure analysis sorting.

    Args:
        pivot_df: DataFrame with columns ['result_FAIL', 'Model', station_columns...]

    Returns:
        Dictionary mapping model names to total failure counts (sorted descending)
    """
    # Handle both error analysis and failure analysis column structures
    excluded_cols = {"error_code", "error_message", "Model", "result_FAIL"}
    station_cols = [col for col in pivot_df.columns if col not in excluded_cols]

    # Calculate total failures per model across all stations
    model_totals = {}
    if "Model" in pivot_df.columns:
        for model in pivot_df["Model"].unique():
            model_data = pivot_df[pivot_df["Model"] == model]
            total_failures = model_data[station_cols].sum().sum()
            model_totals[model] = total_failures

    # Sort by total failures (highest first) - money models first!
    sorted_models = dict(sorted(model_totals.items(), key=lambda x: x[1], reverse=True))

    logger.info(f"Model failure totals (sorted): {list(sorted_models.items())[:5]}...")

    return sorted_models


def sort_stations_by_total_errors(pivot_df: pd.DataFrame) -> List[str]:
    """
    Sort station columns by total error count (highest first) to show the money columns up front.

    Args:
        pivot_df: DataFrame with station columns

    Returns:
        List of station column names sorted by total errors (descending)
    """
    # Handle both error analysis and failure analysis column structures
    excluded_cols = ["error_code", "error_message", "Model", "result_FAIL"]
    station_cols = [col for col in pivot_df.columns if col not in excluded_cols]

    # Calculate total errors per station
    station_totals = {}
    for col in station_cols:
        station_totals[col] = pivot_df[col].sum()

    # Sort by total errors (highest first) - puts the action up front
    sorted_stations = sorted(station_totals.items(), key=lambda x: x[1], reverse=True)

    logger.info(
        f"Station totals (sorted): "
        f"{[(station, total) for station, total in sorted_stations[:10]]}"
    )

    return [station for station, total in sorted_stations]


def transform_error_pivot_to_tree_data(pivot_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Transform error analysis pivot into hierarchical display.
    
    Creates structure: 📊 Total Errors → 📂 Error Code (Message) → └─ Model

    Args:
        pivot_df: DataFrame with columns [error_code, error_message, Model, ...station_cols]

    Returns:
        List of dictionaries with proper 3-level visual hierarchy.
    """
    if pivot_df.empty:
        return []

    hierarchical_data = []

    # Sort stations by total errors (highest first) - show the money columns first!
    station_cols = sort_stations_by_total_errors(pivot_df)

    # Create "Total Errors" summary row (aggregates everything)
    total_row = {"hierarchy": "📊 Total Errors", "isGroup": True}
    total_values = {}
    for col in station_cols:
        total_val = pivot_df[col].sum()
        total_row[col] = total_val  # cellRenderer will handle zero display
        total_values[col] = total_val

    # Find highest station total for red highlighting
    if total_values:
        max_total = max(total_values.values())
        max_cols = [
            col for col, val in total_values.items() if val == max_total and val > 0
        ]
        total_row["maxTotalFields"] = max_cols
    else:
        total_row["maxTotalFields"] = []

    hierarchical_data.append(total_row)

    # Group by error_code (unique values only - no duplicates)
    error_grouped = pivot_df.groupby(["error_code", "error_message"])

    for (error_code, error_message), error_group in error_grouped:
        # Create Error Code folder (level 2) with subtotals
        error_row = {"hierarchy": f"📂 {error_code} - {error_message}", "isGroup": True}

        # Add aggregated station values for this error code
        error_totals = {}
        for col in station_cols:
            total_val = error_group[col].sum()
            error_row[col] = total_val  # cellRenderer will handle zero display
            error_totals[col] = total_val

        # Find highest station total for error code (red highlighting)
        if error_totals:
            max_total = max(error_totals.values())
            max_cols = [
                col for col, val in error_totals.items() if val == max_total and val > 0
            ]
            error_row["maxTotalFields"] = max_cols
        else:
            error_row["maxTotalFields"] = []

        hierarchical_data.append(error_row)

        # Create Model child rows under this error code (level 3)
        for _, row in error_group.iterrows():
            model_row = {"hierarchy": f"  └─ {row['Model']}", "isGroup": False}

            # Add individual station values for this model with this error
            station_values = {}
            for col in station_cols:
                model_row[col] = row[col]  # cellRenderer will handle zero display
                station_values[col] = row[col]

            # Find highest station value for this model (yellow highlighting)
            if station_values:
                max_val = max(station_values.values())
                max_cols = [
                    col
                    for col, val in station_values.items()
                    if val == max_val and val > 0
                ]
                model_row["maxValueFields"] = max_cols
            else:
                model_row["maxValueFields"] = []

            hierarchical_data.append(model_row)

    return hierarchical_data


def create_column_definitions(
    data: List[Dict[str, Any]], analysis_type: str = "failure"
) -> List[Dict[str, Any]]:
    """Create AG Grid column definitions for community version hierarchy."""
    if not data:
        return []

    # Get all possible columns from the data
    all_columns = set()
    for row in data:
        all_columns.update(row.keys())

    # Remove internal columns (used for highlighting logic, not display)
    internal_columns = {
        "isGroup",
        "isTotal",
        "maxField",
        "maxTotalFields",
        "maxValueFields",
    }
    display_columns = [col for col in all_columns if col not in internal_columns]

    column_defs = []

    # Dynamic header name based on analysis type
    if analysis_type == "error":
        header_name = "Error Code → Model"
    else:
        header_name = "Test Case → Model"

    # Always put hierarchy column first (pinned left)
    if "hierarchy" in display_columns:
        column_defs.append(
            {
                "field": "hierarchy",
                "headerName": header_name,
                "minWidth": 350,  # Slightly wider for 3-level hierarchy
                "pinned": "left",  # Pin to left side
                # "cellRenderer": "clickableHierarchyRenderer",  # 🎯 Temporarily disabled until JS registration fixed
                "cellStyle": {
                    "function": "params.data.isTotal ? {'fontWeight': 'bold', 'backgroundColor': '#343a40', 'color': '#ffffff', 'textAlign': 'left', 'paddingLeft': '10px', 'fontSize': '16px'} : params.data.isGroup ? {'fontWeight': 'bold', 'backgroundColor': '#495057', 'color': '#ffffff', 'textAlign': 'left', 'paddingLeft': '10px'} : {'paddingLeft': '10px', 'color': '#6c757d', 'textAlign': 'left'}"
                },
            }
        )

    # Add station columns with highlighting for max values per row
    # Get sorted station columns (excluding hierarchy and internal columns) - money columns first!
    station_columns = [col for col in display_columns if col != "hierarchy"]

    # CRITICAL: Extract station columns in SORTED ORDER (highest failures first)
    # We need to get the station columns in the exact order they were sorted by our transformation
    if data and any("📊" in str(row.get("hierarchy", "")) for row in data):
        # Find the TOTAL FAILURES row and use a sorted approach
        total_row = next(
            (
                row
                for row in data
                if "📊 TOTAL FAILURES" in str(row.get("hierarchy", ""))
            ),
            None,
        )
        if total_row:
            # Get all station columns with their values from the total row (exclude Grand_Total)
            station_data = {
                col: total_row[col]
                for col in total_row.keys()
                if col not in internal_columns
                and col != "hierarchy"
                and col != "Grand_Total"
            }
            # Sort by total failures (highest first) - this maintains our intended order!
            station_columns = sorted(
                station_data.keys(), key=lambda k: station_data[k], reverse=True
            )
            logger.info(
                f"🔥 CRITICAL: Extracted {len(station_columns)} station columns sorted by failures"
            )
            logger.info(f"🔥 CRITICAL: Column order for AG Grid: {station_columns}")
            logger.info(
                f"🔥 CRITICAL: Top 5 station totals: {[(col, station_data[col]) for col in station_columns[:5]]}"
            )

            # Verify the highest station is first
            if station_columns:
                first_col = station_columns[0]
                first_val = station_data[first_col]
                logger.info(
                    f"🔥 CRITICAL: First column will be {first_col} with {first_val} failures"
                )
        else:
            logger.warning("Could not find TOTAL FAILURES row for column extraction")
    elif data and any("📁" in str(row.get("hierarchy", "")) for row in data):
        # Failure analysis fallback: use default extraction but warn
        first_group_row = next(
            (row for row in data if "📁" in str(row.get("hierarchy", ""))), {}
        )
        if first_group_row:
            station_columns = [
                col
                for col in first_group_row.keys()
                if col not in internal_columns
                and col != "hierarchy"
                and col != "Grand_Total"
            ]
            logger.warning(
                f"Using fallback column extraction (may not be sorted): {station_columns[:5]}..."
            )
        else:
            logger.warning("Could not find test case group row for column extraction")
    else:
        logger.warning("No hierarchical data found for column extraction")

    for col in station_columns:
        column_defs.append(
            {
                "field": col,
                "headerName": col,
                "type": "numericColumn",
                "width": 120,
                "valueFormatter": {
                    "function": "params.value === 0 ? '' : params.value"
                },
                "cellClassRules": {
                    # BLUE: Highlight total row (highest priority)
                    "total-row-highlight": f"params.data.isTotal && params.data.maxTotalFields && params.data.maxTotalFields.includes('{col}') && params.value > 0",
                    # RED: Highlight max total per test case (group rows)
                    "max-total-highlight": f"params.data.isGroup && !params.data.isTotal && params.data.maxTotalFields && params.data.maxTotalFields.includes('{col}') && params.value > 0",
                    # YELLOW: Highlight max value per model (individual rows)
                    "max-value-highlight": f"params.data.maxField === '{col}' && !params.data.isGroup && params.value > 0",
                },
                "cellStyle": {
                    "function": "params.data.isTotal ? {'textAlign': 'center', 'fontWeight': 'bold', 'backgroundColor': '#6c757d', 'color': '#ffffff', 'fontSize': '16px'} : params.data.isGroup ? {'textAlign': 'center', 'fontWeight': 'bold', 'backgroundColor': '#e9ecef'} : {'textAlign': 'center'}"
                },
            }
        )

    # Add Grand Total column at the very end (rightmost)
    if "Grand_Total" in all_columns:
        column_defs.append(
            {
                "field": "Grand_Total",
                "headerName": "Grand Total",
                "type": "numericColumn",
                "width": 140,
                "pinned": "right",  # Pin to right side for visibility
                "valueFormatter": {
                    "function": "params.value || 0"
                },  # Always show value, no zen zeros
                "cellStyle": {
                    "function": "{'textAlign': 'center', 'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'borderLeft': '2px solid #6c757d'}"
                },
            }
        )
        logger.info("Added Grand Total column (pinned right)")

    logger.info(
        f"Created {len(column_defs)} column definitions for community hierarchy"
    )
    return column_defs


@callback(
    [
        Output("hierarchical-pivot-grid", "rowData"),
        Output("hierarchical-pivot-grid", "columnDefs"),
        Output("hierarchical-pivot-grid", "dashGridOptions"),
    ],
    Input("pivot-data-store", "data"),
)
def update_grid(stored_data):
    """Update the AG Grid with new pivot data using collapsible row grouping."""
    if not stored_data:
        return [], [], {}

    try:
        # Convert stored data back to DataFrame
        pivot_df = pd.DataFrame(stored_data)

        if pivot_df.empty:
            logger.warning("Received empty pivot data")
            return [], [], {}

        # Detect analysis type based on columns
        if "error_code" in pivot_df.columns and "error_message" in pivot_df.columns:
            # 3-level error analysis - use legacy approach for now
            tree_data = transform_error_pivot_to_tree_data(pivot_df)
            column_defs = create_column_definitions(tree_data, analysis_type="error")
            grid_options = {}  # No grouping for error analysis yet
            logger.info("Using legacy error analysis display")
        else:
            # BACK TO BEAUTIFUL WORKING STATE
            logger.info("Using beautiful working hierarchy display")
            tree_data = transform_pivot_to_tree_data(pivot_df)
            column_defs = create_column_definitions(tree_data, analysis_type="failure")
            grid_options = {
                # Community version settings - no enterprise features
                "headerHeight": 40,
                "rowHeight": 35,
                # Performance settings
                "animateRows": True,
                "suppressRowClickSelection": True,
                # Disable sorting to maintain hierarchy order
                "sortable": False,
                "filter": False,
                # Theme and styling
                "theme": "ag-theme-alpine",
            }

        return tree_data, column_defs, grid_options

    except Exception as e:
        logger.error(f"Error updating grid: {e}")
        return [], [], {}


@callback(
    [
        Output("highest-model-text", "children"),
        Output("highest-test-case-text", "children"),
        Output("highest-station-text", "children"),
    ],
    Input("pivot-data-store", "data"),
)
def update_summary_panel(stored_data):
    """Update the troubleshooting dashboard with key statistics."""
    if not stored_data:
        return "No data available", "No data available", "No data available"

    try:
        # Convert stored data back to DataFrame
        pivot_df = pd.DataFrame(stored_data)

        if pivot_df.empty:
            logger.warning("Received empty pivot data for summary")
            return "No data available", "No data available", "No data available"

        # Calculate summary statistics
        summary_stats = calculate_pivot_summary_stats(pivot_df)

        # Format the text for each section (showing individual cell maximums, not totals)
        model_text = f"{summary_stats['highest_model']['name']}: {summary_stats['highest_model']['count']} failures in '{summary_stats['highest_model']['test_case']}' at {summary_stats['highest_model']['station']}"
        test_case_text = f"{summary_stats['highest_test_case']['name']}: {summary_stats['highest_test_case']['count']} failures with {summary_stats['highest_test_case']['model']} at {summary_stats['highest_test_case']['station']}"
        station_text = f"{summary_stats['highest_station']['name']}: {summary_stats['highest_station']['count']} failures for '{summary_stats['highest_station']['test_case']}' with {summary_stats['highest_station']['model']}"

        logger.info("Updated summary panel with stats")
        return model_text, test_case_text, station_text

    except Exception as e:
        logger.error(f"Error updating summary panel: {e}")
        return (
            "Error calculating statistics",
            "Error calculating statistics",
            "Error calculating statistics",
        )


@callback(
    Output("collapsed-groups-store", "data"),
    Input("hierarchical-pivot-grid", "cellRendererData"),
    State("collapsed-groups-store", "data"),
    prevent_initial_call=True,
)
def handle_group_toggle(cell_data, current_collapsed_state):
    """Handle clicking on test case headers to collapse/expand model rows."""
    if not cell_data or cell_data.get("action") != "toggle_group":
        return current_collapsed_state

    test_case = cell_data.get("testCase")
    if not test_case:
        return current_collapsed_state

    # Toggle the collapsed state for this test case
    new_state = current_collapsed_state.copy()
    new_state[test_case] = not new_state.get(test_case, False)

    logger.info(
        f"🔽 Toggled {test_case}: {'collapsed' if new_state[test_case] else 'expanded'}"
    )
    return new_state


@callback(
    Output("hierarchical-pivot-grid", "rowData", allow_duplicate=True),
    [Input("collapsed-groups-store", "data"), Input("pivot-data-store", "data")],
    prevent_initial_call=True,
)
def filter_rows_by_collapsed_state(collapsed_state, stored_data):
    """Filter rowData to show/hide model rows based on collapsed test cases."""
    if not stored_data:
        return []

    try:
        # Convert stored data back to DataFrame
        pivot_df = pd.DataFrame(stored_data)
        if pivot_df.empty:
            return []

        # Generate the full hierarchical data
        tree_data = transform_pivot_to_tree_data(pivot_df)

        if not collapsed_state:
            # No test cases collapsed, show everything
            return tree_data

        # Filter out model rows for collapsed test cases
        filtered_data = []
        current_test_case = None

        for row in tree_data:
            if row.get("isTotal"):
                # Always show total row
                filtered_data.append(row)
            elif row.get("isGroup"):
                # This is a test case header
                test_case_name = row.get("hierarchy", "").replace("📁 ", "")
                current_test_case = test_case_name
                # Always show test case headers
                filtered_data.append(row)
            else:
                # This is a model row - only show if test case is not collapsed
                if not collapsed_state.get(current_test_case, False):
                    filtered_data.append(row)

        collapsed_count = sum(1 for v in collapsed_state.values() if v)
        logger.info(
            f"🎯 Filtered grid: {len(filtered_data)} rows shown ({collapsed_count} test cases collapsed)"
        )
        return filtered_data

    except Exception as e:
        logger.error(f"Error filtering rows: {e}")
        return []


# Add clientside callback for collapse/expand functionality
clientside_callback(
    """
    function(n_clicks, gridId) {
        if (!n_clicks) {
            return window.dash_clientside.no_update;
        }

        console.log('🔽 Collapse/expand button clicked:', n_clicks);

        // Get the AG Grid API
        const gridApi = dash_ag_grid.getApi(gridId);
        if (!gridApi) {
            console.warn('⚠️ Could not get AG Grid API');
            return window.dash_clientside.no_update;
        }

        // Toggle between collapse and expand
        const shouldCollapse = (n_clicks % 2 === 1);

        if (shouldCollapse) {
            console.log('🔼 Collapsing all groups...');
            gridApi.collapseAll();
        } else {
            console.log('🔽 Expanding all groups...');
            gridApi.expandAll();
        }

        return window.dash_clientside.no_update;
    }
    """,
    Output("hierarchical-pivot-grid", "id"),
    Input("collapse-expand-btn", "n_clicks"),
    State("hierarchical-pivot-grid", "id"),
    prevent_initial_call=True,
)


# Add callback to update button text
@callback(
    Output("collapse-expand-btn", "children"),
    Input("collapse-expand-btn", "n_clicks"),
    prevent_initial_call=True,
)
def update_button_text(n_clicks):
    """Update button text based on current state."""
    if not n_clicks:
        return "🔽 Collapse All Groups"

    # Toggle text based on click count
    if n_clicks % 2 == 1:
        return "🔼 Expand All Groups"
    else:
        return "🔽 Collapse All Groups"


def load_data_from_file(data_file_path: str) -> Optional[pd.DataFrame]:
    """Load pivot data from a temporary file."""
    try:
        if not os.path.exists(data_file_path):
            logger.warning(f"Data file not found: {data_file_path}")
            return None

        # Load the data (could be JSON or pickle)
        if data_file_path.endswith(".json"):
            with open(data_file_path, "r") as f:
                data = json.load(f)
            return pd.DataFrame(data)
        elif data_file_path.endswith(".pkl"):
            return pd.read_pickle(data_file_path)
        else:
            logger.error(f"Unsupported file format: {data_file_path}")
            return None

    except Exception as e:
        logger.error(f"Error loading data from file: {e}")
        return None


# Add a callback to load data when the app starts with a file argument
@app.callback(
    Output("pivot-data-store", "data"),
    Input("pivot-data-store", "id"),  # Triggers on app start
    prevent_initial_call=False,
)
def load_initial_data(_):
    """Load initial data if a file path was provided as command line argument."""
    if len(sys.argv) > 1:
        data_file_path = sys.argv[1]
        logger.info(f"Loading initial data from: {data_file_path}")

        df = load_data_from_file(data_file_path)
        if df is not None:
            return df.to_dict("records")

    return []


def transform_pivot_to_grouped_data(pivot_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Transform pivot table into data structure for AG Grid Community row grouping.

    Uses AG Grid's built-in rowGroup feature instead of text formatting to create
    collapsible test case groups. This provides native expand/collapse functionality.

    Args:
        pivot_df: DataFrame with columns ['result_FAIL', 'Model', station_columns...]

    Returns:
        List of dictionaries structured for AG Grid row grouping
    """
    if pivot_df.empty:
        return []

    # Sort stations by total failures (highest first) - money columns first!
    station_cols = sort_stations_by_total_errors(pivot_df)
    logger.info(f"🔥 Station columns sorted by failures: {station_cols[:5]}")

    # Convert to flat list for AG Grid row grouping
    grouped_data = []

    for _, row in pivot_df.iterrows():
        row_data = {
            "test_case": row["result_FAIL"],  # This will be the grouping column
            "model": row["Model"],
        }

        # Add station failure data
        for col in station_cols:
            row_data[col] = row[col]

        # Calculate model total for sorting within groups
        model_total = sum(row[col] for col in station_cols)
        row_data["model_total"] = model_total

        grouped_data.append(row_data)

    # Sort by test case total failures, then by model total within each test case
    def sort_key(item):
        test_case = item["test_case"]
        # Calculate test case total
        test_case_total = sum(
            row["model_total"] for row in grouped_data if row["test_case"] == test_case
        )
        # Return tuple for sorting: (test_case_total DESC, model_total DESC)
        return (-test_case_total, -item["model_total"])

    grouped_data.sort(key=sort_key)

    logger.info(f"✅ Created {len(grouped_data)} rows for AG Grid row grouping")
    return grouped_data


def create_grouped_column_definitions(
    station_cols: List[str], analysis_type: str = "failure"
) -> List[Dict[str, Any]]:
    """
    Create AG Grid column definitions optimized for row grouping with collapsible test cases.

    Args:
        station_cols: List of station column names sorted by failure count
        analysis_type: Type of analysis ("failure" or "error")

    Returns:
        List of column definitions for AG Grid with row grouping configured
    """
    column_defs = []

    # Hidden grouping column for test cases - THIS CREATES THE COLLAPSIBLE GROUPS!
    column_defs.append(
        {
            "field": "test_case",
            "rowGroup": True,  # 🔑 KEY: This enables collapsible grouping!
            "hide": True,  # Hide the original column, show in group header
            "headerName": "Test Case",
        }
    )

    # Model column (visible in detail rows)
    column_defs.append(
        {
            "field": "model",
            "headerName": "Model",
            "minWidth": 200,
        }
    )

    # Station columns with failure highlighting (sorted by highest failures first)
    for col in station_cols:
        column_defs.append(
            {
                "field": col,
                "headerName": col,
                "type": "numericColumn",
                "aggFunc": "sum",  # Sum values for group totals
                "valueFormatter": {
                    "function": "params.value === 0 ? '' : params.value"  # Zen zeros
                },
                "width": 80,
            }
        )

    logger.info(f"✅ Created {len(column_defs)} column definitions for grouped display")
    return column_defs


def create_grouped_grid_options(analysis_type: str = "failure") -> Dict[str, Any]:
    """
    Create AG Grid options optimized for collapsible row grouping.

    Args:
        analysis_type: Type of analysis ("failure" or "error")

    Returns:
        Dictionary of AG Grid options for row grouping
    """
    # Dynamic header name based on analysis type
    if analysis_type == "error":
        group_header = "Error Code → Model"
    else:
        group_header = "📁 Test Case → Model"  # Keep the folder icon for familiarity

    return {
        "groupDisplayType": "singleColumn",  # Single column for clean hierarchy
        "autoGroupColumnDef": {
            "headerName": group_header,
            "minWidth": 350,
            "pinned": "left",
            "cellRendererParams": {
                "suppressCount": False,  # Show count in group header (e.g., "Camera Pictures (5)")
                "innerRenderer": "agGroupCellRenderer",
            },
        },
        "groupDefaultExpanded": 1,  # Start with groups expanded (like current behavior)
        "suppressAggFuncInHeader": True,  # Hide aggregation info in headers
        "groupIncludeFooter": False,  # No group footers
        "animateRows": True,  # Smooth expand/collapse animation
        "icons": {
            "groupExpanded": "📁",  # Use folder icon when expanded
            "groupContracted": "📁",  # Use folder icon when collapsed (could use different icon)
        },
    }


if __name__ == "__main__":
    # Run the Dash app
    app.run(
        debug=False,  # Set to False for production
        host="127.0.0.1",
        port=8051,  # Different port from Gradio (7860)
        dev_tools_hot_reload=False,
    )
