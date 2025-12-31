import streamlit as st
import requests
import pandas as pd
import datetime
from nse_pages.utils import get_network_details

# --- CONFIG ---
ORDER_TYPES = [
    "NULL", "PUR", "RED", "SWITCH", "SIP", "STP", "SWP", 
    "MANDATE", "SIP CANCEL", "XSIP CANCEL", "STP CANCEL", "SWP CANCEL"
]

def render(headers):
    st.markdown("## 📦 Order Lifecycle Status")
    st.caption("Check status by Order No OR Client Code (7-Day Range)")

    # --- 1. UI LAYOUT (2 Rows, 3 Cols) ---
    with st.form("order_status_form"):
        # Row 1
        c1, c2, c3 = st.columns(3)
        with c1:
            order_type = st.selectbox("Order Type", ORDER_TYPES, index=0)
        with c2:
            order_no = st.text_input("Order No / Product ID")
        with c3:
            client_code = st.text_input("Client UCC")

        # Row 2 (Date Logic)
        c4, c5, c6 = st.columns(3)
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=7)
        default_end = today - datetime.timedelta(days=1)
        
        with c4:
            start_date = st.date_input("Start Date", default_start)
        with c5:
            end_date = st.date_input("End Date", default_end)
        with c6:
            st.write("") # Spacer
            st.write("") # Spacer
            submitted = st.form_submit_button("Fetch Status", use_container_width=True)

    # --- 2. LOGIC HANDLER ---
    if submitted:
        # Scenario A: Order Type + Order No
        if order_type != "NULL" and order_no:
            payload = {
                "from_date": "",
                "to_date": "",
                "Product_type": order_type,
                "product_id": order_no,
                "client_code": ""
            }
            st.info(f"Fetching by Order No: {order_no}")

        # Scenario B: Client Code (Date Range)
        elif client_code:
            # Validate Date Gap (Optional enforcement, but usually good API practice)
            days_diff = (end_date - start_date).days
            if days_diff > 7:
                st.warning("⚠️ Note: Date range is larger than 7 days. API might reject or be slow.")
            
            payload = {
                "from_date": start_date.strftime("%d-%m-%Y"),
                "to_date": end_date.strftime("%d-%m-%Y"),
                "Product_type": "",
                "product_id": "",
                "client_code": client_code
            }
            st.info(f"Fetching for Client {client_code} ({payload['from_date']} to {payload['to_date']})")

        else:
            st.error("🚨 Invalid Input: Please provide either (Order Type + Order No) OR (Client UCC)")
            return

        # --- 3. API CALL ---
        with st.spinner("Fetching Order Lifecycle..."):
            try:
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/ORDER_LIFECYCLE"
                
                # Add the specific cookie mentioned in curl if needed, 
                # but usually 'nse_auth_headers' handles the critical Auth.
                # If cookie is dynamic/required, we might need to add it to headers passed in.
                
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    records = data.get("report_data", [])

                    if not records:
                        st.warning("No records found.")
                        st.json(data)
                        return

                    st.success(f"Found {len(records)} Records")

                    # --- 4. DATA TRANSFORMATION (PIVOT) ---
                    # Goal: Rows = Keys, Cols = Record 1, Record 2...
                    
                    # A. Collect all unique keys that have data
                    all_keys = []
                    # We scan the first record to get the order of keys (to keep it logical)
                    # Then scan others just in case they have extra keys
                    if len(records) > 0:
                        all_keys = list(records[0].keys())

                    # B. Filter Keys: Remove if ALL records are blank/empty for this key
                    valid_keys = []
                    for key in all_keys:
                        is_empty_everywhere = True
                        for rec in records:
                            val = str(rec.get(key, "")).strip()
                            if val and val != "None":
                                is_empty_everywhere = False
                                break
                        if not is_empty_everywhere:
                            valid_keys.append(key)

                    # C. Build the Table Data
                    # { "Field": ["Name", "Amount"], "Rec 1": ["Hitesh", "5000"], "Rec 2": ["Ramesh", "4000"] }
                    table_data = {"Field": [k.replace("_", " ").upper() for k in valid_keys]}
                    
                    for i, rec in enumerate(records):
                        col_name = f"Record {i+1}"
                        col_values = []
                        for key in valid_keys:
                            val = str(rec.get(key, ""))
                            if val == "None": val = ""
                            col_values.append(val)
                        table_data[col_name] = col_values

                    # D. Create DataFrame
                    df = pd.DataFrame(table_data)
                    
                    # E. Display
                    st.dataframe(
                        df, 
                        hide_index=True, 
                        use_container_width=True, 
                        height=600,
                        column_config={
                            "Field": st.column_config.TextColumn("Field", width="medium", help="Field Name"),
                        }
                    )

                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"Connection Error: {e}")
