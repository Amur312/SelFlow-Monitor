from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import FACTOR_LABELS, RISK_LEVELS
from rivers import RIVERS


PLOT_TEMPLATE = "plotly_white"


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        template=PLOT_TEMPLATE,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": "Недостаточно данных",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 16, "color": "#64748b"},
            }
        ],
    )
    return fig


def time_series_figure(history: pd.DataFrame, river_name: str) -> go.Figure:
    if history.empty:
        return empty_figure("Временные ряды параметров")

    frame = history[history["river"] == river_name].copy()
    if frame.empty:
        return empty_figure("Временные ряды параметров")

    columns = [
        "precipitation",
        "water_flow",
        "humidity",
        "temperature",
        "snow_water",
        "seismic_activity",
    ]
    labels = {
        "timestamp": "Дата",
        "value": "Значение",
        "variable": "Параметр",
        **FACTOR_LABELS,
    }
    melted = frame.melt(
        id_vars=["timestamp"],
        value_vars=columns,
        var_name="variable",
        value_name="value",
    )
    melted["variable"] = melted["variable"].map(FACTOR_LABELS)

    fig = px.line(
        melted,
        x="timestamp",
        y="value",
        color="variable",
        template=PLOT_TEMPLATE,
        labels=labels,
        title=f"Временные ряды параметров: {river_name}",
    )
    fig.update_layout(legend_title_text="", hovermode="x unified")
    return fig


def risk_trend_figure(history: pd.DataFrame, river_name: str) -> go.Figure:
    if history.empty:
        return empty_figure("Динамика риска")

    frame = history[history["river"] == river_name].copy()
    if frame.empty:
        return empty_figure("Динамика риска")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["risk_percent"],
            mode="lines+markers",
            name="Риск",
            line={"color": "#2563eb", "width": 3},
            marker={"size": 5},
        )
    )
    for level in RISK_LEVELS:
        fig.add_hrect(
            y0=level["min"],
            y1=min(level["max"], 100),
            fillcolor=level["color"],
            opacity=0.08,
            line_width=0,
        )
    fig.update_layout(
        title=f"Динамика риска: {river_name}",
        xaxis_title="Дата",
        yaxis_title="Риск, %",
        yaxis_range=[0, 100],
        template=PLOT_TEMPLATE,
        hovermode="x unified",
    )
    return fig


def river_comparison_figure(latest: pd.DataFrame) -> go.Figure:
    if latest.empty:
        return empty_figure("Сравнение риска по рекам")

    fig = px.bar(
        latest.sort_values("risk_percent", ascending=False),
        x="river",
        y="risk_percent",
        color="risk_level",
        text="risk_percent",
        template=PLOT_TEMPLATE,
        labels={"river": "Река", "risk_percent": "Риск, %", "risk_level": "Уровень"},
        title="Текущий риск по рекам",
        color_discrete_map={
            "Низкий": "#16a34a",
            "Повышенный": "#ca8a04",
            "Высокий": "#ea580c",
            "Критический": "#dc2626",
        },
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(yaxis_range=[0, 105], legend_title_text="")
    return fig


def risk_map_figure(latest: pd.DataFrame) -> go.Figure:
    if latest.empty:
        return empty_figure("Карта текущего риска")

    frame = latest.copy()
    frame["latitude"] = frame["river"].map(lambda name: RIVERS[name]["latitude"])
    frame["longitude"] = frame["river"].map(lambda name: RIVERS[name]["longitude"])
    frame["description"] = frame["river"].map(lambda name: RIVERS[name]["description"])

    fig = px.scatter_geo(
        frame,
        lat="latitude",
        lon="longitude",
        color="risk_level",
        size="risk_percent",
        hover_name="river",
        hover_data={
            "risk_percent": ":.1f",
            "risk_level": True,
            "description": True,
            "latitude": False,
            "longitude": False,
        },
        labels={"risk_percent": "Риск, %", "risk_level": "Уровень"},
        title="Карта текущего риска по бассейнам рек",
        template=PLOT_TEMPLATE,
        color_discrete_map={
            "Низкий": "#16a34a",
            "Повышенный": "#ca8a04",
            "Высокий": "#ea580c",
            "Критический": "#dc2626",
        },
    )
    fig.update_geos(
        center={"lat": 43.55, "lon": 43.58},
        projection_scale=27,
        showland=True,
        landcolor="#f8fafc",
        showlakes=True,
        lakecolor="#e0f2fe",
        showcountries=True,
        countrycolor="#cbd5e1",
        showrivers=True,
        rivercolor="#93c5fd",
    )
    fig.update_traces(marker={"sizemin": 10, "line": {"width": 1, "color": "#0f172a"}})
    fig.update_layout(height=470, legend_title_text="")
    return fig


def risk_distribution_figure(history: pd.DataFrame) -> go.Figure:
    if history.empty:
        return empty_figure("Распределение уровней риска")

    frame = (
        history.groupby(["river", "risk_level"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    fig = px.bar(
        frame,
        x="river",
        y="count",
        color="risk_level",
        template=PLOT_TEMPLATE,
        labels={"river": "Река", "count": "Количество наблюдений", "risk_level": "Уровень"},
        title="Распределение уровней риска по рекам",
        color_discrete_map={
            "Низкий": "#16a34a",
            "Повышенный": "#ca8a04",
            "Высокий": "#ea580c",
            "Критический": "#dc2626",
        },
    )
    fig.update_layout(legend_title_text="", barmode="stack")
    return fig


def parameter_correlation_figure(history: pd.DataFrame, river_name: str) -> go.Figure:
    if history.empty:
        return empty_figure("Корреляция факторов")

    columns = [
        "precipitation",
        "temperature",
        "humidity",
        "water_flow",
        "snow_water",
        "seismic_activity",
        "risk_percent",
    ]
    frame = history[history["river"] == river_name][columns].copy()
    if frame.empty or len(frame) < 3:
        return empty_figure("Корреляция факторов")

    labels = {
        **FACTOR_LABELS,
        "risk_percent": "Риск",
    }
    corr = frame.corr(numeric_only=True).rename(index=labels, columns=labels)
    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu",
        zmin=-1,
        zmax=1,
        template=PLOT_TEMPLATE,
        title=f"Корреляция факторов: {river_name}",
        labels={"color": "r"},
    )
    fig.update_layout(height=520)
    return fig


def factor_contribution_figure(contributions: list[dict]) -> go.Figure:
    if not contributions:
        return empty_figure("Вклад факторов")

    frame = pd.DataFrame(contributions).sort_values("contribution")
    fig = px.bar(
        frame,
        x="contribution",
        y="factor",
        orientation="h",
        template=PLOT_TEMPLATE,
        text="contribution",
        labels={"contribution": "Вклад, баллы риска", "factor": "Фактор"},
        title="Вклад факторов в расчет риска",
        color="contribution",
        color_continuous_scale=["#22c55e", "#facc15", "#f97316", "#dc2626"],
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    return fig


def risk_surface_figure(x_grid, y_grid, z_grid, river_name: str) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Surface(
                x=x_grid,
                y=y_grid,
                z=z_grid,
                colorscale="RdYlGn_r",
                colorbar={"title": "Риск, %"},
            )
        ]
    )
    fig.update_layout(
        title=f"3D-поверхность риска: {river_name}",
        template=PLOT_TEMPLATE,
        scene={
            "xaxis_title": "Осадки, мм/ч",
            "yaxis_title": "Расход воды, м3/с",
            "zaxis_title": "Риск, %",
            "zaxis": {"range": [0, 100]},
        },
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
        height=640,
    )
    return fig


def heatmap_figure(history: pd.DataFrame) -> go.Figure:
    if history.empty:
        return empty_figure("Тепловая карта риска")

    frame = history.copy()
    frame["date"] = frame["timestamp"].dt.date
    pivot = frame.pivot_table(
        index="river",
        columns="date",
        values="risk_percent",
        aggfunc="mean",
    )
    if pivot.empty:
        return empty_figure("Тепловая карта риска")

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="RdYlGn_r",
        labels={"x": "Дата", "y": "Река", "color": "Риск, %"},
        title="Тепловая карта среднего риска",
        template=PLOT_TEMPLATE,
    )
    fig.update_layout(height=420)
    return fig


def feature_importance_figure(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return empty_figure("Важность признаков ML-модели")
    labels = {
        "precipitation": "Осадки",
        "temperature": "Температура",
        "humidity": "Влажность",
        "water_flow": "Расход",
        "snow_water": "Снег",
        "seismic_activity": "Сейсмика",
        "river_coefficient": "Коэфф. реки",
        "slope_index": "Уклон",
        "precipitation_flow_index": "Осадки x расход",
        "snowmelt_index": "Индекс снеготаяния",
    }
    data = frame.copy()
    data["feature"] = data["feature"].map(labels).fillna(data["feature"])
    data = data.sort_values("importance")
    fig = px.bar(
        data,
        x="importance",
        y="feature",
        orientation="h",
        template=PLOT_TEMPLATE,
        title="Важность признаков ML-модели",
        labels={"importance": "Важность", "feature": "Признак"},
        color="importance",
        color_continuous_scale="Blues",
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig
