import duckdb
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Task 13 | Cross Department Impact",
    layout="wide"
)

st.title("Cross-Department Impact Dashboard")
st.caption("Headcount, payroll, attendance, leave and attrition | Apr 2025 – Sep 2026")

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

df = con.execute("""
    SELECT *
    FROM task13_cross_department
    ORDER BY month_end, department_id
""").fetchdf()

con.close()

if df.empty:
    st.warning("Task 13 dataset is empty.")
    st.stop()

df["month_end"] = df["month_end"].astype(str)

departments = sorted(df["department_name"].dropna().unique())
selected_month = st.selectbox(
    "Select reporting month",
    sorted(df["month_end"].unique(), reverse=True)
)

comparison = df[df["month_end"] == selected_month].copy()

st.subheader("Department comparison")

total_cost = comparison["employer_cost"].sum()
total_overtime = comparison["overtime_cost"].sum()
total_exits = comparison["exits"].sum()
total_leave = comparison["approved_leave_days"].sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Employer Cost", f"INR {total_cost / 10000000:.2f} Cr")
col2.metric("Overtime Cost", f"INR {total_overtime / 100000:.2f} L")
col3.metric("Employee Exits", int(total_exits))
col4.metric("Approved Leave Days", int(total_leave))

st.markdown("### Cost, overtime and attrition comparison")


chart_data = comparison[
    ["department_name", "employer_cost", "overtime_cost",
     "monthly_exit_rate_pct"]
].melt(
    id_vars="department_name",
    var_name="metric",
    value_name="actual_value"
)

chart_data["metric"] = chart_data["metric"].map({
    "employer_cost": "Employer Cost",
    "overtime_cost": "Overtime Cost",
    "monthly_exit_rate_pct": "Exit Rate"
})

chart_data["comparison_index"] = (
    chart_data.groupby("metric")["actual_value"]
    .transform(
        lambda x: x / x.max() * 100 if x.max() > 0 else x
    )
)


fig = px.bar(
    chart_data,
    x="comparison_index",
    y="department_name",
    color="metric",
    barmode="group",
    orientation="h",
    hover_data={"actual_value": ":,.2f"},
    title=f"Department comparison - {selected_month}",
    labels={
        "department_name": "Department",
        "comparison_index": "Relative index (0-100)",
        "metric": "Measure",
        "actual_value": "Actual value"
    }
)

fig.update_layout(
    height=650,
    xaxis_range=[0, 110],
    yaxis_title="Department",
    legend_title="Measure"
)

st.plotly_chart(fig, use_container_width=True)


st.caption(
    "Each measure is scaled separately. The highest department value "
    "for each measure equals 100. Hover to see actual values."
)

st.markdown("### Monthly department details")

selected_department = st.selectbox(
    "Choose department",
    departments
)

department_data = df[
    df["department_name"] == selected_department
].copy()

st.dataframe(
    department_data[
        [
            "month_end",
            "headcount",
            "gross_pay",
            "net_pay",
            "employer_cost",
            "overtime_cost",
            "attendance_rate_pct",
            "approved_leave_days",
            "leave_days_per_head",
            "exits",
            "monthly_exit_rate_pct",
            "cost_per_employee"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.markdown("### Monthly cost and attrition trends")

trend = department_data[
    ["month_end", "employer_cost", "overtime_cost", "monthly_exit_rate_pct"]
].melt(
    id_vars="month_end",
    var_name="metric",
    value_name="value"
)

trend["index_value"] = trend.groupby("metric")["value"].transform(
    lambda values: (
        (values - values.min()) / (values.max() - values.min()) * 100
        if values.max() != values.min()
        else 0
    )
)

trend_fig = px.line(
    trend,
    x="month_end",
    y="index_value",
    color="metric",
    markers=True,
    title=f"Indexed monthly trends — {selected_department}",
    labels={
        "month_end": "Month",
        "index_value": "Relative index (0–100)",
        "metric": "Metric"
    }
)

st.plotly_chart(trend_fig, use_container_width=True)

st.markdown("### Data quality and interpretation")

st.write(
    "- Each source was aggregated to department-month grain before joining."
)
st.write(
    "- Payroll overtime hours were reconciled against attendance overtime hours."
)
st.write(
    "- Only approved leave on working days was included."
)
st.write(
    "- Employer cost already includes overtime pay; overtime cost is displayed "
    "separately and is not added again."
)
st.write(
    "- The exit rate is a descriptive measure, not proof that overtime causes attrition."
)
st.write(
    "- The PQ-13 reference file was not available in the project files, "
    "so reference reconciliation remains pending."
)
