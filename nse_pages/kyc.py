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
                # If get_network_details is not imported, comment this line out
                try: net_info = get_network_details()
                except: net_info = {"User_Public_IP": "Unknown"}

                url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK"
                
                # 🚀 REAL CHROME BROWSER HEADERS (The "Nuclear" Option)
                # This mimics a standard Chrome browser on Windows perfectly.
                chrome_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Content-Type": "application/json",
                    "Origin": "https://www.nseinvest.com",
                    "Referer": "https://www.nseinvest.com/",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "Connection": "keep-alive"
                }

                payload = {"pan_no": pan_number}
                
                # ⚠️ TIMEOUT ADDED: Sometimes WAFs delay responses to annoy bots
                response = requests.post(url, headers=chrome_headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Request Successful")
                    
                    log_to_google_sheet(pan_number, data, net_info)
                    
                    html_table = render_custom_table(data, priority_fields=KYC_PRIORITY)
                    st.markdown(html_table, unsafe_allow_html=True)
                    
                else:
                    st.error(f"API Error: {response.status_code}")
                    if response.status_code == 403:
                        st.error("🚫 Blocked by NSE Security. Try checking from a different network (e.g., mobile hotspot) as your current IP might be flagged.")
                    else:
                        st.text(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {e}")
