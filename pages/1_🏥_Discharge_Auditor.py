import streamlit as st
import google.generativeai as genai
import tempfile
import os
import json

# --- 1. SETUP API KEY SAFELY ---
API_KEY = None

# First, try to get it from Cloud Secrets (or local secrets.toml)
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.image("https://moneyplus.in/wp-content/uploads/2019/01/moneyplus-logo-3-300x277.png", width=100)
    st.title("Settings")
    
    # If key wasn't found in secrets, ask for it here
    if not API_KEY:
        API_KEY = st.text_input("Enter Gemini API Key", type="password")
        if not API_KEY:
             st.warning("⚠️ Please enter your API Key to continue.")
    else:
        st.success("API Key Loaded Securely")

    # --- MODEL SELECTION ---
    # Updated to Gemini 2.5 Flash as requested
    model_name = "gemini-2.5-flash"
    st.caption(f"Model: {model_name}")

# --- CONFIGURE GEMINI ---
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- MAIN PAGE UI ---
st.title("Moneyplus Discharge Summary Auditor")
st.markdown("Submit the claim intimation number and upload the PDF below.")

# Custom CSS for the Report
st.markdown("""
    <style>
    .report-container {
        border: 1px solid #ddd;
        padding: 30px;
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        color: #333;
        font-family: 'Segoe UI', sans-serif;
    }
    .report-header {
        border-bottom: 2px solid #0056b3;
        padding-bottom: 15px;
        margin-bottom: 25px;
        color: #0056b3;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .section-title {
        background-color: #f0f7ff;
        padding: 10px 15px;
        border-left: 5px solid #0056b3;
        color: #004494;
        margin-top: 25px;
        margin-bottom: 10px;
        font-weight: bold;
        font-size: 1.1em;
    }
    .info-table { width: 100%; border-collapse: collapse; }
    .info-table td { padding: 10px; border-bottom: 1px solid #eee; vertical-align: top; }
    .label { font-weight: bold; color: #555; width: 30%; }
    
    .flag-box {
        background-color: #fff5f5;
        border: 1px solid #ffcccc;
        padding: 15px;
        border-radius: 5px;
        color: #cc0000;
        white-space: pre-line;
    }
    .lang-box {
        margin-bottom: 10px;
        padding: 10px;
        background: #fafafa;
        border-left: 3px solid #ccc;
    }
    .lang-label { font-size: 0.8em; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 2])
with col1:
    claim_id = st.text_input("Claim Intimation No.", placeholder="e.g. CLM-2025-001")
with col2:
    uploaded_file = st.file_uploader("Upload Discharge Summary", type=["pdf"])

# --- PROCESSING LOGIC ---
if st.button("Generate Audit Report", type="primary"):
    if not API_KEY:
        st.error("🚨 API Key is missing. Please check your secrets or sidebar input.")
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

                model = genai.GenerativeModel(model_name)
                sample_file = genai.upload_file(path=tmp_path, display_name="Claim Doc")

                # 2. SYSTEM PROMPT (Strict JSON)
                system_prompt = f"""
                You are an expert medical claims processor.
                NON-NEGOTIABLE RULES:
                - Use ONLY the attached discharge summary document(s) as the source of truth.
                - Return ONLY a single valid JSON object.
                - Use EXACTLY the keys and structure specified below.
                
                Claim Intimation No: "{claim_id}"
                
                TASK:
                Read the attached discharge summary and return ONLY a valid JSON object in the exact structure provided below.
                
                GOALS:
                - Extract claim-critical details, final diagnosis, treatment, and red flags.
                - Provide layperson explanations in English, Hindi, and Marathi.
                
                OUTPUT STRUCTURE (JSON ONLY):
                {{
                  "name_and_age": "Patient Name, Age years",
                  "gender": "Male/Female/Other",
                  "admission_date_time": "DD/MM/YYYY HH:MM AM/PM",
                  "discharge_date_time": "DD/MM/YYYY HH:MM AM/PM",
                  "total_duration_hours": "XX hours",
                  "diagnosis": "ONLY the final diagnosis/problem in simple words",
                  "explanation_of_diagnosis_and_treatment": {{
                    "English": "2-3 short lines",
                    "Hindi": "2-3 short lines",
                    "Marathi": "2-3 short lines"
                  }},
                  "medical_history_text": "- Condition 1 - Duration 1\\n- Condition 2 - Duration 2",
                  "potential_red_flags_text": "- Red flag 1\\n- Red flag 2"
                }}
                """

                # 3. Get Response as JSON
                response = model.generate_content(
                    [sample_file, system_prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # 4. Parse JSON
                data = json.loads(response.text)

                # 5. Build HTML Report
                html_report = f"""
                <div class="report-container">
                    <div class="report-header">
                        <div>
                            <h2 style="margin:0;">Clinical Audit Summary</h2>
                            <small>Claim Intimation: <strong>{claim_id}</strong></small>
                        </div>
                        <div style="text-align:right; font-size:0.9em; color:#666;">
                            Generated by Moneyplus AI<br>
                            Status: <span style="color:green; font-weight:bold;">Processed</span>
                        </div>
                    </div>

                    <div class="section-title">Patient & Admission Details</div>
                    <table class="info-table">
                        <tr><td class="label">Patient:</td><td>{data.get('name_and_age', 'N/A')}</td></tr>
                        <tr><td class="label">Gender:</td><td>{data.get('gender', 'N/A')}</td></tr>
                        <tr><td class="label">Admission:</td><td>{data.get('admission_date_time', 'N/A')}</td></tr>
                        <tr><td class="label">Discharge:</td><td>{data.get('discharge_date_time', 'N/A')}</td></tr>
                        <tr><td class="label">Duration:</td><td>{data.get('total_duration_hours', 'N/A')}</td></tr>
                    </table>

                    <div class="section-title">Diagnosis</div>
                    <div style="font-size: 1.1em; font-weight: bold; padding: 10px;">
                        {data.get('diagnosis', 'N/A')}
                    </div>

                    <div class="section-title">Treatment Explanation (Multi-Language)</div>
                    <div class="lang-box">
                        <div class="lang-label">English</div>
                        {data['explanation_of_diagnosis_and_treatment'].get('English', 'N/A')}
                    </div>
                    <div class="lang-box">
                        <div class="lang-label">Hindi</div>
                        {data['explanation_of_diagnosis_and_treatment'].get('Hindi', 'N/A')}
                    </div>
                    <div class="lang-box">
                        <div class="lang-label">Marathi</div>
                        {data['explanation_of_diagnosis_and_treatment'].get('Marathi', 'N/A')}
                    </div>

                    <div class="section-title">Medical History</div>
                    <div style="white-space: pre-line; padding: 10px;">
                        {data.get('medical_history_text', 'None mentioned')}
                    </div>

                    <div class="section-title" style="border-left-color: #cc0000; color: #cc0000; background-color: #fff5f5;">
                        ⚠ Potential Red Flags
                    </div>
                    <div class="flag-box">
                        {data.get('potential_red_flags_text', 'None identified')}
                    </div>

                    <div style="margin-top: 30px; text-align: center; font-size: 0.8em; color: #888;">
                        Disclaimer: AI-generated report. Please verify with original documents.
                    </div>
                </div>
                """

                # 6. Display & Download
                st.markdown("---")
                st.markdown(html_report, unsafe_allow_html=True)
                
                st.download_button(
                    label="📥 Download Report as HTML",
                    data=html_report,
                    file_name=f"Audit_Report_{claim_id}.html",
                    mime="text/html"
                )

                os.remove(tmp_path)

            except Exception as e:
                st.error(f"An error occurred: {e}")
