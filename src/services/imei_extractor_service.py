"""
IMEI Extractor Service

Handles IMEI extraction from filtered test data and generates database export commands.
This service provides functionality for the "IMEI Extractor" tab, which processes
test results and creates database commands for debugging purposes.

Functions:
- process_data(): Main function that filters data and generates db-export commands
- resolve_station(): Maps station IDs to machine names
- get_test_from_result_fail(): Maps failure descriptions to test categories
"""

import pandas as pd
from typing import List, Tuple, Union
import logging

from common.logging_config import capture_exceptions
from common.mappings import (
    TEST_TO_RESULT_FAIL_MAP,
    DEVICE_MAP,
    STATION_TO_MACHINE
)

logger = logging.getLogger(__name__)


def resolve_station(station_id: str) -> str:
    """
    Resolve a station id to a machine name.
    
    Args:
        station_id: The station identifier to resolve
        
    Returns:
        Machine name or "Unknown Machine" if not found
    """
    return STATION_TO_MACHINE.get(station_id.lower(), "Unknown Machine")


def get_test_from_result_fail(result_fail: str) -> str:
    """
    Resolve a result_fail to a test name.
    
    Args:
        result_fail: The failure description to map to a test category
        
    Returns:
        Test category name or "Unknown Test" if not found
    """
    for test, descriptions in TEST_TO_RESULT_FAIL_MAP.items():
        if result_fail in descriptions:
            return test
    return "Unknown Test"


@capture_exceptions(user_message="Failed to process IMEI extraction")
def process_data(
    df: pd.DataFrame,
    source: str,
    station_id: str,
    models: List[str],
    result_fail: str,
    flexible_search: bool
) -> Tuple[str, str, str, str]:
    """
    Process a given DataFrame to produce db-export commands and formatted markdown summary.
    
    This function filters test data based on user criteria, extracts unique IMEIs,
    and generates three types of database export commands along with a comprehensive
    summary.
    
    Args:
        df: DataFrame containing test results data
        source: Filter by data source ("All" or specific source)
        station_id: Filter by station ID ("All" or specific station)
        models: List of device models to filter by (["All"] or specific models)
        result_fail: Filter by specific failure type ("All" or specific failure)
        flexible_search: Boolean flag for case-insensitive substring matching
        
    Returns:
        Tuple containing:
        - messages_command: Database export command for messages
        - raw_data_command: Database export command for raw test data
        - gauge_command: Database export command for gauge data
        - summary: Formatted markdown summary with query results and parameters
    """
    try:
        logger.info(f"Processing IMEI extraction for {len(df)} records")
        
        # Create a copy of the original DataFrame to avoid modifying it directly
        df_filtered = df.copy()

        # Apply filtering based on the source column if a specific source is selected
        if source != "All":
            df_filtered = df_filtered[df_filtered["Source"] == source]
            logger.debug(f"Filtered by source '{source}': {len(df_filtered)} records")

        # Apply filtering based on the station ID if a specific station is selected
        if station_id != "All":
            df_filtered = df_filtered[df_filtered["Station ID"] == station_id]
            logger.debug(f"Filtered by station '{station_id}': {len(df_filtered)} records")

        # Apply filtering based on the selected models if not set to "All"
        if models and "All" not in models:
            df_filtered = df_filtered[df_filtered["Model"].isin(models)]
            logger.debug(f"Filtered by models {models}: {len(df_filtered)} records")

        # Apply filtering based on result_fail with option for flexible search
        if result_fail != "All":
            if flexible_search:
                # Use case-insensitive substring match for flexible search
                df_filtered = df_filtered[
                    df_filtered["result_FAIL"].apply(
                        lambda x: result_fail.lower() in str(x).lower()
                    )
                ]
                logger.debug(f"Flexible search for '{result_fail}': {len(df_filtered)} records")
            else:
                # Exact match filtering
                df_filtered = df_filtered[df_filtered["result_FAIL"] == result_fail]
                logger.debug(f"Exact match for '{result_fail}': {len(df_filtered)} records")

        # Limit the DataFrame to the first 1000 rows for processing
        df_filtered = df_filtered.head(1000)
        logger.debug(f"Limited to first 1000 rows: {len(df_filtered)} records")

        # Extract unique IMEIs, converting to integers and filtering out NaN values
        unique_imeis = df_filtered["IMEI"].unique()
        imeis_as_int = [str(int(float(imei))) for imei in unique_imeis if pd.notna(imei)]
        logger.info(f"Extracted {len(imeis_as_int)} unique IMEIs")

        # Construct a command to export message data for the filtered IMEIs
        messages_command = (
            "db-export messages --dut " + " --dut ".join(imeis_as_int)
            if imeis_as_int
            else "No IMEIs found"
        )

        # Determine the test name from the result_fail mapping
        test_name = get_test_from_result_fail(result_fail)
        logger.debug(f"Mapped result_fail '{result_fail}' to test '{test_name}'")

        # Construct a command to export raw data for the specified test and IMEIs
        raw_data_command = (
            f'db-export raw_data --test "{test_name}" --dut ' + " --dut ".join(imeis_as_int)
            if imeis_as_int
            else "No IMEIs found"
        )

        # Construct a command to export gauge data for the specified test and IMEIs
        gauge_command = (
            f'db-export gauge --test "{test_name}" --dut ' + " --dut ".join(imeis_as_int)
            if imeis_as_int
            else "No IMEIs found"
        )

        # Calculate the number of unique IMEIs processed
        result_count = len(imeis_as_int)

        # Count occurrences of each model in the filtered DataFrame
        model_counts = df_filtered["Model"].value_counts()

        # Generate a markdown summary of query results and model counts
        summary = f"""
<div class="summary-section">

## Query Results Summary

| Metric | Value |
|:-------|:------|
| Total Devices | {result_count} |
| Maximum Results | 1000 |

## Search Parameters

| Parameter | Value |
|:----------|:------|
| Source | {source} |
| Station ID | {station_id} |
| Models | {', '.join(models) if models != ['All'] else 'All'} |
| Result Fail | {result_fail} |
| Flexible Search | {'Enabled' if flexible_search else 'Disabled'} |

</div>

<div class="summary-section">

## Models Found in Query

| Model | Device Code | Count |
|:------|:------------|------:|
{chr(10).join(f"| {model} | {DEVICE_MAP.get(model, 'Unknown') if not isinstance(DEVICE_MAP.get(model, 'Unknown'), list) else ', '.join(DEVICE_MAP.get(model, ['Unknown']))} | {count} |" for model, count in model_counts.items())}

</div>

<div class="summary-section">

## Remote Access Information

| Machine | Station ID |
|:--------|:-----------|
{chr(10).join(f"| {resolve_station(station)} | {station} |" for station in sorted(df_filtered['Station ID'].unique()))}

</div>
"""
        logger.info(f"IMEI extraction completed successfully: {result_count} devices processed")
        
        # Return the commands and the generated summary
        return messages_command, raw_data_command, gauge_command, summary

    except Exception as e:
        logger.error(f"Error in IMEI extraction: {str(e)}")
        # Handle exceptions by returning an error message in markdown format
        error_message = f"""
## Error Occurred

| Error Details |
|:--------------|
| {str(e)} |

Please check your input and try again.
"""
        return error_message, error_message, error_message, error_message