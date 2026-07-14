# Lily L-1 Data-Quality Remediation

## สถานะ

- Order: `B4.1`
- Evidence: `E1`
- Edge claim: `none`
- Decision: `scope_restricted_public_remediation_complete`
- Producing commit: `4c8b0caee522d4acbf70aa1abe86d5023f79cde0`
- Machine digest: `16cd526af634876135fc35b3b93a272442b9237f1d08f73b448db31e074966bf`

## Corporate actions

ผล: `partially_resolved_within_provider`

ผ่าน tolerance รายวัน: VTI, EWJ, IEF, TIP, GLD, DBC

ไม่ผ่าน tolerance รายวัน: VGK, VWO

## Historical expense ratios

ผล: `partially_resolved_decision_bounded`

เอกสารทางการ: 57 รายการ

ผลตอบแทนสุทธิแบบ cash-remediated หลังคืน expense drag ทั้งหมดอย่างมองโลกดีที่สุด: -2.6674% ต่อปี

## Cash benchmark

ผล: `resolved_E1`

Net CAGR เดิม: -2.9756%

Net CAGR หลังใช้ Treasury cash: -2.8936%

เปลี่ยนแปลง: 0.0820% ต่อปี

## Webull Thailand

ผล: `public_capability_partially_resolved_account_scope_restricted`

Manual fractional โดยทั่วไป: `verified_public`

Green diamond ราย ticker: `requires_account_observation`

Fractional OpenAPI: `not_documented`

## ข้อจำกัด

- Corporate-action point-in-time revision provenance is unavailable and VGK/VWO exceed the locked daily reconciliation tolerance.
- Six of eight historical fee series have at least one uncovered interval under the locked 18-month rule; DBC lacks a pre-2007 filing even though operations began in 2006.
- Webull Thailand green-diamond eligibility for the candidate tickers requires an account/app observation.
- Webull Thailand OpenAPI documentation does not explicitly support fractional quantity or notional orders.
- No adversarial review or E2 promotion was attempted.

## ขั้นต่อไปที่ปลอดภัย

Keep validation sealed. In the owner's Webull Thailand mobile app, record the green-diamond status for the ten current-capital candidates without placing or previewing an order, and request written broker confirmation of fractional OpenAPI support before any implementation study. Independent point-in-time corporate-action data remains an E2 prerequisite, not a reason to open validation now.
