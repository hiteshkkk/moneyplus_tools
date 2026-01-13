import streamlit as st
import requests
import gspread
from google.oauth2.service_account import Credentials
import datetime
# Ensure you have your utils import here if needed
# from nse_pages.utils import TABLE_STYLE, render_custom_table, get_network_details

# --- CONFIG ---
KYC_PRIORITY = ["PAN NO", "KYC STATUS", "KYC STATUS REMARK", "NAME"]

# CSS for the table (If you don't have it imported from utils)
TABLE_STYLE = """
<style>
    table {width: 100%; border-collapse: collapse;}
    th {background-color: #f0f2f6; color: #31333F; padding: 10px; font-weight: 600; text-align: left; border-bottom: 2px solid #e6e9ef;}
    td {padding: 8px; border-bottom: 1px solid #f0f2f6; color: #31333F;}
    tr:hover {background-color: #f9fafb;}
</style>
"""

# Helper to render table (If you don't have it imported)
def render_custom_table(data, priority_fields):
    html = "<table><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
    
    # Priority rows first
    for key in priority_fields:
        if key in data:
            html += f"<tr><td><strong>{key}</strong></td><td>{data[key]}</td></tr>"
    
    # Rest of the data
    for key, val in data.items():
        if key not in priority_fields:
            html += f"<tr><td>{key}</td><td>{val}</td></tr>"
            
    html += "</tbody></table>"
    return html

def get_network_details():
    # Placeholder if not imported
    return {"User_Public_IP": "Unknown", "Browser_Info": "Unknown"}

def log_to_google_sheet(pan, full_response_json, net_info):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet_id = "1BEwqqc8rDTSSyYiDwPbc06MCyQIBSNblppbzopS2Rqc" # KYC Sheet
        sheet = client.open_by_key(sheet_id).sheet1 
        
        api_text = str(full_response_json)
        net_text = f"User IP: {net_info.get('User_Public_IP')}\nBrowser: {net_info.get('Browser_Info')}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, pan, api_text, net_text])
    except Exception as e:
        print(f"Logging Error: {e}")

def render(token_headers):
    st.markdown("## 🔍 KYC Status Check")
    st.caption("Check KYC status using NSE Invest API (Secure)")
    
    # INJECT SHARED CSS
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)
    
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
                # If get_network_details is imported from utils, ensure the import is active at top
                net_info = get_network_details() 
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK"
                
                # 🚀 POSTMAN HEADERS
                postman_headers = {
                    "User-Agent": "PostmanRuntime/7.51.0",
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    "Origin": "https://www.nseinvest.com",
                    "Referer": "https://www.nseinvest.com/",
                }

                payload = {"pan_no": pan_number}
                
                response = requests.post(url, headers=postman_headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Request Successful")
                    
                    log_to_google_sheet(pan_number, data, net_info)
                    
                    html_table = render_custom_table(data, priority_fields=KYC_PRIORITY)
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    if "<HTML>" in response.text:
                        st.warning("Server blocked the request. The WAF detected the script.")
                    else:
                        st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
