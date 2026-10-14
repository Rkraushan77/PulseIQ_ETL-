# PulseIQ — Workforce Analytics and Data Pipeline

## Project Overview

PulseIQ is a Python-based data project built around the fictional company Zenith Nova Technologies. The project uses employee, department, payroll, attendance, and accounting data to support workforce and financial operations.

## Technology Stack

- Python
- Pandas
- OpenPyXL
- Git and GitHub
- Docker

## Dataset

The source workbook is stored locally at:

`data/raw/01_LedgerForge_Python_Master_Dataset.xlsx`

The dataset contains fictional company data for educational and development purposes.

## Task 1 Progress

- Created the project structure.
- Inspected the source workbook and its sheets.
- Exported the first 10 employee records to `employees_sample.csv`.
- Exported department records to `departments_sample.csv`.
- Verified that both sample CSV files were created successfully.

## Run the Sample Export

Activate the virtual environment and run:

`python scripts/create_sample_data.py`

## Data and Privacy

The source workbook and generated datasets are local development files. They should not be committed to the Git repository unless explicitly required and approved.