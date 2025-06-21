#!/usr/bin/env python3
"""
HONEST TEST: Create hierarchical display using ONLY AG Grid Community features.
No enterprise row grouping - use custom styling and data structure instead.
"""

import dash
import dash_ag_grid as dag
import pandas as pd
from dash import dcc, html

app = dash.Dash(__name__)


# Create hierarchical display using visual formatting (community-compatible)
def create_hierarchical_data():
    """Create data with visual hierarchy using text formatting"""
    data = [
        # Audio group
        {
            "hierarchy": "📁 Audio",
            "model": "",
            "ST1": 3,
            "ST2": 3,
            "ST3": 1,
            "isGroup": True,
        },
        {
            "hierarchy": "  └─ iPhone14",
            "model": "iPhone14",
            "ST1": 1,
            "ST2": 1,
            "ST3": 0,
            "isGroup": False,
        },
        {
            "hierarchy": "  └─ iPhone15",
            "model": "iPhone15",
            "ST1": 2,
            "ST2": 2,
            "ST3": 1,
            "isGroup": False,
        },
        # Display group
        {
            "hierarchy": "📁 Display",
            "model": "",
            "ST1": 3,
            "ST2": 1,
            "ST3": 3,
            "isGroup": True,
        },
        {
            "hierarchy": "  └─ iPhone14",
            "model": "iPhone14",
            "ST1": 2,
            "ST2": 0,
            "ST3": 1,
            "isGroup": False,
        },
        {
            "hierarchy": "  └─ iPhone15",
            "model": "iPhone15",
            "ST1": 1,
            "ST2": 1,
            "ST3": 2,
            "isGroup": False,
        },
        # WiFi group
        {
            "hierarchy": "📁 WiFi",
            "model": "",
            "ST1": 0,
            "ST2": 3,
            "ST3": 0,
            "isGroup": True,
        },
        {
            "hierarchy": "  └─ iPhone14",
            "model": "iPhone14",
            "ST1": 0,
            "ST2": 3,
            "ST3": 0,
            "isGroup": False,
        },
    ]
    return data


column_defs = [
    {
        "field": "hierarchy",
        "headerName": "Test Case → Model",
        "minWidth": 250,
        "cellStyle": {
            "function": "params.data.isGroup ? {'font-weight': 'bold', 'background-color': '#f0f0f0'} : {'padding-left': '10px'}"
        },
    },
    {"field": "ST1", "headerName": "ST1", "type": "numericColumn", "width": 100},
    {"field": "ST2", "headerName": "ST2", "type": "numericColumn", "width": 100},
    {"field": "ST3", "headerName": "ST3", "type": "numericColumn", "width": 100},
]

app.layout = html.Div(
    [
        html.H1(
            "🎯 COMMUNITY VERSION HIERARCHY TEST",
            style={"textAlign": "center", "color": "green"},
        ),
        html.P(
            "Using visual formatting instead of enterprise row grouping",
            style={"textAlign": "center"},
        ),
        html.Div(
            [
                html.H3("What You Should See:"),
                html.Ul(
                    [
                        html.Li("📁 Audio (bold, highlighted) with total values"),
                        html.Li("  └─ iPhone14 (indented)"),
                        html.Li("  └─ iPhone15 (indented)"),
                        html.Li("📁 Display (bold, highlighted) with total values"),
                        html.Li("  └─ iPhone14 (indented)"),
                        html.Li("  └─ iPhone15 (indented)"),
                        html.Li("📁 WiFi (bold, highlighted) with total values"),
                        html.Li("  └─ iPhone14 (indented)"),
                    ]
                ),
            ],
            style={"margin": "20px", "padding": "20px", "backgroundColor": "#e6ffe6"},
        ),
        dag.AgGrid(
            id="community-hierarchy-grid",
            rowData=create_hierarchical_data(),
            columnDefs=column_defs,
            dashGridOptions={
                "headerHeight": 40,
                "rowHeight": 35,
                "suppressRowClickSelection": True,
                "theme": "ag-theme-alpine",
            },
            defaultColDef={
                "resizable": True,
                "sortable": False,  # Disable sorting to maintain hierarchy
                "filter": False,
            },
            style={"height": "400px", "width": "100%"},
            className="ag-theme-alpine",
        ),
        html.Div(
            [
                html.H3("✅ SUCCESS CRITERIA:"),
                html.Ul(
                    [
                        html.Li("Group rows (📁) appear BOLD and highlighted"),
                        html.Li("Child rows (└─) appear indented"),
                        html.Li("Hierarchy is visually clear"),
                        html.Li("No console errors"),
                        html.Li("Data displays correctly"),
                    ]
                ),
            ],
            style={"margin": "20px", "padding": "20px", "backgroundColor": "#ffffcc"},
        ),
    ]
)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎯 TESTING COMMUNITY VERSION HIERARCHY")
    print("=" * 60)
    print("This uses ONLY community AG Grid features")
    print("No enterprise license required")
    print("URL: http://127.0.0.1:8053")
    print("=" * 60)

    app.run(debug=False, host="127.0.0.1", port=8053)
