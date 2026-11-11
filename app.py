
import duckdb
import streamlit as st
import plotly.express as px
import pandas as pd
import zipfile
from datetime import date

st.set_page_config(
    page_title="PulseIQ | Workforce Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("PulseIQ Workforce Dashboard")
st.caption("Workforce overview | Reporting through September 2026")

DATABASE = "data/warehouse.duckdb"


@st.cache_data
def load_data():
    con = duckdb.connect(DATABASE, read_only=True)

    headcount = con.execute("""
        SELECT month_end, department_id, headcount
        FROM metric_dashboard_headcount
        ORDER BY month_end
    """).df()

    departments = con.execute("""
        SELECT department_id, department_name
        FROM dim_department
        ORDER BY department_name
    """).df()

    department_monthly = con.execute("""
        SELECT
            h.month_end,
            h.department_id,
            d.department_name,
            h.headcount
        FROM metric_dashboard_headcount h
        JOIN dim_department d
            ON h.department_id = d.department_id
        ORDER BY h.month_end, d.department_name
    """).df()

    location_tiers = con.execute("""
        SELECT location_tier, employees
        FROM metric_dashboard_location_tier
        ORDER BY employees DESC
    """).df()

    work_modes = con.execute("""
        SELECT work_mode, employees
        FROM metric_dashboard_work_mode
        ORDER BY employees DESC
    """).df()

    con.close()

    headcount["month_end"] = headcount["month_end"].astype(
        "datetime64[ns]"
    )
    department_monthly["month_end"] = department_monthly[
        "month_end"
    ].astype("datetime64[ns]")

    return (
        headcount,
        departments,
        department_monthly,
        location_tiers,
        work_modes
    )


try:
    (
        headcount,
        departments,
        department_monthly,
        location_tiers,
        work_modes
    ) = load_data()

    if headcount.empty:
        st.warning("No headcount data is available.")
        st.stop()

    # Dashboard filters
    st.sidebar.header("Dashboard Filters")

    all_departments = sorted(
        departments["department_name"].tolist()
    )

    selected_departments = st.sidebar.multiselect(
        "Department",
        all_departments,
        default=all_departments,
        placeholder="Select departments"
    )

    min_date = max(
        headcount["month_end"].min().date(),
        date(2025, 4, 1)
    )
    max_date = headcount["month_end"].max().date()

    date_range = st.sidebar.date_input(
        "Reporting period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    if start_date > end_date:
        st.warning("The start date must be before the end date.")
        st.stop()

    selected_department_ids = departments.loc[
        departments["department_name"].isin(selected_departments),
        "department_id"
    ].tolist()

    # Filter headcount by department and reporting period
    filtered_headcount = headcount[
        headcount["department_id"].isin(selected_department_ids)
        & (headcount["month_end"].dt.date >= start_date)
        & (headcount["month_end"].dt.date <= end_date)
    ]

    if filtered_headcount.empty:
        st.warning("No headcount data matches these filters.")
        st.stop()

    latest_month = filtered_headcount["month_end"].max()

    latest_data = filtered_headcount[
        filtered_headcount["month_end"] == latest_month
    ]

    current_headcount = int(latest_data["headcount"].sum())

    # Compare the latest selected month with the previous available month
    available_months = sorted(
        filtered_headcount["month_end"].dropna().unique()
    )

    previous_headcount = None

    if len(available_months) >= 2:
        previous_month = available_months[-2]

        previous_data = filtered_headcount[
            filtered_headcount["month_end"] == previous_month
        ]

        previous_headcount = int(previous_data["headcount"].sum())

    change = (
        current_headcount - previous_headcount
        if previous_headcount is not None
        else None
    )

    # KPI cards
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Headcount (selected departments)",
        current_headcount
    )

    col2.metric(
        "Change vs previous available month",
        change if change is not None else "N/A"
    )

    col3.metric(
        "Departments selected",
        len(selected_departments)
    )

    # 1. Headcount trend
    st.subheader("Headcount trend")

    trend = (
        filtered_headcount
        .groupby("month_end", as_index=False)["headcount"]
        .sum()
        .sort_values("month_end")
    )

    fig_trend = px.line(
        trend,
        x="month_end",
        y="headcount",
        markers=True,
        labels={
            "month_end": "Month",
            "headcount": "Employees"
        },
        title="How headcount has changed over time"
    )

    st.plotly_chart(fig_trend, width="stretch")

    if len(trend) >= 2:
        first_count = int(trend.iloc[0]["headcount"])
        last_count = int(trend.iloc[-1]["headcount"])
        difference = last_count - first_count

        direction = (
            "increased" if difference > 0
            else "decreased" if difference < 0
            else "remained unchanged"
        )

        st.caption(
            f"Insight: Headcount {direction} by "
            f"{abs(difference):,} employees across the selected period."
        )
    else:
        st.caption(
            "Insight: Select a wider reporting period to compare headcount."
        )

    # 2. Department workforce for the latest selected month
    st.subheader("Department workforce")

    department_chart = department_monthly[
        (department_monthly["month_end"] == latest_month)
        & department_monthly["department_name"].isin(
            selected_departments
        )
    ].sort_values("headcount", ascending=False)

    fig_department = px.bar(
        department_chart,
        x="department_name",
        y="headcount",
        labels={
            "department_name": "Department",
            "headcount": "Employees"
        },
        title="Department headcount in the latest selected month"
    )

    st.plotly_chart(fig_department, width="stretch")

    if not department_chart.empty:
        largest_department = department_chart.iloc[0]

        st.caption(
            f"Insight: {largest_department['department_name']} has "
            f"the highest headcount, with "
            f"{int(largest_department['headcount']):,} employees "
            f"in {latest_month.strftime('%B %Y')}."
        )

    # 3. Location-tier distribution
    st.subheader("Employees by location tier")

    fig_location_tier = px.bar(
        location_tiers,
        x="location_tier",
        y="employees",
        labels={
            "location_tier": "Location tier",
            "employees": "Employees"
        },
        title="Current workforce by location tier"
    )

    st.plotly_chart(fig_location_tier, width="stretch")

    if not location_tiers.empty:
        largest_tier = location_tiers.iloc[0]

        st.caption(
            f"Insight: {largest_tier['location_tier']} locations "
            f"have {int(largest_tier['employees']):,} employees."
        )

    st.caption(
        "Data note: Metro and Other are illustrative dashboard groupings, "
        "not official company location classifications. Location-tier "
        "figures show current employees and are not filtered by the "
        "reporting period or department selection."
    )

    # 4. Work-mode distribution
    st.subheader("Work mode distribution")

    fig_mode = px.bar(
        work_modes.sort_values("employees", ascending=False),
        x="work_mode",
        y="employees",
        labels={
            "work_mode": "Work mode",
            "employees": "Employees"
        },
        title="Current workforce by recorded work mode"
    )

    st.plotly_chart(fig_mode, width="stretch")

    if not work_modes.empty:
        largest_mode = work_modes.sort_values(
            "employees", ascending=False
        ).iloc[0]

        st.caption(
            f"Insight: {largest_mode['work_mode']} is the most common "
            f"recorded work mode, with "
            f"{int(largest_mode['employees']):,} employees."
        )

    st.caption(
        "Data note: Work-mode figures represent current employees. "
        "Headcount charts use historical month-end figures."
    )


    # Task 6: Attendance and leave trends

    st.divider()
    st.header("Task 6: Attendance and Leave Trends")

    con = duckdb.connect(DATABASE, read_only=True)

    attendance_trends = con.execute("""
        SELECT
            a.month_start,
            a.department_id,
            d.department_name,
            a.attendance_rate_pct,
            a.late_arrivals,
            a.overtime_hours
        FROM metric_attendance_trends a
        LEFT JOIN dim_department d
            ON a.department_id = d.department_id
        ORDER BY a.month_start, d.department_name
    """).df()

    leave_trends = con.execute("""
        SELECT
            month_start,
            leave_type_code,
            leave_type_name,
            approved_leave_days,
            approved_requests
        FROM metric_leave_trends
        ORDER BY month_start, leave_type_name
    """).df()

    holidays = con.execute("""
        SELECT
            date_key,
            holiday_name,
            is_holiday
        FROM dim_date
        WHERE is_holiday = TRUE
        ORDER BY date_key
    """).df()

    con.close()

    attendance_trends["month_start"] = (
        attendance_trends["month_start"].astype("datetime64[ns]")
    )
    leave_trends["month_start"] = (
        leave_trends["month_start"].astype("datetime64[ns]")
    )
    holidays["date_key"] = holidays["date_key"].astype("datetime64[ns]")

    task6_attendance = attendance_trends[
        attendance_trends["department_name"].isin(selected_departments)
        & (attendance_trends["month_start"].dt.date >= start_date)
        & (attendance_trends["month_start"].dt.date <= end_date)
    ]

    task6_leave = leave_trends[
        (leave_trends["month_start"].dt.date >= start_date)
        & (leave_trends["month_start"].dt.date <= end_date)
    ]

    task6_holidays = holidays[
        (holidays["date_key"].dt.date >= start_date)
        & (holidays["date_key"].dt.date <= end_date)
    ]

    st.caption(
        "Attendance and leave trends use the selected reporting period. "
        "Department selection applies to attendance metrics."
    )

    # 1. Monthly attendance rate by department
    st.subheader("Monthly attendance rate")

    if task6_attendance.empty:
        st.warning("No attendance data matches the selected filters.")
    else:
        fig_attendance = px.line(
            task6_attendance,
            x="month_start",
            y="attendance_rate_pct",
            color="department_name",
            markers=True,
            labels={
                "month_start": "Month",
                "attendance_rate_pct": "Attendance rate (%)",
                "department_name": "Department"
            },
            title="Monthly attendance rate by department"
        )

        st.plotly_chart(fig_attendance, width="stretch")

    # 2. Late arrivals
    st.subheader("Late arrivals by month")

    late_monthly = (
        task6_attendance
        .groupby("month_start", as_index=False)["late_arrivals"]
        .sum()
        .sort_values("month_start")
    )

    if not late_monthly.empty:
        fig_late = px.bar(
            late_monthly,
            x="month_start",
            y="late_arrivals",
            labels={
                "month_start": "Month",
                "late_arrivals": "Late arrivals"
            },
            title="Monthly late arrivals across selected departments"
        )

        st.plotly_chart(fig_late, width="stretch")

    # 3. Overtime hours
    st.subheader("Overtime hours by month")

    overtime_monthly = (
        task6_attendance
        .groupby("month_start", as_index=False)["overtime_hours"]
        .sum()
        .sort_values("month_start")
    )

    if not overtime_monthly.empty:
        fig_overtime = px.bar(
            overtime_monthly,
            x="month_start",
            y="overtime_hours",
            labels={
                "month_start": "Month",
                "overtime_hours": "Overtime hours"
            },
            title="Monthly overtime hours across selected departments"
        )

        st.plotly_chart(fig_overtime, width="stretch")

    # 4. Approved leave days by type
    st.subheader("Leave trends by type")

    if task6_leave.empty:
        st.warning("No leave data matches the selected reporting period.")
    else:
        leave_monthly = (
            task6_leave
            .groupby(
                ["month_start", "leave_type_name"],
                as_index=False
            )["approved_leave_days"]
            .sum()
        )

        fig_leave = px.bar(
            leave_monthly,
            x="month_start",
            y="approved_leave_days",
            color="leave_type_name",
            barmode="stack",
            labels={
                "month_start": "Month",
                "approved_leave_days": "Approved leave days",
                "leave_type_name": "Leave type"
            },
            title="Monthly approved leave days by type"
        )

        st.plotly_chart(fig_leave, width="stretch")

        leave_summary = (
            task6_leave
            .groupby("leave_type_name", as_index=False)
            ["approved_leave_days"]
            .sum()
            .sort_values("approved_leave_days", ascending=False)
        )

        st.dataframe(leave_summary, hide_index=True)

    # 4. Approved leave days by type
    st.subheader("Leave trends by type")

    if task6_leave.empty:
        st.warning("No leave data matches the selected reporting period.")
    else:
        leave_monthly = (
            task6_leave
            .groupby(
                ["month_start", "leave_type_name"],
                as_index=False
            )["approved_leave_days"]
            .sum()
        )

        fig_leave = px.bar(
            leave_monthly,
            x="month_start",
            y="approved_leave_days",
            color="leave_type_name",
            barmode="stack",
            labels={
                "month_start": "Month",
                "approved_leave_days": "Approved leave days",
                "leave_type_name": "Leave type"
            },
            title="Monthly approved leave days by type"
        )

        st.plotly_chart(
    fig_leave,
    width="stretch",
    key="task6_leave_chart"
)

        leave_summary = (
            task6_leave
            .groupby("leave_type_name", as_index=False)
            ["approved_leave_days"]
            .sum()
            .sort_values("approved_leave_days", ascending=False)
        )

        st.dataframe(leave_summary, hide_index=True)

    # 5. Holiday calendar and long-weekend indicators
    st.subheader("Holidays and long weekends")

    if task6_holidays.empty:
        st.info("No listed holidays fall within the selected period.")
    else:
        holiday_calendar = task6_holidays.copy()

        # Find the weekday for each holiday
        holiday_calendar["weekday"] = (
            holiday_calendar["date_key"].dt.day_name()
        )

        # Friday or Monday holidays can create a long weekend
        holiday_calendar["long_weekend"] = (
            holiday_calendar["date_key"].dt.dayofweek.isin([0, 4])
        )

        holiday_calendar["calendar_note"] = (
            holiday_calendar["long_weekend"].map({
                True: "Potential long weekend",
                False: "Check nearby weekend"
            })
        )

        holiday_calendar = holiday_calendar.rename(
            columns={
                "date_key": "Holiday date",
                "holiday_name": "Holiday"
            }
        )

        st.dataframe(
            holiday_calendar[
                [
                    "Holiday date",
                    "Holiday",
                    "weekday",
                    "calendar_note"
                ]
            ],
            hide_index=True
        )

        long_weekend_count = int(
            holiday_calendar["long_weekend"].sum()
        )

        st.metric(
            "Potential long-weekend holidays",
            long_weekend_count
        )

        st.caption(
            "These are potential long weekends based on Friday or Monday "
            "holidays. Actual company leave arrangements may differ. "
            "The workbook's holiday calendar is a sample calendar."
        )

    # 6. Identify unusual months
    st.subheader("Unusual attendance months")

    if len(task6_attendance) > 0:
        monthly_summary = (
            task6_attendance
            .groupby("month_start", as_index=False)
            .agg(
                attendance_rate_pct=("attendance_rate_pct", "mean"),
                late_arrivals=("late_arrivals", "sum"),
                overtime_hours=("overtime_hours", "sum")
            )
            .sort_values("month_start")
        )

        average_rate = monthly_summary[
            "attendance_rate_pct"
        ].mean()

        monthly_summary["rate_difference"] = (
            monthly_summary["attendance_rate_pct"] - average_rate
        )

        unusual_months = monthly_summary.copy()
        unusual_months["absolute_difference"] = (
            unusual_months["rate_difference"].abs()
        )

        unusual_months = unusual_months.nlargest(
            3, "absolute_difference"
        ).sort_values("month_start")

        st.caption(
            "Unusual months are the three months with attendance rates "
            "furthest from the selected period's average. This identifies "
            "statistical deviations, not proven causes."
        )

        st.dataframe(
            unusual_months[
                [
                    "month_start",
                    "attendance_rate_pct",
                    "rate_difference",
                    "late_arrivals",
                    "overtime_hours"
                ]
            ],
            hide_index=True
        )

        # Three numeric insights
        st.subheader("Key numeric insights")

        best_month = monthly_summary.loc[
            monthly_summary["attendance_rate_pct"].idxmax()
        ]

        lowest_month = monthly_summary.loc[
            monthly_summary["attendance_rate_pct"].idxmin()
        ]

        highest_overtime = monthly_summary.loc[
            monthly_summary["overtime_hours"].idxmax()
        ]

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Highest monthly attendance rate",
            f"{best_month['attendance_rate_pct']:.2f}%",
            best_month["month_start"].strftime("%b %Y")
        )

        col2.metric(
            "Lowest monthly attendance rate",
            f"{lowest_month['attendance_rate_pct']:.2f}%",
            lowest_month["month_start"].strftime("%b %Y")
        )

        col3.metric(
            "Highest monthly overtime",
            f"{highest_overtime['overtime_hours']:,.1f} hours",
            highest_overtime["month_start"].strftime("%b %Y")
        )

    else:
        st.info(
            "Select departments and a reporting period with attendance data "
            "to see unusual months and insights."
        )



    # Task 7: Actual attrition analytics

    st.divider()
    st.header("Task 7: Attrition Analytics")
    st.subheader("Actual employee exits")

    con = duckdb.connect(DATABASE, read_only=True)

    attrition_data = con.execute("""
        SELECT
            a.month_start,
            a.department_id,
            d.department_name,
            a.exits,
            a.voluntary_exits,
            a.involuntary_exits,
            a.contract_end_exits,
            a.average_tenure_years
        FROM metric_attrition_actual a
        LEFT JOIN dim_department d
            ON a.department_id = d.department_id
        ORDER BY a.month_start, d.department_name
    """).df()

    con.close()

    if attrition_data.empty:
        st.info(
            "No exit groups meet the minimum privacy threshold "
            "for the available data."
        )
    else:
        # Monthly exits across departments
        monthly_exits = (
            attrition_data
            .groupby("month_start", as_index=False)["exits"]
            .sum()
            .sort_values("month_start")
        )

        fig_exits = px.bar(
            monthly_exits,
            x="month_start",
            y="exits",
            labels={
                "month_start": "Month",
                "exits": "Exits"
            },
            title="Monthly actual exits (groups with at least 5 exits)"
        )

        st.plotly_chart(
            fig_exits,
            width="stretch",
            key="task7_monthly_exits"
        )

        # Exits by department
        department_exits = (
            attrition_data
            .groupby("department_name", as_index=False)["exits"]
            .sum()
            .sort_values("exits", ascending=False)
        )

        fig_department_exits = px.bar(
            department_exits,
            x="department_name",
            y="exits",
            labels={
                "department_name": "Department",
                "exits": "Exits"
            },
            title="Actual exits by department"
        )

        st.plotly_chart(
            fig_department_exits,
            width="stretch",
            key="task7_department_exits"
        )

        # Exit types
        exit_type_summary = (
            attrition_data[
                [
                    "voluntary_exits",
                    "involuntary_exits",
                    "contract_end_exits"
                ]
            ]
            .sum()
            .reset_index()
        )

        exit_type_summary.columns = ["Exit type", "Exits"]

        exit_type_summary["Exit type"] = (
            exit_type_summary["Exit type"].replace({
                "voluntary_exits": "Voluntary",
                "involuntary_exits": "Involuntary",
                "contract_end_exits": "Contract End"
            })
        )

        fig_exit_types = px.bar(
            exit_type_summary,
            x="Exit type",
            y="Exits",
            title="Exit types in groups meeting the privacy threshold"
        )

        st.plotly_chart(
            fig_exit_types,
            width="stretch",
            key="task7_exit_types"
        )

        # Average tenure at exit
        st.subheader("Average tenure at exit")

        st.dataframe(
            attrition_data[
                [
                    "month_start",
                    "department_name",
                    "average_tenure_years"
                ]
            ].rename(columns={
                "month_start": "Month",
                "department_name": "Department",
                "average_tenure_years": "Average tenure (years)"
            }),
            hide_index=True
        )

    # Predicted attrition risk
    st.divider()
    st.subheader("Predicted, not certain")

    st.info(
        "Employee attrition predictions are not available yet. "
        "A validated prediction model and risk dataset must be "
        "created before risk estimates can be displayed. "
        "Actual employee exits shown above are historical data, "
        "not predictions of future exits."
    )

    # Three biggest historical findings
    st.divider()
    st.subheader("Three Key Historical Findings")

    st.markdown(
        """
        1. **Total exits:** 304 employees exited during the
           historical period in the source dataset.

        2. **Voluntary exits:** 267 of 304 exits were voluntary
           (approximately 87.8%).

        3. **Highest annual exit count:** 2025 recorded 69 exits.
           The 2026 figure covers January to September only.
        """
    )

    # Privacy note
    st.caption(
        "Privacy note: Groups with fewer than 5 employee exits "
        "are suppressed to reduce the risk of identifying "
        "individual employees. Therefore, the charts may show "
        "fewer exits than the overall historical source totals."
    )


    # Task 8: Team Productivity Dashboard
    st.divider()
    st.header("Task 8: Team Productivity Dashboard")

    TASK8_ZIP = "data/raw/CSV.zip"

    try:
        with zipfile.ZipFile(TASK8_ZIP, "r") as task_zip:
            task_data = pd.read_csv(task_zip.open("csv/fact_task.csv"))
            team_data = pd.read_csv(task_zip.open("csv/dim_team.csv"))
            sprint_data = pd.read_csv(task_zip.open("csv/dim_sprint.csv"))
    except FileNotFoundError:
        st.warning(
            "Task 8 data ZIP was not found. Copy the provided CSV.zip file "
            "to data/raw/CSV.zip. The ZIP does not need to be extracted."
        )
        task_data = pd.DataFrame()
        team_data = pd.DataFrame()
        sprint_data = pd.DataFrame()
    except (KeyError, zipfile.BadZipFile) as error:
        st.error(f"Could not read the Task 8 ZIP archive: {error}")
        task_data = pd.DataFrame()
        team_data = pd.DataFrame()
        sprint_data = pd.DataFrame()

    if not task_data.empty:
        # Parse dates once and normalize status text for reliable filtering.
        for date_col in ["created_date", "started_date", "due_date", "completed_date"]:
            task_data[date_col] = pd.to_datetime(task_data[date_col], errors="coerce")
        sprint_data["start_date"] = pd.to_datetime(sprint_data["start_date"], errors="coerce")
        sprint_data["end_date"] = pd.to_datetime(sprint_data["end_date"], errors="coerce")
        task_data["status"] = task_data["status"].astype(str).str.strip().str.title()
        task_data["story_points"] = pd.to_numeric(task_data["story_points"], errors="coerce").fillna(0)
        task_data["reopened_count"] = pd.to_numeric(task_data["reopened_count"], errors="coerce").fillna(0)
        task_data["cycle_time_days"] = pd.to_numeric(task_data["cycle_time_days"], errors="coerce")

        st.caption(
            "Source: provided CSV.zip. Metrics follow metric_dictionary.csv. "
            "Velocity is for each team's own sprint trend and should not be used to rank teams."
        )

        team_names = team_data.sort_values("team_name")["team_name"].tolist()
        selected_team_names = st.multiselect(
            "Teams", team_names, default=team_names, key="task8_teams"
        )
        sprint_data = sprint_data.sort_values("start_date").copy()
        sprint_order = sprint_data["sprint_name"].tolist()
        selected_sprint_names = st.multiselect(
            "Sprints",
            sprint_order,
            default=sprint_order,
            key="task8_sprints"
        )

        selected_team_ids = team_data.loc[
            team_data["team_name"].isin(selected_team_names), "team_id"
        ].tolist()
        selected_sprint_ids = sprint_data.loc[
            sprint_data["sprint_name"].isin(selected_sprint_names), "sprint_id"
        ].tolist()

        filtered_tasks = task_data[
            task_data["team_id"].isin(selected_team_ids)
            & task_data["sprint_id"].isin(selected_sprint_ids)
        ].copy()

        if filtered_tasks.empty:
            st.info("Select at least one team and one sprint to display results.")
        else:
            done_tasks = filtered_tasks[filtered_tasks["status"] == "Done"]
            non_cancelled = filtered_tasks[filtered_tasks["status"] != "Cancelled"]
            valid_cycle = done_tasks[
                done_tasks["started_date"].notna()
                & done_tasks["completed_date"].notna()
                & (done_tasks["completed_date"] >= done_tasks["started_date"])
            ]
            on_time_flag = done_tasks["completed_on_time"].astype(str).str.upper().str.strip()
            valid_on_time = on_time_flag.isin(["Y", "N"])
            on_time_rate = (
                100 * (on_time_flag[valid_on_time] == "Y").mean()
                if valid_on_time.any() else None
            )
            completion_rate = (
                100 * len(done_tasks) / len(non_cancelled)
                if len(non_cancelled) else None
            )

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Tasks in selection", f"{len(filtered_tasks):,}")
            k2.metric("Done tasks", f"{len(done_tasks):,}")
            k3.metric("Completion rate", f"{completion_rate:.1f}%" if completion_rate is not None else "N/A")
            k4.metric("On-time rate", f"{on_time_rate:.1f}%" if on_time_rate is not None else "N/A")
            k5.metric("Blocked tasks", f"{(filtered_tasks['status'] == 'Blocked').sum():,}")

            team_sprint = (
                filtered_tasks.assign(
                    completed_points=filtered_tasks["story_points"].where(
                        filtered_tasks["status"] == "Done", 0
                    ),
                    reopened_task=(filtered_tasks["reopened_count"] > 0).astype(int),
                    blocked_task=(filtered_tasks["status"] == "Blocked").astype(int),
                    cancelled_task=(filtered_tasks["status"] == "Cancelled").astype(int)
                )
                .groupby(["team_id", "sprint_id"], as_index=False)
                .agg(
                    velocity=("completed_points", "sum"),
                    task_count=("task_id", "count"),
                    blocked_tasks=("blocked_task", "sum"),
                    reopened_tasks=("reopened_task", "sum"),
                    cancelled_tasks=("cancelled_task", "sum")
                )
                .merge(team_data[["team_id", "team_name"]], on="team_id", how="left")
                .merge(sprint_data[["sprint_id", "sprint_name", "start_date"]], on="sprint_id", how="left")
                .sort_values("start_date")
            )

            st.subheader("Velocity by team and sprint")
            st.plotly_chart(
                px.line(
                    team_sprint, x="sprint_name", y="velocity", color="team_name",
                    markers=True, labels={"sprint_name": "Sprint", "velocity": "Completed story points", "team_name": "Team"},
                    title="Completed story points across each team's sprints",
                    category_orders={"sprint_name": sprint_order}
                ),
                width="stretch", key="task8_velocity"
            )

            st.subheader("Average cycle time by team and sprint")
            cycle_source = valid_cycle.merge(
                team_data[["team_id", "team_name"]], on="team_id", how="left"
            ).merge(
                sprint_data[["sprint_id", "sprint_name", "start_date"]], on="sprint_id", how="left"
            )
            cycle_summary = cycle_source.groupby(
                ["team_name", "sprint_name", "start_date"], as_index=False
            )["cycle_time_days"].mean()
            if not cycle_summary.empty:
                st.plotly_chart(
                    px.line(
                        cycle_summary, x="sprint_name", y="cycle_time_days",
                        color="team_name", markers=True,
                        labels={"sprint_name": "Sprint", "cycle_time_days": "Average cycle time (days)", "team_name": "Team"},
                        title="Average valid cycle time",
                        category_orders={"sprint_name": sprint_order}
                    ),
                    width="stretch", key="task8_cycle_time"
                )
            else:
                st.info("No valid completed-task cycle times in this selection.")

            st.subheader("Blocked and reopened work")
            work_summary = team_sprint.groupby("team_name", as_index=False)[
                ["blocked_tasks", "reopened_tasks", "cancelled_tasks"]
            ].sum()
            if not work_summary.empty:
                st.plotly_chart(
                    px.bar(
                        work_summary, x="team_name",
                        y=["blocked_tasks", "reopened_tasks", "cancelled_tasks"],
                        barmode="group", labels={"value": "Task count", "team_name": "Team", "variable": "Work type"},
                        title="Blocked, reopened, and cancelled tasks"
                    ),
                    width="stretch", key="task8_blocked_reopened"
                )

            st.subheader("On-time delivery rate by team")
            done_with_flags = done_tasks.copy()
            done_with_flags["on_time_valid"] = done_with_flags[
                "completed_on_time"
            ].astype(str).str.upper().str.strip().isin(["Y", "N"])
            done_with_flags["on_time_yes"] = (
                done_with_flags["completed_on_time"].astype(str).str.upper().str.strip() == "Y"
            )
            ontime_summary = done_with_flags[done_with_flags["on_time_valid"]].groupby(
                "team_id", as_index=False
            ).agg(
                eligible_done_tasks=("task_id", "count"),
                on_time_tasks=("on_time_yes", "sum")
            ).merge(team_data[["team_id", "team_name"]], on="team_id", how="left")
            if not ontime_summary.empty:
                ontime_summary["on_time_rate_pct"] = (
                    100 * ontime_summary["on_time_tasks"] / ontime_summary["eligible_done_tasks"]
                )
                st.plotly_chart(
                    px.bar(
                        ontime_summary, x="team_name", y="on_time_rate_pct",
                        labels={"team_name": "Team", "on_time_rate_pct": "On-time rate (%)"},
                        title="On-time delivery rate by team (valid Y/N flags only)"
                    ),
                    width="stretch", key="task8_ontime"
                )

            st.subheader("Data-quality exclusions")
            invalid_cycle_count = int((
                done_tasks["started_date"].isna()
                | done_tasks["completed_date"].isna()
                | (done_tasks["completed_date"] < done_tasks["started_date"])
            ).sum())
            st.write(
                f"Done tasks excluded from cycle-time calculation because dates are missing "
                f"or completion precedes start: **{invalid_cycle_count:,}**."
            )
            st.caption(
                "Cancelled tasks are excluded from completion-rate denominator, velocity, "
                "and on-time delivery. Missing/invalid cycle-time records are not treated as zero."
            )

            st.subheader("Team sprint summary")
            st.dataframe(
                team_sprint[[
                    "team_name", "sprint_name", "task_count", "velocity",
                    "blocked_tasks", "reopened_tasks", "cancelled_tasks"
                ]].rename(columns={
                    "team_name": "Team", "sprint_name": "Sprint", "task_count": "Tasks",
                    "velocity": "Velocity (story points)", "blocked_tasks": "Blocked",
                    "reopened_tasks": "Tasks reopened", "cancelled_tasks": "Cancelled"
                }),
                hide_index=True, width="stretch"
            )

            # Two-team source-data cross-check: recompute key metrics directly
            # from the filtered task rows, then display the same results clearly.
            st.subheader("Two-team metric verification")
            verification_teams = team_data[
                team_data["team_name"].isin(selected_team_names)
            ].sort_values("team_name")["team_name"].head(2).tolist()
            verification_rows = []
            for verification_team in verification_teams:
                source_rows = filtered_tasks[
                    filtered_tasks["team_id"].isin(
                        team_data.loc[team_data["team_name"] == verification_team, "team_id"]
                    )
                ]
                source_done = source_rows[source_rows["status"] == "Done"]
                source_non_cancelled = source_rows[source_rows["status"] != "Cancelled"]
                source_flags = source_done["completed_on_time"].astype(str).str.strip().str.upper()
                source_valid_flags = source_flags.isin(["Y", "N"])
                source_valid_cycle = source_done[
                    source_done["started_date"].notna()
                    & source_done["completed_date"].notna()
                    & (source_done["completed_date"] >= source_done["started_date"])
                ]
                verification_rows.append({
                    "Team": verification_team,
                    "Source task rows": len(source_rows),
                    "Done rows": len(source_done),
                    "Non-cancelled denominator": len(source_non_cancelled),
                    "Completion rate (%)": round(100 * len(source_done) / len(source_non_cancelled), 2) if len(source_non_cancelled) else None,
                    "Valid on-time flags": int(source_valid_flags.sum()),
                    "On-time rate (%)": round(100 * (source_flags[source_valid_flags] == "Y").mean(), 2) if source_valid_flags.any() else None,
                    "Valid cycle-time rows": len(source_valid_cycle),
                    "Velocity (points)": round(source_done["story_points"].sum(), 2)
                })
            if verification_rows:
                st.dataframe(pd.DataFrame(verification_rows), hide_index=True, width="stretch")
                st.caption(
                    "Cross-checks are recalculated from the selected source CSV rows. "
                    "To complete the assignment's independent manual audit, compare these two teams' "
                    "counts with filtered rows in fact_task.csv."
                )
            else:
                st.info("Select at least one team to run the two-team verification.")

            # Three numeric, data-driven health observations. Avoid ranking teams
            # by velocity because story-point scales can differ across teams.
            st.subheader("Three team health findings")
            team_health = filtered_tasks.assign(
                blocked_flag=(filtered_tasks["status"] == "Blocked").astype(int),
                reopened_flag=(filtered_tasks["reopened_count"] > 0).astype(int),
                valid_on_time_flag=filtered_tasks["completed_on_time"].astype(str).str.strip().str.upper().isin(["Y", "N"]),
                on_time_yes_flag=(filtered_tasks["completed_on_time"].astype(str).str.strip().str.upper() == "Y").astype(int)
            ).groupby("team_id", as_index=False).agg(
                blocked_tasks=("blocked_flag", "sum"),
                reopened_tasks=("reopened_flag", "sum"),
                done_tasks=("status", lambda values: int((values == "Done").sum())),
                valid_on_time_flags=("valid_on_time_flag", "sum"),
                on_time_tasks=("on_time_yes_flag", "sum")
            ).merge(team_data[["team_id", "team_name"]], on="team_id", how="left")
            eligible_health = team_health[team_health["valid_on_time_flags"] >= 30].copy()
            if not team_health.empty:
                blocked_leader = team_health.sort_values("blocked_tasks", ascending=False).iloc[0]
                reopened_leader = team_health.sort_values("reopened_tasks", ascending=False).iloc[0]
                st.markdown(
                    f"1. **Blocked work:** {blocked_leader['team_name']} has the highest blocked-task count "
                    f"in this selection (**{int(blocked_leader['blocked_tasks']):,}**). This is a workload signal, "
                    "not proof that the team is less productive."
                )
                st.markdown(
                    f"2. **Reopened work:** {reopened_leader['team_name']} has the most tasks reopened at least once "
                    f"(**{int(reopened_leader['reopened_tasks']):,}**). Review task complexity and QA context before drawing conclusions."
                )
                if not eligible_health.empty:
                    eligible_health["on_time_rate_pct"] = 100 * eligible_health["on_time_tasks"] / eligible_health["valid_on_time_flags"]
                    low_ontime = eligible_health.sort_values("on_time_rate_pct").iloc[0]
                    st.markdown(
                        f"3. **Delivery follow-up:** {low_ontime['team_name']} has the lowest on-time rate among teams "
                        f"with at least 30 valid completed-task flags (**{low_ontime['on_time_rate_pct']:.1f}%**, "
                        f"{int(low_ontime['on_time_tasks'])}/{int(low_ontime['valid_on_time_flags'])} on time). "
                        "Treat this as a prompt for investigation, not a team-performance verdict."
                    )
                else:
                    st.markdown(
                        "3. **On-time delivery:** No selected team has at least 30 valid Y/N completion flags, "
                        "so the dashboard avoids making a low-sample delivery-rate comparison."
                    )
                st.caption(
                    "Findings update with the team/sprint filters. Counts describe the selected data only; "
                    "team size, sprint scope, task mix, and story-point estimation practices differ."
                )


    # Task 9: Payroll Cost Dashboard and Reconciliation
    st.divider()
    st.header("Task 9: Payroll Cost Dashboard")

    payroll_con = duckdb.connect(DATABASE, read_only=True)

    payroll = payroll_con.execute("""
        SELECT
            p.period_start,
            p.department_id,
            d.department_name,
            p.gross_pay,
            p.net_pay,
            p.employer_cost,
            p.paid_employees
        FROM metric_payroll_monthly p
        LEFT JOIN dim_department d
            ON p.department_id = d.department_id
        ORDER BY p.period_start, d.department_name
    """).df()

    payroll_con.close()

    payroll["period_start"] = pd.to_datetime(payroll["period_start"])

    # Keep only aggregate groups with at least five employees
    payroll = payroll[payroll["paid_employees"] >= 5].copy()

    if payroll.empty:
        st.warning("No payroll data is available for reporting.")
    else:
        payroll_departments = sorted(
            payroll["department_name"].dropna().unique().tolist()
        )

        payroll_col1, payroll_col2 = st.columns(2)

        with payroll_col1:
            payroll_selected_departments = st.multiselect(
                "Payroll departments",
                payroll_departments,
                default=payroll_departments,
                key="payroll_departments"
            )

        with payroll_col2:
            payroll_months = sorted(
                payroll["period_start"].dropna().unique()
            )
            payroll_start, payroll_end = st.select_slider(
                "Payroll reporting period",
                options=payroll_months,
                value=(payroll_months[0], payroll_months[-1]),
                format_func=lambda value: value.strftime("%b %Y"),
                key="payroll_period"
            )

        payroll_filtered = payroll[
            payroll["department_name"].isin(
                payroll_selected_departments
            )
            & (payroll["period_start"] >= payroll_start)
            & (payroll["period_start"] <= payroll_end)
        ].copy()

        if payroll_filtered.empty:
            st.warning("No payroll records match the selected filters.")
        else:
            total_gross = payroll_filtered["gross_pay"].sum()
            total_net = payroll_filtered["net_pay"].sum()
            total_employer = payroll_filtered["employer_cost"].sum()

            # Cost per employee-month, using each department-month group
            total_employee_months = payroll_filtered[
                "paid_employees"
            ].sum()

            cost_per_employee = (
                total_employer / total_employee_months
                if total_employee_months > 0 else 0
            )

            k1, k2, k3, k4 = st.columns(4)

            k1.metric("Gross Pay", f"₹{total_gross:,.0f}")
            k2.metric("Net Pay", f"₹{total_net:,.0f}")
            k3.metric("Employer Cost", f"₹{total_employer:,.0f}")
            k4.metric(
                "Employer Cost per Employee-Month",
                f"₹{cost_per_employee:,.0f}"
            )

            st.subheader("Monthly Payroll Cost Trend")

            monthly_payroll = (
                payroll_filtered.groupby("period_start", as_index=False)
                .agg(
                    gross_pay=("gross_pay", "sum"),
                    net_pay=("net_pay", "sum"),
                    employer_cost=("employer_cost", "sum")
                )
                .sort_values("period_start")
            )

            monthly_long = monthly_payroll.melt(
                id_vars="period_start",
                value_vars=["gross_pay", "net_pay", "employer_cost"],
                var_name="cost_type",
                value_name="amount"
            )

            fig_payroll_trend = px.line(
                monthly_long,
                x="period_start",
                y="amount",
                color="cost_type",
                markers=True,
                labels={
                    "period_start": "Month",
                    "amount": "Amount (₹)",
                    "cost_type": "Cost Type"
                },
                title="Gross, Net and Employer Cost by Month"
            )

            st.plotly_chart(fig_payroll_trend, width="stretch")

            st.subheader("Payroll Cost by Department and Month")

            fig_payroll_department = px.bar(
                payroll_filtered,
                x="department_name",
                y="employer_cost",
                color="period_start",
                barmode="group",
                labels={
                    "department_name": "Department",
                    "employer_cost": "Employer Cost (₹)",
                    "period_start": "Month"
                },
                title="Employer Cost by Department and Month"
            )

            st.plotly_chart(fig_payroll_department, width="stretch")

            st.subheader("Department Payroll Summary")

            department_summary = (
                payroll_filtered.groupby(
                    "department_name", as_index=False
                )
                .agg(
                    gross_pay=("gross_pay", "sum"),
                    net_pay=("net_pay", "sum"),
                    employer_cost=("employer_cost", "sum"),
                    employee_months=("paid_employees", "sum")
                )
            )

            department_summary["cost_per_employee_month"] = (
                department_summary["employer_cost"]
                / department_summary["employee_months"]
            )

            department_summary = department_summary.rename(columns={
                "department_name": "Department",
                "gross_pay": "Gross Pay (₹)",
                "net_pay": "Net Pay (₹)",
                "employer_cost": "Employer Cost (₹)",
                "employee_months": "Employee-Months",
                "cost_per_employee_month": "Cost per Employee-Month (₹)"
            })

            st.dataframe(
                department_summary.round(2),
                hide_index=True,
                width="stretch"
            )

            st.caption(
                "Privacy: only department-level totals and averages are shown. "
                "Department-month groups with fewer than five employees "
                "are excluded. Cost per employee is calculated per "
                "employee-month, not per unique employee across the full period."
            )
    # Task 10: Budget vs Actual and KPI Targets
    st.divider()
    st.header("Task 10: Budget vs Actual and KPI Targets")

    budget_con = duckdb.connect(DATABASE, read_only=True)

    try:
        budget_actual = budget_con.execute("""
            SELECT
                b.department_id,
                d.department_name,
                CAST(b.month AS DATE) AS month,
                b.budget_payroll_cost AS budget,
                p.employer_cost AS actual,
                p.gross_pay,
                p.overtime_pay,
                p.paid_employees
            FROM budget_payroll_dept_month b
            LEFT JOIN metric_payroll_monthly p
                ON b.department_id = p.department_id
                AND CAST(b.month AS DATE) = p.period_start
            LEFT JOIN dim_department d
                ON b.department_id = d.department_id
            ORDER BY month, department_name
        """).df()

        budget_actual["variance"] = (
            budget_actual["actual"] - budget_actual["budget"]
        )

        budget_actual["variance_pct"] = (
            budget_actual["variance"]
            / budget_actual["budget"].replace(0, pd.NA)
            * 100
        )

        st.subheader("Payroll Budget vs Actual")

        st.caption(
            "Sign rule: variance = actual payroll cost − budget. "
            "Positive variance means overspend; negative variance means "
            "underspend. Variance % = variance / budget × 100."
        )

        valid_budget = budget_actual.dropna(
            subset=["actual", "budget"]
        ).copy()

        if not valid_budget.empty:
            total_budget = valid_budget["budget"].sum()
            total_actual = valid_budget["actual"].sum()
            total_variance = total_actual - total_budget

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Approved Budget",
                f"₹{total_budget:,.0f}"
            )

            col2.metric(
                "Actual Payroll Cost",
                f"₹{total_actual:,.0f}"
            )

            col3.metric(
                "Variance",
                f"₹{total_variance:,.0f}",
                delta=f"{total_variance / total_budget * 100:.2f}%"
                if total_budget else None,
                delta_color="inverse"
            )

            st.subheader("Department Overspend Ranking")

            overspend = (
                valid_budget.groupby(
                    ["department_id", "department_name"],
                    as_index=False
                )
                .agg(
                    budget=("budget", "sum"),
                    actual=("actual", "sum"),
                    variance=("variance", "sum")
                )
            )

            overspend["variance_pct"] = (
                overspend["variance"]
                / overspend["budget"].replace(0, pd.NA)
                * 100
            )

            overspend = overspend.sort_values(
                "variance", ascending=False
            )

            st.dataframe(
                overspend.style.format({
                    "budget": "₹{:,.0f}",
                    "actual": "₹{:,.0f}",
                    "variance": "₹{:,.0f}",
                    "variance_pct": "{:.2f}%"
                }),
                width="stretch",
                hide_index=True
            )

            st.subheader("Monthly Budget Variance")

            fig_budget = px.bar(
                valid_budget,
                x="month",
                y="variance",
                color="department_name",
                barmode="group",
                title="Actual Payroll Cost Minus Budget",
                labels={
                    "month": "Month",
                    "variance": "Variance (₹)",
                    "department_name": "Department"
                }
            )

            st.plotly_chart(fig_budget, width="stretch")

            st.subheader("Department and Month Details")

            st.dataframe(
                valid_budget[
                    [
                        "month",
                        "department_name",
                        "budget",
                        "actual",
                        "variance",
                        "variance_pct"
                    ]
                ].style.format({
                    "budget": "₹{:,.0f}",
                    "actual": "₹{:,.0f}",
                    "variance": "₹{:,.0f}",
                    "variance_pct": "{:.2f}%"
                }),
                width="stretch",
                hide_index=True
            )

        else:
            st.warning(
                "No matching budget and actual payroll records were found."
            )

        st.subheader("KPI Performance Against Targets")

        kpi_targets_df = budget_con.execute("""
            SELECT *
            FROM kpi_targets
            ORDER BY month, department_id
        """).df()

        attendance_df = budget_con.execute("""
            SELECT
                month_start AS month,
                department_id,
                present_records,
                attendance_records
            FROM metric_attendance_monthly
        """).df()
        kpi_targets_df["month"] = pd.to_datetime(
        kpi_targets_df["month"]
        ).dt.strftime("%Y-%m-%d")

        attendance_df["month"] = pd.to_datetime(
        attendance_df["month"]
        ).dt.strftime("%Y-%m-%d")
        attendance_df["attendance_actual_pct"] = (
            attendance_df["present_records"]
            / attendance_df["attendance_records"].replace(0, pd.NA)
            * 100
        )

        kpi_view = kpi_targets_df.merge(
            attendance_df[
                ["month", "department_id", "attendance_actual_pct"]
            ],
            on=["month", "department_id"],
            how="left"
        )

        kpi_view["attendance_target_pct"] = (
            kpi_view["attendance_rate_target"] * 100
        )

        kpi_view["attendance_status"] = kpi_view.apply(
            lambda row:
                "Green"
                if pd.notna(row["attendance_actual_pct"])
                and row["attendance_actual_pct"]
                >= row["attendance_target_pct"]
                else "Red"
                if pd.notna(row["attendance_actual_pct"])
                else "Unavailable",
            axis=1
        )

        st.caption(
            "Attendance is shown as a percentage. Green means the target "
            "is met; red means it is missed. Other KPIs are retained in "
            "the target table for comparison as their actual metric "
            "definitions are confirmed."
        )

        st.dataframe(
            kpi_view[
                [
                    "month",
                    "department_id",
                    "attendance_actual_pct",
                    "attendance_target_pct",
                    "attendance_status",
                    "overtime_share_target_pct",
                    "attrition_monthly_target_pct",
                    "task_completion_target_pct"
                ]
            ].style.format({
                "attendance_actual_pct": "{:.2f}%",
                "attendance_target_pct": "{:.2f}%",
                "overtime_share_target_pct": "{:.2f}%",
                "attrition_monthly_target_pct": "{:.2f}%",
                "task_completion_target_pct": "{:.2f}%"
            }),
            width="stretch",
            hide_index=True
        )

        st.subheader("Management Recommendations")

        if not valid_budget.empty:
            top_departments = overspend.head(2)

            for _, department in top_departments.iterrows():
                if department["variance"] > 0:
                    st.write(
                        f"- **{department['department_name']}**: "
                        f"actual payroll is ₹{department['variance']:,.0f} "
                        f"above budget. Review hiring, overtime and "
                        f"payroll changes before revising the forecast."
                    )
                else:
                    st.write(
                        f"- **{department['department_name']}**: "
                        f"payroll is within or below budget. Confirm that "
                        f"service levels and staffing needs are still met."
                    )

        st.info(
            "Fairness note: the approved budget may not reflect the hiring "
            "freeze. Keep the original budget unchanged for audit purposes, "
            "flag affected months, and explain staffing changes before "
            "judging departments solely on overspend."
        )

    finally:
        budget_con.close()


    # Task 11: Profit and Loss and Expense Analytics
    st.divider()
    st.header("Task 11: Profit & Loss and Expense Analytics")

    TASK11_ZIP = "data/raw/CSV.zip"

    try:
        with zipfile.ZipFile(TASK11_ZIP) as z:
            ledger = pd.read_csv(z.open("csv/fact_ledger.csv"))
            accounts = pd.read_csv(z.open("csv/dim_account.csv"))
            expenses = pd.read_csv(z.open("csv/fact_expense.csv"))
            vendors = pd.read_csv(z.open("csv/dim_vendor.csv"))

        # Convert account codes to a consistent data type
        ledger["account_code"] = ledger["account_code"].astype(str)
        accounts["account_code"] = accounts["account_code"].astype(str)
        expenses["category_account"] = expenses["category_account"].astype(str)

        # Exclude group accounts to prevent double counting
        detail_accounts = accounts[
            accounts["is_group"].astype(str).str.upper() == "N"
        ].copy()

        ledger = ledger.merge(
            detail_accounts,
            on="account_code",
            how="inner"
        )

        # Use only Profit & Loss detail accounts
        pnl = ledger[
            ledger["statement"] == "Profit & Loss"
        ].copy()

        pnl["revenue"] = 0.0
        pnl["expenses"] = 0.0

        pnl.loc[
            pnl["account_type"] == "INCOME", "revenue"
        ] = -pnl["signed_amount_debit_positive"]

        pnl.loc[
            pnl["account_type"] == "EXPENSE", "expenses"
        ] = pnl["signed_amount_debit_positive"]

        # Monthly P&L
        monthly_pnl = pnl.groupby("posting_period").agg(
            revenue=("revenue", "sum"),
            expenses=("expenses", "sum")
        ).reset_index()

        monthly_pnl["profit"] = (
            monthly_pnl["revenue"] - monthly_pnl["expenses"]
        )

        monthly_pnl["margin_percent"] = (
            monthly_pnl["profit"] / monthly_pnl["revenue"] * 100
        )

        st.subheader("Monthly Financial Overview")

        selected_month = st.selectbox(
            "Select reporting month",
            monthly_pnl["posting_period"].tolist(),
            index=len(monthly_pnl) - 1,
            key="task11_month"
        )

        selected_data = monthly_pnl[
            monthly_pnl["posting_period"] == selected_month
        ].iloc[0]

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Revenue",
            f"₹{selected_data['revenue'] / 10000000:.2f} Cr"
        )

        col2.metric(
            "Expenses",
            f"₹{selected_data['expenses'] / 10000000:.2f} Cr"
        )

        col3.metric(
            "Net Profit",
            f"₹{selected_data['profit'] / 10000000:.2f} Cr"
        )

        col4.metric(
            "Profit Margin",
            f"{selected_data['margin_percent']:.2f}%"
        )

        st.subheader("Monthly Profit & Loss Table")

        display_pnl = monthly_pnl.copy()

        for column in ["revenue", "expenses", "profit"]:
            display_pnl[column] = (
                display_pnl[column] / 10000000
            ).round(2)

        display_pnl["margin_percent"] = (
            display_pnl["margin_percent"].round(2)
        )

        st.dataframe(
            display_pnl.rename(columns={
                "posting_period": "Month",
                "revenue": "Revenue (₹ Cr)",
                "expenses": "Expenses (₹ Cr)",
                "profit": "Profit (₹ Cr)",
                "margin_percent": "Margin (%)"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Revenue, Expenses and Profit Trend")

        trend_data = monthly_pnl.melt(
            id_vars="posting_period",
            value_vars=["revenue", "expenses", "profit"],
            var_name="Metric",
            value_name="Amount"
        )

        trend_data["Amount"] = trend_data["Amount"] / 10000000

        fig = px.line(
            trend_data,
            x="posting_period",
            y="Amount",
            color="Metric",
            markers=True,
            title="Monthly P&L Trend (₹ Crore)"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Expense category analysis
        st.divider()
        st.subheader("Expense Analysis by Category")

        expenses = expenses.merge(
            detail_accounts[
                ["account_code", "account_name", "is_group"]
            ],
            left_on="category_account",
            right_on="account_code",
            how="left"
        )

        expenses = expenses[
            expenses["is_group"].astype(str).str.upper() == "N"
        ].copy()

        category_data = (
            expenses.groupby("account_name")["amount_excl_gst"]
            .sum()
            .reset_index()
            .sort_values("amount_excl_gst", ascending=False)
        )

        category_data["amount_crore"] = (
            category_data["amount_excl_gst"] / 10000000
        )

        fig_category = px.bar(
            category_data,
            x="account_name",
            y="amount_crore",
            title="Expense by Category (Excluding GST)",
            labels={
                "account_name": "Expense Category",
                "amount_crore": "Amount (₹ Crore)"
            }
        )

        st.plotly_chart(
            fig_category,
            use_container_width=True
        )

        # Top vendors
        st.subheader("Top 10 Vendors")

        vendor_data = expenses.merge(
            vendors[["vendor_id", "vendor_name"]],
            on="vendor_id",
            how="left"
        )

        top_vendors = (
            vendor_data.groupby("vendor_name")["amount_excl_gst"]
            .sum()
            .reset_index()
            .sort_values("amount_excl_gst", ascending=False)
            .head(10)
        )

        top_vendors["amount_crore"] = (
            top_vendors["amount_excl_gst"] / 10000000
        )

        st.dataframe(
            top_vendors[
                ["vendor_name", "amount_crore"]
            ].rename(columns={
                "vendor_name": "Vendor",
                "amount_crore": "Expense (₹ Crore)"
            }).round(2),
            use_container_width=True,
            hide_index=True
        )

        # README headline reconciliation
        st.divider()
        st.subheader("README Headline Reconciliation")

        total_revenue = monthly_pnl["revenue"].sum()
        total_expenses = monthly_pnl["expenses"].sum()
        total_profit = monthly_pnl["profit"].sum()
        total_margin = total_profit / total_revenue * 100

        tieout = pd.DataFrame({
            "Metric": ["Revenue", "Expenses", "Profit", "Profit Margin"],
            "Calculated": [
                total_revenue / 10000000,
                total_expenses / 10000000,
                total_profit / 10000000,
                total_margin
            ],
            "README": [126.09, 103.62, 22.47, 17.8],
            "Unit": ["₹ Crore", "₹ Crore", "₹ Crore", "%"]
        })

        tieout["Difference"] = (
            tieout["Calculated"] - tieout["README"]
        ).round(2)

        st.dataframe(
            tieout.round(2),
            use_container_width=True,
            hide_index=True
        )

        st.warning(
            "Small rounding differences exist between the calculated "
            "P&L totals and the README headline figures. "
            "Please review the Difference column in the table above."
        )

                # Management findings
        st.divider()
        st.subheader("Three Business Findings")

        st.write(
            "1. Salaries and wages are the largest P&L expense, "
            "contributing approximately INR 78.69 crore."
        )

        st.write(
            "2. Office rent, cloud hosting and marketing are the "
            "largest expense-register categories. Skyline Realty "
            "Holdings is the top vendor, with approximately "
            "INR 1.69 crore in expenses."
        )

        st.write(
            "3. Profit margin changes significantly across months. "
            "It reached 27.16% in August 2026 and fell to "
            "18.59% in September 2026."
        )

        st.divider()
        st.subheader("Possible Causes of Margin Changes")

        st.write(
            "1. Payroll growth: Higher salaries, employee headcount "
            "or overtime may increase expenses. Verify using monthly "
            "payroll and headcount data."
        )

        st.write(
            "2. Higher operating costs: Rent, cloud hosting or "
            "marketing expenses may reduce profit margin. Verify "
            "using monthly expense-category data."
        )

        st.write(
            "3. Vendor spending changes: Higher vendor bills may "
            "increase operating costs. Verify using monthly vendor "
            "expenses and corresponding ledger postings."
        )
    except (KeyError, ValueError, zipfile.BadZipFile) as error:
        st.error(f"Task 11 data could not be processed: {error}")

    
    # Task 12: Invoices, Receivables and Cash Flow
    st.divider()
    st.header("Task 12: Invoices, Receivables and Cash Flow")

    TASK12_ZIP = "data/raw/CSV.zip"

    try:
        with zipfile.ZipFile(TASK12_ZIP) as z:
            invoices = pd.read_csv(z.open("csv/fact_invoice.csv"))
            payments = pd.read_csv(z.open("csv/fact_invoice_payment.csv"))
            clients = pd.read_csv(z.open("csv/dim_client.csv"))
            expenses = pd.read_csv(z.open("csv/fact_expense.csv"))

        # Reporting cutoff from the master dataset
        cutoff_date = pd.Timestamp("2026-09-30")

        # Only these invoice statuses count as open receivables
        open_statuses = ["SENT", "OVERDUE", "PARTIALLY_PAID"]

        st.info(
            "Open receivables include only SENT, OVERDUE and "
            "PARTIALLY_PAID invoices. DRAFT and CANCELLED invoices "
            "are excluded."
        )

        open_invoices = invoices[
            invoices["status"].isin(open_statuses)
        ].copy()

        total_receivables = open_invoices["balance_due"].sum()

        # Receivables ageing
        ageing_labels = {
            "Not yet due": "Not yet due",
            "1-30 days": "1-30 days overdue",
            "31-60 days": "31-60 days overdue",
            "61-90 days": "61-90 days overdue",
            "90+ days": "90+ days overdue"
        }

        open_invoices["ageing_category"] = (
            open_invoices["ageing_bucket_at_cutoff"]
            .map(ageing_labels)
            .fillna("Unclassified")
        )

        ageing_order = [
            "Not yet due",
            "1-30 days overdue",
            "31-60 days overdue",
            "61-90 days overdue",
            "90+ days overdue"
        ]

        ageing_summary = (
            open_invoices.groupby("ageing_category")["balance_due"]
            .sum()
            .reindex(ageing_order, fill_value=0)
            .rename_axis("ageing_category")
            .reset_index()
        )

        ageing_order = [
            "Not yet due",
            "1-30 days overdue",
            "31-60 days overdue",
            "61-90 days overdue",
            "90+ days overdue"
        ]

        ageing_summary["ageing_category"] = pd.Categorical(
            ageing_summary["ageing_category"],
            categories=ageing_order + ["Unclassified"],
            ordered=True
        )

        ageing_summary = ageing_summary.sort_values("ageing_category")

        ageing_total = ageing_summary["balance_due"].sum()
        ageing_difference = total_receivables - ageing_total

        # Client names for receivables
        client_receivables = (
            open_invoices.groupby("client_id")["balance_due"]
            .sum()
            .reset_index()
            .merge(
                clients[["client_id", "client_name"]],
                on="client_id",
                how="left"
            )
            .sort_values("balance_due", ascending=False)
        )

        overdue_invoices = open_invoices[
            open_invoices["status"] == "OVERDUE"
        ].copy()

        overdue_clients = (
            overdue_invoices.groupby("client_id")["balance_due"]
            .sum()
            .reset_index()
            .merge(
                clients[["client_id", "client_name"]],
                on="client_id",
                how="left"
            )
            .sort_values("balance_due", ascending=False)
        )

        # Average days to pay by client, using paid invoices only
        paid_invoices = invoices[
            (invoices["status"] == "PAID") &
            (invoices["days_to_pay"].notna())
        ].copy()

        payment_behaviour = (
            paid_invoices.groupby("client_id")
            .agg(
                paid_invoices=("invoice_id", "count"),
                average_days_to_pay=("days_to_pay", "mean")
            )
            .reset_index()
            .merge(
                clients[
                    ["client_id", "client_name", "payment_terms_days"]
                ],
                on="client_id",
                how="left"
            )
        )

        payment_behaviour["days_over_terms"] = (
            payment_behaviour["average_days_to_pay"] -
            payment_behaviour["payment_terms_days"]
        )

        payment_behaviour = payment_behaviour.sort_values(
            "average_days_to_pay",
            ascending=False
        )

        # Cash received from invoice payments
        payments["payment_date"] = pd.to_datetime(
            payments["payment_date"],
            errors="coerce"
        )

        cash_in = (
            payments.dropna(subset=["payment_date"])
            .groupby(payments["payment_date"].dt.to_period("M"))["amount"]
            .sum()
            .rename("cash_in")
        )

        # Cash paid for expenses only
        expenses["paid_date"] = pd.to_datetime(
            expenses["paid_date"],
            errors="coerce"
        )

        paid_expenses = expenses[
            (expenses["status"] == "PAID") &
            (expenses["paid_date"].notna())
        ].copy()

        cash_out = (
            paid_expenses.groupby(
                paid_expenses["paid_date"].dt.to_period("M")
            )["total_amount"]
            .sum()
            .rename("cash_out")
        )

        monthly_cash = pd.concat(
            [cash_in, cash_out],
            axis=1
        ).fillna(0)

        monthly_cash["net_cash_movement"] = (
            monthly_cash["cash_in"] - monthly_cash["cash_out"]
        )

        monthly_cash = monthly_cash.sort_index()
        monthly_cash_display = monthly_cash.copy()
        monthly_cash_display.index = (
            monthly_cash_display.index.astype(str)
        )

        total_cash_in = monthly_cash["cash_in"].sum()
        total_cash_out = monthly_cash["cash_out"].sum()
        net_cash_movement = total_cash_in - total_cash_out

        # Main receivables metrics
        st.subheader("Receivables Overview")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Open Receivables",
            f"₹{total_receivables:,.0f}"
        )

        col2.metric(
            "Open Invoices",
            f"{len(open_invoices):,}"
        )

        col3.metric(
            "Overdue Invoices",
            f"{len(overdue_invoices):,}"
        )

        # Ageing table and chart
        st.subheader("Receivables Ageing")

        ageing_display = ageing_summary.copy()
        ageing_display["balance_due"] = ageing_display[
            "balance_due"
        ].map(lambda value: f"₹{value:,.0f}")

        st.dataframe(
            ageing_display,
            use_container_width=True,
            hide_index=True
        )

        ageing_chart = px.bar(
            ageing_summary,
            x="ageing_category",
            y="balance_due",
            title="Outstanding Receivables by Ageing Bucket",
            labels={
                "ageing_category": "Ageing Category",
                "balance_due": "Outstanding Amount (₹)"
            }
        )

        st.plotly_chart(ageing_chart, use_container_width=True)

        if abs(ageing_difference) < 0.01:
            st.success(
                f"Ageing reconciliation passed. "
                f"Bucket total matches open receivables: "
                f"₹{ageing_total:,.2f}"
            )
        else:
            st.error(
                f"Ageing reconciliation failed. Difference: "
                f"₹{ageing_difference:,.2f}"
            )

        # Clients with the highest overdue amounts
        st.subheader("Clients with Highest Overdue Money")

        st.dataframe(
            overdue_clients.head(10).style.format({
                "balance_due": "₹{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )

        # Client payment behaviour
        st.subheader("Average Days to Pay by Client")

        st.caption(
            "Based on paid invoices only. Compare average payment "
            "days with the client's agreed payment terms."
        )

        st.dataframe(
            payment_behaviour.head(10).style.format({
                "average_days_to_pay": "{:.1f}",
                "payment_terms_days": "{:.0f}",
                "days_over_terms": "{:+.1f}"
            }),
            use_container_width=True,
            hide_index=True
        )

        # Monthly cash in versus cash out
        st.subheader("Monthly Cash In versus Cash Out")

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Cash In", f"₹{total_cash_in / 10000000:.2f} Cr")
        col2.metric("Paid Expense Cash Out", f"₹{total_cash_out / 10000000:.2f} Cr")
        col3.metric("Net Cash Movement", f"₹{net_cash_movement / 10000000:.2f} Cr")

        cash_chart_data = (
            monthly_cash_display.reset_index()
            .rename(columns={"index": "month"})
            .melt(
                id_vars="month",
                value_vars=["cash_in", "cash_out"],
                var_name="cash_type",
                value_name="amount"
            )
        )

        cash_chart = px.bar(
            cash_chart_data,
            x="month",
            y="amount",
            color="cash_type",
            barmode="group",
            title="Monthly Cash Received and Paid",
            labels={
                "month": "Month",
                "amount": "Amount (₹)",
                "cash_type": "Cash Type"
            }
        )

        st.plotly_chart(cash_chart, use_container_width=True)

        st.dataframe(
            monthly_cash_display.style.format({
                "cash_in": "₹{:,.2f}",
                "cash_out": "₹{:,.2f}",
                "net_cash_movement": "₹{:,.2f}"
            }),
            use_container_width=True
        )

        # Business interpretation
        st.subheader("Business Findings")

        if not overdue_clients.empty:
            top_client = overdue_clients.iloc[0]

            st.write(
                f"**Highest overdue exposure:** "
                f"{top_client['client_name']} has "
                f"₹{top_client['balance_due']:,.0f} overdue."
            )

        if not payment_behaviour.empty:
            slow_client = payment_behaviour.iloc[0]

            st.write(
                f"**Slowest average payer:** "
                f"{slow_client['client_name']} takes "
                f"{slow_client['average_days_to_pay']:.1f} days on "
                f"average, against agreed terms of "
                f"{slow_client['payment_terms_days']} days."
            )

        st.write(
            "**Finance recommendation:** Review clients whose "
            "average payment time exceeds agreed terms. Confirm "
            "contract terms, reasons for delays, outstanding "
            "exposure and expected collection dates."
        )

        st.info(
            "Cash movement includes invoice payments received and "
            "paid expenses only. It does not represent complete "
            "company cash flow because payroll and other cash "
            "movements are not included."
        )

    except (KeyError, ValueError, zipfile.BadZipFile) as error:
        st.error(f"Task 12 data could not be processed: {error}")

except Exception as error:
    st.error("The dashboard could not load the metric views.")
    st.exception(error)
