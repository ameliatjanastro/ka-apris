import streamlit as st
import pandas as pd
import numpy as np
import math

# EOQ calculation function with fixed safety factor
def calculate_dynamic_eoq(
    forecast_demand,
    demand_std_dev,
    cost_per_minute,
    time_minute,
    cogs,
    holding_cost
):
    safety_factor = 1.65  # Fixed
    adjusted_demand = (forecast_demand + (safety_factor * demand_std_dev))*7
    adjusted_order_cost = (cost_per_minute) * time_minute
    adjusted_holding_cost = cogs * holding_cost

    if adjusted_holding_cost == 0:
        return 0

    eoq = math.sqrt((2 * adjusted_demand * adjusted_order_cost) / adjusted_holding_cost)
    return round(eoq, 2)

st.title("📦 EOQ Calculator (CSV Input, Safety Factor = 1.65)")

# Upload CSV
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    required_columns = [
        "vendor_id", "product_id", "forecast_demand", "demand_std_dev",
        "cost_per_minute", "time_minute", "cogs", "holding_cost","STOCK"
    ]

    if all(col in df.columns for col in required_columns):
        # Calculate EOQ for each row
        df["EOQ"] = df.apply(lambda row: calculate_dynamic_eoq(
            row["forecast_demand"],
            row["demand_std_dev"],
            row["cost_per_minute"],
            row["time_minute"],
            row["cogs"],
            row["holding_cost"]
        ), axis=1)

        df["DOI"] = ((df["EOQ"]+df["STOCK"]) / (df["forecast_demand"]*7)).apply(
    lambda x: int(x) if pd.notnull(x) and not np.isinf(x) else 0
        )
        df = df.dropna(subset=["EOQ", "forecast_demand"])

        st.success("✅ EOQ calculated successfully!")
        st.dataframe(df[["vendor_id", "product_id", "EOQ","DOI"]])
        st.download_button("📥 Download EOQ Results", df.to_csv(index=False), file_name="eoq_results.csv", mime="text/csv")
    else:
        st.error(f"CSV is missing one or more of the required columns: {', '.join(required_columns)}")
else:
    st.info("Please upload a CSV file with the required EOQ input columns.")

