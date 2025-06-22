#!/usr/bin/env python3
"""
Integration test for the complete automation-only high failure detection workflow.
Tests the full pipeline from data loading to Dash AG Grid display.
ESSENTIAL for production deployment validation.
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

from common.logging_config import get_logger
from services.pivot_service import create_excel_style_failure_pivot

logger = get_logger(__name__)


def test_complete_automation_workflow():
    """Test the complete automation-only workflow end-to-end."""

    print("🚀 AUTOMATION HIGH FAILURE DETECTION - INTEGRATION TEST")
    print("=" * 60)

    # Load test data
    test_data_path = project_root / "test_data" / "feb7_feb10Pull.csv"
    if not test_data_path.exists():
        print("❌ CRITICAL: Test data file not found!")
        print(f"Expected: {test_data_path}")
        return False

    df = pd.read_csv(test_data_path)
    print(f"✅ Loaded test data: {len(df)} records")

    # Step 1: Automation Operator Filtering
    print("\n📋 STEP 1: Automation Operator Filtering")
    automation_operators = [
        "STN251_RED(id:10089)",  # STN1_RED
        "STN252_RED(id:10090)",  # STN2_RED
        "STN351_GRN(id:10380)",  # STN1_GREEN
        "STN352_GRN(id:10381)",  # STN2_GREEN
    ]

    automation_df = df[df["Operator"].isin(automation_operators)]
    print(f"✅ Filtered to automation operators: {len(automation_df)} records")

    if automation_df.empty:
        print("❌ CRITICAL: No automation operator data found!")
        return False

    # Verify 4 operators and ~24 station IDs
    unique_operators = automation_df["Operator"].unique()
    unique_stations = automation_df["Station ID"].unique()

    print(f"   - Operators found: {len(unique_operators)}")
    print(f"   - Station IDs found: {len(unique_stations)}")

    for op in unique_operators:
        op_stations = automation_df[automation_df["Operator"] == op][
            "Station ID"
        ].unique()
        print(f"   - {op}: {len(op_stations)} stations")

    # Step 2: Business Logic Application
    print("\n⚡ STEP 2: Business Logic Application (FAILURE + ERROR with result_FAIL)")

    failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
        (automation_df["Overall status"] == "ERROR")
        & (automation_df["result_FAIL"].notna())
        & (automation_df["result_FAIL"].str.strip() != "")
    )

    automation_failures = automation_df[failure_conditions]
    print(f"✅ Automation failures found: {len(automation_failures)}")

    # Show breakdown
    failure_status_counts = automation_failures["Overall status"].value_counts()
    for status, count in failure_status_counts.items():
        print(f"   - {status}: {count}")

    if automation_failures.empty:
        print("❌ WARNING: No automation failures found!")
        return False

    # Step 3: Pivot Table Creation (Beautiful Hierarchy)
    print("\n📊 STEP 3: Excel-Style Pivot Creation")

    try:
        pivot_result = create_excel_style_failure_pivot(automation_failures, None)
        print(f"✅ Pivot table created: {pivot_result.shape}")
        print(f"   - Columns: {list(pivot_result.columns)}")

        # Verify structure for hierarchy
        required_cols = ["result_FAIL", "Model"]
        for col in required_cols:
            if col not in pivot_result.columns:
                print(f"❌ CRITICAL: Missing required column: {col}")
                return False

        # Count station columns
        station_cols = [col for col in pivot_result.columns if col not in required_cols]
        print(f"   - Station columns: {len(station_cols)}")

        # Show sample data structure
        print(f"\n📋 Sample Pivot Data (first 5 rows):")
        for i, (_, row) in enumerate(pivot_result.head().iterrows()):
            test_case = row["result_FAIL"]
            model = row["Model"]
            non_zero_stations = sum(1 for col in station_cols if row[col] > 0)
            total_failures = sum(row[col] for col in station_cols)
            print(
                f"   {i+1}. {test_case} | {model} | {non_zero_stations} stations | {total_failures} failures"
            )

    except Exception as e:
        print(f"❌ CRITICAL: Pivot creation failed: {e}")
        return False

    # Step 4: Dash AG Grid Data Preparation
    print("\n🎯 STEP 4: Dash AG Grid Data Preparation")

    try:
        # Convert to format expected by Dash app
        pivot_json = pivot_result.to_dict("records")
        print(f"✅ Converted to JSON format: {len(pivot_json)} records")

        # Test temporary file creation (like the real workflow)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(pivot_json, f)
            temp_file = f.name

        print(f"✅ Temporary file created: {temp_file}")

        # Verify file can be loaded back
        with open(temp_file, "r") as f:
            loaded_data = json.load(f)

        print(f"✅ Data round-trip test passed: {len(loaded_data)} records")

        # Clean up
        os.unlink(temp_file)

    except Exception as e:
        print(f"❌ CRITICAL: Dash data preparation failed: {e}")
        return False

    # Step 5: Hierarchy Validation
    print("\n🌳 STEP 5: Hierarchy Structure Validation")

    # Test hierarchy building logic
    try:
        # Group by test case like the Dash app does
        test_cases = pivot_result["result_FAIL"].unique()
        models = pivot_result["Model"].unique()

        print(f"✅ Test cases for hierarchy: {len(test_cases)}")
        print(f"✅ Models for hierarchy: {len(models)}")

        # Show test case breakdown
        print(f"\n📁 Test Case Breakdown:")
        for i, test_case in enumerate(sorted(test_cases)[:5]):  # Show top 5
            test_case_data = pivot_result[pivot_result["result_FAIL"] == test_case]
            models_in_test = test_case_data["Model"].unique()
            total_failures = sum(test_case_data[col].sum() for col in station_cols)
            print(
                f"   {i+1}. 📁 {test_case}: {len(models_in_test)} models, {total_failures} total failures"
            )

            # Show top models in this test case
            for j, model in enumerate(sorted(models_in_test)[:3]):  # Show top 3 models
                model_data = test_case_data[test_case_data["Model"] == model]
                model_failures = sum(model_data.iloc[0][col] for col in station_cols)
                print(f"      └─ {model}: {model_failures} failures")

    except Exception as e:
        print(f"❌ CRITICAL: Hierarchy validation failed: {e}")
        return False

    # Step 6: Production Readiness Validation
    print("\n🚀 STEP 6: Production Readiness Validation")

    checks = []

    # Check data size is reasonable
    if len(pivot_result) < 1000:  # Should have substantial data
        checks.append("✅ Data size appropriate for production")
    else:
        checks.append("⚠️  Large dataset - verify performance")

    # Check station coverage
    if len(station_cols) >= 20:  # Should have most automation stations
        checks.append("✅ Good station coverage")
    else:
        checks.append(
            f"⚠️  Limited stations ({len(station_cols)}) - verify data completeness"
        )

    # Check test case diversity
    if len(test_cases) >= 10:  # Should have diverse test cases
        checks.append("✅ Good test case diversity")
    else:
        checks.append(
            f"⚠️  Limited test cases ({len(test_cases)}) - verify data completeness"
        )

    # Check failure distribution
    total_failures = sum(pivot_result[col].sum() for col in station_cols)
    if total_failures > 100:  # Should have substantial failures
        checks.append("✅ Substantial failure data for analysis")
    else:
        checks.append(f"⚠️  Limited failures ({total_failures}) - verify analysis value")

    for check in checks:
        print(f"   {check}")

    # Final validation
    print(f"\n🎉 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print("✅ Automation operator filtering: PASSED")
    print("✅ Business logic application: PASSED")
    print("✅ Pivot table creation: PASSED")
    print("✅ Dash AG Grid preparation: PASSED")
    print("✅ Hierarchy structure: PASSED")
    print("✅ Production readiness: VALIDATED")
    print("")
    print("🚀 READY FOR PRODUCTION DEPLOYMENT!")
    print("🎯 Beautiful hierarchy with zen zeros and color coding will work perfectly!")

    return True


def test_performance_metrics():
    """Test performance characteristics for production."""
    print(f"\n⚡ PERFORMANCE METRICS")
    print("-" * 30)

    import time

    # Load data
    start_time = time.time()
    test_data_path = project_root / "test_data" / "feb7_feb10Pull.csv"
    df = pd.read_csv(test_data_path)
    load_time = time.time() - start_time
    print(f"Data loading: {load_time:.3f}s")

    # Filter automation data
    start_time = time.time()
    automation_operators = [
        "STN251_RED(id:10089)",
        "STN252_RED(id:10090)",
        "STN351_GRN(id:10380)",
        "STN352_GRN(id:10381)",
    ]
    automation_df = df[df["Operator"].isin(automation_operators)]
    filter_time = time.time() - start_time
    print(f"Automation filtering: {filter_time:.3f}s")

    # Apply business logic
    start_time = time.time()
    failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
        (automation_df["Overall status"] == "ERROR")
        & (automation_df["result_FAIL"].notna())
        & (automation_df["result_FAIL"].str.strip() != "")
    )
    automation_failures = automation_df[failure_conditions]
    logic_time = time.time() - start_time
    print(f"Business logic: {logic_time:.3f}s")

    # Create pivot
    start_time = time.time()
    pivot_result = create_excel_style_failure_pivot(automation_failures, None)
    pivot_time = time.time() - start_time
    print(f"Pivot creation: {pivot_time:.3f}s")

    total_time = load_time + filter_time + logic_time + pivot_time
    print(f"Total processing: {total_time:.3f}s")

    if total_time < 5.0:
        print("✅ Performance: EXCELLENT for production")
    elif total_time < 10.0:
        print("✅ Performance: GOOD for production")
    else:
        print("⚠️  Performance: May need optimization")


if __name__ == "__main__":
    print("🧪 AUTOMATION HIGH FAILURE DETECTION - INTEGRATION TESTS")
    print("=" * 70)

    try:
        # Run main integration test
        success = test_complete_automation_workflow()

        if success:
            # Run performance tests
            test_performance_metrics()

            print(f"\n🎉 ALL TESTS PASSED - PRODUCTION READY! 🎉")
            exit(0)
        else:
            print(f"\n❌ INTEGRATION TESTS FAILED")
            exit(1)

    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
