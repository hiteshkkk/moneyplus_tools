import streamlit as st
import requests

def render(headers):
    st.markdown("## 🔍 KYC Status Check")
    st.caption("Check KYC status using NSE Invest API (Secure)")
    
    # Input Form
    with st.form("kyc_form"):
        pan_number = st.text_input("Enter PAN Number", placeholder="ABCDE1234F", max_chars=10).upper()
        submitted = st.form_submit_button("Check Status")
    
    if submitted:
        if not pan_number:
            st.warning("Please enter a PAN number.")
            return

        with st.spinner(f"Checking KYC for {pan_number}..."):
            try:
                # API Endpoint
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK"
                
                payload = {
                    "pan_no": pan_number
                }
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Request Successful")
                    
                    # --- DATA FORMATTING FOR REPORT ---
                    report_data = []
                    
                    # Loop through the raw JSON data
                    for key, value in data.items():
                        # 1. Clean Key: Remove underscores and make FULL CAPS
                        clean_key = key.replace("_", " ").upper()
                        
                        # 2. Clean Value: Ensure it's a clean string (removes None types)
                        clean_value = str(value) if value is not None else "N/A"
                        
                        # Add to our list
                        report_data.append({
                            "Field": clean_key, 
                            "Description": clean_value
                        })
                    
                    # --- DISPLAY AS TABLE ---
                    # st.table displays a static, clean table
                    st.table(report_data)
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
