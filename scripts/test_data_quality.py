
import re
import shutil
from pathlib import Path

import duckdb


BASE_DIR = Path(__file__).resolve().parents[1]
WAREHOUSE_PATH = BASE_DIR / "data" / "warehouse.duckdb"
TEST_WAREHOUSE_PATH = BASE_DIR / "data" / "warehouse_dq_test.duckdb"
SQL_PATH = BASE_DIR / "config" / "dq_checks.sql"


def load_queries():
    sql_text = SQL_PATH.read_text(encoding="utf-8")
    sql_text = re.sub(r"--[^\n]*", "", sql_text)

    return [
        query.strip()
        for query in sql_text.split(";")
        if query.strip()
    ]


def test_data_quality():
    queries = load_queries()

    bad_data_sql = [
        "INSERT INTO source_employees (employee_id) VALUES (NULL)",
        "INSERT INTO source_employees SELECT * FROM source_employees LIMIT 1",
        """INSERT INTO source_employees
           (employee_id, hire_date, exit_date)
           VALUES ('DQ_TEST_EMP', DATE '2026-01-02', DATE '2026-01-01')""",
        """INSERT INTO source_employees
           (employee_id, employment_status)
           VALUES ('DQ_TEST_EMP', 'INVALID_STATUS')""",
        "INSERT INTO fact_salary_structure SELECT * FROM fact_salary_structure LIMIT 1",
        """INSERT INTO fact_salary_structure
           (structure_id, monthly_amount)
           VALUES ('DQ_TEST_SALARY', -1)""",
        "INSERT INTO fact_attendance SELECT * FROM fact_attendance LIMIT 1",
        """INSERT INTO fact_attendance
           (attendance_id, status)
           VALUES ('DQ_TEST_ATT', 'INVALID_STATUS')""",
        """INSERT INTO fact_attendance
           (attendance_id, overtime_hours)
           VALUES ('DQ_TEST_ATT', -1)""",
        """INSERT INTO fact_leave
           (leave_request_id, start_date, end_date)
           VALUES ('DQ_TEST_LEAVE', DATE '2026-01-10', DATE '2026-01-05')""",
        "INSERT INTO fact_leave SELECT * FROM fact_leave LIMIT 1",
        """INSERT INTO fact_payroll_run
           (run_id, period_start, period_end)
           VALUES ('DQ_TEST_RUN', DATE '2026-02-01', DATE '2026-01-01')""",
        "INSERT INTO fact_payroll SELECT * FROM fact_payroll LIMIT 1",
        """INSERT INTO fact_payroll
           (payroll_item_id, gross_pay, total_deductions, net_pay)
           VALUES ('DQ_TEST_PAY', 100, 20, 99)""",
    ]

    if len(queries) != 14:
        raise ValueError("Expected exactly 14 SQL checks.")

    # Run failure tests against a separate copy of the warehouse.
    if TEST_WAREHOUSE_PATH.exists():
        TEST_WAREHOUSE_PATH.unlink()
    shutil.copy2(WAREHOUSE_PATH, TEST_WAREHOUSE_PATH)
    con = duckdb.connect(str(TEST_WAREHOUSE_PATH))

    passed = 0

    try:
        print("\nDATA QUALITY FAILURE TESTS")
        print("-" * 65)

        for number, (query, insert_sql) in enumerate(
            zip(queries, bad_data_sql), start=1
        ):
            con.execute("BEGIN TRANSACTION")

            try:
                con.execute(insert_sql)
                bad_rows = len(con.execute(query).fetchall())

                if bad_rows > 0:
                    print(
                        f"DQ{number:02d} | PASS | "
                        f"Detected {bad_rows} bad row(s)"
                    )
                    passed += 1
                else:
                    print(
                        f"DQ{number:02d} | FAIL | "
                        "Bad row was not detected"
                    )

            finally:
                con.execute("ROLLBACK")

        print("-" * 65)
        print(f"Tests passed: {passed}/14")
        print(f"Tests failed: {14 - passed}/14")

        if passed != 14:
            raise SystemExit("Some data quality checks need fixing.")

    finally:
        con.close()
        if TEST_WAREHOUSE_PATH.exists():
            TEST_WAREHOUSE_PATH.unlink()
        test_wal = Path(str(TEST_WAREHOUSE_PATH) + ".wal")
        if test_wal.exists():
            test_wal.unlink()



if __name__ == "__main__":
    test_data_quality()

