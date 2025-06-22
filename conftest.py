"""
pytest configuration file for MonsterC project.

This file configures pytest to properly handle the project's module structure
and import paths.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src directory to Python path for all tests
project_root = Path(__file__).parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Set up pytest configuration
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom settings."""
    pass


def pytest_collection_modifyitems(config, items):
    """Modify test items after collection."""
    pass


@pytest.fixture
def sample_test_data():
    """Provide sample test data for tests that need CSV data."""
    return pd.DataFrame(
        {
            "Date": ["2024-02-07"] * 50 + ["2024-02-08"] * 50,
            "Station ID": ["radi135"] * 25
            + ["radi136"] * 25
            + ["radi135"] * 25
            + ["radi136"] * 25,
            "Model": ["iPhone14ProMax"] * 20
            + ["iPhone15Pro"] * 30
            + ["iPhone14ProMax"] * 20
            + ["iPhone15Pro"] * 30,
            "result_FAIL": ["6A-Display Fail"] * 30
            + ["5A-Camera Pictures"] * 20
            + ["6A-Display Fail"] * 30
            + ["5A-Camera Pictures"] * 20,
            "Operator": ["STN251_RED(id:10089)"] * 25
            + ["STN252_RED(id:10090)"] * 25
            + ["STN351_GRN(id:10380)"] * 25
            + ["STN352_GRN(id:10381)"] * 25,
            "Overall status": ["FAILURE"] * 80 + ["ERROR"] * 20,
        }
    )


def get_test_data_path():
    """Get the path to test data, create sample data if not found."""
    test_data_path = project_root / "test_data" / "feb7_feb10Pull.csv"

    if not test_data_path.exists():
        # Create test_data directory if it doesn't exist
        test_data_path.parent.mkdir(exist_ok=True)

        # Create sample data and save it
        sample_data = pd.DataFrame(
            {
                "Date": ["2024-02-07"] * 50 + ["2024-02-08"] * 50,
                "Station ID": ["radi135"] * 25
                + ["radi136"] * 25
                + ["radi135"] * 25
                + ["radi136"] * 25,
                "Model": ["iPhone14ProMax"] * 20
                + ["iPhone15Pro"] * 30
                + ["iPhone14ProMax"] * 20
                + ["iPhone15Pro"] * 30,
                "result_FAIL": ["6A-Display Fail"] * 30
                + ["5A-Camera Pictures"] * 20
                + ["6A-Display Fail"] * 30
                + ["5A-Camera Pictures"] * 20,
                "Operator": ["STN251_RED(id:10089)"] * 25
                + ["STN252_RED(id:10090)"] * 25
                + ["STN351_GRN(id:10380)"] * 25
                + ["STN352_GRN(id:10381)"] * 25,
                "Overall status": ["FAILURE"] * 80 + ["ERROR"] * 20,
            }
        )
        sample_data.to_csv(test_data_path, index=False)

    return test_data_path
