import streamlit as st
import requests
import gspread
from google.oauth2.service_account import Credentials
import datetime
# IMPORT UTILS
from nse_pages.utils import TABLE_STYLE, render_custom_table, get_network_details

# --- CONFIG ---
UCC_PRIORITY = [
    "CLIENT CODE", "PRIMARY HOLDER FIRST NAME", "PRIMARY HOLDER PAN",
    "HOLDING NATURE", "AUTHORIZATION STATUS", "BANK 1 STATUS"
]

def log_to_google_sheet(client_code, full_response_json, net_info):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet_id = "1PI-BfizbrzMftNm69WxZ-YEnviA4aqeSjf4r4DZA4bw" # UCC Sheet
        sheet = client.open_by_key(sheet_id).sheet1 
        
        api_text = str(full_response_json)
        net_text = f"User IP: {net_info.get('User_Public_IP')}\nBrowser: {net_info.get('Browser_Info')}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, client_code, api_text, net_text])
    except Exception as e:
        print(f"Logging Error: {e}")

def render(headers):
    st.markdown("## 📋 NSE UCC Details")
    st.caption("Fetch Client Master Report (UCC) details securely.")
    
    # INJECT SHARED CSS
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
                net_info = get_network_details()
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/CLIENT_AUTHORIZATION"
                payload = { "client_code": client_code, "from_date": "", "to_date": "" }
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    log_to_google_sheet(client_code, data, net_info)

                    if data.get("report_data") and len(data["report_data"]) > 0:
                        record = data["report_data"][0]
                        
                        st.success("Details Fetched Successfully")
                        
                        # --- USE SHARED RENDERER ---
                        html_table = render_custom_table(record, priority_fields=UCC_PRIORITY)
                        st.markdown(html_table, unsafe_allow_html=True)
                        
                    else:
                        st.warning("No data found for this Client Code.")
                        st.json(data)
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
