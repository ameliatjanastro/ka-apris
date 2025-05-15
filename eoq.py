import streamlit as st
import pandas as pd
import numpy as np
import math
import altair as alt


def calculate_clipped_doi(eoq, daily_demand, vendor_freq):
    if daily_demand <= 0 or eoq <= 0:
        return 0
    raw_doi = eoq / daily_demand
    min_doi = 3 if vendor_freq == 2 else 7
    return round(min(max(raw_doi, min_doi), 28), 2)


def clean_id(val):
    val = str(val).strip()
    return val.replace(".0", "") if val.endswith(".0") else val


st.title("📦 EOQ Calculator with Dual & Triple CSV Upload")

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
        for df in [df_demand, df_holding]:
            df['product_id'] = df['product_id'].apply(clean_id)
            df['location_id'] = df['location_id'].apply(clean_id)

        # Clean holding cost (remove 'Rp', commas, etc)
        df_holding['holding_cost'] = df_holding['holding_cost'].astype(float)

        st.subheader("Preview Uploaded Files")
        st.write("Demand File:")
        st.dataframe(df_demand.head(5000))
        st.write("Holding Cost File:")
        st.dataframe(df_holding.head())

        # Merge on product_id and location_id
        df = pd.merge(df_demand, df_holding, on=['product_id', 'location_id'], how='inner')

        # Calculate adjusted annual demand
        df['adjusted_demand'] = (df['avg_sales_final'] + safety_factor * df['demand_std_dev']) * 30
        df['ordering_cost'] = 101539.972 * (1+(df['cogs_contr']*100))
        df['monthly_holding_cost'] = df['holding_cost'] * 30

        # EOQ formula
        df['EOQ'] = (np.sqrt((2 * df['adjusted_demand'] * df['ordering_cost']) / df['monthly_holding_cost']))#*14/df["vendor_frequency"])
        df['EOQ'] = df['EOQ'].fillna(0).round(2)

        # DOI calculation
        df["daily_demand"] = df["adjusted_demand"] / 30
        df["opt_freq"] = df["adjusted_demand"]/df['EOQ']
        df["DOI"] = df['EOQ']/df["daily_demand"] #df.apply(
            #lambda row: calculate_clipped_doi(row["EOQ"], row["daily_demand"], row["vendor_frequency"]),
            #axis=1
        #)

        df["opt_freq_capped"] = df["opt_freq"].apply(lambda x: min(x, 12))

        # Calculate frequency reduction ratio where opt_freq > 12
        df["freq_reduction_pct"] = np.where(
            df["opt_freq"] > 12,
            (df["opt_freq"] - 12) / df["opt_freq"],
            0
        )
        
        # Increase EOQ by the same % as the reduction
        df["EOQ_final"] = df["EOQ"] * (1 + df["freq_reduction_pct"])
        
        # Recalculate DOI with EOQ_final
        df["DOI_final"] = df["EOQ_final"] / df["avg_sales_final"]

        st.success("✅ EOQ Calculated")
        #st.dataframe(df[['product_id', 'location_id', 'EOQ', 'opt_freq', 'DOI']])
        st.dataframe(df[['product_id', 'location_id', 'EOQ', 'EOQ_final', 'opt_freq_capped', 'DOI_final']])

        # Download EOQ results
        st.download_button("📥 Download EOQ Results", df.to_csv(index=False), file_name="eoq_results.csv")

        # EOQ vs DOI Visualization
        st.subheader("📊 EOQ vs. DOI Visualization")
        chart_data = df[["product_id", "EOQ", "DOI"]].dropna()
        chart = alt.Chart(chart_data).mark_circle(size=60).encode(
            x=alt.X("EOQ", title="Economic Order Quantity"),
            y=alt.Y("DOI", title="Snapped DOI (Days)"),
            tooltip=["product_id", "EOQ", "DOI"]
        ).interactive().properties(height=400)
        st.altair_chart(chart, use_container_width=True)

        # --- Additional: Upload Pcs per Carton & COGS ---
        uploaded_cogs = st.file_uploader("📦 Upload Pcs per Carton & COGS CSV", type=["csv"])

        if uploaded_cogs:
            df_cogs = pd.read_csv(uploaded_cogs)
            df_cogs['product_id'] = df_cogs['product_id'].apply(clean_id)

            st.write("COGS File:")
            st.dataframe(df_cogs.head())

            # Merge with main dataframe
            df = pd.merge(df, df_cogs[['product_id', 'pcs_per_carton', 'cogs']], on='product_id', how='left')

            # Round EOQ up to nearest carton size
            df['EOQ_rounded'] = np.ceil(df['EOQ'] / df['pcs_per_carton']) * df['pcs_per_carton']

            st.subheader("🎚️ Adjust EOQ Multiplier and See COGS Impact")
            multiplier = st.slider("EOQ Multiplier (simulate volume discount)", 1.0, 1.1, 1.2, step=0.05)

            # Adjust EOQ with multiplier and round again
            df['EOQ_adj'] = np.ceil(df['EOQ_rounded'] * multiplier / df['pcs_per_carton']) * df['pcs_per_carton']

            # Adjust COGS assuming linear discount: x% EOQ increase = x% COGS decrease, minimum COGS 0
            def adjust_cogs(row):
                if pd.isna(row['cogs']) or row['EOQ_rounded'] == 0:
                    return row['cogs']
                increase_ratio = (row['EOQ_adj'] - row['EOQ_rounded']) / row['EOQ_rounded']
                adjusted = row['cogs'] * max(1 - increase_ratio, 0)
                return adjusted

            df['cogs_adj'] = df.apply(adjust_cogs, axis=1)

            st.success("✅ EOQ Multiplier & COGS Adjusted")
            st.dataframe(df[['product_id', 'location_id', 'EOQ', 'pcs_per_carton', 'EOQ_rounded', 'EOQ_adj', 'cogs', 'cogs_adj']])

            # Download adjusted results
            st.download_button("📥 Download Adjusted EOQ & COGS", df.to_csv(index=False), file_name="eoq_cogs_adjusted.csv")

        else:
            st.info("Upload Pcs per Carton & COGS CSV to continue.")

    except Exception as e:
        st.error(f"❌ Error processing files: {e}")

else:
    st.info("Upload both Demand & Holding Cost CSV files to proceed.")

