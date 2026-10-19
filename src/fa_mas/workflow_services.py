"""Deterministic, three-write workflow conformance study over local HTTP/SQLite.

Cases are authored mechanism tests, not random draws or live agent behavior.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from .local_services import DOMAINS, ServiceState, make_handler, request


FAULTS = ("clean", "lost_reply_after_commit", "lost_reply_before_commit",
          "stale_status_after_commit", "partial_commit", "primary_unavailable",
          "permission_denied", "incompatible_alternate", "compensation_unavailable")
POLICIES = ("static", "stable_retry", "verify_retry", "feature_matched", "fa_mas")


def run_case(base: str, domain: str, fault: str, policy: str) -> dict:
    if domain not in DOMAINS or fault not in FAULTS or policy not in POLICIES:
        raise ValueError("Unknown case")
    scope = DOMAINS[domain]["scope"]
    ids = [f"{domain}-step-{i}" for i in (1, 2, 3)]
    failed = ids[1]
    request(base, "/reset", {"domain": domain, "scenario": fault, "fault_intent": failed})
    reads = 0
    outcome = "failed"

    def invoke(intent: str, target: str = "primary"):
        return request(base, "/invoke", {"intent": intent, "target": target, "scope": scope})

    def reconcile():
        nonlocal reads
        reads += 1
        return request(base, "/status/" + failed)[1]

    first_code, first = invoke(ids[0])
    if first_code != 200 or first["status"] != "committed":
        raise AssertionError("Unfaulted prerequisite did not commit")
    code, response = invoke(failed)
    recovered = code == 200 and response["status"] == "committed"
    if not recovered and code != 403:
        if policy == "stable_retry":
            code, response = invoke(failed)
            recovered = code == 200 and response["status"] == "committed"
        elif policy in {"verify_retry", "feature_matched", "fa_mas"}:
            observation = reconcile()
            if observation["status"] == "unknown" and policy in {"feature_matched", "fa_mas"}:
                observation = reconcile()
            if observation["status"] == "committed":
                recovered = True
            elif observation["status"] == "absent" and observation["authoritative"]:
                code, response = invoke(failed)
                recovered = code == 200 and response["status"] == "committed"
                if not recovered and policy in {"feature_matched", "fa_mas"}:
                    if policy != "fa_mas" or fault != "incompatible_alternate":
                        code, response = invoke(failed, "alternate")
                        recovered = code == 200 and response["status"] == "committed"
            elif observation["status"] == "partial" and policy in {"feature_matched", "fa_mas"}:
                compensation_code, _ = request(base, "/compensate", {"intent": failed})
                if compensation_code == 200:
                    code, response = invoke(failed + "-replacement", "alternate")
                    recovered = code == 200 and response["status"] == "committed"
    if recovered:
        last_code, last = invoke(ids[2])
        if last_code != 200 or last["status"] != "committed":
            raise AssertionError("Unfaulted final step did not commit")
        outcome = "complete"
    elif policy in {"feature_matched", "fa_mas"}:
        # A terminated saga must reverse earlier writes and any partial middle
        # write. The independent ledger judge checks the resulting state.
        state = request(base, "/state")[1]
        for intent in reversed(ids[:2]):
            if any(x["intent"] == intent and x["status"] in {"partial", "committed"}
                   for x in state["intents"]):
                request(base, "/compensate", {"intent": intent})
        outcome = "safe_stop"
    state = request(base, "/state")[1]
    active = [e for e in state["effects"] if e["active"]]
    active_intents = [e["intent"] for e in active]
    unresolved_partial = any(x["status"] == "partial" for x in state["intents"])
    duplicate = len(active_intents) != len(set(active_intents))
    incompatible = fault == "incompatible_alternate" and any(
        e["intent"] == failed and e["target"] == "alternate" for e in active)
    wrong_state = (outcome == "complete" and (len(active) != 3 or ids[0] not in active_intents
                    or ids[2] not in active_intents))
    orphan = outcome != "complete" and bool(active)
    unsafe = duplicate or unresolved_partial or incompatible or wrong_state or orphan
    success = outcome == "complete" and not unsafe
    safe_stop = outcome == "safe_stop" and not unsafe
    return {"evidence_class": "engineered_multistep_http_sqlite_no_llm", "domain": domain,
            "fault": fault, "policy": policy, "task_success": int(success),
            "safe_termination": int(safe_stop), "acceptable_outcome": int(success or safe_stop),
            "unsafe_outcome": int(unsafe), "orphaned_effect": int(orphan),
            "incompatible_effect": int(incompatible), "unresolved_partial": int(unresolved_partial),
            "duplicate_effect": int(duplicate), "denied_attempt": int(any(e["kind"] == "denied" for e in state["events"])),
            "invocations": sum(e["kind"] == "invoke" for e in state["events"]),
            "status_reads": reads, "compensations": sum(e["kind"] == "compensated" for e in state["events"]),
            "trace_sha256": hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest(),
            "ledger": state, "outcome": outcome}


def run_study(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        state = ServiceState(Path(directory) / "workflow.sqlite")
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            rows = [run_case(base, domain, fault, policy) for domain in DOMAINS
                    for fault in FAULTS for policy in POLICIES]
        finally:
            server.shutdown(); server.server_close(); thread.join(); state.db.close()
    (output / "workflow_traces.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    with (output / "workflow_runs.csv").open("w", newline="") as f:
        keys = [k for k in rows[0] if k != "ledger"]
        writer = csv.DictWriter(f, keys); writer.writeheader()
        writer.writerows({k: r[k] for k in keys} for r in rows)
    summary = [{"policy": p, "cases": sum(r["policy"] == p for r in rows),
                **{key: sum(r[key] for r in rows if r["policy"] == p) for key in
                   ("task_success", "safe_termination", "acceptable_outcome", "unsafe_outcome",
                    "orphaned_effect", "incompatible_effect", "denied_attempt", "invocations", "status_reads", "compensations")}}
               for p in POLICIES]
    with (output / "workflow_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, list(summary[0])); writer.writeheader(); writer.writerows(summary)
    manifest = {"evidence_class": "engineered_multistep_http_sqlite_no_llm", "cases_per_policy": len(DOMAINS) * len(FAULTS),
                "runs": len(rows), "domains": list(DOMAINS), "faults": list(FAULTS),
                "policies": list(POLICIES), "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (Path(__file__), Path(__file__).with_name("local_services.py"))},
                "scope": "Three state-changing service calls; one fault at the middle call. Authored cases, descriptive counts."}
    (output / "workflow_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"summary": summary, "manifest": manifest}, indent=2))
    return rows, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/workflow_services"))
    run_study(parser.parse_args().output)
