from pathlib import Path
import logging

from src.etl_pipeline.extract import extract_all
from src.etl_pipeline.transform import clean_data
from src.etl_pipeline.validate import (
    validate_employee,
    validate_non_negative_amounts,
    validate_exact_duplicates,
)
from src.etl_pipeline.load import save_data


BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
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
    files = {
        "employee": "sample/employees_sample.csv",
        "department": "sample/departments_sample.csv",
        "salary_revision": "sample/salary_revisions_sample.csv",
        "salary_structure": "sample/salary_structures_sample.csv",
        "attendance": "sample/attendance_sample.csv",
        "leave_request": "sample/leave_requests_sample.csv",
        "payroll_run": "sample/payroll_runs_sample.csv",
        "payroll_item": "sample/payroll_items_sample.csv",
    }

    logging.info("Pipeline started")
    print("Starting ETL pipeline...")

    try:
        data = extract_all(RAW_DIR, files)

        for name, df in data.items():
            # Count original records before cleaning
            input_rows = len(df)

            # Standardize column names and add helper columns
            transformed = clean_data(df)

            # Reject exact duplicate rows before dataset validation
            unique_rows, duplicate_rejected = (
                validate_exact_duplicates(transformed)
            )

            # Dataset-specific validation
            if name == "employee":
                clean, rejected = validate_employee(unique_rows)

            elif name == "salary_structure":
                clean, rejected = validate_non_negative_amounts(
                    unique_rows,
                    ["monthly_amount"],
                )

            elif name == "payroll_item":
                payroll_amount_columns = [
                    "monthly_fixed_gross",
                    "earned_fixed_pay",
                    "gross_pay",
                    "total_deductions",
                    "net_pay",
                    "employer_cost",
                ]

                clean, rejected = validate_non_negative_amounts(
                    unique_rows,
                    payroll_amount_columns,
                )

            else:
                # Dataset-specific validation will be added later.
                clean = unique_rows.copy()
                rejected = unique_rows.iloc[0:0].copy()
                rejected["rejection_reason"] = ""

            # Combine duplicate rejections with other rejections.
            # Align columns so each rejected row retains its reason.
            rejected_frames = []

            if not duplicate_rejected.empty:
                rejected_frames.append(duplicate_rejected)

            if not rejected.empty:
                rejected_frames.append(rejected)

            if rejected_frames:
                all_rejected = __import__("pandas").concat(
                    rejected_frames,
                    ignore_index=True,
                    sort=False,
                )
            else:
                all_rejected = unique_rows.iloc[0:0].copy()
                all_rejected["rejection_reason"] = ""

            clean_rows = len(clean)
            rejected_rows = len(all_rejected)

            rejection_rate = (
                round(rejected_rows / input_rows * 100, 2)
                if input_rows > 0
                else 0.0
            )

            clean_rate = (
                round(clean_rows / input_rows * 100, 2)
                if input_rows > 0
                else 0.0
            )

            metrics = {
                "dataset": name,
                "input_rows": input_rows,
                "clean_rows": clean_rows,
                "rejected_rows": rejected_rows,
                "rejection_rate": rejection_rate,
                "clean_rate": clean_rate,
            }

            # Save clean and rejected records
            save_data(
                clean,
                CLEAN_DIR,
                f"{name}_clean.csv",
            )

            save_data(
                all_rejected,
                REJECTED_DIR,
                f"{name}_rejected.csv",
            )

            logging.info("Dataset metrics: %s", metrics)

            print(f"\n{name.replace('_', ' ').title()} metrics:")
            for metric_name, value in metrics.items():
                if metric_name != "dataset":
                    print(f"{metric_name}: {value}")

        logging.info("Pipeline completed successfully")
        print("\nPipeline completed successfully")

    except Exception:
        logging.exception("Pipeline failed")
        print("Pipeline failed. Check logs/etl.log for details.")
        raise


if __name__ == "__main__":
    run_pipeline()
