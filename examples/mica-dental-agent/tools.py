import json
from pathlib import Path
import sqlite3



# Determine the path to dental.db relative to this script
ROOT = Path(__file__).parent
DB_DIR = ROOT / "data"
DB_PATH = DB_DIR / "dental.db"


# Ensure the data directory exists and initialize the database
DB_DIR.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    name TEXT,
    contact TEXT,
    dob TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    datetime TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(id)
)
""")



conn.commit()
conn.close()

# --- Tool functions for MICA agents ---

def get_conn():
    """Open a connection to the SQLite database."""
    return sqlite3.connect(str(DB_PATH))


def action_create_patient_record(name, contact_info=None, date_of_birth=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO patients(name,contact,dob) VALUES (?,?,?)",
                (name, contact_info, date_of_birth))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    # *** Print JSON to stdout, not just return it ***
    result = {"patient_id": pid, "text": f"Created patient #{pid} for {name}"}
    print(json.dumps(result))
    return result


def action_check_availability(appointment_datetime, patient_id=None):
    """Return a JSON object indicating whether the time slot is free."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM appointments WHERE datetime = ?",
        (appointment_datetime,)
    )
    booked_count = cur.fetchone()[0]
    conn.close()

    result = {
        "available": (booked_count == 0)
    }
    print(json.dumps(result))
    return result
  

def action_schedule_appointment(name=None, appointment_datetime=None):
    """Schedule an appointment for an existing patient."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE name = ?", (name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        result = {
            "error": f"No patient named '{name}' found. Please create a record first."
        }
        print(json.dumps(result))
        return result

    patient_id = row[0]
    cur.execute(
        "INSERT INTO appointments(patient_id, datetime) VALUES (?, ?)",
        (patient_id, appointment_datetime)
    )
    conn.commit()
    appt_id = cur.lastrowid
    conn.close()

    result = {
      "data": {
        "name": name,
        "appointment_datetime": appointment_datetime
      },
      "appointment_id": appt_id,
      "text": f"Appointment #{appt_id} scheduled for {name} on {appointment_datetime}."
    }
    print(json.dumps(result))
    return result



def action_get_patient_info(name=None, patient_id=None):
    """Retrieve patient's personal and appointment information."""
    conn = get_conn()
    cur = conn.cursor()
    if name:
        cur.execute(
            "SELECT id, name, contact, dob FROM patients WHERE name = ?",
            (name,)
        )
    elif patient_id:
        cur.execute(
            "SELECT id, name, contact, dob FROM patients WHERE id = ?",
            (patient_id,)
        )
    else:
        conn.close()
        result = {"text": "Error: please provide a patient name or ID."}
        print(json.dumps(result))
        return result

    row = cur.fetchone()
    if not row:
        conn.close()
        result = {"text": f"Error: No patient found with name or ID '{name or patient_id}'."}
        print(json.dumps(result))
        return result

    pid, pname, contact, dob = row
    cur.execute(
        "SELECT id, datetime FROM appointments WHERE patient_id = ?",
        (pid,)
    )
    appts = [{"appointment_id": aid, "datetime": dt} for aid, dt in cur.fetchall()]

    conn.close()
    result = {
        "patient_id": pid,
        "name": pname,
        "contact": contact,
        "dob": dob,
        "appointments": appts
    }
    print(json.dumps(result))
    return result