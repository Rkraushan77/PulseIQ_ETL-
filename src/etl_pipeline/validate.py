import pandas as pd
import pandera.pandas as pa


def validate_exact_duplicates(df):
    """
    Keep the first occurrence of each exact row.
    Reject subsequent identical rows with a reason.
    """
    df = df.copy()

    duplicate_mask = df.duplicated(keep="first")

    clean = df.loc[~duplicate_mask].copy()
    rejected = df.loc[duplicate_mask].copy()

    rejected["rejection_reason"] = "Exact duplicate row;"

    return clean, rejected


def validate_employee(df):
    df = df.copy()

    # Validate employee IDs
    df["employee_id"] = (
        df["employee_id"].astype("string").str.strip()
    )

    missing_id = (
        df["employee_id"].isna()
        | (df["employee_id"] == "")
    )

    duplicate_id = (
        df["employee_id"].duplicated(keep=False)
        & ~missing_id
    )

    # Convert date columns safely
    date_columns = ["hire_date", "exit_date"]

    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column], errors="coerce"
            )

    # Flag invalid hire dates
    invalid_hire_date = df["hire_date"].isna()

    # Flag exit dates earlier than hire dates
    invalid_date_order = (
        df["exit_date"].notna()
        & df["hire_date"].notna()
        & (df["exit_date"] < df["hire_date"])
    )

    # Record rejection reasons
    df["rejection_reason"] = ""

    df.loc[missing_id, "rejection_reason"] += (
        "Missing employee ID; "
    )

    df.loc[duplicate_id, "rejection_reason"] += (
        "Duplicate employee ID; "
    )

    df.loc[invalid_hire_date, "rejection_reason"] += (
        "Invalid hire date; "
    )

    df.loc[invalid_date_order, "rejection_reason"] += (
        "Exit date before hire date; "
    )

    # Separate clean and rejected records
    rejected = df[df["rejection_reason"] != ""].copy()

    clean = df[df["rejection_reason"] == ""].drop(
        columns=["rejection_reason"]
    ).copy()

    # Validate clean records using Pandera
    schema = pa.DataFrameSchema(
        {
            "employee_id": pa.Column(str, nullable=False),
            "hire_date": pa.Column(
                pa.DateTime,
                nullable=False,
            ),
        },
        strict=False,
        coerce=True,
    )

    clean = schema.validate(clean)

    return clean, rejected


def validate_non_negative_amounts(df, amount_columns):
    """
    Reject rows where any specified amount is negative
    or cannot be converted to a number.
    """
    df = df.copy()
    df["rejection_reason"] = ""

    for column in amount_columns:
        if column not in df.columns:
            raise ValueError(
                f"Required amount column missing: {column}"
            )

        values = pd.to_numeric(df[column], errors="coerce")

        invalid = values.isna() | (values < 0)

        df.loc[invalid, "rejection_reason"] += (
            f"Invalid or negative {column}; "
        )

    rejected = df[df["rejection_reason"] != ""].copy()

    clean = df[df["rejection_reason"] == ""].drop(
        columns=["rejection_reason"]
    ).copy()

    return clean, rejected

def validate_allowed_values(df, allowed_values):
    """
    Reject rows that contain values not allowed by the contract.
    """
    df = df.copy()
    df["rejection_reason"] = ""

    for column, allowed in allowed_values.items():
        if column not in df.columns:
            raise ValueError(
                f"Required column missing: {column}"
            )

        invalid = (
            df[column].notna()
            & ~df[column].astype(str).isin(allowed)
        )

        df.loc[invalid, "rejection_reason"] += (
            f"Invalid value in {column}; "
        )

    rejected = df[df["rejection_reason"] != ""].copy()

    clean = df[df["rejection_reason"] == ""].drop(
        columns=["rejection_reason"]
    ).copy()

    return clean, rejected

def validate_allowed_values(df, allowed_values):
    """
    Reject rows that contain values not allowed by the contract.
    """
    df = df.copy()
    df["rejection_reason"] = ""

    for column, allowed in allowed_values.items():
        if column not in df.columns:
            raise ValueError(
                f"Required column missing: {column}"
            )

        invalid = (
            df[column].notna()
            & ~df[column].astype(str).isin(allowed)
        )

        df.loc[invalid, "rejection_reason"] += (
            f"Invalid value in {column}; "
        )

    rejected = df[df["rejection_reason"] != ""].copy()

    clean = df[df["rejection_reason"] == ""].drop(
        columns=["rejection_reason"]
    ).copy()

    return clean, rejected
