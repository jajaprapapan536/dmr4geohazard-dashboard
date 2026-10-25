"""
Import user's real geohazard dataset (สทข. 4) into geohazard.db
"""
import csv
import re
import os
import sqlite3
from datetime import datetime
import config
import db
import coordinates

RAW_CSV_PATH = os.path.join(config.DATA_DIR, "raw_geohazard_data.csv")

THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
    "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
    "สิิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4,
    "พ.ค.": 5, "มิ.ย.": 6, "ก.ค.": 7, "ส.ค.": 8,
    "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12
}

def clean_day(val: str) -> int:
    if not val:
        return 1
    val = val.strip()
    # If "9-11", "16-17", "21-22"
    m = re.search(r"(\d+)", val)
    if m:
        return int(m.group(1))
    return 1

def clean_month(val: str) -> int:
    if not val:
        return 1
    val = val.strip()
    return THAI_MONTHS.get(val, 1)

def clean_year(val: str, dmy_val: str) -> int:
    val = str(val).strip()
    if val and val.isdigit():
        y = int(val)
        if y > 2400:
            return y - 543  # Convert BE to CE
        return y
    # Fallback to D/M/Y
    if dmy_val:
        m = re.search(r"(\d{4})", dmy_val)
        if m:
            y = int(m.group(1))
            if y > 2400:
                return y - 543
            elif y < 2000:
                # e.g. 1967 -> 2567 BE -> 2024 CE
                return (y + 600) - 543
            return y
    return 2024

def run_import():
    db.init_db()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Clear existing demo data
    print("Clearing existing data...")
    cursor.execute("DELETE FROM inspection_photos")
    cursor.execute("DELETE FROM inspections")
    conn.commit()

    print(f"Reading {RAW_CSV_PATH}...")
    with open(RAW_CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        count = 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for row in reader:
            raw_id = row.get("ID", "").strip()
            dmy = row.get("D/M/Y", "").strip()
            raw_day = row.get("DATE", "").strip()
            raw_month = row.get("Month", "").strip()
            raw_year = row.get("year", "").strip()
            h_type = row.get("Type", "").strip() or "หลุมยุบ"
            name = row.get("Name", "").strip()
            subdistrict = row.get("Subdistrict", "").strip() or "-"
            district = row.get("District", "").strip() or "-"
            province = row.get("Province", "").strip() or "-"
            raw_e = row.get("UTM_E", "").strip().replace(",", "")
            raw_n = row.get("UTM_N", "").strip().replace(",", "")
            remark = row.get("REMARK", "").strip()
            raw_fy = row.get("ปีงบประมาณ", "").strip()

            try:
                utm_e = float(raw_e)
                utm_n = float(raw_n)
            except ValueError:
                print(f"Skipping row ID {raw_id}: invalid coordinates E={raw_e}, N={raw_n}")
                continue

            # Calculate date
            ce_year = clean_year(raw_year, dmy)
            month = clean_month(raw_month)
            day = clean_day(raw_day)
            try:
                dt = datetime(ce_year, month, day)
                incident_date = dt.strftime("%Y-%m-%d")
            except Exception:
                incident_date = f"{ce_year:04d}-{month:02d}-01"

            # Parse Fiscal Year
            if raw_fy and raw_fy.isdigit():
                fiscal_year = int(raw_fy)
            else:
                fiscal_year = db.calculate_fiscal_year(incident_date)

            # Location name cleanup
            if not name:
                name = f"จุดตรวจสอบ ต.{subdistrict} อ.{district}"
            elif name.isdigit():
                name = f"หมู่ที่ {name}"

            # Coordinate conversion (Southern Thailand = UTM Zone 47N)
            lat, lon = coordinates.utm_to_latlon(utm_e, utm_n, 47)

            # Incident code
            code_num = int(raw_id) if raw_id.isdigit() else (count + 1)
            incident_code = f"GEO-S4-{fiscal_year}-{code_num:03d}"

            # Severity heuristic based on remarks
            if "เสียชีวิต" in remark or "อพยพ" in remark or "วิกฤต" in remark:
                severity = "วิกฤต (Critical - เสี่ยงต่อชีวิต/ต้องอพยพเร่งด่วน)"
            elif "เสียหาย" in remark or "ปิดทับถนน" in remark or "บาดเจ็บ" in remark or "บ้าน" in remark:
                severity = "สูง (High - กระทบโครงสร้างพื้นฐาน/บ้านเรือน)"
            elif "สวน" in remark or "รอยร้าว" in remark:
                severity = "ปานกลาง (Medium - ส่งผลกระทบพื้นที่การเกษตร/สิ่งปลูกสร้างเล็กน้อย)"
            else:
                severity = "ต่ำ (Low - เฝ้าระวัง)"

            status = "ตรวจสอบแล้วเสร็จ (Completed)"
            inspector = "สำนักงานทรัพยากรธรณี เขต 4 (สทข.4)"

            cursor.execute("""
            INSERT INTO inspections (
                incident_code, incident_date, fiscal_year, utm_zone, utm_e, utm_n,
                latitude, longitude, location_name, subdistrict, district,
                province, hazard_type, severity, status, inspector_name,
                geological_unit, details, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_code, incident_date, fiscal_year, 47, utm_e, utm_n,
                lat, lon, name, subdistrict, district,
                province, h_type, severity, status, inspector,
                "", remark, now_str, now_str
            ))
            count += 1

    conn.commit()
    conn.close()
    print(f"Import completed! Successfully imported {count} records into geohazard.db.")

if __name__ == "__main__":
    run_import()
