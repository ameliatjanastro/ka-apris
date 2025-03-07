import streamlit as st
import pandas as pd
import datetime

# Streamlit App Title
st.title("SO Quantity Estimation")

# File Upload Section
st.header("Upload Data Files")
so_file = st.file_uploader("Upload SQL-estimated SO CSV", type=["xlsx"])
dry_forecast_file = st.file_uploader("Upload Dry Demand Forecast CSV", type=["csv"])
fresh_cbn_forecast_file = st.file_uploader("Upload Fresh CBN Demand Forecast CSV", type=["csv"])
fresh_pgs_forecast_file = st.file_uploader("Upload Fresh PGS Demand Forecast CSV", type=["csv"])

if so_file and dry_forecast_file and fresh_cbn_forecast_file and fresh_pgs_forecast_file:
    # Load Data
    final_so_df = pd.read_excel(so_file)
    dry_forecast_df = pd.read_csv(dry_forecast_file)
    fresh_cbn_forecast_df = pd.read_csv(fresh_cbn_forecast_file)
    fresh_pgs_forecast_df = pd.read_csv(fresh_pgs_forecast_file)
    
    # Get tomorrow's date
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Filter forecast data for tomorrow only
    dry_forecast_df = dry_forecast_df[dry_forecast_df["date_key"] == tomorrow]
    fresh_cbn_forecast_df = fresh_cbn_forecast_df[fresh_cbn_forecast_df["date_key"] == tomorrow]
    fresh_pgs_forecast_df = fresh_pgs_forecast_df[fresh_pgs_forecast_df["date_key"] == tomorrow]
    
    # Aggregate Demand Forecast for tomorrow
    dry_demand = dry_forecast_df["Forecast Step 3"].sum()
    fresh_cbn_demand = fresh_cbn_forecast_df["Forecast Step 3"].sum()
    fresh_pgs_demand = fresh_pgs_forecast_df["Forecast Step 3"].sum()
    
    # Allocate Demand Forecast to WHs
    dry_demand_allocation = {772: dry_demand * (1/3), 40: dry_demand * (2/3)}
    fresh_demand_allocation = {661: fresh_cbn_demand, 160: fresh_pgs_demand}

    # Convert IDs to string type
    final_so_df['wh_id'] = final_so_df['wh_id'].astype(int)
    final_so_df['hub_id'] = final_so_df['hub_id'].astype(int)

    st.write("Column Data Types:", final_so_df.dtypes)

    
    # Allocate demand forecast to each WH x Hub
    for wh_id, wh_demand in {**dry_demand_allocation, **fresh_demand_allocation}.items():
        for hub_id in final_so_df.loc[final_so_df['wh_id'] == wh_id, 'hub_id'].unique():
            hub_mask = (final_so_df['wh_id'] == wh_id) & (final_so_df['hub_id'] == hub_id)
            
            # Extract values directly instead of summing
            total_sql_so_final = final_so_df.loc[hub_mask, 'Sum of qty_so_final'].values[0] if not final_so_df.loc[hub_mask].empty else 0
            total_sql_so = final_so_df.loc[hub_mask, 'Sum of qty_so'].values[0] if not final_so_df.loc[hub_mask].empty else 0
            
            if total_sql_so_final > 0:
                final_so_df.loc[hub_mask, 'forecast_based_so'] = (
                    (final_so_df.loc[hub_mask, 'Sum of qty_so_final'] / total_sql_so_final) * wh_demand
                )
            else:
                final_so_df.loc[hub_mask, 'forecast_based_so'] = 0  # Set to 0 if no SO exists
    
    # Compare SQL-estimated SO with Forecast-based SO
    final_so_df['MAX_so_qty'] = final_so_df[['Sum of qty_so_final', 'Sum of qty_so', 'forecast_based_so']].max(axis=1)
    
    # Display Results
    st.header("Final SO Estimation")
    st.dataframe(final_so_df)
    
    # Download Option
    csv = final_so_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Final SO Estimate", csv, "final_so_estimate.csv", "text/csv")


