import duckdb

con = duckdb.connect("data/warehouse.duckdb")

con.execute("""
CREATE OR REPLACE VIEW metric_headcount_monthly AS
WITH months AS (
    SELECT DISTINCT
        DATE_TRUNC('month', date_key)::DATE AS month_start,
        (DATE_TRUNC('month', date_key) + INTERVAL '1 month'
          - INTERVAL '1 day')::DATE AS month_end
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
WHERE headcount >= 5
""")

print(con.execute("""
SELECT MAX(month_end) AS latest_reporting_month,
       COUNT(*) AS department_month_rows
FROM metric_headcount_monthly
""").df().to_string(index=False))

con.close()
