import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" # 🚨 KEEP YOUR URL HERE

# --- 2. SHARED CSS (For the New Tab Quote) ---
# This CSS is injected into the generated HTML file, not the Streamlit app.
QUOTE_CSS = """
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; background-color: #fff; color: #333; }
    
    /* Responsive Container */
    .container { max-width: 900px; margin: 0 auto; }
    
    /* Header */
    .header { text-align: center; border-bottom: 3px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }
    .header h1 { margin: 0; color: #2E7D32; font-size: 28px; }
    .meta { font-size: 14px; color: #666; margin-top: 10px; }
    
    /* Client Info Grid */
    .client-grid { display: flex; gap: 20px; background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
    .client-item { flex: 1; }
    .label { font-size: 12px; font-weight: bold; color: #888; text-transform: uppercase; }
    .value { font-size: 16px; font-weight: 600; color: #000; }

    /* Plan Cards (Flexbox for responsiveness) */
    .plans-container { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 40px; }
    .plan-card { 
        flex: 1; 
        min-width: 250px;
        border: 1px solid #e0e0e0; 
        border-radius: 8px; 
        padding: 20px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        background: #fff;
    }
    .plan-name { font-size: 18px; font-weight: bold; color: #1565C0; margin-bottom: 10px; }
    .premium { font-size: 22px; font-weight: bold; color: #D32F2F; margin-bottom: 5px; }
    .notes { font-size: 13px; font-style: italic; color: #555; background: #fffbe6; padding: 8px; border-radius: 4px; }

    /* Comparison Table */
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th { background-color: #f0f2f6; text-align: left; padding: 12px; border: 1px solid #ddd; }
    td { padding: 12px; border: 1px solid #ddd; vertical-align: top; }
    
    /* Print Tweaks */
    @media print {
        body { padding: 0; }
        .container { max-width: 100%; }
        .plan-card { box-shadow: none; border: 1px solid #ccc; break-inside: avoid; }
        .no-print { display: none; } /* Class to hide buttons during print */
    }
</style>
"""

# --- 3. HELPERS ---
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
def load_master_data():
    client = get_gspread_client()
    if not client: return None, None
    try:
        sheet = client.open_by_url(SHEET_URL)
        # Dropdowns
        ws_drop = sheet.worksheet("Dropdown_Masters")
        raw_drop = ws_drop.get_all_values()
        df_drop = pd.DataFrame(raw_drop[1:], columns=raw_drop[0]) if len(raw_drop) > 1 else pd.DataFrame()
        # Plans
        ws_plans = sheet.worksheet("Plans_Master")
        raw_plans = ws_plans.get_all_values()
        if len(raw_plans) > 3:
            df_plans = pd.DataFrame(raw_plans[3:], columns=raw_plans[2])
        else:
            df_plans = pd.DataFrame() 
        return df_drop, df_plans
    except Exception as e:
        st.error(f"❌ Data Error: {e}")
        return None, None

def create_download_link(html_string, link_text="📄 Open Quote in New Tab"):
    """Generates a link to open HTML content in a new tab."""
    b64 = base64.b64encode(html_string.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" target="_blank" style="text-decoration:none; background-color:#4CAF50; color:white; padding:10px 20px; border-radius:5px; font-weight:bold;">{link_text}</a>'
    return href

# --- 4. MAIN APP ---
def main():
    st.set_page_config(page_title="Quote Generator", page_icon="📝", layout="wide")
    st.title("📝 Health Insurance Quote Generator")

    if "YOUR_FULL_URL_HERE" in SHEET_URL:
        st.warning("⚠️ Update `SHEET_URL` in code.")
        return

    with st.spinner("Syncing..."):
        df_masters, df_plans = load_master_data()

    if df_masters is not None and not df_plans.empty:
        
        # --- INPUTS ---
        with st.container():
            st.subheader("1. Client Details")
            c1, c2, c3, c4 = st.columns(4)
            
            rm_list = [x for x in df_masters['RM Names'].unique() if x]
            sel_rm = c1.selectbox("RM Name", rm_list)
            
            client_name = c2.text_input("Client Name")
            city = c3.text_input("City") # Added City
            
            pol_type = c4.selectbox("Policy Type", ["Fresh", "Port"]) # Added Fresh/Port

        st.divider()

        # --- PLANS ---
        st.subheader("2. Select Plans")
        all_cols = list(df_plans.columns)
        
        if len(all_cols) > 2:
            # Plan Selection
            plan_opts = all_cols[2:]
            sel_plans = st.multiselect("Compare Plans:", options=plan_opts)
            
            if sel_plans:
                st.divider()
                
                # --- PREMIUMS GRID ---
                st.subheader("3. Premiums & Notes")
                input_data = [{"Plan Name": p, "Premium (₹)": 0, "Notes": ""} for p in sel_plans]
                edited_df = st.data_editor(
                    input_data,
                    column_config={
                        "Plan Name": st.column_config.TextColumn(disabled=True),
                        "Premium (₹)": st.column_config.NumberColumn(format="₹%d", min_value=0),
                        "Notes": st.column_config.TextColumn(width="large")
                    },
                    use_container_width=True, hide_index=True
                )

                # --- FEATURE FILTER ---
                st.divider()
                st.subheader("4. Customize Features")
                
                # Prepare Comparison Data
                cols = [all_cols[1]] + sel_plans
                comp_df = df_plans[cols].copy()
                comp_df.rename(columns={all_cols[1]: "Feature"}, inplace=True)
                
                # Filter Logic
                all_features = comp_df['Feature'].unique().tolist()
                hidden_features = st.multiselect("Hide these rows:", options=all_features)
                
                if hidden_features:
                    comp_df = comp_df[~comp_df['Feature'].isin(hidden_features)]

                st.info(f"Showing {len(comp_df)} feature rows.")

                # --- GENERATE ---
                st.divider()
                if st.button("🚀 Generate Quote Link"):
                    
                    # 1. Build Client HTML
                    today = datetime.date.today().strftime("%d-%b-%Y")
                    
                    # 2. Build Plans HTML
                    plans_html = ""
                    final_plans = pd.DataFrame(edited_df).to_dict('records')
                    for row in final_plans:
                        plans_html += f"""
                        <div class="plan-card">
                            <div class="plan-name">{row['Plan Name']}</div>
                            <div class="premium">₹{row['Premium (₹)']:,}</div>
                            <div class="notes">{row['Notes']}</div>
                        </div>
                        """

                    # 3. Build Comparison Table HTML
                    # Convert DF to HTML with basic classes
                    table_html = comp_df.to_html(index=False, border=0, classes="compare-table")
                    # Fix line breaks
                    table_html = table_html.replace("\\n", "<br>").replace("\n", "<br>")

                    # 4. Assemble Full HTML
                    full_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Quote for {client_name}</title>
                        {QUOTE_CSS}
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>Health Insurance Proposal</h1>
                                <div class="meta">Date: {today} | Prepared by: {sel_rm}</div>
                            </div>
                            
                            <div class="client-grid">
                                <div class="client-item">
                                    <div class="label">Client Name</div>
                                    <div class="value">{client_name}</div>
                                </div>
                                <div class="client-item">
                                    <div class="label">City</div>
                                    <div class="value">{city}</div>
                                </div>
                                <div class="client-item">
                                    <div class="label">Policy Type</div>
                                    <div class="value">{pol_type}</div>
                                </div>
                            </div>
                            
                            <h3>Recommended Options</h3>
                            <div class="plans-container">
                                {plans_html}
                            </div>
                            
                            <h3>Feature Comparison</h3>
                            {table_html}
                            
                            <div style="text-align:center; margin-top:40px;" class="no-print">
                                <button onclick="window.print()" style="padding:10px 20px; font-size:16px; cursor:pointer;">🖨️ Save as PDF</button>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # 5. Display the Link
                    st.success("✅ Quote Ready!")
                    st.markdown(create_download_link(full_html), unsafe_allow_html=True)
            
            else:
                st.info("👈 Select plans to begin.")
    else:
        st.error("❌ Data load failed.")

if __name__ == "__main__":
    main()
