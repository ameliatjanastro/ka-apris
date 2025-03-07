import streamlit as st
import pandas as pd
import datetime

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
    
    # Get tomorrow's date
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Filter forecast data for tomorrow only
    dry_forecast_df = dry_forecast_df[dry_forecast_df["date_key"] == tomorrow]
    fresh_cbn_forecast_df = fresh_cbn_forecast_df[fresh_cbn_forecast_df["date_key"] == tomorrow]
    fresh_pgs_forecast_df = fresh_pgs_forecast_df[fresh_pgs_forecast_df["date_key"] == tomorrow]

    final_so_df[['wh_id', 'hub_id']] = final_so_df[['wh_id', 'hub_id']].apply(pd.to_numeric)
    
    # Aggregate Demand Forecast for tomorrow
    dry_demand = dry_forecast_df["Forecast Step 3"].sum()
    fresh_cbn_demand = fresh_cbn_forecast_df["Forecast Step 3"].sum()
    fresh_pgs_demand = fresh_pgs_forecast_df["Forecast Step 3"].sum()

    st.write("Dry Forecast Data for Tomorrow:", dry_forecast_df)
    st.write("Fresh CBN Forecast Data for Tomorrow:", fresh_cbn_forecast_df)
    st.write("Fresh PGS Forecast Data for Tomorrow:", fresh_pgs_forecast_df)

    
    # Allocate Demand Forecast to WHs
    # Allocate Demand Forecast to WHs (convert to int)
    dry_demand_allocation = {772: int(dry_demand * (1/3)), 40: int(dry_demand * (2/3))}
    fresh_demand_allocation = {661: int(fresh_cbn_demand), 160: int(fresh_pgs_demand)}


    # Convert IDs to string type
    final_so_df['wh_id'] = final_so_df['wh_id'].astype(int)
    final_so_df['hub_id'] = final_so_df['hub_id'].astype(int)

    st.write("Column Data Types:", final_so_df.dtypes)

   # Initialize forecast column
    final_so_df['forecast_based_so'] = 0  
    
    for wh_id, wh_demand in {**dry_demand_allocation, **fresh_demand_allocation}.items():
        for hub_id in final_so_df.loc[final_so_df['wh_id'] == wh_id, 'hub_id'].unique():
            hub_mask = final_so_df['wh_id'] == wh_id
            hub_mask2 = (final_so_df['wh_id'] == wh_id) & (final_so_df['hub_id'] == hub_id)
            total_sql_so_final = final_so_df.loc[hub_mask, 'Sum of qty_so_final'].sum()  # ✅ WH × Hub total SO
            total_sql_so_final = final_so_df.loc[hub_mask, 'Sum of qty_so_final'].sum()  # ✅ WH × Hub total SO
            
            if total_sql_so_final > 0:
                # Distribute forecast proportionally based on SO Final at each Hub
                final_so_df.loc[hub_mask, 'forecast_based_so'] = (
                    (final_so_df.loc[hub_mask, 'Sum of qty_so_final'] / total_sql_so_final) * wh_demand
                )
            else:
                final_so_df.loc[hub_mask, 'forecast_based_so'] = 0  # If no SO, assign 0
    
            # Ensure deviation is calculated for each WH × Hub
            final_so_df['Deviation Qty'] = ((final_so_df['Sum of qty_so_final'] - final_so_df['forecast_based_so'])/(final_so_df['Sum of qty_so_final']))*100
                
            # Fill NaN values with 0 for cases where forecast_based_so was originally 0
            final_so_df['Deviation Qty'] = final_so_df['Deviation Qty'].fillna(0)


    # Display Results
    st.header("SO Bias Analysis")
    st.dataframe(final_so_df[["wh_id", "hub_id", "Sum of qty_so_final", "forecast_based_so", "Deviation Qty"]])

    
    # Download Option
    csv = final_so_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Final SO Estimate", csv, "final_so_estimate.csv", "text/csv")


