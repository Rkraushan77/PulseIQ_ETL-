from src.etl_pipeline.validate import validate_non_negative_amounts
import pandas as pd
from src.etl_pipeline.validate import validate_exact_duplicates
from src.etl_pipeline.transform import clean_data
from src.etl_pipeline.validate import validate_employee


def test_clean_data():
    df = pd.DataFrame({
        "Employee Name": ["Amit", "Amit", "Neha"],
        "Salary": [25000, 25000, 30000]
    })

    result = clean_data(df)

    # Cleaning standardizes columns but preserves rows.
    # Duplicate detection happens during validation.
    assert len(result) == 3
    assert "employee_name" in result.columns
    assert "salary" in result.columns
    


def test_invalid_employee_records_are_rejected():
    df = pd.DataFrame({
        "employee_id": ["EMP001", "", "EMP003"],
        "hire_date": [
            "2024-01-10",
            "2024-02-10",
            "2024-05-20"
        ],
        "exit_date": [
            None,
            None,
            "2024-01-01"
        ]
    })

    clean, rejected = validate_employee(df)

    assert len(clean) == 1
    assert len(rejected) == 2

    reasons = " ".join(rejected["rejection_reason"].tolist())

    assert "Missing employee ID" in reasons
    assert "Exit date before hire date" in reasons

def test_duplicate_employee_ids_are_rejected():
    df = pd.DataFrame({
        "employee_id": ["EMP001", "EMP001", "EMP002"],
        "hire_date": [
            "2024-01-10",
            "2024-02-15",
            "2024-03-20"
        ],
        "exit_date": [None, None, None]
    })

    clean, rejected = validate_employee(df)

    assert len(clean) == 1
    assert len(rejected) == 2
    assert all(
        rejected["rejection_reason"].str.contains(
            "Duplicate employee ID"
        )
    )

def test_negative_salary_amounts_are_rejected():
    df = pd.DataFrame({
        "monthly_amount": [25000, -5000, 30000]
    })

    clean, rejected = validate_non_negative_amounts(
        df,
        ["monthly_amount"]
    )

    assert len(clean) == 2
    assert len(rejected) == 1
    assert "negative monthly_amount" in rejected.iloc[0]["rejection_reason"]


def test_exact_duplicate_rows_are_rejected():
    df = pd.DataFrame({
        "employee_id": ["EMP001", "EMP001", "EMP002"],
        "name": ["Amit", "Amit", "Neha"]
    })

    clean, rejected = validate_exact_duplicates(df)

    assert len(clean) == 2
    assert len(rejected) == 1
    assert "Exact duplicate row" in rejected.iloc[0]["rejection_reason"]

    def test_exact_duplicate_rows_are_rejected():
       df = pd.DataFrame({
        "employee_id": ["EMP001", "EMP001", "EMP002"],
        "name": ["Amit", "Amit", "Neha"]
    })

    clean, rejected = validate_exact_duplicates(df)

    assert len(clean) == 2
    assert len(rejected) == 1
    assert "Exact duplicate row" in rejected.iloc[0]["rejection_reason"]