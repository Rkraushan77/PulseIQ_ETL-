# PulseIQ ETL Pipeline

## Project Overview
PulseIQ is a Python-based ETL pipeline built using pandas. It extracts sample employee, department, salary, attendance, leave, and payroll datasets, standardizes their columns, validates selected data quality rules, and saves clean and rejected records separately.

## Technologies Used
- Python 3.11
- pandas
- Pandera
- pytest
- Docker and Docker Compose

## Project Structure
- `src/etl_pipeline/` — ETL extraction, transformation, validation, and loading modules
- `data/raw/sample/` — sample input CSV files
- `data/clean/` — cleaned output CSV files
- `data/rejected/` — rejected records with reasons
- `tests/` — automated tests
- `logs/` — pipeline execution logs
- `docs/metric_dictionary.md` — ETL metric definitions
- `Dockerfile` and `compose.yaml` — Docker configuration

## Setup
Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Locally
```powershell
python -m src.etl_pipeline.pipeline
```

## Run Tests
```powershell
python -m pytest -v
```

## Run with Docker
```powershell
docker compose build etl
docker compose run --rm etl
```

## Data Quality and Outputs
The pipeline standardizes column names, adds helper columns when applicable, checks selected validation rules, and saves clean and rejected records separately. It reports input rows, clean rows, rejected rows, rejection rate, and clean rate. Execution details are recorded in `logs/etl.log`.

## Current Sample Run
The eight sample datasets contain 81 input rows in total. In the latest successful run, all 81 rows were accepted and no rows were rejected. Additional invalid records should be tested when expanding the validation rules.

## Limitations
This version uses small sample CSV files and selected validation rules. It is a foundation for extending validation coverage and processing the full master workbook.
