import streamlit as st

st.set_page_config(
    page_title="Moneyplus AI Suite",
    page_icon="💼",
)

st.title("Welcome to Moneyplus AI Tools")
st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=150)

st.markdown("""
### Select a tool from the sidebar to begin:

* **🏥 Discharge Auditor:** Analyze hospital summaries for claims.
* **📄 Meeting Notes Creator.**
* **📧 Coming soon.**

*System Status: Online | API: Connected*
""")
