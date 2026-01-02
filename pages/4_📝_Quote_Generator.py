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
@st.cache_data(ttl=600) # Cache data for 10 mins to speed up reloading
def load_master_data():
    client = get_gspread_client()
    if not client: return None, None
    
    try:
        # Open the Sheet
        sheet = client.open_by_url(SHEET_URL)
        
        # 1. Load Dropdowns
        ws_dropdowns = sheet.worksheet("Dropdown_Masters")
        data_dropdowns = ws_dropdowns.get_all_records()
        df_dropdowns = pd.DataFrame(data_dropdowns)
        
        # 2. Load Plans
        ws_plans = sheet.worksheet("Plans_Master")
        data_plans = ws_plans.get_all_records()
        df_plans = pd.DataFrame(data_plans)
        
        return df_dropdowns, df_plans
        
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ Error: Spreadsheet not found. Please check the URL.")
        return None, None
    except gspread.exceptions.WorksheetNotFound as e:
        st.error(f"❌ Error: Worksheet not found. Check if tabs named 'Dropdown_Masters' and 'Plans_Master' exist.\nDetails: {e}")
        return None, None
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
