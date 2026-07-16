"""Evaluation Center — the AI governance evaluation platform: an 8-dimension
trust framework, a RAGAS-equivalent rubric, per-scenario judge verdicts, run
history, and the scenario suite itself. Every score here comes from a real
LLM-judge call recorded in eval_runs/judge_scores — nothing is fabricated; pages
with no run yet say so plainly instead of showing a placeholder number.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from eval.run_eval import run_full_eval
from eval.scenarios import FAIRNESS_SCENARIO, SCENARIOS
from src.config import OPENAI_API_KEY
from src.eval_store import latest_run_averages, list_eval_runs, list_judge_scores
from src.judge import DIMENSIONS, JUDGE_MODEL, JUDGE_SYSTEM_PROMPT, RAGAS_METRICS
from ui import theme
from ui.charts import gauge, radar, time_series
from ui.topbar import render_topbar

render_topbar()
theme.page_header(
    "Governance",
    "Evaluation Center",
    "8-dimension trust framework, RAGAS-equivalent rubric, and per-scenario LLM-judge verdicts.",
)

p = theme.get_palette()
run_avgs = latest_run_averages()
runs = list_eval_runs(limit=30)

# --- Run control --------------------------------------------------------------

ctrl_l, ctrl_r = st.columns([3, 1])
with ctrl_l:
    st.caption(
        "Each run executes the full scenario suite live against the agent, then scores every "
        "answer with a structured LLM-judge call. This costs real API calls and takes roughly "
        "a minute — it is not a mock."
    )
with ctrl_r:
    if st.button("Run New Evaluation", type="primary", disabled=not OPENAI_API_KEY, use_container_width=True):
        with st.spinner("Running scenario suite and judging each response…"):
            run_full_eval()
        st.rerun()
if not OPENAI_API_KEY:
    st.caption("Disabled — OPENAI_API_KEY is not configured.")

st.divider()

# --- 8-dimension trust framework ----------------------------------------------

st.markdown("#### 8-Dimension Trust Framework")

if run_avgs:
    dims = run_avgs["dimensions"]
    trust_score = sum(dims.values()) / len(dims)

    col_gauge, col_radar = st.columns([1, 1.6])
    with col_gauge:
        st.plotly_chart(gauge(trust_score, title="Overall Trust Score", color_key="accent"), use_container_width=True, config={"displayModeBar": False})
        st.caption(f"From run `{run_avgs['run']['run_id']}` · {run_avgs['n_scored']} scenario(s) judged")
    with col_radar:
        labels = [d.replace("_", " ").title() for d in DIMENSIONS]
        st.plotly_chart(
            radar(labels, [dims[d] for d in DIMENSIONS], name="Dimensions", color_key="accent"),
            use_container_width=True, config={"displayModeBar": False},
        )

    score_tiles = "".join(
        theme.kpi_tile(d.replace("_", " ").title(), f"{dims[d]:.0f}", theme.category_style(d)["text"])
        for d in DIMENSIONS
    )
    st.markdown(f'<div class="gr-kpi-row">{score_tiles}</div>', unsafe_allow_html=True)

    if len(runs) > 1:
        history = sorted(runs, key=lambda r: r["timestamp"])
        trust_history = []
        for run in history:
            scores = list_judge_scores(run_id=run["run_id"])
            if scores:
                trust_history.append(sum(s["trust_score"] for s in scores) / len(scores))
            else:
                trust_history.append(run["avg_trust_score"] or 0)
        st.markdown("**Trend History**")
        st.plotly_chart(
            time_series([r["timestamp"][:16].replace("T", " ") for r in history], trust_history, name="Trust score", color_key="accent"),
            use_container_width=True, config={"displayModeBar": False},
        )
else:
    st.info("No evaluation run yet. Click **Run New Evaluation** above to populate the trust framework.", icon=":material/info:")

st.divider()

tab_ragas, tab_judge, tab_runs, tab_scenarios = st.tabs(
    ["RAGAS Metrics", "LLM Judge", "Evaluation Runs", "Scenario Testing"]
)

# --- RAGAS Metrics -------------------------------------------------------------

with tab_ragas:
    st.caption(
        "These are **not** output from the `ragas` Python package — there is no separate "
        "embeddings/ground-truth pipeline here. They're the same eight RAGAS metric names, "
        "scored by a single structured LLM-judge rubric call. Treat as an LLM-judged "
        "approximation, not literal RAGAS package output."
    )
    if run_avgs:
        ragas = run_avgs["ragas"]
        labels = [m.replace("_", " ").title() for m in RAGAS_METRICS]
        st.plotly_chart(
            radar(labels, [ragas[m] for m in RAGAS_METRICS], name="RAGAS", color_key="secondary"),
            use_container_width=True, config={"displayModeBar": False},
        )
        tiles = "".join(
            theme.kpi_tile(m.replace("_", " ").title(), f"{ragas[m]:.0f}", theme.category_style(m)["text"])
            for m in RAGAS_METRICS
        )
        st.markdown(f'<div class="gr-kpi-row">{tiles}</div>', unsafe_allow_html=True)
    else:
        st.info("No evaluation run yet.", icon=":material/info:")

# --- LLM Judge -------------------------------------------------------------

with tab_judge:
    st.markdown(f"**Judge Model:** `{JUDGE_MODEL}`")
    with st.expander("Judge Prompt (system instructions given to the judge)"):
        st.code(JUDGE_SYSTEM_PROMPT, language="text")

    scores = list_judge_scores(limit=25)
    if not scores:
        st.info("No judged responses yet.", icon=":material/info:")
    else:
        st.markdown("**Recent Judgments**")
        for s in scores:
            with st.expander(f"{s['scenario_name']} — {s['verdict']} · trust {s['trust_score']}/100"):
                st.markdown(theme.verdict_badge(s["verdict"]), unsafe_allow_html=True)
                st.caption(s["timestamp"][:19].replace("T", " "))
                st.write(s["explanation"] or "_No explanation recorded._")
                st.caption(f"Question: {s['question_text']}")

# --- Evaluation Runs -------------------------------------------------------

with tab_runs:
    if not runs:
        st.info("No evaluation runs recorded yet.", icon=":material/info:")
    else:
        df = pd.DataFrame([
            {
                "Run ID": r["run_id"],
                "Dataset": r["dataset"],
                "Timestamp": r["timestamp"][:19].replace("T", " "),
                "Pass Rate": r["pass_rate"],
                "Avg Trust Score": r["avg_trust_score"] if r["avg_trust_score"] is not None else float("nan"),
            }
            for r in runs
        ])
        st.dataframe(
            df, hide_index=True, use_container_width=True,
            column_config={
                "Pass Rate": st.column_config.ProgressColumn("Pass Rate", min_value=0, max_value=1),
                "Avg Trust Score": st.column_config.NumberColumn("Avg Trust Score", format="%.1f"),
            },
        )

# --- Scenario Testing -------------------------------------------------------

with tab_scenarios:
    st.caption("The fixed scenario suite executed on every evaluation run.")
    latest_by_name = {}
    for s in list_judge_scores(limit=200):
        latest_by_name.setdefault(s["scenario_name"], s)

    all_scenarios = list(SCENARIOS) + [
        {"name": FAIRNESS_SCENARIO["name"], "category": FAIRNESS_SCENARIO["category"], "question": FAIRNESS_SCENARIO["question_a"]}
    ]
    for sc in all_scenarios:
        latest = latest_by_name.get(sc["name"])
        with st.expander(sc["name"]):
            st.markdown(theme.chip(sc["category"], category_key=sc["category"]), unsafe_allow_html=True)
            st.write(sc["question"])
            if latest:
                st.markdown(
                    theme.verdict_badge(latest["verdict"]) + f' <span style="color:{p["text_secondary"]};font-size:.82rem;"> trust {latest["trust_score"]}/100 · last judged {latest["timestamp"][:19].replace("T", " ")}</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Not yet judged in any recorded run.")
