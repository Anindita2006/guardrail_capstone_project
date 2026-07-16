"""Escalations — a ticket-management board over every escalated query, grouped
into Pending Review / Assigned / Resolved lanes.

Streamlit has no true drag-and-drop; each card carries the action that would
otherwise be a drag ("Assign to me", "Mark resolved") as a button instead, which
moves it to the next lane on click.
"""
from __future__ import annotations

import html

import streamlit as st

from src.audit import assign_escalation, list_escalations, mark_reviewed
from ui import theme
from ui.topbar import render_topbar

render_topbar()
theme.page_header(
    "Workspace",
    "Escalations",
    "Every high-stakes or low-confidence query routed to a human, tracked from pending through resolution.",
)

p = theme.get_palette()
escalations = list_escalations()

if not escalations:
    st.info("No escalations yet — nothing has triggered the governance gate so far.", icon=":material/info:")
    st.stop()

lanes = {"pending": [], "assigned": [], "reviewed": []}
for r in escalations:
    lanes.get(r["human_review_status"] or "pending", lanes["pending"]).append(r)

col_pending, col_assigned, col_resolved = st.columns(3)
lane_meta = [
    (col_pending, "pending", "Pending Review"),
    (col_assigned, "assigned", "Assigned"),
    (col_resolved, "reviewed", "Resolved"),
]

for col, key, title in lane_meta:
    with col:
        st.markdown(
            f'<div class="gr-kanban-col-header"><h4>{title}</h4>'
            f'<span class="gr-kanban-count">{len(lanes[key])}</span></div>',
            unsafe_allow_html=True,
        )
        for r in lanes[key]:
            sla_label, sla_tone = theme.sla_status(r["sla_due_at"])
            card_html = (
                f'{theme.glass_open("hoverable")}'
                f'<div style="font-size:.82rem;color:{p["text_muted"]};">{r["timestamp"][:19].replace("T", " ")}</div>'
                f'<div style="font-weight:600;margin:.25rem 0;color:{p["text_primary"]};">{html.escape(r["question_text"][:90])}</div>'
                f'{theme.risk_badge(r["stakes"])} '
                f'{theme.badge(sla_label, sla_tone, sla_tone + "_tint", sla_tone + "_strong")}'
                f'<div style="margin-top:.5rem;">'
                f'<span style="font-size:.78rem;color:{p["text_secondary"]};">Confidence — {r["confidence"] or 0:.2f}</span>'
                f'{theme.meter(r["confidence"] or 0, kind="accent")}'
                f'</div>'
                f'<div style="font-size:.8rem;color:{p["text_secondary"]};margin-top:.4rem;">'
                f'Owner: <strong style="color:{p["text_primary"]};">{r["owner"] or "Unassigned"}</strong>'
                + (f' · Assigned to: <strong style="color:{p["text_primary"]};">{r["assigned_to"]}</strong>' if r.get("assigned_to") else "")
                + '</div>'
                f'{theme.glass_close()}'
            )
            st.markdown(card_html, unsafe_allow_html=True)

            if key == "pending":
                with st.popover("Assign to me", use_container_width=True):
                    assignee = st.text_input("Your name", key=f"assignee_{r['id']}")
                    if st.button("Confirm assignment", key=f"assign_btn_{r['id']}"):
                        if assignee.strip():
                            assign_escalation(r["id"], assignee.strip())
                            st.rerun()
                        else:
                            st.warning("Enter your name first.")
            elif key == "assigned":
                with st.popover("Mark resolved", use_container_width=True):
                    reviewer = st.text_input("Reviewer name", value=r.get("assigned_to") or "", key=f"reviewer_{r['id']}")
                    note = st.text_area("Decision note", key=f"note_{r['id']}", height=80)
                    if st.button("Confirm resolution", key=f"resolve_btn_{r['id']}"):
                        if reviewer.strip():
                            mark_reviewed(r["id"], reviewer.strip(), note.strip())
                            st.rerun()
                        else:
                            st.warning("Enter a reviewer name first.")
            else:
                if r.get("reviewer"):
                    st.caption(f"Resolved by {r['reviewer']}" + (f" — {r['decision_note']}" if r.get("decision_note") else ""))
            st.markdown("<div style='margin-bottom:.6rem;'></div>", unsafe_allow_html=True)
