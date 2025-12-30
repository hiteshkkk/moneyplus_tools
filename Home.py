import streamlit as st

# --- PASSWORD PROTECTION START ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    
    st.title("🔒 Moneyplus Login")
    pwd = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Wrong Password")
    st.stop()

check_password()

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
