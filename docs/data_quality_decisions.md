# Task 3: Data Quality Severity Decisions

## 1. Purpose

This document explains which data-quality checks should stop the data load and which checks should generate warnings. The purpose is to prevent unreliable data from entering the warehouse while allowing non-critical issues to be reviewed.

## 2. Critical Checks

Critical checks stop the load when they fail because they can affect data integrity, relationships, salary calculations, or payroll reporting.

| Check ID | Check | Reason |
|---|---|---|
| DQ01 | Employee ID is missing | Records cannot be reliably identified. |
| DQ02 | Employee ID is duplicated | Duplicate employee records can cause incorrect reporting. |
| DQ03 | Exit date precedes hire date | The employee timeline is invalid. |
| DQ05 | Salary structure ID is duplicated | Duplicate records can distort salary analysis. |
| DQ06 | Salary amount is negative | Negative salary components may cause incorrect calculations. |
| DQ07 | Attendance ID is duplicated | Duplicate attendance records can distort attendance metrics. |
| DQ10 | Leave end date precedes start date | The leave period is invalid. |
| DQ11 | Leave request ID is duplicated | Duplicate requests can distort leave reporting. |
| DQ12 | Payroll period dates are invalid | An invalid payroll period can affect payroll reporting. |
| DQ13 | Payroll item ID is duplicated | Duplicate payroll items can distort payment totals. |
| DQ14 | Payroll net pay does not reconcile | Incorrect payroll arithmetic can result in unreliable payroll figures. |

## 3. Warning Checks

Warning checks flag issues for review without automatically stopping the load. They should be monitored because repeated issues may indicate a wider data problem.

| Check ID | Check | Reason |
|---|---|---|
| DQ04 | Employment status is invalid | The record needs review, but the issue may be corrected without blocking unrelated data. |
| DQ08 | Attendance status is invalid | The attendance record needs investigation before it is used for reporting. |
| DQ09 | Overtime hours are negative | The value is suspicious and should be reviewed. |

## 4. Decision Rules

1. A critical check that detects bad rows must stop the load.
2. A warning check should be recorded in the data-quality results and reported for review.
3. Every check must record its ID, target table, bad-row count, status, and run time.
4. Failed checks must be investigated and corrected at the source or through an approved cleaning rule.
5. The failure-test script must demonstrate that each check detects its intended issue.
6. Severity assignments should be reviewed against the official dq_checks_catalog when that file is available.

## 5. Current Test Evidence

The current warehouse build completed successfully, and all 14 data-quality checks passed on the existing dataset with zero bad rows.

The failure-injection test also passed all 14 checks. Duplicate-key checks reported two affected rows because both the original record and its duplicate were detected.

The current failure tests use transactions that are rolled back. A separate copied-table test should be retained as evidence if the assignment specifically requires testing against a copy.

## 6. Limitation

The original dq_checks_catalog and the unlock_PQ-03 file from 04_Validation_Vault have not yet been provided or located. Therefore, these severity decisions and checks are proposed based on the available warehouse schema and must be compared with the official assignment materials before final submission.
