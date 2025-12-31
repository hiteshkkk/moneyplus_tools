# --- 1. SHARED CSS STYLING ---
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
    /* We keep the background/text colors specific so they pop in BOTH modes */
    .badge-success { 
        background-color: #d1e7dd; color: #0f5132; 
        padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block;
    }
    .badge-danger { 
        background-color: #f8d7da; color: #721c24; 
        padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block;
    }
    .badge-warning { 
        background-color: #fff3cd; color: #856404; 
        padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block;
    }
    .badge-info { 
        background-color: #cff4fc; color: #055160; 
        padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.85em; display: inline-block;
    }
</style>
"""
