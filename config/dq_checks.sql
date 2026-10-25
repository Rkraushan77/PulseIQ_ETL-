
-- DQ01: Employee ID is missing
SELECT *
FROM source_employees
WHERE employee_id IS NULL
   OR TRIM(employee_id) = '';

-- DQ02: Employee ID is duplicated
SELECT *
FROM source_employees
WHERE employee_id IN (
    SELECT employee_id
    FROM source_employees
    WHERE employee_id IS NOT NULL
    GROUP BY employee_id
    HAVING COUNT(*) > 1
);

-- DQ03: Exit date is before hire date
SELECT *
FROM source_employees
WHERE hire_date IS NOT NULL
  AND exit_date IS NOT NULL
  AND exit_date < hire_date;

-- DQ04: Employment status is outside the observed values
SELECT *
FROM source_employees
WHERE employment_status IS NULL
   OR TRIM(employment_status) = ''
   OR employment_status NOT IN (
       'Active',
       'Contract Ended',
       'Resigned',
       'Terminated'
   );

-- DQ05: Salary structure ID is duplicated
SELECT *
FROM fact_salary_structure
WHERE structure_id IN (
    SELECT structure_id
    FROM fact_salary_structure
    WHERE structure_id IS NOT NULL
    GROUP BY structure_id
    HAVING COUNT(*) > 1
);

-- DQ06: Salary amount is negative
SELECT *
FROM fact_salary_structure
WHERE monthly_amount < 0;

-- DQ07: Attendance ID is duplicated
SELECT *
FROM fact_attendance
WHERE attendance_id IN (
    SELECT attendance_id
    FROM fact_attendance
    WHERE attendance_id IS NOT NULL
    GROUP BY attendance_id
    HAVING COUNT(*) > 1
);

-- DQ08: Attendance status is not an observed valid value
SELECT *
FROM fact_attendance
WHERE status IS NOT NULL
  AND status NOT IN (
      'ABSENT_LOP',
      'HALF_DAY_UNPAID',
      'PAID_LEAVE',
      'PRESENT',
      'UNPAID_LEAVE',
      'WFH'
  );

-- DQ09: Overtime hours are negative
SELECT *
FROM fact_attendance
WHERE overtime_hours < 0;

-- DQ10: Leave end date is before start date
SELECT *
FROM fact_leave
WHERE TRY_CAST(start_date AS DATE) IS NOT NULL
  AND TRY_CAST(end_date AS DATE) IS NOT NULL
  AND TRY_CAST(end_date AS DATE) < TRY_CAST(start_date AS DATE);

-- DQ11: Leave request ID is duplicated
SELECT *
FROM fact_leave
WHERE leave_request_id IN (
    SELECT leave_request_id
    FROM fact_leave
    WHERE leave_request_id IS NOT NULL
    GROUP BY leave_request_id
    HAVING COUNT(*) > 1
);

-- DQ12: Payroll run period is invalid
SELECT *
FROM fact_payroll_run
WHERE TRY_CAST(period_start AS DATE) IS NOT NULL
  AND TRY_CAST(period_end AS DATE) IS NOT NULL
  AND TRY_CAST(period_end AS DATE) < TRY_CAST(period_start AS DATE);

-- DQ13: Payroll item ID is duplicated
SELECT *
FROM fact_payroll
WHERE payroll_item_id IN (
    SELECT payroll_item_id
    FROM fact_payroll
    WHERE payroll_item_id IS NOT NULL
    GROUP BY payroll_item_id
    HAVING COUNT(*) > 1
);

-- DQ14: Net pay does not reconcile
SELECT *
FROM fact_payroll
WHERE net_pay IS NOT NULL
  AND gross_pay IS NOT NULL
  AND total_deductions IS NOT NULL
  AND ABS(net_pay - (gross_pay - total_deductions)) > 0.01;
