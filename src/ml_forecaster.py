"""
ml_forecaster.py – Climate-aware crop yield & CSI forecast using Random Forest.

Simulates how +1.5°C / +2°C warming scenarios shift Cold-chain Suitability
Index (CSI) thresholds and expected crop yields for key commodities.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Optional sklearn import – graceful fallback for environments without it
# ---------------------------------------------------------------------------
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COMMODITIES = ["Tomato", "Mango", "Potato", "Onion", "Banana"]

WARMING_SCENARIOS = {
    "baseline":  0.0,
    "+1.5°C":    1.5,
    "+2.0°C":    2.0,
    "+3.0°C":    3.0,
}

# Approximate baseline yield sensitivity (% yield loss per +1°C above optimum)
YIELD_SENSITIVITY = {
    "Tomato":  3.2,
    "Mango":   2.1,
    "Potato":  4.5,
    "Onion":   2.8,
    "Banana":  1.9,
}

# Optimal storage temp (°C) for each commodity
OPTIMAL_TEMP = {
    "Tomato":  13.0,
    "Mango":   10.0,
    "Potato":   4.0,
    "Onion":    0.5,
    "Banana":  13.5,
}

RANDOM_STATE = 42
N_SAMPLES    = 300   # synthetic training samples per commodity


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ClimateFeatures:
    """Feature vector for one observation."""
    ambient_temp: float          # °C
    humidity_pct: float          # 0–100
    transit_hours: float         # hours in transit
    precooling_done: bool        # whether pre-cooling was applied
    warming_delta: float = 0.0   # °C of climate warming above baseline


@dataclass
class ForecastResult:
    commodity: str
    scenario: str
    predicted_csi: float
    predicted_yield_loss_pct: float
    spoilage_risk: str           # LOW / MEDIUM / HIGH / CRITICAL
    recommendation: str


@dataclass
class ModelReport:
    commodity: str
    mae: float
    r2: float
    feature_importance: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Synthetic dataset generator
# ---------------------------------------------------------------------------
def _generate_training_data(commodity: str, n: int = N_SAMPLES):
    """Generate a synthetic dataset for the given commodity."""
    rng = np.random.default_rng(RANDOM_STATE)
    opt_t = OPTIMAL_TEMP[commodity]

    ambient   = rng.uniform(10, 45, n)
    humidity  = rng.uniform(40, 95, n)
    transit   = rng.uniform(2, 72, n)
    precool   = rng.integers(0, 2, n).astype(float)
    warming   = rng.choice([0.0, 1.5, 2.0, 3.0], n)

    effective_temp = ambient + warming

    # CSI: 0–100, higher = better cold-chain conditions
    csi = (
        100
        - 2.5  * np.maximum(0, effective_temp - opt_t)
        - 0.3  * (humidity - 65) ** 2 / 100
        - 0.8  * transit
        + 10.0 * precool
        + rng.normal(0, 2, n)
    )
    csi = np.clip(csi, 0, 100)

    X = np.column_stack([ambient, humidity, transit, precool, warming])
    return X, csi


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------
def train_models() -> Tuple[Dict, List[ModelReport]]:
    """Train one RF model per commodity; return models dict and reports."""
    if not _HAS_SKLEARN:
        return {}, []

    models, reports = {}, []
    for commodity in COMMODITIES:
        X, y = _generate_training_data(commodity)
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_STATE
        )
        rf = RandomForestRegressor(n_estimators=80, random_state=RANDOM_STATE)
        rf.fit(X_tr, y_tr)
        preds = rf.predict(X_te)

        feat_names = ["ambient_temp", "humidity_pct", "transit_hours",
                      "precooling_done", "warming_delta"]
        importance = dict(zip(feat_names, rf.feature_importances_.tolist()))

        reports.append(ModelReport(
            commodity=commodity,
            mae=round(float(mean_absolute_error(y_te, preds)), 3),
            r2=round(float(r2_score(y_te, preds)), 3),
            feature_importance=importance,
        ))
        models[commodity] = rf

    return models, reports


# ---------------------------------------------------------------------------
# Forecast helper
# ---------------------------------------------------------------------------
def _spoilage_label(csi: float) -> Tuple[str, str]:
    if csi >= 75:
        return "LOW",      "Maintain current routing. No intervention needed."
    elif csi >= 50:
        return "MEDIUM",   "Consider pre-cooling and expedited transit."
    elif csi >= 25:
        return "HIGH",     "Reroute to nearer hub. Prioritise offloading."
    else:
        return "CRITICAL", "Immediate offload recommended. Spoilage imminent."


def run_scenario_forecast(
    models: Dict,
    commodity: str,
    features: ClimateFeatures,
) -> List[ForecastResult]:
    """Run forecast for all warming scenarios given a commodity + features."""
    results = []
    sens = YIELD_SENSITIVITY.get(commodity, 2.5)

    for scenario_name, delta in WARMING_SCENARIOS.items():
        feat_vec = np.array([[
            features.ambient_temp,
            features.humidity_pct,
            features.transit_hours,
            float(features.precooling_done),
            delta,
        ]])

        if _HAS_SKLEARN and commodity in models:
            csi = float(models[commodity].predict(feat_vec)[0])
        else:
            # Fallback: rule-based CSI
            opt_t = OPTIMAL_TEMP.get(commodity, 10.0)
            eff   = features.ambient_temp + delta
            csi   = max(0.0, 100 - 2.5 * max(0, eff - opt_t)
                        - 0.8 * features.transit_hours
                        + (10.0 if features.precooling_done else 0.0))

        csi = round(min(100.0, max(0.0, csi)), 2)
        yield_loss = round(sens * delta, 2)
        risk, rec = _spoilage_label(csi)

        results.append(ForecastResult(
            commodity=commodity,
            scenario=scenario_name,
            predicted_csi=csi,
            predicted_yield_loss_pct=yield_loss,
            spoilage_risk=risk,
            recommendation=rec,
        ))
    return results


# ---------------------------------------------------------------------------
# Convenience: bulk forecast across all commodities
# ---------------------------------------------------------------------------
def bulk_forecast(models: Dict, features: ClimateFeatures) -> Dict[str, List[ForecastResult]]:
    return {c: run_scenario_forecast(models, c, features) for c in COMMODITIES}
