from __future__ import annotations

import unittest

from lib.sizing import futures_minimum_capital, inverse_volatility_scenario, round_up_to_hundred


class SizingTests(unittest.TestCase):
    def test_round_up_to_hundred(self) -> None:
        self.assertEqual(40_600, round_up_to_hundred(40_583.01))
        self.assertEqual(40_600, round_up_to_hundred(40_600.00))

    def test_inverse_volatility_exposes_weight_cap_failure(self) -> None:
        sleeves = [
            {"sleeve": f"risk_{index}", "ticker": f"R{index}", "base_annual_volatility": 0.20}
            for index in range(11)
        ] + [{"sleeve": "cash", "ticker": "C", "base_annual_volatility": 0.03}]
        result = inverse_volatility_scenario(
            sleeves,
            breadth=12,
            capital_usd=1000,
            gross_exposure=0.90,
            minimum_trade_usd=5.0,
            maximum_weight=0.25,
            maximum_standalone_risk_contribution=0.16,
        )
        self.assertFalse(result["gates"]["maximum_notional_weight_met"])
        self.assertLessEqual(result["maximum_observed_standalone_risk_contribution"], 0.16)

    def test_futures_formula_uses_single_market_concentration(self) -> None:
        contracts = [
            {
                "contract_id": "example",
                "root_symbol": "X",
                "initial_margin_usd": 1000,
                "stress_method": "locked_100bp_risk_unit",
                "risk_value_per_100bp_usd": 4000,
            }
        ] + [
            {
                "contract_id": f"small_{index}",
                "root_symbol": f"S{index}",
                "initial_margin_usd": 100,
                "stress_method": "locked_100bp_risk_unit",
                "risk_value_per_100bp_usd": 100,
            }
            for index in range(3)
        ]
        result = futures_minimum_capital(contracts, breadth=4, per_market_stress_limit=0.10)
        self.assertEqual("single_market_concentration", result["binding_component"])
        self.assertEqual(40_000, result["minimum_capital_usd"])


if __name__ == "__main__":
    unittest.main()
