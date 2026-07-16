"""Plotly figure builders, themed to match ui/theme.py's palette so charts read
as one system with the glass cards around them rather than a default plotly
look bolted on top."""
from __future__ import annotations

import plotly.graph_objects as go

from ui.theme import get_palette

_FONT_FAMILY = "-apple-system, 'Segoe UI', Inter, sans-serif"


def _base_layout(p: dict, height: int = 260, showlegend: bool = False) -> dict:
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT_FAMILY, color=p["text_secondary"], size=12),
        margin=dict(l=8, r=8, t=28, b=8),
        height=height,
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        hoverlabel=dict(bgcolor=p["bg_surface_alt"], font_color=p["text_primary"], bordercolor=p["border_strong"]),
    )


def time_series(dates: list, values: list, name: str = "Queries", color_key: str = "accent", height: int = 260) -> go.Figure:
    p = get_palette()
    color = p[color_key]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines",
            name=name,
            line=dict(color=color, width=2.5, shape="spline", smoothing=0.3),
            fill="tozeroy",
            fillcolor=p.get(f"{color_key}_tint", "rgba(16,185,129,0.14)"),
            hovertemplate="%{x}<br>%{y}<extra></extra>",
        )
    )
    fig.update_layout(**_base_layout(p, height=height))
    fig.update_xaxes(showgrid=False, color=p["text_muted"], linecolor=p["border"])
    fig.update_yaxes(showgrid=True, gridcolor=p["chart_grid"], zeroline=False, color=p["text_muted"])
    return fig


def multi_line(dates: list, series: dict[str, list], colors: dict[str, str], height: int = 280) -> go.Figure:
    """series: {label: [values]}, colors: {label: hex}."""
    p = get_palette()
    fig = go.Figure()
    for label, values in series.items():
        fig.add_trace(
            go.Scatter(
                x=dates, y=values, mode="lines", name=label,
                line=dict(color=colors.get(label, p["accent"]), width=2.2),
                hovertemplate="%{x}<br>%{y}<extra>" + label + "</extra>",
            )
        )
    fig.update_layout(**_base_layout(p, height=height, showlegend=True))
    fig.update_xaxes(showgrid=False, color=p["text_muted"], linecolor=p["border"])
    fig.update_yaxes(showgrid=True, gridcolor=p["chart_grid"], zeroline=False, color=p["text_muted"])
    return fig


def donut(labels: list[str], values: list[float], colors: list[str], height: int = 260) -> go.Figure:
    p = get_palette()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors, line=dict(color=p["bg_surface"], width=2)),
                textinfo="label+percent",
                textfont=dict(color=p["text_primary"], size=12),
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            )
        ]
    )
    fig.update_layout(**_base_layout(p, height=height, showlegend=False))
    return fig


def radar(categories: list[str], values: list[float], name: str = "Score", color_key: str = "accent", height: int = 380, max_value: float = 100) -> go.Figure:
    p = get_palette()
    color = p[color_key]
    cats = categories + [categories[0]]
    vals = values + [values[0]]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=vals,
            theta=cats,
            fill="toself",
            name=name,
            line=dict(color=color, width=2),
            fillcolor=p.get(f"{color_key}_tint", "rgba(16,185,129,0.18)"),
            hovertemplate="%{theta}: %{r:.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base_layout(p, height=height),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, max_value], color=p["text_muted"], gridcolor=p["chart_grid"]),
            angularaxis=dict(color=p["text_secondary"], gridcolor=p["chart_grid"]),
        ),
    )
    return fig


def dual_radar(categories: list[str], series: dict[str, list[float]], colors: dict[str, str], height: int = 420, max_value: float = 100) -> go.Figure:
    p = get_palette()
    cats = categories + [categories[0]]
    fig = go.Figure()
    for label, values in series.items():
        vals = values + [values[0]]
        color = colors.get(label, p["accent"])
        fig.add_trace(
            go.Scatterpolar(
                r=vals, theta=cats, fill="toself", name=label,
                line=dict(color=color, width=2),
                opacity=0.85,
                hovertemplate="%{theta}: %{r:.0f}<extra>" + label + "</extra>",
            )
        )
    fig.update_layout(
        **_base_layout(p, height=height, showlegend=True),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, max_value], color=p["text_muted"], gridcolor=p["chart_grid"]),
            angularaxis=dict(color=p["text_secondary"], gridcolor=p["chart_grid"]),
        ),
    )
    return fig


def gauge(value: float, title: str = "", color_key: str = "accent", max_value: float = 100, height: int = 220) -> go.Figure:
    p = get_palette()
    color = p[color_key]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "" if max_value == 100 else "", "font": {"color": p["text_primary"], "size": 30}},
            title={"text": title, "font": {"color": p["text_secondary"], "size": 13}},
            gauge={
                "axis": {"range": [0, max_value], "tickcolor": p["text_muted"], "tickfont": {"color": p["text_muted"], "size": 9}},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 1,
                "bordercolor": p["border"],
                "steps": [
                    {"range": [0, max_value * 0.5], "color": p["danger_tint"]},
                    {"range": [max_value * 0.5, max_value * 0.75], "color": p["secondary_tint"]},
                    {"range": [max_value * 0.75, max_value], "color": p["success_tint"]},
                ],
            },
        )
    )
    fig.update_layout(**_base_layout(p, height=height))
    return fig


def horizontal_bar(labels: list[str], values: list[float], color_key: str = "accent", height: int = 280, max_value: float | None = None) -> go.Figure:
    p = get_palette()
    fig = go.Figure(
        go.Bar(
            x=values, y=labels, orientation="h",
            marker=dict(color=p[color_key]),
            hovertemplate="%{y}: %{x:.1f}<extra></extra>",
        )
    )
    fig.update_layout(**_base_layout(p, height=height))
    fig.update_xaxes(showgrid=True, gridcolor=p["chart_grid"], color=p["text_muted"], range=[0, max_value] if max_value else None)
    fig.update_yaxes(showgrid=False, color=p["text_secondary"], autorange="reversed")
    return fig
