import streamlit as st
import pandas as pd
import numpy as np
import math
import altair as alt

st.markdown(
    """
    <style>
    /* Decrease font size for most text */
    html, body, .css-1d391kg, .css-1v3fvcr {
        font-size: 11px;  /* adjust this value as needed */
    }
    /* You can target specific elements too */
    /* For example, headers: */
    h1, h2, h3, h4, h5, h6 {
        font-size: smaller;
    }
    </style>
    """,
    unsafe_allow_html=True
)





def calculate_clipped_doi(eoq, daily_demand, vendor_freq):
    if daily_demand <= 0 or eoq <= 0:
        return 0
    raw_doi = eoq / daily_demand
    min_doi = 3 if vendor_freq == 2 else 7
    return round(min(max(raw_doi, min_doi), 28), 2)


def clean_id(val):
    val = str(val).strip()
    return val.replace(".0", "") if val.endswith(".0") else val

tab1, tab2 = st.tabs(["EOQ 3 Step DOIs", "RL vs EOQ Diagnostic Matrix"])
with tab1:
    st.title("📦 EOQ 3 Step DOIs")
    
    # User Inputs
    # monthly_salary = st.number_input("💰 Monthly Salary (IDR)", value=8000000)
    safety_factor = st.number_input("🛡️ Safety Factor (Z)", value=1.65)
    default_lead_time = st.number_input("📦 Internal Lead Time (SC+comful)", value=2)
    
    
    #cost_per_minute = monthly_salary / (22 * 8 * 60)  # 22 workdays × 8 hours/day × 60 min
    
    # File Uploads
    uploaded_demand = st.file_uploader("📄 Upload Demand & Order Time CSV", type=["csv"])
    uploaded_holding = st.file_uploader("🏢 Upload Holding Cost CSV", type=["csv"])
    
    if uploaded_demand and uploaded_holding:
        try:
            df_demand = pd.read_csv(uploaded_demand)
            df_holding = pd.read_csv(uploaded_holding)
    
            # Clean and standardize keys
            for df in [df_demand, df_holding]:
                df['product_id'] = df['product_id'].apply(clean_id)
                df['location_id'] = df['location_id'].apply(clean_id)
    
            # Clean holding cost (remove 'Rp', commas, etc)
            df_holding['holding_cost'] = df_holding['holding_cost'].astype(float)
    
            st.markdown("""
                ### 📌 Assumptions:
                - EOQ is calculated based on **monthly demand and cost**, due to the **rapid growth rate**.
                - **Holding Cost** is estimated at **5% of COGS**.
                - **Ordering Cost** is derived from:  
                  **(Total Revenue by WH / Count of SKUs) × (Product COGS contribution ÷ Total COGS)**.
                """)
            #st.write("Demand File:")
            #st.dataframe(df_demand.head(5000))
            #st.write("Holding Cost File:")
            #st.dataframe(df_holding.head())
    
            # Merge on product_id and location_id
            df = pd.merge(df_demand, df_holding, on=['product_id', 'location_id'], how='inner')
    
            # Calculate adjusted annual demand
            df['adjusted_demand'] = (df['avg_sales_final'])*30 # + safety_factor * df['demand_std_dev']) * 30
            df['ordering_cost'] = 101539.972 * (1+(df['cogs_contr']*100))
            df['monthly_holding_cost'] = df['holding_cost'] * 30
    
            # EOQ formula
            df['EOQ'] = (np.sqrt((2 * df['adjusted_demand'] * df['ordering_cost']) / df['monthly_holding_cost']))#*14/df["vendor_frequency"])
            df['EOQ'] = df['EOQ'].fillna(0).round(2)
    
            # DOI calculation
            df["daily_demand"] = df["adjusted_demand"] / 30
            df["opt_freq"] = df["adjusted_demand"]/df['EOQ']
            df["DOI"] = df['EOQ']/df["daily_demand"] #df.apply(
                #lambda row: calculate_clipped_doi(row["EOQ"], row["daily_demand"], row["vendor_frequency"]),
                #axis=1
            #)
    
            df["optimal_order_freq"] = df["opt_freq"].apply(lambda x: min(x, 12))
    
            # Calculate frequency reduction ratio where opt_freq > 12
            df["freq_reduction_pct"] = np.where(
                df["opt_freq"] > 12,
                (df["opt_freq"] - 12) / df["opt_freq"],
                0
            )
            
            # Increase EOQ by the same % as the reduction
            df["EOQ_final"] = df["EOQ"] * (1 + df["freq_reduction_pct"])
    
            # Step 4: Calculate preliminary DOI_final
            df["DOI_final_pre_cap"] = df["EOQ_final"] / df["daily_demand"]
            
            # Step 5: Calculate delta days needed to meet minimum of 3 days
            df["doi_delta"] = np.where(df["DOI_final_pre_cap"] < 3, 3 - df["DOI_final_pre_cap"], 0)
            
            # Step 6: Convert DOI delta to EOQ delta and add to EOQ_final
            df["EOQ_final"] += df["doi_delta"] * df["daily_demand"]
            
            # Step 7: Recalculate final DOI after bump
            df["DOI_final"] = df["EOQ_final"] / df["daily_demand"]
    
            if 'demand_std_dev' in df.columns:
                df['safety_stock'] = safety_factor * df['demand_std_dev'] * np.sqrt(default_lead_time)
            else:
                df['safety_stock'] = 0
    
            df['ROP'] = df['daily_demand'] * default_lead_time + df['safety_stock']
            df['ROP'] = df['ROP'].round(2)
            df['safety_stock'] = df['safety_stock'].round(2)
            df['warning'] = np.where(df['opt_freq'] > 12, '⚠️ Over weekly inbound', '')
            df["DOI_final2"] = (df["EOQ_final"]+df['safety_stock']) / df["daily_demand"]
            df = df.dropna()
    
            st.success("✅ EOQ Calculated")
            st.subheader("Ideal DOI Step 1")
            st.dataframe(df[['product_id', 'location_id', 'EOQ_final', 'optimal_order_freq', 'DOI_final']])
    
            st.subheader("Ideal DOI Step 2")
            st.dataframe(df[['product_id', 'location_id', 'EOQ_final', 'safety_stock', 'DOI_final2']])
    
            uploaded_mov = st.file_uploader("🏷️ Upload MOV CSV (by primary_vendor_name)", type=["csv"])
            
            if uploaded_mov:
                try:
                    # Read and clean MOV CSV
                    df_mov = pd.read_csv(uploaded_mov)
                    df_mov['primary_vendor_name'] = df_mov['primary_vendor_name'].astype(str).str.strip()
                    df_mov['location_id'] = df_mov['location_id'].astype(str).str.strip()
                    df_mov['MOV'] = pd.to_numeric(df_mov['MOV'], errors='coerce')
                    #st.dataframe(df_mov)
                    # Clean df
                    df['primary_vendor_name'] = df['primary_vendor_name'].astype(str).str.strip()
                    df['location_id'] = df['location_id'].astype(str).str.strip()
            
                    # Compute value_total
                    df['value_total'] = (df['EOQ_final'] + df['safety_stock']) * df['cogs']
            
                    # Group by vendor & location
                    vendor_totals = df.groupby(['primary_vendor_name', 'location_id'])['value_total'].sum().reset_index()
            
                    # Merge MOV info
                    vendor_totals = pd.merge(vendor_totals, df_mov, on=['primary_vendor_name', 'location_id'], how='left')
            
                    # Calculate shortfall %
                    vendor_totals['shortfall_ratio'] = np.where(
                        (vendor_totals['value_total'] < vendor_totals['MOV']) & (vendor_totals['value_total'] > 0),
                        (vendor_totals['MOV'] - vendor_totals['value_total']) / vendor_totals['value_total'],
                        0
                    )
            
                    vendor_totals['remark'] = np.where(vendor_totals['shortfall_ratio'] > 0, '⚠️ Below MOV', '✅ Safe')
    
            
                    # Display vendor totals
                    st.subheader("📊 Vendor Totals vs MOV")
                    st.dataframe(vendor_totals)
            
                    df = pd.merge(
                        df,
                        vendor_totals[['primary_vendor_name', 'location_id', 'shortfall_ratio', 'remark']],
                        on=['primary_vendor_name', 'location_id'],
                        how='left'
                    )
            
                    # Apply adjustment
                    df['add_qty'] = (df['EOQ_final'] + df['safety_stock']) * df['shortfall_ratio']
                    df['EOQ_adjusted'] = df['EOQ_final'] + df['safety_stock'] + df['add_qty']
            
                    # Final DOI
                    df['DOI_final3'] = df['EOQ_adjusted'] / df['daily_demand']
                    df['DOI_final3'] = df['DOI_final3'].round(2)
                    df['add_qty'] = df['add_qty'].fillna(0).round(2)
                    df['shortfall_ratio'] = df['shortfall_ratio'].fillna(0).round(2)
            
                    # Display results
                    st.subheader("Ideal DOI Step 3")
                    st.dataframe(df[['product_id', 'location_id', 'primary_vendor_name', 'EOQ_adjusted', 'remark', 'add_qty', 'DOI_final3']])
            
                except Exception as e:
                    st.error(f"❌ Error processing MOV CSV: {e}")
    
            # Download EOQ results
            st.download_button("📥 Download EOQ Results", df.to_csv(index=False), file_name="eoq_results.csv")
    
                # --- Additional: Upload Pcs per Carton & COGS ---
            uploaded_cogs = st.file_uploader("📦 Upload Pcs per Carton & COGS CSV", type=["csv"])
        
            if uploaded_cogs:
                df_cogs = pd.read_csv(uploaded_cogs)
                df_cogs['product_id'] = df_cogs['product_id'].apply(clean_id)
        
                #st.write("COGS File:")
                #st.dataframe(df_cogs.head())
        
                # Merge with main dataframe
                df = pd.merge(df, df_cogs[['product_id', 'pcs_per_carton', 'cogs']], on=['product_id','cogs'], how='left')
        
                # Round EOQ up to nearest carton size
                df['EOQ Vendor Constraint'] = df['EOQ_adjusted']
                df['EOQ_rounded'] = np.ceil(df['EOQ Vendor Constraint'] / df['pcs_per_carton']) * df['pcs_per_carton']
        
                st.subheader("🎚️ Adjust COGS and see Impact")
                multiplier = st.slider("EOQ if COGS changes", min_value=0.95, max_value=1.1, value=1.0, step=0.05)
        
                def adjust_cogs(row):
                    if pd.isna(row['cogs']) or row['EOQ_rounded'] == 0:
                        return row['cogs']
                        
                    # Calculate adjusted EOQ and ratio
                    eoq_adj = row['EOQ Vendor Constraint'] * multiplier
                    increase_ratio = (eoq_adj - row['EOQ Vendor Constraint']) / row['EOQ Vendor Constraint']
                        
                    # Adjust COGS based on ratio (allows increase if EOQ decreases)
                    adjusted = row['cogs'] * (1 - increase_ratio)
                        
                    return round(adjusted, 2)
                    
                # Apply the function
                df['EOQ_adj'] = df['EOQ Vendor Constraint'] * multiplier
                df['cogs_adj'] = df.apply(adjust_cogs, axis=1)
                df['EOQ_rounded_multiplier'] = np.ceil(df['EOQ_adj'] / df['pcs_per_carton']) * df['pcs_per_carton']
                df['eoq_needed'] = (df['EOQ_final'] + df['safety_stock'] - df['original_rl_qty']).clip(lower=0)
                df['eoq_gap_vs_rl'] = df['eoq_needed'] - df['original_rl_qty']
                df['gap_doi'] = df['eoq_gap_vs_rl']/df['avg_sales_final']
                st.success("EOQ Multiplier & COGS Adjusted")
                st.dataframe(df[['product_id', 'location_id', 'EOQ Vendor Constraint', 'EOQ_adj', 'EOQ_rounded_multiplier', 'cogs', 'cogs_adj']])
        
                # Download adjusted results
                st.download_button("📥 Download Adjusted EOQ & COGS", df.to_csv(index=False), file_name="eoq_cogs_adjusted.csv")
        
            else:
                st.info("Upload Pcs per Carton & COGS CSV to continue.")
    
        except Exception as e:
            st.error(f"❌ Error processing files: {e}")
    
    else:
        st.info("Upload both Demand & Holding Cost CSV files to proceed.")

with tab2:
    st.title("📦 RL Qty vs EOQ Diagnostic Matrix")
    st.markdown("""
                ### 📌 How to Use:
                - Identify mismatches that can lead to overstock, batching inefficiencies, or cost assumptions that need review.
                - EOQ is used as a cost-efficiency reference — to set minimum order quantities (flooring) or bundle RL orders more efficiently.
                EXCLUDE RL QTY 0
                """)
    st.markdown("""
    
    """)

    uploaded_file = st.file_uploader("Upload your RL + EOQ dataset (CSV)", type=["csv"], key="rl_eoq")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        

        required_cols = ['product_id', 'location_id', 'original_rl_qty', 'EOQ_rounded']
        if not all(col in df.columns for col in required_cols):
            st.error(f"Missing required columns. Make sure your file includes: {required_cols}")
        else:
            st.success("✅ File uploaded and columns validated.")

            df = df[df['original_rl_qty'] != 0]
            df['rl_qty_vs_eoq_ratio'] = df['EOQ_rounded'] / (df['original_rl_qty'] + 1e-6)
            df['flag_rl_high'] = df['original_rl_qty'] > 1.5 * df['EOQ_rounded']
            df['flag_eoq_high'] = df['EOQ_rounded'] > 1.5 * df['original_rl_qty']

            def classify_rl_eoq(row):
                if not row['flag_rl_high'] and not row['flag_eoq_high']:
                    return "Normal / Normal"
                elif not row['flag_rl_high'] and row['flag_eoq_high']:
                    return "Small / Large"
                elif row['flag_rl_high'] and not row['flag_eoq_high']:
                    return "Large / Small"
                else:
                    return "Large / Large"

            df['rl_eoq_diagnosis'] = df.apply(classify_rl_eoq, axis=1)

            def generate_diagnosis_msg(code):
                if code == "Normal / Normal":
                    return "✔ Balanced: RL Qty and EOQ are aligned."
                elif code == "Small / Large":
                    return "⚠️ EOQ suggests batching. Group RL or reduce order freq."
                elif code == "Large / Small":
                    return "🚨 RL too large: Risk of overstock. Review forecast or increase order freq."
                elif code == "Large / Large":
                    return "⚠️ Both values large: Check vendor constraints or cost setup."
                else:
                    return "❓ Unknown condition."

            df['diagnosis'] = df['rl_eoq_diagnosis'].apply(generate_diagnosis_msg)

            st.subheader("Regular RL vs EOQ Qty Summary")
            summary_counts = df['rl_eoq_diagnosis'].value_counts().reset_index()
            summary_counts.columns = ['RL/EOQ Diagnosis', 'Product Count']
            st.dataframe(summary_counts, use_container_width=True)

            st.subheader("What It Means & What We Can Do")
            diagnosis_table = pd.DataFrame([
                {
                    "RL Qty": "Normal",
                    "EOQ": "Normal",
                    "What It Means": "Everything fine",
                    "What We Can Do": "Use EOQ as check"
                },
                {
                    "RL Qty": "Small",
                    "EOQ": "Large",
                    "What It Means": "EOQ suggests batching / low holding cost",
                    "What We Can Do": "Batch RL into EOQ cycles if possible"
                },
                {
                    "RL Qty": "Large",
                    "EOQ": "Small",
                    "What It Means": "High risk of overstock (low demand + large RL)",
                    "What We Can Do": "Cap RL by shelf life / DOI / inv. space"
                },
                {
                    "RL Qty": "Large",
                    "EOQ": "Large",
                    "What It Means": "Potential big inefficiency",
                    "What We Can Do": "Revisit cost & vendor constraints"
                }
            ])
            st.dataframe(diagnosis_table, use_container_width=True)

            st.subheader("Product-Level Diagnostics")
            st.dataframe(df[['product_id', 'location_id', 'original_rl_qty', 'EOQ_rounded', 'rl_eoq_diagnosis', 'diagnosis']], use_container_width=True)

            st.download_button("📥 Download Diagnosed CSV", data=df.to_csv(index=False), file_name="diagnosed_rl_vs_eoq.csv")

    else:
        st.info("👈 Upload a CSV file to begin.")
