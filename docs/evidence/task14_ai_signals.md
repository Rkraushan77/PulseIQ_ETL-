# Task 14: AI Signals Dashboard

## Objective
Display AI-generated anomaly signals, financial exposure, workforce forecasts, prediction intervals and attrition-risk signals.

## Anomaly findings
- Flagged anomaly records: 405
- Total reported money at risk: INR 31,421,239.07
- Highest exposure: STATISTICAL_OUTLIER — INR 19,432,986.26
- Second highest: GROSS_ABOVE_NORM — INR 9,417,924.27

Note: Reported exposure may contain overlapping records and is not confirmed financial loss.

## Forecast findings
- Forecast metrics: ending headcount and monthly attrition rate.
- Forecast model version: trend-seasonal-baseline-0.1
- Training data through: September 2026
- Forecast period: October 2026 to March 2027.
- Prediction range: 80% prediction interval.
- Actual data ends in September 2026.
- No overlapping actual and forecast months were available.
- Forecast error is therefore marked as unavailable, not estimated.

## Attrition-risk signals
- Risk bands are displayed as aggregated employee counts.
- Groups smaller than five are hidden.
- Model output is treated as an HR support signal, never as an employment decision.

## Responsible AI notes
- Anomaly flags require human investigation.
- Forecasts are estimates, not guaranteed outcomes.
- Prediction intervals communicate uncertainty.
- Forecast accuracy must be evaluated when matching actual data becomes available.

## Deliverable
Streamlit page: pages/14_AI_Signals.py
