from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.run_l_0_webull_th_fractional_preview_probe import (
    AUTH_PATHS,
    PREVIEW_PATH,
    QUANTITY_GRID,
    ProbeBlocked,
    build_preview_body,
    install_request_guard,
    run_probe,
)


class FakeRequest:
    def __init__(self, path: str, method: str = "POST") -> None:
        self.path = path
        self.method = method

    def get_action_name(self) -> str:
        return self.path

    def get_method(self) -> str:
        return self.method


class FakeClient:
    def __init__(self) -> None:
        self.call_count = 0

    def get_response(self, request: FakeRequest) -> str:
        self.call_count += 1
        return request.path


class L0WebullThailandFractionalPreviewRunnerTests(unittest.TestCase):
    def test_forbidden_order_endpoint_is_blocked_before_client_call(self) -> None:
        client = FakeClient()
        attempted = install_request_guard(client)
        with self.assertRaisesRegex(ProbeBlocked, "request_path_or_method_outside_locked_allowlist"):
            client.get_response(FakeRequest("/openapi/trade/order/place"))
        self.assertEqual(0, client.call_count)
        self.assertEqual([], attempted)

    def test_ninth_preview_is_blocked(self) -> None:
        client = FakeClient()
        attempted = install_request_guard(client)
        for _ in QUANTITY_GRID:
            client.get_response(FakeRequest(PREVIEW_PATH))
        with self.assertRaisesRegex(ProbeBlocked, "preview_request_cap_exceeded"):
            client.get_response(FakeRequest(PREVIEW_PATH))
        self.assertEqual(8, client.call_count)
        self.assertEqual(8, len(attempted))

    def test_fourth_authentication_request_is_blocked(self) -> None:
        client = FakeClient()
        attempted = install_request_guard(client)
        path = sorted(AUTH_PATHS)[0]
        for _ in range(3):
            client.get_response(FakeRequest(path, "GET"))
        with self.assertRaisesRegex(ProbeBlocked, "authentication_request_cap_exceeded"):
            client.get_response(FakeRequest(path, "GET"))
        self.assertEqual(3, client.call_count)
        self.assertEqual(3, len(attempted))

    def test_missing_activation_blocks_before_credentials_or_sdk(self) -> None:
        with (
            patch(
                "scripts.run_l_0_webull_th_fractional_preview_probe.load_execution_activation",
                side_effect=ProbeBlocked("execution_activation_missing"),
            ),
            patch("scripts.run_l_0_webull_th_fractional_preview_probe.os.environ.get") as environment_get,
        ):
            with self.assertRaisesRegex(ProbeBlocked, "execution_activation_missing"):
                run_probe()
        environment_get.assert_not_called()

    def test_request_body_follows_exact_grid_and_template(self) -> None:
        for index, quantity in enumerate(QUANTITY_GRID):
            with self.subTest(quantity=quantity):
                body = build_preview_body("private-account", quantity, index)
                self.assertEqual("private-account", body["account_id"])
                self.assertEqual(
                    {
                        "combo_type": "NORMAL",
                        "client_order_id": f"LILYB411PREVIEW{index + 1:02d}",
                        "instrument_type": "EQUITY",
                        "market": "US",
                        "symbol": "VTI",
                        "order_type": "MARKET",
                        "entrust_type": "QTY",
                        "support_trading_session": "CORE",
                        "time_in_force": "DAY",
                        "side": "BUY",
                        "quantity": quantity,
                    },
                    body["new_orders"][0],
                )


if __name__ == "__main__":
    unittest.main()
