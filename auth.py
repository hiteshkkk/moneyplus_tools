import streamlit as st

def check_password():
    """Returns `True` if the user had the correct password."""

    # 1. Initialize Session State
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # 2. Check if already logged in
    if st.session_state.authenticated:
        return True

    # 3. Show Login Form
    st.title("🔒 Login Required")
    st.markdown("Please enter the Moneyplus Admin Password to access these tools.")
    
    password = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()  # Refresh the app to load the actual content
        else:
            st.error("❌ Incorrect Password")

    # 4. Stop the App if not authenticated
    st.stop()  # This prevents the rest of the code on the page from running!
