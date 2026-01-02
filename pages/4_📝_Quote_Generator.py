import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" # 🚨 KEEP YOUR URL HERE
APP_BASE_URL = "https://moneyplustools.streamlit.app/" # 🚨 REPLACE with your actual deployed App URL

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
    /* Force Primary Button to be Green */
    div.stButton > button[kind="primary"] {
        background-color: #4CAF50 !important;
        border-color: #4CAF50 !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #45a049 !important;
        border-color: #45a049 !important;
    }
    .input-row { padding: 10px 0; border-bottom: 1px solid #f0f2f6; }
</style>
"""

# HTML Template for the Quote View
QUOTE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Quote {quote_id}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; padding: 40px; background-color: #fff; color: #333; }}
        .container {{ max-width: 950px; margin: 0 auto; }}
        .header {{ text-align: center; border-bottom: 3px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; color: #2E7D32; font-size: 28px; }}
        .meta {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .client-grid {{ display: flex; gap: 15px; background: #f1f8e9; padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #c5e1a5; }}
        .client-item {{ flex: 1; }}
        .label {{ font-size: 11px; font-weight: bold; color: #558b2f; text-transform: uppercase; margin-bottom: 4px; }}
        .value {{ font-size: 15px; font-weight: 600; color: #000; }}
        .plans-container {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 40px; }}
        .plan-card {{ flex: 1; min-width: 250px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); background: #fff; }}
        .plan-name {{ font-size: 18px; font-weight: bold; color: #1565C0; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .premium {{ font-size: 18px; font-weight: bold; color: #D32F2F; margin-bottom: 8px; white-space: pre-wrap; }}
        .notes {{ font-size: 14px; color: #555; background: #fffbe6; padding: 12px; border-radius: 4px; white-space: pre-wrap; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th {{ background-color: #e8f5e9; color: #2e7d32; text-align: left; padding: 10px; border: 1px solid #c8e6c9; }}
        td {{ padding: 10px; border: 1px solid #eee; vertical-align: top; }}
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
        <div style="text-align:center; margin-top:40px; padding-top:20px;" class="no-print">
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

def get_sheet_and_rows():
    client = get_gspread_client()
    if not client: return None, 0
    try:
        sheet = client.open_by_url(SHEET_URL)
        try:
            ws = sheet.worksheet("Generated_Quotes")
        except:
            ws = sheet.add_worksheet(title="Generated_Quotes", rows=1000, cols=25)
            # Create Headers if new
            headers = ["Quote_ID", "Date", "RM_Name", "Client_Name", "City", "Policy_Type", "CRM_Link"]
            for i in range(1, 6): # Add Plan 1 to 5
                headers.extend([f"Plan_{i}", f"Prem_{i}", f"Note_{i}"])
            ws.append_row(headers)
        
        all_values = ws.get_all_values()
        row_count = len(all_values)
        return ws, row_count, all_values
    except Exception as e:
        st.error(f"❌ Sheet Error: {e}")
        return None, 0, []

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

def generate_custom_id(rm_name, row_count):
    # Initials
    initials = "".join([x[0].upper() for x in rm_name.split() if x])
    # Date
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    # Row Num (Unique)
    unique_no = str(row_count + 1) # +1 because row_count includes header, next row is count+1
    return f"{initials}{date_str}{unique_no}"

def log_quote_to_sheet(ws, quote_data):
    try:
        # Base Data
        row = [
            quote_data['quote_id'],
            quote_data['date'],
            quote_data['rm'],
            quote_data['client'],
            quote_data['city'],
            quote_data['type'],
            quote_data['crm_link']
        ]
        
        # Flatten Plans (Max 5)
        plans = quote_data['plans']
        for i in range(5):
            if i < len(plans):
                p = plans[i]
                row.extend([p['Plan Name'], p['Premium'], p['Notes']])
            else:
                row.extend(["", "", ""]) # Empty filler
        
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ Log Error: {e}")
        return False

# --- 4. VIEWER MODE ---
def render_quote_viewer(quote_id):
    st.set_page_config(page_title=f"Quote {quote_id}", layout="centered")
    
    with st.spinner("Loading Quote..."):
        ws, _, all_values = get_sheet_and_rows()
        
        # Find Quote Row
        if not ws: return
        
        headers = all_values[0]
        try:
            q_idx = headers.index("Quote_ID")
        except:
            st.error("Invalid Sheet Format: Quote_ID column missing.")
            return

        target_row = None
        for row in all_values:
            if len(row) > q_idx and row[q_idx] == quote_id:
                target_row = row
                break
        
        if not target_row:
            st.error("Quote not found.")
            return

        # Map Data
        # Safe get helper
        def get_col(name):
            try:
                idx = headers.index(name)
                return target_row[idx] if idx < len(target_row) else ""
            except: return ""

        # Reconstruct Plans
        plans_html = ""
        active_plans = []
        for i in range(1, 6):
            p_name = get_col(f"Plan_{i}")
            if p_name:
                p_prem = get_col(f"Prem_{i}").replace('\n', '<br>')
                p_note = get_col(f"Note_{i}").replace('\n', '<br>')
                active_plans.append(p_name)
                plans_html += f"""
                <div class="plan-card">
                    <div class="plan-name">{p_name}</div>
                    <div class="premium">{p_prem}</div>
                    <div class="notes">{p_note}</div>
                </div>
                """

        # Feature Table (Need to fetch Master Data again to reconstruct)
        _, df_plans = load_master_data()
        table_html = ""
        if df_plans is not None and not df_plans.empty and active_plans:
            all_cols = list(df_plans.columns)
            # Find selected plan columns
            valid_plans = [p for p in active_plans if p in df_plans.columns]
            if valid_plans:
                cols = [all_cols[1]] + valid_plans
                comp_df = df_plans[cols].copy()
                comp_df.rename(columns={all_cols[1]: "Feature"}, inplace=True)
                table_html = comp_df.to_html(index=False, border=0, classes="compare-table")
                table_html = table_html.replace("\\n", "<br>").replace("\n", "<br>")

        # Render HTML
        full_html = QUOTE_HTML_TEMPLATE.format(
            quote_id=quote_id,
            date=get_col("Date"),
            rm=get_col("RM_Name"),
            client=get_col("Client_Name"),
            city=get_col("City"),
            type=get_col("Policy_Type"),
            plans_html=plans_html,
            table_html=table_html
        )
        
        st.components.v1.html(full_html, height=1200, scrolling=True)
        st.button("⬅️ Create New Quote", on_click=lambda: st.query_params.clear())


# --- 5. MAIN GENERATOR ---
def main():
    # Check for Quote ID in URL
    if "quote_id" in st.query_params:
        render_quote_viewer(st.query_params["quote_id"])
        return

    st.set_page_config(page_title="Quote Generator", page_icon="📝", layout="wide")
    st.markdown(ST_STYLE, unsafe_allow_html=True)
    st.title("📝 Health Insurance Quote Generator")

    if "YOUR_FULL_URL_HERE" in SHEET_URL:
        st.warning("⚠️ Please update `SHEET_URL` in code.")
        return

    with st.spinner("Syncing Master Data..."):
        df_masters, df_plans = load_master_data()

    if df_masters is not None and not df_plans.empty:
        
        # --- INPUTS ---
        with st.container():
            st.subheader("1. Client Details")
            c1, c2, c3, c4 = st.columns(4)
            rm_list = [x for x in df_masters['RM Names'].unique() if x]
            sel_rm = c1.selectbox("RM Name", rm_list)
            client_name = c2.text_input("Client Name")
            city = c3.text_input("City")
            pol_type = c4.selectbox("Policy Type", ["Fresh", "Port"])
            crm_link = st.text_input("CRM Lead URL", placeholder="Optional")

        st.divider()

        # --- PLANS ---
        st.subheader("2. Select Plans")
        all_cols = list(df_plans.columns)
        if len(all_cols) > 2:
            plan_opts = all_cols[2:]
            sel_plans = st.multiselect("Compare Plans:", options=plan_opts)
            
            if sel_plans:
                st.divider()
                st.subheader("3. Premiums & Notes")
                
                user_inputs = {}
                for plan in sel_plans:
                    st.markdown(f"**{plan}**")
                    c_prem, c_note = st.columns([1, 2])
                    with c_prem:
                        user_inputs[f"{plan}_prem"] = st.text_area("Premium", placeholder="e.g. ₹15k + GST", key=f"p_{plan}", height=100)
                    with c_note:
                        user_inputs[f"{plan}_note"] = st.text_area("Notes", placeholder="Benefits...", key=f"n_{plan}", height=100)
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.3;'>", unsafe_allow_html=True)

                st.subheader("4. Preview")
                cols = [all_cols[1]] + sel_plans
                comp_df = df_plans[cols].copy()
                comp_df.rename(columns={all_cols[1]: "Feature"}, inplace=True)
                st.dataframe(comp_df, hide_index=True, use_container_width=True, height=300)

                st.divider()
                # GREEN BUTTON (via CSS type="primary")
                if st.button("🚀 Generate Quote Link", type="primary"):
                    if not client_name:
                        st.error("Enter Client Name.")
                    else:
                        with st.spinner("Generating..."):
                            # 1. Get Sheet & Count
                            ws, row_count, _ = get_sheet_and_rows()
                            
                            # 2. Generate ID
                            quote_id = generate_custom_id(sel_rm, row_count)
                            today_str = datetime.date.today().strftime("%d-%b-%Y")
                            
                            # 3. Prepare Data
                            final_plans = []
                            for p in sel_plans:
                                final_plans.append({
                                    "Plan Name": p,
                                    "Premium": user_inputs[f"{p}_prem"],
                                    "Notes": user_inputs[f"{p}_note"]
                                })
                            
                            quote_data = {
                                "quote_id": quote_id,
                                "date": today_str,
                                "rm": sel_rm,
                                "client": client_name,
                                "city": city,
                                "type": pol_type,
                                "crm_link": crm_link,
                                "plans": final_plans
                            }
                            
                            # 4. Log
                            if log_quote_to_sheet(ws, quote_data):
                                # 5. Create Link
                                # We assume the user wants to open the APP with the ID
                                # Since we can't easily get the absolute URL in Streamlit Cloud,
                                # we ask user to set APP_BASE_URL or use a relative one (which might fail in new tab).
                                # Best effort: Use the APP_BASE_URL variable.
                                
                                target_url = f"{APP_BASE_URL}?quote_id={quote_id}"
                                st.success(f"✅ Quote **{quote_id}** Generated!")
                                st.markdown(f"""
                                <a href="{target_url}" target="_blank" style="text-decoration:none;">
                                    <div style="background-color:#4CAF50; color:white; padding:15px; border-radius:5px; text-align:center; font-weight:bold; font-size:18px;">
                                        🔗 OPEN QUOTE: {quote_id}
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)
                            else:
                                st.error("Failed to log quote.")

if __name__ == "__main__":
    main()
