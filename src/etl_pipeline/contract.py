
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
CONTRACT_PATH = BASE_DIR / "contracts" / "data_contract.json"


def load_contract():
    with open(CONTRACT_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_contract_sheet(sheet_name, df, contract):
    if sheet_name not in contract["sheets"]:
        raise ValueError(
            f"No data contract defined for sheet: {sheet_name}"
        )

    rules = contract["sheets"][sheet_name]
    errors = []

    # Check required columns
    for column in rules.get("required_columns", []):
        if column not in df.columns:
            errors.append(f"Missing required column: {column}")

    # Stop if required columns are missing
    if errors:
        raise ValueError(
            f"Contract validation failed for {sheet_name}: "
            + "; ".join(errors)
        )

    # Check unique key
    key = rules.get("unique_key")
    if key:
        if df[key].isna().any() or df[key].astype(str).str.strip().eq("").any():
            errors.append(f"{key} contains missing or blank values")

        if df[key].duplicated().any():
            errors.append(f"{key} contains duplicate values")

    # Check date values
    for column in rules.get("date_columns", []):
        if column in df.columns:
            parsed_dates = pd.to_datetime(df[column], errors="coerce")
            invalid = df[column].notna() & parsed_dates.isna()

            if invalid.any():
                errors.append(
                    f"{column} contains {int(invalid.sum())} invalid date values"
                )

    # Check non-negative numeric values
    
    # Check non-negative numeric values
    for column in rules.get("non_negative_columns", []):
        if column in df.columns:
            numbers = pd.to_numeric(df[column], errors="coerce")
            invalid = numbers.isna() | (numbers < 0)

            if invalid.any():
                errors.append(
                    f"{column} contains "
                    f"{int(invalid.sum())} invalid or negative values"
                )

    # Allow missing values for configured numeric columns,
    # but reject non-numeric or negative values when present.
    for column in rules.get("nullable_non_negative_columns", []):
        if column in df.columns:
            numbers = pd.to_numeric(df[column], errors="coerce")
            invalid = (
                df[column].notna()
                & (numbers.isna() | (numbers < 0))
            )

            if invalid.any():
                errors.append(
                    f"{column} contains "
                    f"{int(invalid.sum())} invalid or negative values"
                )

def split_contract_rows(sheet_name, df, contract):
    """Separate valid rows from rows that violate contract rules."""
    rules = contract["sheets"].get(sheet_name)

    if rules is None:
        raise ValueError(
            f"No data contract defined for sheet: {sheet_name}"
        )

    df = df.copy()
    reasons = pd.Series("", index=df.index, dtype="string")

    # Required columns are structural rules: fail clearly if absent.
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

    # Unique key: reject rows with blank or duplicate keys.
    key = rules.get("unique_key")
    if key:
        blank_key = (
            df[key].isna()
            | df[key].astype("string").str.strip().eq("")
        )
        duplicate_key = df[key].duplicated(keep=False) & ~blank_key

        add_reason(blank_key, f"Missing {key}")
        add_reason(duplicate_key, f"Duplicate {key}")

    # Dates: reject nonblank values that cannot be parsed.
    parsed_dates = {}
    for column in rules.get("date_columns", []):
        if column in df.columns:
            parsed = pd.to_datetime(df[column], errors="coerce")
            parsed_dates[column] = parsed
            invalid = df[column].notna() & parsed.isna()
            add_reason(invalid, f"Invalid {column}")

    # Non-negative numeric columns; blank values are invalid by default.
    for column in rules.get("non_negative_columns", []):
        if column in df.columns:
            numbers = pd.to_numeric(df[column], errors="coerce")
            invalid = numbers.isna() | (numbers < 0)
            add_reason(invalid, f"Invalid or negative {column}")

    # These numeric columns may be blank, but not non-numeric or negative.
    for column in rules.get("nullable_non_negative_columns", []):
        if column in df.columns:
            numbers = pd.to_numeric(df[column], errors="coerce")
            invalid = (
                df[column].notna()
                & (numbers.isna() | (numbers < 0))
            )
            add_reason(invalid, f"Invalid or negative {column}")

    # Date-order rules
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

    rejected_mask = reasons.str.len() > 0
    clean = df.loc[~rejected_mask].copy()
    rejected = df.loc[rejected_mask].copy()
    rejected["rejection_reason"] = reasons.loc[rejected_mask]

    return clean, rejected
