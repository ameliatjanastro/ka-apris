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

    stock_df = pd.read_excel('gab.xlsx')

    # Merge the stock data with the final SO data on 'product_id'
    final_so_df = final_so_df.merge(stock_df, on=['product_id','wh_id'], how='left')

    # Load Stock in Transit to Hub
    stock_in_transit_df = pd.read_excel('sit.xlsx')
    
    # Merge stock in transit with the final SO DataFrame
    final_so_df = final_so_df.merge(stock_in_transit_df, on=['wh_id', 'hub_id'], how='left')
    final_so_df['quantity'] = final_so_df['quantity'].fillna(0)

    # Add stock in transit to the hub quantity
    final_so_df['Sum of hub_qty'] += final_so_df['quantity']
    
    # Load Incoming Stock to WH
    #incoming_ospo = pd.read_excel('ospo.xlsx')
    
    # Merge incoming stock with the stock DataFrame
    #stock_df = stock_df.merge(incoming_ospo, on=['wh_id', 'product_id'], how='left')
    #stock_df['quantity_po'] = stock_df['quantity_po'].fillna(0)
    
    # Update the stock quantity by adding incoming stock
    #stock_df['stock'] += stock_df['quantity_po']

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
            wh_40_products = set(dry_forecast_df[dry_forecast_df["WH ID"] == 40]["product_id"].unique())
            wh_772_products = set(dry_forecast_df[dry_forecast_df["WH ID"] == 772]["product_id"].unique())
                
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

            
            #daily_result.loc[daily_result['WH ID'] == 40, f'Predicted SO Qty D+{day}'] *= 0.71
            #daily_result.loc[daily_result['WH ID'] == 772, f'Predicted SO Qty D+{day}'] *= 0.535
            
        daily_result = daily_result.rename(columns={"wh_id": "WH ID", "hub_id": "Hub ID"})
        results.append(daily_result[["WH ID", "Hub ID", "product_id", "Sum of maxqty", f"Updated Hub Qty D+{day}", f"Predicted SO Qty D+{day}"]])
        
    # Merge results into a single DataFrame
    final_results_df = results[0]
    for df in results[1:]:
        final_results_df = final_results_df.merge(df, on=["WH ID", "Hub ID","product_id", "Sum of maxqty"], how="left")
            
        #final_results_df["WH Name"] = final_results_df["wh_id"].map(wh_name_mapping)
        

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
        
        if 40 in filtered_df["WH ID"].values:
            predicted_so_sum = filtered_df.loc[filtered_df["WH ID"] == 40, f"Predicted SO Qty {selected_day}"].sum() #* #0.78
        elif 772 in filtered_df["WH ID"].values:
            predicted_so_sum = filtered_df.loc[filtered_df["WH ID"] == 772, f"Predicted SO Qty {selected_day}"].sum() #*# 0.52
        else:
            predicted_so_sum = 0  # Default value if no matching WH ID is found
        
        st.metric(label="Total Predicted SO Qty", value=f"{predicted_so_sum:,.0f}")
