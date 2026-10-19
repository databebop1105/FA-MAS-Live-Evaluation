import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from fa_mas.local_services import ServiceState, make_handler, request, run_case


class LocalServiceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.state = ServiceState(Path(self.folder.name) / "service.sqlite")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.state.db.close()
        self.folder.cleanup()

    def test_lost_reply_is_committed_and_stable_key_deduplicates(self):
        request(self.base, "/reset", {"domain": "refund", "scenario": "lost_reply_after_commit"})
        payload = {"intent": "refund-42", "target": "primary", "scope": "refund:write"}
        self.assertEqual(request(self.base, "/invoke", payload)[0], 504)
        self.assertEqual(request(self.base, "/invoke", payload)[0], 200)
        state = request(self.base, "/state")[1]
        self.assertEqual(sum(x["active"] for x in state["effects"]), 1)
        self.assertIn("deduplicated", [x["kind"] for x in state["events"]])

    def test_partial_commit_needs_compensation_then_alternate(self):
        baseline = run_case(self.base, "travel", "partial_commit", "verify_before_retry")
        recovered = run_case(self.base, "travel", "partial_commit", "fa_mas")
        self.assertEqual((baseline["unsafe_outcome"], baseline["task_success"]), (1, 0))
        self.assertEqual((recovered["unsafe_outcome"], recovered["task_success"]), (0, 1))
        self.assertIn("compensated", [x["kind"] for x in recovered["events"]])

    def test_stale_status_does_not_authorize_retry(self):
        baseline = run_case(self.base, "incident", "stale_status_after_commit", "verify_before_retry")
        recovered = run_case(self.base, "incident", "stale_status_after_commit", "fa_mas")
        self.assertEqual(baseline["http_invocations"], 1)
        self.assertEqual(baseline["safe_termination"], 1)
        self.assertEqual(recovered["task_success"], 1)
        self.assertEqual(recovered["status_reads"], 2)

    def test_denial_is_safe_for_every_policy(self):
        for policy in ("static", "retry", "verify_before_retry", "fa_mas"):
            row = run_case(self.base, "refund", "permission_denied", policy)
            self.assertEqual(row["safe_termination"], 1)
            self.assertEqual(row["unsafe_outcome"], 0)
            self.assertEqual(row["denied_attempt"], 1)


if __name__ == "__main__":
    unittest.main()
