#!/usr/bin/env python3
"""
End-to-end test to verify column ordering works with actual automation filtering.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dash_pivot_app import (create_column_definitions,
                            transform_pivot_to_tree_data)
from services.pivot_service import create_excel_style_failure_pivot


def test_end_to_end_column_order():
    """Test the complete automation workflow with column ordering."""

    print("🔬 END-TO-END COLUMN ORDERING TEST")
    print("Simulating exact workflow from 'Automation High Failures' button")
    print("=" * 70)

    # Load test data
    test_data_path = project_root / "test_data" / "feb7_feb10Pull.csv"
    df = pd.read_csv(test_data_path)
    print(f"✅ Loaded {len(df)} total records")

    # STEP 1: Apply automation filtering (exactly like gradio_app.py)
    automation_operators = [
        "STN251_RED(id:10089)",  # STN1_RED
        "STN252_RED(id:10090)",  # STN2_RED
        "STN351_GRN(id:10380)",  # STN1_GREEN
        "STN352_GRN(id:10381)",  # STN2_GREEN
    ]

    automation_df = df[df["Operator"].isin(automation_operators)]
    print(f"✅ Automation filtering: {len(automation_df)} records")

    # STEP 2: Apply business logic (exactly like gradio_app.py)
    failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
        (automation_df["Overall status"] == "ERROR")
        & (automation_df["result_FAIL"].notna())
        & (automation_df["result_FAIL"].str.strip() != "")
    )

    automation_failures = automation_df[failure_conditions]
    print(f"✅ Business logic filtering: {len(automation_failures)} failures")

    # STEP 3: Create pivot (exactly like gradio_app.py calls)
    pivot_result = create_excel_style_failure_pivot(automation_failures, None)
    print(f"✅ Pivot creation: {pivot_result.shape}")

    # STEP 4: Transform to hierarchical data (exactly like dash_pivot_app.py)
    hierarchical_data = transform_pivot_to_tree_data(pivot_result)
    print(f"✅ Hierarchical transformation: {len(hierarchical_data)} rows")

    # STEP 5: Create column definitions (exactly like dash_pivot_app.py)
    column_defs = create_column_definitions(hierarchical_data, analysis_type="failure")
    print(f"✅ Column definitions: {len(column_defs)} columns")

    # STEP 6: Extract and verify column order
    print(f"\n📊 COLUMN ORDER ANALYSIS")

    # Find hierarchy column
    hierarchy_col = next(
        (col for col in column_defs if col.get("field") == "hierarchy"), None
    )
    if hierarchy_col:
        print(f"✅ Hierarchy column: {hierarchy_col['headerName']}")

    # Find station columns in order
    station_cols = [col for col in column_defs if col.get("field") != "hierarchy"]
    print(f"✅ Station columns: {len(station_cols)}")

    # Show first 10 columns with their expected values
    total_row = next(
        (
            row
            for row in hierarchical_data
            if "📊 TOTAL FAILURES" in str(row.get("hierarchy", ""))
        ),
        None,
    )

    if total_row:
        print(f"\n🎯 COLUMN ORDER VERIFICATION")
        print("Expected column order (highest failures first):")

        for i, col_def in enumerate(station_cols[:10]):
            field = col_def["field"]
            value = total_row.get(field, 0)
            print(f"  {i+1}. {field}: {value} failures")

        # Verify the first station column is the highest
        if station_cols:
            first_field = station_cols[0]["field"]
            first_value = total_row.get(first_field, 0)

            # Find the actual highest station
            station_values = {
                field: total_row.get(field, 0)
                for field in [col["field"] for col in station_cols]
            }
            max_field = max(station_values.keys(), key=lambda k: station_values[k])
            max_value = station_values[max_field]

            print(f"\n🔍 VERIFICATION")
            print(f"First column: {first_field} ({first_value} failures)")
            print(f"Highest station: {max_field} ({max_value} failures)")

            if first_field == max_field:
                print("✅ SUCCESS: Highest failure station is first column!")

                # Show what the user should see in the UI
                print(f"\n🖥️  EXPECTED UI BEHAVIOR")
                print(f"In the Dash AG Grid, you should see:")
                print(f"1. First column after 'Test Case → Model': {first_field}")
                print(
                    f"2. TOTAL FAILURES row should show {first_value} highlighted in blue"
                )
                print(
                    f"3. Column order: {' → '.join([col['field'] for col in station_cols[:5]])}"
                )

                return True
            else:
                print("❌ FAILED: Wrong column order!")
                return False
        else:
            print("❌ No station columns found")
            return False
    else:
        print("❌ TOTAL FAILURES row not found")
        return False


if __name__ == "__main__":
    try:
        success = test_end_to_end_column_order()
        if success:
            print(f"\n🎉 END-TO-END TEST PASSED! 🎉")
            print(
                "The automation high failures button should show correct column ordering!"
            )
            exit(0)
        else:
            print(f"\n❌ END-TO-END TEST FAILED")
            exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
