"""OpenAI tool (function) schemas for the compliance agent's ReAct loop."""

SEARCH_POLICY_TOOL = {
    "type": "function",
    "function": {
        "name": "search_policy",
        "description": (
            "Search the compliance policy corpus for clauses relevant to a query. "
            "You must call this at least once before answering — never answer from "
            "memory. Call it again with a refined query if the first results don't "
            "clearly cover the question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'cross-border EU customer data storage'.",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of clauses to retrieve (default 4).",
                    "default": 4,
                },
            },
            "required": ["query"],
        },
    },
}

SUBMIT_ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_answer",
        "description": (
            "Submit your final structured answer once you have searched the policy "
            "corpus. This ends the turn — call it exactly once, after you are done "
            "searching."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "answer_text": {
                    "type": "string",
                    "description": (
                        "The answer to give the employee. If in_corpus is true, it must "
                        "be grounded only in the retrieved clauses and reference them "
                        "inline (e.g. 'per PRIV-3'). If in_corpus is false, briefly "
                        "explain what you found and that it doesn't clearly cover the "
                        "question — do not invent a rule."
                    ),
                },
                "citations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Clause IDs actually returned by search_policy that support the "
                        "answer, e.g. ['PRIV-3', 'PRIV-2']. Empty if in_corpus is false."
                    ),
                },
                "topic": {
                    "type": "string",
                    "description": "Short topic label, e.g. 'cross-border data transfer'.",
                },
                "owner": {
                    "type": "string",
                    "enum": [
                        "Data Protection Officer",
                        "AML Officer",
                        "Legal (Licensing Counsel)",
                        "Compliance Team",
                    ],
                    "description": "The control owner best suited to handle this topic.",
                },
                "stakes": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": (
                        "low = routine, clearly-covered, no real risk if answered directly. "
                        "medium = covered but has judgment calls or partial ambiguity. "
                        "high = cross-border data, sanctions/AML, licensing, or anything "
                        "implying permission for a regulated action."
                    ),
                },
                "confidence": {
                    "type": "number",
                    "description": "Your confidence in this answer, 0.0 to 1.0.",
                },
                "in_corpus": {
                    "type": "boolean",
                    "description": (
                        "True only if the retrieved clauses clearly and directly answer "
                        "the question. False if you had to guess, extrapolate, or the "
                        "corpus is silent on this."
                    ),
                },
            },
            "required": [
                "answer_text",
                "citations",
                "topic",
                "owner",
                "stakes",
                "confidence",
                "in_corpus",
            ],
        },
    },
}

TOOLS = [SEARCH_POLICY_TOOL, SUBMIT_ANSWER_TOOL]
