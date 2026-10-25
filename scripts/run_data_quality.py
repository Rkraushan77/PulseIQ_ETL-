
import json
import re
from datetime import datetime
from pathlib import Path

import duckdb


BASE_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BASE_DIR / "config" / "dq_checks_catalog.json"
SQL_PATH = BASE_DIR / "config" / "dq_checks.sql"
WAREHOUSE_PATH = BASE_DIR / "data" / "warehouse.duckdb"


def load_checks():
    with open(CATALOG_PATH, "r", encoding="utf-8") as file:
        catalog = json.load(file)

    sql_text = SQL_PATH.read_text(encoding="utf-8")
    sql_text = re.sub(r"--[^\n]*", "", sql_text)

    queries = [
        query.strip()
        for query in sql_text.split(";")
        if query.strip()
    ]

    checks = catalog["checks"]

    if len(checks) != 14 or len(queries) != 14:
        raise ValueError(
            "Expected 14 catalog checks and 14 SQL queries."
        )

    return checks, queries


def run_checks():
    checks, queries = load_checks()
    con = duckdb.connect(str(WAREHOUSE_PATH))

    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS dq_results (
                check_id VARCHAR,
                check_name VARCHAR,
                target_table VARCHAR,
                severity VARCHAR,
                bad_rows BIGINT,
                status VARCHAR,
                run_time TIMESTAMP
            )
        """)

        run_time = datetime.now()
        results = []

        for check, query in zip(checks, queries):
            bad_rows = len(con.execute(query).fetchall())

            if bad_rows == 0:
                status = "PASS"
            else:
                status = "FAIL"

            results.append({
                "check_id": check["check_id"],
                "check_name": check["name"],
                "target_table": check["table"],
                "severity": check["severity"],
                "bad_rows": bad_rows,
                "status": status,
                "run_time": run_time,
            })

        con.executemany(
            """
            INSERT INTO dq_results
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    result["check_id"],
                    result["check_name"],
                    result["target_table"],
                    result["severity"],
                    result["bad_rows"],
                    result["status"],
                    result["run_time"],
                )
                for result in results
            ],
        )

        print("\nDATA QUALITY SUMMARY")
        print("-" * 65)

        for result in results:
            print(
                f'{result["check_id"]} | '
                f'{result["status"]} | '
                f'Bad rows: {result["bad_rows"]} | '
                f'{result["check_name"]}'
            )

        failed_critical = [
            result for result in results
            if result["status"] == "FAIL"
            and result["severity"] == "CRITICAL"
        ]

        warnings = [
            result for result in results
            if result["status"] == "FAIL"
            and result["severity"] == "WARNING"
        ]

        print("-" * 65)
        print(f'Total checks: {len(results)}')
        print(f'Passed: {sum(r["status"] == "PASS" for r in results)}')
        print(f'Failed: {sum(r["status"] == "FAIL" for r in results)}')
        print(f'Critical failures: {len(failed_critical)}')
        print(f'Warnings: {len(warnings)}')

        if failed_critical:
            raise SystemExit(
                "Critical data-quality checks failed."
            )

    finally:
        con.close()


if __name__ == "__main__":
    run_checks()
