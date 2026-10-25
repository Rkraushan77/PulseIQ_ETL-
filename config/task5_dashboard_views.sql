-- Task 5: Corrected dashboard views

CREATE OR REPLACE VIEW metric_dashboard_headcount AS
WITH months AS (
    SELECT DISTINCT
        CAST(date_trunc('month', date_key) + INTERVAL '1 month'
             - INTERVAL '1 day' AS DATE) AS month_end
    FROM dim_date
    WHERE date_key >= DATE '2025-04-01'
      AND date_key <= DATE '2026-09-30'
),
active_assignments AS (
    SELECT
        m.month_end,
        e.employee_id,
        e.department_id
    FROM months m
    JOIN dim_employee e
      ON TRY_CAST(e.hire_date AS DATE) <= m.month_end
     AND (
          TRY_CAST(e.exit_date AS DATE) IS NULL
          OR TRY_CAST(e.exit_date AS DATE) > m.month_end
     )
     AND TRY_CAST(e.effective_from AS DATE) <= m.month_end
     AND (
          e.effective_to IS NULL
          OR TRY_CAST(e.effective_to AS DATE) > m.month_end
     )
)
SELECT
    month_end,
    department_id,
    COUNT(DISTINCT employee_id) AS headcount
FROM active_assignments
GROUP BY month_end, department_id;

CREATE OR REPLACE VIEW metric_dashboard_department AS
SELECT
    d.department_id,
    d.department_name,
    h.headcount
FROM metric_dashboard_headcount h
JOIN dim_department d
    ON h.department_id = d.department_id
WHERE h.month_end = (
    SELECT MAX(month_end)
    FROM metric_dashboard_headcount
);

CREATE OR REPLACE VIEW metric_dashboard_location AS
SELECT
    work_location,
    COUNT(DISTINCT employee_id) AS employees
FROM dim_employee
WHERE is_current = TRUE
GROUP BY work_location;

CREATE OR REPLACE VIEW metric_dashboard_work_mode AS
SELECT
    COALESCE(NULLIF(TRIM(work_mode), ''), 'Unknown') AS work_mode,
    COUNT(DISTINCT employee_id) AS employees
FROM dim_employee
WHERE is_current = TRUE
GROUP BY 1;
