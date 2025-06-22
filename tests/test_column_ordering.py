#!/usr/bin/env python3
"""
Test script specifically for column ordering in the Dash AG Grid.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dash_pivot_app import create_column_definitions, transform_pivot_to_tree_data
from services.pivot_service import create_excel_style_failure_pivot


def test_column_ordering():
    """Test that columns appear in correct order (highest failures first)."""

    print("🔍 TESTING COLUMN ORDERING (Money Columns First)")
    print("=" * 60)

    # Load test data
    test_data_path = project_root / "tests" / "sample_test_data.csv"
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
    print(f"✅ Using {len(automation_failures)} automation failures")

    # Create pivot table
    pivot_result = create_excel_style_failure_pivot(automation_failures, None)
    print(f"✅ Created pivot table: {pivot_result.shape}")

    # Transform to hierarchical data
    hierarchical_data = transform_pivot_to_tree_data(pivot_result)
    print(f"✅ Created hierarchical data: {len(hierarchical_data)} rows")

    # Find the TOTAL FAILURES row to check our data
    total_row = next(
        (
            row
            for row in hierarchical_data
            if "📊 TOTAL FAILURES" in str(row.get("hierarchy", ""))
        ),
        None,
    )

    if total_row:
        print(f"\n📊 TOTAL FAILURES ROW FOUND")

        # Get station data from total row
        internal_columns = {
            "isGroup",
            "isTotal",
            "maxField",
            "maxTotalFields",
            "maxValueFields",
            "hierarchy",
            "Grand_Total",  # Exclude computed Grand Total column
        }
        station_data = {
            col: total_row[col]
            for col in total_row.keys()
            if col not in internal_columns
        }

        print(f"Station data from total row:")
        for col, value in sorted(
            station_data.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"  {col}: {value}")

        # Test column definition creation
        print(f"\n🏗️  TESTING COLUMN DEFINITION CREATION")
        column_defs = create_column_definitions(
            hierarchical_data, analysis_type="failure"
        )

        # Extract station column order from column definitions
        station_cols_from_defs = []
        for col_def in column_defs:
            field = col_def.get("field")
            if field and field != "hierarchy":
                station_cols_from_defs.append(field)

        print(f"Column order from AG Grid definitions:")
        for i, col in enumerate(station_cols_from_defs[:10]):
            value = station_data.get(col, 0)
            print(f"  {i+1}. {col}: {value} failures")

        # Verify that the highest failure station is first
        if station_cols_from_defs:
            first_station = station_cols_from_defs[0]
            first_value = station_data.get(first_station, 0)

            # Check if this is the highest value
            max_station = max(station_data.keys(), key=lambda k: station_data[k])
            max_value = station_data[max_station]

            print(f"\n🎯 VERIFICATION")
            print(f"First column: {first_station} ({first_value} failures)")
            print(f"Highest station: {max_station} ({max_value} failures)")

            if first_station == max_station:
                print("✅ COLUMN ORDERING: CORRECT (highest failures station is first)")
                # All checks passed - test passes if we reach here without assertion errors
                assert (
                    first_station == max_station
                ), f"Highest failure station {max_station} should be first column"
                assert len(column_defs) > 0, "Column definitions should be created"
                assert (
                    len(hierarchical_data) > 0
                ), "Hierarchical data should be generated"
            else:
                print(
                    "❌ COLUMN ORDERING: INCORRECT (highest failures station is not first)"
                )
                print(f"Expected {max_station} to be first, but got {first_station}")
                assert (
                    False
                ), f"Expected {max_station} to be first column, but got {first_station}"
        else:
            print("❌ No station columns found in definitions")
            assert False, "No station columns found in definitions"
    else:
        print("❌ TOTAL FAILURES row not found")
        assert False, "TOTAL FAILURES row not found in hierarchical data"


if __name__ == "__main__":
    try:
        success = test_column_ordering()
        if success:
            print(f"\n🎉 COLUMN ORDERING TEST PASSED! 🎉")
            exit(0)
        else:
            print(f"\n❌ COLUMN ORDERING TEST FAILED")
            exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
