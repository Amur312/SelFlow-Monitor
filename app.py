from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from config import APP_SUBTITLE, APP_TITLE, DB_PATH, FACTOR_UNITS, RIVER_ORDER, ensure_project_dirs
from data_generator import generate_demo_history, generate_risk_surface
from database import (
    bulk_insert_history,
    count_measurements,
    fetch_events,
    fetch_history,
    fetch_schema,
    fetch_table_counts,
    init_database,
    latest_risk_by_river,
    save_observation,
)
from ml_model import feature_importance_frame, predict_ml_risk, train_model
from risk_engine import (
    build_recommendation,
    calculate_formula_risk,
    classify_risk,
    factor_contributions,
)
from rivers import RIVERS
from visualization import (
    factor_contribution_figure,
    feature_importance_figure,
    heatmap_figure,
    parameter_correlation_figure,
    risk_distribution_figure,
    risk_map_figure,
    risk_surface_figure,
    risk_trend_figure,
    river_comparison_figure,
    time_series_figure,
)


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="S",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --page-bg: #f7e8f1;
            --panel-bg: #f8fafc;
            --card-bg: #ffffff;
            --ink: #182033;
            --muted: #8a93a6;
            --line: #edf0f6;
            --pink: #ec3f8c;
            --purple: #7b54d8;
            --cyan: #37bce4;
            --orange: #ff9f32;
            --shadow: 0 18px 45px rgba(113, 74, 105, 0.13);
        }

        html, body, [class*="css"] {
            font-family: "Inter", "Segoe UI", Arial, sans-serif;
            color: var(--ink);
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(236, 63, 140, 0.12), transparent 26%),
                radial-gradient(circle at 86% 12%, rgba(123, 84, 216, 0.12), transparent 28%),
                var(--page-bg);
        }

        header[data-testid="stHeader"] {
            background: transparent;
            box-shadow: none;
        }

        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu,
        footer {
            display: none !important;
        }

        .block-container {
            max-width: 1480px;
            padding: 2.2rem 2.3rem 3rem;
            margin-top: 1.35rem;
            margin-bottom: 2rem;
            background: var(--panel-bg);
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 18px;
            box-shadow: var(--shadow);
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
            box-shadow: 12px 0 32px rgba(148, 163, 184, 0.13);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0;
        }

        .sidebar-brand {
            min-height: 82px;
            margin: 0 -1rem 1.25rem -1rem;
            padding: 22px 24px;
            display: flex;
            gap: 12px;
            align-items: center;
            color: #fff;
            background: linear-gradient(135deg, var(--pink), var(--purple));
            box-shadow: 0 12px 26px rgba(236, 63, 140, 0.22);
        }

        .brand-mark {
            width: 30px;
            height: 30px;
            border-radius: 10px;
            background: rgba(255,255,255,0.18);
            display: grid;
            place-items: center;
            font-weight: 800;
            border: 1px solid rgba(255,255,255,0.35);
        }

        .sidebar-brand strong {
            display: block;
            font-size: 1.1rem;
            line-height: 1;
        }

        .sidebar-brand span {
            display: block;
            margin-top: 5px;
            font-size: 0.78rem;
            opacity: 0.82;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: #6d7484;
            font-weight: 600;
        }

        [data-testid="stSidebar"] [role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            min-height: 42px;
            padding: 8px 12px;
            border-radius: 12px;
            color: #4b5563;
            transition: all 140ms ease;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: #fdf2f8;
            color: var(--pink);
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(135deg, rgba(236, 63, 140, 0.12), rgba(123, 84, 216, 0.10));
            color: var(--pink);
            box-shadow: inset 4px 0 0 var(--pink);
        }

        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            border-radius: 13px;
            border-color: var(--line);
            background: #fbfcff;
        }

        .stButton > button,
        [data-testid="stFormSubmitButton"] button {
            border: 0;
            border-radius: 13px;
            background: linear-gradient(135deg, var(--pink), var(--purple));
            color: white;
            font-weight: 700;
            min-height: 42px;
            box-shadow: 0 12px 22px rgba(236, 63, 140, 0.20);
        }

        .stButton > button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            color: white;
            filter: brightness(1.02);
            transform: translateY(-1px);
            box-shadow: 0 16px 26px rgba(123, 84, 216, 0.22);
        }

        .hero-shell {
            border-radius: 18px;
            padding: 22px 24px;
            margin-bottom: 22px;
            color: #fff;
            background:
                linear-gradient(135deg, rgba(236, 63, 140, 0.96), rgba(123, 84, 216, 0.94)),
                linear-gradient(45deg, transparent, rgba(255,255,255,0.18));
            box-shadow: 0 18px 36px rgba(123, 84, 216, 0.22);
        }

        .hero-shell h1 {
            margin: 0;
            color: #fff;
            font-size: 2rem;
            line-height: 1.15;
            letter-spacing: 0;
        }

        .hero-shell p {
            margin: 9px 0 0;
            max-width: 820px;
            color: rgba(255,255,255,0.84);
            font-size: 0.98rem;
        }

        .hero-meta {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 18px;
        }

        .hero-pill {
            border-radius: 999px;
            padding: 8px 12px;
            color: rgba(255,255,255,0.92);
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.22);
            font-weight: 600;
            font-size: 0.82rem;
        }

        .metric-card {
            position: relative;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 18px 19px;
            background: var(--card-bg);
            min-height: 124px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.045);
            overflow: hidden;
        }

        .metric-card::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 4px;
            background: var(--accent, var(--pink));
        }

        .metric-card small {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 600;
        }

        .metric-card strong {
            display: block;
            color: var(--ink);
            font-size: 1.85rem;
            line-height: 1.15;
            margin-top: 8px;
            letter-spacing: 0;
        }

        .metric-card .helper {
            display: block;
            margin-top: 9px;
            line-height: 1.35;
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 500;
        }

        .risk-card {
            border-radius: 18px;
            padding: 22px 24px;
            border: 0;
            box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
            overflow: hidden;
            position: relative;
        }

        .risk-card::after {
            content: "";
            position: absolute;
            width: 190px;
            height: 190px;
            border-radius: 999px;
            right: -54px;
            top: -72px;
            background: rgba(255,255,255,0.36);
        }

        .risk-card h3 {
            margin: 0 0 6px 0;
            font-size: 1.1rem;
            position: relative;
            z-index: 1;
        }

        .risk-card .risk-value {
            font-size: 3.15rem;
            line-height: 1;
            font-weight: 800;
            margin: 8px 0;
            position: relative;
            z-index: 1;
        }

        .risk-card div {
            position: relative;
            z-index: 1;
        }

        .gradient-card {
            min-height: 128px;
            border-radius: 16px;
            padding: 20px 22px;
            color: #ffffff;
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.10);
            position: relative;
            overflow: hidden;
        }

        .gradient-card::after {
            content: "";
            position: absolute;
            right: -32px;
            bottom: -46px;
            width: 150px;
            height: 150px;
            border-radius: 999px;
            background: rgba(255,255,255,0.18);
        }

        .gradient-card small {
            display: block;
            color: rgba(255,255,255,0.82);
            font-weight: 700;
            font-size: 0.78rem;
        }

        .gradient-card strong {
            display: block;
            margin-top: 12px;
            color: #fff;
            font-size: 2rem;
            line-height: 1;
            letter-spacing: 0;
        }

        .gradient-card span {
            display: block;
            margin-top: 8px;
            color: rgba(255,255,255,0.78);
            font-size: 0.82rem;
            font-weight: 600;
        }

        [data-testid="stMetric"] {
            background: var(--card-bg);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.045);
        }

        div[data-testid="stPlotlyChart"] {
            background: var(--card-bg);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 14px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.045);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.045);
        }

        div[data-testid="stTabs"] button {
            border-radius: 12px 12px 0 0;
            font-weight: 700;
        }

        .stAlert {
            border-radius: 14px;
            border: 1px solid var(--line);
        }

        .section-note {
            color: var(--muted);
            font-size: 0.92rem;
            margin-top: -0.5rem;
            margin-bottom: 1rem;
        }

        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: 0;
        }

        hr {
            border-color: var(--line);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def bootstrap() -> None:
    ensure_project_dirs()
    init_database()
    if count_measurements() == 0:
        bulk_insert_history(generate_demo_history())


@st.cache_data(show_spinner=False)
def cached_history() -> pd.DataFrame:
    return fetch_history()


@st.cache_data(show_spinner=False)
def cached_latest() -> pd.DataFrame:
    return latest_risk_by_river()


@st.cache_data(show_spinner=False)
def cached_events() -> pd.DataFrame:
    return fetch_events()


def clear_data_cache() -> None:
    cached_history.clear()
    cached_latest.clear()
    cached_events.clear()


def app_header() -> None:
    st.markdown(
        f"""
        <div class="hero-shell">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}. Аналитическая панель для рек Баксан, Малка, Черек и Чегем.</p>
            <div class="hero-meta">
                <span class="hero-pill">SQLite база данных</span>
                <span class="hero-pill">ML-прогноз</span>
                <span class="hero-pill">3D риск-поверхность</span>
                <span class="hero-pill">Plotly аналитика</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, helper: str = "", accent: str = "#ec3f8c") -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--accent:{accent}">
            <small>{label}</small>
            <strong>{value}</strong>
            <span class="helper">{helper}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def gradient_card(label: str, value: str, helper: str, gradient: str) -> None:
    st.markdown(
        f"""
        <div class="gradient-card" style="background:{gradient};">
            <small>{label}</small>
            <strong>{value}</strong>
            <span>{helper}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_card(risk_percent: float, level: dict) -> None:
    st.markdown(
        f"""
        <div class="risk-card" style="background:linear-gradient(135deg, {level['background']}, #ffffff);">
            <h3 style="color:{level['color']}">Уровень: {level['name']}</h3>
            <div class="risk-value" style="color:{level['color']}">{risk_percent:.1f}%</div>
            <div>{level['recommendation']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_default_values(river_name: str) -> dict:
    history = cached_history()
    river_history = history[history["river"] == river_name]
    if river_history.empty:
        return {
            "timestamp": datetime.now(),
            "precipitation": 18.0,
            "temperature": 12.0,
            "humidity": 70.0,
            "water_flow": 55.0,
            "snow_water": 240.0,
            "seismic_activity": 2.5,
        }
    latest = river_history.sort_values("timestamp").iloc[-1]
    return {
        "timestamp": datetime.now(),
        "precipitation": float(latest["precipitation"]),
        "temperature": float(latest["temperature"]),
        "humidity": float(latest["humidity"]),
        "water_flow": float(latest["water_flow"]),
        "snow_water": float(latest["snow_water"]),
        "seismic_activity": float(latest["seismic_activity"]),
    }


def sidebar() -> tuple[str, str]:
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">S</div>
            <div>
                <strong>SelFlow</strong>
                <span>Intelligent Risk Monitor</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    page = st.sidebar.radio(
        "Раздел",
        [
            "Панель мониторинга",
            "Ввод данных",
            "Аналитика",
            "База данных",
            "История событий",
            "О системе",
        ],
    )
    river_name = st.sidebar.selectbox("Река", RIVER_ORDER)

    st.sidebar.divider()
    if st.sidebar.button("Обновить демо-данные", use_container_width=True):
        bulk_insert_history(generate_demo_history(days=30, seed=int(datetime.now().timestamp()) % 10000))
        clear_data_cache()
        st.sidebar.success("Данные добавлены")

    if st.sidebar.button("Обучить ML-модель", use_container_width=True):
        with st.spinner("Обучение модели..."):
            _, message = train_model(force=True)
        st.sidebar.info(message)

    return page, river_name


def dashboard_page(river_name: str) -> None:
    app_header()
    history = cached_history()
    latest = cached_latest()
    selected_history = history[history["river"] == river_name]

    if selected_history.empty:
        st.warning("Нет данных для выбранной реки.")
        return

    current = selected_history.sort_values("timestamp").iloc[-1]
    level = classify_risk(current["risk_percent"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Текущая река", river_name, RIVERS[river_name]["description"], "#7b54d8")
    with col2:
        metric_card("Последний риск", f"{current['risk_percent']:.1f}%", current["risk_level"], level["color"])
    with col3:
        metric_card("Расход воды", f"{current['water_flow']:.1f}", "м3/с", "#37bce4")
    with col4:
        metric_card("Осадки", f"{current['precipitation']:.1f}", "мм/ч", "#ff9f32")

    st.write("")
    risk_card(float(current["risk_percent"]), level)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        gradient_card(
            "Влажность",
            f"{current['humidity']:.0f}%",
            "готовность бассейна к стоку",
            "linear-gradient(135deg, #ec3f8c, #b548bd)",
        )
    with kpi2:
        gradient_card(
            "Снег",
            f"{current['snow_water']:.0f} мм",
            "запас воды в снежном покрове",
            "linear-gradient(135deg, #7b54d8, #4b65d9)",
        )
    with kpi3:
        gradient_card(
            "Сейсмика",
            f"{current['seismic_activity']:.1f}",
            "условная интенсивность сигнала",
            "linear-gradient(135deg, #36bee5, #5f7edc)",
        )
    with kpi4:
        gradient_card(
            "Температура",
            f"{current['temperature']:.1f}°C",
            "фактор снеготаяния",
            "linear-gradient(135deg, #ffb22e, #ff7149)",
        )

    left, right = st.columns([1.15, 0.85])
    with left:
        st.plotly_chart(risk_trend_figure(history, river_name), use_container_width=True)
    with right:
        st.plotly_chart(river_comparison_figure(latest), use_container_width=True)

    st.plotly_chart(risk_map_figure(latest), use_container_width=True)
    st.plotly_chart(time_series_figure(history, river_name), use_container_width=True)


def input_page(river_name: str) -> None:
    app_header()
    st.subheader("Ввод параметров наблюдения")

    defaults = get_default_values(river_name)
    river = RIVERS[river_name]

    with st.form("observation_form"):
        col_time, col_model = st.columns([1, 1])
        with col_time:
            observation_date = st.date_input("Дата наблюдения", value=defaults["timestamp"].date())
            observation_time = st.time_input("Время наблюдения", value=defaults["timestamp"].time())
        with col_model:
            model_type = st.radio(
                "Метод расчета",
                ["Экспертная формула", "ML-модель"],
                horizontal=True,
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            precipitation = st.slider(
                f"Осадки, {FACTOR_UNITS['precipitation']}",
                0.0,
                100.0,
                defaults["precipitation"],
                0.5,
            )
            humidity = st.slider(
                f"Влажность, {FACTOR_UNITS['humidity']}",
                0.0,
                100.0,
                defaults["humidity"],
                0.5,
            )
        with col2:
            temperature = st.slider(
                f"Температура, {FACTOR_UNITS['temperature']}",
                -20.0,
                40.0,
                defaults["temperature"],
                0.5,
            )
            water_flow = st.slider(
                f"Расход воды, {FACTOR_UNITS['water_flow']}",
                0.0,
                300.0,
                defaults["water_flow"],
                0.5,
            )
        with col3:
            snow_water = st.slider(
                f"Запас воды в снеге, {FACTOR_UNITS['snow_water']}",
                0.0,
                1000.0,
                defaults["snow_water"],
                1.0,
            )
            seismic_activity = st.slider(
                f"Сейсмика, {FACTOR_UNITS['seismic_activity']}",
                0.0,
                10.0,
                defaults["seismic_activity"],
                0.1,
            )

        submitted = st.form_submit_button("Рассчитать и сохранить", use_container_width=True)

    values = {
        "timestamp": datetime.combine(observation_date, observation_time),
        "precipitation": precipitation,
        "temperature": temperature,
        "humidity": humidity,
        "water_flow": water_flow,
        "snow_water": snow_water,
        "seismic_activity": seismic_activity,
    }

    formula_risk = calculate_formula_risk(values, river)
    risk_percent = formula_risk
    model_label = "Formula"
    model_message = "Расчет выполнен по экспертной формуле."

    if model_type == "ML-модель":
        ml_risk, message = predict_ml_risk(values, river)
        model_message = message
        if ml_risk is not None:
            risk_percent = ml_risk
            model_label = "RandomForest"

    level = classify_risk(risk_percent)
    contributions = factor_contributions(values)

    result_col, chart_col = st.columns([0.75, 1.25])
    with result_col:
        risk_card(risk_percent, level)
        st.info(model_message)
        st.caption(f"Рекомендация: {build_recommendation(risk_percent)}")
    with chart_col:
        st.plotly_chart(factor_contribution_figure(contributions), use_container_width=True)

    if submitted:
        save_observation(
            river_name=river_name,
            values=values,
            risk_percent=risk_percent,
            risk_level=level["name"],
            model_type=model_label,
        )
        clear_data_cache()
        st.success("Наблюдение и прогноз сохранены в базу данных.")


def analytics_page(river_name: str) -> None:
    app_header()
    history = cached_history()
    if history.empty:
        st.warning("Нет данных для аналитики.")
        return

    base_values = get_default_values(river_name)
    x_grid, y_grid, z_grid = generate_risk_surface(river_name, base_values)

    st.plotly_chart(risk_surface_figure(x_grid, y_grid, z_grid, river_name), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(risk_trend_figure(history, river_name), use_container_width=True)
    with col2:
        st.plotly_chart(heatmap_figure(history), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        contributions = factor_contributions(base_values)
        st.plotly_chart(factor_contribution_figure(contributions), use_container_width=True)
    with col4:
        st.plotly_chart(feature_importance_figure(feature_importance_frame()), use_container_width=True)

    tab1, tab2, tab3 = st.tabs(["Корреляция", "Распределение риска", "Временные ряды"])
    with tab1:
        st.plotly_chart(parameter_correlation_figure(history, river_name), use_container_width=True)
    with tab2:
        st.plotly_chart(risk_distribution_figure(history), use_container_width=True)
    with tab3:
        st.plotly_chart(time_series_figure(history, river_name), use_container_width=True)


def database_page() -> None:
    app_header()
    st.subheader("SQLite-база данных прототипа")
    st.caption(f"Файл базы: {DB_PATH}")

    counts = fetch_table_counts()
    if not counts.empty:
        columns = st.columns(len(counts))
        labels = {
            "rivers": "Реки",
            "measurements": "Измерения",
            "predictions": "Прогнозы",
            "mudflow_events": "Селевые события",
        }
        for column, row in zip(columns, counts.to_dict("records")):
            with column:
                metric_card(labels.get(row["table"], row["table"]), str(row["rows"]))

    st.write("")
    st.subheader("Последние записи наблюдений")
    history = cached_history()
    latest_records = history.sort_values("timestamp", ascending=False).head(20).copy()
    if latest_records.empty:
        st.info("В базе пока нет измерений.")
    else:
        latest_records["timestamp"] = latest_records["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(
            latest_records[
                [
                    "timestamp",
                    "river",
                    "precipitation",
                    "temperature",
                    "humidity",
                    "water_flow",
                    "snow_water",
                    "seismic_activity",
                    "risk_percent",
                    "risk_level",
                    "model_type",
                ]
            ].rename(
                columns={
                    "timestamp": "Дата и время",
                    "river": "Река",
                    "precipitation": "Осадки",
                    "temperature": "Температура",
                    "humidity": "Влажность",
                    "water_flow": "Расход",
                    "snow_water": "Снег",
                    "seismic_activity": "Сейсмика",
                    "risk_percent": "Риск, %",
                    "risk_level": "Уровень",
                    "model_type": "Модель",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Схема таблиц")
    st.dataframe(fetch_schema(), use_container_width=True, hide_index=True)


def events_page() -> None:
    app_header()
    st.subheader("Исторические селевые события")
    events = cached_events()

    if events.empty:
        st.warning("Исторические события не найдены.")
        return

    river_filter = st.multiselect("Фильтр по реке", RIVER_ORDER, default=RIVER_ORDER)
    filtered = events[events["river"].isin(river_filter)].copy()
    filtered["event_date"] = filtered["event_date"].dt.strftime("%Y-%m-%d")
    filtered = filtered.rename(
        columns={
            "event_date": "Дата",
            "start_time": "Время",
            "duration_min": "Длительность, мин",
            "volume_thousand_m3": "Объем, тыс. м3",
            "power_level": "Мощность",
            "trigger_factor": "Триггер",
            "river": "Река",
        }
    )
    st.dataframe(
        filtered[
            [
                "Дата",
                "Время",
                "Река",
                "Длительность, мин",
                "Объем, тыс. м3",
                "Мощность",
                "Триггер",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def about_page() -> None:
    app_header()
    st.subheader("Назначение прототипа")
    st.write(
        """
        Приложение демонстрирует работу прогнозного модуля системы мониторинга селевых потоков.
        Вводимые параметры преобразуются в интегральный показатель риска, сохраняются в SQLite
        и отображаются в интерактивных графиках.
        """
    )

    st.subheader("Архитектура")
    st.code(
        """
Пользователь
  -> Streamlit UI
  -> Модуль расчета признаков
  -> Экспертная формула / RandomForestClassifier
  -> SQLite: rivers, measurements, predictions, mudflow_events
  -> Plotly-графики и аналитические панели
        """.strip(),
        language="text",
    )

    st.subheader("Стек реализации")
    st.dataframe(
        pd.DataFrame(
            [
                {"Слой": "Интерфейс", "Технология": "Streamlit", "Назначение": "формы ввода, страницы, карточки риска"},
                {"Слой": "Визуализация", "Технология": "Plotly", "Назначение": "временные ряды, 3D-поверхность, карта, heatmap"},
                {"Слой": "Данные", "Технология": "SQLite", "Назначение": "локальное хранение измерений и прогнозов"},
                {"Слой": "ML", "Технология": "scikit-learn", "Назначение": "простая модель классификации риска"},
                {"Слой": "Обработка", "Технология": "Pandas, NumPy", "Назначение": "подготовка данных и расчет признаков"},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Промышленное расширение")
    st.write(
        """
        В дипломе тяжелые компоненты Kafka, Flink, TimescaleDB и Kubernetes можно описывать как
        промышленное развитие системы. Текущая реализация оставлена простой, чтобы ее можно было
        запустить локально и показать на защите без серверной инфраструктуры.
        """
    )


def main() -> None:
    inject_styles()
    bootstrap()
    page, river_name = sidebar()

    if page == "Панель мониторинга":
        dashboard_page(river_name)
    elif page == "Ввод данных":
        input_page(river_name)
    elif page == "Аналитика":
        analytics_page(river_name)
    elif page == "База данных":
        database_page()
    elif page == "История событий":
        events_page()
    else:
        about_page()


if __name__ == "__main__":
    main()
