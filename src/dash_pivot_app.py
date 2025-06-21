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
from dash import Input, Output, callback, dcc, html

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
                        "Interactive hierarchical pivot table with expandable "
                        "test case groups"
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
        html.Div(
            [
                dag.AgGrid(
                    id="hierarchical-pivot-grid",
                    # Grid configuration for Excel-style hierarchy
                    dashGridOptions={
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
                    },
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
                        # Light gray row explanation (for message rows)
                        html.Div(
                            [
                                html.Div(
                                    style={
                                        "width": "20px",
                                        "height": "20px",
                                        "backgroundColor": "#f8f9fa",
                                        "display": "inline-block",
                                        "marginRight": "8px",
                                        "verticalAlign": "middle",
                                        "border": "1px solid #dee2e6",
                                    }
                                ),
                                html.Span(
                                    "Error message rows (blank values, descriptive only)",
                                    style={"verticalAlign": "middle", "fontStyle": "italic"},
                                ),
                            ],
                            style={"marginBottom": "8px"},
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
    row grouping features.

    Args:
        pivot_df: DataFrame with columns ['result_FAIL', 'Model', station_columns...]

    Returns:
        List of dictionaries with visual hierarchy formatting
    """
    if pivot_df.empty:
        return []

    hierarchical_data = []
    station_cols = [
        col for col in pivot_df.columns if col not in ["result_FAIL", "Model"]
    ]

    # Group by test case to create hierarchy
    grouped = pivot_df.groupby("result_FAIL")

    for test_case, group in grouped:
        # Create parent row (group header) with aggregated totals
        group_row = {"hierarchy": f"📁 {test_case}", "isGroup": True}

        # Add aggregated station values and find max for red highlighting
        station_totals = {}
        for col in station_cols:
            total_val = group[col].sum()
            group_row[col] = total_val
            station_totals[col] = total_val

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

        # Create child rows for each model
        for _, row in group.iterrows():
            child_row = {"hierarchy": f"  └─ {row['Model']}", "isGroup": False}

            # Add individual station values
            station_values = {}
            for col in station_cols:
                child_row[col] = row[col]
                station_values[col] = row[col]

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


def transform_error_pivot_to_tree_data(pivot_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Transform error analysis pivot (Model → Error Code → Error Message) into hierarchical display.
    
    Args:
        pivot_df: DataFrame with columns [Model, error_code, error_message, ...station_cols]
    
    Returns:
        List of dictionaries with 3-level visual hierarchy formatting
    """
    if pivot_df.empty:
        return []

    hierarchical_data = []
    station_cols = [
        col for col in pivot_df.columns 
        if col not in ["Model", "error_code", "error_message"]
    ]

    # Group by Model (top level)
    model_grouped = pivot_df.groupby("Model")

    for model, model_group in model_grouped:
        # Create Model parent row (level 1) with aggregated totals
        model_row = {"hierarchy": f"📁 {model}", "isGroup": True}

        # Add aggregated station values for model
        model_totals = {}
        for col in station_cols:
            total_val = model_group[col].sum()
            model_row[col] = total_val
            model_totals[col] = total_val

        # Find highest station total for model (red highlighting)
        if model_totals:
            max_total = max(model_totals.values())
            max_cols = [
                col for col, val in model_totals.items() 
                if val == max_total and val > 0
            ]
            model_row["maxTotalFields"] = max_cols
        else:
            model_row["maxTotalFields"] = []

        hierarchical_data.append(model_row)

        # Group by error_code within this model (level 2)
        code_grouped = model_group.groupby("error_code")

        for error_code, code_group in code_grouped:
            # Create Error Code middle row (level 2) with subtotals
            code_row = {"hierarchy": f"  📂 {error_code}", "isGroup": True}

            # Add aggregated station values for error code
            code_totals = {}
            for col in station_cols:
                total_val = code_group[col].sum()
                code_row[col] = total_val
                code_totals[col] = total_val

            # Find highest station total for error code (red highlighting)
            if code_totals:
                max_total = max(code_totals.values())
                max_cols = [
                    col for col, val in code_totals.items() 
                    if val == max_total and val > 0
                ]
                code_row["maxTotalFields"] = max_cols
            else:
                code_row["maxTotalFields"] = []

            hierarchical_data.append(code_row)

            # Create Error Message child rows (level 3)
            for _, row in code_group.iterrows():
                message_row = {"hierarchy": f"    └─ {row['error_message']}", "isGroup": False, "isMessage": True}

                # Leave station values blank for message rows (since they're 1:1 with error codes)
                # This avoids redundant numbers and keeps the display clean
                for col in station_cols:
                    message_row[col] = ""  # Blank instead of duplicate numbers

                # No highlighting for message rows since they don't show values
                message_row["maxValueFields"] = []

                hierarchical_data.append(message_row)

    return hierarchical_data


def create_column_definitions(data: List[Dict[str, Any]], analysis_type: str = "failure") -> List[Dict[str, Any]]:
    """Create AG Grid column definitions for community version hierarchy."""
    if not data:
        return []

    # Get all possible columns from the data
    all_columns = set()
    for row in data:
        all_columns.update(row.keys())

    # Remove internal columns
    display_columns = [col for col in all_columns if col != "isGroup"]

    column_defs = []

    # Dynamic header name based on analysis type
    if analysis_type == "error":
        header_name = "Model → Error Code → Error Message"
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
                "cellStyle": {
                    "function": "params.data.isGroup ? {'fontWeight': 'bold', 'backgroundColor': '#495057', 'color': '#ffffff', 'textAlign': 'left', 'paddingLeft': '10px'} : params.data.isMessage ? {'paddingLeft': '10px', 'color': '#6c757d', 'textAlign': 'left', 'backgroundColor': '#f8f9fa', 'fontStyle': 'italic'} : {'paddingLeft': '10px', 'color': '#6c757d', 'textAlign': 'left'}"
                },
            }
        )

    # Add station columns with highlighting for max values per row
    station_columns = [col for col in display_columns if col != "hierarchy"]
    for col in station_columns:
        column_defs.append(
            {
                "field": col,
                "headerName": col,
                "type": "numericColumn",
                "width": 120,
                "cellClassRules": {
                    # RED: Highlight max total per test case (group rows)
                    "max-total-highlight": f"params.data.isGroup && params.data.maxTotalFields && params.data.maxTotalFields.includes('{col}') && params.value > 0",
                    # YELLOW: Highlight max value per model (individual rows)
                    "max-value-highlight": f"params.data.maxField === '{col}' && !params.data.isGroup && params.value > 0",
                },
                "cellStyle": {
                    "function": "params.data.isGroup ? {'textAlign': 'center', 'fontWeight': 'bold', 'backgroundColor': '#e9ecef'} : params.data.isMessage ? {'textAlign': 'center', 'backgroundColor': '#f8f9fa', 'color': '#6c757d', 'fontStyle': 'italic'} : {'textAlign': 'center'}"
                },
            }
        )

    logger.info(
        f"Created {len(column_defs)} column definitions for community hierarchy"
    )
    return column_defs


@callback(
    [
        Output("hierarchical-pivot-grid", "rowData"),
        Output("hierarchical-pivot-grid", "columnDefs"),
    ],
    Input("pivot-data-store", "data"),
)
def update_grid(stored_data):
    """Update the AG Grid with new pivot data."""
    if not stored_data:
        return [], []

    try:
        # Convert stored data back to DataFrame
        pivot_df = pd.DataFrame(stored_data)

        if pivot_df.empty:
            logger.warning("Received empty pivot data")
            return [], []

        # Detect analysis type based on columns
        if "error_code" in pivot_df.columns and "error_message" in pivot_df.columns:
            # 3-level error analysis
            tree_data = transform_error_pivot_to_tree_data(pivot_df)
            column_defs = create_column_definitions(tree_data, analysis_type="error")
        else:
            # 2-level failure analysis
            tree_data = transform_pivot_to_tree_data(pivot_df)
            column_defs = create_column_definitions(tree_data, analysis_type="failure")

        logger.info(
            f"Updated grid with {len(tree_data)} rows and {len(column_defs)} columns"
        )
        return tree_data, column_defs

    except Exception as e:
        logger.error(f"Error updating grid: {e}")
        return [], []


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


if __name__ == "__main__":
    # Run the Dash app
    app.run(
        debug=False,  # Set to False for production
        host="127.0.0.1",
        port=8051,  # Different port from Gradio (7860)
        dev_tools_hot_reload=False,
    )
