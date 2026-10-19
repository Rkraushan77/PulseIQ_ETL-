
from pathlib import Path
import logging
import pandas as pd

from src.etl_pipeline.extract import extract_excel_sheets
from src.etl_pipeline.transform import clean_data
from src.etl_pipeline.contract import (
    load_contract,
    split_contract_rows,
)
from src.etl_pipeline.load import save_data


BASE_DIR = Path(__file__).resolve().parents[2]

WORKBOOK = BASE_DIR / "data" / "raw" / "01_LedgerForge_Python_Master_Dataset.xlsx"
CLEAN_DIR = BASE_DIR / "data" / "clean"
REJECTED_DIR = BASE_DIR / "data" / "rejected"
LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "etl.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def run_pipeline():
    logging.info("Pipeline started")
    print("Starting PulseIQ ETL pipeline...")

    try:
        contract = load_contract()

        data = extract_excel_sheets(
            WORKBOOK,
            contract["sheets"].keys(),
        )

        total_input = 0
        total_clean = 0
        total_rejected = 0

        for name, df in data.items():
            input_rows = len(df)
            total_input += input_rows

            # Standardize column names and helper columns.
            transformed = clean_data(df)

            # Contract validation fails clearly if the dataset
            # violates a configured rule.
            clean, rejected = split_contract_rows(
    name,
    transformed,
    contract
)

            clean_rows = len(clean)
            rejected_rows = len(rejected)

            total_clean += clean_rows
            total_rejected += rejected_rows

            rejection_rate = (
                round(rejected_rows / input_rows * 100, 2)
                if input_rows else 0.0
            )
            clean_rate = (
                round(clean_rows / input_rows * 100, 2)
                if input_rows else 0.0
            )

            metrics = {
                "dataset": name,
                "input_rows": input_rows,
                "clean_rows": clean_rows,
                "rejected_rows": rejected_rows,
                "rejection_rate": rejection_rate,
                "clean_rate": clean_rate,
            }

            save_data(clean, CLEAN_DIR, f"{name}_clean.csv")
            save_data(rejected, REJECTED_DIR, f"{name}_rejected.csv")

            logging.info("Dataset metrics: %s", metrics)
            print(f"\n{name} metrics:")
            for key, value in metrics.items():
                if key != "dataset":
                    print(f"{key}: {value}")

        summary = {
            "input_rows": total_input,
            "clean_rows": total_clean,
            "rejected_rows": total_rejected,
        }

        logging.info("Pipeline totals: %s", summary)
        print("\nPipeline totals:")
        for key, value in summary.items():
            print(f"{key}: {value}")

        logging.info("Pipeline completed successfully")
        print("\nPipeline completed successfully")

    except Exception:
        logging.exception("Pipeline failed")
        print("Pipeline failed. Check logs/etl.log for details.")
        raise


if __name__ == "__main__":
    run_pipeline()
