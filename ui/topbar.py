"""Top bar: global search (real, over the audit log + corpus), current user,
environment badge, last corpus refresh, and a real system-health indicator.
Rendered once per page via render_topbar()."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.config import DB_PATH, ENVIRONMENT, OPENAI_API_KEY
from src.retrieval import CORPUS_DIR, get_index
from ui.theme import get_palette, icon


def _corpus_last_refresh() -> datetime | None:
    files = list(CORPUS_DIR.glob("*.md"))
    if not files:
        return None
    return datetime.fromtimestamp(max(f.stat().st_mtime for f in files))


def _system_health() -> tuple[str, str]:
    """Returns (label, tone) — real checks (API key present, corpus loads,
    storage path reachable), not a decorative always-green dot."""
    if not OPENAI_API_KEY:
        return "Degraded — no API key", "danger"
    try:
        idx = get_index()
        if not idx.clauses:
            return "Degraded — empty corpus", "danger"
    except Exception:
        return "Degraded — corpus error", "danger"
    if not DB_PATH.parent.exists():
        return "Degraded — storage unreachable", "danger"
    return "Operational", "success"


def _search_results(query: str, limit: int = 6) -> tuple[list[dict], list]:
    """Substring search over audit-log questions and corpus clauses. Real but
    lightweight — no semantic/fuzzy matching."""
    from src.audit import list_all_records

    q = query.strip().lower()
    if not q:
        return [], []
    records = [r for r in list_all_records() if q in r["question_text"].lower()][:limit]
    clauses = [
        c for c in get_index().clauses
        if q in c.title.lower() or q in c.text.lower() or q in c.clause_id.lower()
    ][:limit]
    return records, clauses


def render_topbar(user_name: str = "employee_demo") -> None:
    p = get_palette()
    health_label, health_tone = _system_health()
    refresh = _corpus_last_refresh()
    refresh_label = refresh.strftime("%Y-%m-%d %H:%M") if refresh else "unknown"

    left, right = st.columns([2, 3], vertical_alignment="center")
    with left:
        with st.popover(":material/search: Search audit log & corpus"):
            query = st.text_input(
                "Search", label_visibility="collapsed",
                placeholder="Search questions, clause IDs, policy text…",
                key="gr_topbar_search",
            )
            if query.strip():
                records, clauses = _search_results(query)
                if not records and not clauses:
                    st.caption("No matches.")
                if records:
                    st.caption(f"Audit log — {len(records)} match(es)")
                    for r in records:
                        st.markdown(f"- `{r['timestamp'][:19]}` {r['question_text'][:80]}")
                if clauses:
                    st.caption(f"Corpus — {len(clauses)} match(es)")
                    for c in clauses:
                        st.markdown(f"- **{c.clause_id}** {c.title}")

    with right:
        st.markdown(
            f"""
            <div class="gr-topbar-right" style="justify-content:flex-end;">
                <span class="gr-env-badge">{ENVIRONMENT}</span>
                <span style="font-size:.78rem;color:{p['text_secondary']};white-space:nowrap;">
                    {icon('user', 13)} {user_name}
                </span>
                <span style="font-size:.78rem;color:{p['text_secondary']};white-space:nowrap;">
                    {icon('refresh-cw', 13)} Corpus refreshed {refresh_label}
                </span>
                <span style="font-size:.78rem;color:{p[health_tone + '_strong']};white-space:nowrap;">
                    <span class="gr-health-dot" style="background:{p[health_tone]};box-shadow:0 0 0 3px {p[health_tone + '_tint']};"></span>{health_label}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
