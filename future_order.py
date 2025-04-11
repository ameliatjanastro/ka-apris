import pandas as pd
import numpy as np
import streamlit as st
import re

# Load Excel Data
@st.cache_data
def load_data(file_path):
    return pd.read_excel(file_path)

# Function to calculate JI, Max Stock WH, RL Qty New, Assumed Stock WH for future cycles, and Assumed OSPO Qty
def calculate_columns(df, cycle):
    # Convert date columns
    df['next_coverage_date'] = pd.to_datetime(df['next_coverage_date'], errors='coerce')
    df['next_order_date'] = pd.to_datetime(df['next_order_date'], errors='coerce')
    df['next_inbound_date'] = pd.to_datetime(df['next_inbound_date'], errors='coerce')

    # Ensure numeric columns
    for col in ['avg_sales_final', 'doi_policy', 'stock_wh', 'ospo_qty', 'ospr_qty', 'osrl_qty']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # JI and max stock
    df['JI'] = (df['next_coverage_date'] - df['next_order_date']).dt.days.clip(lower=0, upper=1000)
    df['max_stock_wh'] = df['avg_sales_final'] * (df['doi_policy'] + df['JI'])

    # Determine cycle number
    match = re.search(r'Cycle\s*(\d+)', cycle)
    cycle_num = int(match.group(1)) if match else 0

    # Future dates
    df['future_order_date'] = (df['next_order_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D')).dt.strftime('%d-%b-%Y')
    df['future_inbound_date'] = (df['next_inbound_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D')).dt.strftime('%d-%b-%Y')

    # RL Qty New
    df['rl_qty_amel'] = (
        df['max_stock_wh']
        - df['stock_wh']
        - df['ospo_qty']
        - df['ospr_qty']
        - df['osrl_qty']
    ).fillna(0).clip(lower=0).round()

    if cycle == 'Current':
        df['rl_qty_amel'] = df['max_stock_wh']
            - df['stock_wh']
            - df['ospo_qty']
        df['landed_doi'] = (df['stock_wh'] / (df['avg_sales_final'] * df['JI'])).fillna(0).clip(lower=0).round()
        df['assumed_stock_wh'] = df['stock_wh']
        df['assumed_ospo_qty'] = df['ospo_qty']
    elif cycle == 'Cycle 1':
        df['avg_sales_future_cycle'] = df['avg_sales_final'] * (1 + np.random.uniform(-0.2, 0.1, size=len(df)))
        df['assumed_stock_wh'] = (df['assumed_stock_wh'].shift(1).fillna(0) + df['assumed_ospo_qty'].shift(1).fillna(0) - df['avg_sales_future_cycle']).fillna(0).clip(lower=0).round()
        df['assumed_ospo_qty'] = df['rl_qty_amel'].shift(1).fillna(0)
        df['rl_qty_amel'] = (
            df['max_stock_wh']
            - df['assumed_stock_wh']
            - df['assumed_ospo_qty']
        ).fillna(0).clip(lower=0).round()
        df['landed_doi'] = (df['assumed_stock_wh'] / (df['avg_sales_final'] * df['JI'])).fillna(0).clip(lower=0).round()
    else:
        df['avg_sales_future_cycle'] = df['avg_sales_final'] * (1 + np.random.uniform(-0.2, 0.1, size=len(df)))

        df.sort_values(by=['product_id', 'location_id', 'next_order_date'], inplace=True)
       
        for i in range(2, cycle_num + 1):
            df[f'assumed_ospo_qty_{i}'] = df.groupby(['product_id', 'location_id'])[f'assumed_ospo_qty_{i-1}' if i > 2 else 'assumed_ospo_qty'].shift(1).fillna(0)
            df[f'assumed_stock_wh_{i}'] = (df.groupby(['product_id', 'location_id'])[f'assumed_stock_wh_{i-1}' if i > 2 else 'assumed_stock_wh'].shift(1).fillna(0))+df[f'assumed_ospo_qty_{i}']
            df[f'rl_qty_amel_{i}'] = (
                df['max_stock_wh']
                - df[f'assumed_stock_wh_{i}']
                - df[f'assumed_ospo_qty_{i}']
            ).fillna(0).clip(lower=0).round()

            df['assumed_stock_wh'] = df[f'assumed_stock_wh_{i}']
            df['assumed_ospo_qty'] = df[f'assumed_ospo_qty_{i}']
            df['rl_qty_amel'] = df[f'rl_qty_amel_{i}']

        df['landed_doi'] = (df['assumed_stock_wh'] / (df['avg_sales_final'] * df['JI'])).fillna(0).clip(lower=0).round()

    return df

# Streamlit Interface
def main():
    st.title('Supply Chain Data Calculation with Cycles')

    uploaded_file = st.file_uploader("Upload your Excel file", type="xlsx")

    if uploaded_file is not None:
        df = load_data(uploaded_file)

        # Cycle selector
        num_cycles = 6
        cycle_options = ['Current'] + [f'Cycle {i}' for i in range(1, num_cycles + 1)]
        selected_cycle = st.selectbox("Select Cycle", cycle_options)

        result_df = calculate_columns(df.copy(), selected_cycle)

        # Show only selected columns
        cols_to_show = [
            'product_id', 'location_id', 'future_order_date', 'future_inbound_date',
            'rl_qty_amel', 'landed_doi', 'assumed_stock_wh', 'assumed_ospo_qty'
        ]
        existing_cols = [col for col in cols_to_show if col in result_df.columns]

        st.success("Calculation complete.")
        st.dataframe(result_df[existing_cols])

if __name__ == "__main__":
    main()


