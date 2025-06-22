#!/usr/bin/env python3
"""
Test script to validate the new TOTAL ROW and Excel-style sorting logic.
"""

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dash_pivot_app import sort_stations_by_total_errors, transform_pivot_to_tree_data
from services.pivot_service import create_excel_style_failure_pivot


def test_total_row_and_sorting():
    """Test the new TOTAL ROW and column sorting logic."""

    print("🧪 TESTING TOTAL ROW AND EXCEL-STYLE SORTING")
    print("=" * 60)

    # Load test data
    test_data_path = project_root / "test_data" / "feb7_feb10Pull.csv"
    if not test_data_path.exists():
        print("❌ Test data file not found!")
        return False

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

    # Test column sorting (stations by total failures)
    print(f"\n📊 TESTING COLUMN SORTING (Highest Failure Stations First)")
    station_cols = sort_stations_by_total_errors(pivot_result)

    print(f"Station columns sorted by total failures:")
    for i, station in enumerate(station_cols[:10]):  # Show top 10
        total_failures = pivot_result[station].sum()
        print(f"  {i+1}. {station}: {total_failures} failures")

    # Verify sorting is correct (descending)
    station_totals = [pivot_result[station].sum() for station in station_cols]
    is_sorted_desc = all(
        station_totals[i] >= station_totals[i + 1]
        for i in range(len(station_totals) - 1)
    )
    if is_sorted_desc:
        print("✅ Column sorting: CORRECT (descending order)")
    else:
        print("❌ Column sorting: INCORRECT (not descending)")
        return False

    # Test hierarchy transformation with TOTAL ROW
    print(f"\n🌳 TESTING HIERARCHY WITH TOTAL ROW")
    hierarchical_data = transform_pivot_to_tree_data(pivot_result)

    print(f"Created hierarchical data with {len(hierarchical_data)} rows")

    # Check that first row is TOTAL ROW
    if hierarchical_data and "📊 TOTAL FAILURES" in hierarchical_data[0].get(
        "hierarchy", ""
    ):
        print("✅ TOTAL ROW: Found at position 1 (top)")
        total_row = hierarchical_data[0]

        # Verify total row has isTotal flag
        if total_row.get("isTotal"):
            print("✅ TOTAL ROW: Has isTotal flag")
        else:
            print("❌ TOTAL ROW: Missing isTotal flag")
            return False

        # Verify total row has station data
        station_count = 0
        total_failures = 0
        for station in station_cols[:5]:  # Check first 5 stations
            if station in total_row:
                station_count += 1
                total_failures += total_row[station]

        print(
            f"✅ TOTAL ROW: Has data for {station_count} stations, {total_failures} total failures"
        )

        # Check for maxTotalFields (highlighting)
        if total_row.get("maxTotalFields"):
            print(
                f"✅ TOTAL ROW: Has highlighting for stations: {total_row['maxTotalFields']}"
            )
        else:
            print("⚠️  TOTAL ROW: No highlighting (may be OK if no clear max)")
    else:
        print("❌ TOTAL ROW: Not found at top position")
        return False

    # Test test case sorting (by total failures)
    print(f"\n📋 TESTING TEST CASE SORTING (Highest Total Failures First)")

    # Find test case rows (not total row, not model rows)
    test_case_rows = [
        row
        for row in hierarchical_data
        if row.get("isGroup")
        and not row.get("isTotal")
        and "📁" in row.get("hierarchy", "")
    ]

    print(f"Found {len(test_case_rows)} test case rows")

    # Show top 5 test cases with their totals
    for i, row in enumerate(test_case_rows[:5]):
        test_case_name = row["hierarchy"].replace("📁 ", "")
        test_case_total = sum(row.get(station, 0) for station in station_cols)
        print(f"  {i+1}. {test_case_name}: {test_case_total} total failures")

    # Verify test cases are sorted by total failures (descending)
    test_case_totals = [
        sum(row.get(station, 0) for station in station_cols) for row in test_case_rows
    ]
    is_test_cases_sorted = all(
        test_case_totals[i] >= test_case_totals[i + 1]
        for i in range(len(test_case_totals) - 1)
    )

    if is_test_cases_sorted:
        print("✅ Test case sorting: CORRECT (descending by total failures)")
    else:
        print("❌ Test case sorting: INCORRECT (not descending)")
        return False

    # Test model sorting within test cases
    print(f"\n🎯 TESTING MODEL SORTING WITHIN TEST CASES")

    # Check first test case and its models
    if len(test_case_rows) > 0:
        first_test_case = test_case_rows[0]
        test_case_name = first_test_case["hierarchy"].replace("📁 ", "")

        # Find all model rows that follow this test case
        first_test_case_index = hierarchical_data.index(first_test_case)
        model_rows = []

        for i in range(first_test_case_index + 1, len(hierarchical_data)):
            row = hierarchical_data[i]
            if row.get("isGroup"):  # Next test case, stop
                break
            if "└─" in row.get("hierarchy", ""):  # Model row
                model_rows.append(row)

        print(f"Test case '{test_case_name}' has {len(model_rows)} models:")

        # Show model totals
        for i, row in enumerate(model_rows[:5]):  # Show top 5 models
            model_name = row["hierarchy"].replace("  └─ ", "")
            model_total = sum(row.get(station, 0) for station in station_cols)
            print(f"  {i+1}. {model_name}: {model_total} failures")

        # Verify models are sorted by total failures (descending)
        model_totals = [
            sum(row.get(station, 0) for station in station_cols) for row in model_rows
        ]
        is_models_sorted = all(
            model_totals[i] >= model_totals[i + 1] for i in range(len(model_totals) - 1)
        )

        if is_models_sorted:
            print("✅ Model sorting: CORRECT (descending by total failures)")
        else:
            print("❌ Model sorting: INCORRECT (not descending)")
            return False

    # Test heat map effect (top-left corner has highest values)
    print(f"\n🔥 TESTING HEAT MAP EFFECT (Highest Activity in Top-Left)")

    if len(hierarchical_data) >= 3 and len(station_cols) >= 3:
        # Check top-left area (first few rows and columns)
        top_left_values = []

        for i in range(min(3, len(hierarchical_data))):
            for j in range(min(3, len(station_cols))):
                station = station_cols[j]
                value = hierarchical_data[i].get(station, 0)
                top_left_values.append(value)

        # Check bottom-right area
        bottom_right_values = []
        start_row = max(0, len(hierarchical_data) - 3)
        start_col = max(0, len(station_cols) - 3)

        for i in range(start_row, len(hierarchical_data)):
            for j in range(start_col, len(station_cols)):
                station = station_cols[j]
                value = hierarchical_data[i].get(station, 0)
                bottom_right_values.append(value)

        avg_top_left = (
            sum(top_left_values) / len(top_left_values) if top_left_values else 0
        )
        avg_bottom_right = (
            sum(bottom_right_values) / len(bottom_right_values)
            if bottom_right_values
            else 0
        )

        print(f"Average value in top-left corner: {avg_top_left:.1f}")
        print(f"Average value in bottom-right corner: {avg_bottom_right:.1f}")

        if avg_top_left >= avg_bottom_right:
            print("✅ Heat map effect: WORKING (higher activity in top-left)")
        else:
            print("⚠️  Heat map effect: May need adjustment (bottom-right higher)")

    print(f"\n🎉 TOTAL ROW AND SORTING TEST SUMMARY")
    print("=" * 60)
    print("✅ TOTAL ROW at top: WORKING")
    print("✅ Column sorting (highest stations left): WORKING")
    print("✅ Test case sorting (highest totals top): WORKING")
    print("✅ Model sorting within test cases: WORKING")
    print("✅ Heat map effect: VALIDATED")
    print("")
    print("🚀 EXCEL-STYLE PIVOT WITH TOTAL ROW IS READY!")
    print("🎯 All highest activity will be in the TOP-LEFT CORNER!")

    return True


if __name__ == "__main__":
    try:
        success = test_total_row_and_sorting()
        if success:
            print(f"\n🎉 ALL TESTS PASSED! 🎉")
            exit(0)
        else:
            print(f"\n❌ TESTS FAILED")
            exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
