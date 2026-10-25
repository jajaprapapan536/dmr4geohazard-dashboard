"""
Seed realistic geological hazard inspection data in Thailand for initial dashboard demonstration.
"""
from db import init_db, add_inspection, get_all_inspections
import coordinates

SAMPLE_DATA = [
    {
        "date": "2026-09-15",
        "zone": 47,
        "utm_e": 498230.0,
        "utm_n": 2077540.0,
        "location": "ทางหลวงชนบท ชม.4051 กม.14 บ้านแม่ลาย",
        "subdistrict": "แม่ออน",
        "district": "แม่ออน",
        "province": "เชียงใหม่",
        "hazard_type": "ดินถล่ม / หินร่วง (Landslide / Rockfall)",
        "severity": "สูง (High - กระทบโครงสร้างพื้นฐาน/บ้านเรือน)",
        "status": "ตรวจสอบแล้วเสร็จ (Completed)",
        "inspector": "ดร.สมชาย ธรณีวิทยา",
        "geological_unit": "หินแปรกลุ่มหินแม่ฮ่องสอน (Phyllite / Schist)",
        "details": "เกิดเหตุดินสไลด์ไหลทับผิวจราจร 1 ช่องทาง หลังฝนตกสะสมต่อเนื่อง 150 มม. ความยาวรอยเลื่อนไถลประมาณ 35 เมตร ความลึกระนาบเลื่อน 3-4 เมตร ดินผุพังตัวสูง มีน้ำซึมออกจากแนวตัดลาดเขา ได้แนะนำติดตั้งตาข่ายกันหินและปรับแนวระบายน้ำข้างทาง"
    },
    {
        "date": "2026-09-28",
        "zone": 47,
        "utm_e": 491120.0,
        "utm_n": 894320.0,
        "location": "สวนปาล์มน้ำมัน ม.3 บ้านควนเกย",
        "subdistrict": "อ่าวลึกเหนือ",
        "district": "อ่าวลึก",
        "province": "กระบี่",
        "hazard_type": "หลุมยุบ (Sinkhole)",
        "severity": "วิกฤต (Critical - เสี่ยงต่อชีวิต/ต้องอพยพเร่งด่วน)",
        "status": "เฝ้าระวังต่อเนื่อง (Monitoring)",
        "inspector": "น.ส.กานดา พิบัติภัย",
        "geological_unit": "หินปูนกลุ่มหินราชบุรี (Ratburi Limestone)",
        "details": "พบหลุมยุบขนาดเส้นผ่านศูนย์กลาง 12 เมตร ลึกประมาณ 8 เมตร ก้นหลุมพบโพรงเชื่อมต่อกับถ้ำหินปูนใต้ดิน มีน้ำไหลลอดผ่าน เสี่ยงต่อการขยายตัวเข้าใกล้บ้านเรือนราษฎรระยะ 15 เมตร กั้นแนวเขตห้ามเข้าและติดตั้งหมุดเฝ้าระวังการทรุดตัว"
    },
    {
        "date": "2026-10-05",
        "zone": 47,
        "utm_e": 512300.0,
        "utm_n": 1642100.0,
        "location": "ใกล้แนวอ่างเก็บน้ำเขื่อนศรีนครินทร์ ม.5",
        "subdistrict": "ท่ากระดาน",
        "district": "ศรีสวัสดิ์",
        "province": "กาญจนบุรี",
        "hazard_type": "แผ่นดินไหว / รอยเลื่อนมีพลัง (Earthquake / Active Fault)",
        "severity": "ปานกลาง (Medium - ส่งผลกระทบพื้นที่การเกษตร/สิ่งปลูกสร้างเล็กน้อย)",
        "status": "ตรวจสอบแล้วเสร็จ (Completed)",
        "inspector": "นายอนุชา นักวิชาการธรณี",
        "geological_unit": "กลุ่มรอยเลื่อนศรีสวัสดิ์ (Srisawat Fault Zone)",
        "details": "ตรวจวัดแผ่นดินไหวขนาด 3.2 ตามมาตราริกเตอร์ ตรวจสอบพื้นที่พบรอยแยกผิวดินยาว 20 เมตร ทิศทาง NW-SE ไม่มีอาคารแตกร้าวรุนแรง เขื่อนศรีนครินทร์ปลอดภัยตามเกณฑ์มาตรฐาน"
    },
    {
        "date": "2026-10-12",
        "zone": 47,
        "utm_e": 695000.0,
        "utm_n": 1618000.0,
        "location": "ชุมชนหน้าพระลาน ม.4 ใกล้โรงโม่หิน",
        "subdistrict": "หน้าพระลาน",
        "district": "เฉลิมพระเกียรติ",
        "province": "สระบุรี",
        "hazard_type": "หลุมยุบ (Sinkhole)",
        "severity": "ปานกลาง (Medium - ส่งผลกระทบพื้นที่การเกษตร/สิ่งปลูกสร้างเล็กน้อย)",
        "status": "ตรวจสอบแล้วเสร็จ (Completed)",
        "inspector": "ดร.สมชาย ธรณีวิทยา",
        "geological_unit": "หินปูนยุคเพอร์เมียน (Permian Limestone)",
        "details": "เกิดหลุมยุบขนาดกว้าง 4 เมตร ลึก 3.5 เมตร ริมถนนซอย คาดว่าเกิดจากระดับน้ำใต้ดินลดลงอย่างรวดเร็วร่วมกับการละลายตัวของโพรงหินปูน ได้ประสานงาน อบต. กลบด้วยหินคลุกและเทคอนกรีตปิดปากหลุม"
    },
    {
        "date": "2026-10-18",
        "zone": 48,
        "utm_e": 348500.0,
        "utm_n": 1928000.0,
        "location": "ทางขึ้นภูชี้ฟ้า กม.8 บ้านร่มฟ้าทอง",
        "subdistrict": "ปอ",
        "district": "เวียงแก่น",
        "province": "เชียงราย",
        "hazard_type": "ดินถล่ม / หินร่วง (Landslide / Rockfall)",
        "severity": "สูง (High - กระทบโครงสร้างพื้นฐาน/บ้านเรือน)",
        "status": "อยู่ระหว่างตรวจสอบ (Under Investigation)",
        "inspector": "น.ส.กานดา พิบัติภัย",
        "geological_unit": "หินทรายและหินดินดาน (Sandstone & Shale)",
        "details": "หินร่วงขนาด 1.5 - 2 ลูกบาศก์เมตร กลิ้งลงมาขวางถนนเนื่องจากรอยแตกในเนื้อหินขยายตัวจากน้ำฝน เจ้าหน้าที่เคลียร์ก้อนหินออกจากผิวทางแล้ว อยู่ระหว่างสำรวจแนวหน้าผาด้านบนเพื่อประเมินความเสี่ยง"
    },
    {
        "date": "2026-10-22",
        "zone": 47,
        "utm_e": 668000.0,
        "utm_n": 1498000.0,
        "location": "พื้นที่ริมคลองสำโรง ม.7",
        "subdistrict": "บางพลีใหญ่",
        "district": "บางพลี",
        "province": "สมุทรปราการ",
        "hazard_type": "ดินทรุดตัว / ดินแยก (Land Subsidence / Ground Crack)",
        "severity": "ปานกลาง (Medium - ส่งผลกระทบพื้นที่การเกษตร/สิ่งปลูกสร้างเล็กน้อย)",
        "status": "อยู่ระหว่างตรวจสอบ (Under Investigation)",
        "inspector": "นายอนุชา นักวิชาการธรณี",
        "geological_unit": "ดินเหนียวกรุงเทพ (Bangkok Soft Clay)",
        "details": "ทางเดินคอนกรีตเลียบคลองทรุดตัวต่างระดับ 30-50 ซม. ความยาว 80 เมตร คันดินริมตลิ่งเกิดการเคลื่อนตัวเนื่องจากระดับน้ำในคลองลดต่ำลงร่วมกับน้ำหนักบรรทุก"
    }
]


def seed():
    init_db()
    df = get_all_inspections()
    if len(df) == 0:
        print("Seeding sample geohazard inspections...")
        for item in SAMPLE_DATA:
            add_inspection(
                incident_date=item["date"],
                utm_zone=item["zone"],
                utm_e=item["utm_e"],
                utm_n=item["utm_n"],
                location_name=item["location"],
                subdistrict=item["subdistrict"],
                district=item["district"],
                province=item["province"],
                hazard_type=item["hazard_type"],
                severity=item["severity"],
                status=item["status"],
                inspector_name=item["inspector"],
                geological_unit=item["geological_unit"],
                details=item["details"]
            )
        print(f"Successfully seeded {len(SAMPLE_DATA)} records.")
    else:
        print(f"Database already contains {len(df)} records. Skipping seed.")


if __name__ == "__main__":
    seed()
