"""B7.10 retains the B7.9 fixture-only runner; no execution is authorized."""
from __future__ import annotations
from lib.l3_corrected_rerun_v6 import MINTRL_FLOOR
from scripts.run_l_3_corrected_rerun_v5 import main
if __name__ == "__main__":
    raise SystemExit(main())
