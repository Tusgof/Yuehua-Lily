# Lily L-1 Validation Funding Capacity

## สถานะ

- Order: `B4.2`
- Evidence: `E1`
- Edge claim: `none`
- Decision: `statistical_capacity_funded_unlock_blocked`
- Producing commit: `b4d7ee8b542b612f6bfb8b9003c8d1e79f919a51`
- Machine digest: `1675714fffb45ab644c78bf2cc3a89ce4038966c27cdb835d1a2d3e1ffb64264`

## คำถาม

ช่วง validation ที่ยังปิดผนึกมีจำนวน session เพียงพอสำหรับ MinTRL_validate ทั้งสาม null หรือไม่ เมื่อใช้ dependence จากช่วง falsification ตามกติกาที่ล็อกไว้ โดยไม่อ่านราคาและผลตอบแทน validation

## ปฏิทินที่ใช้

ช่วง `2016-01-04` ถึง `2026-06-30` มี 2,637 NYSE sessions การนับใช้กฎวันหยุดและวันปิดพิเศษเท่านั้น ไม่มี market observations และวันปิดเร็วถือเป็น session

## ผล capacity ตามกติกาที่ล็อก

Time-effective observations: 3,140.19

Cross-sectional effective dimensions: 6.4888

Projected joint independent-bet equivalents: 20,376.00

Binding MinTRL_validate: 8,673

Capacity ratio: 2.35 เท่า

Null ทั้งหมด funded: `true`

## Sensitivity ที่ต้องระวัง

เมื่อใช้ planning assumptions เดิมแทน dependence ที่วัดได้ จะได้ joint independent-bet equivalents เพียง 7,603.64 และ binding null funded = `false` ผล funded จึงพึ่งพา dependence ที่สืบทอดจากช่วงก่อนปี 2016 อย่างมีนัยสำคัญ

## Databento

Key ใช้ metadata ได้และไม่มีการซื้อข้อมูล แต่ coverage หุ้นสหรัฐที่เกี่ยวข้องเริ่มปี 2018 หรือช้ากว่า และไม่มี dedicated corporate-actions schema จึงใช้แทนข้อมูลทั้ง validation window หรือแก้ point-in-time corporate actions ไม่ได้

## เหตุที่ยังเปิด validation ไม่ได้

- Independent point-in-time corporate-action provenance remains unavailable for the full L-1 path.
- VGK and VWO remain outside the locked daily corporate-action reconciliation tolerance.
- Databento metadata does not cover 2016-01-04 through 2018-04-30 and exposes no dedicated corporate-actions history for this purpose.
- A separate owner-approved unlock gate has not been created.

## ขั้นต่อไปที่ปลอดภัย

Keep validation returns sealed. Resolve or formally source-restrict point-in-time corporate actions, confirm the Databento credit is backed by real payment before any paid request, and create a separate owner-approved validation unlock gate only if the remaining data blockers are cleared.
