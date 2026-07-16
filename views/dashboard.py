"""Dashboard — system overview, query activity, risk distribution, recent
escalations, retrieval performance, and an evaluation summary. Every number
here is computed from the real audit log / eval-run history; anything without
data yet shows an honest empty state instead of a placeholder number.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from src.audit import list_all_records
from src.eval_store import latest_run_averages, list_eval_runs
from src.retrieval import get_index
from ui import theme
from ui.charts import donut, time_series
from ui.topbar import render_topbar

render_topbar()
theme.page_header(
    "Overview",
    "Dashboard",
    "Real-time posture across query volume, escalation risk, retrieval quality, and evaluation trust.",
)

p = theme.get_palette()
records = list_all_records()
clauses = get_index().clauses

# --- System overview KPIs ----------------------------------------------------

today = date.today()
queries_today = sum(1 for r in records if r["timestamp"][:10] == today.isoformat())
n_total = len(records)
n_escalated = sum(1 for r in records if r["escalated"])
escalation_rate = (n_escalated / n_total) if n_total else 0.0
confidences = [r["confidence"] for r in records if r["confidence"] is not None]
avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
n_cited = sum(1 for r in records if r["citations"])
citation_coverage = (n_cited / n_total) if n_total else 0.0

run_avgs = latest_run_averages()
if run_avgs:
    ragas_score = sum(run_avgs["ragas"].values()) / len(run_avgs["ragas"])
    ragas_display = f"{ragas_score:.0f}"
else:
    ragas_display = "—"

tiles = "".join([
    theme.kpi_tile("Corpus Size", f"{len(clauses)} clauses", p["accent"]),
    theme.kpi_tile("Queries Today", str(queries_today), p["secondary"]),
    theme.kpi_tile("Escalation Rate", f"{escalation_rate:.0%}", p["danger"]),
    theme.kpi_tile("Avg Confidence", f"{avg_confidence:.2f}", p["success"]),
    theme.kpi_tile("Citation Coverage", f"{citation_coverage:.0%}", theme.category_style("citation")["text"]),
    theme.kpi_tile(
        "RAGAS Score",
        ragas_display,
        p["accent_strong"] if run_avgs else p["neutral"],
        delta=None if run_avgs else "no eval run yet",
        delta_dir="flat",
    ),
])
st.markdown(f'<div class="gr-kpi-row">{tiles}</div>', unsafe_allow_html=True)

# --- Query activity + risk distribution --------------------------------------

col_activity, col_risk = st.columns([2, 1])

with col_activity:
    st.markdown(f'{theme.glass_open()}<strong>Query Activity</strong> <span style="color:{p["text_muted"]};font-size:.8rem;">— last 14 days</span>', unsafe_allow_html=True)
    day_counts = Counter(r["timestamp"][:10] for r in records)
    last_14 = [(today - timedelta(days=i)) for i in range(13, -1, -1)]
    dates = [d.isoformat() for d in last_14]
    values = [day_counts.get(d, 0) for d in dates]
    if any(values):
        st.plotly_chart(time_series(dates, values, name="Queries", color_key="accent"), use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No queries logged yet — ask a question from Ask Compliance to populate this chart.")
    st.markdown(theme.glass_close(), unsafe_allow_html=True)

with col_risk:
    st.markdown(f'{theme.glass_open()}<strong>Risk Distribution</strong>', unsafe_allow_html=True)
    stakes_counts = Counter(r["stakes"] for r in records if r["stakes"])
    if stakes_counts:
        labels = ["Low", "Medium", "High"]
        keys = ["low", "medium", "high"]
        values = [stakes_counts.get(k, 0) for k in keys]
        colors = [p["success"], p["secondary"], p["danger"]]
        st.plotly_chart(donut(labels, values, colors, height=220), use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No stakes-classified queries yet.")
    st.markdown(theme.glass_close(), unsafe_allow_html=True)

# --- Recent escalations + retrieval performance ------------------------------

col_esc, col_retrieval = st.columns([3, 2])

with col_esc:
    st.markdown(f'{theme.glass_open()}<strong>Recent Escalations</strong>', unsafe_allow_html=True)
    escalated = [r for r in records if r["escalated"]][:8]
    if escalated:
        df = pd.DataFrame([
            {
                "Timestamp": r["timestamp"][:19].replace("T", " "),
                "User": r["user"],
                "Query": r["question_text"][:60],
                "Risk": (r["stakes"] or "—").upper(),
                "Confidence": r["confidence"] or 0.0,
                "Status": (r["human_review_status"] or "n/a").upper(),
            }
            for r in escalated
        ])
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.2f"),
            },
        )
    else:
        st.caption("No escalations yet.")
    st.markdown(theme.glass_close(), unsafe_allow_html=True)

with col_retrieval:
    st.markdown(f'{theme.glass_open()}<strong>Retrieval Performance</strong> <span style="color:{p["text_muted"]};font-size:.8rem;">— avg top match score</span>', unsafe_allow_html=True)
    day_scores = defaultdict(list)
    for r in records:
        if r["retrieved_clauses"]:
            top_score = max((c.get("score", 0) for c in r["retrieved_clauses"]), default=0)
            day_scores[r["timestamp"][:10]].append(top_score)
    dates = [d.isoformat() for d in last_14]
    values = [(sum(day_scores[d]) / len(day_scores[d])) if day_scores.get(d) else 0 for d in dates]
    if any(values):
        st.plotly_chart(time_series(dates, values, name="Top match score", color_key="secondary"), use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No retrieval activity yet.")
    st.markdown(theme.glass_close(), unsafe_allow_html=True)

# --- Evaluation summary -------------------------------------------------------

st.markdown(f'{theme.glass_open()}<strong>Evaluation Summary</strong>', unsafe_allow_html=True)
if run_avgs:
    dims = run_avgs["dimensions"]
    ragas = run_avgs["ragas"]
    run = run_avgs["run"]
    st.caption(
        f"From the latest evaluation run `{run['run_id']}` "
        f"({run['timestamp'][:19].replace('T', ' ')}) — {run_avgs['n_scored']} scenario(s) judged."
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Judge Pass Rate", f"{run_avgs['judge_pass_rate']:.0%}")
    m2.metric("Groundedness", f"{dims['groundedness']:.0f}/100")
    m3.metric("Faithfulness", f"{dims['faithfulness']:.0f}/100")
    m4.metric("Answer Relevance", f"{ragas['answer_relevancy']:.0f}/100")
else:
    st.info(
        "No evaluation run yet. Go to **Evaluation Center → Evaluation Runs** and run the suite "
        "to populate judge pass rate, groundedness, faithfulness, and answer relevance.",
        icon=":material/info:",
    )
st.markdown(theme.glass_close(), unsafe_allow_html=True)
