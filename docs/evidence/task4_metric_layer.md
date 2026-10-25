# PulseIQ Task 4 — Governed Metric Layer Evidence

## 1. Objective
Create reusable SQL metric views and a catalog containing the official 28 metrics.

## 2. Verification results

| Check | Result |
|---|---|
| Official metrics registered | 28 |
| Latest headcount reporting month | 2026-09-30 |
| Department-month headcount rows | 1,250 |
| SQL file execution | Passed |

Verification was run against `data/warehouse.duckdb` using `config/metric_views.sql`.

## 3. Implemented views

- `metric_headcount_monthly`: active employee count at calendar month-end, grouped by department.
- `metric_hires_monthly`: employee hires grouped by month and department.
- `metric_exits_monthly`: employee exits grouped by month and department.
- `metric_payroll_monthly`: gross pay, net pay, employer cost, overtime pay, variable pay, LOP days and paid employee counts.
- `metric_attendance_monthly`: attendance record counts, present-record proxy, late-record counts and overtime hours.
- `metric_catalog`: definitions, source tables, reporting grain, owner, privacy threshold and implementation status for all 28 metrics.

## 4. Metrics requiring further work

- M04-M06: monthly and rolling attrition need opening headcount, rolling calculations and validated exit-type logic.
- M13-M14: official attendance formulas require scheduled-day and present-day definitions.
- M16-M21: ledger and/or invoice tables are unavailable in the current warehouse.
- M22-M25: task-management data is unavailable.
- M26-M28: anomaly, risk and forecast source tables are unavailable.

These metrics must not be presented as calculated results until their required sources and formulas are implemented.

## 5. Attrition denominator decision

For monthly attrition, use:

Monthly attrition rate = monthly exits / opening headcount * 100

For rolling 12-month attrition, use:

Rolling 12-month attrition rate = exits during the previous 12 months / average month-end headcount over those 12 months * 100

Keep these as separate measures. Do not substitute closing headcount for opening headcount in the monthly formula.

## 6. Privacy and validation notes

The headcount, hires, exits, payroll and attendance views currently apply minimum-group filters in SQL. Confirm that each filter matches the official metric dictionary before release. In particular, the exits view currently applies a five-employee threshold although the catalog does not specify one for M03.

The attendance view provides record-level aggregates, not the official scheduled-day-based attendance rate. Do not label its proxy counts as the official M13 or M14 rates.

## 7. Evidence limitations

The verification confirms SQL execution, the latest headcount month, row count and catalog count. Independent hand-calculations for five metrics and all 28 reusable metric views have not yet been evidenced.
