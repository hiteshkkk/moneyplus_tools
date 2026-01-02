import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1B7-y...YOUR_FULL_URL_HERE" # 🚨 KEEP YOUR SHEET URL HERE
APP_BASE_URL = "https://moneyplustools.streamlit.app" 

# --- 2. CSS STYLES ---

# A. Generator Mode Styles (Green Buttons, Tags)
GENERATOR_CSS = """
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
</style>
"""

# B. Viewer Mode Styles (Hides Streamlit UI for "Website" Look)
VIEWER_CSS = """
<style>
    /* 1. HIDE STREAMLIT CHROME (The "Window" parts) */
    [data-testid="stHeader"], 
    [data-testid="stSidebar"], 
    [data-testid="stToolbar"], 
    footer, 
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    
    /* 2. REMOVE PADDING (Full Screen) */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }
    .stApp {
        background-color: #f8f9fa; /* Match Page BG */
        margin-top: -50px; /* Pull up to cover any remaining gap */
    }

    /* 3. CUSTOM TYPOGRAPHY & LAYOUT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .quote-page {
        font-family: 'Inter', sans-serif;
        color: #1f2937;
        line-height: 1.5;
        width: 100%;
    }

    /* HERO */
    .hero-section {
        background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%);
        color: white;
        padding: 80px 20px 100px;
        text-align: center;
        width: 100%;
    }
    .hero-section h1 { margin: 0; font-size: 32px; font-weight: 700; color: white !important; }
    .hero-section p { color: rgba(255,255,255,0.9); font-size: 16px; margin-top: 10px; }
    
    /* CONTAINER */
    .main-container {
        max-width: 1000px;
        margin: -60px auto 0;
        padding: 0 20px 60px;
        position: relative;
        z-index: 10;
    }
    
    /* CARDS */
    .client-card {
        background: white;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 40px;
        border: 1px solid #eaeaea;
    }
    .label { font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; }
    .value { font-size: 16px; font-weight: 700; color: #111; margin-top: 4px; }

    /* SECTIONS */
    .section-header {
        font-size: 20px; font-weight: 700; color: #1f2937; margin: 40px 0 20px;
        padding-bottom: 10px; border-bottom: 2px solid #eee;
    }

    /* PLAN GRID */
    .plans-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 25px;
    }
    .plan-card {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        transition: transform 0.2s;
    }
    .plan-card:hover { transform: translateY(-5px); box-shadow: 0 12px 20px rgba(0,0,0,0.1); }
    
    .card-top { background: #f0fdf4; padding: 20px; border-bottom: 1px solid #e5e7eb; }
    .card-title { font-size: 18px; font-weight: 700; color: #166534; }
    
    .card-content { padding: 25px; }
    .price-tag { font-size: 22px; font-weight: 800; color: #dc2626; margin-bottom: 15px; }
    .notes-text { font-size: 14px; color: #4b5563; background: #fffbeb; padding: 15px; border-radius: 8px; line-height: 1.6; }

    /* TABLE */
    .table-container {
        background: white; border-radius: 12px; overflow: hidden;
        border: 1px solid #e5e7eb; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        overflow-x: auto;
    }
    table { width: 100%; border-collapse: collapse; min-width: 600px; }
    th { background: #f9fafb; padding: 15px; text-align: left; font-size: 13px; color: #6b7280; border-bottom: 1px solid #e5e7eb; }
    td { padding: 15px; border-bottom: 1px solid #e5e7eb; font-size: 14px; color: #374151; vertical-align: top; }
    
    /* PRINT */
    @media print {
        .hero-section { padding: 20px; color: #000; background: none; text-align: left; border-bottom: 2px solid #4CAF50; }
        .hero-section h1 { color: #2E7D32 !important; font-size: 24px; }
        .main-container { margin-top: 0; max-width: 100%; box-shadow: none; padding: 0; }
        .client-card, .plan-card, .table-container { box-shadow: none; border: 1px solid #ccc; margin-bottom: 20px; break-inside: avoid; }
        .no-print { display: none; }
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
        return ws, len(all_values), all_values
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
            quote_data['quote_id'], quote_data['date'], quote_data['rm'],
            quote_data['client'], quote_data['city'], quote_data['type'], quote_data['crm_link']
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

# --- 4. VIEWER MODE ---
def render_quote_viewer(quote_id):
    # 1. Inject CSS to Hide UI
    st.markdown(VIEWER_CSS, unsafe_allow_html=True)
    
    # 2. Fetch Data
    with st.spinner("Loading Proposal..."):
        ws, _, all_values = get_sheet_and_rows()
        if not ws: return
        
        headers = all_values[0]
        try: q_idx = headers.index("Quote_ID")
        except: q_idx = 0 

        target_row = None
        for row in all_values:
            if len(row) > q_idx and str(row[q_idx]).strip() == str(quote_id).strip():
                target_row = row
                break
        
        if not target_row:
            st.error(f"Quote {quote_id} not found.")
            return

        def safe_get(idx): return target_row[idx] if idx < len(target_row) else ""

        # Map Data
        date_val, rm_val = safe_get(1), safe_get(2)
        client_val, city_val = safe_get(3), safe_get(4)
        type_val = safe_get(5)

        # Build Plans HTML
        plans_html = ""
        active_plans = []
        for i in range(5):
            base = 7 + (i * 3)
            p_name = safe_get(base)
            if p_name and p_name.strip():
                p_prem = safe_get(base + 1).replace('\n', '<br>')
                p_note = safe_get(base + 2).replace('\n', '<br>')
                active_plans.append(p_name)
                plans_html += f"""
                <div class="plan-card">
                    <div class="card-top"><div class="card-title">{p_name}</div></div>
                    <div class="card-content">
                        <div class="price-tag">{p_prem}</div>
                        <div class="notes-text"><strong>Highlights:</strong><br>{p_note}</div>
                    </div>
                </div>
                """

        # Build Table HTML
        table_html = ""
        _, df_plans = load_master_data()
        if df_plans is not None and not df_plans.empty and active_plans:
            all_cols = list(df_plans.columns)
            valid_plans = [p for p in active_plans if p in df_plans.columns]
            if valid_plans:
                cols = [all_cols[1]] + valid_plans
                comp_df = df_plans[cols].copy()
                comp_df.rename(columns={all_cols[1]: "Feature"}, inplace=True)
                table_html = comp_df.to_html(index=False, border=0, classes="compare-table")
                table_html = table_html.replace("\\n", "<br>").replace("\n", "<br>")

        # 3. Render Page
        st.markdown(f"""
        <div class="quote-page">
            <div class="hero-section">
                <h1>Health Insurance Proposal</h1>
                <p>Prepared for <strong>{client_val}</strong> by {rm_val} | {date_val}</p>
            </div>
            <div class="main-container">
                <div class="client-card">
                    <div><div class="label">Reference</div><div class="value">{quote_id}</div></div>
                    <div><div class="label">Client</div><div class="value">{client_val}</div></div>
                    <div><div class="label">City</div><div class="value">{city_val}</div></div>
                    <div><div class="label">Type</div><div class="value">{type_val}</div></div>
                </div>
                
                <div class="section-header">Recommended Options</div>
                <div class="plans-grid">{plans_html}</div>
                
                <div class="section-header">Feature Comparison</div>
                <div class="table-container">{table_html}</div>
                
                <div style="text-align:center; margin-top:50px;" class="no-print">
                    <button onclick="window.print()" style="background:#4CAF50; color:white; border:none; padding:15px 30px; font-size:16px; font-weight:bold; border-radius:50px; cursor:pointer; box-shadow:0 4px 10px rgba(76,175,80,0.3);">🖨️ Download PDF</button>
                    <br><br>
                    <a href="{APP_BASE_URL}" style="color:#6b7280; text-decoration:none; font-size:14px;">&larr; Create New Quote</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 5. GENERATOR MODE ---
def render_generator():
    st.markdown(GENERATOR_CSS, unsafe_allow_html=True)
    st.title("📝 Health Insurance Quote Generator")

    if "YOUR_FULL_URL_HERE" in SHEET_URL:
        st.warning("⚠️ Update SHEET_URL in code.")
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
                if len(sel_plans) > 5: st.warning("⚠️ Max 5 plans.")
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
                                "quote_id": quote_id, "date": today_str, "rm": sel_rm,
                                "client": client_name, "city": city, "type": pol_type, "crm_link": crm_link,
                                "plans": final_plans
                            }
                            
                            if log_quote_to_sheet(ws, quote_data):
                                target_url = f"{APP_BASE_URL}?quote_id={quote_id}"
                                st.success(f"✅ Quote **{quote_id}** Generated!")
                                st.markdown(f"""
                                <a href="{target_url}" target="_blank" style="text-decoration:none;">
                                    <div style="background-color:#4CAF50; color:white; padding:15px; border-radius:8px; text-align:center; font-weight:bold; font-size:18px; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                                        🔗 OPEN DIGITAL QUOTE
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)
                            else:
                                st.error("Log failed.")
            else:
                st.info("👈 Select plans.")

# --- 6. MAIN APP LOGIC ---
def main():
    # 🚨 CRITICAL: THIS MUST BE THE FIRST STREAMLIT COMMAND
    # We set layout="wide" globally. We control the rest via CSS.
    st.set_page_config(page_title="Quote Tool", page_icon="📝", layout="wide", initial_sidebar_state="collapsed")

    # Routing
    if "quote_id" in st.query_params:
        render_quote_viewer(st.query_params["quote_id"])
    else:
        render_generator()

if __name__ == "__main__":
    main()
