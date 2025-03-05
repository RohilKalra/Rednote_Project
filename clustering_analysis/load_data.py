import pandas as pd
import os
import sys
from itables import show
from itables import init_notebook_mode  # Use this instead of load_datatables


def display_csv_with_itables(csv_file_path="data.csv"):
    """
    Reads a CSV file and displays it as an interactive table using itables.
    Looks for the file in the parent directory.

    Parameters:
    -----------
    csv_file_path : str
        Path to the CSV file (default is 'data.csv')
    """
    try:
        # Construct path to parent directory
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(parent_dir, "data", csv_file_path)

        print(f"Looking for file at: {full_path}")

        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(full_path)

        # Print basic information about the data
        print(f"Successfully loaded {csv_file_path}")
        print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print("\nColumn names:")
        for col in df.columns:
            print(f"  - {col}")

        print("\nData types:")
        for col, dtype in df.dtypes.items():
            print(f"  - {col}: {dtype}")

        print("\nFirst 5 rows:")
        print(df.head())

        # Check for missing values
        missing = df.isnull().sum()
        if missing.sum() > 0:
            print("\nMissing values detected:")
            for col, count in missing.items():
                if count > 0:
                    print(f"  - {col}: {count} missing values")

        # Display the interactive table
        print("\nDisplaying interactive table (if in Jupyter environment)...")

        # Configure itables options
        show(
            df,
            classes="display compact",
            paging=True,
            searching=True,
            ordering=True,
            info=True,
            lengthMenu=[10, 25, 50, 100, -1],
            scrollX=True,
        )

        return df

    except FileNotFoundError:
        print(f"Error: File '{full_path}' not found.")
        return None
    except pd.errors.EmptyDataError:
        print(f"Error: '{full_path}' is empty.")
        return None
    except pd.errors.ParserError:
        print(f"Error: Unable to parse '{full_path}'. Check if it's a valid CSV file.")
        return None
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}")
        return None


if __name__ == "__main__":
    # Initialize itables for Jupyter notebooks
    try:
        init_notebook_mode(all_interactive=True)
    except Exception as e:
        print(f"Warning: Could not initialize notebook mode: {str(e)}")
        print(
            "Interactive tables may not display correctly outside a Jupyter environment."
        )

    # Get filename from command line argument or use default
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "data.csv"
        print("No filename provided, using default: data.csv")

    # Call the function to display the CSV file
    df = display_csv_with_itables(filename)
