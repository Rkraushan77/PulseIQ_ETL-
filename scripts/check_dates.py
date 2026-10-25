import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

print("DATE RANGE")
print(con.execute(
    "SELECT MIN(date_key), MAX(date_key), COUNT(*) FROM dim_date"
).df().to_string(index=False))

print("\nLATEST DATES")
print(con.execute(
    "SELECT * FROM dim_date ORDER BY date_key DESC LIMIT 10"
).df().to_string(index=False))

con.close()
