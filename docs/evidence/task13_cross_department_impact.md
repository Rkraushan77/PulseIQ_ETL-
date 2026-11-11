# Task 13 - Cross-Department Impact View

## Objective
Combine headcount, payroll, attendance, approved leave and employee exits at department-month grain.

## Reporting period
April 2025 to September 2026.

## Dataset verification
- Total records: 180
- Departments: 10
- Months: 18
- Unique department-month combinations: 180
- Duplicate department-month combinations: 0
- Employee exits: 87

## Aggregation and join approach
Each source was independently aggregated to department-month level before joining to monthly headcount. This prevents row multiplication and incorrect totals.

## Metrics
- Gross pay
- Net pay
- Employer cost
- Overtime cost and hours
- Attendance rate
- Approved leave days
- Leave days per head
- Cost per employee
- Employee exits and monthly exit rate

## Reconciliation
Payroll overtime hours: 9,814
Attendance overtime hours: 9,814
Difference: 0

## Data quality decisions
- Payroll employee-month duplicates: none found in the warehouse.
- Only approved leave on working days was counted.
- Employer cost already includes overtime pay; overtime cost is displayed separately.
- Employee exits were derived from employee exit dates because the available actual attrition metric contained only March 2025.
- Warehouse approved leave total: 7,148 days.
- Earlier CSV validation: 7,164 days.
- Leave reconciliation difference: 16 days; further source investigation required.

## Reference limitation
The PQ-13 reference file and 04_Validation_Vault were not available in the project files or CSV archive. Exact reference reconciliation remains pending.

## Interpretation
The dashboard compares employer cost, overtime cost and employee exit rate by department. A relationship between overtime and exits does not establish causation. Workload, staffing, compensation and management may also influence employee exits.

## Completion
The department-month dataset and Streamlit dashboard were created and syntax-checked successfully.
