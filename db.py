import sqlite3
import json
import datetime
import pandas as pd
import os

# --- 1. Database Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "moneyplus.db")

def get_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") # Speed boost
    return conn

def get_ist_now():
    """Returns IST time for accurate India-based logging."""
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)

def init_db():
    """Initializes ALL tables. Run this once."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Meeting Notes Table
    c.execute('''CREATE TABLE IF NOT EXISTS meeting_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        client_name TEXT,
        rm_name TEXT,
        meeting_date TEXT,
        location TEXT,
        raw_notes TEXT,
        crm_version TEXT,
        client_version TEXT
    )''')

    # 2. Discharge Auditor Table (Simple JSON Text Structure)
    c.execute('''CREATE TABLE IF NOT EXISTS discharge_audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        claim_id TEXT,
        audit_json TEXT
    )''')

    # 3. NSE Logs Table (Unified + Payload Support)
    # Note: We added 'input_payload' to store the request body
    c.execute('''CREATE TABLE IF NOT EXISTS nse_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        log_type TEXT,        -- e.g. 'KYC', 'UCC'
        input_key TEXT,       -- e.g. PAN Number or UCC ID (Searchable)
        input_payload TEXT,   -- The full JSON request sent to NSE
        api_response TEXT,    -- The full JSON response from NSE
        user_ip TEXT,
        browser_info TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with all tables.")

# --- SAVE FUNCTIONS ---

def save_meeting_note(data):
    """Saves Meeting Notes."""
    try:
        conn = get_connection()
        c = conn.cursor()
        timestamp = get_ist_now().strftime("%d-%m-%Y %I:%M %p")
        c.execute('''INSERT INTO meeting_notes 
                  (timestamp, client_name, rm_name, meeting_date, location, raw_notes, crm_version, client_version) 
                  VALUES (?,?,?,?,?,?,?,?)''',
                  (timestamp, data['client_name'], data['rm_name'], str(data['date']), 
                   data['location'], data['input_text'], data['crm_response'], data['client_version']))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Note Save Error: {e}")
        return False

def save_discharge_audit(claim_id, audit_data):
    """Saves Discharge Audits."""
    try:
        conn = get_connection()
        c = conn.cursor()
        timestamp = get_ist_now().strftime("%d-%m-%Y %I:%M %p")
        c.execute('INSERT INTO discharge_audits (timestamp, claim_id, audit_json) VALUES (?,?,?)',
                  (timestamp, claim_id, json.dumps(audit_data)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Audit Save Error: {e}")
        return False

def log_nse_event(log_type, input_key, payload, response, net_info):
    """Logs NSE events with both Request (Payload) and Response."""
    try:
        conn = get_connection()
        c = conn.cursor()
        timestamp = get_ist_now().strftime("%d-%m-%Y %I:%M %p")
        
        c.execute('''INSERT INTO nse_logs 
                  (timestamp, log_type, input_key, input_payload, api_response, user_ip, browser_info) 
                  VALUES (?,?,?,?,?,?,?)''',
                  (timestamp, log_type, str(input_key), 
                   json.dumps(payload),  # Store request
                   json.dumps(response), # Store response
                   net_info.get('User_Public_IP'), net_info.get('Browser_Info')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ NSE Log Error: {e}")
        return False

# --- READ FUNCTIONS (For Admin Panel) ---

def get_table_data(table_name):
    conn = get_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY id DESC", conn)
    conn.close()
    return df

def get_audit_by_claim(claim_id):
    conn = get_connection()
    query = "SELECT * FROM discharge_audits WHERE claim_id = ? ORDER BY id DESC LIMIT 1"
    df = pd.read_sql_query(query, conn, params=(claim_id,))
    conn.close()
    return df

if __name__ == "__main__":
    init_db()
