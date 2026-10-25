from pathlib import Path

path = Path("config/metric_views.sql")
sql = path.read_text(encoding="utf-8-sig")

start = sql.index("CREATE OR REPLACE VIEW metric_headcount_monthly AS")
end = sql.index("CREATE OR REPLACE VIEW metric_hires_monthly AS")

replacement = """CREATE OR REPLACE VIEW metric_headcount_monthly AS
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

"""

path.write_text(sql[:start] + replacement + sql[end:], encoding="utf-8")
print("Updated metric_headcount_monthly in config/metric_views.sql")
