def render(token_headers):
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
                
                # ---------------------------------------------------------
                # 🚀 HEADERS: Mimicking Postman
                # ---------------------------------------------------------
                postman_headers = {
                    "User-Agent": "PostmanRuntime/7.51.0",
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Content-Type": "application/json",
                    # We still include Origin/Referer because the server likely checks these
                    # regardless of the User-Agent to prevent CSRF attacks.
                    "Origin": "https://www.nseinvest.com",
                    "Referer": "https://www.nseinvest.com/",
                }

                payload = {"pan_no": pan_number}
                
                # Use postman_headers here
                response = requests.post(url, headers=postman_headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Request Successful")
                    
                    log_to_google_sheet(pan_number, data, net_info)
                    
                    # --- USE SHARED RENDERER ---
                    html_table = render_custom_table(data, priority_fields=KYC_PRIORITY)
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    if "<HTML>" in response.text:
                        st.warning("Server blocked the request. The WAF detected the script.")
                    else:
                        st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
