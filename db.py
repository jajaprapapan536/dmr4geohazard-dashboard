"""
Database access and management module for Geohazard Dashboard using SQLite.
"""
import sqlite3
import json
import os
import pandas as pd
from datetime import datetime
from config import DB_PATH, UPLOADS_DIR
import coordinates

# Ensure upload subdirectories exist
PHOTOS_DIR = os.path.join(UPLOADS_DIR, "photos")
ONEPAGE_DIR = os.path.join(UPLOADS_DIR, "one_page")
REPORTS_DIR = os.path.join(UPLOADS_DIR, "reports")
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(ONEPAGE_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_fiscal_year(date_str: str) -> int:
    """
    Calculate Thai fiscal year (พ.ศ.) from date string (YYYY-MM-DD).
    Thai fiscal year starts Oct 1 and ends Sep 30.
    """
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        buddhist_year = dt.year + 543
        if dt.month >= 10:
            return buddhist_year + 1
        return buddhist_year
    except Exception:
        now = datetime.now()
        by = now.year + 543
        return by + 1 if now.month >= 10 else by


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_code TEXT UNIQUE,
        incident_date TEXT NOT NULL,
        fiscal_year INTEGER,
        utm_zone INTEGER NOT NULL DEFAULT 47,
        utm_e REAL NOT NULL,
        utm_n REAL NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        location_name TEXT NOT NULL,
        subdistrict TEXT NOT NULL,
        district TEXT NOT NULL,
        province TEXT NOT NULL,
        hazard_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        status TEXT NOT NULL,
        inspector_name TEXT,
        geological_unit TEXT,
        details TEXT,
        one_page_path TEXT,
        one_page_name TEXT,
        report_file_path TEXT,
        report_file_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        caption TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE
    )
    """)

    # Check and migrate columns if missing
    cursor.execute("PRAGMA table_info(inspections)")
    cols = [col["name"] for col in cursor.fetchall()]

    new_cols = {
        "fiscal_year": "INTEGER",
        "one_page_path": "TEXT",
        "one_page_name": "TEXT",
        "report_file_path": "TEXT",
        "report_file_name": "TEXT"
    }

    for col_name, col_type in new_cols.items():
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE inspections ADD COLUMN {col_name} {col_type}")

    # Backfill fiscal_year for existing rows if NULL
    cursor.execute("SELECT id, incident_date FROM inspections WHERE fiscal_year IS NULL")
    rows = cursor.fetchall()
    for r in rows:
        fy = calculate_fiscal_year(r["incident_date"])
        cursor.execute("UPDATE inspections SET fiscal_year = ? WHERE id = ?", (fy, r["id"]))

    conn.commit()
    conn.close()


def generate_incident_code(fiscal_year: int = None) -> str:
    """Generate a guaranteed unique incident code."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM inspections")
    max_id = cursor.fetchone()[0] or 0
    next_id = max_id + 1
    conn.close()
    
    fy_str = str(fiscal_year) if fiscal_year else str(datetime.now().year + 543)
    return f"GEO-S4-{fy_str}-{next_id:04d}"


def add_inspection(
    incident_date: str,
    utm_zone: int,
    utm_e: float,
    utm_n: float,
    location_name: str,
    subdistrict: str = "-",
    district: str = "-",
    province: str = "-",
    hazard_type: str = "หลุมยุบ",
    severity: str = "ปานกลาง (Medium - ส่งผลกระทบพื้นที่การเกษตร/สิ่งปลูกสร้างเล็กน้อย)",
    status: str = "ตรวจสอบแล้วเสร็จ (Completed)",
    inspector_name: str = "",
    geological_unit: str = "",
    details: str = "",
    fiscal_year: int = None,
    one_page_path: str = None,
    one_page_name: str = None,
    report_file_path: str = None,
    report_file_name: str = None
) -> int:
    lat, lon = coordinates.utm_to_latlon(utm_e, utm_n, utm_zone)
    if fiscal_year is None or fiscal_year <= 0:
        fiscal_year = calculate_fiscal_year(incident_date)
        
    incident_code = generate_incident_code(fiscal_year)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Safe defaults
    location_name = str(location_name).strip() or "จุดตรวจสอบ"
    subdistrict = str(subdistrict).strip() or "-"
    district = str(district).strip() or "-"
    province = str(province).strip() or "-"
    details = str(details).strip() or "-"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO inspections (
        incident_code, incident_date, fiscal_year, utm_zone, utm_e, utm_n,
        latitude, longitude, location_name, subdistrict, district,
        province, hazard_type, severity, status, inspector_name,
        geological_unit, details, one_page_path, one_page_name,
        report_file_path, report_file_name, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident_code, incident_date, fiscal_year, utm_zone, utm_e, utm_n,
        lat, lon, location_name, subdistrict, district,
        province, hazard_type, severity, status, inspector_name,
        geological_unit, details, one_page_path, one_page_name,
        report_file_path, report_file_name, now_str, now_str
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_inspection_files(
    record_id: int,
    one_page_path: str = None,
    one_page_name: str = None,
    report_file_path: str = None,
    report_file_name: str = None,
    details: str = None
):
    """Update files and optional details for an existing record."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    updates = ["updated_at = ?"]
    params = [now_str]

    if one_page_path is not None:
        updates.append("one_page_path = ?")
        params.append(one_page_path)
    if one_page_name is not None:
        updates.append("one_page_name = ?")
        params.append(one_page_name)
    if report_file_path is not None:
        updates.append("report_file_path = ?")
        params.append(report_file_path)
    if report_file_name is not None:
        updates.append("report_file_name = ?")
        params.append(report_file_name)
    if details is not None:
        updates.append("details = ?")
        params.append(details)

    params.append(record_id)
    sql = f"UPDATE inspections SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(sql, tuple(params))
    conn.commit()
    conn.close()


def delete_inspection(record_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM inspection_photos WHERE inspection_id = ?", (record_id,))
    photos = cursor.fetchall()
    for p in photos:
        try:
            if os.path.exists(p["file_path"]):
                os.remove(p["file_path"])
        except Exception:
            pass
            
    cursor.execute("SELECT one_page_path, report_file_path FROM inspections WHERE id = ?", (record_id,))
    rec = cursor.fetchone()
    if rec:
        for fpath in [rec["one_page_path"], rec["report_file_path"]]:
            if fpath and os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    cursor.execute("DELETE FROM inspection_photos WHERE inspection_id = ?", (record_id,))
    cursor.execute("DELETE FROM inspections WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def add_photo(inspection_id: int, file_path: str, caption: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO inspection_photos (inspection_id, file_path, caption)
    VALUES (?, ?, ?)
    """, (inspection_id, file_path, caption))
    conn.commit()
    conn.close()


def get_photos(inspection_id: int) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inspection_photos WHERE inspection_id = ? ORDER BY id ASC", (inspection_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_inspection(record_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inspections WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_inspections() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM inspections ORDER BY incident_date DESC, id DESC", conn)
    conn.close()
    return df


def export_to_geojson(df: pd.DataFrame) -> str:
    """Generate GeoJSON string from inspections DataFrame."""
    features = []
    for _, row in df.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])]
            },
            "properties": {
                "id": int(row["id"]),
                "incident_code": str(row["incident_code"]),
                "incident_date": str(row["incident_date"]),
                "fiscal_year": int(row["fiscal_year"]) if pd.notna(row.get("fiscal_year")) else None,
                "hazard_type": str(row["hazard_type"]),
                "location_name": str(row["location_name"]),
                "subdistrict": str(row["subdistrict"]),
                "district": str(row["district"]),
                "province": str(row["province"]),
                "utm_zone": int(row["utm_zone"]),
                "utm_e": float(row["utm_e"]),
                "utm_n": float(row["utm_n"]),
                "severity": str(row["severity"]),
                "status": str(row["status"]),
                "inspector_name": str(row.get("inspector_name", "")),
                "geological_unit": str(row.get("geological_unit", "")),
                "details": str(row.get("details", "")),
                "has_one_page": bool(row.get("one_page_path")),
                "has_report": bool(row.get("report_file_path"))
            }
        }
        features.append(feature)

    geojson_obj = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": features
    }
    return json.dumps(geojson_obj, ensure_ascii=False, indent=2)
