
import pandas as pd

from src.etl_pipeline.transform import clean_data


def test_clean_data():
    df = pd.DataFrame({
        "Employee Name": ["Amit", "Amit", "Neha"],
        "Salary": [25000, 25000, 30000]
    })

    result = clean_data(df)

    assert len(result) == 2
    assert "employee_name" in result.columns
    assert "salary" in result.columns
