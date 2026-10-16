import pandas as pd
from src.etl_pipeline.validate import validate_exact_duplicates

def clean_columns(df):
    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    return df


def remove_duplicates(df):
    """
    Kept for compatibility with existing code.
    Duplicate removal is handled by the validation pipeline
    so duplicate records can be counted and tracked.
    """
    return df.copy()


def add_helper_columns(df):
    df = df.copy()

    # Add tenure fields only when hire_date is available.
    if "hire_date" in df.columns:
        df["hire_date"] = pd.to_datetime(
            df["hire_date"], errors="coerce"
        )

        reference_date = pd.Timestamp("2026-09-30")

        df["hire_month"] = df["hire_date"].dt.month
        df["hire_year"] = df["hire_date"].dt.year

        df["tenure_days"] = (
            reference_date - df["hire_date"]
        ).dt.days

        df["tenure_years"] = (
            df["tenure_days"] / 365.25
        ).round(2)

    return df


def clean_data(df):
    df = clean_columns(df)
    df = remove_duplicates(df)
    df = add_helper_columns(df)

    return df
def test_exact_duplicate_rows_are_rejected():
    df = pd.DataFrame({
        "employee_id": ["EMP001", "EMP001", "EMP002"],
        "name": ["Amit", "Amit", "Neha"]
    })

    clean, rejected = validate_exact_duplicates(df)

    assert len(clean) == 2
    assert len(rejected) == 1
    assert "Exact duplicate row" in rejected.iloc[0]["rejection_reason"]