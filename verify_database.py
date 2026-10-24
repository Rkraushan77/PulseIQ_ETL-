import duckdb

connection = duckdb.connect(
    "data/pulseiq.duckdb",
    read_only=True
)

tables = connection.execute("SHOW TABLES").fetchall()

total_rows = 0

for table in tables:
    table_name = table[0]

    query = f'SELECT COUNT(*) FROM "{table_name}"'
    row_count = connection.execute(query).fetchone()[0]

    total_rows = total_rows + row_count

print("Total raw tables:", len(tables))
print("Total raw rows:", total_rows)

connection.close()