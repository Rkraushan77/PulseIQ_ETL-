
from pathlib import Path
import re
import duckdb


def save_data(df, folder, file_name):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    file_path = folder / file_name
    df.to_csv(file_path, index=False)

    print(f"Saved {len(df)} rows to {file_path}")


def load_to_duckdb(data, database_path):
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(database_path))

    try:
        for sheet_name, df in data.items():
            table_name = "raw_" + re.sub(
                r"[^a-zA-Z0-9_]",
                "_",
                sheet_name.lower(),
            )

            # Use a separate cursor for this sheet.
            cursor = connection.cursor()

            try:
                cursor.register("incoming_data", df)

                cursor.execute(
                    f'CREATE OR REPLACE TABLE "{table_name}" '
                    "AS SELECT * FROM incoming_data"
                ).fetchall()

                cursor.unregister("incoming_data")

                result = cursor.execute(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).fetchall()

                row_count = result[0][0]

                print(
                    f"DuckDB table {table_name}: "
                    f"{row_count} rows"
                )

            finally:
                cursor.close()

    finally:
        connection.close()
