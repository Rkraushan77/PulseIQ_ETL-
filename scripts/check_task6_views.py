
import duckdb

con = duckdb.connect(
    "data/warehouse.duckdb",
    read_only=True
)

query = """
SELECT
    month_start,
    leave_type_code,
    leave_type_name,
    approved_leave_days,
    approved_requests
FROM metric_leave_trends
ORDER BY month_start, leave_type_code
LIMIT 20
"""

result = con.execute(query).fetchdf()

print("\nMonthly leave metrics:")
print(result.to_string(index=False))

con.close()
