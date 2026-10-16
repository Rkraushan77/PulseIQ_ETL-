# PulseIQ ETL - Metric Dictionary

## Purpose
This document defines the five operational metrics reported by the ETL pipeline.

| No. | Metric Name | Definition | Formula | Example |
|---|---|---|---|---|
| 1 | Input Rows | Number of records entering the transformation and validation stage. | Number of input records | 10 |
| 2 | Clean Rows | Number of records that pass validation and are saved to the clean output. | Count of valid records | 10 |
| 3 | Rejected Rows | Number of records that fail validation and are saved separately with a rejection reason. | Count of invalid records | 0 |
| 4 | Rejection Rate (%) | Percentage of records rejected by validation. | (Rejected Rows / Input Rows) * 100 | 0% |
| 5 | Clean Rate (%) | Percentage of records accepted by validation. | (Clean Rows / Input Rows) * 100 | 100% |

## Notes
- These are ETL quality and processing metrics, not business performance KPIs.
- If Input Rows is zero, both rates are reported as 0%.
- Rejected records should retain a rejection reason for troubleshooting.
- Input Rows should represent the original number of extracted records before duplicate removal.
