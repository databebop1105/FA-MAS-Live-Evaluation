"""Bounded, model-free conformance checks for the implemented FA-MAS gates.

This module is intentionally not a language-model evaluation.  It enumerates
the finite, schema-valid one-action proposals available at an empty service
state for every authored fault family, then executes a small set of
state-dependent witness traces.  Each proposal is run against both the
feature-matched gate ablation and FA-MAS, and terminal state is judged without
consulting a controller success claim.

The result is evidence about the implemented controller under declared local
service semantics.  It is not a proof about arbitrary production services,
unbounded traces, or model behavior.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .bounded_e2e import Episode, POLICIES, canonical, digest, make_action, services


WORKFLOW_FAULTS = (
    "clean",
    "lost_reply_after_commit",
    "lost_reply_before_commit",
    "stale_status_after_commit",
    "partial_commit",
    "primary_unavailable",
    "incompatible_alternate",
    "compensation_unavailable",
)
INVENTORY_FAULTS = (
    "clean",
    "lost_after_hold",
    "lost_before_hold",
    "stale_read",
    "primary_outage",
    "wrong_sku_alternate",
    "capture_denied_release_unavailable",
    "capacity_exhausted",
)
EVIDENCE_CLASS = "bounded_contract_conformance_no_llm"

# These are deliberately fixed and small.  They prevent the conformance runner
# from becoming a hidden, open-ended policy search and make its trace space
# auditable from the source alone.
PROTOCOL = {
    "max_turns": 8,
    "max_tool_calls": 8,
    "episode_deadline_seconds": 30,
}


def task_fixture(service: str, fault: str) -> dict[str, Any]:
    """Return an authored fixture independent of the development/held-out bank."""
    if service == "workflow":
        if fault not in WORKFLOW_FAULTS:
            raise ValueError(f"Unknown workflow fault: {fault}")
        return {
            "task_id": f"conformance-workflow-{fault}",
            "split": "conformance",
            "service": "workflow",
            "fault": fault,
            "length": 3,
            "requested_sku": "sku-B",
            "capacity": 2,
            "variant": 0,
        }
    if service == "inventory":
        if fault not in INVENTORY_FAULTS:
            raise ValueError(f"Unknown inventory fault: {fault}")
        return {
            "task_id": f"conformance-inventory-{fault}",
            "split": "conformance",
            "service": "inventory",
            "fault": fault,
            "length": 1,
            "requested_sku": "sku-B",
            "capacity": 2,
            "variant": 0,
        }
    raise ValueError(f"Unknown service: {service}")


def _finish(reason: str = "safe_stop") -> dict[str, Any]:
    return make_action("finish", reason=reason)


def candidate_actions(service: str) -> list[dict[str, Any]]:
    """Enumerate all schema-valid one-turn proposals at an empty state.

    The tool schema uses a common action shape.  Some fields are semantically
    irrelevant to a particular operation but are still valid input to the
    controller, so they remain in this finite enumeration.
    """
    actions: list[dict[str, Any]] = []
    if service == "workflow":
        for operation in ("invoke", "status", "compensate"):
            for step in (1, 2, 3):
                for target in ("primary", "alternate"):
                    for replacement in (False, True):
                        actions.append(make_action(operation, step, target, replacement))
    elif service == "inventory":
        for operation in ("hold", "status", "capture", "release"):
            for target in ("primary", "alternate"):
                actions.append(make_action(operation, 1, target, False))
    else:
        raise ValueError(f"Unknown service: {service}")
    actions.extend(_finish(reason) for reason in ("complete", "safe_stop", "escalate"))
    return actions


def _event(episode: Episode, action: dict[str, Any], turn: int) -> dict[str, Any]:
    """Execute one proposal while retaining its pre-dispatch gate decision."""
    validation_error = episode.validate(action)
    gate_reason = None if validation_error else episode.gate(action)
    executed_action = action if validation_error is None and gate_reason is None else None
    observation = episode.execute(action)
    return {
        "turn": turn,
        "proposed_action": action,
        "validation_error": validation_error,
        "gate_decision": {
            "outcome": "not_evaluated" if validation_error else "blocked" if gate_reason else "allowed",
            "reason": gate_reason,
        },
        "executed_action": executed_action,
        "observation": observation,
    }


def run_trace(
    base: str,
    task: dict[str, Any],
    policy: str,
    trace_id: str,
    actions: Iterable[dict[str, Any]],
    suite: str,
) -> dict[str, Any]:
    """Run a finite proposal sequence and independently judge terminal state."""
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy: {policy}")
    episode = Episode(base, task, policy, PROTOCOL)
    events = []
    status = "exhausted"
    for turn, action in enumerate(actions):
        if turn >= PROTOCOL["max_turns"]:
            status = "turn_limit"
            break
        event = _event(episode, action, turn)
        events.append(event)
        if episode.finished:
            status = "finished"
            break
    state = episode.snapshot()
    verdict = episode.judge(state)
    return {
        "trace_id": trace_id,
        "suite": suite,
        "service": task["service"],
        "fault": task["fault"],
        "policy": policy,
        "status": status,
        "proposed_action_count": len(events),
        "tool_calls": episode.calls,
        "gate_block_count": sum(event["gate_decision"]["outcome"] == "blocked" for event in events),
        "dispatched_blocked_action_count": sum(
            event["gate_decision"]["outcome"] == "blocked" and event["executed_action"] is not None
            for event in events
        ),
        **verdict,
        "trace_sha256": digest({"events": events, "state": state}),
        "events": events,
        "state": state,
        "evidence_class": EVIDENCE_CLASS,
    }


def _single_action_traces() -> list[tuple[str, str, str, list[dict[str, Any]]]]:
    traces = []
    for service, faults in (("workflow", WORKFLOW_FAULTS), ("inventory", INVENTORY_FAULTS)):
        for fault in faults:
            for index, action in enumerate(candidate_actions(service)):
                actions = [action] if action["operation"] == "finish" else [action, _finish()]
                traces.append((f"single-{service}-{fault}-{index:02d}", service, fault, actions))
    return traces


def witness_traces() -> list[tuple[str, str, str, list[dict[str, Any]]]]:
    """State-dependent traces that exercise each implemented contract gate."""
    return [
        (
            "workflow-prerequisite-step-2",
            "workflow",
            "clean",
            [make_action("invoke", 2), _finish()],
        ),
        (
            "workflow-incompatible-alternate",
            "workflow",
            "incompatible_alternate",
            [make_action("invoke", 1, "alternate"), _finish()],
        ),
        (
            "workflow-replacement-before-compensation",
            "workflow",
            "partial_commit",
            [
                make_action("invoke", 1),
                make_action("invoke", 1, "alternate", True),
                make_action("compensate", 1),
                _finish(),
            ],
        ),
        (
            "inventory-wrong-sku-alternate",
            "inventory",
            "wrong_sku_alternate",
            [make_action("hold", target="alternate"), make_action("capture"), _finish()],
        ),
        (
            "inventory-capture-without-observed-hold",
            "inventory",
            "clean",
            [make_action("capture"), _finish()],
        ),
        (
            "inventory-reconcile-before-capture",
            "inventory",
            "lost_after_hold",
            [make_action("hold"), make_action("capture"), make_action("status"), make_action("capture"), _finish("complete")],
        ),
    ]


def _run_all_traces() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    schedules = [("single_action", *entry) for entry in _single_action_traces()]
    schedules.extend(("witness", *entry) for entry in witness_traces())
    with services() as bases:
        for suite, trace_id, service, fault, actions in schedules:
            task = task_fixture(service, fault)
            for policy in POLICIES:
                rows.append(run_trace(bases[service], task, policy, trace_id, actions, suite))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize implementation properties without inferential statistics."""
    if not rows:
        raise ValueError("No conformance rows")
    fa_rows = [row for row in rows if row["policy"] == "fa_mas"]
    baseline_rows = [row for row in rows if row["policy"] == "feature_matched"]
    paired = {}
    for row in rows:
        key = (row["trace_id"], row["suite"])
        paired.setdefault(key, {})[row["policy"]] = row
    witnesses = []
    for key, pair in sorted(paired.items()):
        if key[1] != "witness" or set(pair) != set(POLICIES):
            continue
        baseline, fa_mas = pair["feature_matched"], pair["fa_mas"]
        witnesses.append({
            "trace_id": key[0],
            "baseline_unsafe": baseline["unsafe_outcome"],
            "fa_mas_unsafe": fa_mas["unsafe_outcome"],
            "fa_mas_safe_termination": fa_mas["safe_termination"],
            "fa_mas_gate_blocks": fa_mas["gate_block_count"],
        })
    block_reasons = Counter(
        event["gate_decision"]["reason"]
        for row in fa_rows
        for event in row["events"]
        if event["gate_decision"]["outcome"] == "blocked"
    )
    return {
        "evidence_class": EVIDENCE_CLASS,
        "scope": (
            "finite schema-valid one-action proposals at empty local state plus six fixed "
            "state-dependent witness traces; not an LLM, production, or unbounded-trace evaluation"
        ),
        "traces": len(rows),
        "paired_schedules": len(paired),
        "single_action_schedules": sum(row["suite"] == "single_action" for row in fa_rows),
        "witness_schedules": len(witnesses),
        "fa_mas_gate_blocks": sum(row["gate_block_count"] for row in fa_rows),
        "fa_mas_dispatched_blocked_actions": sum(row["dispatched_blocked_action_count"] for row in fa_rows),
        "baseline_dispatched_valid_proposals": sum(row["tool_calls"] for row in baseline_rows),
        "fa_mas_unsafe_outcomes": sum(row["unsafe_outcome"] for row in fa_rows),
        "baseline_unsafe_outcomes": sum(row["unsafe_outcome"] for row in baseline_rows),
        "block_reasons": dict(sorted(block_reasons.items())),
        "witness_pairs": witnesses,
    }


def _report(summary: dict[str, Any]) -> str:
    witness_lines = [
        "| Witness trace | Baseline unsafe | FA-MAS unsafe | FA-MAS safe termination | FA-MAS gate blocks |",
        "|---|---:|---:|---:|---:|",
    ]
    witness_lines.extend(
        f"| `{row['trace_id']}` | {row['baseline_unsafe']} | {row['fa_mas_unsafe']} | "
        f"{row['fa_mas_safe_termination']} | {row['fa_mas_gate_blocks']} |"
        for row in summary["witness_pairs"]
    )
    block_lines = "\n".join(
        f"- {reason}: {count}" for reason, count in summary["block_reasons"].items()
    ) or "- No blocked proposals"
    return "\n".join([
        "# Bounded contract-conformance report",
        "",
        "This is a model-free, bounded conformance check of the implemented controller. It enumerates schema-valid one-action proposals at empty local state for every authored fault family, plus fixed state-dependent witness traces. It is not a model evaluation, external benchmark, production-service test, or unbounded proof.",
        "",
        "## Summary",
        "",
        f"- Paired schedules: {summary['paired_schedules']}",
        f"- Executions: {summary['traces']}",
        f"- FA-MAS gate blocks: {summary['fa_mas_gate_blocks']}",
        f"- Blocked proposals dispatched to a service: {summary['fa_mas_dispatched_blocked_actions']}",
        f"- Baseline unsafe terminal outcomes: {summary['baseline_unsafe_outcomes']}",
        f"- FA-MAS unsafe terminal outcomes: {summary['fa_mas_unsafe_outcomes']}",
        "",
        "A zero dispatched-blocked-action count demonstrates only that the implemented gate stopped the proposal before its service call under this finite enumeration. It is not a production-safety guarantee. Differences between the two policy counts are properties of the declared gate ablation, not an estimate of model or deployment performance.",
        "",
        "## Gate-block reasons",
        "",
        block_lines,
        "",
        "## State-dependent witnesses",
        "",
        *witness_lines,
        "",
        "Every row, proposal, gate decision, service observation, terminal state, and trace digest is retained in `conformance_traces.jsonl`.",
        "",
    ])


def write_report(output: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    trace_path = output / "conformance_traces.jsonl"
    evidence_files = (
        "conformance_traces.jsonl",
        "conformance_runs.csv",
        "conformance_summary.json",
        "REPORT.md",
    )
    if any((output / name).exists() for name in evidence_files):
        raise FileExistsError(f"Refusing to overwrite existing conformance evidence in {output}")
    trace_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    columns = [
        "trace_id", "suite", "service", "fault", "policy", "status", "proposed_action_count",
        "tool_calls", "gate_block_count", "dispatched_blocked_action_count", "task_success",
        "safe_termination", "unsafe_outcome", "acceptable_outcome", "trace_sha256", "evidence_class",
    ]
    with (output / "conformance_runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({column: row[column] for column in columns} for row in rows)
    summary["rows_sha256"] = digest(rows)
    (output / "conformance_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (output / "REPORT.md").write_text(_report(summary))


def run(output: Path) -> dict[str, Any]:
    rows = _run_all_traces()
    summary = summarize(rows)
    if summary["fa_mas_dispatched_blocked_actions"] != 0:
        raise AssertionError("A blocked FA-MAS proposal reached a service")
    write_report(output, rows, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/conformance_v1")
    args = parser.parse_args()
    print(json.dumps(run(Path(args.output)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
