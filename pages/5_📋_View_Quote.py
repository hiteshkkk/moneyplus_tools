import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" # 🚨 KEEP YOUR SHEET URL HERE
APP_BASE_URL = "https://moneyplustools.streamlit.app" 

# --- 2. CSS STYLES ---
ST_STYLE = """
<style>
    .stMultiSelect span[data-baseweb="tag"] { background-color: #e8f5e9 !important; border: 1px solid #4CAF50 !important; }
    .stMultiSelect span[data-baseweb="tag"] span { color: #1b5e20 !important; }
    div.stButton > button[kind="primary"] { background-color: #4CAF50 !important; border-color: #4CAF50 !important; color: white !important; }
    div.stButton > button[kind="primary"]:hover { background-color: #45a049 !important; border-color: #45a049 !important; }
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
    except Exception: return None

def get_sheet_and_rows():
    client = get_gspread_client()
    if not client: return None, 0
    try:
        sheet = client.open_by_url(SHEET_URL)
        try: ws = sheet.worksheet("Generated_Quotes")
        except: 
            ws = sheet.add_worksheet("Generated_Quotes", 1000, 25)
            ws.append_row(["Quote_ID", "Date", "RM_Name", "Client_Name", "City", "Policy_Type", "CRM_Link"])
        all_values = ws.get_all_values()
        return ws, len(all_values), all_values
    except: return None, 0, []

@st.cache_data(ttl=600)
def load_master_data():
    client = get_gspread_client()
    if not client: return None, None, None
    try:
        sheet = client.open_by_url(SHEET_URL)
        ws_drop = sheet.worksheet("Dropdown_Masters")
        r_drop = ws_drop.get_all_values()
        df_drop = pd.DataFrame(r_drop[1:], columns=r_drop[0]) if len(r_drop) > 1 else pd.DataFrame()
        
        ws_plans = sheet.worksheet("Plans_Master")
        r_plans = ws_plans.get_all_values()
        df_plans = pd.DataFrame(r_plans[3:], columns=r_plans[2]) if len(r_plans) > 3 else pd.DataFrame()

        try:
            ws_config = sheet.worksheet("Feature_Config")
            r_config = ws_config.get_all_values()
            df_config = pd.DataFrame(r_config[1:], columns=r_config[0]) if len(r_config) > 1 else pd.DataFrame()
        except:
            df_config = pd.DataFrame()

        return df_drop, df_plans, df_config
    except: return None, None, None

def generate_custom_id(rm_name, row_count):
    initials = "".join([x[0].upper() for x in rm_name.split() if x])
    return f"{initials}{datetime.datetime.now().strftime('%Y%m%d')}{row_count + 1}"

def log_quote_to_sheet(ws, q):
    try:
        row = [q['quote_id'], q['date'], q['rm'], q['client'], q['city'], q['type'], q['crm_link']]
        plans = q['plans']
        for i in range(5):
            if i < len(plans): row.extend([plans[i]['Plan Name'], plans[i]['Premium'], plans[i]['Notes']])
            else: row.extend(["", "", ""])
        ws.append_row(row)
        return True
    except: return False

# --- 4. VIEWER (FIXED CLICK ISSUE) ---
def render_quote_viewer(quote_id):
    st.set_page_config(page_title=f"Quote {quote_id}", layout="wide", initial_sidebar_state="collapsed")
    
    # Hide Streamlit UI via markdown (still needed to clear the frame)
    st.markdown("""
        <style>
            [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer, #MainMenu { display: none !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        </style>
    """, unsafe_allow_html=True)
    
    with st.spinner("Loading..."):
        ws, _, all_values = get_sheet_and_rows()
        if not ws: return
        
        headers = all_values[0]
        try: q_idx = headers.index("Quote_ID")
        except: q_idx = 0 
        
        target = None
        for row in all_values:
            if len(row) > q_idx and str(row[q_idx]).strip() == str(quote_id).strip():
                target = row; break
        if not target: st.error("Quote not found."); return

        def get(i): return target[i] if i < len(target) else ""

        date, rm, client, city, p_type = get(1), get(2), get(3), get(4), get(5)

        active_plans = []
        mini_cards_html = ""
        for i in range(5):
            base = 7 + (i*3)
            p_name = get(base)
            if p_name:
                p_prem = get(base+1)
                active_plans.append(p_name)
                mini_cards_html += f"""
                <div class="mini-plan-card">
                    <div class="mini-plan-name">{p_name}</div>
                    <div class="mini-plan-prem">{p_prem}</div>
                </div>"""

        _, df_plans, df_config = load_master_data()
        accordion_html = ""
        
        if df_plans is not None and not df_plans.empty and active_plans:
            all_cols = list(df_plans.columns)
            valid_plans = [p for p in active_plans if p in df_plans.columns]
            
            if valid_plans and not df_config.empty:
                for _, config_row in df_config.iterrows():
                    raw_name = config_row.get("Raw_Feature", "").strip()
                    display_title = config_row.get("Display_Title", raw_name)
                    explanation = config_row.get("Explanation", "")
                    icon = config_row.get("Icon", "🔹")
                    
                    good_words = [w.strip().lower() for w in config_row.get("Good_Words", "").split(",") if w.strip()]
                    bad_words = [w.strip().lower() for w in config_row.get("Bad_Words", "").split(",") if w.strip()]

                    plan_data_row = df_plans[df_plans.iloc[:, 1] == raw_name]
                    
                    if not plan_data_row.empty:
                        content_rows = ""
                        for plan in valid_plans:
                            val = str(plan_data_row.iloc[0][plan])
                            val_lower = val.lower()
                            css_class = "val-neutral"
                            status_icon = ""
                            if any(w in val_lower for w in good_words):
                                css_class = "val-good"; status_icon = "✅"
                            elif any(w in val_lower for w in bad_words):
                                css_class = "val-bad"; status_icon = "⚠️"
                            
                            content_rows += f"""
                            <div class="comp-row">
                                <div class="comp-plan-name">{plan}</div>
                                <div class="comp-value">
                                    <span class="{css_class}">{val} {status_icon}</span>
                                </div>
                            </div>"""
                        
                        accordion_html += f"""
                        <div class="accordion-item">
                            <div class="accordion-header" onclick="toggleAccordion(this)">
                                <div><div class="acc-title"><span class="acc-icon">{icon}</span> {display_title}</div><div class="acc-desc">{explanation}</div></div>
                                <div class="chevron">▼</div>
                            </div>
                            <div class="accordion-content">{content_rows}</div>
                        </div>"""

    # FULL HTML PAGE CONTENT
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Inter', sans-serif; background: #f8f9fa; color: #1f2937; }}
        .hero-section {{ background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%); color: white; padding: 60px 20px 80px; text-align: center; }}
        .hero-section h1 {{ margin: 0; font-size: 26px; }}
        .main-container {{ max-width: 800px; margin: -50px auto 0; padding: 0 20px 60px; position: relative; }}
        
        .client-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        .label {{ font-size: 10px; color: #666; text-transform: uppercase; font-weight: 700; }}
        .value {{ font-size: 14px; font-weight: 600; color: #000; }}
        
        .plans-summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 30px; }}
        .mini-plan-card {{ background: white; padding: 12px; border-radius: 8px; border: 1px solid #ddd; border-left: 4px solid #4CAF50; }}
        .mini-plan-name {{ font-weight: 700; color: #1b5e20; font-size: 13px; }}
        .mini-plan-prem {{ font-weight: 800; color: #d32f2f; font-size: 15px; }}

        /* Accordion */
        .accordion-item {{ background: white; border: 1px solid #eee; border-radius: 8px; margin-bottom: 10px; overflow: hidden; }}
        .accordion-header {{ padding: 15px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
        .accordion-header:hover {{ background: #f9f9f9; }}
        .acc-title {{ font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 8px; }}
        .acc-desc {{ font-size: 12px; color: #666; margin-left: 30px; }}
        .chevron {{ transition: 0.3s; }}
        .accordion-content {{ max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; background: #fafafa; border-top: 1px solid #eee; }}
        
        .active .chevron {{ transform: rotate(180deg); }}
        .active .accordion-content {{ max-height: 1000px; }}
        .active .accordion-header {{ background: #f0fdf4; }}

        .comp-row {{ display: flex; justify-content: space-between; padding: 10px 15px; border-bottom: 1px solid #eee; font-size: 13px; }}
        .val-good {{ color: #166534; background: #dcfce7; padding: 2px 6px; border-radius: 4px; font-weight: 600; }}
        .val-bad {{ color: #991b1b; background: #fee2e2; padding: 2px 6px; border-radius: 4px; font-weight: 600; }}
        
        @media print {{ .no-print {{ display: none; }} .accordion-content {{ max-height: none !important; }} }}
    </style>
    </head>
    <body>
        <div class="hero-section">
            <h1>Health Proposal</h1>
            <p>{client} | {date}</p>
        </div>
        <div class="main-container">
            <div class="client-card">
                <div><div class="label">Reference</div><div class="value">{quote_id}</div></div>
                <div><div class="label">Client</div><div class="value">{client}</div></div>
                <div><div class="label">City</div><div class="value">{city}</div></div>
                <div><div class="label">RM</div><div class="value">{rm}</div></div>
            </div>
            
            <div style="font-weight:700; margin-bottom:10px; color:#444;">Selected Plans</div>
            <div class="plans-summary">{mini_cards_html}</div>
            
            <div style="font-weight:700; margin-bottom:10px; color:#444; margin-top:30px;">Feature Guide</div>
            {accordion_html}
            
            <div style="text-align:center; margin-top:40px;" class="no-print">
                <button onclick="window.print()" style="background:#4CAF50; color:white; border:none; padding:12px 25px; font-weight:bold; border-radius:50px; cursor:pointer;">🖨️ Print Quote</button>
                <br><br>
                <a href="{APP_BASE_URL}" style="color:#666; font-size:12px; text-decoration:none;">Create New Quote</a>
            </div>
        </div>
        <script>
            function toggleAccordion(element) {{
                const item = element.parentElement;
                const isActive = item.classList.contains('active');
                document.querySelectorAll('.accordion-item').forEach(i => i.classList.remove('active'));
                if (!isActive) item.classList.add('active');
            }}
        </script>
    </body>
    </html>
    """
    
    # Render with Component (Sandboxed)
    components.html(full_html, height=1200, scrolling=True)

# --- 5. GENERATOR ---
def render_generator():
    st.markdown(ST_STYLE, unsafe_allow_html=True)
    st.title("📝 Health Insurance Quote Generator")
    with st.spinner("Syncing..."): df_drop, df_plans, _ = load_master_data()
    
    if df_plans is not None:
        c1, c2, c3, c4 = st.columns(4)
        rm = c1.selectbox("RM", [x for x in df_drop['RM Names'].unique() if x] if df_drop is not None else [])
        client = c2.text_input("Client Name")
        city = c3.text_input("City")
        p_type = c4.selectbox("Type", ["Fresh", "Port"])
        crm = st.text_input("CRM Link")
        
        st.divider()
        sel_plans = st.multiselect("Select Plans", df_plans.columns[2:].tolist() if not df_plans.empty else [])
        
        if sel_plans:
            user_inputs = {}
            for p in sel_plans[:5]:
                c_p, c_n = st.columns([1,2])
                user_inputs[f"{p}_p"] = c_p.text_area(f"{p} Premium", height=70)
                user_inputs[f"{p}_n"] = c_n.text_area(f"{p} Notes", height=70)
            
            if st.button("🚀 Generate Link", type="primary"):
                if not client: st.error("Client Name Required"); return
                ws, cnt, _ = get_sheet_and_rows()
                qid = generate_custom_id(rm, cnt)
                plans = [{"Plan Name":p, "Premium":user_inputs[f"{p}_p"], "Notes":user_inputs[f"{p}_n"]} for p in sel_plans[:5]]
                q_data = {"quote_id":qid, "date":datetime.date.today().strftime("%d-%b-%Y"), "rm":rm, "client":client, "city":city, "type":p_type, "crm_link":crm, "plans":plans}
                
                if log_quote_to_sheet(ws, q_data):
                    st.success(f"Generated: {qid}")
                    st.markdown(f'<a href="{APP_BASE_URL}?quote_id={qid}" target="_blank" style="background:#4CAF50;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;">Open Quote</a>', unsafe_allow_html=True)

def main():
    if "quote_id" in st.query_params: render_quote_viewer(st.query_params["quote_id"])
    else: render_generator()

if __name__ == "__main__": main()
