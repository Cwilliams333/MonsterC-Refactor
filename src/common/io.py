"""
I/O utilities for CSV data handling and processing.

This module provides comprehensive functionality for loading, parsing, and handling
CSV files with various encodings, date formats, and data types. It includes robust
error handling and type conversion utilities.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import chardet
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)


def detect_encoding(file_path: Union[str, Path]) -> str:
    """
    Detect the encoding of a file using chardet.

    Args:
        file_path: Path to the file to analyze

    Returns:
        str: Detected encoding (defaults to 'utf-8' if detection fails)
    """
    try:
        with open(file_path, "rb") as file:
            raw_data = file.read(10000)  # Read first 10KB for detection
            result = chardet.detect(raw_data)
            encoding = result.get("encoding") or "utf-8"
            confidence = result.get("confidence", 0)

            logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")

            # Fall back to utf-8 if confidence is too low
            if confidence < 0.7:
                logger.warning("Low confidence in encoding detection, using utf-8")
                return "utf-8"

            return encoding
    except Exception as e:
        logger.error(f"Error detecting encoding: {e}")
        return "utf-8"


def auto_format_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Auto-format CSV to include only the required columns for MonsterC.

    Args:
        df: Input DataFrame with potentially many columns

    Returns:
        pd.DataFrame: Formatted DataFrame with only required columns
    """
    # Define the target columns we want to keep
    target_columns = [
        "Operator",
        "Date Time",
        "Model",
        "IMEI",
        "App version",
        "Manufacturer",
        "OS",
        "OS name",
        "Source",
        "RADI app version",
        "Overall status",
        "Station ID",
        "result_FAIL",
        "LCD Grading 1",
        "error_code",
        "error_message",
        "BlindUnlockPerformed",
    ]

    # Check which target columns exist in the DataFrame
    existing_columns = [col for col in target_columns if col in df.columns]
    missing_columns = [col for col in target_columns if col not in df.columns]

    if missing_columns:
        logger.warning(f"Missing columns in CSV: {missing_columns}")
        # Add missing columns with NaN values
        for col in missing_columns:
            df[col] = pd.NA

    # Select only the target columns in the correct order
    formatted_df = df[target_columns].copy()

    # Log formatting information
    original_cols = len(df.columns)
    final_cols = len(formatted_df.columns)
    removed_cols = original_cols - final_cols

    if removed_cols > 0:
        logger.info(f"Auto-formatting: Removed {removed_cols} unnecessary columns")
        logger.info(f"Kept {final_cols} required columns out of {original_cols} total")

    return formatted_df


def load_data(
    file: Union[str, Path],
    encoding: Optional[str] = None,
    auto_detect_encoding: bool = True,
    date_columns: Optional[List[str]] = None,
    custom_na_values: Optional[List[str]] = None,
    auto_format: bool = True,
) -> pd.DataFrame:
    """
    Load data from a CSV file with improved error handling and mixed type handling.

    Args:
        file: File path or file object containing the CSV data
        encoding: Specific encoding to use (if None, will auto-detect or use utf-8)
        auto_detect_encoding: Whether to automatically detect file encoding
        date_columns: List of column names to parse as dates
        custom_na_values: Custom list of values to treat as NaN

    Returns:
        pd.DataFrame: Loaded and processed DataFrame

    Raises:
        FileNotFoundError: If the file doesn't exist
        pd.errors.EmptyDataError: If the CSV file is empty
        UnicodeDecodeError: If encoding issues cannot be resolved
    """
    # Handle file path
    if hasattr(file, "name"):
        file_path = file.name
    else:
        file_path = str(file)

    # Check if file exists
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Determine encoding
    if encoding is None and auto_detect_encoding:
        encoding = detect_encoding(file_path)
    elif encoding is None:
        encoding = "utf-8"

    # Default NA values
    na_values = [
        "",
        "NA",
        "null",
        "NULL",
        "NaN",
        "nan",
        "N/A",
        "#N/A",
        "#VALUE!",
        "#NULL!",
    ]
    if custom_na_values:
        na_values.extend(custom_na_values)

    # Encoding fallback sequence
    encodings_to_try = [encoding, "utf-8", "latin-1", "cp1252", "iso-8859-1"]

    for enc in encodings_to_try:
        try:
            logger.info(f"Attempting to read CSV with encoding: {enc}")

            # First, peek at the columns to determine if we have date columns
            if date_columns is None:
                try:
                    peek_df = pd.read_csv(file_path, nrows=0, encoding=enc)
                    potential_date_cols = [
                        col
                        for col in peek_df.columns
                        if "date" in col.lower() or "time" in col.lower()
                    ]
                    date_columns = potential_date_cols if potential_date_cols else None
                except Exception:
                    date_columns = None

            # Read CSV with comprehensive settings
            try:
                df = pd.read_csv(
                    file_path,
                    low_memory=False,
                    encoding=enc,
                    na_values=na_values,
                    keep_default_na=True,
                    parse_dates=date_columns if date_columns else False,
                    dtype_backend="numpy_nullable",  # Use nullable dtypes
                )
            except Exception as date_parse_error:
                # If date parsing fails, try without parsing dates
                logger.warning(
                    f"Date parsing failed: {date_parse_error}. "
                    "Retrying without date parsing."
                )
                df = pd.read_csv(
                    file_path,
                    low_memory=False,
                    encoding=enc,
                    na_values=na_values,
                    keep_default_na=True,
                    parse_dates=False,  # Disable date parsing
                    dtype_backend="numpy_nullable",
                )

            logger.info(f"Successfully loaded CSV with encoding: {enc}")
            logger.info(f"DataFrame shape: {df.shape}")

            # Auto-format the DataFrame if requested
            if auto_format:
                df = auto_format_csv(df)
                logger.info(f"Auto-formatted DataFrame shape: {df.shape}")

            # Log DataFrame info
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("DataFrame Info:")
                for col in df.columns:
                    logger.debug(f"{col}: {df[col].dtype}")

            return df

        except UnicodeDecodeError as e:
            logger.warning(f"Encoding {enc} failed: {e}")
            continue
        except Exception as e:
            logger.error(f"Error loading CSV with encoding {enc}: {e}")
            if enc == encodings_to_try[-1]:  # Last encoding attempt
                raise
            continue

    raise ValueError(
        f"Could not decode file with any of the attempted encodings: {encodings_to_try}"
    )


def get_date_range(
    df: pd.DataFrame, date_column: str = "Date", date_format: Optional[str] = None
) -> str:
    """
    Get date range from DataFrame, handling mixed types and missing values.

    Args:
        df: pandas DataFrame with a date column
        date_column: Name of the date column (default: 'Date')
        date_format: Specific date format to use for parsing

    Returns:
        str: formatted date range or status message
    """
    try:
        # Check if the DataFrame has the specified date column
        if date_column not in df.columns:
            logger.warning(f"Column '{date_column}' not found in DataFrame")
            return f"Date column '{date_column}' not available"

        # Drop any rows with NaN values in the date column
        # and attempt to convert the remaining values to datetime
        date_series = df[date_column].dropna()

        if date_series.empty:
            logger.warning("Date column is empty after dropping NaN values")
            return "No date data available"

        # Convert to datetime with error handling
        if date_format:
            try:
                date_series = pd.to_datetime(
                    date_series, format=date_format, errors="coerce"
                )
            except Exception:
                logger.warning(
                    f"Failed to parse dates with format {date_format}, "
                    "trying automatic parsing"
                )
                date_series = pd.to_datetime(date_series, errors="coerce")
        else:
            date_series = pd.to_datetime(date_series, errors="coerce")

        # Check if the resulting series contains any valid dates
        valid_dates = date_series.dropna()
        if valid_dates.empty:
            logger.warning("No valid dates found after parsing")
            return "No valid dates found"

        # Get the minimum and maximum dates from the series
        min_date = valid_dates.min()
        max_date = valid_dates.max()

        # Format the dates as strings
        min_date_str = min_date.strftime("%Y-%m-%d")
        max_date_str = max_date.strftime("%Y-%m-%d")

        # Return the formatted date range as a string
        date_range = f"{min_date_str} to {max_date_str}"
        logger.info(f"Date range: {date_range}")
        return date_range

    except Exception as e:
        # Log and return error message
        error_msg = f"Error processing dates: {str(e)}"
        logger.error(error_msg)
        return error_msg


def safe_sort(lst: List[Any]) -> List[Any]:
    """
    Sort list containing mixed types safely.

    This function sorts a list containing mixed data types (strings, numbers,
    NaN values) by converting all values to strings and handling NaN values
    appropriately.

    Args:
        lst: List containing mixed data types to sort

    Returns:
        List[Any]: Sorted list with NaN values filtered out
    """

    def key_func(item: Any) -> Tuple[int, str]:
        """
        Key function for sorting mixed types.

        Returns a tuple where:
        - First element (0 or 1) determines sort priority (0 for valid
          values, 1 for NaN)
        - Second element is the string representation for sorting
        """
        try:
            if pd.isna(item):
                return (1, "")
            elif isinstance(item, str):
                return (0, str(item).lower())
            else:
                return (0, str(item).lower())
        except Exception:
            # Fallback for any conversion issues
            return (1, "")

    try:
        # Filter out NaN values and sort the remaining items
        valid_items = [x for x in lst if pd.notna(x)]
        return sorted(valid_items, key=key_func)
    except Exception as e:
        logger.error(f"Error in safe_sort: {e}")
        # Return original list filtered of NaN values as fallback
        return [x for x in lst if pd.notna(x)]


def parse_datetime(
    date_str: str, date_formats: Optional[List[str]] = None
) -> Optional[datetime]:
    """
    Parse a date string using multiple format attempts.

    Args:
        date_str: String representation of a date
        date_formats: List of date formats to try (if None, uses common formats)

    Returns:
        datetime object if parsing succeeds, None otherwise
    """
    if not date_str or pd.isna(date_str):
        return None

    # Default date formats to try
    if date_formats is None:
        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %H:%M",
            "%d-%m-%Y",
            "%d-%m-%Y %H:%M:%S",
        ]

    # Try pandas to_datetime first (it's quite robust)
    try:
        return pd.to_datetime(date_str)
    except Exception:
        pass

    # Try each format manually
    for fmt in date_formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except (ValueError, TypeError):
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None


def validate_csv_structure(
    df: pd.DataFrame, required_columns: Optional[List[str]] = None, min_rows: int = 1
) -> Dict[str, Any]:
    """
    Validate the structure and content of a loaded CSV DataFrame.

    Args:
        df: DataFrame to validate
        required_columns: List of columns that must be present
        min_rows: Minimum number of rows required

    Returns:
        Dict with validation results including 'valid' boolean and 'issues' list
    """
    validation_result: Dict[str, Any] = {
        "valid": True,
        "issues": [],
        "warnings": [],
        "info": {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": df.dtypes.to_dict(),
            "memory_usage": df.memory_usage(deep=True).sum(),
        },
    }

    # Check minimum rows
    if len(df) < min_rows:
        validation_result["valid"] = False
        validation_result["issues"].append(
            f"DataFrame has {len(df)} rows, minimum required: {min_rows}"
        )

    # Check required columns
    if required_columns:
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            validation_result["valid"] = False
            validation_result["issues"].append(
                f"Missing required columns: {list(missing_columns)}"
            )

    # Check for completely empty columns
    empty_columns = df.columns[df.isnull().all()].tolist()
    if empty_columns:
        validation_result["warnings"].append(
            f"Completely empty columns: {empty_columns}"
        )

    # Check for duplicate columns
    duplicate_columns = df.columns[df.columns.duplicated()].tolist()
    if duplicate_columns:
        validation_result["valid"] = False
        validation_result["issues"].append(
            f"Duplicate column names: {duplicate_columns}"
        )

    # Memory usage warning
    memory_mb = validation_result["info"]["memory_usage"] / (1024 * 1024)
    if memory_mb > 100:  # Warn if over 100MB
        validation_result["warnings"].append(f"Large memory usage: {memory_mb:.1f} MB")

    return validation_result


def get_column_summary(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Get a comprehensive summary of a DataFrame column.

    Args:
        df: DataFrame containing the column
        column: Name of the column to summarize

    Returns:
        Dict with column statistics and information
    """
    if column not in df.columns:
        return {"error": f"Column '{column}' not found in DataFrame"}

    col_data = df[column]

    summary = {
        "column_name": column,
        "dtype": str(col_data.dtype),
        "total_count": len(col_data),
        "non_null_count": col_data.count(),
        "null_count": col_data.isnull().sum(),
        "null_percentage": (col_data.isnull().sum() / len(col_data)) * 100,
        "unique_count": col_data.nunique(),
        "unique_percentage": (
            (col_data.nunique() / col_data.count()) * 100 if col_data.count() > 0 else 0
        ),
    }

    # Add type-specific statistics
    if pd.api.types.is_numeric_dtype(col_data):
        summary.update(
            {
                "min": col_data.min(),
                "max": col_data.max(),
                "mean": col_data.mean(),
                "median": col_data.median(),
                "std": col_data.std(),
            }
        )
    elif pd.api.types.is_datetime64_any_dtype(col_data):
        summary.update(
            {
                "min_date": col_data.min(),
                "max_date": col_data.max(),
                "date_range": get_date_range(df, column),
            }
        )
    else:
        # String or categorical data
        value_counts = col_data.value_counts().head(10)
        summary.update(
            {
                "most_common_values": value_counts.to_dict(),
                "avg_length": (
                    col_data.astype(str).str.len().mean() if col_data.count() > 0 else 0
                ),
            }
        )

    return summary
