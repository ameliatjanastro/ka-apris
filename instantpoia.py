import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Load data from files
df_schedule = pd.read_csv('RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet2.csv')
df_orders = pd.read_csv('RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet4.csv')

# Create date range from June 1 to August 31, 2025
start_date = datetime(2025, 6, 1)
end_date = datetime(2025, 8, 31)
date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]

# Create a dictionary to map (product_id, location_id) to vendor and quantity
order_map = {}
for _, row in df_orders.iterrows():
    if pd.notna(row['product_id']) and row['product_id'] != '':
        key = (int(row['product_id']), int(row['location_id']))
        order_map[key] = {
            'primary_vendor_name': row['primary_vendor_name'],
            'qty_order': int(row['qty_order']) if pd.notna(row['qty_order']) else 0
        }

# Create a dictionary to map (vendor_name, location_id) to inbound days
schedule_map = {}
for _, row in df_schedule.iterrows():
    key = (row['primary_vendor_name'], int(row['location_id']))
    if key not in schedule_map:
        schedule_map[key] = set()
    schedule_map[key].add(row['inbound_day'])

# Create a list of all unique product_ids and location_ids
product_ids = sorted(set([key[0] for key in order_map.keys()]))
location_ids = sorted(set([key[1] for key in order_map.keys()]))

# Create the output DataFrame
columns = ['product_id', 'product_name', 'location_id', 'primary_vendor_name'] + [date.strftime('%d-%b-%Y') for date in date_range]
output_df = pd.DataFrame(columns=columns)

# Populate the DataFrame
for (product_id, location_id), data in order_map.items():
    vendor_name = data['primary_vendor_name']
    qty = data['qty_order']
    
    # Get inbound days for this vendor and location
    inbound_days = schedule_map.get((vendor_name, location_id), set())
    
    # Create a row with all dates initially 0
    row_data = {
        'product_id': product_id,
        'product_name': '',  # Placeholder as product_name isn't in provided files
        'location_id': location_id,
        'primary_vendor_name': vendor_name
    }
    
    # Initialize all dates to 0
    for date in date_range:
        row_data[date.strftime('%d-%b-%Y')] = 0
    
    # Distribute quantity to inbound days
    day_mapping = {
        'Mon': 0, 'Tue': 1, 'Wed': 2, 
        'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6
    }
    
    for day in inbound_days:
        # Find all dates that match this day of week
        for date in date_range:
            if date.weekday() == day_mapping[day]:
                row_data[date.strftime('%d-%b-%Y')] = qty
    
    output_df = pd.concat([output_df, pd.DataFrame([row_data])], ignore_index=True)

# Sort by product_id and location_id
output_df = output_df.sort_values(['product_id', 'location_id'])

# Save to CSV
output_df.to_csv('product_inbound_schedule_jun_aug_2025.csv', index=False)
