import streamlit as st
import requests
import datetime
# IMPORT UTILS
from nse_pages.utils import TABLE_STYLE, render_custom_table, get_network_details
# IMPORT LOCAL DB
from db import log_nse_event

# --- CONFIG ---
KYC_PRIORITY = ["PAN NO", "KYC STATUS", "KYC STATUS REMARK", "NAME"]

def render(headers):
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
                net_info = get_network_details()
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK"
                # Defined payload here so we can log it later
                payload = {"pan_no": pan_number}
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Request Successful")
                    
                    # --- REPLACED GOOGLE SHEET LOGGING WITH SQLITE ---
                    # Logs: Type="KYC", Key=PAN, Payload={...}, Response={...}, NetInfo={...}
                    log_nse_event("KYC", pan_number, payload, data, net_info)
                    
                    # --- USE SHARED RENDERER ---
                    html_table = render_custom_table(data, priority_fields=KYC_PRIORITY)
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                else:
                    # Optional: You can also log failures if you wish
                    # log_nse_event("KYC_FAIL", pan_number, payload, {"error": response.text}, net_info)
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
