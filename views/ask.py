"""Ask Compliance — split layout: query input on the left, AI response
(answer, confidence, risk, escalation, owner, sources, retrieved chunks,
reasoning trace) on the right.

Category/Priority are user-supplied triage hints for their own organization —
they do not feed the model or influence its classification. The system-assessed
risk level (stakes) always comes from the governance gate, never from the user.
"""
from __future__ import annotations

import html

import streamlit as st

from src.agent import run_agent
from src.config import OPENAI_API_KEY
from ui import theme
from ui.topbar import render_topbar

render_topbar()
theme.page_header(
    "Workspace",
    "Ask Compliance",
    "Cited answers over the policy corpus, with a full retrieval and governance trace.",
)

if "gr_ask_result" not in st.session_state:
    st.session_state.gr_ask_result = None

p = theme.get_palette()
col_query, col_result = st.columns([1, 1.4])

with col_query:
    st.markdown(f'{theme.glass_open()}<strong>Query</strong>', unsafe_allow_html=True)
    user = st.text_input("Your name / employee ID", value="employee_demo")
    category = st.selectbox(
        "Category (your triage hint)",
        ["General", "Data Privacy", "AML / Sanctions", "Licensing", "HR & Employment", "Other"],
    )
    priority = st.select_slider("Priority (your triage hint)", ["Low", "Normal", "High", "Urgent"], value="Normal")
    question = st.text_area(
        "Compliance question",
        placeholder="e.g. Can we store EU customer data in our US-East region?",
        height=130,
    )
    ask = st.button(
        "Ask GuardRail", type="primary",
        disabled=not question.strip() or not OPENAI_API_KEY,
        use_container_width=True,
    )
    if not OPENAI_API_KEY:
        st.caption("Disabled — OPENAI_API_KEY is not configured.")
    st.markdown(theme.glass_close(), unsafe_allow_html=True)

with col_result:
    st.markdown("**Response**")
    skeleton_slot = st.empty()

    if ask and question.strip():
        with skeleton_slot.container():
            st.markdown(
                f"""
                <div class="gr-glass gr-card">
                    <div class="gr-skeleton" style="height:16px;width:55%;margin-bottom:12px;"></div>
                    <div class="gr-skeleton" style="height:12px;width:95%;margin-bottom:8px;"></div>
                    <div class="gr-skeleton" style="height:12px;width:88%;margin-bottom:8px;"></div>
                    <div class="gr-skeleton" style="height:12px;width:70%;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        try:
            record = run_agent(question.strip(), user=user or "anonymous")
        except Exception as e:  # noqa: BLE001
            st.session_state.gr_ask_result = None
            skeleton_slot.empty()
            st.error(f"Agent run failed: {e}")
        else:
            record["_category_hint"] = category
            record["_priority_hint"] = priority
            st.session_state.gr_ask_result = record
            skeleton_slot.empty()

    record = st.session_state.gr_ask_result
    if record:
        st.markdown(
            f'{theme.glass_open()}'
            f'<div style="font-size:.95rem;line-height:1.55;color:{p["text_primary"]};">{record["answer_text"]}</div>'
            f'{theme.glass_close()}',
            unsafe_allow_html=True,
        )

        badges = (
            theme.risk_badge(record["stakes"])
            + " " + theme.status_badge(record["human_review_status"])
            + " " + theme.chip(record.get("_category_hint", "General"), category_key=record.get("_category_hint", "General"))
            + " " + theme.chip(f'Priority: {record.get("_priority_hint", "Normal")}', category_key=record.get("_priority_hint", "Normal"))
        )
        st.markdown(badges, unsafe_allow_html=True)

        m1, m2 = st.columns(2)
        with m1:
            st.markdown(
                f'<div style="font-size:.8rem;color:{p["text_secondary"]};margin-top:.6rem;">Confidence Score — {record["confidence"]:.2f}</div>'
                + theme.meter(record["confidence"], kind="accent"),
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f'<div style="font-size:.8rem;color:{p["text_secondary"]};margin-top:.6rem;">Control Owner</div>'
                f'<div style="font-weight:600;color:{p["text_primary"]};">{record["owner"]}</div>',
                unsafe_allow_html=True,
            )

        if record["escalated"]:
            st.warning(f"Escalated to **{record['escalated_to']}** — {record['escalation_reason']}", icon=":material/priority_high:")
        else:
            st.success("Answered directly — low-stakes, clearly covered by policy.", icon=":material/check_circle:")

        if record["injection_flagged"]:
            st.info(
                "The query contained language resembling an attempt to override policy "
                "guidance. It was treated as untrusted input.",
                icon=":material/shield_moon:",
            )

        # --- Sources (cited clauses only) ---
        if record["citations"]:
            st.markdown("##### Sources")
            by_id = {c["clause_id"]: c for c in record["retrieved_clauses"]}
            for cid in record["citations"]:
                c = by_id.get(cid)
                with st.expander(f"{cid} — {c['title'] if c else 'cited clause'}"):
                    if c:
                        st.markdown(theme.meter(c["score"], kind="secondary"), unsafe_allow_html=True)
                        st.caption(f"Match score {c['score']:.3f} · {c['source_title']} · owner: {c['owner']}")
                        st.write(c["text"])
                    else:
                        st.caption("Clause text not found in this run's retrieval trace.")

        # --- Retrieved chunks (everything retrieved, cited or not) ---
        with st.expander(f"Retrieved Chunks ({len(record['retrieved_clauses'])})"):
            if not record["retrieved_clauses"]:
                st.caption("No clauses retrieved.")
            for c in record["retrieved_clauses"]:
                cited = c["clause_id"] in record["citations"]
                st.markdown(
                    theme.chip(c["clause_id"], category_key=c["clause_id"].split("-")[0])
                    + (theme.chip("cited", category_key="cited-flag") if cited else "")
                    + f'<strong style="margin-left:.3rem;">{html.escape(c["title"])}</strong>',
                    unsafe_allow_html=True,
                )
                st.markdown(theme.meter(c["score"], kind="secondary"), unsafe_allow_html=True)
                st.caption(c["text"][:220] + ("..." if len(c["text"]) > 220 else ""))

        # --- Reasoning trace (collapsible timeline) ---
        with st.expander("Reasoning Trace"):
            st.caption(f"{record['agent_turns']} agent turn(s) · {len(record['tool_calls'])} tool call(s)")
            secondary = p["text_secondary"]
            retrieved_so_far = 0
            timeline_html = []
            for i, call in enumerate(record["tool_calls"], start=1):
                if call == "search_policy":
                    retrieved_so_far += 1
                    detail = f"Queried the policy corpus (retrieval pass #{retrieved_so_far})."
                    label = f"<strong>Step {i} — search_policy</strong><br><span style='color:{secondary};font-size:.85rem;'>{detail}</span>"
                elif call == "submit_answer":
                    detail = "Model submitted its structured answer for governance review."
                    label = f"<strong>Step {i} — submit_answer</strong><br><span style='color:{secondary};font-size:.85rem;'>{detail}</span>"
                else:
                    label = f"<strong>Step {i} — {call}</strong>"
                timeline_html.append(f'<div class="gr-timeline-item"><span class="dot"></span>{label}</div>')
            st.markdown("".join(timeline_html), unsafe_allow_html=True)
    else:
        st.caption("Ask a question to see the governed response here.")
