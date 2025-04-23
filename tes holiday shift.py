import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.title("SKU-Level Vendor Allocation Scheduler")

st.markdown("""
This app:
- Groups SKU-level data by **vendor**,
- Calculates **blended DOI left**: total stock / total sales avg,
- Allocates vendors to delivery days (Mon–Sat), skipping holidays,
- Respects daily caps: **115 for KOS**, **165 for STL**,
- Applies the vendor’s assigned date to all their SKUs.
""")

# Upload files
holiday_file = st.file_uploader("Upload Holiday CSV (tgl_holiday)", type="csv")
sku_file = st.file_uploader("Upload SKU-level Vendor Data CSV", type="csv")

if holiday_file and sku_file:
    # Load holiday data
    holiday_df = pd.read_csv(holiday_file)
    holiday_df['tgl_holiday'] = pd.to_datetime(holiday_df['tgl_holiday'])
    holidays = set(holiday_df['tgl_holiday'])

    # Load SKU-level data
    sku_df = pd.read_csv(sku_file)

    # Ensure correct types
    sku_df['stock_wh'] = sku_df['stock_wh'].astype(float)
    sku_df['sales_avg'] = sku_df['sales_avg'].replace(0, 0.01)
    sku_df['rl_qty'] = sku_df['rl_qty'].astype(int)

    # Calculate aggregated per vendor
    vendor_group = sku_df.groupby(['primary_vendor_name', 'location_id']).agg({
        'stock_wh': 'sum',
        'sales_avg': 'sum',
        'rl_qty': 'sum'
    }).reset_index()

    vendor_group['doi_left'] = vendor_group['stock_wh'] / vendor_group['sales_avg']

    # Sort by DOI left ascending
    vendor_group = vendor_group.sort_values(by='doi_left')

    # Get the Monday of the current week
    today = datetime.today()
    base_monday = today - timedelta(days=today.weekday())

    # Allocate per vendor
    allocations = []
    daily_totals = {}

    for _, row in vendor_group.iterrows():
        vendor_name = row['primary_vendor_name']
        vendor_wh = row['location_id']
        qty = row['rl_qty']
        max_cap = 115000 if vendor_wh == '40' else 165000

        for i in range(6):  # Monday to Saturday
            candidate_day = base_monday + timedelta(days=i)
            if candidate_day in holidays or candidate_day.weekday() > 5:
                continue

            current_total = daily_totals.get((candidate_day, vendor_wh), 0)
            if current_total + qty <= max_cap:
                # Assign this day to the vendor
                daily_totals[(candidate_day, vendor_wh)] = current_total + qty
                allocations.append({
                    'vendor_name': vendor_name,
                    'allocated_date': candidate_day
                })
                break

# Ensure inbound_date is datetime
sku_df['inbound_date'] = pd.to_datetime(sku_df['inbound_date'])

# Function to shift date if it's a holiday
def shift_if_holiday(date):
    while date in holidays or date.weekday() > 5:  # skip weekends too
        date += timedelta(days=1)
    return date

# Apply shifting logic
sku_df['adjusted_inbound_date'] = sku_df['inbound_date'].apply(shift_if_holiday)

# Show result
st.subheader("Adjusted Inbound Dates")
st.dataframe(sku_df[['product_id','primary_vendor_name', 'location_id', 'inbound_date', 'adjusted_inbound_date']])

