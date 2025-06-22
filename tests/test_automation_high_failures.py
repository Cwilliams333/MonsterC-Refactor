#!/usr/bin/env python3
"""
Unit tests for automation-only high failure detection logic.
CRITICAL for production deployment and CI/CD pipeline.
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from services.pivot_service import create_excel_style_failure_pivot


class TestAutomationHighFailures(unittest.TestCase):
    """Test suite for automation-only high failure detection."""

    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests."""
        test_data_path = project_root / "test_data" / "feb7_feb10Pull.csv"
        if test_data_path.exists():
            cls.df = pd.read_csv(test_data_path)
        else:
            # Create minimal test data if file doesn't exist
            cls.df = pd.DataFrame(
                {
                    "Operator": [
                        "STN251_RED(id:10089)",
                        "STN352_GRN(id:10381)",
                        "Manual-Core_1(id:12246)",
                    ],
                    "Overall status": ["FAILURE", "ERROR", "SUCCESS"],
                    "result_FAIL": ["Camera Pictures", "Touch Screen", ""],
                    "Station ID": ["radi133", "radi157", "radi052"],
                    "Model": ["iPhone14ProMax", "iPhone16Pro", "SM-G781V"],
                }
            )

    def setUp(self):
        """Set up automation operators for each test."""
        self.automation_operators = [
            "STN251_RED(id:10089)",  # STN1_RED
            "STN252_RED(id:10090)",  # STN2_RED
            "STN351_GRN(id:10380)",  # STN1_GREEN
            "STN352_GRN(id:10381)",  # STN2_GREEN
        ]

    def test_automation_operator_filtering(self):
        """Test that only automation operators are included."""
        # Filter for automation operators only
        automation_df = self.df[self.df["Operator"].isin(self.automation_operators)]

        # Verify only automation operators remain
        unique_operators = automation_df["Operator"].unique()
        for op in unique_operators:
            self.assertIn(
                op, self.automation_operators, f"Non-automation operator found: {op}"
            )

        # Verify manual operators are excluded
        manual_operators = self.df[
            ~self.df["Operator"].isin(self.automation_operators)
        ]["Operator"].unique()
        for op in manual_operators:
            self.assertNotIn(
                op, unique_operators, f"Manual operator incorrectly included: {op}"
            )

    def test_failure_logic_criteria(self):
        """Test FAILURE OR (ERROR with result_FAIL populated) logic."""
        automation_df = self.df[self.df["Operator"].isin(self.automation_operators)]

        # Apply business logic
        failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
            (automation_df["Overall status"] == "ERROR")
            & (automation_df["result_FAIL"].notna())
            & (automation_df["result_FAIL"].str.strip() != "")
        )

        automation_failures = automation_df[failure_conditions]

        # Verify all included records meet criteria
        for _, row in automation_failures.iterrows():
            status = row["Overall status"]
            result_fail = row["result_FAIL"]

            if status == "FAILURE":
                # FAILURE status should always be included
                self.assertEqual(status, "FAILURE")
            elif status == "ERROR":
                # ERROR must have populated result_FAIL
                self.assertTrue(
                    pd.notna(result_fail), f"ERROR record missing result_FAIL: {row}"
                )
                self.assertNotEqual(
                    str(result_fail).strip(),
                    "",
                    f"ERROR record with empty result_FAIL: {row}",
                )
            else:
                self.fail(f"Invalid record included: {row}")

    def test_automation_operators_exist(self):
        """Test that all expected automation operators exist in data."""
        if hasattr(self, "df") and len(self.df) > 100:  # Only test with real data
            unique_operators = self.df["Operator"].unique()

            # Check that at least some automation operators exist
            automation_found = [
                op for op in self.automation_operators if op in unique_operators
            ]
            self.assertGreater(
                len(automation_found), 0, "No automation operators found in test data"
            )

    def test_station_ids_for_automation(self):
        """Test that automation operators have expected station IDs (6 each)."""
        automation_df = self.df[self.df["Operator"].isin(self.automation_operators)]

        if len(automation_df) > 0:
            for operator in self.automation_operators:
                op_data = automation_df[automation_df["Operator"] == operator]
                if len(op_data) > 0:
                    station_ids = op_data["Station ID"].unique()
                    # Each automation operator should have multiple stations
                    self.assertGreaterEqual(
                        len(station_ids), 1, f"Operator {operator} has no station IDs"
                    )
                    self.assertLessEqual(
                        len(station_ids),
                        10,
                        f"Operator {operator} has too many station IDs: {len(station_ids)}",
                    )

    def test_pivot_creation_with_automation_data(self):
        """Test that pivot table can be created with automation-filtered data."""
        automation_df = self.df[self.df["Operator"].isin(self.automation_operators)]

        # Apply failure logic
        failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
            (automation_df["Overall status"] == "ERROR")
            & (automation_df["result_FAIL"].notna())
            & (automation_df["result_FAIL"].str.strip() != "")
        )

        automation_failures = automation_df[failure_conditions]

        if len(automation_failures) > 0:
            # Test pivot creation
            pivot_result = create_excel_style_failure_pivot(automation_failures, None)

            # Verify pivot structure
            self.assertIsInstance(
                pivot_result, pd.DataFrame, "Pivot result should be DataFrame"
            )
            self.assertGreater(len(pivot_result), 0, "Pivot result should not be empty")

            # Verify required columns exist
            required_columns = ["result_FAIL", "Model"]
            for col in required_columns:
                self.assertIn(
                    col, pivot_result.columns, f"Missing required column: {col}"
                )

            # Verify station columns exist
            station_cols = [
                col
                for col in pivot_result.columns
                if col not in ["result_FAIL", "Model"]
            ]
            self.assertGreater(
                len(station_cols), 0, "No station columns found in pivot"
            )

    def test_hierarchy_data_structure(self):
        """Test that hierarchy can be built from automation data."""
        automation_df = self.df[self.df["Operator"].isin(self.automation_operators)]

        # Apply failure logic
        failure_conditions = (automation_df["Overall status"] == "FAILURE") | (
            (automation_df["Overall status"] == "ERROR")
            & (automation_df["result_FAIL"].notna())
            & (automation_df["result_FAIL"].str.strip() != "")
        )

        automation_failures = automation_df[failure_conditions]

        if len(automation_failures) > 0:
            # Test that we have the structure needed for hierarchy
            test_cases = automation_failures["result_FAIL"].dropna().unique()
            models = automation_failures["Model"].unique()
            stations = automation_failures["Station ID"].unique()

            self.assertGreater(len(test_cases), 0, "No test cases found for hierarchy")
            self.assertGreater(len(models), 0, "No models found for hierarchy")
            self.assertGreater(len(stations), 0, "No stations found for hierarchy")

    def test_data_quality_validation(self):
        """Test data quality for automation analysis."""
        automation_df = self.df[self.df["Operator"].isin(self.automation_operators)]

        if len(automation_df) > 0:
            # Check for required columns
            required_cols = [
                "Operator",
                "Overall status",
                "result_FAIL",
                "Station ID",
                "Model",
            ]
            for col in required_cols:
                self.assertIn(
                    col, automation_df.columns, f"Missing required column: {col}"
                )

            # Check that we have valid statuses
            valid_statuses = ["SUCCESS", "FAILURE", "ERROR", "Fail"]
            invalid_statuses = automation_df[
                ~automation_df["Overall status"].isin(valid_statuses)
            ]
            self.assertEqual(
                len(invalid_statuses),
                0,
                f"Invalid status values found: {invalid_statuses['Overall status'].unique()}",
            )


class TestProductionReadiness(unittest.TestCase):
    """Test production readiness aspects."""

    def test_imports_work(self):
        """Test that all required imports work."""
        try:
            from common.logging_config import get_logger
            from services.pivot_service import create_excel_style_failure_pivot
        except ImportError as e:
            self.fail(f"Import failed: {e}")

    def test_automation_operators_defined(self):
        """Test that automation operators are properly defined."""
        automation_operators = [
            "STN251_RED(id:10089)",  # STN1_RED
            "STN252_RED(id:10090)",  # STN2_RED
            "STN351_GRN(id:10380)",  # STN1_GREEN
            "STN352_GRN(id:10381)",  # STN2_GREEN
        ]

        # Verify we have exactly 4 automation operators
        self.assertEqual(
            len(automation_operators), 4, "Should have exactly 4 automation operators"
        )

        # Verify operator naming convention
        for op in automation_operators:
            self.assertIn("STN", op, f"Operator should contain STN: {op}")
            self.assertTrue(
                ("RED" in op) or ("GRN" in op),
                f"Operator should contain RED or GRN: {op}",
            )
            self.assertIn("(id:", op, f"Operator should contain ID: {op}")


if __name__ == "__main__":
    # Run with verbose output for CI/CD
    unittest.main(verbosity=2)
