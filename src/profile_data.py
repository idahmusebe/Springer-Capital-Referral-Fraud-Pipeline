from pathlib import Path
import pandas as pd


# Find the project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Folder containing the 7 CSV files
DATA_DIR = PROJECT_ROOT / "data"

# Folder where profiling results will be saved
OUTPUT_DIR = PROJECT_ROOT / "profiling"
OUTPUT_DIR.mkdir(exist_ok=True)


def profile_table(file_path):
    """Profile one CSV file."""

    df = pd.read_csv(file_path)

    profile = pd.DataFrame({
        "column_name": df.columns,
        "data_type": [str(df[column].dtype) for column in df.columns],
        "null_count": [df[column].isna().sum() for column in df.columns],
        "distinct_count": [df[column].nunique(dropna=True) for column in df.columns],
    })

    profile.insert(0, "table_name", file_path.stem)
    profile.insert(1, "row_count", len(df))

    return profile


def main():
    """Profile all CSV files in the data folder."""

    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError("No CSV files found in the data folder.")

    all_profiles = []

    for file_path in csv_files:
        print(f"Profiling: {file_path.name}")
        profile = profile_table(file_path)
        all_profiles.append(profile)

    final_profile = pd.concat(all_profiles, ignore_index=True)

    output_file = OUTPUT_DIR / "profiling_results.csv"
    final_profile.to_csv(output_file, index=False)

    print("\nProfiling completed successfully!")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()