from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

WORKBOOK_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "01_LedgerForge_Python_Master_Dataset.xlsx"
)

OUTPUT_DIR = BASE_DIR / "data" / "raw" / "sample"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Keep the existing employee and department samples.
sample_sheets = {
    "employees": 10,
    "departments": None,
    "salary_revisions": 10,
    "salary_structures": 10,
    "attendance": 10,
    "leave_requests": 10,
    "payroll_runs": 10,
    "payroll_items": 10,
}

try:
    for sheet_name, row_limit in sample_sheets.items():
        if row_limit is None:
            df = pd.read_excel(
                WORKBOOK_PATH,
                sheet_name=sheet_name,
            )
        else:
            df = pd.read_excel(
                WORKBOOK_PATH,
                sheet_name=sheet_name,
                nrows=row_limit,
            )

        output_file = OUTPUT_DIR / f"{sheet_name}_sample.csv"

        df.to_csv(output_file, index=False)

        print(f"{sheet_name}: {len(df)} rows saved")


    print("\nSample files created successfully!")
    print("Output folder:", OUTPUT_DIR)

except Exception as error:
    print("Error creating sample files:", error)
    raise