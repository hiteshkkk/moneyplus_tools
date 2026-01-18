import streamlit as st
import requests
import json
import datetime
# Import Shared CSS and Utils
from nse_pages.utils import TABLE_STYLE, format_html_value, get_network_details
# Import Local DB
from db import log_nse_event

# --- CONFIG ---
EXCLUDED_FIELDS = ["MEMBER NAME", "MEMBER CODE", "MEMBER ID"]

# --- HELPER: RENDER PIVOT TABLE ---
def render_pivot_table(records):
    """
    Standard renderer for NSE reports: Keys on Left, Values on Right.
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
    st.markdown("## 📈 SIP Registration Report")
    st.caption("Fetch active SIP/XSIP details for a client.")
    
    # Inject Shared CSS
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)

    with st.form("sip_report_form"):
        # Input for UCC
        col1, col2 = st.columns([2, 1])
        with col1:
            client_code = st.text_input("Enter Client UCC", placeholder="e.g. YH032").upper()
        with col2:
            st.write("") # Spacer to align button
            st.write("") 
            submitted = st.form_submit_button("Fetch Report", use_container_width=True)

    if submitted:
        if not client_code:
            st.warning("⚠️ Please enter a Client Code.")
            return

        # Prepare Payload (Based on your Curl)
        payload = {
            "xsip_reg_id": "",
            "client_code": client_code,
            "from_date": "",
            "to_date": ""
        }

        with st.spinner(f"Fetching SIP Report for {client_code}..."):
            try:
                # Capture Network Info
                net_info = get_network_details()
                
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/XSIP_REG_REPORT"
                
                # API Call
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    
                    # ✅ Log to SQLite
                    # Log Type="SIP_REPORT", Key=UCC, Payload=Request, Response=FullData
                    log_nse_event("SIP_REPORT", client_code, payload, data, net_info)
                    
                    records = data.get("report_data", [])

                    if not records:
                        st.warning("No SIP records found for this client.")
                        return

                    st.success(f"Found {len(records)} SIP Records")
                    
                    # Render Table
                    html_table = render_pivot_table(records)
                    st.markdown(html_table, unsafe_allow_html=True)

                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"Connection Error: {e}")
