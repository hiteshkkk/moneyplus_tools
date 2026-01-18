import streamlit as st
import json
from db import get_audit_by_claim
from auth import check_password

st.set_page_config(page_title="View Audit", page_icon="👁️", layout="wide")
check_password()

st.title("👁️ Audit Report Viewer")

claim_id = st.text_input("Enter Claim ID / Reference Number", placeholder="e.g. CLM12345")

if claim_id:
    df = get_audit_by_claim(claim_id)
    
    if df.empty:
        st.error(f"❌ No audit found for Claim ID: {claim_id}")
    else:
        # Extract data from the row
        audit_data = df.iloc[0]
        report = json.loads(audit_data['audit_json'])
        
        st.success(f"✅ Report Found (Audited on: {audit_data['timestamp']})")
        st.divider()

        # --- BEAUTIFUL UI LAYOUT ---
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Patient", report['patient_details']['name_and_age'])
            st.write(f"**Gender:** {report['patient_details']['gender']}")
            st.write(f"**Hospital:** {audit_data['hospital_name']}")
        
        with col2:
            st.metric("Total Bill", f"₹{audit_data['total_bill']:,.2f}")
            st.write(f"**Admission:** {report['timing']['admission']}")
            st.write(f"**Discharge:** {report['timing']['discharge']}")

        st.subheader("📋 Diagnosis & Clinical Summary")
        st.info(report['clinical_summary']['diagnosis'])
        
        # Display Red Flags with color coding
        red_flags = report['clinical_summary']['potential_red_flags']
        if report['clinical_summary']['red_flags_count'] > 0:
            st.error(f"🚩 Potential Red Flags Detected:\n{red_flags}")
        else:
            st.success("✅ No major red flags identified.")

        # Multilingual Explanations in Expanders
        st.subheader("🌍 Patient Explanations")
        with st.expander("English Explanation"):
            st.write(report['multilingual_explanation']['English'])
            
        with st.expander("Hindi (हिंदी)"):
            st.write(report['multilingual_explanation']['Hindi'])
            
        with st.expander("Marathi (मराठी)"):
            st.write(report['multilingual_explanation']['Marathi'])

        # Option to download the raw JSON for advanced troubleshooting
        st.download_button("📥 Download Raw Audit Data", audit_data['audit_json'], f"audit_{claim_id}.json", "application/json")
