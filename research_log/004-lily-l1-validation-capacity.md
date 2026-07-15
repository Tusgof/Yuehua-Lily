# บันทึกการวิจัย 004: ความเพียงพอของช่วง Validation สำหรับ L-1

## 1. ข้อมูลพื้นฐาน

- Timestamp UTC: `2026-07-15T00:30:43Z`
- โครงการ: Trend Following - Lily
- Hypothesis ID: `L-1`
- Experiment ID: `L1-VALIDATION-CAPACITY`
- ผู้บันทึก: Codex
- ระดับหลักฐาน: `E1`
- ข้อสรุป: `มี capacity ทางสถิติ แต่ยังห้ามเปิด validation`
- Artifact หลัก: `reports/diagnostics/l_1_validation_capacity.json`
- Producing commit: `b4d7ee8b542b612f6bfb8b9003c8d1e79f919a51`

### อ่านแบบเร็ว

งานรอบนี้ไม่ได้ทดสอบว่ากลยุทธ์ทำกำไรในช่วง validation หรือไม่ แต่ตรวจว่าช่วงเวลาที่ปิดผนึกไว้ยาวพอสำหรับเกณฑ์ `MinTRL_validate` หรือไม่ เรานับได้ 2,637 NYSE sessions และเมื่อใช้ dependence จากช่วง falsification ตามกติกาที่ล็อกไว้ จะได้ประมาณ 20,376 joint independent-bet equivalents สูงกว่าเกณฑ์สูงสุด 8,673 อย่างไรก็ตาม ผลนี้ไม่อนุญาตให้เปิด validation เพราะปัญหา corporate-action provenance ยังไม่จบ และ sensitivity ตาม planning assumptions เดิมยังให้จำนวนไม่ถึงเกณฑ์

## 2. ปัญหา (คำถาม) และสมมติฐาน

- คำถามวิจัย: ช่วง `2016-01-04` ถึง `2026-06-30` มี capacity ถึง `MinTRL_validate` ทั้งสาม null หรือไม่ เมื่อใช้ dependence จากช่วงก่อนปี 2016 โดยไม่อ่าน validation returns?
- ขอบเขต: ใช้เฉพาะปฏิทิน NYSE, เกณฑ์จาก locked L-1 preregistration และ autocorrelation กับ cross-sectional dimension จาก B4; ไม่โหลดราคา ผลตอบแทน สัญญาณ หรือ PnL หลัง `2015-12-31`
- สมมติฐาน: จำนวน session ราวสิบปีน่าจะมากพอเมื่อใช้ cross-sectional breadth ของ ETF แปดตัว แต่ผลอาจอ่อนไหวต่อสมมติฐานเรื่อง serial correlation และจำนวนมิติที่เป็นอิสระ
- เกณฑ์ตัดสิน: ถือว่ามี capacity เมื่อ projected joint independent-bet equivalents ไม่น้อยกว่า 8,673 และ null ทั้งสาม funded; ต่อให้ผ่านก็ยังห้ามเปิด validation หาก data-integrity blocker หรือ owner-approved unlock gate ยังไม่มี

คำถามนี้แยก “มีจำนวนข้อมูลพอหรือไม่” ออกจาก “ผลตอบแทนดีหรือไม่” อย่างตั้งใจ การรู้เพียงจำนวน session และ dependence เดิมไม่เปิดเผยทิศทางหรือขนาดผลตอบแทนใน validation จึงช่วยตัดสินความคุ้มค่าก่อนใช้ข้อมูลที่เปิดได้เพียงครั้งเดียว

## 3. ขั้นตอนการทดลอง

1. อ่านช่วง validation, null ทั้งสาม และ binding MinTRL 8,673 จาก `experiments/l_1_baseline_preregistration.json` ที่มี SHA-256 ตรงกับ locked gate เดิม
2. สร้างปฏิทินตั้งแต่ `2016-01-04` ถึง `2026-06-30` จากวันทำการ จังหวะวันหยุด NYSE, Good Friday, Juneteenth ตั้งแต่ปี 2022 และวันปิดพิเศษเพื่อไว้อาลัยวันที่ `2018-12-05` กับ `2025-01-09` โดยถือวันปิดเร็วเป็น session
3. อ่านเฉพาะ autocorrelation lag 1–5 และ cross-sectional effective dimensions จากผล B4 ก่อนปี 2016 แล้วคำนวณ time-effective observations และ joint independent-bet equivalents ด้วย statistics kernel เดิม
4. เปรียบเทียบ capacity เดียวกันกับทุก null โดยไม่ปรับ threshold และรายงาน planning assumptions เดิมเป็น sensitivity ที่ไม่มีสิทธิ์แทนกติกา actual recalculation
5. ใช้ `DATABENTO_API_02` เรียกเฉพาะ metadata, schema, coverage และ cost estimate ไม่ขอ market data ไม่บันทึก key และไม่เสียเงิน
6. รัน validator ให้คำนวณ session และ capacity ซ้ำจาก source fields พร้อมตรวจว่า maximum return date ยังเป็น `2015-12-31`

## 4. ผลลัพธ์

ช่วง validation มี `2,637` NYSE sessions เมื่อใช้ autocorrelation lag 1–5 เท่ากับ `-0.02680, -0.02792, -0.01373, -0.02338, 0.01165` จากช่วงเดิม จะได้ time-effective observations `3,140.19` ค่าเพิ่มสูงกว่าจำนวน session จริงเพราะ autocorrelation รวมในห้า lag เป็นลบ

เมื่อนำไปคูณ cross-sectional effective dimensions `6.4888` จะได้ projected joint independent-bet equivalents `20,376.00` เทียบกับ binding MinTRL `8,673` หรือ `2.35 เท่า` Null ทั้งสาม ได้แก่ผลเหนือเงินสด, Sharpe ขั้นต่ำ 0.25 และ active return เหนือ matched benchmark จึงมี capacity ตาม actual-recalculation rule ที่ล็อกไว้

ผล sensitivity ให้ภาพที่ระวังมากขึ้น เมื่อใช้ planning autocorrelation ที่เป็นบวกและ cross-sectional dimension เท่ากับ 4 จะได้เพียง `7,603.64` joint independent-bet equivalents หรือต่ำกว่า binding MinTRL ประมาณ `1,069.36` ดังนั้นคำว่า funded ไม่ได้แข็งแรงต่อทุกสมมติฐาน แต่เกิดจากการใช้ dependence ที่วัดจริงจากช่วงก่อนปี 2016 ตามกติกาเดิม

Databento key ผ่าน authenticated metadata access ชุด `ARCX.PILLAR` ที่เกี่ยวข้องเริ่ม `2018-05-01` และ `DBEQ.BASIC` เริ่ม `2023-03-28` จึงไม่ครอบคลุมต้น validation ตั้งแต่ปี 2016 Metadata estimate สำหรับ daily bars แปด ticker มีมูลค่าต่ำกว่า USD 0.10 แต่ schema ที่เห็นไม่มีประวัติ corporate actions แบบที่ต้องการ และเราไม่ได้ซื้อหรือดาวน์โหลดข้อมูล ยอดเครดิต USD 50 เป็นข้อมูลที่เจ้าของแจ้งและยังไม่ได้ยืนยันว่าเกิดจาก real payment ตามกติกา Lily

## 5. อภิปรายผล ปัญหา และข้อจำกัด

ผลนี้ตอบได้เพียงว่าช่วง validation มีขนาดทางสถิติเพียงพอภายใต้กติกา actual recalculation ไม่ได้บอกว่า L-1 จะให้ผลบวก ไม่ได้ตรวจ regime coverage และไม่ได้พิสูจน์ว่า dependence หลังปี 2016 จะเหมือนช่วงก่อนหน้า การใช้ dependence เดิมเป็นการประมาณล่วงหน้าตามกติกาที่ล็อกไว้ ไม่ใช่ข้อเท็จจริงของ validation

ความต่างระหว่าง 20,376 ในกรณีหลักกับ 7,604 ใน sensitivity มีขนาดใหญ่ จึงต้องรายงานควบคู่กัน กรณีหลักพึ่งพา autocorrelation รวมที่เป็นลบและ cross-sectional dimension ที่สูงกว่า planning assumption หากเปิด validation ในภายหลัง ต้องรายงานค่าที่เกิดขึ้นจริงและห้ามใช้ projection นี้แทนผลจริง

Databento อาจมีประโยชน์เป็นแหล่งตรวจราคาและ microstructure ตั้งแต่ปี 2018 แต่ไม่เหมาะเป็นแหล่งเดียวสำหรับ validation ทั้งช่วง และ metadata ที่ตรวจไม่พบ dedicated corporate-actions history จึงไม่แก้ blocker หลัก การมีเครดิตราคาถูกไม่ใช่เหตุผลให้ซื้อข้อมูลที่ไม่ตรงคำถาม

สิ่งที่ห้ามสรุปจากการทดลองนี้:

- ห้ามสรุปว่า L-1 ผ่าน validation มี edge หรือพร้อมเลื่อนเป็น `E2`
- ห้ามสรุปว่า projected independent bets คือ independent bets ที่เกิดขึ้นจริงหลังปี 2016
- ห้ามโหลดราคา ผลตอบแทน สัญญาณ หรือ PnL validation โดยไม่มี owner-approved unlock gate ใหม่
- ห้ามใช้เครดิต Databento จนกว่าจะยืนยัน real-payment provenance และมี named data gap ที่ผ่าน cost guard

## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

ข้อสรุป: `มี capacity ทางสถิติ แต่ยังห้ามเปิด validation` ช่วงปิดผนึกรองรับ MinTRL ทั้งสามภายใต้ actual dependence ที่ล็อกไว้ แต่ planning sensitivity ยัง underfunded และ corporate-action provenance ยังคงเป็น blocker

แนวทางพัฒนาต่อ:

1. หาแหล่ง point-in-time corporate actions ที่ครอบคลุม ETF ทั้งแปดตัว หรือสร้างเกณฑ์ source restriction ใหม่โดยไม่ใช้ validation returns มาช่วยตัดสิน
2. ให้เจ้าของยืนยันว่าเครดิต Databento USD 50 มาจาก real payment ก่อนเสนอ paid request; หากยืนยันไม่ได้ให้ใช้ metadata ฟรีเท่านั้น
3. ทำ Webull capability probe แยกเมื่อ API พร้อม โดยไม่ส่ง preview หรือคำสั่ง และไม่เชื่อมผล broker เข้ากับ edge claim
4. เมื่อ data-integrity blockers ปิดครบแล้ว จึงสร้าง validation unlock gate แยก ขออนุมัติเจ้าของ และย้ำว่าช่วง validation ใช้ได้เพียงครั้งเดียว
