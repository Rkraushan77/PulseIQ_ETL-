import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

query = """
SELECT
    COUNT(*) AS missing_end_dates
FROM fact_leave f
LEFT JOIN dim_date d
    ON TRY_CAST(f.end_date AS DATE) = d.date_key
WHERE d.date_key IS NULL
"""

print("Leave end-date check:")
print(con.execute(query).fetchdf().to_string(index=False))

con.close()