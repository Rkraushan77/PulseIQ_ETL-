
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
CONTRACT_PATH = BASE_DIR / "contracts" / "data_contract.json"


def load_contract():
    with open(CONTRACT_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def split_contract_rows(sheet_name, df, contract):
    """Separate valid rows from rows that break contract rules."""

    rules = contract["sheets"].get(sheet_name)

    if rules is None:
        raise ValueError(
            f"No data contract defined for sheet: {sheet_name}"
        )

    df = df.copy()
    reasons = pd.Series("", index=df.index, dtype="string")

    # Required columns are structural rules.
    missing_columns = [
        column
        for column in rules.get("required_columns", [])
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{sheet_name} is missing required columns: "
            + ", ".join(missing_columns)
        )

    def add_reason(mask, message):
        nonlocal reasons
        reasons.loc[mask] = reasons.loc[mask] + message + "; "

    nullable_columns = set(rules.get("nullable_columns", []))

    # Check missing values in columns that must not be blank.
    for column in df.columns:
        if column in nullable_columns:
            continue

        if column in rules.get("column_types", {}):
            blank = df[column].isna()

            if pd.api.types.is_string_dtype(df[column]):
                blank = blank | df[column].astype("string").str.strip().eq("")

            add_reason(blank, f"Missing value in {column}")

    # Check unique key values.
    key = rules.get("unique_key")

    if key:
        blank_key = (
            df[key].isna()
            | df[key].astype("string").str.strip().eq("")
        )

        duplicate_key = df[key].duplicated(keep=False) & ~blank_key

        add_reason(blank_key, f"Missing {key}")
        add_reason(duplicate_key, f"Duplicate {key}")

    # Check configured column types.
    for column, expected_type in rules.get("column_types", {}).items():
        if column not in df.columns:
            continue

        values = df[column]
        present = values.notna()

        if expected_type == "string":
            invalid = present & (
                values.astype("string").str.strip().eq("")
            )

        elif expected_type in ("number", "integer"):
            numbers = pd.to_numeric(values, errors="coerce")

            invalid = present & numbers.isna()

            if expected_type == "integer":
                invalid = invalid | (
                    present
                    & numbers.notna()
                    & (numbers % 1 != 0)
                )

        elif expected_type == "date":
            parsed = pd.to_datetime(values, errors="coerce")
            invalid = present & parsed.isna()

        else:
            raise ValueError(
                f"Unsupported column type '{expected_type}' "
                f"for {sheet_name}.{column}"
            )

        add_reason(invalid, f"Invalid type for {column}")

    # Check configured date columns.
    parsed_dates = {}

    for column in rules.get("date_columns", []):
        if column not in df.columns:
            continue

        parsed = pd.to_datetime(df[column], errors="coerce")
        parsed_dates[column] = parsed

        invalid = df[column].notna() & parsed.isna()
        add_reason(invalid, f"Invalid {column}")

    # Check non-negative numeric columns.
    for column in rules.get("non_negative_columns", []):
        if column not in df.columns:
            continue

        numbers = pd.to_numeric(df[column], errors="coerce")
        invalid = numbers.isna() | (numbers < 0)

        add_reason(invalid, f"Invalid or negative {column}")

    # Check numeric columns where missing values are permitted.
    for column in rules.get("nullable_non_negative_columns", []):
        if column not in df.columns:
            continue

        numbers = pd.to_numeric(df[column], errors="coerce")

        invalid = (
            df[column].notna()
            & (numbers.isna() | (numbers < 0))
        )

        add_reason(invalid, f"Invalid or negative {column}")

    # Check allowed values.
    for column, allowed in rules.get("allowed_values", {}).items():
        if column not in df.columns:
            continue

        invalid = (
            df[column].notna()
            & ~df[column].astype(str).isin(allowed)
        )

        add_reason(invalid, f"Invalid value in {column}")

    # Check the order of related dates.
    date_pairs = {
        "employees": ("hire_date", "exit_date"),
        "leave_requests": ("start_date", "end_date"),
        "payroll_runs": ("period_start", "period_end"),
        "payroll_items": ("period_start", "period_end"),
    }

    if sheet_name in date_pairs:
        start, end = date_pairs[sheet_name]

        if start in parsed_dates and end in parsed_dates:
            invalid_order = (
                parsed_dates[start].notna()
                & parsed_dates[end].notna()
                & (parsed_dates[end] < parsed_dates[start])
            )

            add_reason(invalid_order, f"{end} before {start}")

    # Separate valid rows and rejected rows.
    rejected_mask = reasons.str.len() > 0

    clean = df.loc[~rejected_mask].copy()
    rejected = df.loc[rejected_mask].copy()

    rejected["rejection_reason"] = (
        reasons.loc[rejected_mask].str.rstrip("; ")
    )

    return clean, rejected
