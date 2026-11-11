# Task 15: Executive Company Health Scorecard

## Objective
Created a one-page executive scorecard showing eight company-level workforce and payroll KPIs with a reporting month selector, month-on-month comparisons, target information, and links to detailed dashboards.

## Selected KPIs

| KPI | Source metric view | Business reason |
|---|---|---|
| Total Headcount | metric_headcount_monthly | Measures active workforce size. |
| New Hires | metric_hires_monthly | Tracks workforce expansion. |
| Gross Payroll | metric_payroll_monthly | Shows employee earnings before deductions. |
| Net Payroll | metric_payroll_monthly | Shows employee payments after deductions. |
| Employer Payroll Cost | metric_payroll_monthly | Measures total employer payroll expense. |
| Cost Per Paid Employee | metric_payroll_monthly | Measures average employer cost per paid employee. |
| Overtime Share | metric_payroll_monthly | Monitors overtime expense against employer cost. |
| Leave Without Pay Days | metric_payroll_monthly | Tracks unpaid leave recorded through payroll. |

## Target and Status Handling

- Overtime share uses department-level targets from kpi_targets.
- Company-level overtime target is weighted by department employer payroll cost.
- Other selected KPIs display "No target defined".
- No unsupported targets or performance statuses are invented.

## Five Most Important KPIs

1. Total Headcount
2. New Hires
3. Employer Payroll Cost
4. Cost Per Paid Employee
5. Overtime Share

Gross Payroll and Net Payroll were removed because Employer Payroll Cost provides a broader employer-cost measure.

Leave Without Pay Days was removed because it is a supporting operational measure.

## Validation

- Month selector tested.
- Eight KPI cards verified.
- Month-on-month comparisons checked.
- Target and status display checked.
- Detailed page navigation tested.
- A4 landscape print layout tested.

## Evidence

Dashboard screenshot: Executive Company Health Scorecard, September 2026.

## Completion

Task 15 completed.
