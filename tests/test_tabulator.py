#!/usr/bin/env python3
"""
Test script for Tabulator.js collapsible groups functionality.
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(
    __file__
).parent.parent  # Go up one more level since we're in tests/
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))  # Also add project root for relative imports

from services.pivot_service import create_excel_style_failure_pivot
from tabulator_app import create_tabulator_columns, transform_pivot_to_tabulator_tree


def test_tabulator_transformation():
    """Test the Tabulator tree data transformation."""

    print("🧪 TESTING TABULATOR.JS TREE DATA TRANSFORMATION")
    print("=" * 70)

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

    # Transform to Tabulator tree format
    print(f"\n🌳 TESTING TABULATOR TREE TRANSFORMATION")
    tree_data = transform_pivot_to_tabulator_tree(pivot_result)

    print(f"Generated tree data:")
    print(f"  Total parent rows: {len(tree_data)}")

    # Analyze the structure
    total_rows = [row for row in tree_data if row.get("isTotal")]
    group_rows = [row for row in tree_data if row.get("isGroup")]

    print(f"  Total rows: {len(total_rows)}")
    print(f"  Group rows (test cases): {len(group_rows)}")

    # Show sample structure
    print(f"\n📊 SAMPLE TREE STRUCTURE:")
    for i, row in enumerate(tree_data[:3]):
        hierarchy = row.get("hierarchy", "")
        children_count = len(row.get("_children", []))

        if row.get("isTotal"):
            print(f"  {i+1}. [TOTAL] {hierarchy}")
        elif row.get("isGroup"):
            print(f"  {i+1}. [GROUP] {hierarchy} ({children_count} children)")
            # Show first few children
            for j, child in enumerate(row.get("_children", [])[:3]):
                child_hierarchy = child.get("hierarchy", "")
                print(f"       └─ {child_hierarchy}")
            if children_count > 3:
                print(f"       └─ ... and {children_count - 3} more children")
        else:
            print(f"  {i+1}. [OTHER] {hierarchy}")

    # Test column creation
    print(f"\n🏗️  TESTING COLUMN CREATION")
    station_cols = [
        col for col in pivot_result.columns if col not in ["result_FAIL", "Model"]
    ][:5]
    columns = create_tabulator_columns(station_cols)

    print(f"Created {len(columns)} columns:")
    for col in columns:
        print(
            f"  - {col['title']} (field: {col['field']}, width: {col.get('width', 'auto')})"
        )

    # Verify tree structure requirements
    print(f"\n✅ STRUCTURE VERIFICATION:")

    # Check total row
    if total_rows:
        total_row = total_rows[0]
        print(f"  ✅ Total row found: {total_row['hierarchy']}")
        print(
            f"  ✅ Has station data: {len([k for k in total_row.keys() if k.startswith('radi')])} stations"
        )
    else:
        print(f"  ❌ No total row found!")
        return False

    # Check group rows with children
    groups_with_children = [
        row for row in group_rows if len(row.get("_children", [])) > 0
    ]
    if groups_with_children:
        print(f"  ✅ Groups with children: {len(groups_with_children)}")

        sample_group = groups_with_children[0]
        child_count = len(sample_group["_children"])
        print(
            f"  ✅ Sample group '{sample_group['hierarchy']}' has {child_count} children"
        )

        # Check child structure
        sample_child = sample_group["_children"][0]
        child_stations = len([k for k in sample_child.keys() if k.startswith("radi")])
        print(f"  ✅ Sample child has {child_stations} station values")
    else:
        print(f"  ❌ No groups with children found!")
        return False

    # Save sample data for testing
    sample_file = project_root / "sample_tabulator_data.json"
    with open(sample_file, "w") as f:
        json.dump(tree_data, f, indent=2)
    print(f"\n💾 Sample data saved to: {sample_file}")

    print(f"\n🎉 TABULATOR TRANSFORMATION TEST PASSED! 🎉")
    print("The tree data structure is ready for Tabulator.js!")
    print("Next steps:")
    print("1. Run: python3 launch_tabulator.py")
    print("2. Navigate to http://127.0.0.1:5001")
    print("3. Enjoy collapsible groups! 🚀")

    return True


if __name__ == "__main__":
    try:
        success = test_tabulator_transformation()
        if success:
            exit(0)
        else:
            exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
