import streamlit as st
import requests
import json
import gspread
from google.oauth2.service_account import Credentials
import datetime
# Import Shared CSS and Utils
from nse_pages.utils import TABLE_STYLE, format_html_value

# --- CONFIG ---
EXCLUDED_FIELDS = ["MEMBER NAME", "MEMBER CODE", "MEMBER ID"]

# --- HELPER: LOG TO GOOGLE SHEET ---
def log_to_google_sheet(request_body, response_json):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Systematic Order Logs Sheet
        sheet_id = "1SZfVmIc1ruhJT4_6O2BUgf7nqK2VH7mJFA_FijtK9os"
        sheet = client.open_by_key(sheet_id).sheet1 
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body_str = json.dumps(request_body, indent=2)
        
        resp_str = json.dumps(response_json)
        if len(resp_str) > 500:
            resp_str = resp_str[:500] + "... [TRUNCATED]"
            
        sheet.append_row([timestamp, body_str, resp_str])
        
    except Exception as e:
        print(f"Logging Error: {e}")

# --- HELPER: RENDER PIVOT TABLE ---
def render_pivot_table(records):
    if not records:
        return "No Data"

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

    html = "<div style='overflow-x: auto;'><table class='custom-report'>"
    html += "<thead><tr><th class='field-label'>FIELD</th>"
    for i in range(len(records)):
        html += f"<th style='text-align: center; font-weight: 600; padding: 10px;'>RECORD {i+1}</th>"
    html += "</tr></thead><tbody>"

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

# --- HELPER: MAPPER FOR RE-ORDER ---
def prepare_reorder_payload(record):
    """
    Maps the Order Status Response fields to the Re-Order Request Body.
    Handles NRM vs SWH logic.
    """
    order_sub_type = record.get("order_sub_type", "NRM")
    
    # Common Helpers
    def get_val(k): return str(record.get(k, "")).strip()
    
    # Demat Mapper: PHYSICAL -> P, DEMAT -> D
    mode_raw = get_val("transaction_mode").upper()
    demat_val = "P" # Default
    if "DEMAT" in mode_raw: demat_val = "D"
    elif "CDSL" in mode_raw or "NSDL" in mode_raw: demat_val = "D"
    elif "PHYSICAL" in mode_raw: demat_val = "P"

    # --- SCENARIO 1: NORMAL ORDER (NRM) ---
    if order_sub_type == "NRM":
        # Handle Redemptions vs Purchase for Amounts/Units
        trxn_type = get_val("transaction_type") # P or R
        amount = get_val("amount")
        qty = get_val("quantity")
        
        redemption_units = ""
        order_amount = ""
        
        if trxn_type == "P":
            order_amount = amount
        else:
            # If Redemption, check if by amount or units
            if float(qty or 0) > 0:
                redemption_units = qty
            else:
                order_amount = amount

        payload = {
            "transaction_details": [{
                "order_ref_number": "", # Always blank for new order
                "scheme_code": get_val("scheme_code"),
                "trxn_type": trxn_type,
                "buy_sell_type": get_val("investment_type"), # FRESH / ADDITIONAL
                "client_code": get_val("client_code"),
                "demat_physical": demat_val,
                "order_amount": order_amount,
                "folio_no": get_val("folio_no"),
                "remarks": "MONEYPLUS TOOLS",
                "kyc_flag": get_val("kyc_declaration_flag"),
                "sub_broker_code": get_val("sub_broker_code"),
                "euin_number": get_val("euin_code"),
                "euin_declaration": get_val("euin_declaration_flag"),
                "min_redemption_flag": get_val("min_redemption_flag"),
                "dpc_flag": get_val("dpc_flag"),
                "all_units": get_val("all_units"),
                "redemption_units": redemption_units,
                "sub_broker_arn": get_val("sub_broker_arn_code"),
                "bank_ref_no": get_val("bank_ref_no"),
                "account_no": get_val("account_no"),
                "mobile_no": get_val("mobile_no"),
                "email": get_val("email"),
                "mandate_id": get_val("mandate_id")
            }]
        }
        return "NORMAL", payload

    # --- SCENARIO 2: SWITCH ORDER (SWH) ---
    elif order_sub_type == "SWH":
        payload = {
            "transaction_details": [{
                "order_ref_number": "",
                "from_scheme_code": get_val("scheme_code"),
                "to_scheme_code": get_val("to_scheme_code"), # WARNING: Might be missing in source
                "buy_sell_type": get_val("investment_type"),
                "client_code": get_val("client_code"),
                "demat_physical": "C" if demat_val == "D" else "P", # API docs often use 'C' for demat switch? Reverting to P/D logic usually safer unless specific req.
                "amount": get_val("amount"),
                "units": get_val("quantity"),
                "all_units": get_val("all_units"),
                "folio_no": get_val("folio_no"),
                "remarks": "MONEYPLUS TOOLS",
                "kyc_flag": get_val("kyc_declaration_flag"),
                "sub_broker_code": get_val("sub_broker_code"),
                "euin_number": get_val("euin_code"),
                "euin_declaration": get_val("euin_declaration_flag"),
                "sub_broker_arn": get_val("sub_broker_arn_code"),
                "mobile_no": get_val("mobile_no"),
                "email": get_val("email"),
                "filler1": "", "filler2": "", "filler3": ""
            }]
        }
        return "SWITCH", payload
    
    return None, None

# --- MAIN RENDER ---
def render(headers):
    st.markdown("## 📊 Systematic Order Status")
    st.caption("Check status by Order No OR Client Code (7-Day Range)")
    st.markdown(TABLE_STYLE, unsafe_allow_html=True)

    with st.form("sys_order_form"):
        c1, c2 = st.columns(2)
        with c1: order_no = st.text_input("Order No (Specific)")
        with c2: client_code = st.text_input("Client UCC").upper()

        c3, c4, c5 = st.columns(3)
        today = datetime.date.today()
        start_date = st.date_input("Start Date", today - datetime.timedelta(days=7))
        end_date = st.date_input("End Date", today - datetime.timedelta(days=1))
        
        with c5:
            st.write("") 
            st.write("") 
            submitted = st.form_submit_button("Fetch Status", use_container_width=True)

    if submitted:
        # Prepare Payload
        payload = {
            "from_date": "", "to_date": "",
            "trans_type": "ALL", "order_type": "ALL",
            "order_ids": "", "sub_order_type": "ALL", "client_code": ""
        }

        if order_no:
            payload["order_ids"] = order_no
        elif client_code:
            payload["client_code"] = client_code
            payload["from_date"] = start_date.strftime("%d-%m-%Y")
            payload["to_date"] = end_date.strftime("%d-%m-%Y")
        else:
            st.error("🚨 Please enter either an Order No OR a Client Code.")
            return

        with st.spinner("Fetching Systematic Status..."):
            try:
                url = "https://www.nseinvest.com/nsemfdesk/api/v2/reports/ORDER_STATUS"
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
                    
                    # --- REORDER SYSTEM ---
                    st.markdown("---")
                    st.subheader("🔄 Re-Order Action")
                    
                    # Dropdown to select record
                    record_options = {}
                    for i, rec in enumerate(records):
                        # Label: Record 1 | NRM | Scheme Name...
                        desc = f"Record {i+1} | {rec.get('order_sub_type','NRM')} | {rec.get('scheme_name','Unknown')[:30]}..."
                        record_options[desc] = rec

                    selected_desc = st.selectbox("Select Record to Re-Order", list(record_options.keys()))
                    
                    if st.button("🚀 Place Order Again"):
                        sel_rec = record_options[selected_desc]
                        
                        # 1. Map Data
                        txn_mode, reorder_payload = prepare_reorder_payload(sel_rec)
                        
                        if txn_mode:
                            reorder_url = f"https://www.nseinvest.com/nsemfdesk/api/v2/transaction/{txn_mode}"
                            
                            st.caption(f"Target URL: {reorder_url}")
                            # st.json(reorder_payload) # Debug: Show payload before sending
                            
                            # 2. Fire Request
                            with st.spinner(f"Placing {txn_mode} Order..."):
                                r2 = requests.post(reorder_url, headers=headers, json=reorder_payload)
                                
                                # 3. Log & Show Result
                                log_to_google_sheet(reorder_payload, r2.json() if r2.status_code == 200 else {"error": r2.text})
                                
                                if r2.status_code == 200:
                                    st.success("Order Placed Successfully!")
                                    st.json(r2.json())
                                else:
                                    st.error(f"Failed: {r2.status_code}")
                                    st.text(r2.text)
                        else:
                            st.error("Could not determine Transaction Mode (NRM/SWH)")

                else:
                    st.error(f"API Error: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"Connection Error: {e}")
