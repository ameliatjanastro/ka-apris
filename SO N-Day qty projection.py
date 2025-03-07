import streamlit as st 
import pandas as pd
import datetime
import numpy as np
import plotly.express as px

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
    final_so_df["hub_id"] = final_so_df["hub_id"].astype(int)
    final_so_df = final_so_df[~final_so_df['hub_id'].isin([537, 758])]
    final_so_df = final_so_df[~final_so_df['wh_id'].isin([583])]
    
    # Initialize result DataFrame
    results = []
    
    for day, forecast_date in enumerate(forecast_dates, start=1):
        # Get daily demand forecast
        daily_dry_forecast = dry_forecast_df[dry_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        daily_fresh_cbn_forecast = fresh_cbn_forecast_df[fresh_cbn_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
        daily_fresh_pgs_forecast = fresh_pgs_forecast_df[fresh_pgs_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()

        st.write(dry_forecast_df.head(8))

        
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
                
                daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] -= hub_forecast*0.7
                daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] = daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'].clip(lower=0)
        
        # Compute Predicted SO Quantity
        daily_result[f'Predicted SO Qty D+{day}'] = ((daily_result['Sum of maxqty'] - daily_result[f'Updated Hub Qty D+{day}']) / 
                                                    daily_result['Sum of multiplier']) * daily_result['Sum of multiplier']
        daily_result[f'Predicted SO Qty D+{day}'] = daily_result[f'Predicted SO Qty D+{day}'].clip(lower=0).astype(int)

        sample_wh = daily_result[(daily_result["wh_id"] == 40) & (daily_result["hub_id"] == 121)].head()
        st.dataframe(sample_wh[["Sum of maxqty", "Updated Hub Qty D+1", "Sum of multiplier", "Predicted SO Qty D+1"]])



        
        def check_triggered(row, day):
            if row[f'Predicted SO Qty D+{day}'] == 0:
                return "Not Triggered"
            return "Triggered" if row[f'Predicted SO Qty D+{day}'] - row['Sum of reorder_point'] < 0 else "Not Triggered"
        
        daily_result[f'SO vs Reorder Point D+{day}'] = daily_result.apply(lambda row: check_triggered(row, day), axis=1)
        
        results.append(daily_result[["wh_id", "hub_id", f"Updated Hub Qty D+{day}", f"Predicted SO Qty D+{day}", f"SO vs Reorder Point D+{day}"]])
    
    # Merge results into a single DataFrame
    final_results_df = results[0]
    for df in results[1:]:
        final_results_df = final_results_df.merge(df, on=["wh_id", "hub_id"], how="left")


    # Hub ID to Hub Name mapping
    hub_name_mapping = {
        98: "MTG - Menteng",
        121: "BS9 - Bintaro Sektor 9",
        125: "PPN - Pos Pengumben",
        152: "LBB - Lebak Bulus",
        189: "SRP - Serpong Utara",
        201: "MSB - Medan Satria Bekasi",
        206: "JTB - Jatibening",
        207: "GWB - Grand Wisata Bekasi",
        223: "CT2 - Citra 2",
        261: "CNR - Cinere",
        288: "MRG - Margonda",
        517: "FTW - Fatmawati",
        523: "JLB - Jelambar",
        529: "BSX - New BSD",
        538: "KJT - Kramat Jati",  # Excluded
        591: "MRY - Meruya",
        615: "GPL - Gudang Peluru",
        619: "TSY - Transyogi",
        626: "DST - Duren Sawit",
        634: "PPL - Panglima Polim",
        648: "DNS - Danau Sunter",
        654: "TGX - New TGC",
        657: "APR - Ampera",
        669: "BRY - Buncit Raya",
        672: "KPM - Kapuk Muara",
        759: "CWG - Cawang",  # Excluded
        763: "PSG - Pisangan",
        767: "PKC - Pondok Kacang",
        773: "PGD - Pulo Gadung",
        776: "BGS - Boulevard Gading Serpong"
    }

    # WH ID to WH Name mapping
    wh_name_mapping = {
        40: "KOS - WH Kosambi",
        772: "STL - Sentul",
        160: "PGS - Pegangsaan",
        661: "CBN - WH Cibinong"
    }

    final_results_df["Hub Name"] = final_results_df["hub_id"].map(hub_name_mapping)
    # Map WH names
    final_results_df["WH Name"] = final_results_df["wh_id"].map(wh_name_mapping)
    final_so_df["WH Name"] = final_so_df["wh_id"].map(wh_name_mapping)
    final_so_df["Hub Name"] = final_so_df["hub_id"].map(hub_name_mapping)
    
    st.dataframe(final_so_df[["WH Name", "Hub Name", "Sum of qty_so", "Sum of qty_so_final"]])

    # Create a WH-level aggregated DataFrame
    wh_summary_df = final_so_df.groupby("WH Name").agg({
    'Sum of qty_so': 'sum',
    'Sum of qty_so_final': 'sum'
    }).reset_index()
    
    st.dataframe(wh_summary_df)
    
    # Display Results
    st.header("W+1 to D+6 SO Prediction")
    def highlight_triggered(val):
        color = 'background-color: lightgreen' if val == "Triggered" else 'background-color: lightcoral'
        return color
    
    styled_df = final_results_df.style.applymap(highlight_triggered, subset=[col for col in final_results_df.columns if "SO vs Reorder Point" in col])
    st.dataframe(styled_df)

    # Dropdown for selecting WH ID


    # Dropdown for selecting Hub ID
   # Dropdown for selecting Hub ID
    hub_options = final_results_df['hub_id'].unique()
    # Combine Hub ID and Name for display
    final_results_df["Hub Display"] = final_results_df["hub_id"].astype(str) + " - " + final_results_df["Hub Name"]

    selected_hub = st.selectbox("Select Hub", final_results_df["Hub Display"].dropna().unique())  # Drop NaN to avoid excluded hubs

    
    # Filter the DataFrame for the selected hub
    selected_hub_id = int(selected_hub.split(" - ")[0])  # Extracts ID
    filtered_df = final_results_df[final_results_df["hub_id"] == selected_hub_id]

    #filtered_df = final_results_df[final_results_df['hub_id'] == selected_hub].copy()
    
    # Rename D+1 to D+6 columns to actual dates
    forecast_dates_dict = {f"Predicted SO Qty D+{i+1}": (today + datetime.timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(6)}
    filtered_df.rename(columns=forecast_dates_dict, inplace=True)
    
    # Reshape the data for plotting
    melted_df = filtered_df.melt(id_vars=['wh_id'], 
                                  value_vars=list(forecast_dates_dict.values()), 
                                  var_name='Date', 
                                  value_name='SO Quantity')
    
    # Convert Date column to datetime type for proper plotting
    melted_df['Date'] = pd.to_datetime(melted_df['Date'])
    
    # Separate data for Dry WHs (772, 40) and Fresh WHs (160, 661)
    dry_wh_df = melted_df[melted_df['wh_id'].isin([772, 40])]
    fresh_wh_df = melted_df[melted_df['wh_id'].isin([160, 661])]
    
    # Create Dry WHs line chart
    st.subheader("Predicted SO Quantity for Dry Warehouses (772, 40)")
    fig_dry = px.line(
        dry_wh_df,
        x='Date', 
        y='SO Quantity', 
        color='wh_id',  
        markers=True,  
        title=f'Dry Warehouses (772 & 40) - Predicted SO Quantity for Hub {selected_hub}'
    )
    
    # Add data labels
    for wh in dry_wh_df['wh_id'].unique():
        wh_data = dry_wh_df[dry_wh_df['wh_id'] == wh]
        fig_dry.add_scatter(
            x=wh_data['Date'], 
            y=wh_data['SO Quantity'], 
            mode='text', 
            text=wh_data['SO Quantity'].astype(str), 
            textposition="top center",
            showlegend=False
        )
    
    st.plotly_chart(fig_dry)
    
    # Create Fresh WHs line chart
    st.subheader("Predicted SO Quantity for Fresh Warehouses (160, 661)")
    fig_fresh = px.line(
        fresh_wh_df,
        x='Date', 
        y='SO Quantity', 
        color='wh_id',  
        markers=True,  
        title=f'Fresh Warehouses (160 & 661) - Predicted SO Quantity for Hub {selected_hub}'
    )
    
    # Add data labels
    for wh in fresh_wh_df['wh_id'].unique():
        wh_data = fresh_wh_df[fresh_wh_df['wh_id'] == wh]
        fig_fresh.add_scatter(
            x=wh_data['Date'], 
            y=wh_data['SO Quantity'], 
            mode='text', 
            text=wh_data['SO Quantity'].astype(str), 
            textposition="top center",
            showlegend=False
        )
    
    st.plotly_chart(fig_fresh)

    
    # Provide a download button for results
    csv = final_results_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download W+1 to W+6 SO Prediction", csv, "w1_w6_so_prediction.csv", "text/csv")



