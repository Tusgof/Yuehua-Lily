"""Provider-neutral data contracts for Lily's research boundary."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any

from lib.timestamps import parse_aware_timestamp


FIXTURE_SCHEMAS = {
    "daily_bars": "lily_provider_daily_bars_v1",
    "instrument_master": "lily_provider_instrument_master_v1",
    "universe_membership": "lily_provider_universe_membership_v1",
    "futures_contracts": "lily_provider_futures_contracts_v1",
    "continuous_futures": "lily_provider_continuous_futures_v1",
}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def validate_dataset_registry(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["dataset_registry_must_be_object"]
    blockers: list[str] = []
    if payload.get("schema_version") != "lily_dataset_registry_v1":
        blockers.append("invalid_dataset_registry_schema_version")
    if payload.get("storage_root_variable") != "LILY_DATA_ROOT":
        blockers.append("storage_root_must_be_LILY_DATA_ROOT")
    if payload.get("bootstrap_network_used") is not False:
        blockers.append("B1_bootstrap_network_used_must_be_false")
    if payload.get("bootstrap_paid_data_spend_usd") != 0:
        blockers.append("B1_bootstrap_paid_data_spend_must_be_zero")
    boundaries = payload.get("boundaries")
    if not isinstance(boundaries, dict) or set(boundaries) != {"raw", "normalized", "derived"}:
        blockers.append("data_boundaries_must_be_raw_normalized_derived")
    else:
        expected_mutability = {
            "raw": "immutable",
            "normalized": "new_version_only",
            "derived": "rebuildable_new_version_only",
        }
        for layer, expected in expected_mutability.items():
            if not isinstance(boundaries[layer], dict) or boundaries[layer].get("mutability") != expected:
                blockers.append(f"invalid_boundary_mutability:{layer}")
    hash_policies = payload.get("hash_policies")
    required_policies = {"hard_to_reproduce", "redownloadable_free_daily", "derived"}
    if not isinstance(hash_policies, dict) or set(hash_policies) != required_policies:
        blockers.append("hash_policies_must_cover_all_data_classes")

    datasets = payload.get("datasets")
    if not isinstance(datasets, list):
        blockers.append("datasets_must_be_list")
        return blockers
    seen: set[str] = set()
    for index, dataset in enumerate(datasets):
        if not isinstance(dataset, dict):
            blockers.append(f"dataset_{index}_must_be_object")
            continue
        dataset_id = str(dataset.get("dataset_id", f"index_{index}"))
        if dataset_id in seen:
            blockers.append(f"duplicate_dataset_id:{dataset_id}")
        seen.add(dataset_id)
        required = {
            "dataset_id",
            "hypothesis_ids",
            "layer",
            "status",
            "storage_reference",
            "provider",
            "provider_schema_version",
            "license",
            "timezone",
            "coverage",
            "point_in_time_status",
            "survivorship_status",
            "hash_policy",
            "hashes",
            "parent_dataset_ids",
            "acquisition",
            "limitations",
        }
        blockers.extend(
            f"{dataset_id}:missing_required_field:{field}"
            for field in sorted(required - set(dataset))
        )
        if dataset.get("layer") not in {"raw", "normalized", "derived"}:
            blockers.append(f"{dataset_id}:invalid_layer")
        for field in ("provider", "provider_schema_version", "license", "timezone"):
            if not isinstance(dataset.get(field), str) or not dataset[field].strip():
                blockers.append(f"{dataset_id}:{field}_must_be_non_empty_string")
        if dataset.get("point_in_time_status") not in {"verified", "limited", "not_applicable"}:
            blockers.append(f"{dataset_id}:invalid_point_in_time_status")
        if dataset.get("survivorship_status") not in {"verified", "limited", "not_applicable"}:
            blockers.append(f"{dataset_id}:invalid_survivorship_status")
        if not _safe_storage_reference(dataset.get("storage_reference")):
            blockers.append(f"{dataset_id}:unsafe_storage_reference")
        policy = dataset.get("hash_policy")
        hashes = dataset.get("hashes")
        if policy not in required_policies or not isinstance(hashes, dict):
            blockers.append(f"{dataset_id}:invalid_hash_policy")
        else:
            required_hashes = set(hash_policies.get(policy, [])) if isinstance(hash_policies, dict) else set()
            for field in sorted(required_hashes - {"parent_dataset_ids", "producing_git_commit"}):
                if not HASH_PATTERN.fullmatch(str(hashes.get(field, ""))):
                    blockers.append(f"{dataset_id}:missing_or_invalid_hash:{field}")
            if policy == "derived" and not re.fullmatch(r"[0-9a-f]{40}", str(hashes.get("producing_git_commit", ""))):
                blockers.append(f"{dataset_id}:missing_or_invalid_producing_git_commit")
        if not isinstance(dataset.get("parent_dataset_ids"), list):
            blockers.append(f"{dataset_id}:parent_dataset_ids_must_be_list")
        elif dataset.get("layer") in {"normalized", "derived"} and not dataset["parent_dataset_ids"]:
            blockers.append(f"{dataset_id}:non_raw_layer_requires_parent_dataset")
        if not isinstance(dataset.get("hypothesis_ids"), list):
            blockers.append(f"{dataset_id}:hypothesis_ids_must_be_list")
        if not isinstance(dataset.get("limitations"), list):
            blockers.append(f"{dataset_id}:limitations_must_be_list")
        acquisition = dataset.get("acquisition")
        if not isinstance(acquisition, dict):
            blockers.append(f"{dataset_id}:acquisition_must_be_object")
        else:
            acquisition_required = {
                "network_used", "paid_amount_usd", "acquired_at", "key_provenance_label", "request_specification"
            }
            blockers.extend(
                f"{dataset_id}:acquisition_missing:{field}"
                for field in sorted(acquisition_required - set(acquisition))
            )
            paid = acquisition.get("paid_amount_usd")
            if not isinstance(paid, (int, float)) or paid < 0:
                blockers.append(f"{dataset_id}:acquisition_paid_amount_invalid")
            acquired_at = acquisition.get("acquired_at")
            if acquired_at is not None and not _aware_timestamp(acquired_at):
                blockers.append(f"{dataset_id}:acquisition_timestamp_invalid")
    return blockers


def validate_provider_fixture(kind: str, payload: Any) -> list[str]:
    if kind not in FIXTURE_SCHEMAS:
        return [f"unsupported_fixture_kind:{kind}"]
    if not isinstance(payload, dict):
        return [f"{kind}:fixture_must_be_object"]
    blockers = _validate_envelope(kind, payload)
    if kind == "daily_bars":
        blockers.extend(_validate_daily_bars(payload.get("records")))
    elif kind == "instrument_master":
        blockers.extend(_validate_instruments(payload.get("records")))
    elif kind == "universe_membership":
        blockers.extend(_validate_memberships(payload.get("records")))
    elif kind == "futures_contracts":
        blockers.extend(_validate_futures_contracts(payload.get("records")))
    else:
        blockers.extend(_validate_continuous_futures(payload))
    return blockers


def _validate_envelope(kind: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("schema_version") != FIXTURE_SCHEMAS[kind]:
        blockers.append(f"{kind}:invalid_schema_version")
    if payload.get("boundary_kind") != kind:
        blockers.append(f"{kind}:boundary_kind_mismatch")
    if payload.get("provider") != "synthetic":
        blockers.append(f"{kind}:fixture_provider_must_be_synthetic")
    if payload.get("fixture_only") is not True:
        blockers.append(f"{kind}:fixture_only_must_be_true")
    if payload.get("network_used") is not False or payload.get("paid_data_used") is not False:
        blockers.append(f"{kind}:fixture_must_use_zero_network_and_paid_data")
    if not _aware_timestamp(payload.get("acquired_at")):
        blockers.append(f"{kind}:acquired_at_must_be_timezone_aware")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        blockers.append(f"{kind}:records_must_be_non_empty_list")
    return blockers


def _validate_daily_bars(records: Any) -> list[str]:
    blockers: list[str] = []
    if not isinstance(records, list):
        return blockers
    required = {
        "instrument_id", "session_date", "available_at", "open", "high", "low", "close",
        "adjusted_close", "volume", "currency", "adjustment_basis", "provider_revision", "is_backfilled",
    }
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blockers.append(f"daily_bars:{index}:record_must_be_object")
            continue
        blockers.extend(f"daily_bars:{index}:missing:{field}" for field in sorted(required - set(record)))
        prices = [record.get(field) for field in ("open", "high", "low", "close")]
        if not all(isinstance(value, (int, float)) and value > 0 for value in prices):
            blockers.append(f"daily_bars:{index}:prices_must_be_positive")
        elif record["high"] < max(record["open"], record["close"], record["low"]):
            blockers.append(f"daily_bars:{index}:high_is_inconsistent")
        elif record["low"] > min(record["open"], record["close"], record["high"]):
            blockers.append(f"daily_bars:{index}:low_is_inconsistent")
        if not _iso_date(record.get("session_date")) or not _aware_timestamp(record.get("available_at")):
            blockers.append(f"daily_bars:{index}:invalid_date_or_availability")
    return blockers


def _validate_instruments(records: Any) -> list[str]:
    blockers: list[str] = []
    if not isinstance(records, list):
        return blockers
    required = {
        "instrument_id", "provider_symbol", "instrument_type", "name", "exchange", "trading_currency",
        "domicile", "exposure_region", "inception_date", "first_available_date", "delisting_date", "active",
        "distribution_treatment", "provider_revision",
    }
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blockers.append(f"instrument_master:{index}:record_must_be_object")
            continue
        blockers.extend(f"instrument_master:{index}:missing:{field}" for field in sorted(required - set(record)))
        inception = _date_value(record.get("inception_date"))
        first_available = _date_value(record.get("first_available_date"))
        delisting = _date_value(record.get("delisting_date"), allow_none=True)
        if inception is None or first_available is None or first_available < inception:
            blockers.append(f"instrument_master:{index}:pre_inception_history_not_flagged")
        if record.get("delisting_date") is not None and delisting is None:
            blockers.append(f"instrument_master:{index}:invalid_delisting_date")
        if record.get("active") is True and delisting is not None:
            blockers.append(f"instrument_master:{index}:active_instrument_has_delisting_date")
        if record.get("active") is False and delisting is None:
            blockers.append(f"instrument_master:{index}:inactive_instrument_missing_delisting_date")
    return blockers


def _validate_memberships(records: Any) -> list[str]:
    blockers: list[str] = []
    if not isinstance(records, list):
        return blockers
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blockers.append(f"universe_membership:{index}:record_must_be_object")
            continue
        start = _date_value(record.get("effective_from"))
        end = _date_value(record.get("effective_to"), allow_none=True)
        if (
            start is None
            or (record.get("effective_to") is not None and end is None)
            or (end is not None and end < start)
        ):
            blockers.append(f"universe_membership:{index}:invalid_effective_range")
        known = record.get("known_at")
        if not _aware_timestamp(known):
            blockers.append(f"universe_membership:{index}:known_at_must_be_timezone_aware")
    return blockers


def _validate_futures_contracts(records: Any) -> list[str]:
    blockers: list[str] = []
    if not isinstance(records, list):
        return blockers
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blockers.append(f"futures_contracts:{index}:record_must_be_object")
            continue
        first_trade = _date_value(record.get("first_trade_date"))
        last_trade = _date_value(record.get("last_trade_date"))
        first_notice = _date_value(record.get("first_notice_date"), allow_none=True)
        expiry = _date_value(record.get("expiry_date"))
        if first_trade is None or last_trade is None or expiry is None or not first_trade <= last_trade <= expiry:
            blockers.append(f"futures_contracts:{index}:invalid_contract_dates")
        if record.get("delivery_type") == "physical" and first_notice is None:
            blockers.append(f"futures_contracts:{index}:physical_contract_missing_first_notice")
        if record.get("first_notice_date") is not None and first_notice is None:
            blockers.append(f"futures_contracts:{index}:invalid_first_notice_date")
        for field in ("contract_multiplier", "tick_size", "tick_value"):
            if not isinstance(record.get(field), (int, float)) or record[field] <= 0:
                blockers.append(f"futures_contracts:{index}:{field}_must_be_positive")
    return blockers


def _validate_continuous_futures(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("signal_use_only") is not True:
        blockers.append("continuous_futures:must_be_signal_use_only")
    if payload.get("pnl_source") != "individual_contracts_and_roll_trades":
        blockers.append("continuous_futures:pnl_source_must_be_individual_contracts")
    if not isinstance(payload.get("roll_rule"), str) or not payload["roll_rule"].strip():
        blockers.append("continuous_futures:roll_rule_missing")
    if payload.get("adjustment_method") not in {
        "none", "additive_back_adjusted", "ratio_back_adjusted", "panama"
    }:
        blockers.append("continuous_futures:invalid_adjustment_method")
    records = payload.get("records")
    if not isinstance(records, list):
        return blockers
    previous_contract: str | None = None
    roll_count = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blockers.append(f"continuous_futures:{index}:record_must_be_object")
            continue
        if not _iso_date(record.get("session_date")) or not _aware_timestamp(record.get("available_at")):
            blockers.append(f"continuous_futures:{index}:invalid_date_or_availability")
        current = record.get("active_contract_id")
        rolled = record.get("roll_event") is True
        if rolled:
            roll_count += 1
            if previous_contract is None or current == previous_contract:
                blockers.append(f"continuous_futures:{index}:roll_event_without_contract_change")
        elif previous_contract is not None and current != previous_contract:
            blockers.append(f"continuous_futures:{index}:contract_changed_without_roll_event")
        previous_contract = str(current)
    if roll_count == 0:
        blockers.append("continuous_futures:fixture_must_include_roll_event")
    return blockers


def _safe_storage_reference(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if value.startswith("${LILY_DATA_ROOT}/"):
        value = value[len("${LILY_DATA_ROOT}/") :]
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parse_aware_timestamp(value)
    except (TypeError, ValueError):
        return False
    return True


def _iso_date(value: Any) -> bool:
    return _date_value(value) is not None


def _date_value(value: Any, *, allow_none: bool = False) -> date | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
