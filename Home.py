import streamlit as st
# Import the centralized check_password function
from auth import check_password

# 1. Page Config (Must be the first Streamlit command)
st.set_page_config(
    page_title="Moneyplus AI Suite",
    page_icon="💼",
    layout="centered"
) 

# 2. Run Password Check (Centralized in auth.py)
check_password() 

# 3. Header & Logo
st.title("Welcome to Moneyplus AI Tools") 
st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=150) 

# 4. Menu Descriptions
st.markdown("""
### Select a tool from the sidebar to begin:

* **🏥 Discharge Auditor:** Analyze hospital discharge summaries for insurance claims.
* **📄 Meeting Notes Creator:** Convert raw notes into structured CRM records & Client WhatsApp updates.
* **📈 NSE Tools:** Secure access to KYC, UCC, and Order status.
* **📧 Email Generator:** (Coming Soon)

---
*System Status: Online | Database: SQLite (Fast)*
""") 
