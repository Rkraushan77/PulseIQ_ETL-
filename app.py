
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

except Exception as error:
    st.error("The dashboard could not load the metric views.")
    st.exception(error)
