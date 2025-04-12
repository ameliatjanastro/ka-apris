import pandas as pd
import numpy as np
import streamlit as st
import re

# Load Excel Data
@st.cache_data
def load_data(file_path):
    return pd.read_excel(file_path)

# Function to calculate JI, Max Stock WH, RL Qty New, Assumed Stock WH for future cycles, and Assumed OSPO Qty
import pandas as pd
import numpy as np
import re

def calculate_columns(df, cycle):
    # Convert date columns
    df['next_coverage_date'] = pd.to_datetime(df['next_coverage_date'], errors='coerce')
    df['next_order_date'] = pd.to_datetime(df['next_order_date'], errors='coerce')
    df['next_inbound_date'] = pd.to_datetime(df['next_inbound_date'], errors='coerce')

    # Ensure numeric columns
    for col in ['avg_sales_final', 'doi_policy', 'stock_wh', 'ospo_qty', 'ospr_qty', 'osrl_qty']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # JI and max stock
    df['cov'] = (df['next_coverage_date'] - df['next_order_date']).dt.days.clip(lower=0, upper=1000)
    df['JI'] = (df['next_inbound_date'] - df['next_order_date']).dt.days.clip(lower=0, upper=1000)
    df['max_stock_wh'] = df['avg_sales_final'] * (df['doi_policy'] + df['cov'])

    match = re.search(r'Cycle\s*(\d+)', cycle)
    cycle_num = int(match.group(1)) if match else 0

    # Future dates
    df['future_order_date'] = (df['next_order_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D'))
    df['future_inbound_date'] = (df['next_inbound_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D')).dt.strftime('%d-%b-%Y')

    df['period_days'] = 7  # Default to 7 for period days
    df['future_order_date'] = (df['next_order_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D')).dt.strftime('%d-%b-%Y')
    df['future_order_date2'] = pd.to_datetime(df['future_order_date'], errors='coerce')

    # Set base values for Cycle 0 (Current)
    df['assumed_stock_wh_0'] = df['stock_wh'].fillna(0)
    df['assumed_ospo_qty_0'] = df['ospo_qty'].fillna(0)
    df['rl_qty_amel_0'] = (
        df['max_stock_wh']
        - df['assumed_stock_wh_0']
        - df['assumed_ospo_qty_0']
    ).fillna(0).clip(lower=0).round()

    # Choose how many cycles to run based on Streamlit dropdown
    selected_cycle = int(cycle.split()[-1]) if cycle.startswith('Cycle') else 0
    start = 1
    end = selected_cycle + 1

    # Loop from Cycle 1 up to selected cycle
    for i in range(start, end):
        # Simulate future sales (can be replaced with actual forecast)
        df[f'avg_sales_future_cycle_{i}'] = df['avg_sales_final'] * (1 + np.random.uniform(-0.2, 0.1, len(df)))

        # Assumed stock WH: from previous stock + previous RL Qty - estimated sales
        df[f'assumed_stock_wh_{i}'] = (df[f'assumed_stock_wh_{i-1}'] + df[f'assumed_ospo_qty_{i-1}'] - (df[f'avg_sales_future_cycle_{i}'] * df['period_days'])).fillna(0).clip(lower=0).round()

        # Assumed OSPO: previous cycle's RL Qty
        df[f'assumed_ospo_qty_{i}'] = df[f'rl_qty_amel_{i-1}'].fillna(0)

        # RL Qty for this cycle
        df[f'rl_qty_amel_{i}'] = (
            df['max_stock_wh']
            - df[f'assumed_stock_wh_{i}']
            - df[f'assumed_ospo_qty_{i}']
        ).fillna(0).clip(lower=0).round()

        # Landed DOI for this cycle
        df[f'landed_doi_{i}'] = (
            (df[f'assumed_stock_wh_{i}'] - (df[f'avg_sales_future_cycle_{i}'] * df['period_days'])) / df[f'avg_sales_future_cycle_{i}']
        ).fillna(0).clip(lower=0).round()

        # Calculate the minimum JI required to ensure Landed DOI >= 1
        df[f'min_JI_{i}'] = pd.to_numeric(
            df[f'min_JI_{i}'] if f'min_JI_{i}' in df.columns else pd.Series(0, index=df.index),
            errors='coerce'
        ).fillna(0).clip(lower=0, upper=1000)

        # Calculate the coverage date when Landed DOI is at least 1 (using min_JI)
        df[f'bisa_cover_sampai_{i}'] = ((df['next_coverage_date'] + pd.to_timedelta(cycle_num * df['JI'], unit='D')) + pd.to_timedelta(df[f'min_JI_{i}'], unit='D')).dt.strftime('%d-%b-%Y')

    # After loop: Output selected cycle's columns
    df['assumed_stock_wh'] = df[f'assumed_stock_wh_{selected_cycle}']
    df['assumed_ospo_qty'] = df[f'assumed_ospo_qty_{selected_cycle}']
    df['rl_qty_amel'] = df[f'rl_qty_amel_{selected_cycle}']

    # Calculate Landed DOI and Coverage date for the selected cycle
    if str(selected_cycle).lower() == 'current':
        df['landed_doi'] = (df['stock_wh'] - (df['avg_sales_final'] * df['period_days'])) / df['avg_sales_final']
        df['bisa_cover_sampai'] = ((df['next_order_date'] + pd.to_timedelta(2 * df['JI'], unit='D')).dt.strftime('%d-%b-%Y'))
        df.loc[df['assumed_stock_wh'] == 0, 'bisa_cover_sampai'] = df['future_order_date'].dt.strftime('%d-%b-%Y')
    else:
        df['landed_doi'] = df.get(f'landed_doi_{selected_cycle}', ((df['stock_wh'] - (df['avg_sales_final'] * df['period_days'])) / df['avg_sales_final']).round().fillna(0).clip(lower=0))
        df['bisa_cover_sampai'] = df.get(f'bisa_cover_sampai_{selected_cycle}', ((df['next_order_date'] + pd.to_timedelta(2 * df['JI'], unit='D')).dt.strftime('%d-%b-%Y')))  # Adding the coverage date column

    # Add logic for 'bisa_cover_sampai_custom'
    # Step 1: Identify which columns are the assumed stock columns
    assumed_stock_cols = [col for col in df.columns if col.startswith("assumed_stock_wh_")]

    # Step 2: Create helper masks
    landed_zero = df[f'landed_doi_{i}'] == 0
    all_zero_assumed = df[assumed_stock_cols].sum(axis=1) == 0

    # Step 3: Initialize the column with default values
    df['bisa_cover_sampai_custom'] = df['bisa_cover_sampai']
    df['custom_updated'] = False  # Helper flag to track updates

    # Step 4: Condition 1 — landed_doi == 0 AND all assumed_stock_wh == 0
    mask1 = landed_zero & all_zero_assumed
    df.loc[mask1, 'bisa_cover_sampai_custom'] = "currently OOS WH"
    df.loc[mask1, 'custom_updated'] = True

    # Step 5: Condition 2 — landed_doi == 0 AND at least one assumed_stock_wh > 0
    def find_latest_cycle(row):
        for cycle in sorted(assumed_stock_cols, reverse=True):  # latest cycle first
            if row[cycle] > 0:
                return f"OOS, order at cycle {cycle.split('_')[-1]}"
        return None

    mask2 = landed_zero & ~all_zero_assumed
    df.loc[mask2, 'bisa_cover_sampai_custom'] = df[mask2].apply(find_latest_cycle, axis=1)
    df.loc[mask2, 'custom_updated'] = True

    # Step 6: Condition 3 — Only landed_doi == 0 and not already updated
    mask3 = landed_zero & ~df['custom_updated']
    df.loc[mask3, 'bisa_cover_sampai_custom'] = "add coverage/qty"

    # Optional cleanup
    df.drop(columns='custom_updated', inplace=True)

    # Optional: Output total assumptions for the selected cycle
    assumed_stock_tot = f'assumed_stock_wh_{selected_cycle}'
    assumed_rl = f'rl_qty_amel_{selected_cycle}'
    if assumed_stock_tot in df.columns:
        total_assumed_stock = df[assumed_stock_tot].sum()
        st.metric(f"Total Assumed Stock WH ({selected_cycle})", f"{int(total_assumed_stock):,}")
        total_rl = df[assumed_rl].sum()
        st.metric(f"Total RL Qty ({selected_cycle})", f"{int(total_rl):,}")

    return df
    
# Streamlit Interface
def main():
    st.title('Supply Chain Data Calculation with Cycles')

    uploaded_file = st.file_uploader("Upload your Excel file", type="xlsx")

    if uploaded_file is not None:
        df = load_data(uploaded_file)

        # Cycle selector
        num_cycles = 12
        cycle_options = ['Current'] + [f'Cycle {i}' for i in range(1, num_cycles + 1)]
        selected_cycle = st.selectbox("Select Cycle", cycle_options)

        result_df = calculate_columns(df.copy(), selected_cycle)

        # Show only selected columns
        cols_to_show = [
            'product_id', 'location_id', 'future_order_date', 'future_inbound_date',
            'assumed_stock_wh', 'assumed_ospo_qty','rl_qty_amel', 'landed_doi','bisa_cover_sampai'
        ]
        existing_cols = [col for col in cols_to_show if col in result_df.columns]

        st.success("Calculation complete.")
        st.dataframe(result_df[existing_cols])

if __name__ == "__main__":
    main()


