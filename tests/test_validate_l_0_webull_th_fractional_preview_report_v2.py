from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_0_webull_th_fractional_preview_report_v2 import (
    CLAIM_LIMITS,
    QUANTITY_GRID,
    validate_report,
)


class L0WebullThailandFractionalPreviewReportV2Tests(unittest.TestCase):
    def test_complete_synthetic_matrix_passes(self) -> None:
        payload = _payload(8)
        result = _validate_temporary(payload)
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_eight_authentication_and_eight_preview_requests_pass(self) -> None:
        payload = _payload(8, mode="uat_preview")
        payload["request_attestation"].update(
            {
                "authentication_paths": ["/openapi/auth/token/create"] + ["/openapi/auth/token/check"] * 7,
                "authentication_request_count": 8,
                "auth_create_request_count": 1,
                "auth_check_request_count": 7,
                "preview_request_count": 8,
                "synthetic_preview_row_count": 0,
                "total_broker_request_count": 16,
            }
        )
        result = _validate_temporary(payload)
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_second_create_or_eighth_check_is_blocked(self) -> None:
        for paths in (
            ["/openapi/auth/token/create"] * 2,
            ["/openapi/auth/token/create"] + ["/openapi/auth/token/check"] * 8,
        ):
            with self.subTest(paths=paths):
                payload = _payload(0, mode="uat_preview")
                payload["request_attestation"].update(
                    {
                        "authentication_paths": paths,
                        "authentication_request_count": len(paths),
                        "auth_create_request_count": paths.count("/openapi/auth/token/create"),
                        "auth_check_request_count": paths.count("/openapi/auth/token/check"),
                        "total_broker_request_count": len(paths),
                    }
                )
                result = _validate_temporary(payload)
                self.assertIn("request_cap_exceeded", result["blockers"])

    def test_polling_or_validation_tampering_is_blocked(self) -> None:
        payload = _payload(8)
        payload["authentication_polling"]["duration_seconds"] = 300
        payload["validation_return_seal"]["returns_opened"] = True
        result = _validate_temporary(payload)
        self.assertIn("field_mismatch:authentication_polling", result["blockers"])
        self.assertIn("validation_seal_false_field_mismatch:returns_opened", result["blockers"])


def _payload(row_count: int, *, mode: str = "synthetic_fixture") -> dict[str, object]:
    rows = [
        {
            "quantity": quantity,
            "outcome": "accepted",
            "response_class": "success",
            "documented_error_code": None,
            "response_sha256": "a" * 64,
        }
        for quantity in QUANTITY_GRID[:row_count]
    ]
    return {
        "schema_version": "lily_l0_webull_th_fractional_preview_report_v2",
        "order_id": "B4.12",
        "hypothesis_id": "L-0",
        "linked_hypothesis_id": "L-1",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "report_mode": mode,
        "produced_at": "2026-07-20T00:00:00Z",
        "producing_git_commit": "b" * 40,
        "environment": "webull_thailand_uat",
        "host": "th-api.uat.webullbroker.com",
        "contract_sha256": "c" * 64,
        "activation_gate_id": "l_0_webull_th_fractional_preview_activation_v2" if mode == "uat_preview" else None,
        "authentication_polling": {
            "duration_seconds": 30,
            "interval_seconds": 5,
            "maximum_auth_create_requests": 1,
            "maximum_auth_check_requests": 7,
        },
        "rows": rows,
        "summary": {
            "tested_quantity_count": row_count,
            "accepted_count": row_count,
            "rejected_count": 0,
            "smallest_accepted_tested_quantity": QUANTITY_GRID[row_count - 1] if row_count else None,
            "largest_rejected_tested_quantity": None,
            "exact_broker_minimum_known": False,
        },
        "decision": "all_tested_quantities_accepted" if row_count == 8 else "blocked_before_preview",
        "blockers": [] if row_count == 8 else ["authentication_not_normal_within_30_seconds"],
        "request_attestation": {
            "authentication_paths": [],
            "authentication_request_count": 0,
            "auth_create_request_count": 0,
            "auth_check_request_count": 0,
            "preview_path": "/openapi/trade/order/preview",
            "preview_request_count": 0,
            "synthetic_preview_row_count": row_count if mode == "synthetic_fixture" else 0,
            "total_broker_request_count": 0,
            "forbidden_request_count": 0,
            "production_request_count": 0,
            "order_mutation_or_query_count": 0,
            "orders_sent": 0,
            "raw_response_persisted": False,
            "private_material_persisted": False,
            "paid_spend_usd": 0,
        },
        "validation_return_seal": {
            "status": "sealed_not_accessed",
            "prices_opened": False,
            "adjusted_prices_opened": False,
            "returns_opened": False,
            "signals_opened": False,
            "positions_opened": False,
            "regimes_opened": False,
            "benchmarks_opened": False,
            "pnl_opened": False,
        },
        "claim_limits": CLAIM_LIMITS,
    }


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_report(path)


if __name__ == "__main__":
    unittest.main()
