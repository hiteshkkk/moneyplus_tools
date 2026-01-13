import streamlit.components.v1 as components
import json

def render(token_headers):
    st.markdown("## 🔍 KYC Status Check (Client-Side)")
    st.caption("Runs in your browser to bypass IP blocks. (Note: Logging disabled)")
    
    with st.form("kyc_form"):
        pan_input = st.text_input("Enter PAN Number", placeholder="ABCDE1234F", max_chars=10)
        pan_number = pan_input.upper() if pan_input else ""
        submitted = st.form_submit_button("Check Status")
    
    if submitted:
        if not pan_number:
            st.warning("Please enter a PAN number.")
            return

        # We inject HTML + JavaScript to make the request from YOUR browser
        # This bypasses the Streamlit Cloud IP block.
        
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{ font-family: sans-serif; padding: 10px; }}
            .status-box {{ padding: 15px; border-radius: 8px; border: 1px solid #ddd; background: #f9fafb; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ text-align: left; padding: 8px; background: #eee; border-bottom: 2px solid #ddd; font-size: 14px; }}
            td {{ padding: 8px; border-bottom: 1px solid #eee; font-size: 14px; }}
            .error {{ color: #d32f2f; font-weight: bold; }}
            .success {{ color: #2e7d32; font-weight: bold; }}
            .loader {{ font-style: italic; color: #666; }}
        </style>
        </head>
        <body>
            <div id="status" class="loader">🔄 Connecting to NSE from your browser...</div>
            <div id="result"></div>

            <script>
                async function checkKYC() {{
                    const url = "https://www.nseinvest.com/nsemfdesk/api/v2/utility/KYC_CHECK";
                    const payload = {{ "pan_no": "{pan_number}" }};
                    
                    try {{
                        const response = await fetch(url, {{
                            method: "POST",
                            headers: {{
                                "Content-Type": "application/json",
                                "Accept": "application/json"
                            }},
                            body: JSON.stringify(payload)
                        }});

                        if (!response.ok) {{
                            throw new Error("Server Error: " + response.status);
                        }}

                        const data = await response.json();
                        
                        // Build Table
                        let tableHtml = "<table><tr><th>Field</th><th>Value</th></tr>";
                        
                        // Priority Fields
                        const priorities = ["PAN NO", "KYC STATUS", "KYC STATUS REMARK", "NAME"];
                        priorities.forEach(key => {{
                            if (data[key]) {{
                                tableHtml += `<tr><td><strong>${{key}}</strong></td><td>${{data[key]}}</td></tr>`;
                            }}
                        }});
                        
                        // Other Fields
                        for (const [key, value] of Object.entries(data)) {{
                            if (!priorities.includes(key)) {{
                                tableHtml += `<tr><td>${{key}}</td><td>${{value}}</td></tr>`;
                            }}
                        }}
                        tableHtml += "</table>";

                        document.getElementById("status").innerHTML = '<span class="success">✅ Request Successful</span>';
                        document.getElementById("result").innerHTML = tableHtml;

                    }} catch (error) {{
                        console.error(error);
                        let msg = error.message;
                        if (msg.includes("Failed to fetch")) {{
                            msg = "⚠️ Browser Blocked (CORS): The NSE server blocked this request because it didn't come from their own website. <br><br><b>Solution:</b> You must use a Proxy (Option 1) or Run Locally (Option 3).";
                        }}
                        document.getElementById("status").innerHTML = `<div class="status-box error">${{msg}}</div>`;
                    }}
                }}
                
                // Run immediately
                checkKYC();
            </script>
        </body>
        </html>
        """
        
        # Render the JS component with enough height to show the table
        components.html(html_code, height=600, scrolling=True)
