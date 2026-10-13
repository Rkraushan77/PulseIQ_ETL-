
from pathlib import Path
import logging

from src.etl_pipeline.extract import extract_all
from src.etl_pipeline.transform import clean_data
from src.etl_pipeline.validate import validate_employee
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
        "employee": "employee.csv",
    }

    logging.info("Pipeline started")

    try:
        data = extract_all(RAW_DIR, files)

        employee = clean_data(data["employee"])

        clean, rejected = validate_employee(employee)

        total_rows = len(employee)
        clean_rows = len(clean)
        rejected_rows = len(rejected)

        if total_rows > 0:
            rejection_rate = round(
                rejected_rows / total_rows * 100, 2
            )
            clean_rate = round(
                clean_rows / total_rows * 100, 2
            )
        else:
            rejection_rate = 0
            clean_rate = 0

        metrics = {
            "input_rows": total_rows,
            "clean_rows": clean_rows,
            "rejected_rows": rejected_rows,
            "rejection_rate": rejection_rate,
            "clean_rate": clean_rate,
        }

        save_data(clean, CLEAN_DIR, "employee_clean.csv")
        save_data(rejected, REJECTED_DIR, "employee_rejected.csv")

        logging.info("Metrics: %s", metrics)
        logging.info("Pipeline completed successfully")

        print("\nPipeline completed successfully")
        print("Metrics:")

        for name, value in metrics.items():
            print(f"{name}: {value}")

    except Exception:
        logging.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    run_pipeline()
