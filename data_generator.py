from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import RIVER_ORDER
from risk_engine import calculate_formula_risk, classify_risk
from rivers import RIVERS


def generate_demo_history(days: int = 90, points_per_day: int = 4, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    start = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=days)
    periods = days * points_per_day
    step_hours = 24 / points_per_day

    for river_name in RIVER_ORDER:
        river = RIVERS[river_name]
        river_shift = (RIVER_ORDER.index(river_name) + 1) * 0.35

        for index in range(periods):
            timestamp = start + timedelta(hours=index * step_hours)
            seasonal = np.sin((index / periods) * np.pi * 2 + river_shift)
            storm_wave = max(0, np.sin(index / 13 + river_shift)) ** 3
            event_spike = 1.0 if rng.random() < 0.045 else 0.0

            precipitation = max(
                0,
                rng.normal(5 + 16 * storm_wave + 38 * event_spike, 5),
            )
            temperature = rng.normal(10 + 12 * seasonal, 4)
            humidity = np.clip(rng.normal(58 + precipitation * 0.45 + 14 * storm_wave, 10), 20, 100)
            snow_water = np.clip(rng.normal(240 + 180 * max(0, -seasonal) + 90 * event_spike, 80), 0, 850)
            water_flow = np.clip(
                rng.normal(
                    34 + precipitation * 1.35 + snow_water * 0.045 + 30 * event_spike,
                    12,
                ),
                2,
                260,
            )
            seismic_activity = np.clip(
                rng.normal(1.3 + water_flow / 55 + event_spike * 2.7, 0.8),
                0,
                10,
            )

            values = {
                "timestamp": timestamp,
                "precipitation": round(float(precipitation), 1),
                "temperature": round(float(temperature), 1),
                "humidity": round(float(humidity), 1),
                "water_flow": round(float(water_flow), 1),
                "snow_water": round(float(snow_water), 1),
                "seismic_activity": round(float(seismic_activity), 2),
            }
            risk_percent = calculate_formula_risk(values, river)
            risk_level = classify_risk(risk_percent)["name"]

            rows.append(
                {
                    "river": river_name,
                    **values,
                    "risk_percent": risk_percent,
                    "risk_level": risk_level,
                    "model_type": "Demo formula",
                }
            )

    return pd.DataFrame(rows)


def generate_risk_surface(
    river_name: str,
    base_values: dict,
    precipitation_steps: int = 34,
    flow_steps: int = 34,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    river = RIVERS[river_name]
    precipitation_values = np.linspace(0, 100, precipitation_steps)
    flow_values = np.linspace(0, 260, flow_steps)
    x_grid, y_grid = np.meshgrid(precipitation_values, flow_values)
    z_grid = np.zeros_like(x_grid)

    for i in range(y_grid.shape[0]):
        for j in range(x_grid.shape[1]):
            values = {
                **base_values,
                "precipitation": float(x_grid[i, j]),
                "water_flow": float(y_grid[i, j]),
            }
            z_grid[i, j] = calculate_formula_risk(values, river)

    return x_grid, y_grid, z_grid
