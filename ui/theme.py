"""Shared design system for the GuardRail console: palette, base CSS (glass
cards, sidebar, top bar, tables, animations), icons, and small HTML component
builders (badges, chips, meters, KPI tiles, SLA status).

Streamlit doesn't expose theme colors as CSS custom properties in this version,
so the palette is resolved once per rerun from `st.context.theme.type` and every
color is inlined as a literal — see get_palette().
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import streamlit as st

# --- Palette ----------------------------------------------------------------

_DARK = {
    "bg_page": "#0B1020",
    "bg_surface": "#111827",
    "bg_surface_alt": "#0F172A",
    "glass": "rgba(17,24,39,0.55)",
    "glass_strong": "rgba(17,24,39,0.78)",
    "border": "rgba(148,163,184,0.14)",
    "border_strong": "rgba(148,163,184,0.28)",
    "text_primary": "#E2E8F0",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "accent": "#10B981",
    "accent_strong": "#34D399",
    "accent_tint": "rgba(16,185,129,0.16)",
    "secondary": "#F59E0B",
    "secondary_strong": "#FBBF24",
    "secondary_tint": "rgba(245,158,11,0.16)",
    "danger": "#EF4444",
    "danger_strong": "#F87171",
    "danger_tint": "rgba(239,68,68,0.16)",
    "success": "#22C55E",
    "success_strong": "#4ADE80",
    "success_tint": "rgba(34,197,94,0.16)",
    "neutral": "#94A3B8",
    "neutral_strong": "#CBD5E1",
    "neutral_tint": "rgba(148,163,184,0.14)",
    "shadow": "0 8px 24px rgba(0,0,0,0.35)",
    "chart_paper": "#111827",
    "chart_grid": "rgba(148,163,184,0.12)",
}

_LIGHT = {
    "bg_page": "#F8FAFC",
    "bg_surface": "#FFFFFF",
    "bg_surface_alt": "#F1F5F9",
    "glass": "rgba(255,255,255,0.72)",
    "glass_strong": "rgba(255,255,255,0.92)",
    "border": "rgba(15,23,42,0.08)",
    "border_strong": "rgba(15,23,42,0.16)",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#64748B",
    "accent": "#059669",
    "accent_strong": "#10B981",
    "accent_tint": "rgba(5,150,105,0.12)",
    "secondary": "#B45309",
    "secondary_strong": "#D97706",
    "secondary_tint": "rgba(180,83,9,0.12)",
    "danger": "#DC2626",
    "danger_strong": "#EF4444",
    "danger_tint": "rgba(220,38,38,0.10)",
    "success": "#16A34A",
    "success_strong": "#22C55E",
    "success_tint": "rgba(22,163,74,0.10)",
    "neutral": "#64748B",
    "neutral_strong": "#334155",
    "neutral_tint": "rgba(100,116,139,0.12)",
    "shadow": "0 4px 16px rgba(15,23,42,0.08)",
    "chart_paper": "#FFFFFF",
    "chart_grid": "rgba(15,23,42,0.08)",
}

# 8-hue categorical set (validated for CVD/contrast as an ordered set) used only
# for identity-coding tags — topics, clause/citation prefixes — never for brand
# chrome (buttons, nav, KPI accents), which stays emerald/amber/red/green.
_CATEGORY_ORDER = ["emerald", "violet", "magenta", "amber", "cyan", "orange", "indigo", "rose"]
_CATEGORY_DARK = {
    "emerald": {"text": "#6EE7B7", "bg": "rgba(16,185,129,0.20)"},
    "violet": {"text": "#B9B2F0", "bg": "rgba(144,133,233,0.22)"},
    "magenta": {"text": "#F5A8C9", "bg": "rgba(213,81,129,0.22)"},
    "amber": {"text": "#FDE68A", "bg": "rgba(245,158,11,0.20)"},
    "cyan": {"text": "#67E8F9", "bg": "rgba(34,211,238,0.20)"},
    "orange": {"text": "#FDBA74", "bg": "rgba(249,115,22,0.20)"},
    "indigo": {"text": "#A5B4FC", "bg": "rgba(99,102,241,0.22)"},
    "rose": {"text": "#FDA4AF", "bg": "rgba(244,63,94,0.20)"},
}
_CATEGORY_LIGHT = {
    "emerald": {"text": "#047857", "bg": "rgba(5,150,105,0.12)"},
    "violet": {"text": "#5B21B6", "bg": "rgba(124,58,237,0.12)"},
    "magenta": {"text": "#9D174D", "bg": "rgba(219,39,119,0.12)"},
    "amber": {"text": "#92400E", "bg": "rgba(217,119,6,0.14)"},
    "cyan": {"text": "#0E7490", "bg": "rgba(8,145,178,0.12)"},
    "orange": {"text": "#9A3412", "bg": "rgba(234,88,12,0.12)"},
    "indigo": {"text": "#3730A3", "bg": "rgba(79,70,229,0.12)"},
    "rose": {"text": "#9F1239", "bg": "rgba(225,29,72,0.12)"},
}


def is_dark() -> bool:
    return st.context.theme.type == "dark"


def get_palette() -> dict:
    return dict(_DARK if is_dark() else _LIGHT)


def category_style(key: str) -> dict:
    order = _CATEGORY_DARK if is_dark() else _CATEGORY_LIGHT
    idx = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % len(_CATEGORY_ORDER)
    return order[_CATEGORY_ORDER[idx]]


# --- Icons (Feather-style, 24x24, stroke=currentColor) -----------------------

_ICONS = {
    "dashboard": '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
    "message": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
    "file-check": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15l2 2 4-4"/>',
    "alert-triangle": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "book-open": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "user": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "server": '<rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "arrow-up-right": '<line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/>',
    "arrow-down-right": '<line x1="7" y1="7" x2="17" y2="17"/><polyline points="17 7 17 17 7 17"/>',
    "check-circle": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "x-circle": '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
    "refresh-cw": '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M20.49 9A9 9 0 0 0 5.65 5.36L1 10m22 4l-4.65 4.64A9 9 0 0 1 3.51 15"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "tag": '<path d="M20.59 13.41L13.42 20.6a2 2 0 0 1-2.83 0L2.5 12.5V4a2 2 0 0 1 2-2h8.5l7.59 7.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
    "gauge": '<path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 12l6-3"/><path d="M12 2v3"/>',
}


def icon(name: str, size: int = 16, color: str = "currentColor", stroke_width: float = 2) -> str:
    body = _ICONS.get(name, "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;">{body}</svg>'
    )


# --- Base CSS -----------------------------------------------------------------

def inject_base_css() -> None:
    p = get_palette()
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{ font-family: -apple-system, "Segoe UI", Inter, sans-serif; }}

        [data-testid="stAppViewContainer"] > .main {{ background: {p['bg_page']}; }}
        [data-testid="stSidebar"] {{
            background: {p['bg_surface']};
            border-right: 1px solid {p['border']};
        }}
        [data-testid="stHeader"] {{ background: transparent; }}

        .block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }}

        /* ---- Glass surfaces ---- */
        .gr-glass {{
            background: {p['glass']};
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid {p['border']};
            border-radius: 14px;
            box-shadow: {p['shadow']};
            transition: border-color .15s ease, transform .15s ease;
        }}
        .gr-glass:hover {{ border-color: {p['border_strong']}; }}
        .gr-card {{ padding: 1.1rem 1.3rem; margin-bottom: .9rem; }}
        .gr-card.hoverable:hover {{ transform: translateY(-1px); }}

        /* ---- Page header (compact, no hero banner) ---- */
        .gr-page-header {{ margin-bottom: 1.3rem; }}
        .gr-page-header .brand-tag {{
            display: flex; align-items: center; gap: .3rem; font-size: .7rem; font-weight: 700;
            letter-spacing: .04em; color: {p['text_muted']}; margin-bottom: .5rem;
        }}
        .gr-page-header .brand-tag svg {{ flex-shrink: 0; }}
        .gr-page-header .eyebrow {{
            font-size: .72rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
            color: {p['accent_strong']}; margin-bottom: .2rem;
        }}
        .gr-page-header h1 {{
            font-size: 1.5rem; font-weight: 700; color: {p['text_primary']}; margin: 0;
            letter-spacing: -.01em;
        }}
        .gr-page-header p {{
            font-size: .88rem; color: {p['text_secondary']}; margin: .3rem 0 0; max-width: 720px;
        }}

        /* ---- Top bar ---- */
        .gr-topbar {{
            display: flex; align-items: center; justify-content: space-between;
            gap: 1rem; padding: .55rem .9rem; margin-bottom: 1.2rem;
            flex-wrap: wrap;
        }}
        .gr-topbar-left {{ display: flex; align-items: center; gap: .6rem; color: {p['text_secondary']}; font-size: .82rem; }}
        .gr-topbar-right {{ display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }}
        .gr-env-badge {{
            font-size: .68rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
            padding: .2rem .55rem; border-radius: 6px; border: 1px solid {p['border_strong']};
            color: {p['secondary_strong']}; background: {p['secondary_tint']};
        }}
        .gr-health-dot {{
            width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: .35rem;
            box-shadow: 0 0 0 3px {p['success_tint']};
        }}

        /* ---- Sidebar brand ---- */
        .gr-brand {{
            display: flex; align-items: center; gap: .55rem; padding: .3rem 0 1rem;
            color: {p['text_primary']}; font-weight: 700; font-size: 1.05rem;
            border-bottom: 1px solid {p['border']}; margin-bottom: .8rem;
        }}
        .gr-brand .mark {{
            width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center;
            justify-content: center; background: linear-gradient(135deg, {p['accent']}, {p['accent_strong']});
            color: #06251b; flex-shrink: 0;
        }}
        .gr-brand small {{ display: block; font-weight: 500; font-size: .68rem; color: {p['text_muted']}; }}

        /* ---- KPI tiles ---- */
        .gr-kpi-row {{ display: flex; gap: .8rem; flex-wrap: wrap; margin-bottom: 1.1rem; }}
        .gr-kpi {{ flex: 1; min-width: 170px; padding: .95rem 1.1rem; }}
        .gr-kpi .top {{ display: flex; align-items: center; justify-content: space-between; }}
        .gr-kpi .label {{
            font-size: .7rem; color: {p['text_secondary']}; text-transform: uppercase;
            letter-spacing: .06em; font-weight: 600;
        }}
        .gr-kpi .value {{ font-size: 1.6rem; font-weight: 700; color: {p['text_primary']}; margin-top: .25rem; }}
        .gr-kpi .delta {{ font-size: .75rem; margin-top: .15rem; font-weight: 600; }}
        .gr-kpi .delta.up {{ color: {p['success_strong']}; }}
        .gr-kpi .delta.down {{ color: {p['danger_strong']}; }}
        .gr-kpi .delta.flat {{ color: {p['text_muted']}; }}

        /* ---- Badges / chips ---- */
        .gr-badge {{
            display: inline-flex; align-items: center; gap: .35rem;
            padding: .2rem .62rem; border-radius: 999px;
            font-weight: 600; font-size: .74rem; letter-spacing: .02em;
            border: 1px solid transparent;
        }}
        .gr-badge-dot {{ width: 7px; height: 7px; border-radius: 50%; display: inline-block; }}
        .gr-chip {{
            display: inline-block; padding: .16rem .55rem; border-radius: 6px; font-size: .74rem;
            font-family: ui-monospace, "SF Mono", Consolas, monospace; margin: .12rem .25rem .12rem 0;
        }}

        /* ---- Meters ---- */
        .gr-meter {{
            background: {p['neutral_tint']}; border-radius: 999px; height: 6px;
            overflow: hidden; margin: .35rem 0 .1rem;
        }}
        .gr-meter-fill {{ height: 100%; border-radius: 999px; }}

        /* ---- SLA / timeline ---- */
        .gr-timeline-item {{
            position: relative; padding-left: 1.3rem; padding-bottom: 1rem; border-left: 2px solid {p['border']};
            margin-left: .4rem;
        }}
        .gr-timeline-item:last-child {{ border-color: transparent; }}
        .gr-timeline-item .dot {{
            position: absolute; left: -6px; top: 2px; width: 10px; height: 10px; border-radius: 50%;
            background: {p['accent']}; box-shadow: 0 0 0 3px {p['accent_tint']};
        }}

        /* ---- Skeleton loader ---- */
        .gr-skeleton {{
            border-radius: 10px; background: linear-gradient(90deg, {p['bg_surface_alt']} 25%, {p['border_strong']} 37%, {p['bg_surface_alt']} 63%);
            background-size: 400% 100%; animation: gr-shimmer 1.4s ease infinite;
        }}
        @keyframes gr-shimmer {{ 0% {{ background-position: 100% 50%; }} 100% {{ background-position: 0 50%; }} }}

        /* ---- Kanban ---- */
        .gr-kanban-col-header {{
            display: flex; align-items: center; justify-content: space-between;
            padding: .5rem .2rem; margin-bottom: .6rem; border-bottom: 2px solid {p['border']};
        }}
        .gr-kanban-col-header h4 {{ margin: 0; font-size: .88rem; color: {p['text_primary']}; }}
        .gr-kanban-count {{
            font-size: .72rem; font-weight: 700; color: {p['text_secondary']};
            background: {p['neutral_tint']}; padding: .1rem .5rem; border-radius: 999px;
        }}

        /* Buttons */
        .stButton > button {{ border-radius: 8px; transition: all .12s ease; }}
        .stButton > button:hover {{ transform: translateY(-1px); }}

        /* Tabs */
        .stTabs [data-baseweb="tab"] {{ font-weight: 600; }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-thumb {{ background: {p['border_strong']}; border-radius: 8px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- Component builders --------------------------------------------------------

def page_header(eyebrow: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="gr-page-header">
            <div class="brand-tag">{icon('shield', 12, stroke_width=2.4)} GuardRail</div>
            <div class="eyebrow">{eyebrow}</div>
            <h1>{title}</h1>
            {f'<p>{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


_RISK_KIND = {
    "low": ("success", "success_tint", "success_strong"),
    "medium": ("secondary", "secondary_tint", "secondary_strong"),
    "high": ("danger", "danger_tint", "danger_strong"),
}
_STATUS_KIND = {
    "pending": ("secondary", "secondary_tint", "secondary_strong", "PENDING"),
    "assigned": ("accent", "accent_tint", "accent_strong", "ASSIGNED"),
    "reviewed": ("success", "success_tint", "success_strong", "RESOLVED"),
    "n/a": ("neutral", "neutral_tint", "text_secondary", "N/A"),
}
_VERDICT_KIND = {
    "PASS": ("success", "success_tint", "success_strong"),
    "CONCERN": ("secondary", "secondary_tint", "secondary_strong"),
    "FAIL": ("danger", "danger_tint", "danger_strong"),
}


def badge(label: str, dot_key: str, tint_key: str, text_key: str) -> str:
    p = get_palette()
    return (
        f'<span class="gr-badge" style="color:{p[text_key]};background:{p[tint_key]};">'
        f'<span class="gr-badge-dot" style="background:{p[dot_key]};"></span>{label}</span>'
    )


def risk_badge(stakes: str) -> str:
    dot, tint, text = _RISK_KIND.get(stakes, _RISK_KIND["medium"])
    return badge((stakes or "unknown").upper(), dot, tint, text)


def status_badge(status: str) -> str:
    dot, tint, text, label = _STATUS_KIND.get(status, _STATUS_KIND["n/a"])
    return badge(label, dot, tint, text)


def verdict_badge(verdict: str) -> str:
    dot, tint, text = _VERDICT_KIND.get(verdict, _VERDICT_KIND["CONCERN"])
    return badge(verdict, dot, tint, text)


def chip(text: str, category_key: str | None = None) -> str:
    p = get_palette()
    if category_key is not None:
        style = category_style(category_key)
        return f'<span class="gr-chip" style="background:{style["bg"]};color:{style["text"]};">{text}</span>'
    return f'<span class="gr-chip" style="background:{p["accent_tint"]};color:{p["accent_strong"]};">{text}</span>'


def meter(value: float, kind: str = "accent") -> str:
    p = get_palette()
    pct = max(0, min(100, round(value * 100)))
    color = p.get(kind, p["accent"])
    return f'<div class="gr-meter"><div class="gr-meter-fill" style="width:{pct}%;background:{color};"></div></div>'


def kpi_tile(label: str, value: str, accent_hex: str, delta: str | None = None, delta_dir: str = "flat") -> str:
    delta_html = f'<div class="delta {delta_dir}">{delta}</div>' if delta else ""
    return (
        f'<div class="gr-glass gr-kpi" style="border-left:3px solid {accent_hex};">'
        f'<div class="label">{label}</div><div class="value">{value}</div>{delta_html}</div>'
    )


def glass_open(extra_class: str = "", extra_style: str = "") -> str:
    return f'<div class="gr-glass gr-card {extra_class}" style="{extra_style}">'


def glass_close() -> str:
    return "</div>"


def sla_status(due_at_iso: str | None) -> tuple[str, str]:
    """Returns (label, tone) where tone in {success, secondary, danger, neutral}."""
    if not due_at_iso:
        return "No SLA", "neutral"
    due = datetime.fromisoformat(due_at_iso)
    now = datetime.now(timezone.utc) if due.tzinfo else datetime.now()
    remaining = due - now
    hours = remaining.total_seconds() / 3600
    if hours < 0:
        return f"Overdue by {abs(hours):.0f}h", "danger"
    if hours < 6:
        return f"Due in {hours:.0f}h", "secondary"
    return f"Due in {hours:.0f}h", "success"
