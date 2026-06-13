from __future__ import annotations

from config import FACTOR_LABELS, FACTOR_WEIGHTS, RISK_LEVELS


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return clamp((float(value) - low) / (high - low))


def temperature_score(temperature: float) -> float:
    temp = float(temperature)
    if temp <= -5:
        return 0.05
    if temp < 0:
        return 0.15
    if temp <= 22:
        return normalize(temp, 0, 22)
    return clamp(1.0 - ((temp - 22) / 28), 0.45, 1.0)


def factor_scores(values: dict) -> dict[str, float]:
    temp_factor = temperature_score(values["temperature"])
    snow_base = normalize(values["snow_water"], 0, 800)
    snowmelt_boost = 0.45 + 0.55 * temp_factor

    return {
        "precipitation": normalize(values["precipitation"], 0, 80),
        "water_flow": normalize(values["water_flow"], 5, 220),
        "humidity": normalize(values["humidity"], 35, 100),
        "snow_water": clamp(snow_base * snowmelt_boost),
        "temperature": temp_factor,
        "seismic_activity": normalize(values["seismic_activity"], 0, 10),
    }


def calculate_formula_risk(values: dict, river: dict) -> float:
    scores = factor_scores(values)
    raw = sum(scores[name] * FACTOR_WEIGHTS[name] for name in FACTOR_WEIGHTS)
    risk = raw * river["risk_coefficient"] * 100

    if values["precipitation"] >= 50 and values["water_flow"] >= 120:
        risk += 8
    if values["humidity"] >= 85 and values["precipitation"] >= 40:
        risk += 5
    if values["seismic_activity"] >= 7:
        risk += 6
    if values["snow_water"] >= 450 and values["temperature"] >= 8:
        risk += 5

    return round(clamp(risk, 0, 100), 1)


def classify_risk(risk_percent: float) -> dict:
    risk = float(risk_percent)
    for level in RISK_LEVELS:
        if level["min"] <= risk < level["max"]:
            return level
    return RISK_LEVELS[-1]


def factor_contributions(values: dict) -> list[dict]:
    scores = factor_scores(values)
    contributions = []
    for name, score in scores.items():
        contribution = score * FACTOR_WEIGHTS[name] * 100
        contributions.append(
            {
                "factor": FACTOR_LABELS[name],
                "score": round(score, 3),
                "weight": FACTOR_WEIGHTS[name],
                "contribution": round(contribution, 2),
            }
        )
    return sorted(contributions, key=lambda item: item["contribution"], reverse=True)


def build_recommendation(risk_percent: float) -> str:
    return classify_risk(risk_percent)["recommendation"]
