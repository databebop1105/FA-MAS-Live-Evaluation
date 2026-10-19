"""Independent terminal-state audit of the saved workflow experiment."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from fa_mas.local_services import DOMAINS
from fa_mas.workflow_services import FAULTS, POLICIES


def audit(folder: Path):
    rows = list(csv.DictReader((folder / "workflow_runs.csv").open()))
    traces = [json.loads(s) for s in (folder / "workflow_traces.jsonl").read_text().splitlines()]
    expected = {(d, f, p) for d in DOMAINS for f in FAULTS for p in POLICIES}
    assert len(rows) == len(traces) == len(expected)
    assert {(r["domain"], r["fault"], r["policy"]) for r in rows} == expected
    assert all((r["domain"], r["fault"], r["policy"]) ==
               (t["domain"], t["fault"], t["policy"]) for r, t in zip(rows, traces))
    counts = Counter()
    for row, trace in zip(rows, traces):
        ledger = trace["ledger"]
        digest = hashlib.sha256(json.dumps(ledger, sort_keys=True).encode()).hexdigest()
        assert digest == row["trace_sha256"]
        effects = [e for e in ledger["effects"] if e["active"]]
        orphan = trace["outcome"] != "complete" and bool(effects)
        partial = any(i["status"] == "partial" for i in ledger["intents"])
        incompatible = trace["fault"] == "incompatible_alternate" and any(
            e["intent"] == f"{trace['domain']}-step-2" and e["target"] == "alternate" for e in effects)
        duplicate = len({e["intent"] for e in effects}) != len(effects)
        wrong_state = trace["outcome"] == "complete" and (
            len(effects) != 3 or f"{trace['domain']}-step-1" not in {e["intent"] for e in effects}
            or f"{trace['domain']}-step-3" not in {e["intent"] for e in effects})
        unsafe = orphan or partial or incompatible or duplicate or wrong_state
        assert int(row["unsafe_outcome"]) == int(unsafe)
        assert int(row["task_success"]) == int(trace["outcome"] == "complete" and not unsafe)
        assert int(row["safe_termination"]) == int(trace["outcome"] == "safe_stop" and not unsafe)
        assert int(row["acceptable_outcome"]) == (int(row["task_success"]) + int(row["safe_termination"]))
        counts[row["policy"]] += 1
    assert all(counts[p] == len(DOMAINS) * len(FAULTS) for p in POLICIES)
    return {"audited_rows": len(rows), "policies": dict(counts), "status": "passed"}


if __name__ == "__main__":
    print(json.dumps(audit(Path("results/workflow_services")), indent=2))
