from __future__ import annotations
from pathlib import Path
from lib.provenance import file_sha256
from scripts import validate_l_3_corrected_rerun_report_v3 as core
ROOT=Path(__file__).resolve().parents[1]
core.GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v4.json'
core._IMPLEMENTATION_PATHS={"gate":"experiments/l_3_corrected_rerun_activation_v4.json","runner":"scripts/run_l_3_corrected_rerun_v3.py","report_validator":"scripts/validate_l_3_corrected_rerun_report_v4.py","report_schema":"schemas/l_3_corrected_rerun_report_v3.schema.json","side_effect_library":"lib/l3_corrected_rerun_v3.py"}
validate=core.validate
main=core.main
if __name__=='__main__':raise SystemExit(main())
