import streamlit as st
import pandas as pd
from datetime import date, timedelta

# Read the CSV files
df_sheet2 = pd.read_csv("RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet2.csv")
df_sheet4 = pd.read_csv("RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet4.csv")

# 1. Generate Dates
start_date = date(2025, 6, 1)
end_date = date(2025, 8, 31)
delta = end_date - start_date

date_range = []
for i in range(delta.days + 1):
    current_date = start_date + timedelta(days=i)
    # Format as 'D Mon' (e.g., '1 Jun') - remove leading zero for day
    date_range.append(current_date.strftime('%#d %b')) # Using %#d for Windows, for Linux/macOS use %-d

# 2. Filter df_sheet4 and convert product_id to Int64
df_sheet4_filtered = df_sheet4[df_sheet4['location_id'].isin([796, 160])].copy()
# Convert product_id to nullable integer
df_sheet4_filtered['product_id'] = df_sheet4_filtered['product_id'].astype('Int64')

# 3. Merge Data
# Merge df_sheet4_filtered with df_sheet2 on 'location_id'
merged_df = pd.merge(df_sheet4_filtered, df_sheet2, on=['location_id','primary_vendor_name'], how='left')

# Convert inbound_day string to weekday number
weekday_mapping = {
    'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6
}
merged_df['inbound_day_num'] = merged_df['inbound_day'].map(weekday_mapping)

# 4. Create Result DataFrame
# Identify key columns for the output
st.write("Available columns:", merged_df.columns.tolist())
identifying_cols = merged_df['product_id', 'location_id', 'primary_vendor_name']
print("Requested columns:", identifying_cols)

unique_product_locations = merged_df[identifying_cols].drop_duplicates()

# DEBUG: Print columns of unique_product_locations
print("Columns of unique_product_locations:", unique_product_locations.columns)

# Create the result DataFrame with identifying columns and date columns initialized to 0
result_df = pd.DataFrame(0, index=pd.MultiIndex.from_frame(unique_product_locations), columns=date_range)
result_df = result_df.reset_index() # Convert multi-index back to columns

# DEBUG: Print columns of result_df after reset_index
print("Columns of result_df after reset_index:", result_df.columns)


# 5. Populate Quantities
# Iterate through each row of the merged DataFrame to populate the result_df
for index, row in merged_df.iterrows():
    product_id = row['product_id']
    location_id = row['location_id']
    primary_vendor_name = row['primary_vendor_name']
    qty_order = row['qty_order']
    inbound_day_num = row['inbound_day_num']

    if pd.isna(inbound_day_num) or pd.isna(qty_order): # Skip if inbound day or qty is missing
        continue

    # Find the corresponding row(s) in result_df based on identifying columns
    # and update quantities for matching dates
    mask = (result_df['product_id'] == product_id) & \
           (result_df['location_id'] == location_id) & \
           (result_df['primary_vendor_name'] == primary_vendor_name)

    if not result_df.loc[mask].empty: # Ensure the row exists before attempting to update
        for i, current_date_str in enumerate(date_range):
            current_date_dt = start_date + timedelta(days=i)
            # Check if the weekday of the current date matches the inbound day
            if current_date_dt.weekday() == inbound_day_num:
                # Add qty_order to the specific date column for the matched row
                result_df.loc[mask, current_date_str] += qty_order

# Ensure product_id is integer for final output
result_df['product_id'] = result_df['product_id'].astype(int)

# Save the DataFrame to a CSV file
output_filename = "daily_qty_order_june_august.csv"
result_df.to_csv(output_filename, index=False)

print(f"CSV file '{output_filename}' generated successfully.")
output_df = pd.DataFrame(output_data, columns=output_columns)
output_df = output_df.sort_values(['product_id', 'location_id'])

# Save to CSV
output_df.to_csv('product_inbound_schedule_june_august_2025.csv', index=False)
