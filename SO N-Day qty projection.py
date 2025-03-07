import streamlit as st
import pandas as pd

# Load data
st.title("Final SO Quantity Estimation Based on Demand Forecast")

# Upload estimated SO data
estimated_so_file = st.file_uploader("Upload Estimated SO Data (CSV)", type=["csv"])
if estimated_so_file:
    estimated_so = pd.read_csv(estimated_so_file)
    st.write("### Estimated SO Data:")
    st.dataframe(estimated_so.head())

# Upload demand forecast data
demand_forecast_file = st.file_uploader("Upload Demand Forecast Data (CSV)", type=["csv"])
if demand_forecast_file:
    demand_forecast = pd.read_csv(demand_forecast_file)
    st.write("### Demand Forecast Data:")
    st.dataframe(demand_forecast.head())

# Process the final SO estimation if both files are uploaded
if estimated_so_file and demand_forecast_file:
    # Define warehouse types
    dry_wh = [772, 40]
    fresh_cbn = 661
    fresh_pgs = 160
    
    # Merge and adjust SO quantities based on demand
    estimated_so["Final_SO_Qty"] = estimated_so["sum_qty_so_final"]
    
    # Adjust based on demand forecast
    for index, row in estimated_so.iterrows():
        wh_id = row["wh_id"]
        if wh_id in dry_wh:
            demand = demand_forecast[demand_forecast["type"] == "Dry"]["forecast_qty"].sum()
        elif wh_id == fresh_cbn:
            demand = demand_forecast[demand_forecast["type"] == "Fresh_CBN"]["forecast_qty"].sum()
        elif wh_id == fresh_pgs:
            demand = demand_forecast[demand_forecast["type"] == "Fresh_PGS"]["forecast_qty"].sum()
        else:
            demand = 0
        
        # Apply adjustment based on demand (you can refine this logic)
        estimated_so.at[index, "Final_SO_Qty"] = min(row["sum_qty_so_final"], demand)
    
    st.write("### Final SO Estimation:")
    st.dataframe(estimated_so)

    # Download final SO estimation
    csv = estimated_so.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Final SO Data",
        data=csv,
        file_name="final_so_estimation.csv",
        mime="text/csv"
    )
