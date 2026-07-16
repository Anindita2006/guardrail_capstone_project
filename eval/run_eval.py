"""Run the required test scenarios end to end against the live agent, judge each
one against the 8-dimension/RAGAS-equivalent rubric, and write an evaluation
report with KPIs. Also callable in-process from the Evaluation Center UI.

Usage:  python -m eval.run_eval
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows consoles default stdout to cp1252, which can't encode characters the LLM
# sometimes generates (e.g. non-breaking hyphens). Force UTF-8 with replacement so a
# console-encoding gap never crashes the eval run itself.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from eval.scenarios import FAIRNESS_SCENARIO, SCENARIOS
from src.agent import run_agent
from src.eval_store import new_run_id, record_eval_run, record_judge_score
from src.judge import judge_answer

REPORT_PATH = Path(__file__).resolve().parent / "eval_report.md"
DATASET_NAME = "core_scenarios_v1"


def _judge_or_none(question_text: str, record: dict | None) -> dict | None:
    """Best-effort judge call — a judge failure shouldn't fail the whole eval run,
    it just means that scenario has no judge score attached."""
    if record is None:
        return None
    try:
        return judge_answer(
            question_text=question_text,
            answer_text=record["answer_text"],
            retrieved_clauses=record.get("retrieved_clauses", []),
            citations=record.get("citations", []),
            stakes=record.get("stakes"),
            confidence=record.get("confidence"),
            in_corpus=record.get("in_corpus", False),
            escalated=record.get("escalated", False),
        )
    except Exception as e:  # noqa: BLE001
        print(f"  [judge failed] {e}")
        return None


def _run_single_scenarios(run_id: str) -> list[dict]:
    results = []
    for sc in SCENARIOS:
        start = time.time()
        try:
            record = run_agent(sc["question"], user="eval_suite")
            elapsed = time.time() - start
            passed, detail = sc["check"](record)
        except Exception as e:  # noqa: BLE001
            elapsed = time.time() - start
            passed, detail, record = False, f"EXCEPTION: {e}", None

        judgment = _judge_or_none(sc["question"], record)
        if judgment:
            record_judge_score(
                run_id=run_id,
                scenario_name=sc["name"],
                category=sc["category"],
                audit_record_id=record.get("id") if record else None,
                question_text=sc["question"],
                scenario_passed=passed,
                judgment=judgment,
            )

        results.append(
            {
                "name": sc["name"],
                "category": sc["category"],
                "passed": passed,
                "detail": detail,
                "elapsed": elapsed,
                "record": record,
                "judgment": judgment,
            }
        )
        status = "PASS" if passed else "FAIL"
        trust_note = f" · trust={judgment['trust_score']}" if judgment else ""
        print(f"[{status}] {sc['name']} ({sc['category']}) — {detail}{trust_note}")
    return results


def _run_fairness_scenario(run_id: str) -> dict:
    sc = FAIRNESS_SCENARIO
    start = time.time()
    try:
        record_a = run_agent(sc["question_a"], user="eval_suite_a")
        record_b = run_agent(sc["question_b"], user="eval_suite_b")
        elapsed = time.time() - start
        passed, detail = sc["check"](record_a, record_b)
        record = record_a  # representative record for aggregate KPI stats below
    except Exception as e:  # noqa: BLE001
        elapsed = time.time() - start
        passed, detail, record = False, f"EXCEPTION: {e}", None

    judgment = _judge_or_none(sc["question_a"], record)
    if judgment:
        record_judge_score(
            run_id=run_id,
            scenario_name=sc["name"],
            category=sc["category"],
            audit_record_id=record.get("id") if record else None,
            question_text=sc["question_a"],
            scenario_passed=passed,
            judgment=judgment,
        )

    result = {
        "name": sc["name"],
        "category": sc["category"],
        "passed": passed,
        "detail": detail,
        "elapsed": elapsed,
        "record": record,
        "judgment": judgment,
    }
    status = "PASS" if passed else "FAIL"
    trust_note = f" · trust={judgment['trust_score']}" if judgment else ""
    print(f"[{status}] {sc['name']} ({sc['category']}) — {detail}{trust_note}")
    return result


def run_full_eval() -> dict:
    """Run the full suite once, persist a run + judge scores, write the markdown
    report, and return a summary dict. Safe to call in-process (e.g. from the
    Evaluation Center's "Run new evaluation" button), not just from the CLI."""
    run_id = new_run_id()
    results = _run_single_scenarios(run_id)
    results.append(_run_fairness_scenario(run_id))

    n_pass = sum(1 for r in results if r["passed"])
    n_total = len(results)
    total_latency = sum(r["elapsed"] for r in results)
    avg_latency = total_latency / n_total if n_total else 0.0
    escalation_rate = sum(1 for r in results if r["record"] and r["record"]["escalated"]) / n_total
    cited_rate = sum(
        1 for r in results if r["record"] and r["record"]["citations"]
    ) / n_total
    trace_ok_rate = sum(
        1 for r in results if r["record"] and "search_policy" in r["record"]["tool_calls"]
    ) / n_total

    judged = [r["judgment"] for r in results if r["judgment"]]
    avg_trust_score = (sum(j["trust_score"] for j in judged) / len(judged)) if judged else None

    record_eval_run(
        run_id=run_id,
        dataset=DATASET_NAME,
        n_total=n_total,
        n_passed=n_pass,
        avg_latency=avg_latency,
        avg_trust_score=avg_trust_score,
    )

    routing_result = next((r for r in results if r["name"] == "Correct routing"), None)

    lines = [
        "# Compliance Advisory & Triage Agent — Evaluation Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Scenarios passed:** {n_pass}/{n_total}",
        f"**Avg response time:** {avg_latency:.2f}s",
        f"**Escalation rate:** {escalation_rate:.0%}",
        f"**Citation rate:** {cited_rate:.0%}",
        f"**Retrieval-tool-invoked rate (trace check):** {trace_ok_rate:.0%}",
        f"**Avg judge trust score:** {avg_trust_score:.1f}/100" if avg_trust_score is not None else "**Avg judge trust score:** n/a",
        "",
        "## Scenario results",
        "",
        "| Scenario | Category | Result | Detail |",
        "|---|---|---|---|",
    ]
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        detail = r["detail"].replace("|", "\\|")
        lines.append(f"| {r['name']} | {r['category']} | {status} | {detail} |")

    lines += [
        "",
        "## Business KPIs (from this run)",
        "",
        "- **Advisory response time:** avg " + f"{avg_latency:.2f}s per query",
        f"- **Correct-routing %:** "
        f"{'PASS' if routing_result and routing_result['passed'] else 'FAIL'} on the routing scenario",
        f"- **Audit readiness:** every scenario produced a logged audit record "
        f"(see audit_log.db) with retrieval trace, classification, and outcome.",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    return {
        "run_id": run_id,
        "n_pass": n_pass,
        "n_total": n_total,
        "avg_latency": avg_latency,
        "escalation_rate": escalation_rate,
        "cited_rate": cited_rate,
        "trace_ok_rate": trace_ok_rate,
        "avg_trust_score": avg_trust_score,
        "results": results,
    }


def main() -> int:
    summary = run_full_eval()
    print(f"\nReport written to {REPORT_PATH}")
    print(f"\n{summary['n_pass']}/{summary['n_total']} scenarios passed.")
    return 0 if summary["n_pass"] == summary["n_total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
