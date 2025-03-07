import pandas as pd

# Load SQL-generated SO data
sql_so_df = pd.read_csv("estimated so.csv")  # Ensure this file is uploaded

# Load Demand Forecast data
demand_forecast_df = pd.read_csv("demand_forecast.csv")  # Ensure this file is uploaded

# Define Warehouse IDs for Dry and Fresh WHs
dry_whs = {772: 1/3, 40: 2/3}  # Dry demand split
fresh_whs = {661: "CBN", 160: "PGS"}  # Fresh warehouses

# Extract demand forecast per category
dry_demand = demand_forecast_df[demand_forecast_df['type'] == 'Dry']['demand'].sum()
cbn_demand = demand_forecast_df[demand_forecast_df['type'] == 'CBN']['demand'].sum()
pgs_demand = demand_forecast_df[demand_forecast_df['type'] == 'PGS']['demand'].sum()

# Assign demand forecast to WHs
dry_demand_allocation = {wh: dry_demand * ratio for wh, ratio in dry_whs.items()}
fresh_demand_allocation = {661: cbn_demand, 160: pgs_demand}

# Merge SQL SO data with demand allocations
final_so_df = sql_so_df.copy()
final_so_df['forecast_based_so'] = 0  # Initialize column

# Allocate demand forecast to each WH x Hub
for wh_id, wh_demand in {**dry_demand_allocation, **fresh_demand_allocation}.items():
    hub_mask = final_so_df['wh_id'] == wh_id
    total_sql_so = final_so_df.loc[hub_mask, 'Sum of qty_so_final'].sum()
    
    if total_sql_so > 0:
        # Distribute forecasted SO based on SQL-estimated SO proportions
        final_so_df.loc[hub_mask, 'forecast_based_so'] = (
            final_so_df.loc[hub_mask, 'Sum of qty_so_final'] / total_sql_so * wh_demand
        )

# Compare SQL-estimated SO with Forecast-based SO
final_so_df['final_so_qty'] = final_so_df[['qty_so_final', 'forecast_based_so']].max(axis=1)

# Save the final SO output
#final_so_df.to_csv("final_so_estimate.csv", index=False)

#print("Final SO estimation completed. File saved as final_so_estimate.csv.")
