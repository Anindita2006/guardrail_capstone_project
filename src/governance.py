"""Deterministic governance gate.

This is intentionally NOT another LLM call. Escalation, citation validity, and
refusal-on-out-of-scope are safety-critical, so they are enforced in plain code
against the model's structured output rather than trusted from the model directly.
The agent may *recommend* a stakes level and an answer; this gate has the final say
on whether it ships as-is or gets escalated.
"""
from __future__ import annotations

import re

from src.config import ALLOWED_OWNERS, ALLOWED_STAKES, CONFIDENCE_ESCALATION_THRESHOLD, COVERAGE_SCORE_THRESHOLD

INJECTION_PATTERNS = [
    r"\bignore (the )?(policy|rules?|instructions?|checks?)\b",
    r"\bskip (the )?(checks?|review|approval)\b",
    r"\bapprove regardless\b",
    r"\bconfirm we can (just )?",
    r"\bthe manager said so\b",
    r"\bdisregard (the )?(policy|rules?)\b",
    r"\bpretend (that )?",
    r"\bact as (if|though)\b",
]

REFUSAL_TEMPLATE = (
    "I don't have a policy clause in the compliance corpus that clearly covers this "
    "question, so I'm not going to guess at an answer. I've routed this to {owner} "
    "for a human to review and respond directly. Please don't take action based on "
    "this preliminary note."
)

ESCALATION_DISCLAIMER = (
    "\n\n**This response has been escalated to {owner} for human review "
    "({stakes} stakes). Do not proceed based on this preliminary answer alone.**"
)


def detect_injection(question_text: str) -> bool:
    text = question_text.lower()
    return any(re.search(p, text) for p in INJECTION_PATTERNS)


def apply_gate(
    question_text: str,
    model_output: dict,
    retrieved_clause_ids: set[str],
    max_retrieval_score: float,
) -> dict:
    """Take the agent's proposed structured output and enforce governance rules.

    Returns the final record ready to display and audit-log.
    """
    citations = [c for c in (model_output.get("citations") or []) if c]
    valid_citations = [c for c in citations if c in retrieved_clause_ids]
    citation_valid = len(citations) > 0 and len(valid_citations) == len(citations)

    corpus_covered = max_retrieval_score >= COVERAGE_SCORE_THRESHOLD
    model_claims_in_corpus = bool(model_output.get("in_corpus", False))

    final_in_corpus = (
        model_claims_in_corpus and citation_valid and corpus_covered and len(valid_citations) > 0
    )

    owner = model_output.get("owner", "Compliance Team")
    owner_uncertain = owner not in ALLOWED_OWNERS
    if owner_uncertain:
        owner = "Compliance Team"

    stakes = model_output.get("stakes", "medium")
    if stakes not in ALLOWED_STAKES:
        stakes = "medium"  # fail safe: unrecognized stakes defaults to escalation

    try:
        confidence = float(model_output.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    injection_flagged = detect_injection(question_text)

    reasons = []
    if not final_in_corpus:
        reasons.append("not clearly covered by the policy corpus")
    if stakes in ("medium", "high"):
        reasons.append(f"{stakes}-stakes topic")
    if confidence < CONFIDENCE_ESCALATION_THRESHOLD:
        reasons.append(f"low confidence ({confidence:.2f})")
    if not citation_valid and citations:
        reasons.append("proposed citation(s) not found in retrieved sources")
    if owner_uncertain:
        reasons.append("control owner routing uncertain")
    if injection_flagged:
        reasons.append("possible instruction-override attempt detected in the query")

    escalate = len(reasons) > 0

    if final_in_corpus:
        answer_text = model_output.get("answer_text", "").strip()
    else:
        answer_text = REFUSAL_TEMPLATE.format(owner=owner)
        valid_citations = []

    if escalate:
        answer_text += ESCALATION_DISCLAIMER.format(owner=owner, stakes=stakes)

    return {
        "question_text": question_text,
        "topic": model_output.get("topic", "unclassified"),
        "owner": owner,
        "stakes": stakes,
        "confidence": confidence,
        "answer_text": answer_text,
        "citations": valid_citations,
        "in_corpus": final_in_corpus,
        "escalated": escalate,
        "escalation_reason": "; ".join(reasons) if reasons else None,
        "escalated_to": owner if escalate else None,
        "human_review_status": "pending" if escalate else "n/a",
        "injection_flagged": injection_flagged,
    }
