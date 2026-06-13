from __future__ import annotations

import numpy as np
import pandas as pd

from config import MODEL_PATH, ensure_project_dirs
from risk_engine import calculate_formula_risk
from rivers import RIVERS


FEATURE_COLUMNS = [
    "precipitation",
    "temperature",
    "humidity",
    "water_flow",
    "snow_water",
    "seismic_activity",
    "river_coefficient",
    "slope_index",
    "precipitation_flow_index",
    "snowmelt_index",
]


def build_feature_row(values: dict, river: dict) -> dict:
    precipitation = float(values["precipitation"])
    temperature = float(values["temperature"])
    snow_water = float(values["snow_water"])
    water_flow = float(values["water_flow"])

    return {
        "precipitation": precipitation,
        "temperature": temperature,
        "humidity": float(values["humidity"]),
        "water_flow": water_flow,
        "snow_water": snow_water,
        "seismic_activity": float(values["seismic_activity"]),
        "river_coefficient": float(river["risk_coefficient"]),
        "slope_index": float(river["slope_index"]),
        "precipitation_flow_index": precipitation * water_flow / 100,
        "snowmelt_index": max(0, temperature) * snow_water / 100,
    }


def generate_training_frame(samples: int = 2600, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    river_names = list(RIVERS)

    for _ in range(samples):
        river_name = rng.choice(river_names)
        river = RIVERS[river_name]
        event_like = rng.random() < 0.28

        values = {
            "precipitation": np.clip(rng.normal(45 if event_like else 10, 18), 0, 100),
            "temperature": np.clip(rng.normal(14 if event_like else 7, 8), -20, 40),
            "humidity": np.clip(rng.normal(82 if event_like else 55, 15), 0, 100),
            "water_flow": np.clip(rng.normal(135 if event_like else 42, 45), 0, 280),
            "snow_water": np.clip(rng.normal(390 if event_like else 180, 160), 0, 900),
            "seismic_activity": np.clip(rng.normal(5.2 if event_like else 1.7, 1.9), 0, 10),
        }
        risk = calculate_formula_risk(values, river)
        noisy_threshold = 53 + rng.normal(0, 8)
        label = int(risk >= noisy_threshold)

        rows.append(
            {
                **build_feature_row(values, river),
                "label": label,
            }
        )

    return pd.DataFrame(rows)


def train_model(force: bool = False) -> tuple[object | None, str]:
    ensure_project_dirs()
    if MODEL_PATH.exists() and not force:
        return load_model()

    try:
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        return None, f"ML-модуль недоступен: {exc}"

    frame = generate_training_frame()
    x = frame[FEATURE_COLUMNS]
    y = frame["label"]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.22,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=160,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(x_train, y_train)
    score = model.score(x_test, y_test)

    joblib.dump(
        {
            "model": model,
            "feature_columns": FEATURE_COLUMNS,
            "score": float(score),
        },
        MODEL_PATH,
    )
    return model, f"ML-модель обучена. Accuracy на тестовой выборке: {score:.2f}"


def load_model() -> tuple[object | None, str]:
    try:
        import joblib
    except ImportError as exc:
        return None, f"ML-модуль недоступен: {exc}"

    if not MODEL_PATH.exists():
        return None, "ML-модель еще не обучена"

    payload = joblib.load(MODEL_PATH)
    score = payload.get("score")
    suffix = f" Accuracy: {score:.2f}" if score is not None else ""
    return payload["model"], f"ML-модель загружена.{suffix}"


def predict_ml_risk(values: dict, river: dict) -> tuple[float | None, str]:
    model, message = train_model(force=False)
    if model is None:
        return None, message

    feature_row = build_feature_row(values, river)
    frame = pd.DataFrame([feature_row], columns=FEATURE_COLUMNS)
    probability = float(model.predict_proba(frame)[0][1])
    return round(probability * 100, 1), message


def feature_importance_frame() -> pd.DataFrame:
    model, _ = train_model(force=False)
    if model is None or not hasattr(model, "feature_importances_"):
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
