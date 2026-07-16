"""Streamlit UI for the Compliance Advisory & Triage Agent (Project 06)."""
import hashlib
import html
import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.agent import run_agent
from src.audit import list_records, mark_reviewed
from src.config import OPENAI_API_KEY
from src.retrieval import get_index

EVAL_REPORT_PATH = Path(__file__).resolve().parent / "eval" / "eval_report.md"

st.set_page_config(page_title="GuardRail — Compliance Assistant", layout="wide")

# Streamlit (this version) doesn't expose theme colors as CSS custom properties, so
# `var(--secondary-background-color)` silently resolves to nothing. st.context.theme
# reflects the resolved theme (including "System" following the OS/browser), so we
# branch on it and inline literal colors for both palettes instead.
_DARK = st.context.theme.type == "dark"

_CARD_BG = "#1c1f26" if _DARK else "#f0efec"
_CARD_BORDER = "rgba(255,255,255,0.14)" if _DARK else "rgba(11,11,11,0.10)"
_MUTED_TEXT = "#a6a49f" if _DARK else "#898781"
_EXCERPT_TEXT = "#c9c7c2" if _DARK else "#52514e"
_METER_TRACK = "rgba(255,255,255,0.16)" if _DARK else "rgba(137,135,129,0.22)"
_CHIP_TEXT = "#7fb2ea" if _DARK else "#1c5cab"
_CHIP_BG = "rgba(42,120,214,0.24)" if _DARK else "rgba(42,120,214,0.12)"

# --- Status palette (fixed roles: good / warning / critical) --------------------
# Text colors are tuned per-theme so they stay readable against their tint
# background (the raw mid-tone status hex is contrast-safe as an accent/icon, not
# as small text) — the tint + text + dot icon together carry the status, so color
# is never the only signal.
if _DARK:
    _STAKES_STYLE = {
        "low": {"dot": "#2ecc40", "text": "#6fdc7f", "bg": "rgba(46,204,64,0.18)"},
        "medium": {"dot": "#ffc107", "text": "#ffd873", "bg": "rgba(255,193,7,0.18)"},
        "high": {"dot": "#ff5c5c", "text": "#ff8f8f", "bg": "rgba(255,92,92,0.18)"},
    }
    _REVIEW_STYLE = {
        "pending": {"dot": "#ffc107", "text": "#ffd873", "bg": "rgba(255,193,7,0.18)", "label": "PENDING REVIEW"},
        "reviewed": {"dot": "#2ecc40", "text": "#6fdc7f", "bg": "rgba(46,204,64,0.18)", "label": "REVIEWED"},
        "n/a": {"dot": "#9a9890", "text": "#c9c7c2", "bg": "rgba(154,152,144,0.18)", "label": "N/A"},
    }
else:
    _STAKES_STYLE = {
        "low": {"dot": "#0ca30c", "text": "#0a7d0a", "bg": "rgba(12,163,12,0.12)"},
        "medium": {"dot": "#fab219", "text": "#8a6000", "bg": "rgba(250,178,25,0.18)"},
        "high": {"dot": "#d03b3b", "text": "#b23030", "bg": "rgba(208,59,59,0.14)"},
    }
    _REVIEW_STYLE = {
        "pending": {"dot": "#fab219", "text": "#8a6000", "bg": "rgba(250,178,25,0.18)", "label": "PENDING REVIEW"},
        "reviewed": {"dot": "#0ca30c", "text": "#0a7d0a", "bg": "rgba(12,163,12,0.12)", "label": "REVIEWED"},
        "n/a": {"dot": "#898781", "text": "#52514e", "bg": "rgba(137,135,129,0.14)", "label": "N/A"},
    }

# --- Categorical palette (identity coding for topics/citations, KPI accents) -----
# 8-hue order validated for CVD/contrast as a set; kept deliberately distinct from
# the status palette above so a topic chip is never mistaken for a stakes/review
# badge. Assignment is a stable hash of the label, not display order, so the same
# topic/clause prefix always gets the same hue across reruns.
_CATEGORY_ORDER = ["blue", "green", "magenta", "yellow", "aqua", "orange", "violet", "red"]
_CATEGORY_ACCENT = {
    "blue": "#3987e5" if _DARK else "#2a78d6",
    "green": "#008300",
    "magenta": "#d55181" if _DARK else "#e87ba4",
    "yellow": "#c98500" if _DARK else "#eda100",
    "aqua": "#199e70" if _DARK else "#1baf7a",
    "orange": "#d95926" if _DARK else "#eb6834",
    "violet": "#9085e9" if _DARK else "#4a3aa7",
    "red": "#e66767" if _DARK else "#e34948",
}
if _DARK:
    _CATEGORY_CHIP_STYLE = {
        "blue": {"text": "#7fb2ea", "bg": "rgba(57,135,229,0.22)"},
        "green": {"text": "#4ade4a", "bg": "rgba(0,131,0,0.22)"},
        "magenta": {"text": "#f5a8c9", "bg": "rgba(213,81,129,0.22)"},
        "yellow": {"text": "#f0c04d", "bg": "rgba(201,133,0,0.22)"},
        "aqua": {"text": "#5fe0b5", "bg": "rgba(25,158,112,0.22)"},
        "orange": {"text": "#ff9d6e", "bg": "rgba(217,89,38,0.22)"},
        "violet": {"text": "#b9b2f0", "bg": "rgba(144,133,233,0.22)"},
        "red": {"text": "#ff9b9a", "bg": "rgba(230,103,103,0.22)"},
    }
else:
    _CATEGORY_CHIP_STYLE = {
        "blue": {"text": "#1c5cab", "bg": "rgba(42,120,214,0.12)"},
        "green": {"text": "#0a6b0a", "bg": "rgba(0,131,0,0.10)"},
        "magenta": {"text": "#a8447a", "bg": "rgba(232,123,164,0.16)"},
        "yellow": {"text": "#8a6300", "bg": "rgba(237,161,0,0.16)"},
        "aqua": {"text": "#0f7a56", "bg": "rgba(27,175,122,0.14)"},
        "orange": {"text": "#a8481f", "bg": "rgba(235,104,52,0.14)"},
        "violet": {"text": "#4a3aa7", "bg": "rgba(74,58,167,0.12)"},
        "red": {"text": "#a8302f", "bg": "rgba(227,73,72,0.14)"},
    }


def _category_slot(key: str) -> str:
    idx = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % len(_CATEGORY_ORDER)
    return _CATEGORY_ORDER[idx]


def _badge(label: str, style: dict) -> str:
    return (
        f'<span class="gr-badge" style="color:{style["text"]};background:{style["bg"]};">'
        f'<span class="gr-badge-dot" style="background:{style["dot"]};"></span>{html.escape(label)}</span>'
    )


def _chip(text: str, category_key: str | None = None) -> str:
    if category_key is not None:
        style = _CATEGORY_CHIP_STYLE[_category_slot(category_key)]
        return (
            f'<span class="gr-chip" style="background:{style["bg"]};color:{style["text"]};">'
            f'{html.escape(text)}</span>'
        )
    return f'<span class="gr-chip">{html.escape(text)}</span>'


def _meter(value: float) -> str:
    pct = max(0, min(100, round(value * 100)))
    return (
        '<div class="gr-meter"><div class="gr-meter-fill" style="width:{pct}%;"></div></div>'
        .format(pct=pct)
    )


def _kpi_tile(label: str, value: str, accent: str) -> str:
    return (
        f'<div class="gr-kpi" style="border-left:3px solid {accent};">'
        f'<div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(str(value))}</div></div>'
    )


def _parse_eval_report(text: str) -> dict:
    """Pull the summary stats, scenario table, and KPI bullets out of the fixed
    markdown format eval/run_eval.py writes (see eval/eval_report.md)."""
    summary = dict(re.findall(r"^\*\*(.+?):\*\*\s*(.+)$", text, re.MULTILINE))

    scenarios = []
    table_match = re.search(
        r"\|\s*Scenario\s*\|\s*Category\s*\|\s*Result\s*\|\s*Detail\s*\|\n\|[-\s|]+\|\n((?:\|.*\|\n?)*)",
        text,
    )
    if table_match:
        for line in table_match.group(1).strip().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 4:
                scenarios.append(
                    {"name": cells[0], "category": cells[1], "result": cells[2], "detail": cells[3]}
                )

    kpis = []
    kpi_section = text.split("## Business KPIs", 1)
    if len(kpi_section) == 2:
        for line in kpi_section[1].splitlines():
            line = line.strip()
            if line.startswith("- "):
                kpis.append(line[2:])

    return {"summary": summary, "scenarios": scenarios, "kpis": kpis}


st.markdown(
    f"""
    <style>
    .gr-header {{
        background: linear-gradient(135deg, #0d366b 0%, #2a78d6 100%);
        color: #ffffff;
        padding: 1.4rem 1.8rem;
        border-radius: 14px;
        margin-bottom: 1.4rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }}
    .gr-header h1 {{ margin: 0; font-size: 1.5rem; font-weight: 700; }}
    .gr-header p {{ margin: .3rem 0 0; opacity: .88; font-size: .92rem; }}
    .gr-header-stats {{ display: flex; gap: 1.6rem; }}
    .gr-header-stats .stat-value {{ font-size: 1.3rem; font-weight: 700; }}
    .gr-header-stats .stat-label {{ font-size: .72rem; opacity: .8; text-transform: uppercase; letter-spacing: .04em; }}

    .gr-card {{
        border: 1px solid {_CARD_BORDER};
        border-radius: 12px;
        padding: 1rem 1.2rem;
        background: {_CARD_BG};
        margin-bottom: .8rem;
    }}

    .gr-kpi-row {{ display: flex; gap: .9rem; flex-wrap: wrap; margin-bottom: 1.1rem; }}
    .gr-kpi {{
        flex: 1; min-width: 150px;
        background: {_CARD_BG};
        border: 1px solid {_CARD_BORDER};
        border-radius: 10px;
        padding: .8rem 1rem;
    }}
    .gr-kpi .label {{ font-size: .72rem; color: {_MUTED_TEXT}; text-transform: uppercase; letter-spacing: .04em; }}
    .gr-kpi .value {{ font-size: 1.5rem; font-weight: 700; margin-top: .15rem; }}

    .gr-badge {{
        display: inline-flex; align-items: center; gap: .35rem;
        padding: .18rem .6rem; border-radius: 999px;
        font-weight: 600; font-size: .78rem; letter-spacing: .02em;
    }}
    .gr-badge-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}

    .gr-chip {{
        display: inline-block; background: {_CHIP_BG}; color: {_CHIP_TEXT};
        padding: .16rem .55rem; border-radius: 6px; font-size: .78rem;
        font-family: ui-monospace, Consolas, monospace; margin: .12rem .25rem .12rem 0;
    }}

    .gr-meter {{
        background: {_METER_TRACK}; border-radius: 999px; height: 7px;
        overflow: hidden; margin: .3rem 0 .1rem;
    }}
    .gr-meter-fill {{ background: #2a78d6; height: 100%; border-radius: 999px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

_corpus_count = len(get_index().clauses)
_logged_count = len(list_records(limit=1000))

st.markdown(
    f"""
    <div class="gr-header">
        <div>
            <h1>GuardRail — Compliance Advisory &amp; Triage Agent</h1>
            <p>Cited answers over the policy corpus · routes to the right control owner ·
            escalates high-stakes questions to a human before any action is implied.</p>
        </div>
        <div class="gr-header-stats">
            <div><div class="stat-value">{_corpus_count}</div><div class="stat-label">Corpus clauses</div></div>
            <div><div class="stat-value">{_logged_count}</div><div class="stat-label">Logged queries</div></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not OPENAI_API_KEY:
    st.error(
        "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key, "
        "then restart the app."
    )
    st.stop()

tab_ask, tab_audit, tab_eval = st.tabs(["Ask a question", "Audit log", "Evaluation"])

with tab_ask:
    col_query, col_result = st.columns([1, 1.3])

    with col_query:
        st.subheader("Query")
        user = st.text_input("Your name / employee id", value="employee_demo")
        question = st.text_area(
            "Compliance question",
            placeholder="e.g. Can we store EU customer data in our US-East region?",
            height=120,
        )
        ask = st.button("Ask GuardRail", type="primary", disabled=not question.strip())

    with col_result:
        st.subheader("Response")
        if ask and question.strip():
            with st.spinner("Retrieving policy, classifying, drafting answer..."):
                try:
                    record = run_agent(question.strip(), user=user or "anonymous")
                except Exception as e:
                    st.error(f"Agent run failed: {e}")
                    record = None

            if record:
                st.markdown(f'<div class="gr-card">{record["answer_text"]}</div>', unsafe_allow_html=True)

                stakes_style = _STAKES_STYLE.get(record["stakes"], _STAKES_STYLE["medium"])
                badges_html = (
                    _badge(record["stakes"].upper(), stakes_style)
                    + " " + _chip(record["topic"], category_key=record["topic"])
                    + " " + _chip("in corpus: yes" if record["in_corpus"] else "in corpus: no")
                )
                st.markdown(badges_html, unsafe_allow_html=True)

                st.markdown(
                    f'<div style="margin-top:.6rem;font-size:.85rem;color:{_MUTED_TEXT};">Confidence — {record["confidence"]:.2f}</div>'
                    + _meter(record["confidence"]),
                    unsafe_allow_html=True,
                )

                if record["citations"]:
                    st.markdown(
                        "**Citations:** " + "".join(
                            _chip(c, category_key=c.split("-")[0]) for c in record["citations"]
                        ),
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='margin-top:.6rem;'></div>", unsafe_allow_html=True)
                if record["escalated"]:
                    st.warning(
                        f"Escalated to **{record['escalated_to']}** — "
                        f"{record['escalation_reason']}"
                    )
                else:
                    st.success("Answered directly — low-stakes, clearly covered by policy.")

                if record["injection_flagged"]:
                    st.info(
                        "Note: the query contained language resembling an attempt to "
                        "override policy guidance. It was treated as untrusted input."
                    )

                with st.expander("Retrieved sources / trace"):
                    st.write(f"Agent turns: {record['agent_turns']} · Tool calls: {record['tool_calls']}")
                    for c in record["retrieved_clauses"]:
                        st.markdown(
                            _chip(c["clause_id"], category_key=c["clause_id"].split("-")[0])
                            + f'<strong>{html.escape(c["title"])}</strong>'
                            + _meter(c["score"])
                            + f'<span style="font-size:.85rem;color:{_EXCERPT_TEXT};">{html.escape(c["text"][:200])}...</span>',
                            unsafe_allow_html=True,
                        )

with tab_audit:
    st.subheader("Audit log")
    records = list_records(limit=100)
    if not records:
        st.write("No queries logged yet.")
    else:
        n = len(records)
        n_escalated = sum(1 for r in records if r["escalated"])
        n_pending = sum(1 for r in records if r["human_review_status"] == "pending")
        avg_conf = sum(r["confidence"] or 0 for r in records) / n

        audit_tiles = "".join([
            _kpi_tile("Total queries", str(n), _CATEGORY_ACCENT["blue"]),
            _kpi_tile("Escalation rate", f"{n_escalated / n:.0%}", _CATEGORY_ACCENT["orange"]),
            _kpi_tile("Pending review", str(n_pending), _CATEGORY_ACCENT["yellow"]),
            _kpi_tile("Avg confidence", f"{avg_conf:.2f}", _CATEGORY_ACCENT["aqua"]),
        ])
        st.markdown(f'<div class="gr-kpi-row">{audit_tiles}</div>', unsafe_allow_html=True)

        for r in records:
            stakes_style = _STAKES_STYLE.get(r["stakes"], _STAKES_STYLE["medium"])
            review_style = _REVIEW_STYLE.get(r["human_review_status"], _REVIEW_STYLE["n/a"])
            header_badges = (
                _badge((r["stakes"] or "?").upper(), stakes_style)
                + " " + _badge(review_style["label"], review_style)
            )
            with st.expander(f"[{r['timestamp']}] {r['question_text'][:70]}"):
                st.markdown(header_badges, unsafe_allow_html=True)
                st.write(f"**User:** {r['user']}")
                st.write(f"**Owner:** {r['owner']} · **Topic:** {r['topic']}")
                st.write(f"**Confidence:** {r['confidence']} · **In corpus:** {bool(r['in_corpus'])}")
                st.write(f"**Escalated:** {bool(r['escalated'])} — {r['escalation_reason'] or ''}")
                if r["citations"]:
                    st.markdown(
                        "**Citations:** " + "".join(
                            _chip(c, category_key=c.split("-")[0]) for c in r["citations"]
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.write("**Citations:** none")
                st.write("**Answer:**")
                st.markdown(r["answer_text"])
                if r["human_review_status"] == "pending":
                    reviewer = st.text_input("Reviewer name", key=f"reviewer_{r['id']}")
                    if st.button("Mark reviewed", key=f"review_btn_{r['id']}"):
                        if reviewer:
                            mark_reviewed(r["id"], reviewer)
                            st.rerun()
                        else:
                            st.warning("Enter a reviewer name first.")

with tab_eval:
    st.subheader("Evaluation")
    if not EVAL_REPORT_PATH.exists():
        st.write(
            "No evaluation report yet. Run `python -m eval.run_eval` from the project "
            "root to generate one."
        )
    else:
        report_text = EVAL_REPORT_PATH.read_text(encoding="utf-8")
        parsed = _parse_eval_report(report_text)
        summary = parsed["summary"]

        mtime = datetime.fromtimestamp(EVAL_REPORT_PATH.stat().st_mtime)
        st.caption(
            f"Read-only snapshot from the last `python -m eval.run_eval` run · "
            f"{mtime:%Y-%m-%d %H:%M}. Re-run that command to refresh it."
        )

        kpi_items = [
            ("Scenarios passed", summary.get("Scenarios passed", "—"), _CATEGORY_ACCENT["green"]),
            ("Avg response time", summary.get("Avg response time", "—"), _CATEGORY_ACCENT["blue"]),
            ("Escalation rate", summary.get("Escalation rate", "—"), _CATEGORY_ACCENT["orange"]),
            ("Citation rate", summary.get("Citation rate", "—"), _CATEGORY_ACCENT["violet"]),
            (
                "Retrieval-tool rate",
                summary.get("Retrieval-tool-invoked rate (trace check)", "—"),
                _CATEGORY_ACCENT["aqua"],
            ),
        ]
        tiles = "".join(_kpi_tile(label, value, accent) for label, value, accent in kpi_items)
        st.markdown(f'<div class="gr-kpi-row">{tiles}</div>', unsafe_allow_html=True)

        if parsed["scenarios"]:
            st.markdown("#### Scenario results")
            for sc in parsed["scenarios"]:
                result_style = _STAKES_STYLE["low"] if sc["result"] == "PASS" else _STAKES_STYLE["high"]
                with st.expander(f"{sc['name']} — {sc['category']}"):
                    st.markdown(_badge(sc["result"], result_style), unsafe_allow_html=True)
                    st.write(sc["detail"])

        if parsed["kpis"]:
            st.markdown("#### Business KPIs")
            for kpi in parsed["kpis"]:
                st.markdown(f"- {kpi}")
