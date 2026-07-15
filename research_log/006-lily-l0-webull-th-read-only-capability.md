# บันทึกการวิจัย 006: ตรวจความสามารถแบบอ่านอย่างเดียวของ Webull Thailand

## 1. ข้อมูลพื้นฐาน

- Timestamp UTC: `2026-07-15T05:24:36Z`
- โครงการ: Trend Following - Lily
- Hypothesis ID: `L-0`
- Experiment ID: `L0-WEBULL-TH-READ-ONLY-CAPABILITY`
- ผู้บันทึก: Codex
- ระดับหลักฐาน: `E0`
- ข้อสรุป: `จำกัดขอบเขต`
- Artifact หลัก: `reports/feasibility/l_0_webull_th_read_only_capability.json`
- Producing commit: `4d109be190ff28339c5d142958623f0b7e06299e`

### อ่านแบบเร็ว

Webull Thailand production API ยืนยันตัวตนและอ่านข้อมูลบัญชีได้โดยไม่ส่งคำสั่งซื้อขาย ETF ผู้สมัครทั้งสิบตัวมีสถานะซื้อขายได้และคืนค่า `fractionable=true` จึงแก้ข้อสงสัยเรื่องการรองรับ fractional ผ่าน OpenAPI สำหรับรายชื่อชุดนี้ได้ อย่างไรก็ตาม ผลระดับ E0 นี้ยังไม่บอกขั้นต่ำต่อคำสั่ง คุณภาพราคา ค่าแลกเงิน หรือความเหมาะสมของระบบ trend following และไม่อนุญาตให้เริ่ม paper trade

## 2. ปัญหา (คำถาม) และสมมติฐาน

- คำถามวิจัย: บัญชี Webull Thailand และ ETF ผู้สมัครสิบตัวรองรับข้อมูลแบบ read-only และ fractional implementation หรือไม่
- ขอบเขต: บัญชี production ของเจ้าของและ VTI, VGK, EWJ, IPAC, VWO, IEF, SCHP, GLDM, PDBC, VNQI; ตรวจเพียง authentication, account list, balance, positions และ instrument metadata; ไม่อ่าน validation returns และไม่เรียก order endpoint
- สมมติฐาน: หาก Webull Thailand รองรับเส้นทาง ETF สำหรับทุนปัจจุบัน API ควรอ่านบัญชีได้และคืน `status=OC` พร้อม `fractionable=true` ให้ ETF ทั้งสิบตัว
- เกณฑ์ตัดสิน: ผ่านด้านความสามารถเมื่อ read-only endpoint ทั้งสี่ตอบสำเร็จและ ETF ทุกตัวคืนสถานะซื้อขายได้พร้อม fractional; ถ้าขาดตัวใด ให้จำกัดขอบเขตหรือถือว่า probe ถูกบล็อก โดยห้ามใช้ preview เพื่อแก้ข้อสงสัย

คำถามนี้สำคัญเพราะผล sizing เดิมผ่านทางเศรษฐศาสตร์ที่ 8–10 sleeves แต่ยังไม่รู้ว่า broker และ API ของบัญชีไทยรองรับ fractional จริงหรือไม่ หากไม่ตรวจข้อจำกัดนี้ งานออกแบบระบบอาจตั้งอยู่บนความสามารถที่ไม่มีอยู่จริง

## 3. ขั้นตอนการทดลอง

1. ล็อก gate `experiments/l_0_webull_th_read_only_capability_probe.json` และ push ก่อนเรียก API จริง โดยกำหนด Thailand production, SDK 2.0.13, Python 3.11 และ ETF สิบตัวล่วงหน้า
2. ใช้ App Key และ App Secret จาก environment ของผู้ใช้ พร้อมยืนยัน 2FA ในแอป Webull โดยไม่บันทึก credential, access token หรือ Account ID ใน repo
3. ใช้ allowlist บังคับให้เรียกได้เฉพาะ authentication, account list, balance, positions และ instrument list รวม read-only request สี่ครั้ง
4. เก็บเฉพาะชื่อฟิลด์ hash ของ response และ metadata สาธารณะของ ETF ข้อมูลยอดเงิน buying power หลักทรัพย์ที่ถือ และจำนวนหน่วยถูกทิ้งหลังคำนวณ hash ในหน่วยความจำ
5. ใช้ validator ตรวจจำนวน ETF สถานะ fractional ลำดับ endpoint การไม่เรียก order และตราประทับว่า validation ยังไม่ถูกเปิด

## 4. ผลลัพธ์

Authentication สำเร็จ และ endpoint ของ account list, balance และ positions ตอบกลับสำเร็จทั้งสามรายการ ระบบจึงยืนยันได้ว่าบัญชี production ของเจ้าของใช้ read-only account API ได้

Instrument list คืน ETF ครบสิบตัวตามลำดับที่ล็อกไว้ ทุกตัวมี `status=OC` ซึ่งหมายถึงซื้อขายได้ และทุกตัวมี `fractionable=true` ได้แก่ VTI, VGK, EWJ, IPAC, VWO, IEF, SCHP, GLDM, PDBC และ VNQI

มี read-only request ทั้งหมด 4 ครั้ง ค่า `preview_calls`, `order_endpoint_calls` และ `orders_sent` เป็นศูนย์ ค่าใช้จ่ายข้อมูลเป็น USD 0 และ validation returns ยังคง `sealed_not_accessed`

## 5. อภิปรายผล ปัญหา และข้อจำกัด

หลักฐานสนับสนุนว่า Webull Thailand OpenAPI ในบัญชีจริงมีองค์ประกอบพื้นฐานที่ Lily ต้องใช้สำหรับ fractional ETF path: อ่านบัญชีได้และระบุ ETF ชุดปัจจุบันว่าแบ่งหน่วยได้ ผลนี้แก้ข้อจำกัดเดิมที่อาศัยเพียงเอกสารสาธารณะซึ่งยังไม่ยืนยันราย ticker

แต่ `fractionable=true` เป็น metadata ไม่ใช่หลักฐานว่าคำสั่งขนาดเล็กทุกขนาดจะผ่านจริง เราไม่ได้ตรวจขั้นต่ำต่อคำสั่ง ค่าธรรมเนียมจริง ค่าแลกเงินบาทเป็นดอลลาร์ fill, slippage, เวลา posting ของ corporate actions หรือความต่างระหว่างบัญชี broker กับระบบบัญชีของกลยุทธ์ นอกจากนี้ field `instrument_type` ใน response ชุดนี้ไม่มีค่า จึงควรอ้างอิง symbol, status และ fractionable เท่านั้น

สิ่งที่ห้ามสรุปจากการทดลองนี้:

- ห้ามสรุปว่ากลยุทธ์มี edge หรือผ่านระดับ E2
- ห้ามสรุปว่าพอร์ตทุน USD 1,000–2,000 พร้อมใช้งานจริงโดยไม่มีข้อจำกัดอื่น
- ห้ามสรุปว่าข้อมูล corporate actions ในอดีตถูกต้อง
- ห้ามถือว่าผลนี้อนุญาตให้ preview ส่งคำสั่ง paper trade หรือใช้เงินจริง

## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

ข้อสรุป: `จำกัดขอบเขต` Webull Thailand production ผ่านการตรวจ read-only และ ETF ผู้สมัครทั้งสิบตัวรองรับ fractional metadata แต่ L-0 ยังจำกัดขอบเขตเรื่องขั้นต่ำต่อคำสั่ง ค่าแลกเงิน คุณภาพ execution และต้นทุนจริง

แนวทางพัฒนาต่อ:

1. ออกแบบและขออนุมัติ gate ใหม่สำหรับ `E0 prospective shadow accounting dry run` โดยล็อก materiality thresholds ก่อนเห็น event แรก และยังไม่อ้าง edge
2. กำหนดวิธีตรวจขั้นต่ำต่อคำสั่งและต้นทุน operational โดยไม่ใช้เงินจริงหรือเรียก preview จนกว่าจะมีคำสั่งอนุมัติแยกที่ชัดเจน
3. หาก dry run มี corporate-action event น้อยเกินไป ให้รายงานว่าหลักฐานไม่พอ ห้ามตีความว่าความต่างในอดีตมีขนาดเล็ก
