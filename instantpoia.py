import pandas as pd
from datetime import datetime, timedelta

# Load the data from the provided files
schedule_df = pd.read_csv('RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet2.csv')
orders_df = pd.read_csv('RL AUTO_[WIP] RL Fresh Final by WH_Table - Sheet4.csv')

# Create date range from June 1 to August 31, 2025
start_date = datetime(2025, 6, 1)
end_date = datetime(2025, 8, 31)
date_columns = [(start_date + timedelta(days=x)).strftime('%d-%b-%Y') for x in range((end_date - start_date).days + 1)]

# Create a mapping of (vendor_name, location_id) to inbound days
vendor_schedule = {}
for _, row in schedule_df.iterrows():
    key = (row['primary_vendor_name'], row['location_id'])
    if key not in vendor_schedule:
        vendor_schedule[key] = set()
    vendor_schedule[key].add(row['inbound_day'])

# Create day of week mapping (Mon=0, Tue=1, etc.)
day_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}

# Prepare the output DataFrame
output_columns = ['product_id', 'product_name', 'location_id', 'primary_vendor_name'] + date_columns
output_data = []

# Process each product order
for _, row in orders_df.iterrows():
    if pd.isna(row['product_id']) or row['product_id'] == '':
        continue
        
    product_id = int(row['product_id'])
    location_id = int(row['location_id'])
    vendor = row['primary_vendor_name']
    qty = int(row['qty_order']) if not pd.isna(row['qty_order']) else 0
    
    # Initialize a row with all dates set to 0
    new_row = {
        'product_id': product_id,
        'product_name': '',  # Placeholder - product names not in provided files
        'location_id': location_id,
        'primary_vendor_name': vendor
    }
    for date in date_columns:
        new_row[date] = 0
    
    # Get the inbound days for this vendor/location
    inbound_days = vendor_schedule.get((vendor, location_id), set())
    
    # Set quantities for inbound days
    for day_abbr in inbound_days:
        day_num = day_map[day_abbr]
        # Find all dates that match this day of week
        for i, date_str in enumerate(date_columns):
            date = datetime.strptime(date_str, '%d-%b-%Y')
            if date.weekday() == day_num:
                new_row[date_str] = qty
    
    output_data.append(new_row)

# Create DataFrame and sort by product_id and location_id
output_df = pd.DataFrame(output_data, columns=output_columns)
output_df = output_df.sort_values(['product_id', 'location_id'])

# Save to CSV
output_df.to_csv('product_inbound_schedule_june_august_2025.csv', index=False)
