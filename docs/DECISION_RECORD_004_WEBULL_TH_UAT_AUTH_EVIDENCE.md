# Decision Record 004 — ขอบเขตการอ้างอิง Webull Thailand UAT

- **Date**: 2026-07-23
- **Status**: accepted by the owner
- **Order**: `B4.13`
- **Hypothesis**: `L-0` (linked `L-1` remains unchanged)
- **Evidence status**: `E0 scope_restricted`
- **Validation window**: `sealed_not_accessed`

## คำถามและขอบเขต

คำถามคือ เอกสารสาธารณะของ Webull Thailand ให้สิทธิ์เข้าถึง UAT หรือมีเส้นทางยืนยันตัวตนและการจัดสรรบัญชี UAT ที่เจ้าของควบคุมได้ เพื่อให้พิจารณา probe ใหม่อย่างปลอดภัยหรือไม่

งานนี้เป็นการตรวจเอกสารแบบ static เท่านั้น ไม่มีการเรียก broker หรือ provider API, authentication, app/SMS/2FA flow, preview, order, production, paper trading, หรือ real-money action และไม่มีการอ่านหรือบันทึก credential, token หรือ account identifier

## แหล่งข้อมูลที่ตรวจ

- `https://developer.webull.co.th/apis/docs/sdk.md` ตรวจเมื่อ `2026-07-23T16:54:04Z` โดยมี HTTP status `200`, `Last-Modified` `2026-07-19T03:14:09Z`, ETag `W/"131f-19f785def7f"` และ SHA-256 ของเนื้อหา UTF-8 `614ef29ba9978573a181ebdf04f6bd321c8874ae386669d1d90359342c13f866`
- `https://developer.webull.co.th/apis/docs/trade-api/getting-started/` ตรวจว่าเข้าถึงได้ด้วย HTTP status `200` เมื่อ `2026-07-24`
- `https://developer.webull.co.th/apis/docs/market-data-api/getting-started/` ตรวจว่าเข้าถึงได้ด้วย HTTP status `200` เมื่อ `2026-07-24`

## หลักฐาน

การตรวจแบบ redacted ยืนยันเพียงว่า SDK markdown อ้างถึง Thailand UAT host และมีคำเกี่ยวกับ two-factor authentication, verification และ test account การอ้างถึง hostname นี้ไม่ใช่หลักฐานว่า Webull เปิด UAT เป็นบริการสาธารณะ หรือให้ Lily มีสิทธิ์ใช้งาน

สำหรับการตัดสินใจนี้ หน้าสาธารณะที่ตรวจคือ getting-started ของ Trade API และ Market Data API ตามรายการข้างต้น ทั้งสองหน้าไม่ให้คำสั่งสำหรับจัดสรรบัญชี UAT ที่เจ้าของควบคุมได้ หรือเส้นทาง authentication แบบไม่ต้องยืนยันตัวตน ผลการตรวจไม่แสดง ไม่บันทึก และไม่ใช้ค่า credential ใด ๆ

## การตัดสินใจ

สำหรับ Lily hostname นี้จึงเป็นเพียง `unverified_reference` ไม่ใช่ UAT ที่พิสูจน์ได้ว่าเข้าถึงได้ หลัง B4.12 Lily ไม่มีสิทธิ์ใช้งาน UAT ที่ยืนยันได้ จนกว่าจะมีหลักฐานทางการใหม่ที่ระบุขั้นตอนยืนยันที่ทำซ้ำได้ หรือมี dedicated test account ที่เจ้าของควบคุมได้

ข้อนี้เป็นข้อจำกัดเชิงปฏิบัติการระดับ `E0` เท่านั้น ไม่ได้พิสูจน์ว่า Webull มีข้อบกพร่องถาวร ไม่ได้พิสูจน์ผล fractional preview ของ VTI ไม่ได้ยืนยันความสามารถของ production และไม่เกี่ยวกับคุณภาพการส่งคำสั่งหรือ strategy edge

ไม่สร้าง locked gate สำหรับ B4.13 เพราะไม่มีการเรียก broker หากจะมี probe ในอนาคต ต้องมีหลักฐานใหม่, owner approval ชัดเจน และ locked gate ใหม่ก่อนเสมอ โดย B4.11 และ B4.12 ยังคงเป็น one-run-only

## สิ่งที่การตัดสินใจนี้ไม่อนุญาต

- ไม่อนุญาตให้ rerun B4.11 หรือ B4.12
- ไม่อนุญาต UAT authentication, preview, order, production, paper trading หรือ real-money action
- ไม่อนุญาตเปิด validation prices, returns, signals, positions, regimes, benchmarks หรือ PnL
- ไม่อนุญาตอ้าง fractional minimum, execution quality, E2, edge หรือ deployment readiness

## งานถัดไปที่ปลอดภัย

รอหลักฐานทางการใหม่หรือ dedicated test account ที่เจ้าของควบคุมได้ แล้วขออนุมัติ work order และ locked gate ใหม่แยกต่างหากก่อนพิจารณา broker probe
