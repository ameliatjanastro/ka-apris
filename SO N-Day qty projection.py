import streamlit as st
import pandas as pd

# Streamlit App Title
st.title("SO Quantity Estimation")

# File Upload Section
st.header("Upload Data Files")
so_file = st.file_uploader("Upload SQL-estimated SO CSV", type=["csv"])
dry_forecast_file = st.file_uploader("Upload Dry Demand Forecast CSV", type=["csv"])
fresh_cbn_forecast_file = st.file_uploader("Upload Fresh CBN Demand Forecast CSV", type=["csv"])
fresh_pgs_forecast_file = st.file_uploader("Upload Fresh PGS Demand Forecast CSV", type=["csv"])

if so_file and dry_forecast_file and fresh_cbn_forecast_file and fresh_pgs_forecast_file:
    # Load Data
    final_so_df = pd.read_csv(so_file)
    dry_forecast_df = pd.read_csv(dry_forecast_file)
    fresh_cbn_forecast_df = pd.read_csv(fresh_cbn_forecast_file)
    fresh_pgs_forecast_df = pd.read_csv(fresh_pgs_forecast_file)
    
    # Aggregate Demand Forecast
    dry_demand = dry_forecast_df["forecast_qty"].sum()
    fresh_cbn_demand = fresh_cbn_forecast_df["forecast_qty"].sum()
    fresh_pgs_demand = fresh_pgs_forecast_df["forecast_qty"].sum()
    
    # Allocate Demand Forecast to WHs
    dry_demand_allocation = {772: dry_demand * (1/3), 40: dry_demand * (2/3)}
    fresh_demand_allocation = {661: fresh_cbn_demand, 160: fresh_pgs_demand}
    
    # Allocate demand forecast to each WH x Hub
    for wh_id, wh_demand in {**dry_demand_allocation, **fresh_demand_allocation}.items():
        hub_mask = final_so_df['wh_id'] == wh_id
        total_sql_so_final = final_so_df.loc[hub_mask, 'Sum of qty_so_final'].sum()
        total_sql_so = final_so_df.loc[hub_mask, 'Sum of qty_so'].sum()
        
        if total_sql_so_final > 0:
            # Distribute forecasted SO based on SQL-estimated SO proportions
            final_so_df.loc[hub_mask, 'forecast_based_so'] = (
                final_so_df.loc[hub_mask, 'Sum of qty_so_final'] / total_sql_so_final * wh_demand
            )
    
    # Compare SQL-estimated SO with Forecast-based SO
    final_so_df['final_so_qty'] = final_so_df[['Sum of qty_so_final', 'Sum of qty_so', 'forecast_based_so']].max(axis=1)
    
    # Display Results
    st.header("Final SO Estimation")
    st.dataframe(final_so_df)
    
    # Download Option
    #csv = final_so_df.to_csv(index=False).encode('utf-8')
    #st.download_button("Download Final SO Estimate", csv, "final_so_estimate.csv", "text/csv")

