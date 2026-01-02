import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" # 🚨 KEEP YOUR SHEET URL HERE
APP_BASE_URL = "https://moneyplustools.streamlit.app" 

# --- 2. CSS FOR STREAMLIT GENERATOR (Backend) ---
ST_STYLE = """
<style>
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #e8f5e9 !important; border: 1px solid #4CAF50 !important;
    }
    .stMultiSelect span[data-baseweb="tag"] span {
        color: #1b5e20 !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #4CAF50 !important; border-color: #4CAF50 !important; color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #45a049 !important; border-color: #45a049 !important;
    }
    .input-row { padding: 10px 0; border-bottom: 1px solid #f0f2f6; }
</style>
"""

# --- 3. RICH HTML TEMPLATE (Frontend for Client) ---
# This is a full responsive web page design
QUOTE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proposal for {client}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #2E7D32;
            --bg-color: #f8f9fa;
            --card-bg: #ffffff;
            --text-main: #1f2937;
            --text-muted: #6b7280;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            margin: 0;
            padding: 0;
            color: var(--text-main);
            line-height: 1.5;
        }}

        /* HERO SECTION */
        .hero {{
            background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%);
            color: white;
            padding: 40px 20px 80px;
            text-align: center;
        }}
        .hero h1 {{ margin: 0; font-size: 28px; font-weight: 700; }}
        .hero p {{ margin: 10px 0 0; opacity: 0.9; font-size: 16px; }}
        .badge {{ 
            background: rgba(255,255,255,0.2); 
            padding: 4px 12px; 
            border-radius: 20px; 
            font-size: 12px; 
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        /* MAIN CONTAINER (Overlaps Hero) */
        .container {{
            max-width: 1000px;
            margin: -50px auto 40px;
            padding: 0 20px;
            position: relative;
            z-index: 10;
        }}

        /* CLIENT INFO CARD */
        .client-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
            border: 1px solid #eaeaea;
        }}
        .info-item .label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }}
        .info-item .value {{ font-size: 16px; font-weight: 700; color: var(--text-main); }}

        /* SECTION TITLES */
        .section-title {{
            text-align: center;
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 25px;
            color: var(--text-main);
            position: relative;
            display: inline-block;
            width: 100%;
        }}
        
        /* PLAN CARDS GRID */
        .plans-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 50px;
        }}
        
        .plan-card {{
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02), 0 10px 15px rgba(0,0,0,0.03);
            transition: transform 0.2s, box-shadow 0.2s;
            border: 1px solid #f0f0f0;
            display: flex;
            flex-direction: column;
        }}
        .plan-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 25px rgba(0,0,0,0.1);
            border-color: var(--primary);
        }}
        
        .card-header {{
            background: #f1f8e9;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .plan-name {{ font-size: 18px; font-weight: 700; color: #1b5e20; }}
        
        .card-body {{ padding: 25px; flex-grow: 1; }}
        
        .premium-box {{ 
            margin-bottom: 20px; 
            padding-bottom: 20px; 
            border-bottom: 1px dashed #e0e0e0; 
        }}
        .premium-label {{ font-size: 12px; color: var(--text-muted); font-weight: 600; }}
        .premium-value {{ font-size: 24px; font-weight: 800; color: #d32f2f; white-space: pre-wrap; }}
        
        .notes-box {{ font-size: 14px; color: #555; line-height: 1.6; white-space: pre-wrap; }}
        .notes-box ul {{ margin: 0; padding-left: 20px; }}

        /* COMPARISON TABLE */
        .table-wrapper {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            overflow-x: auto; /* Scroll on mobile */
            border: 1px solid #eaeaea;
        }}
        table {{ width: 100%; border-collapse: collapse; min-width: 600px; }}
        th {{ 
            background: #f8f9fa; 
            text-align: left; 
            padding: 15px 20px; 
            font-size: 13px; 
            color: var(--text-muted); 
            text-transform: uppercase;
            border-bottom: 2px solid #eaeaea;
        }}
        td {{ 
            padding: 15px 20px; 
            border-bottom: 1px solid #eaeaea; 
            font-size: 14px; 
            color: var(--text-main);
        }}
        tr:last-child td {{ border-bottom: none; }}
        
        /* FOOTER */
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: var(--text-muted);
            font-size: 14px;
        }}
        
        /* MOBILE TWEAKS */
        @media (max-width: 768px) {{
            .hero {{ padding-bottom: 60px; }}
            .container {{ margin-top: -40px; }}
            .client-card {{ grid-template-columns: 1fr 1fr; gap: 15px; }}
            .section-title {{ font-size: 20px; }}
        }}
    </style>
</head>
<body>

    <div class="hero">
        <span class="badge">Health Insurance Proposal</span>
        <h1 style="margin-top: 10px;">Quote for {client}</h1>
        <p>Prepared by {rm} on {date}</p>
    </div>

    <div class="container">
        
        <div class="client-card">
            <div class="info-item">
                <div class="label">Quote Reference</div>
                <div class="value">{quote_id}</div>
            </div>
            <div class="info-item">
                <div class="label">Client Name</div>
                <div class="value">{client}</div>
            </div>
            <div class="info-item">
                <div class="label">Location</div>
                <div class="value">{city}</div>
            </div>
            <div class="info-item">
                <div class="label">Policy Type</div>
                <div class="value">{type}</div>
            </div>
        </div>

        <div class="section-title">Recommended Plans</div>
        <div class="plans-grid">
            {plans_html}
        </div>

        <div class="section-title">Feature Comparison</div>
        <div class="table-wrapper">
            {table_html}
        </div>

        <div class="footer">
            <p>Need changes? Contact {rm} for assistance.</p>
        </div>

    </div>

</body>
</html>
"""

# --- 4. GOOGLE SHEETS HELPERS ---
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
            headers = ["Quote_ID", "Date", "RM_Name", "Client_Name", "City", "Policy_Type", "CRM_Link"]
            for i in range(1, 6): 
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
    initials = "".join([x[0].upper() for x in rm_name.split() if x])
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    unique_no = str(row_count + 1)
    return f"{initials}{date_str}{unique_no}"

def log_quote_to_sheet(ws, quote_data):
    try:
        row = [
            quote_data['quote_id'],
            quote_data['date'],
            quote_data['rm'],
            quote_data['client'],
            quote_data['city'],
            quote_data['type'],
            quote_data['crm_link']
        ]
        plans = quote_data['plans']
        for i in range(5):
            if i < len(plans):
                p = plans[i]
                row.extend([p['Plan Name'], p['Premium'], p['Notes']])
            else:
                row.extend(["", "", ""]) 
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ Log Error: {e}")
        return False

# --- 5. VIEWER MODE ---
def render_quote_viewer(quote_id):
    st.set_page_config(page_title=f"Quote {quote_id}", layout="centered", initial_sidebar_state="collapsed")
    
    with st.spinner("Fetching Proposal..."):
        ws, _, all_values = get_sheet_and_rows()
        if not ws or not all_values: return
        
        headers = all_values[0]
        try: q_idx = headers.index("Quote_ID")
        except: q_idx = 0 

        target_row = None
        for row in all_values:
            if len(row) > q_idx and str(row[q_idx]).strip() == str(quote_id).strip():
                target_row = row
                break
        
        if not target_row:
            st.error("Quote not found.")
            return

        def safe_get(idx): return target_row[idx] if idx < len(target_row) else ""

        # Map Basic Info
        # Assumes Header Order: Quote_ID(0), Date(1), RM(2), Client(3), City(4), Type(5), CRM(6)
        date_val = safe_get(1)
        rm_val = safe_get(2)
        client_val = safe_get(3)
        city_val = safe_get(4)
        type_val = safe_get(5)

        # Map Plans (Starting Index 7)
        plans_html = ""
        active_plans = []
        
        for i in range(5):
            base_idx = 7 + (i * 3)
            p_name = safe_get(base_idx)
            if p_name and p_name.strip():
                p_prem = safe_get(base_idx + 1).replace('\n', '<br>')
                p_note = safe_get(base_idx + 2).replace('\n', '<br>') # Keeps line breaks
                active_plans.append(p_name)
                
                plans_html += f"""
                <div class="plan-card">
                    <div class="card-header">
                        <div class="plan-name">{p_name}</div>
                    </div>
                    <div class="card-body">
                        <div class="premium-box">
                            <div class="premium-label">PREMIUM ESTIMATE</div>
                            <div class="premium-value">{p_prem}</div>
                        </div>
                        <div class="notes-box">
                            <strong>Key Highlights:</strong><br>
                            {p_note}
                        </div>
                    </div>
                </div>
                """

        # Map Table
        _, df_plans = load_master_data()
        table_html = ""
        if df_plans is not None and not df_plans.empty and active_plans:
            all_cols = list(df_plans.columns)
            valid_plans = [p for p in active_plans if p in df_plans.columns]
            if valid_plans:
                cols = [all_cols[1]] + valid_plans
                comp_df = df_plans[cols].copy()
                comp_df.rename(columns={all_cols[1]: "Feature"}, inplace=True)
                table_html = comp_df.to_html(index=False, border=0, classes="compare-table")
                table_html = table_html.replace("\\n", "<br>").replace("\n", "<br>")

        # Render Full Page
        full_html = QUOTE_HTML_TEMPLATE.format(
            quote_id=quote_id,
            date=date_val,
            rm=rm_val,
            client=client_val,
            city=city_val,
            type=type_val,
            plans_html=plans_html,
            table_html=table_html
        )
        
        st.components.v1.html(full_html, height=1200, scrolling=True)
        st.markdown(f'<div style="text-align:center; margin-top:20px;"><a href="{APP_BASE_URL}" target="_self" style="text-decoration:none; color:#2E7D32; font-weight:bold;">⬅️ Create New Quote</a></div>', unsafe_allow_html=True)


# --- 6. MAIN GENERATOR ---
def main():
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

        st.subheader("2. Select Plans")
        all_cols = list(df_plans.columns)
        if len(all_cols) > 2:
            plan_opts = all_cols[2:]
            sel_plans = st.multiselect("Compare Plans:", options=plan_opts)
            
            if sel_plans:
                if len(sel_plans) > 5:
                    st.warning("⚠️ You can select a maximum of 5 plans.")
                
                st.divider()
                st.subheader("3. Premiums & Notes")
                user_inputs = {}
                for plan in sel_plans[:5]:
                    st.markdown(f"**{plan}**")
                    c_prem, c_note = st.columns([1, 2])
                    with c_prem:
                        user_inputs[f"{plan}_prem"] = st.text_area("Premium", placeholder="e.g. ₹15k + GST", key=f"p_{plan}", height=100)
                    with c_note:
                        user_inputs[f"{plan}_note"] = st.text_area("Notes", placeholder="Benefits...", key=f"n_{plan}", height=100)
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.3;'>", unsafe_allow_html=True)

                st.subheader("4. Preview")
                cols = [all_cols[1]] + sel_plans[:5]
                comp_df = df_plans[cols].copy()
                comp_df.rename(columns={all_cols[1]: "Feature"}, inplace=True)
                st.dataframe(comp_df, hide_index=True, use_container_width=True, height=300)

                st.divider()
                if st.button("🚀 Generate Quote Link", type="primary"):
                    if not client_name:
                        st.error("Enter Client Name.")
                    else:
                        with st.spinner("Generating..."):
                            ws, row_count, _ = get_sheet_and_rows()
                            quote_id = generate_custom_id(sel_rm, row_count)
                            today_str = datetime.date.today().strftime("%d-%b-%Y")
                            
                            final_plans = []
                            for p in sel_plans[:5]:
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
                            
                            if log_quote_to_sheet(ws, quote_data):
                                target_url = f"{APP_BASE_URL}?quote_id={quote_id}"
                                st.success(f"✅ Quote **{quote_id}** Generated!")
                                st.markdown(f"""
                                <a href="{target_url}" target="_blank" style="text-decoration:none;">
                                    <div style="background-color:#4CAF50; color:white; padding:15px; border-radius:5px; text-align:center; font-weight:bold; font-size:18px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                        🔗 OPEN DIGITAL QUOTE: {quote_id}
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)
                            else:
                                st.error("Failed to log quote.")
            else:
                st.info("👈 Select plans to proceed.")
    else:
        st.error("❌ Data load failed.")

if __name__ == "__main__":
    main()
