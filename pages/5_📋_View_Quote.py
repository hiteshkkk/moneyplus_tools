import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG (Public Access - No Password Check) ---
st.set_page_config(page_title="View Quote", page_icon="📋", layout="wide")

# --- 2. GET QUOTE ID FROM URL ---
query_params = st.query_params
quote_id = query_params.get("id", None)

if not quote_id:
    st.warning("⚠️ No Quote ID found. Please check the link.")
    st.stop()

# --- 3. CONNECT & FETCH DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # A. Fetch the specific Quote from 'Generated_Quotes'
    # We read the whole sheet and filter. (Efficient enough for <5000 rows)
    df_quotes = conn.read(worksheet="Generated_Quotes")
    
    # Filter by Quote ID
    # Convert ID to string to be safe
    df_quotes['Quote_ID'] = df_quotes['Quote_ID'].astype(str)
    quote_data = df_quotes[df_quotes['Quote_ID'] == str(quote_id)]

    if quote_data.empty:
        st.error("❌ Invalid Quote ID. This quote does not exist.")
        st.stop()
    
    # Get the single row as a dictionary
    q = quote_data.iloc[0].fillna("")

    # B. Identify Selected Plans
    selected_plans = []
    premiums = []
    notes = []
    
    for i in range(1, 6):
        p_name = q.get(f"Plan_{i}")
        if p_name and str(p_name).strip() != "":
            selected_plans.append(p_name)
            premiums.append(q.get(f"Prem_{i}", ""))
            notes.append(q.get(f"Note_{i}", ""))

    # C. Fetch Features from 'Plans_Master' for the selected plans
    # Header is row 3 (index 2)
    df_master = conn.read(worksheet="Plans_Master", header=2)
    
    # 1. Get Feature Names (Col A, usually named 'Feature Code' or similar based on your image)
    # Based on your image, Features are in Col B? "Plan Name >>" is C3. 
    # Let's look for the column that holds features. Usually it's the first or second column.
    # We will assume Column 1 (Index 1) is Feature Name based on your logic "Features in Col A... Plan names in Row 3"
    # Actually, looking at your image, Col A is Feature Code (F2), Col B is "Room Rent".
    
    # Normalize column names to find the 'Feature Name' column
    # We'll take the 2nd column (Index 1) as the Feature Name
    feature_col_name = df_master.columns[1] 
    
    # Filter Master: Keep 'Feature Name' col and 'Selected Plan' cols
    cols_to_keep = [feature_col_name] + [p for p in selected_plans if p in df_master.columns]
    
    df_features = df_master[cols_to_keep].copy()
    
    # Handle Blanks -> "Not Specified"
    df_features = df_features.fillna("Not Specified")

except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

# --- 4. RENDER UI (Responsive HTML) ---

# CSS for nice printing and mobile view
st.markdown("""
<style>
    @media print {
        .stApp > header { display: none; }
        .sidebar { display: none; }
        .no-print { display: none; }
        body { padding-top: 0; }
    }
    .quote-container {
        font-family: 'Helvetica Neue', sans-serif;
        max-width: 1000px;
        margin: auto;
        padding: 20px;
        background: white;
        border: 1px solid #eee;
        border-radius: 8px;
    }
    .header-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #0056b3;
        margin-bottom: 25px;
    }
    .client-title { font-size: 24px; font-weight: bold; color: #333; margin: 0; }
    .meta-text { font-size: 14px; color: #666; margin-top: 5px; }
    
    /* Comparison Table Styling */
    .comp-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .comp-table th { background: #004085; color: white; padding: 10px; text-align: left; font-size: 14px; }
    .comp-table td { padding: 10px; border-bottom: 1px solid #ddd; font-size: 13px; vertical-align: top; }
    .feature-name { font-weight: bold; color: #444; width: 25%; }
    .highlight-row { background-color: #f9f9f9; }
    
    /* Premium Box */
    .prem-box {
        background: #e3f2fd;
        padding: 10px;
        border-radius: 4px;
        font-weight: bold;
        color: #0d47a1;
        white-space: pre-line; /* Respects new lines in premium text */
        font-size: 14px;
    }
    .note-text { font-size: 12px; color: #d32f2f; margin-top: 4px; font-style: italic; white-space: pre-line; }

</style>
""", unsafe_allow_html=True)

# Generate HTML Table Rows
table_html = "<table class='comp-table'>"
# Header Row
table_html += "<tr><th>Feature</th>"
for p in selected_plans:
    table_html += f"<th>{p}</th>"
table_html += "</tr>"

# Premium Row (Custom added at top)
table_html += "<tr><td class='feature-name'>💰 PREMIUM ESTIMATE</td>"
for i, p in enumerate(selected_plans):
    table_html += f"<td><div class='prem-box'>{premiums[i]}</div><div class='note-text'>{notes[i]}</div></td>"
table_html += "</tr>"

# Data Rows from Master Sheet
for index, row in df_features.iterrows():
    f_name = row[feature_col_name]
    # Skip rows where feature name is empty or just "Feature Code"
    if str(f_name).strip() == "" or str(f_name) == "nan": continue
    
    table_html += "<tr>"
    table_html += f"<td class='feature-name'>{f_name}</td>"
    
    for p in selected_plans:
        val = row.get(p, "Not Specified")
        table_html += f"<td>{val}</td>"
    table_html += "</tr>"
table_html += "</table>"

# Final Layout
st.markdown(f"""
<div class="quote-container">
    <div style="text-align:right;" class="no-print">
        <button onclick="window.print()" style="padding:8px 15px; background:#0056b3; color:white; border:none; border-radius:4px; cursor:pointer;">🖨️ Print / Save PDF</button>
    </div>
    
    <div class="header-box">
        <div class="client-title">Health Insurance Proposal for {q['Client_Name']}</div>
        <div class="meta-text">
            <strong>Family:</strong> {q['Family']} &nbsp;|&nbsp; 
            <strong>City:</strong> {q['City']} &nbsp;|&nbsp; 
            <strong>Quote ID:</strong> {q['Quote_ID']} &nbsp;|&nbsp; 
            <strong>Date:</strong> {q['Date']}
        </div>
        <div style="font-size:12px; color:#888; margin-top:5px;">Prepared by: {q['RM_Name']} (Moneyplus)</div>
    </div>

    {table_html}

    <div style="margin-top: 30px; font-size: 12px; color: #888; text-align: center;">
        Disclaimer: Premiums are indicative. Features mentioned are subject to policy wordings.
    </div>
</div>
""", unsafe_allow_html=True)
