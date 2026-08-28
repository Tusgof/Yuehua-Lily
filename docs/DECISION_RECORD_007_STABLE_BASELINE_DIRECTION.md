# Decision Record 007: CORE-1 stable baseline direction

## การตัดสินใจของเจ้าของ

เจ้าของอนุมัติให้เปิด workstream `CORE-1P` เพื่อ preregister การทดสอบพัฒนาแบบ long/cash ที่ลด turnover โดยเป็น E0 และ `edge_claim: none` เท่านั้น คำถามที่ล็อกใน machine artifact คือ: `Can a low-turnover long/cash trend-following system produce positive net return and positive net Sharpe after realistic costs on globally diversified ETFs?`

CORE-1P ไม่อนุญาตให้ทำ backtest หรืออ่าน/parse ผลตอบแทน, ข้อมูลชุดข้อมูลหรือ container, validation, provider/network, credential, broker/account, paid action, paper trade หรือเงินจริง การดำเนินการถัดไปที่ปลอดภัยมีเพียง `CORE-1E` หลัง Inspector รับรองและผู้ใช้ integrate เท่านั้น

## เหตุผลและขอบเขต

L-1 มีหลักฐาน E1 อยู่แล้ว ไม่ใช่โครงการว่างเปล่า: ช่วง 2007-02-05 ถึง 2015-12-31 ให้ gross annual arithmetic return +3.6674479855% และ gross Sharpe 0.4934695406 แต่ net annual arithmetic return -2.7427845464%, net Sharpe -0.3681760727, maximum drawdown -29.6729404515% และมี executed asset trades 3,224 รายการ

พอร์ตเดิมเป็น continuous signed q/vol จึงมีปัญหาต้นทุนและ turnover. CORE-1 ไม่แทนที่ bytes ที่ล็อกไว้หรือประวัติ L-1 แต่ทดสอบ implementation long/cash ที่เรียบง่ายกว่า เพื่อลด turnover.

ล็อก candidate พัฒนาเพียงสามตัว: `CORE1_DC60`, `CORE1_DC120`, และ `CORE1_SMA200` บน universe ตามลำดับ `VTI, VGK, EWJ, VWO, IEF, TIP, GLD, DBC` ใช้ sleeve คงที่ 1/8 NAV, ไม่มี short, leverage, inverse-vol, target-vol, regime filter, ensemble หรือ parameter variation. สัญญาณและ timing, band 2 percentage points, costs, stress test, benchmark, A-H gates, selection และ stop rule ถูกล็อกครบใน `experiments/core_1_stable_baseline_preregistration_v1.json`.

## วิทยาศาสตร์ที่ล็อกไว้

- `CORE1_DC60` นับทิศทางของ daily total-return ใน 60 complete sessions ก่อนหน้า และ long เมื่อผลรวม direction มากกว่า 0; ศูนย์นับเป็น 0. `CORE1_DC120` ใช้กติกาเดียวกันกับ 120 complete sessions.
- `CORE1_SMA200` long เมื่อ current corporate-action-aware total-return close สูงกว่า simple moving average ของ current และ 199 complete sessions ก่อนหน้าอย่างเคร่งครัด; มิฉะนั้นเป็น cash. หาก observation ที่จำเป็นขาด ให้ asset นั้นเป็น cash จนกว่าจะครบ.
- แต่ละ asset มี fixed sleeve budget และ long target เท่ากับ 0.125 ของ NAV; inactive asset target เท่ากับ 0.0 และ sleeve ที่ไม่ active อยู่ใน cash. ไม่ renormalize active sleeves, gross exposure อยู่ระหว่าง 0 ถึง 1, และ cash รวมเท่ากับ 1-gross.
- ตัดสินใจรายสัปดาห์หลัง official close ของ actual last NYSE session ในแต่ละ ISO week แล้ว execute ที่ official close ของ actual NYSE session ถัดไป; PnL เริ่มหลัง execution close และห้าม same-close execution. ซื้อขายเมื่อส่วนต่างระหว่าง target กับ drifted pre-trade weight อย่างน้อย 0.02 ของ NAV มิฉะนั้นคง drifted weight.
- ต้นทุนหลักคือ Webull Thailand commission รวม VAT 0.00107 ของ one-way traded notional, spread/slippage 25 bps ต่อเที่ยว และ sell surcharge 1 bp. ต้นทุน execution ทั้งสามรายการบันทึกเฉพาะ executed notional changes; ETF expense ratios ที่ล็อกไว้บันทึกทุกวันบน held notional แยกจาก execution costs. Stress 2x เพิ่มเฉพาะ commission, spread/slippage และ sell surcharge ไม่เพิ่ม ETF expenses.
- cash yield เป็นศูนย์จนกว่าจะมี cash series ที่อนุมัติและ timestamp-valid; funding FX ไม่รวมใน recurring PnL และต้องรายงานแยกภายหลัง.
- warmup/QA คือ 2006-02-03 ถึง 2007-02-02 โดยไม่มี performance claim. Development/falsification ที่เปิดคือ 2007-02-05 ถึง 2015-12-31. Final validation 2016-01-04 ถึง 2026-06-30 ยังคง sealed และห้ามอ่าน, scan, hash, count หรือ infer.
- search inventory มีเพียง 3 trials. การวิเคราะห์ภายหลังต้องใช้ PSR, HAC/Newey-West, autocorrelation-adjusted Sharpe variance, calendar count, trades, turnover, independent-bet equivalents และ DSR จากทั้งสาม trials.

เป็น US-listed fractional implementation proxies ที่ครอบคลุมประเทศและสินทรัพย์ทั่วโลกเท่านั้น จึงห้ามอ้างความทั่วไปของ opportunity set แบบ point-in-time. Cash yield เป็นศูนย์จนกว่าจะมี series ที่อนุมัติและ timestamp-valid; funding FX ไม่รวม PnL ประจำและต้องรายงานแยกภายหลัง.

## การพักงานและขีดจำกัด claim

ระหว่าง CORE-1 active ให้พักการ execute enhancement ของ L-2, L-3 และ L-4 แบบ prospective โดยคงสถานะ evidence tier, locked artifacts และประวัติทั้งหมดไว้. Commit `e76a2ec` ของ B8.9-D บน milestone branch ที่ยังไม่ merge เป็น non-authoritative และห้าม merge หรือแก้ในคำสั่งนี้.

CORE-1P เป็น E0 planning/governance เท่านั้น ไม่มีผลเชิงประจักษ์ ไม่มีการเปิด validation และไม่มี edge claim. Inspector ยังคงเป็นผู้เขียน `research_log/` แต่เพียงผู้เดียว.

## กฎหยุด

หากไม่มี candidate ใดผ่าน A-H ทุกข้อหลัง CORE-1E ให้หยุด CORE-1, เก็บ validation ไว้ sealed และต้องมี owner/Inspector decision เพื่อ reformulate หรือปิด ETF trend family. ห้ามเพิ่ม candidate ที่สี่, parameter rescue, เปลี่ยน universe/date/cost หรือซ้อน remediation. หากมีผู้ผ่าน ให้ล็อก candidate เดียวในคำสั่งอนาคตแยกต่างหากก่อนขอเปิด final validation.

## GOV-1 เฉพาะคำสั่งนี้

GOV-1 ยังมี Inspector เป็น `gpt-5.6-sol / high` แบบ read-only และ Worker ปกติเป็น `gpt-5.6-luna / max` แบบ workspace-write. CORE-1P นี้ดำเนินการโดย Worker ปกติของ GOV-1 คือ `gpt-5.6-luna / max` และไม่เปลี่ยนบทบาทในอนาคต.
