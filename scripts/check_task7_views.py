
import duckdb

# Connect to the warehouse in read-only mode
con = duckdb.connect(
    "data/warehouse.duckdb",
    read_only=True
)

# Check whether the new attrition view exists
print("Checking metric_attrition_actual...")

view_exists = con.execute("""
    SELECT COUNT(*)
    FROM information_schema.views
    WHERE table_name = 'metric_attrition_actual'
""").fetchone()[0]

if view_exists == 1:
    print("View exists.")

    # Display the first 10 rows
    result = con.execute("""
        SELECT *
        FROM metric_attrition_actual
        ORDER BY month_start
        LIMIT 10
    """).fetchdf()

    print("\nActual attrition metrics:")
    print(result.to_string(index=False))
else:
    print("View not found.")

con.close()
