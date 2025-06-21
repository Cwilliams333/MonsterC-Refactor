#!/usr/bin/env python3
"""
Comprehensive test to validate AG Grid hierarchical display actually works.
This creates a minimal standalone test to verify row grouping renders properly.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import dash
import dash_ag_grid as dag
import pandas as pd
from dash import Input, Output, State, callback, dcc, html

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

app = dash.Dash(__name__)

# Test data that matches our real scenario
test_data = [
    {"testCase": "Audio", "model": "iPhone14", "ST1": 1, "ST2": 1, "ST3": 0},
    {"testCase": "Audio", "model": "iPhone15", "ST1": 0, "ST2": 2, "ST3": 1},
    {"testCase": "Display", "model": "iPhone14", "ST1": 2, "ST2": 0, "ST3": 1},
    {"testCase": "Display", "model": "iPhone15", "ST1": 1, "ST2": 1, "ST3": 2},
    {"testCase": "WiFi", "model": "iPhone14", "ST1": 0, "ST2": 3, "ST3": 0},
]

column_defs = [
    {
        "field": "testCase",
        "headerName": "Test Case",
        "rowGroup": True,
        "hide": True,
        "aggFunc": "count",
    },
    {"field": "model", "headerName": "Model", "width": 150},
    {
        "field": "ST1",
        "headerName": "ST1",
        "type": "numericColumn",
        "aggFunc": "sum",
        "width": 100,
    },
    {
        "field": "ST2",
        "headerName": "ST2",
        "type": "numericColumn",
        "aggFunc": "sum",
        "width": 100,
    },
    {
        "field": "ST3",
        "headerName": "ST3",
        "type": "numericColumn",
        "aggFunc": "sum",
        "width": 100,
    },
]

app.layout = html.Div(
    [
        html.H1("🧪 AG Grid Hierarchy Test", style={"textAlign": "center"}),
        html.P(
            "Testing if row grouping actually creates visual hierarchy",
            style={"textAlign": "center"},
        ),
        html.Div(
            [
                html.H3("Expected Result:"),
                html.Ul(
                    [
                        html.Li("Should see ► Audio (2) as expandable group"),
                        html.Li("Under Audio: iPhone14 and iPhone15 as child rows"),
                        html.Li("Should see ► Display (2) as expandable group"),
                        html.Li("Under Display: iPhone14 and iPhone15 as child rows"),
                        html.Li("Should see ► WiFi (1) as expandable group"),
                        html.Li("Under WiFi: iPhone14 as child row"),
                        html.Li("Group rows should show aggregated totals"),
                    ]
                ),
            ],
            style={"margin": "20px", "padding": "20px", "backgroundColor": "#f0f0f0"},
        ),
        dag.AgGrid(
            id="hierarchy-test-grid",
            rowData=test_data,
            columnDefs=column_defs,
            dashGridOptions={
                "groupDisplayType": "groupRows",
                "groupDefaultExpanded": -1,  # Auto-expand to verify hierarchy
                "autoGroupColumnDef": {
                    "headerName": "Test Case → Model",
                    "minWidth": 250,
                    "cellRendererParams": {
                        "suppressCount": False,  # Show count to verify grouping
                    },
                },
                "animateRows": True,
                "theme": "ag-theme-alpine",
            },
            defaultColDef={"resizable": True, "sortable": True, "filter": True},
            style={"height": "500px", "width": "100%"},
            className="ag-theme-alpine",
        ),
        html.Div(
            [
                html.H3("Validation Checklist:"),
                html.Ul(
                    [
                        html.Li(
                            "✓ Can you see expandable arrows (►) next to test cases?"
                        ),
                        html.Li("✓ Are models indented under their test case groups?"),
                        html.Li("✓ Do group headers show aggregated totals?"),
                        html.Li("✓ Can you collapse/expand groups by clicking arrows?"),
                        html.Li(
                            "✓ Does the 'Test Case → Model' column show hierarchy?"
                        ),
                    ]
                ),
            ],
            style={"margin": "20px", "padding": "20px", "backgroundColor": "#ffe6e6"},
        ),
    ]
)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 STARTING AG GRID HIERARCHY VALIDATION TEST")
    print("=" * 60)
    print(f"Test data: {len(test_data)} rows")
    print(f"Expected groups: Audio (2), Display (2), WiFi (1)")
    print(f"URL: http://127.0.0.1:8052")
    print("=" * 60)

    app.run(
        debug=False,
        host="127.0.0.1",
        port=8052,  # Different port to avoid conflicts
        dev_tools_hot_reload=False,
    )
