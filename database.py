from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import DB_PATH, ensure_project_dirs
from rivers import river_records


EVENTS = [
    ("2015-08-03", "19:15", 50, 95.0, "Средний", "Ливневые осадки", "Баксан"),
    ("2016-07-11", "14:40", 120, 380.0, "Очень мощный", "Ливень + снеготаяние", "Чегем"),
    ("2017-06-22", "21:05", 30, 48.0, "Малый", "Ливневые осадки", "Черек"),
    ("2018-08-15", "16:50", 60, 210.0, "Мощный", "Интенсивный ливень", "Баксан"),
    ("2019-05-19", "11:30", 90, 250.0, "Мощный", "Снеготаяние + дождь", "Малка"),
    ("2020-07-28", "19:05", 55, 95.0, "Средний", "Ливневые осадки", "Чегем"),
    ("2022-06-12", "15:40", 75, 160.0, "Мощный", "Прорыв ледникового озера", "Баксан"),
    ("2023-08-09", "17:25", 40, 70.0, "Средний", "Ливневые осадки", "Черек"),
]


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    ensure_project_dirs()
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rivers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                basin_area REAL NOT NULL,
                slope_index REAL NOT NULL,
                risk_coefficient REAL NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                river_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                precipitation REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                water_flow REAL NOT NULL,
                snow_water REAL NOT NULL,
                seismic_activity REAL NOT NULL,
                FOREIGN KEY (river_id) REFERENCES rivers(id)
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                measurement_id INTEGER NOT NULL,
                risk_percent REAL NOT NULL,
                risk_level TEXT NOT NULL,
                model_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (measurement_id) REFERENCES measurements(id)
            );

            CREATE TABLE IF NOT EXISTS mudflow_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                river_id INTEGER NOT NULL,
                event_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                duration_min INTEGER NOT NULL,
                volume_thousand_m3 REAL NOT NULL,
                power_level TEXT NOT NULL,
                trigger_factor TEXT NOT NULL,
                FOREIGN KEY (river_id) REFERENCES rivers(id)
            );
            """
        )
        seed_rivers(connection)
        seed_events(connection)


def seed_rivers(connection: sqlite3.Connection) -> None:
    for river in river_records():
        connection.execute(
            """
            INSERT INTO rivers (id, name, basin_area, slope_index, risk_coefficient, description)
            VALUES (:id, :name, :basin_area, :slope_index, :risk_coefficient, :description)
            ON CONFLICT(name) DO UPDATE SET
                basin_area = excluded.basin_area,
                slope_index = excluded.slope_index,
                risk_coefficient = excluded.risk_coefficient,
                description = excluded.description;
            """,
            river,
        )


def seed_events(connection: sqlite3.Connection) -> None:
    count = connection.execute("SELECT COUNT(*) FROM mudflow_events").fetchone()[0]
    if count:
        return

    river_ids = {
        row["name"]: row["id"]
        for row in connection.execute("SELECT id, name FROM rivers").fetchall()
    }
    rows = [
        (
            river_ids[river_name],
            event_date,
            start_time,
            duration,
            volume,
            power,
            trigger,
        )
        for event_date, start_time, duration, volume, power, trigger, river_name in EVENTS
    ]
    connection.executemany(
        """
        INSERT INTO mudflow_events (
            river_id, event_date, start_time, duration_min,
            volume_thousand_m3, power_level, trigger_factor
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )


def count_measurements() -> int:
    with connect() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM measurements").fetchone()[0])


def fetch_table_counts() -> pd.DataFrame:
    tables = ["rivers", "measurements", "predictions", "mudflow_events"]
    rows = []
    with connect() as connection:
        for table in tables:
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            rows.append({"table": table, "rows": int(count)})
    return pd.DataFrame(rows)


def fetch_schema() -> pd.DataFrame:
    tables = ["rivers", "measurements", "predictions", "mudflow_events"]
    rows = []
    with connect() as connection:
        for table in tables:
            for column in connection.execute(f"PRAGMA table_info({table})").fetchall():
                rows.append(
                    {
                        "table": table,
                        "column": column["name"],
                        "type": column["type"],
                        "required": "Да" if column["notnull"] else "Нет",
                        "primary_key": "Да" if column["pk"] else "Нет",
                    }
                )
    return pd.DataFrame(rows)


def fetch_rivers() -> pd.DataFrame:
    with connect() as connection:
        return pd.read_sql_query(
            """
            SELECT
                name,
                basin_area,
                slope_index,
                risk_coefficient,
                description
            FROM rivers
            ORDER BY id;
            """,
            connection,
        )


def save_observation(
    river_name: str,
    values: dict,
    risk_percent: float,
    risk_level: str,
    model_type: str,
) -> int:
    with connect() as connection:
        river_id = connection.execute(
            "SELECT id FROM rivers WHERE name = ?",
            (river_name,),
        ).fetchone()["id"]

        measurement_cursor = connection.execute(
            """
            INSERT INTO measurements (
                river_id, timestamp, precipitation, temperature, humidity,
                water_flow, snow_water, seismic_activity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                river_id,
                values["timestamp"].isoformat()
                if hasattr(values["timestamp"], "isoformat")
                else str(values["timestamp"]),
                float(values["precipitation"]),
                float(values["temperature"]),
                float(values["humidity"]),
                float(values["water_flow"]),
                float(values["snow_water"]),
                float(values["seismic_activity"]),
            ),
        )
        measurement_id = int(measurement_cursor.lastrowid)

        connection.execute(
            """
            INSERT INTO predictions (
                measurement_id, risk_percent, risk_level, model_type, created_at
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                measurement_id,
                float(risk_percent),
                risk_level,
                model_type,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return measurement_id


def bulk_insert_history(history: pd.DataFrame) -> None:
    if history.empty:
        return

    with connect() as connection:
        river_ids = {
            row["name"]: row["id"]
            for row in connection.execute("SELECT id, name FROM rivers").fetchall()
        }
        measurement_rows = []
        prediction_rows = []

        for row in history.to_dict("records"):
            river_id = river_ids[row["river"]]
            measurement_rows.append(
                (
                    river_id,
                    pd.Timestamp(row["timestamp"]).isoformat(),
                    float(row["precipitation"]),
                    float(row["temperature"]),
                    float(row["humidity"]),
                    float(row["water_flow"]),
                    float(row["snow_water"]),
                    float(row["seismic_activity"]),
                )
            )

        cursor = connection.executemany(
            """
            INSERT INTO measurements (
                river_id, timestamp, precipitation, temperature, humidity,
                water_flow, snow_water, seismic_activity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            measurement_rows,
        )

        first_id = cursor.lastrowid
        if first_id is None:
            first_id = connection.execute(
                "SELECT MAX(id) - ? + 1 FROM measurements",
                (len(measurement_rows),),
            ).fetchone()[0]

        for offset, row in enumerate(history.to_dict("records")):
            prediction_rows.append(
                (
                    int(first_id) + offset,
                    float(row["risk_percent"]),
                    row["risk_level"],
                    row.get("model_type", "Formula"),
                    datetime.now().isoformat(timespec="seconds"),
                )
            )

        connection.executemany(
            """
            INSERT INTO predictions (
                measurement_id, risk_percent, risk_level, model_type, created_at
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            prediction_rows,
        )


def fetch_history(river_name: str | None = None, limit: int | None = None) -> pd.DataFrame:
    query = """
        SELECT
            m.id AS measurement_id,
            r.name AS river,
            m.timestamp,
            m.precipitation,
            m.temperature,
            m.humidity,
            m.water_flow,
            m.snow_water,
            m.seismic_activity,
            p.risk_percent,
            p.risk_level,
            p.model_type,
            p.created_at
        FROM measurements m
        JOIN rivers r ON r.id = m.river_id
        JOIN predictions p ON p.measurement_id = m.id
    """
    params: list = []
    if river_name:
        query += " WHERE r.name = ?"
        params.append(river_name)
    query += " ORDER BY m.timestamp DESC"
    if limit:
        query += " LIMIT ?"
        params.append(int(limit))

    with connect() as connection:
        frame = pd.read_sql_query(query, connection, params=params)
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], format="mixed")
        frame["created_at"] = pd.to_datetime(frame["created_at"], format="mixed")
        frame = frame.sort_values("timestamp")
    return frame


def fetch_events() -> pd.DataFrame:
    query = """
        SELECT
            e.id,
            e.event_date,
            e.start_time,
            e.duration_min,
            e.volume_thousand_m3,
            e.power_level,
            e.trigger_factor,
            r.name AS river
        FROM mudflow_events e
        JOIN rivers r ON r.id = e.river_id
        ORDER BY e.event_date;
    """
    with connect() as connection:
        frame = pd.read_sql_query(query, connection)
    if not frame.empty:
        frame["event_date"] = pd.to_datetime(frame["event_date"])
    return frame


def latest_risk_by_river() -> pd.DataFrame:
    history = fetch_history()
    if history.empty:
        return history
    return (
        history.sort_values("timestamp")
        .groupby("river", as_index=False)
        .tail(1)
        .sort_values("river")
    )
