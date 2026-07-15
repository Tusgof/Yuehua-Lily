from __future__ import annotations

import unittest

from scripts.run_l_0_webull_th_read_only_capability_probe import (
    ProbeBlocked,
    candidate_rows,
    field_inventory,
    install_request_guard,
    public_instrument_summary,
)


class FakeRequest:
    def __init__(self, path: str) -> None:
        self.path = path

    def get_action_name(self) -> str:
        return self.path


class FakeClient:
    def get_response(self, request: FakeRequest) -> str:
        return request.path


class L0WebullThailandReadOnlyProbeTests(unittest.TestCase):
    def test_order_request_is_blocked_before_client_call(self) -> None:
        client = FakeClient()
        attempted = install_request_guard(client)
        with self.assertRaisesRegex(ProbeBlocked, "request_path_outside_locked_allowlist"):
            client.get_response(FakeRequest("/openapi/orders/place"))
        self.assertEqual([], attempted)

    def test_fifth_read_only_request_is_blocked(self) -> None:
        client = FakeClient()
        install_request_guard(client)
        for path in (
            "/openapi/account/list",
            "/openapi/assets/balance",
            "/openapi/assets/positions",
            "/openapi/instrument/stock/list",
        ):
            client.get_response(FakeRequest(path))
        with self.assertRaisesRegex(ProbeBlocked, "read_only_request_cap_exceeded"):
            client.get_response(FakeRequest("/openapi/account/list"))

    def test_candidate_summary_preserves_locked_order(self) -> None:
        symbols = ["VTI", "VGK"]
        payload = {"data": [{"symbol": "VGK", "status": "OC", "fractionable": True, "instrument_type": "ETF"}, {"symbol": "VTI", "status": "OC", "fractionable": True, "instrument_type": "ETF"}]}
        rows = candidate_rows(payload, symbols)
        summary = public_instrument_summary(rows, symbols)
        self.assertEqual(symbols, [row["symbol"] for row in summary])

    def test_field_inventory_never_contains_values(self) -> None:
        payload = {"account_id": "private-value", "nested": [{"cash_balance": "123.45"}]}
        self.assertEqual(["account_id", "cash_balance", "nested"], field_inventory(payload))


if __name__ == "__main__":
    unittest.main()
