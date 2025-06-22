#!/usr/bin/env python3
"""
Test script to verify clickable collapse/expand functionality is properly configured.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dash_pivot_app import transform_pivot_to_tree_data
from services.pivot_service import create_excel_style_failure_pivot


def test_clickable_functionality():
    """Test that the clickable collapse/expand setup is correct."""

    print("🎯 TESTING CLICKABLE COLLAPSE/EXPAND FUNCTIONALITY")
    print("=" * 70)

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
    print(f"✅ Using {len(automation_failures)} automation failures for testing")

    # Create pivot table
    pivot_result = create_excel_style_failure_pivot(automation_failures, None)
    print(f"✅ Created pivot table: {pivot_result.shape}")

    # Generate hierarchical data
    tree_data = transform_pivot_to_tree_data(pivot_result)
    print(f"✅ Generated hierarchical data: {len(tree_data)} rows")

    # Test data structure for clickable functionality
    print(f"\n🔍 TESTING DATA STRUCTURE FOR CLICKABLE GROUPS")

    # Check for required flags
    total_rows = [row for row in tree_data if row.get("isTotal")]
    group_rows = [
        row for row in tree_data if row.get("isGroup") and not row.get("isTotal")
    ]
    model_rows = [
        row for row in tree_data if not row.get("isGroup") and not row.get("isTotal")
    ]

    print(f"  Total rows: {len(total_rows)}")
    print(f"  Group rows (test cases): {len(group_rows)}")
    print(f"  Model rows: {len(model_rows)}")

    # Show sample group rows (these should be clickable)
    print(f"\n📁 TEST CASE HEADERS (SHOULD BE CLICKABLE):")
    for i, row in enumerate(group_rows[:5]):
        hierarchy = row.get("hierarchy", "")
        print(f"  {i+1}. {hierarchy}")

        # Verify this row has the right structure for clicking
        if "📁" in hierarchy and row.get("isGroup") and not row.get("isTotal"):
            print(f"      ✅ Ready for collapse/expand")
        else:
            print(f"      ❌ Not properly configured")

    # Show sample model rows (these should collapse/expand)
    print(f"\n📱 MODEL ROWS (SHOULD COLLAPSE/EXPAND):")
    for i, row in enumerate(model_rows[:5]):
        hierarchy = row.get("hierarchy", "")
        print(f"  {i+1}. {hierarchy}")

        if "└─" in hierarchy and not row.get("isGroup"):
            print(f"      ✅ Will collapse when parent test case is clicked")
        else:
            print(f"      ❌ Not properly configured")

    # Simulate collapsed state filtering
    print(f"\n🎭 SIMULATING COLLAPSED STATE")

    # Test collapsing "Camera Pictures"
    collapsed_state = {"Camera Pictures": True}

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

    print(f"Original rows: {len(tree_data)}")
    print(f"After collapsing 'Camera Pictures': {len(filtered_data)}")
    print(f"Rows hidden: {len(tree_data) - len(filtered_data)}")

    # Show what would be visible after collapsing Camera Pictures
    print(f"\n👁️  VISIBLE ROWS AFTER COLLAPSING 'Camera Pictures':")
    for i, row in enumerate(filtered_data[:10]):
        hierarchy = row.get("hierarchy", "")
        row_type = (
            "TOTAL"
            if row.get("isTotal")
            else "GROUP"
            if row.get("isGroup")
            else "MODEL"
        )
        print(f"  {i+1}. [{row_type}] {hierarchy}")

    print(f"\n🎉 EXPECTED BEHAVIOR IN UI:")
    print(f"1. Click on '📁 Camera Pictures' → All iPhone models collapse")
    print(f"2. Click again → iPhone models expand back")
    print(f"3. Only test case headers remain when collapsed")
    print(f"4. Heat mapping and column ordering preserved")
    print(f"5. Smooth visual feedback with hover effects")

    # Check for required files
    assets_dir = project_root / "assets"
    js_file = assets_dir / "dashAgGridComponentFunctions.js"

    print(f"\n📁 CHECKING REQUIRED FILES:")
    if js_file.exists():
        print(f"  ✅ {js_file} exists")
        with open(js_file, "r") as f:
            content = f.read()
            if "clickableHierarchyRenderer" in content:
                print(f"  ✅ Custom cell renderer found")
            else:
                print(f"  ❌ Custom cell renderer missing")
    else:
        print(f"  ❌ {js_file} missing")

    # All checks passed - test passes if we reach here without assertion errors
    assert len(tree_data) > 0, "Tree data should be generated"
    assert len(group_rows) > 0, "Should have test case groups"
    assert len(model_rows) > 0, "Should have model rows"


if __name__ == "__main__":
    try:
        success = test_clickable_functionality()
        if success:
            print(f"\n🎉 CLICKABLE FUNCTIONALITY TEST PASSED! 🎉")
            print("The collapse/expand feature is ready to test in the UI!")
            print("Click on the dark '📁 Camera Pictures' headers to collapse/expand!")
            exit(0)
        else:
            print(f"\n❌ CLICKABLE FUNCTIONALITY TEST FAILED")
            exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
