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
                # API Endpoint from your curl command
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK"
                
                payload = {
                    "pan_no": pan_number
                }

                # Debug: Show what we are sending (Optional)
                # st.write("Headers being sent:", headers) 
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Display Result nicely
                    st.success("Request Successful")
                    st.json(data)
                    
                    # Optional: Show a friendly status badge if JSON structure is known
                    # if data.get("status") == "verified":
                    #     st.success("✅ KYC VERIFIED")
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
