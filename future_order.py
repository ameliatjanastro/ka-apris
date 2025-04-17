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

def calculate_columns(df, cycle, frequency_df,forecast_df):
    # Convert date columns
    df['next_coverage_date'] = pd.to_datetime(df['next_coverage_date'], errors='coerce')
    df['next_order_date'] = pd.to_datetime(df['next_order_date'], errors='coerce')
    df['next_inbound_date'] = pd.to_datetime(df['next_inbound_date'], errors='coerce')
    
    for col in ['avg_sales_final', 'doi_policy', 'stock_wh', 'ospo_qty', 'ospr_qty', 'osrl_qty']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # JI and coverage
    df['cov'] = (df['next_coverage_date'] - df['next_order_date']).dt.days.clip(lower=0, upper=1000)
    df['JI'] = (df['next_inbound_date'] - df['next_order_date']).dt.days.clip(lower=0, upper=1000)
    df['max_stock_wh'] = df['avg_sales_final'] * (df['doi_policy'] + df['cov'])
    
    # Get cycle number from string
    match = re.search(r'Cycle\s*(\d+)', cycle)
    cycle_num = int(match.group(1)) if match else 0
    
    # Create base columns for current cycle
    df['cycle_order_date'] = df['next_order_date']
    df['cycle_inbound_date'] = df['next_inbound_date']# + pd.to_timedelta(df['JI'], unit='D')
    df['cycle_coverage_date'] = df['next_coverage_date']# + pd.to_timedelta(df['cov'], unit='D')
    
    # Now loop to shift the dates by 7 days per cycle number
    if cycle_num > 0:
        df['cycle_order_date'] = df['cycle_order_date'] + pd.to_timedelta(7 * cycle_num, unit='D')
        df['cycle_inbound_date'] = df['cycle_order_date'] + pd.to_timedelta(7 * cycle_num, unit='D')
        df['cycle_coverage_date'] = df['cycle_order_date'] + pd.to_timedelta(7 * cycle_num, unit='D')
    
    # Final formatting
    df['period_days'] = 7  
    df['future_order_date'] = df['cycle_order_date'].dt.strftime('%d-%b-%Y')
    df['future_inbound_date'] = df['cycle_inbound_date'].dt.strftime('%d-%b-%Y')
    df['future_coverage_date'] = df['cycle_coverage_date'].dt.strftime('%d-%b-%Y')
    df['future_order_date2'] = pd.to_datetime(df['future_order_date'], errors='coerce')

    # Set base values for Cycle 0 (Current)
    df['assumed_stock_wh_0'] = df['stock_wh'].fillna(0)
    df['assumed_ospo_qty_0'] = df['ospo_qty'].fillna(0)
    df['rl_qty_amel_0'] = (
        df['max_stock_wh']
        - df['assumed_stock_wh_0']
        - df['assumed_ospo_qty_0']
    ).fillna(0).clip(lower=0).round()
    df[f'avg_sales_future_cycle_0'] = df['avg_sales_final'].fillna(0)

    #test
    df['rl_qty_amel_0'] = df['original rl_qty'].fillna(0)
    forecast_long = forecast_df.melt(
    id_vars=['product_id', 'location_id'],
    var_name='week',
    value_name='forecast_value'
    )

    forecast_long['week'] = forecast_long['week'].astype(int)

    # Choose how many cycles to run based on Streamlit dropdown
    selected_cycle = int(cycle.split()[-1]) if cycle.startswith('Cycle') else 0
    start = 1
    end = selected_cycle + 1

    # Loop from Cycle 1 up to selected cycle
    for i in range(start, end):
        temp = df[['product_id', 'location_id']].copy()
        temp['week'] = i
    
        merged = temp.merge(forecast_long, on=['product_id', 'location_id', 'week'], how='left')

        # Use forecast value where available, otherwise fallback to avg_sales_final
        df[f'avg_sales_future_cycle_{i}'] = df['avg_sales_final']  # default
    
        # Overwrite only where forecast is available
        df.loc[merged['forecast_value'].notna(), f'avg_sales_future_cycle_{i}'] = merged['forecast_value']
        
        # Simulate future sales (can be replaced with actual forecast)
        #df[f'avg_sales_future_cycle_{i}'] = df['avg_sales_final_{i}'] #* (1 + np.random.uniform(-0.2, 0.1, len(df)))

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
            (df[f'assumed_stock_wh_{i}'] + df[f'assumed_ospo_qty_{i}'] - (df[f'avg_sales_future_cycle_{i}'] * df['period_days'])) / df[f'avg_sales_future_cycle_{i}'].replace(0, np.nan)
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
    df[f'avg_sales_future_cycle'] = df[f'avg_sales_future_cycle_{selected_cycle}']

    # Calculate Landed DOI and Coverage date for the selected cycle
    if str(selected_cycle).lower() == 'current':
        df['landed_doi'] = (df['stock_wh'] + df['ospo_qty'] - (df['avg_sales_final'] * df['period_days'])) / df['avg_sales_final']
        df['bisa_cover_sampai'] = ((df['next_order_date'] + pd.to_timedelta(2 * df['JI'], unit='D')).dt.strftime('%d-%b-%Y'))
     
    else:
        df['landed_doi'] = df.get(f'landed_doi_{selected_cycle}', ((df['stock_wh'] + df['ospo_qty'] - (df['avg_sales_final'] * df['period_days'])) / df['avg_sales_final']).round().fillna(0).clip(lower=0))
        df['bisa_cover_sampai'] = df.get(f'bisa_cover_sampai_{selected_cycle}', ((df['next_order_date'] + pd.to_timedelta(2 * df['JI'], unit='D')).dt.strftime('%d-%b-%Y')))  # Adding the coverage date column

    # Add a helper column for the cycle group
    df['cycle_number'] = df['future_order_date'].str.extract(r'(\d+)').astype(float)
    
    # Backup original value for landed_doi for logic comparison
    df['landed_doi_original'] = df['landed_doi']
    
    # Set "currently oos wh" where both assumed_stock_wh and landed_doi are 0
    df.loc[(df['assumed_stock_wh'] == 0) & (df['landed_doi_original'] == 0), 'bisa_cover_sampai'] = 'currently oos wh'
    
    # For rows where only landed_doi is 0, fill with the last non-zero cycle
    # First, replace 0s with NaN in 'landed_doi' temporarily
    
    # Overwrite only those that are NaN landed_doi but non-zero assumed_stock_wh
    df.loc[(df['assumed_stock_wh'] != 0) & (df['landed_doi_original'] == 0), 'bisa_cover_sampai'] = 'tambah coverage/qty'
    df['landed_doi'] = df['landed_doi'].replace(np.nan,0)
    # Optional: clean up helper columns
    
    # Optional: Output total assumptions for the selected cycle
    assumed_stock_tot = f'assumed_stock_wh_{selected_cycle}'
    assumed_rl = f'rl_qty_amel_{selected_cycle}'
    if assumed_stock_tot in df.columns:
        total_assumed_stock = df[assumed_stock_tot].sum()
        st.metric(f"Total Assumed Stock WH ({selected_cycle})", f"{int(total_assumed_stock):,}")
        total_rl = df[assumed_rl].sum()
        st.metric(f"Total RL Qty ({selected_cycle})", f"{int(total_rl):,}")

        rl_qty_col = 'rl_qty_amel' if selected_cycle == 'Current' else f'rl_qty_amel_{selected_cycle}'
        
        # Safely create rl_qty_col if missing
        if rl_qty_col in df.columns:
            df[rl_qty_col] = pd.to_numeric(df[rl_qty_col], errors='coerce').fillna(0)*df['cogs']
        else:
            df[rl_qty_col] = 0  # Create a column of zeros
    
        # Safely create 'mov' column if missing
        if 'mov' in df.columns:
            df['mov'] = pd.to_numeric(df['mov'], errors='coerce').fillna(1)
        else:
            df['mov'] = 1  # Default to 1 if MOV not available
    
        # Calculate summary by vendor
        df = df[~df['primary_vendor_name'].astype(str).str.upper().isin(['0', 'TESTING'])]
        df = df[~df['primary_vendor_name'].astype(str).str.match(r'^\d+$')]
        summary_df = (
            df.groupby(['primary_vendor_name', 'location_id'])
            .agg(
                total_rl_value=(rl_qty_col, 'sum'),
                avg_mov=('mov', 'mean')
            )
            .reset_index()
        )
        summary_df['avg_mov'] = summary_df['avg_mov'].replace(0, 1).fillna(1)  # Avoid division by 0
        summary_df['location_id'] = summary_df['location_id']
        summary_df['rl_to_mov_ratio'] = summary_df['total_rl_value'] / summary_df['avg_mov']
        summary_df['avg_mov'] = summary_df['avg_mov'].replace(1, 0)
        summary_df['rl_to_mov_ratio'] = summary_df.apply(
            lambda row: 1 if row['avg_mov'] == 0 else min(row['total_rl_value'] / row['avg_mov'], 1),
            axis=1
        )
        summary_df['rl_to_mov_ratio'] = summary_df['rl_to_mov_ratio'].clip(upper=1)  # Cap at 1 (100%)
        summary_df['rl_to_mov_ratio'] = (summary_df['rl_to_mov_ratio'] * 100).round(2).astype(str) + '%'  # Convert to % string
        st.dataframe(summary_df)

        summary_distribution = (
                    df.groupby(['primary_vendor_name','vendor_frequency'])
                    .agg(total_rl_qty_per_cycle=('rl_qty_amel', 'sum'))
                    .reset_index()
                )
        
        # Show result
        summary_distribution = summary_distribution[summary_distribution['vendor_frequency'] >= 2]

        st.dataframe(summary_distribution)

        merge_columns = ['vendor_id', 'vendor_frequency']
        merged = df.merge(frequency_df, on=merge_columns, how='left')
        merged['selisih_hari'] = merged['selisih_hari'].fillna('0')
        #selisih_days = str(row['selisih_hari']).split(',')
        base_date = pd.to_datetime(merged['future_inbound_date'], format='%d-%b-%Y', errors='coerce')
        future_date_freq = base_date + merged['selisih_hari']
        vendor_freq = float(merged['vendor_frequency']) if merged['vendor_frequency'] else 1
        qty_per_day_freq = merged['rl_qty_amel'] / vendor_freq

        summary_distribution2 = (
                    df.groupby(['primary_vendor_name','vendor_frequency'])
                    .agg(total_rl_qty_per_cycle2=('qty_per_day_freq', 'sum'))
                    .reset_index()
                )
        
        # Show result
        summary_distribution2 = summary_distribution2[summary_distribution2['vendor_frequency'] >= 2]
        
        st.dataframe(summary_distribution2)

        #detailed_rl_distribution = None
        #if frequency_df is not None:
            #merge_columns = ['vendor_id', 'primary_vendor_name', 'vendor_frequency']
            #merged = df.merge(frequency_df, on=merge_columns, how='left')
            
            #merged['vendor_frequency'] = merged['vendor_frequency'].fillna(1)
            #merged['selisih_hari'] = merged['selisih_hari'].fillna('0')
    
            #expanded_rows = []

            #for _, row in merged.iterrows():
                #selisih_days = str(row['selisih_hari']).split(',')
        
                # Handle case where selisih_hari is '0' or missing
                #if selisih_days == ['0']:
                    #qty_per_day = row['rl_qty_amel']  # full amount to the base date
                    #future_date = pd.to_datetime(row['future_inbound_date'], format='%d-%b-%Y', errors='coerce')#pd.to_datetime(row['future_inbound_date']).strftime('%d-%b-%Y')
                    #expanded_rows.append({
                        #'primary_vendor_name': row['primary_vendor_name'],
                        #'location_id': row['location_id'],
                        #'future_inbound_date': future_date,
                        #'rl_qty_per_cycle': qty_per_day
                    #})
                #else:
                    #try:
                        #vendor_freq = float(row['vendor_frequency']) if row['vendor_frequency'] else 1
                        #qty_per_day = row['rl_qty_amel'] / vendor_freq #gblh per row
                    #except ZeroDivisionError:
                        #qty_per_day = row['rl_qty_amel']
                
                    #try:
                        #base_date = pd.to_datetime(row['future_inbound_date'], format='%d-%b-%Y', errors='coerce')
                        #if pd.isna(base_date):
                            #continue
                
                        #for day_offset in selisih_days:
                            #try:
                                #offset = int(day_offset.strip())
                                #delivery_date = (base_date + pd.Timedelta(days=offset)).strftime('%d-%b-%Y')
                
                                #expanded_rows.append({
                                  #  'primary_vendor_name': row['primary_vendor_name'],
                                  #  'location_id': row['location_id'],
                                  #  'future_inbound_date': delivery_date,  # This is the actual delivery date
                                  #  'rl_qty_per_cycle': qty_per_day #* vendor_freq
                                #})
                            #except Exception:
                                #continue
                    #except Exception:
                        #continue
        
            #detailed_rl_distribution = pd.DataFrame(expanded_rows)
        
            # Ensure all rows are included in summary, even if selisih_hari = 0
            #if not detailed_rl_distribution.empty:
                

    return df
    
# Streamlit Interface
def main():
    st.title('Supply Chain Data Calculation with Cycles')

    uploaded_file = st.file_uploader("Upload your Excel file", type="xlsx")
    freq_file = st.file_uploader("Upload vendor frequency file", type=["csv", "xlsx"])
    forecast_file = st.file_uploader("Upload forecast file", type=["csv", "xlsx"])


    if uploaded_file is not None:
        df = load_data(uploaded_file)
        frequency_df = pd.read_csv(freq_file) if freq_file and freq_file.name.endswith('.csv') else pd.read_excel(freq_file) if freq_file else None
        forecast_df = pd.read_csv(forecast_file)
        
        # Cycle selector
        num_cycles = 6
        cycle_options = ['Current'] + [f'Cycle {i}' for i in range(1, num_cycles + 1)]
        selected_cycle = st.selectbox("Select Cycle", cycle_options)

        result_df = calculate_columns(df.copy(), selected_cycle, frequency_df,forecast_df)

        # Show only selected columns
        cols_to_show = [
            'product_id', 'location_id','primary_vendor_name','avg_sales_future_cycle','doi_policy', 'future_order_date', 'future_inbound_date',
            'assumed_stock_wh', 'assumed_ospo_qty','rl_qty_amel', 'landed_doi','bisa_cover_sampai'
        ]
        existing_cols = [col for col in cols_to_show if col in result_df.columns]

        st.success("Calculation complete.")
        st.dataframe(result_df[existing_cols])

if __name__ == "__main__":
    main()
