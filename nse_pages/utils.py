import streamlit as st
import requests
from streamlit.web.server.websocket_headers import _get_websocket_headers

# --- 1. SHARED CSS STYLING (Dark Mode & Auto Width Optimized) ---
TABLE_STYLE = """
<style>
    /* 1. Reset Table Styles to blend with Streamlit Theme */
    table.custom-report {
        width: 100%;
        border-collapse: collapse;
        font-family: "Source Sans Pro", sans-serif; /* Streamlit's font */
        color: inherit; /* <--- KEY CHANGE: Uses Streamlit's Text Color (White/Black) */
    }
    
    /* 2. Row Styling */
    table.custom-report td {
        padding: 10px 12px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2); /* Subtle border visible in both modes */
        vertical-align: middle;
        line-height: 1.5;
    }

    /* 3. Label Column (Left) */
    .field-label {
        font-weight: 600;
        width: 1%;           /* Trick: Shrink column to fit content */
        white-space: nowrap; /* Prevent label text from wrapping */
        padding-right: 20px; /* Spacing between Label and Value */
        opacity: 0.9;        /* Slightly softer contrast */
    }

    /* 4. Value Column (Right) */
    .field-value {
        font-weight: 400;
        width: auto;         /* Take up all remaining space */
        word-break: break-word; /* Wrap long values (like addresses) */
    }

    /* 5. Status Pills (Badges) - High Contrast Preserved */
    .badge-success { background-color: #d1e7dd; color: #0f5132; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block; }
    .badge-danger { background-color: #f8d7da; color: #721c24; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block; }
    .badge-warning { background-color: #fff3cd; color: #856404; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block; }
    .badge-info { background-color: #cff4fc; color: #055160; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block; }
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
    """Generates the HTML table string from a dictionary."""
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
