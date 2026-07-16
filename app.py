"""GuardRail Enterprise — Compliance Advisory & Governance Console.

Multi-page Streamlit entry point. Shared chrome (theme CSS, sidebar branding)
renders here on every navigation; the selected page's module then runs via
st.navigation/st.Page.
"""
import streamlit as st

from src.config import OPENAI_API_KEY
from ui.theme import get_palette, icon, inject_base_css

st.set_page_config(
    page_title="GuardRail — Compliance Console",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_base_css()
_p = get_palette()

with st.sidebar:
    st.markdown(
        f"""
        <div class="gr-brand">
            <div class="mark">{icon('shield', 18, color='#06251b', stroke_width=2.4)}</div>
            <div>GuardRail<small>Compliance Console</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not OPENAI_API_KEY:
        st.warning(
            "OPENAI\\_API\\_KEY not set — Ask Compliance and Evaluation runs are "
            "disabled until it's configured in `.env`.",
            icon=":material/key_off:",
        )

dashboard_page = st.Page("views/dashboard.py", title="Dashboard", icon=":material/space_dashboard:", default=True)
ask_page = st.Page("views/ask.py", title="Ask Compliance", icon=":material/forum:")
audit_page = st.Page("views/audit_trail.py", title="Audit Trail", icon=":material/fact_check:")
escalations_page = st.Page("views/escalations.py", title="Escalations", icon=":material/emergency_home:")
eval_page = st.Page("views/evaluation_center.py", title="Evaluation Center", icon=":material/analytics:")
corpus_page = st.Page("views/corpus_explorer.py", title="Corpus Explorer", icon=":material/menu_book:")
settings_page = st.Page("views/settings.py", title="Settings", icon=":material/settings:")

nav = st.navigation(
    {
        "Overview": [dashboard_page],
        "Workspace": [ask_page, audit_page, escalations_page],
        "Governance": [eval_page, corpus_page],
        "System": [settings_page],
    }
)
nav.run()
