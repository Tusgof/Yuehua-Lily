# บันทึกการวิจัย 009: การรัน L-3 falsification หนึ่งครั้ง

## 1. ข้อมูลพื้นฐาน

- Timestamp UTC: `2026-07-26T00:00:00Z`
- โครงการ: Trend Following - Lily
- Hypothesis ID: `L-3`
- Experiment ID: `L3-FALSIFICATION-ONE-RUN`
- ผู้บันทึก: GPT-5.6 Terra
- ระดับหลักฐาน: `E1`
- ข้อสรุป: `จำกัดขอบเขต`
- Artifact หลัก: `reports/experiments/l_3_falsification_report.json`
- Producing commit: `3e3cfc773b8e327dca63bfdd8f2a1b103376173d`

### อ่านแบบเร็ว

การรันที่ได้รับอนุญาตเพียงครั้งเดียวผ่าน preflight ของ container และไม่ได้เปิด validation แต่บันทึก weekly paired observations 500 รายการ เกินเพดานที่ล็อกไว้ 465 รายการ ผลชั่วคราวจึงใช้ตัดสิน L-3 ไม่ได้ ไม่มีการรันซ้ำ และยังห้ามอ้างว่าเป็น edge.

## 2. ปัญหา (คำถาม) และสมมติฐาน

- คำถามวิจัย: ภายใต้กติกา L-3 ที่ล็อกไว้ การให้น้ำหนัก `q / volatility` ลด HHI ได้หรือไม่ โดยไม่เกินเพดานตัวอย่างและผลข้างเคียงที่กำหนด
- ขอบเขต: ETF แปดตัวใน container falsification ถึง `2015-12-31` เท่านั้น; ไม่เปิดหรือรวม validation
- สมมติฐาน: การให้น้ำหนักตาม inverse volatility ลดความกระจุกตัวของ component risk โดยไม่เพิ่มผลข้างเคียงเกินกติกา
- เกณฑ์ตัดสิน: ใช้หนึ่ง weekly paired portfolio observation ต่อสัปดาห์, `MinTRL_falsify` 49 และเพดาน optimistic 465; หากข้อมูลเกินเพดาน ผลต้องเป็น `scope_restricted`

คำถามนี้ทดสอบเฉพาะสัญญากลไกการจัดขนาด L-3 ไม่ได้ทดสอบความสามารถทำกำไร และไม่อนุญาตให้ใช้ validation.

## 3. ขั้นตอนการทดลอง

1. ตรวจ hash ของ gate และ one-run authorization ก่อนเปิด container
2. ตรวจ schema, วันสูงสุด, และลำดับ ETF ก่อนอ่าน return
3. ทำหนึ่ง real-return decision run และบันทึก append-only ledger
4. ตรวจ report, validation seal, และเพดาน weekly observation หลังรัน

## 4. ผลลัพธ์

container ผ่าน preflight: ลำดับ ETF ตรงกับที่ล็อกไว้ และวันสูงสุดคือ `2015-12-31` จึงไม่มี validation ถูกเปิดอ่าน การรันเพียงครั้งเดียวบันทึก weekly paired observations 500 รายการ ซึ่งเกินเพดาน 465 รายการ

ตัวเลข 500 ไม่ใช่หลักฐานเพิ่มความน่าเชื่อถือ เพราะเกิดจากการรวม warm-up decisions ก่อนขอบเขต falsification ที่ควรใช้ ผลชั่วคราวจึงถูกยกเลิกและไม่มีผล falsification หรือ not_falsified.

## 5. อภิปรายผล ปัญหา และข้อจำกัด

ข้อผิดพลาดเป็นปัญหาการกำหนด observation window ใน runner ไม่ใช่ผลของกลไก inverse-volatility ข้อสั่งงานนี้อนุญาตเพียงหนึ่ง real-return decision run จึงห้ามแก้แล้วรันใหม่

สิ่งที่ห้ามสรุปจากการทดลองนี้:

- ห้ามสรุปว่า L-3 ถูก falsified หรือ not_falsified
- ห้ามสรุปว่ามี edge, validation, ความสามารถทำกำไร หรือความพร้อมใช้งานจริง
- ห้ามใช้หรือเปิดข้อมูล validation ช่วง `2016-01-04` ถึง `2026-06-30`

## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

ข้อสรุป: `จำกัดขอบเขต` L-3 เป็น `E1 scope_restricted` เพราะการรันเพียงครั้งเดียวเกินเพดาน 465 รายการ ผลจึงไม่รองรับการตัดสินสมมติฐาน และ `edge_claim` ยังคง `none`.

แนวทางพัฒนาต่อ:

1. หากเจ้าของอนุมัติในอนาคต ต้องสร้าง preregistration และ one-run order ใหม่ที่ตรวจขอบเขต weekly decision date ก่อนอ่าน return
2. คง validation seal ไว้จนกว่าจะมีคำสั่งเจ้าของใหม่ที่ชัดเจน

## ภาคผนวกแก้ไข B7.4: สถานะ ledger

เมื่อ 2026-07-27 มีการตรวจพบว่า ledger แถวเดิมยังเก็บคำว่า `falsified` แม้รายงานสุดท้ายระบุ `scope_restricted` แถวเดิมถูกเก็บไว้ตามประวัติและไม่ได้แก้ไข B7.4 เพิ่ม invalidation event หนึ่งรายการที่ผูก hash ของ original ledger row และ final report

คำว่า `falsified` ใน original ledger เป็นเพียงผลชั่วคราวและ invalid แล้ว เช่นเดียวกับ metrics ชั่วคราวทั้งหมด จึงห้ามใช้สรุปผล L-3. สถานะที่อ้างอิงได้เพียงสถานะเดียวคือ `E1 scope_restricted`, `edge_claim none`, validation sealed และห้าม rerun. การแก้ไขนี้อ่าน market returns เพิ่ม `0` รายการ.
