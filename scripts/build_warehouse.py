
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = PROJECT_DIR / "data" / "clean"
SOURCE_DB = PROJECT_DIR / "data" / "pulseiq.duckdb"
WAREHOUSE_DB = PROJECT_DIR / "data" / "warehouse.duckdb"
REPORT_DIR = PROJECT_DIR / "data" / "warehouse_reports"

EXPECTED_ROWS = {
    "employees_clean.csv": 745,
    "salary_structures_clean.csv": 12295,
    "attendance_clean.csv": 150155,
    "leave_requests_clean.csv": 3441,
    "payroll_runs_clean.csv": 18,
    "payroll_items_clean.csv": 7340,
}

FACT_FILES = {
    "salary_structures_clean.csv": "fact_salary_structure",
    "attendance_clean.csv": "fact_attendance",
    "leave_requests_clean.csv": "fact_leave",
    "payroll_runs_clean.csv": "fact_payroll_run",
    "payroll_items_clean.csv": "fact_payroll",
}

FACT_MAPPING = {
    "fact_attendance": ("attendance_date", True, False),
    "fact_leave": ("start_date", False, False),
    "fact_salary_structure": ("effective_from", False, False),
    "fact_payroll": ("period_start", True, True),
}

DATE_KEY_COLUMNS = {
    "fact_attendance": ["attendance_date"],
    "fact_leave": ["start_date", "end_date"],
    "fact_payroll": ["period_start", "period_end"],
}


def read_csv(filename):
    return pd.read_csv(CLEAN_DIR / filename)


def check_clean_files():
    print("\nSTEP 1: Checking Task 1 clean files")
    results = []

    for filename, expected in EXPECTED_ROWS.items():
        path = CLEAN_DIR / filename

        if not path.exists():
            raise FileNotFoundError(f"Missing clean file: {path}")

        actual = len(read_csv(filename))
        status = "PASS" if actual == expected else "FAIL"

        results.append({
            "file": filename,
            "expected_rows": expected,
            "actual_rows": actual,
            "status": status,
        })

        print(f"{filename}: {actual:,} rows - {status}")

    report = pd.DataFrame(results)
    report.to_csv(REPORT_DIR / "row_count_check.csv", index=False)

    if (report["status"] != "PASS").any():
        raise ValueError("Task 1 row-count check failed.")


def map_employee_keys(
    warehouse, table_name, date_column, use_department, use_role
):
    """Map fact rows to their historical employee assignment."""

    if table_name == "fact_payroll":
        date_condition = """
            CAST(d.effective_from AS DATE)
                <= CAST(f.period_end AS DATE)
            AND COALESCE(
                CAST(d.effective_to AS DATE),
                DATE '9999-12-31'
            ) >= CAST(f.period_start AS DATE)
        """
    else:
        date_condition = f"""
            CAST(f.{date_column} AS DATE)
                BETWEEN CAST(d.effective_from AS DATE)
                    AND COALESCE(
                        CAST(d.effective_to AS DATE),
                        DATE '9999-12-31'
                    )
        """

    warehouse.execute(f"""
        CREATE OR REPLACE TABLE {table_name}_mapped AS
        SELECT
            f.*,
            e.employee_key
        FROM {table_name} f
        LEFT JOIN LATERAL (
            SELECT d.employee_key
            FROM dim_employee d
            WHERE d.employee_id = f.employee_id
              AND {date_condition}
              {"AND f.department_id = d.department_id" if use_department else ""}
              {"AND f.role_id = d.role_id" if use_role else ""}
            ORDER BY d.effective_from DESC
            LIMIT 1
        ) e ON TRUE
    """)

    unmapped = warehouse.execute(f"""
        SELECT COUNT(*)
        FROM {table_name}_mapped
        WHERE employee_key IS NULL
    """).fetchone()[0]

    warehouse.execute(f"DROP TABLE {table_name}")
    warehouse.execute(
        f"ALTER TABLE {table_name}_mapped RENAME TO {table_name}"
    )

    if unmapped:
        raise ValueError(
            f"{table_name}: {unmapped} rows could not be mapped to "
            "a historical employee assignment."
        )


def add_date_keys(warehouse):
    """Add date dimension keys to the selected fact tables."""

    print("\nSTEP 4B: Adding date dimension keys")

    for table_name, date_columns in DATE_KEY_COLUMNS.items():
        for column in date_columns:
            key_column = f"{column}_key"

            # Drop the column first so the script can be run again safely.
            existing_columns = warehouse.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = ?
            """, [table_name]).fetchdf()["column_name"].tolist()

            if key_column in existing_columns:
                warehouse.execute(
                    f"ALTER TABLE {table_name} DROP COLUMN {key_column}"
                )

            warehouse.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN {key_column} DATE
            """)

            warehouse.execute(f"""
                UPDATE {table_name}
                SET {key_column} = TRY_CAST({column} AS DATE)
            """)

            print(f"{table_name}: added {key_column}")


def check_unique_key(warehouse, table_name, key_column):
    """Check that a candidate primary key is present and unique."""

    null_count = warehouse.execute(f"""
        SELECT COUNT(*) FROM {table_name}
        WHERE {key_column} IS NULL
    """).fetchone()[0]

    duplicate_count = warehouse.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT {key_column}
            FROM {table_name}
            GROUP BY {key_column}
            HAVING COUNT(*) > 1
        ) duplicates
    """).fetchone()[0]

    return {
        "table": table_name,
        "key_column": key_column,
        "null_keys": null_count,
        "duplicate_keys": duplicate_count,
        "status": (
            "PASS"
            if null_count == 0 and duplicate_count == 0
            else "FAIL"
        ),
    }


def check_foreign_key(
    warehouse, fact_table, dimension_table,
    fact_column, dimension_column
):
    """Count missing or unmatched foreign-key references."""

    orphan_count = warehouse.execute(f"""
        SELECT COUNT(*)
        FROM {fact_table} f
        LEFT JOIN {dimension_table} d
          ON f.{fact_column} = d.{dimension_column}
        WHERE f.{fact_column} IS NOT NULL
          AND d.{dimension_column} IS NULL
    """).fetchone()[0]

    null_count = warehouse.execute(f"""
        SELECT COUNT(*)
        FROM {fact_table}
        WHERE {fact_column} IS NULL
    """).fetchone()[0]

    return {
        "fact_table": fact_table,
        "dimension_table": dimension_table,
        "fact_column": fact_column,
        "orphan_rows": orphan_count,
        "null_keys": null_count,
        "status": (
            "PASS"
            if orphan_count == 0 and null_count == 0
            else "FAIL"
        ),
    }


def check_date_key(warehouse, table_name, date_column, key_column):
    """Check date-key completeness and matching with dim_date."""

    result = warehouse.execute(f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT({key_column}) AS populated_keys,
            COUNT(*) FILTER (
                WHERE TRY_CAST({date_column} AS DATE) IS NULL
            ) AS invalid_source_dates,
            COUNT(*) FILTER (
                WHERE {key_column} IS NOT NULL
                  AND d.date_key IS NULL
            ) AS orphan_date_keys,
            COUNT(*) FILTER (
                WHERE TRY_CAST({date_column} AS DATE) IS DISTINCT FROM
                      {key_column}
            ) AS mismatched_keys
        FROM {table_name} f
        LEFT JOIN dim_date d
            ON f.{key_column} = d.date_key
    """).fetchdf().iloc[0]

    passed = (
        result["total_rows"] == result["populated_keys"]
        and result["invalid_source_dates"] == 0
        and result["orphan_date_keys"] == 0
        and result["mismatched_keys"] == 0
    )

    return {
        "table": table_name,
        "date_column": date_column,
        "key_column": key_column,
        "total_rows": int(result["total_rows"]),
        "populated_keys": int(result["populated_keys"]),
        "invalid_source_dates": int(result["invalid_source_dates"]),
        "orphan_date_keys": int(result["orphan_date_keys"]),
        "mismatched_keys": int(result["mismatched_keys"]),
        "status": "PASS" if passed else "FAIL",
    }


def build_warehouse():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found: {SOURCE_DB}"
        )

    check_clean_files()

    source = duckdb.connect(str(SOURCE_DB), read_only=True)
    warehouse = duckdb.connect(str(WAREHOUSE_DB))

    try:
        print("\nSTEP 2: Creating dimensions")

        assignments = source.execute("""
            SELECT
                assignment_id,
                employee_id,
                CAST(effective_from AS DATE) AS effective_from,
                CAST(effective_to AS DATE) AS effective_to,
                department_id,
                role_id,
                job_level,
                manager_id,
                change_reason
            FROM raw_employee_assignments
        """).fetchdf()

        employees = read_csv("employees_clean.csv")

        departments = source.execute("""
            SELECT department_id, department_name, cost_center
            FROM raw_departments
        """).fetchdf()

        roles = source.execute("""
            SELECT role_id, department_id, role_title, level, grade
            FROM raw_roles
        """).fetchdf()

        leave_types = source.execute("""
            SELECT leave_type_code, leave_type_name
            FROM raw_leave_types
        """).fetchdf()

        employee_dim = assignments.merge(
            employees.drop(
                columns=["department_id", "role_id", "manager_id"],
                errors="ignore",
            ),
            on="employee_id",
            how="left",
            validate="many_to_one",
        )

        employee_dim = employee_dim.sort_values(
            ["employee_id", "effective_from", "assignment_id"]
        ).reset_index(drop=True)

        employee_dim.insert(
            0, "employee_key", range(1, len(employee_dim) + 1)
        )

        employee_dim["is_current"] = employee_dim["effective_to"].isna()

        if employee_dim["full_name"].isna().any():
            raise ValueError(
                "Some assignments have no matching employee."
            )

        dimensions = {
            "dim_employee": employee_dim,
            "dim_department": departments,
            "dim_role": roles,
            "dim_leave_type": leave_types,
        }

        for table_name, data in dimensions.items():
            warehouse.register("dimension_df", data)
            warehouse.execute(
                f"CREATE OR REPLACE TABLE {table_name} "
                "AS SELECT * FROM dimension_df"
            )
            warehouse.unregister("dimension_df")

        # Build the calendar from the dates in the clean files.
        all_dates = []

        for filename in EXPECTED_ROWS:
            data = read_csv(filename)

            for column in data.columns:
                if (
                    column.endswith("_date")
                    or column in [
                        "attendance_date",
                        "start_date",
                        "end_date",
                        "effective_from",
                        "effective_to",
                        "period_start",
                        "period_end",
                        "pay_date",
                    ]
                ):
                    parsed = pd.to_datetime(
                        data[column], errors="coerce"
                    )
                    all_dates.extend(
                        parsed.dropna().dt.normalize().tolist()
                    )

        if not all_dates:
            raise ValueError("No valid dates found for dim_date.")

        calendar = pd.DataFrame({
            "date_key": pd.date_range(
                min(all_dates), max(all_dates), freq="D"
            )
        })

        calendar["date_key"] = calendar["date_key"].dt.date
        calendar["year"] = pd.to_datetime(
            calendar["date_key"]
        ).dt.year
        calendar["month"] = pd.to_datetime(
            calendar["date_key"]
        ).dt.month
        calendar["quarter"] = pd.to_datetime(
            calendar["date_key"]
        ).dt.quarter

        warehouse.register("calendar_df", calendar)
        warehouse.execute("""
            CREATE OR REPLACE TABLE dim_date AS
            SELECT * FROM calendar_df
        """)
        warehouse.unregister("calendar_df")

        print("Dimension tables created.")

        print("\nSTEP 3: Creating fact tables")

        for filename, table_name in FACT_FILES.items():
            data = read_csv(filename)

            for column in ["effective_from", "effective_to"]:
                if column in data.columns:
                    data[column] = pd.to_datetime(
                        data[column], errors="coerce"
                    ).dt.date

            warehouse.register("fact_data_df", data)
            warehouse.execute(
                f"CREATE OR REPLACE TABLE {table_name} "
                "AS SELECT * FROM fact_data_df"
            )
            warehouse.unregister("fact_data_df")

        warehouse.execute("""
            CREATE OR REPLACE TABLE source_employees AS
            SELECT * FROM read_csv_auto(?)
        """, [str(CLEAN_DIR / "employees_clean.csv")])

        print("\nSTEP 4: Mapping historical employee keys")

        for table_name, (
            date_column, use_department, use_role
        ) in FACT_MAPPING.items():
            print(f"Mapping {table_name} using {date_column}...")

            map_employee_keys(
                warehouse,
                table_name,
                date_column,
                use_department,
                use_role,
            )

        add_date_keys(warehouse)

        print("\nSTEP 5: Checking row counts")

        reconciliation = []

        for filename, expected in EXPECTED_ROWS.items():
            table_name = {
                "employees_clean.csv": "source_employees",
                **FACT_FILES,
            }[filename]

            actual = warehouse.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            reconciliation.append({
                "source_file": filename,
                "warehouse_table": table_name,
                "expected_rows": expected,
                "actual_rows": actual,
                "status": "PASS" if expected == actual else "FAIL",
            })

        reconciliation_df = pd.DataFrame(reconciliation)
        reconciliation_df.to_csv(
            REPORT_DIR / "warehouse_reconciliation.csv",
            index=False,
        )
        print(reconciliation_df.to_string(index=False))

        print("\nSTEP 6: Checking primary-key candidates")

        key_candidates = [
            ("dim_employee", "employee_key"),
            ("dim_department", "department_id"),
            ("dim_role", "role_id"),
            ("dim_leave_type", "leave_type_code"),
            ("dim_date", "date_key"),
            ("fact_attendance", "attendance_id"),
            ("fact_leave", "leave_request_id"),
            ("fact_salary_structure", "structure_id"),
            ("fact_payroll", "payroll_item_id"),
            ("fact_payroll_run", "run_id"),
        ]

        key_report = pd.DataFrame([
            check_unique_key(warehouse, table, column)
            for table, column in key_candidates
        ])

        key_report.to_csv(
            REPORT_DIR / "key_check.csv", index=False
        )
        print(key_report.to_string(index=False))

        print("\nSTEP 7: Checking foreign-key references")

        foreign_keys = [
            ("fact_attendance", "dim_employee",
             "employee_key", "employee_key"),
            ("fact_leave", "dim_employee",
             "employee_key", "employee_key"),
            ("fact_salary_structure", "dim_employee",
             "employee_key", "employee_key"),
            ("fact_payroll", "dim_employee",
             "employee_key", "employee_key"),
            ("dim_employee", "source_employees",
             "employee_id", "employee_id"),
            ("dim_employee", "dim_department",
             "department_id", "department_id"),
            ("dim_employee", "dim_role",
             "role_id", "role_id"),
            ("fact_leave", "dim_leave_type",
             "leave_type_code", "leave_type_code"),
            ("fact_payroll", "fact_payroll_run",
             "run_id", "run_id"),
        ]

        fk_report = pd.DataFrame([
            check_foreign_key(warehouse, *fk)
            for fk in foreign_keys
        ])

        fk_report.to_csv(
            REPORT_DIR / "orphan_check.csv", index=False
        )
        print(fk_report.to_string(index=False))

        print("\nSTEP 8: Checking date dimension keys")

        date_results = []

        for table_name, date_columns in DATE_KEY_COLUMNS.items():
            for column in date_columns:
                date_results.append(
                    check_date_key(
                        warehouse,
                        table_name,
                        column,
                        f"{column}_key",
                    )
                )

        date_report = pd.DataFrame(date_results)
        date_report.to_csv(
            REPORT_DIR / "date_key_check.csv", index=False
        )
        print(date_report.to_string(index=False))

        failed = (
            (reconciliation_df["status"] != "PASS").any()
            or (key_report["status"] != "PASS").any()
            or (fk_report["status"] != "PASS").any()
            or (date_report["status"] != "PASS").any()
        )

        if failed:
            raise ValueError(
                "One or more warehouse validations failed. "
                "Review reports in data/warehouse_reports."
            )

        print("\nAll warehouse validations passed.")
        print(f"Warehouse database: {WAREHOUSE_DB}")
        print(f"Reports folder: {REPORT_DIR}")

    finally:
        warehouse.close()
        source.close()


if __name__ == "__main__":
    build_warehouse()
