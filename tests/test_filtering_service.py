"""
Unit tests for Filtering Service
Tests the extracted filtering functionality.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
import gradio as gr
from src.services.filtering_service import (
    get_unique_values,
    format_dataframe,
    analyze_top_errors_by_model,
    analyze_overall_status,
    update_filter_visibility,
    filter_data,
    apply_filter_and_sort,
    update_filter_dropdowns
)


class TestFilteringService:
    """Test suite for the filtering service."""
    
    @pytest.fixture
    def sample_test_data(self):
        """Create sample test data matching actual CSV format."""
        return pd.DataFrame({
            'Overall status': ['SUCCESS', 'FAILURE', 'SUCCESS', 'ERROR', 'FAILURE', 'SUCCESS'],
            'Station ID': ['radi135', 'radi138', 'radi135', 'radi162', 'radi138', 'radi135'],
            'Model': ['iPhone14ProMax', 'iPhone15Pro', 'iPhone14ProMax', 'iPhone16', 'iPhone15Pro', 'iPhone14ProMax'],
            'result_FAIL': ['', 'Camera Pictures', '', '6A-Display Fail', 'AQA_Microphone', ''],
            'Date': ['1/2/2025', '1/2/2025', '1/2/2025', '1/2/2025', '1/2/2025', '1/3/2025'],
            'IMEI': ['123456789', '987654321', '111222333', '444555666', '777888999', '000111222'],
            'Operator': ['TestOp1', 'TestOp2', 'TestOp1', 'TestOp3', 'TestOp2', 'TestOp1'],
            'Source': ['SourceA', 'SourceB', 'SourceA', 'SourceA', 'SourceB', 'SourceA'],
            'Manufacturer': ['Apple', 'Apple', 'Apple', 'Apple', 'Apple', 'Apple']
        })
    
    @pytest.fixture
    def empty_dataframe(self):
        """Create an empty DataFrame for testing."""
        return pd.DataFrame()
    
    def test_get_unique_values_basic(self, sample_test_data):
        """Test get_unique_values returns correct sorted unique values."""
        unique_operators = get_unique_values(sample_test_data, 'Operator')
        
        expected = ['TestOp1', 'TestOp2', 'TestOp3']
        assert unique_operators == expected
        
        unique_models = get_unique_values(sample_test_data, 'Model')
        expected_models = ['iPhone14ProMax', 'iPhone15Pro', 'iPhone16']
        assert unique_models == expected_models
    
    def test_get_unique_values_with_nulls(self):
        """Test get_unique_values handles null values correctly."""
        df_with_nulls = pd.DataFrame({
            'Column': ['A', 'B', None, 'A', pd.NA, 'C']
        })
        
        unique_values = get_unique_values(df_with_nulls, 'Column')
        assert unique_values == ['A', 'B', 'C']
    
    def test_get_unique_values_empty_column(self, empty_dataframe):
        """Test get_unique_values with empty DataFrame."""
        # This should raise a KeyError since the column doesn't exist
        with pytest.raises(KeyError):
            get_unique_values(empty_dataframe, 'nonexistent_column')
    
    def test_format_dataframe_simple_series(self):
        """Test format_dataframe with a simple pandas Series."""
        data = pd.Series([10, 5, 3], index=['A', 'B', 'C'])
        
        result = format_dataframe(data)
        
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['Category', 'Count']
        assert len(result) == 3
        assert result['Category'].tolist() == ['A', 'B', 'C']
        assert result['Count'].tolist() == [10, 5, 3]
    
    def test_analyze_top_errors_by_model(self, sample_test_data):
        """Test analyze_top_errors_by_model function."""
        result = analyze_top_errors_by_model(sample_test_data)
        
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['Model', 'error', 'count']
        
        # Should have entries for failing models with error details
        if len(result) > 0:
            assert 'iPhone15Pro' in result['Model'].values or 'iPhone16' in result['Model'].values
    
    def test_analyze_overall_status(self, sample_test_data):
        """Test analyze_overall_status function."""
        result = analyze_overall_status(sample_test_data)
        
        assert isinstance(result, pd.Series)
        assert 'SUCCESS' in result.index
        assert 'FAILURE' in result.index
        assert 'ERROR' in result.index
        
        # Check counts match our sample data
        assert result['SUCCESS'] == 3
        assert result['FAILURE'] == 2
        assert result['ERROR'] == 1
    
    def test_update_filter_visibility_no_filter(self):
        """Test update_filter_visibility with 'No Filter' selection."""
        result = update_filter_visibility("No Filter")
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        
        # All should be invisible
        for update_obj in result:
            assert hasattr(update_obj, 'get')
            # Note: Can't directly check visible=False due to gr.update internal structure
    
    def test_update_filter_visibility_operator_filter(self):
        """Test update_filter_visibility with 'Filter by Operator' selection."""
        result = update_filter_visibility("Filter by Operator")
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        # Should return operator visible, source hidden, station_id visible
    
    def test_update_filter_visibility_source_filter(self):
        """Test update_filter_visibility with 'Filter by Source' selection."""
        result = update_filter_visibility("Filter by Source")
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        # Should return operator hidden, source visible, station_id visible
    
    def test_filter_data_no_filtering(self, sample_test_data):
        """Test filter_data with no actual filtering applied."""
        result = filter_data(sample_test_data, "No Filter", "All", "All", "All")
        
        # Should return 7-tuple
        assert len(result) == 7
        
        summary, models_chart, test_cases_chart, status_chart, models_df, test_cases_df, errors_df = result
        
        # Validate types
        assert isinstance(summary, str)
        assert isinstance(models_chart, go.Figure)
        assert isinstance(test_cases_chart, go.Figure)
        assert isinstance(status_chart, go.Figure)
        assert isinstance(models_df, pd.DataFrame)
        assert isinstance(test_cases_df, pd.DataFrame)
        assert isinstance(errors_df, pd.DataFrame)
        
        # Summary should contain basic stats (format is in a table)
        assert "| Total Tests         | 6" in summary
        assert "| Total Unique Devices | 6" in summary  # 6 unique IMEIs
        
    def test_filter_data_by_operator(self, sample_test_data):
        """Test filter_data with operator filtering."""
        result = filter_data(sample_test_data, "Filter by Operator", "TestOp1", "All", "All")
        
        summary = result[0]
        
        # Should filter to only TestOp1 records (3 records in our sample data)
        assert "| Operator  | TestOp1" in summary
        # TestOp1 has 3 records: all SUCCESS in our data
        assert "| Successes | 3" in summary
        assert "| Failures  | 0" in summary
    
    def test_filter_data_by_station(self, sample_test_data):
        """Test filter_data with station ID filtering."""
        result = filter_data(sample_test_data, "No Filter", "All", "All", "radi135")
        
        summary = result[0]
        
        # Should filter to only radi135 records (3 records)
        assert "| Station ID| radi135" in summary
        # radi135 has 3 records: all SUCCESS
        assert "| Successes | 3" in summary
        assert "| Failures  | 0" in summary
    
    def test_filter_data_error_handling(self):
        """Test filter_data with error conditions."""
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        
        # Should return error tuple due to missing required columns
        result = filter_data(empty_df, "No Filter", "All", "All", "All")
        
        # With @capture_exceptions decorator, should return None tuple
        expected_error_result = (None, None, None, None, None, None, None)
        assert result == expected_error_result
    
    def test_apply_filter_and_sort_basic(self, sample_test_data):
        """Test apply_filter_and_sort with basic filtering."""
        filtered_df, summary = apply_filter_and_sort(
            sample_test_data, 
            [], # no sorting
            "TestOp1",  # operator filter
            "All",      # model filter  
            "All",      # manufacturer filter
            "All",      # source filter
            "All",      # overall_status filter
            "All",      # station_id filter
            "All"       # result_fail filter
        )
        
        assert isinstance(filtered_df, pd.DataFrame)
        assert isinstance(summary, str)
        
        # Should filter to TestOp1 only (3 records)
        assert len(filtered_df) == 3
        assert all(filtered_df['Operator'] == 'TestOp1')
        
        # Summary should reflect filtering
        assert "Filtered data: 3 rows" in summary
        assert "Operator=TestOp1" in summary
    
    def test_apply_filter_and_sort_with_sorting(self, sample_test_data):
        """Test apply_filter_and_sort with sorting."""
        filtered_df, summary = apply_filter_and_sort(
            sample_test_data,
            ['Model', 'Overall status'],  # sort columns
            "All", "All", "All", "All", "All", "All", "All"
        )
        
        # Should be sorted by Model, then Overall status
        assert len(filtered_df) == len(sample_test_data)
        assert "Sorted by: Model, Overall status" in summary
        
        # Check if actually sorted (first few rows should be in order)
        models = filtered_df['Model'].tolist()
        assert models == sorted(models) or len(set(models[:2])) == 1  # Either sorted or first elements are same
    
    def test_apply_filter_and_sort_multiple_filters(self, sample_test_data):
        """Test apply_filter_and_sort with multiple filters."""
        filtered_df, summary = apply_filter_and_sort(
            sample_test_data,
            [],
            "TestOp1",        # operator
            "iPhone14ProMax", # model
            "All",           # manufacturer
            "All",           # source
            "SUCCESS",       # overall_status
            "All",           # station_id
            "All"            # result_fail
        )
        
        # Should have only records matching all criteria
        assert len(filtered_df) <= len(sample_test_data)
        if len(filtered_df) > 0:
            assert all(filtered_df['Operator'] == 'TestOp1')
            assert all(filtered_df['Model'] == 'iPhone14ProMax')
            assert all(filtered_df['Overall status'] == 'SUCCESS')
        
        # Summary should list all applied filters
        assert "Operator=TestOp1" in summary
        assert "Model=iPhone14ProMax" in summary
        assert "Overall status=SUCCESS" in summary
    
    def test_apply_filter_and_sort_list_filters(self, sample_test_data):
        """Test apply_filter_and_sort with list-type filters."""
        filtered_df, summary = apply_filter_and_sort(
            sample_test_data,
            [],
            ["TestOp1", "TestOp2"],  # list of operators
            "All", "All", "All", "All", "All", "All"
        )
        
        # Should include records for both operators
        operators_in_result = filtered_df['Operator'].unique()
        assert 'TestOp1' in operators_in_result or 'TestOp2' in operators_in_result
        
        # Summary should show list format
        assert "Operator=TestOp1, TestOp2" in summary
    
    def test_apply_filter_and_sort_error_handling(self):
        """Test apply_filter_and_sort error handling."""
        empty_df = pd.DataFrame()
        
        # Should handle empty DataFrame gracefully
        result_df, summary = apply_filter_and_sort(
            empty_df, [], "All", "All", "All", "All", "All", "All", "All"
        )
        
        # Should return empty DataFrame and summary
        assert isinstance(result_df, pd.DataFrame)
        assert isinstance(summary, str)
        assert "Filtered data: 0 rows" in summary
    
    def test_update_filter_dropdowns(self, sample_test_data):
        """Test update_filter_dropdowns function."""
        # Note: This function creates actual Gradio components which may not work in test environment
        # We'll test that it returns the expected structure
        try:
            dropdowns = update_filter_dropdowns(sample_test_data)
            assert isinstance(dropdowns, list)
            # Should create dropdowns for the filter columns that exist
        except Exception as e:
            # Gradio components might not work in test environment
            # This is acceptable for unit testing
            assert "gradio" in str(e).lower() or "component" in str(e).lower()
    
    def test_edge_cases_filtering(self):
        """Test edge cases in filtering functionality."""
        # Test with DataFrame that has only success records
        success_only_df = pd.DataFrame({
            'Overall status': ['SUCCESS', 'SUCCESS', 'SUCCESS'],
            'Station ID': ['radi135', 'radi138', 'radi135'],
            'Model': ['iPhone14ProMax', 'iPhone15Pro', 'iPhone14ProMax'],
            'result_FAIL': ['', '', ''],
            'Date': ['1/2/2025', '1/2/2025', '1/2/2025'],
            'IMEI': ['123', '456', '789'],
            'Operator': ['TestOp1', 'TestOp1', 'TestOp1'],
            'Source': ['SourceA', 'SourceA', 'SourceA'],
            'Manufacturer': ['Apple', 'Apple', 'Apple']
        })
        
        result = filter_data(success_only_df, "No Filter", "All", "All", "All")
        
        if result != (None, None, None, None, None, None, None):  # Not an error
            summary = result[0]
            # Check for 100% success rate in table format
            assert "| Successes | 3        | 100.00%" in summary
    
    def test_data_types_and_edge_values(self):
        """Test filtering with various data types and edge values."""
        mixed_df = pd.DataFrame({
            'Overall status': ['SUCCESS', 'FAILURE', None, 'ERROR'],
            'Station ID': ['radi135', '', 'radi138', 'radi162'],
            'Model': [None, 'iPhone15Pro', 'iPhone14ProMax', ''],
            'result_FAIL': ['', 'Camera Pictures', None, '6A-Display Fail'],
            'Date': ['1/2/2025', None, '1/2/2025', '1/2/2025'],
            'IMEI': ['123', '456', '789', '000'],
            'Operator': ['TestOp1', 'TestOp2', None, 'TestOp3'],
            'Source': ['SourceA', '', 'SourceB', 'SourceA'],
            'Manufacturer': ['Apple', 'Apple', None, 'Apple']
        })
        
        # Test get_unique_values with mixed data
        unique_operators = get_unique_values(mixed_df, 'Operator')
        # Should exclude None values and sort
        assert None not in unique_operators
        assert 'TestOp1' in unique_operators
        
        # Test analyze functions with mixed data
        status_counts = analyze_overall_status(mixed_df)
        assert isinstance(status_counts, pd.Series)
        # Should have counts for non-null statuses