import streamlit as st
import google.generativeai as genai
import tempfile
import os
import json
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. INITIALIZE API KEY ---
API_KEY = None
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=100)
    st.title("Settings")
    
    if not API_KEY:
        API_KEY = st.text_input("Enter Gemini API Key", type="password")
        if not API_KEY:
             st.warning("⚠️ Enter API Key to continue")
    else:
        st.success("Key Loaded Securely")

    model_name = "gemini-2.5-flash"
    st.caption(f"Model: {model_name}")

if API_KEY:
    genai.configure(api_key=API_KEY)

# --- MAIN PAGE UI ---
st.title("Moneyplus Discharge Summary Auditor")
st.markdown("Submit the claim intimation number and upload the PDF below.")

# --- INPUT SECTION ---
col1, col2 = st.columns([1, 2])
with col1:
    claim_id = st.text_input("Claim Intimation No.", placeholder="e.g. 251300314060")
with col2:
    uploaded_file = st.file_uploader("Upload Discharge Summary", type=["pdf"])

# --- PROCESSING LOGIC ---
if st.button("Generate Audit Report", type="primary"):
    if not API_KEY:
        st.error("🚨 API Key is missing.")
    elif not uploaded_file:
        st.error("Please upload a PDF file first.")
    elif not claim_id:
        st.warning("Please enter a Claim ID.")
    else:
        with st.spinner(f"Analyzing with {model_name}..."):
            try:
                # 1. Handle File
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                # 2. SYSTEM PROMPT (Strict JSON)
                system_instruction = """
                You are an expert medical claims processor.
                NON-NEGOTIABLE RULES:
                - Use ONLY the attached discharge summary document(s) as the source of truth.
                - Return ONLY a single valid JSON object.
                - Use EXACTLY the keys specified.
                - If a value is not present, output "Not mentioned" or "N/A".

                ANTI-JARGON RULES:
                - Write for a common person: simple words, short sentences.
                - Explain medical terms once in brackets.

                OUTPUT STRUCTURE (JSON ONLY):
                {
                  "name_and_age": "Patient Name, Age years",
                  "gender": "Male/Female/Other",
                  "admission_date_time": "DD/MM/YYYY HH:MM AM/PM",
                  "discharge_date_time": "DD/MM/YYYY HH:MM AM/PM",
                  "total_duration_hours": "XX hours",
                  "diagnosis": "Simple summary of diagnosis",
                  "explanation_of_diagnosis_and_treatment": {
                    "English": "Explanation...",
                    "Hindi": "Explanation...",
                    "Marathi": "Explanation..."
                  },
                  "medical_history_text": "- History item 1",
                  "potential_red_flags_text": "- Red flag 1"
                }
                """

                # 3. USER PROMPT
                user_prompt = f"""
                Claim Intimation No: "{claim_id}"
                TASK: Read the attached discharge summary and return ONLY a valid JSON object.
                STEPS:
                1) Extract patient basic details.
                2) Extract final diagnosis (simple wording).
                3) Write "explanation_of_diagnosis_and_treatment" in English, Hindi, Marathi.
                4) Extract medical history as multi-line string.
                5) Extract red flags as multi-line string.
                """

                # 4. Generate
                model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                sample_file = genai.upload_file(path=tmp_path, display_name="Claim Doc")
                
                response = model.generate_content(
                    [sample_file, user_prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                data = json.loads(response.text)
                gen_time = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")

                # 5. Build HTML Report (Self-contained for Component)
                # We include the <style> tag INSIDE this string so the component is fully styled.
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .report-container {{
                        background-color: white;
                        padding: 40px;
                        border: 1px solid #e0e0e0;
                        border-radius: 5px;
                        color: #000;
                        max-width: 850px;
                        margin: 20px auto;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                    }}
                    .brand-text {{ color: #555; font-size: 14px; font-weight: bold; margin-bottom: 5px; }}
                    .main-title {{ color: #000; font-size: 24px; font-weight: bold; margin: 0; }}
                    .sub-title {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
                    .claim-header {{ font-weight: bold; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #000; padding-bottom: 10px; }}
                    .section-head {{ font-size: 14px; font-weight: bold; text-transform: uppercase; color: #000; margin-top: 25px; margin-bottom: 10px; border-bottom: 1px solid #eee; }}
                    .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                    .details-table td {{ padding: 6px 0; border-bottom: 1px solid #f0f0f0; vertical-align: top; font-size: 14px; color: #000; }}
                    .label-col {{ width: 35%; font-weight: bold; color: #444; }}
                    .content-text {{ font-size: 14px; line-height: 1.5; margin-bottom: 10px; color: #000; }}
                    .lang-title {{ font-weight: bold; font-size: 15px; margin-top: 15px; color: #000; }}
                    .expl-sub {{ font-size: 12px; color: #666; font-style: italic; margin-bottom: 2px; }}
                    .footer {{ margin-top: 40px; font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 10px; }}
                    
                    @media print {{
                        body {{ background-color: white; }}
                        .report-container {{ box-shadow: none; margin: 0; border: none; max-width: 100%; width: 100%; padding: 0; }}
                        .no-print {{ display: none; }}
                    }}
                </style>
                <script>
                    function triggerPrint() {{
                        document.title = "Audit_{claim_id}";
                        window.print();
                    }}
                </script>
                </head>
                <body>
                
                <div class="report-container">
                    <div style="text-align: right; margin-bottom: 10px;" class="no-print">
                        <button onclick="triggerPrint()" style="background: #0056b3; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">🖨️ Print / Save PDF</button>
                    </div>

                    <div class="brand-text">moneyplus</div>
                    <div class="main-title">Moneyplus Discharge Summary AI Auditor</div>
                    <div class="sub-title">AI-assisted discharge summary extraction for claims review</div>
                    <div class="claim-header">Claim Intimation No: {claim_id}</div>

                    <div class="section-head">BASIC DETAILS</div>
                    <table class="details-table">
                        <tr><td class="label-col">Name & Age</td><td>{data.get('name_and_age', 'N/A')}</td></tr>
                        <tr><td class="label-col">Gender</td><td>{data.get('gender', 'N/A')}</td></tr>
                        <tr><td class="label-col">Admission</td><td>{data.get('admission_date_time', 'N/A')}</td></tr>
                        <tr><td class="label-col">Discharge</td><td>{data.get('discharge_date_time', 'N/A')}</td></tr>
                        <tr><td class="label-col">Total duration</td><td>{data.get('total_duration_hours', 'N/A')}</td></tr>
                    </table>
                    <div style="font-size:12px; color:#888; margin-bottom:20px;">Generated: {gen_time}</div>

                    <div class="section-head">DIAGNOSIS (SIMPLE)</div>
                    <div class="content-text">{data.get('diagnosis', 'N/A')}</div>

                    <div class="lang-title">English</div>
                    <div class="expl-sub">Explanation</div>
                    <div class="content-text">{data['explanation_of_diagnosis_and_treatment'].get('English', 'N/A')}</div>

                    <div class="lang-title">Hindi</div>
                    <div class="expl-sub">Explanation</div>
                    <div class="content-text">{data['explanation_of_diagnosis_and_treatment'].get('Hindi', 'N/A')}</div>

                    <div class="lang-title">Marathi</div>
                    <div class="expl-sub">Explanation</div>
                    <div class="content-text">{data['explanation_of_diagnosis_and_treatment'].get('Marathi', 'N/A')}</div>

                    <div class="section-head">HISTORY</div>
                    <div class="content-text" style="white-space: pre-line;">{data.get('medical_history_text', 'Not mentioned')}</div>

                    <div class="section-head" style="color: #d32f2f;">POTENTIAL RED FLAGS</div>
                    <div class="content-text" style="white-space: pre-line;">{data.get('potential_red_flags_text', 'None identified')}</div>

                    <div class="footer">Disclaimer: This is an AI generated summary and may not be accurate.</div>
                </div>
                </body>
                </html>
                """

                st.markdown("---")
                st.success("Report Generated Successfully!")

                # --- THE FIX: USE components.html ---
                # This renders the HTML inside an iframe, preventing Streamlit from treating it as Markdown/Code.
                # 'height=1000' ensures the whole report is visible.
                # 'scrolling=True' adds a scrollbar if the report is very long.
                components.html(html_content, height=1000, scrolling=True)

                # Optional: Provide a download button for the raw HTML file as backup
                st.download_button(
                    label="📥 Download HTML File",
                    data=html_content,
                    file_name=f"Audit_{claim_id}.html",
                    mime="text/html"
                )

                os.remove(tmp_path)

            except Exception as e:
                st.error(f"An error occurred: {e}")
