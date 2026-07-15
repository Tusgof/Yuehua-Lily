# รายงาน B4.4: ตรวจ corporate actions ด้วย Alpha Vantage

- Order: `B4.4`
- Hypothesis: `L-1`
- Evidence tier: `E1`
- Decision: `scope_restricted_no_point_in_time_revision_archive`
- Producing commit: `e6355a746d05433b76427ed4878f3e2fb46b8e43`
- Report digest: `838f8d674e32e9d53b5eb8af25dd5ed04cfa63124724ebb175608d9a3bfec854`
- Validation return status: `sealed_not_accessed`
- ค่าใช้จ่าย: `USD 0`

## ผลโดยสรุป

ดึงข้อมูลตาม matrix ที่ล็อกไว้สำเร็จครบ `16/16` payload ด้วย `16` network attempts ไม่มี retry และไม่เสียเงิน ข้อมูลรวมมี `772` corporate-action rows โดยมี empty array ที่สะอาด `6` payload และไม่พบ canonical row ซ้ำ

เมื่อนำเฉพาะ event ระหว่าง `2006-02-03` ถึง `2015-12-31` ไปเทียบกับ Yahoo เดิมแบบวันที่และเลขทศนิยมตรงกันทุกหลัก พบว่าตรงกันครบเพียง `11/16` คู่ อีก `5/16` คู่มีความต่าง รวม event ที่จับคู่ตรงกัน `80` รายการ ฝั่ง Alpha Vantage เกินมา `227` รายการ และฝั่ง Yahoo เกินมา `228` รายการ รายงาน tracked นี้ไม่เปิดเผย event amounts หรือรายการรายแถว

| Symbol | Alpha dividend rows ทั้งหมด | Alpha split rows ทั้งหมด | Dividend ตรงก่อนปี 2016 | Split ตรงก่อนปี 2016 |
|:--|--:|--:|:--:|:--:|
| DBC | 9 | 0 | ใช่ | ใช่ |
| EWJ | 45 | 1 | ไม่ | ใช่ |
| GLD | 0 | 0 | ใช่ | ใช่ |
| IEF | 288 | 0 | ไม่ | ใช่ |
| TIP | 200 | 0 | ไม่ | ใช่ |
| VGK | 63 | 0 | ใช่ | ใช่ |
| VTI | 102 | 1 | ไม่ | ใช่ |
| VWO | 62 | 1 | ไม่ | ใช่ |

## ความหมายและข้อจำกัด

Alpha Vantage ใช้งานได้จริงในฐานะแหล่งตรวจอิสระแบบ current snapshot แต่ไม่ใช่ revision archive ที่บอกว่าในอดีตผู้ใช้เห็นค่าใด ณ เวลานั้น ความต่างห้าคู่จึงห้ามแก้ด้วยการเลือกค่าจาก provider ที่ทำให้ผลการลงทุนดีขึ้น และยังห้ามนำไปปรับราคาหรือคำนวณผลตอบแทนในรอบนี้

ช่วง validation ตั้งแต่ `2016-01-04` ถึง `2026-06-30` ยังปิดผนึก ข้อมูลหลังปี 2015 ที่อ่านมีเพียง corporate-action metadata ที่แยกจากราคาและผลตอบแทน ไม่มีการโหลดหรือคำนวณ validation price, return, signal, position, regime, benchmark หรือ PnL

## งานถัดไปที่ปลอดภัย

คง validation seal ไว้ แล้วสร้าง gate ใหม่ที่เจ้าของอนุมัติ เพื่อเลือกอย่างใดอย่างหนึ่งระหว่างหาแหล่ง point-in-time corporate actions เพิ่ม หรือยอมรับอย่างเป็นทางการว่า L-1 คงได้เพียง `E1 scope_restricted` ห้ามใช้ผล B4.4 ปลด validation หรือเลื่อนเป็น `E2` ส่วน Webull Thailand capability probe ให้ทำเป็นงานแยกแบบ read-only
