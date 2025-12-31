import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
from streamlit.web.server.websocket_headers import _get_websocket_headers

# --- CONSTANTS: PRIORITY SORT ORDER ---
# These fields will always appear at the top in this specific order
PRIORITY_FIELDS = [
    "CLIENT CODE",
    "PRIMARY HOLDER FIRST NAME", 
    "PRIMARY HOLDER PAN",
    "HOLDING NATURE",
    "TAX STATUS",
    "INDIAN MOBILE NO",      # Adjusted based on your sample JSON key
    "EMAIL",                 # Adjusted based on your sample JSON key
    "BANK 1 STATUS",
    "BANK 1 STATUS REMARKS"
]

# --- CONSTANTS: COLOR LOGIC ---
def get_color(val):
    """
    Returns CSS background color string based on value keywords.
    """
    if not isinstance(val, str):
        return ""
    
    val_lower = val.lower()
    
    # GREEN: Success / Active / Approved
    if any(x in val_lower for x in ['success', 'active', 'approved', 'svalid', 'done', 'yes']):
        return 'background-color: #d4edda; color: #155724' # Light Green BG, Dark Green Text
        
    # ORANGE: Pending / Wait
    if any(x in val_lower for x in ['pending', 'wait']):
        return 'background-color: #fff3cd; color: #856404' # Light Yellow BG, Dark Yellow Text
        
    # RED: Fail / Reject / Error / Invalid
    if any(x in val_lower for x in ['fail', 'reject', 'error', 'differs', 'invalid', 'insufficient', 'no']):
        return 'background-color: #f8d7da; color: #721c24' # Light Red BG, Dark Red Text
        
    return "" # Default (No Color)

# --- HELPER: GET NETWORK DETAILS ---
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

# --- HELPER: LOG TO SHEET ---
def log_to_google_sheet(client_code, full_response_json, net_info):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        # Sheet ID for UCC
        sheet_id = "1PI-BfizbrzMftNm69WxZ-YEnviA4aqeSjf4r4DZA4bw"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        api_text = str(full_response_json)
        net_text = (
            f"User IP: {net_info.get('User_Public_IP')}\n"
            f"Browser: {net_info.get('Browser_Info')}\n"
            f"Server IP: {net_info.get('Streamlit_Server_IP')}"
        )

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

                    # 4. Process Data
                    if data.get("report_data") and len(data["report_data"]) > 0:
                        record = data["report_data"][0]
                        
                        # --- A. CLEAN AND FILTER DATA ---
                        cleaned_dict = {}
                        for key, value in record.items():
                            if value is None: continue
                            if str(value).strip() == "": continue
                            
                            clean_key = key.replace("_", " ").upper()
                            cleaned_dict[clean_key] = str(value)
                        
                        # --- B. APPLY SORTING LOGIC ---
                        final_rows = []
                        
                        # 1. Add Priority Fields first (if they exist in data)
                        for field in PRIORITY_FIELDS:
                            if field in cleaned_dict:
                                final_rows.append({"Field": field, "Description": cleaned_dict[field]})
                                del cleaned_dict[field] # Remove so we don't add it again
                        
                        # 2. Add Remaining fields (Optional: Sort them alphabetically)
                        remaining_fields = sorted(cleaned_dict.keys())
                        for field in remaining_fields:
                            final_rows.append({"Field": field, "Description": cleaned_dict[field]})
                            
                        # --- C. CREATE DATAFRAME ---
                        df = pd.DataFrame(final_rows)
                        
                        # --- D. APPLY COLOR STYLING ---
                        # We apply the 'get_color' function to the 'Description' column
                        styled_df = df.style.map(get_color, subset=['Description'])

                        st.success("Details Fetched Successfully")
                        
                        # Display the Styled Dataframe
                        st.dataframe(
                            styled_df, 
                            hide_index=True, 
                            use_container_width=True, 
                            height=600,
                            column_config={
                                "Field": st.column_config.TextColumn("Field", width="medium"),
                                "Description": st.column_config.TextColumn("Description", width="large")
                            }
                        )
                    else:
                        st.warning("No data found for this Client Code.")
                        st.json(data)
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
