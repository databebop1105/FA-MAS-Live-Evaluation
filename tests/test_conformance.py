import json
import tempfile
import unittest
from pathlib import Path

from fa_mas.conformance import (
    INVENTORY_FAULTS,
    WORKFLOW_FAULTS,
    candidate_actions,
    run,
)


class ConformanceTests(unittest.TestCase):
    def test_candidate_spaces_are_finite_and_schema_complete(self):
        self.assertEqual(len(candidate_actions("workflow")), 39)
        self.assertEqual(len(candidate_actions("inventory")), 11)
        self.assertEqual(len(WORKFLOW_FAULTS), 8)
        self.assertEqual(len(INVENTORY_FAULTS), 8)
        self.assertEqual(
            {action["finish_reason"] for action in candidate_actions("workflow") if action["operation"] == "finish"},
            {"complete", "safe_stop", "escalate"},
        )

    def test_bounded_conformance_never_dispatches_a_blocked_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "conformance"
            summary = run(output)
            rows = [json.loads(line) for line in (output / "conformance_traces.jsonl").read_text().splitlines()]
            stored_summary = json.loads((output / "conformance_summary.json").read_text())

        self.assertEqual(len(rows), 812)
        self.assertEqual(summary["paired_schedules"], 406)
        self.assertEqual(summary["fa_mas_dispatched_blocked_actions"], 0)
        self.assertGreater(summary["fa_mas_gate_blocks"], 0)
        self.assertEqual(stored_summary["rows_sha256"], summary["rows_sha256"])
        self.assertTrue(all(row["evidence_class"] == "bounded_contract_conformance_no_llm" for row in rows))
        self.assertTrue(
            all(
                event["executed_action"] is None
                for row in rows
                if row["policy"] == "fa_mas"
                for event in row["events"]
                if event["gate_decision"]["outcome"] == "blocked"
            )
        )
        witnesses = {row["trace_id"]: row for row in summary["witness_pairs"]}
        for trace_id in (
            "workflow-prerequisite-step-2",
            "workflow-incompatible-alternate",
            "workflow-replacement-before-compensation",
            "inventory-wrong-sku-alternate",
        ):
            self.assertEqual(witnesses[trace_id]["baseline_unsafe"], 1)
            self.assertEqual(witnesses[trace_id]["fa_mas_unsafe"], 0)
            self.assertGreater(witnesses[trace_id]["fa_mas_gate_blocks"], 0)


if __name__ == "__main__":
    unittest.main()
