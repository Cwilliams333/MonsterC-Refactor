#!/usr/bin/env python3

import pandas as pd


def analyze_test_failures():
    # Read the CSV file
    df = pd.read_csv("test_data/feb7_feb10Pull.csv")

    # Filter for automation failures (specific operators)
    automation_operators = [
        "STN251_RED(id:10089)",
        "STN252_RED(id:10090)",
        "STN351_GRN(id:10380)",
        "STN352_GRN(id:10381)",
    ]
    automation_df = df[df["Operator"].isin(automation_operators)]

    print(f"Total records: {len(df)}")
    print(f"Automation records: {len(automation_df)}")

    # Focus on result_FAIL column for non-empty values
    fail_data = automation_df[
        automation_df["result_FAIL"].notna() & (automation_df["result_FAIL"] != "")
    ]

    print(f"Records with failure data: {len(fail_data)}")

    # Get unique values in result_FAIL column
    unique_failures = fail_data["result_FAIL"].value_counts()

    print("\n=== UNIQUE VALUES IN result_FAIL COLUMN ===")
    for failure_string, count in unique_failures.items():
        print(f'{count:3d} occurrences: "{failure_string}"')

    print("\n=== TOP 10 MOST FREQUENT TEST CASE STRINGS ===")
    top_10 = unique_failures.head(10)
    for i, (failure_string, count) in enumerate(top_10.items(), 1):
        print(f'{i:2d}. {count:3d} occurrences: "{failure_string}"')

    print("\n=== CONCATENATED TEST CASES (containing commas) ===")
    concatenated = unique_failures[unique_failures.index.str.contains(",", na=False)]
    print(f"Found {len(concatenated)} unique concatenated test case strings:")
    for failure_string, count in concatenated.items():
        print(f'{count:3d} occurrences: "{failure_string}"')

    print("\n=== SAMPLE RECORDS WITH CONCATENATED FAILURES ===")
    concat_records = fail_data[fail_data["result_FAIL"].str.contains(",", na=False)]
    print(f"Found {len(concat_records)} records with concatenated failures:")
    for _, row in concat_records.head(10).iterrows():
        print(
            f'Station: {row["Operator"]}, Model: {row["Model"]}, Date: {row["Date Time"]}, Failures: "{row["result_FAIL"]}"'
        )

    # Additional analysis: breakdown by station
    print("\n=== FAILURE BREAKDOWN BY STATION ===")
    station_failures = fail_data.groupby("Operator")["result_FAIL"].value_counts()
    for (station, failure), count in station_failures.items():
        print(f'{station}: {count} occurrences of "{failure}"')


if __name__ == "__main__":
    analyze_test_failures()
