import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="Quote Generator", page_icon="📝", layout="wide")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.warning("🔒 Please log in from the Home Page first.")
    st.stop()

check_password()

# --- 2. CONNECT TO GOOGLE SHEETS ---
# Replace with your ACTUAL Sheet URL in secrets.toml or here
# We use the worksheet names you set up: Plans_Master, Dropdown_Masters, Generated_Quotes
conn = st.connection("gsheets", type=GSheetsConnection)

def get_initials(name):
    """Extracts initials for Quote ID (e.g. 'Hitesh Kakkad' -> 'HK')"""
    if not isinstance(name, str): return "MP"
    parts = name.strip().split()
    initials = "".join([p[0].upper() for p in parts if p])
    return initials if initials else "MP"

# --- 3. LOAD DATA ---
st.title("📝 Health Insurance Quote Generator")

try:
    with st.spinner("Loading Masters..."):
        # A. Load Dropdowns (Family & RM)
        # Assuming Family is Col A, RM is Col B in 'Dropdown_Masters'
        df_dropdowns = conn.read(worksheet="Dropdown_Masters", usecols=[0, 1])
        family_options = df_dropdowns.iloc[:, 0].dropna().unique().tolist()
        rm_options = df_dropdowns.iloc[:, 1].dropna().unique().tolist()

        # B. Load Plan Names from 'Plans_Master'
        # User said Plan Names are in Row 3 (Index 2). We read header=2.
        df_plans_header = conn.read(worksheet="Plans_Master", header=2, nrows=0)
        # Filter: Exclude 'Feature Code', 'Plan Name >>', and unnamed columns
        # Assuming Plan Names start from Column C (Index 2)
        raw_cols = df_plans_header.columns.tolist()
        plan_options = [c for c in raw_cols if "Unnamed" not in c and c not in ["Feature Code", "Plan Name >>"]]

except Exception as e:
    st.error(f"Error loading Master Data: {e}")
    st.info("Check if sheet tabs are named 'Dropdown_Masters' and 'Plans_Master'.")
    st.stop()

# --- 4. INPUT FORM ---
with st.form("quote_form"):
    st.subheader("Client Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        client_name = st.text_input("Client Name")
        city = st.text_input("City")
    with c2:
        rm_name = st.selectbox("RM Name", ["Select"] + rm_options)
        lead_id = st.text_input("Lead ID (CRM)")
    with c3:
        family = st.selectbox("Family Structure", ["Select"] + family_options)
        reference = st.text_input("Reference")

    st.markdown("---")
    st.subheader("Plan Selection")
    
    selected_plans = []
    
    # 5 Rows of Selection
    for i in range(1, 6):
        col_plan, col_prem, col_note = st.columns([2, 1, 1])
        with col_plan:
            # Searchable Dropdown
            p_name = st.selectbox(f"Plan {i}", ["None"] + plan_options, key=f"p{i}")
        with col_prem:
            p_prem = st.text_area(f"Premium {i}", height=68, placeholder="e.g. 1 Yr: 15k\n2 Yr: 28k", key=f"pr{i}")
        with col_note:
            p_note = st.text_area(f"Notes {i}", height=68, placeholder="Optional Notes", key=f"n{i}")
            
        if p_name != "None":
            selected_plans.append({"plan": p_name, "prem": p_prem, "note": p_note})

    submitted = st.form_submit_button("🚀 Generate Quote Link", type="primary")

# --- 5. SUBMISSION LOGIC ---
if submitted:
    if rm_name == "Select" or family == "Select" or not client_name:
        st.warning("⚠️ Client Name, RM Name, and Family Structure are required.")
    elif not selected_plans:
        st.warning("⚠️ Please select at least one plan.")
    else:
        with st.spinner("Generating Quote ID & Saving..."):
            try:
                # 1. Read existing quotes to get the running count
                try:
                    df_existing = conn.read(worksheet="Generated_Quotes")
                    # If sheet is empty, count is 0
                    current_count = len(df_existing) if not df_existing.empty else 0
                except:
                    df_existing = pd.DataFrame()
                    current_count = 0
                
                # 2. Generate Quote ID: RM + Date + RowNo (e.g., HK020126005)
                rm_initials = get_initials(rm_name)
                date_str = date.today().strftime("%d%m%y")
                row_no = f"{current_count + 1:03d}" # Pads with 0 (e.g. 005)
                quote_id = f"{rm_initials}{date_str}{row_no}"

                # 3. Prepare Data Row
                new_data = {
                    "Quote_ID": quote_id,
                    "Date": str(date.today()),
                    "Client_Name": client_name,
                    "City": city,
                    "RM_Name": rm_name,
                    "Lead_ID": lead_id,
                    "Family": family,
                    "Reference": reference,
                }
                
                # Fill Plan Data (up to 5)
                for i in range(5):
                    if i < len(selected_plans):
                        new_data[f"Plan_{i+1}"] = selected_plans[i]['plan']
                        new_data[f"Prem_{i+1}"] = selected_plans[i]['prem']
                        new_data[f"Note_{i+1}"] = selected_plans[i]['note']
                    else:
                        new_data[f"Plan_{i+1}"] = ""
                        new_data[f"Prem_{i+1}"] = ""
                        new_data[f"Note_{i+1}"] = ""

                # 4. Save to Sheet
                df_new_row = pd.DataFrame([new_data])
                df_updated = pd.concat([df_existing, df_new_row], ignore_index=True)
                conn.update(worksheet="Generated_Quotes", data=df_updated)

                # 5. Success Message & Link
                st.success(f"✅ Quote Saved! ID: {quote_id}")
                
                # Dynamic Link
                base_url = "https://moneyplus-tools.streamlit.app/View_Quote"
                # Use localhost for testing if running locally
                # base_url = "http://localhost:8501/View_Quote" 
                
                share_link = f"{base_url}?id={quote_id}"
                
                st.markdown("### 🔗 Share this link:")
                st.code(share_link, language="text")
                st.caption("Copy and send via WhatsApp/Email")

            except Exception as e:
                st.error(f"Error saving quote: {e}")
