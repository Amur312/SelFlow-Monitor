from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
ASSETS_DIR = BASE_DIR / "assets"
SCREENSHOTS_DIR = ASSETS_DIR / "screenshots"

DB_PATH = DATA_DIR / "selflow.db"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"

APP_TITLE = "SelFlow Monitor"
APP_SUBTITLE = "Прототип мониторинга риска селевых потоков"

RIVER_ORDER = ["Баксан", "Малка", "Черек", "Чегем"]

RISK_LEVELS = [
    {
        "name": "Низкий",
        "min": 0,
        "max": 30,
        "color": "#16a34a",
        "background": "#dcfce7",
        "recommendation": "Ситуация стабильная. Достаточно штатного наблюдения.",
    },
    {
        "name": "Повышенный",
        "min": 30,
        "max": 55,
        "color": "#ca8a04",
        "background": "#fef9c3",
        "recommendation": "Нужно усилить наблюдение и проверить последние измерения.",
    },
    {
        "name": "Высокий",
        "min": 55,
        "max": 75,
        "color": "#ea580c",
        "background": "#ffedd5",
        "recommendation": "Вероятны опасные процессы. Требуется готовность к оповещению.",
    },
    {
        "name": "Критический",
        "min": 75,
        "max": 100.01,
        "color": "#dc2626",
        "background": "#fee2e2",
        "recommendation": "Необходимо сформировать предупреждение и передать сигнал ответственным службам.",
    },
]

FACTOR_LABELS = {
    "precipitation": "Осадки",
    "temperature": "Температура",
    "humidity": "Влажность",
    "water_flow": "Расход воды",
    "snow_water": "Снег",
    "seismic_activity": "Сейсмика",
}

FACTOR_UNITS = {
    "precipitation": "мм/ч",
    "temperature": "°C",
    "humidity": "%",
    "water_flow": "м3/с",
    "snow_water": "мм",
    "seismic_activity": "усл. ед.",
}

FACTOR_WEIGHTS = {
    "precipitation": 0.25,
    "water_flow": 0.22,
    "humidity": 0.15,
    "snow_water": 0.15,
    "temperature": 0.08,
    "seismic_activity": 0.15,
}


def ensure_project_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
