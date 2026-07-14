from __future__ import annotations

import math
from typing import Any


def round_up_to_hundred(value: float) -> int:
    """Round a positive capital requirement up to the next USD 100."""
    return int(math.ceil(value / 100.0) * 100)


def inverse_volatility_scenario(
    sleeves: list[dict[str, Any]],
    *,
    breadth: int,
    capital_usd: int,
    gross_exposure: float,
    minimum_trade_usd: float,
    maximum_weight: float,
    maximum_standalone_risk_contribution: float,
) -> dict[str, Any]:
    selected = sleeves[:breadth]
    inverse_volatility = [1.0 / float(item["base_annual_volatility"]) for item in selected]
    normalizer = sum(inverse_volatility)
    rows: list[dict[str, Any]] = []
    risk_units: list[float] = []
    for item, inverse in zip(selected, inverse_volatility, strict=True):
        weight = gross_exposure * inverse / normalizer
        risk_units.append(weight * float(item["base_annual_volatility"]))
        rows.append(
            {
                "sleeve": item["sleeve"],
                "ticker": item["ticker"],
                "weight": round(weight, 8),
                "target_notional_usd": round(capital_usd * weight, 2),
            }
        )
    total_risk_units = sum(risk_units)
    for row, risk_unit in zip(rows, risk_units, strict=True):
        row["standalone_risk_contribution"] = round(risk_unit / total_risk_units, 8)

    maximum_observed_weight = max(row["weight"] for row in rows)
    maximum_observed_risk = max(row["standalone_risk_contribution"] for row in rows)
    minimum_observed_trade = min(row["target_notional_usd"] for row in rows)
    gates = {
        "breadth_at_least_8": breadth >= 8,
        "cash_buffer_at_least_10_percent": 1.0 - gross_exposure >= 0.10 - 1e-12,
        "gross_exposure_at_most_90_percent": gross_exposure <= 0.90,
        "minimum_trade_met": minimum_observed_trade >= minimum_trade_usd,
        "maximum_notional_weight_met": maximum_observed_weight <= maximum_weight,
        "maximum_standalone_risk_contribution_met": (
            maximum_observed_risk <= maximum_standalone_risk_contribution
        ),
        "no_leverage": gross_exposure <= 1.0,
    }
    return {
        "breadth": breadth,
        "capital_usd": capital_usd,
        "economic_classification": "feasible" if all(gates.values()) else "infeasible",
        "gates": gates,
        "gross_exposure": gross_exposure,
        "cash_fraction": round(1.0 - gross_exposure, 8),
        "maximum_observed_weight": round(maximum_observed_weight, 8),
        "maximum_observed_standalone_risk_contribution": round(maximum_observed_risk, 8),
        "minimum_observed_trade_usd": round(minimum_observed_trade, 2),
        "allocations": rows,
    }


def contract_stress_loss(contract: dict[str, Any]) -> float:
    if contract["stress_method"] == "price_fraction":
        return (
            float(contract["reference_price"])
            * float(contract["contract_multiplier"])
            * float(contract["stress_move_fraction"])
        )
    if contract["stress_method"] == "locked_100bp_risk_unit":
        return float(contract["risk_value_per_100bp_usd"])
    raise ValueError(f"unsupported stress method: {contract['stress_method']}")


def futures_minimum_capital(
    contracts: list[dict[str, Any]],
    *,
    breadth: int,
    per_market_stress_limit: float,
) -> dict[str, Any]:
    selected = contracts[:breadth]
    rows: list[dict[str, Any]] = []
    for contract in selected:
        stress_loss = contract_stress_loss(contract)
        rows.append(
            {
                "contract_id": contract["contract_id"],
                "root_symbol": contract["root_symbol"],
                "initial_margin_usd": round(float(contract["initial_margin_usd"]), 6),
                "stress_loss_usd": round(stress_loss, 6),
            }
        )

    initial_margin_sum = sum(row["initial_margin_usd"] for row in rows)
    aggregate_stress_loss = sum(row["stress_loss_usd"] for row in rows)
    maximum_single_stress = max(row["stress_loss_usd"] for row in rows)
    components = {
        "initial_margin_occupancy": initial_margin_sum / 0.40,
        "stressed_margin_occupancy": (initial_margin_sum * 1.50) / 0.60,
        "aggregate_stress_loss": aggregate_stress_loss / 0.30,
        "single_market_concentration": maximum_single_stress / per_market_stress_limit,
    }
    binding_component = max(components, key=components.get)
    return {
        "breadth": breadth,
        "classification": "minimum_capital_only",
        "minimum_capital_usd": round_up_to_hundred(components[binding_component]),
        "binding_component": binding_component,
        "initial_margin_sum_usd": round(initial_margin_sum, 6),
        "stressed_margin_sum_usd": round(initial_margin_sum * 1.50, 6),
        "aggregate_stress_loss_usd": round(aggregate_stress_loss, 6),
        "maximum_single_market_stress_loss_usd": round(maximum_single_stress, 6),
        "per_market_stress_limit": per_market_stress_limit,
        "formula_components_usd": {key: round(value, 6) for key, value in components.items()},
        "contracts": rows,
    }
