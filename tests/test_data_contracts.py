from __future__ import annotations

import copy
import unittest

from lib.data_contracts import validate_dataset_registry, validate_provider_fixture
from lib.io import load_json
from scripts.validate_data_layer import DEFAULT_REGISTRY, PROJECT_ROOT, validate_data_layer


FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "data"


class DataContractTests(unittest.TestCase):
    def test_current_B1_data_layer_passes(self) -> None:
        result = validate_data_layer()
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertFalse(result["network_used"])
        self.assertFalse(result["paid_data_used"])

    def test_registry_rejects_network_or_paid_acquisition_in_B1(self) -> None:
        registry = copy.deepcopy(load_json(DEFAULT_REGISTRY))
        registry["bootstrap_network_used"] = True
        registry["bootstrap_paid_data_spend_usd"] = 1
        blockers = validate_dataset_registry(registry)
        self.assertIn("B1_bootstrap_network_used_must_be_false", blockers)
        self.assertIn("B1_bootstrap_paid_data_spend_must_be_zero", blockers)

    def test_inactive_instrument_requires_delisting_date(self) -> None:
        fixture = copy.deepcopy(load_json(FIXTURE_ROOT / "provider_instrument_master.json"))
        fixture["records"][1]["delisting_date"] = None
        blockers = validate_provider_fixture("instrument_master", fixture)
        self.assertIn("instrument_master:1:inactive_instrument_missing_delisting_date", blockers)

    def test_continuous_series_cannot_be_PnL_source(self) -> None:
        fixture = copy.deepcopy(load_json(FIXTURE_ROOT / "provider_continuous_futures.json"))
        fixture["pnl_source"] = "adjusted_continuous_prices"
        blockers = validate_provider_fixture("continuous_futures", fixture)
        self.assertIn("continuous_futures:pnl_source_must_be_individual_contracts", blockers)

    def test_roll_event_requires_contract_change(self) -> None:
        fixture = copy.deepcopy(load_json(FIXTURE_ROOT / "provider_continuous_futures.json"))
        fixture["records"][1]["active_contract_id"] = fixture["records"][0]["active_contract_id"]
        blockers = validate_provider_fixture("continuous_futures", fixture)
        self.assertIn("continuous_futures:1:roll_event_without_contract_change", blockers)


if __name__ == "__main__":
    unittest.main()
