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

    # Exclude specific hubs
    final_so_df = final_so_df[~final_so_df['hub_id'].isin([537, 758])]
    
    # Initialize result DataFrame
    results = []
    
    for day, forecast_date in enumerate(forecast_dates, start=1):
        # Get daily demand forecast
        daily_dry_forecast = dry_forecast_df[dry_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        daily_fresh_cbn_forecast = fresh_cbn_forecast_df[fresh_cbn_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        daily_fresh_pgs_forecast = fresh_pgs_forecast_df[fresh_pgs_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        
        # Allocate Demand Forecast to WHs
        dry_demand_allocation = {772: int(daily_dry_forecast * (1/3)), 40: int(daily_dry_forecast * (2/3))}
        fresh_demand_allocation = {661: int(daily_fresh_cbn_forecast), 160: int(daily_fresh_pgs_forecast)}
        
        daily_result = final_so_df.copy()
        daily_result[f'Updated Hub Qty D+{day}'] = daily_result['Sum of hub_qty']
        
        for wh_id in final_so_df['wh_id'].unique():
            for hub_id in final_so_df.loc[final_so_df['wh_id'] == wh_id, 'hub_id'].unique():
                hub_mask = (daily_result['wh_id'] == wh_id) & (daily_result['hub_id'] == hub_id)
                total_so_final = final_so_df.loc[final_so_df['wh_id'] == wh_id, 'Sum of qty_so_final'].sum()
                
                if total_so_final > 0:
                    hub_forecast = ((final_so_df.loc[hub_mask, 'Sum of qty_so_final'] / total_so_final) * 
                                    (dry_demand_allocation.get(wh_id, 0) + fresh_demand_allocation.get(wh_id, 0))).astype(int)
                else:
                    hub_forecast = 0
                
                daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] -= hub_forecast
                daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] = daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'].clip(lower=0)
        
        # Compute Predicted SO Quantity
        daily_result[f'Predicted SO Qty D+{day}'] = ((daily_result['Sum of maxqty'] - daily_result[f'Updated Hub Qty D+{day}']) / 
                                                    daily_result['Sum of multiplier']) * daily_result['Sum of multiplier']
        daily_result[f'Predicted SO Qty D+{day}'] = daily_result[f'Predicted SO Qty D+{day}'].clip(lower=0).astype(int)
        
        # Compare with Sum of Reorder Point
        daily_result[f'SO vs Reorder Point D+{day}'] = daily_result[f'Predicted SO Qty D+{day}'] - daily_result['Sum of reorder_point']

        # Convert SO vs Reorder Point to "Triggered" or "Not Triggered"
        daily_result[f'SO vs Reorder Point D+{day}'] = daily_result[f'SO vs Reorder Point D+{day}'].apply(lambda x: "Triggered" if x <= 0 else "Not Triggered")
        
        results.append(daily_result[["wh_id", "hub_id", f"Updated Hub Qty D+{day}", f"Predicted SO Qty D+{day}", f"SO vs Reorder Point D+{day}"]])
    
    # Merge results into a single DataFrame
    final_results_df = results[0]
    for df in results[1:]:
        final_results_df = final_results_df.merge(df, on=["wh_id", "hub_id"], how="left")
    
    # Display Results
    st.header("W+1 to D+6 SO Prediction")
    def highlight_triggered(val):
        color = 'background-color: lightgreen' if val == "Triggered" else 'background-color: lightcoral'
        return color
    
    styled_df = final_results_df.style.applymap(highlight_triggered, subset=[col for col in final_results_df.columns if "SO vs Reorder Point" in col])
    st.dataframe(styled_df)


    st.dataframe(final_so_df[["wh_id", "hub_id", "Sum of qty_so", "Sum of qty_so_final"]])

    # Create a WH-level aggregated DataFrame
    wh_summary_df = final_so_df.groupby('wh_id').agg({
        'Sum of qty_so': 'sum',
        'Sum of qty_so_final': 'sum'
    }).reset_index()
    
    # Rename columns for clarity
    wh_summary_df.rename(columns={'Sum of qty_so_final': 'Total_qty_so_final', 
                                  'forecast_based_so': 'Total_forecast_based_so'}, inplace=True)

    st.dataframe(wh_summary_df)
    
    # Provide a download button for results
    csv = final_results_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download W+1 to W+6 SO Prediction", csv, "w1_w6_so_prediction.csv", "text/csv")



