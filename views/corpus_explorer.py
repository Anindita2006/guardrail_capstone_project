"""Corpus Explorer — browse and search the underlying policy corpus that the
agent retrieves from, grouped by source document and owner."""
from __future__ import annotations

from collections import defaultdict

import streamlit as st

from src.retrieval import get_index
from ui import theme
from ui.topbar import render_topbar

render_topbar()
theme.page_header("Governance", "Corpus Explorer", "Every policy clause available to the retrieval index, grouped by source document.")

p = theme.get_palette()
clauses = get_index().clauses

f1, f2 = st.columns([2, 1])
with f1:
    query = st.text_input("Search clauses", placeholder="Search by clause ID, title, or text…")
with f2:
    owners = sorted({c.owner for c in clauses})
    owner_filter = st.multiselect("Owner", owners, default=[])

filtered = clauses
if query.strip():
    q = query.strip().lower()
    filtered = [c for c in filtered if q in c.clause_id.lower() or q in c.title.lower() or q in c.text.lower()]
if owner_filter:
    filtered = [c for c in filtered if c.owner in owner_filter]

tiles = "".join([
    theme.kpi_tile("Total Clauses", str(len(clauses)), p["accent"]),
    theme.kpi_tile("Source Documents", str(len({c.doc_id for c in clauses})), p["secondary"]),
    theme.kpi_tile("Control Owners", str(len(owners)), p["success"]),
    theme.kpi_tile("Matching Filter", str(len(filtered)), theme.category_style("filter")["text"]),
])
st.markdown(f'<div class="gr-kpi-row">{tiles}</div>', unsafe_allow_html=True)

by_doc = defaultdict(list)
for c in filtered:
    by_doc[c.source_title].append(c)

if not filtered:
    st.info("No clauses match this filter.", icon=":material/info:")

for source_title, doc_clauses in sorted(by_doc.items()):
    st.markdown(f"#### {source_title}")
    for c in sorted(doc_clauses, key=lambda x: x.clause_id):
        with st.expander(f"{c.clause_id} — {c.title}"):
            st.markdown(
                theme.chip(c.clause_id, category_key=c.clause_id.split("-")[0])
                + theme.chip(c.owner, category_key=c.owner),
                unsafe_allow_html=True,
            )
            st.write(c.text)
