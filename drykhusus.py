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

dry_forecast_df = pd.read_excel("demand_dry_productid.xlsx")


if so_file:
    # Load Data
    final_so_df = pd.read_excel(so_file)

    
    # Get forecast dates D+1 to D+6
    dry_forecast_df['date_key'] = pd.to_datetime(dry_forecast_df['date_key'], errors='coerce')
    forecast_dates = [(today + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 7)]
    
    # Filter forecast data for D+1 to D+6
    dry_forecast_df = dry_forecast_df[dry_forecast_df["date_key"].isin(forecast_dates)]

    # Convert IDs to integer type
    final_so_df[['wh_id','product_id', 'hub_id']] = final_so_df[['wh_id','product_id', 'hub_id']].apply(pd.to_numeric)

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

    stock_df1 = pd.read_excel('kos.xlsx')
    stock_df2 = pd.read_excel('stl.xlsx')
    
    # Concatenate the stock data from both files (assuming they have the same structure)
    stock_df = pd.concat([stock_df1, stock_df2])
    
    # Merge the stock data with the final SO data on 'product_id'
    final_so_df = final_so_df.merge(stock_df, on='product_id', how='left')








    
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
        styled_filtered_so = filtered_so_df[["Hub Name", "Sum of qty_so", "Sum of qty_so_final", "Predicted SO Qty D+0"]].style.apply(
            highlight_final_so, subset=["Sum of qty_so_final"]
        )

        # Display Final SO DataFrame with highlight

        st.dataframe(filtered_so_df, use_container_width=True)
        #st.dataframe(filtered_so_df[["Hub Name", "Sum of qty_so", "Sum of qty_so_final", "Predicted SO Qty D+0"]],column_config={col: st.column_config.TextColumn(width="small") for col in filtered_so_df.columns})

        csv1 = final_so_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Next Day SO Prediction", csv1, "next_day_so_prediction.csv", "text/csv")
   
    
    with tab2:
            
        # Initialize result DataFrame
        results = []

        dry_forecast_df = dry_forecast_df.merge(final_so_df[['product_id', 'WH ID']], on='product_id', how='left')
        
        for day, forecast_date in enumerate(forecast_dates, start=1):
            for product_id in dry_forecast_df["product_id"].unique():
                # Get the daily dry forecast for the given date and product ID
                daily_dry_forecast = dry_forecast_df[
                    (dry_forecast_df["date_key"] == forecast_date) & 
                    (dry_forecast_df["product_id"] == product_id)
                ]["Forecast Step 3"].sum()
        
                # Get unique product IDs for WH 40 and WH 772
                wh_40_products = set(dry_forecast_df[dry_forecast_df["wh_id"] == 40]["product_id"].unique())
                wh_772_products = set(dry_forecast_df[dry_forecast_df["wh_id"] == 772]["product_id"].unique())
                
                # Determine product IDs that are associated with both WHs
                common_products = wh_40_products.intersection(wh_772_products)
        
                # Allocate Demand Forecast to WHs
                if product_id in common_products:
                    dry_demand_allocation_split = {
                        772: int(daily_dry_forecast * 0.62),
                        40: int(daily_dry_forecast * 0.38)
                    }
                elif product_id in wh_40_products:
                    dry_demand_allocation_split = {40: int(daily_dry_forecast)}
                elif product_id in wh_772_products:
                    dry_demand_allocation_split = {772: int(daily_dry_forecast)}
                else:
                    dry_demand_allocation_split = {}
        
                # Log the allocation for debugging
                st.write(f"Day {day}, Product {product_id}, Allocation: {dry_demand_allocation_split}")
                    
            daily_result = final_so_df.copy()
            daily_result[f'Updated Hub Qty D+{day}'] = daily_result['Sum of hub_qty']
            
            # Iterate through each WH ID and Hub ID
            for wh_id in final_so_df['WH ID'].unique():
                for hub_id in final_so_df.loc[final_so_df['WH ID'] == wh_id, 'hub_id'].unique():
                    hub_mask = (daily_result['WH ID'] == wh_id) & (daily_result['hub_id'] == hub_id)
                    total_so_final = final_so_df.loc[final_so_df['WH ID'] == wh_id, 'Sum of qty_so_final'].sum()
            
                    if total_so_final > 0:
                        hub_forecast = ((final_so_df.loc[hub_mask, 'Sum of qty_so_final'] / total_so_final) * 
                                        (dry_demand_allocation_split.get(wh_id, 0)).astype(int))
                    else:
                        hub_forecast = 0
            
                    daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] -= hub_forecast
                    daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'] = daily_result.loc[hub_mask, f'Updated Hub Qty D+{day}'].clip(lower=0)
            
            # Compute Predicted SO Quantity
            daily_result[f'Predicted SO Qty D+{day}'] = (
                (daily_result['Sum of maxqty'] - daily_result[f'Updated Hub Qty D+{day}']) / 
                daily_result['Sum of multiplier']
            ) * daily_result['Sum of multiplier']
            
            # Adjust Predicted SO Quantity based on stock availability
            # Merge daily_result with stock_df to add the 'stock' column
            daily_result = daily_result.merge(stock_df[['product_id', 'stock']], on='product_id', how='left')
            
            # Set Predicted SO Qty to NaN if stock is less than the predicted quantity
            daily_result.loc[daily_result['stock'] < daily_result[f'Predicted SO Qty D+{day}'], f'Predicted SO Qty D+{day}'] = np.nan

            print(daily_result[[f'Predicted SO Qty D+{day}', 'stock']])
            
            #daily_result.loc[daily_result['WH ID'] == 40, f'Predicted SO Qty D+{day}'] *= 0.71
            #daily_result.loc[daily_result['WH ID'] == 772, f'Predicted SO Qty D+{day}'] *= 0.535
            
            #daily_result[f'Predicted SO Qty D+{day}'] = daily_result[f'Predicted SO Qty D+{day}'].clip(lower=0).astype(int)
            
            #sample_wh = daily_result[(daily_result["wh_id"] == 160) & (daily_result["hub_id"] == 121)].head()
            #st.dataframe(sample_wh[["Sum of maxqty", "Updated Hub Qty D+1", "Sum of multiplier", "Predicted SO Qty D+1"]])
            
            daily_result = daily_result.rename(columns={"wh_id": "WH ID", "hub_id": "Hub ID"})
            results.append(daily_result[["WH ID", "Hub ID", "product_id", "Sum of maxqty", f"Updated Hub Qty D+{day}", f"Predicted SO Qty D+{day}"]])
        
        # Merge results into a single DataFrame
        final_results_df = results[0]
        for df in results[1:]:
            final_results_df = final_results_df.merge(df, on=["WH ID", "Hub ID","product_id", "Sum of maxqty"], how="left")
            
        #final_results_df["WH Name"] = final_results_df["wh_id"].map(wh_name_mapping)
        
        # Display Results
        #st.subheader("D+1 to D+6 SO Prediction")
        
        def highlight_triggered(val):
            color = 'background-color: lightgreen' if val == "Triggered" else 'background-color: lightcoral'
            return color
    
        #final_results_df = final_results_df.rename(columns={"wh_id": "WH ID", "hub_id": "Hub ID"})

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
        selected_columns = ["Hub ID","product_id", f"Updated Hub Qty {selected_day}", f"Predicted SO Qty {selected_day}", "Max Total Allocation"]
        
        # Apply selection and styling
        styled_df = filtered_df[selected_columns].style.applymap(highlight_triggered, subset=[f"SO vs Reorder Point {selected_day}"])
    
        #styled_df = final_results_df.style.applymap(highlight_triggered, subset=[col for col in final_results_df.columns if "SO vs Reorder Point" in col])

        styled_df = styled_df.hide(axis="index")
        st.markdown('<h4 style="color: maroon;">Summary by WH by Day</h4>', unsafe_allow_html=True)
        st.dataframe(styled_df, use_container_width=True)

        if 40 in filtered_df["WH ID"].values:
            predicted_so_sum = filtered_df.loc[filtered_df["WH ID"] == 40, f"Predicted SO Qty {selected_day}"].sum() #* #0.78
        elif 772 in filtered_df["WH ID"].values:
            predicted_so_sum = filtered_df.loc[filtered_df["WH ID"] == 772, f"Predicted SO Qty {selected_day}"].sum() #*# 0.52
        else:
            predicted_so_sum = 0  # Default value if no matching WH ID is found
        
        st.metric(label="Total Predicted SO Qty", value=f"{predicted_so_sum:,.0f}")
        
        csv = final_results_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download D+1 to D+6 SO Prediction", csv, "d1_d6_so_prediction.csv", "text/csv")
