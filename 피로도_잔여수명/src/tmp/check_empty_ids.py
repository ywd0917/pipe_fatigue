import pandas as pd
from pathlib import Path
import sys

def check_empty_ids():
    """
    Checks for empty or null 'ID' values in the merged repair data CSV file.
    """
    # Define the path to the merged CSV file
    file_path = Path("results/main11e_merge_all_repairs/누수공사_통합_위치추가.csv")

    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        sys.exit(1)

    try:
        # Load the CSV file
        df = pd.read_csv(file_path, low_memory=False)

        # Check if 'ID' column exists
        if 'ID' not in df.columns:
            print("Error: 'ID' column not found in the file.")
            sys.exit(1)

        # Find rows where 'ID' is null or an empty string
        empty_id_mask = df['ID'].isnull() | (df['ID'].astype(str).str.strip() == '')
        empty_id_rows = df[empty_id_mask]

        num_empty_ids = len(empty_id_rows)
        total_rows = len(df)

        print(f"Total rows in file: {total_rows}")
        print(f"Number of rows with empty or null ID: {num_empty_ids}")

        if num_empty_ids > 0:
            print(f"Percentage of rows with empty ID: {(num_empty_ids / total_rows) * 100:.2f}%")
            print("\n--- First 5 rows with empty ID ---")
            print(empty_id_rows.head())
            print("------------------------------------")
        else:
            print("No empty or null ID values found.")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_empty_ids()
