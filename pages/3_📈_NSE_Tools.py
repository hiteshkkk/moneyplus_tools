import streamlit as st
import base64
import random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

# --- 1. SETUP PAGE & AUTH ---
st.set_page_config(page_title="NSE Tools Suite", page_icon="📈", layout="wide")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.warning("🔒 Please log in from the Home Page first.")
    st.stop()

check_password()

# --- 2. ENCRYPTION LOGIC (Shared) ---
def generate_encrypted_password(api_key, api_secret):
    separator = '|'
    random_number = str(int(random.random() * 10000000000) + 1)
    plain_text = api_secret + separator + random_number
    
    iv = get_random_bytes(16)
    salt = get_random_bytes(16)
    key = PBKDF2(api_key, salt, dkLen=16, count=1000)
    
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    ciphertext_bytes = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
    
    iv_hex = iv.hex()
    salt_hex = salt.hex()
    ciphertext_b64 = base64.b64encode(ciphertext_bytes).decode('utf-8')
    
    combined_string = f"{iv_hex}::{salt_hex}::{ciphertext_b64}"
    return base64.b64encode(combined_string.encode('utf-8')).decode('utf-8')

# --- 3. GENERATE HEADERS (ONCE) ---
if "nse_auth_headers" not in st.session_state:
    try:
        # Load Secrets
        api_key_member = st.secrets["NSE_API_KEY_MEMBER"]
        api_secret_user = st.secrets["NSE_API_SECRET_USER"]
        member_id = st.secrets["NSE_MEMBER_ID"]
        username = st.secrets["NSE_USERNAME"]

        # 1. Generate Encrypted Password
        encrypted_pwd = generate_encrypted_password(api_key_member, api_secret_user)

        # 2. Construct Basic Auth String: "username:encrypted_password"
        auth_string = f"{username}:{encrypted_pwd}"
        auth_base64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

        # 3. Store Final Headers in Session State
        st.session_state.nse_auth_headers = {
            'memberId': member_id,
            'Content-Type': 'application/json',
            'Authorization': f"Basic {auth_base64}",
            'User-Agent': 'PostmanRuntime/7.51.0', # Matching your screenshot
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        
    except Exception as e:
        st.error(f"Failed to generate secure headers: {e}")
        st.stop()

# ... (Previous imports and Auth logic remain the same) ...# ... (Keep existing imports and auth logic) ...

# --- 4. NAVIGATION SIDEBAR ---
tool_selection = st.sidebar.radio(
    "Select Tool:",
    ["KYC Check", "UCC Details", "Order Lifecycle Status", "Systematic Order Status"]  # <--- NEW ADDITION
)

# --- 5. LOAD MODULES ---
try:
    if tool_selection == "KYC Check":
        from nse_pages import kyc
        kyc.render(st.session_state.nse_auth_headers)
        
    elif tool_selection == "UCC Details":
        from nse_pages import ucc
        ucc.render(st.session_state.nse_auth_headers)
        
    elif tool_selection == "Order Lifecycle Status":
        from nse_pages import order_status
        order_status.render(st.session_state.nse_auth_headers)
        
    elif tool_selection == "Systematic Order Status":  # <--- NEW BLOCK
        from nse_pages import systematic_order
        systematic_order.render(st.session_state.nse_auth_headers)

except ImportError as e:
    st.error(f"⚠️ Error loading module: {e}")
except Exception as e:
    st.error(f"An error occurred: {e}")
