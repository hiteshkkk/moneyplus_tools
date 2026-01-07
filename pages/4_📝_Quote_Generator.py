import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import string
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" # 🚨 REPLACE THIS
APP_BASE_URL = "https://moneyplustools.streamlit.app/Quote_Generator" 
ADMIN_PASSWORD = "admin" # 🔒 Change this

# --- 2. CSS STYLES (THE NUCLEAR VERSION) ---
ST_STYLE = """
<style>
    /* 1. HIDE STANDARD STREAMLIT UI */
    [data-testid="stHeader"], 
    [data-testid="stSidebar"], 
    [data-testid="stToolbar"], 
    .stDeployButton,            /* Hides Deploy Button */
    [data-testid="stDecoration"], /* Hides top decoration bar */
    footer, 
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    /* 2. REMOVE WHITE SPACE AT TOP */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        margin-top: 0 !important;
    }
    
    /* 3. FORCE LIGHT BACKGROUND UNIVERSALLY */
    .stApp {
        background-color: #ffffff;
        margin-top: -60px; /* Pulls content up to cover the header gap */
    }

    /* 4. HIDE 'MANAGE APP' BUTTON (Streamlit Cloud specific) */
    .stApp > header {
        display: none !important;
    }
    
    /* 5. YOUR CUSTOM BRANDING */
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
    if not client: return None, None, None, None, None, None
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
        except: df_config = pd.DataFrame()

        try:
            ws_faq = sheet.worksheet("FAQ_Master")
            r_faq = ws_faq.get_all_values()
            df_faq = pd.DataFrame(r_faq[1:], columns=r_faq[0]) if len(r_faq) > 1 else pd.DataFrame()
        except: df_faq = pd.DataFrame()

        try:
            ws_foot = sheet.worksheet("Footer_Master")
            r_foot = ws_foot.get_all_values()
            df_foot = pd.DataFrame(r_foot[1:], columns=r_foot[0]) if len(r_foot) > 1 else pd.DataFrame()
        except: df_foot = pd.DataFrame()

        try:
            ws_q = sheet.worksheet("Quotes_Master")
            r_q = ws_q.get_all_values()
            quotes_list = [row[0] for row in r_q[1:] if row]
        except: quotes_list = []

        return df_drop, df_plans, df_config, df_faq, df_foot, quotes_list
    except: return None, None, None, None, None, None

def generate_secure_id(rm_name, row_count, p_type):
    initials = "".join([x[0].upper() for x in rm_name.split() if x])
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    random_no = str(random.randint(100, 999)) # Random 3-digit
    type_suffix = "F" if p_type == "Fresh" else "P"
    # Format: PJ20260106846F
    return f"{initials}{date_str}{random_no}{type_suffix}"

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

def fetch_quote_data(quote_id):
    ws, _, all_values = get_sheet_and_rows()
    if not ws: return None
    
    headers = all_values[0]
    try: q_idx = headers.index("Quote_ID")
    except: q_idx = 0 
    
    target = None
    for row in all_values:
        if len(row) > q_idx and str(row[q_idx]).strip() == str(quote_id).strip():
            target = row; break
            
    if not target: return None
    
    def get(i): return target[i] if i < len(target) else ""
    
    data = {
        "quote_id": quote_id,
        "date": get(1), "rm": get(2), "client": get(3), "city": get(4), "type": get(5), "crm_link": get(6),
        "plans": []
    }
    
    for i in range(5):
        base = 7 + (i*3)
        p_name = get(base)
        if p_name:
            data["plans"].append({
                "Plan Name": p_name,
                "Premium": get(base+1),
                "Notes": get(base+2)
            })
    return data

# --- 4. VIEWER ---
def render_quote_viewer(quote_id):
    quote_data = fetch_quote_data(quote_id)
    page_title = f"Health Proposal for {quote_data['client']}" if quote_data else "MoneyPlus Quote"
    
    st.set_page_config(page_title=page_title, page_icon="🏥", layout="wide", initial_sidebar_state="collapsed")
    
    # APPLY NUCLEAR CSS IN VIEWER MODE TOO
    st.markdown("""
        <style>
            [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"], footer, #MainMenu { display: none !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
            body { font-family: 'Inter', sans-serif; background-color: #ffffff; color: #1f2937; margin: 0; }
        </style>
    """, unsafe_allow_html=True)
    
    if not quote_data: st.error("Quote not found."); return

    _, df_plans, df_config, df_faq, df_foot, quotes_list = load_master_data()
    
    client = quote_data['client']
    try: rm_initials = quote_id[:2]
    except: rm_initials = "GEN"

    buy_link = f"https://health.moneyplus.in?id={rm_initials}"
    whatsapp_msg = f"I need more help with my quote {APP_BASE_URL}?quote_id={quote_id}"
    whatsapp_link = f"https://wa.me/918087058000?text={whatsapp_msg.replace(' ', '%20')}"
    random_quote = random.choice(quotes_list) if quotes_list else "Health is wealth. Protect it today."

    # 1. HTML GENERATION
    plans_html = ""
    active_plans_names = []
    for p in quote_data['plans']:
        active_plans_names.append(p['Plan Name'])
        p_prem = p['Premium'].replace('\n', '<br>')
        p_note = p['Notes'].replace('\n', '<br>')
        plans_html += f"""<div class="plan-card"><div class="plan-header">{p['Plan Name']}</div><div class="plan-prem">{p_prem}</div><div class="plan-notes"><strong>📝 Notes:</strong><br>{p_note}</div></div>"""

    accordion_html = ""
    if df_plans is not None and not df_plans.empty and active_plans_names:
        if not df_config.empty:
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
                    for plan in active_plans_names:
                        val = str(plan_data_row.iloc[0][plan])
                        val_cleaned = val.replace('\n', '<br>')
                        if "http" in val_cleaned:
                            urls = [word for word in val.split() if word.startswith('http')]
                            if urls: val_cleaned = f'<a href="{urls[0]}" target="_blank" style="color:#2E7D32; text-decoration:underline;">Click to View</a>'
                        val_lower = val.lower()
                        css_class = "val-neutral"; status_icon = ""
                        if any(w in val_lower for w in good_words): css_class = "val-good"; status_icon = "✅"
                        elif any(w in val_lower for w in bad_words): css_class = "val-bad"; status_icon = "⚠️"
                        content_rows += f"""<div class="comp-row"><div class="comp-label">{plan}</div><div class="comp-val"><span class="{css_class}">{val_cleaned} {status_icon}</span></div></div>"""
                    accordion_html += f"""<div class="accordion-item"><div class="accordion-header" onclick="toggleAccordion(this)"><div class="acc-left"><span class="acc-icon">{icon}</span> {display_title} <span class="acc-desc"> - {explanation}</span></div><div class="chevron">▼</div></div><div class="accordion-content">{content_rows}</div></div>"""

    faq_html = ""
    if not df_faq.empty:
        for _, row in df_faq.iterrows():
            if row.get("Question"): 
                q = row.get("Question", "")
                a = str(row.get("Answer", "")).replace('\n', '<br>')
                faq_html += f'<div class="faq-item"><div class="faq-q">❓ {q}</div><div class="faq-a">{a}</div></div>'

    footer_text_html = ""
    if not df_foot.empty:
        for _, row in df_foot.iterrows():
            if row.get("Content"): footer_text_html += f"<p>{row['Content']}</p>"

    # 4. FINAL HTML WITH GOOGLE TRANSLATE
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Inter', sans-serif; background: #fff; color: #1f2937; top: 0 !important; }}
        
        #google_translate_element {{ text-align: center; margin-top: 10px; }}
        .goog-te-gadget-simple {{ background-color: #f0fdf4 !important; border: 1px solid #4CAF50 !important; padding: 5px 10px !important; border-radius: 20px !important; font-size: 13px !important; line-height: 20px !important; display: inline-block; cursor: pointer; zoom: 1; }}
        .goog-te-gadget-simple a {{ text-decoration: none !important; color: #166534 !important; font-weight: bold !important; }}
        .goog-te-banner-frame {{ display: none !important; }} 
        body {{ top: 0px !important; }}

        .header {{ text-align: center; padding: 20px 20px 20px; border-bottom: 1px solid #eee; }}
        .header img {{ height: 60px; margin-bottom: 10px; }}
        .header h1 {{ margin: 0; font-size: 24px; color: #2E7D32; font-weight: 700; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 0 20px 120px; }}
        
        .client-card {{ background: #f0f4f8; border-radius: 8px; padding: 20px; margin: 30px 0; border: 1px solid #dbeafe; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        .c-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 700; }}
        .c-val {{ font-size: 15px; font-weight: 600; color: #0f172a; }}

        .plan-card {{ break-inside: avoid; page-break-inside: avoid; background: white; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-top: 4px solid #4CAF50; overflow: hidden; }}
        .plans-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 40px; }}
        .plan-header {{ padding: 15px; background: #fff; font-size: 16px; font-weight: 700; color: #14532d; border-bottom: 1px solid #f1f5f9; }}
        .plan-prem {{ padding: 15px; font-size: 20px; font-weight: 800; color: #1e3a8a; }}
        .plan-notes {{ padding: 15px; background: #fffbeb; font-size: 13px; color: #4b5563; line-height: 1.5; border-top: 1px solid #fef3c7; }}

        .pro-tip {{ background: #fff7ed; border-left: 4px solid #ea580c; padding: 15px; margin: 30px 0; border-radius: 4px; break-inside: avoid; }}
        .pro-title {{ color: #9a3412; font-weight: 700; font-size: 15px; margin-bottom: 5px; }}
        .pro-text {{ color: #431407; font-size: 13px; line-height: 1.5; }}

        .section-title {{ font-size: 18px; font-weight: 700; color: #111; margin: 40px 0 15px; border-bottom: 2px solid #4CAF50; display: inline-block; padding-bottom: 5px; page-break-after: avoid; }}
        .controls {{ margin-bottom: 15px; text-align: right; }}
        .btn-ctrl {{ font-size: 12px; cursor: pointer; color: #2E7D32; text-decoration: underline; margin-left: 15px; background: none; border: none; }}
        
        .accordion-item {{ border: 1px solid #e2e8f0; margin-bottom: 8px; border-radius: 6px; overflow: hidden; break-inside: avoid; page-break-inside: avoid; }}
        .accordion-header {{ padding: 12px 15px; background: #f8fafc; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: 0.2s; }}
        .accordion-header:hover {{ background: #f1f5f9; }}
        .acc-left {{ font-weight: 600; font-size: 15px; color: #334155; }}
        .acc-desc {{ font-weight: 400; font-size: 12px; color: #64748b; margin-left: 5px; display: inline-block; }}
        .chevron {{ font-size: 12px; color: #94a3b8; transition: 0.3s; }}
        .accordion-content {{ max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; background: white; }}
        .comp-row {{ display: grid; grid-template-columns: 35% 65%; padding: 12px 15px; border-top: 1px solid #f1f5f9; font-size: 13px; align-items: start; }}
        .comp-label {{ font-weight: 600; color: #475569; }}
        .comp-val {{ text-align: right; color: #0f172a; white-space: pre-wrap; }}
        .active .chevron {{ transform: rotate(180deg); }}
        .active .accordion-content {{ max-height: 2000px; }}
        .active .accordion-header {{ background: #dcfce7; }}
        .val-good {{ color: #15803d; font-weight: 600; background: #dcfce7; padding: 2px 6px; border-radius: 4px; }}
        .val-bad {{ color: #b91c1c; font-weight: 600; background: #fee2e2; padding: 2px 6px; border-radius: 4px; }}

        .quote-box {{ text-align: center; margin: 40px 0; padding: 20px; background: #f0fdf4; border-radius: 8px; color: #166534; font-style: italic; font-weight: 500; border: 1px dashed #4CAF50; break-inside: avoid; }}
        .faq-item {{ margin-bottom: 15px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; break-inside: avoid; }}
        .faq-q {{ font-weight: 700; color: #1e293b; margin-bottom: 5px; }}
        .faq-a {{ font-size: 13px; color: #475569; line-height: 1.5; }}
        .static-footer {{ text-align: center; font-size: 11px; color: #94a3b8; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }}

        .sticky-footer {{ position: fixed; bottom: 0; left: 0; width: 100%; background: white; border-top: 1px solid #ccc; padding: 10px 0; display: flex; justify-content: space-around; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); z-index: 100; }}
        .f-btn {{ text-decoration: none; padding: 12px 20px; border-radius: 5px; font-size: 14px; font-weight: 700; text-align: center; flex: 1; margin: 0 10px; display: flex; align-items: center; justify-content: center; }}
        .btn-print {{ background: #f1f5f9; color: #334155; }}
        .btn-help {{ background: #22c55e; color: white; }}
        .btn-buy {{ background: #2563eb; color: white; }}
        @media (max-width: 600px) {{ .acc-desc {{ display: block; margin-left: 24px; margin-top: 2px; }} .sticky-footer {{ padding: 10px 5px; }} .f-btn {{ padding: 10px 5px; font-size: 12px; margin: 0 2px; }} }}
        @media print {{ .no-print, .sticky-footer, .controls, #google_translate_element {{ display: none; }} .accordion-content {{ max-height: none !important; display: block; }} }}
    </style>
    
    <script type="text/javascript">
    function googleTranslateElementInit() {{
      new google.translate.TranslateElement({{
        pageLanguage: 'en', 
        includedLanguages: 'en,hi,mr,gu,ml,ta,kn,te,bn', 
        layout: google.translate.TranslateElement.InlineLayout.SIMPLE
      }}, 'google_translate_element');
    }}
    </script>
    <script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>

    </head>
    <body>
        <div id="google_translate_element"></div>
        <div class="header">
            <img src="https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png" alt="MoneyPlus">
            <h1>Health Insurance Quotes</h1>
        </div>
        <div class="container">
            <div class="client-card">
                <div><div class="c-label">Name</div><div class="c-val">{client}</div></div>
                <div><div class="c-label">City</div><div class="c-val">{quote_data['city']}</div></div>
                <div><div class="c-label">Quote ID</div><div class="c-val">{quote_id}</div></div>
                <div><div class="c-label">Date</div><div class="c-val">{quote_data['date']}</div></div>
            </div>
            
            <div class="section-title">Selected Plans</div>
            <div class="plans-grid">{plans_html}</div>
            
            <div class="pro-tip">
                <div class="pro-title">🚀 Pro-tip: Beat the Premium Hike</div>
                <div class="pro-text">Medical costs rise every year, and so do insurance premiums. But you can outsmart inflation! Opt for a multi-year plan (3 or 5 years) to freeze your premium at today’s rate and enjoy an extra discount. Same protection, significantly lower cost.</div>
            </div>

            <div class="section-title">Feature Comparison</div>
            <div class="controls no-print">
                <button class="btn-ctrl" onclick="expandAll()">[+] Expand All</button>
                <button class="btn-ctrl" onclick="collapseAll()">[-] Collapse All</button>
            </div>
            {accordion_html}
            
            <div class="quote-box">
                 🧠 Food for Thought: "{random_quote}"
            </div>

            <div class="section-title">Frequently Asked Questions</div>
            {faq_html}
            <div class="static-footer">{footer_text_html}</div>
        </div>
        <div class="sticky-footer no-print">
            <a href="{whatsapp_link}" target="_blank" class="f-btn btn-help">💬 Need Help?</a>
            <a href="{buy_link}" target="_blank" class="f-btn btn-buy">🛒 Buy Now</a>
            <a href="#" onclick="window.print(); return false;" class="f-btn btn-print">🖨️ Print Quote</a>
        </div>
        <script>
            function toggleAccordion(element) {{
                const item = element.parentElement;
                const isActive = item.classList.contains('active');
                if (isActive) item.classList.remove('active');
                else item.classList.add('active');
            }}
            function expandAll() {{ document.querySelectorAll('.accordion-item').forEach(i => i.classList.add('active')); }}
            function collapseAll() {{ document.querySelectorAll('.accordion-item').forEach(i => i.classList.remove('active')); }}
        </script>
    </body>
    </html>
    """
    components.html(full_html, height=1200, scrolling=True)

# --- 5. ADMIN / GENERATOR ---
def render_admin_login():
    st.title("🔒 Admin Access")
    pwd = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if pwd == ADMIN_PASSWORD:
            st.session_state['authenticated'] = True
            st.rerun()
        else: st.error("Invalid Password")

def render_generator():
    if not st.session_state.get('authenticated', False):
        render_admin_login()
        return

    st.markdown(ST_STYLE, unsafe_allow_html=True)
    st.title("📝 Quote Generator")
    
    # EDIT MODE
    c_load1, c_load2 = st.columns([3, 1])
    edit_id = c_load1.text_input("Load Quote to Edit (ID)", placeholder="Paste Quote ID here...")
    
    if c_load2.button("Load Data"):
        if edit_id:
            data = fetch_quote_data(edit_id)
            if data:
                st.session_state['edit_data'] = data
                st.success(f"Loaded: {data['client']}")
                st.rerun()
            else: st.warning("ID Not Found")

    loaded = st.session_state.get('edit_data', None)

    with st.spinner("Syncing..."): df_drop, df_plans, _, _, _, _ = load_master_data()
    
    if df_plans is not None:
        c1, c2, c3, c4 = st.columns(4)
        
        # Helper to get existing values
        def get_val(key, default): return loaded[key] if loaded else default
        
        rm_opts = [x for x in df_drop['RM Names'].unique() if x] if df_drop is not None else []
        def_rm_idx = 0
        if loaded and loaded['rm'] in rm_opts: def_rm_idx = rm_opts.index(loaded['rm'])
        
        rm = c1.selectbox("RM Name", rm_opts, index=def_rm_idx)
        client = c2.text_input("Client Name", value=get_val('client', ''))
        city = c3.text_input("City", value=get_val('city', ''))
        
        type_opts = ["Fresh", "Port"]
        def_type_idx = 0
        if loaded and loaded['type'] in type_opts: def_type_idx = type_opts.index(loaded['type'])
        p_type = c4.selectbox("Policy Type", type_opts, index=def_type_idx)
        
        crm = st.text_input("CRM Link", value=get_val('crm_link', ''))
        
        st.divider()
        
        # Plan Selection
        all_plan_names = df_plans.columns[2:].tolist()
        def_plans = []
        if loaded:
            def_plans = [p['Plan Name'] for p in loaded['plans'] if p['Plan Name'] in all_plan_names]
            
        sel_plans = st.multiselect("Select Plans", all_plan_names, default=def_plans)
        
        if sel_plans:
            user_inputs = {}
            for p in sel_plans[:5]:
                exist_p, exist_n = "", ""
                if loaded:
                    for lp in loaded['plans']:
                        if lp['Plan Name'] == p: exist_p, exist_n = lp['Premium'], lp['Notes']
                
                st.markdown(f"**{p}**")
                c_p, c_n = st.columns([1,2])
                user_inputs[f"{p}_p"] = c_p.text_area("Premium", value=exist_p, height=70, key=f"p_{p}")
                user_inputs[f"{p}_n"] = c_n.text_area("Notes", value=exist_n, height=70, key=f"n_{p}")
            
            if st.button("🚀 Generate Quote Link", type="primary"):
                if not client: st.error("Client Name Required"); return
                
                ws, cnt, _ = get_sheet_and_rows()
                qid = generate_secure_id(rm, cnt, p_type) # Always new ID
                
                final_plans = [{"Plan Name":p, "Premium":user_inputs[f"{p}_p"], "Notes":user_inputs[f"{p}_n"]} for p in sel_plans[:5]]
                q_data = {
                    "quote_id":qid, "date":datetime.date.today().strftime("%d-%b-%Y"), 
                    "rm":rm, "client":client, "city":city, "type":p_type, "crm_link":crm, "plans":final_plans
                }
                
                if log_quote_to_sheet(ws, q_data):
                    st.success(f"✅ Created Quote: {qid}")
                    link = f"{APP_BASE_URL}?quote_id={qid}"
                    st.code(link)
                    st.markdown(f'<a href="{link}" target="_blank" style="background:#4CAF50;color:white;padding:12px 25px;text-decoration:none;border-radius:5px;display:inline-block;font-weight:bold;">Open Quote Viewer</a>', unsafe_allow_html=True)

# --- 6. MAIN ROUTER ---
def main():
    if "quote_id" in st.query_params:
        render_quote_viewer(st.query_params["quote_id"])
    else:
        render_generator()

if __name__ == "__main__":
    main()
