import streamlit as st
import math

def calculate_dynamic_eoq(
    forecast_demand,
    demand_std_dev,
    safety_factor,
    labor_cost_per_hour,
    time_per_order_hours,
    cogs,
    holding_cost
):
    adjusted_demand = forecast_demand + (safety_factor * demand_std_dev)
    adjusted_order_cost = (labor_cost_per_hour * time_per_order_hours)
    adjusted_holding_cost = cogs * holding_cost
    
    eoq = math.sqrt((2 * adjusted_demand * adjusted_order_cost) / adjusted_holding_cost)
    return round(eoq, 2)

st.title("📦 Dynamic EOQ Calculator")

st.sidebar.header("Input Parameters")

forecast_demand = st.sidebar.number_input("Forecasted Annual Demand (units)", value=10000, step=100)
demand_std_dev = st.sidebar.number_input("Demand Standard Deviation (units)", value=1200, step=100)
safety_factor = st.sidebar.slider("Safety Factor (Z-score)", min_value=0.0, max_value=3.0, value=1.65, step=0.05)

labor_cost_per_hour = st.sidebar.number_input("Labor Cost per Hour (IDR)", value=15000, step=1000)
time_per_order_hours = st.sidebar.number_input("Time Required per Order (hours)", value=1.0, step=0.1)

cogs = st.sidebar.number_input("Cost of Goods Sold per Unit (USD)", value=50.0, step=1.0)
holding_cost_rate = st.sidebar.slider("Annual Holding Cost Rate (% of COGS)", min_value=0.01, max_value=0.50, value=0.18, step=0.01)

if st.button("Calculate EOQ"):
    eoq = calculate_dynamic_eoq(
        forecast_demand,
        demand_std_dev,
        safety_factor,
        labor_cost_per_hour,
        time_per_order_hours,
        cogs,
        holding_cost
    )

    st.success(f"📊 Dynamic EOQ: {eoq} units")
else:
    st.info("Enter parameters and click 'Calculate EOQ' to get the result.")
