# Webull Thailand Read-only Capability Probe

- หลักฐาน: `E0` — ตรวจความสามารถด้านการทำงานเท่านั้น
- ผล: `verified_read_only_and_fractional_candidate_set`
- validation returns: `sealed_not_accessed`

## ผลการตรวจบัญชีแบบไม่เปิดเผยข้อมูลส่วนตัว

Authentication, account list, balance และ positions ตอบกลับสำเร็จทั้งหมด รายงานนี้เก็บเฉพาะชื่อฟิลด์และ hash ของ response ไม่เก็บ Account ID, ยอดเงิน, buying power, หลักทรัพย์ที่ถือ หรือจำนวนหน่วย

## ETF Candidate Set

| Symbol | Status | Fractionable |
|:--|:--|:--|
| VTI | OC | true |
| VGK | OC | true |
| EWJ | OC | true |
| IPAC | OC | true |
| VWO | OC | true |
| IEF | OC | true |
| SCHP | OC | true |
| GLDM | OC | true |
| PDBC | OC | true |
| VNQI | OC | true |

## ขอบเขตของผล

ผลนี้ยืนยันเพียงว่า Webull Thailand production API อ่านบัญชีได้และคืน metadata ของ ETF ตามตาราง ไม่ได้ยืนยันขั้นต่ำต่อคำสั่ง, คุณภาพราคา, slippage, ค่าแลกเงิน, edge, E2 หรือความพร้อมใช้เงินจริง

ไม่มีการเรียก preview/place/replace/cancel order ไม่มี paper trade และไม่ได้เปิด validation returns

## งานถัดไปที่ปลอดภัย

ออกแบบ preregistration แยกสำหรับ `E0 prospective shadow accounting dry run` และขออนุมัติเจ้าของก่อนเริ่ม โดยยังห้ามเรียก preview หรือ order endpoint
