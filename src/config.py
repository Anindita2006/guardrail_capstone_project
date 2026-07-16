"""Central config: env loading, thresholds, and allowed control owners."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
# Optional: point the OpenAI SDK at an OpenAI-compatible endpoint instead (e.g. Groq's
# free tier at https://api.groq.com/openai/v1). Leave unset to use OpenAI directly.
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL") or None

# Governance thresholds — enforced in code, not left to the model.
CONFIDENCE_ESCALATION_THRESHOLD = 0.6
# Top embedding cosine-similarity score below this = "not in corpus". Calibrated
# empirically against all-MiniLM-L6-v2: genuinely uncovered queries top out around
# 0.28-0.30 (weak semantic overlap, e.g. "gym membership" vs "reimbursement" clauses);
# genuinely covered queries start around 0.56+. 0.40 sits in the gap with margin
# both ways.
COVERAGE_SCORE_THRESHOLD = 0.40
MAX_AGENT_TURNS = 6  # bound the ReAct loop so it can't run away

ALLOWED_OWNERS = {
    "Data Protection Officer",
    "AML Officer",
    "Legal (Licensing Counsel)",
    "Compliance Team",  # catch-all / fallback for uncertain routing
}

ALLOWED_STAKES = {"low", "medium", "high"}

DB_PATH = Path(__file__).resolve().parent.parent / "audit_log.db"

# Escalation SLA policy — hours to human review before a ticket is "overdue".
HIGH_STAKES_SLA_HOURS = 24
MEDIUM_STAKES_SLA_HOURS = 72

# Cosmetic/operational only — never gates behavior, just labels the environment
# badge in the UI so a screenshot/demo doesn't get mistaken for production.
ENVIRONMENT = os.environ.get("GUARDRAIL_ENV", "Development")
