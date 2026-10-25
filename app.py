import duckdb
import streamlit as st
import plotly.express as px

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
        SELECT department_id, department_name, headcount
        FROM metric_dashboard_department
        ORDER BY headcount DESC
    """).df()

    locations = con.execute("""
        SELECT work_location, employees
        FROM metric_dashboard_location
        ORDER BY employees DESC
    """).df()

    work_modes = con.execute("""
        SELECT work_mode, employees
        FROM metric_dashboard_work_mode
        ORDER BY employees DESC
    """).df()

    con.close()
    headcount["month_end"] = headcount["month_end"].astype("datetime64[ns]")
    return headcount, departments, locations, work_modes


try:
    headcount, departments, locations, work_modes = load_data()

    st.sidebar.header("Dashboard Filters")

    all_departments = sorted(departments["department_name"].tolist())
    selected_departments = st.sidebar.multiselect(
        "Department",
        all_departments,
        default=all_departments,
        placeholder="Select departments"
    )

    min_date = max(headcount["month_end"].min().date(), __import__("datetime").date(2025, 4, 1))
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

    filtered_headcount = headcount[
        (headcount["department_id"].isin(
            departments.loc[
                departments["department_name"].isin(selected_departments),
                "department_id"
            ]
        ))
        & (headcount["month_end"].dt.date >= start_date)
        & (headcount["month_end"].dt.date <= end_date)
    ]

    latest_month = filtered_headcount["month_end"].max()
    if filtered_headcount.empty:
        st.warning("No headcount data matches these filters.")
        st.stop()

    latest_data = filtered_headcount[
        filtered_headcount["month_end"] == latest_month
    ]
    current_headcount = int(latest_data["headcount"].sum())

    previous_months = sorted(
        filtered_headcount["month_end"].dropna().unique()
    )
    previous_headcount = None

    if len(previous_months) >= 2:
        previous_data = filtered_headcount[
            filtered_headcount["month_end"] == previous_months[-2]
        ]
        previous_headcount = int(previous_data["headcount"].sum())

    change = (
        current_headcount - previous_headcount
        if previous_headcount is not None else None
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Headcount", current_headcount)
    col2.metric(
        "Change vs previous month",
        change if change is not None else "N/A"
    )
    col3.metric("Departments selected", len(selected_departments))

    st.subheader("Headcount trend")
    trend = (
        filtered_headcount.groupby("month_end", as_index=False)["headcount"]
        .sum()
        .sort_values("month_end")
    )

    fig_trend = px.line(
        trend,
        x="month_end",
        y="headcount",
        markers=True,
        labels={"month_end": "Month", "headcount": "Employees"},
        title="How headcount has changed over time"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    if len(trend) >= 2:
        first_count = int(trend.iloc[0]["headcount"])
        last_count = int(trend.iloc[-1]["headcount"])
        difference = last_count - first_count
        direction = "increased" if difference > 0 else (
            "decreased" if difference < 0 else "remained unchanged"
        )
        st.caption(
            f"Insight: Headcount {direction} by "
            f"{abs(difference):,} employees across the selected period."
        )
    else:
        st.caption("Insight: Select a wider period to compare headcount.")

    st.subheader("Department workforce")
    department_chart = departments[
        departments["department_name"].isin(selected_departments)
    ].sort_values("headcount", ascending=False)

    fig_department = px.bar(
        department_chart,
        x="department_name",
        y="headcount",
        labels={
            "department_name": "Department",
            "headcount": "Employees"
        },
        title="Engineering has the largest reported department headcount"
    )
    st.plotly_chart(fig_department, use_container_width=True)

    if not department_chart.empty:
        largest = department_chart.iloc[0]
        st.caption(
            f"Insight: {largest['department_name']} has the highest "
            f"reported headcount ({int(largest['headcount'])} employees)."
        )

    st.subheader("Employees by city")
    fig_location = px.bar(
        locations.sort_values("employees", ascending=False),
        x="work_location",
        y="employees",
        labels={"work_location": "City", "employees": "Employees"},
        title="Bengaluru has the largest reported workforce by city"
    )
    st.plotly_chart(fig_location, use_container_width=True)

    if not locations.empty:
        largest_city = locations.sort_values(
            "employees", ascending=False
        ).iloc[0]
        st.caption(
            f"Insight: {largest_city['work_location']} has the most "
            f"employees ({int(largest_city['employees'])})."
        )

    st.subheader("Work mode distribution")
    fig_mode = px.bar(
        work_modes.sort_values("employees", ascending=False),
        x="work_mode",
        y="employees",
        labels={"work_mode": "Work mode", "employees": "Employees"},
        title="Hybrid is the most common recorded work mode"
    )
    st.plotly_chart(fig_mode, use_container_width=True)

    if not work_modes.empty:
        largest_mode = work_modes.sort_values(
            "employees", ascending=False
        ).iloc[0]
        st.caption(
            f"Insight: {largest_mode['work_mode']} is the most common "
            f"recorded work mode ({int(largest_mode['employees'])} employees)."
        )

    st.caption(
        "Data note: Department headcount and current employee distributions "
        "come from different governed views. Their totals may differ."
    )

except Exception as error:
    st.error("The dashboard could not load the metric views.")
    st.exception(error)
