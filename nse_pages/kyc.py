import streamlit as st
import requests
import pandas as pd  # Import pandas for the clean table

def render(headers):
    st.markdown("## 🔍 KYC Status Check")
    st.caption("Check KYC status using NSE Invest API (Secure)")
    
    # Input Form
    with st.form("kyc_form"):
        # 1. FORCE UPPERCASE: .upper() here ensures we always send capital letters
        pan_input = st.text_input("Enter PAN Number", placeholder="ABCDE1234F", max_chars=10)
        pan_number = pan_input.upper() if pan_input else ""
        
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
                    
                    # --- DATA FORMATTING ---
                    report_data = []
                    
                    for key, value in data.items():
                        clean_key = key.replace("_", " ").upper()
                        clean_value = str(value) if value is not None else "N/A"
                        
                        report_data.append({
                            "Field": clean_key, 
                            "Description": clean_value
                        })
                    
                    # --- DISPLAY AS FULL-WIDTH CLEAN TABLE ---
                    # Convert list to Pandas DataFrame
                    df = pd.DataFrame(report_data)
                    
                    # Display with specific options:
                    # 1. hide_index=True -> Removes the 0, 1, 2 column
                    # 2. use_container_width=True -> Stretches table to fit screen
                    st.dataframe(
                        df, 
                        hide_index=True, 
                        use_container_width=True,
                        height=400  # Optional: Fixed height if list is long
                    )
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
