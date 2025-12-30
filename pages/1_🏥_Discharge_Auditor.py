import streamlit as st
import google.generativeai as genai
import tempfile
import os
import json
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. SETUP API KEY SAFELY ---
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
             st.warning("⚠️ Please enter your API Key to continue.")
    else:
        st.success("API Key Loaded Securely")

    # Use the latest model
    model_name = "gemini-2.5-flash"
    st.caption(f"Model: {model_name}")

if API_KEY:
    genai.configure(api_key=API_KEY)

# --- MAIN PAGE UI ---
st.title("Moneyplus Discharge Summary Auditor")
st.markdown("Submit the claim intimation number and upload the PDF below.")

# --- CSS TO MATCH YOUR PDF ---
st.markdown("""
    <style>
    /* Screen View Container */
    .report-container {
        background-color: white;
        padding: 40px;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #000;
        max-width: 850px; /* A4 width approx */
        margin: auto;
    }
    
    /* Headers */
    .brand-text { color: #555; font-size: 14px; font-weight: bold; margin-bottom: 5px; }
    .main-title { color: #000; font-size: 24px; font-weight: bold; margin: 0; }
    .sub-title { color: #666; font-size: 14px; margin-bottom: 20px; }
    
    .claim-header { 
        font-weight: bold; 
        font-size: 16px; 
        margin-bottom: 20px; 
        border-bottom: 2px solid #000; 
        padding-bottom: 10px;
    }

    /* Section Headers */
    .section-head {
        font-size: 14px;
        font-weight: bold;
        text-transform: uppercase;
        color: #000;
        margin-top: 25px;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
    }

    /* Table Styling */
    .details-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
    .details-table td { 
        padding: 6px 0; 
        border-bottom: 1px solid #f0f0f0; 
        vertical-align: top; 
        font-size: 14px;
    }
    .label-col { width: 35%; font-weight: bold; color: #444; }

    /* Content Styling */
    .content-text { font-size: 14px; line-height: 1.5; margin-bottom: 10px; }
    
    /* Language specific */
    .lang-title { font-weight: bold; font-size: 15px; margin-top: 15px; }
    .expl-sub { font-size: 12px; color: #666; font-style: italic; margin-bottom: 2px; }

    /* Footer */
    .footer { margin-top: 40px; font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 10px; }

    @media print {
        header, footer, aside, .stApp > header { display: none !important; }
        .stApp { margin: 0; padding: 0; }
        .report-container { border: none; padding: 0; margin: 0; width: 100%; }
    }
    </style>
""", unsafe_allow_html=True)

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

                # 2. YOUR EXACT SYSTEM PROMPT (The Rules)
                system_instruction = """
                You are an expert medical claims processor.

                NON-NEGOTIABLE RULES:
                - Use ONLY the attached discharge summary document(s) as the source of truth.
                - Return ONLY a single valid JSON object (no markdown/code fences, no extra text).
                - Use EXACTLY the keys and structure specified in the user prompt. Do not add or rename keys.
                - If a value is not present in the document, output exactly "Not mentioned" or "N/A" (as instructed).

                ANTI-JARGON RULES (mandatory for explanation_of_diagnosis_and_treatment):
                - Write for a common person: simple words, short sentences.
                - Do NOT use medical abbreviations/acronyms (e.g., CT, MRI, HTN, DM). Spell meaning in simple words instead.
                - Do NOT use technical procedure/technique/brand names. Describe in simple words instead.
                - If a medical word is unavoidable, explain it once in brackets in simple words, then avoid using it again.

                ANTI-REPETITION RULES (mandatory):
                - The field 'diagnosis' must contain ONLY what problem/condition was diagnosed (no treatment details).
                - The field 'explanation_of_diagnosis_and_treatment' must focus ONLY on what was done in hospital and why it helps.
                - Do NOT repeat the same sentence/idea across these two fields.

                QUALITY:
                - Keep the overall JSON concise (about 1 page).
                - Prefer explicit values from headings like Final Diagnosis, Admission/Discharge date/time, Procedure/Surgery, Medicines, Past history.
                """

                # 3. YOUR EXACT USER PROMPT (The Task)
                user_prompt = f"""
                Claim Intimation No: "{claim_id}"

                TASK
                Read the attached discharge summary and return ONLY a valid JSON object in the exact structure provided below.

                GOALS
                - Extract claim-critical details: patient basics, final diagnosis, treatment/procedures/medicines (as available), medical history with duration, and potential claim red flags.
                - Write a layperson-friendly explanation of treatment in multiple languages.

                LANGUAGES REQUIRED
                Provide explanations in these languages (use the language name as JSON key): English, Hindi, Marathi

                ANTI-REPETITION RULES (MANDATORY)
                - The fields 'diagnosis' and 'explanation_of_diagnosis_and_treatment' must NOT repeat the same sentences or ideas.
                - 'diagnosis' must contain ONLY what condition/problem was finally diagnosed (no treatment details).
                - 'explanation_of_diagnosis_and_treatment' must focus on ONLY what was done in hospital (treatment/procedure/medicines) and why it helps (do not repeat the diagnosis sentence).

                STEP-BY-STEP
                1) Read the entire discharge summary.
                2) Extract patient basic details: name, age, gender/sex (if present), admission date/time, discharge date/time.
                3) Extract the final diagnosis/diagnoses.
                4) Compute total_duration_hours from admission_date_time to discharge_date_time (hours; can be decimal). If times are missing, write "Not mentioned".
                5) Write "diagnosis" as simple non-medical wording of ONLY the final diagnosis/problem (1-2 short lines). Do NOT mention tests, procedures, surgery, implants, medicines, or treatment steps here.
                6) Write "explanation_of_diagnosis_and_treatment" in ALL requested languages (each 2-3 short lines) using the anti-jargon rules.
                   - Line 1: What treatment was done in hospital (surgery/procedure/medicines).
                   - Line 2: Why it was done / how it helps.
                   - Line 3 (optional): What to expect next / precautions if clearly mentioned.
                7) Medical history MUST be returned as a SINGLE multi-line string field (NOT an array):
                   - Field name: medical_history_text
                   - Each item on a new line, starting with "- "
                   - Format: "- <condition in simple words> - <duration>"
                   - If no medical history is mentioned, return "Not mentioned".
                8) Potential red flags MUST be returned as a SINGLE multi-line string field (NOT an array):
                   - Field name: potential_red_flags_text
                   - Each red flag on a new line, starting with "- "
                   - If no red flags are found, return "None identified".

                OUTPUT STRUCTURE (MUST be valid JSON)
                Return ONLY a JSON object with this exact structure:

                {{
                  "name_and_age": "Patient Name, Age years",
                  "gender": "Male/Female/Other",
                  "admission_date_time": "DD/MM/YYYY HH:MM AM/PM",
                  "discharge_date_time": "DD/MM/YYYY HH:MM AM/PM",
                  "total_duration_hours": "XX hours",
                  "diagnosis": "ONLY the final diagnosis/problem in simple words (1-2 short lines; no treatment details)",
                  "explanation_of_diagnosis_and_treatment": {{
                    "English": "2-3 short lines (treatment-focused, no jargon, do not repeat diagnosis sentence)",
                    "Hindi": "2-3 short lines (treatment-focused, no jargon, do not repeat diagnosis sentence)",
                    "Marathi": "2-3 short lines (treatment-focused, no jargon, do not repeat diagnosis sentence)"
                  }},
                  "medical_history_text": "- Condition 1 - Duration 1\\n- Condition 2 - Duration 2",
                  "potential_red_flags_text": "- Red flag 1\\n- Red flag 2"
                }}

                IMPORTANT
                - Return ONLY valid JSON. No extra text.
                - Use the language name as the key (English/Hindi/Marathi).
                - Keep explanations jargon-free and short.
                - If information is not available, use "Not mentioned" or "N/A".
                - medical_history_text and potential_red_flags_text must be multi-line strings using \\n for new lines.
                """

                # 4. Upload & Generate
                # We pass system_instruction into the Model constructor for best results
                model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                
                sample_file = genai.upload_file(path=tmp_path, display_name="Claim Doc")

                response = model.generate_content(
                    [sample_file, user_prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                data = json.loads(response.text)
                gen_time = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")

                # 5. Build HTML Report (Using Your specific JSON Keys)
                html_report = f"""
                <div class="report-container">
                    <div class="brand-text">moneyplus</div>
                    <div class="main-title">Moneyplus Discharge Summary AI Auditor</div>
                    <div class="sub-title">AI-assisted discharge summary extraction for claims review</div>
                    
                    <div class="claim-header">
                        Claim Intimation No: {claim_id}
                    </div>

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

                    <div class="footer">
                        Disclaimer: This is an AI generated summary and may not be accurate. Please verify with original documents.
                    </div>
                </div>
                """

                # 6. Render Report & Print Button
                st.markdown("---")
                
                c1, c2 = st.columns(2)
                
                with c1:
                    components.html(
                        f"""
                        <script>
                        function printReport() {{
                            window.parent.document.title = "Audit_{claim_id}";
                            window.parent.print();
                        }}
                        </script>
                        <button onclick="printReport()" style="
                            background: #0056b3; color: white; border: none; padding: 10px 20px; 
                            border-radius: 5px; font-weight: bold; cursor: pointer; width: 100%;">
                            🖨️ Print / Save as PDF
                        </button>
                        """,
                        height=50
                    )

                with c2:
                    st.download_button(
                        label="📥 Download Raw HTML",
                        data=html_report,
                        file_name=f"Audit_{claim_id}.html",
                        mime="text/html"
                    )

                st.markdown(html_report, unsafe_allow_html=True)
                os.remove(tmp_path)

            except Exception as e:
                st.error(f"An error occurred: {e}")
