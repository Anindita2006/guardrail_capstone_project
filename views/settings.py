"""Settings — read-only view of the governance configuration actually in
effect. No destructive actions; changing any of this requires editing
src/config.py or .env, not clicking a button here."""
from __future__ import annotations

import streamlit as st

from src.config import (
    ALLOWED_OWNERS,
    ALLOWED_STAKES,
    CONFIDENCE_ESCALATION_THRESHOLD,
    COVERAGE_SCORE_THRESHOLD,
    DB_PATH,
    ENVIRONMENT,
    HIGH_STAKES_SLA_HOURS,
    MAX_AGENT_TURNS,
    MEDIUM_STAKES_SLA_HOURS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)
from src.judge import JUDGE_MODEL
from src.retrieval import CORPUS_DIR, EMBEDDING_MODEL_NAME, get_index
from ui import theme
from ui.topbar import render_topbar

render_topbar()
theme.page_header("System", "Settings", "The governance configuration currently in effect — read-only.")

p = theme.get_palette()

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(f'{theme.glass_open()}<strong>Environment</strong>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin-top:.5rem;">{theme.chip(ENVIRONMENT)}</div>'
        f'<table style="width:100%;margin-top:.7rem;font-size:.86rem;color:{p["text_secondary"]};">'
        f'<tr><td style="padding:.25rem 0;">API key configured</td><td style="text-align:right;color:{p["text_primary"]};">{"Yes" if OPENAI_API_KEY else "No"}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Base URL</td><td style="text-align:right;color:{p["text_primary"]};">{OPENAI_BASE_URL or "OpenAI default"}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Agent model</td><td style="text-align:right;color:{p["text_primary"]};">{OPENAI_MODEL}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Judge model</td><td style="text-align:right;color:{p["text_primary"]};">{JUDGE_MODEL}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Audit database</td><td style="text-align:right;color:{p["text_primary"]};">{DB_PATH.name}</td></tr>'
        f'</table>{theme.glass_close()}',
        unsafe_allow_html=True,
    )

    st.markdown(f'{theme.glass_open()}<strong>Retrieval</strong>', unsafe_allow_html=True)
    idx = get_index()
    st.markdown(
        f'<table style="width:100%;margin-top:.5rem;font-size:.86rem;color:{p["text_secondary"]};">'
        f'<tr><td style="padding:.25rem 0;">Embedding model</td><td style="text-align:right;color:{p["text_primary"]};">{EMBEDDING_MODEL_NAME}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Corpus directory</td><td style="text-align:right;color:{p["text_primary"]};">{CORPUS_DIR}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Indexed clauses</td><td style="text-align:right;color:{p["text_primary"]};">{len(idx.clauses)}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Coverage threshold</td><td style="text-align:right;color:{p["text_primary"]};">{COVERAGE_SCORE_THRESHOLD}</td></tr>'
        f'</table>{theme.glass_close()}',
        unsafe_allow_html=True,
    )

with col_b:
    st.markdown(f'{theme.glass_open()}<strong>Governance Gate</strong>', unsafe_allow_html=True)
    st.markdown(
        f'<table style="width:100%;margin-top:.5rem;font-size:.86rem;color:{p["text_secondary"]};">'
        f'<tr><td style="padding:.25rem 0;">Confidence escalation threshold</td><td style="text-align:right;color:{p["text_primary"]};">{CONFIDENCE_ESCALATION_THRESHOLD}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Max agent turns</td><td style="text-align:right;color:{p["text_primary"]};">{MAX_AGENT_TURNS}</td></tr>'
        f'<tr><td style="padding:.25rem 0;">High-stakes SLA</td><td style="text-align:right;color:{p["text_primary"]};">{HIGH_STAKES_SLA_HOURS}h</td></tr>'
        f'<tr><td style="padding:.25rem 0;">Medium-stakes SLA</td><td style="text-align:right;color:{p["text_primary"]};">{MEDIUM_STAKES_SLA_HOURS}h</td></tr>'
        f'</table>{theme.glass_close()}',
        unsafe_allow_html=True,
    )

    st.markdown(f'{theme.glass_open()}<strong>Allowed Control Owners</strong>', unsafe_allow_html=True)
    st.markdown(
        "".join(theme.chip(o, category_key=o) for o in sorted(ALLOWED_OWNERS)),
        unsafe_allow_html=True,
    )
    st.markdown(theme.glass_close(), unsafe_allow_html=True)

    st.markdown(f'{theme.glass_open()}<strong>Stakes Levels</strong>', unsafe_allow_html=True)
    st.markdown(
        "".join(theme.risk_badge(s) + " " for s in ["low", "medium", "high"] if s in ALLOWED_STAKES),
        unsafe_allow_html=True,
    )
    st.markdown(theme.glass_close(), unsafe_allow_html=True)
