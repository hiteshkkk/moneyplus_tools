import streamlit as st
import google.generativeai as genai
from datetime import date

# --- 1. AUTHENTICATION & SETUP ---
st.set_page_config(page_title="Meeting Notes Creator", page_icon="📄", layout="wide")

API_KEY = None
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]

# Sidebar for manual key entry if needed
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

# Form Layout using Columns for Full HD optimization
with st.form("notes_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        client_name = st.text_input("Client / Lead Name", placeholder="e.g. Renuka Ma'am")
        meeting_date = st.date_input("Meeting Date", value=date.today())
        location = st.selectbox("Location", ["Jalgaon Office", "Nashik Office", "Client Visit", "Call", "WhatsApp"])
    
    with col2:
        rm_name = st.text_input("RM Name", placeholder="e.g. Hitesh")
        # Placeholder for spacing if needed, or leave empty
        st.write("") 
        st.write("")

    # Full width for summary
    raw_notes = st.text_area("Meeting Summary (Raw Notes)", height=300, 
                            placeholder="Type raw notes here... e.g. She want to set aside 15L for moving city. Son education taken care by husband...")

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
                
                # We combine the system instructions with the specific user input
                full_prompt = f"""
                ### ROLE
                You are an expert Financial Editor for "Moneyplus," an investment and insurance firm. Your job is to take raw, unstructured, or grammatically incorrect meeting notes provided by Relationship Managers and convert them into two professional, structured formats: one for Internal CRM records and one for sending to the Client.

                ### INPUT DATA
                * **Client Name:** {client_name}
                * **RM Name:** {rm_name}
                * **Date:** {meeting_date}
                * **Location:** {location}
                * **Raw Notes:** {raw_notes}

                ### OUTPUT INSTRUCTIONS
                You must generate exactly two versions. Both must be in simple, crisp, and short English. Use bullet points for readability.

                ---

                ### VERSION 1: FOR CRM (Internal Record)
                * **Tone:** Professional, Objective, Data-centric.
                * **Header:** "Meeting Notes: {client_name} | {meeting_date} | {location}"
                * **Sub-header:** "Action Required: [Key tasks]"
                * **Structure:**
                    * Use numbered points with bold headers.
                    * Clearly distinguish between "Plan" and "Rationale".
                    * Include specific numbers.
                * **Footer:** "Next Follow-up: [Specific trigger or date]"

                ### VERSION 2: FOR CLIENT (WhatsApp/Email)
                * **Tone:** Polite, Action-oriented, Supportive, Professional yet warm.
                * **Header:** "Dear {client_name},"
                * **Opening:** "Here is a quick summary of our discussion and the action plan:"
                * **Structure:**
                    * Use bullet points to summarize decisions.
                    * Focus on the *benefit* to the client.
                    * Clearly list what the client needs to do or what you are doing next.
                * **Sign-off:** "Regards, Team Moneyplus"

                ---

                ### CONSTRAINTS
                * Do not use complex jargon. Keep English simple.
                * Fix all grammar and spelling errors.
                * If the raw notes mention "I suggested," frame it as "Advice Given" in CRM and "Recommendation" in Client version.

                ### OUTPUT FORMAT
                Please separate the two versions with a clear delimiter like "|||SEPARATOR|||" so I can split them programmatically.
                """

                response = model.generate_content(full_prompt)
                
                # Split the response into two parts using the separator we asked for
                if "|||SEPARATOR|||" in response.text:
                    crm_part, client_part = response.text.split("|||SEPARATOR|||")
                else:
                    # Fallback if AI forgets separator
                    crm_part = response.text
                    client_part = "Could not auto-separate. Please check the CRM text above."

                # --- 4. DISPLAY RESULTS ---
                st.success("Notes Generated Successfully!")
                
                # Use Tabs for cleaner interface
                tab1, tab2 = st.tabs(["📂 CRM Version", "📱 Client Version (WhatsApp/Email)"])

                with tab1:
                    st.info("Copy this content for your internal records.")
                    # st.code adds a copy button automatically!
                    st.code(crm_part.strip(), language="markdown")

                with tab2:
                    st.info("Copy this content to send to the client.")
                    st.code(client_part.strip(), language="markdown")

            except Exception as e:
                st.error(f"An error occurred: {e}")
