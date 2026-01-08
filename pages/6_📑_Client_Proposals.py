import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import streamlit.components.v1 as components
import datetime

# --- CONFIGURATION ---
SHEET_ID = "182JF4alQGimymohEsq9IS3x3PLNnPPqHaH0AMJIxBGU"

# --- MASTER STYLING (Ashwin Plan - Browser Print Ready) ---
MASTER_CSS = """
<style>
    /* Print Settings */
    @media print {
        @page { size: A4; margin: 1cm; }
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        .no-print { display: none !important; }
        .card, .bucket-green, .bucket-yellow, .bucket-blue, .warn-box, .info-box { break-inside: avoid; }
    }

    body { font-family: 'Helvetica', sans-serif; font-size: 12px; line-height: 1.5; color: #333; background: #fff; }
    
    /* HEADER */
    .header-box {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 25px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .header-box::before {
        content: ""; position: absolute; top: -20px; right: -20px;
        width: 100px; height: 100px; background: rgba(255,255,255,0.1); border-radius: 50%;
    }
    .header-title { font-size: 24px; font-weight: bold; margin: 0; color: #fff; position: relative; z-index: 2; }
    
    /* CARDS */
    .card {
        background-color: #f8f9ff;
        border: 1px solid #e3e6ff;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* TIMELINE */
    .timeline-box {
        background: #e3f2fd;
        border-radius: 50px;
        padding: 15px 20px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid #bbdefb;
        display: flex;
        justify-content: space-around;
        align-items: center;
    }
    .t-item { 
        background: white; border: 2px solid #1565c0; color: #1565c0;
        border-radius: 12px; padding: 5px 15px; font-weight: bold; font-size: 11px;
        min-width: 80px; text-align: center;
    }
    .t-line { color: #1565c0; font-weight: bold; opacity: 0.5; }

    /* BUCKETS (Colors) */
    .bucket-green {
        background: linear-gradient(to right, #e8f5e9, #f1f8e9);
        border: 1px solid #c8e6c9; border-left: 5px solid #4caf50;
        padding: 15px; margin-bottom: 15px; border-radius: 8px;
    }
    .bucket-yellow {
        background: linear-gradient(to right, #fff8e1, #fffde7);
        border: 1px solid #ffe082; border-left: 5px solid #ffb300;
        padding: 15px; margin-bottom: 15px; border-radius: 8px;
    }
    .bucket-blue {
        background: linear-gradient(to right, #e3f2fd, #e1f5fe);
        border: 1px solid #bbdefb; border-left: 5px solid #1e88e5;
        padding: 15px; margin-bottom: 15px; border-radius: 8px;
    }
    
    /* TEXT STYLES */
    h2 { color: #1a237e; font-size: 16px; margin-top: 0; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    h3 { color: #333; font-size: 14px; margin-top: 0; font-weight: bold; }
    ul { padding-left: 18px; margin: 5px 0; }
    li { margin-bottom: 5px; }
    strong { color: #000; font-weight: bold; }
    
    /* BOXES */
    .warn-box { background: #fff3e0; border-left: 4px solid #fb8c00; padding: 12px; margin-top: 20px; border-radius: 6px; }
    .info-box { background: #e0f2f1; border-left: 4px solid #00897b; padding: 12px; margin-top: 10px; border-radius: 6px; }
    
    .footer-note { font-size: 9px; color: #888; margin-top: 40px; text-align: center; border-top: 1px solid #eee; padding-top: 15px; }
</style>
"""

# --- CSS FOR UI BUTTONS ---
st.markdown("""
<style>
    div.stButton > button[kind="primary"] { background-color: #4CAF50 !important; border-color: #4CAF50 !important; color: white !important; }
    div.stButton > button[kind="primary"]:hover { background-color: #45a049 !important; border-color: #45a049 !important; }
</style>
""", unsafe_allow_html=True)

# --- AUTH & SETUP ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds)
    except Exception: return None

@st.cache_data(ttl=600)
def load_config_data():
    client = get_gspread_client()
    if not client: return None, None
    try:
        sheet = client.open_by_key(SHEET_ID)
        ws_sys = sheet.worksheet("System_Prompts")
        sys_val = ws_sys.acell('A2').value 
        ws_temp = sheet.worksheet("Template_Master")
        df_templates = pd.DataFrame(ws_temp.get_all_records())
        return sys_val, df_templates
    except Exception as e:
        st.error(f"Sheet Load Error: {e}"); return None, None

def log_proposal_to_sheet(data_dict):
    client = get_gspread_client()
    if not client: return False
    try:
        sheet = client.open_by_key(SHEET_ID)
        try:
            ws = sheet.worksheet("Generated_Plans")
        except:
            ws = sheet.add_worksheet("Generated_Plans", 1000, 10)
            ws.append_row(["Date", "Client Name", "Template Type", "Meeting Notes", "Proposal Details", "Generated HTML", "Generated WhatsApp"])
        
        ws.append_row([
            str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            data_dict['client_name'],
            data_dict['template_type'],
            data_dict['meeting_notes'],
            data_dict['proposal_details'],
            data_dict['html_output'],
            data_dict['whatsapp_output']
        ])
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

def main():
    st.title("📑 Client Proposal Creator")
    system_role, df_templates = load_config_data()
    
    if df_templates is None: return

    with st.form("proposal_form"):
        c1, c2 = st.columns(2)
        with c1: client_name = st.text_input("Client Name", placeholder="e.g. Rahul Patil")
        with c2: selected_template = st.selectbox("Select Proposal Type", df_templates['Template_Name'].tolist())

        c_note, c_prop = st.columns(2)
        with c_note: meeting_notes = st.text_area("Client Background (Income, Goals, Timelines)", height=200, placeholder="E.g., Needs money for wedding in 2 years...")
        with c_prop: proposal_context = st.text_area("Specific Details / Bucket Amounts", height=200, placeholder="E.g., 10k Comfort, 15k Dream, 25k Wealth...")

        submit = st.form_submit_button("✨ Generate Proposal", type="primary")

    if submit:
        if not client_name or not proposal_context:
            st.error("Missing details.")
        else:
            with st.spinner("Drafting..."):
                try:
                    temp_data = df_templates[df_templates['Template_Name'] == selected_template].iloc[0]
                    
                    full_prompt = f"""
                    ### ROLE
                    {system_role}
                    *IMPORTANT:* Independent financial advisor. No company names.

                    ### INPUTS
                    Client: {client_name}
                    Notes: {meeting_notes}
                    Proposal: {proposal_context}

                    ### TEMPLATE INSTRUCTIONS
                    {temp_data['Input_Instructions']}

                    ### OUTPUT 1: HTML BODY CONTENT ONLY
                    {temp_data['HTML_Output_Instructions']}
                    
                    *STRICT HTML RULES:*
                    - Generate content ONLY inside the body.
                    - Do NOT use <html>, <head>, <style> tags.
                    - Use the provided CSS classes (bucket-green, timeline-box, etc.).

                    ### OUTPUT 2: WHATSAPP
                    {temp_data['WhatsApp_Output_Instructions']}

                    ### SEPARATOR
                    |||SEPARATOR|||
                    """

                    model = genai.GenerativeModel("gemini-2.0-flash-exp")
                    response = model.generate_content(full_prompt)
                    
                    if "|||SEPARATOR|||" in response.text:
                        html_body, wa_part = response.text.split("|||SEPARATOR|||")
                    else:
                        html_body, wa_part = response.text, "Error"

                    html_body = html_body.replace("```html", "").replace("```", "").strip()
                    
                    # Store in Session
                    st.session_state['prop_html_body'] = html_body
                    st.session_state['prop_wa'] = wa_part.strip()
                    st.session_state['client_name'] = client_name 

                except Exception as e: st.error(f"Error: {e}")

            # SAVE TO SHEET AUTOMATICALLY
            with st.spinner("Saving to database..."):
                save_data = {
                    "client_name": client_name,
                    "template_type": selected_template,
                    "meeting_notes": meeting_notes,
                    "proposal_details": proposal_context,
                    "html_output": html_body,
                    "whatsapp_output": wa_part.strip()
                }
                if log_proposal_to_sheet(save_data):
                    st.success("✅ Proposal Generated & Saved!")
                else:
                    st.warning("⚠️ Proposal generated but failed to save to Google Sheet.")

    if 'prop_html_body' in st.session_state:
        st.divider()
        st.subheader("🎉 Generated Proposal")
        tab_html, tab_wa = st.tabs(["📄 Document Preview", "📱 WhatsApp"])
        
        with tab_html:
            preview_html = f"""
            {MASTER_CSS}
            <div style="max-width:800px; margin:auto; background:white; padding:40px; border:1px solid #ddd; box-shadow:0 0 10px rgba(0,0,0,0.1);">
                {st.session_state['prop_html_body']}
                <div class="footer-note">Disclaimer: Investments are subject to market risk. Read all scheme related documents carefully.</div>
            </div>
            <div style="text-align:center; margin-top:20px;" class="no-print">
                <button onclick="window.print()" style="background:#4CAF50; color:white; border:none; padding:12px 25px; font-size:16px; border-radius:50px; cursor:pointer; font-weight:bold;">🖨️ Print / Save PDF</button>
            </div>
            """
            components.html(preview_html, height=1200, scrolling=True)
        
        with tab_wa:
            st.text_area("WhatsApp Text", value=st.session_state['prop_wa'], height=400)

if __name__ == "__main__":
    main()
