import streamlit as st
import google.generativeai as genai
from datetime import date

# --- 1. AUTHENTICATION & SETUP ---
st.set_page_config(page_title="Meeting Notes Creator", page_icon="📄", layout="wide")

API_KEY = None
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]

# Sidebar for manual key entry
with st.sidebar:
    st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=100)
    if not API_KEY:
        API_KEY = st.text_input("Enter Gemini API Key", type="password")
    st.caption("Model: gemini-2.5-flash")

# Configure Gemini
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- 2. MAIN UI LAYOUT ---
st.title("📄 Meeting Notes Creator")
st.markdown("Turn raw notes into professional CRM records and Client updates.")

# Form Layout
with st.form("notes_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        client_name = st.text_input("Client / Lead Name", placeholder="e.g. Renuka Ma'am")
        meeting_date = st.date_input("Meeting Date", value=date.today())
        location = st.selectbox("Location", ["Jalgaon Office", "Nashik Office", "Client Visit", "Call", "WhatsApp"])
    
    with col2:
        rm_name = st.text_input("RM Name", placeholder="e.g. Hitesh")
        st.write("") 
        st.write("")

    raw_notes = st.text_area("Meeting Summary (Raw Notes)", height=300, 
                            placeholder="Type raw notes here...")

    submitted = st.form_submit_button("✨ Generate Professional Notes", type="primary")

# --- 3. PROCESSING LOGIC ---
if submitted:
    if not API_KEY:
        st.error("🚨 API Key is missing.")
    elif not raw_notes or not client_name:
        st.warning("Please enter at least the Client Name and Meeting Notes.")
    else:
        with st.spinner("Drafting professional notes..."):
            try:
                # Construct the Prompt
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                full_prompt = f"""
                ### ROLE
                You are an expert Financial Editor for "Moneyplus". Convert raw meeting notes into two formats: CRM (Internal) and Client (External).

                ### INPUT DATA
                * **Client Name:** {client_name}
                * **RM Name:** {rm_name}
                * **Date:** {meeting_date}
                * **Location:** {location}
                * **Raw Notes:** {raw_notes}

                ### OUTPUT INSTRUCTIONS
                Generate exactly two versions separated by "|||SEPARATOR|||".

                ---

                ### VERSION 1: FOR CRM (Internal Record)
                * **FORMATTING RULES:** - STRICTLY PLAIN TEXT. 
                    - NO markdown, NO bolding (**), NO italics (*), NO headers (###).
                    - CRM does not support formatting.
                * **Structure:**
                    - Header: "Meeting Notes: {client_name} | {meeting_date} | {location}"
                    - Sub-header: "Action Required: [Tasks]"
                    - Body: Use numbered lists (1., 2., 3.) for all points. Do not use bullet points (*).
                    - Footer: "Next Follow-up: [Date]"

                ### VERSION 2: FOR CLIENT (WhatsApp/Email)
                * **FORMATTING RULES:** - User Whatsapp based formatting like bold/italics/underline at relevant places.
                * **Tone:** Polite, Action-oriented, Professional, Use simple Indian english words.
                * **Structure:**
                    - Header: "Dear {client_name},"
                    - Body: Use numbered lists (1., 2., 3.) for main points to allow easy reading on mobile.
                    - Blank Line: after each numbered list item
                    - content: Focus on benefits and next steps.
                    

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
                    client_part = "Could not auto-separate. Please check the text above."

                # --- 4. DISPLAY RESULTS ---
                st.success("Notes Generated Successfully!")
                
                tab1, tab2 = st.tabs(["📂 CRM Version (Plain Text)", "📱 Client Version (WhatsApp)"])

                with tab1:
                    st.caption("Plain text for CRM copy-paste (Wraps to screen width)")
                    # st.text_area respects screen width and allows scrolling if content is huge
                    st.text_area("CRM Output", value=crm_part.strip(), height=400)

                with tab2:
                    st.caption("Formatted for WhatsApp/Email")
                    st.text_area("Client Output", value=client_part.strip(), height=400)

            except Exception as e:
                st.error(f"An error occurred: {e}")
