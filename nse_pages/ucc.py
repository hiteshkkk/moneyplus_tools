import streamlit as st
import requests
import gspread
from google.oauth2.service_account import Credentials
import datetime
from streamlit.web.server.websocket_headers import _get_websocket_headers

# --- 1. CONFIGURATION ---
PRIORITY_FIELDS = [
    "CLIENT CODE",
    "PRIMARY HOLDER FIRST NAME", 
    "PRIMARY HOLDER PAN",
    "HOLDING NATURE",
    "AUTHORIZATION STATUS",  # Matches your screenshot
    "BANK 1 STATUS"          # Matches your screenshot
]

# --- 2. CSS STYLING (The "Look and Feel") ---
# This CSS makes the table look clean, bold, and creates the "Pills"
TABLE_STYLE = """
<style>
    table.custom-report {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
    }
    table.custom-report td {
        padding: 12px 15px;
        border-bottom: 1px solid #e0e0e0;
        vertical-align: middle;
    }
    .field-label {
        font-weight: 700; /* BOLD Text */
        color: #31333F;
        width: 40%;
    }
    .field-value {
        color: #31333F;
        font-weight: 500;
    }
    /* The Green Pill */
    .badge-success {
        background-color: #d1e7dd;
        color: #0f5132;
        padding: 4px 10px;
        border-radius: 12px; /* Rounded Corners */
        font-weight: 700;
        font-size: 0.9em;
        display: inline-block;
    }
    /* The Red Pill */
    .badge-danger {
        background-color: #f8d7da;
        color: #721c24;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.9em;
        display: inline-block;
    }
    /* The Orange Pill */
    .badge-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.9em;
        display: inline-block;
    }
</style>
"""

# --- 3. HELPER: FORMAT VALUE AS HTML ---
def format_html_value(val):
    """Wraps status text in HTML spans for the 'Badge' look."""
    s = str(val)
    s_lower = s.lower()
    
    # Logic for badges
    if any(x in s_lower for x in ['success', 'active', 'approved', 'yes']):
        return f'<span class="badge-success">{s}</span>'
    
    if any(x in s_lower for x in ['fail', 'reject', 'error', 'no', 'invalid']):
        return f'<span class="badge-danger">{s}</span>'
        
    if any(x in s_lower for x in ['pending', 'wait']):
        return f'<span class="badge-warning">{s}</span>'
    
    return s # Return plain text if no keyword matches

# --- 4. NETWORK & LOGGING HELPERS (Keep same as before) ---
def get_network_details():
    details = {}
    try:
        details['Streamlit_Server_IP'] = requests.get('https://api.ipify.org').text
    except:
        details['Streamlit_Server_IP'] = "Unknown"
    try:
        headers = _get_websocket_headers()
        if headers:
            details['User_Public_IP'] = headers.get("X-Forwarded-For", "Hidden/Localhost")
            details['Browser_Info'] = headers.get("User-Agent", "Unknown")
        else:
            details['User_Public_IP'] = "Localhost/Unknown"
            details['Browser_Info'] = "Unknown"
    except:
        details['User_Public_IP'] = "Error"
        details['Browser_Info'] = "Error"
    return details

def log_to_google_sheet(client_code, full_response_json, net_info):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet_id = "1PI-BfizbrzMftNm69WxZ-YEnviA4aqeSjf4r4DZA4bw"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        api_text = str(full_response_json)
        net_text = f"User IP: {net_info.get('User_Public_IP')}\nBrowser: {net_info.get('Browser_Info')}\nServer IP: {net_info.get('Streamlit_Server_IP')}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, client_code, api_text, net_text])
    except Exception as e:
        print(f"Logging Error: {e}")

# --- 5. MAIN RENDER FUNCTION ---
def render(headers):
    st.markdown("## 📋 NSE UCC Details")
    st.caption("Fetch Client Master Report (UCC) details securely.")
    
    # Inject CSS
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)
    
    with st.form("ucc_form"):
        client_code = st.text_input("Enter Client Code", placeholder="e.g. YH032").upper()
        submitted = st.form_submit_button("Fetch Details")
    
    if submitted:
        if not client_code:
            st.warning("Please enter a Client Code.")
            return

        with st.spinner(f"Fetching details for {client_code}..."):
            try:
                # 1. Network & API
                net_info = get_network_details()
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/client_master_report"
                payload = { "client_code": client_code, "from_date": "", "to_date": "" }
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    log_to_google_sheet(client_code, data, net_info)

                    if data.get("report_data") and len(data["report_data"]) > 0:
                        record = data["report_data"][0]
                        
                        # --- BUILD THE HTML TABLE ---
                        html_rows = ""
                        
                        # Helper dict to track what we have printed
                        processed_keys = set()
                        cleaned_data = {}

                        # Pre-process keys (clean them)
                        for k, v in record.items():
                            if v is None or str(v).strip() == "": continue
                            clean_k = k.replace("_", " ").upper()
                            cleaned_data[clean_k] = v

                        # 1. Render Priority Fields First
                        for field in PRIORITY_FIELDS:
                            # We check if the priority field exists in our cleaned data
                            # We loop because your API keys might slightly differ (e.g. "BANK_1_STATUS")
                            # So we check exact matches or close matches
                            for k, v in cleaned_data.items():
                                if k == field and k not in processed_keys:
                                    formatted_val = format_html_value(v)
                                    html_rows += f"<tr><td class='field-label'>{k}</td><td class='field-value'>{formatted_val}</td></tr>"
                                    processed_keys.add(k)
                        
                        # 2. Render Remaining Fields
                        for k, v in cleaned_data.items():
                            if k not in processed_keys:
                                formatted_val = format_html_value(v)
                                html_rows += f"<tr><td class='field-label'>{k}</td><td class='field-value'>{formatted_val}</td></tr>"

                        # 3. Final Output
                        table_html = f"<table class='custom-report'>{html_rows}</table>"
                        st.success("Details Fetched Successfully")
                        st.markdown(table_html, unsafe_allow_html=True)
                        
                    else:
                        st.warning("No data found for this Client Code.")
                        st.json(data)
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
