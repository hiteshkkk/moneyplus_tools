import streamlit as st
import google.generativeai as genai
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
MEETING_SHEET_ID = "113g598FEs7DxZYlBVAP1iHYqrkAUj49Ra6U95UA9PEE"

# --- CSS FOR GREEN BUTTON ---
st.markdown("""
<style>
    div.stButton > button[kind="primary"] {
        background-color: #4CAF50 !important;
        border-color: #4CAF50 !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #45a049 !important;
        border-color: #45a049 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- PASSWORD PROTECTION ---
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

# --- 1. SETUP ---
st.set_page_config(page_title="Meeting Notes Creator", page_icon="📄", layout="wide")

API_KEY = None
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]

# Sidebar
with st.sidebar:
    st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=100)
    if not API_KEY:
        API_KEY = st.text_input("Enter Gemini API Key", type="password")
    st.caption("Model: gemini-2.5-flash")

if API_KEY:
    genai.configure(api_key=API_KEY)

# --- 2. GOOGLE SHEETS FUNCTIONS ---
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Auth Error: {e}")
        return None

def log_meeting_to_sheet(data_dict):
    client = get_gspread_client()
    if not client: return False
    try:
        sheet = client.open_by_key(MEETING_SHEET_ID)
        ws = sheet.get_worksheet(0)
        # Headers: Client Name | RM Name | Meeting Date | Location | Input Text | CRM Response | Client Version
        # Note: We are saving the core fields to match your existing sheet structure
        ws.append_row([
            data_dict.get('client_name', ''),
            data_dict.get('rm_name', ''),
            str(data_dict.get('date', '')),
            data_dict.get('location', ''),
            data_dict.get('input_text', ''),
            data_dict.get('crm_response', ''),
            data_dict.get('client_version', '')
        ])
        return True
    except Exception as e:
        st.error(f"❌ Sheet Save Error: {e}")
        return False

# --- 3. UI LAYOUT ---
st.title("📄 Meeting Notes Creator")
st.markdown("Turn raw notes into professional CRM records and Client updates.")

# Initialize Session State
if "generated_crm" not in st.session_state:
    st.session_state.generated_crm = ""
if "generated_client" not in st.session_state:
    st.session_state.generated_client = ""

with st.form("notes_form"):
    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input("Client / Lead Name", placeholder="e.g. Renuka Ma'am")
        # UPDATED: Date format
        meeting_date = st.date_input("Meeting Date", value=date.today(), format="DD/MM/YYYY")
        # UPDATED: Added Google Meet
        location = st.selectbox("Location", ["Jalgaon Office", "Nashik Office", "Client Visit", "Google Meet", "Call", "WhatsApp"])
    
    with col2:
        rm_name = st.text_input("RM Name", placeholder="e.g. Hitesh")
        # NEW: Meeting Done By
        meeting_done_by = st.selectbox("Meeting Done by", ["Hitesh sir", "Anuya mam", "RM Self"])
        # NEW: WhatsApp Formatting
        whatsapp_format = st.radio("WhatsApp Formatting?", ["Yes", "No"], horizontal=True)

    raw_notes = st.text_area("Meeting Summary (Raw Notes)", height=300, 
                            placeholder="Type raw notes here...")

    # BUTTON IS NOW GREEN VIA CSS
    submitted = st.form_submit_button("✨ Generate Professional Notes", type="primary")

# --- 4. GENERATION LOGIC ---
if submitted:
    if not API_KEY:
        st.error("🚨 API Key is missing.")
    elif not raw_notes or not client_name:
        st.warning("Please enter at least the Client Name and Meeting Notes.")
    else:
        with st.spinner("Drafting professional notes..."):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                # LOGIC FOR PERSPECTIVE
                perspective_instruction = ""
                if meeting_done_by == "RM Self":
                    perspective_instruction = "The meeting was done by the RM. Use 'I suggest', 'I recommend' in the Client Version."
                else:
                    perspective_instruction = f"The meeting was done by {meeting_done_by}. The note is assigned to the RM. Use 'We suggest', 'We recommend' in the Client Version to represent the firm."

                # LOGIC FOR FORMATTING
                fmt_instruction = ""
                if whatsapp_format == "Yes":
                    fmt_instruction = "Use bold, italics, and 2-3 relevant emojis to make it engaging."
                else:
                    fmt_instruction = "STRICTLY PLAIN TEXT. No bold, no italics, no emojis."

                full_prompt = f"""
                ### ROLE
                You are an expert Financial Editor for "Moneyplus". Convert raw meeting notes into two formats: CRM (Internal) and Client (External).

                ### INPUT DATA
                * Client: {client_name} | RM: {rm_name} 
                * Meeting Done By: {meeting_done_by}
                * Date: {meeting_date} | Loc: {location}
                * Raw Notes: {raw_notes}
                * WhatsApp Formatting Allowed: {whatsapp_format}

                ### PERSPECTIVE LOGIC
                {perspective_instruction}

                ### OUTPUT INSTRUCTIONS
                Generate exactly two versions separated by "|||SEPARATOR|||".
                
                1. CRM VERSION (Internal): 
                   - Plain text, numbered lists.
                   - NO markdown formatting.
                   - Optimize for BREVITY but CLARITY (Short, punchy sentences).
                
                2. CLIENT VERSION (External): 
                   - Tone: Professional, polite, action-oriented.
                   - Language: Friendly Indian English (Simple words, avoid complicated vocabulary).
                   - Formatting: {fmt_instruction}
                
                ### OUTPUT FORMAT
                CRM VERSION TEXT...
                |||SEPARATOR|||
                CLIENT VERSION TEXT...
                """

                response = model.generate_content(full_prompt)
                
                if "|||SEPARATOR|||" in response.text:
                    crm_part, client_part = response.text.split("|||SEPARATOR|||")
                else:
                    crm_part = response.text
                    client_part = "Could not auto-separate."

                # Save to session state
                st.session_state.generated_crm = crm_part.strip()
                st.session_state.generated_client = client_part.strip()
                
            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- 5. DISPLAY & SAVE LOGIC ---
if st.session_state.generated_crm:
    st.success("Notes Generated Successfully!")
    
    tab1, tab2 = st.tabs(["📂 CRM Version", "📱 Client Version"])
    
    with tab1:
        st.text_area("CRM Output", value=st.session_state.generated_crm, height=400, key="crm_display")
    with tab2:
        st.text_area("Client Output", value=st.session_state.generated_client, height=400, key="client_display")

    st.divider()
    
    # SAVE BUTTON (GREEN)
    if st.button("💾 Save to Google Sheet", type="primary"):
        # We append the 'Meeting Done By' info to RM Name for the sheet record to keep context
        # without breaking the fixed sheet columns.
        final_rm_entry = f"{rm_name} (By: {meeting_done_by})"
        
        payload = {
            "client_name": client_name,
            "rm_name": final_rm_entry, 
            "date": meeting_date,
            "location": location,
            "input_text": raw_notes,
            "crm_response": st.session_state.generated_crm,
            "client_version": st.session_state.generated_client
        }
        
        with st.spinner("Saving..."):
            if log_meeting_to_sheet(payload):
                st.success(f"✅ Saved for {client_name}!")
            else:
                st.error("Failed to save.")
