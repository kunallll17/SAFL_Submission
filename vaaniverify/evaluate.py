"""Reproducible policy simulation, explicitly not a live-model or human study."""

import argparse
import csv
import hashlib
import json
import platform
import statistics
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .capabilities import SecurityError
from .compiler import TEMPLATE_HASH, digest
from .gateway import Gateway
from .kernel import Kernel
from .models import Action, Approval, DIRECTIONS, Intent, ProposalInput
from .scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ["unguarded", "operation_only", "strict_external_block", "without_execution_binding", "vaaniverify"]


def full_trial(case, kernel, gateway, binding=True):
    selected = kernel.create_intent(Intent.model_validate(case["intent"]))
    proposal = kernel.propose(ProposalInput(intent_id=selected["intent_id"], action=Action.model_validate(case["action"]),
                                           external_text=case["external_text"], agent_message=case["agent_message"]))
    if proposal["status"] == "BLOCKED":
        return False, proposal["decision"]["reason"]
    action = Action.model_validate(case["action"])
    proof = Approval(direction=case.get("direction_answer", DIRECTIONS[action.operation]),
                     recipient_answer=action.recipient or action.mandate_id or "",
                     amount_answer_paise=action.amount_paise or 0,
                     action_digest=proposal["confirmation"]["action_digest"], terms_accepted=True)
    try:
        approved = kernel.approve(proposal["proposal_id"], proof)
        if binding:
            gateway.execute(Action.model_validate(case.get("execution_action", case["action"])), approved["token"])
        return True, "EXECUTED" if binding else "SIMULATED_EXECUTION_NO_BINDING"
    except SecurityError as exc:
        return False, exc.code


def run_evaluation(output_dir: Path | None = None):
    started = time.perf_counter()
    rows = []
    scratch = ROOT / "tmp"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="evaluation-", dir=scratch) as directory:
        kernel = Kernel()
        gateway = Gateway(kernel.signing_key.public_key(), Path(directory) / "ledger.db")
        for case in SCENARIOS:
            for policy in POLICIES:
                tick = time.perf_counter_ns()
                if policy == "unguarded":
                    executed, reason = True, "SIMULATED_GENERIC_APPROVAL"
                elif policy == "operation_only":
                    executed = case["intent"]["operation"] == case["action"]["operation"]
                    reason = "SIMULATED_EXECUTION" if executed else "OPERATION_BOUND"
                elif policy == "strict_external_block":
                    executed = not case["external_parameters"]
                    reason = "SIMULATED_EXECUTION" if executed else "EXTERNAL_SOURCE_REJECTED"
                else:
                    executed, reason = full_trial(case, kernel, gateway, binding=policy == "vaaniverify")
                elapsed = (time.perf_counter_ns() - tick) / 1_000_000
                rows.append({"scenario_id": case["id"], "kind": case["kind"], "language": case["language"],
                             "family": case["family"], "policy": policy, "executed": executed,
                             "reason": reason, "elapsed_ms": round(elapsed, 4)})
    summary = []
    for policy in POLICIES:
        selected = [r for r in rows if r["policy"] == policy]
        attacks = [r for r in selected if r["kind"] == "attack"]
        benign = [r for r in selected if r["kind"] == "benign"]
        summary.append({"policy": policy, "attack_count": len(attacks), "attack_executions": sum(r["executed"] for r in attacks),
                        "benign_count": len(benign), "benign_blocked": sum(not r["executed"] for r in benign),
                        "benign_executions": sum(r["executed"] for r in benign)})
    latencies = sorted(r["elapsed_ms"] for r in rows if r["policy"] == "vaaniverify")
    languages = {}
    for language in ("en", "hi", "hinglish", "ta"):
        subset = [r for r in rows if r["language"] == language and r["policy"] == "vaaniverify"]
        languages[language] = {"cases": len(subset), "attack_executions": sum(r["executed"] and r["kind"] == "attack" for r in subset),
                               "benign_blocked": sum(not r["executed"] and r["kind"] == "benign" for r in subset)}
    source_hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((ROOT / "vaaniverify").glob("*.py"))}
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "suite": "synthetic-policy-v1",
              "evidence_type": "Authored synthetic tool-call and modeled-approval simulation. No live LLM or human participants.",
              "case_count": len(SCENARIOS), "independent_semantic_templates": 20, "language_variants_per_template": 4,
              "corpus_sha256": digest(SCENARIOS), "template_sha256": TEMPLATE_HASH,
              "runtime": {"python": platform.python_version(), "platform": platform.platform()},
              "source_sha256": source_hashes, "summary": summary, "by_language": languages,
              "full_pipeline_latency_ms": {"p50": round(statistics.median(latencies), 4),
                                           "p95": latencies[int(len(latencies) * .95) - 1],
                                           "scope": "In-process intent creation, policy, compilation, modeled approval, signing, verification and SQLite mock execution; blocked cases exit early. Excludes UI, human, network and model latency."},
              "duration_seconds": round(time.perf_counter() - started, 3), "rows": rows,
              "limitations": ["Not a measured LLM prompt-injection success rate.", "Matched translations are not independent attacks.",
                              "Approval choices are fixtures, not measured comprehension.", "Author-designed corpus; no held-out adversary or production DPI testing."]}
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "benchmark.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / "scenarios.json").write_text(json.dumps(SCENARIOS, ensure_ascii=False, indent=2), encoding="utf-8")
        with (output_dir / "benchmark.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence")
    args = parser.parse_args()
    report = run_evaluation(args.output)
    print(report["evidence_type"])
    print(f"Cases: {report['case_count']} (20 semantic templates x 4 languages)")
    print(f"{'Policy':30} {'Attack executions':>18} {'Benign blocked':>16}")
    for row in report["summary"]:
        print(f"{row['policy']:30} {row['attack_executions']:>12}/{row['attack_count']:<5} {row['benign_blocked']:>10}/{row['benign_count']}")
    print(f"Evidence written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
