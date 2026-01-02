import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64
import uuid

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" # 🚨 KEEP YOUR URL HERE

# --- 2. CSS STYLING ---
ST_STYLE = """
<style>
    /* Green Tags for Multiselect */
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #e8f5e9 !important; border: 1px solid #4CAF50 !important;
    }
    .stMultiSelect span[data-baseweb="tag"] span {
        color: #1b5e20 !important;
    }
    /* Better spacing for the input rows */
    .input-row {
        padding: 10px 0;
        border-bottom: 1px solid #f0f2f6;
    }
</style>
"""

QUOTE_CSS = """
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; background-color: #fff; color: #333; }
    .container { max-width: 950px; margin: 0 auto; }
    
    .header { text-align: center; border-bottom: 3px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }
    .header h1 { margin: 0; color: #2E7D32; font-size: 28px; }
    .meta { font-size: 14px; color: #666; margin-top: 5px; }
    
    .client-grid { display: flex; gap: 15px; background: #f1f8e9; padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #c5e1a5; }
    .client-item { flex: 1; }
    .label { font-size: 11px; font-weight: bold; color: #558b2f; text-transform: uppercase; margin-bottom: 4px; }
    .value { font-size: 15px; font-weight: 600; color: #000; }

    .plans-container { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 40px; }
    .plan-card { 
        flex: 1; min-width: 250px;
        border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); background: #fff;
    }
    .plan-name { font-size: 18px; font-weight: bold; color: #1565C0; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 10px;}
    .premium { font-size: 18px; font-weight: bold; color: #D32F2F; margin-bottom: 8px; white-space: pre-wrap; line-height: 1.4; }
    .notes { font-size: 14px; color: #555; background: #fffbe6; padding: 12px; border-radius: 4px; white-space: pre-wrap; line-height: 1.5; }

    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
    th { background-color: #e8f5e9; color: #2e7d32; text-align: left; padding: 10px; border: 1px solid #c8e6c9; }
    td { padding: 10px; border: 1px solid #eee; vertical-align: top; line-height: 1.5; }
    
    @media print {
        body { padding: 0; }
        .no-print { display: none; }
        .plan-card { break-inside: avoid; border: 1px solid #999; }
    }
</style>
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
def load_master_data():
    client = get_gspread_client()
    if not client: return None, None
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_drop = sheet.worksheet("Dropdown_Masters")
        raw_drop = ws_drop.get_all_values()
        df_drop = pd.DataFrame(raw_drop[1:], columns=raw_drop[0]) if len(raw_drop) > 1 else pd.DataFrame()
        
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

def log_quote_to_sheet(quote_data):
    client = get_gspread_client()
    if not client: return False
    try:
        sheet = client.open_by_url(SHEET_URL)
        try:
            ws = sheet.worksheet("Generated_Quotes")
        except:
            ws = sheet.add_worksheet(title="Generated_Quotes", rows=1000, cols=10)
            ws.append_row(["Quote ID", "Date", "RM", "Client Name", "City", "Type", "CRM Link", "Plans JSON"])
            
        ws.append_row([
            quote_data['quote_id'],
            quote_data['date'],
            quote_data['rm'],
            quote_data['client'],
            quote_data['city'],
            quote_data['type'],
            quote_data['crm_link'],
            str(quote_data['plans']) 
        ])
        return True
    except Exception as e:
        st.error(f"❌ Failed to Log Quote: {e}")
        return False

def create_download_link(html_string, link_text="📄 OPEN QUOTE IN NEW TAB"):
    b64 = base64.b64encode(html_string.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" target="_blank" style="text-decoration:none; background-color:#2E7D32; color:white; padding:12px 25px; border-radius:5px; font-weight:bold; font-size:16px; display:inline-block;">{link_text}</a>'
    return href

# --- 4. MAIN APP ---
def main():
    st.set_page_config(page_title="Quote Generator", page_icon="📝", layout="wide")
    st.markdown(ST_STYLE, unsafe_allow_html=True)
    st.title("📝 Health Insurance Quote Generator")

    if "YOUR_FULL_URL_HERE" in SHEET_URL:
        st.warning("⚠️ Please update `SHEET_URL` in code.")
        return

    with st.spinner("Syncing Master Data..."):
        df_masters, df_plans = load_master_data()

    if df_masters is not None and not df_plans.empty:
        
        # --- 1. CLIENT DETAILS ---
        with st.container():
            st.subheader("1. Client Details")
            c1, c2, c3, c4 = st.columns(4)
            rm_list = [x for x in df_masters['RM Names'].unique() if x]
            sel_rm = c1.selectbox("RM Name", rm_list)
            client_name = c2.text_input("Client Name")
            city = c3.text_input("City")
            pol_type = c4.selectbox("Policy Type", ["Fresh", "Port"])
            crm_link = st.text_input("CRM Lead URL (Optional)", placeholder="Paste CRM link here...")

        st.divider()

        # --- 2. PLAN SELECTION ---
        st.subheader("2. Select Plans")
        all_cols = list(df_plans.columns)
        
        if len(all_cols) > 2:
            plan_opts = all_cols[2:]
            sel_plans = st.multiselect("Compare Plans:", options=plan_opts)
            
            if sel_plans:
                st.divider()
                
                # --- 3. PREMIUMS & NOTES (MULTILINE TEXT BOXES) ---
                st.subheader("3. Premiums & Custom Notes")
                st.info("💡 Tip: You can drag the bottom-right corner of these boxes to expand them.")
                
                # Dictionary to store user inputs
                user_inputs = {}

                # Loop through selected plans to create dedicated Input Rows
                for plan in sel_plans:
                    st.markdown(f"**{plan}**") # Plan Title
                    c_prem, c_note = st.columns([1, 2]) # Split: 1 part Premium, 2 parts Note
                    
                    with c_prem:
                        # Premium Text Area
                        user_inputs[f"{plan}_prem"] = st.text_area(
                            "Premium Details", 
                            placeholder="e.g. ₹15,000\n+ GST", 
                            key=f"prem_{plan}", 
                            height=100
                        )
                    
                    with c_note:
                        # Notes Text Area
                        user_inputs[f"{plan}_note"] = st.text_area(
                            "Key Benefits / Notes", 
                            placeholder="e.g. - No Room Rent Limit\n- OPD Cover included", 
                            key=f"note_{plan}", 
                            height=100
                        )
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.3;'>", unsafe_allow_html=True)

                # --- 4. FEATURE TABLE (AUTO) ---
                st.subheader("4. Feature Preview")
                cols = [all_cols[1]] + sel_plans
                comp_df = df_plans[cols].copy()
                comp_df.rename(columns={all_cols[1]: "Feature"}, inplace=True)
                st.dataframe(comp_df, hide_index=True, use_container_width=True, height=400)

                # --- 5. GENERATE ACTIONS ---
                st.divider()
                if st.button("🚀 Generate Quote & Log", type="primary"):
                    
                    if not client_name:
                        st.error("Please enter a Client Name first.")
                    else:
                        # A. Generate ID
                        timestamp = datetime.datetime.now().strftime("%Y%m%d")
                        short_uid = str(uuid.uuid4())[:4].upper()
                        quote_id = f"Q-{timestamp}-{short_uid}"
                        today_str = datetime.date.today().strftime("%d-%b-%Y")
                        
                        # B. Collect Data from Text Areas
                        final_plans = []
                        for plan in sel_plans:
                            final_plans.append({
                                "Plan Name": plan,
                                "Premium": user_inputs[f"{plan}_prem"],
                                "Notes": user_inputs[f"{plan}_note"]
                            })
                        
                        log_payload = {
                            "quote_id": quote_id,
                            "date": today_str,
                            "rm": sel_rm,
                            "client": client_name,
                            "city": city,
                            "type": pol_type,
                            "crm_link": crm_link,
                            "plans": final_plans
                        }
                        
                        # C. Log to Sheet
                        with st.spinner("Logging to Database..."):
                            success = log_quote_to_sheet(log_payload)
                        
                        if success:
                            # D. Generate HTML
                            plans_html = ""
                            for row in final_plans:
                                # Convert newlines to HTML breaks
                                p_prem = str(row['Premium']).replace('\n', '<br>')
                                p_note = str(row['Notes']).replace('\n', '<br>')
                                
                                plans_html += f"""
                                <div class="plan-card">
                                    <div class="plan-name">{row['Plan Name']}</div>
                                    <div class="premium">{p_prem}</div>
                                    <div class="notes">{p_note}</div>
                                </div>
                                """

                            table_html = comp_df.to_html(index=False, border=0, classes="compare-table")
                            table_html = table_html.replace("\\n", "<br>").replace("\n", "<br>")

                            full_html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <title>Quote {quote_id} - {client_name}</title>
                                {QUOTE_CSS}
                            </head>
                            <body>
                                <div class="container">
                                    <div class="header">
                                        <h1>Health Insurance Proposal</h1>
                                        <div class="meta">Quote ID: {quote_id} | Date: {today_str}</div>
                                    </div>
                                    
                                    <div class="client-grid">
                                        <div class="client-item"><div class="label">RM Name</div><div class="value">{sel_rm}</div></div>
                                        <div class="client-item"><div class="label">Client</div><div class="value">{client_name}</div></div>
                                        <div class="client-item"><div class="label">City</div><div class="value">{city}</div></div>
                                        <div class="client-item"><div class="label">Type</div><div class="value">{pol_type}</div></div>
                                    </div>
                                    
                                    <h3>Recommended Options</h3>
                                    <div class="plans-container">{plans_html}</div>
                                    
                                    <h3>Feature Comparison</h3>
                                    {table_html}
                                    
                                    <div style="text-align:center; margin-top:40px; border-top:1px solid #eee; padding-top:20px;" class="no-print">
                                        <button onclick="window.print()" style="padding:10px 20px; cursor:pointer; background:#4CAF50; color:white; border:none; border-radius:4px; font-size:16px;">🖨️ Save as PDF</button>
                                    </div>
                                </div>
                            </body>
                            </html>
                            """
                            
                            st.success(f"✅ Quote **{quote_id}** Created & Logged Successfully!")
                            st.markdown(create_download_link(full_html), unsafe_allow_html=True)
                        else:
                            st.error("❌ Failed to log quote. Check permissions.")
            else:
                st.info("👈 Select plans to proceed.")
    else:
        st.error("❌ Data load failed.")

if __name__ == "__main__":
    main()
