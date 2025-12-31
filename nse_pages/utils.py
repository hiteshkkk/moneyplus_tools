import streamlit as st
import requests
from streamlit.web.server.websocket_headers import _get_websocket_headers

# --- 1. SHARED CSS STYLING ---
TABLE_STYLE = """
<style>
    table.custom-report {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
    }
    table.custom-report td {
        padding: 12px 15px;
        border-bottom: 1px solid #e0e0e0;
        vertical-align: middle;
    }
    .field-label {
        font-weight: 700;
        color: #31333F;
        width: 35%; /* Fixed width for labels */
    }
    .field-value {
        color: #31333F;
        font-weight: 500;
    }
    /* PILLS / BADGES */
    .badge-success { background-color: #d1e7dd; color: #0f5132; padding: 4px 12px; border-radius: 12px; font-weight: 700; display: inline-block; font-size: 0.9em;}
    .badge-danger { background-color: #f8d7da; color: #721c24; padding: 4px 12px; border-radius: 12px; font-weight: 700; display: inline-block; font-size: 0.9em;}
    .badge-warning { background-color: #fff3cd; color: #856404; padding: 4px 12px; border-radius: 12px; font-weight: 700; display: inline-block; font-size: 0.9em;}
    .badge-info { background-color: #cff4fc; color: #055160; padding: 4px 12px; border-radius: 12px; font-weight: 700; display: inline-block; font-size: 0.9em;}
</style>
"""

# --- 2. FORMATTING FUNCTION ---
def format_html_value(val):
    """Wraps status text in HTML spans for the 'Badge' look."""
    s = str(val)
    if not s or s == "None": return ""
    
    s_lower = s.lower()
    
    # Success / Active
    if any(x in s_lower for x in ['success', 'active', 'approved', 'yes', 'verified', 'svalid']):
        return f'<span class="badge-success">{s}</span>'
    
    # Error / Reject
    if any(x in s_lower for x in ['fail', 'reject', 'error', 'no', 'invalid', 'closed']):
        return f'<span class="badge-danger">{s}</span>'
        
    # Warning / Pending
    if any(x in s_lower for x in ['pending', 'wait', 'hold']):
        return f'<span class="badge-warning">{s}</span>'
    
    # Info (e.g. modes)
    if any(x in s_lower for x in ['electronic', 'physical']):
        return f'<span class="badge-info">{s}</span>'
    
    return s

# --- 3. TABLE GENERATOR FUNCTION ---
def render_custom_table(data_dict, priority_fields=None):
    """
    Generates the HTML table string from a dictionary.
    """
    html_rows = ""
    processed_keys = set()
    
    # Clean Data (Remove empty/None)
    clean_data = {}
    for k, v in data_dict.items():
        if v is None or str(v).strip() in ["", "None"]: continue
        clean_k = k.replace("_", " ").upper()
        clean_data[clean_k] = v

    # 1. Render Priority Fields
    if priority_fields:
        for field in priority_fields:
            # Flexible matching (exact match or key contains field name)
            for k, v in clean_data.items():
                if k == field and k not in processed_keys:
                    html_rows += f"<tr><td class='field-label'>{k}</td><td class='field-value'>{format_html_value(v)}</td></tr>"
                    processed_keys.add(k)

    # 2. Render Remaining Fields (Sorted)
    for k in sorted(clean_data.keys()):
        if k not in processed_keys:
            v = clean_data[k]
            html_rows += f"<tr><td class='field-label'>{k}</td><td class='field-value'>{format_html_value(v)}</td></tr>"

    return f"<table class='custom-report'>{html_rows}</table>"

# --- 4. NETWORK INFO HELPER (Shared) ---
def get_network_details():
    details = {}
    try:
        details['Streamlit_Server_IP'] = requests.get('https://api.ipify.org').text
    except:
        details['Streamlit_Server_IP'] = "Unknown"
    try:
        headers = _get_websocket_headers()
        if headers:
            details['User_Public_IP'] = headers.get("X-Forwarded-For", "Hidden/Localhost")
            details['Browser_Info'] = headers.get("User-Agent", "Unknown")
        else:
            details['User_Public_IP'] = "Localhost"
            details['Browser_Info'] = "Unknown"
    except:
        details['User_Public_IP'] = "Error"
        details['Browser_Info'] = "Error"
    return details
