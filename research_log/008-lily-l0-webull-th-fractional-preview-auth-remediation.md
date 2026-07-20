# บันทึกการวิจัย 008: แก้เพดาน authentication สำหรับ Webull Thailand UAT

## 1. ข้อมูลพื้นฐาน

- Timestamp UTC: `2026-07-20T06:20:27.200452Z`
- โครงการ: Trend Following - Lily
- Hypothesis ID: `L-0`
- Experiment ID: `L0-WEBULL-TH-FRACTIONAL-PREVIEW-AUTH-REMEDIATION`
- ระดับหลักฐาน: `E0`
- ข้อสรุป: `จำกัดขอบเขตและถูกบล็อกก่อน preview`
- Artifact หลัก: `reports/feasibility/l_0_webull_th_fractional_preview_v2.json`
- Producing commit: `152c8e1e8ecc946b889472707b4b3280e63d4e02`

### อ่านแบบเร็ว

การทดลองเพิ่มเวลารอ authentication จากกรอบเดิมเป็น 30 วินาทีตามพฤติกรรมของ SDK แล้ว แต่ shared UAT ยังไม่เปลี่ยนเป็นสถานะพร้อมใช้งานภายในเวลาที่ล็อกไว้ ระบบจึงหยุดก่อนส่ง preview request แรก ผลนี้ไม่ได้บอกว่า VTI จำนวนใดซื้อขายแบบเศษหุ้นได้หรือไม่ได้ และไม่มีคำสั่งซื้อหรือข้อมูล validation ถูกเปิด

## 2. ปัญหา (คำถาม) และสมมติฐาน

- คำถามวิจัย: ภายในกรอบ 30 วินาที Webull Thailand UAT ยืนยันตัวตนสำเร็จและเปิดให้ทดสอบ preview ของ VTI ได้หรือไม่
- ขอบเขต: shared UAT แถวแรกจากหน้า SDK ทางการ, host `th-api.uat.webullbroker.com`, token create ไม่เกิน 1 ครั้ง, token check ไม่เกิน 7 ครั้งทุก 5 วินาที, `POST /openapi/trade/order/preview` ไม่เกิน 8 ครั้งสำหรับ VTI ตามตาราง QTY เดิม และ request รวมไม่เกิน 16 ครั้ง ห้าม production, balance, positions, order mutation/query, provider และ validation returns
- สมมติฐาน: หาก shared UAT เปลี่ยนเป็นสถานะ `NORMAL` ภายใน 30 วินาที ระบบจะส่ง preview ตามตารางทั้ง 8 ค่าและจำแนกแต่ละค่าเป็น accepted หรือ rejected โดยไม่ส่งคำสั่งซื้อ
- เกณฑ์ตัดสิน: หาก authentication สำเร็จและ preview ครบ 8 ค่า ให้จำแนกผลตาม response ที่ตัดข้อมูลลับแล้ว หาก authentication ยังไม่พร้อมเมื่อครบ 30 วินาที ให้สรุป `blocked_before_preview` และห้ามอนุมานขั้นต่ำนายหน้า

คำถามนี้สั้นและจำกัดอยู่ที่ความพร้อมของ authentication สำหรับการทดลอง preview บน shared UAT เท่านั้น ไม่ได้ถามว่ากลยุทธ์มีกำไรหรือพร้อมใช้เงินจริงหรือไม่

## 3. ขั้นตอนการทดลอง

1. สร้าง gate `l_0_webull_th_fractional_preview_activation_v2` เป็นไฟล์ใหม่โดยเก็บ B4.10 และ B4.11 เดิมไว้ครบ แล้วล็อก runner, schema, validator และ tests ด้วย SHA-256
2. push gate commit `152c8e1e8ecc946b889472707b4b3280e63d4e02` ไปยัง `origin/main` และรอ GitHub Hermetic CI run `29721298183` ผ่านก่อนอ่าน credential หรือเรียก broker
3. อ่าน shared UAT แถวแรกจาก `https://developer.webull.co.th/apis/docs/sdk.md` หนึ่งครั้งเข้าเฉพาะหน่วยความจำของ process โดยไม่พิมพ์หรือบันทึก App Key, App Secret หรือ Account ID
4. เรียก runner v2 ด้วย Python 3.11 และ SDK 2.0.13 เพียงครั้งเดียว ตั้ง polling 30 วินาที ช่วงละ 5 วินาที ปิด retry และติดตั้ง request guard ก่อน authentication
5. ไม่ใช้ `TokenManager.init_token` ซึ่งบันทึก token ลง local storage แต่ใช้การดึง token ในหน่วยความจำและกำหนดให้บันทึกได้เฉพาะรายงานที่ตัดข้อมูลลับแล้ว
6. ตรวจรายงานด้วย validator v2 และตรวจว่าขอบเขต validation returns ยังเป็น `sealed_not_accessed`

## 4. ผลลัพธ์

ผลลัพธ์คือ `blocked_before_preview` โดยมี blocker `authentication_not_normal_within_30_seconds`

ระบบส่ง authentication requests รวม 8 ครั้ง แบ่งเป็น token create 1 ครั้งและ token check 7 ครั้ง เมื่อครบกรอบ 30 วินาที authentication ยังไม่เปลี่ยนเป็น `NORMAL` จึงไม่มี preview request และไม่มีแถวปริมาณ VTI ที่ถูกทดสอบ

ค่าที่เกี่ยวกับ forbidden request, production request, order mutation/query, orders sent, provider call และ paid spend เป็นศูนย์ทั้งหมด ไม่มี raw response หรือข้อมูลส่วนตัวถูกบันทึก และ validation prices, returns, signals, positions, regimes, benchmarks และ PnL ไม่ถูกเปิด

## 5. อภิปรายผล ปัญหา และข้อจำกัด

ผลนี้ตอบคำถามเฉพาะหน้าได้ว่า shared UAT ไม่พร้อมสำหรับ preview ภายในกรอบ 30 วินาทีของการทดลองครั้งนี้ การเพิ่มเพดานจาก B4.11 ทำให้เห็นว่าปัญหาไม่ได้เกิดจากเพดาน 3 requests ที่สั้นเกินไปเพียงอย่างเดียว แต่หลักฐานยังไม่พอจะระบุสาเหตุภายในของ Webull

เราไม่เก็บ raw authentication response เพื่อป้องกัน token และข้อมูลบัญชี จึงไม่เห็นรายละเอียดสถานะภายในมากกว่าคำว่าไม่เป็น `NORMAL` นอกจากนี้ shared UAT เป็นบัญชีสาธารณะที่สภาพอาจเปลี่ยนได้ ผลครั้งนี้จึงไม่ใช่หลักฐานว่า credential ใช้ไม่ได้ถาวร ไม่ใช่หลักฐานว่า endpoint เสีย และไม่ใช่หลักฐานว่า Webull Thailand production ไม่รองรับ fractional order

การเพิ่มเวลารอต่อไปโดยไม่มีข้อมูลใหม่ไม่คุ้มกับการสร้าง gate และการเรียกซ้ำ เพราะยังไม่รู้ว่าระบบต้องการขั้นตอนยืนยันจากภายนอกหรือบัญชีทดสอบเฉพาะหรือไม่ การทดลองครั้งต่อไปควรเกิดเมื่อมีหลักฐานใหม่ เช่น ขั้นตอนยืนยัน token ที่ Webull ระบุชัด หรือ dedicated test account ที่ควบคุมได้

สิ่งที่ห้ามสรุปจากการทดลองนี้:

- ห้ามสรุปว่า VTI ปริมาณใด accepted หรือ rejected เพราะ preview request เป็นศูนย์
- ห้ามสรุปขั้นต่ำนายหน้าหรือขยายผลไปยัง ETF อื่นและ production
- ห้ามสรุปว่ามี fill, execution quality, strategy edge, E2 หรือความพร้อมใช้เงินจริง
- ห้ามใช้ผล E0 นี้เปิด paper trading หรือ validation returns

## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

ข้อสรุป: `จำกัดขอบเขตและถูกบล็อกก่อน preview` B4.12 พิสูจน์ว่า gate, request guard, polling budget และการตัดข้อมูลลับทำงานตามที่ล็อกไว้ แต่ยังไม่ให้หลักฐานเรื่อง fractional preview ของ VTI และไม่ลดข้อจำกัดหลักของ L-0

แนวทางพัฒนาต่อ:

1. ปิดการเรียกซ้ำของ B4.11 และ B4.12 ตามกติกา one-run-only
2. คง L-0 ที่ `scope-restricted E0` และคง L-1 ที่ `scope-restricted E1` โดยไม่เปิด validation window
3. หากต้องทดลอง Webull UAT อีก ให้หาหลักฐานใหม่เกี่ยวกับขั้นตอนยืนยัน authentication หรือ dedicated test account ก่อน แล้วสร้าง gate ใหม่ที่เจ้าของอนุมัติ
4. วาง work order วิจัยถัดไปแยกต่างหาก โดยไม่ใช้ความล้มเหลวด้าน UAT ไปแทนคำตอบเรื่อง edge หรือความสามารถของ production
