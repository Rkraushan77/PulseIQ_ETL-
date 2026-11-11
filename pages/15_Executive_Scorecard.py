
import streamlit as st
import duckdb
import pandas as pd

# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Executive Company Health Scorecard",
    page_icon="📊",
    layout="wide"
)

# A4 print layout
st.markdown("""
<style>
@media print {
    @page {
        size: A4 landscape;
        margin: 10mm;
    }

    [data-testid="stSidebar"],
    header,
    footer,
    [data-testid="stToolbar"],
    .stSelectbox {
        display: none !important;
    }

    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    [data-testid="stMetric"] {
        break-inside: avoid;
    }
}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

con = duckdb.connect(
    "data/warehouse.duckdb",
    read_only=True
)


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("Executive Company Health Scorecard")

st.caption(
    "Company-wide workforce and payroll performance"
)


# --------------------------------------------------
# MONTH SELECTOR
# --------------------------------------------------

months = con.execute("""
    SELECT DISTINCT period_start
    FROM metric_payroll_monthly
    ORDER BY period_start DESC
""").df()

if months.empty:
    st.error("No payroll reporting months are available.")
    con.close()
    st.stop()

month_options = months["period_start"].tolist()

selected_month = st.selectbox(
    "Select reporting month",
    month_options,
    format_func=lambda x: x.strftime("%B %Y")
)

previous_month = (
    pd.Timestamp(selected_month) -
    pd.DateOffset(months=1)
).date()

month_end = (
    pd.Timestamp(selected_month) +
    pd.offsets.MonthEnd(0)
).date()

previous_month_end = (
    pd.Timestamp(previous_month) +
    pd.offsets.MonthEnd(0)
).date()

st.caption(
    "Reporting period: " +
    selected_month.strftime("%B %Y")
)


# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------

def get_value(query, params=None):

    result = con.execute(
        query,
        params or []
    ).fetchone()

    if result is None:
        return None

    return result[0]


# --------------------------------------------------
# HEADCOUNT
# --------------------------------------------------

headcount = get_value("""
    SELECT SUM(headcount)
    FROM metric_headcount_monthly
    WHERE month_end = ?
""", [month_end])

previous_headcount = get_value("""
    SELECT SUM(headcount)
    FROM metric_headcount_monthly
    WHERE month_end = ?
""", [previous_month_end])

headcount = headcount or 0


# --------------------------------------------------
# NEW HIRES
# --------------------------------------------------

hires = get_value("""
    SELECT SUM(hires)
    FROM metric_hires_monthly
    WHERE month_start = ?
""", [selected_month])

previous_hires = get_value("""
    SELECT SUM(hires)
    FROM metric_hires_monthly
    WHERE month_start = ?
""", [previous_month])

hires = hires or 0


# --------------------------------------------------
# CURRENT MONTH PAYROLL
# --------------------------------------------------

payroll = con.execute("""
    SELECT
        SUM(gross_pay),
        SUM(net_pay),
        SUM(employer_cost),
        SUM(overtime_pay),
        SUM(lop_days),
        SUM(paid_employees)
    FROM metric_payroll_monthly
    WHERE period_start = ?
""", [selected_month]).fetchone()

gross_pay = payroll[0] or 0
net_pay = payroll[1] or 0
employer_cost = payroll[2] or 0
overtime_pay = payroll[3] or 0
lop_days = payroll[4] or 0
paid_employees = payroll[5] or 0

# Cost per paid employee
cost_per_employee = (
    employer_cost / paid_employees
    if paid_employees > 0 else 0
)

# Overtime share
overtime_share = (
    overtime_pay / employer_cost * 100
    if employer_cost > 0 else 0
)


# --------------------------------------------------
# PREVIOUS MONTH PAYROLL
# --------------------------------------------------

previous_payroll = con.execute("""
    SELECT
        SUM(gross_pay),
        SUM(net_pay),
        SUM(employer_cost),
        SUM(overtime_pay),
        SUM(lop_days),
        SUM(paid_employees)
    FROM metric_payroll_monthly
    WHERE period_start = ?
""", [previous_month]).fetchone()

previous_gross = previous_payroll[0]
previous_net = previous_payroll[1]
previous_employer_cost = previous_payroll[2]
previous_overtime = previous_payroll[3]
previous_lop = previous_payroll[4]
previous_paid = previous_payroll[5]

# Previous cost per employee
if previous_employer_cost is not None and previous_paid:
    previous_cost_per_employee = (
        previous_employer_cost / previous_paid
    )
else:
    previous_cost_per_employee = None

# Previous overtime share
if previous_employer_cost and previous_overtime is not None:
    previous_overtime_share = (
        previous_overtime / previous_employer_cost * 100
    )
else:
    previous_overtime_share = None


# --------------------------------------------------
# OVERTIME TARGET
# --------------------------------------------------

target_data = con.execute("""
    SELECT
        SUM(
            p.employer_cost *
            k.overtime_share_target_pct
        ) / NULLIF(SUM(p.employer_cost), 0)
    FROM metric_payroll_monthly p
    JOIN kpi_targets k
        ON p.department_id = k.department_id
    WHERE p.period_start = ?
      AND k.month = ?
""", [
    selected_month,
    selected_month.strftime("%Y-%m-%d")
]).fetchone()

overtime_target = target_data[0]

if overtime_target is not None:

    if overtime_share <= overtime_target:
        overtime_status = "Within target"
    else:
        overtime_status = "Above target"

    target_text = "{:.2f}%".format(overtime_target)

else:
    overtime_status = "No target defined"
    target_text = "No target defined"


# --------------------------------------------------
# VALUE FORMATTING FUNCTION
# --------------------------------------------------

def format_value(value, number_format):

    if number_format == "currency":

        if abs(value) >= 10000000:
            return "₹{:.2f} Cr".format(
                value / 10000000
            )

        elif abs(value) >= 100000:
            return "₹{:.2f} L".format(
                value / 100000
            )

        else:
            return "₹{:,.0f}".format(value)

    elif number_format == "percent":
        return "{:.2f}%".format(value)

    elif number_format == "decimal":
        return "{:,.2f}".format(value)

    else:
        return "{:,.0f}".format(value)


# --------------------------------------------------
# KPI CARD FUNCTION
# --------------------------------------------------

def show_kpi(
    column,
    title,
    value,
    previous_value,
    number_format,
    target_text="No target defined",
    status="No target defined",
    page="pages/13_Cross_Department_Impact.py"
):

    with column:

        with st.container(border=True):

            st.markdown("**" + title + "**")

            display_value = format_value(
                value,
                number_format
            )

            # Previous month comparison
            if previous_value is None:

                delta_text = "Previous month unavailable"

            else:

                difference = value - previous_value

                if number_format == "percent":

                    delta_text = (
                        "{:+.2f} percentage points".format(
                            difference
                        )
                    )

                else:

                    delta_text = (
                        format_value(
                            abs(difference),
                            number_format
                        )
                    )

                    if difference > 0:
                        delta_text = "+" + delta_text

                    elif difference < 0:
                        delta_text = "-" + delta_text

                    else:
                        delta_text = "No change"

            # Only ONE metric display
            st.metric(
                label="Current value",
                value=display_value,
                delta=delta_text,
                delta_color="off"
            )

            st.caption("Target: " + target_text)

            st.caption("Status: " + status)

            st.page_link(
                page,
                label="View department details"
            )


# --------------------------------------------------
# COMPANY PERFORMANCE SCORECARD
# --------------------------------------------------

st.divider()

st.subheader("Company Performance")

columns = st.columns(4)

show_kpi(
    columns[0],
    "Total Headcount",
    headcount,
    previous_headcount,
    "number"
)

show_kpi(
    columns[1],
    "New Hires",
    hires,
    previous_hires,
    "number"
)

show_kpi(
    columns[2],
    "Gross Payroll",
    gross_pay,
    previous_gross,
    "currency"
)

show_kpi(
    columns[3],
    "Net Payroll",
    net_pay,
    previous_net,
    "currency"
)

columns = st.columns(4)

show_kpi(
    columns[0],
    "Employer Payroll Cost",
    employer_cost,
    previous_employer_cost,
    "currency"
)

show_kpi(
    columns[1],
    "Cost Per Paid Employee",
    cost_per_employee,
    previous_cost_per_employee,
    "currency"
)

show_kpi(
    columns[2],
    "Overtime Share",
    overtime_share,
    previous_overtime_share,
    "percent",
    target_text,
    overtime_status
)

show_kpi(
    columns[3],
    "Leave Without Pay Days",
    lop_days,
    previous_lop,
    "decimal"
)


# --------------------------------------------------
# KPI DEFINITIONS AND REASONS
# --------------------------------------------------

st.divider()

st.subheader("KPI Definitions and Business Reasons")

kpi_reasons = [
    (
        "Total Headcount",
        "Measures the active workforce available to the company."
    ),
    (
        "New Hires",
        "Tracks workforce expansion and recruitment activity."
    ),
    (
        "Gross Payroll",
        "Shows total employee earnings before deductions."
    ),
    (
        "Net Payroll",
        "Shows the total amount paid to employees after deductions."
    ),
    (
        "Employer Payroll Cost",
        "Measures the total payroll expense incurred by the employer."
    ),
    (
        "Cost Per Paid Employee",
        "Shows the average employer payroll cost per paid employee."
    ),
    (
        "Overtime Share",
        "Highlights overtime expense as a percentage of employer cost."
    ),
    (
        "Leave Without Pay Days",
        "Tracks unpaid leave recorded through payroll."
    )
]

for name, reason in kpi_reasons:

    st.markdown(
        "**" + name + ":** " + reason
    )


# --------------------------------------------------
# FIVE MOST IMPORTANT KPIs
# --------------------------------------------------

st.divider()

st.subheader(
    "If Management Could Track Only Five KPIs"
)

st.markdown("""
The five highest-priority KPIs would be:

1. **Total Headcount** – workforce size.
2. **New Hires** – recruitment and workforce growth.
3. **Employer Payroll Cost** – total employee cost to the business.
4. **Cost Per Paid Employee** – average workforce cost.
5. **Overtime Share** – additional labour cost monitoring.

I would remove Gross Payroll and Net Payroll because
Employer Payroll Cost already provides the broader
company cost measure.

I would also remove Leave Without Pay Days because
it is a supporting operational measure rather than
a primary company-health measure.
""")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Data source: PulseIQ DuckDB metric views | "
    "Targets: kpi_targets | "
    "Company-level aggregated reporting"
)

con.close()
