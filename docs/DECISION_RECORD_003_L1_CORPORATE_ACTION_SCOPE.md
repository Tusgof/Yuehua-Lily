# Decision Record 003 — ยอมรับข้อจำกัด Corporate Actions ของ L-1

- **Date**: 2026-07-15
- **Status**: accepted by the owner
- **Hypothesis**: `L-1`
- **Evidence status**: `E1 scope_restricted`
- **Validation window**: `sealed_not_accessed`

## การตัดสินใจ

เจ้าของยอมรับว่าข้อมูล corporate actions ของ L-1 ยังไม่มีหลักฐานแบบ point-in-time revision archive และให้พักการค้นหา provider เพิ่มไว้ก่อน L-1 จึงคงอยู่ที่ `E1 scope_restricted` โดยไม่เปิด validation ไม่เลื่อนเป็น `E2` และไม่อ้างว่าพบ edge

เหตุผลคือ B4.4 ดึง Alpha Vantage ครบ 16 payload และพบว่า 11 จาก 16 คู่ก่อนปี 2016 ตรงกับ Yahoo แบบ exact แต่อีก 5 คู่ dividend ไม่ตรง การซื้อหรือค้นข้อมูลเพิ่มตอนนี้อาจใช้ทรัพยากรมากกว่าประโยชน์ ในขณะที่ความเป็นไปได้ด้าน broker และการทำงานจริงยังไม่ได้ตรวจครบ

การยอมรับนี้ไม่แปลว่าความต่างในอดีตมีขนาดเล็ก ไม่ได้ตัดสินว่า Alpha Vantage หรือ Yahoo ถูกกว่า และไม่อนุญาตให้เลือกค่าของ provider ตามผลตอบแทนที่ดูดีกว่า

## สถานะของการค้นหาข้อมูล

- พักการค้นหา corporate-action provider ใหม่
- ไม่ซื้อข้อมูล corporate actions เพิ่ม
- เก็บ raw containers, hashes, reports และข้อจำกัดเดิมไว้ครบ
- เปิดการค้นหาใหม่ได้เมื่อมีแหล่งฟรีหรือแหล่งที่มีอยู่แล้วซึ่งให้ revision provenance จริง, dry run พบความต่างที่ผ่านเกณฑ์ materiality ที่ล็อกไว้, broker ledger ตรวจสอบไม่ได้ หรือเจ้าของเปลี่ยนเป้าหมายเป็นเส้นทาง E2

## Prospective Shadow Accounting

อนาคตอาจทำ paper-trade dry run เพื่อดูว่าความต่างของแหล่ง corporate actions ส่งผลต่อเงินสด จำนวนหน่วย น้ำหนักเป้าหมาย และคำสั่ง rebalance หรือไม่ แต่ต้องเป็น `E0 operational dry run` ที่มี `edge_claim: none` เท่านั้น

ก่อนเริ่ม dry run ต้องมี gate ใหม่ที่ล็อกอย่างน้อย:

1. stream ที่นำมาเทียบ ได้แก่ broker หรือ paper-account ledger, Alpha Vantage current snapshot และ strategy-accounting stream ที่เลือกไว้ล่วงหน้า
2. ฟิลด์ event วันที่ เงินสด จำนวนหน่วย น้ำหนักเป้าหมาย คำสั่ง และ source hash
3. เกณฑ์ materiality สำหรับ cash, units, weights, order notional และ posting delay
4. ระยะเวลาหรือกติกาเมื่อมี event น้อยเกินไป
5. stop conditions และข้อห้ามเรื่อง edge, historical-return correctness, E2 และ deployment

Broker ledger เป็นเพียง operational reference ว่าบัญชีจำลองบันทึกอะไร ไม่ใช่ research ground truth และ dry run ในอนาคตไม่สามารถพิสูจน์ย้อนหลังว่าความต่างก่อนปี 2016 ไม่มีนัยสำคัญได้

## สิ่งที่การตัดสินใจนี้ไม่อนุญาต

- ไม่อนุญาตให้เริ่ม paper trade ทันที
- ไม่อนุญาต preview หรือส่งคำสั่งซื้อขาย
- ไม่อนุญาตเปิด validation prices, returns, signals, positions, regimes, benchmarks หรือ PnL
- ไม่อนุญาตอ้าง edge, E2, deployment readiness หรือใช้เงินจริง
- ไม่อนุญาตตั้งเกณฑ์ materiality หลังเห็น event ของ dry run แล้ว

## งานถัดไปที่ปลอดภัย

ทำ Webull Thailand capability probe แบบ read-only โดยไม่ preview และไม่ส่ง order เมื่อทราบความสามารถของ broker แล้วจึงออกแบบ preregistration ของ E0 shadow-accounting dry run เป็นงานแยกและขออนุมัติเจ้าของอีกครั้ง

## Source Lineage

- `reports/data_quality/l_1_alpha_vantage_corporate_actions.json`: ผล B4.4 และข้อจำกัด current snapshot
- `docs/EVIDENCE_TIER_POLICY.md`: ขอบเขต E0 paper dry run ที่ตรวจ operations เท่านั้น
- Local Wiki `wiki/concepts/strategy-research-workflow.md`, SHA-256 `25d5ebb09648fc12c7e531d6fd4d951a937c7c4ded329ca1302b3e920194522d`: แยกการตัดสินใจ revise, paper trade และ deploy พร้อม stop conditions
