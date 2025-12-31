import streamlit as st
import requests
import json
import gspread
from google.oauth2.service_account import Credentials
import datetime
# Import Shared CSS and Utils
from nse_pages.utils import TABLE_STYLE, format_html_value

# --- CONFIG ---
EXCLUDED_FIELDS = ["MEMBER NAME", "MEMBER CODE", "MEMBER ID"]

# --- HELPER: LOG TO GOOGLE SHEET ---
def log_to_google_sheet(request_body, response_json):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Mandate Status Sheet
        sheet_id = "1nodEv0nz4A9XnfyEv7-_aBHHMLY6TiVjriBh0d299Xg"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body_str = json.dumps(request_body, indent=2)
        
        resp_str = json.dumps(response_json)
        if len(resp_str) > 500:
            resp_str = resp_str[:500] + "... [TRUNCATED]"
            
        sheet.append_row([timestamp, body_str, resp_str])
        
    except Exception as e:
        print(f"Logging Error: {e}")

# --- HELPER: RENDER PIVOT TABLE ---
def render_pivot_table(records):
    if not records:
        return "No Data"

    # 1. Collect Valid Keys
    all_keys = list(records[0].keys())
    valid_keys = []
    
    for key in all_keys:
        clean_key = key.replace("_", " ").upper()
        if clean_key in EXCLUDED_FIELDS:
            continue
        has_data = False
        for rec in records:
            if str(rec.get(key, "")).strip() not in ["", "None"]:
                has_data = True
                break
        if has_data:
            valid_keys.append(key)

    # 2. Build HTML Header
    html = "<div style='overflow-x: auto;'><table class='custom-report'>"
    html += "<thead><tr><th class='field-label'>FIELD</th>"
    
    for i in range(len(records)):
        html += f"<th style='text-align: center; font-weight: 600; padding: 10px;'>RECORD {i+1}</th>"
    html += "</tr></thead><tbody>"

    # 3. Build Data Rows
    for key in valid_keys:
        clean_key = key.replace("_", " ").upper()
        html += f"<tr><td class='field-label'>{clean_key}</td>"
        
        for rec in records:
            val = rec.get(key, "")
            fmt_val = format_html_value(val)
            html += f"<td class='field-value' style='text-align: center;'>{fmt_val}</td>"
        
        html += "</tr>"
    
    html += "</tbody></table></div>"
    return html

# --- MAIN RENDER ---
def render(headers):
    st.markdown("## 📜 NSE Mandate Status")
    st.caption("Check Mandate Status (Details)")
    
    # Inject Shared CSS
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)

    with st.form("mandate_status_form"):
        c1, c2 = st.columns(2)
        with c1:
            mandate_id = st.text_input("Mandate ID").upper()
        with c2:
            client_code = st.text_input("Client UCC").upper()

        st.write("") # Spacer
        submitted = st.form_submit_button("Fetch Status", use_container_width=True)

    if submitted:
        # Validation
        if not mandate_id and not client_code:
            st.error("🚨 Please enter at least one field (Mandate ID or Client UCC)")
            return

        # Prepare Payload
        payload = {
            "from_date": "",
            "to_date": "",
            "client_code": client_code if client_code else "",
            "mandate_id": mandate_id if mandate_id else ""
        }

        with st.spinner("Fetching Mandate Details..."):
            try:
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/MANDATE_STATUS"
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    
                    # Log to Google Sheet
                    log_to_google_sheet(payload, data)
                    
                    records = data.get("report_data", [])

                    if not records:
                        st.warning("No records found.")
                        return

                    st.success(f"Found {len(records)} Records")
                    
                    # Render Table (Pivot)
                    html_table = render_pivot_table(records)
                    st.markdown(html_table, unsafe_allow_html=True)

                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"Connection Error: {e}")
