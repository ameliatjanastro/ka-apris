import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.title("SKU-Level Vendor Allocation Scheduler")

st.markdown("""
This app:
- Groups SKU-level data by **vendor**,
- Calculates **blended DOI left**: total stock / total sales avg,
- Allocates vendors to delivery days (Mon–Sat), skipping holidays,
- Respects daily caps: **115,000 for KOS (WH 40)**, **165,000 for STL**,
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
    sku_df['sales_avg'] = sku_df['sales_avg'].replace(0, 0.01)  # Avoid division by zero
    sku_df['rl_qty'] = sku_df['rl_qty'].astype(int)
    sku_df['doi_policy'] = sku_df['doi_policy'].astype(int)
    
    # Calculate aggregated per vendor
    vendor_group = sku_df.groupby(['primary_vendor_name', 'location_id']).agg({
        'stock_wh': 'sum',
        'sales_avg': 'sum',
        'rl_qty': 'sum',
        'doi_policy': 'mean'  # DOI policy for vendor
    }).reset_index()

    vendor_group['doi_left'] = vendor_group['stock_wh'] / vendor_group['sales_avg']
    vendor_group = vendor_group.sort_values(by='rl_qty', ascending=False)

    # Add original and revised DOI and RL qty for all vendors
    sku_df['original_doi'] = sku_df['doi_policy']
    sku_df['revised_doi'] = sku_df['doi_policy'].apply(lambda x: x - 1 if x > 3 else x)

    # Recalculate RL qty using the revised DOI
    sku_df['original_rl_qty'] = sku_df['rl_qty']
    sku_df['revised_rl_qty'] = sku_df.apply(
        lambda row: int(row['rl_qty'] * (row['revised_doi'] / row['doi_policy'])) if row['doi_policy'] > 3 else row['rl_qty'],
        axis=1
    )

    # Base Monday of the current week
    today = datetime.today()
    base_monday = today - timedelta(days=today.weekday())

    # Allocation logic
    allocations = []
    daily_totals = {}
    vendor_alloc_map = {}
    unallocated_vendors_original = []
    unallocated_vendors_revised = []

    for _, row in vendor_group.iterrows():
        vendor_name = row['primary_vendor_name']
        vendor_wh = row['location_id']
        qty_original = row['rl_qty']
        qty_revised = row['revised_rl_qty']
        max_cap = 115000 if str(vendor_wh) == '40' else 165000

        # Original allocation attempt
        allocated_original = False
        for i in range(6):  # Monday to Saturday
            candidate_day = base_monday + timedelta(days=i)
            if candidate_day in holidays or candidate_day.weekday() > 5:
                continue

            current_total = daily_totals.get((candidate_day, vendor_wh), 0)
            if current_total + qty_original <= max_cap:
                daily_totals[(candidate_day, vendor_wh)] = current_total + qty_original
                vendor_alloc_map[(vendor_name, vendor_wh)] = candidate_day
                allocations.append({
                    'vendor_name': vendor_name,
                    'allocated_date': candidate_day
                })
                allocated_original = True
                break

        if not allocated_original:
            unallocated_vendors_original.append({
                'vendor_name': vendor_name,
                'location_id': vendor_wh,
                'original_rl_qty': qty_original,
                'original_doi': row['doi_policy']
            })

        # Revised allocation attempt
        allocated_revised = False
        for i in range(6):  # Monday to Saturday
            candidate_day = base_monday + timedelta(days=i)
            if candidate_day in holidays or candidate_day.weekday() > 5:
                continue

            current_total = daily_totals.get((candidate_day, vendor_wh), 0)
            if current_total + qty_revised <= max_cap:
                daily_totals[(candidate_day, vendor_wh)] = current_total + qty_revised
                vendor_alloc_map[(vendor_name, vendor_wh)] = candidate_day
                allocations.append({
                    'vendor_name': vendor_name,
                    'allocated_date': candidate_day
                })
                allocated_revised = True
                break

        if not allocated_revised:
            unallocated_vendors_revised.append({
                'vendor_name': vendor_name,
                'location_id': vendor_wh,
                'revised_rl_qty': qty_revised,
                'revised_doi': row['revised_doi']
            })

    # Map allocated date to each SKU
    sku_df['allocated_date'] = sku_df.apply(
        lambda row: vendor_alloc_map.get((row['primary_vendor_name'], row['location_id']), pd.NaT),
        axis=1
    )

    # Shift if it falls on holiday or weekend
    def shift_if_holiday(date):
        while pd.notna(date) and (date in holidays or date.weekday() > 5):
            date += timedelta(days=1)
        return date

    sku_df['adjusted_inbound_date'] = sku_df['allocated_date'].apply(shift_if_holiday)

    # Show result with adjusted dates, original and revised RL qtys
    st.subheader("Adjusted Inbound Dates with Original & Revised RL Qty and DOI")
    st.dataframe(sku_df[['product_id', 'primary_vendor_name', 'location_id', 'original_rl_qty', 'revised_rl_qty', 'original_doi', 'revised_doi', 'allocated_date', 'adjusted_inbound_date']])

    # Summary by adjusted date and warehouse
    summary_df = sku_df.groupby(['adjusted_inbound_date', 'location_id'])[['original_rl_qty', 'revised_rl_qty']].sum().reset_index()
    summary_df.rename(columns={
        'adjusted_inbound_date': 'Date',
        'location_id': 'Warehouse (location_id)',
        'original_rl_qty': 'Total Original RL Qty',
        'revised_rl_qty': 'Total Revised RL Qty'
    }, inplace=True)

    summary_df['Date'] = summary_df['Date'].dt.strftime('%Y-%m-%d')
    summary_df = summary_df.sort_values(by=['Date', 'Warehouse (location_id)'])

    st.subheader("📊 Daily Allocation Summary (Original & Revised RL Qty)")
    st.dataframe(summary_df)

    # Show unallocated vendors for original RL qty
    if unallocated_vendors_original:
        st.subheader("⚠️ Unallocated Vendors (Original RL Qty and DOI)")
        unallocated_df_original = pd.DataFrame(unallocated_vendors_original)
        unallocated_df_original = unallocated_df_original.rename(columns={
            'vendor_name': 'Vendor Name',
            'location_id': 'Warehouse',
            'original_rl_qty': 'Original RL Qty',
            'original_doi': 'Original DOI'
        })
        st.dataframe(unallocated_df_original)

    # Show unallocated vendors for revised RL qty
    if unallocated_vendors_revised:
        st.subheader("⚠️ Unallocated Vendors (Revised RL Qty and DOI)")
        unallocated_df_revised = pd.DataFrame(unallocated_vendors_revised)
        unallocated_df_revised = unallocated_df_revised.rename(columns={
            'vendor_name': 'Vendor Name',
            'location_id': 'Warehouse',
            'revised_rl_qty': 'Revised RL Qty',
            'revised_doi': 'Revised DOI'
        })
        st.dataframe(unallocated_df_revised)

    else:
        st.success("🎉 All vendors were successfully allocated within capacity limits.")




