import streamlit as st
import pandas as pd
import numpy as np
import math

def snap_doi(eoq, daily_demand, valid_dois):
    if daily_demand <= 0 or eoq <= 0:
        return 0
    raw_doi = eoq / daily_demand
    return min(valid_dois, key=lambda x: abs(x - raw_doi))

st.title("📦 EOQ Calculator with Dual CSV Upload")

# User Inputs
monthly_salary = st.number_input("💰 Monthly Salary (IDR)", value=8000000)
safety_factor = st.number_input("🛡️ Safety Factor (Z)", value=1.65)

cost_per_minute = monthly_salary / (22 * 8 * 60)  # 22 workdays × 8 hours/day × 60 min

# File Uploads
uploaded_demand = st.file_uploader("📄 Upload Demand & Order Time CSV", type=["csv"])
uploaded_holding = st.file_uploader("🏢 Upload Holding Cost CSV", type=["csv"])

if uploaded_demand and uploaded_holding:
    try:
        df_demand = pd.read_csv(uploaded_demand)
        df_holding = pd.read_csv(uploaded_holding)

        # Clean and standardize keys

        def clean_id(val):
            val = str(val).strip()
            return val.replace(".0", "") if val.endswith(".0") else val
        
        # Apply to both dataframes
        for df in [df_demand, df_holding]:
            df['product_id'] = df['product_id'].apply(clean_id)
            df['location_id'] = df['location_id'].apply(clean_id)
        #for df in [df_demand, df_holding]:
            #df['product_id'] = df['product_id'].astype(str).str.strip()
            #df['location_id'] = df['location_id'].astype(str).str.strip()

        # Clean holding cost (remove 'Rp', commas)
        df_holding['holding_cost'] = df_holding['holding_cost'].astype(str).replace('[^0-9.]', '', regex=True).astype(float)

        st.subheader("Preview Uploaded Files")
        st.write("Demand File:")
        st.dataframe(df_demand.head())
        st.write("Holding Cost File:")
        st.dataframe(df_holding.head())

        # Merge on product_id and location_id
        df = pd.merge(df_demand, df_holding, on=['product_id', 'location_id'], how='inner')

        # Calculate adjusted annual demand
        df['adjusted_demand'] = df['avg_sales_final'] * 365 + safety_factor * df['demand_std_dev']
        df['ordering_cost'] = df['vendor_frequency'] * df['time_(mins)'] * cost_per_minute * 52
        df['annual_holding_cost'] = df['holding_cost'] * 365

        # EOQ formula
        df['EOQ'] = np.sqrt((2 * df['adjusted_demand'] * df['ordering_cost']) / df['annual_holding_cost'])
        df['EOQ'] = df['EOQ'].fillna(0).round(2)

        # DOI calculation
        df["daily_demand"] = df["adjusted_demand"] / 365
        
        valid_dois = [7, 14, 21, 28]
        df["DOI"] = df.apply(
            lambda row: snap_doi(row["EOQ"], row["daily_demand"], valid_dois=valid_dois), axis=1
        )
        #df['DOI'] = (df['EOQ'] / (df['avg_sales_final'] / 365)).replace([np.inf, -np.inf], 0).fillna(0).round(0).astype(int)

        # Show results
        st.success("✅ EOQ Calculated")
        st.dataframe(df[['product_id', 'location_id', 'EOQ', 'DOI']])

        # Download
        st.download_button("📥 Download EOQ Results", df.to_csv(index=False), file_name="eoq_results.csv")

        st.subheader("📊 EOQ vs. DOI Visualization")
        chart_data = merged_df[["product_id", "EOQ", "DOI"]].dropna()
        chart = alt.Chart(chart_data).mark_circle(size=60).encode(
            x=alt.X("EOQ", title="Economic Order Quantity"),
            y=alt.Y("DOI", title="Snapped DOI (Days)"),
            tooltip=["product_id", "EOQ", "DOI"]
        ).interactive().properties(height=400)
        st.altair_chart(chart, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error processing files: {e}")
else:
    st.info("Upload both CSV files to proceed.")
