
import duckdb
import streamlit as st
import plotly.express as px
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

except Exception as error:
    st.error("The dashboard could not load the metric views.")
    st.exception(error)
