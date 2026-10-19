import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from fa_mas.local_services import ServiceState, make_handler, request
from fa_mas.workflow_services import run_case


class WorkflowServiceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.state = ServiceState(Path(self.folder.name) / "service.sqlite")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.state.db.close(); self.folder.cleanup()

    def test_fault_is_scoped_to_middle_step(self):
        result = run_case(self.base, "refund", "lost_reply_after_commit", "fa_mas")
        self.assertEqual((result["task_success"], result["unsafe_outcome"]), (1, 0))
        effects = result["ledger"]["effects"]
        self.assertEqual({x["intent"] for x in effects if x["active"]},
                         {"refund-step-1", "refund-step-2", "refund-step-3"})

    def test_denial_rolls_back_previously_committed_write(self):
        result = run_case(self.base, "travel", "permission_denied", "fa_mas")
        self.assertEqual((result["safe_termination"], result["unsafe_outcome"]), (1, 0))
        self.assertEqual(sum(x["active"] for x in result["ledger"]["effects"]), 0)
        self.assertEqual(result["denied_attempt"], 1)

    def test_partial_effect_compensated_then_replaced(self):
        result = run_case(self.base, "incident", "partial_commit", "feature_matched")
        self.assertEqual(result["task_success"], 1)
        self.assertEqual(result["compensations"], 1)
        self.assertEqual(result["unresolved_partial"], 0)

    def test_incompatible_substitute_detected_from_ledger(self):
        greedy = run_case(self.base, "travel", "incompatible_alternate", "feature_matched")
        gated = run_case(self.base, "travel", "incompatible_alternate", "fa_mas")
        self.assertEqual((greedy["incompatible_effect"], greedy["unsafe_outcome"]), (1, 1))
        self.assertEqual((gated["safe_termination"], gated["unsafe_outcome"]), (1, 0))
        self.assertEqual(sum(x["active"] for x in gated["ledger"]["effects"]), 0)

    def test_failed_compensation_remains_unsafe(self):
        result = run_case(self.base, "refund", "compensation_unavailable", "fa_mas")
        self.assertEqual((result["task_success"], result["safe_termination"], result["unsafe_outcome"]),
                         (0, 0, 1))
        self.assertEqual(result["unresolved_partial"], 1)


if __name__ == "__main__":
    unittest.main()
