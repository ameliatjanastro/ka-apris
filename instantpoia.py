import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Load your input files
df_sheet4 = pd.read_csv("RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet4.csv")
df_sheet2 = pd.read_csv("RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet2.csv")

# Step 1: Generate date columns
start_date = datetime(2025, 6, 1)
end_date = datetime(2025, 8, 31)
date_range = pd.date_range(start=start_date, end=end_date, freq='D')
date_columns = [d.strftime('%-d %b') for d in date_range]

# Step 2: Create product × location_id matrix
unique_products = df_sheet4[['product_id', 'primary_vendor_name']].drop_duplicates()
vendor_locations = df_sheet2[['primary_vendor_name', 'location_id']].drop_duplicates()
unique_products = unique_products.merge(vendor_locations, on='primary_vendor_name', how='left')

# Initialize the matrix
final_matrix = unique_products.copy()
for col in date_columns:
    final_matrix[col] = 0

# Step 3: Weekday mapping
weekday_map = {
    'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6
}
inbound_dates_by_day = {i: [] for i in range(7)}
for d in date_range:
    inbound_dates_by_day[d.weekday()].append(d.strftime('%-d %b'))

# Step 4: Merge and distribute quantities
# Melt the date columns into long format: one row per product/date/qty
df_sheet4.columns = df_sheet4.columns.str.strip()
df_sheet2.columns = df_sheet2.columns.str.strip()
st.write("Sheet4 columns:", df_sheet4.columns.tolist())

date_cols = [col for col in df_sheet4.columns if '-' in col]  # e.g., '02-May-2025'
df_long = df_sheet4.melt(
    id_vars=['product_id', 'primary_vendor_name'],
    value_vars=date_cols,
    var_name='order_date',
    value_name='qty_order'
)

# Convert to datetime
df_long['order_date'] = pd.to_datetime(df_long['order_date'], dayfirst=True)
df_long = df_long[df_long['qty_order'] > 0]  # remove 0 orders

# Merge with inbound days & locations
merged_orders = df_long.merge(
    df_sheet2[['primary_vendor_name', 'location_id', 'inbound_day']],
    on='primary_vendor_name',
    how='left'
)

merged_orders = merged_orders.dropna(subset=['inbound_day', 'location_id'])


for _, row in merged_orders.iterrows():
    product_id = row['product_id']
    vendor = row['primary_vendor_name']
    location_id = row['location_id']
    qty_order = row['qty_order']
    inbound_day = row['inbound_day']
    weekday_num = weekday_map.get(inbound_day)

    if weekday_num is not None:
        matching_dates = inbound_dates_by_day[weekday_num]
        if matching_dates:
            qty_per_date = qty_order // len(matching_dates)
            remainder = qty_order % len(matching_dates)

            for i, date in enumerate(matching_dates):
                qty = qty_per_date + (1 if i < remainder else 0)
                mask = (
                    (final_matrix['product_id'] == product_id) &
                    (final_matrix['primary_vendor_name'] == vendor) &
                    (final_matrix['location_id'] == location_id)
                )
                final_matrix.loc[mask, date] += qty

# Step 5: Export to CSV
final_matrix.to_csv("daily_order_matrix.csv", index=False)
print("✅ Exported to 'daily_order_matrix.csv'")
