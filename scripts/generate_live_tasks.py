"""Generate the frozen, entity-disjoint Tier-2 task bank deterministically."""
from __future__ import annotations

import json
from pathlib import Path


DOMAINS = {
    "refund": {
        "goals": [
            "Refund a verified duplicate subscription renewal",
            "Reverse an eligible shipping overcharge",
            "Refund a canceled event ticket",
            "Correct a duplicate marketplace debit",
            "Refund an approved service credit",
        ],
        "steps": ["account_lookup", "policy_check", "refund", "notify"],
        "scope": "refund:write", "fault_steps": [1, 2, 2, 3], "idempotent": True,
    },
    "travel": {
        "goals": [
            "Reserve a refundable hotel and issue payment",
            "Book a flight itinerary subject to a fixed budget",
            "Reserve a rail itinerary and confirm the ticket",
            "Book a rental car with free cancellation",
            "Reserve a connecting itinerary with a price ceiling",
        ],
        "steps": ["search", "reserve", "pay", "confirm"],
        "scope": "booking:write", "fault_steps": [0, 1, 2, 3], "idempotent": False,
    },
    "incident": {
        "goals": [
            "Diagnose and roll back a faulty service deployment",
            "Restore a degraded service and validate health",
            "Remediate a saturated worker pool",
            "Restart a stalled consumer and verify recovery",
            "Roll back a configuration regression",
        ],
        "steps": ["telemetry", "localize", "remediate", "validate"],
        "scope": "ops:write", "fault_steps": [0, 1, 2, 3], "idempotent": True,
    },
}


def build() -> list[dict]:
    rows = []
    for domain, spec in DOMAINS.items():
        rows.append({"task_id": f"dev-{domain}-01", "split": "development", "domain": domain,
                     "goal": spec["goals"][0] + " using development entities", "steps": spec["steps"],
                     "fault_step": spec["fault_steps"][0], "required_scope": spec["scope"],
                     "idempotent": spec["idempotent"], "entity_set": f"dev-{domain}"})
        for i in range(30):
            rows.append({"task_id": f"confirm-{domain}-{i+1:02d}", "split": "confirmatory", "domain": domain,
                         "goal": f"{spec['goals'][i % len(spec['goals'])]} for held-out case {i+1:02d}",
                         "steps": spec["steps"], "fault_step": spec["fault_steps"][i % 4],
                         "required_scope": spec["scope"], "idempotent": spec["idempotent"],
                         "entity_set": f"heldout-{domain}-{i+1:02d}"})
    return rows


if __name__ == "__main__":
    path = Path("configs/live_tasks_v1.jsonl")
    path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in build()) + "\n")
    print(f"wrote {len(build())} tasks to {path}")
