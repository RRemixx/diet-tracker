"""
Plotly visualization functions for the diet tracker.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- Color palette ---
COLORS = {
    "calories": "#F97316",
    "protein": "#3B82F6",
    "total_fat": "#EAB308",
    "total_carbs": "#10B981",
    "fiber": "#8B5CF6",
    "sugar": "#EC4899",
    "sodium": "#6366F1",
    "potassium": "#14B8A6",
    "goal": "#94A3B8",
}

LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    margin=dict(l=40, r=20, t=40, b=40),
    font=dict(family="Inter, system-ui, sans-serif", size=13),
    hoverlabel=dict(bgcolor="white", font_size=13),
    height=360,
)


def daily_calorie_bar(df: pd.DataFrame, calorie_goal: float = 2000) -> go.Figure:
    """Bar chart of daily total calories with a horizontal goal line."""
    if df.empty:
        return _empty_chart("No data yet")

    daily = df.groupby("date")["calories"].sum().reset_index()
    daily = daily.sort_values("date").tail(14)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["date"], y=daily["calories"],
        marker_color=COLORS["calories"],
        name="Calories",
        hovertemplate="%{x}<br>%{y:.0f} kcal<extra></extra>",
    ))
    fig.add_hline(
        y=calorie_goal, line_dash="dash", line_color=COLORS["goal"],
        annotation_text=f"Goal: {calorie_goal} kcal",
        annotation_position="top right",
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Daily Calories (Last 14 Days)",
        xaxis_title="", yaxis_title="kcal",
    )
    return fig


def macro_area_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked area chart of protein / fat / carbs over time."""
    if df.empty:
        return _empty_chart("No data yet")

    daily = df.groupby("date")[["protein", "total_fat", "total_carbs"]].sum().reset_index()
    daily = daily.sort_values("date").tail(30)

    fig = go.Figure()
    for col, label in [("protein", "Protein"), ("total_fat", "Fat"), ("total_carbs", "Carbs")]:
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily[col],
            mode="lines", stackgroup="one",
            name=label,
            line=dict(width=0.5),
            fillcolor=COLORS.get(col, "#888"),
            hovertemplate=f"{label}: %{{y:.1f}}g<extra></extra>",
        ))
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Macro Breakdown Over Time (Last 30 Days)",
        xaxis_title="", yaxis_title="grams",
    )
    return fig


def micro_trend_lines(df: pd.DataFrame, fields: list[str] | None = None) -> go.Figure:
    """Line chart for selected micronutrients over time."""
    if df.empty:
        return _empty_chart("No data yet")

    if fields is None:
        fields = ["fiber", "sodium", "potassium"]

    daily = df.groupby("date")[fields].sum().reset_index()
    daily = daily.sort_values("date").tail(30)

    fig = go.Figure()
    palette = px.colors.qualitative.Set2
    for i, col in enumerate(fields):
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily[col],
            mode="lines+markers",
            name=col.replace("_", " ").title(),
            line=dict(color=palette[i % len(palette)], width=2),
            marker=dict(size=5),
        ))
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Nutrient Trends (Last 30 Days)",
        xaxis_title="", yaxis_title="Amount",
    )
    return fig


def macro_radar(df: pd.DataFrame) -> go.Figure:
    """Radar/spider chart of average daily macros & key micros."""
    if df.empty:
        return _empty_chart("No data yet")

    fields = ["protein", "total_fat", "total_carbs", "fiber", "sugar", "sodium"]
    labels = ["Protein (g)", "Fat (g)", "Carbs (g)", "Fiber (g)", "Sugar (g)", "Sodium (mg)"]

    daily = df.groupby("date")[fields].sum()
    avg = daily.mean()

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[avg.get(f, 0) for f in fields],
        theta=labels,
        fill="toself",
        fillcolor="rgba(59, 130, 246, 0.15)",
        line=dict(color="#3B82F6", width=2),
        name="Daily Average",
    ))
    radar_layout = {**LAYOUT_DEFAULTS, "height": 400}
    fig.update_layout(
        **radar_layout,
        title="Average Daily Nutrient Profile",
        polar=dict(radialaxis=dict(visible=True, showticklabels=True)),
        showlegend=False,
    )
    return fig


def body_weight_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart of body weight over time."""
    if df.empty:
        return _empty_chart("No body data yet")

    df = df.sort_values("date").tail(90)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["weight_kg"],
        mode="lines+markers",
        name="Weight",
        line=dict(color="#3B82F6", width=2),
        marker=dict(size=6),
        hovertemplate="%{x}<br>%{y:.1f} kg<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Body Weight (Last 90 Days)",
        xaxis_title="", yaxis_title="kg",
    )
    return fig


def body_fat_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart of body fat % over time."""
    if df.empty:
        return _empty_chart("No body data yet")

    df = df.sort_values("date").tail(90)
    df_valid = df.dropna(subset=["body_fat_pct"])
    if df_valid.empty:
        return _empty_chart("No body fat data yet")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid["date"], y=df_valid["body_fat_pct"],
        mode="lines+markers",
        name="Body Fat %",
        line=dict(color="#F97316", width=2),
        marker=dict(size=6),
        hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Body Fat % (Last 90 Days)",
        xaxis_title="", yaxis_title="%",
    )
    return fig


def _empty_chart(message: str) -> go.Figure:
    """Return a placeholder chart with a centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="#94A3B8"),
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig
