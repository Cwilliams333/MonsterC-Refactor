"""
Pivot Service Module for MonsterC CSV Analysis Tool.

This module provides pivot table generation and analysis functionality,
extracted from the legacy monolith following the Strangler Fig pattern.
"""

from typing import List, Optional, Union, Tuple, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.common.logging_config import get_logger, capture_exceptions

# Initialize logger
logger = get_logger(__name__)


@capture_exceptions(user_message="Failed to apply filters to data")
def apply_filters(
    df: pd.DataFrame, 
    operator: Union[str, List[str]], 
    station_id: Union[str, List[str]], 
    model: Union[str, List[str]]
) -> pd.DataFrame:
    """
    Apply filters to the DataFrame before creating pivot table.
    
    Args:
        df: Input DataFrame to filter
        operator: Operator(s) to filter by
        station_id: Station ID(s) to filter by
        model: Model(s) to filter by
    
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    # Handle operator filter
    if operator and "All" not in operator:
        filtered_df = filtered_df[filtered_df["Operator"].isin(operator)]
    
    # Handle station_id filter
    if station_id and "All" not in station_id:
        filtered_df = filtered_df[filtered_df["Station ID"].isin(station_id)]
    
    # Handle model filter
    if model and "All" not in model:
        filtered_df = filtered_df[filtered_df["Model"].isin(model)]
    
    logger.info(f"Applied filters - rows before: {len(df)}, rows after: {len(filtered_df)}")
    return filtered_df


@capture_exceptions(user_message="Failed to create pivot table")
def create_pivot_table(
    df: pd.DataFrame, 
    rows: List[str], 
    columns: Optional[List[str]], 
    values: str, 
    aggfunc: str = 'count'
) -> pd.DataFrame:
    """
    Creates a pivot table from the given DataFrame based on user selections.
    
    Args:
        df: Input DataFrame
        rows: Columns to use as row indices
        columns: Columns to use as column indices (optional)
        values: Column to aggregate
        aggfunc: Aggregation function to use
    
    Returns:
        Pivot table as DataFrame
    """
    try:
        if not rows or not values:
            logger.warning("Missing required fields for pivot table")
            return pd.DataFrame()  # Return empty DataFrame if required fields are missing
        
        # Handle the aggregation function
        if aggfunc == 'count':
            aggfunc = 'size'
        
        # Create pivot table
        pivot = pd.pivot_table(
            df,
            index=rows,
            columns=columns if columns else None,
            values=values if aggfunc != 'size' else None,
            aggfunc=aggfunc,
            fill_value=0
        )
        
        # Reset index for better display
        pivot = pivot.reset_index()
        
        # Flatten column names if they're multi-level
        if isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = [f"{col[0]}_{col[1]}" if isinstance(col, tuple) else col for col in pivot.columns]
        
        logger.info(f"Created pivot table with shape: {pivot.shape}")
        return pivot
    
    except Exception as e:
        logger.error(f"Error creating pivot table: {str(e)}")
        return pd.DataFrame({'Error': [str(e)]})


@capture_exceptions(user_message="Failed to generate filtered pivot table")
def generate_pivot_table_filtered(
    df: pd.DataFrame, 
    rows: List[str], 
    columns: Optional[List[str]], 
    values: str, 
    aggfunc: str,
    operator: Union[str, List[str]], 
    station_id: Union[str, List[str]], 
    model: Union[str, List[str]]
) -> pd.DataFrame:
    """
    Generate a filtered pivot table based on user selections.
    
    Args:
        df: Input DataFrame
        rows: Columns to use as row indices
        columns: Columns to use as column indices (optional)
        values: Column to aggregate
        aggfunc: Aggregation function to use
        operator: Operator(s) to filter by
        station_id: Station ID(s) to filter by
        model: Model(s) to filter by
    
    Returns:
        Filtered pivot table as DataFrame
    """
    try:
        # First apply filters
        filtered_df = apply_filters(df, operator, station_id, model)
        
        # Then create pivot table
        result = create_pivot_table(filtered_df, rows, columns, values, aggfunc)
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating filtered pivot table: {str(e)}")
        return pd.DataFrame({'Error': [str(e)]})


@capture_exceptions(user_message="Failed to find top failing stations")
def find_top_failing_stations(pivot: pd.DataFrame, top_n: int = 5) -> pd.Series:
    """
    Finds the top failing stations based on the provided pivot table.

    Args:
        pivot: A Pandas DataFrame with a pivot table structure, where the
               index is the model, the columns are the test cases, and the
               values are the counts of failures for each test case
        top_n: The number of top failing stations to return
    
    Returns:
        A Series with the top failing stations and their failure counts
    """
    # Get the sum of all failures for each station
    station_failures = pivot.sum().fillna(0)

    # Get the top N failing stations
    return station_failures.nlargest(top_n)


@capture_exceptions(user_message="Failed to analyze top models")
def analyze_top_models(pivot: pd.DataFrame, top_stations: pd.Series, top_n: int = 5) -> pd.Series:
    """
    Analyzes the top models based on the provided pivot table and top failing stations.

    This function takes a pivot table as input, which should be a DataFrame with the following structure:

        | Model | Station ID | Test Case | Count |
        |-------|------------|-----------|-------|
        |   A   |    1       |   1       |   10  |
        |   A   |    1       |   2       |   5   |
        |   B   |    2       |   1       |   8   |
        |   B   |    2       |   2       |   3   |

    The function also takes a Series of top failing stations as input, which should have the station IDs as
    the index and the total number of failures for each station as the values.

    Args:
        pivot: Pivot table DataFrame
        top_stations: Series with top failing stations
        top_n: Number of top models to return
    
    Returns:
        Series with top models and their failure counts
    """
    # Filter the pivot table to only include the top failing stations
    top_models_pivot = pivot[top_stations.index]

    # Sum up the counts for each model
    top_models = top_models_pivot.sum(axis=1).fillna(0)

    # Return the top N models with the highest total counts
    top_models = top_models.nlargest(top_n)

    # Rename the index to include the result (SUCCESS/FAILURE) for each model
    top_models.index = [f"{model} - {result}" for model, result in top_models.index]

    return top_models


@capture_exceptions(user_message="Failed to analyze top test cases")
def analyze_top_test_cases(pivot: pd.DataFrame, top_stations: pd.Series, top_n: int = 5) -> pd.Series:
    """
    Analyzes the top test cases based on the provided pivot table and top failing stations.

    The pivot table is filtered to only include the top failing stations. Then, the test cases are grouped
    by their result (SUCCESS/FAILURE), and the sum of each group is calculated. This gives us the total
    number of test cases that failed for each station.

    Args:
        pivot: Pivot table DataFrame
        top_stations: Series with top failing stations
        top_n: Number of top test cases to return
    
    Returns:
        Series with top test cases and their failure counts
    """
    # Filter the pivot table to only include the top failing stations
    top_stations_pivot = pivot[top_stations.index]

    # Group the test cases by their result (SUCCESS/FAILURE) and calculate the sum of each group
    test_case_failures = top_stations_pivot.groupby('result_FAIL').sum().sum(axis=1).fillna(0)

    # Return the top N test cases, sorted by their failure count in descending order
    return test_case_failures.nlargest(top_n)