import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import string

# --- CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" # 🚨 REPLACE THIS
# NOTE: This URL points to the SEPARATE page we will create next
APP_BASE_URL = "https://moneyplustools.streamlit.app/View_Quote" 
ADMIN_PASSWORD = "admin" 

# --- GOOGLE SHEETS HELPERS ---
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
        
        # We also need to fetch existing quotes for the "Load" feature
        try:
            ws_generated = sheet.worksheet("Generated_Quotes")
            r_gen = ws_generated.get_all_values()
            # Simple list of IDs for verification/loading could be done here if needed
        except: pass

        return df_drop, df_plans, client
    except: return None, None, None

def generate_secure_id(rm_name, row_count, p_type):
    initials = "".join([x[0].upper() for x in rm_name.split() if x])
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    random_no = str(random.randint(100, 999))
    type_suffix = "F" if p_type == "Fresh" else "P"
    return f"{initials}{date_str}{random_no}{type_suffix}"

def log_quote_to_sheet(ws, q):
    try:
        row = [q['quote_id'], q['date'], q['rm'], q['client'], q['city'], q['type'], q['crm_link']]
        plans = q['plans']
        for i in range(5):
            if i < len(plans): 
                row.extend([plans[i]['Plan Name'], plans[i]['Premium'], plans[i]['Notes']])
            else: 
                row.extend(["", "", ""])
        ws.append_row(row)
        return True
    except: return False

def fetch_quote_data_by_id(quote_id):
    # This helper is needed for the "Load Data" feature in Generator
    ws, _, all_values = get_sheet_and_rows()
    if not ws: return None
    
    headers = all_values[0]
    try: q_idx = headers.index("Quote_ID")
    except: q_idx = 0 
    
    target = None
    for row in all_values:
        if len(row) > q_idx and str(row[q_idx]).strip() == str(quote_id).strip():
            target = row
            break
    
    if not target: return None
    
    def get(i): return target[i] if i < len(target) else ""
    
    # Parse back into dictionary
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

# --- MAIN GENERATOR UI ---
def main():
    st.set_page_config(page_title="Quote Admin", page_icon="🛠️", layout="wide")

    # 1. Password Check
    if not st.session_state.get('authenticated', False):
        st.title("🔒 Admin Login")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Incorrect Password")
        return

    # 2. Main App Interface
    st.title("📝 Quote Generator")
    
    # --- Edit Mode Logic ---
    c_load1, c_load2 = st.columns([3, 1])
    edit_id = c_load1.text_input("Load Quote to Edit (ID)", placeholder="Paste Quote ID here...")
    
    if c_load2.button("Load Data"):
        if edit_id:
            data = fetch_quote_data_by_id(edit_id)
            if data:
                st.session_state['edit_data'] = data
                st.success(f"Loaded: {data['client']}")
                st.rerun()
            else:
                st.warning("ID Not Found")

    loaded = st.session_state.get('edit_data', None)

    # --- Load Data ---
    with st.spinner("Syncing Master Data..."): 
        df_drop, df_plans, _ = load_master_data()
    
    if df_plans is not None:
        c1, c2, c3, c4 = st.columns(4)
        
        # Helper to get existing values (Pre-fill)
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
        
        # --- Plan Selection ---
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
                st.divider()
            
            if st.button("🚀 Generate Quote Link", type="primary"):
                if not client: 
                    st.error("Client Name Required")
                    return
                
                ws, cnt, _ = get_sheet_and_rows()
                qid = generate_secure_id(rm, cnt, p_type)
                
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

if __name__ == "__main__":
    main()
