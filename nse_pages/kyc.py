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
    
    # 1. Get Streamlit Server Public IP (The machine running the code)
    try:
        details['Streamlit_Server_IP'] = requests.get('https://api.ipify.org').text
    except:
        details['Streamlit_Server_IP'] = "Unknown"

    # 2. Get User Info from Headers (Best effort for Streamlit Cloud)
    try:
        headers = _get_websocket_headers()
        if headers:
            # X-Forwarded-For usually contains the real User IP on Cloud
            details['User_Public_IP'] = headers.get("X-Forwarded-For", "Hidden/Localhost")
            details['Browser_Info'] = headers.get("User-Agent", "Unknown")
        else:
            details['User_Public_IP'] = "Localhost/Unknown"
            details['Browser_Info'] = "Unknown"
    except:
        details['User_Public_IP'] = "Error Fetching"
        details['Browser_Info'] = "Error Fetching"
        
    return details

# --- HELPER: LOG TO GOOGLE SHEET ---
def log_to_google_sheet(pan, full_response_json, net_info):
    """
    Appends a row: 
    [Timestamp, PAN, Raw API Response, Network Details]
    """
    try:
        # 1. Load Credentials
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        # 2. Open Sheet
        sheet_id = "1BEwqqc8rDTSSyYiDwPbc06MCyQIBSNblppbzopS2Rqc"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        # 3. Format Raw API Response (Col C)
        api_text = ""
        for key, value in full_response_json.items():
            api_text += f"{key}: {value}\n"
            
        # 4. Format Network Details (Col D) - Multiline with Labels
        net_text = (
            f"User Public IP: {net_info.get('User_Public_IP')}\n"
            f"Browser: {net_info.get('Browser_Info')}\n"
            f"Streamlit Server IP: {net_info.get('Streamlit_Server_IP')}"
        )

        # 5. Append Row
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, pan, api_text, net_text])
        
    except Exception as e:
        print(f"Logging Error: {e}")

# --- MAIN RENDER FUNCTION ---
def render(headers):
    st.markdown("## 🔍 KYC Status Check")
    st.caption("Check KYC status using NSE Invest API (Secure)")
    
    with st.form("kyc_form"):
        pan_input = st.text_input("Enter PAN Number", placeholder="ABCDE1234F", max_chars=10)
        pan_number = pan_input.upper() if pan_input else ""
        submitted = st.form_submit_button("Check Status")
    
    if submitted:
        if not pan_number:
            st.warning("Please enter a PAN number.")
            return

        with st.spinner(f"Checking KYC for {pan_number}..."):
            try:
                # 1. Fetch Network Details immediately (before API call)
                net_info = get_network_details()

                # 2. API Call
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK"
                payload = {"pan_no": pan_number}
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Request Successful")
                    
                    # 3. Log to Google Sheet (Background)
                    log_to_google_sheet(pan_number, data, net_info)
                    
                    # 4. Display Table
                    report_data = []
                    for key, value in data.items():
                        clean_key = key.replace("_", " ").upper()
                        clean_value = str(value) if value is not None else "N/A"
                        report_data.append({"Field": clean_key, "Description": clean_value})
                    
                    df = pd.DataFrame(report_data)
                    st.dataframe(df, hide_index=True, use_container_width=True, height=400)
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
