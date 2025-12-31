import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- HELPER: LOG TO YOUR SPECIFIC SHEET ---
def log_to_google_sheet(pan, status, remark):
    """Appends a row to the specific Google Sheet provided."""
    try:
        # 1. Load Credentials
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        # 2. Open Sheet by ID (Extracted from your URL)
        # URL: https://docs.google.com/spreadsheets/d/1BEwqqc8rDTSSyYiDwPbc06MCyQIBSNblppbzopS2Rqc/...
        sheet_id = "1BEwqqc8rDTSSyYiDwPbc06MCyQIBSNblppbzopS2Rqc"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        # 3. Append Row [Timestamp, PAN, Status, Remark]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, pan, status, remark])
        
    except Exception as e:
        # We print to console instead of UI so it doesn't disturb the user
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
                    
                    # --- 1. LOG TO GOOGLE SHEET (Background Action) ---
                    # We extract specific fields for the log
                    kyc_status = str(data.get("kyc_status", "N/A"))
                    kyc_remark = str(data.get("kyc_status_remark", "N/A"))
                    
                    log_to_google_sheet(pan_number, kyc_status, kyc_remark)
                    
                    # --- 2. DISPLAY TABLE ---
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
