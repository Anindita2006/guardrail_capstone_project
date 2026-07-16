"""Audit Trail — a professional, filterable, searchable table over every
logged query. Columns: Timestamp, User, Query, Risk, Confidence, Escalated,
Decision. Filters: date range, risk, user, escalated."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from src.audit import list_all_records
from ui import theme
from ui.topbar import render_topbar

render_topbar()
theme.page_header("Workspace", "Audit Trail", "Every query the agent has processed, with full filtering for review and export.")

records = list_all_records()
p = theme.get_palette()

if not records:
    st.info("No queries logged yet.", icon=":material/info:")
    st.stop()

df = pd.DataFrame([
    {
        "id": r["id"],
        "Timestamp": r["timestamp"],
        "User": r["user"],
        "Query": r["question_text"],
        "Risk": (r["stakes"] or "unknown"),
        "Confidence": r["confidence"] or 0.0,
        "Escalated": bool(r["escalated"]),
        "Decision": (r["human_review_status"] or "n/a"),
    }
    for r in records
])
df["_date"] = pd.to_datetime(df["Timestamp"]).dt.date

st.markdown(f'{theme.glass_open()}<strong>Filters</strong>', unsafe_allow_html=True)
f1, f2, f3, f4, f5 = st.columns([1.3, 1, 1.2, 1, 1.5])
with f1:
    min_d, max_d = df["_date"].min(), df["_date"].max()
    date_range = st.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
with f2:
    risk_filter = st.multiselect("Risk", ["low", "medium", "high"], default=[])
with f3:
    user_filter = st.multiselect("User", sorted(df["User"].unique().tolist()), default=[])
with f4:
    escalated_filter = st.selectbox("Escalated", ["Any", "Yes", "No"])
with f5:
    search = st.text_input("Search query text", placeholder="substring match…")
st.markdown(theme.glass_close(), unsafe_allow_html=True)

filtered = df.copy()
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["_date"] >= start) & (filtered["_date"] <= end)]
if risk_filter:
    filtered = filtered[filtered["Risk"].isin(risk_filter)]
if user_filter:
    filtered = filtered[filtered["User"].isin(user_filter)]
if escalated_filter != "Any":
    filtered = filtered[filtered["Escalated"] == (escalated_filter == "Yes")]
if search.strip():
    filtered = filtered[filtered["Query"].str.contains(search, case=False, na=False)]

st.caption(f"{len(filtered)} of {len(df)} records")

display_df = filtered.drop(columns=["id", "_date"]).copy()
display_df["Risk"] = display_df["Risk"].str.upper()
display_df["Decision"] = display_df["Decision"].str.upper()

st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    height=460,
    column_config={
        "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.2f"),
        "Timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
        "Query": st.column_config.TextColumn("Query", width="large"),
    },
)

csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("Export filtered CSV", csv, file_name="guardrail_audit_trail.csv", mime="text/csv", icon=":material/download:")
