"""
monte_carlo_risk.py – Stochastic Monte Carlo Spoilage Simulation & Value-at-Risk (VaR) Engine.

Models perishable cargo financial exposure under uncertain micro-climate thermal excursions:
1. Vectorized Monte Carlo simulation (1,000+ stochastic temperature paths)
2. Heatwave shock injection and Arrhenius Q10 shelf-life degradation
3. Financial Value-at-Risk (VaR 95% / 99%) and Conditional Value-at-Risk (CVaR / Expected Shortfall)
4. Optimal pre-cooling buffer recommendations for quantitative commodities risk desks
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from iot_simulator import COMMODITY_SPECS


@dataclass
class MonteCarloConfig:
    """Configuration parameters for a commodity corridor Monte Carlo simulation."""
    commodity: str
    cargo_value_usd: float
    transit_hours: float
    ambient_mean_c: float = 8.0
    ambient_volatility_c: float = 2.5
    heatwave_prob: float = 0.08
    n_simulations: int = 1000
    seed: Optional[int] = 42


@dataclass
class RiskSimulationResult:
    """Aggregated probabilistic spoilage and Value-at-Risk metrics."""
    commodity: str
    n_simulations: int
    spoilage_probability_pct: float
    expected_loss_usd: float
    var_95_usd: float
    var_99_usd: float
    cvar_95_usd: float
    recommended_precool_hours: float
    risk_tier: str
    simulated_losses_usd: List[float]
    simulated_peak_temps_c: List[float]


def _classify_risk_tier(spoilage_prob_pct: float) -> str:
    if spoilage_prob_pct >= 35.0:
        return "CRITICAL"
    if spoilage_prob_pct >= 18.0:
        return "HIGH"
    if spoilage_prob_pct >= 5.0:
        return "MODERATE"
    return "LOW"


def simulate_spoilage_var(config: MonteCarloConfig) -> RiskSimulationResult:
    """
    Runs a vectorized Monte Carlo simulation of micro-climate temperature drift
    to quantify perishable cargo Value-at-Risk (VaR) and Expected Shortfall.
    """
    specs = COMMODITY_SPECS.get(config.commodity, COMMODITY_SPECS["Hass Avocados"])
    _, ideal_t_max = specs["ideal_temp_c"]
    q10 = specs["q10_temp_sensitivity"]
    base_shelf_life = specs["base_shelf_life_hours"]

    rng = np.random.default_rng(config.seed)
    n = max(10, int(config.n_simulations))

    # Stochastic thermal trajectories + rare reefer drift / heatwave shocks
    base_temps = rng.normal(config.ambient_mean_c, config.ambient_volatility_c, size=n)
    shock_mask = rng.random(size=n) < np.clip(config.heatwave_prob, 0.0, 1.0)
    shock_magnitudes = rng.uniform(5.0, 11.0, size=n)
    peak_temps = base_temps + (shock_mask * shock_magnitudes)

    # Vectorized Arrhenius Q10 multiplier
    temp_excess = np.maximum(0.0, peak_temps - ideal_t_max)
    multipliers = np.power(q10, temp_excess / 10.0)
    effective_shelf_life = base_shelf_life / np.maximum(multipliers, 1.0)

    # Financial loss per scenario (95% loss when spoiled in transit, gradual decay otherwise)
    spoiled_mask = effective_shelf_life < config.transit_hours
    gradual_decay_ratio = np.clip((config.transit_hours / effective_shelf_life) * 0.5, 0.0, 0.90)
    losses = np.where(
        spoiled_mask,
        config.cargo_value_usd * 0.95,
        config.cargo_value_usd * gradual_decay_ratio,
    )

    spoilage_prob_pct = round(float(np.mean(spoiled_mask) * 100.0), 2)
    expected_loss = round(float(np.mean(losses)), 2)
    var_95 = round(float(np.percentile(losses, 95)), 2)
    var_99 = round(float(np.percentile(losses, 99)), 2)

    tail_losses = losses[losses >= var_95]
    cvar_95 = round(float(np.mean(tail_losses)) if len(tail_losses) > 0 else var_95, 2)

    risk_tier = _classify_risk_tier(spoilage_prob_pct)
    precool_hours = round(min(12.0, max(1.0, (spoilage_prob_pct / 10.0) * 1.5 + 1.0)), 1)

    return RiskSimulationResult(
        commodity=config.commodity,
        n_simulations=n,
        spoilage_probability_pct=spoilage_prob_pct,
        expected_loss_usd=expected_loss,
        var_95_usd=var_95,
        var_99_usd=var_99,
        cvar_95_usd=cvar_95,
        recommended_precool_hours=precool_hours,
        risk_tier=risk_tier,
        simulated_losses_usd=[round(float(x), 2) for x in losses],
        simulated_peak_temps_c=[round(float(x), 2) for x in peak_temps],
    )


def simulate_fleet_var(
    fleet_df: pd.DataFrame, n_simulations: int = 500, seed: int = 42
) -> Dict[str, Any]:
    """
    Aggregates portfolio-level Expected Loss and Value-at-Risk across an entire reefer fleet.
    """
    if fleet_df.empty:
        return {
            "containers_simulated": 0,
            "portfolio_value_usd": 0.0,
            "portfolio_expected_loss_usd": 0.0,
            "portfolio_var_95_usd": 0.0,
            "portfolio_cvar_95_usd": 0.0,
            "highest_risk_container": None,
            "container_results": [],
        }

    container_results: List[Dict[str, Any]] = []
    portfolio_losses = np.zeros(max(10, int(n_simulations)), dtype=float)

    for idx, (_, row) in enumerate(fleet_df.iterrows()):
        cfg = MonteCarloConfig(
            commodity=str(row.get("commodity", "Hass Avocados")),
            cargo_value_usd=float(row.get("cargo_value_usd", 25000.0)),
            transit_hours=float(row.get("hours_to_primary_market", 36.0)),
            ambient_mean_c=float(row.get("internal_temp_celsius", 8.0)),
            n_simulations=n_simulations,
            seed=(seed + idx) if seed is not None else None,
        )
        res = simulate_spoilage_var(cfg)
        portfolio_losses += np.array(res.simulated_losses_usd)
        container_results.append({
            "container_id": str(row.get("container_id", f"CONT-{idx}")),
            "commodity": res.commodity,
            "spoilage_prob_pct": res.spoilage_probability_pct,
            "expected_loss_usd": res.expected_loss_usd,
            "var_95_usd": res.var_95_usd,
            "risk_tier": res.risk_tier,
            "precool_hours": res.recommended_precool_hours,
        })

    port_var_95 = round(float(np.percentile(portfolio_losses, 95)), 2)
    tail = portfolio_losses[portfolio_losses >= port_var_95]
    port_cvar_95 = round(float(np.mean(tail)) if len(tail) > 0 else port_var_95, 2)
    highest = max(container_results, key=lambda r: r["var_95_usd"])

    return {
        "containers_simulated": len(container_results),
        "portfolio_value_usd": round(float(fleet_df["cargo_value_usd"].sum()), 2) if "cargo_value_usd" in fleet_df.columns else 0.0,
        "portfolio_expected_loss_usd": round(float(np.mean(portfolio_losses)), 2),
        "portfolio_var_95_usd": port_var_95,
        "portfolio_cvar_95_usd": port_cvar_95,
        "highest_risk_container": highest["container_id"],
        "container_results": container_results,
    }
