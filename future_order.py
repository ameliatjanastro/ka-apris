import pandas as pd
import numpy as np
import streamlit as st

# Load Excel Data
@st.cache_data
def load_data(file_path):
    return pd.read_excel(file_path)

# Function to calculate JI, Max Stock WH, RL Qty New, Assumed Stock WH for future cycles, and Assumed OSPO Qty
import re
import pandas as pd

def calculate_columns(df, cycle):
    # Convert date columns
    df['next_coverage_date'] = pd.to_datetime(df['next_coverage_date'], errors='coerce')
    df['next_order_date'] = pd.to_datetime(df['next_order_date'], errors='coerce')
    df['next_inbound_date'] = pd.to_datetime(df['next_inbound_date'], errors='coerce')

    # Fill NaT with today + 14 days
    default_date = pd.to_datetime('today') + pd.Timedelta(days=14)
    df['next_coverage_date'] = df['next_coverage_date'].fillna(default_date)
    df['next_order_date'] = df['next_order_date'].fillna(default_date)
    df['next_inbound_date'] = pd.to_datetime(df['next_inbound_date'], errors='coerce')

    # Ensure numeric columns
    df['avg_sales_final'] = pd.to_numeric(df['avg_sales_final'], errors='coerce').fillna(0)
    df['doi_policy'] = pd.to_numeric(df['doi_policy'], errors='coerce').fillna(0)
    df['stock_wh'] = pd.to_numeric(df['stock_wh'], errors='coerce').fillna(0)
    df['ospo_qty'] = pd.to_numeric(df['ospo_qty'], errors='coerce').fillna(0)
    df['ospr_qty'] = pd.to_numeric(df['ospr_qty'], errors='coerce').fillna(0)
    df['osrl_qty'] = pd.to_numeric(df['osrl_qty'], errors='coerce').fillna(0)
    df['rl_qty_hub'] = pd.to_numeric(df['rl_qty_hub'], errors='coerce').fillna(0)

    # JI and max stock
    df['JI'] = (df['next_coverage_date'] - df['next_order_date']).dt.days.clip(lower=0, upper=1000)
    df['max_stock_wh'] = df['avg_sales_final'] * (df['doi_policy'] + df['JI'])

    # Determine future_order_date based on cycle
    match = re.search(r'Cycle\s*(\d+)', cycle)
    if match:
        cycle_num = int(match.group(1))
        df['future_order_date'] = df['next_order_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D')
        df['future_inbound_date'] = df['next_inbound_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D')
    else:
        df['future_order_date'] = df['next_order_date']  # For 'Current'
        df['future_inbound_date'] = df['next_inbound_date']
    
    # Calculate rl_qty_new
    df['rl_qty_new'] = (
            df['max_stock_wh']
            - df['stock_wh']
            - df['ospo_qty']
            - df['ospr_qty']
            - df['osrl_qty']
            + df['rl_qty_hub']
        ).fillna(0).clip(lower=0).round()
    
    if cycle != 'Current':
        # Calculate future average sales between order dates
        df['avg_sales_future_cycle'] = df['avg_sales_final'] #df.apply(
            #lambda row: df[
                #(df['next_order_date'] >= row['next_order_date']) & 
                #(df['next_order_date'] <= row['future_order_date'])
            #]['avg_sales_final'].mean(),
            #axis=1
        #)
        
        # Calculate assumed stock for the future cycle
        df['assumed_stock_wh'] = (df['stock_wh'] + df['ospr_qty'] - df['avg_sales_future_cycle']).fillna(0).clip(lower=0).round()

        # Sort before shift so we get meaningful previous RL Qty per product/location
        df.sort_values(by=['product_id', 'location_id', 'next_order_date'], inplace=True)

        # Shift by product_id & location_id group
        df['assumed_ospo_qty'] = (
            df.groupby(['product_id', 'location_id'])['rl_qty_new']
            .shift(1)
            .fillna(0)
            .clip(lower=0)
            .round()
        )

        # Final future RL Qty calculation
        df['rl_qty_future'] = (
            df['max_stock_wh']
            - df['assumed_stock_wh']
            - df['assumed_ospo_qty']
            + df['rl_qty_hub']
        ).fillna(0).clip(lower=0).round()
        df['landed_doi'] =  df['assumed_stock_wh']/(df['avg_sales_final']*(df['JI'])).clip(lower=0).round()
        
    else:
        # Current cycle calculations
        df['rl_qty_future'] = df['rl_qty_new'].fillna(0).clip(lower=0).round()
        df['landed_doi'] =  df['stock_wh']/(df['avg_sales_final']*(df['JI'])).clip(lower=0).round()
    return df


# Streamlit Interface
def main():
    st.title('Supply Chain Data Calculation with Cycles')

    # File Upload for Excel
    uploaded_file = st.file_uploader("Upload your Excel file", type="xlsx")
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)

        # Display the first few rows of the dataframe
        #st.write(df.head())

        # Dropdown for selecting the cycle
        num_cycles = 5  # Adjust this based on how far ahead you want to plan
        cycle_options = ['Current'] + [f'Cycle {i}' for i in range(1, num_cycles + 1)]
        
        cycle = st.selectbox("Select Cycle", cycle_options)

        # Calculate columns based on selected cycle
        df = calculate_columns(df, cycle)

        # Display the modified dataframe with future order dates, assumed stock, and assumed OSPO
        st.write(df)
# Run the app
if __name__ == "__main__":
    main()


