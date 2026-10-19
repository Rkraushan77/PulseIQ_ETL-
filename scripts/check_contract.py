import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.etl_pipeline.extract import extract_excel_sheets
from src.etl_pipeline.contract import (
    load_contract,
    validate_contract_sheet,
)


workbook = Path(
    "data/raw/01_LedgerForge_Python_Master_Dataset.xlsx"
)

contract = load_contract()

data = extract_excel_sheets(
    workbook,
    contract["sheets"].keys(),
)

errors = []

for name, df in data.items():
    try:
        validate_contract_sheet(name, df, contract)
        print(f"{name}: PASS")
    except ValueError as error:
        errors.append(str(error))
        print(f"{name}: FAIL - {error}")

if errors:
    print(f"\nContract issues found: {len(errors)}")
else:
    print("\nAll configured sheets passed the contract.")
