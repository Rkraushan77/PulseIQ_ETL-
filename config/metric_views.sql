-- PulseIQ Task 4: Governed Metric Layer
-- Sources: existing DuckDB warehouse tables.
-- Unsupported metrics must not be reported as calculated values.

CREATE OR REPLACE VIEW metric_headcount_monthly AS
WITH months AS (
    SELECT DISTINCT
        DATE_TRUNC('month', date_key)::DATE AS month_start,
        (DATE_TRUNC('month', date_key)
          + INTERVAL '1 month' - INTERVAL '1 day')::DATE AS month_end
    FROM dim_date
    WHERE date_key <= DATE '2026-09-30'
),
headcounts AS (
    SELECT
        m.month_end,
        e.department_id,
        COUNT(DISTINCT e.employee_id) AS headcount
    FROM months m
    JOIN dim_employee e
      ON TRY_CAST(e.hire_date AS DATE) <= m.month_end
     AND (
          TRY_CAST(e.exit_date AS DATE) IS NULL
          OR TRY_CAST(e.exit_date AS DATE) > m.month_end
     )
    GROUP BY m.month_end, e.department_id
)
SELECT *
FROM headcounts
WHERE headcount >= 5;

CREATE OR REPLACE VIEW metric_hires_monthly AS
SELECT
    DATE_TRUNC('month', TRY_CAST(hire_date AS DATE))::DATE AS month_start,
    department_id,
    COUNT(DISTINCT employee_id) AS hires
FROM source_employees
WHERE TRY_CAST(hire_date AS DATE) IS NOT NULL
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW metric_exits_monthly AS
SELECT
    DATE_TRUNC('month', TRY_CAST(exit_date AS DATE))::DATE AS month_start,
    department_id,
    COUNT(DISTINCT employee_id) AS exits
FROM source_employees
WHERE TRY_CAST(exit_date AS DATE) IS NOT NULL
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW metric_payroll_monthly AS
SELECT
    TRY_CAST(period_start AS DATE) AS period_start,
    department_id,
    SUM(gross_pay) AS gross_pay,
    SUM(net_pay) AS net_pay,
    SUM(employer_cost) AS employer_cost,
    SUM(overtime_pay) AS overtime_pay,
    SUM(variable_pay) AS variable_pay,
    SUM(lop_days) AS lop_days,
    COUNT(DISTINCT employee_id) AS paid_employees
FROM fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW metric_attendance_monthly AS
SELECT
    DATE_TRUNC('month', TRY_CAST(attendance_date AS DATE))::DATE AS month_start,
    department_id,
    COUNT(DISTINCT employee_id) AS employees,
    COUNT(*) AS attendance_records,
    SUM(CASE WHEN LOWER(status) IN ('present', 'half_day') THEN 1 ELSE 0 END) AS present_records,
    SUM(CASE WHEN LOWER(CAST(late_flag AS VARCHAR)) IN ('yes', 'true', '1', 'y') THEN 1 ELSE 0 END) AS late_records,
    SUM(COALESCE(overtime_hours, 0)) AS overtime_hours
FROM fact_attendance
WHERE TRY_CAST(attendance_date AS DATE) IS NOT NULL
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW metric_catalog AS
SELECT * FROM (VALUES
('M01','Headcount','Active employees at month end','fact_headcount_monthly / dim_employee','Department x month','HR Analytics',5,'IMPLEMENTED'),
('M02','Hires','Employees hired during month','fact_headcount_monthly / source_employees','Department x month','HR Analytics',5,'IMPLEMENTED'),
('M03','Exits','Employees whose exit date falls in month','fact_headcount_monthly / source_employees','Department x month','HR Analytics',NULL,'IMPLEMENTED'),
('M04','Attrition rate (monthly)','Monthly exits divided by opening headcount x 100','fact_headcount_monthly','Department x month','HR Analytics',10,'NEEDS OPENING HEADCOUNT VIEW'),
('M05','Attrition rate (rolling 12 months)','12-month exits divided by average month-end headcount x 100','fact_headcount_monthly','Department x month','HR Analytics',10,'NEEDS 12-MONTH ROLLING VIEW'),
('M06','Voluntary attrition rate','12-month voluntary exits divided by average headcount x 100','fact_headcount_monthly','Department x month','HR Analytics',10,'NEEDS EXIT TYPE VALIDATION'),
('M07','Gross pay','Sum of gross pay','fact_payroll','Employee x month','Payroll',5,'IMPLEMENTED'),
('M08','Net pay','Sum of net pay','fact_payroll','Employee x month','Payroll',5,'IMPLEMENTED'),
('M09','Payroll cost (employer cost)','Sum of employer cost','fact_payroll','Employee x month','Finance',5,'IMPLEMENTED'),
('M10','Cost per head','Employer cost divided by distinct paid employees','fact_payroll','Department x month','Finance',5,'IMPLEMENTED'),
('M11','Overtime share','Overtime pay divided by employer cost x 100','fact_payroll','Department x month','Payroll',5,'IMPLEMENTED'),
('M12','Variable pay share','Variable pay divided by gross pay x 100','fact_payroll','Department x month','Payroll',5,'IMPLEMENTED'),
('M13','Attendance rate','Present days adjusted for half days divided by scheduled days','fact_attendance_monthly','Department x month','HR Analytics',5,'NEEDS SCHEDULED-DAY DEFINITION'),
('M14','Late arrival rate','Late check-ins divided by present days','fact_attendance_monthly','Department x month','HR Analytics',5,'NEEDS PRESENT-DAY MAPPING'),
('M15','Leave without pay days','Sum of payroll LOP days','fact_payroll','Employee x month','Payroll',5,'IMPLEMENTED'),
('M16','Revenue','Negative sum of ledger signed amounts for accounts 4001-4004','fact_ledger','Account x month','Finance',NULL,'BLOCKED: LEDGER TABLE MISSING'),
('M17','Net profit','Revenue minus expenses','fact_ledger','Month','Finance',NULL,'BLOCKED: LEDGER TABLE MISSING'),
('M18','Operating margin','Net profit divided by revenue x 100','fact_ledger','Month','Finance',NULL,'BLOCKED: LEDGER TABLE MISSING'),
('M19','Payroll as % of revenue','Ledger payroll cost divided by revenue x 100','fact_payroll + fact_ledger','Month','Finance',NULL,'BLOCKED: LEDGER TABLE MISSING'),
('M20','Days sales outstanding (DSO)','Closing receivables divided by 90-day credit sales x 90','fact_invoice / fact_ledger','Month','Finance',NULL,'BLOCKED: INVOICE AND LEDGER TABLES MISSING'),
('M21','Overdue receivables','Unpaid overdue invoice balance','fact_invoice','Client x date','Finance',NULL,'BLOCKED: INVOICE TABLE MISSING'),
('M22','Task completion rate','Done tasks divided by non-cancelled tasks','fact_task','Team x sprint','Engineering Ops',5,'BLOCKED: TASK TABLE MISSING'),
('M23','On-time delivery rate','On-time completed tasks divided by done tasks','fact_task','Team x sprint','Engineering Ops',NULL,'BLOCKED: TASK TABLE MISSING'),
('M24','Velocity','Story points completed','fact_task','Team x sprint','Engineering Ops',NULL,'BLOCKED: TASK TABLE MISSING'),
('M25','Average cycle time','Average days from task start to completion','fact_task','Team x sprint','Engineering Ops',5,'BLOCKED: TASK TABLE MISSING'),
('M26','Anomaly flag rate','Flagged records divided by scored records','fact_anomaly','Source x month','AI/ML',NULL,'BLOCKED: ANOMALY TABLE MISSING'),
('M27','High-risk share','High-risk employees divided by scored employees','fact_attrition_risk','Department','AI/ML',10,'BLOCKED: RISK TABLE MISSING'),
('M28','Forecast error (MAPE)','Average absolute percentage forecast error','fact_forecast / fact_headcount','Department x month','AI/ML',NULL,'BLOCKED: FORECAST TABLE MISSING')
) AS t(metric_id, metric_name, business_definition, source_table, grain, owner_team, minimum_group_size, implementation_status);

