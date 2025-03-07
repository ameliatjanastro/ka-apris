import streamlit as st 
import pandas as pd
import datetime
import numpy as np

# Streamlit App Title
st.title("SO Quantity Estimation")

# File Upload Section
st.header("Upload Data Files")
so_file = st.file_uploader("Upload SQL-estimated SO CSV", type=["xlsx"])
dry_forecast_file = st.file_uploader("Upload Dry Demand Forecast CSV", type=["xlsx"])
fresh_cbn_forecast_file = st.file_uploader("Upload Fresh CBN Demand Forecast CSV", type=["xlsx"])
fresh_pgs_forecast_file = st.file_uploader("Upload Fresh PGS Demand Forecast CSV", type=["xlsx"])

if so_file and dry_forecast_file and fresh_cbn_forecast_file and fresh_pgs_forecast_file:
    # Load Data
    final_so_df = pd.read_excel(so_file)
    dry_forecast_df = pd.read_excel(dry_forecast_file)
    fresh_cbn_forecast_df = pd.read_excel(fresh_cbn_forecast_file)
    fresh_pgs_forecast_df = pd.read_excel(fresh_pgs_forecast_file)
    
    # Get forecast dates D+1 to D+6
    today = datetime.date.today()
    forecast_dates = [(today + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 7)]
    
    # Filter forecast data for D+1 to D+6
    dry_forecast_df = dry_forecast_df[dry_forecast_df["date_key"].isin(forecast_dates)]
    fresh_cbn_forecast_df = fresh_cbn_forecast_df[fresh_cbn_forecast_df["date_key"].isin(forecast_dates)]
    fresh_pgs_forecast_df = fresh_pgs_forecast_df[fresh_pgs_forecast_df["date_key"].isin(forecast_dates)]

    # Convert IDs to integer type
    final_so_df[['wh_id', 'hub_id']] = final_so_df[['wh_id', 'hub_id']].apply(pd.to_numeric)
    
    # Initialize result dataframe
    results_df = final_so_df[['wh_id', 'hub_id']].copy()
    
    for i, forecast_date in enumerate(forecast_dates):
        # Get daily forecast
        daily_dry_demand = dry_forecast_df[dry_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        daily_fresh_cbn_demand = fresh_cbn_forecast_df[fresh_cbn_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        daily_fresh_pgs_demand = fresh_pgs_forecast_df[fresh_pgs_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        
        # Allocate Demand Forecast to WHs
        dry_demand_allocation = {772: int(daily_dry_demand * (1/3)), 40: int(daily_dry_demand * (2/3))}
        fresh_demand_allocation = {661: int(daily_fresh_cbn_demand), 160: int(daily_fresh_pgs_demand)}
        
        # Initialize updated hub quantity
        final_so_df[f'Updated Hub Qty D+{i+1}'] = final_so_df['Sum of hub_qty']
        
        for wh_id in final_so_df['wh_id'].unique():
            for hub_id in final_so_df.loc[final_so_df['wh_id'] == wh_id, 'hub_id'].unique():
                hub_mask = (final_so_df['wh_id'] == wh_id) & (final_so_df['hub_id'] == hub_id)
                demand = dry_demand_allocation.get(wh_id, 0) + fresh_demand_allocation.get(wh_id, 0)
                
                final_so_df.loc[hub_mask, f'Updated Hub Qty D+{i+1}'] -= demand
                final_so_df.loc[hub_mask, f'Updated Hub Qty D+{i+1}'] = final_so_df.loc[hub_mask, f'Updated Hub Qty D+{i+1}'].clip(lower=0)
        
        # Compute Predicted SO Quantity
        final_so_df[f'Predicted SO Qty D+{i+1}'] = ((final_so_df['Sum of maxqty'] - final_so_df[f'Updated Hub Qty D+{i+1}']) / 
                                                    final_so_df['Sum of multiplier']) * final_so_df['Sum of multiplier']
        final_so_df[f'Predicted SO Qty D+{i+1}'] = final_so_df[f'Predicted SO Qty D+{i+1}'].clip(lower=0).astype(int)
        
        # Compare with Sum of Reorder Point
        final_so_df[f'SO vs Reorder Point D+{i+1}'] = final_so_df[f'Predicted SO Qty D+{i+1}'] - final_so_df['Sum of reorder_point']
        
        # Store in results dataframe
        results_df[f'Updated Hub Qty D+{i+1}'] = final_so_df[f'Updated Hub Qty D+{i+1}']
        results_df[f'Predicted SO Qty D+{i+1}'] = final_so_df[f'Predicted SO Qty D+{i+1}']
        results_df[f'SO vs Reorder Point D+{i+1}'] = final_so_df[f'SO vs Reorder Point D+{i+1}']
    
    # Display Results
    st.header("W+1 to W+6 SO Prediction")
    st.dataframe(results_df)


    st.dataframe(final_so_df[["wh_id", "hub_id", "Sum of qty_so", "Sum of qty_so_final"]])

    # Create a WH-level aggregated DataFrame
    wh_summary_df = final_so_df.groupby('wh_id').agg({
        'Sum of qty_so': 'sum',
        'Sum of qty_so_final': 'sum',
        'forecast_based_so': 'sum'
    }).reset_index()
    
    # Rename columns for clarity
    wh_summary_df.rename(columns={'Sum of qty_so_final': 'Total_qty_so_final', 
                                  'forecast_based_so': 'Total_forecast_based_so'}, inplace=True)

    st.dataframe(wh_summary_df)
    
    # Provide a download button for results
    csv = results_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download W+1 to W+6 SO Prediction", csv, "w1_w6_so_prediction.csv", "text/csv")



