import streamlit as st
import pandas as pd
from db import get_table_data, get_connection
from auth import check_password

# Set page config
st.set_page_config(page_title="Moneyplus Admin", page_icon="🔐", layout="wide")

# Force login
check_password()

st.title("🔐 Moneyplus Admin Panel")
st.markdown("Use this panel to verify data stored in the local SQLite database.")

# Select which table to view
table_option = st.selectbox(
    "Select Table to View",
    ["meeting_notes", "quotes", "nse_logs","discharge_audits"]
)

if st.button("🔄 Refresh Data"):
    try:
        # Fetch data using the helper from your db.py
        df = get_table_data(table_option)
        
        if df.empty:
            st.warning(f"No records found in the '{table_option}' table.")
        else:
            st.success(f"Showing {len(df)} records from {table_option}")
            
            # Display the data
            st.dataframe(df, use_container_width=True)
            
            # Download as CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"{table_option}_export.csv",
                mime='text/csv',
            )
    except Exception as e:
        st.error(f"Error reading database: {e}")

st.divider()
st.caption("System Status: SQLite Connected | Admin Mode")
