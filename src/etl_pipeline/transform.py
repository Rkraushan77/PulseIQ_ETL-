import logging
import pandas as pd

logger = logging.getLogger(__name__)


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
    """Keep duplicate handling in the validation pipeline."""
    return df.copy()


def add_helper_columns(df):
    df = df.copy()

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


def warn_unexpected_columns(df, sheet_name, contract):
    """Log unexpected columns without deleting them."""
    sheet_rules = contract.get("sheets", {}).get(sheet_name)

    if sheet_rules is None:
        logger.warning(
            "No contract found for dataset '%s'.", sheet_name
        )
        return

    expected_columns = (
        set(sheet_rules.get("column_types", {}).keys())
        | set(sheet_rules.get("required_columns", []))
    )

    actual_columns = set(df.columns)
    unexpected_columns = sorted(actual_columns - expected_columns)

    if unexpected_columns:
        logger.warning(
            "Unexpected columns in '%s': %s",
            sheet_name,
            ", ".join(unexpected_columns),
        )


def clean_data(df):
    df = clean_columns(df)
    df = remove_duplicates(df)
    df = add_helper_columns(df)

    return df
