import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1B7-y...YOUR_FULL_URL_HERE" # 🚨 KEEP YOUR SHEET URL HERE

# --- 2. HTML TEMPLATE (Clean & Printable) ---
QUOTE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Quote {quote_id}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; padding: 40px; background-color: #fff; color: #333; }}
        .container {{ max-width: 950px; margin: 0 auto; }}
        
        /* Header */
        .header {{ text-align: center; border-bottom: 3px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; color: #2E7D32; font-size: 28px; }}
        .meta {{ font-size: 14px; color: #666; margin-top: 5px; }}
        
        /* Client Grid */
        .client-grid {{ display: flex; gap: 15px; background: #f1f8e9; padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #c5e1a5; }}
        .client-item {{ flex: 1; }}
        .label {{ font-size: 11px; font-weight: bold; color: #558b2f; text-transform: uppercase; margin-bottom: 4px; }}
        .value {{ font-size: 15px; font-weight: 600; color: #000; }}
        
        /* Plan Cards */
        .plans-container {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 40px; }}
        .plan-card {{ flex: 1; min-width: 250px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); background: #fff; }}
        .plan-name {{ font-size: 18px; font-weight: bold; color: #1565C0; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .premium {{ font-size: 18px; font-weight: bold; color: #D32F2F; margin-bottom: 8px; white-space: pre-wrap; }}
        .notes {{ font-size: 14px; color: #555; background: #fffbe6; padding: 12px; border-radius: 4px; white-space: pre-wrap; }}
        
        /* Comparison Table */
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th {{ background-color: #e8f5e9; color: #2e7d32; text-align: left; padding: 10px; border: 1px solid #c8e6c9; }}
        td {{ padding: 10px; border: 1px solid #eee; vertical-align: top; }}
        
        /* Print Button Hiding */
        @media print {{ .no-print {{ display: none; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Health Insurance Proposal</h1>
            <div class="meta">Quote ID: {quote_id} | Date: {date}</div>
        </div>
        
        <div class="client-grid">
            <div class="client-item"><div class="label">RM Name</div><div class="value">{rm}</div></div>
            <div class="client-item"><div class="label">Client</div><div class="value">{client}</div></div>
            <div class="client-item"><div class="label">City</div><div class="value">{city}</div></div>
            <div class="client-item"><div class="label">Type</div><div class="value">{type}</div></div>
        </div>
        
        <h3>Recommended Options</h3>
        <div class="plans-container">{plans_html}</div>
        
        <h3>Feature Comparison</h3>
        {table_html}
        
        <div style="text-align:center; margin-top:40px; border-top:1px solid #eee; padding-top:20px;" class="no-print">
            <button onclick="window.print()" style="padding:10px 20px; background:#4CAF50; color:white; border:none; border-radius:4px; font-size:16px; cursor:pointer;">🖨️ Save as PDF</button>
        </div>
    </div>
</body>
</html>
"""

# --- 3. GOOGLE SHEETS HELPERS ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Auth Error: {e}")
        return None

@st.cache_data(ttl=600)
def load_master_plans():
    """Loads Plans Master to reconstruct the comparison table."""
    client = get_gspread_client()
    if not client: return None
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_plans = sheet.worksheet("Plans_Master")
        raw_plans = ws_plans.get_all_values()
        if len(raw_plans) > 3:
            # Headers are in Row 3 (index 2)
            df_plans = pd.DataFrame(raw_plans[3:], columns=raw_plans[2])
            return df_plans
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def get_quote_data(quote_id):
    """Fetches the specific quote row from 'Generated_Quotes'."""
    client = get_gspread_client()
    if not client: return None
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws = sheet.worksheet("Generated_Quotes")
        
        # Get all data to find the row (Using get_all_records handles headers automatically)
        records = ws.get_all_records() 
        # Note: get_all_records uses Row 1 as keys. Ensure Row 1 has unique headers like 'Quote_ID', 'Plan_1', etc.
        
        for row in records:
            if str(row.get("Quote_ID")) == str(quote_id):
                return row
        return None
    except Exception as e:
        st.error(f"❌ Error fetching quote: {e}")
        return None

# --- 4. MAIN VIEWER APP ---
def main():
    st.set_page_config(page_title="View Quote", layout="centered")

    # 1. Get Quote ID from URL
    if "quote_id" not in st.query_params:
        st.error("⚠️ No Quote ID provided.")
        st.info("Use the Quote Generator to create a link.")
        return

    quote_id = st.query_params["quote_id"]

    # 2. Fetch Data
    with st.spinner(f"Loading Quote {quote_id}..."):
        quote_data = get_quote_data(quote_id)

    if quote_data:
        # --- 3. RECONSTRUCT HTML ---
        
        # A. Plans Logic (Flattened Columns -> HTML Cards)
        plans_html = ""
        active_plans = [] # To store plan names for the table comparison
        
        # Loop through Plan_1 to Plan_5
        for i in range(1, 6):
            p_name = quote_data.get(f"Plan_{i}")
            if p_name:
                p_prem = str(quote_data.get(f"Prem_{i}", "")).replace('\n', '<br>')
                p_note = str(quote_data.get(f"Note_{i}", "")).replace('\n', '<br>')
                
                active_plans.append(p_name)
                
                plans_html += f"""
                <div class="plan-card">
                    <div class="plan-name">{p_name}</div>
                    <div class="premium">{p_prem}</div>
                    <div class="notes">{p_note}</div>
                </div>
                """

        # B. Comparison Table Logic
        table_html = ""
        df_plans = load_master_plans()
        
        if df_plans is not None and not df_plans.empty and active_plans:
            # 1. Get Features Column (Usually Col 1) and Selected Plans
            # Standard Plan Master: [Code, Feature Name, Plan A, Plan B...]
            all_cols = list(df_plans.columns)
            
            # Find columns that match our Active Plans
            valid_cols = [col for col in active_plans if col in df_plans.columns]
            
            if valid_cols:
                # Assuming 'Plan Name >>' or similar is the 2nd column (Index 1) for features
                # Use the column name from your dataframe. Usually Index 1.
                feature_col_name = all_cols[1] 
                
                cols_to_show = [feature_col_name] + valid_cols
                comp_df = df_plans[cols_to_show].copy()
                comp_df.rename(columns={feature_col_name: "Feature"}, inplace=True)
                
                # Convert to HTML
                table_html = comp_df.to_html(index=False, border=0, classes="compare-table")
                table_html = table_html.replace("\\n", "<br>").replace("\n", "<br>")

        # C. Render Full Page
        full_html = QUOTE_HTML_TEMPLATE.format(
            quote_id=quote_id,
            date=quote_data.get("Date", ""),
            rm=quote_data.get("RM_Name", ""),
            client=quote_data.get("Client_Name", ""),
            city=quote_data.get("City", ""),
            type=quote_data.get("Policy_Type", ""),
            plans_html=plans_html,
            table_html=table_html
        )
        
        st.components.v1.html(full_html, height=1200, scrolling=True)
        
    else:
        st.error("❌ Quote not found. It may have been deleted or the ID is incorrect.")

if __name__ == "__main__":
    main()
