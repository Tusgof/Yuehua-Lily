# Lily L-1 Baseline — Falsification Window

## สถานะหลักฐาน

- Hypothesis: `L-1`
- ระดับ: `E1`
- Edge claim: `none`
- ข้อสรุป: `not_falsified_but_not_validated`
- Producing commit: `c36d74980cda9094f26e8ed959a0b723328d1c62`
- Machine digest: `25985d2f649fa6a01d41b0ea76bde25624ada38f2ff5acc3ea2b35258e056439`

## ผลของ primary_60

ผลตอบแทนเรขาคณิตสุทธิต่อปี: -2.9756%

Sharpe สุทธิต่อปี: -0.3682

Maximum drawdown: -29.6729%

จำนวน joint independent-bet equivalents: 17338.87

## MinTRL และข้อมูลที่ปิดผนึก

ต้องการฝั่ง falsification: 3,850

ได้จริง: 17338.87

สถานะ validation: `sealed_not_accessed`

คำตัดสินการเปิดข้อมูล: `remain_sealed`

## ข้อจำกัดสำคัญ

- Yahoo public chart data is not a point-in-time revision archive and provider close is split-normalized.
- The fixed universe contains surviving proxies and does not represent the historical ETF opportunity set.
- Current expense-ratio proxies replace unavailable then-current fee histories.
- Cash return is set to zero because a matched point-in-time public cash series was not acquired.
- Market impact is not modeled.
- Webull Thailand fractional eligibility and OpenAPI capability remain unverified, so the current-capital branch was not run.
- No independent adversarial review has been performed; E2 promotion is forbidden.

## สิ่งที่ยังห้ามสรุป

ผลนี้ไม่ใช่หลักฐานระดับ E2 ไม่ยืนยันว่ามี edge ไม่อนุมัติ paper trading และไม่อนุมัติเงินจริง

## ขั้นต่อไปที่ปลอดภัย

Keep validation sealed. Resolve the corporate-action, historical fee, cash-series, and broker-eligibility gaps under a new bounded data-quality order; then independently verify whether the sealed window can fund all validation nulls before any unlock request.
