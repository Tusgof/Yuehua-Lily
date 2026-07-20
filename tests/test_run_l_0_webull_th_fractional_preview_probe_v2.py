from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.run_l_0_webull_th_fractional_preview_probe_v2 import (
    AUTH_CHECK_PATH,
    AUTH_CREATE_PATH,
    PREVIEW_PATH,
    QUANTITY_GRID,
    ProbeBlocked,
    build_api_client,
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
    def __init__(self, *_args, **kwargs) -> None:
        self.call_count = 0
        self.kwargs = kwargs

    def get_response(self, request: FakeRequest) -> str:
        self.call_count += 1
        return request.path


class L0WebullThailandFractionalPreviewRunnerV2Tests(unittest.TestCase):
    def test_polling_configuration_is_bounded_to_30_seconds(self) -> None:
        client = build_api_client(FakeClient, "key", "secret")
        self.assertEqual(30, client.kwargs["token_check_duration_seconds"])
        self.assertEqual(5, client.kwargs["token_check_interval_seconds"])
        self.assertFalse(client.kwargs["auto_retry"])

    def test_forbidden_path_and_method_are_blocked_before_client_call(self) -> None:
        client = FakeClient()
        attempted = install_request_guard(client)
        for request in (FakeRequest("/openapi/trade/order/place"), FakeRequest(PREVIEW_PATH, "GET")):
            with self.subTest(path=request.path, method=request.method):
                with self.assertRaises(ProbeBlocked):
                    client.get_response(request)
        self.assertEqual(0, client.call_count)
        self.assertEqual([], attempted)

    def test_second_create_and_eighth_check_are_blocked(self) -> None:
        client = FakeClient()
        attempted = install_request_guard(client)
        client.get_response(FakeRequest(AUTH_CREATE_PATH))
        with self.assertRaisesRegex(ProbeBlocked, "token_create_request_cap_exceeded"):
            client.get_response(FakeRequest(AUTH_CREATE_PATH))
        for _ in range(7):
            client.get_response(FakeRequest(AUTH_CHECK_PATH))
        with self.assertRaisesRegex(ProbeBlocked, "token_check_request_cap_exceeded"):
            client.get_response(FakeRequest(AUTH_CHECK_PATH))
        self.assertEqual(8, client.call_count)
        self.assertEqual(8, len(attempted))

    def test_ninth_preview_and_seventeenth_total_request_are_blocked(self) -> None:
        client = FakeClient()
        attempted = install_request_guard(client)
        client.get_response(FakeRequest(AUTH_CREATE_PATH))
        for _ in range(7):
            client.get_response(FakeRequest(AUTH_CHECK_PATH))
        for _ in QUANTITY_GRID:
            client.get_response(FakeRequest(PREVIEW_PATH))
        with self.assertRaisesRegex(ProbeBlocked, "preview_request_cap_exceeded"):
            client.get_response(FakeRequest(PREVIEW_PATH))
        self.assertEqual(16, client.call_count)
        self.assertEqual(16, len(attempted))

    def test_missing_activation_blocks_before_credentials(self) -> None:
        with (
            patch(
                "scripts.run_l_0_webull_th_fractional_preview_probe_v2.load_execution_activation",
                side_effect=ProbeBlocked("execution_activation_missing"),
            ),
            patch("scripts.run_l_0_webull_th_fractional_preview_probe_v2.os.environ.get") as environment_get,
        ):
            with self.assertRaisesRegex(ProbeBlocked, "execution_activation_missing"):
                run_probe()
        environment_get.assert_not_called()

    def test_request_body_keeps_the_locked_vti_grid(self) -> None:
        for index, quantity in enumerate(QUANTITY_GRID):
            body = build_preview_body("private-account", quantity, index)
            self.assertEqual("private-account", body["account_id"])
            self.assertEqual(f"LILYB412PREVIEW{index + 1:02d}", body["new_orders"][0]["client_order_id"])
            self.assertEqual(quantity, body["new_orders"][0]["quantity"])
            self.assertEqual("VTI", body["new_orders"][0]["symbol"])


if __name__ == "__main__":
    unittest.main()
