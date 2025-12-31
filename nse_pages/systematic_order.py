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
# Using the same sheet as Order Status since the data is similar
def log_to_google_sheet(request_body, response_json):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Sheet ID: Order Status Logs
        sheet_id = "1SZfVmIc1ruhJT4_6O2BUgf7nqK2VH7mJFA_FijtK9os"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body_str = json.dumps(request_body, indent=2)
        
        resp_str = json.dumps(response_json)
        if len(resp_str) > 500:
            resp_str = resp_str[:500] + "... [TRUNCATED]"
            
        sheet.append_row([timestamp, body_str, resp_str])
        
    except Exception as e:
        print(f"Logging Error: {e}")

# --- HELPER: RENDER PIVOT TABLE (Reused Logic) ---
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
    st.markdown("## 📊 Systematic Order Status")
    st.caption("Check status by Order No OR Client Code (7-Day Range)")
    
    # Inject Shared CSS
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)

    # --- FORM UI ---
    with st.form("sys_order_form"):
        # Row 1: Inputs
        c1, c2 = st.columns(2)
        with c1:
            order_no = st.text_input("Order No (Specific)")
        with c2:
            client_code = st.text_input("Client UCC").upper()

        # Row 2: Dates & Submit
        c3, c4, c5 = st.columns(3)
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=7)
        default_end = today - datetime.timedelta(days=1)
        
        with c3:
            start_date = st.date_input("Start Date", default_start)
        with c4:
            end_date = st.date_input("End Date", default_end)
        with c5:
            st.write("") 
            st.write("") 
            submitted = st.form_submit_button("Fetch Status", use_container_width=True)

    # --- LOGIC HANDLER ---
    if submitted:
        # Base Payload Defaults
        payload = {
            "from_date": "",
            "to_date": "",
            "trans_type": "ALL",
            "order_type": "ALL",
            "order_ids": "",
            "sub_order_type": "ALL",
            "client_code": ""
        }

        # Logic A: If Order No is present, clear everything else
        if order_no:
            payload["order_ids"] = order_no
            # Dates and Client Code remain blank ("")
        
        # Logic B: If Client Code is present (and No Order No)
        elif client_code:
            payload["client_code"] = client_code
            payload["from_date"] = start_date.strftime("%d-%m-%Y")
            payload["to_date"] = end_date.strftime("%d-%m-%Y")
        
        else:
            st.error("🚨 Please enter either an Order No OR a Client Code.")
            return

        # --- API CALL ---
        with st.spinner("Fetching Systematic Status..."):
            try:
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/ORDER_STATUS"
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    
                    # Log Request/Response
                    log_to_google_sheet(payload, data)
                    
                    records = data.get("report_data", [])
                    if not records:
                        st.warning("No records found.")
                        return

                    st.success(f"Found {len(records)} Records")
                    
                    # Render Table
                    html_table = render_pivot_table(records)
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                    # Placeholder for Reorder System (To be added later)
                    # st.subheader("🔄 Actions")
                    # ...

                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"Connection Error: {e}")
