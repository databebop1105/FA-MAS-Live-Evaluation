"""HTTP and SQLite fault-injection study for stateful service recovery.

This is an engineered service test, not a live-model experiment. Faults and
policies are deterministic, so a case is a conformance example, not a sample
from a population of provider behavior.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DOMAINS = {
    "refund": {"primary": "issue_refund", "alternate": "issue_refund_backup", "scope": "refund:write"},
    "travel": {"primary": "reserve_room", "alternate": "reserve_room_backup", "scope": "booking:write"},
    "incident": {"primary": "apply_rollback", "alternate": "apply_rollback_backup", "scope": "ops:write"},
}
SCENARIOS = (
    "lost_reply_after_commit", "lost_reply_before_commit", "stale_status_after_commit",
    "partial_commit", "primary_unavailable", "permission_denied",
)
POLICIES = ("static", "retry", "verify_before_retry", "fa_mas")


class ServiceState:
    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.execute("CREATE TABLE intents(intent TEXT PRIMARY KEY, domain TEXT, status TEXT, target TEXT)")
        self.db.execute("CREATE TABLE effects(id INTEGER PRIMARY KEY, intent TEXT, target TEXT, active INTEGER)")
        self.db.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY, kind TEXT, intent TEXT, detail TEXT)")
        self.db.commit()
        self.scenario = ""
        self.domain = ""
        self.invocations = 0
        self.status_reads = 0
        self.auth_scope = ""
        self.fault_intent = None

    def log(self, kind: str, intent: str, detail: str = "") -> None:
        self.db.execute("INSERT INTO events(kind,intent,detail) VALUES (?,?,?)", (kind, intent, detail))

    def reset(self, domain: str, scenario: str, fault_intent: str | None = None) -> dict:
        with self.lock, self.db:
            for table in ("intents", "effects", "events"):
                self.db.execute(f"DELETE FROM {table}")
            self.scenario, self.domain = scenario, domain
            self.fault_intent = fault_intent
            self.invocations = self.status_reads = 0
            self.auth_scope = DOMAINS[domain]["scope"]
        return {"ok": True}

    def invoke(self, intent: str, target: str, scope: str) -> tuple[int, dict]:
        with self.lock, self.db:
            fault = self.scenario if self.fault_intent is None or intent == self.fault_intent else "clean"
            self.invocations += 1
            self.log("invoke", intent, target)
            if scope != self.auth_scope or fault == "permission_denied":
                self.log("denied", intent)
                return 403, {"status": "denied"}
            if target == "primary" and fault in {"primary_unavailable", "incompatible_alternate"}:
                return 503, {"status": "unavailable"}
            existing = self.db.execute("SELECT status FROM intents WHERE intent=?", (intent,)).fetchone()
            if existing:
                self.log("deduplicated", intent, existing[0])
                return 200, {"status": existing[0]}
            if target == "primary" and fault == "lost_reply_before_commit":
                return 504, {"status": "timeout"}
            status = "partial" if target == "primary" and fault in {"partial_commit", "compensation_unavailable"} else "committed"
            self.db.execute("INSERT INTO intents VALUES (?,?,?,?)", (intent, self.domain, status, target))
            self.db.execute("INSERT INTO effects(intent,target,active) VALUES (?,?,1)", (intent, target))
            self.log("effect", intent, status)
            if target == "primary" and fault in {"lost_reply_after_commit", "stale_status_after_commit", "partial_commit", "compensation_unavailable"}:
                return 504, {"status": "timeout"}
            return 200, {"status": status}

    def status(self, intent: str) -> tuple[int, dict]:
        with self.lock, self.db:
            self.status_reads += 1
            row = self.db.execute("SELECT status FROM intents WHERE intent=?", (intent,)).fetchone()
            if self.scenario == "stale_status_after_commit" and (self.fault_intent is None or intent == self.fault_intent) and self.status_reads == 1:
                self.log("stale_read", intent)
                return 200, {"status": "unknown", "authoritative": False}
            return 200, {"status": row[0] if row else "absent", "authoritative": True}

    def compensate(self, intent: str) -> tuple[int, dict]:
        with self.lock, self.db:
            if self.scenario == "compensation_unavailable" and intent == self.fault_intent:
                self.log("compensation_unavailable", intent)
                return 503, {"status": "unavailable"}
            row = self.db.execute("SELECT status FROM intents WHERE intent=?", (intent,)).fetchone()
            if not row or row[0] not in {"partial", "committed"}:
                return 409, {"status": "invalid_compensation"}
            self.db.execute("UPDATE intents SET status='compensated' WHERE intent=?", (intent,))
            self.db.execute("UPDATE effects SET active=0 WHERE intent=?", (intent,))
            self.log("compensated", intent)
            return 200, {"status": "compensated"}

    def inspect(self) -> dict:
        with self.lock:
            intents = [dict(zip(("intent", "domain", "status", "target"), row)) for row in self.db.execute("SELECT * FROM intents ORDER BY intent")]
            effects = [dict(zip(("intent", "target", "active"), row)) for row in self.db.execute("SELECT intent,target,active FROM effects ORDER BY id")]
            events = [dict(zip(("seq", "kind", "intent", "detail"), row)) for row in self.db.execute("SELECT * FROM events ORDER BY seq")]
            return {"intents": intents, "effects": effects, "events": events}


def make_handler(state: ServiceState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, code: int, data: dict):
            payload = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size))
            if self.path == "/reset":
                self.reply(200, state.reset(body["domain"], body["scenario"], body.get("fault_intent")))
            elif self.path == "/invoke":
                self.reply(*state.invoke(body["intent"], body["target"], body["scope"]))
            elif self.path == "/compensate":
                self.reply(*state.compensate(body["intent"]))
            else:
                self.reply(404, {"error": "unknown_endpoint"})

        def do_GET(self):
            if self.path.startswith("/status/"):
                self.reply(*state.status(self.path.removeprefix("/status/")))
            elif self.path == "/state":
                self.reply(200, state.inspect())
            else:
                self.reply(404, {"error": "unknown_endpoint"})
    return Handler


def request(base: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(base + path, data=payload, method="POST" if body is not None else "GET",
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def run_case(base: str, domain: str, scenario: str, policy: str) -> dict:
    assert domain in DOMAINS and scenario in SCENARIOS and policy in POLICIES
    request(base, "/reset", {"domain": domain, "scenario": scenario})
    spec = DOMAINS[domain]
    original = f"{domain}-intent-001"

    def invoke(target: str, intent: str = original):
        return request(base, "/invoke", {"intent": intent, "target": target, "scope": spec["scope"]})

    code, result = invoke("primary")
    complete = code == 200 and result["status"] == "committed"
    outcome = "complete" if complete else "failed"
    status_calls = 0
    if not complete and policy == "retry" and code != 403:
        code, result = invoke("primary")
        complete = code == 200 and result["status"] == "committed"
        outcome = "complete" if complete else "failed"
    elif not complete and policy in {"verify_before_retry", "fa_mas"} and code != 403:
        _, observed = request(base, "/status/" + original)
        status_calls += 1
        # A replica's unknown answer cannot prove absence. FA-MAS can query an
        # authoritative ledger; the simple wrapper stops safely here.
        if observed["status"] == "unknown" and policy == "fa_mas":
            _, observed = request(base, "/status/" + original)
            status_calls += 1
        if observed["status"] == "committed":
            complete, outcome = True, "complete"
        elif observed["status"] == "absent" and observed["authoritative"]:
            code, result = invoke("primary")
            complete = code == 200 and result["status"] == "committed"
            if not complete and policy == "fa_mas":
                code, result = invoke("alternate")
                complete = code == 200 and result["status"] == "committed"
            outcome = "complete" if complete else "safe_stop"
        elif observed["status"] == "partial" and policy == "fa_mas":
            code, _ = request(base, "/compensate", {"intent": original})
            if code == 200:
                code, result = invoke("alternate", original + "-replacement")
                complete = code == 200 and result["status"] == "committed"
            outcome = "complete" if complete else "safe_stop"
        else:
            outcome = "safe_stop"
    if code == 403:
        # All controllers honor a provider's explicit denial. Counting this as
        # a failure for baseline controllers would artificially favor FA-MAS.
        outcome = "safe_stop"
    state = request(base, "/state")[1]
    active = [e for e in state["effects"] if e["active"]]
    partial = any(x["status"] == "partial" for x in state["intents"])
    denied = any(e["kind"] == "denied" for e in state["events"])
    duplicate = len(active) > 1
    unsafe = duplicate or partial  # Denied calls have no side effect; report separately.
    success = complete and len(active) == 1 and not unsafe and not denied
    safe_stop = outcome == "safe_stop" and not unsafe
    return {"evidence_class": "local_http_sqlite_no_llm", "domain": domain,
            "scenario": scenario, "policy": policy, "task_success": int(success),
            "safe_termination": int(safe_stop), "acceptable_outcome": int(success or safe_stop),
            "unsafe_outcome": int(unsafe), "duplicate_effect": int(duplicate),
            "unresolved_partial_effect": int(partial), "denied_attempt": int(denied),
            "http_invocations": sum(e["kind"] == "invoke" for e in state["events"]),
            "status_reads": status_calls,
            "trace_sha256": hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest(),
            "events": state["events"]}


def run_study(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        state = ServiceState(Path(folder) / "service.sqlite")
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            rows = [run_case(base, domain, scenario, policy)
                    for domain in DOMAINS for scenario in SCENARIOS for policy in POLICIES]
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
            state.db.close()
    trace_path = output / "local_service_traces.jsonl"
    trace_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    columns = [k for k in rows[0] if k != "events"]
    with (output / "local_service_runs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: row[k] for k in columns} for row in rows)
    metrics = ("task_success", "safe_termination", "acceptable_outcome", "unsafe_outcome",
               "duplicate_effect", "unresolved_partial_effect", "denied_attempt", "http_invocations")
    summary = [{"policy": policy, "cases": sum(r["policy"] == policy for r in rows),
                **{metric: sum(r[metric] for r in rows if r["policy"] == policy) for metric in metrics}}
               for policy in POLICIES]
    with (output / "local_service_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    manifest = {"evidence_class": "local_http_sqlite_no_llm", "run_count": len(rows),
                "paired_cases_per_policy": len(DOMAINS) * len(SCENARIOS),
                "domains": list(DOMAINS), "fault_scenarios": list(SCENARIOS), "policies": list(POLICIES),
                "protocol_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "interpretation": "Engineered conformance cases; counts are descriptive and do not estimate real-world fault incidence."}
    (output / "local_service_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report = [
        "# Local HTTP service evaluation", "",
        "The study executes **72 real HTTP request sequences** against a local SQLite-backed service. "
        "Each policy receives the same 18 engineered domain-by-fault cases. This is deterministic "
        "service conformance evidence, with no language model or external provider.", "",
        "| Policy | Cases | Complete | Safe stop | Acceptable | Unsafe | HTTP invokes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        report.append(f"| {row['policy']} | {row['cases']} | {row['task_success']} | "
                      f"{row['safe_termination']} | {row['acceptable_outcome']} | "
                      f"{row['unsafe_outcome']} | {row['http_invocations']} |")
    report.extend(["", "## Scope and controls", "",
                   "- The six cases are timeout after commit, timeout before commit, stale first status, "
                   "partial commit, unavailable primary, and denied permission.",
                   "- A fresh database state is established through the HTTP reset endpoint for each run. "
                   "The post-run judge reads the actual ledger, not the controller's response text.",
                   "- The retry policy uses the same stable idempotency key across retries. "
                   "This is a strong retry control, so no policy produced a duplicate effect.",
                   "- The verify-before-retry control performs one status read and retries only after "
                   "authoritative non-commit. FA-MAS performs a second status read if the first is stale "
                   "and can compensate a partial effect or substitute when the primary is unavailable.",
                   "- All policies stop on an explicit permission denial, which is judged a safe refusal; "
                   "the denied invocation is separately counted.",
                   "- Cases test one failing state-changing service call each. They do not test full "
                   "multi-step agent planning, calibrated risk ranking, live LLM decisions, production "
                   "fault incidence, or provider behavior. The stronger outcome for FA-MAS reflects "
                   "capabilities encoded in this scenario design; no p-values or population inference apply.", "",
                   "## Reproduce", "", "`PYTHONPATH=src python -m fa_mas.local_services`", "",
                   "The raw run table, event traces, and protocol digest are alongside this report."])
    (output / "REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps({"manifest": manifest, "summary": summary}, indent=2))
    return rows, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/local_services"))
    args = parser.parse_args()
    run_study(args.output)


if __name__ == "__main__":
    main()
