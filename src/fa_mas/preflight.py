"""Review a bounded development run before a single-configuration freeze.

This tool deliberately reviews only the sanitized development manifest and
trace records. It does not run a model, read credentials, or make a provider
request. A passing report binds the development result to the exact source,
task bank, access settings, and protocol hash subsequently accepted by freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .bounded_e2e import (
    POLICIES,
    freeze_hash,
    load_tasks,
    model_classes,
    public_model_spec,
    validate_access,
    validate_protocol,
)


SECRET_PATTERN = re.compile(
    r"(?:\b(?:sk|key)_[A-Za-z0-9_-]{12,}\b|\bbearer\s+(?!\[redacted\])[A-Za-z0-9._-]{12,})",
    re.IGNORECASE,
)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


def _row_configuration_id(row: dict[str, Any]) -> str | None:
    value = row.get("model_configuration_id", row.get("model_class"))
    return value if isinstance(value, str) else None


def review(
    protocol_path: Path,
    tasks_path: Path,
    access_path: Path,
    runs_path: Path,
    manifest_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Write an immutable pass/fail report for the configured development run."""
    if report_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing preflight report: {report_path}")

    failures: list[str] = []
    protocol = _load_json(protocol_path, "Protocol")
    access = _load_json(access_path, "Access configuration")
    manifest = _load_json(manifest_path, "Development manifest")
    development = load_tasks(tasks_path, "development")
    confirmatory = load_tasks(tasks_path, "confirmatory")
    classes = validate_protocol(protocol, development, confirmatory)
    if not protocol.get("require_preflight_report", False):
        raise ValueError("Protocol does not require a single-configuration preflight")
    if len(classes) != 1:
        raise ValueError("Preflight review is limited to one named model configuration")
    validate_access(access, require_confirmatory_guarantees=False, expected_model_classes=classes)

    expected_hash = freeze_hash(protocol_path, tasks_path, access_path)
    if manifest.get("evidence_class") != "live_development_local_services":
        failures.append("manifest does not identify development-only live evidence")
    if manifest.get("protocol_sha256") != expected_hash:
        failures.append("manifest protocol hash differs from current source/configuration")
    if not runs_path.exists() or hashlib.sha256(runs_path.read_bytes()).hexdigest() != manifest.get("runs_sha256"):
        failures.append("development trace hash differs from its manifest")

    try:
        rows = [json.loads(line) for line in runs_path.read_text().splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        rows = []
        failures.append("development trace file is unreadable")

    expected_model = public_model_spec(access["models"][0])
    manifest_models = manifest.get("models")
    if manifest_models != [expected_model]:
        failures.append("manifest model configuration differs from the reviewed access configuration")

    expected_cells = {
        (task["task_id"], policy, expected_model.get("configuration_id", classes[0]))
        for task in development
        for policy in POLICIES
    }
    actual_cells = {
        (row.get("task_id"), row.get("policy"), _row_configuration_id(row))
        for row in rows
        if isinstance(row, dict)
    }
    if actual_cells != expected_cells or len(rows) != len(expected_cells) or not manifest.get("complete_matrix"):
        failures.append("development matrix is incomplete, duplicated, or uses an unexpected task/policy/configuration cell")

    operations: set[str] = set()
    all_finished = True
    for row in rows:
        if not isinstance(row, dict):
            all_finished = False
            continue
        if row.get("evidence_class") != "live_development_local_services":
            failures.append("a row is not labeled development-only live evidence")
        if row.get("model_id") != expected_model.get("model_id") or row.get("model_class") != classes[0]:
            failures.append("a row has a different model identity or configuration class")
        if row.get("status") != "finished" or row.get("error") is not None:
            all_finished = False
        events = row.get("events")
        if not isinstance(events, list) or len(events) < 2 or row.get("model_responses") != len(events):
            failures.append("a development trajectory did not complete a multi-turn model/tool cycle")
            continue
        if not any(event.get("proposed_action", {}).get("operation") == "finish" for event in events if isinstance(event, dict)):
            failures.append("a development trajectory lacks an explicit model-selected finish")
        for event in events:
            if not isinstance(event, dict):
                failures.append("a development event is malformed")
                continue
            action = event.get("proposed_action")
            if isinstance(action, dict) and isinstance(action.get("operation"), str):
                operations.add(action["operation"])
            model = event.get("model")
            shape = model.get("response_shape") if isinstance(model, dict) else None
            if (not isinstance(model, dict) or not isinstance(model.get("tool_call_id"), str) or
                    not isinstance(shape, dict) or shape.get("tool_call_count") != 1):
                failures.append("a development response lacks exactly one preserved tool call")
    if not all_finished:
        failures.append("one or more development trajectories did not finish without an operational error")
    if "finish" not in operations or len(operations - {"finish"}) < 2:
        failures.append("the development run did not demonstrate multiple non-finish operations plus explicit finish")

    try:
        raw = runs_path.read_text()
    except OSError:
        raw = ""
    if SECRET_PATTERN.search(raw):
        failures.append("development trace contains a credential-like string")

    report = {
        "report_version": "openai-single-preflight-v1",
        "status": "passed" if not failures else "failed",
        "development_protocol_sha256": expected_hash,
        "runs_sha256": manifest.get("runs_sha256"),
        "configuration": expected_model,
        "planned_episodes": len(expected_cells),
        "observed_episodes": len(rows),
        "operations_observed": sorted(operations),
        "failures": sorted(set(failures)),
        "scope": "development-only integration acceptance; not held-out outcome evidence",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--access", required=True)
    parser.add_argument("--runs", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = review(
        Path(args.protocol), Path(args.tasks), Path(args.access), Path(args.runs),
        Path(args.manifest), Path(args.report),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "passed":
        raise SystemExit("Preflight failed; no freeze is authorized")


if __name__ == "__main__":
    main()
