import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
from streamlit.web.server.websocket_headers import _get_websocket_headers

# --- HELPER: GET NETWORK DETAILS ---
def get_network_details():
    """Captures Server IP, User IP, and Browser Info."""
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

# --- HELPER: LOG TO UCC SHEET ---
def log_to_google_sheet(client_code, full_response_json, net_info):
    """
    Appends a row to the UCC Logs Sheet.
    Sheet ID: 1PI-BfizbrzMftNm69WxZ-YEnviA4aqeSjf4r4DZA4bw
    """
    try:
        # 1. Load Credentials
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        # 2. Open Sheet by ID
        sheet_id = "1PI-BfizbrzMftNm69WxZ-YEnviA4aqeSjf4r4DZA4bw"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        # 3. Format Raw API Response (Col C)
        api_text = str(full_response_json) # Convert dict to string for safety
            
        # 4. Format Network Details (Col D)
        net_text = (
            f"User IP: {net_info.get('User_Public_IP')}\n"
            f"Browser: {net_info.get('Browser_Info')}\n"
            f"Server IP: {net_info.get('Streamlit_Server_IP')}"
        )

        # 5. Append Row
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, client_code, api_text, net_text])
        
    except Exception as e:
        print(f"Logging Error: {e}")

# --- MAIN RENDER FUNCTION ---
def render(headers):
    st.markdown("## 📋 NSE UCC Details")
    st.caption("Fetch Client Master Report (UCC) details securely.")
    
    with st.form("ucc_form"):
        client_code = st.text_input("Enter Client Code", placeholder="e.g. YH032").upper()
        submitted = st.form_submit_button("Fetch Details")
    
    if submitted:
        if not client_code:
            st.warning("Please enter a Client Code.")
            return

        with st.spinner(f"Fetching details for {client_code}..."):
            try:
                # 1. Network Info
                net_info = get_network_details()

                # 2. API Call
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/client_master_report"
                payload = {
                    "client_code": client_code,
                    "from_date": "",
                    "to_date": ""
                }
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 3. Log to Google Sheet
                    log_to_google_sheet(client_code, data, net_info)

                    # 4. Process Data for Display
                    if data.get("report_data") and len(data["report_data"]) > 0:
                        record = data["report_data"][0] # Take the first record
                        
                        report_data = []
                        for key, value in record.items():
                            # FILTER LOGIC: Skip if value is None, "", or " "
                            if value is None: continue
                            if str(value).strip() == "": continue
                            
                            # Clean Key
                            clean_key = key.replace("_", " ").upper()
                            clean_value = str(value)
                            
                            report_data.append({"Field": clean_key, "Description": clean_value})
                        
                        st.success("Details Fetched Successfully")
                        df = pd.DataFrame(report_data)
                        st.dataframe(df, hide_index=True, use_container_width=True, height=600)
                    else:
                        st.warning("No data found for this Client Code.")
                        st.json(data) # Show raw if structure is unexpected
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
