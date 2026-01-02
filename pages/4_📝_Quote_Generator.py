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
        
        # 1. Load Dropdowns (Standard Read)
        ws_dropdowns = sheet.worksheet("Dropdown_Masters")
        raw_dropdowns = ws_dropdowns.get_all_values()
        if len(raw_dropdowns) > 1:
            df_dropdowns = pd.DataFrame(raw_dropdowns[1:], columns=raw_dropdowns[0])
        else:
            df_dropdowns = pd.DataFrame()

        # 2. Load Plans (STARTS AT ROW 3 based on your screenshot)
        ws_plans = sheet.worksheet("Plans_Master")
        raw_plans = ws_plans.get_all_values()
        
        if len(raw_plans) > 3:
            # Row 3 (Index 2) contains Headers like "Feature Code", "Plan Name >>", "Niva Bupa..."
            headers = raw_plans[2] 
            data = raw_plans[3:] # Data starts from Row 4
            df_plans = pd.DataFrame(data, columns=headers)
        else:
            df_plans = pd.DataFrame() 
        
        return df_dropdowns, df_plans
        
    except Exception as e:
        st.error(f"❌ Error Loading Data: {e}")
        return None, None

# --- 4. MAIN APP UI ---
def main():
    st.set_page_config(page_title="Quote Generator", page_icon="📝", layout="wide")
    st.title("📝 Health Insurance Quote Generator")

    # A. Check URL
    if "YOUR_FULL_URL_HERE" in SHEET_URL:
        st.warning("⚠️ Please update the `SHEET_URL` in the code with your actual Google Sheet Link.")
        return

    # B. Load Data
    with st.spinner("Syncing with Master Sheet..."):
        df_masters, df_plans = load_master_data()

    if df_masters is not None and not df_plans.empty:
        
        # --- SECTION 1: INPUT FORM ---
        with st.container():
            st.subheader("1. Client Details")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                # Get RM Names, filter out empty rows
                rm_list = [x for x in df_masters['RM Names'].unique() if x]
                st.selectbox("Relationship Manager (RM)", rm_list)
                
            with c2:
                st.text_input("Client Name")
                
            with c3:
                # Get Family Structure
                fam_list = [x for x in df_masters['Family Structure'].unique() if x]
                st.selectbox("Family Structure", fam_list)

        st.divider()

        # --- SECTION 2: PLAN COMPARISON ---
        st.subheader("2. Compare Plans")
        
        # Identify Plan Columns: All columns AFTER "Plan Name >>"
        # Based on screenshot, col 0 is Code, col 1 is Feature Name.
        # So actual plans start from column index 2.
        all_columns = list(df_plans.columns)
        
        # Safety check to ensure we have columns
        if len(all_columns) > 2:
            plan_options = all_columns[2:] # ["Niva Bupa...", "HDFC...", etc.]
            
            selected_plans = st.multiselect(
                "Select Plans to Compare:", 
                options=plan_options,
                default=[plan_options[0]] if plan_options else None
            )
            
            if selected_plans:
                # Filter Dataframe: Keep 'Plan Name >>' (Feature) + Selected Plans
                cols_to_show = [all_columns[1]] + selected_plans
                compare_df = df_plans[cols_to_show].copy()
                
                # Rename the feature column for display
                compare_df.rename(columns={all_columns[1]: "Feature"}, inplace=True)
                
                st.write("") # Spacer
                st.markdown("### 🔍 Feature Comparison")
                
                # Display Interactive Table
                st.dataframe(
                    compare_df,
                    hide_index=True,
                    use_container_width=True,
                    height=600
                )
            else:
                st.info("👈 Please select at least one plan to view features.")
        else:
            st.error("⚠️ Could not detect plan columns. Check 'Plans_Master' headers in Row 3.")

    else:
        st.error("❌ Failed to load valid data. Please check the sheet format.")

if __name__ == "__main__":
    main()
