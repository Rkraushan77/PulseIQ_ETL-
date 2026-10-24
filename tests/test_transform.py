import pandas as pd

from src.etl_pipeline.transform import (
    clean_columns,
    add_helper_columns,
    clean_data,
)
from src.etl_pipeline.validate import validate_exact_duplicates


def test_clean_columns():
    df = pd.DataFrame({
        " Employee ID ": ["EMP-001"],
        "First Name": ["Raushan"],
    })

    result = clean_columns(df)

    assert list(result.columns) == ["employee_id", "first_name"]


def test_add_helper_columns():
    df = pd.DataFrame({
        "hire_date": ["2025-09-30"],
    })

    result = add_helper_columns(df)

    assert result.loc[0, "hire_month"] == 9
    assert result.loc[0, "hire_year"] == 2025
    assert result.loc[0, "tenure_days"] == 365
    assert result.loc[0, "tenure_years"] == 1.0


def test_clean_data():
    df = pd.DataFrame({
        "Employee ID": ["EMP-001"],
    })

    result = clean_data(df)

    assert "employee_id" in result.columns
    assert len(result) == 1


def test_validate_exact_duplicates():
    df = pd.DataFrame({
        "employee_id": ["EMP-001", "EMP-001"],
        "first_name": ["Asha", "Asha"],
    })

    clean, rejected = validate_exact_duplicates(df)

    assert len(clean) == 1
    assert len(rejected) == 1
    assert "rejection_reason" in rejected.columns
