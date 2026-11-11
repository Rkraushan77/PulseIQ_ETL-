import zipfile
from io import BytesIO

import pandas as pd
import streamlit as st
import plotly.graph_objects as go


st.set_page_config(
    page_title="Task 14 - AI Signals",
    page_icon="🤖",
    layout="wide"
)


# Load the required CSV files from the original ZIP file
@st.cache_data
def load_task14_data():

    with zipfile.ZipFile("data/raw/CSV.zip") as archive:

        def load_csv(filename):
            path = next(
                file for file in archive.namelist()
                if file.endswith(filename)
            )

            return pd.read_csv(
                BytesIO(archive.read(path))
            )

        anomaly = load_csv("fact_anomaly.csv")
        forecast = load_csv("fact_forecast.csv")
        attrition = load_csv("fact_attrition_risk.csv")
        headcount = load_csv("fact_headcount_monthly.csv")

    return anomaly, forecast, attrition, headcount


try:

    anomaly, forecast, attrition, headcount = load_task14_data()

    st.title("Task 14: AI Signals Dashboard")

    st.write(
        "This dashboard presents AI-generated anomaly signals, "
        "workforce forecasts and attrition-risk indicators. "
        "All outputs require human review."
    )

    st.divider()

    # Prepare anomaly data
    flagged = anomaly[
        anomaly["flagged"].astype(str).str.upper() == "Y"
    ].copy()

    anomaly_summary = (
        flagged.groupby("reason_code")
        .agg(
            records=("result_id", "count"),
            money_at_risk=("money_at_risk", "sum")
        )
        .reset_index()
        .sort_values("money_at_risk", ascending=False)
    )

    total_anomalies = len(flagged)
    total_money_at_risk = flagged["money_at_risk"].sum()

    # Prepare attrition-risk counts
    risk_summary = (
        attrition.groupby("risk_band")
        .size()
        .reset_index(name="employees")
    )

    risk_counts = dict(
        zip(risk_summary["risk_band"], risk_summary["employees"])
    )

    high_risk_count = risk_counts.get("High", 0)
    medium_risk_count = risk_counts.get("Medium", 0)

    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Flagged anomalies", f"{total_anomalies:,}")
    col2.metric(
        "Reported money at risk",
        f"₹{total_money_at_risk:,.0f}"
    )
    col3.metric("High attrition-risk signals", f"{high_risk_count:,}")
    col4.metric("Medium attrition-risk signals", f"{medium_risk_count:,}")

    st.caption(
        "Money at risk is the sum of reported anomaly exposures. "
        "It may include overlapping records and is not confirmed financial loss."
    )

    st.divider()

    # --------------------------------------------------
    # 1. ANOMALY ANALYSIS
    # --------------------------------------------------

    st.header("1. Anomalies by Type")

    st.write(
        "This chart ranks flagged anomaly categories by their reported "
        "financial exposure. Categories with zero reported money at risk "
        "are also included so operational signals are not hidden."
    )

    anomaly_chart = go.Figure()

    anomaly_chart.add_trace(
        go.Bar(
            x=anomaly_summary["money_at_risk"],
            y=anomaly_summary["reason_code"],
            orientation="h",
            text=anomaly_summary["records"],
            textposition="auto",
            hovertemplate=(
                "Anomaly: %{y}<br>"
                "Money at risk: ₹%{x:,.2f}<br>"
                "Records: %{text}<extra></extra>"
            )
        )
    )

    anomaly_chart.update_layout(
        height=480,
        xaxis_title="Reported money at risk (INR)",
        yaxis_title="Anomaly type",
        yaxis={"categoryorder": "total ascending"},
        showlegend=False
    )

    st.plotly_chart(
        anomaly_chart,
        use_container_width=True
    )

    st.caption("AI-generated, for human review")

    st.info(
        "Business interpretation: Statistical outliers and gross-pay "
        "above-norm signals account for the largest reported exposures. "
        "Finance or payroll teams should investigate the underlying records "
        "before taking corrective action."
    )

    st.subheader("Anomaly Summary")

    display_anomalies = anomaly_summary.copy()
    display_anomalies["money_at_risk"] = (
        display_anomalies["money_at_risk"].map(
            lambda value: f"₹{value:,.2f}"
        )
    )

    st.dataframe(
        display_anomalies,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # --------------------------------------------------
    # 2. FORECAST VS ACTUAL
    # --------------------------------------------------

    st.header("2. Workforce Forecast vs Actual")

    st.write(
        "The forecast uses the company-wide ALL department series. "
        "The shaded region represents the model's 80% prediction interval."
    )

    selected_metric = st.selectbox(
        "Select forecast metric",
        [
            "headcount_end",
            "attrition_rate_monthly_pct"
        ],
        format_func=lambda value: (
            "Ending Headcount"
            if value == "headcount_end"
            else "Monthly Attrition Rate (%)"
        )
    )

    forecast_data = forecast[
        (forecast["metric"] == selected_metric)
        & (forecast["department_id"] == "ALL")
    ].copy()

    forecast_data["forecast_month"] = pd.to_datetime(
        forecast_data["forecast_month"]
    )

    forecast_data = forecast_data.sort_values("forecast_month")

    # Prepare historical actual values
    actual_data = headcount.copy()

    actual_data["month_start_date"] = pd.to_datetime(
        actual_data["month_start_date"]
    )

    if selected_metric == "headcount_end":

        actual_summary = (
            actual_data.groupby("month_start_date")["headcount_end"]
            .sum()
            .reset_index()
        )

        actual_summary = actual_summary.rename(
            columns={"headcount_end": "actual_value"}
        )

    else:

        actual_summary = (
            actual_data.groupby("month_start_date")
            .agg(
                total_exits=("exits", "sum"),
                total_headcount_start=("headcount_start", "sum")
            )
            .reset_index()
        )

        actual_summary["actual_value"] = (
            actual_summary["total_exits"]
            / actual_summary["total_headcount_start"].replace(0, pd.NA)
        ) * 100

    actual_summary = actual_summary.dropna(
        subset=["actual_value"]
    )

    # Build forecast chart
    forecast_chart = go.Figure()

    forecast_chart.add_trace(
        go.Scatter(
            x=actual_summary["month_start_date"],
            y=actual_summary["actual_value"],
            mode="lines",
            name="Historical actual",
            line={"width": 2}
        )
    )

    # Lower boundary of the 80% prediction interval
    forecast_chart.add_trace(
        go.Scatter(
            x=forecast_data["forecast_month"],
            y=forecast_data["lower_80"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip"
        )
    )

    # Upper boundary fills the area between lower and upper
    forecast_chart.add_trace(
        go.Scatter(
            x=forecast_data["forecast_month"],
            y=forecast_data["upper_80"],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(100, 149, 237, 0.20)",
            name="80% prediction interval",
            hoverinfo="skip"
        )
    )

    forecast_chart.add_trace(
        go.Scatter(
            x=forecast_data["forecast_month"],
            y=forecast_data["forecast_value"],
            mode="lines+markers",
            name="AI forecast",
            line={"width": 3, "dash": "dash"}
        )
    )

    if selected_metric == "headcount_end":
        y_axis_title = "Employees"
    else:
        y_axis_title = "Monthly attrition rate (%)"

    forecast_chart.update_layout(
        height=480,
        xaxis_title="Month",
        yaxis_title=y_axis_title,
        hovermode="x unified"
    )

    st.plotly_chart(
        forecast_chart,
        use_container_width=True
    )

    st.caption("AI-generated, for human review")

    st.info(
        "Business interpretation: Historical actuals are shown separately "
        "from future model forecasts. The shaded band represents the model's "
        "80% prediction interval, not a guarantee that actual results will "
        "fall inside it."
    )

    # Model information
    if not forecast_data.empty:

        model_method = forecast_data["method"].iloc[0]
        model_version = forecast_data["model_version"].iloc[0]
        trained_through = forecast_data["trained_through"].iloc[0]

        st.caption(
            f"Model: {model_version} | "
            f"Method: {model_method} | "
            f"Trained through: {trained_through}"
        )

    st.divider()

    # --------------------------------------------------
    # 3. FORECAST ERROR TABLE
    # --------------------------------------------------

    st.header("3. Forecast Error Analysis")

    st.write(
        "Forecast error can only be calculated when actual data is "
        "available for the same month and metric."
    )

    actual_lookup = dict(
        zip(
            actual_summary["month_start_date"].dt.strftime("%Y-%m"),
            actual_summary["actual_value"]
        )
    )

    error_rows = []

    for _, row in forecast_data.iterrows():

        month = row["forecast_month"].strftime("%Y-%m")
        actual_value = actual_lookup.get(month)

        if actual_value is not None:

            absolute_error = abs(
                row["forecast_value"] - actual_value
            )

            if actual_value != 0:
                error_percentage = (
                    absolute_error / abs(actual_value)
                ) * 100
            else:
                error_percentage = None

            status = "Actual available"

        else:

            absolute_error = None
            error_percentage = None
            status = "Actual not available yet"

        error_rows.append({
            "Forecast Month": month,
            "Forecast Value": round(row["forecast_value"], 2),
            "Actual Value": actual_value,
            "Absolute Error": absolute_error,
            "Error Percentage": error_percentage,
            "Status": status
        })

    error_table = pd.DataFrame(error_rows)

    st.dataframe(
        error_table,
        use_container_width=True,
        hide_index=True
    )

    if error_table["Actual Value"].notna().any():

        st.success(
            "Forecast errors have been calculated for months "
            "where actual values are available."
        )

    else:

        st.warning(
            "No forecast error can be calculated yet. Actual data ends "
            "in September 2026, while the forecast starts in October 2026. "
            "There are zero overlapping months."
        )

    st.divider()

    # --------------------------------------------------
    # 4. ATTRITION RISK SIGNALS
    # --------------------------------------------------

    st.header("4. AI Attrition-Risk Signals")

    st.write(
        "This section shows the number of employees in each model-generated "
        "risk band. Employee-level details are intentionally not displayed."
    )

    # Hide very small groups
    visible_risks = risk_summary[
        risk_summary["employees"] >= 5
    ].copy()

    suppressed_count = len(
        risk_summary[risk_summary["employees"] < 5]
    )

    if not visible_risks.empty:

        risk_chart = go.Figure()

        risk_chart.add_trace(
            go.Bar(
                x=visible_risks["risk_band"],
                y=visible_risks["employees"],
                text=visible_risks["employees"],
                textposition="auto"
            )
        )

        risk_chart.update_layout(
            height=350,
            xaxis_title="AI risk band",
            yaxis_title="Employee count",
            showlegend=False
        )

        st.plotly_chart(
            risk_chart,
            use_container_width=True
        )

        st.caption("AI-generated, for human review")

    if suppressed_count > 0:

        st.caption(
            f"{suppressed_count} risk group(s) with fewer than "
            "5 employees have been hidden."
        )

    st.info(
        "HR interpretation: These are model-generated support signals, "
        "not confirmed predictions of employee resignation. HR should "
        "review context and speak with employees appropriately. "
        "The model must never be used as the sole basis for employment decisions."
    )

    st.caption(
        "Risk model version: "
        + str(attrition["model_version"].iloc[0])
    )

    st.divider()

    st.subheader("Task 14: Important Limitations")

    st.write(
        """
        - Anomaly flags require investigation and are not proof of fraud or error.
        - Reported money at risk may contain overlapping exposures.
        - Forecasts are model estimates, not guaranteed future outcomes.
        - The 80% prediction interval communicates uncertainty.
        - Forecast accuracy cannot be evaluated until matching actual months arrive.
        - Attrition-risk bands are support signals for human review, never decisions.
        """
    )

    st.success("Task 14 AI Signals Dashboard loaded successfully.")

except Exception as error:

    st.error("The AI Signals dashboard could not load.")
    st.exception(error)
