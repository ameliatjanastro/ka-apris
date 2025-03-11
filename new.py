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

    # Load Stock in Transit to Hub
    stock_in_transit_df = pd.read_excel('sit.xlsx')
    
    # Merge stock in transit with the final SO DataFrame
    final_so_df = final_so_df.merge(stock_in_transit_df, on=['wh_id', 'hub_id'], how='left')
    final_so_df['quantity'] = final_so_df['quantity'].fillna(0)

    # Add stock in transit to the hub quantity
    final_so_df['Sum of hub_qty'] += final_so_df['quantity']
    
    # Load Incoming Stock to WH
    incoming_ospo = pd.read_excel('ospo.xlsx')
    
    # Merge incoming stock with the stock DataFrame
    stock_df = stock_df.merge(incoming_ospo, on=['wh_id', 'product_id'], how='left')
    stock_df['quantity_po'] = stock_df['quantity_po'].fillna(0)
    
    # Update the stock quantity by adding incoming stock
    stock_df['stock'] += stock_df['quantity_po']
