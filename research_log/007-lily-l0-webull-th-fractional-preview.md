# บันทึกการวิจัย 007: ตรวจ fractional preview บน Webull Thailand UAT

## 1. ข้อมูลพื้นฐาน

- Timestamp UTC: `2026-07-20T05:48:17Z`
- โครงการ: Trend Following - Lily
- Hypothesis ID: `L-0`
- Experiment ID: `L0-WEBULL-TH-FRACTIONAL-PREVIEW`
- ระดับหลักฐาน: `E0`
- ข้อสรุป: `จำกัดขอบเขตและถูกบล็อกก่อน preview`
- Artifact หลัก: `reports/feasibility/l_0_webull_th_fractional_preview.json`
- Producing commit: `d3d1f5197b33e8e428c3df6b721d3d70e875dd84`

### อ่านแบบเร็ว

การทดลองยังตอบไม่ได้ว่า Webull Thailand UAT ยอมรับ VTI ขนาดเล็กเพียงใด เพราะขั้นตอน authentication ใช้ครบเพดาน 3 requests ก่อนส่ง preview request แรก ระบบหยุดตาม gate โดยไม่มีคำสั่งซื้อ ไม่มีข้อมูลส่วนตัวในรายงาน และไม่เปิด validation returns

## 2. ปัญหา (คำถาม) และสมมติฐาน

- คำถามวิจัย: Webull Thailand UAT ยอมรับ preview ของ VTI ตามตารางปริมาณ 1 ถึง 0.0000001 หุ้นหรือไม่
- ขอบเขต: shared test account แถวแรกจากเอกสารทางการ, host `th-api.uat.webullbroker.com`, symbol VTI, `POST /openapi/trade/order/preview`, QTY 8 ค่า, authentication ไม่เกิน 3 requests และ preview ไม่เกิน 8 requests; ห้าม production, balance, positions, order endpoint และ validation returns
- สมมติฐาน: หาก authentication ของ shared UAT เสร็จภายในเพดานที่ล็อกไว้ ระบบควรส่ง preview ครบตารางและจำแนกแต่ละปริมาณว่า accepted หรือ rejected โดยไม่ส่งคำสั่งซื้อ
- เกณฑ์ตัดสิน: จำแนกผลได้เมื่อ preview ครบทั้ง 8 ค่า; หาก authentication ไม่เสร็จหรือ request guard หยุดก่อนหน้า ให้สรุปว่าถูกบล็อกก่อน preview และห้ามอนุมานขั้นต่ำต่อคำสั่ง

คำถามนี้ตรวจเฉพาะความสามารถของ request บน UAT ไม่ได้ถามว่ากลยุทธ์ทำกำไรหรือพร้อมใช้เงินจริงหรือไม่

## 3. ขั้นตอนการทดลอง

1. สร้าง gate `l_0_webull_th_fractional_preview_activation_v1` จากคำอนุมัติของเจ้าของ แล้วตรวจ hash ของ B4.10 contract และ runner
2. commit และ push gate ไปยัง `origin/main` ก่อนอ่าน credential หรือเรียก Webull พร้อมรอ Hermetic CI ให้ผ่าน
3. ติดตั้ง `webull-openapi-python-sdk==2.0.13` ใน Python 3.11 ตามรุ่นที่ล็อกไว้
4. เรียกเอกสารสาธารณะทางการรวม 3 requests ได้แก่หน้า SDK สองครั้งและ `llms.txt` หนึ่งครั้ง การเรียกหน้า SDK ครั้งที่สองอ่าน shared test account แถวแรกเข้าหน่วยความจำของ process และไม่พิมพ์หรือบันทึก App Key, App Secret หรือ Account ID
5. เรียก runner ด้วย `--execute` เพียงครั้งเดียว ติดตั้ง request guard ก่อน authentication และอนุญาตเฉพาะ path ที่ล็อกไว้
6. ตรวจรายงานด้วย validator และตรวจ source ของ SDK หลังการทดลองเพื่ออธิบายกลไกการ polling โดยไม่เรียก API เพิ่ม

## 4. ผลลัพธ์

ผลลัพธ์คือ `blocked_before_preview` โดยมี blocker `authentication_request_cap_exceeded`

request attestation แสดง authentication 3 ครั้ง ได้แก่ token create 1 ครั้งและ token check 2 ครั้ง หลังจากนั้น request guard ปฏิเสธการตรวจครั้งที่สี่ตามเพดานที่ล็อกไว้ ไม่มี preview request จึงไม่มีปริมาณใดถูกทดสอบ ทั้ง accepted และ rejected เป็นศูนย์

ค่า `forbidden_request_count`, `production_request_count`, `order_mutation_or_query_count` และ `orders_sent` เป็นศูนย์ ค่าใช้จ่ายเป็น USD 0 ไม่มี raw response, credential หรือ account identifier ถูกบันทึก และ validation returns ยังคง `sealed_not_accessed`

## 5. อภิปรายผล ปัญหา และข้อจำกัด

ข้อเท็จจริงที่ได้คือ request guard ทำงานตรงตาม gate และป้องกัน authentication request ที่สี่ แต่หลักฐานยังไม่แตะคำถามเรื่อง fractional quantity เพราะ preview endpoint ไม่ถูกเรียกเลย

การตรวจ source ของ SDK รุ่น 2.0.13 พบว่า `TokenManager` ตรวจ token ที่ยังไม่เป็น `NORMAL` ทุก 5 วินาที และค่าเริ่มต้นอนุญาตให้รอได้นานถึง 300 วินาที เพดาน authentication 3 requests ของ Lily จึงรองรับเพียง create หนึ่งครั้งและ check สองครั้ง ผลนี้ชี้ว่าการออกแบบ authentication budget ไม่สอดคล้องกับ polling behavior ของ SDK ไม่ได้พิสูจน์ว่า credential ผิดหรือ Webull ปฏิเสธ fractional trading

รายงานจงใจไม่เก็บ raw authentication response จึงไม่สามารถระบุสถานะภายในหรือข้อความจาก server ได้ละเอียดกว่านี้ นี่เป็นข้อจำกัดที่แลกกับการไม่เปิดเผย token และข้อมูลบัญชี นอกจากนี้ shared UAT เป็นสภาพแวดล้อมสาธารณะ จึงไม่ควรใช้ผลไปแทน production หรือบัญชีจริง

สิ่งที่ห้ามสรุปจากการทดลองนี้:

- ห้ามสรุปว่า VTI ขนาดใดผ่านหรือไม่ผ่าน เพราะ preview request เป็นศูนย์
- ห้ามสรุปว่า Webull Thailand มีขั้นต่ำ 0.0000001 หุ้นหรือขั้นต่ำค่าอื่น
- ห้ามสรุปว่า credential ใช้ไม่ได้ หรือ preview endpoint เสีย
- ห้ามสรุปว่ามี fill, execution quality, strategy edge, E2 หรือความพร้อมใช้เงินจริง

## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

ข้อสรุป: `จำกัดขอบเขตและถูกบล็อกก่อน preview` B4.11 ยืนยันว่า gate, hash check, credential redaction และ request guard ทำงาน แต่ยังไม่ให้หลักฐานเรื่อง fractional minimum หรือ preview acceptance ของ VTI

แนวทางพัฒนาต่อ:

1. ห้าม rerun ภายใต้ gate B4.11 เพราะสัญญาเป็น one-run-only และผลถูกบันทึกแล้ว
2. หากต้องการทดลองต่อ ให้ตั้งคำถามใหม่ว่า authentication polling budget เท่าใดจึงเพียงพอสำหรับ shared UAT โดยไม่เพิ่ม request เกินจำเป็น
3. สร้าง gate ใหม่ที่ supersede B4.11 ระบุเพดาน authentication, เวลารอ, stop rule และหลักฐาน redaction ก่อนเรียก API เพิ่ม
4. แม้ authentication สำเร็จในอนาคต ผล preview ยังเป็นเพียง E0 ของ VTI บน UAT และห้ามขยายความไปยังทุก ETF หรือ production
