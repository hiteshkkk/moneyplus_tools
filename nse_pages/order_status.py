import streamlit as st
import requests
import json
import gspread
from google.oauth2.service_account import Credentials
import datetime
# Import Shared CSS and Network Utils
from nse_pages.utils import TABLE_STYLE, get_network_details, format_html_value

# --- CONFIG ---
ORDER_TYPES = [
    "Select Option", "PUR", "RED", "SWITCH", "SIP", "STP", "SWP", 
    "MANDATE", "SIP CANCEL", "XSIP CANCEL", "STP CANCEL", "SWP CANCEL"
]

EXCLUDED_FIELDS = ["MEMBER NAME", "MEMBER CODE"]

# --- HELPER: LOG TO NEW SHEET ---
def log_to_google_sheet(request_body, response_json):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet_id = "1f5rTXv9DiEpfbQke-1rHYIXjD5U0UX7U9A7Ypit0x58"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body_str = json.dumps(request_body, indent=2)
        
        resp_str = json.dumps(response_json)
        if len(resp_str) > 500:
            resp_str = resp_str[:500] + "... [TRUNCATED]"
            
        sheet.append_row([timestamp, body_str, resp_str])
        
    except Exception as e:
        print(f"Logging Error: {e}")

# --- HELPER: RENDER MULTI-COLUMN HTML TABLE ---
def render_pivot_table(records):
    """
    Renders a HTML table where Keys are the 1st Column and Records are subsequent columns.
    """
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
    st.markdown("## 📦 Order Lifecycle Status")
    st.caption("Check status by Order No OR Client Code (7-Day Range)")
    
    # Inject CSS from utils
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)

    with st.form("order_status_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            order_type_ui = st.selectbox("Order Type", ORDER_TYPES, index=0)
        with c2:
            order_no = st.text_input("Order No / Product ID")
        with c3:
            client_code = st.text_input("Client UCC")

        c4, c5, c6 = st.columns(3)
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=7)
        default_end = today - datetime.timedelta(days=1)
        
        with c4:
            start_date = st.date_input("Start Date", default_start)
        with c5:
            end_date = st.date_input("End Date", default_end)
        with c6:
            st.write("") 
            st.write("") 
            submitted = st.form_submit_button("Fetch Status", use_container_width=True)

    if submitted:
        final_order_type = "" if order_type_ui == "Select Option" else order_type_ui
        
        payload = {}
        if final_order_type and order_no:
            payload = {
                "from_date": "", "to_date": "",
                "Product_type": final_order_type, "product_id": order_no, "client_code": ""
            }
        elif client_code:
            payload = {
                "from_date": start_date.strftime("%d-%m-%Y"),
                "to_date": end_date.strftime("%d-%m-%Y"),
                "Product_type": "", "product_id": "", "client_code": client_code
            }
        else:
            st.error("🚨 Please enter (Order Type + No) OR (Client Code)")
            return

        with st.spinner("Fetching Order Lifecycle..."):
            try:
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/ORDER_LIFECYCLE"
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    log_to_google_sheet(payload, data)
                    
                    records = data.get("report_data", [])
                    if not records:
                        st.warning("No records found.")
                        return

                    st.success(f"Found {len(records)} Records")
                    
                    html_table = render_pivot_table(records)
                    st.markdown(html_table, unsafe_allow_html=True)

                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"Connection Error: {e}")
