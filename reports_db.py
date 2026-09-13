"""
reports_db.py
Dedicated Database Layer for Storing & Managing Citizen Hazard Reports in reports.db.

Kept strictly independent from ner_vision.db to isolate community feedback,
NLP verification metrics, and administrative moderation logs.
"""

import sqlite3
import json
from datetime import datetime, timezone

REPORTS_DB_PATH = "reports.db"


def get_reports_db():
    conn = sqlite3.connect(REPORTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_reports_db():
    conn = get_reports_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS citizen_reports (
        id TEXT PRIMARY KEY,
        location_id TEXT,
        location_name TEXT,
        lat REAL,
        lng REAL,
        description TEXT,
        reported_severity TEXT,
        media_url TEXT,
        is_emergency INTEGER,
        is_verified INTEGER DEFAULT 0,
        verification_score REAL DEFAULT 0.0,
        verification_status TEXT DEFAULT 'UNVERIFIED',
        verification_reasons TEXT,
        admin_override INTEGER DEFAULT 0,
        timestamp TEXT
    );
    """)
    conn.commit()
    conn.close()


def save_report(report_id, location_id, location_name, lat, lng, description,
                reported_severity, media_url, is_emergency, ver_res):
    conn = get_reports_db()
    reasons_str = json.dumps(ver_res.get("verification_reasons", []))
    
    conn.execute("""
    INSERT INTO citizen_reports (
        id, location_id, location_name, lat, lng, description,
        reported_severity, media_url, is_emergency, is_verified,
        verification_score, verification_status, verification_reasons, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id, location_id, location_name, lat, lng, description,
        reported_severity, media_url, 1 if is_emergency else 0,
        1 if ver_res.get("is_verified") else 0,
        ver_res.get("verification_score", 0.0),
        ver_res.get("verification_status", "UNVERIFIED"),
        reasons_str,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()


def fetch_all_reports(limit=100):
    conn = get_reports_db()
    rows = conn.execute(
        "SELECT * FROM citizen_reports ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["verification_reasons"] = json.loads(d["verification_reasons"])
        except Exception:
            d["verification_reasons"] = [d["verification_reasons"]] if d["verification_reasons"] else []
        out.append(d)
    return out


def update_report_status(report_id, is_verified, admin_override=1):
    conn = get_reports_db()
    status = "VERIFIED_REAL" if is_verified else "FLAGGED_SPAM"
    conn.execute("""
    UPDATE citizen_reports
    SET is_verified = ?, verification_status = ?, admin_override = ?
    WHERE id = ?
    """, (1 if is_verified else 0, status, admin_override, report_id))
    conn.commit()
    conn.close()
