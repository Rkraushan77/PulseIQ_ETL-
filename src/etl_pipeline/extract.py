
from pathlib import Path
import pandas as pd


def load_csv(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    df = pd.read_csv(file_path)
    print(f"Loaded {file_path.name}: {len(df)} rows")
    return df


def extract_all(raw_dir, files):
    data = {}

    for name, file_name in files.items():
        data[name] = load_csv(Path(raw_dir) / file_name)

    return data


def extract_excel_sheets(workbook_path, sheet_names):
    workbook_path = Path(workbook_path)

    if not workbook_path.exists():
        raise FileNotFoundError(
            f"Workbook not found: {workbook_path}"
        )

    data = {}

    for sheet_name in sheet_names:
        df = pd.read_excel(
            workbook_path,
            sheet_name=sheet_name,
        )
        data[sheet_name] = df
        print(
            f"Loaded sheet {sheet_name}: {len(df)} rows"
        )

    return data
