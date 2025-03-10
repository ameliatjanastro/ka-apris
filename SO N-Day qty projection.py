import streamlit as st 
import pandas as pd
import datetime
import numpy as np
import plotly.express as px

#st.set_page_config(layout="wide") 

# Streamlit App Title

st.markdown(f"#### SO Qty Projection: Understanding **:red[Qty SO]** vs. **:red[Qty SO Final]** 😊")  
#st.title("SO Quantity Estimation")

today = datetime.date.today()
st.sidebar.markdown(f"📅 Today’s Date: **{today}**")

# File Upload Section
so_file = st.sidebar.file_uploader("Upload SQL-estimated SO (after 9 PM best :) )", type=["xlsx"])

st.markdown(
    """
    <style>
        /* Reduce space at the top of the page */
        .block-container {
            padding-top: 3rem;
        }
        /* Reduce overall font size */
        html, body, [class*="css"] {
            font-size: 12px !important;
        }

        /* Reduce dataframe font size */
        div[data-testid="stDataFrame"] * {
            font-size: 9px !important;
        }
        
        /* Reduce table font size */
        table {
            font-size: 9px !important;
        }

        /* EXCLUDE Plotly Charts from Font Size Reduction */
        .js-plotly-plot .plotly * {
            font-size: 11px !important;  /* Ensures default or larger font */
        }
        
    </style>
    """,
    unsafe_allow_html=True
)

with st.expander("View Description"):
    st.markdown("""
    
    | Concept  | qty_so (how much should be ordered) | qty_so_final (final approved SO quantity)|
    |----------|--------|-------------|
    | **Purpose** | Initial calculated order quantity | Final approved SO quantity after warehouse stock check |
    | **Based on** | hub_qty, reorder_point, total_allocation, multiplier | wh_qty and cumulative_so_qty |
    | **Triggers order?** | ✅ Yes, if hub_qty ≤ reorder_point | ❌ No, if warehouse stock is insufficient |
    | **Explanation** | If **hub_qty > reorder_point**, no order is triggered (**qty_so = NULL**) | If **wh_qty < cumulative_so_qty**, lower-priority hubs might not get stock (**qty_so_final = NULL**) |
    """)
    
    st.markdown("""
    - **Total Active Hubs**: 30  
    - **Total WH**: 4  
    - Predicted **SO Qty D + X** is based on Demand Forecast for **next day, before considering wh_qty** 
    - **The displayed Qty for CBN excludes Xdock (30% of total SO)**  
     
    """)

# Sidebar navigation
tab1, tab2 = st.tabs(["Next Day SO Prediction", "D+1 to D+6 SO Prediction"])
#page = st.sidebar.radio("Select Page", ["D+0 SO Prediction", "D+1 to D+6 SO Prediction"])
#dry_forecast_file = st.file_uploader("Upload Dry Demand Forecast CSV", type=["xlsx"])
#fresh_cbn_forecast_file = st.file_uploader("Upload Fresh CBN Demand Forecast CSV", type=["xlsx"])
#fresh_pgs_forecast_file = st.file_uploader("Upload Fresh PGS Demand Forecast CSV", type=["xlsx"])

dry_forecast_df = pd.read_excel("Forecast Mar Dry.xlsx")
fresh_cbn_forecast_df = pd.read_excel("Forecast Mar Fresh CBN.xlsx")
fresh_pgs_forecast_df = pd.read_excel("Forecast Mar Fresh PGS.xlsx")


if so_file:
    # Load Data
    final_so_df = pd.read_excel(so_file)

    
    # Get forecast dates D+1 to D+6

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

    with tab1:
        #st.subheader("Next Day SO Prediction")
    
         # Compute Predicted SO Qty D+0
        final_so_df['Predicted SO Qty D+0'] = ((final_so_df['Sum of maxqty'] - final_so_df['Sum of hub_qty']) / 
                                               final_so_df['Sum of multiplier']) * final_so_df['Sum of multiplier']
        final_so_df['Predicted SO Qty D+0'] = final_so_df['Predicted SO Qty D+0'].clip(lower=0).astype(int)
    
        final_so_df["WH Name"] = final_so_df["wh_id"].map(wh_name_mapping)
        final_so_df["Hub Name"] = final_so_df["hub_id"].map(hub_name_mapping)
        final_so_df = final_so_df.rename(columns={"wh_id": "WH ID"})

        def highlight_final_so(s):
            return ['background-color: #FFFACD' if s.name == 'Sum of qty_so_final' else '' for _ in s]

        # Create a WH-level aggregated DataFrame
        wh_summary_df = final_so_df.groupby("WH Name").agg({
        'Sum of qty_so': 'sum',
        'Predicted SO Qty D+0': 'sum',
        'Sum of qty_so_final': 'sum'
        }).reset_index()
        
        # Apply styling
        styled_wh_summary = wh_summary_df.style.apply(highlight_final_so, subset=["Sum of qty_so_final"])
        
        # Display WH-level summary with highlight
        st.markdown('<h4 style="color: maroon;">Summary by WH</h4>', unsafe_allow_html=True)
        st.dataframe(styled_wh_summary, use_container_width=True)
        
        # Select WH dropdown
        st.markdown('<h4 style="color: maroon;">Summary by Hub</h4>', unsafe_allow_html=True)
        wh_options = final_so_df["WH Name"].unique().tolist()
        selected_wh = st.selectbox("Select WH", wh_options)
        
        # Filter DataFrame by selected WH
        filtered_so_df = final_so_df[final_so_df["WH Name"] == selected_wh]
        
        # Apply styling to filtered DataFrame
        styled_filtered_so = filtered_so_df[["Hub Name", "Sum of qty_so", "Predicted SO Qty D+0", "Sum of qty_so_final"]].style.apply(
            highlight_final_so, subset=["Sum of qty_so_final"]
        )

        # Display Final SO DataFrame with highlight

        st.dataframe(styled_filtered_so, column_config={col: st.column_config.TextColumn(width="small") for col in filtered_so_df.columns}, use_container_width=True)
        #st.dataframe(filtered_so_df[["Hub Name", "Sum of qty_so", "Predicted SO Qty D+0", "Sum of qty_so_final"]],column_config={col: st.column_config.TextColumn(width="small") for col in filtered_so_df.columns})

        csv1 = final_so_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Next Day SO Prediction", csv1, "next_day_so_prediction.csv", "text/csv")
   
    
    with tab2:
            
        # Initialize result DataFrame
        results = []
        
        for day, forecast_date in enumerate(forecast_dates, start=0):
            # Get daily demand forecast
            daily_dry_forecast = dry_forecast_df[dry_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
            daily_fresh_cbn_forecast = fresh_cbn_forecast_df[fresh_cbn_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
            daily_fresh_pgs_forecast = fresh_pgs_forecast_df[fresh_pgs_forecast_df["date_key"] == forecast_date]["Forecast Step 3"].sum()
    
            # Allocate Demand Forecast to WHs
            dry_demand_allocation = {772: int(daily_dry_forecast * (1/3)), 40: int(daily_dry_forecast * (2/3))}
            fresh_demand_allocation = {661: int(daily_fresh_cbn_forecast), 160: int(daily_fresh_pgs_forecast)}
            
            daily_result = final_so_df.copy()
            daily_result[f'Updated Hub Qty D+{day}'] = daily_result['Sum of hub_qty']
            
            for wh_id in final_so_df['WH ID'].unique():
                for hub_id in final_so_df.loc[final_so_df['WH ID'] == wh_id, 'hub_id'].unique():
                    hub_mask = (daily_result['WH ID'] == wh_id) & (daily_result['hub_id'] == hub_id)
                    total_so_final = final_so_df.loc[final_so_df['WH ID'] == wh_id, 'Sum of qty_so_final'].sum()
                    
                    if total_so_final > 0:
                        hub_forecast = ((final_so_df.loc[hub_mask, 'Sum of qty_so_final'] / total_so_final) * 
                                        (dry_demand_allocation.get(wh_id, 0) + fresh_demand_allocation.get(wh_id, 0))).astype(int)
                    else:
                        hub_forecast = 0

                    previous_day_qty = 0
                    if day >= 1:
                        previous_day_qty = daily_result.loc[hub_mask, f'Predicted SO Qty D+{day-1}'].fillna(0).astype(int)
                    
                    daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] = (
                        daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] - hub_forecast + previous_day_qty
                    ).clip(lower=0)

                    #daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] -= hub_forecast
                    daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] = daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'].clip(lower=0)
            
            # Compute Predicted SO Quantity
            daily_result[f'Predicted SO Qty D+{day}'] = ((daily_result['Sum of maxqty'] - daily_result[f'Updated Hub Qty D+{day}']) / 
                                                        daily_result['Sum of multiplier']) * daily_result['Sum of multiplier']
            daily_result[f'Predicted SO Qty D+{day}'] = daily_result[f'Predicted SO Qty D+{day}'].clip(lower=0).astype(int)
    
            #sample_wh = daily_result[(daily_result["wh_id"] == 160) & (daily_result["hub_id"] == 121)].head()
            #st.dataframe(sample_wh[["Sum of maxqty", "Updated Hub Qty D+1", "Sum of multiplier", "Predicted SO Qty D+1"]])
            
            def check_triggered(row, day):
                if row[f'Predicted SO Qty D+{day}'] == 0:
                    return "Not Triggered"
                return "Triggered" if row[f'Predicted SO Qty D+{day}'] - row['Sum of reorder_point'] < 0 else "Not Triggered"
            
            daily_result[f'SO vs Reorder Point D+{day}'] = daily_result.apply(lambda row: check_triggered(row, day), axis=1)
            daily_result = daily_result.rename(columns={"wh_id": "WH ID", "hub_id": "Hub ID"})
            results.append(daily_result[["WH ID", "Hub ID", "Sum of maxqty", f"Updated Hub Qty D+{day}", f"Predicted SO Qty D+{day}", f"SO vs Reorder Point D+{day}"]])
        
        # Merge results into a single DataFrame
        final_results_df = results[0]
        for df in results[1:]:
            final_results_df = final_results_df.merge(df, on=["WH ID", "Hub ID","Sum of maxqty"], how="left")
            
        #final_results_df["WH Name"] = final_results_df["wh_id"].map(wh_name_mapping)
        
        # Display Results
        #st.subheader("D+1 to D+6 SO Prediction")
        
        def highlight_triggered(val):
            color = 'background-color: lightgreen' if val == "Triggered" else 'background-color: lightcoral'
            return color
    
        #final_results_df = final_results_df.rename(columns={"wh_id": "WH ID", "hub_id": "Hub ID"})

        # Dropdown for selecting WH ID
    
        hub_options = final_results_df['Hub ID'].unique()
        # Combine Hub ID and Name for display
        final_results_df["Hub Name"] = final_results_df["Hub ID"].map(hub_name_mapping)
        final_results_df["Hub Display"] = final_results_df["Hub ID"].astype(str) + " - " + final_results_df["Hub Name"]

        st.markdown("""
        
        **Demand Forecast assumptions:**  
        - *Dry*: 2/3 demand for KOS, 1/3 for STL  
        - *Fresh*: By L2 Category (CBN -> Telur, Roti & Pastry, Sayur, Buah) 
        """)


        st.markdown('<h4 style="color: maroon;">Summary by Hub by Week</h4>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            #selected_hub = st.select_slider("Select WH", options=final_results_df["Hub Display"].dropna().unique())
            selected_hub = st.selectbox("Select Hub", final_results_df["Hub Display"].dropna().unique())  # Drop NaN to avoid excluded hubs
            
        with col2:
            product_type = st.selectbox("Select Product Type:", ["Dry", "Fresh"])
            
    
        # Filter the DataFrame for the selected hub
        selected_hub_id = int(selected_hub.split(" - ")[0])  # Extracts ID
        filtered_df = final_results_df[final_results_df["Hub ID"] == selected_hub_id]
    
        #filtered_df = final_results_df[final_results_df['Hub ID'] == selected_hub].copy()
        
        # Rename D+1 to D+6 columns to actual dates
        forecast_dates_dict = {f"Predicted SO Qty D+{i+1}": (today + datetime.timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(6)}
        filtered_df.rename(columns=forecast_dates_dict, inplace=True)
        
        # Reshape the data for plotting
        melted_df = filtered_df.melt(id_vars=['WH ID'], 
                                      value_vars=list(forecast_dates_dict.values()), 
                                      var_name='Date', 
                                      value_name='SO Quantity')
        
        # Convert Date column to datetime type for proper plotting
        melted_df['Date'] = pd.to_datetime(melted_df['Date'])
        
        # Separate data for Dry WHs (772, 40) and Fresh WHs (160, 661)
        dry_wh_df = melted_df[melted_df['WH ID'].isin([772, 40])]
        fresh_wh_df = melted_df[melted_df['WH ID'].isin([160, 661])]
        
        # Create Dry WHs line chart
        
        # Show selected chart
        if product_type == "Dry":
            # Dry WHs Line Chart
            fig_dry = px.line(
                dry_wh_df,
                x='Date', 
                y='SO Quantity', 
                color='WH ID',  
                markers=True  
                #title=f'Dry Warehouses (KOS & STL) - Predicted SO Quantity for Hub {selected_hub}'
            )
        
            # Add data labels
            for wh in dry_wh_df['WH ID'].unique():
                wh_data = dry_wh_df[dry_wh_df['WH ID'] == wh]
                fig_dry.add_scatter(
                    x=wh_data['Date'], 
                    y=wh_data['SO Quantity'] * 1.05, 
                    mode='text', 
                    text=wh_data['SO Quantity'].astype(str), 
                    textposition="top center",  # Adjusted placement
                    textfont=dict(color="gray", size=11, weight="bold"),  # Bold Red Text
                    showlegend=False
                )

                fig_dry.update_layout(
                    margin=dict(t=10),  # Reduce top space for Dry WH chart
                )
        
            st.plotly_chart(fig_dry, use_container_width=True)
        
        else:
            # Fresh WHs Line Chart
            fig_fresh = px.line(
                fresh_wh_df,
                x='Date', 
                y='SO Quantity', 
                color='WH ID',  
                markers=True  
                #title=f'Fresh Warehouses (PGS & CBN) - Predicted SO Quantity for Hub {selected_hub}'
            )
        
            # Add data labels
            for wh in fresh_wh_df['WH ID'].unique():
                wh_data = fresh_wh_df[fresh_wh_df['WH ID'] == wh]
                fig_fresh.add_scatter(
                    x=wh_data['Date'], 
                    y=wh_data['SO Quantity'] + 10, 
                    mode='text', 
                    text=wh_data['SO Quantity'].astype(str), 
                    textposition="top center",  # Adjusted placement
                    textfont=dict(color="gray", size=11, weight="bold"),  # Bold Red Text
                    showlegend=False
                )

                fig_fresh.update_layout(
                    margin=dict(t=10),  # Reduce top space for Fresh WH chart
                )
        
            st.plotly_chart(fig_fresh, use_container_width=True)
    
        
        # Provide a download button for results

         # Create two columns for better layout
        col1, col2 = st.columns(2)
        
        # Place the select boxes in separate columns
        with col2:
            selected_day = st.selectbox("Select D+X day(s)", [f"D+{i}" for i in range(1, 7)])
        
        with col1:
            wh_options = final_results_df["WH ID"].unique().tolist()
            selected_wh = st.selectbox("Select WH ID", wh_options)
        
        # Filter the dataframe based on selected WH
        
        final_results_df = final_results_df.rename(columns={"Sum of maxqty": "Max Total Allocation"})
        filtered_df = final_results_df[final_results_df["WH ID"] == selected_wh]
        
        # Select relevant columns dynamically based on the chosen day
        selected_columns = ["Hub ID", f"Updated Hub Qty {selected_day}", f"Predicted SO Qty {selected_day}", "Max Total Allocation", f"SO vs Reorder Point {selected_day}"]
        
        # Apply selection and styling
        styled_df = filtered_df[selected_columns].style.applymap(highlight_triggered, subset=[f"SO vs Reorder Point {selected_day}"])
    
        #styled_df = final_results_df.style.applymap(highlight_triggered, subset=[col for col in final_results_df.columns if "SO vs Reorder Point" in col])

        styled_df = styled_df.hide(axis="index")
        st.markdown('<h4 style="color: maroon;">Summary by WH by Day</h4>', unsafe_allow_html=True)
        st.dataframe(styled_df, use_container_width=True)
        
        csv = final_results_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download D+1 to D+6 SO Prediction", csv, "d1_d6_so_prediction.csv", "text/csv")



