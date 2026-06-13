from __future__ import annotations


RIVERS = {
    "Баксан": {
        "name": "Баксан",
        "basin_area": 680.0,
        "slope_index": 0.22,
        "risk_coefficient": 1.15,
        "latitude": 43.68,
        "longitude": 43.54,
        "description": "Высокогорный бассейн с выраженной селевой активностью и развитой инфраструктурой в долине.",
        "accent": "#2563eb",
    },
    "Малка": {
        "name": "Малка",
        "basin_area": 850.0,
        "slope_index": 0.18,
        "risk_coefficient": 1.00,
        "latitude": 43.76,
        "longitude": 43.25,
        "description": "Крупный бассейн, где существенную роль играют снеготаяние и накопленная водность.",
        "accent": "#0891b2",
    },
    "Черек": {
        "name": "Черек",
        "basin_area": 560.0,
        "slope_index": 0.21,
        "risk_coefficient": 1.05,
        "latitude": 43.31,
        "longitude": 43.94,
        "description": "Горный бассейн с крутыми склонами, высокой расчлененностью рельефа и ливневыми триггерами.",
        "accent": "#7c3aed",
    },
    "Чегем": {
        "name": "Чегем",
        "basin_area": 420.0,
        "slope_index": 0.23,
        "risk_coefficient": 1.10,
        "latitude": 43.57,
        "longitude": 43.58,
        "description": "Селеопасный бассейн, где риск усиливается при сочетании ливней, снеготаяния и резкого роста расхода.",
        "accent": "#f97316",
    },
}


def get_river(name: str) -> dict:
    return RIVERS[name]


def river_records() -> list[dict]:
    records = []
    for index, river in enumerate(RIVERS.values(), start=1):
        records.append(
            {
                "id": index,
                "name": river["name"],
                "basin_area": river["basin_area"],
                "slope_index": river["slope_index"],
                "risk_coefficient": river["risk_coefficient"],
                "description": river["description"],
            }
        )
    return records
