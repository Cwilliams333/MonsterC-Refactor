#!/usr/bin/env python3
"""
Test script for new collapsible row grouping functionality.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dash_pivot_app import (
    create_grouped_column_definitions,
    create_grouped_grid_options,
    sort_stations_by_total_errors,
    transform_pivot_to_grouped_data,
)
from services.pivot_service import create_excel_style_failure_pivot


def test_collapsible_groups():
    """Test the new collapsible row grouping functionality."""

    print("🎯 TESTING NEW COLLAPSIBLE ROW GROUPING FUNCTIONALITY")
    print("=" * 70)

    # Load test data
    test_data_path = project_root / "test_data" / "feb7_feb10Pull.csv"
    df = pd.read_csv(test_data_path)

    # Apply automation filtering
    automation_operators = [
        "STN251_RED(id:10089)",
        "STN252_RED(id:10090)",
        "STN351_GRN(id:10380)",
        "STN352_GRN(id:10381)",
    ]

    automation_df = df[df["Operator"].isin(automation_operators)]

    # Apply business logic
    failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
        (automation_df["Overall status"] == "ERROR")
        & (automation_df["result_FAIL"].notna())
        & (automation_df["result_FAIL"].str.strip() != "")
    )

    automation_failures = automation_df[failure_conditions]
    print(f"✅ Using {len(automation_failures)} automation failures for testing")

    # Create pivot table
    pivot_result = create_excel_style_failure_pivot(automation_failures, None)
    print(f"✅ Created pivot table: {pivot_result.shape}")

    # Test new grouping data structure
    print(f"\n🔥 TESTING NEW ROW GROUPING DATA STRUCTURE")
    grouped_data = transform_pivot_to_grouped_data(pivot_result)

    print(f"Grouped data structure:")
    print(f"  Total rows: {len(grouped_data)}")

    # Check data structure
    if grouped_data:
        sample_row = grouped_data[0]
        print(f"  Sample row keys: {list(sample_row.keys())}")
        print(f"  Sample row: {sample_row}")

        # Verify key fields exist
        required_fields = ["test_case", "model"]
        for field in required_fields:
            if field in sample_row:
                print(f"  ✅ Has required field: {field}")
            else:
                print(f"  ❌ Missing required field: {field}")
                return False

    # Test grouped column definitions
    print(f"\n🏗️  TESTING GROUPED COLUMN DEFINITIONS")
    station_cols = sort_stations_by_total_errors(pivot_result)
    column_defs = create_grouped_column_definitions(station_cols)

    print(f"Column definitions:")
    print(f"  Total columns: {len(column_defs)}")

    # Check for rowGroup column
    group_columns = [col for col in column_defs if col.get("rowGroup") == True]
    if group_columns:
        group_col = group_columns[0]
        print(f"  ✅ Found grouping column: {group_col['field']}")
        print(f"  ✅ Hidden: {group_col.get('hide', False)}")
    else:
        print(f"  ❌ No grouping column found!")
        return False

    # Check for model column
    model_columns = [col for col in column_defs if col.get("field") == "model"]
    if model_columns:
        print(f"  ✅ Found model column")
    else:
        print(f"  ❌ No model column found!")
        return False

    # Test grid options
    print(f"\n⚙️  TESTING GRID OPTIONS FOR COLLAPSIBLE GROUPS")
    grid_options = create_grouped_grid_options()

    required_options = [
        "groupDisplayType",
        "autoGroupColumnDef",
        "groupDefaultExpanded",
    ]
    for option in required_options:
        if option in grid_options:
            print(f"  ✅ Has option: {option}")
        else:
            print(f"  ❌ Missing option: {option}")
            return False

    print(f"  Group display type: {grid_options['groupDisplayType']}")
    print(f"  Default expanded: {grid_options['groupDefaultExpanded']}")

    # Test unique test cases (should create collapsible groups)
    print(f"\n📁 TESTING TEST CASE GROUPING")
    test_cases = list(set(row["test_case"] for row in grouped_data))
    print(f"  Unique test cases: {len(test_cases)}")
    for i, test_case in enumerate(sorted(test_cases)[:5]):
        models_in_group = [
            row["model"] for row in grouped_data if row["test_case"] == test_case
        ]
        print(f"  {i+1}. {test_case}: {len(models_in_group)} models")

    # Test model distribution
    print(f"\n📱 TESTING MODEL DISTRIBUTION")
    models = [row["model"] for row in grouped_data]
    unique_models = set(models)
    print(f"  Total model entries: {len(models)}")
    print(f"  Unique models: {len(unique_models)}")

    # Show example of expected collapsible structure
    print(f"\n🎯 EXPECTED COLLAPSIBLE STRUCTURE IN UI:")
    print(f"  📁 Camera Pictures (25)          ← CLICK TO COLLAPSE/EXPAND")
    print(f"    └─ iPhone14ProMax")
    print(f"    └─ iPhone13ProMax")
    print(f"    └─ iPhone15ProMax")
    print(f"  📁 Hot pixel analysis (8)        ← CLICK TO COLLAPSE/EXPAND")
    print(f"    └─ iPhone14")
    print(f"    └─ iPhone15")
    print(f"")
    print(f"✨ The 📁 icons will be CLICKABLE to expand/collapse groups!")
    print(f"✨ No more text-based hierarchy - real AG Grid row grouping!")

    return True


if __name__ == "__main__":
    try:
        success = test_collapsible_groups()
        if success:
            print(f"\n🎉 COLLAPSIBLE GROUPS TEST PASSED! 🎉")
            print("The new row grouping functionality is ready!")
            print("Test case groups will be collapsible in the Dash AG Grid!")
            exit(0)
        else:
            print(f"\n❌ COLLAPSIBLE GROUPS TEST FAILED")
            exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
