import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION ---
# 🚨 PASTE YOUR GOOGLE SHEET URL BELOW 🚨
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZN7x6TgIU-zCT4ffV8ec9KFxztpSCSR-p83RWwW1zXA" 

# --- 2. HELPER: CONNECT TO GOOGLE SHEETS ---
@st.cache_resource
def get_gspread_client():
    """Authenticates using the same secrets as NSE tools."""
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Auth Error: {e}")
        return None

# --- 3. HELPER: LOAD MASTER DATA ---

@st.cache_data(ttl=600)
def load_master_data():
    client = get_gspread_client()
    if not client: return None, None
    
    try:
        sheet = client.open_by_url(SHEET_URL)
        
        # 1. Load Dropdowns (Assuming this still starts at Row 1?)
        # If Dropdowns ALSO start at Row 3, change the logic below to match Plans_Master
        ws_dropdowns = sheet.worksheet("Dropdown_Masters")
        raw_dropdowns = ws_dropdowns.get_all_values()
        if len(raw_dropdowns) > 1:
            df_dropdowns = pd.DataFrame(raw_dropdowns[1:], columns=raw_dropdowns[0])
        else:
            df_dropdowns = pd.DataFrame()

        # 2. Load Plans (STARTS AT ROW 3)
        ws_plans = sheet.worksheet("Plans_Master")
        raw_plans = ws_plans.get_all_values()
        
        # Ensure we have enough data (at least 3 rows)
        if len(raw_plans) > 3:
            # Row 3 (Index 2) contains the Headers
            headers = raw_plans[2] 
            
            # Row 4 (Index 3) onwards contains the Data
            data = raw_plans[3:]
            
            df_plans = pd.DataFrame(data, columns=headers)
        else:
            df_plans = pd.DataFrame() # Empty fallback
        
        return df_dropdowns, df_plans
        
    except Exception as e:
        st.error(f"❌ Unexpected Error: {e}")
        return None, None

# --- 4. MAIN APP UI ---
def main():
    st.title("📝 Health Insurance Quote Generator")

    if "YOUR_SHEET_ID_HERE" in SHEET_URL:
        st.warning("⚠️ Please update the `SHEET_URL` variable in the code with your actual Google Sheet Link.")
        return

    with st.spinner("Loading Master Data..."):
        df_masters, df_plans = load_master_data()

    if df_masters is not None and df_plans is not None:
        st.success("✅ Master Data Loaded Successfully")
        
        # --- DEBUG VIEW (Remove this later) ---
        with st.expander("🕵️ Debug: View Raw Data"):
            st.write("Dropdown Masters:", df_masters.head())
            st.write("Plans Master:", df_plans.head())

        # --- APP LOGIC GOES HERE ---
        # You can now use df_masters and df_plans to build your dropdowns
        # Example:
        # unique_companies = df_masters['Company_Name'].unique()
        # selected_company = st.selectbox("Select Company", unique_companies)

    else:
        st.error("Failed to load data. Please check the error messages above.")

if __name__ == "__main__":
    main()
