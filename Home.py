import streamlit as st

# 1. Page Config
st.set_page_config(
    page_title="Moneyplus AI Suite",
    page_icon="💼",
    layout="centered"
)

# 2. Header & Logo
st.title("Welcome to Moneyplus AI Tools")
st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=150)

# 3. Menu Descriptions
st.markdown("""
### Select a tool from the sidebar to begin:

* **🏥 Discharge Auditor:** Analyze hospital discharge summaries for insurance claims.
* **📄 Meeting Notes Creator:** Convert raw notes into structured CRM records & Client WhatsApp updates.
* **📧 Email Generator:** (Coming Soon)

---
*System Status: Online | API: Connected*
""")
