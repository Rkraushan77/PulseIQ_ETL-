
import pandas as pd
import pandera.pandas as pa


def validate_employee(df):
    df = df.copy()

    df["salary"] = pd.to_numeric(df["salary"], errors="coerce")

    missing_id = df["employee_id"].isna() | (
        df["employee_id"].astype(str).str.strip() == ""
    )
    bad_salary = df["salary"].isna() | (df["salary"] < 0)

    df["rejection_reason"] = ""

    df.loc[missing_id, "rejection_reason"] += "Missing employee ID; "
    df.loc[bad_salary, "rejection_reason"] += "Invalid salary; "

    rejected = df[df["rejection_reason"] != ""].copy()
    clean = df[df["rejection_reason"] == ""].drop(
        columns=["rejection_reason"]
    ).copy()

    schema = pa.DataFrameSchema(
        {
            "employee_id": pa.Column(str, nullable=False),
            "salary": pa.Column(float, nullable=False, checks=pa.Check.ge(0)),
        },
        strict=False,
        coerce=True,
    )

    clean = schema.validate(clean)

    return clean, rejected
