
import duckdb

connection = duckdb.connect(
    "data/warehouse.duckdb",
    read_only=True,
)

print("HOLIDAY TABLE:")
print(connection.execute("""
    SELECT holiday_date, holiday_name, holiday_type
    FROM dim_holiday
    ORDER BY holiday_date
""").fetchdf().to_string(index=False))

print("\nDATE DIMENSION COLUMNS:")
print(connection.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'dim_date'
""").fetchdf().to_string(index=False))

print("\nHOLIDAY FLAG COUNTS:")
print(connection.execute("""
    SELECT is_holiday, COUNT(*) AS dates
    FROM dim_date
    GROUP BY is_holiday
    ORDER BY is_holiday
""").fetchdf().to_string(index=False))

connection.close()
