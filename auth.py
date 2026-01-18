import streamlit as st

def check_password():
    """Returns `True` if the user had the correct password."""

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True 

    st.title("🔒 Login Required")
    st.markdown("Please enter the Moneyplus Admin Password to access these tools.") 
    
    # Use st.form to enable "Enter" to submit
    with st.form("login_form"):
        password = st.text_input("Enter Password", type="password")
        submit_button = st.form_submit_button("Login") 
        
        if submit_button:
            if password == st.secrets["APP_PASSWORD"]: 
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect Password") 

    st.stop() 
