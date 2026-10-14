from pathlib import Path
import pandas as pd

from openpyxl import load_workbook


BASE_DIR = Path(__file__).resolve().parents[1]

WORKBOOK_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "01_LedgerForge_Python_Master_Dataset.xlsx"
)

OUTPUT_DIR = BASE_DIR / "data" / "raw" / "sample"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

workbook = load_workbook(
    WORKBOOK_PATH,
    read_only=True,
    data_only=True,
)

try:
    employees = pd.read_excel(
        WORKBOOK_PATH,
        sheet_name="employees",
        nrows=10,
    )

    departments = pd.read_excel(
        WORKBOOK_PATH,
        sheet_name="departments",
    )

    employees.to_csv(
        OUTPUT_DIR / "employees_sample.csv",
        index=False,
    )

    departments.to_csv(
        OUTPUT_DIR / "departments_sample.csv",
        index=False,
    )

    print("Sample files created successfully!")
    print("Employee sample rows:", len(employees))
    print("Department rows:", len(departments))
    print("Output folder:", OUTPUT_DIR)

finally:
    workbook.close()