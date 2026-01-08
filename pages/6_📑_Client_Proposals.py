import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import streamlit.components.v1 as components
import datetime

# --- CONFIGURATION ---
SHEET_ID = "182JF4alQGimymohEsq9IS3x3PLNnPPqHaH0AMJIxBGU"

# --- MASTER STYLING (PRO DESIGN) ---
MASTER_CSS = """
<style>
    /* ---- Base & Print Settings ---- */
    @media print {
        @page { size: A4; margin: 0.5cm; }
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; background: #fff !important; }
        .page { box-shadow: none !important; border-radius: 0 !important; margin: 0 !important; padding: 0 !important; }
        .no-print { display: none !important; }
        .bucket, .card, .warn-box, .info-box { break-inside: avoid; }
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        line-height: 1.5; color: #222;
        background: linear-gradient(135deg, #5c6bc0 0%, #7e57c2 50%, #26a69a 100%);
    }

    .page {
        background: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.16);
        max-width: 800px; margin: auto;
    }

    /* ---- Header ---- */
    .header {
        text-align: center;
        background: radial-gradient(circle at top left, #42a5f5, #1e3c72);
        color: #fff;
        padding: 20px;
        border-radius: 14px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    .header::before {
        content: ""; position: absolute; width: 160px; height: 160px; border-radius: 50%;
        background: rgba(255,255,255,0.12); top: -60px; right: -40px;
    }
    .header::after {
        content: ""; position: absolute; width: 120px; height: 120px; border-radius: 50%;
        background: rgba(255,255,255,0.08); bottom: -40px; left: -20px;
    }
    .header h1 { font-size: 22px; margin: 0 0 5px; position: relative; z-index: 1; }
    .tagline { font-size: 13px; opacity: 0.95; margin: 0; position: relative; z-index: 1; }

    /* Pill Row */
    .pill-row { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 10px; position: relative; z-index: 1; }
    .pill {
        font-size: 11px; background: rgba(255,255,255,0.15); border-radius: 20px;
        padding: 4px 12px; border: 1px solid rgba(255,255,255,0.3);
    }

    /* ---- Typography & Highlights ---- */
    h2 { font-size: 18px; color: #1a237e; margin: 20px 0 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    h3 { font-size: 15px; color: #0d47a1; margin: 15px 0 5px; font-weight: bold; }
    p { font-size: 13px; margin-bottom: 8px; text-align: justify; }
    ul { padding-left: 18px; margin: 5px 0 15px; }
    li { font-size: 13px; margin-bottom: 5px; }
    
    .highlight {
        font-weight: 600; color: #1b5e20; background: #e8f5e9;
        padding: 0 5px; border-radius: 4px;
    }

    /* ---- Cards & Buckets ---- */
    .card {
        background: #f8f9ff; border: 1px solid #e3e6ff; border-radius: 12px;
        padding: 15px; margin-bottom: 15px;
    }
    
    .bucket {
        border-radius: 12px; padding: 15px; margin: 15px 0;
        position: relative; overflow: hidden; border: 1px solid #ddd;
    }
    .bucket-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .bucket-title { font-weight: 700; font-size: 14px; color: #0d47a1; display: flex; align-items: center; gap: 6px; }
    .bucket-amount {
        font-size: 13px; font-weight: 700; background: rgba(255,255,255,0.9);
        border-radius: 20px; padding: 4px 12px; border: 1px solid rgba(0,0,0,0.1); color: #1b5e20;
    }
    
    .b-green { background: linear-gradient(135deg,#e8f5e9,#f1f8e9); border-color: #c8e6c9; }
    .b-yellow { background: linear-gradient(135deg,#fff8e1,#ffecb3); border-color: #ffe082; }
    .b-blue { background: linear-gradient(135deg,#e8eaf6,#e3f2fd); border-color: #c5cae9; }

    /* ---- Timeline ---- */
    .timeline-wrap {
        background: #e3f2fd; border: 1px solid #bbdefb; border-radius: 12px;
        padding: 15px; margin: 15px 0; text-align: center;
    }
    .timeline-label { font-size: 12px; font-weight: 600; color: #1a237e; margin-bottom: 10px; }
    .timeline { display: flex; justify-content: space-around; align-items: center; position: relative; }
    .timeline::before {
        content: ""; position: absolute; left: 10%; right: 10%; top: 50%; height: 3px;
        background: linear-gradient(90deg,#4caf50,#ffb300,#3949ab); opacity: 0.5; z-index: 0;
    }
    .t-item {
        position: relative; z-index: 1; width: 80px; height: 80px; border-radius: 50%;
        background: #fff; border: 3px solid #c5cae9; display: flex; flex-direction: column;
        align-items: center; justify-content: center; font-size: 10px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .t-item span { font-weight: 700; font-size: 12px; display: block; margin-bottom: 2px; }

    /* ---- Boxes ---- */
    .warn-box { background: #fff3e0; border-left: 4px solid #fb8c00; padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 20px; }
    .info-box { background: #e0f2f1; border-left: 4px solid #00897b; padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 10px; }
    .footer-note { font-size: 10px; color: #777; margin-top: 30px; text-align: center; border-top: 1px solid #eee; padding-top: 10px; }
</style>
"""

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
        
        # 1. System Prompt (Robust Read)
        ws_sys = sheet.worksheet("System_Prompts")
        sys_val = ws_sys.acell('A2').value 
        
        # 2. Templates (Robust Read using get_all_values instead of records)
        ws_temp = sheet.worksheet("Template_Master")
        raw_data = ws_temp.get_all_values()
        
        # Convert to DataFrame
        # We assume Row 1 is headers. We take only the first 4 columns to avoid empty trailing columns.
        headers = raw_data[0]
        rows = raw_data[1:]
        
        df_templates = pd.DataFrame(rows, columns=headers)
        
        # Filter out rows where Template_Name is empty
        if 'Template_Name' in df_templates.columns:
            df_templates = df_templates[df_templates['Template_Name'] != ""]
            
        return sys_val, df_templates
        
    except Exception as e:
        st.error(f"Sheet Load Error: {e}")
        return None, None

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
        with c_note: meeting_notes = st.text_area("Client Background (Income, Goals, Timelines)", height=200)
        with c_prop: proposal_context = st.text_area("Specific Details / Bucket Amounts", height=200, placeholder="E.g., 25k Safety (Liquid), 15k Dream (Hybrid)...")

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
                    - ONLY generate content inside the body.
                    - Do NOT use <html>, <head> or <style>.
                    - STRICTLY USE these CSS classes:
                      - Header: <div class="header"> with <div class="pill-row">
                      - Highlights: <span class="highlight">
                      - Timeline: <div class="timeline-wrap"> with <div class="t-item">
                      - Buckets: <div class="bucket b-green">, <div class="bucket b-yellow">, <div class="bucket b-blue">
                      - Bucket Amounts: <div class="bucket-amount">
                    
                    ### OUTPUT 2: WHATSAPP
                    {temp_data['WhatsApp_Output_Instructions']}

                    ### SEPARATOR
                    |||SEPARATOR|||
                    """

                    model = genai.GenerativeModel("gemini-2.5-flash")
                    response = model.generate_content(full_prompt)
                    
                    if "|||SEPARATOR|||" in response.text:
                        html_body, wa_part = response.text.split("|||SEPARATOR|||")
                    else:
                        html_body, wa_part = response.text, "Error"

                    html_body = html_body.replace("```html", "").replace("```", "").strip()
                    
                    st.session_state['prop_html_body'] = html_body
                    st.session_state['prop_wa'] = wa_part.strip()
                    st.session_state['client_name'] = client_name 

                    save_data = {
                        "client_name": client_name,
                        "template_type": selected_template,
                        "meeting_notes": meeting_notes,
                        "proposal_details": proposal_context,
                        "html_output": html_body,
                        "whatsapp_output": wa_part.strip()
                    }
                    log_proposal_to_sheet(save_data)

                except Exception as e: st.error(f"Error: {e}")

    if 'prop_html_body' in st.session_state:
        st.divider()
        st.subheader("🎉 Generated Proposal")
        tab_html, tab_wa = st.tabs(["📄 Document Preview", "📱 WhatsApp"])
        
        with tab_html:
            preview_html = f"""
            {MASTER_CSS}
            <div class="page">
                {st.session_state['prop_html_body']}
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
