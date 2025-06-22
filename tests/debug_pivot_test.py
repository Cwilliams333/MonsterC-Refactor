#!/usr/bin/env python3
"""
Debug script to test pivot table calculations with actual CSV data.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src directory to Python path for imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from common.logging_config import get_logger
from services.pivot_service import create_excel_style_failure_pivot

# Configure logging
logger = get_logger(__name__)


def main():
    # Load the test CSV file
    csv_file = "test_data/feb7_feb10Pull.csv"

    try:
        # Load the raw data
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded raw CSV with {len(df)} rows")

        # Show some sample raw data
        logger.info("Sample raw data:")
        for i, (_, row) in enumerate(df.head(10).iterrows()):
            logger.info(
                f"Row {i}: Model={row['Model']}, Station={row['Station ID']}, Result_FAIL={row['result_FAIL']}"
            )

        # Create the pivot table (this is what the dashboard uses)
        pivot_result = create_excel_style_failure_pivot(df, operator_filter=None)

        logger.info(f"\nCreated pivot table with shape: {pivot_result.shape}")
        logger.info(f"Pivot columns: {list(pivot_result.columns)}")

        # Show some sample pivot data
        logger.info("\nSample pivot data (first 10 rows):")
        for i, (_, row) in enumerate(pivot_result.head(10).iterrows()):
            # Show key info for each row
            station_cols = [
                col
                for col in pivot_result.columns
                if col not in ["result_FAIL", "Model"]
            ]
            total_failures = row[station_cols].sum()
            logger.info(
                f"Pivot Row {i}: Test={row['result_FAIL']}, Model={row['Model']}, Total failures={total_failures}"
            )

            # Show station breakdown for this row
            non_zero_stations = [
                (col, row[col]) for col in station_cols if row[col] > 0
            ]
            if non_zero_stations:
                logger.info(f"  Non-zero stations: {non_zero_stations}")

        # Check specific cases user mentioned
        logger.info("\n=== CHECKING USER'S SPECIFIC CASES ===")

        # 1. iPhone14ProMax in Camera Pictures
        iphone14_camera = pivot_result[
            (pivot_result["Model"] == "iPhone14ProMax")
            & (pivot_result["result_FAIL"] == "Camera Pictures")
        ]

        if not iphone14_camera.empty:
            logger.info("iPhone14ProMax + Camera Pictures rows:")
            for _, row in iphone14_camera.iterrows():
                station_cols = [
                    col
                    for col in pivot_result.columns
                    if col not in ["result_FAIL", "Model"]
                ]
                total = row[station_cols].sum()
                logger.info(f"  Total failures: {total}")
                non_zero = [(col, row[col]) for col in station_cols if row[col] > 0]
                logger.info(f"  Non-zero stations: {non_zero}")
        else:
            logger.info("No iPhone14ProMax + Camera Pictures combination found!")

        # 2. Camera Pictures test case total
        camera_pictures = pivot_result[pivot_result["result_FAIL"] == "Camera Pictures"]
        if not camera_pictures.empty:
            logger.info(f"\nCamera Pictures test case ({len(camera_pictures)} rows):")
            station_cols = [
                col
                for col in pivot_result.columns
                if col not in ["result_FAIL", "Model"]
            ]
            total_camera_failures = 0
            for _, row in camera_pictures.iterrows():
                row_total = row[station_cols].sum()
                total_camera_failures += row_total
                logger.info(f"  {row['Model']}: {row_total} failures")
            logger.info(f"  TOTAL Camera Pictures failures: {total_camera_failures}")

        # 3. radi056 station total
        if "radi056" in pivot_result.columns:
            radi056_total = pivot_result["radi056"].sum()
            logger.info(f"\nradi056 station total: {radi056_total}")

            # Show breakdown
            non_zero_radi056 = pivot_result[pivot_result["radi056"] > 0]
            logger.info(f"radi056 non-zero entries ({len(non_zero_radi056)} rows):")
            for _, row in non_zero_radi056.iterrows():
                logger.info(
                    f"  {row['result_FAIL']} - {row['Model']}: {row['radi056']} failures"
                )
        else:
            logger.info("radi056 column not found in pivot table!")

        # Show all station totals for verification
        logger.info("\n=== ALL STATION TOTALS ===")
        station_cols = [
            col for col in pivot_result.columns if col not in ["result_FAIL", "Model"]
        ]
        station_totals = {}
        for col in station_cols:
            station_totals[col] = pivot_result[col].sum()

        # Sort by total (highest first)
        sorted_stations = sorted(
            station_totals.items(), key=lambda x: x[1], reverse=True
        )
        for i, (station, total) in enumerate(sorted_stations[:10]):
            logger.info(f"{i+1}. {station}: {total} total failures")

        # Test the new individual cell value calculation
        logger.info("\n=== NEW INDIVIDUAL CELL VALUE CALCULATIONS ===")
        from dash_pivot_app import calculate_pivot_summary_stats

        summary_stats = calculate_pivot_summary_stats(pivot_result)

        logger.info(
            f"🏆 Highest Model Cell: {summary_stats['highest_model']['name']} with {summary_stats['highest_model']['count']} failures"
        )
        logger.info(
            f"   Context: {summary_stats['highest_model']['test_case']} at station {summary_stats['highest_model']['station']}"
        )

        logger.info(
            f"📊 Highest Test Case Cell: {summary_stats['highest_test_case']['name']} with {summary_stats['highest_test_case']['count']} failures"
        )
        logger.info(
            f"   Context: {summary_stats['highest_test_case']['model']} at station {summary_stats['highest_test_case']['station']}"
        )

        logger.info(
            f"🔧 Highest Station Cell: {summary_stats['highest_station']['name']} with {summary_stats['highest_station']['count']} failures"
        )
        logger.info(
            f"   Context: {summary_stats['highest_station']['test_case']} with {summary_stats['highest_station']['model']}"
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
