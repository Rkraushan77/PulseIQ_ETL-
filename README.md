# PulseIQ ETL Pipeline

## Project Overview

PulseIQ is a Python-based Extract, Transform, Load (ETL) pipeline developed using pandas. It processes employee, salary, attendance, leave, and payroll data from the LedgerForge Master Dataset Excel workbook.

The pipeline extracts selected worksheets, standardizes column names, applies data transformations, validates records against a JSON data contract, and saves clean and rejected records separately. It also records processing metrics and execution logs.

The project is designed to demonstrate automated data processing, data quality validation, repeatable execution, automated testing, and Docker-based deployment.

## Technologies Used

- Python 3.11
- pandas
- Pandera
- openpyxl
- pytest
- Docker
- Docker Compose
- JSON

## Datasets Processed

The pipeline currently processes six worksheets from the master Excel workbook:

| Dataset | Input Rows |
|---|---:|
| Employees | 745 |
| Salary Structures | 12,295 |
| Attendance | 150,155 |
| Leave Requests | 3,441 |
| Payroll Runs | 18 |
| Payroll Items | 7,340 |
| **Total** | **173,994** |

The workbook is expected at `data/raw/01_LedgerForge_Python_Master_Dataset.xlsx`.

## Project Structure

PulseIQ_ETL/
|-- contracts/
|   `-- data_contract.json
|-- data/
|   |-- raw/
|   |   |-- master workbook
|   |   `-- sample/
|   |-- clean/
|   `-- rejected/
|-- docs/
|-- logs/
|-- scripts/
|-- src/
|   `-- etl_pipeline/
|-- tests/
|-- requirements.txt
|-- Dockerfile
|-- compose.yaml
`-- README.md
## Setup

Create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```powershell
pip install -r requirements.txt
```

Ensure that the master Excel workbook is available at the expected path before running the pipeline.

## Run Locally

Execute the ETL pipeline using:

```powershell
python -m src.etl_pipeline.pipeline
```

The pipeline extracts the configured worksheets, transforms the data, applies contract validation, saves outputs, and records metrics and logs.

## Run with Docker

Build and run the pipeline using Docker Compose:

```powershell
docker compose up --build
```

The Docker Compose configuration mounts the local data and logs directories so generated outputs and logs remain accessible outside the container.

## Data Contract and Validation

The JSON data contract is maintained in `contracts/data_contract.json`.

The contract defines required columns, unique keys, date columns, non-negative numeric values, and selected dataset-specific rules.

The validation module separates records that violate supported row-level rules into rejected outputs and records the corresponding rejection reasons. Missing required columns or other structural contract problems may cause the pipeline to fail rather than continue with an invalid dataset.

Validation coverage is limited to the rules currently implemented; passing validation does not guarantee that every possible data-quality issue has been detected.

## Output Files

- `data/clean/` — accepted records saved as CSV files.
- `data/rejected/` — rejected records with rejection reasons.
- `logs/etl.log` — pipeline execution and error logs.

The pipeline creates separate clean and rejected output files for each configured dataset.

## ETL Metrics

The pipeline reports the following metrics:

- **Input Rows:** Records extracted before row-level rejection.
- **Clean Rows:** Records accepted by the current validation rules.
- **Rejected Rows:** Records that failed supported row-level checks.
- **Rejection Rate:** Rejected rows divided by input rows, multiplied by 100.
- **Clean Rate:** Clean rows divided by input rows, multiplied by 100.

Metric definitions are documented in `docs/metric_dictionary.md`.

## Automated Tests

Run the test suite using:

```powershell
python -m pytest -v
```

The latest verified test run completed with **5 tests passed**. The tests cover data transformation, invalid employee records, duplicate employee IDs, negative salary amounts, and exact duplicate records.

## Latest Verified Pipeline Run

The latest successful Docker execution processed the six configured worksheets.

| Metric | Result |
|---|---:|
| Total input rows | 173,994 |
| Clean rows | 173,994 |
| Rejected rows | 0 |
| Clean rate | 100% |
| Rejection rate | 0% |

These results reflect the current contract and validation rules. They should not be interpreted as proof that the source data contains no possible quality issues.

## Limitations and Future Improvements

- Expand validation coverage for business-specific rules and cross-dataset relationships.
- Add more automated tests for the data contract and row-level rejection logic.
- Improve rejection reporting and data-quality summaries.
- Add stronger reconciliation checks for payroll and related datasets.
- Extend the pipeline to support additional worksheets and external team CSV exports.
- Improve configuration so workbook paths and processing options can be managed without modifying source code.

## Author

Developed as a data engineering internship project to demonstrate Python-based ETL, data quality validation, automated testing, and containerized execution.
