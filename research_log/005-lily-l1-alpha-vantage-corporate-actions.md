# บันทึกการวิจัย 005: ตรวจ corporate actions ของ ETF แปดตัวด้วย Alpha Vantage

## 1. ข้อมูลพื้นฐาน

- Timestamp UTC: `2026-07-15T02:03:00Z`
- โครงการ: Trend Following - Lily
- Hypothesis ID: `L-1`
- Experiment ID: `L1-ALPHA-VANTAGE-CORPORATE-ACTIONS`
- ผู้บันทึก: Codex
- ระดับหลักฐาน: `E1`
- ข้อสรุป: `จำกัดขอบเขต`
- Artifact หลัก: `reports/data_quality/l_1_alpha_vantage_corporate_actions.json`
- Producing commit: `e6355a746d05433b76427ed4878f3e2fb46b8e43`

### อ่านแบบเร็ว

เราดึงประวัติเงินปันผลและการแตกหน่วยจาก Alpha Vantage ครบ 16 ชุดโดยไม่เสียเงิน แล้วเทียบเฉพาะเหตุการณ์ก่อนปี 2016 กับ Yahoo เดิม ผลตรงกัน 11 จาก 16 คู่ แต่ต่างกัน 5 คู่ จึงใช้ Alpha Vantage เป็นแหล่งตรวจอิสระแบบข้อมูลปัจจุบันได้เท่านั้น ยังใช้ยืนยันข้อมูลแบบ point-in-time หรือเปิด validation ไม่ได้

## 2. ปัญหา (คำถาม) และสมมติฐาน

- คำถามวิจัย: Alpha Vantage ยืนยัน dividend และ split ของ ETF แปดตัวก่อนปี 2016 ตรงกับ Yahoo ทุกคู่หรือไม่
- ขอบเขต: ดึง `DIVIDENDS` และ `SPLITS` ของ VTI, VGK, EWJ, VWO, IEF, TIP, GLD และ DBC; เทียบ event ตั้งแต่ 2006-02-03 ถึง 2015-12-31; ไม่เปิดราคาและผลตอบแทน validation
- สมมติฐาน: หากทั้งสอง provider บันทึกเหตุการณ์เดียวกัน วันที่และจำนวนเงินหรืออัตรา split ควรตรงกันเมื่อเทียบด้วยเลขทศนิยมโดยไม่ปรับ tolerance ตามผล
- เกณฑ์ตัดสิน: ผ่านเฉพาะเมื่อ payload ครบ 16 ชุดและทุก event ก่อนปี 2016 ตรงกัน; หากมีความต่างหรือไม่มี revision archive ให้จำกัดขอบเขตและห้ามปลด validation

คำถามนี้สำคัญเพราะ L-1 ใช้ ETF ที่มีเงินปันผลและ split การบันทึก event ผิดสามารถเปลี่ยน adjusted price และผลตอบแทนได้ เราจึงต้องตรวจแหล่งอิสระก่อนเชื่อผลการทดลองระยะ validation

## 3. ขั้นตอนการทดลอง

1. ล็อก ETF แปดตัวและ endpoint สองชนิด รวม 16 คู่ พร้อมกำหนดเพดาน 25 attempts ต่อวัน เว้นอย่างน้อย 15 วินาที และค่าใช้จ่าย USD 0
2. อ่าน key จากตัวแปร `ALPHAVANTAGE_API_FREE` เฉพาะตอนรัน ไม่บันทึก key, URL ที่มี key, account identifier หรือ absolute path ลง artifact
3. เก็บ response แบบ immutable ใต้ `LILY_DATA_ROOT` ทำ SHA-256 รายไฟล์ สร้าง normalized dataset ด้วยเลขทศนิยม และหยุดทันทีเมื่อพบ service message หรือ schema เปลี่ยน
4. ตรวจ Yahoo container เดิมว่าข้อมูลตลาดไม่ข้าม `2015-12-31` แล้วอ่านเฉพาะ corporate-action events เพื่อเทียบวันที่และค่าทศนิยมแบบตรงตัว
5. เก็บรายละเอียดความต่างไว้นอก git รายงาน tracked เฉพาะจำนวน ช่วงวันที่ schema และ hashes โดยไม่แสดง event amount รายแถว
6. ตรวจด้วย validator ว่า validation returns ยังปิดผนึก ค่าใช้จ่ายเป็นศูนย์ registry และ cost ledger ตรงกับ report และไม่มีการอ้าง `E2` หรือ edge

## 4. ผลลัพธ์

การดึงข้อมูลสำเร็จครบ `16/16` payload ด้วย `16` attempts ไม่มี retry และไม่มีค่าใช้จ่าย ได้ corporate-action rows รวม `772` แถว มี empty array `6` payload ซึ่งถือว่าเป็นคำตอบว่า provider ไม่รายงานเหตุการณ์ แต่ยังไม่ใช่หลักฐานว่าประวัติสมบูรณ์

การเทียบช่วงก่อนปี 2016 ตรงกัน `11/16` คู่ และต่างกัน `5/16` คู่ คู่ที่ต่างอยู่ใน dividend ของ EWJ, IEF, TIP, VTI และ VWO ส่วน split ตรงกันทุกคู่ตามกติกาที่ล็อกไว้ มี event ที่จับคู่ตรงกัน `80` รายการ Alpha Vantage มีรายการที่จับคู่ไม่ได้ `227` รายการ และ Yahoo มีรายการที่จับคู่ไม่ได้ `228` รายการ

ผลนี้ตอบคำถามว่า “ไม่ตรงกันทุกคู่” จึงไม่ผ่านเกณฑ์ independent current-snapshot reconciliation แบบครบถ้วน และต้องคงสถานะ `scope_restricted_no_point_in_time_revision_archive`

## 5. อภิปรายผล ปัญหา และข้อจำกัด

ข้อเท็จจริงที่ยืนยันได้คือ key และ endpoint ฟรีใช้งานกับ ETF ทั้งแปดตัวได้จริง schema ของ nonempty rows ตรงตามที่ล็อก และการเก็บข้อมูลไม่หลุดเพดาน request แต่ความต่างของ event มีขนาดมากพอที่จะห้ามสรุปว่า provider ใดถูกโดยอัตโนมัติ

เราไม่ได้เปิด validation prices หรือ returns จึงไม่รู้ว่าความต่างเหล่านี้กระทบผลตอบแทนมากเพียงใด การไม่คำนวณผลกระทบเป็น guardrail ที่ตั้งใจไว้ เพื่อป้องกันการเลือก provider หลังเห็นว่าค่าใดทำให้กลยุทธ์ดูดีขึ้น นอกจากนี้ Alpha Vantage เป็น snapshot ณ วันที่ดึง ไม่ได้เก็บทุก revision ที่เคยเผยแพร่ในอดีต

สิ่งที่ห้ามสรุปจากการทดลองนี้:

- ห้ามสรุปว่า Alpha Vantage หรือ Yahoo ถูกต้องกว่าเพราะให้ผลการลงทุนดีกว่า
- ห้ามสรุปว่า point-in-time corporate-action blocker ถูกแก้แล้ว
- ห้ามเปิด validation หรือเลื่อน L-1 เป็น `E2`
- ห้ามอ้างว่าพบ edge หรือระบบพร้อมใช้งานจริง

## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

ข้อสรุป: `จำกัดขอบเขต` Alpha Vantage เป็นแหล่งตรวจ corporate actions อิสระที่ใช้งานได้ฟรี แต่ข้อมูลก่อนปี 2016 ไม่ตรงกับ Yahoo ครบทุกคู่ และไม่มี revision archive จึงยังไม่พอสำหรับหลักฐานระดับ E2

แนวทางพัฒนาต่อ:

1. คง validation seal และห้ามนำความต่างไปปรับราคาในรอบนี้
2. สร้าง gate ใหม่ที่เจ้าของอนุมัติ เพื่อค้นหาแหล่ง point-in-time corporate actions ที่มี revision provenance หรือกำหนดอย่างเป็นทางการว่า L-1 หยุดที่ E1
3. หากได้แหล่งใหม่ ให้ล็อกกติกาเทียบก่อนอ่านข้อมูล และห้ามเลือกค่าตามผลตอบแทน
4. ทำ Webull Thailand capability probe เป็นงานแยกแบบ read-only โดยไม่ preview หรือส่งคำสั่งซื้อขาย
