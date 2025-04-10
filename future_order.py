import pandas as pd
import numpy as np
import streamlit as st

# Load Excel Data
@st.cache_data
def load_data(file_path):
    return pd.read_excel(file_path)

# Function to calculate JI, Max Stock WH, RL Qty New, Assumed Stock WH for future cycles, and Assumed OSPO Qty
def calculate_columns(df, cycle):
    # Convert 'next_coverage_date' and 'next_order_date' to datetime if they aren't already
    df['next_coverage_date'] = pd.to_datetime(df['next_coverage_date'], errors='coerce').dt.date
    df['next_order_date'] = pd.to_datetime(df['next_order_date'], errors='coerce').dt.date
    
    # Ensure avg_sales_final and doi_policy are numeric and handle missing values
    df['avg_sales_final'] = pd.to_numeric(df['avg_sales_final'], errors='coerce')
    df['doi_policy'] = pd.to_numeric(df['doi_policy'], errors='coerce')
    
    # Handle missing values by filling with 0 or another appropriate strategy
    df['avg_sales_final'].fillna(0, inplace=True)
    df['doi_policy'].fillna(0, inplace=True)

    # Check for missing dates and handle them (e.g., fill with a default date)
    # Ensure 'next_coverage_date' is in datetime format first
    df['next_coverage_date'] = pd.to_datetime(df['next_coverage_date'], errors='coerce')
    df['next_order_date'] = pd.to_datetime(df['next_order_date'], errors='coerce')
    
    # Fill NaN values with a default date (today + 14 days)
    df['next_coverage_date'].fillna(pd.to_datetime('today') + pd.Timedelta(days=14), inplace=True)
    df['next_order_date'].fillna(pd.to_datetime('today') + pd.Timedelta(days=14), inplace=True)
    
    # Ensure both columns are of datetime type
    df['next_coverage_date'] = pd.to_datetime(df['next_coverage_date'], errors='coerce')
    df['next_order_date'] = pd.to_datetime(df['next_order_date'], errors='coerce')
        
    # Calculate JI as the difference between coverage_date and order_date
    df['JI'] = (df['next_coverage_date'] - df['next_order_date']).dt.days
    
    # Overwrite Max Stock WH based on the given formula
    df['max_stock_wh'] = df['avg_sales_final'] * (df['doi_policy'] + (df['next_coverage_date'] - df['next_order_date']).dt.days)
    
    # Calculate RL Qty New
    df['rl_qty_new'] = df['stock_wh'] - df['ospo_qty'] - df['osrl_qty'] - df['ospr_qty'] + df['rl_qty_hub']
    
    # Looping logic for future cycles based on the selected cycle
    df['future_order_date'] = df['next_order_date']  # Default to the current order date

    # Cycle logic
    if cycle == 'Cycle 1':
        df['future_order_date'] = df['next_order_date'] + pd.to_timedelta(df['JI'], unit='D')
    elif cycle == 'Cycle 2':
        df['future_order_date'] = df['next_order_date'] + pd.to_timedelta(2 * df['JI'], unit='D')

    # Calculate Assumed Stock WH for future cycle
    if cycle != 'Current':
        # Calculate Average Sales from RL order date to RL date of current cycle
        df['avg_sales_future_cycle'] = df.apply(
            lambda row: np.mean(
                df[(df['next_order_date'] >= row['next_order_date']) & (df['next_order_date'] <= row['future_order_date'])]['avg_sales_final']
            ), axis=1
        )
        # Assumed Stock WH for future cycle: last cycle stock + OSPR last cycle - average sales from RL order date to RL date this cycle
        df['assumed_stock_wh'] = (df['stock_wh'] + df['ospr_qty'] - df['avg_sales_future_cycle'])
    else:
        df['assumed_stock_wh'] = df['stock_wh']  # For current cycle, assumed stock is simply the stock_wh

    # Assumed OSPO Qty for future cycle: from previous RL Qty of the last cycle
    df['assumed_ospo_qty'] = df['rl_qty_new'].shift(1)  # Assuming RL Qty from last cycle is the OSPO for future cycle

    return df

# Streamlit Interface
def main():
    st.title('Supply Chain Data Calculation with Cycles')

    # File Upload for Excel
    uploaded_file = st.file_uploader("Upload your Excel file", type="xlsx")
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)

        # Display the first few rows of the dataframe
        st.write(df.head())

        # Dropdown for selecting the cycle
        cycle = st.selectbox("Select Cycle", ["Current", "Cycle 1", "Cycle 2"])

        # Calculate columns based on selected cycle
        df = calculate_columns(df, cycle)

        # Display the modified dataframe with future order dates, assumed stock, and assumed OSPO
        st.write(df)
# Run the app
if __name__ == "__main__":
    main()


