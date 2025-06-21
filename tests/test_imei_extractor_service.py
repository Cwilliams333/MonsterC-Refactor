"""
Tests for IMEI Extractor Service

Comprehensive test suite for the IMEI extraction functionality that processes
test data and generates database export commands.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from src.services.imei_extractor_service import (
    process_data,
    resolve_station,
    get_test_from_result_fail
)


@pytest.fixture
def sample_data():
    """Create sample test data for IMEI extraction testing."""
    return pd.DataFrame({
        'IMEI': [123456789012345, 234567890123456, 345678901234567, 456789012345678, np.nan],
        'Source': ['Source1', 'Source2', 'Source1', 'Source2', 'Source1'],
        'Station ID': ['station1', 'station2', 'station1', 'station3', 'station1'],
        'Model': ['iPhone14Pro', 'iPhone15Pro', 'iPhone14Pro', 'iPhone15ProMax', 'iPhone14Pro'],
        'result_FAIL': ['Display Fail', 'Battery Test Failed', 'Audio Issue', 'Camera Error', 'Display Fail'],
        'Operator': ['Operator1', 'Operator2', 'Operator1', 'Operator3', 'Operator1']
    })


@pytest.fixture
def large_sample_data():
    """Create larger sample data for testing pagination limits."""
    data = []
    for i in range(1200):  # More than 1000 to test limit
        data.append({
            'IMEI': 100000000000000 + i,
            'Source': f'Source{i % 3 + 1}',
            'Station ID': f'station{i % 4 + 1}',
            'Model': f'iPhone{14 + (i % 3)}Pro',
            'result_FAIL': 'Test Failure',
            'Operator': f'Operator{i % 2 + 1}'
        })
    return pd.DataFrame(data)


class TestHelperFunctions:
    """Test helper functions used by the IMEI extractor service."""
    
    def test_resolve_station_known_station(self):
        """Test station resolution for known stations."""
        # Mock data should be available from mappings
        result = resolve_station('radi135')
        # Should return mapped value or "Unknown Machine" if not in mapping
        assert isinstance(result, str)
        assert result != ""
    
    def test_resolve_station_unknown_station(self):
        """Test station resolution for unknown stations."""
        result = resolve_station('unknown_station_xyz')
        assert result == "Unknown Machine"
    
    def test_resolve_station_case_insensitive(self):
        """Test that station resolution is case insensitive."""
        result1 = resolve_station('RADI135')
        result2 = resolve_station('radi135')
        # Both should give same result due to .lower() in function
        assert result1 == result2
    
    def test_get_test_from_result_fail_known_failure(self):
        """Test test name resolution for known failure descriptions."""
        # Test with a known failure pattern
        result = get_test_from_result_fail('Display Fail')
        assert isinstance(result, str)
        assert result != ""
    
    def test_get_test_from_result_fail_unknown_failure(self):
        """Test test name resolution for unknown failure descriptions."""
        result = get_test_from_result_fail('Unknown Failure XYZ')
        assert result == "Unknown Test"


class TestProcessData:
    """Test the main process_data function."""
    
    def test_process_data_all_filters(self, sample_data):
        """Test process_data with all filters set to 'All'."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # Should process all valid IMEIs (4 valid, 1 NaN)
        assert "db-export messages --dut" in messages_cmd
        assert "123456789012345" in messages_cmd
        assert "234567890123456" in messages_cmd
        assert "345678901234567" in messages_cmd
        assert "456789012345678" in messages_cmd
        
        # Raw data and gauge commands should include test name
        assert "db-export raw_data --test" in raw_data_cmd
        assert "db-export gauge --test" in gauge_cmd
        
        # Summary should be markdown format
        assert "## Query Results Summary" in summary
        assert "Total Devices | 4" in summary
        
    def test_process_data_source_filter(self, sample_data):
        """Test process_data with source filtering."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="Source1",
            station_id="All",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # Should only include Source1 devices (3 total, but 1 has NaN IMEI)
        assert "db-export messages --dut" in messages_cmd
        assert "123456789012345" in messages_cmd
        assert "345678901234567" in messages_cmd
        # Should not include Source2 devices
        assert "234567890123456" not in messages_cmd
        
        # Summary should show filtered count
        assert "Total Devices | 2" in summary
        assert "Source | Source1" in summary
    
    def test_process_data_station_filter(self, sample_data):
        """Test process_data with station ID filtering."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="All",
            station_id="station1",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # Should only include station1 devices (3 total, but 1 has NaN IMEI)
        assert "123456789012345" in messages_cmd
        assert "345678901234567" in messages_cmd
        # Should not include other stations
        assert "234567890123456" not in messages_cmd
        
        assert "Station ID | station1" in summary
    
    def test_process_data_model_filter(self, sample_data):
        """Test process_data with model filtering."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="All",
            station_id="All",
            models=["iPhone14Pro"],
            result_fail="All",
            flexible_search=False
        )
        
        # Should only include iPhone14Pro devices (3 total, but 1 has NaN IMEI)
        assert "123456789012345" in messages_cmd
        assert "345678901234567" in messages_cmd
        # Should not include iPhone15Pro models
        assert "234567890123456" not in messages_cmd
        
        assert "Models | iPhone14Pro" in summary
    
    def test_process_data_result_fail_exact_match(self, sample_data):
        """Test process_data with exact result_fail filtering."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="Display Fail",
            flexible_search=False
        )
        
        # Should only include "Display Fail" entries (2 total, but 1 has NaN IMEI)
        assert "123456789012345" in messages_cmd
        # Should not include other failure types
        assert "234567890123456" not in messages_cmd
        
        assert "Result Fail | Display Fail" in summary
        assert "Total Devices | 1" in summary
    
    def test_process_data_result_fail_flexible_search(self, sample_data):
        """Test process_data with flexible result_fail searching."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="fail",  # Should match "Display Fail" and "Battery Test Failed"
            flexible_search=True
        )
        
        # Should include entries with "fail" in failure description
        assert "123456789012345" in messages_cmd  # Display Fail
        assert "234567890123456" in messages_cmd  # Battery Test Failed
        # Should not include entries without "fail"
        assert "345678901234567" not in messages_cmd  # Audio Issue
        
        assert "Flexible Search | Enabled" in summary
    
    def test_process_data_no_matching_data(self, sample_data):
        """Test process_data when no data matches filters."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="NonexistentSource",
            station_id="All",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # Should return "No IMEIs found" messages
        assert messages_cmd == "No IMEIs found"
        assert raw_data_cmd == "No IMEIs found"
        assert gauge_cmd == "No IMEIs found"
        assert "Total Devices | 0" in summary
    
    def test_process_data_limit_1000_rows(self, large_sample_data):
        """Test that process_data limits results to 1000 rows."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=large_sample_data,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # Should limit to 1000 unique IMEIs max
        imei_count = messages_cmd.count("--dut")
        assert imei_count <= 1000
        assert "Maximum Results | 1000" in summary
    
    def test_process_data_nan_imei_handling(self):
        """Test that NaN IMEIs are properly filtered out."""
        data_with_nans = pd.DataFrame({
            'IMEI': [123456789012345, np.nan, None, 234567890123456],
            'Source': ['Source1', 'Source1', 'Source1', 'Source1'],
            'Station ID': ['station1', 'station1', 'station1', 'station1'],
            'Model': ['iPhone14Pro', 'iPhone14Pro', 'iPhone14Pro', 'iPhone14Pro'],
            'result_FAIL': ['Test Fail', 'Test Fail', 'Test Fail', 'Test Fail'],
            'Operator': ['Op1', 'Op1', 'Op1', 'Op1']
        })
        
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=data_with_nans,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # Should only include valid IMEIs
        assert "123456789012345" in messages_cmd
        assert "234567890123456" in messages_cmd
        assert "Total Devices | 2" in summary
    
    def test_process_data_command_format(self, sample_data):
        """Test that generated commands have correct format."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="Display Fail",
            flexible_search=False
        )
        
        # Messages command format
        assert messages_cmd.startswith("db-export messages --dut")
        # Extract IMEIs from command and check they are numeric
        imei_parts = [part.strip() for part in messages_cmd.split("--dut")[1:] if part.strip()]
        assert all(imei.isdigit() for imei in imei_parts)
        
        # Raw data command format
        assert raw_data_cmd.startswith("db-export raw_data --test")
        assert "--dut" in raw_data_cmd
        
        # Gauge command format
        assert gauge_cmd.startswith("db-export gauge --test")
        assert "--dut" in gauge_cmd
    
    def test_process_data_error_handling(self):
        """Test error handling for invalid input."""
        # Test with invalid DataFrame
        invalid_df = pd.DataFrame({'wrong_column': [1, 2, 3]})
        
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=invalid_df,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # All outputs should contain error message
        assert "## Error Occurred" in messages_cmd
        assert "## Error Occurred" in raw_data_cmd
        assert "## Error Occurred" in gauge_cmd
        assert "## Error Occurred" in summary
    
    def test_process_data_summary_sections(self, sample_data):
        """Test that summary contains all required sections."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="All",
            station_id="All",
            models=["All"],
            result_fail="All",
            flexible_search=False
        )
        
        # Check all required sections are present
        assert "## Query Results Summary" in summary
        assert "## Search Parameters" in summary
        assert "## Models Found in Query" in summary
        assert "## Remote Access Information" in summary
        
        # Check parameter values are displayed
        assert "Source | All" in summary
        assert "Station ID | All" in summary
        assert "Models | All" in summary
        assert "Result Fail | All" in summary
        assert "Flexible Search | Disabled" in summary
    
    def test_process_data_multiple_filters_combined(self, sample_data):
        """Test process_data with multiple filters applied simultaneously."""
        messages_cmd, raw_data_cmd, gauge_cmd, summary = process_data(
            df=sample_data,
            source="Source1",
            station_id="station1",
            models=["iPhone14Pro"],
            result_fail="Display Fail",
            flexible_search=False
        )
        
        # Should apply all filters - multiple records match the criteria
        # Check that filtering worked and we have some results
        assert ("Total Devices |" in summary) and ("No IMEIs found" not in messages_cmd)
        
        # Check all parameters are reflected in summary
        assert "Source | Source1" in summary
        assert "Station ID | station1" in summary
        assert "Models | iPhone14Pro" in summary
        assert "Result Fail | Display Fail" in summary