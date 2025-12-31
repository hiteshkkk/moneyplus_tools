import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- HELPER: LOG RAW RESPONSE TO SHEET ---
def log_to_google_sheet(pan, full_response_json):
    """
    Appends a row: [Timestamp, PAN, Multi-line Raw Response]
    """
    try:
        # 1. Load Credentials
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        # 2. Open Sheet by ID
        sheet_id = "1BEwqqc8rDTSSyYiDwPbc06MCyQIBSNblppbzopS2Rqc"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        # 3. Format JSON into Multi-line String
        # Example format in cell:
        # pan_no: ABCDE1234F
        # kyc_status: Verified
        # ...
        formatted_text = ""
        for key, value in full_response_json.items():
            formatted_text += f"{key}: {value}\n"
            
        # 4. Append Row
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, pan, formatted_text])
        
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
                # API Call
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK"
                payload = {"pan_no": pan_number}
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Request Successful")
                    
                    # --- 1. LOG TO GOOGLE SHEET ---
                    # Now sending the FULL data object
                    log_to_google_sheet(pan_number, data)
                    
                    # --- 2. DISPLAY CLEAN TABLE ---
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
