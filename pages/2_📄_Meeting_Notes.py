import streamlit as st
import google.generativeai as genai
from datetime import date
from auth import check_password
from db import save_meeting_note  # <--- NEW DATABASE IMPORT

# --- 1. SETUP & AUTH ---
st.set_page_config(page_title="Meeting Notes Creator", page_icon="📄", layout="wide")

# Use the centralized auth from auth.py
check_password()

# --- CSS FOR GREEN BUTTON ---
st.markdown("""
<style>
    /* Force Green Color for Primary Button */
    div.stButton > button[kind="primary"] {
        background-color: #4CAF50 !important;
        border: 1px solid #4CAF50 !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:focus {
        background-color: #4CAF50 !important;
        border-color: #4CAF50 !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #45a049 !important;
        border-color: #45a049 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# API Key handling
API_KEY = st.secrets.get("GEMINI_API_KEY")

# Sidebar
with st.sidebar:
    st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=100)
    if not API_KEY:
        API_KEY = st.text_input("Enter Gemini API Key", type="password")
    st.caption("Model: gemini-2.5-flash")

if API_KEY:
    genai.configure(api_key=API_KEY)

# --- 2. UI LAYOUT ---
st.title("📄 Meeting Notes Creator")
st.markdown("Turn raw notes into professional CRM records and Client updates.")

# Initialize Session State for results
if "generated_crm" not in st.session_state:
    st.session_state.generated_crm = ""
if "generated_client" not in st.session_state:
    st.session_state.generated_client = ""

with st.form("notes_form"):
    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input("Client / Lead Name", placeholder="e.g. Renuka Ma'am")
        meeting_date = st.date_input("Meeting Date", value=date.today(), format="DD/MM/YYYY")
        location = st.selectbox("Location", ["Jalgaon Office", "Nashik Office", "Client Visit", "Google Meet", "Call", "WhatsApp"])
    
    with col2:
        rm_name = st.text_input("RM Name", placeholder="e.g. Hitesh")
        meeting_done_by = st.selectbox("Meeting Done by", ["Hitesh sir", "Anuya mam", "RM Self"])
        whatsapp_format = st.radio("WhatsApp Formatting?", ["Yes", "No"], horizontal=True)

    raw_notes = st.text_area("Meeting Summary (Raw Notes)", height=300, 
                            placeholder="Type raw notes here...")

    submitted = st.form_submit_button("✨ Generate & Save Notes", type="primary")

# --- 3. GENERATION & DATABASE LOGIC ---
if submitted:
    if not API_KEY:
        st.error("🚨 API Key is missing.")
    elif not raw_notes or not client_name:
        st.warning("Please enter at least the Client Name and Meeting Notes.")
    else:
        with st.spinner("Drafting notes..."):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                # PERSPECTIVE LOGIC
                perspective_instruction = ""
                if meeting_done_by == "RM Self":
                    perspective_instruction = "The meeting was done by the RM. Use 'I suggest', 'I recommend' in the Client Version."
                else:
                    perspective_instruction = f"The meeting was done by {meeting_done_by}. The note is assigned to the RM. Use 'We suggest', 'We recommend' in the Client Version."

                # FORMATTING LOGIC
                fmt_instruction = ""
                if whatsapp_format == "Yes":
                    fmt_instruction = "Use bold (*text*), italics (_text_), and emojis."
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
                   - Plain text only, using short numbered lists for key points and actions.
                   - NO markdown, bold, italics, emojis, or extra formatting.
                   - Optimize for extreme BREVITY (under 200 words total).
                   - Structure: 
                     - Start with header: "CRM Notes - {client_name} - {meeting_date} - {location}".
                     - "Key Discussion Points:" (3-6 items max).
                     - "Action Items:" splitting client and team actions.
                
                2. CLIENT VERSION (External): 
                   - Tone: Professional, polite, action-oriented.
                   - Language: Simple, friendly Indian English.
                   - Formatting: {fmt_instruction}
                   - Structure: 
                     - Header: "Quick Notes from Your Moneyplus Meeting with {rm_name} Ji - {client_name} 😊".
                     - Greeting: "Dear [first name] Ji,".
                     - Recap main topics faktually.
                     - "Actions Expected" for client and team.
                     - Close with "Best wishes, {rm_name}".

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

                st.session_state.generated_crm = crm_part.strip()
                st.session_state.generated_client = client_part.strip()
                
            except Exception as e:
                st.error(f"Generation Error: {e}")

        # --- SAVE TO LOCAL SQLITE ---
        with st.spinner("Saving to local database..."):
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
            
            # Using the new local save function from db.py
            if save_meeting_note(payload):
                st.success(f"✅ Generated & Saved to Local DB for {client_name}!")
            else:
                st.error("❌ Generation successful, but database save failed.")

# --- 4. DISPLAY OUTPUT ---
if st.session_state.generated_crm:
    st.divider()
    st.markdown("### 📋 Generated Notes")
    st.info("👉 Click the copy icon in the top-right corner of the text box to copy.")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("📂 CRM Version")
        st.code(st.session_state.generated_crm, language=None)
        
    with col_b:
        st.subheader("📱 Client Version")
        st.code(st.session_state.generated_client, language="markdown")
