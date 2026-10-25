"""
Geological Hazard Inspection Dashboard & Recording System
ระบบบันทึกและติดตามการตรวจสอบธรณีพิบัติภัย
"""
import os
import io
import datetime
import importlib
import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster, Fullscreen
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

import config
import db
import coordinates

# Ensure fresh modules
importlib.reload(config)
importlib.reload(db)
importlib.reload(coordinates)

# Set page configuration
st.set_page_config(
    page_title="Geohazard Inspection Portal | ระบบตรวจสอบธรณีพิบัติภัย",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #F9FAFB 0%, #EFF6FF 100%);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #DBEAFE;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        border-radius: 8px;
        font-weight: 600;
    }
    .upload-card {
        background-color: #F8FAFC;
        border: 1px dashed #CBD5E1;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
db.init_db()

# Color mapping for all hazard types
HAZARD_COLORS = {
    "หลุมยุบ": "#EA580C",
    "ดินถล่ม": "#DC2626",
    "หินถล่ม": "#B91C1C",
    "หินร่วง": "#F97316",
    "บ่อน้ำทรุดตัว": "#2563EB",
    "ดินทรุด": "#3B82F6",
    "ดินไหล": "#92400E",
    "แผ่นดินไหว": "#7C3AED",
    "โพรงใต้ดิน": "#D97706",
    "น้ำผุด": "#0D9488",
    "รอยร้าวในผนังถ้ำ": "#C026D3",
    "ตรวจธรณีวิทยา": "#059669",
    "คล้ายหินถล่ม": "#64748B",
    "อื่น ๆ": "#6B7280"
}

def get_marker_color_name(hazard_type: str) -> str:
    h = str(hazard_type).strip()
    if "หลุมยุบ" in h or "โพรงใต้ดิน" in h:
        return "orange"
    if "หินถล่ม" in h:
        return "darkred"
    if "หินร่วง" in h:
        return "lightred"
    if "ดินถล่ม" in h or "ดินไหล" in h:
        return "red"
    if "บ่อน้ำทรุดตัว" in h:
        return "blue"
    if "ดินทรุด" in h:
        return "cadetblue"
    if "แผ่นดินไหว" in h:
        return "purple"
    if "ตรวจธรณีวิทยา" in h:
        return "green"
    if "น้ำผุด" in h:
        return "lightblue"
    if "รอยร้าว" in h:
        return "pink"
    return "gray"

def compute_fiscal_year(date_obj) -> int:
    """Safe fiscal year calculation."""
    try:
        b_year = date_obj.year + 543
        return b_year + 1 if date_obj.month >= 10 else b_year
    except Exception:
        now = datetime.datetime.now()
        b_year = now.year + 543
        return b_year + 1 if now.month >= 10 else b_year


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/earth-element.png", width=70)
    st.markdown("### 🌍 ระบบตรวจสอบธรณีพิบัติภัย")
    st.caption("สทข. 4 กรมทรัพยากรธรณี (ภาคใต้)")
    st.markdown("---")

    menu = st.radio(
        "เมนูหลัก (Navigation)",
        [
            "📊 แดชบอร์ดและแผนที่ (Dashboard & GIS)",
            "➕ บันทึกข้อมูลการตรวจสอบ (New Inspection)",
            "📋 รายการข้อมูลและส่งออก (Data Table & Export)",
            "📥 นำเข้าไฟล์ข้อมูลเดิม (Import Excel / CSV)",
            "🧭 เครื่องมือแปลงพิกัด UTM (UTM Converter)"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("##### 📌 โซน UTM ประเทศไทย")
    st.info(
        "• **Zone 47N (EPSG:32647)**: เหนือ, กลาง, ใต้, ตะวันตก\n"
        "• **Zone 48N (EPSG:32648)**: ตะวันออกเฉียงเหนือ, ตะวันออกบางส่วน"
    )

# Load data fresh
df = db.get_all_inspections()


# ==========================================
# PAGE 1: DASHBOARD & GIS MAP
# ==========================================
if menu == "📊 แดชบอร์ดและแผนที่ (Dashboard & GIS)":
    st.markdown('<div class="main-header">📊 แดชบอร์ดติดตามและแผนที่ตรวจสอบธรณีพิบัติภัย</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">ภาพรวมสถิติการตรวจสอบธรณีพิบัติภัยและตำแหน่งพิกัดทางธรณีวิทยาแบบ Interactive GIS</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("⚠️ ยังไม่มีข้อมูลการตรวจสอบในระบบ กรุณาไปที่แท็บ '➕ บันทึกข้อมูลการตรวจสอบ' หรือ '📥 นำเข้าไฟล์ข้อมูลเดิม' เพื่อนำเข้าข้อมูล")
    else:
        # Filter Bar with Fiscal Year
        with st.expander("🔍 ตัวกรองข้อมูล (Filters)", expanded=True):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                available_fy = sorted([int(x) for x in df["fiscal_year"].dropna().unique().tolist()], reverse=True)
                selected_fy = st.multiselect(
                    "📅 ปีงบประมาณ (พ.ศ.)",
                    options=available_fy,
                    default=available_fy
                )
            with col_f2:
                available_hazards = sorted(df["hazard_type"].unique().tolist())
                selected_hazards = st.multiselect(
                    "ประเภทพิบัติภัย",
                    options=available_hazards,
                    default=available_hazards
                )
            with col_f3:
                available_provinces = sorted(df["province"].unique().tolist())
                selected_provinces = st.multiselect(
                    "จังหวัด",
                    options=available_provinces,
                    default=available_provinces
                )
            with col_f4:
                available_status = sorted(df["status"].unique().tolist())
                selected_status = st.multiselect(
                    "สถานะการตรวจสอบ",
                    options=available_status,
                    default=available_status
                )

        # Apply Filters
        filtered_df = df[
            (df["fiscal_year"].isin(selected_fy)) &
            (df["hazard_type"].isin(selected_hazards)) &
            (df["province"].isin(selected_provinces)) &
            (df["status"].isin(selected_status))
        ]

        # Top KPIs
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("จำนวนเหตุการณ์ตามตัวกรอง", f"{len(filtered_df):,} จุด", delta=f"จากทั้งหมด {len(df)} จุด")
        with kpi2:
            sinkhole_count = len(filtered_df[filtered_df["hazard_type"].str.contains("หลุมยุบ|โพรง", na=False)])
            st.metric("หลุมยุบ / โพรงใต้ดิน", f"{sinkhole_count:,} จุด")
        with kpi3:
            landslide_count = len(filtered_df[filtered_df["hazard_type"].str.contains("ถล่ม|ร่วง|ไหล", na=False)])
            st.metric("ดิน/หินถล่ม / หินร่วง", f"{landslide_count:,} จุด")
        with kpi4:
            subsidence_count = len(filtered_df[filtered_df["hazard_type"].str.contains("ทรุด", na=False)])
            st.metric("บ่อน้ำทรุดตัว / ดินทรุด", f"{subsidence_count:,} จุด")

        st.markdown("### 🗺️ แผนที่พิกัดจุดตรวจสอบธรณีพิบัติภัย (Interactive GIS Map)")

        # Map Layer Selector
        map_col1, map_col2 = st.columns([3, 1])
        with map_col2:
            basemap_choice = st.selectbox(
                "ชั้นข้อมูลแผนที่ฐาน (Basemap)",
                ["ภาพถ่ายดาวเทียม (Esri Satellite)", "แผนที่ถนน (OpenStreetMap)", "แผนที่ภูมิประเทศ (CartoDB Positron)"],
                index=0
            )
            use_cluster = st.checkbox("จัดกลุ่มหมุดพิกัด (Cluster Markers)", value=True)

        with map_col1:
            st.caption("💡 เลื่อนเมาส์หรือคลิกที่หมุดเพื่อดูข้อมูลเหตุการณ์ ปีงบประมาณ พิกัด UTM และรายละเอียดการตรวจสอบ")

        # Create Folium Map
        if not filtered_df.empty:
            avg_lat = filtered_df["latitude"].mean()
            avg_lon = filtered_df["longitude"].mean()
            initial_zoom = 8 if len(filtered_df) > 1 else 11
        else:
            avg_lat = 8.5
            avg_lon = 99.2
            initial_zoom = 7

        m = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=initial_zoom,
            tiles=None,
            control_scale=True
        )

        # Add Basemaps
        if basemap_choice == "ภาพถ่ายดาวเทียม (Esri Satellite)":
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri World Imagery",
                name="Esri Satellite",
                overlay=False,
                control=True
            ).add_to(m)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
                attr="Esri Boundaries",
                name="Labels",
                overlay=True,
                control=True
            ).add_to(m)
        elif basemap_choice == "แผนที่ถนน (OpenStreetMap)":
            folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
        else:
            folium.TileLayer("CartoDB Positron", name="CartoDB Positron").add_to(m)

        Fullscreen(position="topright").add_to(m)

        # Add Markers
        marker_container = MarkerCluster().add_to(m) if use_cluster else m

        for _, row in filtered_df.iterrows():
            marker_color = get_marker_color_name(str(row["hazard_type"]))
            
            photos = db.get_photos(row["id"])
            photo_html = ""
            if photos:
                photo_html = f"<div style='margin-top:8px;'><img src='file:///{photos[0]['file_path']}' style='max-width:180px; border-radius:6px;'><br><small style='color:#666;'>{photos[0].get('caption','')}</small></div>"

            fy_display = f"ปีงบ {row['fiscal_year']}" if pd.notna(row.get('fiscal_year')) else ""

            # Doc badge
            badge_html = ""
            if row.get("one_page_path"):
                badge_html += "<span style='background:#E0E7FF; color:#3730A3; font-size:10px; padding:2px 6px; border-radius:10px; margin-right:4px;'>📄 มี One Page</span>"
            if row.get("report_file_path"):
                badge_html += "<span style='background:#DCFCE7; color:#166534; font-size:10px; padding:2px 6px; border-radius:10px; margin-right:4px;'>📑 มีรายงาน</span>"

            popup_content = f"""
            <div style="font-family:sans-serif; width:270px;">
                <div style="font-weight:bold; font-size:14px; color:#1E3A8A; border-bottom:1px solid #ccc; padding-bottom:4px;">
                    {row['incident_code']} <span style="font-size:11px; color:#0284C7;">({fy_display})</span>
                </div>
                <div style="margin-top:6px; font-size:12px;">
                    <b>ประเภท:</b> <span style="color:#DC2626; font-weight:bold;">{row['hazard_type']}</span><br>
                    <b>วันที่:</b> {row['incident_date']}<br>
                    <b>สถานที่:</b> {row['location_name']}<br>
                    <b>ตำบล/อำเภอ/จ.:</b> ต.{row['subdistrict']} อ.{row['district']} จ.{row['province']}<br>
                    <b>พิกัด UTM (Z{row['utm_zone']}):</b> {row['utm_e']:,.0f} E, {row['utm_n']:,.0f} N<br>
                    <b>พิกัด Lat/Lon:</b> {row['latitude']:.5f}, {row['longitude']:.5f}<br>
                    <div style="margin:4px 0;">{badge_html}</div>
                    <div style="margin-top:6px; font-size:11px; color:#374151; background:#F3F4F6; padding:6px; border-radius:4px; max-height:80px; overflow-y:auto;">
                        <b>รายละเอียด:</b> {str(row.get('details', ''))[:160]}...
                    </div>
                    {photo_html}
                </div>
            </div>
            """

            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"[{row['hazard_type']}] {row['location_name']} จ.{row['province']} ({fy_display})",
                icon=folium.Icon(color=marker_color, icon="info-sign")
            ).add_to(marker_container)

        st_folium(m, width="100%", height=550, returned_objects=[])

        # Charts Section
        st.markdown("### 📈 การวิเคราะห์เชิงสถิติ (Hazard Analytics)")
        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            hazard_counts = filtered_df["hazard_type"].value_counts().reset_index()
            hazard_counts.columns = ["ประเภทพิบัติภัย", "จำนวนครั้ง"]
            fig_pie = px.pie(
                hazard_counts,
                names="ประเภทพิบัติภัย",
                values="จำนวนครั้ง",
                title="สัดส่วนเหตุการณ์แยกตามประเภทพิบัติภัย",
                hole=0.45,
                color="ประเภทพิบัติภัย",
                color_discrete_map=HAZARD_COLORS
            )
            fig_pie.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=360)
            st.plotly_chart(fig_pie, use_container_width=True)

        with ch_col2:
            prov_counts = filtered_df["province"].value_counts().head(8).reset_index()
            prov_counts.columns = ["จังหวัด", "จำนวนครั้ง"]
            fig_bar = px.bar(
                prov_counts,
                x="จังหวัด",
                y="จำนวนครั้ง",
                text="จำนวนครั้ง",
                title="จำนวนเหตุการณ์แยกตามจังหวัด",
                color="จำนวนครั้ง",
                color_continuous_scale="Reds"
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=360)
            st.plotly_chart(fig_bar, use_container_width=True)

        # Fiscal Year Comparison
        st.markdown("##### 📅 สถิติจำนวนเหตุการณ์เปรียบเทียบตามปีงบประมาณ (พ.ศ. 2559 - 2569)")
        fy_counts = filtered_df.groupby(["fiscal_year", "hazard_type"]).size().reset_index(name="จำนวนครั้ง")
        fy_counts["fiscal_year_label"] = "ปีงบ " + fy_counts["fiscal_year"].astype(str)
        fig_fy = px.bar(
            fy_counts,
            x="fiscal_year_label",
            y="จำนวนครั้ง",
            color="hazard_type",
            title="จำนวนการตรวจสอบธรณีพิบัติภัยในแต่ละปีงบประมาณ",
            labels={"fiscal_year_label": "ปีงบประมาณ", "จำนวนครั้ง": "จำนวนครั้ง", "hazard_type": "ประเภทพิบัติภัย"},
            color_discrete_map=HAZARD_COLORS,
            barmode="stack"
        )
        fig_fy.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=350)
        st.plotly_chart(fig_fy, use_container_width=True)


# ==========================================
# PAGE 2: NEW INSPECTION ENTRY FORM
# ==========================================
elif menu == "➕ บันทึกข้อมูลการตรวจสอบ (New Inspection)":
    st.markdown('<div class="main-header">➕ บันทึกผลการตรวจสอบธรณีพิบัติภัย</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">กรอกข้อมูลการรับแจ้ง ปีงบประมาณ พิกัด UTM รายละเอียด และอัปโหลดไฟล์ One Page, รูปสำรวจ (ไม่เกิน 10 รูป) และไฟล์รายงาน</div>', unsafe_allow_html=True)

    today = datetime.date.today()
    default_fy = compute_fiscal_year(today)

    with st.form("new_inspection_form", clear_on_submit=False):
        st.markdown("#### 1. ข้อมูลทั่วไปและประเภทเหตุการณ์")
        col1, col2, col3 = st.columns(3)
        with col1:
            incident_date = st.date_input("วันที่ตรวจสอบ / รับแจ้ง (Date)*", today)
            fiscal_year = st.number_input(
                "ปีงบประมาณ (พ.ศ.)*",
                min_value=2500,
                max_value=2650,
                value=default_fy,
                step=1,
                help="คำนวณอัตโนมัติตามปีงบประมาณไทย (1 ต.ค. - 30 ก.ย.) หรือแก้ไขได้ตามจริง"
            )

        with col2:
            hazard_type = st.selectbox("ประเภทพิบัติภัย (Hazard Type)*", config.HAZARD_TYPES)
            severity = st.selectbox("ระดับความรุนแรง (Severity)", config.SEVERITY_LEVELS, index=1)

        with col3:
            status = st.selectbox("สถานะการตรวจสอบ (Status)", config.STATUS_CHOICES, index=0)
            inspector_name = st.text_input("ชื่อผู้ตรวจสอบ / หน่วยงาน (Inspector)", value="สำนักงานทรัพยากรธรณี เขต 4 (สทข.4)")

        geological_unit = st.text_input("กลุ่มหิน / ดิน / โครงสร้างทางธรณี (Geological Unit)", placeholder="เช่น หินปูนกลุ่มหินทุ่งสง / หินแกรนิต / ตะกอนเศษหินเชิงเขา")

        st.markdown("---")
        st.markdown("#### 2. พิกัดตำแหน่ง (UTM Coordinates)")
        st.caption("กรอกพิกัด UTM ระบบ WGS84 ระบบจะคำนวณ ละติจูด / ลองจิจูด ให้โดยอัตโนมัติ")

        coord_col1, coord_col2, coord_col3 = st.columns(3)
        with coord_col1:
            utm_zone = st.selectbox("UTM Zone*", [47, 48], index=0, help="ภาคใต้ ภาคเหนือ ภาคกลาง ใช้ Zone 47N | ภาคอีสาน ตะวันออก ใช้ Zone 48N")
        with coord_col2:
            utm_e = st.number_input("UTM Easting (UTM_E)* (เมตร)", min_value=100000.0, max_value=900000.0, value=500000.0, step=1.0, format="%.2f")
        with coord_col3:
            utm_n = st.number_input("UTM Northing (UTM_N)* (เมตร)", min_value=500000.0, max_value=2500000.0, value=900000.0, step=1.0, format="%.2f")

        try:
            calc_lat, calc_lon = coordinates.utm_to_latlon(utm_e, utm_n, utm_zone)
            st.success(f"📍 **ตำแหน่งที่คำนวณได้:** Latitude: `{calc_lat:.6f}` | Longitude: `{calc_lon:.6f}` (WGS84)")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการคำนวณพิกัด: {e}")
            calc_lat, calc_lon = 8.5, 99.2

        st.markdown("---")
        st.markdown("#### 3. ข้อมูลสถานที่และหน่วยการปกครอง")
        loc_col1, loc_col2 = st.columns(2)
        with loc_col1:
            location_name = st.text_input("สถานที่เกิดเหตุ / จุดสังเกต (Location Name)*", placeholder="เช่น ม.3 บ้านป่าใหม่ หรือ วัดเขาพนม")
            subdistrict = st.text_input("ตำบล (Subdistrict)", placeholder="เช่น ดินอุดม (หากไม่มีให้เว้นว่างหรือใส่ -)")
        with loc_col2:
            district = st.text_input("อำเภอ (District)", placeholder="เช่น ลำทับ (หากไม่มีให้เว้นว่างหรือใส่ -)")
            province = st.selectbox("จังหวัด (Province)*", config.THAI_PROVINCES, index=0)

        st.markdown("---")
        st.markdown("#### 4. รายละเอียดการตรวจสอบและข้อสังเกตทางธรณีวิทยา")
        details = st.text_area(
            "รายละเอียดเหตุการณ์ ขนาดความเสียหาย สาเหตุ และข้อเสนอแนะ",
            height=120,
            placeholder="ระบุขนาดของหลุมยุบ/ดินสไลด์ ความยาวรอยแยก ทิศทางการเคลื่อนตัว สภาพอากาศ ปริมาณน้ำฝนสะสม และข้อเสนอแนะในการเฝ้าระวังหรือบรรเทาภัย..."
        )

        st.markdown("---")
        st.markdown("#### 5. อัปโหลดไฟล์รายงานและไฟล์รูป")

        up_col1, up_col2 = st.columns(2)
        with up_col1:
            st.markdown("##### 📄 1. One Page")
            st.caption("เอกสารสรุป 1 หน้า (รองรับ PDF, Word, หรือ รูปภาพ)")
            one_page_file = st.file_uploader(
                "อัปโหลดไฟล์ One Page",
                type=["pdf", "docx", "doc", "jpg", "jpeg", "png"],
                key="new_one_page"
            )

        with up_col2:
            st.markdown("##### 📑 3. ไฟล์รายงาน (ถ้ามี)")
            st.caption("เอกสารรายงานฉบับเต็ม (รองรับ PDF, Word, Excel, ZIP)")
            report_file = st.file_uploader(
                "อัปโหลดไฟล์รายงานฉบับเต็ม",
                type=["pdf", "docx", "doc", "xlsx", "zip"],
                key="new_report"
            )

        st.markdown("##### 📷 2. รูปสำรวจ ไม่เกิน 10 รูป")
        st.caption("ภาพถ่ายจุดเกิดเหตุ ร่องรอยความเสียหาย (รองรับ JPG, JPEG, PNG สูงสุด 10 รูป)")
        survey_photos = st.file_uploader(
            "เลือกรูปสำรวจ (ไม่เกิน 10 รูป)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="new_photos"
        )

        if survey_photos:
            if len(survey_photos) > 10:
                st.warning(f"⚠️ คุณเลือกภาพทั้งหมด {len(survey_photos)} รูป ระบบจะบันทึกเฉพาะ 10 รูปแรกตามข้อกำหนดครับ")
            st.caption(f"เลือกภาพแล้ว {min(len(survey_photos), 10)} รูป")

        submitted = st.form_submit_button("💾 บันทึกข้อมูลการตรวจสอบ (Save Inspection)", type="primary")

        if submitted:
            loc_clean = location_name.strip() if location_name else ""
            if not loc_clean:
                st.error("⚠️ กรุณาระบุ 'สถานที่เกิดเหตุ / จุดสังเกต'")
            else:
                try:
                    # Save One Page file if uploaded
                    saved_one_page_path = None
                    saved_one_page_name = None
                    if one_page_file:
                        saved_one_page_name = one_page_file.name
                        ext = os.path.splitext(one_page_file.name)[1]
                        filename = f"onepage_{int(datetime.datetime.now().timestamp())}_{saved_one_page_name}"
                        saved_one_page_path = os.path.join(db.ONEPAGE_DIR, filename)
                        with open(saved_one_page_path, "wb") as f:
                            f.write(one_page_file.getbuffer())

                    # Save Report file if uploaded
                    saved_report_path = None
                    saved_report_name = None
                    if report_file:
                        saved_report_name = report_file.name
                        filename = f"report_{int(datetime.datetime.now().timestamp())}_{saved_report_name}"
                        saved_report_path = os.path.join(db.REPORTS_DIR, filename)
                        with open(saved_report_path, "wb") as f:
                            f.write(report_file.getbuffer())

                    # Insert inspection record
                    new_id = db.add_inspection(
                        incident_date=str(incident_date),
                        fiscal_year=int(fiscal_year),
                        utm_zone=utm_zone,
                        utm_e=utm_e,
                        utm_n=utm_n,
                        location_name=loc_clean,
                        subdistrict=subdistrict.strip() or "-",
                        district=district.strip() or "-",
                        province=province,
                        hazard_type=hazard_type,
                        severity=severity,
                        status=status,
                        inspector_name=inspector_name.strip() or "สทข.4",
                        geological_unit=geological_unit.strip(),
                        details=details.strip() or "-",
                        one_page_path=saved_one_page_path,
                        one_page_name=saved_one_page_name,
                        report_file_path=saved_report_path,
                        report_file_name=saved_report_name
                    )

                    # Save up to 10 photos
                    if survey_photos:
                        photos_to_save = survey_photos[:10]
                        for idx, pfile in enumerate(photos_to_save):
                            ext = os.path.splitext(pfile.name)[1]
                            fname = f"insp_{new_id}_{int(datetime.datetime.now().timestamp())}_{idx+1}{ext}"
                            p_path = os.path.join(db.PHOTOS_DIR, fname)
                            with open(p_path, "wb") as f:
                                f.write(pfile.getbuffer())
                            db.add_photo(new_id, p_path, pfile.name)

                    st.success(f"✅ บันทึกข้อมูลการตรวจสอบสำเร็จเรียบร้อย! (รหัสรายการ ID: {new_id} | ปีงบประมาณ: {fiscal_year})")
                    st.balloons()
                    st.info("💡 ข้อมูลถูกบันทึกลงสู่ฐานข้อมูลแล้ว คลิกไปที่แท็บ '📊 แดชบอร์ดและแผนที่' หรือ '📋 รายการข้อมูลและส่งออก' เพื่อดูข้อมูลได้ทันที")

                except Exception as err:
                    st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล: {err}")


# ==========================================
# PAGE 3: DATA TABLE & EXPORT + ATTACHMENT UPLOAD FOR EXISTING
# ==========================================
elif menu == "📋 รายการข้อมูลและส่งออก (Data Table & Export)":
    st.markdown('<div class="main-header">📋 รายการข้อมูลและการส่งออก (Data Table & Export)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">สืบค้น อัปโหลดไฟล์ให้กับข้อมูลเดิม ดาวน์โหลดไฟล์ One Page / รายงาน และส่งออกข้อมูล</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("ยังไม่มีข้อมูลในระบบ")
    else:
        s_col1, s_col2, s_col3 = st.columns([2, 1, 1])
        with s_col1:
            search_query = st.text_input("🔍 ค้นหา (รหัสเหตุการณ์, สถานที่, จังหวัด, รายละเอียด)", "")
        with s_col2:
            hazard_filter = st.selectbox("กรองตามประเภทภัย", ["ทั้งหมด"] + config.HAZARD_TYPES)
        with s_col3:
            fy_list = ["ทั้งหมด"] + sorted([str(int(x)) for x in df["fiscal_year"].dropna().unique().tolist()], reverse=True)
            fy_filter = st.selectbox("กรองตามปีงบประมาณ", fy_list)

        table_df = df.copy()
        if search_query:
            query = search_query.lower()
            table_df = table_df[
                table_df["incident_code"].str.lower().str.contains(query, na=False) |
                table_df["location_name"].str.lower().str.contains(query, na=False) |
                table_df["province"].str.lower().str.contains(query, na=False) |
                table_df["inspector_name"].str.lower().str.contains(query, na=False) |
                table_df["details"].str.lower().str.contains(query, na=False)
            ]
        if hazard_filter != "ทั้งหมด":
            table_df = table_df[table_df["hazard_type"] == hazard_filter]
        if fy_filter != "ทั้งหมด":
            table_df = table_df[table_df["fiscal_year"] == int(fy_filter)]

        st.caption(f"พบข้อมูลทั้งหมด {len(table_df)} รายการ")

        exp_col1, exp_col2, exp_col3 = st.columns([1, 1, 2])

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            table_df.to_excel(writer, index=False, sheet_name="Geohazard_Inspections")
        excel_data = excel_buffer.getvalue()

        with exp_col1:
            st.download_button(
                label="📥 ส่งออกเป็น Excel (.xlsx)",
                data=excel_data,
                file_name=f"geohazard_report_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

        geojson_str = db.export_to_geojson(table_df)
        with exp_col2:
            st.download_button(
                label="🗺️ ส่งออกเป็น GeoJSON (QGIS/ArcGIS)",
                data=geojson_str,
                file_name=f"geohazard_spatial_{datetime.date.today()}.geojson",
                mime="application/geo+json"
            )

        display_columns = [
            "id", "incident_code", "fiscal_year", "incident_date", "hazard_type",
            "location_name", "subdistrict", "district", "province",
            "utm_zone", "utm_e", "utm_n", "latitude", "longitude",
            "severity", "status", "inspector_name"
        ]
        rename_dict = {
            "id": "ID",
            "incident_code": "รหัสเหตุการณ์",
            "fiscal_year": "ปีงบประมาณ",
            "incident_date": "วันที่",
            "hazard_type": "ประเภทพิบัติภัย",
            "location_name": "สถานที่",
            "subdistrict": "ตำบล",
            "district": "อำเภอ",
            "province": "จังหวัด",
            "utm_zone": "UTM Zone",
            "utm_e": "UTM_E",
            "utm_n": "UTM_N",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "severity": "ความรุนแรง",
            "status": "สถานะ",
            "inspector_name": "ผู้ตรวจสอบ"
        }
        st.dataframe(table_df[display_columns].rename(columns=rename_dict), use_container_width=True, height=350)

        st.markdown("---")
        st.markdown("### 🔍 ดูรายละเอียด / อัปโหลดไฟล์เพิ่มเติม / จัดการข้อมูลรายจุด")
        
        selected_id = st.selectbox(
            "เลือกรายการที่ต้องการดูหรืออัปโหลดไฟล์ (Select Record ID)",
            options=table_df["id"].tolist(),
            format_func=lambda x: f"ID {x}: {table_df[table_df['id']==x]['incident_code'].values[0]} (ปีงบ {table_df[table_df['id']==x]['fiscal_year'].values[0]}) - {table_df[table_df['id']==x]['hazard_type'].values[0]} : {table_df[table_df['id']==x]['location_name'].values[0]} จ.{table_df[table_df['id']==x]['province'].values[0]}"
        )

        if selected_id:
            record = db.get_inspection(selected_id)
            if record:
                rec_col1, rec_col2 = st.columns([1.3, 1.7])
                with rec_col1:
                    st.markdown(f"### รหัสเหตุการณ์: `{record['incident_code']}`")
                    st.write(f"**ปีงบประมาณ:** พ.ศ. `{record.get('fiscal_year') or '-'}`")
                    st.write(f"**ประเภทพิบัติภัย:** <span style='color:#DC2626; font-weight:bold;'>{record['hazard_type']}</span>", unsafe_allow_html=True)
                    st.write(f"**วันที่ตรวจสอบ:** {record['incident_date']}")
                    st.write(f"**สถานที่:** {record['location_name']} ต.{record['subdistrict']} อ.{record['district']} จ.{record['province']}")
                    st.write(f"**พิกัด UTM:** Zone {record['utm_zone']}N | E: `{record['utm_e']:,.2f}` | N: `{record['utm_n']:,.2f}`")
                    st.write(f"**พิกัด WGS84 Lat/Lon:** Lat `{record['latitude']:.6f}`, Lon `{record['longitude']:.6f}`")
                    st.write(f"**ผู้ตรวจสอบ:** {record.get('inspector_name') or '-'}")
                    st.info(f"**รายละเอียด / ผลการตรวจสอบทางธรณีวิทยา:**\n\n{record.get('details') or '-'}")

                    st.markdown("##### 📁 ไฟล์เอกสารที่แนบไว้")
                    
                    # One Page download
                    op_path = record.get("one_page_path")
                    if op_path and os.path.exists(op_path):
                        with open(op_path, "rb") as f:
                            op_bytes = f.read()
                        st.download_button(
                            label=f"📄 ดาวน์โหลด One Page ({record.get('one_page_name') or 'OnePage'})",
                            data=op_bytes,
                            file_name=record.get("one_page_name") or "OnePage.pdf",
                            key=f"dl_op_{selected_id}"
                        )
                    else:
                        st.caption("📄 One Page: ยังไม่มีไฟล์แนบ (สามารถอัปโหลดได้ด้านล่าง)")

                    # Report download
                    rep_path = record.get("report_file_path")
                    if rep_path and os.path.exists(rep_path):
                        with open(rep_path, "rb") as f:
                            rep_bytes = f.read()
                        st.download_button(
                            label=f"📑 ดาวน์โหลดรายงาน ({record.get('report_file_name') or 'Report'})",
                            data=rep_bytes,
                            file_name=record.get("report_file_name") or "Report.pdf",
                            key=f"dl_rep_{selected_id}"
                        )
                    else:
                        st.caption("📑 ไฟล์รายงาน: ยังไม่มีไฟล์แนบ (สามารถอัปโหลดได้ด้านล่าง)")

                with rec_col2:
                    st.markdown("#### 📷 รูปสำรวจ (สูงสุด 10 รูป)")
                    photos = db.get_photos(selected_id)
                    if photos:
                        st.caption(f"มีภาพถ่ายทั้งหมด {len(photos)} รูป")
                        grid_cols = st.columns(2)
                        for idx, p in enumerate(photos):
                            if os.path.exists(p["file_path"]):
                                col_target = grid_cols[idx % 2]
                                with col_target:
                                    st.image(p["file_path"], caption=f"รูปที่ {idx+1}: {p.get('caption', '')}", use_container_width=True)
                    else:
                        st.caption("ไม่มีภาพถ่ายแนบในรายการนี้ (สามารถอัปโหลดเพิ่มได้ด้านล่าง)")

                    st.markdown("---")
                    if st.button("🗑️ ลบรายการนี้ออกจากฐานข้อมูล", type="secondary"):
                        db.delete_inspection(selected_id)
                        st.success(f"ลบรายการ ID {selected_id} สำเร็จแล้ว")
                        st.rerun()

                # SECTION: UPLOAD FILES FOR THIS EXISTING RECORD
                st.markdown("---")
                with st.expander(f"📤 อัปโหลด / เพิ่มไฟล์ให้กับจุดนี้: {record['incident_code']} ({record['location_name']})", expanded=True):
                    st.markdown("คุณสามารถอัปโหลดไฟล์ One Page, รูปสำรวจ (ไม่เกิน 10 รูป) และไฟล์รายงานให้กับข้อมูลชุดนี้ได้โดยตรง:")

                    with st.form(f"upload_existing_form_{selected_id}", clear_on_submit=False):
                        e_col1, e_col2 = st.columns(2)
                        with e_col1:
                            st.markdown("##### 📄 1. One Page (อัปโหลดใหม่ / แทนที่เดิม)")
                            u_one_page = st.file_uploader(
                                "เลือกไฟล์ One Page",
                                type=["pdf", "docx", "doc", "jpg", "jpeg", "png"],
                                key=f"exist_one_page_{selected_id}"
                            )

                        with e_col2:
                            st.markdown("##### 📑 3. ไฟล์รายงาน (ถ้ามี)")
                            u_report = st.file_uploader(
                                "เลือกไฟล์รายงาน",
                                type=["pdf", "docx", "doc", "xlsx", "zip"],
                                key=f"exist_report_{selected_id}"
                            )

                        st.markdown("##### 📷 2. เพิ่มรูปสำรวจ (ไม่เกิน 10 รูป)")
                        current_photo_count = len(photos)
                        available_photo_slots = max(0, 10 - current_photo_count)
                        st.caption(f"ปัจจุบันมี {current_photo_count} รูป (สามารถเพิ่มได้อีก {available_photo_slots} รูป)")
                        
                        u_photos = st.file_uploader(
                            "เลือกรูปสำรวจเพิ่มเติม",
                            type=["jpg", "jpeg", "png"],
                            accept_multiple_files=True,
                            key=f"exist_photos_{selected_id}"
                        )

                        save_existing_btn = st.form_submit_button("💾 บันทึกไฟล์แนบสำหรับจุดนี้ (Save Attachments)", type="primary")

                        if save_existing_btn:
                            any_updated = False
                            new_op_path = None
                            new_op_name = None
                            if u_one_page:
                                new_op_name = u_one_page.name
                                filename = f"onepage_{int(datetime.datetime.now().timestamp())}_{new_op_name}"
                                new_op_path = os.path.join(db.ONEPAGE_DIR, filename)
                                with open(new_op_path, "wb") as f:
                                    f.write(u_one_page.getbuffer())
                                any_updated = True

                            new_rep_path = None
                            new_rep_name = None
                            if u_report:
                                new_rep_name = u_report.name
                                filename = f"report_{int(datetime.datetime.now().timestamp())}_{new_rep_name}"
                                new_rep_path = os.path.join(db.REPORTS_DIR, filename)
                                with open(new_rep_path, "wb") as f:
                                    f.write(u_report.getbuffer())
                                any_updated = True

                            if any_updated:
                                db.update_inspection_files(
                                    selected_id,
                                    one_page_path=new_op_path,
                                    one_page_name=new_op_name,
                                    report_file_path=new_rep_path,
                                    report_file_name=new_rep_name
                                )

                            if u_photos:
                                photos_to_add = u_photos[:available_photo_slots]
                                for idx, pfile in enumerate(photos_to_add):
                                    ext = os.path.splitext(pfile.name)[1]
                                    fname = f"insp_{selected_id}_{int(datetime.datetime.now().timestamp())}_{idx+1}{ext}"
                                    p_path = os.path.join(db.PHOTOS_DIR, fname)
                                    with open(p_path, "wb") as f:
                                        f.write(pfile.getbuffer())
                                    db.add_photo(selected_id, p_path, pfile.name)
                                any_updated = True

                            if any_updated:
                                st.success("✅ บันทึกและแนบไฟล์ให้กับข้อมูลจุดนี้เรียบร้อยแล้ว!")
                                st.rerun()
                            else:
                                st.warning("⚠️ ยังไม่ได้เลือกไฟล์ใด ๆ เพื่ออัปโหลด")


# ==========================================
# PAGE 4: BATCH IMPORT EXCEL / CSV
# ==========================================
elif menu == "📥 นำเข้าไฟล์ข้อมูลเดิม (Import Excel / CSV)":
    st.markdown('<div class="main-header">📥 นำเข้าข้อมูลเดิมจากไฟล์ Excel หรือ CSV (Batch Import)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">อัปโหลดไฟล์ข้อมูลเดิมที่มีอยู่เพื่อนำเข้าสู่ฐานข้อมูลและแสดงผลบนแผนที่ทันที</div>', unsafe_allow_html=True)

    with st.expander("⚙️ ตัวเลือกการจัดการข้อมูลก่อนนำเข้า (Data Management Options)", expanded=False):
        c_del1, c_del2 = st.columns([2, 1])
        with c_del1:
            st.write("หากต้องการลบข้อมูลทั้งหมดในระบบก่อนนำเข้าข้อมูลชุดใหม่ สามารถกดปุ่มล้างข้อมูลได้ที่นี่")
        with c_del2:
            if st.button("🗑️ ล้างข้อมูลทั้งหมดในระบบ (Clear All Data)", type="secondary"):
                conn = db.get_connection()
                conn.execute("DELETE FROM inspection_photos")
                conn.execute("DELETE FROM inspections")
                conn.commit()
                conn.close()
                st.success("ล้างข้อมูลเรียบร้อยแล้ว!")
                st.rerun()

    uploaded_file = st.file_uploader(
        "เลือกไฟล์ Excel (.xlsx, .xls) หรือ CSV (.csv) ของคุณ",
        type=["xlsx", "xls", "csv"]
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                try:
                    import_df = pd.read_csv(uploaded_file, encoding="utf-8")
                except Exception:
                    uploaded_file.seek(0)
                    import_df = pd.read_csv(uploaded_file, encoding="cp874")
            else:
                import_df = pd.read_excel(uploaded_file)

            st.success(f"📄 โหลดไฟล์ `{uploaded_file.name}` สำเร็จ! พบข้อมูลทั้งหมด **{len(import_df):,}** แถว")
            st.markdown("##### ตัวอย่างข้อมูล 5 แถวแรก:")
            st.dataframe(import_df.head(5), use_container_width=True)

            st.markdown("---")
            st.markdown("#### 🔗 จับคู่คอลัมน์ในไฟล์ของคุณกับข้อมูลของระบบ (Column Mapping)")
            st.caption("ระบบจะพยายามจับคู่คอลัมน์ให้อัตโนมัติ หากไม่ตรงสามารถเลือกปรับเปลี่ยนได้")

            cols = ["-- ไม่ระบุ (ใช้ค่าเริ่มต้น/คำนวณอัตโนมัติ) --"] + list(import_df.columns)

            def find_best_col(patterns):
                for p in patterns:
                    for col in import_df.columns:
                        if p.lower() in str(col).lower():
                            return col
                return cols[0]

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                map_date = st.selectbox("คอลัมน์ วันที่ (Date)", cols, index=cols.index(find_best_col(["date", "วัน", "เวลา"])))
                map_fy = st.selectbox("คอลัมน์ ปีงบประมาณ (Fiscal Year)", cols, index=cols.index(find_best_col(["งบประมาณ", "fiscal", "ปีงบ", "fy"])))
                map_hazard = st.selectbox("คอลัมน์ ประเภทพิบัติภัย (Hazard Type)", cols, index=cols.index(find_best_col(["hazard", "type", "ภัย", "ประเภท"])))
                map_utm_e = st.selectbox("คอลัมน์ พิกัด UTM_E (Easting)*", cols, index=cols.index(find_best_col(["utm_e", "easting", "utm e", "e_utm", "e"])))
                map_utm_n = st.selectbox("คอลัมน์ พิกัด UTM_N (Northing)*", cols, index=cols.index(find_best_col(["utm_n", "northing", "utm n", "n_utm", "n"])))
                default_zone = st.selectbox("UTM Zone ค่าเริ่มต้น", [47, 48], index=0, help="ภาคใต้ ภาคเหนือ ภาคกลาง ใช้ Zone 47N")

            with col_m2:
                map_location = st.selectbox("คอลัมน์ สถานที่ (Location)", cols, index=cols.index(find_best_col(["สถานที่", "name", "location", "หมู่บ้าน", "จุด", "ชื่อ"])))
                map_subdistrict = st.selectbox("คอลัมน์ ตำบล (Subdistrict)", cols, index=cols.index(find_best_col(["ตำบล", "subdistrict", "ต."])))
                map_district = st.selectbox("คอลัมน์ อำเภอ (District)", cols, index=cols.index(find_best_col(["อำเภอ", "district", "อ."])))
                map_province = st.selectbox("คอลัมน์ จังหวัด (Province)", cols, index=cols.index(find_best_col(["จังหวัด", "province", "จ."])))
                map_details = st.selectbox("คอลัมน์ รายละเอียด (Details)", cols, index=cols.index(find_best_col(["remark", "รายละเอียด", "detail", "หมายเหตุ", "ความเสียหาย"])))

            st.markdown("---")
            if st.button("🚀 ยืนยันและนำเข้าข้อมูลสู่ระบบ (Import Data Now)", type="primary"):
                if map_utm_e == cols[0] or map_utm_n == cols[0]:
                    st.error("⚠️ กรุณาเลือกคอลัมน์พิกัด UTM_E และ UTM_N ให้ถูกต้อง")
                else:
                    progress_bar = st.progress(0)
                    success_count = 0
                    error_count = 0

                    for idx, row in import_df.iterrows():
                        try:
                            raw_e = str(row[map_utm_e]).replace(",", "").strip()
                            raw_n = str(row[map_utm_n]).replace(",", "").strip()
                            e_val = float(raw_e)
                            n_val = float(raw_n)

                            if map_date != cols[0] and pd.notna(row[map_date]):
                                d_val = str(pd.to_datetime(row[map_date], errors="coerce").date())
                                if d_val == "NaT":
                                    d_val = str(datetime.date.today())
                            else:
                                d_val = str(datetime.date.today())

                            fy_val = None
                            if map_fy != cols[0] and pd.notna(row[map_fy]):
                                try:
                                    clean_fy = int(float(str(row[map_fy]).replace("พ.ศ.", "").replace("ปี", "").strip()))
                                    if clean_fy < 2500:
                                        clean_fy += 543
                                    fy_val = clean_fy
                                except Exception:
                                    pass

                            h_val = str(row[map_hazard]) if (map_hazard != cols[0] and pd.notna(row[map_hazard])) else config.HAZARD_TYPES[0]
                            loc_val = str(row[map_location]) if (map_location != cols[0] and pd.notna(row[map_location])) else f"จุดที่ {idx+1}"
                            sub_val = str(row[map_subdistrict]) if (map_subdistrict != cols[0] and pd.notna(row[map_subdistrict])) else "-"
                            dis_val = str(row[map_district]) if (map_district != cols[0] and pd.notna(row[map_district])) else "-"
                            prov_val = str(row[map_province]) if (map_province != cols[0] and pd.notna(row[map_province])) else "ไม่ระบุ"
                            det_val = str(row[map_details]) if (map_details != cols[0] and pd.notna(row[map_details])) else ""

                            db.add_inspection(
                                incident_date=d_val,
                                fiscal_year=fy_val,
                                utm_zone=default_zone,
                                utm_e=e_val,
                                utm_n=n_val,
                                location_name=loc_val,
                                subdistrict=sub_val,
                                district=dis_val,
                                province=prov_val,
                                hazard_type=h_val,
                                severity=config.SEVERITY_LEVELS[1],
                                status=config.STATUS_CHOICES[0],
                                inspector_name="สำนักงานทรัพยากรธรณี เขต 4 (สทข.4)",
                                geological_unit="",
                                details=det_val
                            )
                            success_count += 1
                        except Exception:
                            error_count += 1

                        progress_bar.progress((idx + 1) / len(import_df))

                    st.success(f"🎉 นำเข้าข้อมูลเสร็จสิ้น! สำเร็จ **{success_count:,}** รายการ (ผิดพลาด {error_count} รายการ)")
                    st.info("คลิกไปที่แท็บ '📊 แดชบอร์ดและแผนที่' เพื่อดูการแสดงผลบนแผนที่ดาวเทียมและกราฟวิเคราะห์ได้ทันที!")

        except Exception as err:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {err}")


# ==========================================
# PAGE 5: UTM CONVERTER TOOL
# ==========================================
elif menu == "🧭 เครื่องมือแปลงพิกัด UTM (UTM Converter)":
    st.markdown('<div class="main-header">🧭 เครื่องมือแปลงพิกัด UTM & Geographic (WGS84)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">เครื่องมือช่วยเหลือสำหรับนักธรณีวิทยาในการแปลงพิกัดระหว่าง UTM Zone 47N/48N และ Latitude/Longitude</div>', unsafe_allow_html=True)

    c_tab1, c_tab2 = st.tabs(["➡️ แปลงจาก UTM เป็น Lat/Long", "⬅️ แปลงจาก Lat/Long เป็น UTM"])

    with c_tab1:
        st.markdown("##### กรอกพิกัด UTM (Zone 47N หรือ 48N)")
        uc_col1, uc_col2, uc_col3 = st.columns(3)
        with uc_col1:
            u_zone = st.selectbox("UTM Zone", [47, 48], index=0, key="conv_zone")
        with uc_col2:
            u_e = st.number_input("UTM Easting (เมตร)", value=500000.0, step=10.0, format="%.2f", key="conv_e")
        with uc_col3:
            u_n = st.number_input("UTM Northing (เมตร)", value=900000.0, step=10.0, format="%.2f", key="conv_n")

        if st.button("🔄 แปลงพิกัดเป็น Lat/Long"):
            try:
                res_lat, res_lon = coordinates.utm_to_latlon(u_e, u_n, u_zone)
                st.success(f"""
                **ผลลัพธ์พิกัดทางภูมิศาสตร์ (WGS84 EPSG:4326):**
                - **Latitude (ละติจูด):** `{res_lat:.7f}°`
                - **Longitude (ลองจิจูด):** `{res_lon:.7f}°`
                - **Google Maps Link:** [เปิดใน Google Maps](https://www.google.com/maps?q={res_lat},{res_lon})
                """)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    with c_tab2:
        st.markdown("##### กรอกพิกัด Latitude / Longitude (Decimal Degrees)")
        lc_col1, lc_col2 = st.columns(2)
        with lc_col1:
            in_lat = st.number_input("Latitude (องศาทศนิยม)", value=8.14022, step=0.0001, format="%.6f")
        with lc_col2:
            in_lon = st.number_input("Longitude (องศาทศนิยม)", value=99.00000, step=0.0001, format="%.6f")

        if st.button("🔄 แปลงพิกัดเป็น UTM"):
            try:
                res_e, res_n, res_z = coordinates.latlon_to_utm(in_lat, in_lon)
                st.success(f"""
                **ผลลัพธ์พิกัดกริด UTM (WGS84):**
                - **UTM Zone:** `{res_z}N`
                - **UTM Easting (UTM_E):** `{res_e:,.2f} m`
                - **UTM Northing (UTM_N):** `{res_n:,.2f} m`
                """)
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

    st.markdown("---")
    st.markdown("##### 📚 ข้อมูลทางธรณีวิทยาและการกำหนดค่าพิกัดในประเทศไทย")
    st.markdown("""
    * **WGS84 UTM Zone 47N (EPSG:32647):** ครอบคลุมพื้นที่ลองจิจูด $96^\circ\text{E} - 102^\circ\text{E}$ (ภาคเหนือ, ภาคกลาง, ภาคใต้, ภาคตะวันตก และ กทม.) เมอริเดียนกลาง $99^\circ\text{E}$
    * **WGS84 UTM Zone 48N (EPSG:32648):** ครอบคลุมพื้นที่ลองจิจูด $102^\circ\text{E} - 108^\circ\text{E}$ (ภาคตะวันออกเฉียงเหนือ, ภาคตะวันออกบางส่วน เช่น ตราด จันทบุรี ปราจีนบุรี สระแก้ว นครพนม อุบลราชธานี) เมอริเดียนกลาง $105^\circ\text{E}$
    """)
