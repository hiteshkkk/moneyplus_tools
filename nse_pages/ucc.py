import streamlit as st
import requests
import datetime
# IMPORT UTILS
from nse_pages.utils import TABLE_STYLE, render_custom_table, get_network_details
# IMPORT LOCAL DB
from db import log_nse_event

# --- CONFIG ---
UCC_PRIORITY = [
    "CLIENT CODE", "PRIMARY HOLDER NAME", "PRIMARY HOLDER PAN", "GUARDIAN NAME", "UCC STATUS",
    "AUTH STATUS", "BANK1 STATUS", "BANK1 REJECTION REMARKS", "HOLDING NATURE", 
]

def render(headers):
    st.markdown("## 📋 NSE UCC Details")
    st.caption("Fetch Client Master Report (UCC) details securely.")
    
    # INJECT SHARED CSS
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)
    
    with st.form("ucc_form"):
        client_code_input = st.text_input("Enter Client Code", placeholder="e.g. YH032")
        client_code = client_code_input.upper() if client_code_input else ""
        submitted = st.form_submit_button("Fetch Details")
    
    if submitted:
        if not client_code:
            st.warning("Please enter a Client Code.")
            return

        with st.spinner(f"Fetching details for {client_code}..."):
            try:
                net_info = get_network_details()
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/client_detail_report"
                
                # Payload defined explicitly so we can log it
                payload = { "client_code": client_code, "from_date": "", "to_date": "" }
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # --- REPLACED GOOGLE SHEET LOGGING WITH SQLITE ---
                    # Logs: Type="UCC", Key=ClientCode, Payload={...}, Response={...}
                    log_nse_event("UCC", client_code, payload, data, net_info)

                    if data.get("report_data") and len(data["report_data"]) > 0:
                        record = data["report_data"][0]
                        
                        st.success("Details Fetched Successfully")
                        
                        # --- USE SHARED RENDERER ---
                        html_table = render_custom_table(record, priority_fields=UCC_PRIORITY)
                        st.markdown(html_table, unsafe_allow_html=True)
                        
                    else:
                        st.warning("No data found for this Client Code.")
                        st.json(data)
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
