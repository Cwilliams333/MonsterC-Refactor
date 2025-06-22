from datetime import datetime

import gradio as gr
import pandas as pd
import plotly.express as px

test_to_result_fail_map = {
    "Display": [
        "Hot pixel analysis",
        "Burn in",
        "Blemish analysis",
        "6Y-Bad/Dead pixels/Lines/Areas",
        "6L-White Discolored Area",
        "6X-Display Burn-In of any type",
        "6M-Discolored DSP/Pressure Point",
        "6A-Display Fail",
        "6W-Horizontal/Vertical lines",
    ],
    "Mic": ["AQA_Microphone"],
    "Camera front photo": ["Front camera", "Front Camera"],
    "Camera rear photo": ["Camera Pictures", "Camera pictures", "Camera"],
    "Camera Flash": ["Camera Flash", "Camera flash"],
    "Speaker": ["AQA_Speaker"],
    "speaker": ["AQA_Earpiece"],
    "Touch": ["Touch screen", "Touch Screen"],
    "Vibration Engine": ["Device Vibrate", "Device vibrate"],
    "Proximity": ["Proximity sensor"],
    "Headset": ["AQA_Headset"],
}

station_to_machine = {
    "radi135": "B56 Red Primary",
    "radi138": "B56 Red Primary",
    "radi115": "B56 Red Primary",
    "radi163": "B56 Red Primary",
    "radi185": "B56 Red Primary",
    "radi133": "B56 Red Primary",
    "radi160": "B18 Red Secondary",
    "radi161": "B18 Red Secondary",
    "radi162": "B18 Red Secondary",
    "radi181": "B18 Red Secondary",
    "radi183": "B18 Red Secondary",
    "radi116": "B18 Red Secondary",
    "radi154": "B25 Green Secondary",
    "radi155": "B25 Green Secondary",
    "radi156": "B25 Green Secondary",
    "radi166": "B25 Green Secondary",
    "radi158": "B25 Green Secondary",
    "radi157": "B25 Green Secondary",
    "radi149": "B17 Green Primary",
    "radi151": "B17 Green Primary",
    "radi152": "B17 Green Primary",
    "radi165": "B17 Green Primary",
    "radi164": "B17 Green Primary",
    "radi153": "B17 Green Primary",
    "radi079": "B24 Manual Trades",
    "radi044": "B24 Manual Trades",
    "radi041": "B24 Manual Trades",
    "radi055": "B22 Manual Core",
    "radi052": "B22 Manual Core",
    "radi058": "B22 Manual Core",
    "radi056": "B22 Manual Core",
    "radi078": "B22 Manual Core",
    "radi062": "B22 Manual Core",
    "radi081": "B22 Manual Core",
    # LS NPI Area
    "radi117": "B56 NPI Area",
    # New Bertta37 DHL stations
    "radi173": "B37 Packers",
    "radi177": "B37 Packers",
    "radi180": "B37 Packers",
    "radi172": "B37 Packers",
    "radi175": "B37 Packers",
    "radi176": "B37 Packers",
    # New Bertta58 DHL stations
    "radi169": "B58 Hawks",
    "radi171": "B58 Hawks",
    "radi174": "B58 Hawks",
    "radi178": "B58 Hawks",
    "radi179": "B58 Hawks",
    "radi182": "B58 Hawks",
}

device_map = {
    "iPhone6": "iphone7,2",
    "iPhone6 Plus": "iphone7,1",
    "iPhone6S": "iphone8,1",
    "iPhone6S Plus": "iphone8,2",
    "iPhoneSE (1st Gen)": "iphone8,4",
    "iPhone7": ["iphone9,1", "iphone9,3"],
    "iPhone7Plus": ["iphone9,2", "iphone9,4"],
    "iPhone8": "iphone10,1",
    "iPhone8Plus": ["iphone10,2", "iphone10,5"],
    "iPhoneX": ["iphone10,3", "iphone10,6"],
    "iPhoneXR": "iphone11,8",
    "iPhoneXS": "iphone11,2",
    "iPhoneXS-Max": ["iphone11,4", "iphone11,6"],
    "iPhone11": "iphone12,1",
    "iPhone11Pro": "iphone12,3",
    "iPhone11ProMax": "iphone12,5",
    "iPhoneSE2": "iphone12,8",
    "iPhone12": "iphone13,2",
    "iPhone12mini": "iphone13,1",
    "iPhone12Mini": "iphone13,1",
    "iPhone12Pro": "iphone13,3",
    "iPhone12ProMax": "iphone13,4",
    "iPhone13": "iphone14,5",
    "iPhone13mini": "iphone14,4",
    "iPhone13Mini": "iphone14,4",
    "iPhone13Pro": "iphone14,2",
    "iPhone13ProMax": "iphone14,3",
    "iPhoneSE3": "iphone14,6",
    "iPhone14": "iphone14,7",
    "iPhone14Plus": "iphone14,8",
    "iPhone14Pro": "iphone15,2",
    "iPhone14ProMax": "iphone15,3",
    "iPhone15": "iphone15,4",
    "iPhone15Plus": "iphone15,5",
    "iPhone15Pro": "iphone16,1",
    "iPhone15ProMax": "iphone16,2",
    "iPhone16": "iphone17,3",
    "iPhone16Plus": "iphone17,4",
    "iPhone16Pro": "iphone17,1",
    "iPhone16ProMax": "iphone17,2",
    "SM-G996U": "t2q",
    "SM-A156U": "a15x",
    "SM-A037U": "a03su",
    "SM-S928U": "e3q",
    "SM-S926U": "e2q",
    "SM-S921U": "e1q",
    "SM-G991U": "o1q",
    "SM-G998U": "p3q",
    "SM-G781V": "r8q",
    "SM-S906U": "g0q",
    "SM-S901U": "r0q",
    "SM-A515U": "a51",
    "SM-A426U": "a42xuq",
    "SM-A426U1": "a42xuq",
    "SM-G981V": "x1q",
    "SM-N986U": "c2q",
    "SM-G970U": "beyond0q",
    "SM-G965U": "star2qltesq",
    "SM-G960U": "starqltesq",
    "SM-G975U": "beyond2q",
    "SM-G986U": "y2q",
    "SM-S908U": "b0q",
    "SM-S911U": "dm1q",
    "SM-S918U": "dm3q",
    "SM-S916U": "dm2q",
    "SM-N960U": "crownqltesq",
    "SM-N975U": "d2q",
    "SM-N970U": "d1q",
    "SM-A215U": "a21",
    "SM-A505U": "a50",
    "SM-A716V": "a71xq",
    "SM-G950U": "dreamqltesq",
    "SM-A236V": "a23x",
    "Pixel 6a": "bluejay",
    "Pixel 6": "oriole",
    "Pixel 6 Pro": "raven",
    "Pixel 7": "panther",
    "Pixel 7a": "lynx",
    "Pixel 7 Pro": "cheetah",
    "Pixel 8": "shiba",
    "Pixel 8 Pro": "husky",
    "Pixel 8a": "akita",
    "Pixel 9": "tokay",
    "Pixel 9 Pro": "caiman",
    "Pixel 9 Pro XL": "komodo",
    "SM-G973U": "beyond1q",
    "SM-G973U1": "beyond1q",
    "SM-G988U": "z3q",
    "SM-G991U1": "o1q",
    "SM-S926U": "e2q",
    "SM-A102U": "a10e",
    "SM-A205U": "a20q",
    "SM-S711U": "r11q",
    "SM-S721U": "r12s",
    "SM-S938U": "pa3q",
    "SM-S936U": "pa2q",
    "SM-S931U": "pa1q",
}


def load_data(file):
    """
    Load data from a CSV file with improved error handling and mixed type handling.

    Args:
        file: File object containing the CSV data

    Returns:
        pd.DataFrame: Loaded and processed DataFrame
    """
    try:
        # Read CSV with low_memory=False to prevent DtypeWarning
        df = pd.read_csv(
            file.name,
            low_memory=False,
            # Handle potential encoding issues
            encoding="utf-8",
            # Handle missing values consistently
            na_values=["", "NA", "null", "NULL", "NaN"],
            # Handle potential date parsing
            parse_dates=(
                ["Date"] if "Date" in pd.read_csv(file.name, nrows=0).columns else False
            ),
        )

        # Print DataFrame info for debugging
        print("\nDataFrame Info:")
        print(df.info())

        # Print data types of columns
        print("\nColumn Data Types:")
        for col in df.columns:
            print(f"{col}: {df[col].dtype}")

        # Optional: Print sample of problematic column (adjust index 8 as needed)
        if len(df.columns) > 8:
            problem_col = df.columns[8]
            print(f"\nSample of column {problem_col}:")
            print(df[problem_col].head())
            print(f"Unique values in {problem_col}:", df[problem_col].unique())

        return df

    except Exception as e:
        print(f"Error loading CSV file: {str(e)}")
        # Return empty DataFrame in case of error
        return pd.DataFrame()


def create_pivot_table(df, rows, columns, values, aggfunc="count"):
    """
    Creates a pivot table from the given DataFrame based on user selections.

    Args:
        df (pd.DataFrame): Input DataFrame
        rows (list): Columns to use as row indices
        columns (list): Columns to use as column indices
        values (str): Column to aggregate
        aggfunc (str): Aggregation function to use
    """
    try:
        if not rows or not values:
            return (
                pd.DataFrame()
            )  # Return empty DataFrame if required fields are missing

        # Handle the aggregation function
        if aggfunc == "count":
            aggfunc = "size"

        # Create pivot table
        pivot = pd.pivot_table(
            df,
            index=rows,
            columns=columns if columns else None,
            values=values if aggfunc != "size" else None,
            aggfunc=aggfunc,
            fill_value=0,
        )

        # Reset index for better display
        pivot = pivot.reset_index()

        # Flatten column names if they're multi-level
        if isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = [
                f"{col[0]}_{col[1]}" if isinstance(col, tuple) else col
                for col in pivot.columns
            ]

        return pivot

    except Exception as e:
        print(f"Error creating pivot table: {str(e)}")
        return pd.DataFrame({"Error": [str(e)]})


def generate_pivot_table(
    df, rows, columns, aggfunc, filter_operator, filter_station_id, filter_model
):
    """
    Wrapper function to generate the pivot table with filtering and handle exceptions.

    :param df: Input DataFrame
    :param rows: Columns to use as row indices
    :param columns: Columns to use as column indices
    :param aggfunc: Aggregation function to use
    :param filter_operator: List of operators to filter by
    :param filter_station_id: List of station IDs to filter by
    :param filter_model: List of models to filter by
    :return: A styled DataFrame with the pivot table, or an error message if there is an exception
    """
    try:
        # Make a copy of the original DataFrame to avoid modifying it
        filtered_df = df.copy()

        # Apply filters based on user selections
        if filter_operator and "All" not in filter_operator:
            # Filter by operator
            filtered_df = filtered_df[filtered_df["Operator"].isin(filter_operator)]
        if filter_station_id and "All" not in filter_station_id:
            # Filter by station ID
            filtered_df = filtered_df[filtered_df["Station ID"].isin(filter_station_id)]
        if filter_model and "All" not in filter_model:
            # Filter by model
            filtered_df = filtered_df[filtered_df["Model"].isin(filter_model)]

        # Generate the pivot table based on user selections, using 'count' as a default aggregation
        pivot = pd.pivot_table(
            filtered_df,
            index=rows,
            columns=columns,
            aggfunc="size",  # Use 'size' to count occurrences of rows
            fill_value=0,
        )

        # Apply styling to highlight rows with the highest counts
        if not pivot.empty:
            # Get the sum of each row to determine highest counts
            row_sums = pivot.sum(axis=1)

            # Get indices of top 4 highest counts
            top_indices = row_sums.nlargest(4).index

            def highlight_rows(val):
                """Highlight the row based on its rank among the top 4 highest."""
                if val.name in top_indices:
                    rank = top_indices.get_loc(val.name)
                    if rank == 0:
                        # Red for highest count
                        return ["background-color: red"] * len(val)
                    elif rank == 1:
                        # Orange for second highest count
                        return ["background-color: orange"] * len(val)
                    elif rank == 2:
                        # Yellow for third highest count
                        return ["background-color: yellow"] * len(val)
                    elif rank == 3:
                        # Green for fourth highest count
                        return ["background-color: green"] * len(val)
                # No highlighting for other rows
                return [""] * len(val)

            # Apply the highlighting
            styled_pivot = pivot.style.apply(highlight_rows, axis=1)

            # Return the styled DataFrame
            return styled_pivot

        # Return the pivot table if there are no rows to style
        return pivot

    except Exception as e:
        # Handle any exceptions that occur and return an error message
        return pd.DataFrame({"Error": [str(e)]})


def find_top_failing_stations(pivot, top_n=5):
    """
    Finds the top failing stations based on the provided pivot table.

    :param pivot: A Pandas DataFrame with a pivot table structure, where the
                  index is the model, the columns are the test cases, and the
                  values are the counts of failures for each test case
    :type pivot: pandas.DataFrame
    :param top_n: The number of top failing stations to return
    :type top_n: int
    :return: A Series with the top failing stations and their failure counts
    :rtype: pandas.Series
    """
    # Get the sum of all failures for each station
    station_failures = pivot.sum().fillna(0)

    # Get the top N failing stations
    return station_failures.nlargest(top_n)


def analyze_top_models(pivot, top_stations, top_n=5):
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

    The function first filters the pivot table to only include the top failing stations. Then, it sums up the
    counts for each model and returns the top N models with the highest total counts.

    The resulting Series has the model names as the index and the total number of failures as the values.
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


def analyze_top_test_cases(pivot, top_stations, top_n=5):
    """
    Analyzes the top test cases based on the provided pivot table and top failing stations.

    The pivot table is filtered to only include the top failing stations. Then, the test cases are grouped
    by their result (SUCCESS/FAILURE), and the sum of each group is calculated. This gives us the total
    number of test cases that failed for each station.

    Finally, the top N test cases are returned, sorted by their failure count in descending order.
    """
    # Filter the pivot table to only include the top failing stations
    top_stations_pivot = pivot[top_stations.index]

    # Group the test cases by their result (SUCCESS/FAILURE) and calculate the sum of each group
    test_case_failures = (
        top_stations_pivot.groupby("result_FAIL").sum().sum(axis=1).fillna(0)
    )

    # Return the top N test cases, sorted by their failure count in descending order
    return test_case_failures.nlargest(top_n)


def create_summary_chart(data, title):
    """
    Creates a summary chart based on the provided data and title with enhanced styling.
    """
    # Color scheme for consistent styling
    color_scheme = {
        "SUCCESS": "#2ECC71",  # Green
        "FAILURE": "#E74C3C",  # Red
        "ERROR": "#F39C12",  # Orange
        "background": "#F7F9FB",
        "gridlines": "#E0E6ED",
    }

    # Create the bar chart with enhanced styling
    fig = px.bar(
        x=data.index.astype(str),
        y=data.values,
        title=title,
        labels={"x": "Category", "y": "Count"},
        color_discrete_sequence=[color_scheme["FAILURE"]],  # Use failure color for bars
    )

    # Add value labels on top of bars
    fig.update_traces(texttemplate="%{y}", textposition="outside")

    # Apply consistent styling
    fig.update_layout(
        plot_bgcolor=color_scheme["background"],
        paper_bgcolor="white",
        font=dict(size=12),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(
            title="Category",
            tickangle=-45,
            showgrid=True,
            gridwidth=1,
            gridcolor=color_scheme["gridlines"],
            showline=True,
            linewidth=2,
            linecolor=color_scheme["gridlines"],
        ),
        yaxis=dict(
            title="Count",
            showgrid=True,
            gridwidth=1,
            gridcolor=color_scheme["gridlines"],
            showline=True,
            linewidth=2,
            linecolor=color_scheme["gridlines"],
        ),
    )

    return fig


def format_dataframe(data):
    """
    Formats a given dataframe for display.

    The purpose of this function is to take an input DataFrame and format it
    in a way that is easy to display. The output DataFrame should have two
    columns: "Category" and "Count".

    If the input DataFrame has a MultiIndex, the function will
    1. Reset the index of the DataFrame to create a new column for the index.
    2. Create a new column called "Category" that combines the two index columns
       with a hyphen in between.
    3. Drop the original index columns.
    4. Rename the columns to "Category" and "Count".

    If the input DataFrame does not have a MultiIndex, the function will
    1. Reset the index of the DataFrame to create a new column for the index.
    2. Rename the columns to "Category" and "Count".
    """
    df = pd.DataFrame({"Count": data})
    if isinstance(df.index, pd.MultiIndex):
        # Reset the index to create a new column for the index
        df = df.reset_index()

        # Create a new column that combines the two index columns with a hyphen in between
        df["Category"] = df.apply(lambda row: f"{row[0]} - {row[1]}", axis=1)

        # Drop the original index columns
        df = df[["Category", "Count"]]
    else:
        # Reset the index to create a new column for the index
        df = df.reset_index()

        # Rename the columns to "Category" and "Count"
        df.columns = ["Category", "Count"]
    return df


def analyze_top_errors_by_model(df, top_n=5):
    """
    Analyzes the top errors by model in a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing error data with columns "Model", "error_code", and "error_message".
        top_n (int): The number of top errors to return. Defaults to 5.

    Returns:
        pd.DataFrame: DataFrame containing the top errors by model, sorted by count.
    """
    # Group the DataFrame by "Model", "error_code", and "error_message"
    # Count the number of occurrences for each group
    error_counts = (
        df.groupby(["Model", "error_code", "error_message"])
        .size()  # Count occurrences
        .reset_index(
            name="count"
        )  # Convert the result into a DataFrame with a "count" column
    )

    # Sort the resulting DataFrame by the "count" column in descending order
    # Select the top N entries based on the "count"
    top_errors = error_counts.sort_values("count", ascending=False).head(top_n)

    # Create a new "error" column by concatenating "error_code" and "error_message"
    top_errors["error"] = (
        top_errors["error_code"].astype(str)  # Convert error code to string
        + ": "  # Add separator
        + top_errors["error_message"].astype(str)  # Convert error message to string
    )

    # Return the DataFrame containing the top errors
    return top_errors


def analyze_overall_status(df):
    """
    Analyzes the overall status of a given DataFrame.
    """
    return df["Overall status"].value_counts()


def create_top_errors_chart(data, title):
    """
    Creates a bar chart displaying the top errors by model.
    """
    fig = px.bar(
        data,
        x="Model",
        y="count",
        color="error",
        title=title,
        labels={"count": "Error Count", "error": "Error Type"},
    )
    fig.update_layout(xaxis_title="Model", yaxis_title="Count", xaxis_tickangle=-45)
    return fig


def create_overall_status_chart(data, title):
    """
    Creates an enhanced status pie chart with custom styling and interactivity.

    Args:
        data: DataFrame or Series containing the status counts
        title: Chart title
    """
    # Create a base pie chart with Plotly Express using custom colors for each status
    fig = px.pie(
        values=data.values,  # Values for the pie chart slices
        names=data.index,  # Names/labels for each slice
        title=title,  # Title of the pie chart
        color=data.index,  # Color the slices based on their names
        color_discrete_map={  # Define custom colors for specific statuses
            "SUCCESS": "#00C853",  # Brighter green for success
            "FAILURE": "#D50000",  # Deeper red for failures
            "ERROR": "#FF9100",  # Vibrant orange for errors
        },
    )

    # Update trace properties for enhanced styling and interactivity
    fig.update_traces(
        textposition="inside",  # Display text inside the slices
        textinfo="percent+label",  # Show both percentage and label inside slices
        hovertemplate="<b>%{label}</b><br>"  # Customize hover information
        + "Count: %{value}<br>"  # Show count of each status
        + "Percentage: %{percent}<extra></extra>",  # Show percentage
        marker=dict(line=dict(color="white", width=2)),  # White border around slices
        pull=[0.1, 0.1, 0.1],  # Slightly separate each slice for emphasis
        rotation=90,  # Rotate the starting point of the chart to the top
    )

    # Customize overall layout settings
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",  # Bold the chart title
            x=0.5,  # Center the title horizontally
            y=0.95,  # Position title near the top
            xanchor="center",  # Anchor title to center
            yanchor="top",  # Anchor title to the top
            font=dict(size=20),  # Set font size of the title
        ),
        showlegend=True,  # Display legend on the chart
        legend=dict(
            orientation="h",  # Set legend to be horizontal
            yanchor="bottom",  # Anchor legend to the bottom
            y=-0.2,  # Position legend below the chart
            xanchor="center",  # Center the legend horizontally
            x=0.5,  # Center the legend on the x-axis
        ),
        margin=dict(t=80, b=80, l=40, r=40),  # Set margins around the chart
        paper_bgcolor="rgba(0,0,0,0)",  # Set paper background to be transparent
        plot_bgcolor="rgba(0,0,0,0)",  # Set plot background to be transparent
    )

    return fig  # Return the fully customized figure


def get_date_range(df):
    """
    Safely gets the date range from a DataFrame, handling mixed types and missing values.

    Args:
        df: pandas DataFrame with a 'Date' column

    Returns:
        str: formatted date range or status message
    """
    try:
        # Check if the DataFrame has a 'Date' column
        if "Date" not in df.columns:
            print("Date information not available")
            return "Date information not available"

        # Drop any rows with NaN values in the 'Date' column
        # and attempt to convert the remaining values to datetime
        date_series = pd.to_datetime(df["Date"].dropna(), errors="coerce")

        # Check if the resulting series is empty or contains all NaN values
        if date_series.empty or date_series.isna().all():
            print("No valid dates found")
            return "No valid dates found"

        # Get the minimum and maximum dates from the series
        min_date = date_series.min()
        max_date = date_series.max()

        # Format the dates as strings
        min_date_str = min_date.strftime("%Y-%m-%d")
        max_date_str = max_date.strftime("%Y-%m-%d")

        # Return the formatted date range as a string
        return f"{min_date_str} to {max_date_str}"

    except Exception as e:
        # Print any errors that occur during processing
        print(f"Error processing dates: {str(e)}")
        return "Error processing date range"


def perform_analysis(csv_file):
    """
    Performs comprehensive analysis on test results data from a CSV file.

    Args:
        csv_file: File object containing the CSV data

    Returns:
        tuple: (
            summary (str),
            overall_fig (plotly figure),
            stations_fig (plotly figure),
            models_fig (plotly figure),
            test_cases_fig (plotly figure),
            stations_data (list),
            models_data (list),
            test_cases_data (list)
        )
    """
    try:
        # Define color scheme for consistent styling across charts
        COLOR_SCHEME = {
            "SUCCESS": "#2ECC71",  # Green for success
            "FAILURE": "#E74C3C",  # Red for failures
            "ERROR": "#F39C12",  # Orange for errors
            "background": "#F7F9FB",  # Light background
            "gridlines": "#E0E6ED",  # Light gridlines
            "text": "#2C3E50",  # Dark blue text
            "highlight": "#3498DB",  # Light blue for highlights
        }

        # Helper function to apply consistent styling to plotly charts
        def style_chart(fig, title, height=500):
            """
            Applies consistent styling to plotly figures.

            Args:
                fig: plotly figure object
                title: str, chart title
                height: int, chart height in pixels

            Returns:
                plotly figure object with applied styling
            """
            fig.update_layout(
                title=dict(
                    text=title,  # Set the chart title
                    font=dict(
                        size=16, color=COLOR_SCHEME["text"]
                    ),  # Font size and color for title
                    x=0.5,  # Center the title
                    xanchor="center",
                ),
                plot_bgcolor=COLOR_SCHEME["background"],  # Set plot background color
                paper_bgcolor="white",  # Set paper background color
                font=dict(
                    family="Arial",
                    size=12,
                    color=COLOR_SCHEME["text"],  # Set font color for the entire chart
                ),
                margin=dict(l=40, r=40, t=60, b=40),  # Define chart margins
                showlegend=True,  # Display legend
                legend=dict(
                    orientation="h",  # Horizontal legend
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
                height=height,  # Set the height of the chart
                xaxis=dict(
                    gridcolor=COLOR_SCHEME["gridlines"],  # Gridline color
                    showline=True,
                    linewidth=1,
                    linecolor=COLOR_SCHEME["gridlines"],  # Line color
                ),
                yaxis=dict(
                    gridcolor=COLOR_SCHEME["gridlines"],
                    showline=True,
                    linewidth=1,
                    linecolor=COLOR_SCHEME["gridlines"],
                ),
            )
            return fig

        # Helper function to check for missing data in a DataFrame column
        def handle_missing_data(df, column):
            """
            Checks and logs missing data in specified column.

            Args:
                df: pandas DataFrame
                column: str, column name to check

            Returns:
                int: number of missing values
            """
            missing = df[column].isna().sum()
            if missing > 0:
                print(f"Warning: Found {missing} missing values in {column}")
            return missing

        # Load CSV data into a pandas DataFrame
        df = pd.read_csv(csv_file.name)

        # List of required columns for analysis
        required_columns = [
            "Overall status",
            "Model",
            "Station ID",
            "result_FAIL",
            "Date",
        ]
        # Check if any required columns are missing
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        # Check data quality for each required column
        for column in required_columns:
            if column in df.columns:
                handle_missing_data(df, column)

        # Calculate basic statistics from the data
        total_tests = len(df)  # Total number of tests
        valid_tests = len(
            df[df["Overall status"].notna()]
        )  # Tests with non-null status
        failed_tests = len(
            df[df["Overall status"] == "FAILURE"]
        )  # Count of failed tests
        error_tests = len(df[df["Overall status"] == "ERROR"])  # Count of error tests
        success_tests = len(
            df[df["Overall status"] == "SUCCESS"]
        )  # Count of successful tests
        pass_rate = (
            (success_tests / valid_tests * 100) if valid_tests > 0 else 0
        )  # Calculate pass rate

        # Create timestamp and date range info
        analysis_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )  # Current timestamp
        date_range = get_date_range(df)  # Get date range from data

        # Analyze station failures
        station_failures = df[
            (df["Overall status"].isin(["FAILURE", "ERROR"]))
            & (df["Station ID"].notna())  # Filter for non-null station IDs
        ][
            "Station ID"
        ].value_counts()  # Count failures per station

        # Create bar chart for top 10 failing stations
        stations_fig = px.bar(
            x=station_failures.head(10).index,
            y=station_failures.head(10).values,
            title="Top 10 Failing Stations",
            labels={"x": "Station ID", "y": "Number of Failures"},
            color_discrete_sequence=[
                COLOR_SCHEME["FAILURE"]
            ],  # Use failure color for bars
        )
        # Add text and hover information to the chart
        stations_fig.update_traces(
            texttemplate="%{y}",
            textposition="outside",
            hovertemplate="<b>Station:</b> %{x}<br><b>Failures:</b> %{y}<extra></extra>",
        )
        style_chart(stations_fig, "Top 10 Failing Stations")  # Apply styling

        # Analyze model failures
        model_failures = df[
            (df["Overall status"].isin(["FAILURE", "ERROR"]))
            & (df["Model"].notna())  # Filter for non-null models
            & (df["Model"] != "None")  # Exclude 'None' values
        ][
            "Model"
        ].value_counts()  # Count failures per model

        # Create bar chart for top 10 failing models
        models_fig = px.bar(
            x=model_failures.head(10).index,
            y=model_failures.head(10).values,
            title="Top 10 Failing Models",
            labels={"x": "Model", "y": "Number of Failures"},
            color_discrete_sequence=[COLOR_SCHEME["FAILURE"]],
        )
        # Add text and hover information to the chart
        models_fig.update_traces(
            texttemplate="%{y}",
            textposition="outside",
            hovertemplate="<b>Model:</b> %{x}<br><b>Failures:</b> %{y}<extra></extra>",
        )
        style_chart(models_fig, "Top 10 Failing Models")  # Apply styling

        # Analyze test case failures
        test_case_failures = df[
            df["result_FAIL"].notna()  # Filter for non-null test cases
            & (df["result_FAIL"] != "")  # Exclude empty strings
        ][
            "result_FAIL"
        ].value_counts()  # Count failures per test case

        # Create bar chart for top 10 failing test cases
        test_cases_fig = px.bar(
            x=test_case_failures.head(10).index,
            y=test_case_failures.head(10).values,
            title="Top 10 Failing Test Cases",
            labels={"x": "Test Case", "y": "Number of Failures"},
            color_discrete_sequence=[COLOR_SCHEME["FAILURE"]],
        )
        # Add text and hover information to the chart
        test_cases_fig.update_traces(
            texttemplate="%{y}",
            textposition="outside",
            hovertemplate="<b>Test Case:</b> %{x}<br><b>Failures:</b> %{y}<extra></extra>",
        )
        style_chart(test_cases_fig, "Top 10 Failing Test Cases")  # Apply styling

        # Create overall status distribution pie chart
        status_counts = df["Overall status"].value_counts()  # Count test statuses
        overall_fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Overall Test Status Distribution",
            color=status_counts.index,
            color_discrete_map=COLOR_SCHEME,  # Map colors to statuses
            hole=0.4,  # Doughnut chart style
        )
        # Add text and hover information to the pie chart
        overall_fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>Status:</b> %{label}<br><b>Count:</b> %{value}<br><b>Percentage:</b> %{percent}<extra></extra>",
        )
        style_chart(overall_fig, "Overall Test Status Distribution")  # Apply styling

        # Prepare data for display in a tabular format for stations
        stations_data = [
            [station, count, round((count / valid_tests * 100), 2)]
            for station, count in station_failures.head(10).items()
        ]

        # Prepare data for display in a tabular format for models
        models_data = [
            [model, count, round((count / valid_tests * 100), 2)]
            for model, count in model_failures.head(10).items()
        ]

        # Prepare data for display in a tabular format for test cases
        test_cases_data = [
            [test, count, round((count / failed_tests * 100), 2)]
            for test, count in test_case_failures.head(10).items()
        ]

        # Create a comprehensive summary of the analysis
        summary = [
            f"Analysis Time: {analysis_time}",  # Timestamp of the analysis
            f"Data Range: {date_range}",  # Date range of the data
            f"Total Tests: {total_tests:,}",  # Total number of tests
            f"Valid Tests: {valid_tests:,}",  # Total number of valid tests
            f"Success: {success_tests:,}",  # Number of successful tests
            f"Failures: {failed_tests:,}",  # Number of failed tests
            f"Errors: {error_tests:,}",  # Number of error tests
            f"Pass Rate: {pass_rate:.2f}%",  # Pass rate percentage
        ]

        # Return the analysis results
        return (
            "\n".join(summary),  # Join the summary list into a single string
            overall_fig,  # Overall test status distribution chart
            stations_fig,  # Top failing stations chart
            models_fig,  # Top failing models chart
            test_cases_fig,  # Top failing test cases chart
            stations_data,  # Data for stations in tabular format
            models_data,  # Data for models in tabular format
            test_cases_data,  # Data for test cases in tabular format
        )

    except Exception as e:
        # Print error message and stack trace if an exception occurs
        print(f"Error in perform_analysis: {str(e)}")
        import traceback

        traceback.print_exc()
        return (
            f"An error occurred during analysis: {str(e)}",  # Error message
            None,  # Return None for figures in case of error
            None,
            None,
            None,
            [],  # Return empty lists for data in case of error
            [],
            [],
        )


def update_station_id_choices(operator, df):
    """
    Updates the Station ID dropdown choices based on the selected Operator.

    If an Operator is selected, filter the DataFrame to get the unique Station IDs
    associated with that Operator. Otherwise, get all unique Station IDs from the
    DataFrame. Sort the list of Station IDs and update the dropdown choices.
    """
    # If an Operator is selected, get the unique Station IDs associated with that Operator
    if operator and operator != "All":
        station_ids = df[df["Operator"] == operator]["Station ID"].unique().tolist()
    # Otherwise, get all unique Station IDs from the DataFrame
    else:
        station_ids = df["Station ID"].unique().tolist()
    # Sort the list of Station IDs
    station_ids.sort()
    # Update the dropdown choices
    return gr.update(choices=["All"] + station_ids, value="All")


def update_filter_visibility(filter_type):
    """
    Updates the visibility of filter dropdowns based on the selected filter type.

    Args:
        filter_type (str): The type of filter to apply, which determines which dropdowns are visible.

    Returns:
        dict: A dictionary mapping each filter to a Gradio update object, specifying its visibility.
    """
    # Check if no filter is selected, hide all dropdowns
    if filter_type == "No Filter":
        return {
            # Hide the operator filter dropdown
            operator_filter: gr.update(visible=False),
            # Hide the source filter dropdown
            source_filter: gr.update(visible=False),
            # Hide the station ID filter dropdown
            station_id_filter: gr.update(visible=False),
        }
    # Check if filtering by operator, show only relevant dropdowns
    elif filter_type == "Filter by Operator":
        return {
            # Show the operator filter dropdown
            operator_filter: gr.update(visible=True),
            # Hide the source filter dropdown
            source_filter: gr.update(visible=False),
            # Show the station ID filter dropdown
            station_id_filter: gr.update(visible=True),
        }
    else:  # Assume filtering by source if not by operator
        return {
            # Hide the operator filter dropdown
            operator_filter: gr.update(visible=False),
            # Show the source filter dropdown
            source_filter: gr.update(visible=True),
            # Show the station ID filter dropdown
            station_id_filter: gr.update(visible=True),
        }


def filter_data(df, filter_type, operator, source, station_id):
    """
    Filter a given DataFrame by Operator and/or Station ID with horizontal layout.
    """
    filtered_df = df.copy()

    # Apply filters based on selection
    if filter_type == "Filter by Operator" and operator != "All":
        filtered_df = filtered_df[filtered_df["Operator"] == operator]
    elif filter_type == "Filter by Source" and source != "All":
        filtered_df = filtered_df[filtered_df["Source"] == source]

    # Apply Station ID filter if selected
    if station_id != "All":
        filtered_df = filtered_df[filtered_df["Station ID"] == station_id]

    total_devices = filtered_df["IMEI"].nunique()
    total_tests = len(filtered_df)
    failures = filtered_df[filtered_df["Overall status"] == "FAILURE"]
    successes = filtered_df[filtered_df["Overall status"] == "SUCCESS"]

    # Use flexbox for layout and keep markdown intact
    summary = """<div style='display: flex; flex-wrap: wrap; gap: 20px; justify-content: space-between;'>

<div style='flex: 1; min-width: 300px;'>

## Overall Statistics

| Metric              | Value                |
|:--------------------|:--------------------|
| Total Unique Devices | {devices:<18} |
| Total Tests         | {tests:<18} |

## Filter Settings

| Filter    | Value                |
|:----------|:--------------------|
| Operator  | {operator:<18} |
| Station ID| {station_id:<18} |

## Test Results

| Result    | Count    | Percentage         |
|:----------|:---------|:------------------|
| Successes | {successes:<8} | {success_rate:>6.2f}% |
| Failures  | {failures:<8} | {failure_rate:>6.2f}% |

</div>

<div style='flex: 1; min-width: 300px;'>

## Top 5 Failing Models

| Model              | Failure Count       |
|:-------------------|:-------------------|
{model_rows}

## Top 5 Failing Test Cases

| Test Case                    | Failure Count       |
|:----------------------------|:-------------------|
{test_rows}

</div>

<div style='flex: 1; min-width: 300px;'>

## Active Station IDs

| Station ID         | Machine            |
|:------------------|:------------------|
{station_rows}

</div>

</div>""".format(
        devices=total_devices,
        tests=total_tests,
        operator=operator if operator != "All" else "All",
        station_id=station_id if station_id != "All" else "All",
        successes=len(successes),
        failures=len(failures),
        success_rate=len(successes) / total_tests * 100 if total_tests else 0,
        failure_rate=len(failures) / total_tests * 100 if total_tests else 0,
        model_rows="\n".join(
            f"| {model:<17} | {count:<17} |"
            for model, count in filtered_df[filtered_df["Overall status"] == "FAILURE"][
                "Model"
            ]
            .value_counts()
            .head()
            .items()
        ),
        test_rows="\n".join(
            f"| {test:<26} | {count:<17} |"
            for test, count in filtered_df[filtered_df["Overall status"] == "FAILURE"][
                "result_FAIL"
            ]
            .value_counts()
            .head()
            .items()
        ),
        station_rows="\n".join(
            f"| {station:<16} | {resolve_station(station):<17} |"
            for station in sorted(filtered_df["Station ID"].unique())
        ),
    )

    # Rest of the function remains the same...
    top_errors = analyze_top_errors_by_model(filtered_df)
    overall_status = analyze_overall_status(filtered_df)
    top_models = filtered_df["Model"].value_counts().head()
    top_test_cases = filtered_df["result_FAIL"].value_counts().head()

    title_suffix = (
        f"for Operator {operator}"
        if operator != "All"
        else f"for Station {station_id}"
        if station_id != "All"
        else "(All Data)"
    )

    models_chart = create_summary_chart(
        top_models, f"Top 5 Failing Models {title_suffix}"
    )
    test_cases_chart = create_summary_chart(
        top_test_cases, f"Top 5 Failing Test Cases {title_suffix}"
    )
    status_chart = create_overall_status_chart(
        overall_status, f"Overall Status {title_suffix}"
    )

    models_df = format_dataframe(top_models)
    test_cases_df = format_dataframe(top_test_cases)
    errors_df = top_errors[["Model", "error", "count"]]

    return (
        summary,
        models_chart,
        test_cases_chart,
        status_chart,
        models_df,
        test_cases_df,
        errors_df,
    )


def repeated_failures_wrapper(file, min_failures):
    """
    Wraps the repeated failures analysis by loading data from a file.
    """
    df = load_data(file)
    summary, chart, data = analyze_repeated_failures(df, min_failures)
    return summary, chart, data


def analyze_repeated_failures(df, min_failures=4):
    try:
        # If df is a file object, load it first
        if hasattr(df, "name"):
            df = pd.read_csv(df.name)

        # Filter for FAILURE in Overall status
        failure_df = df[df["Overall status"] == "FAILURE"]
        print(f"Found {len(failure_df)} failures")  # Debug print
        print("Columns in failure_df:", failure_df.columns.tolist())  # Debug print
        print("Data types:", failure_df.dtypes)  # Debug print

        # Create initial aggregation with both counts
        agg_df = (
            failure_df.groupby(["Model", "Station ID", "result_FAIL"])
            .agg({"IMEI": ["count", "nunique"]})
            .reset_index()
        )

        # Rename columns
        agg_df.columns = [
            "Model",
            "Station ID",
            "result_FAIL",
            "TC Count",
            "IMEI Count",
        ]
        print("After aggregation - Columns:", agg_df.columns.tolist())  # Debug print
        print("After aggregation - Data types:", agg_df.dtypes)  # Debug print

        # Filter for minimum test case failures threshold
        repeated_failures = agg_df[agg_df["TC Count"] >= min_failures].copy()
        print(
            f"Found {len(repeated_failures)} instances of repeated failures"
        )  # Debug print
        print("After filtering - Data types:", repeated_failures.dtypes)  # Debug print

        # Add Model Code column
        repeated_failures["Model Code"] = repeated_failures["Model"].apply(
            get_model_code
        )
        print(
            "After adding Model Code - Data types:", repeated_failures.dtypes
        )  # Debug print

        # Sort by TC Count in descending order
        repeated_failures = repeated_failures.sort_values("TC Count", ascending=False)
        print("First few rows of repeated_failures:")  # Debug print
        print(repeated_failures.head())  # Debug print

        # Create summary and plot
        summary = f"Found {len(repeated_failures)} instances of repeated failures:\n\n"
        summary += """<div class="table-container">
| Model | Code | Station ID | Test Case | TC Count | IMEI Count |
|:------|:-----|:-----------|:----------|--------:|----------:|
"""
        print("Starting row iteration for summary")  # Debug print
        for index, row in repeated_failures.iterrows():
            try:
                summary_row = f"| {row['Model']} | {row['Model Code']} | {row['Station ID']} | {row['result_FAIL']} | {row['TC Count']} | {row['IMEI Count']} |\n"
                summary += summary_row
                print(f"Successfully added row {index}")  # Debug print
            except Exception as row_error:
                print(f"Error on row {index}:", row_error)  # Debug print
                print("Row contents:", row)  # Debug print
                raise row_error

        summary += "</div>"

        # Create bar chart
        fig = px.bar(
            repeated_failures,
            x="Station ID",
            y="TC Count",
            color="Model",
            hover_data=["result_FAIL", "IMEI Count"],
            title=f"Repeated Failures (≥{min_failures} times)",
            labels={"TC Count": "Number of Test Case Failures"},
            height=600,
        )

        fig.update_layout(
            xaxis_title="Station ID",
            yaxis_title="Number of Test Case Failures",
            xaxis_tickangle=-45,
            legend_title="Model",
            barmode="group",
        )

        # Create interactive dataframe with explicit column names
        interactive_df = gr.Dataframe(
            value=repeated_failures,
            headers=repeated_failures.columns.tolist(),
            interactive=True,
            type="pandas",  # Specify the type as pandas
            # height=500,
            show_label=True,
            label="Repeated Failures Analysis",
            column_widths=None,
            wrap=True,  # Enable column reorderin
        )

        # Get test cases for dropdown
        test_case_counts = repeated_failures.groupby("result_FAIL")["TC Count"].max()
        sorted_test_cases = test_case_counts.sort_values(ascending=False).index.tolist()

        print("Creating dropdown choices")  # Debug print
        dropdown_choices = ["Select All", "Clear All"] + [
            f"{test_case} ({test_case_counts[test_case]}) max failures"
            for test_case in sorted_test_cases
        ]

        print("Successfully completed analysis")  # Debug print
        return (
            summary,
            fig,
            interactive_df,
            gr.Dropdown(
                choices=dropdown_choices,
                value=dropdown_choices[2:],
                label="Filter by Test Case",
                multiselect=True,
            ),
        )

    except Exception as e:
        print(f"Error in analyze_repeated_failures: {str(e)}")  # Debug print
        print("Exception type:", type(e))  # Debug print
        import traceback

        print("Traceback:", traceback.format_exc())  # Debug print
        error_message = f"""<div class="table-container">
## Error Occurred
| Error Details |
|:--------------|
| {str(e)} |
Please check your input and try again.
</div>"""
        return error_message, None, None, None


def update_summary_chart_and_data(repeated_failures_df, sort_by, selected_test_cases):
    """
    Updates the summary chart, interactive dataframe, and test case filter options based on sorting and filtering preferences.

    Parameters:
        repeated_failures_df (pandas.DataFrame): Input dataframe with repeated failures data
        sort_by (str): Column name to sort by; one of "TC Count", "Model", "Station ID", "Test Case", or "Model Code"
        selected_test_cases (list): List of selected test cases to filter by

    Returns:
        tuple: (summary text, plotly figure, interactive dataframe)
    """

    # Check for no data
    if repeated_failures_df is None or len(repeated_failures_df) == 0:
        return "No data available to sort/filter", None, None

    # Make a copy of the dataframe so we don't modify the original
    df = repeated_failures_df.copy()

    # Handle test case filtering
    if selected_test_cases:
        # If the user chose "Select All", do nothing
        if "Select All" in selected_test_cases:
            pass
        # If the user chose "Clear All", filter out all test cases
        elif "Clear All" in selected_test_cases:
            df = df[df["result_FAIL"] == ""]
        # If the user chose specific test cases, filter for those
        else:
            # Convert the selected test cases to the actual test case names without counts
            selected_actual_cases = [
                test_case.split(" (")[0] for test_case in selected_test_cases
            ]
            # Filter the dataframe for the selected test cases
            df = df[df["result_FAIL"].isin(selected_actual_cases)]

    # Sort the dataframe by the selected column
    sort_column_map = {
        "TC Count": "TC Count",
        "Model": "Model",
        "Station ID": "Station ID",
        "Test Case": "result_FAIL",
        "Model Code": "Model Code",
    }

    df = df.sort_values(sort_column_map[sort_by], ascending=False)

    # Create an updated interactive dataframe with explicit column names
    interactive_df = gr.Dataframe(
        value=df,
        headers=df.columns.tolist(),
        interactive=True,
        wrap=True,
        # height=500,
        show_label=True,
        column_widths=None,
        label="Filtered Repeated Failures",
    )

    # Return the updated summary text, plotly figure, and interactive dataframe
    return create_summary(df), create_plot(df), interactive_df


def create_summary(df):
    """Create markdown summary of the dataframe"""
    summary = f"Found {len(df)} instances of repeated failures:\n\n"
    summary += """| Model | Model Code | Station ID | Test Case | TC Count | IMEI Count |
|:------|:-----------|:-----------|:----------|--------:|----------:|
"""
    # Note the right alignment (--------:) for numeric columns
    for _, row in df.iterrows():
        summary += f"| {row['Model']} | {row['Model Code']} | {row['Station ID']} | {row['result_FAIL']} | {row['TC Count']} | {row['IMEI Count']} |\n"

    return summary


def create_plot(df):
    """Create bar chart visualization of the data"""
    fig = px.bar(
        df,
        x="Station ID",
        y="TC Count",
        color="Model",
        hover_data=["result_FAIL", "IMEI Count"],
        title=f"Filtered Repeated Failures",
        labels={"TC Count": "Number of Test Case Failures"},
        height=600,
    )

    fig.update_layout(
        xaxis_title="Station ID",
        yaxis_title="Number of Test Case Failures",
        xaxis_tickangle=-45,
        legend_title="Model",
        barmode="group",
    )

    return fig


def get_model_code(model):
    """Helper function to get model code from device map"""
    code = device_map.get(model, "Unknown")
    if isinstance(code, list):
        return code[0]  # Take first code if multiple exist
    return code


def update_summary(repeated_failures_df, sort_by, selected_test_cases):
    """
    Updates the summary text based on sorting and filtering preferences
    """
    try:
        if repeated_failures_df is None or len(repeated_failures_df) == 0:
            return "No data available to sort/filter"

        df = repeated_failures_df.copy()

        # Handle Select All/Clear All and apply test case filter
        if selected_test_cases:
            if "Select All" in selected_test_cases:
                # Include all test cases
                pass
            elif "Clear All" in selected_test_cases:
                # Clear all selections
                df = df[df["result_FAIL"] == ""]  # This will create an empty result
            else:
                # Filter for selected test cases
                selected_actual_cases = [
                    test_case.split(" (")[0] for test_case in selected_test_cases
                ]
                df = df[df["result_FAIL"].isin(selected_actual_cases)]

        # Apply sorting
        sort_column_map = {
            "TC Count": "TC Count",
            "Model": "Model",
            "Station ID": "Station ID",
            "Test Case": "result_FAIL",
            "Model Code": "Model Code",  # Add this line to support sorting by Model Code
        }
        df = df.sort_values(sort_column_map[sort_by], ascending=False)

        # Create summary with proper markdown table formatting
        summary = f"Found {len(df)} instances of repeated failures:\n\n"
        summary += "| Model              | Model Code       | Station ID    | Test Case                    | Count |\n"
        summary += "|:-------------------|:----------------|:--------------|:----------------------------|-------:|\n"

        for _, row in df.iterrows():
            summary += f"| {row['Model']:<17} | {row['Model Code']:<14} | {row['Station ID']:<12} | {row['result_FAIL']:<26} | {row['TC Count']:>5} |\n"

        return summary
    except Exception as e:
        return f"Error updating summary: {str(e)}"


def handle_test_case_selection(evt: gr.SelectData, selected_test_cases):
    """
    Handles the Select All/Clear All functionality
    """
    if evt.value == "Select All":
        # Return all choices except "Select All" and "Clear All"
        return test_case_filter.choices[2:]
    elif evt.value == "Clear All":
        return []
    return selected_test_cases


def analyze_wifi_errors(file, error_threshold=9):
    """
    Analyzes WiFi errors in a given data file and returns a summary of the errors.
    Includes hourly breakdown and separate trend lines for each error type.
    """
    # Enable copy on write mode
    pd.options.mode.copy_on_write = True

    # Load and prepare data
    try:
        # Load the data
        df = pd.read_csv(file.name)

        # Convert timestamp string to datetime
        df = df.assign(
            DateTime=pd.to_datetime(
                df["Date"] + " " + df["Hour"], format="%m/%d/%Y %H:%M:%S"
            ),
        )

        # Extract date and hour components
        df = df.assign(
            DateOnly=lambda x: x["DateTime"].dt.date,
            HourOfDay=lambda x: x["DateTime"].dt.hour,
        )

        # Get timeline bounds
        start_time = df["DateTime"].min()
        end_time = df["DateTime"].max()
        date_range = pd.date_range(start=start_time, end=end_time, freq="h")

    except pd.errors.ParserError as e:
        print(f"Error parsing dates: {e}")
        return None, None, None, None

    # Define constants
    operators = [
        "STN251_RED(id:10089)",
        "STN252_RED(id:10090)",
        "STN351_GRN(id:10380)",
        "STN352_GRN(id:10381)",
    ]
    wifi_errors = [
        "Device closed the socket",
        "DUT connection error",
        "DUT lost WIFI connection",
    ]

    # Filter data and calculate overall statistics
    df_filtered = df[df["Operator"].isin(operators)].copy()

    # Calculate error statistics
    total_transactions = (
        df_filtered["Operator"].value_counts().reindex(operators, fill_value=0)
    )
    wifi_error_breakdown = (
        df_filtered[df_filtered["error_message"].isin(wifi_errors)]
        .groupby(["Operator", "error_message"])
        .size()
        .unstack(fill_value=0)
    )

    # Prepare summary results
    wifi_error_breakdown = wifi_error_breakdown.reindex(
        index=operators, columns=wifi_errors, fill_value=0
    )
    wifi_error_breakdown.loc["Total"] = wifi_error_breakdown.sum()
    wifi_error_counts = wifi_error_breakdown.sum(axis=1)

    total_transactions_with_total = pd.concat(
        [total_transactions, pd.Series({"Total": total_transactions.sum()})]
    )
    wifi_error_percentages = (
        wifi_error_counts / total_transactions_with_total * 100
    ).round(2)

    # Create summary results DataFrame
    results = pd.DataFrame(
        {
            "Operator": operators + ["Grand Total"],
            "Total Transactions": total_transactions_with_total.values,
            "WiFi Errors": wifi_error_counts.values,
            "Error Percentage": wifi_error_percentages.values,
        }
    )

    # Style the results
    def highlight_high_errors(s):
        is_high = s["Error Percentage"] > error_threshold
        return ["background-color: red; color: black" if is_high else "" for _ in s]

    styled_results = results.style.apply(highlight_high_errors, axis=1)

    # Identify high error operators
    high_error_operators = results[results["Error Percentage"] > error_threshold][
        "Operator"
    ].tolist()

    if not high_error_operators:
        return styled_results, None, None, None

    # Process data for high error operators
    df_high_errors = df[
        (df["Operator"].isin(high_error_operators))
        & (df["error_message"].isin(wifi_errors))
    ].copy()

    # Create hourly pivot table
    pivot = pd.pivot_table(
        df_high_errors,
        values="IMEI",
        index=["DateOnly", "HourOfDay"],
        columns=["Operator", "error_message"],
        aggfunc="count",
        fill_value=0,
    )

    # Ensure all hours are represented
    dates = sorted(df_high_errors["DateOnly"].unique())
    hours = range(24)
    all_hours = pd.MultiIndex.from_product(
        [dates, hours], names=["DateOnly", "HourOfDay"]
    )
    pivot = pivot.reindex(all_hours, fill_value=0)

    # Helper function for column naming
    def condense_column_name(operator, error):
        color = "Red" if "RED" in operator else "Green"
        primary_or_secondary = "2nd" if operator.split("_")[0][-1] == "2" else "Primary"
        if "DUT connection error" in error:
            error_short = "Connect Error"
        elif "DUT lost WIFI connection" in error:
            error_short = "Lost Wifi"
        else:
            error_short = "Closed socket"
        return f"{color} {primary_or_secondary} - {error_short}"

    # Prepare pivot table for display
    new_columns = [condense_column_name(op, err) for op, err in pivot.columns]
    pivot.columns = new_columns
    display_pivot = pivot.reset_index()
    display_pivot["DateOnly"] = display_pivot["DateOnly"].astype(str)
    display_pivot["Time"] = display_pivot["HourOfDay"].apply(lambda x: f"{x:02d}:00")

    # Style pivot table
    error_cols = [
        col
        for col in display_pivot.columns
        if any(err in col for err in ["Connect Error", "Lost Wifi", "Closed socket"])
    ]
    highlight_threshold = display_pivot[error_cols].mean().mean() * (
        1 + error_threshold / 100
    )

    def style_above_threshold(val):
        if isinstance(val, pd.Series) and val.name in error_cols:
            return [
                (
                    "background-color: yellow; color: black"
                    if v > highlight_threshold
                    else ""
                )
                for v in val
            ]
        return [""] * len(val)

    styled_pivot = display_pivot.style.apply(style_above_threshold)

    # Create heatmap
    heatmap_data = pivot.reset_index().melt(
        id_vars=["DateOnly", "HourOfDay"],
        var_name="Error Type",
        value_name="Error Count",
    )
    heatmap_data["DateTime"] = pd.to_datetime(
        heatmap_data["DateOnly"].astype(str)
        + " "
        + heatmap_data["HourOfDay"].astype(str)
        + ":00:00"
    )

    fig = px.density_heatmap(
        heatmap_data,
        x="Error Type",
        y="DateTime",
        z="Error Count",
        title=f'WiFi Error Heatmap ({start_time.strftime("%m/%d")} - {end_time.strftime("%m/%d")})',
        labels={"Error Count": "Number of Errors", "DateTime": "Time"},
        color_continuous_scale="RdBu_r",
    )

    # Create trend lines using pivot table data directly
    error_trends = pd.DataFrame()
    error_trends["DateTime"] = pd.to_datetime(
        display_pivot["DateOnly"] + " " + display_pivot["Time"]
    )

    # Add error counts from pivot table
    for col in error_cols:  # error_cols already contains our error column names
        error_trends[col] = display_pivot[col]

    # Create trend line plot with the pivot data
    hourly_summary_fig = px.line(
        error_trends,
        x="DateTime",
        y=error_cols,  # Use error columns directly
        title=f'WiFi Errors by Type ({start_time.strftime("%m/%d")} - {end_time.strftime("%m/%d")})',
        labels={
            "DateTime": "Time",
            "value": "Number of Errors",
            "variable": "Error Type",
        },
    )

    # Set custom colors for error types
    color_map = {
        "Connect Error": "rgb(239, 85, 59)",  # Red
        "Lost Wifi": "rgb(99, 110, 250)",  # Blue
        "Closed socket": "rgb(0, 204, 150)",  # Green
    }

    # Apply colors to lines
    for trace in hourly_summary_fig.data:
        for error_type, color in color_map.items():
            if error_type in trace.name:
                trace.line.color = color

    # Apply consistent styling to both plots
    for plot in [fig, hourly_summary_fig]:
        plot.update_layout(
            plot_bgcolor="rgba(255, 255, 255, 0.05)",
            paper_bgcolor="rgba(255, 255, 255, 0.05)",
            font=dict(color="rgba(255, 255, 255, 0.9)"),
            title_font=dict(size=16, color="rgb(107, 99, 246)"),
            xaxis=dict(
                title_font=dict(color="rgb(107, 99, 246)"),
                tickfont=dict(color="rgba(255, 255, 255, 0.9)"),
                gridcolor="rgba(107, 99, 246, 0.1)",
                showgrid=True,
                tickformat="%m/%d %H:%M",
            ),
            yaxis=dict(
                title="Number of Errors",
                title_font=dict(color="rgb(107, 99, 246)"),
                tickfont=dict(color="rgba(255, 255, 255, 0.9)"),
                gridcolor="rgba(107, 99, 246, 0.1)",
                showgrid=True,
            ),
            legend=dict(
                title_font=dict(color="rgb(107, 99, 246)"),
                font=dict(color="rgba(255, 255, 255, 0.9)"),
                bgcolor="rgba(255, 255, 255, 0.05)",
            ),
            margin=dict(t=50, l=50, r=50, b=50),
        )

    # Set specific heights for each plot
    fig.update_layout(height=800)
    hourly_summary_fig.update_layout(height=600)

    return styled_results, fig, styled_pivot, hourly_summary_fig


def get_unique_values(df, column):
    """
    Returns a sorted list of unique values in a given column of a pandas DataFrame.
    """
    unique_values = df[column].unique()
    # Convert to strings and remove None/NaN values
    unique_values = [
        str(val) for val in unique_values if val is not None and not pd.isna(val)
    ]
    return sorted(unique_values)


def apply_filter_and_sort(
    df,
    sort_columns,
    operator,
    model,
    manufacturer,
    source,
    overall_status,
    station_id,
    result_fail,
):
    """
    Applies filters and sorting to a pandas DataFrame.

    Args:
        df (pd.DataFrame): The original DataFrame to be filtered and sorted.
        sort_columns (list): A list of column names to sort the DataFrame by.
        operator (str): The operator to filter by.
        model (str): The model to filter by.
        manufacturer (str): The manufacturer to filter by.
        source (str): The source to filter by.
        overall_status (str): The overall status to filter by.
        station_id (str): The station id to filter by.
        result_fail (str): The result fail to filter by.

    Returns:
        pd.DataFrame: The filtered and sorted DataFrame.
        str: A summary of the applied filters and sorting.
    """
    try:
        # Start with a copy of the original DataFrame to avoid modifying the original data.
        filtered_df = df.copy()

        # Define the columns to filter and their corresponding values.
        filter_columns = [
            "Operator",
            "Model",
            "Manufacturer",
            "Source",
            "Overall status",
            "Station ID",
            "result_FAIL",
        ]
        filter_values = [
            operator,
            model,
            manufacturer,
            source,
            overall_status,
            station_id,
            result_fail,
        ]

        # Iterate over filter columns and their corresponding values.
        for column, value in zip(filter_columns, filter_values):
            # Check if the value is not None, not "All", and not ["All"].
            if value and value != "All" and value != ["All"]:
                # Check if the value is a list, indicating multiselect filters.
                if isinstance(value, list):
                    # Filter the DataFrame to include only rows where the column value is in the list.
                    filtered_df = filtered_df[filtered_df[column].isin(value)]
                else:
                    # Filter the DataFrame to include only rows where the column value matches exactly.
                    filtered_df = filtered_df[filtered_df[column].astype(str) == value]

        # Check if there are columns to sort by.
        if sort_columns:
            # Sort the DataFrame by the specified columns.
            filtered_df = filtered_df.sort_values(by=sort_columns)

        # Prepare a summary of the number of rows after filtering.
        summary = f"Filtered data: {len(filtered_df)} rows\n"
        applied_filters = []

        # Create a list of applied filters for the summary.
        for k, v in zip(filter_columns, filter_values):
            if v and v != "All" and v != ["All"]:
                if isinstance(v, list):
                    # Append the filter to the summary if it's a list.
                    applied_filters.append(f"{k}={', '.join(v)}")
                else:
                    # Append the filter to the summary if it's a single value.
                    applied_filters.append(f"{k}={v}")

        # Add the applied filters and sorting information to the summary.
        summary += f"Applied filters: {', '.join(applied_filters) if applied_filters else 'None'}\n"
        summary += f"Sorted by: {', '.join(sort_columns) if sort_columns else 'None'}"

        # Return the filtered and sorted DataFrame along with the summary.
        return filtered_df, summary

    except Exception as e:
        # Handle exceptions and return an error message.
        error_message = f"Error applying filters: {str(e)}"
        print(error_message)  # Print the error message for debugging purposes.
        return pd.DataFrame(), error_message


def update_filter_dropdowns(df):
    """
    Generate a list of dropdown widgets for each filter column in the provided DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to generate dropdown widgets for.

    Returns:
        list: A list of gr.Dropdown widgets for each filter column in the DataFrame.
    """
    # The list comprehension loops over the filter columns and creates a gr.Dropdown
    # widget for each one. The widget is initialized with the unique values from
    # the column, plus the string "All" as the first element of the list. The value
    # parameter is set to "All" so that the widget defaults to showing all values.
    return [
        gr.Dropdown(
            # The choices parameter takes a list of strings, which are the options
            # to display in the dropdown. The list comprehension adds "All" as the
            # first element of the list, and then appends the unique values from
            # the column. The unique values are obtained by calling the
            # get_unique_values function, which takes the DataFrame and the column
            # name as arguments.
            choices=["All"] + get_unique_values(df, col),
            # The value parameter sets the initial value of the dropdown to "All",
            # which will show all values in the column when the widget is created.
            value="All",
            # The label parameter sets the label that is displayed above the
            # dropdown.
            label=col,
        )
        # The list comprehension loops over the filter columns, which are the
        # columns that are used to filter the data. The filter columns are
        # hardcoded as a list of strings.
        for col in [
            "Operator",
            "Model",
            "Manufacturer",
            "Source",
            "Overall status",
            "Station ID",
            "result_FAIL",
        ]
    ]


def resolve_station(station_id):
    """
    Resolve a station id to a machine name.
    """
    return station_to_machine.get(station_id.lower(), "Unknown Machine")


def get_test_from_result_fail(result_fail):
    """
    Resolve a result_fail to a test name.
    """
    for test, descriptions in test_to_result_fail_map.items():
        if result_fail in descriptions:
            return test
    return "Unknown Test"


def apply_filters(df, operator, station_id, model):
    """
    Apply filters to the DataFrame before creating pivot table.
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

    return filtered_df


def generate_pivot_table_filtered(
    df, rows, columns, values, aggfunc, operator, station_id, model
):
    """
    Generate a filtered pivot table based on user selections.
    """
    try:
        # First apply filters
        filtered_df = apply_filters(df, operator, station_id, model)

        # Then create pivot table
        result = create_pivot_table(filtered_df, rows, columns, values, aggfunc)

        return result

    except Exception as e:
        print(f"Error generating filtered pivot table: {str(e)}")
        return pd.DataFrame({"Error": [str(e)]})


def process_data(df, source, station_id, models, result_fail, flexible_search):
    """
    Process a given DataFrame to produce db-export commands and formatted markdown summary.
    """
    try:
        # Create a copy of the original DataFrame to avoid modifying it directly
        df_filtered = df.copy()

        # Apply filtering based on the source column if a specific source is selected
        if source != "All":
            df_filtered = df_filtered[df_filtered["Source"] == source]

        # Apply filtering based on the station ID if a specific station is selected
        if station_id != "All":
            df_filtered = df_filtered[df_filtered["Station ID"] == station_id]

        # Apply filtering based on the selected models if not set to "All"
        if models and "All" not in models:
            df_filtered = df_filtered[df_filtered["Model"].isin(models)]

        # Apply filtering based on result_fail with option for flexible search
        if result_fail != "All":
            if flexible_search:
                # Use case-insensitive substring match for flexible search
                df_filtered = df_filtered[
                    df_filtered["result_FAIL"].apply(
                        lambda x: result_fail.lower() in str(x).lower()
                    )
                ]
            else:
                # Exact match filtering
                df_filtered = df_filtered[df_filtered["result_FAIL"] == result_fail]

        # Limit the DataFrame to the first 1000 rows for processing
        df_filtered = df_filtered.head(1000)

        # Extract unique IMEIs, converting to integers and filtering out NaN values
        unique_imeis = df_filtered["IMEI"].unique()
        imeis_as_int = [
            str(int(float(imei))) for imei in unique_imeis if pd.notna(imei)
        ]

        # Construct a command to export message data for the filtered IMEIs
        messages_command = (
            "db-export messages --dut " + " --dut ".join(imeis_as_int)
            if imeis_as_int
            else "No IMEIs found"
        )

        # Determine the test name from the result_fail mapping
        test_name = get_test_from_result_fail(result_fail)

        # Construct a command to export raw data for the specified test and IMEIs
        raw_data_command = (
            f'db-export raw_data --test "{test_name}" --dut '
            + " --dut ".join(imeis_as_int)
            if imeis_as_int
            else "No IMEIs found"
        )

        # Construct a command to export gauge data for the specified test and IMEIs
        gauge_command = (
            f'db-export gauge --test "{test_name}" --dut '
            + " --dut ".join(imeis_as_int)
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
{chr(10).join(f"| {model} | {device_map.get(model, 'Unknown') if not isinstance(device_map.get(model, 'Unknown'), list) else ', '.join(device_map.get(model, ['Unknown']))} | {count} |" for model, count in model_counts.items())}

</div>

<div class="summary-section">

## Remote Access Information

| Machine | Station ID |
|:--------|:-----------|
{chr(10).join(f"| {resolve_station(station)} | {station} |" for station in sorted(df_filtered['Station ID'].unique()))}

</div>
"""
        # Return the commands and the generated summary
        return messages_command, raw_data_command, gauge_command, summary

    except Exception as e:
        # Handle exceptions by returning an error message in markdown format
        error_message = f"""
## Error Occurred

| Error Details |
|:--------------|
| {str(e)} |

Please check your input and try again.
"""
        return error_message, error_message, error_message, error_message


def load_and_update(file):
    """
    Loads a CSV file into a Pandas DataFrame, and creates dropdowns for
    selecting various fields from the loaded DataFrame.
    """
    dataframe = load_data(file)

    def safe_sort(lst):
        """Custom sorting function to handle mixed types"""

        def key_func(item):
            if pd.isna(item):
                return (1, "")
            elif isinstance(item, str):
                return (0, str(item).lower())  # Convert to string before lower()
            else:
                return (0, str(item))

        return sorted(
            [x for x in lst if pd.notna(x)], key=key_func
        )  # Filter out NaN values

    # Create lists of unique values for each column
    operators = ["All"] + safe_sort(dataframe["Operator"].unique())
    station_ids = ["All"] + safe_sort(dataframe["Station ID"].unique())
    models = ["All"] + safe_sort(dataframe["Model"].unique())
    manufacturers = ["All"] + safe_sort(dataframe["Manufacturer"].unique())
    sources = ["All"] + safe_sort(dataframe["Source"].unique())
    overall_statuses = ["All"] + safe_sort(dataframe["Overall status"].unique())
    result_fails = ["All"] + safe_sort(dataframe["result_FAIL"].unique())

    # Get columns of the DataFrame for Pivot Table Builder
    columns = dataframe.columns.tolist()

    return (
        dataframe,
        gr.update(choices=sources, value="All"),  # source (IMEI Extractor)
        gr.update(choices=station_ids, value="All"),  # station_id (IMEI Extractor)
        gr.update(choices=models, value="All"),  # model_input
        gr.update(choices=result_fails, value="All"),  # result_fail
        gr.update(choices=operators, value="All"),  # advanced_operator_filter
        gr.update(choices=models, value="All"),  # advanced_model_filter
        gr.update(choices=manufacturers, value="All"),  # advanced_manufacturer_filter
        gr.update(choices=sources, value="All"),  # advanced_source_filter
        gr.update(
            choices=overall_statuses, value="All"
        ),  # advanced_overall_status_filter
        gr.update(choices=station_ids, value="All"),  # advanced_station_id_filter
        gr.update(choices=result_fails, value="All"),  # advanced_result_fail_filter
        gr.update(choices=columns, value=[]),  # pivot_rows
        gr.update(choices=columns, value=[]),  # pivot_columns
        gr.update(choices=columns, value=[]),  # pivot_values
        gr.update(choices=operators, value="All"),  # filter_operator (Pivot Table)
        gr.update(choices=station_ids, value="All"),  # filter_station_id (Pivot Table)
        gr.update(choices=models, value="All"),  # filter_model (Pivot Table)
        gr.update(choices=operators, value="All"),  # operator_filter (new)
        gr.update(choices=sources, value="All"),  # source_filter (new)
        gr.update(choices=station_ids, value="All"),  # station_id_filter (new)
    )


with gr.Blocks(
    theme=gr.themes.Soft(),
    css="""
    /* Base styles for markdown content */
    .markdown-body {
        padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        max-width: 1200px;  /* Limit maximum width */
        margin: 0 auto;     /* Center the container */
    }

    /* Header styling */
    .markdown-body h2 {
        margin-top: 0;
        color: rgb(107, 99, 246);
        font-size: 1.25rem;
        font-weight: 600;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(107, 99, 246, 0.2);
    }

    /* Table styling */
    .markdown-body table,
    .custom-markdown table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        background: rgba(255, 255, 255, 0.05);
    }

    /* Table column width controls */
    .markdown-body table th:nth-child(1) { width: 15%; }  /* Model column */
    .markdown-body table th:nth-child(2) { width: 15%; }  /* Model Code column */
    .markdown-body table th:nth-child(3) { width: 15%; }  /* Station ID column */
    .markdown-body table th:nth-child(4) { width: 40%; }  /* Test Case column */
    .markdown-body table th:nth-child(5) { width: 15%; }  /* Count column */

    .markdown-body th {
        background: rgba(107, 99, 246, 0.1);
        color: rgb(107, 99, 246);
        font-weight: 600;
        text-align: left;
    }

    .markdown-body td,
    .markdown-body th {
        padding: 0.5rem 0.75rem;
        border: 1px solid rgba(107, 99, 246, 0.2);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 0;
    }

    /* Allow test case column to wrap if needed */
    .markdown-body td:nth-child(4) {
        white-space: normal;
        line-height: 1.2;
    }

    .markdown-body tr:nth-child(even) {
        background: rgba(107, 99, 246, 0.03);
    }

    /* Table container for scrolling */
    .markdown-body .table-container {
        overflow-x: auto;
        margin: 1rem 0;
    }

    /* Command section styling */
    .command-section {
        margin-bottom: 1.5rem;
        padding: 1rem;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.05);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Code styling */
    .custom-textbox,
    .command-box {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        line-height: 1.5;
        white-space: pre-wrap;
        background: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(107, 99, 246, 0.2) !important;
        border-radius: 4px;
        padding: 1rem;
        margin-bottom: 0.75rem !important;
        color: rgba(255, 255, 255, 0.9) !important;
    }

    .markdown-body code {
        background: rgba(107, 99, 246, 0.1);
        padding: 0.2em 0.4em;
        border-radius: 3px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    /* Summary section styling */
    .summary-section {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Flexbox layout */
    .flex-container {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        justify-content: space-between;
    }

    .flex-item {
        flex: 1;
        min-width: 300px;
        background: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Markdown container */
    .custom-markdown {
        width: 100%;
        padding: 1rem;
    }

    /* Spacing utilities */
    .markdown-body > *:first-child { margin-top: 0; }
    .markdown-body > *:last-child { margin-bottom: 0; }

    /* Responsive adjustments */
    @media (max-width: 768px) {
        .markdown-body {
            padding: 0.5rem;
        }

        .markdown-body td,
        .markdown-body th {
            padding: 0.4rem 0.5rem;
            font-size: 0.9rem;
        }
    }
""",
) as demo:
    gr.Markdown("# CSV Analysis Tool")

    with gr.Row():
        file_input = gr.File(label="Upload CSV File")

    df = gr.State()  # State to hold the DataFrame

    with gr.Tabs():
        with gr.TabItem("Analysis Results"):
            with gr.Row():
                analyze_button = gr.Button("Perform Analysis")
            with gr.Row():
                analysis_summary = gr.Textbox(label="Summary", lines=6)
            with gr.Row():
                overall_status_chart = gr.Plot(label="Overall Status Distribution")
                stations_chart = gr.Plot(label="Top Failing Stations")
                models_chart = gr.Plot(label="Top Failing Models")
                test_cases_chart = gr.Plot(label="Top Failing Test Cases")
            with gr.Row():
                stations_df = gr.Dataframe(
                    headers=["Station ID", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Stations",
                    interactive=False,
                )
                models_df = gr.Dataframe(
                    headers=["Model", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Models",
                    interactive=False,
                )
                test_cases_df = gr.Dataframe(
                    headers=["Test Case", "Failure Count", "Failure Rate (%)"],
                    label="Top Failing Test Cases",
                    interactive=False,
                )

        with gr.TabItem("Custom Data Filtering"):
            with gr.Row():
                filter_type = gr.Radio(
                    choices=["No Filter", "Filter by Operator", "Filter by Source"],
                    value="No Filter",
                    label="Select Filter Type",
                    interactive=True,
                )

            with gr.Row():
                operator_filter = gr.Dropdown(
                    label="Operator",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )
                source_filter = gr.Dropdown(
                    label="Source",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )
                station_id_filter = gr.Dropdown(
                    label="Station ID",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    scale=1,
                    visible=False,  # Initially hidden
                )

            with gr.Row():
                custom_filter_button = gr.Button("Filter Data")

            # Rest of the components remain the same
            with gr.Row():
                custom_filter_summary = gr.Markdown(
                    label="Filtered Summary", value="", elem_classes=["custom-markdown"]
                )
            with gr.Row():
                with gr.Column(scale=1):
                    custom_filter_chart1 = gr.Plot(label="Top 5 Failing Models")
                with gr.Column(scale=1):
                    custom_filter_chart2 = gr.Plot(label="Top 5 Failing Test Cases")
                with gr.Column(scale=1):
                    custom_filter_chart3 = gr.Plot(label="Overall Status")
            with gr.Row():
                with gr.Column(scale=1):
                    custom_filter_df1 = gr.Dataframe(label="Top 5 Failing Models")
                with gr.Column(scale=1):
                    custom_filter_df2 = gr.Dataframe(label="Top 5 Failing Test Cases")
                with gr.Column(scale=1):
                    custom_filter_df3 = gr.Dataframe(label="Top 5 Errors")

        with gr.TabItem("Pivot Table Builder"):
            with gr.Row():
                # Adding filter dropdowns for filtering before creating the pivot table with multiselect enabled
                filter_operator = gr.Dropdown(
                    label="Filter by Operator",
                    choices=["All"],
                    value="All",
                    multiselect=True,
                    interactive=True,
                )
                filter_station_id = gr.Dropdown(
                    label="Filter by Station ID",
                    choices=["All"],
                    value="All",
                    multiselect=True,
                    interactive=True,
                )
                filter_model = gr.Dropdown(
                    label="Filter by Model",
                    choices=["All"],
                    value="All",
                    multiselect=True,
                    interactive=True,
                )

            # Adding pivot table options after the filters
            with gr.Row():
                # Pivot table configuration
                pivot_rows = gr.Dropdown(
                    label="Select Row Fields (required)",
                    choices=[],
                    multiselect=True,
                    interactive=True,
                )
                pivot_columns = gr.Dropdown(
                    label="Select Column Fields (optional)",
                    choices=[],
                    multiselect=True,
                    interactive=True,
                )
                pivot_values = gr.Dropdown(
                    label="Select Values Field (required)", choices=[], interactive=True
                )
                pivot_aggfunc = gr.Dropdown(
                    label="Aggregation Function",
                    choices=["count", "sum", "mean", "median", "max", "min"],
                    value="count",
                    interactive=True,
                )

            with gr.Row():
                generate_pivot_button = gr.Button("Generate Pivot Table")

            with gr.Row():
                pivot_table_output = gr.Dataframe(
                    label="Pivot Table Results", interactive=False
                )

        with gr.TabItem("Repeated Failures Analysis"):
            with gr.Row():
                min_failures = gr.Slider(
                    minimum=2, maximum=10, value=4, step=1, label="Minimum Failures"
                )
                analyze_failures_button = gr.Button("Analyze Repeated Failures")

            # Add sorting controls
            with gr.Row():
                sort_by = gr.Dropdown(
                    choices=["TC Count", "Model", "Station ID", "Test Case"],
                    value="TC Count",
                    label="Sort Results By",
                )
                test_case_filter = gr.Dropdown(
                    choices=["Select All", "Clear All"],
                    value=[],
                    label="Filter by Test Case",
                    multiselect=True,
                )

            with gr.Row():
                failures_summary = gr.Markdown(
                    value="", label="Repeated Failures Summary"
                )
            with gr.Row():
                failures_chart = gr.Plot(label="Repeated Failures Chart")
            with gr.Row():
                failures_df = gr.Dataframe(label="Repeated Failures Data")

        with gr.TabItem("WiFi Error Analysis"):
            with gr.Row():
                error_threshold = gr.Slider(
                    minimum=0, maximum=100, value=9, step=1, label="Error Threshold (%)"
                )

            analyze_wifi_button = gr.Button("Analyze WiFi Errors")

            with gr.Row():
                summary_table = gr.Dataframe(label="Summary Table")

            with gr.Accordion("Detailed Analysis for High Error Rates", open=False):
                with gr.Row():
                    error_heatmap = gr.Plot(label="Detailed WiFi Error Heatmap")

                with gr.Row():
                    hourly_trend_plot = gr.Plot(
                        label="Hourly Error Trends for High-Error Operators"
                    )

                with gr.Row():
                    pivot_table = gr.Dataframe(
                        label="Hourly Error Breakdown by Operator and Error Type"
                    )

        with gr.TabItem("Advanced Filtering"):
            with gr.Row():
                advanced_operator_filter = gr.Dropdown(
                    label="Operator", choices=["All"], multiselect=True, value="All"
                )
                advanced_model_filter = gr.Dropdown(
                    label="Model", choices=["All"], multiselect=True, value="All"
                )
                advanced_manufacturer_filter = gr.Dropdown(
                    label="Manufacturer", choices=["All"], multiselect=True, value="All"
                )
                advanced_source_filter = gr.Dropdown(
                    label="Source", choices=["All"], multiselect=True, value="All"
                )
            with gr.Row():
                advanced_overall_status_filter = gr.Dropdown(
                    label="Overall status",
                    choices=["All"],
                    multiselect=True,
                    value="All",
                )
                advanced_station_id_filter = gr.Dropdown(
                    label="Station ID", choices=["All"], multiselect=True, value="All"
                )
                advanced_result_fail_filter = gr.Dropdown(
                    label="result_FAIL", choices=["All"], multiselect=True, value="All"
                )
            with gr.Row():
                sort_columns = gr.Dropdown(
                    choices=[
                        "Date Time",
                        "Operator",
                        "Model",
                        "IMEI",
                        "Manufacturer",
                        "Source",
                        "Overall status",
                        "Station ID",
                        "result_FAIL",
                        "error_code",
                        "error_message",
                    ],
                    label="Select columns to sort",
                    multiselect=True,
                )
            with gr.Row():
                apply_filter_button = gr.Button("Apply Filter and Sort")
            with gr.Row():
                filtered_data = gr.Dataframe(label="Filtered Data")
            with gr.Row():
                filter_summary = gr.Textbox(label="Filter Summary", lines=3)

        with gr.TabItem("IMEI Extractor"):
            with gr.Row():
                source = gr.Dropdown(
                    label="Source", choices=["All"], value="All", interactive=True
                )
                station_id = gr.Dropdown(
                    label="Station ID", choices=["All"], value="All", interactive=True
                )
                model_input = gr.Dropdown(
                    label="Model(s)",
                    choices=["All"],
                    value="All",
                    interactive=True,
                    multiselect=True,
                )
                result_fail = gr.Dropdown(
                    label="Result Fail", choices=["All"], value="All", interactive=True
                )
                flexible_search = gr.Checkbox(
                    label="Enable Flexible Search", value=False
                )

            with gr.Row():
                process_button = gr.Button("Process Data", variant="primary")

            with gr.Column():
                # Group commands first
                with gr.Column(elem_classes=["command-section"]):
                    messages_output = gr.Code(
                        label="Messages Command",
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"],
                    )
                    raw_data_output = gr.Code(
                        label="Raw Data Command",
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"],
                    )
                    gauge_output = gr.Code(
                        label="Gauge Command",
                        language="shell",
                        elem_classes=["custom-textbox", "command-box"],
                    )

                # Then show summary
                summary_output = gr.Markdown(
                    label="Query Results",
                    elem_classes=["markdown-body", "custom-markdown"],
                )

    # Event Handlers
    file_input.change(
        load_and_update,
        inputs=[file_input],
        outputs=[
            df,
            source,  # IMEI Extractor: Source
            station_id,  # IMEI Extractor: Station ID
            model_input,  # IMEI Extractor: Model(s)
            result_fail,  # IMEI Extractor: Result Fail
            advanced_operator_filter,
            advanced_model_filter,
            advanced_manufacturer_filter,
            advanced_source_filter,
            advanced_overall_status_filter,
            advanced_station_id_filter,
            advanced_result_fail_filter,
            pivot_rows,  # For Pivot Table Builder
            pivot_columns,
            pivot_values,
            filter_operator,  # Pivot Table Filters
            filter_station_id,
            filter_model,
            operator_filter,
            source_filter,
            station_id_filter,
        ],
    )

    analyze_button.click(
        fn=perform_analysis,
        inputs=[file_input],
        outputs=[
            analysis_summary,
            overall_status_chart,
            stations_chart,
            models_chart,
            test_cases_chart,
            stations_df,
            models_df,
            test_cases_df,
        ],
    )

    filter_type.change(
        update_filter_visibility,
        inputs=[filter_type],
        outputs=[operator_filter, source_filter, station_id_filter],
    )

    custom_filter_button.click(
        filter_data,
        inputs=[df, filter_type, operator_filter, source_filter, station_id_filter],
        outputs=[
            custom_filter_summary,
            custom_filter_chart1,
            custom_filter_chart2,
            custom_filter_chart3,
            custom_filter_df1,
            custom_filter_df2,
            custom_filter_df3,
        ],
    )

    analyze_wifi_button.click(
        analyze_wifi_errors,
        inputs=[file_input, error_threshold],
        outputs=[summary_table, error_heatmap, pivot_table, hourly_trend_plot],
    )

    analyze_failures_button.click(
        analyze_repeated_failures,
        inputs=[file_input, min_failures],
        outputs=[failures_summary, failures_chart, failures_df, test_case_filter],
    )

    sort_by.change(
        update_summary_chart_and_data,
        inputs=[failures_df, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart, failures_df],
    )

    test_case_filter.change(
        update_summary_chart_and_data,
        inputs=[failures_df, sort_by, test_case_filter],
        outputs=[failures_summary, failures_chart, failures_df],
    )

    # Add select/clear all handler
    test_case_filter.select(
        handle_test_case_selection,
        inputs=[test_case_filter],
        outputs=[test_case_filter],
    )

    apply_filter_button.click(
        apply_filter_and_sort,
        inputs=[
            df,
            sort_columns,
            advanced_operator_filter,
            advanced_model_filter,
            advanced_manufacturer_filter,
            advanced_source_filter,
            advanced_overall_status_filter,
            advanced_station_id_filter,
            advanced_result_fail_filter,
        ],
        outputs=[filtered_data, filter_summary],
    )

    generate_pivot_button.click(
        generate_pivot_table_filtered,
        inputs=[
            df,
            pivot_rows,
            pivot_columns,
            pivot_values,
            pivot_aggfunc,
            filter_operator,
            filter_station_id,
            filter_model,
        ],
        outputs=[pivot_table_output],
    )

    process_button.click(
        process_data,
        inputs=[
            df,
            source,
            station_id,
            model_input,
            result_fail,
            flexible_search,
        ],
        outputs=[messages_output, raw_data_output, gauge_output, summary_output],
    )

demo.launch(share=False)
