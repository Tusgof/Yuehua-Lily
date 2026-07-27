# บันทึกการวิจัย 010: การลองรัน L-3 ที่แก้ตารางเวลา

## 1. ข้อมูลพื้นฐาน

- Timestamp UTC: `2026-07-27T00:00:00Z`
- โครงการ: Trend Following - Lily
- Hypothesis ID: `L-3`
- Experiment ID: `L3-CORRECTED-RERUN`
- ผู้บันทึก: GPT-5.6 Terra
- ระดับหลักฐาน: `E1`
- ข้อสรุป: `จำกัดขอบเขต`
- Artifact หลัก: `reports/experiments/l_3_corrected_rerun_falsification_report.json`
- Producing commit: `973087e5e2f504a6e1e2298396694626ac9c77d3`

### อ่านแบบเร็ว

คำสั่ง B7.6 อนุญาตการลองรันที่แก้ตารางเพียงครั้งเดียว แต่ตัวตรวจแบบวันอย่างเดียวหยุดที่ `date_only_schema_metadata_missing` ก่อนอ่านผลตอบแทน จึงไม่มีการคำนวณสัญญาณหรือผลการลงทุน และไม่มี ledger ใหม่

## 2. ปัญหา (คำถาม) และสมมติฐาน

- คำถามวิจัย: ตารางก่อนอ่านผลตอบแทนของ L-3 ตรวจผ่านได้อย่างไรโดยไม่เปิดข้อมูลผลตอบแทน?
- ขอบเขต: ใช้เฉพาะ container ที่ระบุในคำสั่งและห้ามเปิด validation
- สมมติฐาน: metadata แบบวันจะยืนยัน schema และตารางได้ก่อนอ่านผลตอบแทน
- เกณฑ์ตัดสิน: หาก preflight หยุดก่อนอ่านผลตอบแทน ให้เป็น `scope_restricted`

## 3. ขั้นตอนการทดลอง

1. ตรวจ gate, hash และ one-run authorization จาก commit ที่ล็อก
2. สแกน metadata และวันโดยไม่ decode หรือ parse ฟิลด์ผลตอบแทน
3. หยุดทันทีเมื่อหา metadata schema ตามสัญญาไม่พบ

## 4. ผลลัพธ์

ผลคือ `date_only_schema_metadata_missing` ก่อน return parsing. `market_returns_read_count` เท่ากับ 0, ไม่มี pre-return schedule attestation และไม่มี fresh real-return ledger row.

## 5. อภิปรายผล ปัญหา และข้อจำกัด

นี่เป็นข้อจำกัดของ preflight format ไม่ใช่ผลของ inverse-volatility sizing. ประวัติ B7.3 ยัง invalidated ตาม B7.4 และไม่ได้ถูกแก้ไข

สิ่งที่ห้ามสรุปจากการทดลองนี้:

- ห้ามสรุปว่า L-3 falsified หรือ not_falsified
- ห้ามสรุป edge, กำไร, validation หรือความพร้อมใช้งานจริง

## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

ข้อสรุป: `จำกัดขอบเขต` เพราะ preflight หยุดก่อนอ่านผลตอบแทนและ validation ยัง sealed.

แนวทางพัฒนาต่อ:

1. การเข้าถึงข้อมูลครั้งต่อไปต้องมี owner authorization ใหม่และสัญญา metadata ที่ตรวจได้โดยไม่เปิด return
2. ห้าม rerun ภายใต้ B7.6 และห้ามเปิด validation
