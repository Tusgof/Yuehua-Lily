"""Post-provenance constants for the B8.6R9/v11 bounded runtime."""
from __future__ import annotations

# This module is imported only after the committed bootstrap has verified this
# file, its v10 helper, and the opaque scanner against the producing commit.
from lib.l4_b86r8_contract_v10 import (  # noqa: F401
    BLOCKERS, CUTOFF, MAX_BYTES, SEAL, U8, artifact, atomic_write_all,
    canonical, claim_once, sha256,
)

GATE = "experiments/l_4_breadth_b86r9_provisioning_gate_v11.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r9_provisioning_activation_v11.json"
DATASET = "data/normalized/l1_yahoo_daily_v1.json"
EXPECTED_DATASET_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
MARKER = "reports/experiments/l_4_breadth_b86r9_provisioning_attempt_v11.json"
REPORT = "reports/experiments/l_4_breadth_b86r9_provisioning_report_v11.json"
MANIFEST = "experiments/provisioned/l_4_breadth_b86r9_falsification_manifest_v11.json"
PAYLOAD = "experiments/provisioned/l_4_breadth_b86r9_u8_session_dates_v11.json"
REPORT_SCHEMA = "lily_l4_b86r9_provisioning_report_v11"
