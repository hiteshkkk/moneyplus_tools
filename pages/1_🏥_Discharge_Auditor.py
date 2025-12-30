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
# We inject this CSS so the 'Print' view looks exactly like your PDF reference
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

    /* Section Headers (Uppercase like PDF) */
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

    /* Print Specifics: Hide Streamlit UI elements when printing */
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

                model = genai.GenerativeModel(model_name)
                sample_file = genai.upload_file(path=tmp_path, display_name="Claim Doc")

                # 2. SYSTEM PROMPT (Strict JSON)
                # We extract the raw data, then Python builds the pretty HTML
                system_prompt = f"""
                You are an expert medical claims processor.
                Task: Extract data from the discharge summary for Claim ID: {claim_id}.
                Return ONLY valid JSON.
                
                OUTPUT STRUCTURE:
                {{
                  "name_and_age": "Patient Name, Age",
                  "gender": "Male/Female",
                  "admission": "DD/MM/YYYY HH:MM AM/PM",
                  "discharge": "DD/MM/YYYY HH:MM AM/PM",
                  "duration": "XX hours",
                  "diagnosis": "Simple summary of final diagnosis",
                  "explanations": {{
                    "English": "Treatment explanation...",
                    "Hindi": "Treatment explanation...",
                    "Marathi": "Treatment explanation..."
                  }},
                  "history": "List of history items (newline separated)",
                  "red_flags": "List of red flags or 'None identified'"
                }}
                """

                # 3. Get Response
                response = model.generate_content(
                    [sample_file, system_prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                data = json.loads(response.text)
                
                # Timestamp for "Generated on"
                gen_time = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")

                # 4. Build HTML Report (Exact PDF Structure)
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
                        <tr><td class="label-col">Admission</td><td>{data.get('admission', 'N/A')}</td></tr>
                        <tr><td class="label-col">Discharge</td><td>{data.get('discharge', 'N/A')}</td></tr>
                        <tr><td class="label-col">Total duration</td><td>{data.get('duration', 'N/A')}</td></tr>
                    </table>
                    <div style="font-size:12px; color:#888; margin-bottom:20px;">Generated: {gen_time}</div>

                    <div class="section-head">DIAGNOSIS (SIMPLE)</div>
                    <div class="content-text">{data.get('diagnosis', 'N/A')}</div>

                    <div class="lang-title">English</div>
                    <div class="expl-sub">Explanation</div>
                    <div class="content-text">{data['explanations'].get('English', 'N/A')}</div>

                    <div class="lang-title">Hindi</div>
                    <div class="expl-sub">Explanation</div>
                    <div class="content-text">{data['explanations'].get('Hindi', 'N/A')}</div>

                    <div class="lang-title">Marathi</div>
                    <div class="expl-sub">Explanation</div>
                    <div class="content-text">{data['explanations'].get('Marathi', 'N/A')}</div>

                    <div class="section-head">HISTORY</div>
                    <div class="content-text" style="white-space: pre-line;">{data.get('history', 'Not mentioned')}</div>

                    <div class="section-head" style="color: #d32f2f;">POTENTIAL RED FLAGS</div>
                    <div class="content-text" style="white-space: pre-line;">{data.get('red_flags', 'None identified')}</div>

                    <div class="footer">
                        Disclaimer: This is an AI generated summary and may not be accurate. Please verify with original documents.
                    </div>
                </div>
                """

                # 5. Render Report & Print Button
                st.markdown("---")
                
                # Two buttons: One for Print/PDF, One for HTML download
                c1, c2 = st.columns(2)
                
                with c1:
                    # Javascript Button for "Print / Save as PDF"
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

                # Show the report on screen
                st.markdown(html_report, unsafe_allow_html=True)
                
                os.remove(tmp_path)

            except Exception as e:
                st.error(f"An error occurred: {e}")
